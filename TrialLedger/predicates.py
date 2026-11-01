"""The first predicate registry (openspec/changes/add-scoped-assertions task 1.2; design Decision 2).

Each concept of the seed concept registry (add-bank-coverage's `nsclc_legacy` fragment: the existing banks'
concepts, `semantics/loader.py`) is mapped to the predicate a literal states of it: its predicate kind (one
of `assertions.PREDICATE_KINDS`), its key, the value kind its literal takes (one of `assertions.VALUE_KINDS`)
with its unit where it has one, and the subject it speaks of (the participant, unless the concept itself names
another). The key is the concept id itself: one predicate per registry concept, so two concepts are never one
variable of entailment; making them one would be an ontology relation, which needs a cited source (A3), and
none is declared. A concept whose predicate kind is not settled is mapped "unresolved", never guessed, with
what leaves it open in its note (UNRESOLVED lists them).

The mapping is versioned by its own digest (VERSION: the SHA-256 of its canonical JSON, in concept order).
Its provenance is the concept registry's: `predicate_registry` gives each entry the concept's authority
(`provenance.CONCEPT_AUTHORITIES`) and the rule exposure its owning fragment declares
(`provenance.RULE_EXPOSURE`), with the populations that exposure names, and refuses a mapping that disagrees
with the registry.

Two pure decisions: `mapping_problems` (what makes a mapping disagree with the registry or the closed
vocabularies) and `atom_literal` (the literal a mapped atom becomes; the compiler of task group 2 calls it).
Nothing here reads text: an atom's params that are not its value's operands (a window, a grade, a scope, a
stage or PD-L1 expression as written, a lab's qualifier) are named back, unread, for the compiling decisions
of D5 and D6, and its candidate annotations (`text_polarity`, `modality`) are never read (Decision 1).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from operator import itemgetter

from TrialLedger.assertions import (
    PREDICATE_KINDS,
    SUBJECT_KINDS,
    VALUE_KINDS,
    Evidence,
    Literal,
    Predicate,
    Subject,
    Value,
)
from TrialLedger.banks import AGENT_WORDS, ANALYTES, GENES, HISTOLOGY
from TrialLedger.provenance import RULE_EXPOSURE
from TrialLedger.semantics.contracts import ANNOTATIONS, Atom, slug
from TrialLedger.semantics.loader import Fragment, compile_registry, load_fragments

# The unit of a quantity read from the atom's own "unit" param, as written ("" when the atom has none).
UNIT_AS_WRITTEN = "<as written>"

# The value kinds a literal of each predicate family (loader.FAMILIES) may take; "unresolved" fits every
# family. A characteristic (Attribute) is any of them; a measured value is a number, an interval or one score
# of an ordinal scale (ECOG); a state holds or not, or is one or several of named states; an event, a
# capability or a commitment holds or not; an exposure holds or not, or names its agents; a count is a
# number, an interval or a counted category as written ("3+"); a relation holds or not, or names its object.
# The first setting (2026-11-01), open to the founder's ruling.
FAMILY_VALUE_KINDS: dict[str, frozenset[str]] = {
    "Attribute": frozenset({"boolean", "enum", "enum_set", "quantity", "interval"}),
    "Measurement": frozenset({"quantity", "interval", "enum"}),
    "State": frozenset({"boolean", "enum", "enum_set"}),
    "Event": frozenset({"boolean"}),
    "Exposure": frozenset({"boolean", "enum_set", "entity_ref"}),
    "Count": frozenset({"quantity", "interval", "enum"}),
    "Relation": frozenset({"boolean", "entity_ref"}),
    "Capability": frozenset({"boolean"}),
    "Commitment": frozenset({"boolean"}),
}
# The params each value kind reads as its operands; every other param but the annotations is named unread.
OPERANDS = {"quantity": ("comparator", "value", "unit"), "interval": ("minimum", "maximum")}
# The banks' normalised comparators (banks._COMPARATORS) as the model's comparisons.
COMPARISONS = {"≥": "ge", "≤": "le", ">": "gt", "<": "lt"}
_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")  # a plain decimal; "1,5" is not read (1.5 or 1,500?)


@dataclass(frozen=True)
class PredicateMapping:
    """One registry concept as a predicate: its kind, the value kind of its literal, the unit of a quantity or
    interval ("" none; UNIT_AS_WRITTEN read from the atom; else the concept's own unit, an atom writing
    another never read), the subject it speaks of, and why (an unresolved mapping's note says what leaves it
    open). The key is the concept id."""

    concept_id: str
    kind: str
    value_kind: str
    unit: str = ""
    subject: str = "participant"
    note: str = ""


_NAMED_CONDITION = "a named condition (design Decision 2: named conditions are condition_status)"
_TREATMENT = "prior therapy (design Decision 2: prior therapy is treatment_history)"
_MEDICATION = "the use of a medication, current or planned (D4 decides which)"
_NO_NUMBER = (
    "a named measurement (the construction's reading, open to the founder's ruling); the conditions bank "
    "keeps no number and the concept declares no operand, so its value is unresolved"
)
# (predicate kind, value kind, unit, subject, note) of each named condition of bank:conditions, by name.
_CONDITIONS: dict[str, tuple[str, str, str, str, str]] = {
    "informed_consent": (
        "consent",
        "boolean",
        "",
        "participant",
        "the participant's consent: a Commitment that a predicate kind names (consent), unlike compliance, "
        "contraception and vitamin premedication",
    ),
    "compliance": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: a willingness or ability to comply with the protocol; no predicate kind names an "
        "undertaking or a capability",
    ),
    "contraception": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: its words name a status (sterilised) and an undertaking (to use contraception, "
        "abstinence); reproductive_status names the status only",
    ),
    "pregnancy_or_breastfeeding": (
        "reproductive_status",
        "boolean",
        "",
        "participant",
        "pregnancy or breastfeeding",
    ),
    "life_expectancy": ("measurement", "unresolved", "", "participant", _NO_NUMBER),
    "measurable_disease": (
        "disease_attribute",
        "boolean",
        "",
        "participant",
        "measurable disease (RECIST): an attribute of the trial's own disease",
    ),
    "cns_metastases": (
        "disease_attribute",
        "boolean",
        "",
        "participant",
        "metastasis of the trial's own disease to the CNS: an attribute of that disease, as its extent is",
    ),
    "other_malignancy": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "hiv": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "hepatitis": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "tuberculosis": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "active_infection": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "autoimmune_disease": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "pneumonitis_ild": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "organ_transplant": (
        "procedure_event",
        "boolean",
        "",
        "participant",
        "a transplant undergone: a procedure",
    ),
    "immunosuppression_steroids": ("medication_use", "boolean", "", "participant", _MEDICATION),
    "qtc": ("measurement", "unresolved", "", "participant", _NO_NUMBER),
    "cardiac_disease": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "hypertension": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "bleeding_thrombosis": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "anticoagulant_use": ("medication_use", "boolean", "", "participant", _MEDICATION),
    "gi_perforation_fistula": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "malabsorption": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: its words name a condition (malabsorption) and a capability (to swallow); no predicate "
        "kind names a capability",
    ),
    "hypersensitivity": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "live_vaccine": (
        "exposure",
        "boolean",
        "",
        "participant",
        "receipt of a live vaccine: an exposure to an agent, neither a treatment of the disease nor a "
        "medication in use",
    ),
    "recent_surgery": ("procedure_event", "boolean", "", "participant", "surgery undergone: a procedure"),
    "recent_radiotherapy": ("treatment_history", "boolean", "", "participant", _TREATMENT),
    "unresolved_toxicity": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "tissue_available": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: the availability of a tissue specimen; no predicate kind names availability, and its "
        "subject stays the participant, since the concept (a Capability) does not name the specimen",
    ),
    "other_investigational": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: its words name an investigational agent received and participation in another study; "
        "no predicate kind names study participation",
    ),
    "interacting_medication": ("medication_use", "boolean", "", "participant", _MEDICATION),
    "substance_or_psychiatric": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "smoking": ("exposure", "boolean", "", "participant", "tobacco smoking: an exposure"),
    "effusion": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "neurologic_disorder": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "pulmonary_function": ("measurement", "unresolved", "", "participant", _NO_NUMBER),
    "weight_loss": (
        "condition_status",
        "boolean",
        "",
        "participant",
        "weight loss, read as a condition the participant has (as cachexia is), though its family is Event "
        "(a loss over a window); no predicate kind names an event other than a procedure, and the bank keeps "
        "no number. Open to the founder's ruling",
    ),
    "investigator_judgment": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: an investigator's judgment of the participant, a relation, not the participant's "
        "attribute; no predicate kind names it",
    ),
    "serious_comorbidity": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
    "sex": (
        "demographic",
        "enum",
        "",
        "participant",
        "sex; the bank's words admit either sex and name no member, so its value is unresolved",
    ),
    "diagnosis_confirmed": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: how a diagnosis was established (histology, cytology), of a condition the concept "
        "does not name",
    ),
    "prior_enrollment": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: enrolment in this study before; no predicate kind names study participation",
    ),
    "vitamin_premedication": (
        "unresolved",
        "boolean",
        "",
        "participant",
        "unresolved: an undertaking to take folic acid or vitamin B12 (a Commitment, as compliance and "
        "contraception are); no predicate kind names an undertaking, and medication_use names the use only",
    ),
    "organ_impairment": ("condition_status", "boolean", "", "participant", _NAMED_CONDITION),
}

# (concept id, predicate kind, value kind, unit, subject, note), in the seed fragment's order.
_ROWS: list[tuple[str, str, str, str, str, str]] = [
    (
        "nsclc.ecog_ps",
        "measurement",
        "enum",
        "",
        "participant",
        "a performance-status score, one of those a criterion allows: an ordinal scale, its scores members",
    ),
    (
        "nsclc.prior_lines",
        "treatment_history",
        "enum",
        "",
        "participant",
        "prior lines of systemic therapy, one of 0, 1, 2 or 3+ (3+ is no number)",
    ),
    (
        "nsclc.stage",
        "disease_attribute",
        "enum",
        "",
        "participant",
        "the disease's major stage group, one of I-IV",
    ),
    (
        "nsclc.extent",
        "disease_attribute",
        "enum_set",
        "",
        "participant",
        "the disease's extent words; several hold at once (recurrent and metastatic): a member set",
    ),
    (
        "nsclc.setting_word",
        "unresolved",
        "enum_set",
        "",
        "participant",
        "unresolved: a treatment-setting word speaks of a treatment's role (the study's or a prior one's); "
        "no predicate kind names a treatment role",
    ),
    (
        "nsclc.resection",
        "unresolved",
        "enum_set",
        "",
        "participant",
        "unresolved: resected is a procedure undergone (procedure_event), resectable an attribute of the "
        "disease (disease_attribute); one concept holds both",
    ),
    (
        "nsclc.organ_function_unspecified",
        "unresolved",
        "enum",
        "",
        "participant",
        'unresolved: "adequate organ function" with no threshold; the record leaves what is measured '
        "unspecified",
    ),
    (
        "nsclc.age",
        "demographic",
        "interval",
        "years",
        "participant",
        "age in years (the concept's definition); the bank keeps no comparator, so the boundaries' "
        "inclusivity is unspecified",
    ),
]
_ROWS += [
    (
        f"nsclc.biomarker.{slug(gene)}",
        "disease_attribute",
        "enum",
        "",
        "participant",
        f"the tumour's {gene} status, one of positive, negative or unknown",
    )
    for gene in GENES
]
_ROWS += [
    (f"nsclc.prior_agent.{slug(agent)}", "treatment_history", "boolean", "", "participant", _TREATMENT)
    for agent in AGENT_WORDS
]
_ROWS += [
    (
        f"nsclc.lab.{slug(analyte)}",
        "measurement",
        "quantity",
        UNIT_AS_WRITTEN,
        "participant",
        f"a {analyte} value against a threshold, the unit as written, never converted",
    )
    for analyte in ANALYTES
]
_ROWS += [(f"nsclc.condition.{slug(name)}", *row) for name, row in _CONDITIONS.items()]
_ROWS += [
    (
        f"nsclc.histology.{slug(name)}",
        "disease_attribute",
        "boolean",
        "",
        "participant",
        "a histology of the trial's own disease",
    )
    for name in HISTOLOGY
]

MAPPINGS: tuple[PredicateMapping, ...] = tuple(PredicateMapping(*row) for row in _ROWS)
MAPPING_BY_CONCEPT: dict[str, PredicateMapping] = {mapping.concept_id: mapping for mapping in MAPPINGS}
UNRESOLVED: tuple[str, ...] = tuple(
    mapping.concept_id for mapping in MAPPINGS if mapping.kind == "unresolved"
)


def _digest(mappings: tuple[PredicateMapping, ...]) -> str:
    """The SHA-256 of the mappings' canonical JSON in concept order: the same mappings, in any order, give the
    same version; any change to any field gives another."""
    ordered = sorted((asdict(mapping) for mapping in mappings), key=itemgetter("concept_id"))
    canonical = json.dumps(ordered, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


VERSION = _digest(MAPPINGS)


def mapping_problems(
    mappings: tuple[PredicateMapping, ...], families: dict[str, str], arguments: dict[str, tuple[str, ...]]
) -> tuple[tuple[str, str], ...]:
    """What makes a predicate mapping disagree with its concept registry or the vocabularies (pure — pinned).

    `families` is the registry's concept id → predicate family, `arguments` its concept id → the names of the
    arguments the concept declares (none when absent). Per mapping, in the order given, each as (code, concept
    id): duplicate_mapping (a concept mapped before; nothing more is checked of it); concept_of_no_registry;
    predicate_kind_outside_vocabulary; subject_kind_outside_vocabulary, or subject_without_referent
    (other_person: a referent is the text's, never a concept's); value_kind_outside_vocabulary, or
    value_kind_not_for_family (a value kind other than "unresolved" that FAMILY_VALUE_KINDS does not give the
    concept's family, an unknown family giving none); operand_not_declared (a registry concept whose value
    kind reads an operand, OPERANDS, that the concept does not declare as an argument, so no atom of it could
    carry one); unit_not_for_value_kind (a unit on a value kind other than quantity or interval). Then
    registry_concept_unmapped for each registry concept no mapping names, in concept order. No problem: an
    empty tuple."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for mapping in mappings:
        concept = mapping.concept_id
        if concept in seen:
            found.append(("duplicate_mapping", concept))
            continue
        seen.add(concept)
        if concept not in families:
            found.append(("concept_of_no_registry", concept))
        if mapping.kind not in PREDICATE_KINDS:
            found.append(("predicate_kind_outside_vocabulary", concept))
        if mapping.subject not in SUBJECT_KINDS:
            found.append(("subject_kind_outside_vocabulary", concept))
        elif mapping.subject == "other_person":
            found.append(("subject_without_referent", concept))
        if mapping.value_kind not in VALUE_KINDS:
            found.append(("value_kind_outside_vocabulary", concept))
        elif (
            concept in families
            and mapping.value_kind != "unresolved"
            and mapping.value_kind not in FAMILY_VALUE_KINDS.get(families[concept], frozenset())
        ):
            found.append(("value_kind_not_for_family", concept))
        declared = set(arguments.get(concept, ()))
        if concept in families and not set(OPERANDS.get(mapping.value_kind, ())) <= declared:
            found.append(("operand_not_declared", concept))
        if mapping.unit and mapping.value_kind not in ("quantity", "interval"):
            found.append(("unit_not_for_value_kind", concept))
    found += [("registry_concept_unmapped", concept) for concept in sorted(set(families) - seen)]
    return tuple(found)


