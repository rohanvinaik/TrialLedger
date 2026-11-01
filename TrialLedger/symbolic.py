"""The JSON form of `trialledger resolve`: a population reading rendered as plain data, each study's
eligibility coverage, typed criteria, coordinates, drugs, outcomes, near misses, review flags and expectation
observations, each value with the record text it rests on."""

from __future__ import annotations

from typing import Any

from TrialLedger.expectations import deviation_status


def symbolic_output(reading: dict[str, Any]) -> list[dict[str, Any]]:
    """Each study's symbolic reading as plain data: typed criteria, coordinates, drugs, outcomes, near misses
    and expectation observations, each value with the record text it rests on. The JSON form of `resolve`."""
    pairs = reading["pairs"]
    output = []
    for view, flags in zip(reading["views"], reading["flags"], strict=True):
        output.append(
            {
                "nct": view["nct"],
                "digest": view["digest"],
                "lead_sponsor": view["sponsor"],
                "status": view["status"],
                "itemized": view["itemize"],
                "eligibility_coverage": {
                    "content": view["coverage"]["content"],
                    "sectioning": view["coverage"]["sectioning"],
                    "evidence": dict(view["coverage"]["evidence"]),
                    "markers": [
                        {"kind": k, "scope": sc, "piece": p, "start": s, "end": e, "text": t}
                        for k, sc, p, s, e, t in view["coverage"]["markers"]
                    ],
                },
                "criteria": [
                    {
                        "piece": index,
                        "section": section,
                        "text": text,
                        "atoms": [
                            {
                                "bank": a[0],
                                "concept": a[1],
                                "values": list(a[2]),
                                "params": dict(a[3]),
                                "span": text[a[4] : a[5]],
                            }
                            for a in atoms
                        ],
                    }
                    for index, section, text, atoms in view["criteria"]
                ],
                "coordinates": {
                    name: {
                        "domain": list(row["domain"]),
                        "state": row["state"],
                        "with_proposed_relations": list(row["with_proposed"]),
                        "removed_by": [
                            [c[0], list(c[1]), c[2]] for c in row["causes"] + row["proposed_causes"]
                        ],
                    }
                    for name, row in view["coordinates"].items()
                },
                "experimental_drugs": [
                    {"name": d, "state": s, "classes": e, "resolved_by": r} for d, s, e, r in view["drugs"]
                ],
                "outcomes": [
                    {"type": k, "measure": m, "time_frame": f, "endpoint_classes": c, "time_points": p}
                    for k, m, f, c, p in view["outcomes"]
                ],
                "review": [
                    {
                        "kind": k,
                        "element": el,
                        "why": why,
                        "priority": int(pr),
                        "evidence": ev,
                        "question": q,
                        "options": opts,
                        "answer": None,
                    }
                    for k, el, why, pr, ev, q, opts in flags
                ],
                "near_misses": [
                    {
                        "other": p[1 - side],
                        "difference": p[2],
                        "value": p[3 + side],
                        "other_value": p[4 - side],
                        "other_sponsor": p[6 - side],
                        "other_start_year": p[8 - side],
                        "predicates_agreeing": p[9],
                    }
                    for p in pairs
                    for side in (0, 1)
                    if p[side] == view["nct"]
                ],
                "expectations": {
                    eid: {
                        "status": s,
                        "reason": r,
                        "cited": c,
                        "qualifiers": q,
                        "deviation": deviation_status(s, len(q), ""),
                    }
                    for eid, (s, r, c, q) in view["observations"].items()
                },
            }
        )
    return output
