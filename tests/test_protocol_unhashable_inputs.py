"""An unhashable value where user JSON expects an id is a named refusal, never a TypeError (ty triage)."""

import copy

from tests.test_protocol_options import _alt, _base, _replacement, _with_decision
from tests.test_protocol_session_replay import _adult_body, _session, _with_condition
from TrialLedger.layer2 import run


def _decision_request() -> dict:
    base = _base()
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("as-drafted", [], ("week12-schedule",)),
    ]
    return _with_decision(base, alternatives)


def test_a_replacement_object_with_a_list_id_is_refused_by_name():
    request = _decision_request()
    request["session"]["decisions"][0]["alternatives"][0]["replace_objects"][0]["id"] = ["collection"]
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", ["protocol_option_fields"])


def test_a_selection_naming_a_list_is_refused_by_name():
    request = _decision_request()
    request["session"]["decisions"][0]["selected"] = {
        "alternative": ["as-drafted"],
        "origin": "user",
        "basis": ["user:invented choice"],
    }
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", ["protocol_option_selection"])


def test_applicability_premises_that_are_not_strings_are_refused_by_name():
    request = _with_condition(_adult_body(_session("84")), [["adult"]])
    reply = run(copy.deepcopy(request))
    assert (reply["code"], reply["problems"]) == ("refused", ["protocol_applicability_binding"])
