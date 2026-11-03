"""Authored obligations for per-finding metadata; clinical results stay untouched."""

import copy

import pytest

from TrialLedger.layer2 import result_semantics as r


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("resource_bound", "computation"),
        ("resource_bound:design_bounds", "computation"),
        ("proposed_refused:reading", "premise"),
        ("open_scope:arm:A", "translation"),
        ("class_membership_unresolved", "evidence"),
        ("no_constraint_mentions_query", "coverage"),
        ("undecided_by_constraints", "constraint"),
        ("signal_conflict:counts", "conflict"),
        ("unknown_future_code", "unclassified"),
        ("", "unclassified"),
    ],
)
def test_named_causes_preserve_unknowns(code, expected):
    assert r.cause_kind(code) == expected


def test_computation_limit_is_never_called_an_evidence_gap():
    assert r.completion_code("UNDETERMINED", ["resource_bound"]) == "limited"
    assert r.completion_code("REFUSED", ["resource_bound:interpretations"]) == "limited"
    assert r.completion_code("UNDETERMINED", ["no_constraint_mentions_query"]) == "complete"


def test_unknown_causes_and_outcomes_do_not_gain_a_complete_label():
    assert r.completion_code("UNDETERMINED", ["future_blocker"]) == "unclassified"
    assert r.completion_code("FUTURE_RESULT", []) == "unclassified"
    assert r.completion_code("UNSUPPORTED_QUERY", []) == "unsupported"
    assert r.completion_code("REFUSED", ["request_not_an_object"]) == "invalid"


def test_open_knowledge_does_not_mean_unfinished_computation():
    assert r.completion_code("unresolved", ["proposed_refused:bridge"]) == "complete"
    assert r.completion_code("abstain", ["rarity_abstained"]) == "complete"


def test_independent_limit_must_not_erase_an_effective_supported_conflict():
    assert r.disposition_code("INCONSISTENT", "known", "limited") == "conflict"
    assert r.disposition_code("refuted", "proposed", "limited") == "conflict"
    assert r.disposition_code("incoherent", "interpolated", "limited") == "conflict"
    assert r.disposition_code("INCONSISTENT", "", "limited") == "unclassified"


def test_conclusive_effective_query_keeps_its_own_support_despite_other_limit():
    assert r.disposition_code("ENTAILED", "known", "limited") == "settled"
    assert r.disposition_code("REFUTED", "interpolated", "limited") == "conditional"
    assert r.disposition_code("ENTAILED", "proposed", "limited") == "conditional"
    assert r.disposition_code("ENTAILED", "", "limited") == "unclassified"


@pytest.mark.parametrize(
    ("result", "standing", "completion", "expected"),
    [
        ("ENTAILED", "known", "complete", "settled"),
        ("REFUTED", "known", "complete", "settled"),
        ("ENTAILED", "interpolated", "complete", "conditional"),
        ("ENTAILED", "proposed", "complete", "conditional"),
        ("ENTAILED", "", "complete", "unclassified"),
        ("UNDETERMINED", "known", "complete", "open"),
        ("UNDETERMINED", "known", "limited", "not_computed"),
        ("INCONSISTENT", "known", "complete", "conflict"),
        ("UNSUPPORTED_QUERY", "known", "unsupported", "unsupported"),
        ("unresolved", "proposed", "complete", "open"),
        ("resolved", "proposed", "complete", "conditional"),
        ("FUTURE", "known", "complete", "unclassified"),
    ],
)
def test_disposition_never_invents_a_design_choice(result, standing, completion, expected):
    assert r.disposition_code(result, standing, completion) == expected


def test_entailment_metadata_preserves_the_payload_and_all_causes():
    payload = {
        "decision": {
            "result": "UNDETERMINED",
            "status": None,
            "proof": [],
            "blockers": ["resource_bound", "proposed_refused:reading"],
        }
    }
    before = copy.deepcopy(payload)
    output = r.metadata("entailment", payload)
    assert payload == before
    assert output["kind"] == "reasoning"
    finding = output["findings"][0]
    assert finding["path"] == "/result/decision"
    assert finding["completion"] == "limited"
    assert finding["disposition"] == "not_computed"
    assert finding["causes"] == [
        {"code": "proposed_refused:reading", "kind": "premise"},
        {"code": "resource_bound", "kind": "computation"},
    ]


def test_discovery_and_empty_source_inspection_are_not_clinical_findings():
    assert r.metadata("describe", {"decision": {"result": "ENTAILED"}}) == {
        "version": 1,
        "kind": "discovery",
        "findings": [],
    }
    assert r.metadata("source_assertions", {"coverage": [{"code": "compiled"}], "analyses": []}) == {
        "version": 1,
        "kind": "inspection",
        "findings": [],
    }


