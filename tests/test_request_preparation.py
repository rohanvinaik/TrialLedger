"""Small typed requests must preserve meaning and must never claim clinical computation.

All choices and profiles are invented teaching fixtures, never actual confirmations.
"""

import json
from copy import deepcopy

import pytest

from TrialLedger import reasoning_artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.cli import main
from TrialLedger.evidence_access import pointer_value
from TrialLedger.layer2 import entail, run
from TrialLedger.layer2 import request_preparation as prepare
from TrialLedger.mcp_server import Context, call_tool
from TrialLedger.reasoning_cards import describe_card


def boolean(key, **fields):
    return {"kind": "boolean", "predicate": {"kind": "condition_status", "key": key}, **fields}


def criterion(body, **fields):
    return {
        "id": "criterion",
        "modality": "required",
        "body": body,
        "origin": {"kind": "user_choice", "ref": "invented:brief"},
        "status": "known",
        "resolution": "resolved",
        **fields,
    }


def request(body, query, **fields):
    return {
        "operation": "prepare",
        "for": "entailment",
        "criteria": [criterion(body)],
        "query": query,
        **fields,
    }


def prepared(payload):
    reply = run(payload)
    assert reply["code"] == "complete", reply["problems"]
    assert set(reply["result"]) == {"request", "defaults", "origins", "limits_of_claim"}
    return reply["result"]


@pytest.mark.parametrize(
    "keys,expected",
    [
        (["class"], "canonical"),
        (["all"], "all"),
        (["any"], "any"),
        (["not"], "not"),
        (["kind"], "literal"),
        (["all", "any"], "invalid_compound"),
        (["not", "kind"], "invalid_compound"),
        (["all", "note"], "invalid_compound"),
        ([], "invalid_node"),
        (["prose"], "invalid_node"),
    ],
)
def test_compact_syntax_selects_exact_declared_branch_not_token_meaning(keys, expected):
    assert prepare.compact_node_code(keys) == expected


@pytest.mark.parametrize("factory", [prepare.example, prepare.session_example])
def test_every_reported_default_names_its_actual_expanded_value(factory):
    result = prepared(factory())
    assert result["defaults"]
    for default in result["defaults"]:
        code, value = pointer_value(result, default["path"])
        assert code == "ok", default
        assert value == default["value"], default
    assert run(result["request"])["code"] == "complete"


