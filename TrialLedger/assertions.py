"""Scoped assertions: eligibility as scoped constraints over structured propositions
(openspec/changes/add-scoped-assertions, design Decisions 1-6 and 9; task 1.1).

An assertion is a modality acting on a whole proposition, under an applicability condition and a cohort scope,
with its spans, its rule and its epistemic status. A proposition keeps its Boolean structure (`AllOf`,
`AnyOf`, `Not`), each literal its subject, predicate, value, polarity, time and qualifiers, and what is not
yet read is `Opaque`: unresolved, never false. Every field is immutable typed data whose words come from a
closed vocabulary; a construction outside the vocabularies is refused (`ModelError`, naming the problem), so
an unknown word is written "unresolved", never as a new string. `canonical` is the serialization that keeps
compound identity: a qualified literal, a conjunction and their order survive it, and `from_canonical` reads
it back unchanged.

Atoms stay as they are, evidence candidates; nothing here reads text or atoms (the compiler is task group 2).
"""

from __future__ import annotations

import dataclasses
import json
import math
from typing import Any

# The closed vocabularies of design Decision 2 (the draft's table, reconciled; 2026-11-01).
MODALITIES = frozenset({"required", "excluded", "permitted", "definitional", "descriptive", "unresolved"})
POLARITIES = frozenset({"positive", "negative", "unresolved"})
STATUSES = frozenset({"known", "interpolated", "proposed"})
RESOLUTIONS = frozenset({"resolved", "partially_resolved", "unresolved", "conflicting"})
SUBJECT_KINDS = frozenset(
    {
        "participant",
        "source_case",
        "partner",
        "caregiver",
        "other_person",
        "study_intervention",
        "study_procedure",
        "encounter",
        "specimen",
        "unresolved",
    }
)
PREDICATE_KINDS = frozenset(
    {
        "condition_status",
        "exposure",
        "treatment_history",
        "procedure_event",
        "measurement",
        "demographic",
        "disease_attribute",
        "medication_use",
        "medication_stability",
        "consent",
        "reproductive_status",
        "encounter_purpose",
        "defined_term",
        "unresolved",
    }
)
VALUE_KINDS = frozenset(
    {"boolean", "enum", "enum_set", "quantity", "interval", "entity_ref", "definition_ref", "unresolved"}
)
COMPARISONS = frozenset({"eq", "ne", "lt", "le", "gt", "ge", "in", "not_in"})
ORIENTATIONS = frozenset({"at", "before", "after", "during", "between", "unspecified"})
ANCHOR_KINDS = frozenset(
    {
        "enrollment",
        "randomization",
        "treatment_start",
        "study_interval",
        "named_event",
        "calendar_date",
        "unspecified",
    }
)
INCLUSIVITIES = frozenset({"inclusive", "exclusive", "unspecified"})
CERTAINTIES = frozenset({"explicit", "entailed", "unresolved"})
BRANCH_NODES = frozenset({"all_of", "any_of", "not", "leaf", "opaque", "unresolved"})
SCOPE_KINDS = frozenset(
    {"all_participants", "cohort_ref", "phase_ref", "arm_ref", "all_of", "any_of", "unresolved"}
)
EVIDENCE_KINDS = frozenset(
    {"record_field", "text_span", "atom_ref", "rule_application", "warrant_ref", "targeted_answer"}
)

# Which comparisons each value kind admits; members and numbers are checked in `model_problem`.
KIND_COMPARISONS = {
    "boolean": frozenset({"eq"}),
    "enum": frozenset({"eq", "ne", "in", "not_in"}),
    "enum_set": frozenset({"in", "not_in"}),
    "quantity": frozenset({"eq", "ne", "lt", "le", "gt", "ge"}),
    "interval": frozenset({"in", "not_in"}),
    "entity_ref": frozenset({"eq"}),
    "definition_ref": frozenset({"eq"}),
    "unresolved": COMPARISONS,
}
SCOPE_REFS = frozenset({"cohort_ref", "phase_ref", "arm_ref", "unresolved"})


class ModelError(ValueError):
    """A construction outside the object model; its argument is the problem's code."""


