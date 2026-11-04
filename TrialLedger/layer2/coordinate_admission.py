"""Admit coordinate evidence at its declared standing without rewriting the typed solver.

Known and interpolated inputs have separate consumers. Pending readings remain in the
admission ledger and never become one conjunction of competing clinical hypotheses.
No source or confirmation is certified by a caller's standing declaration.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy

from TrialLedger.layer2 import admission, coherence
from TrialLedger.layer2.reasoning_explanations import coordinate_effect_code

Evidence = tuple[str, str, tuple[str, ...], str, str]
Domains = dict[str, tuple[str, ...]]
Cause = tuple[str, tuple[str, ...], str]


def _narrow_from(base: Domains, evidence: list[Evidence]) -> tuple[Domains, list[Cause]]:
    """Apply the existing direct-evidence removals to an already established domain."""
    _, removals = coherence.narrow_by_evidence(evidence)
    current = dict(base)
    causes = []
    for coordinate, removed, ref in removals:
        actual = tuple(value for value in current[coordinate] if value in removed)
        if actual:
            current[coordinate] = tuple(value for value in current[coordinate] if value not in actual)
            causes.append((coordinate, actual, ref))
    return current, causes


def _close_level(
    base: Domains, extra: list[Evidence], all_evidence: list[Evidence], kinds: tuple[str, ...]
) -> tuple[Domains, list[Cause]]:
    """Use the stored relation table and typed operators, retaining only this level's removals."""
    domains, evidence_causes = _narrow_from(base, extra)
    relation_ids = [relation.id for relation in coherence.RELATIONS if relation.kind in kinds]
    closed, relation_causes = coherence.close(domains, coherence.facts_of(all_evidence), relation_ids)
    return closed, [*evidence_causes, *relation_causes]


def _coordinates(known: list[Evidence], interpolated: list[Evidence]) -> dict[str, dict]:
    """Keep the existing known result while computing a separate weaker closure and each proposal."""
    rows = coherence.resolve(known)
    known_domains = {name: row["domain"] for name, row in rows.items()}
    all_evidence = [*known, *interpolated]
    closed, causes = _close_level(known_domains, interpolated, all_evidence, ("strict", "default"))
    proposals = [
        (relation.id, *coherence.close(closed, coherence.facts_of(all_evidence), [relation.id]))
        for relation in coherence.RELATIONS
        if relation.kind == "proposal"
    ]
    for name, full in coherence.COORDINATES.items():
        rows[name]["interpolated"] = {
            "domain": closed[name],
            "state": coherence.domain_state(closed[name], full),
            "causes": [cause for cause in causes if cause[0] == name],
        }
        rows[name]["proposals"] = [
            {
                "relation": relation,
                "domain": proposed[name],
                "state": coherence.domain_state(proposed[name], full),
                "causes": [cause for cause in proposal_causes if cause[0] == name],
            }
            for relation, proposed, proposal_causes in proposals
            if proposed[name] != closed[name]
        ]
    return rows


def _domain_levels(rows: dict[str, dict]) -> dict[tuple[str, str], tuple[str, ...]]:
    """Flatten actual levels without treating an absent proposal as a new restriction."""
    levels = {}
    for name, row in rows.items():
        levels[name, "known"] = row["domain"]
        levels[name, "interpolated"] = row["interpolated"]["domain"]
        for relation in coherence.RELATIONS:
            if relation.kind == "proposal" and relation.narrows == name:
                proposal = next((p for p in row["proposals"] if p["relation"] == relation.id), None)
                levels[name, "proposal:" + relation.id] = (
                    proposal["domain"] if proposal else row["interpolated"]["domain"]
                )
    return levels


def _consumers(item: Evidence, rows: dict[str, dict], facts_by_level: dict[str, list[str]]) -> list[dict]:
    """Find actual exact fact/coordinate interfaces, including a rule's negative guard."""
    section, concept, values, scope, _ref = item
    consumers = []
    coordinate = coherence.direct_coordinate(concept, scope)
    if coordinate or concept == "prior_lines":
        consumers.append(
            {
                "kind": "direct_coordinate",
                "coordinate": coordinate or "prior_advanced_lines",
                "rule": "coherence.narrow_by_evidence",
                "level": "input_standing",
                "applicability": "applicable"
                if coordinate and section in ("inclusion", "exclusion") and values
                else "inactive",
                "reason": "exact_coordinate_restriction" if coordinate else "advanced_scope_required",
            }
        )
    own_facts = coherence.facts_of([item])
    for relation in coherence.RELATIONS:
        roles = {
            role: [fact for fact in own_facts if fact in facts]
            for role, facts in (
                ("required", relation.needs),
                ("alternative", relation.needs_any),
                ("forbidden", relation.forbids),
            )
        }
        roles = {role: facts for role, facts in roles.items() if facts}
        line_consumer = bool(relation.lines_within and coordinate == "prior_advanced_lines")
        if not roles and not line_consumer:
            continue
        level = "known" if relation.kind == "strict" else "interpolated"
        domains = {
            name: row["domain"] if level == "known" else row["interpolated"]["domain"]
            for name, row in rows.items()
        }
        details = coherence.relation_applicability(relation, facts_by_level[level], domains)
        consumers.append(
            {
                "kind": "relation",
                "relation": relation.id,
                "relation_kind": relation.kind,
                "coordinate": relation.narrows,
                "level": "proposal" if relation.kind == "proposal" else level,
                "matched_fact_roles": roles,
                "line_domain_consumer": line_consumer,
                "applicability": details["code"],
                "details": details,
            }
        )
    return consumers


