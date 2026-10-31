"""The registry's own description of its records, from the API's /studies/metadata and /studies/enums
(API 2.0.5, fetched 2026-10-31, kept byte for byte in TrialLedger/registry/).

Everything a view names comes from here: each field's title, each module's category (its data element
definitions section, or its metadata title), each enum value's label, and the fields the registry redacts for
withheld studies. Nothing is renamed by TrialLedger.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from importlib import resources
from typing import Any

_WITHHELD_RULE = re.compile(r"(Redacted|\[Redacted\]|\[Missing\]) for Withheld studies")
_SECTIONS = ("protocolSection", "resultsSection", "annotationSection", "documentSection", "derivedSection")


def _bytes(name: str) -> bytes:
    return resources.files("TrialLedger").joinpath("registry", name).read_bytes()


def _load(name: str) -> Any:
    return json.loads(_bytes(name).decode("utf-8"))


def _walk(nodes: list[dict[str, Any]], path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], dict]]:
    for node in nodes:
        here = (*path, node["name"])
        yield here, node
        yield from _walk(node.get("children", []), here)


METADATA: list[dict[str, Any]] = _load("ctg-metadata.json")
# The digests of the two files as shipped; a rule that reads them commits to them in its warrant.
METADATA_DIGEST = hashlib.sha256(_bytes("ctg-metadata.json")).hexdigest()
ENUMS_DIGEST = hashlib.sha256(_bytes("ctg-enums.json")).hexdigest()
ENUMS: list[dict[str, Any]] = _load("ctg-enums.json")
FIELDS: dict[str, dict[str, Any]] = {".".join(path): node for path, node in _walk(METADATA)}


def _label(node: dict[str, Any]) -> str:
    return (node.get("dedLink") or {}).get("label") or node.get("title") or node["name"]


def category(field: str) -> str:
    """The registry's category for a field path: its section and module, in the registry's names.

    For example "Study Protocol › Study Design" or "Study Results › Adverse Event Information"; a top-level
    field (hasResults) is its own category.
    """
    parts = field.split(".")
    if parts[0] in _SECTIONS and len(parts) >= 2:
        section, module = FIELDS.get(parts[0]), FIELDS.get(".".join(parts[:2]))
        if section is not None and module is not None:
            return f"{_label(section)} › {_label(module)}"
    node = FIELDS.get(parts[0])
    return _label(node) if node is not None else parts[0]


def title(field: str) -> str:
    """The registry's title for a field path, or its name where the metadata gives no title."""
    node = FIELDS.get(field)
    if node is None:
        return field.rsplit(".", 1)[-1]
    return node.get("title") or node["name"]


def enum_labels(enum_type: str) -> dict[str, str]:
    """value → the registry's label (legacyValue) for one enum type of /studies/enums."""
    for entry in ENUMS:
        if entry["type"] == enum_type:
            return {item["value"]: item["legacyValue"] for item in entry["values"]}
    raise KeyError(f"{enum_type} is not an enum type of the registry")


def redacted_when_withheld() -> frozenset[str]:
    """Field paths the metadata says are redacted or marked missing for withheld studies."""
    return frozenset(
        field
        for field, node in FIELDS.items()
        if _WITHHELD_RULE.search((node.get("rules") or "") + " " + (node.get("description") or ""))
    )
