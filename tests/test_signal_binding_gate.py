"""Ordinary consumers cannot use a disputed binding to refute a design."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_bounds, entail, interpretation_bindings, signals
from TrialLedger.layer2.signal_binding_gate import gate_signals


def scope() -> dict:
    return {"study": "study", "population": "ITT:A", "arm": "A", "time": "entry", "version": "v1"}


def declaration(status: str = "known", identity: str = "population-binding") -> dict:
    return {
        "id": identity,
        "kind": "population",
        "relation": "subset_of",
        "subjects": ["parent", "subset"],
        "scope": scope(),
        "sources": [{"ref": "registry", "version": "v1", "address": "/population", "digest": "raw-sha"}],
        "status": status,
        "resolution": "resolved",
        "basis": ["source:explicit-subset"],
    }


def use(identity: str = "population-binding") -> dict:
    return {"binding": identity, "signal": "coverage", "scope": scope()}


def proposition(key: str) -> a.Literal:
    return a.Literal(a.Subject("participant"), a.Predicate("demographic", key), a.Value("boolean"))


def population() -> signals.Signal:
    return signals.Signal(
        "coverage",
        "population",
        {
            "universe": "ITT:A",
            "alignment": "confirmed",
            "total": 10,
            "parent_ref": "parent",
            "subset_relation": "confirmed",
            "subset": {"ref": "subset", "universe": "ITT:A", "lower": 8, "upper": 8},
        },
        (signals.Support("counts", "known", "resolved", ("source:counts",)),),
        {"parent": proposition("in_parent"), "subset": proposition("in_subset")},
    )


@pytest.mark.parametrize(
    "status,expected_code",
    [("known", "bounded"), ("interpolated", "bounded"), ("proposed", "unresolved")],
)
def test_standing_reaches_evaluate_derived_witness_and_candidate_claim(status: str, expected_code: str):
    original = population()
    raw, raw_use = declaration(status), use()
    before = copy.deepcopy((raw, raw_use, original))
    (gated,), checks = gate_signals((original,), [raw], [raw_use], "study")
    result = signals.evaluate(gated)
    assert result["code"] == expected_code and result["calculation_code"] == "bounded"
    assert result["status"] == status
    assert result["value"]["counts"][2] == {"id": "outside", "lower": 2, "upper": 2}
    derived = signals.derived_witness(gated, result, "outside", "ITT:A", 10)
    assert derived["lower"] == derived["upper"] == 2
    assert derived["body"] == a.AllOf((proposition("in_parent"), a.Not(proposition("in_subset"))))
    claim = {"count": "outside", "lower": None, "upper": 0}
    claim_result = signals.evaluate(gated, [claim])
    assert claim_result["calculation_code"] == "conflict"
    assert claim_result["code"] == ("unresolved" if status == "proposed" else "conflict")
    candidate = design_bounds.bound_designs(
        [("draft", ())],
        [],
        proposition("in_parent"),
        entail.EVERYONE,
        entail.MAX_ASSIGNMENTS,
        [gated],
        {"draft": [{"signal": "coverage", "claim": claim}]},
    )
    assert candidate["candidates"][0]["state"] == ("unresolved" if status == "proposed" else "ruled_out")
    if status == "proposed":
        exact = "proposed_refused:population-binding"
        assert exact in checks[0]["blockers"] and checks[0]["checked_code"] == "conditional"
        assert exact in result["blockers"] and exact in derived["blockers"]
        assert exact in candidate["candidates"][0]["signal_checks"][0]["blockers"]
    else:
        assert not derived["blockers"]
        assert candidate["candidates"][0]["elimination_status"] == status
    assert (raw, raw_use, original) == before
    assert checks[0]["declaration"]["sources"][0]["digest"] == "raw-sha"
    assert gated.support[0] is original.support[0]
    assert result["basis"] == ["source:counts", "source:explicit-subset", "registry@v1#/population"]


@pytest.mark.parametrize("axis", ["arm", "version", "time", "population", "study"])
def test_scope_disagreement_remains_exactly_unresolved_in_every_consumer(axis: str):
    application = use()
    application["scope"][axis] = "other"
    (gated,), checks = gate_signals((population(),), [declaration()], [application], "study")
    exact = ("study_mismatch" if axis == "study" else "scope_mismatch") + ":population-binding"
    result = signals.evaluate(gated)
    assert result["code"] == "unresolved" and result["calculation_code"] == "bounded"
    assert exact in checks[0]["blockers"] and exact in result["blockers"]
    derived = signals.derived_witness(gated, result, "outside", "ITT:A", 10)
    assert exact in derived["blockers"] and derived["lower"] == 2
    checked = signals.evaluate(gated, [{"count": "outside", "lower": None, "upper": 0}])
    assert checked["code"] == "unresolved" and checked["calculation_code"] == "conflict"
    assert exact in checked["blockers"]
    assert checks[0]["declaration"]["scope"] == scope()


def test_unbound_signal_existing_blockers_and_source_ids_are_preserved():
    source = population()
    collision = signals.Support("binding-use:population-binding", "known", "resolved", ("source:old",))
    source = replace(source, support=(*source.support, collision), application_blockers=("held:source",))
    independent = replace(population(), id="independent")
    (gated, untouched), checks = gate_signals((source, independent), [declaration()], [use()], "study")
    assert untouched is independent
    assert signals.evaluate(untouched) == signals.evaluate(independent)
    assert gated.data is source.data and gated.bindings is source.bindings
    assert gated.support[:2] == source.support
    assert gated.application_blockers == ("held:source",)
    assert checks[0]["support_id"] == "binding-use:population-binding:1"
    assert len({item.id for item in gated.support}) == len(gated.support)
    assert "held:source" in signals.evaluate(gated)["blockers"]


def test_multiple_binding_uses_are_conjunctive_without_support_id_collisions():
    second = declaration("proposed", "population-binding:1")
    source = replace(
        population(),
        support=(signals.Support("binding-use:population-binding", "known", "resolved", ("original",)),),
    )
    (gated,), rows = gate_signals((source,), [declaration(), second], [use(), use(second["id"])], "study")
    assert [row["support_id"] for row in rows] == [
        "binding-use:population-binding:1",
        "binding-use:population-binding:1:1",
    ]
    assert len(gated.support) == len({item.id for item in gated.support}) == 3
    result = signals.evaluate(gated)
    assert result["code"] == "unresolved" and result["status"] == "proposed"
    assert "proposed_refused:population-binding:1" in result["blockers"]


def test_existing_frame_binding_assumption_semantics_are_unchanged():
    bindings = interpretation_bindings.parse_bindings([declaration("proposed")], "study")
    uses = interpretation_bindings.parse_uses([use()], bindings, {"coverage"}, "study")
    frame_rows = interpretation_bindings.check_uses(bindings, uses, (population(),), "study")
    assert frame_rows[0]["code"] == "conditional" and not frame_rows[0]["blockers"]
    (_,), ordinary_rows = gate_signals((population(),), [declaration("proposed")], [use()], "study")
    assert ordinary_rows[0]["code"] == "unresolved"


@pytest.mark.parametrize("resolution", ["partially_resolved", "unresolved", "conflicting"])
def test_unresolved_binding_does_not_become_a_count_conflict(resolution: str):
    raw = declaration()
    raw["resolution"] = resolution
    (gated,), rows = gate_signals((population(),), [raw], [use()], "study")
    result = signals.evaluate(gated, [{"count": "outside", "lower": None, "upper": 0}])
    assert result["code"] == "unresolved" and result["calculation_code"] == "conflict"
    assert "binding_unresolved:population-binding" in rows[0]["blockers"]
    assert "binding_unresolved:population-binding" in result["blockers"]


def test_strict_parsers_remain_the_single_refusal_owner():
    with pytest.raises(ValueError, match="unknown_signal"):
        gate_signals((population(),), [declaration()], [{**use(), "signal": "absent"}], "study")
    with pytest.raises(ValueError, match="duplicate_target_identity"):
        gate_signals((population(), population()), [], [], "study")
    with pytest.raises(ValueError, match="list_required"):
        gate_signals((population(),), None, [], "study")
    signal = population()
    assert gate_signals((signal,), [], [], "study") == ((signal,), [])
