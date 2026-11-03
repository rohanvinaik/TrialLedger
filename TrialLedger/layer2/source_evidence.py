"""Locate retained NIH values and substitute explicit source selections without interpreting them.

A content version identifies the complete retained study object, never a clinical protocol edition.
Location proves preservation and quotation only; callers supply every clinical binding separately.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any, cast

from TrialLedger.warrants import study_digest

MAX_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 100_000
MAX_ANCHORS = 256
_NCT = re.compile(r"NCT[0-9]{8}\Z")
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_INDEX = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_BAD_ESCAPE = re.compile(r"~(?![01])")


class BridgeError(ValueError):
    """A named translation refusal, never a clinical refutation."""


def _object(value: object, allowed: set[str], required: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise BridgeError(f"not_an_object:{where}")
    if set(value) - allowed:
        raise BridgeError(f"unknown_field:{where}")
    if required - set(value):
        raise BridgeError(f"missing_field:{where}")
    return cast(dict[str, Any], value)


def _text(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise BridgeError(f"not_text:{where}")
    return value


def _json_copy(
    value: object,
    where: str,
    resolve: Callable[[dict[str, Any]], object] | None = None,
) -> Any:
    """Copy finite strict JSON under independent byte, depth, and node limits.

    Marker substitution, when enabled, is bounded while constructing the output. Source JSON selected by
    a marker remains literal even when it happens to contain a ``$source`` property itself.
    """
    nodes = 0
    size = 0

    def spend(amount: int) -> None:
        nonlocal size
        size += amount
        if size > MAX_BYTES:
            raise BridgeError(f"resource_bound:bytes:{where}")

    def encoded(item: object) -> int:
        if type(item) is str and len(item) > MAX_BYTES:
            raise BridgeError(f"resource_bound:bytes:{where}")
        try:
            return len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (ValueError, UnicodeError, OverflowError) as error:
            raise BridgeError(f"invalid_json:{where}") from error

    def walk(item: object, depth: int, markers: bool) -> Any:
        nonlocal nodes
        if depth > MAX_DEPTH:
            raise BridgeError(f"resource_bound:depth:{where}")
        if type(item) is dict and markers and "$source" in item and resolve is not None:
            return walk(resolve(cast(dict[str, Any], item)), depth, False)
        nodes += 1
        if nodes > MAX_NODES:
            raise BridgeError(f"resource_bound:nodes:{where}")
        if type(item) is dict:
            if len(item) > MAX_NODES:
                raise BridgeError(f"resource_bound:nodes:{where}")
            spend(2 + max(0, len(item) - 1))
            result = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise BridgeError(f"invalid_json_key:{where}")
                spend(encoded(key) + 1)
                result[key] = walk(child, depth + 1, markers)
            return result
        if type(item) is list:
            if len(item) > MAX_NODES:
                raise BridgeError(f"resource_bound:nodes:{where}")
            spend(2 + max(0, len(item) - 1))
            return [walk(child, depth + 1, markers) for child in item]
        if type(item) not in (str, int, float, bool, type(None)):
            raise BridgeError(f"invalid_json:{where}")
        if type(item) is float and not math.isfinite(item):
            raise BridgeError(f"nonfinite_json:{where}")
        spend(encoded(item))
        return item

    return walk(value, 0, resolve is not None)


def integer_state(value: object) -> str:
    """Classify only exact integers and whole signed decimal integer strings (pure).

    post: __return__ in ('integer', 'integer_text', 'invalid_integer')
    post: type(value) is not bool or __return__ == 'invalid_integer'
    post: type(value) is not int or __return__ == 'integer'
    """
    if type(value) is int:
        return "integer"
    if type(value) is str and _INTEGER.fullmatch(value) is not None:
        return "integer_text"
    return "invalid_integer"


def strict_integer(value: object) -> int:
    """Convert a lexical integer only; decimal, comma, whitespace and boolean coercion are refused."""
    state = integer_state(value)
    if state == "integer":
        return cast(int, value)
    if state == "integer_text":
        try:
            return int(cast(str, value))
        except ValueError as error:
            raise BridgeError("resource_bound:integer") from error
    raise BridgeError("invalid_integer:source_marker")


def pointer_state(address: object) -> str:
    """Admit a non-root RFC 6901 string pointer with strict escapes (pure).

    post: __return__ in ('pointer', 'invalid_pointer')
    post: type(address) is str or __return__ == 'invalid_pointer'
    """
    if type(address) is not str or not address.startswith("/") or _BAD_ESCAPE.search(address):
        return "invalid_pointer"
    return "pointer"


def pointer_tokens(address: object) -> tuple[str, ...]:
    """Decode each RFC 6901 token once; URI fragments and permissive escape repair are refused."""
    if pointer_state(address) != "pointer":
        raise BridgeError("invalid_pointer:anchor.address")
    assert isinstance(address, str)
    return tuple(token.replace("~1", "/").replace("~0", "~") for token in address[1:].split("/"))


def exact_json_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's boolean/integer equality coercion (pure).

    post: type(left) is type(right) or not __return__
    """
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            exact_json_equal(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            exact_json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def snapshot(study: object) -> dict[str, Any]:
    """Identify a bounded retained NIH v2 study; its version is content identity only."""
    held = _json_copy(study, "study")
    if type(held) is not dict:
        raise BridgeError("not_an_object:study")
    protocol = held.get("protocolSection")
    if type(protocol) is not dict:
        raise BridgeError("not_an_object:study.protocolSection")
    identity = protocol.get("identificationModule")
    if type(identity) is not dict:
        raise BridgeError("not_an_object:study.identificationModule")
    nct = identity.get("nctId")
    if type(nct) is not str or _NCT.fullmatch(nct) is None:
        raise BridgeError("invalid_nct:study")
    status = protocol.get("statusModule", {})
    if type(status) is not dict:
        raise BridgeError("not_an_object:study.statusModule")
    last_update = status.get("lastUpdatePostDateStruct")
    if last_update is not None and type(last_update) is not dict:
        raise BridgeError("not_an_object:study.last_update")
    digest = study_digest(held)
    return {
        "nct": nct,
        "digest": digest,
        "study_ref": f"ctg:{nct}:{digest}",
        "version": digest,
        "last_update": last_update,
    }


def _selected(study: object, address: object) -> Any:
    node = study
    for token in pointer_tokens(address):
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list):
            if _INDEX.fullmatch(token) is None:
                raise BridgeError("invalid_list_index:anchor.address")
            if len(token) > len(str(len(node))) or int(token) >= len(node):
                raise BridgeError("missing_location:anchor.address")
            node = node[int(token)]
        else:
            raise BridgeError("missing_location:anchor.address")
    return node


