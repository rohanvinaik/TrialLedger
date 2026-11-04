"""Authored MUST/MUST-NOT contracts: explicit origins, local warrants and fresh replay.

All study objects and clinical premises here are invented teaching fixtures, not NIH evidence.
"""

import itertools
import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_session as session
from TrialLedger.layer2 import service, source_evidence
from TrialLedger.layer2 import session_state as state


def plain(value):
    return json.loads(a.canonical(value))


def age(number, comparison="ge"):
    return plain(
        a.Literal(
            a.Subject("participant"),
            a.Predicate("measurement", "age"),
            a.Value("quantity", comparison, number=number, unit="Years"),
        )
    )


def target(kind="new_trial", ref="draft"):
    return {
        "kind": kind,
        "ref": ref,
        "scope": {"study": ref, "population": "general", "arm": "all", "time": "entry", "version": "v1"},
    }


def origin(kind="user_choice", ref="user:age", source=None, analysis=None):
    return {"kind": kind, "ref": ref, "source": source, "analysis": analysis}


def assertion(identity="adult", number=18, status="known", resolution="resolved", kind="user_choice"):
    return {
        "id": identity,
        "kind": "assertion",
        "payload": plain(
            a.ScopedAssertion(
                identity,
                "user:" + identity,
                "required",
                a.from_canonical(state.canonical(age(number))),
                rule=a.Rule("user-explicit", "1"),
                status=status,
                resolution=resolution,
            )
        ),
        "origin": origin(kind, "user:" + identity),
        "depends_on": [],
    }


def analysis(identity="older", query=None, premises=("adult",), kind="new_trial"):
    return {
        "id": identity,
        "operation": "entailment",
        "target": target(kind),
        "parameters": {"query": age(65) if query is None else query, "bound": 128},
        "uses": [{"premise": v, "slot": "assertions", "projection": "identity"} for v in premises],
    }


def bare():
    return {
        "schema_version": 1,
        "id": "design",
        "revision": "one",
        "parent_digest": None,
        "target": target(),
        "sources": [],
        "premises": [assertion()],
        "analyses": [
            analysis(),
            analysis("younger", plain(a.Not(a.from_canonical(state.canonical(age(65)))))),
        ],
        "decisions": [
            {
                "id": "age-policy",
                "question": "Should the represented age restriction require age 65?",
                "target": target(),
                "coverage": "represented_restriction",
                "alternatives": [
                    {"id": "older", "label": "65 or older", "analysis": "older", "query": age(65)},
                    {
                        "id": "younger",
                        "label": "Below 65",
                        "analysis": "younger",
                        "query": plain(a.Not(a.from_canonical(state.canonical(age(65))))),
                    },
                ],
                "selected": None,
            }
        ],
        "limits": dict(state.HARD_LIMITS),
    }


def run(value, **kwargs):
    return session.run({"operation": "design_session", "session": value, "previous": None}, **kwargs)


def study_source():
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "eligibilityCriteria": "Adults with condition X.",
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Invented sponsor"}},
        }
    }
    snap = source_evidence.snapshot(study)
    return {"id": "registry", "study": study, "expected_digest": snap["digest"]}, snap


def add_source(value):
    source, snap = study_source()
    value["sources"] = [source]
    value["premises"].append(
        {
            "id": "registered-age",
            "kind": "source_assertion",
            "payload": {"source": "registry", "assertion": "registry-age-minimumAge"},
            "origin": origin(
                "source_rule",
                snap["study_ref"] + "#/protocolSection/eligibilityModule/minimumAge",
                "registry",
            ),
            "depends_on": [],
        }
    )
    return snap


def test_actual_entailment_supports_two_declared_alternatives_without_full_eligibility_claim():
    request = bare()
    unchanged = deepcopy(request)
    result = run(request)
    assert request == unchanged
    assert result["result"]["decisions"][0]["code"] == "design_choice"
    assert [v["code"] for v in result["result"]["decisions"][0]["alternatives"]] == ["feasible", "feasible"]
    assert "not complete" in result["result"]["decisions"][0]["coverage_limit"]
    assert result["result"]["analyses"][0]["result"] == json.loads(
        state.canonical(service.run(result["result"]["analyses"][0]["request"]))
    )


