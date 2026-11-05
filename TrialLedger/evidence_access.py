"""Shared bounded access to saved clinical evidence, without a server or reasoning dependency.

The CLI and MCP delegate to this one selector. Direct values, source addresses,
missing-value objects and exact text/page continuation preserve the saved record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from TrialLedger.contract import FIELDS, SCHEMA_VERSION
from TrialLedger.record_access import (
    DEFAULT_BYTES,
    MAX_BYTES,
    MIN_BYTES,
    TEXT_LIMIT,
    bounded_view,
    response_bytes,
)

RECORD_PARTS = ("manifest", "studies", "study", "statuses", "fields", "address", "source", "coverage")

RECORD_PAGE_LIMIT = 50

RECORD_WORDS = {
    "not_a_record": "landscape.json in this run folder is not a record of TrialLedger's form; do not answer "
    "from it.",
    "schema_not_4": "landscape.json in this run folder was written under another form of the record (its "
    "schema_version is not 4), which these tools do not read. Call landscape with a new run name and the "
    "same request to gather it again.",
    "nct_needed": "part study needs nct, the study's NCT number (part studies lists them).",
    "no_such_study": "The record holds no study of that NCT number. held lists available IDs when small; "
    "otherwise follow next for the paged study index.",
    "address_needed": "part address needs address, a row's address in the record as the workbook gives it "
    "(a JSON pointer such as /studies/0/adverse_events/events/3).",
    "not_a_pointer": "address must be a JSON pointer starting with '/', each step a key or a list position "
    "written without leading zeros (for example /studies/1/posted_outcomes/0), as the workbook's 'Address in "
    "the record' column gives it.",
    "outside_record": "The record holds nothing at that address (a step names a key it does not have, a list "
    "position past its end, or steps into a single value). Check the address against the workbook's 'Address "
    "in the record' column.",
    "offset_out_of_range": "offset must be 0, or a position before the end of the part (page.total gives "
    "its length).",
    "limit_out_of_range": f"limit must be between 1 and {RECORD_PAGE_LIMIT}.",
    "unknown_part": "part must be one of " + ", ".join(RECORD_PARTS) + ".",
    "max_bytes_out_of_range": f"max_bytes must be an integer from {MIN_BYTES} to {MAX_BYTES}.",
    "text_offset_out_of_range": "text_offset must be 0 or a character position before the end of the text.",
    "text_limit_out_of_range": f"text_limit must be an integer from 1 to {TEXT_LIMIT}.",
    "not_text": "Text offsets apply only to a string. Follow the returned addresses for nested values.",
    "value_too_large": "The address or scalar cannot fit this response budget. Increase max_bytes up to "
    f"{MAX_BYTES}, or use the complete landscape.json in this run folder; no source value was shortened.",
}


def _served(part: str) -> tuple[str, ...]:
    """The names of the contract fields the record tool serves in `part` (contract.FIELDS' consumers)."""
    return tuple(field.name for field in FIELDS if ("mcp", part) in field.consumers)


STUDY_LINE = tuple(name.removeprefix("studies[].") for name in _served("studies"))

MANIFEST_KEYS = tuple(dict.fromkeys(name.split(".")[0] for name in _served("manifest")))

STATUS_KEYS = tuple(dict.fromkeys(name.split(".")[0] for name in _served("statuses")))


def page_window(total: int, offset: int, limit: int) -> tuple[str, dict[str, Any]]:
    """The page of a part `total` entries long that an offset and a limit name (pure — pinned).

    ("ok", page) with page = {offset, limit, returned, total, next_offset}: the entries from offset, at most
    limit of them; next_offset the position the next page starts at, None on the last page.
      offset_out_of_range — offset below 0, or not before the end (0 is always a page, the only one of an
                            empty part);
      limit_out_of_range  — limit below 1 or above RECORD_PAGE_LIMIT.
    The refusals carry an empty page.
    """
    if limit < 1 or limit > RECORD_PAGE_LIMIT:
        return "limit_out_of_range", {}
    if offset < 0 or (offset >= total and offset != 0):
        return "offset_out_of_range", {}
    returned = min(limit, total - offset)
    following = offset + returned
    page = {"offset": offset, "limit": limit, "returned": returned, "total": total}
    return "ok", page | {"next_offset": following if following < total else None}


def pointer_value(document: Any, pointer: Any) -> tuple[str, Any]:
    """The value at a JSON pointer (RFC 6901) in a document (pure — pinned).

    A workbook row's address in the record: "/" then each step, "~1" written for "/" and "~0" for "~" within
    a step. ("ok", the value) when every step is held: a key of an object, or a list position written in
    decimal without leading zeros. Codes:
      not_a_pointer  — not a string starting with "/", or a "~" not followed by 0 or 1;
      outside_record — a step the document does not hold: a key an object lacks, a list position that is
                       not a number or is past the list's end ("-", the position after the end, among them),
                       or any step into a value that is neither an object nor a list.
    """
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return "not_a_pointer", None
    node = document
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            return "not_a_pointer", None
        step = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and step in node:
            node = node[step]
        elif isinstance(node, list) and re.fullmatch(r"0|[1-9][0-9]*", step) and int(step) < len(node):
            node = node[int(step)]
        else:
            return "outside_record", None
    return "ok", node


def study_line(study: dict[str, Any]) -> dict[str, Any]:
    """The contract's source fields for one index line, preserving missing-value objects whole.

    Nested source fields retain their parent object. No derived clinical category is substituted.
    """
    line: dict[str, Any] = {}
    for name in STUDY_LINE:
        top, _, inner = name.partition(".")
        top = top.removesuffix("[]")
        held = study.get(top)
        if inner and isinstance(held, dict) and "status" not in held:
            line.setdefault(top, {})[inner] = held.get(inner)
        else:
            line[top] = held
    return line


def record_view(record: Any, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Read a part of the direct source record, with bounded paging and exact JSON addresses.

    Parts: manifest, statuses, fields, studies, study and address. No clinical inference or
    proposed design findings are part of a layer-one record. A different schema is refused.
    """
    if not isinstance(record, dict) or not isinstance(record.get("studies"), list):
        return "not_a_record", {}
    studies = record["studies"]
    if not all(isinstance(study, dict) for study in studies):
        return "not_a_record", {}
    if record.get("schema_version") != SCHEMA_VERSION:
        return "schema_not_4", {}
    budget = arguments.get("max_bytes", DEFAULT_BYTES)
    if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:
        return "max_bytes_out_of_range", {}
    part = arguments.get("part")
    if part == "study":
        nct = arguments.get("nct")
        if nct is None:
            return "nct_needed", {}
        held = [study.get("nct") for study in studies]
        if nct not in held:
            if response_bytes({"held": held}) > budget:
                return "no_such_study", {"held_count": len(held), "next": {"part": "studies", "offset": 0}}
            return "no_such_study", {"held": held}
    whole: Any
    address = ""
    if part == "manifest":
        whole = {key: record.get(key) for key in MANIFEST_KEYS}
    elif part == "statuses":
        whole = {key: record.get(key) for key in STATUS_KEYS}
    elif part == "study":
        whole = studies[held.index(nct)]
        address = f"/studies/{held.index(nct)}"
    elif part == "studies":
        whole = [study_line(study) for study in studies]
        address = "/studies"
    elif part == "fields":
        whole = record.get("fields")
        address = "/fields"
    elif part == "address":
        if "address" not in arguments:
            return "address_needed", {}
        code, whole = pointer_value(record, arguments["address"])
        if code != "ok":
            return code, {}
        address = arguments["address"]
    else:
        return "unknown_part", {}
    key = "value" if part == "address" else part
    if not isinstance(whole, list | dict):
        return bounded_view(whole, address, key, None, arguments)
    if "text_offset" in arguments or "text_limit" in arguments:
        return "not_text", {}
    code, page = page_window(
        len(whole), arguments.get("offset", 0), arguments.get("limit", RECORD_PAGE_LIMIT)
    )
    if code != "ok":
        return code, {}
    code, view = bounded_view(whole, address, key, page, arguments)
    if (
        part in {"manifest", "statuses"}
        and code == "ok"
        and "navigation" not in view
        and page["next_offset"] is None
        and page["offset"] == 0
    ):
        # Preserve these existing compact reply shapes when the complete part fits.
        view.pop("page", None)
    return code, view


def read_record(folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Read one bounded saved-record reply; the bool is transport error status only.

    Folder authorization belongs to the transport: an explicit CLI folder or MCP's
    existing root/run isolation check. This owner never fetches, repairs or rewrites.
    """
    if "coverage_file" in arguments and arguments.get("part") != "coverage":
        return {
            "error": "coverage_file_requires_coverage_part",
            "why": "coverage_file selects only a coverage document; use part coverage.",
        }, True
    if arguments.get("part") == "coverage":
        from TrialLedger.coverage_access import read_coverage

        return read_coverage(folder, arguments)
    if arguments.get("part") == "source":
        from TrialLedger.retained_sources import read_source

        return read_source(folder, arguments)
    path = folder / "landscape.json"
    if not path.is_file():
        return {
            "error": "no_record",
            "why": "This run has no record yet: call landscape until it reports complete.",
        }, True
    try:
        record = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        record = None
    code, view = record_view(record, arguments)
    if code != "ok":
        return {"error": code, "why": RECORD_WORDS[code], **view}, True
    return {"part": arguments["part"], **view}, False
