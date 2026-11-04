"""Exact retained study access and transport-only source references.

The reference is resolved before reasoning, then the complete study becomes part of the
ordinary immutable request. This module neither interprets source text nor changes standing.
Its record-reading path imports no layer-two compiler.
"""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

from TrialLedger.landscape_verify import strict_json
from TrialLedger.record import DuplicateKey
from TrialLedger.warrants import canonical, study_digest

MARKER = "$retained_study"
RUN_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"
NCT_PATTERN = r"NCT[0-9]{8}"
DIGEST_PATTERN = r"[0-9a-f]{64}"
SOURCE_CODES = ("invalid_source_run", "invalid_source_nct", "invalid_source_digest", "source_reference")
SOURCE_CONTRACT = {
    "marker": {MARKER: {"run": "root-child run name", "nct": "NCT identifier", "digest": "SHA-256"}},
    "slots": ["source_assertions.study", "design_session.session.sources[].study"],
    "meaning": "Exact complete retained NIH study; preservation only, never clinical interpretation.",
    "root": "MCP served root; CLI --source-root explicitly names the equivalent root.",
    "read": "record part source, nct, optional raw-study address; follow ordinary page/text continuation.",
}


def source_marker_code(run: str, nct: str, digest: str) -> str:
    """Validate the three declared identities, without interpreting them (pure).

    post: __return__ in SOURCE_CODES
    post: __return__ != 'source_reference' or bool(run)
    """
    if re.fullmatch(RUN_PATTERN, run) is None:
        return "invalid_source_run"
    if re.fullmatch(NCT_PATTERN, nct) is None:
        return "invalid_source_nct"
    if re.fullmatch(DIGEST_PATTERN, digest) is None:
        return "invalid_source_digest"
    return "source_reference"


def run_folder(root: Path, name: str) -> Path:
    """Serve only a named immediate child, including after resolving filesystem links."""
    if not isinstance(name, str) or re.fullmatch(RUN_PATTERN, name) is None:
        raise ValueError("invalid_source_run")
    folder = root / name
    if folder.resolve().parent != root.resolve():
        raise ValueError("source_run_outside_root")
    return folder


def _read(folder: Path, path: Path) -> object:
    if not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError("source_file_outside_run")
    try:
        return strict_json(path.read_bytes())
    except DuplicateKey as error:
        raise ValueError("source_duplicate_json_key") from error
    except OSError as error:
        raise ValueError("source_file_unreadable:" + path.relative_to(folder).as_posix()) from error
    except ValueError as error:
        raise ValueError("source_json_unreadable:" + path.relative_to(folder).as_posix()) from error


def _identity(record: object, manifest: object, nct: str) -> str:
    """Bind the requested study to both retained documentary identity lists."""
    if not isinstance(record, dict) or record.get("schema_version") != 4:
        raise ValueError("source_record_not_schema4")
    if not isinstance(manifest, dict) or canonical(record.get("manifest")) != canonical(manifest):
        raise ValueError("source_manifest_mismatch")
    studies, digests = record.get("studies"), manifest.get("study_digests")
    if not isinstance(studies, list) or not isinstance(digests, list) or len(studies) != len(digests):
        raise ValueError("source_index_malformed")
    matches = [i for i, study in enumerate(studies) if isinstance(study, dict) and study.get("nct") == nct]
    if len(matches) != 1:
        raise ValueError("source_study_not_unique" if matches else "source_study_not_found")
    index = matches[0]
    digest = studies[index].get("digest")
    if (
        not isinstance(digest, str)
        or re.fullmatch(DIGEST_PATTERN, digest) is None
        or digest != digests[index]
    ):
        raise ValueError("source_record_digest_mismatch")
    return digest


def _batch_paths(folder: Path) -> list[Path]:
    fetches = _read(folder, folder / "fetches.json")
    if not isinstance(fetches, list):
        raise ValueError("source_fetches_malformed")
    paths = []
    for fetch in fetches:
        if not isinstance(fetch, dict):
            raise ValueError("source_fetches_malformed")
        if fetch.get("why") != "studies_batch":
            continue
        name = fetch.get("file")
        if not isinstance(name, str) or not name or Path(name).name != name or name in (".", ".."):
            raise ValueError("source_file_outside_run")
        path = folder / "bodies" / name
        if fetch.get("save_as") != "bodies/" + name:
            raise ValueError("source_fetch_location_mismatch")
        paths.append(path)
    return paths


