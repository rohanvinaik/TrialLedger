"""Bound conversational record access without changing saved evidence or shortening source values."""

from __future__ import annotations

import json
from itertools import islice
from typing import Any

DEFAULT_BYTES = 24_576
MIN_BYTES = 2_048
MAX_BYTES = 65_536
TEXT_LIMIT = 8_192


def response_bytes(value: Any) -> int:
    """Conservative size of the JSON text reply, including indentation and escaped Unicode."""
    return len(json.dumps(value, ensure_ascii=True, indent=1).encode("ascii"))


def text_window(text: str, offset: int, limit: int, budget: int) -> tuple[str, dict[str, Any]]:
    """Lossless character paging that also fits a serialized byte budget.

    Offsets count Python/JSON Unicode characters, not UTF-8 bytes. No normalization is applied.
    A chunk is explicitly text, never a replacement for the complete source value.
    """
    if type(offset) is not int or offset < 0 or (offset >= len(text) and offset != 0):
        return "text_offset_out_of_range", {}
    if type(limit) is not int or not 1 <= limit <= TEXT_LIMIT:
        return "text_limit_out_of_range", {}
    if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:
        return "max_bytes_out_of_range", {}
    low, high = 0, min(limit, len(text) - offset)
    while low < high:
        middle = (low + high + 1) // 2
        # Leave room for address and page metadata, which the caller checks independently.
        if response_bytes(text[offset : offset + middle]) <= budget - 1_024:
            low = middle
        else:
            high = middle - 1
    following = offset + low
    return "ok", {
        "text": text[offset:following],
        "text_page": {
            "offset": offset,
            "returned": low,
            "total": len(text),
            "next_offset": following if following < len(text) else None,
        },
    }


def bounded_view(
    whole: Any,
    address: str,
    key: str,
    page: dict[str, Any] | None,
    arguments: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Return exact values, a smaller page, an address directory, or explicit text continuation.

    Directories are navigation metadata outside source values. Their addresses always name the
    unchanged record. `page` has already been validated by the record entry point.
    """
    budget = arguments.get("max_bytes", DEFAULT_BYTES)
    if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:
        return "max_bytes_out_of_range", {}
    explicit_text = "text_offset" in arguments or "text_limit" in arguments
    prefix = {"address": address} if arguments["part"] == "address" else {}
    if explicit_text and not isinstance(whole, str):
        return "not_text", {}
    if page is None:
        reply = prefix | {key: whole}
        if not explicit_text and response_bytes(reply) <= budget:
            return "ok", reply
        if not isinstance(whole, str):
            return "value_too_large", {}
        code, chunk = text_window(
            whole, arguments.get("text_offset", 0), arguments.get("text_limit", TEXT_LIMIT), budget
        )
        reply = {"address": address, **chunk}
        if code == "ok" and response_bytes(reply) > budget:
            return "value_too_large", {}
        return code, reply if code == "ok" else {}
    offset, count = page["offset"], page["returned"]
    window = list(islice(whole, offset, offset + count))
    shown = {item: whole[item] for item in window} if isinstance(whole, dict) else window
    reply = prefix | {key: shown, "page": page}
    if response_bytes(reply) <= budget:
        return "ok", reply
    # A directory avoids repeatedly returning nested values that are irrelevant to this question.
    entries = []
    for index, item in enumerate(window, offset):
        name = str(item) if isinstance(whole, dict) else str(index)
        escaped = name.replace("~", "~0").replace("/", "~1")
        child = whole[item] if isinstance(whole, dict) else item
        entry = {"address": address + "/" + escaped}
        if isinstance(whole, dict):
            entry["key"] = name
        else:
            entry["index"] = index
        entry["kind"] = (
            "object"
            if isinstance(child, dict)
            else "array"
            if isinstance(child, list)
            else "text"
            if isinstance(child, str)
            else "scalar"
        )
        candidate = {"entries": [*entries, entry], "page": page, "navigation": "addresses"}
        if response_bytes(prefix | candidate) > budget:
            break
        entries.append(entry)
    if not entries:
        return "value_too_large", {}
    following = offset + len(entries)
    return "ok", prefix | {
        "navigation": "addresses",
        "entries": entries,
        "page": page
        | {
            "returned": len(entries),
            "next_offset": following if following < page["total"] else None,
        },
    }