def test_historical_undetermined_is_evidence_question_not_historical_design_freedom():
    value = bare()
    value["target"] = target("historical")
    for item in value["analyses"] + value["decisions"]:
        item["target"] = target("historical")
    assert run(value)["result"]["decisions"][0]["code"] == "evidence_question"


def test_target_mismatch_never_becomes_design_choice():
    value = bare()
    value["analyses"][0]["target"] = target("historical", "comparator")
    result = run(value)
    assert result["result"]["decisions"][0]["code"] == "translation_question"
    assert result["result"]["decisions"][0]["alternatives"][0]["code"] == "target_mismatch"


def test_source_fact_cannot_be_silently_adopted_into_new_trial():
    value = bare()
    add_source(value)
    value["analyses"][0]["uses"][0]["premise"] = "registered-age"
    with pytest.raises(ValueError, match="explicit_adoption"):
        run(value)


def test_explicit_independent_adoption_is_valid_without_certifying_proposed_comparator_reading():
    value = bare()
    add_source(value)
    assert run(value)["result"]["decisions"][0]["code"] == "design_choice"


def test_actual_compiled_source_floor_projects_known_corpus_feature_not_caller_status():
    value = bare()
    snap = add_source(value)
    value["premises"].append(
        {
            "id": "trial",
            "kind": "corpus_trial",
            "payload": {
                "source": "registry",
                "stratum": "chosen-set",
                "feature_uses": [
                    {"premise": "registered-age", "projection": "registered_general_age_to_corpus"}
                ],
                "metadata": {},
            },
            "origin": origin("user_choice", "user:comparison-set"),
            "depends_on": [],
        }
    )
    value["analyses"].append(
        {
            "id": "rates",
            "operation": "corpus",
            "target": target("historical"),
            "parameters": {},
            "uses": [{"premise": "trial", "slot": "trials", "projection": "corpus_trial"}],
        }
    )
    result = run(value)["result"]
    row = next(v for v in result["analyses"] if v["id"] == "rates")
    feature = row["result"]["result"]["frequency"][0]
    assert feature["element"] == "inclusion:minimum_age=18_Years"
    assert (feature["stating"], feature["trials"]) == (1, 1)
    assert (
        row["request"]["trials"][0]["feature_standings"]["elements"][feature["element"]]["status"] == "known"
    )
    assert result["dependency_graph"]["premise:registered-age"] == ["source:registry"]
    assert result["sources"][0]["snapshot"]["digest"] == snap["digest"]


def test_known_age_survives_pending_independent_documented_feature():
    value = bare()
    snap = add_source(value)
    reading = assertion("reading", 65, "proposed")
    reading["origin"] = origin(
        "source_interpretation",
        snap["study_ref"] + "#/protocolSection/eligibilityModule/eligibilityCriteria",
        "registry",
    )
    reading["payload"]["criterion_ref"] = reading["origin"]["ref"]
    value["premises"].extend(
        [
            reading,
            {
                "id": "trial",
                "kind": "corpus_trial",
                "payload": {
                    "source": "registry",
                    "stratum": "set",
                    "feature_uses": [
                        {"premise": "registered-age", "projection": "registered_general_age_to_corpus"},
                        {"premise": "reading", "projection": "documented_assertion_to_corpus"},
                    ],
                    "metadata": {},
                },
                "origin": origin("user_choice"),
                "depends_on": [],
            },
        ]
    )
    value["analyses"].append(
        {
            "id": "rates",
            "operation": "corpus",
            "target": target("historical"),
            "parameters": {},
            "uses": [{"premise": "trial", "slot": "trials", "projection": "corpus_trial"}],
        }
    )
    rows = run(value)["result"]["analyses"][-1]["result"]["result"]["frequency"]
    assert sorted((v["stating"], v["pending_stating"], v["trials"]) for v in rows) == [(0, 1, 1), (1, 0, 1)]


def test_user_choice_cannot_be_counted_as_documented_statement():
    from TrialLedger.layer2 import session_projections as projections

    value = bare()
    prepared = state.prepare(value)
    item = projections.effective(value["premises"][0], prepared, {}, {})
    with pytest.raises(ValueError, match="documentary_origin"):
        projections.feature(item, "documented_assertion_to_corpus", prepared)


