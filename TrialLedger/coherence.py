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
    "consolidation",
    "advanced_first_line",
    "advanced_previously_treated",
    "maintenance",
)
PRIOR_LINES = ("0", "1", "2", "3+")
STATES = ("negative", "positive", "unknown")
SELECTED_GENES = ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2")
COORDINATES: dict[str, tuple[str, ...]] = {
    "setting": SETTINGS,
    "prior_advanced_lines": PRIOR_LINES,
    **{f"selection:{gene}": STATES for gene in SELECTED_GENES},
}
EARLY = ("neoadjuvant", "adjuvant", "perioperative", "consolidation")
ADVANCED = ("advanced_first_line", "advanced_previously_treated", "maintenance")


@dataclass(frozen=True)
class Relation:
    id: str
    statement: str
    basis: str
    approval: str  # "approved" or "proposed"
    needs: tuple[str, ...]  # facts all required ("inclusion:resection:resected"), or a domain test (below)
    lines_within: tuple[str, ...]  # when non-empty, prior_advanced_lines must lie within these values
    narrows: str
    allowed: tuple[str, ...]


# Every relation is proposed: none is the registry's stated rule; each is the reading of what a trial's own
# criteria entail, for the founder to approve or reject by id.
RELATIONS = (
    Relation(
        "first_line_when_no_prior_advanced_therapy",
        "A trial requiring no prior systemic therapy for advanced disease is a first-line advanced trial.",
        "definition of line of therapy",
        "proposed",
        (),
        ("0",),
        "setting",
        ("advanced_first_line",),
    ),
    Relation(
        "previously_treated_when_prior_advanced_therapy_required",
        "A trial requiring at least one prior line for advanced disease is a previously treated "
        "advanced trial.",
        "definition of line of therapy",
        "proposed",
        (),
        ("1", "2", "3+"),
        "setting",
        ("advanced_previously_treated",),
    ),
    Relation(
        "adjuvant_or_perioperative_when_resection_required",
        "A trial requiring a completed resection of the lung tumour treats in the adjuvant or "
        "perioperative setting.",
        "the meaning of adjuvant therapy",
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
        "the meaning of neoadjuvant therapy",
        "proposed",
        ("inclusion:resection:resectable",),
        (),
        "setting",
        ("neoadjuvant", "perioperative"),
    ),
    Relation(
        "advanced_when_metastatic_disease_required",
        "A trial requiring metastatic or stage IV disease treats in an advanced setting.",
        "staging (AJCC 8th edition: stage IV is metastatic)",
        "proposed",
        ("inclusion:extent:metastatic",),
        (),
        "setting",
        ADVANCED,
    ),
    Relation(
        "advanced_when_stage_iv_required",
        "A trial requiring stage IV disease treats in an advanced setting.",
        "staging (AJCC 8th edition)",
        "proposed",
        ("inclusion:stage:IV",),
        (),
        "setting",
        ADVANCED,
    ),
    Relation(
        "consolidation_when_named",
        "A trial whose inclusion criteria name consolidation treats in the consolidation setting.",
        "the trial's own words",
        "proposed",
        ("inclusion:setting_word:consolidation",),
        (),
        "setting",
        ("consolidation",),
    ),
)
RELATION_IDS = tuple(relation.id for relation in RELATIONS)


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

    A relation applies when every fact it needs is among `facts` and, if it names prior lines, the
    prior_advanced_lines domain is non-empty and lies within them; it then keeps only its allowed values of
    the coordinate it narrows. Intersection is monotone, so the fixed point does not depend on the order of
    `relation_ids`. Returns the closed domains and the causes, each (coordinate, values removed, relation id).
    An unknown relation id raises KeyError: a relation that does not exist cannot be applied.
    """
    table = {relation.id: relation for relation in RELATIONS}
    chosen = [table[relation_id] for relation_id in relation_ids]
    current = dict(domains)
    causes: list[tuple[str, tuple[str, ...], str]] = []
    changed = True
    while changed:
        changed = False
        for relation in chosen:
            lines = current["prior_advanced_lines"]
            if any(fact not in facts for fact in relation.needs):
                continue
            if relation.lines_within and not (lines and set(lines) <= set(relation.lines_within)):
                continue
            kept = tuple(v for v in current[relation.narrows] if v in relation.allowed)
            removed = tuple(v for v in current[relation.narrows] if v not in kept)
            if removed:
                current[relation.narrows] = kept
                causes.append((relation.narrows, removed, relation.id))
                changed = True
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
