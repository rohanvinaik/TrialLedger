"""One source-bound clinical handoff; full canonical results remain its evidence."""

from __future__ import annotations

from copy import deepcopy

from TrialLedger import clinical_display


def _premises(result: dict, proof: list, base: str = "/result") -> list[dict]:
    by_id = {row["id"]: (i, row) for i, row in enumerate(result.get("effective_premises", []))}
    rows = []
    for identity in proof:
        if identity not in by_id:
            rows.append(
                {"id": identity, "text": "Open the exact deciding premise.", "code": "premise_not_projected"}
            )
            continue
        index, row = by_id[identity]
        ref = f"{base}/effective_premises/{index}"
        display = clinical_display.assertion(row.get("payload"), ref + "/payload")
        rows.append(
            {
                "id": identity,
                **display,
                "origin": deepcopy(row.get("origin")),
                "support": deepcopy(row.get("standing")),
                "canonical_ref": ref,
            }
        )
    return rows


def _conditions(explanations: dict, ref: str) -> list[dict]:
    rows = []
    for index, condition in enumerate(explanations.get("conditions", [])):
        here = f"{ref}/conditions/{index}"
        rows.append(
            {
                "relation": condition.get("relation"),
                "requirement": clinical_display.proposition(condition.get("body"), here + "/body"),
                "standing": condition.get("status"),
                "scope": deepcopy(condition.get("scope")),
                "profile_check": deepcopy(condition.get("profile_check")),
                "warrant_query": clinical_display.proposition(
                    condition.get("warrant", {}).get("query"), here + "/warrant/query"
                ),
                "proof": deepcopy(condition.get("warrant", {}).get("proof", [])),
                "canonical_ref": here,
            }
        )
    return rows


def build(response: dict) -> list[dict]:
    """One coherent view per declared decision; labels never stand in for represented profiles."""
    if response.get("operation") != "design_session" or not isinstance(response.get("result"), dict):
        return []
    result = response["result"]
    analyses = {row["id"]: (i, row) for i, row in enumerate(result.get("analyses", []))}
    views = []
    for index, decision in enumerate(result.get("decisions", [])):
        ref = f"/result/decisions/{index}"
        options = []
        for j, option in enumerate(decision.get("alternatives", [])):
            here = f"{ref}/alternatives/{j}"
            warrant = option.get("warrant") or {}
            analysis_index, analysis = analyses.get(option.get("analysis"), (None, {}))
            explanations = analysis.get("result", {}).get("result", {}).get("explanations", {})
            options.append(
                {
                    "id": option["id"],
                    "caller_label": {
                        "text": option["label"],
                        "origin": "caller_wording; not a computed assertion",
                    },
                    "profile": clinical_display.proposition(option.get("query"), here + "/query"),
                    "context": deepcopy(analysis.get("request", {}).get("context", {})),
                    "context_origin": "actual analysis request; omitted cohort/phase/arm remain open",
                    "logical_result": warrant.get("result"),
                    "feasibility": option.get("code"),
                    "computed_answer": clinical_display.decision_outcome(warrant, option.get("code", "")),
                    "standing": option.get("feasibility_status", warrant.get("status")),
                    "logical_standing": warrant.get("status"),
                    "deciding_premises": _premises(result, warrant.get("proof", [])),
                    "condition_coverage": explanations.get("coverage"),
                    "conditions": _conditions(
                        explanations, f"/result/analyses/{analysis_index}/result/result/explanations"
                    ),
                    "permissions": [
                        {
                            "id": p.get("id"),
                            "code": p.get("code"),
                            "statement": clinical_display.proposition(
                                p.get("body"),
                                f"/result/analyses/{analysis_index}/result/result/explanations/permissions/{k}/body",
                            ),
                            "standing": p.get("status"),
                            "applicability": clinical_display.proposition(p.get("applicability")),
                            "scope": deepcopy(p.get("scope")),
                            "blockers": deepcopy(p.get("blockers", [])),
                        }
                        for k, p in enumerate(explanations.get("permissions", []))
                    ],
                    "open_items": deepcopy(warrant.get("blockers", [])),
                    "origin": deepcopy(option.get("origin_refs", [])),
                    "canonical_ref": here,
                }
            )
        selected = decision.get("selected")
        views.append(
            {
                "id": decision["id"],
                "caller_question": {
                    "text": decision["question"],
                    "origin": "caller_wording; not a computed assertion",
                },
                "decision_code": decision.get("code"),
                "selected": deepcopy(selected),
                "origin": deepcopy(decision.get("origin")),
                "coverage": decision.get("coverage_limit", "Only the represented restrictions are checked."),
                "evidence": deepcopy(decision.get("evidence", [])),
                "options": options,
                "canonical_ref": ref,
            }
        )
    return views
