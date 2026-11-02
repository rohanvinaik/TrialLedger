"""The describe guide is tied to the operations it explains.

Every worked-session request runs and returns exactly the decision, proof and blockers stated beside it; the
answer guide names every decision and blocker the entailment engine can emit and every state the coordinate
and corpus results report; and "notable" names only callable components while reserving significance.
"""

import importlib
import json
import re
from pathlib import Path

from TrialLedger.layer2 import entail, guide, run

ENTAIL_SOURCE = Path(entail.__file__).read_text(encoding="utf-8")


def describe():
    reply = run({"operation": "describe", "view": "full"})
    assert reply["code"] == "complete"
    return reply["result"]


def test_every_worked_session_step_returns_its_stated_answer():
    session = describe()["worked_session"]
    assert session["premise_origin"].startswith("A demonstration brief")
    for step in session["steps"]:
        assert step["ask_plain"] and step["say"]
        reply = run(json.loads(json.dumps(step["request"])))
        assert reply["code"] == "complete", step["ask_plain"]
        decision = reply["result"]["decision"]
        got = {
            "result": decision["result"],
            "proof": list(decision["proof"]),
            "blockers": list(decision["blockers"]),
        }
        assert got == step["expect"], step["ask_plain"]


def test_the_worked_session_shows_abstention_scope_provenance_and_contradiction():
    expected = {
        (step["expect"]["result"], tuple(step["expect"]["blockers"]))
        for step in describe()["worked_session"]["steps"]
    }
    assert ("UNDETERMINED", ("undecided_by_constraints",)) in expected
    assert ("INCONSISTENT", ()) in expected
    assert any("proposed_refused:age" in blockers for _, blockers in expected)
    assert any(any(b.startswith("open_scope:") for b in blockers) for _, blockers in expected)
    assert ("UNDETERMINED", ("no_constraint_mentions_query",)) in expected


def test_two_readings_of_one_criterion_are_shown_with_different_answers():
    steps = [step for step in describe()["worked_session"]["steps"] if "exon 20" in step["ask_plain"]]
    assert {step["expect"]["result"] for step in steps} == {"REFUTED", "UNDETERMINED"}


def test_the_answer_guide_covers_every_entailment_decision_and_emitted_blocker():
    answer = describe()["answer_guide"]
    assert set(answer["entailment"]["decisions"]) == set(entail.RESULTS)
    emitted = set(re.findall(r'f"([a-z_]+):\{', ENTAIL_SOURCE))
    emitted |= set(re.findall(r'\{"([a-z_]+)"\}', ENTAIL_SOURCE)) | set(
        re.findall(r'\("([a-z_]+)",\)', ENTAIL_SOURCE)
    )
    assert emitted == set(answer["entailment"]["blockers"])
    allowed = {*guide.CATEGORIES, "translation", "by_blocker"}
    for category, meaning in [
        *answer["entailment"]["decisions"].values(),
        *answer["entailment"]["blockers"].values(),
    ]:
        assert category in allowed and meaning


def test_the_answer_guide_covers_coordinate_and_corpus_states():
    answer = describe()["answer_guide"]
    for state in ("resolved", "unresolved", "conflict", "unnarrowed"):
        assert f"known.{state}" in answer["coordinates"]
    for state in ("resolved", "unresolved", "conflict", "unnarrowed"):
        assert f"interpolated.{state}" in answer["coordinates"]
    assert "proposals" in answer["coordinates"]
    assert answer["coordinates"]["interpolated.resolved"][0] == "settled"
    assert "by default" in answer["coordinates"]["interpolated.resolved"][1]
    assert answer["coordinates"]["interpolated.unresolved"][0] == "your_call"
    for status in ("proposed", "below_support", "unresolved"):
        assert f"associations.{status}" in answer["corpus"]
    for state in ("occupied", "unknown", "empty"):
        assert f"occupancy.{state}" in answer["corpus"]
    assert answer["corpus"]["frequency.statement_rate"][0] == "settled"
    assert answer["corpus"]["frequency.range"][0] == "not_knowable_here"
    assert {"expectations.abstain", "expectations.cell_or_parent", "frequency.tier", "near_misses"} <= set(
        answer["corpus"]
    )
    for category, meaning in [*answer["coordinates"].values(), *answer["corpus"].values()]:
        assert category in guide.CATEGORIES and meaning


def test_notable_names_callable_parts_and_reserves_significance():
    answer = describe()["answer_guide"]
    notable = answer["notable"]
    entry = "TrialLedger.layer2.expectations.deviation_status"
    assert entry in notable
    module_name, name = entry.rsplit(".", 1)
    assert callable(getattr(importlib.import_module(module_name), name))
    assert "does not yet expose" in notable and "not yet built" in notable
    assert run({"operation": "deviation_status"})["code"] == "refused"
    words = {row["words"]: row for row in describe()["question_vocabulary"]}
    assert words["notable"]["computed_by"] == "see notable"
    assert words["significant (derivational significance)"]["computed_by"] == "not yet built"


def test_the_guide_states_the_operations_that_do_not_enforce_confirmation():
    confirmation = describe()["answer_guide"]["confirmation"]
    assert "Entailment refuses a proposed premise" in confirmation
    assert "confirm with the person before running" in confirmation


def test_the_described_boolean_rule_matches_the_validator():
    encoding = describe()["tagged_model"]["encoding"]
    assert "boolean_with_operand" in encoding
    session = describe()["worked_session"]
    request = json.loads(json.dumps(session["steps"][0]["request"]))
    request["assertions"][3]["body"]["value"]["members"] = ["true"]
    reply = run(request)
    assert reply["code"] == "refused" and any(
        "boolean_with_operand" in problem for problem in reply["problems"]
    )