def test_derived_result_uses_local_actual_warrant_without_unrelated_pending_poison():
    value = bare()
    value["decisions"] = []
    value["premises"].append(assertion("pending", 30, "proposed"))
    value["analyses"] = [analysis("producer", age(18), ("adult", "pending"))]
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "producer", "query": age(18)},
            "origin": origin("derived", "result:producer", analysis="producer"),
            "depends_on": [],
        }
    )
    value["analyses"].append(analysis("consumer", age(18), ("derived",)))
    result = run(value)["result"]
    assert result["analyses"][0]["result"]["result"]["decision"]["status"] == "known"
    assert result["analyses"][1]["result"]["result"]["decision"]["result"] == "ENTAILED"
    assert result["analyses"][1]["result"]["result"]["decision"]["status"] == "known"
    assert result["dependency_graph"]["analysis:producer"] == ["premise:adult", "premise:pending"]
    assert result["dependency_graph"]["premise:derived"] == ["analysis:producer"]


def test_claimed_pending_support_does_weaken_dependent_assertion():
    value = bare()
    value["premises"].append(assertion("pending", 30, "proposed"))
    value["premises"][0]["depends_on"] = ["pending"]
    result = run(value)["result"]
    assert result["effective_premises"][1]["standing"]["status"] == "proposed"
    assert result["decisions"][0]["code"] == "translation_question"


def test_full_bipartite_cycle_refuses_before_solver():
    value = bare()
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "older", "query": age(65)},
            "origin": origin("derived", "result:older", analysis="older"),
            "depends_on": [],
        }
    )
    value["analyses"][0]["uses"].append(
        {"premise": "derived", "slot": "assertions", "projection": "identity"}
    )
    calls = []
    with pytest.raises(ValueError, match="dependency_cycle"):
        run(value, execute=lambda req: calls.append(req))
    assert calls == []


def test_premise_cycle_refuses_before_solver():
    value = bare()
    value["premises"][0]["depends_on"] = ["adult"]
    with pytest.raises(ValueError, match="dependency_cycle"):
        run(value)


def test_digest_mismatch_and_stale_interpretation_ref_refuse():
    value = bare()
    snap = add_source(value)
    value["sources"][0]["expected_digest"] = "bad"
    with pytest.raises(ValueError, match="source_digest_mismatch"):
        run(value)
    value["sources"][0]["expected_digest"] = snap["digest"]
    reading = assertion("reading")
    reading["origin"] = origin("source_interpretation", "ctg:NCT00000001:old#/protocolSection", "registry")
    value["premises"].append(reading)
    with pytest.raises(ValueError, match="digest_mismatch"):
        run(value)


def test_projection_collision_refuses_before_solver():
    value = bare()
    value["analyses"][0]["parameters"]["assertions"] = []
    with pytest.raises(ValueError, match="slot_collision"):
        run(value)


def test_unknown_dependency_refuses_before_solver():
    value = bare()
    value["premises"][0]["depends_on"] = ["missing"]
    with pytest.raises(ValueError, match="unknown_dependency"):
        run(value)


def test_fresh_revision_replays_both_snapshots_and_does_not_trust_old_result():
    first = bare()
    prior = run(first)
    second = deepcopy(first)
    second["revision"] = "two"
    second["parent_digest"] = state.digest(first)
    second["premises"][0] = assertion(number=65)
    calls = []

    def execute(request):
        calls.append(deepcopy(request))
        return service.run(request)

    result = session.run(
        {
            "operation": "design_session",
            "session": second,
            "previous": {
                "session": first,
                "result": prior["result"],
                "expected_result_digest": state.digest(prior["result"]),
            },
        },
        execute,
    )
    assert len(calls) == 5
    assert result["previous_fresh"]["session_digest"] == state.digest(first)
    assert result["result"]["decisions"][0]["code"] == "settled_within_declared_alternatives"
    assert all(v["code"] == "changed" for v in result["diff"]["analyses"])


