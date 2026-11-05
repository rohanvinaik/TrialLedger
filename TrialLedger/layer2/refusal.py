"""Structured, bounded refusal diagnostics (never an interpretation, never a guessed location).

A refusal keeps its exact code in `problems`. Where the failing input is known, an exception also carries
one diagnostic beside it: the RFC 6901 pointer into the request as submitted, the rejected value (bounded),
the permitted vocabulary or structural requirement, and the discovery view that documents it. Where the
location is not tracked the diagnostic says so with `pointer: null`; a location is never guessed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

MAX_REJECTED = 80
MAX_VOCABULARY = 40
MAX_CANDIDATES = 8
MAX_WALK = 200_000
MISSING = object()
UNKNOWN_NOTE = "location not tracked for this refusal"


def escape(token: object) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def join(base: str | None, tokens: tuple) -> str | None:
    if base is None:
        return None
    return base + "".join("/" + escape(token) for token in tokens)


def bounded(value: object) -> dict:
    """The rejected value, truncated; its type always, so a short text and a long one stay distinguishable."""
    kind = type(value).__name__
    try:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=repr)
    except (TypeError, ValueError):
        text = repr(value)
    held = {"type": kind, "value": text[:MAX_REJECTED]}
    if len(text) > MAX_REJECTED:
        held["truncated"] = True
    return held


def vocabulary(words: Iterable[object]) -> dict:
    ordered = sorted(str(word) for word in words)
    held: dict[str, Any] = {"vocabulary": ordered[:MAX_VOCABULARY]}
    if len(ordered) > MAX_VOCABULARY:
        held["vocabulary_truncated"] = len(ordered)
    return held


def annotate[E: BaseException](
    error: E,
    *,
    code: str | None = None,
    tokens: tuple = (),
    node: object = MISSING,
    container: object = MISSING,
    rejected: object = MISSING,
    expected: dict | None = None,
    pointer: object = MISSING,
    path: tuple = (),
    reference_view: str | None = None,
) -> E:
    """Attach one location record to an exception unless it already has one (the innermost wins)."""
    if getattr(error, "refusal", None) is not None:
        return error
    error.__dict__["refusal"] = {
        "code": code if code is not None else str(error),
        "tokens": tuple(tokens),
        "node": node,
        "container": container,
        "rejected": rejected,
        "expected": expected or {},
        "pointer": pointer,
        "path": tuple(path),
        "reference_view": reference_view,
    }
    return error


def find_record(error: BaseException | None) -> dict | None:
    seen: set[int] = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        record = getattr(error, "refusal", None)
        if record is not None:
            return record
        error = error.__cause__ or error.__context__
    return None


def _walk(root: object, test) -> list[str]:
    """Pointers of every container in `root` satisfying `test`, in document order, bounded."""
    found: list[str] = []
    stack: list[tuple[object, str]] = [(root, "")]
    visited = 0
    while stack:
        item, where = stack.pop()
        visited += 1
        if visited > MAX_WALK:
            return ["<unbounded>"]
        if test(item):
            found.append(where)
            if len(found) > MAX_CANDIDATES:
                break
        if isinstance(item, dict):
            stack.extend((value, where + "/" + escape(key)) for key, value in reversed(list(item.items())))
        elif isinstance(item, list):
            stack.extend((value, f"{where}/{index}") for index, value in reversed(list(enumerate(item))))
    return found


def locate(root: object, record: dict) -> tuple[str | None, list[str]]:
    """(pointer, candidates): one exact pointer, or null with every equal candidate when ambiguous."""
    if record["pointer"] is not MISSING:
        return record["pointer"], []
    if record["container"] is not MISSING:
        found = _walk(root, lambda item: item is record["container"])
    elif record["node"] is not MISSING:
        node = record["node"]
        found = _walk(root, lambda item: type(item) is type(node) and item == node)
    else:
        return None, []
    if len(found) == 1 and found[0] != "<unbounded>":
        return join(found[0], record["tokens"]), []
    return None, [join(f, record["tokens"]) or "" for f in found if f != "<unbounded>"][:MAX_CANDIDATES]


def render(
    error: BaseException, request: object, views: object, *, base: str = "request"
) -> list[dict] | None:
    """The diagnostics list for a refusal, or None when the failure carries no record."""
    record = find_record(error)
    if record is None:
        return None
    pointer, candidates = locate(request, record)
    operation = request.get("operation") if isinstance(request, dict) else None
    view = record["reference_view"] or (
        operation if isinstance(operation, str) and operation in views else "overview"
    )
    diagnostic: dict[str, Any] = {
        "code": record["code"],
        "pointer": pointer,
        "input": record.get("base", base),
    }
    if pointer is None:
        diagnostic["note"] = UNKNOWN_NOTE if not candidates else "several identical inputs match"
        if candidates:
            diagnostic["candidates"] = candidates
    if record["rejected"] is not MISSING:
        diagnostic["rejected"] = bounded(record["rejected"])
    if record["expected"]:
        diagnostic["expected"] = record["expected"]
    if record.get("expanded_pointer"):
        diagnostic["expanded_pointer"] = record["expanded_pointer"]
    diagnostic["reference"] = {"operation": "describe", "view": view, "detail": "schema"}
    return [diagnostic]


def rebase(error: BaseException, source: object, expanded_base: str | None = None) -> None:
    """Re-point a node-relative record at the submitted `source` it was expanded from (when keys agree).

    The record's tokens are relative to the failing node; `path` is that node's place inside the object that
    was read. The expanded pointer (`expanded_base` + those tokens) is kept beside the submitted one."""
    record = getattr(error, "refusal", None)
    if record is None or record["node"] is MISSING:
        return
    tokens = (*record["path"], *record["tokens"])
    if expanded_base is not None:
        record["expanded_pointer"] = join(expanded_base, tokens)
    record.update(container=source, node=MISSING, tokens=tokens, path=())


def settle(error: BaseException, submitted: object, base: str) -> None:
    """Resolve a record against the submitted input now, so later copies cannot change the answer."""
    record = getattr(error, "refusal", None)
    if record is None:
        return
    if record["node"] is not MISSING:
        # Located only in an expansion of the input: its place in the submitted input is not tracked.
        record.update(pointer=None, node=MISSING, container=MISSING)
    else:
        record["pointer"] = locate(submitted, record)[0]
        record["container"] = MISSING
    record["base"] = base