def model_problem(item: object) -> str:
    """What makes one object of the model malformed, as a code, or "ok" (pure — pinned).

    Every word must belong to its closed vocabulary (design Decision 2: unknown is "unresolved", never a new
    string); every nested field must be of its declared class and every sequence a tuple (immutability); an
    `AllOf` or `AnyOf` holds at least two propositions; `other_person` names its referent; a predicate other
    than unresolved names its key; a value's comparison suits its kind, with its members or its finite number
    (never a bool or NaN), an interval's bounds ordered; an event anchor names its event; a span is half-open
    and non-negative; an unresolved rule names nothing else (version "unresolved", no premise, warrant or
    answer: no invented provenance); an assertion has an id and its rule, stated or explicitly unresolved,
    never defaulted. The nested objects were checked when they were built."""
    if isinstance(item, Always):  # first: the module builds ALWAYS before the classes after it
        return "ok"
    if isinstance(item, Evidence):
        if item.kind not in EVIDENCE_KINDS:
            return "evidence_kind_outside_vocabulary"
        return "ok" if isinstance(item.ref, str) and item.ref else "evidence_without_ref"
    if isinstance(item, Subject):
        if item.kind not in SUBJECT_KINDS:
            return "subject_kind_outside_vocabulary"
        if item.kind == "other_person" and not item.referent:
            return "other_person_without_referent"
        return "ok" if isinstance(item.referent, str) else "referent_not_text"
    if isinstance(item, Predicate):
        if item.kind not in PREDICATE_KINDS:
            return "predicate_kind_outside_vocabulary"
        if not isinstance(item.key, str) or (item.kind != "unresolved" and not item.key):
            return "predicate_without_key"
        return "ok"
    if isinstance(item, Value):
        return _value_problem(item)
    if isinstance(item, TemporalScope):
        return _time_problem(item)
    if isinstance(item, Literal):
        if not isinstance(item.subject, Subject):
            return "literal_subject_not_subject"
        if not isinstance(item.predicate, Predicate):
            return "literal_predicate_not_predicate"
        if not isinstance(item.value, Value):
            return "literal_value_not_value"
        if item.polarity not in POLARITIES:
            return "polarity_outside_vocabulary"
        if item.time is not None and not isinstance(item.time, TemporalScope):
            return "literal_time_not_temporal_scope"
        if not isinstance(item.qualifiers, CONDITIONS):
            return "qualifiers_not_condition"
        return _evidence_problem(item.evidence)
    if isinstance(item, AllOf | AnyOf):
        if not isinstance(item.parts, tuple) or len(item.parts) < 2:
            return "compound_needs_two_parts"
        return (
            "ok" if all(isinstance(p, PROPOSITIONS) for p in item.parts) else "compound_part_not_proposition"
        )
    if isinstance(item, Not):
        return "ok" if isinstance(item.part, PROPOSITIONS) else "negated_part_not_proposition"
    if isinstance(item, Opaque):
        return "ok" if isinstance(item.ref, str) and item.ref else "opaque_without_ref"
    if isinstance(item, Scope):
        return _scope_problem(item)
    if isinstance(item, Branch):
        if item.node not in BRANCH_NODES:
            return "branch_node_outside_vocabulary"
        ok_path = isinstance(item.path, tuple) and all(_whole(i) and i >= 0 for i in item.path)
        return "ok" if ok_path else "branch_path_not_indexes"
    if isinstance(item, Span):
        if not (_whole(item.start) and _whole(item.end)) or item.start < 0:
            return "span_not_offsets"
        return "ok" if item.start <= item.end else "span_not_half_open"
    if isinstance(item, Rule):
        if not (isinstance(item.id, str) and item.id and isinstance(item.version, str) and item.version):
            return "rule_without_id_or_version"
        refs = (*item.premises, *item.warrants, *item.answers)
        if item.id == "unresolved" and (item.version != "unresolved" or refs):
            return "unresolved_rule_with_provenance"
        tuples = all(isinstance(t, tuple) for t in (item.premises, item.warrants, item.answers))
        return "ok" if tuples and all(isinstance(r, str) and r for r in refs) else "rule_refs_not_text"
    if isinstance(item, ScopedAssertion):
        return _assertion_problem(item)
    return "not_a_model_object"


def _whole(number: object) -> bool:
    return isinstance(number, int) and not isinstance(number, bool)