def test_prior_result_digest_cannot_be_faked_and_parent_must_match():
    first = bare()
    prior = run(first)
    second = deepcopy(first)
    second.update(revision="two", parent_digest=state.digest(first))
    request = {
        "operation": "design_session",
        "session": second,
        "previous": {"session": first, "result": prior["result"], "expected_result_digest": "bad"},
    }
    with pytest.raises(ValueError, match="result_mismatch"):
        session.run(request)
    request["session"]["parent_digest"] = "bad"
    with pytest.raises(ValueError, match="parent_mismatch"):
        session.run(request)


@pytest.mark.parametrize("limit", ["max_analyses", "max_solver_work", "max_output_bytes"])
def test_aggregate_limits_refuse_without_truncation(limit):
    value = bare()
    value["limits"][limit] = 1
    with pytest.raises(ValueError, match="resource_bound"):
        run(value)


@pytest.mark.parametrize("bad", [None, [], True, float("nan"), {"extra": 1}])
def test_malformed_nested_input_refuses(bad):
    value = bare()
    value["premises"] = bad
    with pytest.raises(ValueError):
        run(value)


@pytest.mark.parametrize(
    "status,resolution", [("proposed", "resolved"), ("known", "unresolved"), ("interpolated", "conflicting")]
)
def test_pending_restriction_never_creates_clinical_freedom(status, resolution):
    value = bare()
    value["premises"][0]["payload"].update(status=status, resolution=resolution)
    assert run(value)["result"]["decisions"][0]["code"] != "design_choice"


def test_selected_refuted_option_is_blocker_but_choice_remains_recorded():
    value = bare()
    value["premises"][0] = assertion(number=65)
    value["decisions"][0]["selected"] = {
        "alternative": "younger",
        "origin": "user",
        "basis": ["user:selected"],
    }
    result = run(value)["result"]["decisions"][0]
    assert result["code"] == "blocker"
    assert result["selected"]["alternative"] == "younger"


@pytest.mark.parametrize(
    "result,blockers,accepted,matches,expected",
    [
        ("ENTAILED", [], True, True, "feasible"),
        ("ENTAILED", [], False, True, "evidence_question"),
        ("ENTAILED", ["open_scope:cohort:x"], True, True, "evidence_question"),
        ("REFUTED", [], True, True, "infeasible"),
        ("REFUTED", [], False, True, "evidence_question"),
        ("UNDETERMINED", ["undecided_by_constraints"], True, True, "feasible"),
        ("UNDETERMINED", ["no_constraint_mentions_query"], True, True, "evidence_question"),
        ("UNDETERMINED", ["undecided_by_constraints", "resource_bound"], True, True, "computation_task"),
        ("UNDETERMINED", ["proposed_refused:x"], True, True, "translation_question"),
        ("UNSUPPORTED_QUERY", [], True, True, "translation_question"),
        ("INCONSISTENT", [], True, True, "conflict"),
        ("INCONSISTENT", [], True, False, "target_mismatch"),
        ("OUT_OF_SCOPE", [], True, True, "evidence_question"),
    ],
)
def test_alternative_contract_positive_and_must_not(result, blockers, accepted, matches, expected):
    assert session.alternative_code(result, blockers, accepted, matches) == expected


@pytest.mark.parametrize(
    "has_previous,parent_matches,result_matches", list(itertools.product([False, True], repeat=3))
)
def test_revision_gate_authored_all_signs(has_previous, parent_matches, result_matches):
    expected = (
        "initial"
        if not has_previous
        else "parent_mismatch"
        if not parent_matches
        else "result_mismatch"
        if not result_matches
        else "replay"
    )
    assert state.revision_code(has_previous, parent_matches, result_matches) == expected


@pytest.mark.parametrize("before,after,equal", list(itertools.product([False, True], repeat=3)))
def test_change_gate_authored_all_signs(before, after, equal):
    expected = (
        ("unchanged" if equal else "changed")
        if before and after
        else "withdrawn"
        if before
        else "new"
        if after
        else "absent"
    )
    assert state.change_code(before, after, equal) == expected


def test_flat_thousand_premise_chain_does_not_use_python_recursion():
    value = bare()
    value["analyses"] = []
    value["decisions"] = []
    value["premises"] = [assertion("p" + str(i)) for i in range(1000)]
    for i in range(999):
        value["premises"][i]["depends_on"] = ["p" + str(i + 1)]
    result = run(value)
    assert len(result["result"]["effective_premises"]) == 1000