def test_unknown_operation_and_null_result_remain_unclassified():
    unknown = r.metadata("future_operation", {"decision": {"result": "ENTAILED", "status": "known"}})
    assert unknown["kind"] == "inspection"
    assert unknown["findings"][0]["disposition"] == "unclassified"
    assert r.metadata("entailment", None)["findings"][0]["completion"] == "unclassified"


def test_refused_resource_work_differs_from_invalid_input():
    limited = r.metadata("design_bounds", None, ["resource_bound:design_bounds"])
    invalid = r.metadata("entailment", None, ["request_not_an_object"])
    assert limited["kind"] == invalid["kind"] == "refusal"
    assert limited["findings"][0]["completion"] == "limited"
    assert invalid["findings"][0]["completion"] == "invalid"


def test_signal_keeps_completed_arithmetic_separate_from_refused_support():
    result = {
        "signals": [
            {
                "code": "unresolved",
                "calculation_code": "bounded",
                "status": "proposed",
                "blockers": ["proposed_refused:overlap"],
            }
        ]
    }
    finding = r.metadata("signals", result)["findings"][0]
    assert finding["completion"] == "complete"
    assert finding["disposition"] == "open"
    assert finding["raw_result"] == "bounded"
    assert finding["raw_path"] == "/result/signals/0/calculation_code"


def test_effective_interpretation_query_is_not_overruled_by_raw_entailment():
    query = {
        "id": "Q",
        "result": "UNDETERMINED",
        "decision": {"result": "ENTAILED", "status": "known", "blockers": []},
        "warrant": {"status": "proposed", "blockers": ["resource_bound", "unresolved_assertion:reading"]},
    }
    result = {
        "fixed": {
            "queries": [
                {
                    "result": "ENTAILED",
                    "decision": {"result": "ENTAILED"},
                    "warrant": {"status": "known", "blockers": []},
                }
            ]
        },
        "interpretations": [
            {
                "state": "unresolved",
                "warrant": {"status": "proposed", "blockers": ["resource_bound"]},
                "queries": [query],
            }
        ],
    }
    before = copy.deepcopy(result)
    findings = r.metadata("interpretations", result)["findings"]
    assert result == before
    assert findings[0]["disposition"] == "settled"
    finding = next(row for row in findings if row["path"] == "/result/interpretations/0/queries/0")
    assert finding["logical_result"] == "UNDETERMINED"
    assert finding["raw_result"] == "ENTAILED"
    assert finding["completion"] == "limited"
    assert finding["support_path"] == "/result/interpretations/0/queries/0/warrant"
    assert {cause["kind"] for cause in finding["causes"]} == {"computation", "premise"}


def test_coordinate_layers_and_json_pointer_escaping_stay_separate():
    result = {
        "coordinates": {
            "a/b~c": {
                "state": "unnarrowed",
                "interpolated": {"state": "resolved"},
                "proposals": [{"state": "resolved"}],
            }
        },
        "admission": [{"code": "proposed_refused", "standing": {"status": "proposed"}}],
    }
    rows = r.metadata("coordinates", result)["findings"]
    assert rows[0]["path"] == "/result/coordinates/a~1b~0c"
    assert rows[0]["disposition"] == "open"
    assert rows[1]["standing"] == "interpolated"
    assert rows[1]["disposition"] == rows[2]["disposition"] == "conditional"
    assert rows[3]["disposition"] == "open"


def test_corpus_statistics_do_not_claim_clinical_recommendation():
    result = {
        "frequency": [{"tier": "unresolved", "lower": 0.5, "unresolved": 1}],
        "associations": [{"status": "proposed"}, {"status": "below_support"}],
        "occupancy": [{"state": "unknown"}],
        "expectations": [{"rarity": ["abstain", None, 0, None, None]}],
    }
    rows = r.metadata("corpus", result)["findings"]
    assert rows[0]["kind"] == "corpus_statistic" and rows[0]["disposition"] == "descriptive"
    assert rows[1]["kind"] == "corpus_eligibility_interval" and rows[1]["disposition"] == "open"
    assert rows[2]["standing"] == "proposed" and rows[2]["disposition"] == "conditional"
    assert rows[3]["disposition"] == rows[4]["disposition"] == rows[5]["disposition"] == "open"
    assert all(row["completion"] == "complete" for row in rows)
    assert not any(row["disposition"] == "design_choice" for row in rows)