def _finite(number: object) -> bool:
    return isinstance(number, int | float) and not isinstance(number, bool) and math.isfinite(number)


def _evidence_problem(evidence: object) -> str:
    if not isinstance(evidence, tuple) or not all(isinstance(e, Evidence) for e in evidence):
        return "evidence_not_tuple_of_evidence"
    return "ok"


def _value_problem(value: Value) -> str:
    if value.kind not in VALUE_KINDS:
        return "value_kind_outside_vocabulary"
    if value.comparison not in KIND_COMPARISONS[value.kind]:
        return "comparison_not_for_value_kind"
    if value.inclusivity not in INCLUSIVITIES:
        return "inclusivity_outside_vocabulary"
    if not isinstance(value.members, tuple) or not all(isinstance(m, str) and m for m in value.members):
        return "members_not_tuple_of_text"
    if not isinstance(value.unit, str):
        return "unit_not_text"
    numbers = [n for n in (value.number, value.upper) if n is not None]
    if not all(_finite(n) for n in numbers):
        return "number_not_finite"
    if value.kind == "unresolved":
        return "ok"
    single = value.comparison in ("eq", "ne")
    if value.kind in ("enum", "enum_set", "entity_ref", "definition_ref"):
        if len(value.members) != 1 if single else not value.members:
            return "members_do_not_fit_comparison"
        return "ok" if not numbers else "number_on_unnumbered_kind"
    if value.kind == "boolean":
        return "ok" if not (numbers or value.members) else "boolean_with_operand"
    if value.members:
        return "members_on_numbered_kind"
    if value.kind == "quantity":
        return "ok" if value.number is not None and value.upper is None else "quantity_needs_one_number"
    if value.number is None or value.upper is None:
        return "interval_needs_two_numbers"
    return "ok" if value.number <= value.upper else "interval_bounds_reversed"


def _time_problem(time: TemporalScope) -> str:
    if time.orientation not in ORIENTATIONS:
        return "orientation_outside_vocabulary"
    if time.anchor not in ANCHOR_KINDS:
        return "anchor_outside_vocabulary"
    if time.anchor == "named_event" and not time.anchor_ref:
        return "named_event_without_ref"
    if time.inclusivity not in INCLUSIVITIES:
        return "inclusivity_outside_vocabulary"
    if time.certainty not in CERTAINTIES:
        return "certainty_outside_vocabulary"
    bounds = [b for b in (time.lower, time.upper) if b is not None]
    if not all(_finite(b) for b in bounds):
        return "number_not_finite"
    if time.lower is not None and time.upper is not None and time.lower > time.upper:
        return "time_bounds_reversed"
    if not (isinstance(time.unit, str) and isinstance(time.anchor_ref, str)):
        return "time_text_not_text"
    return _evidence_problem(time.evidence)


def _scope_problem(scope: Scope) -> str:
    if scope.kind not in SCOPE_KINDS:
        return "scope_kind_outside_vocabulary"
    if not isinstance(scope.parts, tuple) or not all(isinstance(p, Scope) for p in scope.parts):
        return "scope_parts_not_scopes"
    if scope.kind in ("all_of", "any_of"):
        return "ok" if len(scope.parts) >= 2 and not scope.ref else "scope_combination_malformed"
    if scope.parts:
        return "scope_combination_malformed"
    if scope.kind in SCOPE_REFS and scope.kind != "unresolved":
        return "ok" if isinstance(scope.ref, str) and scope.ref else "scope_without_ref"
    return "ok" if isinstance(scope.ref, str) else "scope_ref_not_text"


def _assertion_problem(item: ScopedAssertion) -> str:
    if not (isinstance(item.id, str) and item.id):
        return "assertion_without_id"
    if not isinstance(item.criterion_ref, str):
        return "criterion_ref_not_text"
    if item.modality not in MODALITIES:
        return "modality_outside_vocabulary"
    if item.status not in STATUSES:
        return "status_outside_vocabulary"
    if item.resolution not in RESOLUTIONS:
        return "resolution_outside_vocabulary"
    if not isinstance(item.body, PROPOSITIONS):
        return "body_not_proposition"
    if not isinstance(item.applicability, CONDITIONS):
        return "applicability_not_condition"
    if item.rule is None:
        return "assertion_without_rule"
    kinds = ((item.cohort, Scope), (item.branch, Branch), (item.rule, Rule))
    if not all(isinstance(field, cls) for field, cls in kinds):
        return "assertion_field_not_its_class"
    if not isinstance(item.span, tuple) or not all(isinstance(s, Span) for s in item.span):
        return "span_not_tuple_of_spans"
    return "ok"


