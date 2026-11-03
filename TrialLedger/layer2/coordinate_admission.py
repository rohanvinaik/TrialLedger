"""Admit coordinate evidence at its declared standing without rewriting the typed solver.

Known and interpolated inputs have separate consumers. Pending readings remain in the
admission ledger and never become one conjunction of competing clinical hypotheses.
No source or confirmation is certified by a caller's standing declaration.
"""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import admission, coherence

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
    return {"coordinates": _coordinates(known, interpolated), "admission": ledger}