def test_nested_table_reservation_refuses_before_any_child_execution():
    from TrialLedger.layer2 import decision_tables

    value = bare()
    value["decisions"] = []
    value["limits"]["max_solver_work"] = 1000
    value["premises"].append(
        {
            "id": "table",
            "kind": "signal",
            "payload": {
                "id": "table",
                "kind": "decision_table",
                "data": deepcopy(decision_tables.EXAMPLES["decision_table"]),
                "support": [
                    {
                        "id": "declared-table",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["user:declared-table"],
                    }
                ],
            },
            "origin": origin("user_choice", "user:declared-table"),
            "depends_on": [],
        }
    )
    value["analyses"] = [
        {
            "id": "check",
            "operation": "signals",
            "target": target(),
            "parameters": {},
            "uses": [{"premise": "table", "slot": "signals", "projection": "identity"}],
        }
    ]
    calls = []
    with pytest.raises(ValueError, match="solver_work"):
        run(value, execute=lambda req: calls.append(req))
    assert calls == []


def test_selected_unchecked_option_retains_open_feasibility_state():
    value = bare()
    value["analyses"][0]["parameters"]["query"] = age(18, "le")
    # A distinct predicate is absent: selection is a choice, not proof it is feasible.
    query = plain(
        a.Literal(
            a.Subject("participant"),
            a.Predicate("measurement", "weight"),
            a.Value("quantity", "ge", number=10, unit="kg"),
        )
    )
    value["analyses"][0]["parameters"]["query"] = query
    value["decisions"][0]["alternatives"][0]["query"] = query
    value["decisions"][0]["selected"] = {
        "alternative": "older",
        "origin": "user",
        "basis": ["user:chooses-open-option"],
    }
    result = run(value)["result"]["decisions"][0]
    assert result["code"] == "chosen_with_open_checks"
    assert result["alternatives"][0]["code"] == "evidence_question"
    assert result["alternatives"][0]["warrant"]["blockers"] == ["no_constraint_mentions_query"]


def test_refuted_derivation_projects_negation_not_positive_query():
    value = bare()
    value["decisions"] = []
    query = age(17, "le")
    value["analyses"] = [analysis("producer", query)]
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "producer", "query": query},
            "origin": origin("derived", "result:producer", analysis="producer"),
            "depends_on": [],
        }
    )
    value["analyses"].append(analysis("consumer", query, ("derived",)))
    result = run(value)["result"]["analyses"][-1]
    assert result["request"]["assertions"][0]["body"]["class"] == "Not"
    assert result["result"]["result"]["decision"]["result"] == "REFUTED"


def test_undetermined_result_cannot_be_promoted_to_derived_fact():
    value = bare()
    value["decisions"] = []
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "older", "query": age(65)},
            "origin": origin("derived", "result:older", analysis="older"),
            "depends_on": [],
        }
    )
    with pytest.raises(ValueError, match="not_accepted"):
        run(value)


def test_derived_query_must_match_actual_query_not_only_same_analysis_id():
    value = bare()
    value["decisions"] = []
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "older", "query": age(18)},
            "origin": origin("derived", "result:older", analysis="older"),
            "depends_on": [],
        }
    )
    with pytest.raises(ValueError, match="query_identity_mismatch"):
        run(value)


def test_duplicate_source_floor_ids_are_unique_in_premise_ledger():
    value = bare()
    snap = add_source(value)
    value["decisions"] = []
    value["analyses"] = [analysis("historical", age(18), ("registered-age",), "historical")]
    value["analyses"][0]["target"]["scope"]["study"] = snap["study_ref"]
    result = run(value)["result"]["analyses"][0]
    assert result["request"]["assertions"][0]["id"] == "registered-age"
    assert result["request"]["assertions"][0]["criterion_ref"].startswith(snap["study_ref"])
    assert result["result"]["result"]["decision"]["proof"] == ["registered-age"]


def test_hypothesis_known_status_cannot_supply_fact():
    value = bare()
    value["premises"][0]["origin"]["kind"] = "hypothesis"
    with pytest.raises(ValueError, match="hypothesis_cannot_supply_fact"):
        run(value)


