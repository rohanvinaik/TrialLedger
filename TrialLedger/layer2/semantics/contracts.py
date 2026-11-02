"""The bank contract (add-bank-coverage Decision 1): a bank recognizes; it never decides eligibility.

`recognize(text, version) -> BankResult(atoms, findings)`. An atom is
`(atom_id, owner_bank, concept_id, mention_kind, values, params, spans, rule_id)`: the registry concept it
mentions, the values the text allows (a sorted tuple), its parameters as written, and its evidence spans,
each half-open `[start, end)` on the original criterion text, with the role of the words it rests on
(concept, value, unit, comparator apart). Findings carry one of five codes; NO_TRIGGER is never evidence that
the criterion holds no relevant concept. Negation, attachment and applicability belong to the assertion layer
(add-scoped-assertions); `text_polarity` and `modality` stay candidate annotations in the params.

Today's atoms `(concept, values, params, start, end)` are extended, not replaced: `from_legacy` gives each a
contract atom whose only span is the legacy span (role `whole`: the legacy span does not hold its parts
apart, and no part is re-searched), and `to_legacy` gives the legacy atom back unchanged.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FINDING_CODES = ("IDENTIFIED", "AMBIGUOUS", "ABSTAINED", "NO_TRIGGER", "INVALID_INPUT")
FINDING_TEXT = {
    "IDENTIFIED": "the bank identified a concept and emitted its atom",
    "AMBIGUOUS": "the words admit more than one concept or reading; each kept as an alternative",
    "ABSTAINED": "the bank's trigger matched but it declines to read the words",
    "NO_TRIGGER": "nothing the bank recognizes; never evidence that the criterion holds no such concept",
    "INVALID_INPUT": "the input is not a criterion's text the bank can read",
}
# How the concept is mentioned: named only, a value or threshold stated, a state or category stated, a count
# stated, or a requirement whose content the text leaves unspecified ("adequate organ function").
MENTION_KINDS = ("named", "value_stated", "state_stated", "count_stated", "unspecified")
# The words a span rests on. `whole` is the legacy atom's one span, its parts not held apart.
SPAN_ROLES = ("concept", "value", "unit", "comparator", "qualifier", "window", "whole")
# Candidate annotations the assertion layer may override; allowed on every concept.
ANNOTATIONS = ("text_polarity", "modality")


@dataclass(frozen=True)
class Span:
    """The words one part of an atom rests on: `text[start:end]` of the original criterion."""

    role: str
    start: int
    end: int


@dataclass(frozen=True)
class Atom:
    atom_id: str
    owner_bank: str
    concept_id: str
    mention_kind: str
    values: tuple[str, ...]
    params: tuple[tuple[str, str], ...]
    spans: tuple[Span, ...]
    rule_id: str
    legacy_concept: str | None = None  # today's concept name, kept so the legacy atom is given back unchanged


@dataclass(frozen=True)
class Finding:
    code: str
    owner_bank: str
    concept_id: str | None
    span: Span | None
    note: str


@dataclass(frozen=True)
class BankResult:
    atoms: tuple[Atom, ...]
    findings: tuple[Finding, ...]


def atom_digest(
    owner_bank: str,
    concept_id: str,
    values: tuple[str, ...],
    params: tuple[tuple[str, str], ...],
    spans: tuple[Span, ...],
    rule_id: str,
) -> str:
    """An atom's identity: the first 16 hex digits of the SHA-256 of its content as canonical JSON
    (pure — pinned). The same bank, concept, values, params, spans and rule give the same id on every run and
    machine; any difference in any of them gives another."""
    content: list[object] = [owner_bank, concept_id, list(values), [list(p) for p in params]]
    content += [[[s.role, s.start, s.end] for s in spans], rule_id]
    canonical = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _span_problems(span: Span, text: str) -> list[str]:
    if span.role not in SPAN_ROLES:
        return ["unknown_span_role"]
    if not 0 <= span.start < span.end <= len(text):
        return ["span_out_of_bounds"]
    return []


def atom_problems(atom: Atom, text: str) -> tuple[str, ...]:
    """What makes an atom break the contract against the criterion text it was read from (pure — pinned).

    Each problem once, in this order: empty_owner, empty_concept, empty_rule; unknown_mention_kind;
    no_evidence (no span); unknown_span_role, span_out_of_bounds (a span not half-open and non-empty within
    the text: 0 <= start < end <= len(text)); duplicate_values (the values are a set); unsorted_values;
    duplicate_param (a parameter name twice); wrong_atom_id (the id is not the digest of its content). No
    problem: an empty tuple.
    """
    found: list[str] = []
    if not atom.owner_bank:
        found.append("empty_owner")
    if not atom.concept_id:
        found.append("empty_concept")
    if not atom.rule_id:
        found.append("empty_rule")
    if atom.mention_kind not in MENTION_KINDS:
        found.append("unknown_mention_kind")
    if not atom.spans:
        found.append("no_evidence")
    for span in atom.spans:
        found.extend(_span_problems(span, text))
    if len(set(atom.values)) != len(atom.values):
        found.append("duplicate_values")
    if list(atom.values) != sorted(atom.values):
        found.append("unsorted_values")
    names = [name for name, _ in atom.params]
    if len(set(names)) != len(names):
        found.append("duplicate_param")
    digest = atom_digest(atom.owner_bank, atom.concept_id, atom.values, atom.params, atom.spans, atom.rule_id)
    if atom.atom_id != digest:
        found.append("wrong_atom_id")
    return tuple(dict.fromkeys(found))


def result_problems(result: BankResult, text: str) -> tuple[str, ...]:
    """What makes a bank's result break the contract (pure — pinned).

    Every atom's own problems (atom_problems); unknown_finding_code; a finding span's problems; no_finding (a
    result must say something: at least one finding); atom_without_identified (each atom has an IDENTIFIED or
    AMBIGUOUS finding of its concept); atoms_with_no_trigger and atoms_with_invalid_input (a bank that emitted
    atoms cannot also say nothing triggered or that its input was invalid). Each problem once, in order of
    first finding. No problem: an empty tuple.
    """
    found: list[str] = []
    for atom in result.atoms:
        found.extend(atom_problems(atom, text))
    codes = {finding.code for finding in result.findings}
    for finding in result.findings:
        if finding.code not in FINDING_CODES:
            found.append("unknown_finding_code")
        if finding.span is not None:
            found.extend(_span_problems(finding.span, text))
    if not result.findings:
        found.append("no_finding")
    said = {(f.owner_bank, f.concept_id) for f in result.findings if f.code in ("IDENTIFIED", "AMBIGUOUS")}
    if any((atom.owner_bank, atom.concept_id) not in said for atom in result.atoms):
        found.append("atom_without_identified")
    if result.atoms and "NO_TRIGGER" in codes:
        found.append("atoms_with_no_trigger")
    if result.atoms and "INVALID_INPUT" in codes:
        found.append("atoms_with_invalid_input")
    return tuple(dict.fromkeys(found))


# ── the adapter from today's atoms ───────────────────────────────────────────────────────────────────

LEGACY_NAMESPACE = "nsclc"
# Legacy concepts whose first value names the concept itself (the vocabulary entry the bank matched).
LEGACY_KEYED = ("condition", "lab", "prior_agent", "histology")
LEGACY_MENTION_KIND = {
    "ecog_ps": "value_stated",
    "biomarker": "state_stated",
    "prior_lines": "count_stated",
    "prior_agent": "named",
    "stage": "state_stated",
    "extent": "state_stated",
    "setting_word": "named",
    "resection": "state_stated",
    "lab": "value_stated",
    "organ_function_unspecified": "unspecified",
    "condition": "named",
    "age": "value_stated",
    "histology": "named",
}


def slug(word: str) -> str:
    """A vocabulary word as a concept-id segment: lower case, each run of other characters one "_"
    (pure — pinned). "PD-L1" is "pd_l1", "creatinine clearance" is "creatinine_clearance", "AST" is "ast"."""
    out: list[str] = []
    for char in word.lower():
        if char.isascii() and char.isalnum():
            out.append(char)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")


def legacy_concept_id(concept: str, values: tuple[str, ...]) -> str:
    """The registry concept a legacy atom mentions (pure — pinned).

    "biomarker:EGFR" is nsclc.biomarker.egfr; a keyed concept (condition, lab, prior_agent, histology) is
    named by its first value, nsclc.condition.hiv, nsclc.lab.creatinine_clearance; any other concept is
    nsclc.<concept> (nsclc.ecog_ps, nsclc.stage). A keyed concept with no value, or an empty concept: "" (no
    concept, which the contract refuses)."""
    if not concept:
        return ""
    if concept.startswith("biomarker:"):
        return f"{LEGACY_NAMESPACE}.biomarker.{slug(concept.removeprefix('biomarker:'))}"
    if concept in LEGACY_KEYED:
        return f"{LEGACY_NAMESPACE}.{concept}.{slug(values[0])}" if values else ""
    return f"{LEGACY_NAMESPACE}.{concept}"


def from_legacy(
    bank: str,
    atom: tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], int, int],
) -> Atom:
    """A legacy atom `(concept, values, params, start, end)` of one bank as a contract atom (pure — pinned).

    Its concept id from legacy_concept_id; its mention kind from LEGACY_MENTION_KIND by the concept's family
    name ("biomarker:EGFR" is a biomarker), "named" for a concept not in the table; values and params exactly
    as given; one span, role `whole`, the legacy span; rule id "banks.<bank>"; the legacy concept kept, so
    to_legacy gives the atom back unchanged."""
    concept, values, params, start, end = atom
    spans = (Span("whole", start, end),)
    concept_id = legacy_concept_id(concept, values)
    rule_id = f"banks.{bank}"
    kind = LEGACY_MENTION_KIND.get(concept.split(":")[0], "named")
    digest = atom_digest(bank, concept_id, values, params, spans, rule_id)
    return Atom(digest, bank, concept_id, kind, values, params, spans, rule_id, concept)


def to_legacy(atom: Atom) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], int, int]:
    """The legacy atom a contract atom carries: its legacy concept, values, params and the first span's
    offsets (pure — pinned). An atom with no legacy concept or no span has none: ValueError, never a guess."""
    if atom.legacy_concept is None or not atom.spans:
        raise ValueError(f"atom {atom.atom_id} carries no legacy atom")
    return (atom.legacy_concept, atom.values, atom.params, atom.spans[0].start, atom.spans[0].end)


def legacy_result(
    bank: str,
    text: str,
    atoms: list[tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], int, int]],
) -> BankResult:
    """A legacy bank's answer for one criterion as a contract result (pure — pinned).

    Blank text (empty or whitespace only): INVALID_INPUT, whatever atoms are given (a bank gives none for
    it). Atoms: each a contract atom (from_legacy) with an IDENTIFIED finding of its concept over its span.
    No atom: one NO_TRIGGER finding (a legacy bank cannot tell "nothing here" from "declined to read", and
    NO_TRIGGER claims neither); never ABSTAINED, never an absence."""
    if not text.strip():
        return BankResult((), (Finding("INVALID_INPUT", bank, None, None, "blank criterion text"),))
    converted = tuple(from_legacy(bank, atom) for atom in atoms)
    if not converted:
        return BankResult((), (Finding("NO_TRIGGER", bank, None, None, FINDING_TEXT["NO_TRIGGER"]),))
    findings = tuple(
        Finding("IDENTIFIED", bank, atom.concept_id, atom.spans[0], atom.atom_id) for atom in converted
    )
    return BankResult(converted, findings)
