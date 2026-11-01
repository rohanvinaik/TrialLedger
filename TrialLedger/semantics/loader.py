"""One registry compiled from per-package fragments (add-bank-coverage Decision 2).

The registry holds predicate signatures, not patient facts. Each concept belongs to one predicate family
(FAMILIES), has one owner (the fragment that defines it), declares its arguments by name and type, and cites
the authority its identity comes from (`provenance.CONCEPT_AUTHORITIES`). A fragment is one package's plain
data (a Python module with a `FRAGMENT` dict, or a JSON file of the same shape) with its name, version, rule
exposure (`provenance.RULE_EXPOSURE`), the fragments it requires, the concepts it owns, and the shared
concepts it references with the signature it expects of them. The build refuses, naming each problem: a
duplicate or incompatible concept (naming both owners), an unknown family or argument, an invalid argument
type, missing provenance, an unversioned scale, an unresolved dependency or requirement, a code from an
authority whose edition is unpinned or whose licence is not held or allows words only, a local concept
without its own definition and definition date. No version is invented: a scale whose source edition is not
pinned is refused, unless it is marked UNVERSIONED in a legacy fragment (LEGACY_FRAGMENTS), where it is
accepted and flagged on the registry (`Registry.flags`); a new package's unversioned scale is refused.
Clinical entailments are not here: they are separately registered, versioned rules, never consequences of
recognizing a word.
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import re
from dataclasses import asdict, dataclass
from operator import attrgetter
from pathlib import Path
from typing import Any

from TrialLedger import provenance
from TrialLedger.semantics.contracts import ANNOTATIONS, Atom

FRAGMENTS_DIR = Path(__file__).resolve().parent / "fragments"

# family → the argument names a concept of that family may declare
FAMILIES: dict[str, tuple[str, ...]] = {
    "Attribute": ("value", "unit", "comparator", "minimum", "maximum", "expression"),
    "Measurement": (
        "value",
        "unit",
        "comparator",
        "qualifier",
        "reference",
        "scale_score",
        "window",
        "method",
        "expression",
    ),
    "State": ("value", "expression", "qualifier", "window", "grade"),
    "Event": ("window", "grade", "count", "qualifier"),
    "Exposure": ("agent", "dose", "route", "window", "count", "scope", "grade"),
    "Count": ("count", "scope", "window"),
    "Relation": ("object", "relation", "window"),
    "Capability": ("value", "qualifier", "window"),
    "Commitment": ("action", "method", "duration", "actor", "window"),
}
ARGUMENT_TYPES = (
    "number",
    "comparator",
    "ucum_unit",
    "unit_as_written",
    "duration_as_written",
    "grade_as_written",
    "reference_expression",
    "scale_score",
    "code",
    "text_as_written",
)
PROBLEM_CODES = (
    "malformed_fragment",
    "duplicate_fragment",
    "unversioned_fragment",
    "missing_provenance",
    "unknown_exposure",
    "unresolved_requirement",
    "invalid_concept_id",
    "unknown_family",
    "unknown_argument",
    "invalid_argument_type",
    "unknown_authority",
    "licence_not_held",
    "proprietary_code",
    "unpinned_edition",
    "missing_definition",
    "missing_definition_date",
    "unversioned_scale",
    "duplicate_concept",
    "incompatible_definition",
    "unresolved_dependency",
)
_CONCEPT_ID = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# The explicit mark of a scale whose source edition is not pinned: never a version, never borrowed from a
# fragment's own version. Accepted, and flagged, only in a legacy fragment.
UNVERSIONED = "unversioned"
# Fragments that predate the contract, whose entries may carry UNVERSIONED scales until they are audited
# (add-bank-coverage 2.1). Declared here, never by a fragment of itself.
LEGACY_FRAGMENTS = ("nsclc_legacy",)

Problem = tuple[str, str, str]  # (code, subject, detail)


@dataclass(frozen=True)
class ConceptEntry:
    concept_id: str
    family: str
    arguments: tuple[tuple[str, str], ...]  # (name, type)
    authority: str
    code: str | None
    definition: str
    scale: tuple[str, str] | None  # (instrument, pinned source edition, or UNVERSIONED in a legacy fragment)
    depends_on: tuple[str, ...]
    defined_on: str | None = None  # YYYY-MM-DD, the date its written definition was written; local: required


@dataclass(frozen=True)
class Reference:
    """A shared concept another package owns, with the signature this fragment expects of it."""

    concept_id: str
    family: str
    arguments: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Fragment:
    name: str
    version: str
    exposure: str
    requires: tuple[str, ...]
    concepts: tuple[ConceptEntry, ...]
    references: tuple[Reference, ...]


@dataclass(frozen=True)
class Registry:
    version: str  # SHA-256 of the fragments' canonical JSON: the frozen version banks are read under
    concepts: dict[str, ConceptEntry]
    owners: dict[str, str]  # concept id → owning fragment
    fragments: tuple[tuple[str, str], ...]  # (name, version)
    flags: tuple[tuple[str, str, str], ...] = ()  # registry_flags: accepted, but not vouched for


class RegistryError(ValueError):
    def __init__(self, problems: tuple[Problem, ...]) -> None:
        super().__init__("; ".join(f"{code} {subject}: {detail}" for code, subject, detail in problems))
        self.problems = problems


def _pairs(items: Any) -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(kind)) for name, kind in items)


def fragment_from_data(data: dict[str, Any]) -> Fragment:
    """A fragment's plain data as a Fragment (pure — pinned).

    Keys: name, version, exposure (strings), requires (names), concepts (each: concept_id, family, arguments
    as [name, type] pairs, authority, and optionally code, definition, scale as [instrument, version],
    depends_on, defined_on), references (each: concept_id, family, arguments). A missing key, a value of the
    wrong shape or an unknown key raises RegistryError with one malformed_fragment problem naming it; nothing
    is defaulted except the optional keys (code None, definition "", scale None, depends_on empty,
    defined_on None)."""
    subject = str(data.get("name", "?")) if isinstance(data, dict) else "?"
    try:
        allowed = {"name", "version", "exposure", "requires", "concepts", "references"}
        unknown = set(data) - allowed
        if unknown:
            raise KeyError(f"unknown keys {sorted(unknown)}")
        concepts = []
        for entry in data["concepts"]:
            extra = set(entry) - {
                "concept_id",
                "family",
                "arguments",
                "authority",
                "code",
                "definition",
                "scale",
                "depends_on",
                "defined_on",
            }
            if extra:
                raise KeyError(f"unknown keys {sorted(extra)} in {entry.get('concept_id')}")
            scale = entry.get("scale")
            concepts.append(
                ConceptEntry(
                    str(entry["concept_id"]),
                    str(entry["family"]),
                    _pairs(entry["arguments"]),
                    str(entry["authority"]),
                    None if entry.get("code") is None else str(entry["code"]),
                    str(entry.get("definition", "")),
                    None if scale is None else (str(scale[0]), str(scale[1])),
                    tuple(str(d) for d in entry.get("depends_on", ())),
                    None if entry.get("defined_on") is None else str(entry["defined_on"]),
                )
            )
        references = tuple(
            Reference(str(r["concept_id"]), str(r["family"]), _pairs(r["arguments"]))
            for r in data["references"]
        )
        return Fragment(
            str(data["name"]),
            str(data["version"]),
            str(data["exposure"]),
            tuple(str(r) for r in data["requires"]),
            tuple(concepts),
            references,
        )
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        raise RegistryError((("malformed_fragment", subject, str(error)),)) from error


def _is_date(text: str | None) -> bool:
    if text is None or not _DATE.fullmatch(text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _entry_problems(
    entry: ConceptEntry, authorities: dict[str, tuple[str, str | None, str, str]], legacy: bool
) -> list[Problem]:
    subject = entry.concept_id
    found: list[Problem] = []
    if not _CONCEPT_ID.fullmatch(entry.concept_id):
        found.append(("invalid_concept_id", subject, "lower-case dotted segments, a namespace first"))
    allowed = FAMILIES.get(entry.family)
    if allowed is None:
        found.append(("unknown_family", subject, entry.family))
    for name, kind in entry.arguments:
        if allowed is not None and name not in allowed:
            found.append(("unknown_argument", subject, f"{name} is no argument of {entry.family}"))
        if kind not in ARGUMENT_TYPES:
            found.append(("invalid_argument_type", subject, f"{name}: {kind}"))
    authority = authorities.get(entry.authority)
    if not entry.authority:
        found.append(("missing_provenance", subject, "no concept authority"))
    elif authority is None:
        found.append(("unknown_authority", subject, entry.authority))
    else:
        _name, edition, licence, _note = authority
        if licence == "licence_required":
            found.append(("licence_not_held", subject, entry.authority))
        if entry.code is not None and licence == "words_only":
            found.append(("proprietary_code", subject, f"{entry.authority} allows its words only"))
        elif entry.code is not None and edition is None:
            found.append(("unpinned_edition", subject, f"a {entry.authority} code needs a pinned edition"))
        if licence == "local" and not entry.definition.strip():
            found.append(("missing_definition", subject, "a local concept needs a written definition"))
        if licence == "local" and not _is_date(entry.defined_on):
            found.append(
                ("missing_definition_date", subject, "a local concept needs its own YYYY-MM-DD date")
            )
    scored = any(kind == "scale_score" for _, kind in entry.arguments)
    edition = None if entry.scale is None else entry.scale[1].strip()
    if (entry.scale is not None and not edition) or (scored and entry.scale is None):
        found.append(("unversioned_scale", subject, "a scale needs its instrument and pinned source edition"))
    elif edition == UNVERSIONED and not legacy:
        found.append(("unversioned_scale", subject, "only a legacy fragment may mark a scale unversioned"))
    return found


def registry_problems(
    fragments: list[Fragment],
    authorities: dict[str, tuple[str, str | None, str, str]],
    exposures: dict[str, Any],
) -> tuple[Problem, ...]:
    """Every reason the fragments do not compile into one registry (pure — pinned).

    Per fragment, in the order given: duplicate_fragment (a name seen before), unversioned_fragment,
    missing_provenance (no exposure) or unknown_exposure (not in `exposures`), unresolved_requirement (a
    required fragment absent). Per concept: invalid_concept_id, unknown_family, unknown_argument (a name its
    family does not take), invalid_argument_type, missing_provenance (no authority) or unknown_authority,
    licence_not_held, proprietary_code (a code from a words-only authority), unpinned_edition (a code from an
    authority whose edition is not pinned), missing_definition (a local concept without one),
    missing_definition_date (a local concept without its own valid YYYY-MM-DD definition date),
    unversioned_scale (a scale without a version, a scale-score argument without a scale, or a scale marked
    UNVERSIONED in a fragment outside LEGACY_FRAGMENTS). Across
    fragments: duplicate_concept (defined twice alike) and incompatible_definition (defined twice
    differently), each naming both owners; unresolved_dependency (a depends_on or a reference naming no
    defined concept); incompatible_definition for a reference whose family or arguments differ from the
    owner's definition, naming the owner and the referrer. No problem: an empty tuple.
    """
    found: list[Problem] = []
    names = [fragment.name for fragment in fragments]
    defined: dict[str, tuple[str, ConceptEntry]] = {}
    for index, fragment in enumerate(fragments):
        if fragment.name in names[:index]:
            found.append(("duplicate_fragment", fragment.name, "a fragment of this name was given before"))
        if not fragment.version.strip():
            found.append(("unversioned_fragment", fragment.name, "no version"))
        if not fragment.exposure:
            found.append(("missing_provenance", fragment.name, "no rule exposure"))
        elif fragment.exposure not in exposures:
            found.append(("unknown_exposure", fragment.name, fragment.exposure))
        for required in fragment.requires:
            if required not in names:
                found.append(("unresolved_requirement", fragment.name, required))
        for entry in fragment.concepts:
            found.extend(_entry_problems(entry, authorities, fragment.name in LEGACY_FRAGMENTS))
            if entry.concept_id in defined:
                owner, first = defined[entry.concept_id]
                alike = asdict(first) == asdict(entry)
                code = "duplicate_concept" if alike else "incompatible_definition"
                found.append((code, entry.concept_id, f"owners: {owner}, {fragment.name}"))
            else:
                defined[entry.concept_id] = (fragment.name, entry)
    for fragment in fragments:
        for entry in fragment.concepts:
            for dependency in entry.depends_on:
                if dependency not in defined:
                    found.append(("unresolved_dependency", entry.concept_id, dependency))
        for reference in fragment.references:
            if reference.concept_id not in defined:
                found.append(
                    ("unresolved_dependency", reference.concept_id, f"referenced by {fragment.name}")
                )
                continue
            owner, entry = defined[reference.concept_id]
            if (reference.family, set(reference.arguments)) != (entry.family, set(entry.arguments)):
                detail = f"owner {owner}, referenced differently by {fragment.name}"
                found.append(("incompatible_definition", reference.concept_id, detail))
    return tuple(found)


def registry_flags(fragments: list[Fragment]) -> tuple[tuple[str, str, str], ...]:
    """What a registry accepts without vouching for it (pure — pinned): (unversioned_scale, concept id,
    fragment name) for each concept of a LEGACY_FRAGMENTS fragment whose scale is marked UNVERSIONED, in
    fragment and concept order. A fragment outside LEGACY_FRAGMENTS is never flagged (registry_problems
    refuses its unversioned scale). None: an empty tuple."""
    return tuple(
        ("unversioned_scale", entry.concept_id, fragment.name)
        for fragment in fragments
        if fragment.name in LEGACY_FRAGMENTS
        for entry in fragment.concepts
        if entry.scale is not None and entry.scale[1].strip() == UNVERSIONED
    )


def compile_registry(fragments: list[Fragment]) -> Registry:
    """The registry the fragments compile into, under the provenance tables, or RegistryError naming every
    problem. Its version is the SHA-256 of the fragments' canonical JSON in name order, so the same fragments
    give the same version whatever order they are given in; its flags are registry_flags of that order."""
    problems = registry_problems(fragments, provenance.CONCEPT_AUTHORITIES, provenance.RULE_EXPOSURE)
    if problems:
        raise RegistryError(problems)
    ordered = sorted(fragments, key=attrgetter("name"))
    canonical = json.dumps([asdict(f) for f in ordered], ensure_ascii=False, sort_keys=True)
    concepts = {entry.concept_id: entry for fragment in ordered for entry in fragment.concepts}
    owners = {entry.concept_id: fragment.name for fragment in ordered for entry in fragment.concepts}
    return Registry(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        concepts,
        owners,
        tuple((fragment.name, fragment.version) for fragment in ordered),
        registry_flags(ordered),
    )


def load_fragments(directory: Path = FRAGMENTS_DIR) -> list[Fragment]:
    """Every fragment file of a directory, in file-name order: `*.json` read as JSON, `*.py` (not
    `__init__.py`) executed for its `FRAGMENT` dict."""
    fragments = []
    for path in sorted(directory.iterdir()):
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".py" and path.name != "__init__.py":
            spec = importlib.util.spec_from_file_location(f"_fragment_{path.stem}", path)
            if spec is None or spec.loader is None:
                raise RegistryError((("malformed_fragment", path.name, "not loadable"),))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            data = getattr(module, "FRAGMENT", None)
        else:
            continue
        if not isinstance(data, dict):
            raise RegistryError((("malformed_fragment", path.name, "no FRAGMENT dict"),))
        fragments.append(fragment_from_data(data))
    return fragments


def atom_registry_problems(atom: Atom, registry: Registry) -> tuple[str, ...]:
    """What makes an atom disagree with the registry (pure — pinned): unknown_concept (its concept id is not
    defined), unknown_argument (a param that is neither an argument its concept declares nor a candidate
    annotation, text_polarity or modality), each once. An atom of an unknown concept is not checked further.
    No problem: an empty tuple."""
    entry = registry.concepts.get(atom.concept_id)
    if entry is None:
        return ("unknown_concept",)
    declared = {name for name, _ in entry.arguments} | set(ANNOTATIONS)
    if any(name not in declared for name, _ in atom.params):
        return ("unknown_argument",)
    return ()
