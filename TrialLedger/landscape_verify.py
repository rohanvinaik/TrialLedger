"""Reproduce the clinical record and workbook from retained registry data and lookup answers.

Verification checks saved input digests, direct transformations and workbook bytes offline.
It does not establish the truth of a registry assertion or authorize clinical inference.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, NoReturn


def _reject(code: str, detail: str) -> NoReturn:
    raise ValueError(f"{code}: {detail}")


def _constant(value: str) -> Any:
    _reject("unreadable", f"non-finite JSON number {value}")


def strict_json(raw: bytes | str) -> Any:
    """The existing duplicate-key refusal applies to every retained JSON input, including source bodies."""
    from TrialLedger.record import _unique

    return json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)


def _same(left: Any, right: Any) -> bool:
    # JSON equality alone conflates True/1 and 7/7.0.
    return json.dumps(left, sort_keys=True, ensure_ascii=True) == json.dumps(
        right, sort_keys=True, ensure_ascii=True
    )


def _read(path: Path) -> Any:
    return strict_json(path.read_bytes())


def _class_answers(cache: Any) -> dict[str, Any]:
    """Validate the persisted cache's common schema; historical optional warrants remain optional.

    Class rows are (classId, className, relation, source). Empty classes are a recorded answer only when
    per-query codes are retained. This reads a frozen input and never asks RxNav or invents an absence.
    """
    if not isinstance(cache, dict) or not isinstance(cache.get("answers"), dict):
        _reject("invalid_source", "classes cache requires an answers object")
    for name, answer in cache["answers"].items():
        if not isinstance(name, str) or not isinstance(answer, dict):
            _reject("invalid_source", "classes cache answer has no name or is not an object")
        codes, classes = answer.get("codes"), answer.get("classes")
        if (
            not isinstance(codes, dict)
            or not codes
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in codes.items())
        ):
            _reject("invalid_source", "classes cache per-query codes are absent or malformed")
        if not isinstance(classes, list) or any(
            not isinstance(row, list) or len(row) != 4 or not all(isinstance(item, str) for item in row)
            for row in classes
        ):
            _reject("invalid_source", "classes cache class rows are malformed")
        if "axes" in answer and not isinstance(answer["axes"], dict):
            _reject("invalid_source", "classes cache axes are malformed")
    return cache["answers"]


def verify_landscape(folder: Path, *, limit: int = 20) -> tuple[str, list[str]]:
    """Replay saved sources and compare the whole derived record and deterministic workbook bytes.

    verified, changed, wrong_code, missing_source, unreadable, invalid_source are distinct remedies.
    No source is fetched or repaired. The source index and input metadata are not derived from output facts.
    """
    from TrialLedger import classes, landscape, operate, readout, steps, warrants
    from TrialLedger.landscape_warrants import derivation_root, retained_format
    from TrialLedger.record import DuplicateKey

    try:
        record = _read(folder / "landscape.json")
        manifest = _read(folder / "manifest.json")
        if not isinstance(record, dict) or not isinstance(manifest, dict):
            return "unreadable", ["record_shape: record and manifest must be JSON objects"]
        if not _same(record.get("manifest"), manifest):
            return "changed", ["manifest_mismatch: standalone manifest differs from the record"]
        versions = manifest.get("rule_versions")
        current_root = derivation_root(Path(landscape.__file__).parent)
        writing_format = retained_format(versions)
        legacy = writing_format in ("legacy_source_passages_v1", "legacy_source_context_v2")
        if not legacy and (
            not isinstance(versions, dict) or versions.get("derivation_code_root") != current_root
        ):
            return "wrong_code", [
                "code_root: current derivation source differs; verify using the recorded code"
            ]
        if not legacy and not _same(versions, landscape.RULE_VERSIONS):
            return "wrong_code", ["rule_versions: use the derivation code/version that wrote this run"]
        request = _read(folder / "request.json")
        resolution = _read(folder / "resolution.json")
        scope = _read(folder / "scope.json")
        if not _same(scope.get("query"), resolution.get("query")):
            return "changed", ["scope_mismatch: persisted query and resolution differ"]
        # Refuse ambiguous JSON in every saved body before the step protocol reads it permissively.
        for path in sorted((folder / steps.BODIES).iterdir()):
            if path.is_file() and not path.name.startswith("."):
                try:
                    _read(path)
                except DuplicateKey:
                    raise
                except (ValueError, UnicodeDecodeError):
                    # RxNav failure notes are not JSON; steps.records refuses invalid registry bodies.
                    pass
        _read(folder / "fetches.json")
        studies, api_version, timestamp = steps.records(folder)
        checkpoint, named, bodies, unreadable = steps._state(folder)
        checkpoint_code, plan, _awaited, detail = steps.next_step(
            checkpoint["query"],
            checkpoint["rxnav"],
            named,
            bodies,
            unreadable,
            acquisition=scope.get("acquisition"),
        )
        if checkpoint_code != "complete":
            return "missing_source", [f"registry_checkpoint: {checkpoint_code}: {detail}"]
        expected_fetches = [
            {
                "file": fetch["file"],
                "url": steps.request_url(fetch["url"], fetch["params"]),
                "save_as": f"{steps.BODIES}/{fetch['file']}",
                "why": fetch["why"],
                "params": fetch["params"],
            }
            for fetch in plan
        ]
        if not _same(_read(folder / "fetches.json"), expected_fetches):
            return "invalid_source", ["fetch_history: saved requests differ from the verified retrieval plan"]
        expected_digests = [warrants.study_digest(study) for study in studies]
        if not _same(manifest.get("study_digests"), expected_digests) or manifest.get(
            "merkle_root"
        ) != warrants.merkle_root(expected_digests):
            return "invalid_source", [
                "registry_digest: saved registry bodies differ from the committed source digests"
            ]
        if manifest.get("api_version") != api_version or manifest.get("data_timestamp") != timestamp:
            return "invalid_source", ["registry_snapshot: saved source version differs from the manifest"]
        mode = (manifest.get("retrieval") or {}).get("mode")
        if mode not in {"direct", "relay"}:
            return "missing_source", ["retrieval_mode: no documented reading mode"]
        input_digests = manifest.get("input_digests")
        input_names = {"request.json", "resolution.json", "scope.json", "classes.json"}
        expected_inputs = {name for name in input_names if (folder / name).is_file()}
        if not isinstance(input_digests, dict) or not expected_inputs <= set(input_digests):
            return "missing_source", ["input_digests: a persisted source input has no commitment"]
        for name, digest in input_digests.items():
            if name not in {"request.json", "resolution.json", "classes.json", "scope.json"}:
                return "invalid_source", [f"input_digest: unsupported input path {name!r}"]
            if not (folder / name).is_file():
                return "missing_source", [f"input_digest: missing {name}"]
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                return "invalid_source", [f"input_digest: changed {name}"]
            _read(folder / name)
        answers = {}
        if mode == "direct":
            names = operate.drug_aliases(studies)
            if (folder / classes.CACHE_NAME).is_file():
                answers = _class_answers(_read(folder / classes.CACHE_NAME))
            elif names:
                return "missing_source", ["classes_cache: direct-mode drug answers missing"]
            if any(name not in answers for name in names):
                return "missing_source", ["classes_cache: a requested drug answer is missing"]
        matched = _read(folder / steps.BODIES / "ids-001.json")["totalCount"]
        retrieval = operate.retrieval_coverage(mode, matched, resolution["query"], studies)
        rebuilt_manifest = landscape.landscape_manifest(
            studies,
            api_version,
            timestamp,
            manifest.get("code_commit", ""),
            retrieval,
            versions if legacy else landscape.RULE_VERSIONS,
        )
        for key in ("input_digests",):
            if key in manifest:
                rebuilt_manifest[key] = manifest[key]
        rebuilt = landscape.landscape_record(
            studies,
            request,
            resolution,
            rebuilt_manifest,
            answers if mode == "direct" else None,
        )
        if legacy:
            rebuilt = landscape.legacy_record_projection(rebuilt, writing_format)
        # Production writes the JSON-decoded record, including tuple-to-list normalization.
        rebuilt = strict_json(json.dumps(rebuilt, ensure_ascii=False))
        if not _same(rebuilt, record):
            return "changed", ["record_derivation: landscape.json differs from replay of retained sources"]
        book = folder / "landscape.xlsx"
        if not book.is_file():
            return "missing_source", ["workbook_missing: landscape.xlsx is absent"]
        with tempfile.TemporaryDirectory(prefix="trialledger-verify-") as temporary:
            expected_book = Path(temporary) / "landscape.xlsx"
            readout.write_book(rebuilt, expected_book)
            if book.read_bytes() != expected_book.read_bytes():
                details = readout.book_problems(rebuilt, book, limit=limit)
                return "changed", details or [
                    "workbook_bytes: workbook formatting, links or file parts differ"
                ]
        if writing_format == "legacy_source_passages_v1":
            return "verified", [
                "legacy_format: source-passages-v1 replay; "
                "local source context was not part of this retained format"
            ]
        if writing_format == "legacy_source_context_v2":
            return "verified", [
                "legacy_format: source-context-v2 replay; "
                "case-sensitive headings and optional-note display retain their writing contract"
            ]
        return "verified", []
    except DuplicateKey as error:
        return "unreadable", [f"duplicate_key: {error}"]
    except FileNotFoundError as error:
        return "missing_source", [f"missing_file: {error.filename}"]
    except steps.StepError as error:
        return "missing_source", [f"registry_checkpoint: {error.code}: {error.detail}"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError) as error:
        message = str(error)
        code = message.partition(":")[0]
        return (code if code in {"invalid_source", "missing_source", "wrong_code"} else "unreadable"), [
            message
        ]