def test_disjoint_historical_derivation_cannot_constrain_new_target():
    value = bare()
    value["decisions"] = []
    value["analyses"] = [analysis("historical", age(18), kind="historical")]
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "historical", "query": age(18)},
            "origin": origin("derived", "result:historical", analysis="historical"),
            "depends_on": [],
        }
    )
    value["analyses"].append(analysis("consumer", age(18), ("derived",)))
    with pytest.raises(ValueError, match="derived_target_mismatch"):
        run(value)


def test_coordinate_projection_preserves_native_nsclc_owner_and_pending_standing():
    value = bare()
    value["decisions"] = []
    value["premises"].append(
        {
            "id": "coordinate",
            "kind": "coordinate_evidence",
            "payload": {
                "evidence": {
                    "section": "inclusion",
                    "concept": "stage",
                    "values": ["IV"],
                    "scope": "unspecified",
                    "ref": "invented:stage",
                },
                "standing": {
                    "status": "proposed",
                    "resolution": "resolved",
                    "basis": ["invented:stage-reading"],
                },
            },
            "origin": origin("hypothesis", "invented:stage-reading"),
            "depends_on": [],
        }
    )
    value["analyses"] = [
        {
            "id": "coordinate-check",
            "operation": "coordinates",
            "target": target("historical"),
            "parameters": {"domain": "nsclc"},
            "uses": [
                {"premise": "coordinate", "slot": "evidence", "projection": "coordinate_evidence_identity"}
            ],
        }
    ]
    row = run(value)["result"]["analyses"][0]
    assert row["request"]["evidence"][0]["standing"]["status"] == "proposed"
    assert row["result"]["code"] == "complete"
    assert row["result"] == json.loads(state.canonical(service.run(row["request"])))


def test_source_study_projection_is_scalar_actual_snapshot_and_has_replay_dependency():
    value = bare()
    snap = add_source(value)
    value["decisions"] = []
    value["analyses"] = [
        {
            "id": "source-inspection",
            "operation": "source_assertions",
            "target": target("historical"),
            "parameters": {},
            "uses": [{"premise": "registry", "slot": "study", "projection": "source_study"}],
        }
    ]
    value["analyses"][0]["target"]["scope"]["study"] = snap["study_ref"]
    result = run(value)["result"]
    assert result["dependency_graph"]["analysis:source-inspection"] == ["source:registry"]
    assert result["analyses"][0]["request"]["study"] == value["sources"][0]["study"]
    assert result["analyses"][0]["result"]["code"] == "complete"


def test_empty_session_is_inspection_not_clinical_validation():
    value = bare()
    value.update(premises=[], analyses=[], decisions=[])
    result = run(value)
    assert result["work"]["analyses"] == 0
    assert result["result"]["decisions"] == []
    assert result["result"]["analyses"] == []


def test_known_historical_question_is_settled_not_evidence_gap():
    value = bare()
    value["target"] = target("historical")
    q = age(18)
    opposite = plain(a.Not(a.from_canonical(state.canonical(q))))
    value["analyses"] = [
        analysis("older", q, kind="historical"),
        analysis("younger", opposite, kind="historical"),
    ]
    value["decisions"][0]["target"] = target("historical")
    value["decisions"][0]["alternatives"][0]["query"] = q
    value["decisions"][0]["alternatives"][1]["query"] = opposite
    assert run(value)["result"]["decisions"][0]["code"] == "settled_within_declared_alternatives"


def test_two_names_for_same_exact_query_refuse_before_execution():
    value = bare()
    value["decisions"][0]["alternatives"][1].update(analysis="older", query=age(65))
    calls = []
    with pytest.raises(ValueError, match="duplicate_alternative_query"):
        run(value, execute=lambda req: calls.append(req))
    assert calls == []


def test_two_required_entailed_facts_are_not_design_freedom():
    value = bare()
    value["analyses"] = [analysis("older", age(18)), analysis("younger", age(10))]
    value["decisions"][0]["alternatives"][0]["query"] = age(18)
    value["decisions"][0]["alternatives"][1]["query"] = age(10)
    assert run(value)["result"]["decisions"][0]["code"] == "options_not_distinguished"