class _Validated:
    """Every class of the model refuses, on construction, what `model_problem` names."""

    def __post_init__(self) -> None:
        problem = model_problem(self)
        if problem != "ok":
            raise ModelError(problem)


@dataclasses.dataclass(frozen=True)
class Evidence(_Validated):
    """One piece of provenance: a record field, a half-open span, an atom, a rule, a warrant, an answer."""

    kind: str
    ref: str


@dataclasses.dataclass(frozen=True)
class Subject(_Validated):
    """Whose attribute a literal states; `other_person` names its referent explicitly."""

    kind: str
    referent: str = ""


@dataclasses.dataclass(frozen=True)
class Predicate(_Validated):
    """The predicate's kind and its key in a versioned registry (task 1.2); unresolved may lack a key."""

    kind: str
    key: str = ""


@dataclasses.dataclass(frozen=True)
class Value(_Validated):
    """A literal's value: boolean, an enumerated member or members, a quantity (number and unit as written; a
    missing unit stays ""), an interval [number, upper] with its boundary inclusivity, a reference, or
    unresolved. An `enum` is one value of an open domain (`in` S: it is one of S); an `enum_set` is a set of
    members (`in` S: the set holds every member of S; `not_in` S: it holds none of them)."""

    kind: str
    comparison: str = "eq"
    members: tuple[str, ...] = ()
    number: float | None = None
    upper: float | None = None
    unit: str = ""
    inclusivity: str = "unspecified"


@dataclasses.dataclass(frozen=True)
class TemporalScope(_Validated):
    """Time (design Decision 4): orientation, anchor (an event anchor named), bounds with their unit as
    written, inclusivity, certainty and evidence. An event-relative window is never an enrollment window."""

    orientation: str
    anchor: str
    anchor_ref: str = ""
    lower: float | None = None
    upper: float | None = None
    unit: str = ""
    inclusivity: str = "unspecified"
    certainty: str = "unresolved"
    evidence: tuple[Evidence, ...] = ()


@dataclasses.dataclass(frozen=True)
class Always(_Validated):
    """The condition that always holds: no applicability antecedent, no qualifier."""


ALWAYS = Always()


@dataclasses.dataclass(frozen=True)
class Literal(_Validated):
    """subject . predicate (comparison) value, with polarity, time and qualifiers. A qualified literal denotes
    the conjunction of its base and its qualifiers, and its polarity negates that conjunction: a negative
    qualified literal is NOT (base AND qualifiers), never (NOT base) AND qualifiers. Its compound identity
    survives serialization."""

    subject: Subject
    predicate: Predicate
    value: Value
    polarity: str = "positive"
    time: TemporalScope | None = None
    qualifiers: Condition = ALWAYS
    evidence: tuple[Evidence, ...] = ()


@dataclasses.dataclass(frozen=True)
class AllOf(_Validated):
    """Every part holds (at least two parts, in their written order)."""

    parts: tuple[Proposition, ...]


@dataclasses.dataclass(frozen=True)
class AnyOf(_Validated):
    """At least one part holds (inclusive; at least two parts)."""

    parts: tuple[Proposition, ...]


@dataclasses.dataclass(frozen=True)
class Not(_Validated):
    """The part does not hold; the negation keeps its scope."""

    part: Proposition


@dataclasses.dataclass(frozen=True)
class Opaque(_Validated):
    """Content not yet read, named by its unresolved reference: unresolved, never false."""

    ref: str


@dataclasses.dataclass(frozen=True)
class Scope(_Validated):
    """The cohort scope: all participants, a named cohort, phase or arm, a combination, or unresolved."""

    kind: str
    ref: str = ""
    parts: tuple[Scope, ...] = ()


EVERY_PARTICIPANT = Scope("all_participants")


@dataclasses.dataclass(frozen=True)
class Branch(_Validated):
    """Where in its criterion's structure an assertion sits: the node kind and its path of part indexes; a
    position not known is "unresolved", never "leaf"."""

    node: str
    path: tuple[int, ...] = ()


