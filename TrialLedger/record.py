"""Write a complete pull to disk, all of it or none of it: the record, the registry's spreadsheet, and the
review workbook certified against the record. And re-derive a written folder to certify it later.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from TrialLedger import __version__, warrants
from TrialLedger.cells import GOOGLE_SHEETS_CELLS, book_size_state
from TrialLedger.ingest import API_BASE, Pull
from TrialLedger.ledger import as_list, get
from TrialLedger.workbook import (
    BOOKS,
    CODE_ROOT,
    RECORD_NAME,
    WORKBOOK_NAME,
    WRITER,
    certify,
    file_problems,
    write_workbook,
)

JSON_NAME = "studies.json"
CSV_NAME = "studies.csv"
UTF8_BOM = "﻿"  # tells Excel the CSV is UTF-8; it changes no cell
# The provenance entries that are content addresses: a record without them cannot be verified.
DIGEST_KEYS = ("study_digests", "merkle_root", "spreadsheet_sha256", "record_root")
PACKAGE = Path(__file__).parent


def _ignore(_message: str) -> None:
    """Default progress sink: say nothing."""


def code_commit(package: Path = PACKAGE) -> str:
    """The git commit the derivation code was checked out at, marked when that code has uncommitted changes;
    "not a git checkout" when git cannot say. The code root, not the commit, is what a warrant commits to."""
    files = [str(path) for path in warrants.derivation_files(package)]
    git = ["git", "-C", str(package)]
    try:
        head = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        changes = subprocess.run(
            [*git, "status", "--porcelain", "--", *files], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "not a git checkout"
    commit = head.stdout.strip()
    return f"{commit} with uncommitted changes to the derivation code" if changes.stdout.strip() else commit


def record_root(provenance: dict[str, Any]) -> str:
    """The root of a written record: its whole provenance, the studies' digests, their Merkle root and the
    spreadsheet's digest included, everything but the record root itself."""
    committed = {key: value for key, value in provenance.items() if key != "record_root"}
    return warrants.digest("record", warrants.canonical(committed))


def digests(provenance: dict[str, Any], studies: list[dict[str, Any]], spreadsheet: bytes) -> dict[str, Any]:
    """The provenance's content addresses: each study's digest in pull order with its NCT number, their
    Merkle root, the SHA-256 of the spreadsheet's bytes as written, and the record root over all of it."""
    study_digests = [warrants.study_digest(study) for study in studies]
    merkle = warrants.merkle_root(study_digests)
    spreadsheet_sha256 = hashlib.sha256(spreadsheet).hexdigest()
    addresses: dict[str, Any] = {
        "study_digests": [
            {"nctId": get(study, "protocolSection", "identificationModule", "nctId"), "digest": digest}
            for study, digest in zip(studies, study_digests, strict=True)
        ],
        "merkle_root": merkle,
        "spreadsheet_sha256": spreadsheet_sha256,
    }
    addresses["record_root"] = record_root({**provenance, **addresses})
    return addresses