def test_different_analysis_floors_do_not_claim_computed_variation():
    value = bare()
    value["premises"].append(assertion("also-adult", 18))
    value["analyses"][1]["uses"][0]["premise"] = "also-adult"
    assert run(value)["result"]["decisions"][0]["code"] == "options_not_distinguished"


def test_mismatched_historical_source_scope_refuses():
    value = bare()
    add_source(value)
    value["decisions"] = []
    value["analyses"] = [analysis("history", age(18), ("registered-age",), "historical")]
    with pytest.raises(ValueError, match="historical_source_target_mismatch"):
        run(value)


@pytest.mark.parametrize("same_nct", [False, True])
def test_documentary_feature_cannot_transfer_between_sources_or_versions(same_nct):
    value = bare()
    add_source(value)
    other = deepcopy(value["sources"][0])
    other["id"] = "other"
    if not same_nct:
        other["study"]["protocolSection"]["identificationModule"]["nctId"] = "NCT00000002"
    other["study"]["protocolSection"]["eligibilityModule"]["minimumAge"] = "65 Years"
    other["expected_digest"] = source_evidence.snapshot(other["study"])["digest"]
    value["sources"].append(other)
    value["decisions"] = []
    value["premises"].append(
        {
            "id": "trial",
            "kind": "corpus_trial",
            "payload": {
                "source": "other",
                "stratum": "set",
                "feature_uses": [
                    {"premise": "registered-age", "projection": "registered_general_age_to_corpus"}
                ],
                "metadata": {},
            },
            "origin": origin("user_choice"),
            "depends_on": [],
        }
    )
    value["analyses"] = [
        {
            "id": "rates",
            "operation": "corpus",
            "target": target("historical"),
            "parameters": {},
            "uses": [{"premise": "trial", "slot": "trials", "projection": "corpus_trial"}],
        }
    ]
    with pytest.raises(ValueError, match="corpus_feature_source_mismatch"):
        run(value)


def test_source_coordinate_reading_cannot_silently_constrain_new_trial():
    value = bare()
    snap = add_source(value)
    value["decisions"] = []
    ref = snap["study_ref"] + "#/protocolSection/eligibilityModule/eligibilityCriteria"
    value["premises"].append(
        {
            "id": "stage",
            "kind": "coordinate_evidence",
            "payload": {
                "evidence": {
                    "section": "inclusion",
                    "concept": "stage",
                    "values": ["IV"],
                    "scope": "unspecified",
                    "ref": ref,
                },
                "standing": {
                    "status": "known",
                    "resolution": "resolved",
                    "basis": ["user:confirmed-comparator-reading"],
                },
            },
            "origin": origin("source_interpretation", ref, "registry"),
            "depends_on": [],
        }
    )
    value["analyses"] = [
        {
            "id": "coordinates",
            "operation": "coordinates",
            "target": target(),
            "parameters": {"domain": "nsclc"},
            "uses": [{"premise": "stage", "slot": "evidence", "projection": "coordinate_evidence_identity"}],
        }
    ]
    with pytest.raises(ValueError, match="explicit_adoption"):
        run(value)


@pytest.mark.parametrize("dimension", ["cohort", "arm", "phase"])
def test_scoped_derived_assertion_cannot_escape_producer_context(dimension):
    value = bare()
    value["decisions"] = []
    value["premises"][0] = assertion(number=65)
    value["premises"][0]["payload"]["cohort"] = plain(a.Scope(dimension + "_ref", "A"))
    value["analyses"] = [analysis("producer", age(65)), analysis("consumer", age(65), ("derived",))]
    value["analyses"][0]["parameters"]["context"] = {dimension: "A"}
    value["analyses"][1]["parameters"]["context"] = {dimension: "B"}
    value["premises"].append(
        {
            "id": "derived",
            "kind": "derived_assertion",
            "payload": {"analysis": "producer", "query": age(65)},
            "origin": origin("derived", "result:producer", analysis="producer"),
            "depends_on": [],
        }
    )
    result = run(value)["result"]["analyses"][-1]
    assert result["result"]["result"]["decision"]["result"] == "OUT_OF_SCOPE"
    assert result["request"]["assertions"][0]["cohort"] == plain(a.Scope(dimension + "_ref", "A"))