def test_common_candidate_limit_uses_survivors_not_unattached_context():
    result = {
        "remaining": ["open"],
        "candidates": [
            {
                "id": "open",
                "state": "unresolved",
                "query_decision": {"result": "UNDETERMINED", "status": None, "blockers": ["resource_bound"]},
            },
            {
                "id": "excluded",
                "state": "ruled_out",
                "query_decision": {
                    "result": "UNDETERMINED",
                    "status": None,
                    "blockers": ["not-a-cause-for-survival"],
                },
            },
        ],
        "consequence": {"result": "UNDETERMINED", "status": None},
        "signals": [
            {
                "code": "unresolved",
                "calculation_code": "bounded",
                "status": "proposed",
                "blockers": ["proposed_refused:unattached"],
            }
        ],
    }
    rows = r.metadata("design_bounds", result)["findings"]
    consequence = next(row for row in rows if row["kind"] == "candidate_family_consequence")
    assert consequence["completion"] == "limited"
    assert consequence["causes"] == [{"code": "resource_bound", "kind": "computation"}]
    candidate = next(row for row in rows if row["path"] == "/result/candidates/0")
    assert candidate["standing"] is None


def test_source_child_metadata_is_reused_detached_and_prefixed():
    child = {
        "operation": "entailment",
        "result": {"decision": {"result": "REFUTED", "status": "known", "blockers": []}},
        "metadata": {
            "version": 1,
            "kind": "reasoning",
            "findings": [
                {
                    "path": "/result/decision",
                    "kind": "logical",
                    "logical_result": "UNDETERMINED",
                    "standing": None,
                    "completion": "limited",
                    "disposition": "not_computed",
                    "causes": [{"code": "resource_bound", "kind": "computation"}],
                    "support_path": "/result/warrant",
                }
            ],
        },
    }
    result = {"analyses": [child]}
    before = copy.deepcopy(result)
    row = r.metadata("source_assertions", result)["findings"][0]
    assert row["path"] == "/result/analyses/0/result/decision"
    assert row["support_path"] == "/result/analyses/0/result/warrant"
    assert row["disposition"] == "not_computed"
    row["causes"].append({"code": "changed", "kind": "unclassified"})
    assert result == before


def test_unannotated_source_child_is_supported_explicitly():
    result = {
        "analyses": [
            {
                "operation": "entailment",
                "result": {"decision": {"result": "ENTAILED", "status": "known", "blockers": []}},
                "problems": [],
            }
        ]
    }
    row = r.metadata("source_assertions", result)["findings"][0]
    assert row["path"] == "/result/analyses/0/result/decision"
    assert row["disposition"] == "settled"


def test_all_focused_examples_have_only_real_result_paths():
    from TrialLedger.layer2 import run

    for operation in (
        "entailment",
        "coordinates",
        "corpus",
        "design_bounds",
        "signals",
        "interpretations",
        "source_assertions",
    ):
        request = run({"operation": "describe", "view": operation})["result"]["example"]
        response = run(request)
        assert response["code"] == "complete"
        output = r.metadata(operation, response["result"])
        assert output["findings"]
        for finding in output["findings"]:
            cursor = response
            for token in finding["path"].split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                cursor = cursor[int(token)] if isinstance(cursor, (list, tuple)) else cursor[token]


def test_real_frame_conflict_survives_its_independently_limited_check():
    from TrialLedger.layer2 import run
    from TrialLedger.layer2.interpretations_guide import frame, premise, quantity

    request = copy.deepcopy(run({"operation": "describe", "view": "interpretations"})["result"]["example"])
    request["bound"] = 10
    literals = [
        {
            "class": "Literal",
            "subject": {"class": "Subject", "kind": "participant"},
            "predicate": {"class": "Predicate", "kind": "demographic", "key": "flag" + str(i)},
            "value": {"class": "Value", "kind": "boolean"},
        }
        for i in range(8)
    ]
    request["interpretations"] = [
        frame(
            "conflict-and-limit",
            "An incompatible PS range with an independently limited conjunction",
            [
                premise("negative-PS", quantity("ECOG", "le", -1, "ECOG")),
                premise("large", {"class": "AllOf", "parts": literals}),
            ],
        )
    ]
    reply = run(request)
    assert reply["code"] == "complete"
    result = reply["result"]
    actual = result["interpretations"][0]
    assert actual["state"] == "refuted"
    assert actual["warrant"]["blockers"] == ["resource_bound"]
    rows = r.metadata("interpretations", result)["findings"]
    finding = next(row for row in rows if row["path"] == "/result/interpretations/0")
    assert finding["logical_result"] == "refuted"
    assert finding["standing"] == "proposed"
    assert finding["completion"] == "limited"
    assert finding["disposition"] == "conflict"