def _span(raw: object, value: object) -> dict[str, Any]:
    span = _object(raw, {"start", "end", "text"}, {"start", "end", "text"}, "anchor.span")
    start, end, text = span["start"], span["end"], span["text"]
    if type(value) is not str or type(start) is not int or type(end) is not int or type(text) is not str:
        raise BridgeError("invalid_span:anchor.span")
    if not 0 <= start <= end <= len(value):
        raise BridgeError("invalid_span:anchor.span")
    if value[start:end] != text:
        raise BridgeError("stale_span:anchor.span")
    return {"start": start, "end": end, "text": text}


def anchors(study: object, snapshot_dict: dict[str, Any], raw: list[Any]) -> list[dict[str, Any]]:
    """Verify caller-selected addresses, expected exact values and optional Unicode spans."""
    current = snapshot(study)
    supplied = _json_copy(snapshot_dict, "snapshot")
    if not exact_json_equal(current, supplied):
        raise BridgeError("stale_snapshot:anchors")
    requested = _json_copy(raw, "anchors")
    if type(requested) is not list:
        raise BridgeError("not_a_list:anchors")
    if len(requested) > MAX_ANCHORS:
        raise BridgeError("resource_bound:anchors")
    located = []
    seen = set()
    required = {"id", "address", "digest", "expected"}
    for item in requested:
        anchor = _object(item, required | {"span"}, required, "anchor")
        identity = _text(anchor["id"], "anchor.id")
        if identity in seen:
            raise BridgeError("duplicate_id:anchor")
        seen.add(identity)
        if anchor["digest"] != current["digest"] or type(anchor["digest"]) is not str:
            raise BridgeError("stale_digest:anchor")
        address = anchor["address"]
        value = _selected(study, address)
        if not exact_json_equal(value, anchor["expected"]):
            raise BridgeError("stale_value:anchor.expected")
        result = {
            "id": identity,
            "address": address,
            "digest": current["digest"],
            "value": value,
            "ref": f"{current['study_ref']}#{address}",
            "source": {
                "ref": current["study_ref"],
                "version": current["version"],
                "address": address,
                "digest": current["digest"],
            },
            "code": "located",
        }
        if "span" in anchor:
            span = _span(anchor["span"], value)
            result["span"] = span
            result["ref"] += f":chars:{span['start']}:{span['end']}"
        located.append(result)
    return _json_copy(located, "located")


def hydrate(node: object, located: list[dict[str, Any]]) -> object:
    """Copy a JSON template, resolving only exact explicit source markers under output budgets."""
    _json_copy(node, "template")
    selections = _json_copy(located, "located")
    if type(selections) is not list:
        raise BridgeError("not_a_list:located")
    if len(selections) > MAX_ANCHORS:
        raise BridgeError("resource_bound:anchors")
    values = {}
    required = {"id", "address", "digest", "value", "ref", "source", "code"}
    for item in selections:
        selection = _object(item, required | {"span"}, required, "located")
        identity = _text(selection["id"], "located.id")
        if identity in values:
            raise BridgeError("duplicate_id:located")
        if selection["code"] != "located":
            raise BridgeError("not_located:source_marker")
        values[identity] = (
            _span(selection["span"], selection["value"])["text"]
            if "span" in selection
            else selection["value"]
        )

    def resolve(marker: dict[str, Any]) -> object:
        _object(marker, {"$source", "as"}, {"$source", "as"}, "source_marker")
        identity = _text(marker["$source"], "source_marker.$source")
        mode = marker["as"]
        if type(mode) is not str or mode not in ("integer", "text", "json"):
            raise BridgeError("unknown_mode:source_marker")
        if identity not in values:
            raise BridgeError("unknown_ref:source_marker")
        value = values[identity]
        if mode == "integer":
            return strict_integer(value)
        if mode == "text" and type(value) is not str:
            raise BridgeError("not_text:source_marker")
        return value

    return _json_copy(node, "hydrated", resolve)
