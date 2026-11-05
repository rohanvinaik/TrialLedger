"""Read exact search-coverage sidecars through the existing bounded record interface.

The fixed document selector is not a filesystem path. A digest establishes which retained bytes were
read; neither it nor a retrieval route establishes disease membership or comparator suitability.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

from TrialLedger.landscape_verify import strict_json
from TrialLedger.record import DuplicateKey
from TrialLedger.record_access import DEFAULT_BYTES, MAX_BYTES, MIN_BYTES, bounded_view, response_bytes

COVERAGE_FILES = {"comparison": "coverage.json", "union_request": "coverage_union_request.json"}
STATES = {
    "complete",
    "failed",
    "incomplete",
    "not_run",
    "not_applicable",
    "snapshot_differs",
    "awaiting_fetch",
}
CODES = {"ok", "coverage_document_invalid", "coverage_schema_unsupported", "coverage_state_unsupported"}
WORDS = {
    "invalid_coverage_file": "coverage_file must be comparison or union_request; it is never a file path.",
    "coverage_not_available": "This run has no saved coverage document of that kind; "
    "no comparison is implied.",
    "coverage_file_outside_run": "The selected coverage file resolves outside this authorized run.",
    "coverage_file_unreadable": "The selected coverage file could not be read; no values are supplied.",
    "coverage_duplicate_json_key": "The coverage document repeats a JSON key; no reading is selected.",
    "coverage_json_invalid": "The coverage document is not finite, unambiguous JSON.",
    "coverage_document_invalid": "The saved document does not have the declared coverage structure.",
    "coverage_schema_unsupported": "This reader supports coverage-1; the saved schema is not supported.",
    "coverage_state_unsupported": "The saved comparison state is not supported; it is not read as complete.",
    "coverage_union_not_offered": "The current comparison does not offer a union request; "
    "an older file is not an offer.",
    "coverage_union_mismatch": "The union request does not name exactly the current "
    "comparison's identifiers.",
    "outside_record": "The selected coverage document holds nothing at that address.",
}


def coverage_selector_code(selector: object) -> str:
    """A fixed selector or a named refusal; a path never becomes a selector (pure).

    post: __return__ in ('comparison', 'union_request', 'invalid_coverage_file')
    """
    return selector if isinstance(selector, str) and selector in COVERAGE_FILES else "invalid_coverage_file"


def _id_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(identity, str) and re.fullmatch(r"NCT[0-9]{8}", identity) is not None for identity in value
    )


def coverage_document_code(document: object) -> str:
    """Validate the saved comparison envelope; incomplete evidence never defaults to complete (pure).

    post: __return__ in CODES
    """
    if not isinstance(document, dict):
        return "coverage_document_invalid"
    if document.get("schema") != "coverage-1":
        return "coverage_schema_unsupported"
    state = document.get("state")
    if not isinstance(state, str) or state not in STATES:
        return "coverage_state_unsupported"
    if state == "complete":
        comparison, union = document.get("comparison"), document.get("union")
        if not isinstance(comparison, dict) or not isinstance(union, dict):
            return "coverage_document_invalid"
        if type(union.get("offered")) is not bool or not all(
            _id_list(comparison.get(key)) for key in ("intersection", "class_only", "text_only")
        ):
            return "coverage_document_invalid"
    return "ok"


def _read(folder: Path, filename: str) -> tuple[object, str]:
    path = folder / filename
    if not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError("coverage_file_outside_run")
    if not path.is_file():
        raise ValueError("coverage_not_available")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError("coverage_file_unreadable") from error
    try:
        document = strict_json(raw)
        # JSON's exponent syntax can parse to infinity without going through parse_constant.
        json.dumps(document, allow_nan=False)
    except DuplicateKey as error:
        raise ValueError("coverage_duplicate_json_key") from error
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError("coverage_json_invalid") from error
    return document, hashlib.sha256(raw).hexdigest()


def _union_matches(document: object, comparison: dict) -> bool:
    if not isinstance(document, dict) or set(document) != {"params"}:
        return False
    params = document["params"]
    if not isinstance(params, dict) or set(params) != {"filter.ids"}:
        return False
    identities = sorted(
        {identity for ids in comparison.values() if isinstance(ids, list) for identity in ids}
    )
    return bool(identities) and params["filter.ids"] == ",".join(identities)


def _selected(folder: Path, selector: str) -> tuple[object, dict]:
    comparison, comparison_digest = _read(folder, COVERAGE_FILES["comparison"])
    code = coverage_document_code(comparison)
    if code != "ok":
        raise ValueError(code)
    # The named validator above established this runtime shape.
    comparison = cast(dict, comparison)
    snapshot = {
        "file": COVERAGE_FILES[selector],
        "digest": comparison_digest,
        "digest_scope": "exact_stored_bytes",
        "state": comparison["state"],
    }
    if selector == "comparison":
        return comparison, snapshot
    if comparison["state"] != "complete" or comparison["union"]["offered"] is not True:
        raise ValueError("coverage_union_not_offered")
    document, digest = _read(folder, COVERAGE_FILES[selector])
    if not _union_matches(document, comparison["comparison"]):
        raise ValueError("coverage_union_mismatch")
    return document, snapshot | {"digest": digest, "comparison_digest": comparison_digest}


def _selection(document: object, arguments: dict) -> tuple[str, object, dict | None]:
    from TrialLedger.evidence_access import RECORD_PAGE_LIMIT, page_window, pointer_value

    address = arguments.get("address", "")
    whole = document
    if address != "":
        code, whole = pointer_value(document, address)
        if code != "ok":
            raise ValueError(code)
    if not isinstance(whole, (dict, list)):
        return address, whole, None
    if "text_offset" in arguments or "text_limit" in arguments:
        raise ValueError("not_text")
    offset, limit = arguments.get("offset", 0), arguments.get("limit", RECORD_PAGE_LIMIT)
    if type(offset) is not int:
        raise ValueError("offset_out_of_range")
    if type(limit) is not int:
        raise ValueError("limit_out_of_range")
    code, page = page_window(len(whole), offset, limit)
    if code != "ok":
        raise ValueError(code)
    return address, whole, page


def _bounded(document: object, snapshot: dict, selector: str, arguments: dict) -> dict:
    from TrialLedger.evidence_access import page_window

    budget = arguments.get("max_bytes", DEFAULT_BYTES)
    if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:
        raise ValueError("max_bytes_out_of_range")
    address, whole, page = _selection(document, arguments)
    envelope = {"part": "coverage", "coverage_file": selector, "snapshot": snapshot}
    controls = {**arguments, "part": "address"}
    while True:
        code, value = bounded_view(whole, address, "value", page, controls)
        if code != "ok":
            raise ValueError(code)
        reply = envelope | value
        if response_bytes(reply) <= budget:
            return reply
        if page is not None and page["returned"] > 1:
            # Only a selected list or object has a page (_selection).
            _, page = page_window(
                len(cast(dict | list, whole)), page["offset"], max(1, page["returned"] // 2)
            )
        elif isinstance(whole, str) and "text_offset" not in controls:
            controls["text_offset"] = 0
        else:
            raise ValueError("value_too_large")


def read_coverage(folder: Path, arguments: dict) -> tuple[dict, bool]:
    """Read a coverage document without fetching, rewriting or inferring clinical membership."""
    from TrialLedger.evidence_access import RECORD_WORDS

    selector = coverage_selector_code(arguments.get("coverage_file", "comparison"))
    try:
        if selector == "invalid_coverage_file":
            raise ValueError(selector)
        document, snapshot = _selected(folder, selector)
        return _bounded(document, snapshot, selector, arguments), False
    except ValueError as error:
        code = str(error)
        return {
            "error": code,
            "why": WORDS.get(code, RECORD_WORDS.get(code, "No coverage value supplied.")),
        }, True