@dataclasses.dataclass(frozen=True)
class Span(_Validated):
    """A half-open character span [start, end) of the record's text."""

    start: int
    end: int


@dataclasses.dataclass(frozen=True)
class Rule(_Validated):
    """The derivation: rule id and version, the premises, warrants and targeted answers it used.
    `UNRESOLVED_RULE` says explicitly that the derivation is not known; an assertion carrying it is never a
    premise."""

    id: str
    version: str
    premises: tuple[str, ...] = ()
    warrants: tuple[str, ...] = ()
    answers: tuple[str, ...] = ()


UNRESOLVED_RULE = Rule("unresolved", "unresolved")


@dataclasses.dataclass(frozen=True)
class ScopedAssertion(_Validated):
    """A modality on a whole proposition, under applicability and cohort scope, with provenance and status.
    Its rule is required (no default: provenance is never invented; `UNRESOLVED_RULE` says it is not known),
    its branch position defaults to "unresolved", its status to proposed and its resolution to unresolved."""

    id: str
    criterion_ref: str
    modality: str
    body: Proposition
    applicability: Condition = ALWAYS
    cohort: Scope = EVERY_PARTICIPANT
    branch: Branch = Branch("unresolved")
    span: tuple[Span, ...] = ()
    rule: Rule | None = None
    status: str = "proposed"
    resolution: str = "unresolved"


Proposition = Literal | AllOf | AnyOf | Not | Opaque
Condition = Always | Literal | AllOf | AnyOf | Not | Opaque
PROPOSITIONS = (Literal, AllOf, AnyOf, Not, Opaque)
CONDITIONS = (Always, *PROPOSITIONS)
CLASSES = {
    cls.__name__: cls
    for cls in (
        Evidence,
        Subject,
        Predicate,
        Value,
        TemporalScope,
        Always,
        Literal,
        AllOf,
        AnyOf,
        Not,
        Opaque,
        Scope,
        Branch,
        Span,
        Rule,
        ScopedAssertion,
    )
}


def canonical(item: object) -> str:
    """The canonical serialization of a model object (pure — pinned).

    JSON with each object tagged by its class, keys sorted, every number written as a float (200 and 200.0 are
    one value), sequences in their written order. Nothing is flattened, reordered or dropped: `AllOf(A, B)`,
    `AllOf(B, A)`, `Literal(A, qualifiers=Q)` and `AllOf(A, Q)` serialize distinctly, so compound identity
    survives; `from_canonical` reads it back to an equal object. Anything outside the model: `ModelError`."""
    return json.dumps(_plain(item), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _plain(item: object) -> object:
    if isinstance(item, tuple):
        return [_plain(part) for part in item]
    if isinstance(item, bool) or item is None or isinstance(item, str):
        return item
    if isinstance(item, int | float):
        return float(item)
    if type(item).__name__ in CLASSES and dataclasses.is_dataclass(item):
        fields = {f.name: _plain(getattr(item, f.name)) for f in dataclasses.fields(item)}
        return {"class": type(item).__name__, **fields}
    raise ModelError("not_a_model_object")


def from_canonical(text: str) -> object:
    """The model object a canonical serialization names; validated again on the way (`ModelError`)."""
    return _build(json.loads(text))


def _build(node: object) -> object:
    if isinstance(node, list):
        return tuple(_build(part) for part in node)
    if not isinstance(node, dict):
        return node
    cls = CLASSES.get(node.get("class"))
    if cls is None:
        raise ModelError("not_a_model_object")
    fields: dict[str, Any] = {name: _build(value) for name, value in node.items() if name != "class"}
    # offsets and indexes are whole numbers, written as floats; a fraction stays one, and is refused
    if cls is Span:
        fields = {k: int(v) if isinstance(v, float) and v.is_integer() else v for k, v in fields.items()}
    if cls is Branch and isinstance(fields.get("path"), tuple):
        path = fields["path"]
        fields["path"] = tuple(int(i) if isinstance(i, float) and i.is_integer() else i for i in path)
    names = {f.name for f in dataclasses.fields(cls)}
    if not set(fields) <= names:
        raise ModelError("fields_do_not_fit_class")
    return cls(**fields)