def atom_literal(mapping: PredicateMapping | None, atom: Atom) -> tuple[str, Literal, tuple[str, ...]]:
    """The literal a mapped atom becomes, with its code and the params it leaves unread (pure — pinned).

    The literal states, of the mapping's subject, the predicate (the mapping's kind, keyed by the atom's
    concept id) with the value the atom's values or operand params give; polarity positive, no time, no
    qualifier, and the atom as its evidence (atom_ref). A value the concept's own name (a keyed concept's
    vocabulary entry, "hiv" of nsclc.condition.hiv) is not a member. boolean: the concept named, nothing more.
    enum: the atom's other values, "eq" one, "in" several; enum_set: "in" them. quantity: the comparator (≥ ≤
    > <), a plain decimal number and the unit (the atom's as written, or the mapping's own, which the atom may
    write but never replaces). interval: minimum and maximum, inclusivity unspecified (the atom keeps no
    comparator), the mapping's unit. Codes, the first that holds: concept_not_mapped (no mapping, or another
    concept's: subject and predicate unresolved, value unresolved); predicate_unresolved (the mapping's kind;
    the value as read); operand_not_kept (no member, no comparator or number, a bound missing: value
    unresolved); operand_not_read (a value beside a boolean concept's name, a comparator outside the four, a
    number not plain digits, reversed bounds, a unit written other than the mapping's own, a value kind with
    no reading here: value unresolved); mapped. Unread: each param name, once, in order, that is neither
    an operand of the value kind nor an annotation (text_polarity, modality: the compiler's, never read
    here). An atom without an id has no evidence: ModelError."""
    evidence = (Evidence("atom_ref", atom.atom_id),)
    params = dict(atom.params)
    if mapping is None or mapping.concept_id != atom.concept_id:
        unread = tuple(dict.fromkeys(name for name, _ in atom.params if name not in ANNOTATIONS))
        literal = Literal(
            Subject("unresolved"),
            Predicate("unresolved", atom.concept_id),
            Value("unresolved"),
            evidence=evidence,
        )
        return "concept_not_mapped", literal, unread
    operands = OPERANDS.get(mapping.value_kind, ())
    unread = tuple(dict.fromkeys(n for n, _ in atom.params if n not in ANNOTATIONS and n not in operands))
    own = atom.concept_id.rsplit(".", 1)[-1]
    members = tuple(value for value in atom.values if slug(value) != own)
    unit = params.get("unit", "") if mapping.unit == UNIT_AS_WRITTEN else mapping.unit
    # a unit the atom writes is never replaced: one other than the concept's own is another measurement
    unit_differs = mapping.unit != UNIT_AS_WRITTEN and params.get("unit", mapping.unit) != mapping.unit
    code, value = "mapped", Value("unresolved")
    if mapping.value_kind == "boolean":
        code, value = ("operand_not_read", value) if members else ("mapped", Value("boolean"))
    elif mapping.value_kind in ("enum", "enum_set"):
        comparison = "eq" if len(members) == 1 and mapping.value_kind == "enum" else "in"
        found = Value(mapping.value_kind, comparison, members) if members else value
        code, value = ("mapped", found) if members else ("operand_not_kept", value)
    elif mapping.value_kind == "quantity":
        comparator, number = params.get("comparator"), params.get("value")
        if comparator is None or number is None:
            code = "operand_not_kept"
        elif comparator not in COMPARISONS or not _NUMBER.fullmatch(number) or unit_differs:
            code = "operand_not_read"
        else:
            value = Value("quantity", COMPARISONS[comparator], number=float(number), unit=unit)
    elif mapping.value_kind == "interval":
        low, high = params.get("minimum"), params.get("maximum")
        if low is None or high is None:
            code = "operand_not_kept"
        elif (
            not (_NUMBER.fullmatch(low) and _NUMBER.fullmatch(high))
            or float(low) > float(high)
            or unit_differs
        ):
            code = "operand_not_read"
        else:
            value = Value("interval", "in", number=float(low), upper=float(high), unit=unit)
    else:
        code = "operand_not_read"
    literal = Literal(
        Subject(mapping.subject), Predicate(mapping.kind, atom.concept_id), value, evidence=evidence
    )
    return ("predicate_unresolved" if mapping.kind == "unresolved" else code), literal, unread