def _domain_key(level: str, item: Evidence) -> tuple[str, str, str, frozenset[str], str]:
    """Exact extensional identity for domain-only operators; refs and order remain in each original row.

    Direct restrictions use value membership, relation consumers use exact fact membership, and neither
    reads a ref or the ordering of values. This identity establishes no clinical or source equivalence.
    """
    section, concept, values, scope, _ref = item
    return level, section, concept, frozenset(values), scope


def _effects(ledger: list[dict], evidence: list[Evidence], rows: dict[str, dict]) -> list[dict]:
    """Explain actual consumers and marginal retraction; this is not a unique proof or clinical causality.

    Duplicate semantic inputs at the same level are known redundant for domains, regardless of their refs.
    Only changed coordinate/value deltas are retained; complete output domains remain in coordinates.
    """
    accepted = [(row, item) for row, item in zip(ledger, evidence, strict=True) if row["code"] == "accepted"]
    known = [item for row, item in accepted if row["level"] == "known"]
    weaker = [item for row, item in accepted if row["level"] == "interpolated"]
    full = _domain_levels(rows)
    facts_by_level = {
        "known": coherence.facts_of(known),
        "interpolated": coherence.facts_of([*known, *weaker]),
    }
    keys = [_domain_key(row["level"], item) for row, item in accepted]
    counts = Counter(keys)
    effects = []
    for row, item in zip(ledger, evidence, strict=True):
        consumers = _consumers(item, rows, facts_by_level)
        admitted = row["code"] == "accepted"
        changes = []
        # An intersection identity on the full finite domain is an identity on every subset. Without
        # any fact/rule consumer, retracting that input cannot change a domain at another level either.
        can_change_domains = any(consumer["kind"] == "relation" for consumer in consumers) or bool(
            coherence.narrow_by_evidence([item])[1]
        )
        if admitted and can_change_domains and counts[_domain_key(row["level"], item)] == 1:
            remaining = [(other, value) for other, value in accepted if other["index"] != row["index"]]
            without_rows = _coordinates(
                [value for other, value in remaining if other["level"] == "known"],
                [value for other, value in remaining if other["level"] == "interpolated"],
            )
            without = _domain_levels(without_rows)
            reported_proposals = {
                (name, "proposal:" + proposal["relation"])
                for snapshot in (rows, without_rows)
                for name, coordinate_row in snapshot.items()
                for proposal in coordinate_row["proposals"]
            }
            for (coordinate, level), domain in full.items():
                if level not in ("known", "interpolated") and (coordinate, level) not in reported_proposals:
                    continue
                removed = [value for value in without[coordinate, level] if value not in domain]
                preserved = [value for value in domain if value not in without[coordinate, level]]
                if removed or preserved:
                    changes.append(
                        {
                            "coordinate": coordinate,
                            "level": level,
                            "excluded_by_input": removed,
                            "preserved_by_input": preserved,
                        }
                    )
        active = any(consumer["applicability"] == "applicable" for consumer in consumers)
        guarded = any(
            consumer["applicability"] == "guarded" and consumer.get("matched_fact_roles", {}).get("forbidden")
            for consumer in consumers
        )
        narrowed = any(change["excluded_by_input"] for change in changes)
        code = coordinate_effect_code(admitted, bool(consumers), active, narrowed, guarded)
        effects.append(
            {
                "index": row["index"],
                "ref": row["ref"],
                "standing": deepcopy(row["standing"]),
                "level": row["level"],
                "code": code,
                "input_path": "/result/admission/" + str(row["index"]),
                "consumers": consumers,
                "domain_deltas": changes,
                "comparison": "marginal_retraction_not_unique_proof_or_clinical_causality",
            }
        )
    return effects


def resolve(given: list[dict], evidence: list[Evidence]) -> dict:
    """Pair validated public evidence with its tuples and return coordinates plus admission provenance.

    The service validates the clinical vocabulary and tuple shape. This boundary validates each optional
    closed standing, distinguishes omission from explicit null, and routes only resolved known or
    interpolated declarations into their respective consumers. It never promotes pending evidence.
    """
    if len(given) != len(evidence):
        raise ValueError("coordinate_evidence_length_mismatch")
    known = []
    interpolated = []
    ledger = []
    for index, (raw, item) in enumerate(zip(given, evidence, strict=True)):
        label = f"coordinates.evidence:{index}"
        if "standing" in raw and raw["standing"] is None:
            raise ValueError("invalid_standing:" + label)
        standing = admission.read_standing(raw.get("standing"), label)
        code = admission.code(standing, interpolated=True)
        level = "pending"
        if code == "accepted":
            level = standing["status"]
            if level == "known":
                known.append(item)
            else:
                interpolated.append(item)
        ledger.append(
            {
                "index": index,
                "ref": item[4],
                "standing": standing,
                "code": code,
                "level": level,
                "evidence": deepcopy(raw),
            }
        )
    rows = _coordinates(known, interpolated)
    return {"coordinates": rows, "admission": ledger, "effects": _effects(ledger, evidence, rows)}
