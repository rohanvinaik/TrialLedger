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
import math
import re
from dataclasses import asdict, dataclass
from operator import attrgetter
from pathlib import Path
from typing import Any

from TrialLedger import provenance
from TrialLedger.semantics.contracts import ANNOTATIONS, SPAN_ROLES, Atom, Span
from TrialLedger.semantics.parsers import read_comparator, read_number, read_unit

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
    "unsupported_unit",
    "invalid_span",
    "nondeterministic_fragment",
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
class Example:
    """A criterion's text the concept is read in, with the spans of its evidence, half-open on that text."""

    text: str
    spans: tuple[Span, ...]


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
    # Added by task 3.1, each checked against the shared parsers (`semantics.parsers`): the units the
    # concept's unit argument may be stated in, as written ("mg/dL", "× 10^9/L"), and examples with spans.
    units: tuple[str, ...] = ()
    examples: tuple[Example, ...] = ()


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


def _offset(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"a span offset must be an integer, not {value!r}")
    return value


def _example(data: Any) -> Example:
    if set(data) != {"text", "spans"}:
        raise KeyError(f"an example has text and spans only, not {sorted(data)}")
    spans = tuple(Span(str(role), _offset(start), _offset(end)) for role, start, end in data["spans"])
    return Example(str(data["text"]), spans)


def fragment_from_data(data: dict[str, Any]) -> Fragment:
    """A fragment's plain data as a Fragment (pure — pinned).

    Keys: name, version, exposure (strings), requires (names), concepts (each: concept_id, family, arguments
    as [name, type] pairs, authority, and optionally code, definition, scale as [instrument, version],
    depends_on, defined_on, units as written, examples each {text, spans as [role, start, end]}), references
    (each: concept_id, family, arguments). A missing key, a value of the wrong shape (a span offset that is
    not an integer among them) or an unknown key raises RegistryError with one malformed_fragment problem
    naming it; nothing is defaulted except the optional keys (code None, definition "", scale None,
    depends_on, units and examples empty, defined_on None)."""
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
                "units",
                "examples",
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
                    tuple(str(unit) for unit in entry.get("units", ())),
                    tuple(_example(example) for example in entry.get("examples", ())),
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
    return [*found, *unit_problems(entry), *example_problems(entry)]


def unit_problems(entry: ConceptEntry) -> tuple[Problem, ...]:
    """Every unit a concept declares that the shared parsers cannot support (pure — pinned).

    Each declared unit, in order, is unsupported_unit (subject the concept id, detail naming the unit and the
    reason) when the concept takes no unit argument; when `parsers.read_unit` does not read the whole of it as
    one unit (a reference expression such as "× ULN" is never a unit; "mg/dL " or "mg/dL and" is more than
    one); or when it has no UCUM form and the concept's unit argument is typed ucum_unit (an unmapped unit is
    supported only as unit_as_written). No problem: an empty tuple."""
    unit_type = dict(entry.arguments).get("unit")
    found: list[Problem] = []
    for unit in entry.units:
        parse = read_unit(unit, 0)
        if unit_type is None:
            reason = "the concept takes no unit"
        elif parse.status == "abstained" or parse.spans != (Span("unit", 0, len(unit)),):
            reason = parse.note or "not one unit, whole"
        elif unit_type == "ucum_unit" and dict(parse.readings[0])["mapping"] == "unmapped":
            reason = "no UCUM form, and the unit argument is ucum_unit"
        else:
            continue
        found.append(("unsupported_unit", entry.concept_id, f"{unit!r}: {reason}"))
    return tuple(found)


_SPAN_READERS = {"comparator": read_comparator, "unit": read_unit}


def example_problems(entry: ConceptEntry) -> tuple[Problem, ...]:
    """Every invalid span of a concept's examples (pure — pinned).

    Each span of each example, in order, is invalid_span (subject the concept id, detail naming the example's
    index, the span and the reason) when its role is not a contract span role (contracts.SPAN_ROLES); when it
    is not half-open and non-empty within the example's text (0 <= start < end <= len(text)); or when the
    shared parsers, reading at its start, do not read exactly its words in its role: a comparator span as a
    comparator, a unit span as a unit (a reference expression is never a unit), and, for a concept whose value
    argument is typed number, a value span as a number. Any other span (concept, qualifier, window, whole, a
    categorical value) is held to its bounds only. No problem: an empty tuple."""
    numeric = dict(entry.arguments).get("value") == "number"
    found: list[Problem] = []
    for index, example in enumerate(entry.examples):
        for span in example.spans:
            reader = read_number if span.role == "value" and numeric else _SPAN_READERS.get(span.role)
            if span.role not in SPAN_ROLES:
                reason = "a role no contract span has"
            elif not 0 <= span.start < span.end <= len(example.text):
                reason = "not a non-empty half-open span within the text"
            elif reader is not None and span not in (parse := reader(example.text, span.start)).spans:
                reason = f"not read there as its role ({parse.note or 'other words'})"
            else:
                continue
            where = f"example {index}: {span.role} [{span.start}, {span.end})"
            found.append(("invalid_span", entry.concept_id, f"{where} {reason}"))
    return tuple(found)