def test_three_distinct_cutoffs_get_actual_solver_distinctions_not_syntactic_guard():
    value = bare()
    value["analyses"] = [analysis("a" + str(n), age(n)) for n in (50, 60, 70)]
    value["decisions"][0]["alternatives"] = [
        {"id": "a" + str(n), "label": str(n), "analysis": "a" + str(n), "query": age(n)} for n in (50, 60, 70)
    ]
    result = run(value)
    decision = result["result"]["decisions"][0]
    assert decision["code"] == "design_choice"
    assert len(decision["distinctions"]) == 3
    assert {v["code"] for v in decision["distinctions"]} == {"distinguishable_under_floor"}
    assert result["work"]["analyses"] == 6
    assert all(
        v["result"] == json.loads(state.canonical(service.run(v["request"])))
        for v in decision["distinctions"]
    )


def test_two_entailed_options_preserve_computed_equivalence_warrant():
    value = bare()
    value["analyses"] = [analysis("older", age(18)), analysis("younger", age(10))]
    value["decisions"][0]["alternatives"][0]["query"] = age(18)
    value["decisions"][0]["alternatives"][1]["query"] = age(10)
    decision = run(value)["result"]["decisions"][0]
    assert decision["code"] == "options_not_distinguished"
    assert decision["distinctions"][0]["code"] == "equivalent_under_floor"
    assert decision["distinctions"][0]["result"]["result"]["decision"]["result"] == "REFUTED"


def test_interpolated_feasibility_is_visible_while_independent_known_result_stays_known():
    value = bare()
    value["premises"][0]["payload"]["status"] = "interpolated"
    value["premises"].append(assertion("known-floor", 0))
    value["analyses"].append(analysis("independent", age(0), ("adult", "known-floor")))
    result = run(value)["result"]
    decision = result["decisions"][0]
    assert decision["code"] == "design_choice"
    assert decision["standing"] == "interpolated"
    assert {v["feasibility_status"] for v in decision["alternatives"]} == {"interpolated"}
    assert decision["distinctions"][0]["support_status"] == "known"
    assert decision["origin_refs"] == [{"premise": "adult", "origin": origin("user_choice", "user:adult")}]
    assert (
        next(v for v in result["analyses"] if v["id"] == "independent")["result"]["result"]["decision"][
            "status"
        ]
        == "known"
    )


def test_open_choice_has_null_feasibility_standing_and_explicit_person_origin():
    value = bare()
    query = plain(
        a.Literal(
            a.Subject("participant"),
            a.Predicate("measurement", "weight"),
            a.Value("quantity", "ge", number=10, unit="kg"),
        )
    )
    value["analyses"][0]["parameters"]["query"] = query
    value["decisions"][0]["alternatives"][0]["query"] = query
    value["decisions"][0]["selected"] = {
        "alternative": "older",
        "origin": "user",
        "basis": ["user:open-selection"],
    }
    result = run(value)["result"]["decisions"][0]
    assert result["standing"] is None
    assert result["alternatives"][0]["feasibility_status"] is None
    assert result["origin"] == {"kind": "user_choice", "basis": ["user:open-selection"]}


def test_undecided_blocker_cannot_promote_another_result_kind_to_feasible():
    assert (
        session.alternative_code("OUT_OF_SCOPE", ["undecided_by_constraints"], True, True)
        == "evidence_question"
    )


def test_all_declared_options_refuted_retains_weakest_actual_blocking_warrant():
    value = bare()
    value["premises"][0]["payload"]["status"] = "interpolated"
    value["analyses"] = [analysis("older", age(10, "le")), analysis("younger", age(15, "le"))]
    value["decisions"][0]["alternatives"][0]["query"] = age(10, "le")
    value["decisions"][0]["alternatives"][1]["query"] = age(15, "le")
    decision = run(value)["result"]["decisions"][0]
    assert decision["code"] == "blocker"
    assert decision["standing"] == "interpolated"
    assert decision["determining_alternatives"] == ["older", "younger"]
    assert {v["warrant"]["result"] for v in decision["alternatives"]} == {"REFUTED"}
