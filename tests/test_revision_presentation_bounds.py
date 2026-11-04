"""Retained presentation is evidence for delivery, not another logical replay input."""

from copy import deepcopy

import pytest

from TrialLedger.layer2 import design_session
from TrialLedger.layer2.service import run


def test_large_retained_views_do_not_spend_logical_input_budget_or_change_replay():
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    response = run(request)
    following = deepcopy(request["session"])
    following["revision"] = "two"
    expected = design_session.prepare_revision(request, response, following)
    response["decision_view"] = [{"caller_presentation": list(range(100001))}]
    response["answer_diff"] = {"analyses": list(range(100001))}
    assert design_session.prepare_revision(request, response, following) == expected
    assert len(response["decision_view"][0]["caller_presentation"]) == 100001
    # An altered logical result remains refused even when the display is large.
    response["result"]["session_id"] = "wrong-session"
    with pytest.raises(ValueError, match="previous_result_session_mismatch"):
        design_session.prepare_revision(request, response, following)
