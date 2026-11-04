"""The signal gate reads an operator's internal support status and resolution separately (C1.1, R6b).

A missing, unresolved or conflicting internal binding is refused as unresolved. It is never relabelled
proposed, and an accepted result keeps its operator's code.
"""

from types import SimpleNamespace

import pytest

from TrialLedger.layer2 import signals

OUTER = (signals.Support("outer", "known", "resolved", ("user:invented",)),)


def _signal() -> signals.Signal:
    return signals.Signal("s", "invented_kind", {}, OUTER, {})


def _stub(monkeypatch, envelope: dict) -> None:
    module = SimpleNamespace(
        evaluate=lambda kind, data: dict(envelope), check=lambda kind, data, claims: dict(envelope)
    )
    monkeypatch.setattr(signals, "operator", lambda kind: module)


def _envelope(status, resolution) -> dict:
    return {
        "code": "computed",
        "value": {},
        "blockers": [],
        "rule": "invented:1",
        "support_status": status,
        "determining_ids": ["invented:assumption"] if status is not None else [],
        "support_resolution": resolution,
    }


def test_accepted_internal_support_keeps_the_operator_code(monkeypatch):
    _stub(monkeypatch, _envelope("known", "resolved"))
    result = signals.evaluate(_signal())
    assert result["code"] == "computed"
    assert result["admission"]["code"] == "accepted"
    assert result["operator_support"] == {
        "status": "known",
        "determining_ids": ["invented:assumption"],
        "resolution": "resolved",
    }


def test_unresolved_internal_binding_is_refused_as_unresolved_never_relabelled_proposed(monkeypatch):
    _stub(monkeypatch, _envelope("known", "unresolved"))
    result = signals.evaluate(_signal())
    assert result["code"] == "unresolved"
    assert result["calculation_code"] == "computed"
    assert result["admission"]["code"] == "binding_unresolved"
    assert result["status"] == "known"
    assert "proposed_refused:s" not in result["blockers"]


def test_conflicting_internal_binding_is_refused(monkeypatch):
    _stub(monkeypatch, _envelope("interpolated", "conflicting"))
    result = signals.evaluate(_signal())
    assert (result["code"], result["admission"]["code"], result["status"]) == (
        "unresolved",
        "binding_unresolved",
        "interpolated",
    )


def test_a_proposed_internal_reading_is_refused_as_proposed(monkeypatch):
    _stub(monkeypatch, _envelope("proposed", "resolved"))
    result = signals.evaluate(_signal())
    assert (result["code"], result["admission"]["code"], result["status"]) == (
        "unresolved",
        "proposed_refused",
        "proposed",
    )


def test_no_internal_support_adds_nothing_to_the_outer_gate(monkeypatch):
    _stub(monkeypatch, _envelope(None, None))
    result = signals.evaluate(_signal())
    assert result["code"] == "computed"
    assert result["operator_support"]["resolution"] is None


@pytest.mark.parametrize(
    ("status", "resolution"),
    [("known", None), (None, "resolved"), ("known", "settled"), ("known", True)],
)
def test_malformed_internal_support_is_an_operator_contract_error(monkeypatch, status, resolution):
    _stub(monkeypatch, _envelope(status, resolution))
    with pytest.raises(ValueError, match="^invalid_signal_operator_support$"):
        signals.evaluate(_signal())


def test_the_two_existing_envelope_forms_are_unchanged(monkeypatch):
    plain = {"code": "consistent", "value": {}, "blockers": [], "rule": "invented:1"}
    _stub(monkeypatch, plain)
    assert "operator_support" not in signals.evaluate(_signal())
    extended = {**plain, "support_status": "interpolated", "determining_ids": ["x"]}
    _stub(monkeypatch, extended)
    result = signals.evaluate(_signal())
    assert result["operator_support"] == {"status": "interpolated", "determining_ids": ["x"]}
    assert result["code"] == "consistent"