def write_record(pull: Pull, out_dir: Path, *, progress: Callable[[str], None] = _ignore) -> list[Path]:
    """Create `out_dir` holding studies.json (the raw records, provenance and content digests), studies.csv,
    review.xlsx and record.xlsx (both workbooks certified against the record before anything is renamed into
    place).

    studies.csv is the API's own CSV for the same query, byte for byte, after a UTF-8 byte-order mark. The
    files are written into `<out_dir>.partial` and renamed into place only when all four are complete and
    both workbooks re-derive from the record, so a failure leaves no record at all. A workbook over Google
    Sheets' cap on cells is named through `progress`. An existing `out_dir` is never overwritten.
    """
    if out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists; TrialLedger never overwrites a record")
    staging = out_dir.with_name(out_dir.name + ".partial")
    staging.mkdir(parents=True)
    try:
        spreadsheet = (UTF8_BOM + pull.csv_text).encode("utf-8")
        provenance: dict[str, Any] = {
            "source": f"{API_BASE}/studies",
            "query": pull.query,
            "api_version": pull.api_version,
            "data_timestamp": pull.data_timestamp,
            "retrieved_at": pull.retrieved_at,
            "study_count": pull.total_count,
            "spreadsheet": f"{CSV_NAME}: ClinicalTrials.gov's own CSV (format=csv) for this query",
            "workbook": f"{WORKBOOK_NAME}: the review workbook, the design questions study by study, every "
            "cell warranted (trialledger verify)",
            "record_workbook": f"{RECORD_NAME}: every value of every study in the registry's own categories, "
            "every cell warranted (trialledger verify)",
            "tool": f"TrialLedger {__version__}",
            "writer": WRITER,
            "code_root": CODE_ROOT,
            "code_commit": code_commit(),
        }
        if pull.requested_ids:
            provenance["requested_ids"] = pull.requested_ids
        provenance.update(digests(provenance, pull.studies, spreadsheet))
        record = {"provenance": provenance, "studies": pull.studies}
        (staging / JSON_NAME).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / CSV_NAME).write_bytes(spreadsheet)
        for book in BOOKS:
            progress(f"writing and certifying {book.name} ({len(pull.studies)} studies)")
            cells = write_workbook(record, staging / book.name, book)
            if book_size_state(cells) == "over_google_sheets":
                progress(
                    f"note: {book.name} holds {cells:,} cells, more than the {GOOGLE_SHEETS_CELLS:,} that "
                    "Google Sheets opens in one spreadsheet"
                )
        staging.rename(out_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return [out_dir / JSON_NAME, out_dir / CSV_NAME, *(out_dir / book.name for book in BOOKS)]


def record_problems(record: Any, spreadsheet: bytes | None) -> list[str]:
    """Whatever in a written record no longer matches its own provenance digests (pure — pinned).

    Each problem names what differs: a study's digest or NCT number (by position), the Merkle root, the
    spreadsheet's digest, the record root (which commits to the whole provenance), or the absence of
    the digests (a record written before warrants). Empty when every digest re-derives.
    """
    provenance = record.get("provenance") if isinstance(record, dict) else None
    studies = as_list(record.get("studies")) if isinstance(record, dict) else []
    if not isinstance(provenance, dict) or not all(key in provenance for key in DIGEST_KEYS):
        return ["record.no_digests: the record carries no content digests (written before warrants)"]
    problems: list[str] = []
    recorded = as_list(provenance.get("study_digests"))
    recomputed = [warrants.study_digest(study) for study in studies]
    if len(recorded) != len(recomputed):
        problems.append(f"record.study_count: {len(recorded)} digests recorded for {len(recomputed)} studies")
    for index, (entry, study, digest) in enumerate(zip(recorded, studies, recomputed, strict=False)):
        label = get(entry, "nctId")
        if get(entry, "digest") != digest:
            problems.append(f"record.study_digest: study {index} ({label}) no longer matches its digest")
        actual = get(study, "protocolSection", "identificationModule", "nctId")
        if label != actual:
            problems.append(
                f"record.study_label: study {index} is recorded as {label}, its record is {actual}"
            )
    merkle, spreadsheet_sha256 = provenance.get("merkle_root"), provenance.get("spreadsheet_sha256")
    if merkle != warrants.merkle_root(recomputed):
        problems.append("record.merkle_root: the studies no longer match the recorded root")
    if spreadsheet is None:
        problems.append(f"record.no_spreadsheet: {CSV_NAME} is missing")
    elif spreadsheet_sha256 != hashlib.sha256(spreadsheet).hexdigest():
        problems.append(f"record.spreadsheet_digest: {CSV_NAME} no longer matches its digest")
    if provenance.get("record_root") != record_root(provenance):
        problems.append("record.record_root: the provenance no longer matches the recorded root")
    return problems


class DuplicateKey(ValueError):
    """An object in studies.json repeats a key, so a reader and a parser can see different values."""


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    repeated = sorted(key for key, count in Counter(key for key, _ in pairs).items() if count > 1)
    if repeated:
        raise DuplicateKey(", ".join(repeated))
    return dict(pairs)


def verify_folder(folder: Path, *, limit: int = 20) -> tuple[str, list[str]]:
    """Certify a folder TrialLedger wrote, by re-deriving every digest and root, every cell and warrant of
    both workbooks, and both workbook files themselves, under the code and writer that wrote them.

    ("certified", [])           — everything re-derives from studies.json.
    ("not_certified", problems) — something no longer follows, each named.
    ("not_a_record", [reason])  — no readable studies.json here.
    """
    try:
        record = json.loads((folder / JSON_NAME).read_text(encoding="utf-8"), object_pairs_hook=_unique)
    except DuplicateKey as repeated:
        return "not_certified", [f"record.duplicate_key: an object in {JSON_NAME} repeats the key {repeated}"]
    except (OSError, ValueError) as error:  # unreadable, not UTF-8, not JSON, or a number Python cannot read
        return "not_a_record", [f"{folder / JSON_NAME}: {error}"]
    try:
        warrants.canonical(record)
    except UnicodeEncodeError:
        return "not_certified", [
            f"record.invalid_text: {JSON_NAME} holds text that is not Unicode (a lone surrogate), which "
            "TrialLedger never writes"
        ]
    csv_path = folder / CSV_NAME
    problems = record_problems(record, csv_path.read_bytes() if csv_path.is_file() else None)
    if any(problem.startswith("record.no_digests") for problem in problems):
        return "not_certified", problems[:limit]
    provenance = record["provenance"]
    missing = [book.name for book in BOOKS if not (folder / book.name).is_file()]
    if missing:
        problems.extend(f"workbook.missing: {name} is not in the folder" for name in missing)
    elif provenance.get("code_root") != CODE_ROOT:
        problems.append(
            f"record.code_root: written by TrialLedger derivation code {provenance.get('code_root')} (commit "
            f"{provenance.get('code_commit')}), and this is {CODE_ROOT}; a warrant re-derives only under the "
            "code that wrote it, so verify the folder with TrialLedger at that commit"
        )
    elif provenance.get("writer") != WRITER:
        cells = [p for book in BOOKS for p in certify(record, folder / book.name, book=book, limit=limit)]
        problems.extend(cells)
        if not cells:
            problems.append(
                f"record.writer: the workbooks were written with {provenance.get('writer')} and this "
                f"TrialLedger writes with {WRITER}, so their files cannot be compared byte for byte"
            )
    else:
        # A file identical, part for part, to what this code writes for the record holds exactly the cells the
        # record derives, so the cell-by-cell comparison runs only on a file that differs, to name the cells.
        files = {book.name: file_problems(record, folder / book.name, book) for book in BOOKS}
        differing = [book for book in BOOKS if files[book.name]]
        cells = [p for book in differing for p in certify(record, folder / book.name, book=book, limit=limit)]
        problems.extend(cells or [p for book in differing for p in files[book.name]])
    return ("certified", []) if not problems else ("not_certified", problems[:limit])
