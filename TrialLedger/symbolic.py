"""The JSON form of `trialledger resolve`: a population reading rendered as plain data, each study's
eligibility coverage, typed criteria, coordinates, drugs and their axes, its interventions' modality and cell
extractions, its intervention MeSH, outcomes, near misses (as written and aligned), structure relations,
review flags and expectation observations, each value with the record text or the request it rests on."""

from __future__ import annotations

from typing import Any

from TrialLedger.expectations import deviation_status


def symbolic_output(reading: dict[str, Any]) -> list[dict[str, Any]]:
    """Each study's symbolic reading as plain data: typed criteria, coordinates, drugs with their axes (each
    class with its standing, request, retrieval time and RxNav release), modality and cell extractions with
    their warrants, intervention MeSH at its level, outcomes, near misses as written and aligned (with each
    trial's basis), the structure relations its drugs hold, and expectation observations, each value with the
    record text or the request it rests on. The JSON form of `resolve`."""
    pairs = reading["pairs"]
    aligned = reading["aligned_pairs"]
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
                "drug_axes": [_axes(axes) for axes in view["drug_axes"]],
                "extractions": [
                    {
                        "subject": e[0],
                        "property": e[1],
                        "value": e[2],
                        "polarity": e[3],
                        "scope": e[4],
                        "location": e[5],
                        "rule": e[6],
                        "status": e[7],
                        "warrant": e[8],
                    }
                    for e in view["properties"]
                ],
                "intervention_mesh": [
                    {"id": i, "term": t, "level": level, "intervention": name}
                    for i, t, level, name in view["intervention_mesh"]
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
                "aligned_near_misses": [
                    {
                        "other": p[1 - side],
                        "difference": p[2],
                        "value": p[3 + side],
                        "other_value": p[4 - side],
                        "other_sponsor": p[6 - side],
                        "other_start_year": p[8 - side],
                        "predicates_agreeing": p[9],
                        "basis": p[10 + side],
                        "other_basis": p[11 - side],
                    }
                    for p in aligned
                    for side in (0, 1)
                    if p[side] == view["nct"]
                ],
                "structure_relations": [
                    {
                        "a": {"rxcui": r[0], "name": r[1]},
                        "b": {"rxcui": r[2], "name": r[3]},
                        "taxonomy": r[4],
                        "class": r[5],
                        "release": r[6],
                    }
                    for r in reading["structure_relations"]
                    if {r[0], r[2]} & _known_subjects(view)
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


def _known_subjects(view: dict[str, Any]) -> set[str]:
    """The RxNorm concepts a study's drugs hold a known structure class of."""
    return {
        a[6] for axes in view["drug_axes"] for a in axes["assertions"] if a[1] != "ATC" and a[5] == "known"
    }


def _axes(axes: dict[str, Any]) -> dict[str, Any]:
    """One experimental drug's axes as plain data, every class and name with the request it rests on."""
    return {
        "drug": axes["drug"],
        "identity": axes["identity"],
        "reason": axes["reason"],
        "names": [
            {
                "name": name,
                "code": code,
                "rxcui": rxcui,
                "ingredients": list(parts),
                "role": role,
                "requests": [{"request": r, "retrieved": t} for r, t in requests],
                "release": release,
            }
            for name, code, rxcui, parts, role, requests, release in axes["identities"]
        ],
        "classes": [
            {
                "name": a[0],
                "axis": a[1],
                "class_id": a[2],
                "class_name": a[3],
                "class_type": a[4],
                "standing": a[5],
                "asserted_of": {"rxcui": a[6], "name": a[7]},
                "release": a[8],
                "request": a[9],
                "retrieved": a[10],
            }
            for a in axes["assertions"]
        ],
        "targets": list(axes["targets"]),
        "alignment": [
            {
                "target": t,
                "atc": atc,
                "atc_name": name,
                "relation": relation,
                "member": member,
                "request": request,
                "retrieved": read,
            }
            for t, atc, name, relation, member, request, read in axes["alignment"]
        ],
        "atc": {"basis": axes["atc"][0], "classes": list(axes["atc"][1])},
    }