def _unstable(value: Any, where: str) -> list[tuple[str, str]]:
    """Where plain data holds what may differ from one load to the next."""
    if isinstance(value, (set, frozenset)):
        return [(where, "an unordered set, whose order is the interpreter's hash seed's")]
    if isinstance(value, float) and not math.isfinite(value):
        return [(where, "a number that is not finite")]
    if isinstance(value, dict):
        return [found for key, item in value.items() for found in _unstable(item, f"{where}.{key}")]
    if isinstance(value, (list, tuple)):
        return [found for index, item in enumerate(value) for found in _unstable(item, f"{where}[{index}]")]
    return []


def _alike(first: Any, second: Any) -> bool:
    """Whether two loads are one and the same, a NaN alike to a NaN (each load makes its own float object)."""
    if isinstance(first, float) and isinstance(second, float) and math.isnan(first) and math.isnan(second):
        return True
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(_alike(first[key], second[key]) for key in first)
    if isinstance(first, (list, tuple)) and type(first) is type(second):
        return len(first) == len(second) and all(map(_alike, first, second))
    return first == second


def nondeterminism_problems(name: str, first: Any, second: Any) -> tuple[Problem, ...]:
    """Whether a fragment's data, loaded twice, is one and the same (pure — pinned).

    nondeterministic_fragment (subject the fragment's file name) for each place in the first load that holds
    an unordered set or frozenset (its order, once listed, is the interpreter's hash seed's) or a number that
    is not finite (NaN is not even equal to itself), each named by its path ("FRAGMENT.concepts[2].units");
    and once more when the two loads are not alike (a fragment that reads a clock, a random draw or a
    counter), a NaN alike to a NaN in the same place, so a NaN is named by its place alone. A list made from a
    set's order within one process loads alike twice and is not seen here. No problem: an empty tuple."""
    found = [
        ("nondeterministic_fragment", name, f"{where}: {why}") for where, why in _unstable(first, "FRAGMENT")
    ]
    if not _alike(first, second):
        found.append(("nondeterministic_fragment", name, "two loads of the fragment gave different data"))
    return tuple(found)


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


def _canonical(fragment: Fragment) -> dict[str, Any]:
    data = asdict(fragment)
    for concept in data["concepts"]:
        for added in ("units", "examples"):
            if not concept[added]:
                del concept[added]
    return data


def compile_registry(fragments: list[Fragment]) -> Registry:
    """The registry the fragments compile into, under the provenance tables, or RegistryError naming every
    problem. Its version is the SHA-256 of the fragments' canonical JSON in name order, so the same fragments
    give the same version whatever order they are given in; its flags are registry_flags of that order. The
    units and examples task 3.1 added enter the canonical JSON only when a concept has them, so every registry
    compiled before them keeps its version."""
    problems = registry_problems(fragments, provenance.CONCEPT_AUTHORITIES, provenance.RULE_EXPOSURE)
    if problems:
        raise RegistryError(problems)
    ordered = sorted(fragments, key=attrgetter("name"))
    canonical = json.dumps([_canonical(f) for f in ordered], ensure_ascii=False, sort_keys=True)
    concepts = {entry.concept_id: entry for fragment in ordered for entry in fragment.concepts}
    owners = {entry.concept_id: fragment.name for fragment in ordered for entry in fragment.concepts}
    return Registry(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        concepts,
        owners,
        tuple((fragment.name, fragment.version) for fragment in ordered),
        registry_flags(ordered),
    )


def _fragment_data(path: Path) -> Any:
    """A fragment file's plain data: `*.json` read as JSON, `*.py` executed afresh for its `FRAGMENT`."""
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(f"_fragment_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RegistryError((("malformed_fragment", path.name, "not loadable"),))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "FRAGMENT", None)


def load_fragments(directory: Path = FRAGMENTS_DIR) -> list[Fragment]:
    """Every fragment file of a directory, in file-name order: `*.json` read as JSON, `*.py` (not
    `__init__.py`) executed for its `FRAGMENT` dict. Each is loaded twice, and refused, naming each place,
    when the two loads are not one and the same (nondeterminism_problems)."""
    fragments = []
    for path in sorted(directory.iterdir()):
        if path.suffix != ".json" and (path.suffix != ".py" or path.name == "__init__.py"):
            continue
        data = _fragment_data(path)
        problems = nondeterminism_problems(path.name, data, _fragment_data(path))
        if problems:
            raise RegistryError(problems)
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
