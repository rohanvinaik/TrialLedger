"""Coherence: coordinate domains narrowed by explicitly supplied typed premises and declared relations.

A domain starts as every value a coordinate can take. A premise narrows it only where its typed content
states the coordinate's value; silence never narrows. This engine does not read clinical prose or establish
the truth or applicability of its inputs. Callers retain each premise's source, identity and scope.

Relations have a kind apart from approval and basis: strict (entailed by positive premises and explicit
definitions), default (assumed until overruled), or proposal (shown separately, never built on). The current
stored NSCLC relations are defaults or proposals. Known domains use supplied evidence and strict relations;
interpolated domains also use defaults and strict consequences of those defaults. Each proposal is applied
separately to the interpolated domain, never cumulatively.

Closure intersects domains to a fixed point independently of relation order. An empty domain is a named
conflict with the causes that removed its values; nothing is selected by agreement or vote. Duplicate
representations do not establish independent support. Consumers declare the statuses they accept through
accepted_value; proposals remain separate from accepted conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from TrialLedger.layer2 import universes
from TrialLedger.layer2.reasoning_explanations import relation_application_code

SETTINGS = (
    "neoadjuvant",
    "adjuvant",
    "perioperative",
    "definitive_chemoradiation",
    "consolidation_after_chemoradiation",
    "advanced_first_line",
    "advanced_previously_treated",
    "maintenance",
    "local_consolidative_therapy",
)
PRIOR_LINES = ("0", "1", "2", "3+")
STATES = ("negative", "positive", "unknown")
SELECTED_GENES = ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2")
COORDINATES: dict[str, tuple[str, ...]] = {
    "setting": SETTINGS,
    "prior_advanced_lines": PRIOR_LINES,
    **{f"selection:{gene}": STATES for gene in SELECTED_GENES},
}
ADVANCED = (
    "advanced_first_line",
    "advanced_previously_treated",
    "maintenance",
    "local_consolidative_therapy",
)
# Facts that place a trial's treatment around surgery or radiation, which the advanced relations must not
# override (Codex's counterexamples, 2026-10-31: neoadjuvant stage III; resected oligometastatic disease).
PERIOPERATIVE_FACTS = (
    "inclusion:resection:resected",
    "inclusion:resection:resectable",
    "inclusion:setting_word:neoadjuvant",
    "inclusion:setting_word:adjuvant",
    "inclusion:setting_word:perioperative",
)
ADVANCED_FACTS = (
    "inclusion:extent:metastatic",
    "inclusion:stage:IV",
    "inclusion:extent:recurrent",
    "inclusion:extent:advanced",
)


KINDS = ("strict", "default", "proposal")
# The statuses a reported value can rest on, strongest first (Decision 1).
STATUSES = ("known", "interpolated", "proposed")


@dataclass(frozen=True)
class Relation:
    id: str
    statement: str
    basis: str
    approval: str  # "approved" or "proposed": metadata, never the relation's kind
    kind: str  # one of KINDS: what its conclusion is (known, interpolated or proposed)
    needs: tuple[str, ...]  # facts all required ("inclusion:resection:resected")
    lines_within: tuple[str, ...]  # when non-empty, prior_advanced_lines must lie within these values
    narrows: str
    allowed: tuple[str, ...]
    needs_any: tuple[str, ...] = ()  # when non-empty, at least one of these facts is required
    forbids: tuple[str, ...] = ()  # none of these facts may hold


# Four relations were approved by the founder's instruction of 2026-10-31 (paraphrased: promote the relations
# that are common-sense domain priors, unambiguous read literally and logically), each after its guards
# answered the counterexamples of a Codex reading that day. Approved is not strict (add-scoped-reasoning,
# Decision 8): each of the four excludes a qualifying design (a locoregional recurrence treated with
# chemoradiation; local consolidation after prior systemic therapy; palliative radiotherapy in stage IV
# disease; a treatment-naive trial randomising at maintenance; Codex's counterexamples, which Claude holds
# valid), so each is a default: its conclusion is interpolated, never known, until the scoped premises of task
# 3 and the split setting of task 4 give strict relations. The other three are proposals, shown one at a
# time and never built on. No relation is strict yet. Approval stays as it was given, by id.
RELATIONS = (
    Relation(
        "first_line_when_no_prior_advanced_therapy",
        "A trial of advanced disease (metastatic, stage IV, recurrent or advanced, not locally "
        "advanced alone) that requires no prior systemic therapy for advanced disease, and plans no "
        "surgery around its treatment, is a first-line advanced trial.",
        "definition of line of therapy",
        "approved",
        "default",
        (),
        ("0",),
        "setting",
        ("advanced_first_line",),
        needs_any=ADVANCED_FACTS,
        forbids=PERIOPERATIVE_FACTS,
    ),
    Relation(
        "previously_treated_when_prior_advanced_therapy_required",
        "A trial requiring at least one prior line for advanced disease, other than chemoradiation, is a "
        "previously treated or maintenance advanced trial.",
        "definition of line of therapy; maintenance follows first-line induction",
        "approved",
        "default",
        (),
        ("1", "2", "3+"),
        "setting",
        ("advanced_previously_treated", "maintenance"),
        forbids=("inclusion:prior_agent:radiotherapy", "inclusion:setting_word:consolidation"),
    ),
    Relation(
        "adjuvant_or_perioperative_when_resection_required",
        "A trial requiring a completed resection of the lung tumour treats in the adjuvant or "
        "perioperative setting.",
        "the meaning of adjuvant therapy; ambiguous: advanced trials admit recurrence after resection",
        "proposed",
        "proposal",
        ("inclusion:resection:resected",),
        (),
        "setting",
        ("adjuvant", "perioperative"),
    ),
    Relation(
        "neoadjuvant_or_perioperative_when_resectable_required",
        "A trial requiring resectable disease treats before surgery, in the neoadjuvant or "
        "perioperative setting.",
        "the meaning of neoadjuvant therapy; ambiguous: resectability is feasibility, not planned treatment",
        "proposed",
        "proposal",
        ("inclusion:resection:resectable",),
        (),
        "setting",
        ("neoadjuvant", "perioperative"),
    ),
    Relation(
        "advanced_when_metastatic_disease_required",
        "A trial requiring metastatic disease, with no resection or perioperative treatment, treats in an "
        "advanced setting.",
        "staging (AJCC 8th edition: stage IV is metastatic)",
        "approved",
        "default",
        ("inclusion:extent:metastatic",),
        (),
        "setting",
        ADVANCED,
        forbids=PERIOPERATIVE_FACTS,
    ),
    Relation(
        "advanced_when_stage_iv_required",
        "A trial whose inclusion admits stage IV and no earlier stage, with no resection or perioperative "
        "treatment, treats in an advanced setting.",
        "staging (AJCC 8th edition)",
        "approved",
        "default",
        ("inclusion:stage:IV",),
        (),
        "setting",
        ADVANCED,
        forbids=(*PERIOPERATIVE_FACTS, "inclusion:stage:I", "inclusion:stage:II", "inclusion:stage:III"),
    ),
    Relation(
        "consolidation_when_named",
        "A trial whose inclusion criteria name consolidation gives consolidation, after chemoradiation or "
        "local consolidative therapy of metastatic disease.",
        "the trial's own words; ambiguous: a criterion may name earlier consolidation",
        "proposed",
        "proposal",
        ("inclusion:setting_word:consolidation",),
        (),
        "setting",
        ("consolidation_after_chemoradiation", "local_consolidative_therapy"),
    ),
)


def direct_coordinate(concept: str, scope: str) -> str:
    """Return the exact finite coordinate consumer; an unmatched concept has no direct consumer.

    post: __return__ == '' or __return__ in COORDINATES
    post: concept != 'setting' or __return__ == 'setting'
    post: concept != 'prior_lines' or ((__return__ == 'prior_advanced_lines') == (scope == 'advanced'))
    """
    if concept == "prior_lines":
        return "prior_advanced_lines" if scope == "advanced" else ""
    return {
        "setting": "setting",
        **{f"biomarker:{gene}": f"selection:{gene}" for gene in SELECTED_GENES},
    }.get(concept, "")


def relation_applicability(relation: Relation, facts: list[str], domains: dict[str, tuple[str, ...]]) -> dict:
    """The actual closure guard, including exact positive and veto facts and the line-domain test."""
    missing = [fact for fact in relation.needs if fact not in facts]
    alternatives = [fact for fact in relation.needs_any if fact in facts]
    forbidden = [fact for fact in relation.forbids if fact in facts]
    lines = domains["prior_advanced_lines"]
    lines_fit = not relation.lines_within or bool(lines and set(lines) <= set(relation.lines_within))
    return {
        "code": relation_application_code(
            bool(missing), bool(relation.needs_any and not alternatives), lines_fit, bool(forbidden)
        ),
        "missing_required": missing,
        "matched_required": [fact for fact in relation.needs if fact in facts],
        "matched_alternatives": alternatives,
        "required_alternatives": list(relation.needs_any),
        "matched_forbidden": forbidden,
        "prior_advanced_lines": list(lines),
        "lines_within": list(relation.lines_within),
        "lines_fit": lines_fit,
    }


def narrow_by_evidence(
    evidence: list[tuple[str, str, tuple[str, ...], str, str]],
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, tuple[str, ...], str]]]:
    """The domains a trial's typed evidence leaves, and each removal's cause (pure — pinned).

    `evidence` holds (section, concept, values, scope, ref): an atom's criterion section, its concept, the
    values it states, its scope ("advanced", "unspecified" or "") and a reference naming its criterion. Only a
    stated coordinate narrows: prior_lines of advanced scope narrows prior_advanced_lines, and a biomarker's
    states narrow its gene's selection; an explicit setting restriction narrows setting. An inclusion atom
    keeps its values; an exclusion atom removes them; an
    unsectioned atom, an atom of unspecified scope or one with no values narrows nothing. Returns the domains
    (every coordinate, in COORDINATES order, each a tuple in its coordinate's order) and the causes, each
    (coordinate, values removed, ref), only where a value was removed.
    """
    domains = {name: values for name, values in COORDINATES.items()}
    causes: list[tuple[str, tuple[str, ...], str]] = []
    for section, concept, values, scope, ref in evidence:
        coordinate = direct_coordinate(concept, scope)
        if not coordinate:
            continue
        if section not in ("inclusion", "exclusion") or not values:
            continue
        current = domains[coordinate]
        kept = tuple(v for v in current if (v in values) == (section == "inclusion"))
        removed = tuple(v for v in current if v not in kept)
        if removed:
            domains[coordinate] = kept
            causes.append((coordinate, removed, ref))
    return domains, causes


def close(
    domains: dict[str, tuple[str, ...]],
    facts: list[str],
    relation_ids: list[str],
    relations: tuple[Relation, ...] = RELATIONS,
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, tuple[str, ...], str]]]:
    """Apply the named relations to a fixed point (pure — pinned).

    The ids name relations of `relations` (RELATIONS unless a caller declares another table). A relation
    applies when every fact it needs is among `facts`, at least one of its needs_any facts is (when it names
    any), none of its forbids facts is, and, if it names prior lines, the prior_advanced_lines domain is
    non-empty and lies within them; it then keeps only its allowed values of the coordinate it narrows.
    Intersection is monotone, so the fixed point does not depend on the order of `relation_ids`; and as each
    changing pass removes a value, closure ends within (number of values + 1) passes, a bound declared in the
    loop. Returns the closed domains and the causes, each (coordinate, values removed, relation id). A
    relation's kind is not read here: which relations close a domain is the caller's (resolve's) decision.
    An unknown relation id raises KeyError: a relation that does not exist cannot be applied.
    """
    table = {relation.id: relation for relation in relations}
    chosen = [table[relation_id] for relation_id in relation_ids]
    current = dict(domains)
    causes: list[tuple[str, tuple[str, ...], str]] = []
    # Declared bound: every pass that changes anything removes at least one value, so no more passes than
    # there are values, plus the pass that finds nothing to remove, can occur.
    for _ in range(sum(len(values) for values in current.values()) + 1):
        changed = False
        for relation in chosen:
            if relation_applicability(relation, facts, current)["code"] != "applicable":
                continue
            kept = tuple(v for v in current[relation.narrows] if v in relation.allowed)
            removed = tuple(v for v in current[relation.narrows] if v not in kept)
            if removed:
                current[relation.narrows] = kept
                causes.append((relation.narrows, removed, relation.id))
                changed = True
        if not changed:
            break
    return current, causes


def domain_state(domain: tuple[str, ...], full: tuple[str, ...]) -> str:
    """resolved (one value), conflict (none), unresolved (several, narrowed or not) (pure — pinned)."""
    if not domain:
        return "conflict"
    if len(domain) == 1:
        return "resolved"
    return "unnarrowed" if len(domain) == len(full) else "unresolved"


def facts_of(evidence: list[tuple[str, str, tuple[str, ...], str, str]]) -> list[str]:
    """The trial's typed facts, "section:concept:value", in the order first seen, each once."""
    seen: dict[str, None] = {}
    for section, concept, values, _scope, _ref in evidence:
        for value in values:
            seen.setdefault(f"{section}:{concept}:{value}", None)
    return list(seen)


def resolve(
    evidence: list[tuple[str, str, tuple[str, ...], str, str]],
    assignment: Any = None,
    *,
    relations: tuple[Relation, ...] = RELATIONS,
) -> dict[str, dict]:
    """The coordinates of one trial its universes permit, at each status: known, interpolated and each
    proposal on its own (pure — pinned).

    `evidence` is narrow_by_evidence's. `assignment` is the trial's universes.Assignment: only the coordinates
    and relations of its permitted packs (its `packs`) are computed, each coordinate's row naming the packs
    that own it ("packs"); a coordinate no permitted pack owns is absent, so a general or unresolved trial has
    none. With no assignment, every coordinate and relation applies, as for a solid-tumour treatment trial,
    and no row names its packs. `relations` is the table of relations (RELATIONS unless a caller declares
    another), each applied by its kind, never by its approval:
      known        — the stated evidence (narrow_by_evidence), closed under the strict relations;
      interpolated — the known domains closed under the strict and default relations together (a strict rule
                     applied to a default's conclusion yields an interpolated value);
      proposals    — each proposal relation alone, in table order, closing the interpolated domains: one at a
                     time, never cumulative, and never consumed by another level.
    Returns, for every coordinate of COORDINATES, in order, {"domain", "state", "causes"} for the known level,
    "interpolated": {"domain", "state", "causes"}, and "proposals": [{"relation", "domain", "state",
    "causes"}] for each proposal that narrows that coordinate. Each level's causes are the removals made at
    that level, each (coordinate, values removed, the criterion or relation): the known level's by evidence
    and strict relations, the interpolated level's beyond the known, a proposal's beyond the interpolated.
    A relation whose kind is not one of KINDS raises ValueError: a relation of no kind is applied at no level.
    """
    unknown = [relation.id for relation in relations if relation.kind not in KINDS]
    if unknown:
        raise ValueError(f"relations of no kind: {unknown}")
    owners: dict[str, list[str]] = {}
    if assignment is not None:
        owners, owned = universes.pack_scope(tuple(assignment.packs))
        relations = tuple(relation for relation in relations if relation.id in owned)
    stated, stated_causes = narrow_by_evidence(evidence)
    facts = facts_of(evidence)
    ids = {kind: [r.id for r in relations if r.kind == kind] for kind in KINDS}
    known, strict_causes = close(stated, facts, ids["strict"], relations)
    interpolated, default_causes = close(known, facts, ids["strict"] + ids["default"], relations)
    proposals = [(rid, *close(interpolated, facts, [rid], relations)) for rid in ids["proposal"]]
    result = {}
    for name, full in COORDINATES.items():
        result[name] = {
            "domain": known[name],
            "state": domain_state(known[name], full),
            "causes": [c for c in stated_causes + strict_causes if c[0] == name],
            "interpolated": {
                "domain": interpolated[name],
                "state": domain_state(interpolated[name], full),
                "causes": [c for c in default_causes if c[0] == name],
            },
            "proposals": [
                {
                    "relation": rid,
                    "domain": closed[name],
                    "state": domain_state(closed[name], full),
                    "causes": [c for c in causes if c[0] == name],
                }
                for rid, closed, causes in proposals
                if closed[name] != interpolated[name]
            ],
        }
    if assignment is None:
        return result
    return {name: {**row, "packs": owners[name]} for name, row in result.items() if name in owners}


def level_status(level: str, domain: tuple[str, ...], known: tuple[str, ...]) -> str:
    """The status a coordinate's domain carries at its level, as a reader is told it (pure — pinned).

    `domain` is resolve's domain at `level`, `known` the coordinate's known domain.
      known        — "known" when one value remains, "unresolved" when several or none (a conflict);
      interpolated — the known level's status when the defaults leave the known domain as it is; otherwise
                     "interpolated" when they leave one or more values, "unresolved" when none;
      proposed     — "proposed" when the proposal leaves one or more values, "unresolved" when none.
    Any other level raises ValueError: a level that is not one of the three has no status.
    """
    if level == "known" or (level == "interpolated" and tuple(domain) == tuple(known)):
        return "known" if len(known) == 1 else "unresolved"
    if level in ("interpolated", "proposed"):
        return level if domain else "unresolved"
    raise ValueError(f"no status for the level {level!r}")


def accepted_value(row: dict[str, Any], accepts: tuple[str, ...]) -> tuple[str, str]:
    """The one value of a coordinate a consumer may build on, and the status it rests on (pure — pinned).

    `row` is resolve's for the coordinate; `accepts` the statuses the consumer declares (Decision 7):
    ("known",) for the strata, expectation cells, occupancy and results grouping; ("known", "interpolated")
    for near misses.
      (value, "known")        — the known domain is one value, whatever else is accepted (a value with a known
                                and an interpolated derivation is known);
      (value, "interpolated") — interpolated is accepted and the interpolated domain is one value;
      ("", "")                — otherwise: several values or none (a conflict) at every accepted status.
    A proposal is never built on: `accepts` naming "proposed" or anything but known and interpolated, or not
    naming "known", raises ValueError.
    """
    if "known" not in accepts or not set(accepts) <= {"known", "interpolated"}:
        raise ValueError(f"a consumer accepts known, and interpolated at most, never {list(accepts)}")
    if len(row["domain"]) == 1:
        return row["domain"][0], "known"
    held = row["interpolated"]["domain"] if "interpolated" in accepts else ()
    return (held[0], "interpolated") if len(held) == 1 else ("", "")


def weakest(statuses: list[str]) -> str:
    """The weakest status a value derived from others rests on (pure — pinned).

    Statuses rank as STATUSES: known, then interpolated, then proposed; the result is the lowest-ranked of
    `statuses` (a near-miss pair of a known and an interpolated representation rests on an interpolated one).
    No status, or one outside STATUSES, raises ValueError: a value resting on nothing named has no status.
    """
    if not statuses or any(status not in STATUSES for status in statuses):
        raise ValueError(f"no status to weigh among {list(statuses)}")
    return max(statuses, key=STATUSES.index)
