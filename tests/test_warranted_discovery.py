"""Discovery names real validator vocabulary and role-separated decision context."""

from TrialLedger.layer2.estimand_evidence import STRATEGIES
from TrialLedger.layer2.service import run


def test_estimand_strategies_are_exposed_from_validation_owner():
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    assert guide["operator_inputs"]["estimand"]["strategies"] == list(STRATEGIES)


def test_decision_context_is_optional_and_discoverable_without_source_code():
    guide = run({"operation": "describe", "view": "design_session", "detail": "schema"})["result"]
    decision = guide["input_shapes"]["decision"]
    assert "evidence" in decision["fields"] and "evidence" not in decision["required"]
    assert guide["input_shapes"]["decision_context"]["fields"]["role"] == ["quote", "reading", "gap"]
    assert run(guide["example"])["code"] == "complete"