def load_study(folder: Path, nct: str, digest: str | None = None) -> tuple[dict, dict]:
    """Read unchanged raw NIH data and verify its recorded canonical content identity.

    This is a preservation check, not a replay of the report's derivations or certification
    that the registry is clinically correct. No network request or source mutation occurs.
    """
    if not isinstance(nct, str) or re.fullmatch(NCT_PATTERN, nct) is None:
        raise ValueError("invalid_source_nct")
    recorded = _identity(
        _read(folder, folder / "landscape.json"), _read(folder, folder / "manifest.json"), nct
    )
    if digest is not None and digest != recorded:
        raise ValueError("stale_source_digest")
    matches = []
    for path in _batch_paths(folder):
        page = _read(folder, path)
        if not isinstance(page, dict) or not isinstance(page.get("studies"), list):
            raise ValueError("source_batch_malformed")
        for study in page["studies"]:
            if not isinstance(study, dict):
                raise ValueError("source_batch_malformed")
            protocol = study.get("protocolSection")
            identification = protocol.get("identificationModule") if isinstance(protocol, dict) else None
            if isinstance(identification, dict) and identification.get("nctId") == nct:
                matches.append(study)
    if len(matches) != 1:
        raise ValueError("source_study_not_unique" if matches else "source_raw_study_not_found")
    study = matches[0]
    if study_digest(study) != recorded:
        raise ValueError("source_body_digest_mismatch")
    return study, {"nct": nct, "digest": recorded, "study_ref": f"ctg:{nct}:{recorded}"}


def read_source(folder: Path, arguments: dict) -> tuple[dict, bool]:
    """Page exact raw-study values with the existing lossless record selector."""
    from TrialLedger.evidence_access import RECORD_PAGE_LIMIT, RECORD_WORDS, page_window, pointer_value
    from TrialLedger.record_access import bounded_view

    try:
        nct = arguments.get("nct")
        if not isinstance(nct, str):
            raise ValueError("invalid_source_nct")
        study, snapshot = load_study(folder, nct)
        address = arguments.get("address", "")
        whole = study
        if address != "":
            code, whole = pointer_value(study, address)
            if code != "ok":
                return {"error": code, "why": RECORD_WORDS[code]}, True
        page = None
        if isinstance(whole, (list, dict)):
            if "text_offset" in arguments or "text_limit" in arguments:
                return {"error": "not_text", "why": RECORD_WORDS["not_text"]}, True
            code, page = page_window(
                len(whole), arguments.get("offset", 0), arguments.get("limit", RECORD_PAGE_LIMIT)
            )
            if code != "ok":
                return {"error": code, "why": RECORD_WORDS[code]}, True
        code, value = bounded_view(whole, address, "value", page, {**arguments, "part": "address"})
        if code != "ok":
            return {"error": code, "why": RECORD_WORDS[code]}, True
        return {"part": "source", "snapshot": snapshot, **value}, False
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {
            "error": str(error),
            "why": "Retained source identity could not be established; no value supplied.",
        }, True


def _resolve(study: object, root: Path | None) -> object:
    if not isinstance(study, dict) or MARKER not in study:
        return study
    if set(study) != {MARKER} or not isinstance(study[MARKER], dict):
        raise ValueError("invalid_source_marker")
    reference = study[MARKER]
    if set(reference) != {"run", "nct", "digest"} or not all(isinstance(v, str) for v in reference.values()):
        raise ValueError("invalid_source_marker")
    code = source_marker_code(reference["run"], reference["nct"], reference["digest"])
    if code != "source_reference":
        raise ValueError(code)
    if root is None:
        raise ValueError("source_root_required")
    return load_study(run_folder(root, reference["run"]), reference["nct"], reference["digest"])[0]


def hydrate_request(request: dict, root: Path | None) -> dict:
    """Resolve only typed study slots; literal source contents and other objects stay literal."""
    held = deepcopy(request)
    if not isinstance(held, dict):
        return held
    if held.get("operation") == "source_assertions" and "study" in held:
        held["study"] = _resolve(held["study"], root)
    if held.get("operation") == "design_session" and isinstance(held.get("session"), dict):
        session = held["session"]
        if isinstance(session.get("sources"), list):
            for source in session["sources"]:
                if isinstance(source, dict) and "study" in source:
                    source["study"] = _resolve(source["study"], root)
    return held
