"""Coherence: each trial's design coordinates as domains of still-possible values.

A domain starts as every value a coordinate can take. Evidence narrows it only where a typed atom states the
coordinate's value (an inclusion criterion keeps the values it allows; an exclusion criterion removes the
values it excludes); silence never narrows. Relations carry inference between coordinates and the trial's
typed facts; every relation is proposed until the founder approves it by id (law 13), so the reported domains
are those under approved relations, and the narrowing proposed relations would add is shown beside them.
Closure intersects domains to a fixed point, so its result does not depend on the order relations are listed
in. A domain emptied is a conflict, named with every cause that removed a value; nothing is chosen or voted.
Two atoms from one criterion are one piece of evidence; agreement never assigns, only elimination does.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class Relation:
    id: str
    statement: str
    basis: str
    approval: str  # "approved" or "proposed"
    needs: tuple[str, ...]  # facts all required ("inclusion:resection:resected")
    lines_within: tuple[str, ...]  # when non-empty, prior_advanced_lines must lie within these values
    narrows: str
    allowed: tuple[str, ...]
    needs_any: tuple[str, ...] = ()  # when non-empty, at least one of these facts is required
    forbids: tuple[str, ...] = ()  # none of these facts may hold


# Relations approved by the founder's instruction of 2026-10-31 (paraphrased: promote the relations that are
# common-sense domain priors, unambiguous read literally and logically), each after its guards answered the
# counterexamples of a Codex reading that day; the rest stay proposed, shown and never applied to a reported
# value. Approval is by id and reversible by changing one word.
RELATIONS = (
    Relation(
        "first_line_when_no_prior_advanced_therapy",
        "A trial of advanced disease (metastatic, stage IV, recurrent or advanced, not locally "
        "advanced alone) that requires no prior systemic therapy for advanced disease, and plans no "
        "surgery around its treatment, is a first-line advanced trial.",
        "definition of line of therapy",
        "approved",
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
        ("inclusion:setting_word:consolidation",),
        (),
        "setting",
        ("consolidation_after_chemoradiation", "local_consolidative_therapy"),
    ),
)


def narrow_by_evidence(
    evidence: list[tuple[str, str, tuple[str, ...], str, str]],
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, tuple[str, ...], str]]]:
    """The domains a trial's typed evidence leaves, and each removal's cause (pure — pinned).

    `evidence` holds (section, concept, values, scope, ref): an atom's criterion section, its concept, the
    values it states, its scope ("advanced", "unspecified" or "") and a reference naming its criterion. Only a
    stated coordinate narrows: prior_lines of advanced scope narrows prior_advanced_lines, and a biomarker's
    states narrow its gene's selection. An inclusion atom keeps its values; an exclusion atom removes them; an
    unsectioned atom, an atom of unspecified scope or one with no values narrows nothing. Returns the domains
    (every coordinate, in COORDINATES order, each a tuple in its coordinate's order) and the causes, each
    (coordinate, values removed, ref), only where a value was removed.
    """
    domains = {name: values for name, values in COORDINATES.items()}
    causes: list[tuple[str, tuple[str, ...], str]] = []
    for section, concept, values, scope, ref in evidence:
        if concept == "prior_lines" and scope == "advanced":
            coordinate = "prior_advanced_lines"
        elif concept.startswith("biomarker:") and f"selection:{concept[10:]}" in domains:
            coordinate = f"selection:{concept[10:]}"
        else:
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
    domains: dict[str, tuple[str, ...]], facts: list[str], relation_ids: list[str]
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, tuple[str, ...], str]]]:
    """Apply the named relations to a fixed point (pure — pinned).

    A relation applies when every fact it needs is among `facts`, at least one of its needs_any facts is
    (when it names any), none of its forbids facts is, and, if it names prior lines, the
    prior_advanced_lines domain is non-empty and lies within them; it then keeps only its allowed values of
    the coordinate it narrows. Intersection is monotone, so the fixed point does not depend on the order of
    `relation_ids`; and as each changing pass removes a value, closure ends within (number of values + 1)
    passes, a bound declared in the loop. Returns the closed domains and the causes, each (coordinate,
    values removed, relation id).
    An unknown relation id raises KeyError: a relation that does not exist cannot be applied.
    """
    table = {relation.id: relation for relation in RELATIONS}
    chosen = [table[relation_id] for relation_id in relation_ids]
    current = dict(domains)
    causes: list[tuple[str, tuple[str, ...], str]] = []
    # Declared bound: every pass that changes anything removes at least one value, so no more passes than
    # there are values, plus the pass that finds nothing to remove, can occur.
    for _ in range(sum(len(values) for values in current.values()) + 1):
        changed = False
        for relation in chosen:
            lines = current["prior_advanced_lines"]
            if any(fact not in facts for fact in relation.needs):
                continue
            if relation.needs_any and not any(fact in facts for fact in relation.needs_any):
                continue
            if any(fact in facts for fact in relation.forbids):
                continue
            if relation.lines_within and not (lines and set(lines) <= set(relation.lines_within)):
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


def resolve(evidence: list[tuple[str, str, tuple[str, ...], str, str]]) -> dict[str, dict]:
    """Every coordinate of one trial: its domain under approved relations, its domain with proposed relations
    added, each one's state, and the causes of every removal."""
    stated, stated_causes = narrow_by_evidence(evidence)
    facts = facts_of(evidence)
    approved_ids = [r.id for r in RELATIONS if r.approval == "approved"]
    approved, approved_causes = close(stated, facts, approved_ids)
    proposed, proposed_causes = close(approved, facts, [r.id for r in RELATIONS if r.approval == "proposed"])
    result = {}
    for name, full in COORDINATES.items():
        result[name] = {
            "domain": approved[name],
            "state": domain_state(approved[name], full),
            "with_proposed": proposed[name],
            "proposed_state": domain_state(proposed[name], full),
            "causes": [c for c in stated_causes + approved_causes if c[0] == name],
            "proposed_causes": [c for c in proposed_causes if c[0] == name],
        }
    return result