def test_preparation_never_invokes_solver_or_source_reader(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preparation may construct typed requests but must not compute or fetch")

    monkeypatch.setattr(entail, "decide", forbidden)
    result = prepared(prepare.example())
    assert result["request"]["operation"] == "entailment"
    assert "no clinical answer" in result["limits_of_claim"][0].lower()


def test_missing_standing_stays_proposed_and_unresolved_even_for_declared_user_choice():
    payload = prepare.example()
    del payload["criteria"][0]["status"]
    del payload["criteria"][0]["resolution"]
    result = prepared(payload)
    assertion = result["request"]["assertions"][0]
    assert assertion["status"] == "proposed" and assertion["resolution"] == "unresolved"
    answer = run(result["request"])
    assert answer["result"]["decision"]["result"] == "UNDETERMINED"
    assert "proposed_refused:age" in answer["result"]["decision"]["blockers"]


def test_source_reading_origin_is_retained_and_never_implicitly_admitted():
    payload = request(boolean("A"), boolean("A"))
    payload["criteria"][0]["origin"] = {
        "kind": "source_interpretation",
        "ref": "invented:source#criterion",
        "source": "source-one",
        "analysis": None,
    }
    del payload["criteria"][0]["status"]
    del payload["criteria"][0]["resolution"]
    result = prepared(payload)
    assert result["origins"][0]["origin"] == payload["criteria"][0]["origin"]
    assert result["request"]["assertions"][0]["status"] == "proposed"
    assert result["request"]["assertions"][0]["criterion_ref"] == "invented:source#criterion"


def test_all_and_any_keep_different_clinical_answers():
    for connector, expected in (("all", "ENTAILED"), ("any", "UNDETERMINED")):
        result = prepared(request({connector: [boolean("A"), boolean("B")]}, boolean("A")))
        assert run(result["request"])["result"]["decision"]["result"] == expected


def test_qualified_exclusion_never_flattens_into_excluding_every_unqualified_profile():
    body = boolean("A", qualifiers=boolean("B"))
    payload = request(body, boolean("A"))
    payload["criteria"][0]["modality"] = "excluded"
    result = prepared(payload)
    assert run(result["request"])["result"]["decision"]["result"] == "UNDETERMINED"
    payload["query"] = {"all": [boolean("A"), boolean("B")]}
    assert run(prepared(payload)["request"])["result"]["decision"]["result"] == "REFUTED"


def test_conditional_requirement_never_requires_its_antecedent():
    payload = request(boolean("stable"), boolean("uses-drug"))
    payload["criteria"][0]["applicability"] = boolean("uses-drug")
    result = prepared(payload)
    assert run(result["request"])["result"]["decision"]["result"] == "UNDETERMINED"
    assert result["request"]["assertions"][0]["applicability"]["predicate"]["key"] == "uses-drug"


def test_explicit_cohort_subject_time_unit_and_boundary_are_not_normalized():
    atom = {
        "kind": "quantity",
        "predicate": {"kind": "medication_stability", "key": "washout"},
        "comparison": "ge",
        "number": 21,
        "unit": "days",
        "inclusivity": "exclusive",
        "subject": {"kind": "partner", "referent": "partner-one"},
        "polarity": "negative",
        "time": {
            "orientation": "before",
            "anchor": "named_event",
            "anchor_ref": "screening",
            "lower": 0,
            "upper": 21,
            "unit": "days",
            "inclusivity": "inclusive",
            "certainty": "explicit",
        },
    }
    payload = request(atom, deepcopy(atom), context={"cohort": "C"})
    payload["criteria"][0]["cohort"] = {"kind": "cohort_ref", "ref": "C"}
    result = prepared(payload)
    assertion = result["request"]["assertions"][0]
    assert assertion["cohort"]["ref"] == "C"
    assert assertion["body"]["subject"]["kind"] == "partner"
    assert assertion["body"]["value"]["unit"] == "days"
    assert assertion["body"]["value"]["inclusivity"] == "exclusive"
    assert assertion["body"]["time"]["anchor_ref"] == "screening"
    assert assertion["body"]["polarity"] == "negative"
    assert result["request"]["context"] == {"cohort": "C", "phase": None, "arm": None}


def test_enum_and_enum_set_are_not_treated_as_equivalent():
    for kind in ("enum", "enum_set"):
        atom = {
            "kind": kind,
            "predicate": {"kind": "disease_attribute", "key": "markers"},
            "comparison": "in",
            "members": ["A", "B"],
        }
        result = prepared(request(atom, atom))
        assert result["request"]["assertions"][0]["body"]["value"]["kind"] == kind
        assert result["request"]["query"]["value"]["members"] == ["A", "B"]


def test_existing_canonical_proposition_passes_through_validated():
    canonical = prepared(request(boolean("A"), boolean("A")))["request"]["query"]
    result = prepared(request(canonical, {"not": canonical}))
    assert result["request"]["assertions"][0]["body"] == canonical
    assert result["request"]["query"] == {"class": "Not", "part": canonical}


def test_session_projection_defaults_and_explicit_criterion_subset_are_inspectable():
    payload = prepare.session_example()
    other = criterion(boolean("B"), id="other")
    payload["criteria"].append(other)
    full = prepared(payload)
    assert all(
        [use["premise"] for use in analysis["uses"]] == ["age", "other"]
        for analysis in full["request"]["session"]["analyses"]
    )
    assert any(row["path"].endswith("/uses") for row in full["defaults"])
    payload["questions"][0]["criteria"] = ["age"]
    selected = prepared(payload)
    assert all(
        [use["premise"] for use in analysis["uses"]] == ["age"]
        for analysis in selected["request"]["session"]["analyses"]
    )
    assert not any(row["path"].endswith("/uses") for row in selected["defaults"])


def test_prepare_keeps_raw_source_handles_unchanged_until_execution():
    payload = prepare.session_example()
    marker = {"$retained_study": {"run": "unavailable", "nct": "NCT00000001", "digest": "a" * 64}}
    payload["sources"] = [{"id": "source", "study": marker, "expected_digest": "a" * 64}]
    result = prepared(payload)
    assert result["request"]["session"]["sources"] == payload["sources"]
    assert payload["sources"][0]["study"] == marker


def test_advanced_canonical_analysis_is_retained_without_execution():
    payload = prepare.session_example()
    canonical_query = prepared(prepare.example())["request"]["query"]
    analysis = {
        "id": "advanced",
        "operation": "entailment",
        "target": deepcopy(payload["target"]),
        "parameters": {"query": canonical_query, "bound": 8},
        "uses": [{"premise": "age", "slot": "assertions", "projection": "identity"}],
    }
    payload["analyses"] = [analysis]
    result = prepared(payload)
    assert result["request"]["session"]["analyses"][0] == analysis


@pytest.mark.parametrize("field", ["comparison", "unit", "inclusivity"])
def test_quantity_requires_material_numeric_choices_instead_of_guessing(field):
    payload = prepare.example()
    del payload["criteria"][0]["body"][field]
    result = run(payload)
    assert result["code"] == "refused" and result["problems"][0].startswith("missing_field:")


@pytest.mark.parametrize(
    "where,field,value",
    [
        ("root", "unexpected", True),
        ("criterion", "force", "required"),
        ("origin", "confirmed", True),
        ("body", "words", "age 18"),
        ("criterion", "status", "confirmed"),
        ("criterion", "modality", "must"),
    ],
)
def test_unknown_fields_or_vocabularies_never_silently_become_a_rule(where, field, value):
    payload = prepare.example()
    target = (
        payload
        if where == "root"
        else payload["criteria"][0]
        if where == "criterion"
        else payload["criteria"][0][where]
    )
    target[field] = value
    result = run(payload)
    assert result["code"] == "refused" and result["result"] is None


@pytest.mark.parametrize(
    "query",
    [
        None,
        "ECOG must be zero",
        {"all": []},
        {"all": [boolean("A")]},
        {"all": [boolean("A"), boolean("B")], "not": boolean("C")},
        {"kind": "boolean", "predicate": {"kind": "measurement", "key": "A"}, "number": 1},
    ],
)
def test_malformed_or_prose_queries_are_refused_not_interpreted(query):
    result = run(request(boolean("A"), query))
    assert result["code"] == "refused"


@pytest.mark.parametrize(
    "options",
    [
        [],
        [{"id": "one", "label": "Only one", "query": boolean("A")}],
        [
            {"id": "same", "label": "A", "query": boolean("A")},
            {"id": "same", "label": "B", "query": boolean("B")},
        ],
    ],
)
def test_session_requires_distinct_real_options_at_least_two(options):
    payload = prepare.session_example()
    payload["questions"][0]["options"] = options
    assert run(payload)["code"] == "refused"


def test_selection_must_name_an_actual_alternative_and_never_confers_source_truth():
    payload = prepare.session_example()
    payload["questions"][0]["selected"] = {
        "alternative": "missing",
        "origin": "user",
        "basis": ["invented:choice"],
    }
    assert run(payload)["code"] == "refused"
    payload["questions"][0]["selected"]["alternative"] = "eighteen"
    result = prepared(payload)
    assert result["request"]["session"]["decisions"][0]["selected"] == payload["questions"][0]["selected"]


def test_no_input_mutation_and_returned_objects_are_detached():
    payload = prepare.session_example()
    before = deepcopy(payload)
    result = prepared(payload)
    result["request"]["session"]["premises"][0]["payload"]["status"] = "proposed"
    assert payload == before


def test_prepare_is_inspection_with_no_computed_clinical_finding():
    reply = run(prepare.example())
    assert reply["code"] == "complete"
    assert reply["metadata"]["kind"] == "inspection"
    assert reply["metadata"]["findings"] == []
    assert reply["clinical"]["findings"] == []


def test_cli_mcp_prepare_and_run_need_only_public_json_requests(tmp_path, capsys):
    payload = prepare.session_example()
    path = tmp_path / "prepare.json"
    path.write_text(json.dumps(payload))
    assert main(["reason", "--request", str(path)]) == 0
    cli = json.loads(capsys.readouterr().out)
    code, wire = call_tool(Context(tmp_path), {"name": "reason", "arguments": {"request": payload}})
    assert code == "ok" and not wire["isError"]
    remote = json.loads(wire["content"][0]["text"])
    remote.pop("tool")
    assert remote == cli
    runnable = remote["result"]["request"]
    code, computed = call_tool(
        Context(tmp_path), {"name": "reason", "arguments": {"request": runnable, "retain": True}}
    )
    assert code == "ok" and not computed["isError"]
    result = json.loads(computed["content"][0]["text"])
    stored = reasoning_artifacts.load(tmp_path / ".reasoning", result["artifact"]["id"])
    assert stored["request"] == runnable
    assert stored["response"]["result"]["decisions"][0]["code"] == "settled_within_declared_alternatives"


def test_small_card_and_schema_publish_runnable_examples_and_source_handle_contract():
    for detail in ("card", "schema", "full"):
        response = run({"operation": "describe", "view": "prepare", "detail": detail})
        assert response["code"] == "complete"
        card = response["result"]
        assert len(json.dumps(card).encode()) < 12000
        assert run(card["example"])["code"] == "complete"
        assert run(card["session_example"])["code"] == "complete"
    assert "source_handles" in describe_card("delivery")
    assert "source_handles" in describe_card("source_assertions")


def definition_session():
    payload = prepare.session_example()
    standing = {"status": "known", "resolution": "resolved", "basis": ["invented:definition-reading"]}
    payload["definition_checks"] = [
        {
            "id": "age-profile-relation",
            "relation": "equivalent",
            **deepcopy(standing),
            "left": {
                "analysis": "question:age-choice:option:seventeen",
                "address": "/request/query",
                "body": deepcopy(payload["questions"][0]["options"][0]["query"]),
                **deepcopy(standing),
            },
            "right": {
                "analysis": "question:age-choice:option:eighteen",
                "address": "/request/query",
                "body": deepcopy(payload["questions"][0]["options"][1]["query"]),
                **deepcopy(standing),
            },
        }
    ]
    return payload


def test_definition_compact_bodies_expand_without_losing_addresses_standing_or_basis():
    payload = definition_session()
    result = prepared(payload)
    check = result["request"]["session"]["definition_checks"][0]
    assert check["left"]["body"]["class"] == "Literal"
    assert check["right"]["body"]["value"]["number"] == 18
    for side in ("left", "right"):
        assert {key: value for key, value in check[side].items() if key != "body"} == {
            key: value for key, value in payload["definition_checks"][0][side].items() if key != "body"
        }
    for default in result["defaults"]:
        assert pointer_value(result, default["path"]) == ("ok", default["value"])
    computed = run(result["request"])
    assert computed["code"] == "complete"
    assert computed["result"]["definition_checks"][0]["code"] == "conflict"


def test_definition_revision_replays_changed_declared_relation_with_new_basis(tmp_path):
    construction = prepared(definition_session())
    first = delivery.execute(construction["request"], store=tmp_path)
    revised = delivery.revise(
        tmp_path,
        first["artifact"]["id"],
        revision="two",
        response_view="full",
        edits=[
            {"op": "replace", "path": "/definition_checks/0/relation", "value": "disjoint"},
            {
                "op": "replace",
                "path": "/definition_checks/0/basis",
                "value": ["invented:new-relation-choice"],
            },
        ],
    )
    assert revised["code"] == "complete"
    assert revised["result"]["definition_checks"][0]["code"] == "consistent"
    assert revised["previous_fresh"]["definition_checks"][0]["code"] == "conflict"
    assert revised["result"]["definition_checks"][0]["basis"] == ["invented:new-relation-choice"]


@pytest.mark.parametrize(
    "request_operation,response_operation,code,expanded_operation,expected",
    [
        ("prepare", "prepare", "complete", "entailment", "prepared_request"),
        ("prepare", "prepare", "complete", "design_session", "prepared_request"),
        ("entailment", "prepare", "complete", "entailment", "not_preparation_artifact"),
        ("prepare", "entailment", "complete", "entailment", "not_preparation_artifact"),
        ("prepare", "prepare", "refused", "entailment", "preparation_not_complete"),
        ("prepare", "prepare", "complete", "prepare", "invalid_prepared_request"),
        ("prepare", "prepare", "complete", "", "invalid_prepared_request"),
    ],
)
def test_prepared_artifact_guard_never_treats_an_answer_as_an_executable_preparation(
    request_operation, response_operation, code, expanded_operation, expected
):
    assert (
        delivery.prepared_artifact_code(request_operation, response_operation, code, expanded_operation)
        == expected
    )


def invoke_mcp(root, arguments):
    code, wire = call_tool(Context(root), {"name": "reason", "arguments": arguments})
    assert code == "ok"
    response = json.loads(wire["content"][0]["text"])
    response.pop("tool")
    return response, wire["isError"]


def test_no_copy_preparation_handoff_cli_mcp_parity_and_full_origin_retention(tmp_path, capsys):
    path = tmp_path / "prepare.json"
    path.write_text(json.dumps(prepare.session_example()))
    store = tmp_path / ".reasoning"
    assert main(["reason", "--request", str(path), "--store", str(store), "--compact"]) == 0
    built = json.loads(capsys.readouterr().out)
    identity = built["artifact"]["id"]
    assert main(["reason", "--prepared", identity, "--store", str(store), "--compact"]) == 0
    cli = json.loads(capsys.readouterr().out)
    remote, error = invoke_mcp(tmp_path, {"prepared": identity, "response_view": "compact"})
    assert not error and cli == remote
    original = reasoning_artifacts.load(store, identity)
    computed = reasoning_artifacts.load(store, remote["artifact"]["id"])
    assert computed["request"] == original["response"]["result"]["request"]
    assert computed["response"]["preparation"]["origins"] == original["response"]["result"]["origins"]
    assert computed["response"]["preparation"]["defaults"] == original["response"]["result"]["defaults"]
    assert remote["preparation"]["artifact"] == identity
    assert isinstance(remote["preparation"]["defaults"], int)
    revised = delivery.revise(
        store,
        remote["artifact"]["id"],
        revision="two",
        edits=[{"op": "replace", "path": "/decisions/0/question", "value": "Reworded invented question"}],
    )
    revised_canonical = reasoning_artifacts.load(store, revised["artifact"]["id"])
    assert (
        revised_canonical["response"]["preparation"]["origins"] == original["response"]["result"]["origins"]
    )
    assert "current premises and edits take precedence" in revised["preparation"]["applies_to"]


@pytest.mark.parametrize("budget", [2048, 4096, 24576])
def test_compact_preparation_and_execution_never_echo_the_full_defaults_ledger(tmp_path, budget):
    from TrialLedger.record_access import response_bytes

    built, error = invoke_mcp(
        tmp_path, {"request": prepare.session_example(), "response_view": "compact", "max_bytes": budget}
    )
    assert not error and response_bytes(built) <= budget
    computed, error = invoke_mcp(
        tmp_path, {"prepared": built["artifact"]["id"], "response_view": "compact", "max_bytes": budget}
    )
    assert not error and response_bytes(computed) <= budget
    assert isinstance(computed["preparation"]["defaults"], int)
    assert "origins" not in computed["preparation"] or isinstance(computed["preparation"]["origins"], int)


def test_wrong_artifact_type_and_modified_artifact_are_named_refusals(tmp_path):
    ordinary = delivery.execute(prepared(prepare.example())["request"], store=tmp_path / ".reasoning")
    result, error = invoke_mcp(tmp_path, {"prepared": ordinary["artifact"]["id"]})
    assert error and result["problems"] == ["not_preparation_artifact"]
    built, error = invoke_mcp(tmp_path, {"request": prepare.example(), "retain": True})
    assert not error
    path = tmp_path / ".reasoning" / (built["artifact"]["id"] + ".json")
    path.write_bytes(path.read_bytes() + b" ")
    result, error = invoke_mcp(tmp_path, {"prepared": built["artifact"]["id"]})
    assert error and result["problems"] == ["artifact_changed"]


def test_prepared_requires_a_store_and_request_prepared_are_mutually_exclusive(tmp_path, capsys):
    assert main(["reason", "--prepared", "a" * 64]) == 2
    assert json.loads(capsys.readouterr().out)["problems"] == ["prepared_requires_artifact_store"]
    for arguments in ({}, {"request": prepare.example(), "prepared": "a" * 64}):
        result, error = invoke_mcp(tmp_path, arguments)
        assert error and result["problems"] == ["reason_requires_request_or_prepared"]


def test_source_changed_after_preparation_is_refused_before_computation(tmp_path, monkeypatch):
    from test_retained_sources import saved

    folder, _, marker = saved(tmp_path)
    payload = prepare.session_example()
    payload["sources"] = [
        {"id": "source", "study": marker, "expected_digest": marker["$retained_study"]["digest"]}
    ]
    built, error = invoke_mcp(tmp_path, {"request": payload, "response_view": "compact"})
    assert not error
    (folder / "bodies/studies-001.json").write_text(
        json.dumps({"studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}]})
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed source must refuse before the solver runs")

    monkeypatch.setattr(entail, "decide", forbidden)
    result, error = invoke_mcp(tmp_path, {"prepared": built["artifact"]["id"]})
    assert error and result["problems"] == ["source_body_digest_mismatch"]