@dataclass(frozen=True)
class PredicateEntry:
    """A mapping with its provenance: the concept's authority, its fragment's rule exposure and the
    populations that exposure names."""

    mapping: PredicateMapping
    authority: str
    exposure: str
    populations: tuple[str, ...]


@dataclass(frozen=True)
class PredicateRegistry:
    version: str  # the mapping's digest (VERSION for MAPPINGS)
    concept_registry: str  # the version of the concept registry it agrees with
    entries: dict[str, PredicateEntry]


class PredicateError(ValueError):
    """A mapping that disagrees with its concept registry; its argument is mapping_problems' tuple."""


def predicate_registry(
    fragments: list[Fragment] | None = None, mappings: tuple[PredicateMapping, ...] = MAPPINGS
) -> PredicateRegistry:
    """The predicate registry: the mappings checked against the concept registry the fragments compile into
    (the fragments directory's by default), each entry with its provenance; PredicateError naming every
    problem when they disagree (a RegistryError when the fragments themselves do not compile)."""
    fragments = load_fragments() if fragments is None else fragments
    registry = compile_registry(fragments)
    families = {cid: entry.family for cid, entry in registry.concepts.items()}
    declared = {cid: tuple(name for name, _ in entry.arguments) for cid, entry in registry.concepts.items()}
    problems = mapping_problems(mappings, families, declared)
    if problems:
        raise PredicateError(problems)
    exposures = {fragment.name: fragment.exposure for fragment in fragments}
    entries = {}
    for mapping in mappings:
        exposure = exposures[registry.owners[mapping.concept_id]]
        authority = registry.concepts[mapping.concept_id].authority
        entries[mapping.concept_id] = PredicateEntry(mapping, authority, exposure, RULE_EXPOSURE[exposure][0])
    return PredicateRegistry(_digest(mappings), registry.version, entries)
