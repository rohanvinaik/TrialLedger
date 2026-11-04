"""Local evidence size must not masquerade as a new NIH acquisition."""

from copy import deepcopy

from TrialLedger.layer2 import run
from TrialLedger.layer2.design_session import session_work_code
from TrialLedger.layer2.design_session_guide import EXAMPLE
from TrialLedger.layer2.session_state import digest
from TrialLedger.layer2.source_evidence import snapshot


def test_session_work_boundary_includes_exact_budget():
    assert session_work_code(2, 20, 2, 20) == "within_budget"


def test_solver_work_exhaustion_is_not_hidden_by_other_limits():
    assert session_work_code(3, 21, 2, 20) == "resource_bound:session_solver_work"


def test_analysis_exhaustion_remains_a_distinct_remedy():
    assert session_work_code(3, 20, 2, 20) == "resource_bound:session_analyses"


def test_legacy_expanded_item_limit_is_explicitly_nonoperative():
    request = deepcopy(EXAMPLE)
    request["session"]["limits"]["max_expanded_items"] = 1
    result = run(request)
    assert result["code"] == "complete"
    assert result["work"]["expanded_items"] > 1
    assert result["result"]["limit_semantics"]["max_expanded_items"].startswith("legacy_nonoperative")


def test_large_retained_source_and_both_replays_remain_complete():
    # Invented source-shaped evidence; the repeated retained values supply no clinical premise.
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"minimumAge": "18 Years"},
        },
        "resultsSection": {"uninterpreted_retained_values": ["unchanged"] * 10050},
    }
    source = snapshot(study)
    request = deepcopy(EXAMPLE)
    session = request["session"]
    session.update(premises=[], decisions=[])
    session["sources"] = [{"id": "registry", "study": study, "expected_digest": source["digest"]}]
    analysis = deepcopy(session["analyses"][0])
    analysis["id"] = "historical-age"
    analysis["operation"] = "source_assertions"
    analysis["target"] = {
        "kind": "historical",
        "ref": source["study_ref"],
        "scope": {
            "study": source["study_ref"],
            "population": "registered-general-population",
            "arm": "all",
            "time": "entry",
            "version": source["digest"],
        },
    }
    analysis["parameters"] = {"queries": [{"id": "older", "body": analysis["parameters"]["query"]}]}
    analysis["uses"] = [{"premise": "registry", "slot": "study", "projection": "source_study"}]
    session["analyses"] = [analysis]
    baseline = run(request)
    assert baseline["code"] == "complete"
    assert baseline["work"]["expanded_items"] > 10000
    revised = deepcopy(session)
    revised.update(revision="revised", parent_digest=baseline["result"]["session_digest"])
    revised["analyses"][0]["parameters"]["queries"][0]["body"]["value"]["number"] = 18
    result = run(
        {
            "operation": "design_session",
            "session": revised,
            "previous": {
                "session": session,
                "result": baseline["result"],
                "expected_result_digest": digest(baseline["result"]),
            },
        }
    )
    assert result["code"] == "complete"
    assert result["previous_fresh"] == baseline["result"]
    assert result["result"]["sources"][0]["study"] == study
    assert result["result"]["analyses"][0]["request"]["study"] == study
    assert result["work"]["analyses"] == 2
    assert (
        result["result"]["analyses"][0]["result"]["result"]["analyses"][0]["result"]["decision"]["result"]
        == "ENTAILED"
    )
