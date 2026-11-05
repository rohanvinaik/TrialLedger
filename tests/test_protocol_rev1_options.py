"""REV-1 remainder (task 5.6): option-level and decision-level revision axes with both snapshots replayed.

Axis names come from `design_session.PROTOCOL_AXES`: verdict, requirements, support, origin, scope_model,
wording, input. Rows live in `answer_diff.protocol_decisions` (one per protocol_options decision) and
`answer_diff.protocol_checks` (one per check). Every value is an invented fixture.
"""

import copy

from tests.test_protocol_options import _alt, _base, _decision, _replacement, _with_decision
from tests.test_protocol_session_replay import adoption_premise
from TrialLedger.layer2 import design_session, run, session_state

DECISION = "collection-plan"
CHECK = "week12-schedule"
SELECTION = {"alternative": "through-95", "origin": "user", "basis": ["user:invented choice"]}


def _own_edition(base: dict, upper: str, version: str, status: str = "known") -> dict:
    """A replacement collection with its own version and adoption, sharing nothing with the baseline."""
    item = _replacement(base, upper, ref=f"through {upper}")
    item["version"] = version
    item["support"] = [f"adopt:collection:{version}"]
    base["session"]["premises"] = [
        p for p in base["session"]["premises"] if p["id"] != f"adopt:collection:{version}"
    ]
    base["session"]["premises"].append(adoption_premise("collection", version, status, "resolved"))
    return item


def _plan(second_status: str = "known", baseline_status: str = "known") -> dict:
    """Two own-edition replacement plans; the baseline collection is shared by neither."""
    base = _base()
    for premise in base["session"]["premises"]:
        if premise["id"] == "adopt:collection:invented-v1":
            premise["payload"]["status"] = baseline_status
    first = _own_edition(base, "95", "alt-95")
    second = _own_edition(base, "100", "alt-100", second_status)
    return _with_decision(
        base,
        [_alt("through-95", [first], (CHECK,)), _alt("through-100", [second], (CHECK,))],
    )


def _selected(selection: dict = SELECTION) -> dict:
    request = _plan()
    request["session"]["decisions"][0]["selected"] = copy.deepcopy(selection)
    return request


def _revise(previous: dict, mutate) -> dict:
    """Run `previous`, then a revision whose session is changed by `mutate`; both are replayed by `run`."""
    first = run(previous)
    assert first["code"] == "complete", first.get("problems")
    session = copy.deepcopy(previous["session"])
    session["revision"] = "two"
    session["parent_digest"] = session_state.digest(previous["session"])
    mutate(session)
    request = copy.deepcopy(previous)
    request["session"] = session
    request["previous"] = {
        "session": copy.deepcopy(previous["session"]),
        "result": first["result"],
        "expected_result_digest": first["result_digest"],
    }
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def _row(reply: dict, section: str, identity: str) -> dict:
    rows = [row for row in reply["answer_diff"][section] if row["id"] == identity]
    assert len(rows) == 1, reply["answer_diff"][section]
    return rows[0]


def _premise(identity: str, **payload):
    def mutate(session: dict) -> None:
        item = next(p for p in session["premises"] if p["id"] == identity)
        item["payload"].update(payload)

    return mutate


def _compat(reply: dict) -> dict:
    return {a["id"]: a["compatibility"] for a in _decision(reply)["alternatives"]}


def test_the_axes_this_file_asserts_are_the_ones_the_implementation_names():
    """Guard against invented axis names: the axes used below are members of PROTOCOL_AXES."""
    assert design_session.PROTOCOL_AXES == (
        "verdict",
        "requirements",
        "support",
        "origin",
        "scope_model",
        "wording",
        "input",
    )


def test_both_snapshots_are_freshly_replayed_with_their_decision_rows():
    """The previous snapshot is a new replay, not the supplied result; the new one is replayed too."""
    previous = _plan()
    reply = _revise(previous, _premise("adopt:collection:alt-95", resolution="unresolved"))

    assert reply["previous_fresh"]["protocol"] == run(previous)["result"]["protocol"]
    assert reply["previous_fresh"]["protocol"]["decisions"], "previous snapshot lost its decision rows"
    assert _decision(reply)["alternatives"], "new snapshot lost its decision rows"
    assert _compat(reply)["through-95"] != reply["previous_fresh"]["protocol"]["decisions"][0][
        "alternatives"
    ][0].get("compatibility")


def test_a_forged_previous_result_is_refused_not_trusted():
    """MUST-NOT: a supplied previous result that differs from a fresh replay is refused (result_mismatch)."""
    previous = _plan()
    first = run(previous)
    forged = copy.deepcopy(first["result"])
    forged["protocol"]["decisions"][0]["disposition"] = "blocker"
    session = copy.deepcopy(previous["session"])
    session["revision"] = "two"
    session["parent_digest"] = session_state.digest(previous["session"])
    request = copy.deepcopy(previous)
    request["session"] = session
    request["previous"] = {
        "session": copy.deepcopy(previous["session"]),
        "result": forged,
        "expected_result_digest": first["result_digest"],
    }
    reply = run(request)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["result_mismatch"]


def test_an_option_level_residual_change_is_a_decision_requirements_change_without_a_verdict():
    """Option-level: one alternative's admission moves (proposed_refused to binding_unresolved)."""
    previous = _plan(second_status="proposed")
    reply = _revise(previous, _premise("adopt:collection:alt-100", status="known", resolution="unresolved"))

    assert _compat(run(previous)) == {
        "through-95": _compat(reply)["through-95"],
        "through-100": "undetermined",
    }
    assert _compat(reply)["through-100"] == "undetermined"
    claims = _decision(reply)["alternatives"][1]["checks"][0]["claims"]
    assert {claim["admission"] for claim in claims} == {"binding_unresolved"}

    decision_row = _row(reply, "protocol_decisions", DECISION)
    assert decision_row["code"] == "changed"
    assert decision_row["axes"] == ["requirements"]
    # The baseline check itself did not move: the change is carried by the option, not by the check.
    assert _row(reply, "protocol_checks", CHECK)["axes"] == []


def test_a_decision_level_residual_change_is_a_check_requirements_change_not_an_option_change():
    """Check-level: the baseline's admission moves; no alternative uses it, so the decision row holds."""
    previous = _plan(baseline_status="proposed")
    reply = _revise(
        previous, _premise("adopt:collection:invented-v1", status="known", resolution="unresolved")
    )

    check_axes = _row(reply, "protocol_checks", CHECK)["axes"]
    assert "requirements" in check_axes
    assert "verdict" not in check_axes
    decision_row = _row(reply, "protocol_decisions", DECISION)
    assert decision_row["code"] == "unchanged"
    assert decision_row["axes"] == []


def test_a_requirements_only_change_never_lists_verdict_in_either_section():
    """MUST-NOT: residual-only revisions are never verdict changes, for options or checks."""
    cases = (
        (
            _plan(second_status="proposed"),
            _premise("adopt:collection:alt-100", status="known", resolution="unresolved"),
        ),
        (
            _plan(baseline_status="proposed"),
            _premise("adopt:collection:invented-v1", status="known", resolution="unresolved"),
        ),
    )
    for previous, mutate in cases:
        reply = _revise(previous, mutate)
        rows = reply["answer_diff"]["protocol_decisions"] + reply["answer_diff"]["protocol_checks"]
        assert any("requirements" in row["axes"] for row in rows), rows
        for row in rows:
            assert "verdict" not in row["axes"], row


def test_an_option_change_that_moves_compatibility_is_reported_as_verdict_with_requirements():
    """Positive control: a compatibility change lists verdict, so its absence elsewhere is meaningful."""
    reply = _revise(_plan(), _premise("adopt:collection:alt-95", resolution="unresolved"))
    assert _compat(reply)["through-95"] == "undetermined"
    row = _row(reply, "protocol_decisions", DECISION)
    assert set(row["axes"]) == {"verdict", "requirements"}


def test_a_selection_change_is_never_a_verdict_change():
    """A selection moves no compatibility or disposition, so verdict must not be claimed for it."""
    previous = _selected()

    def reselect(session: dict) -> None:
        session["decisions"][0]["selected"]["alternative"] = "through-100"

    reply = _revise(previous, reselect)
    assert _compat(reply) == _compat(run(previous))
    assert _decision(reply)["disposition"] == _decision(run(previous))["disposition"]
    assert _decision(reply)["selection"]["alternative"] == "through-100"
    assert "verdict" not in _row(reply, "protocol_decisions", DECISION)["axes"]


def test_choosing_an_alternative_is_reported_as_a_changed_decision_on_the_origin_axis():
    """REV-1 contract: adding a selection is a selection/origin change, not a verdict change."""

    def choose(session: dict) -> None:
        session["decisions"][0]["selected"] = copy.deepcopy(SELECTION)

    reply = _revise(_plan(), choose)
    row = _row(reply, "protocol_decisions", DECISION)
    assert row["code"] == "changed", row
    assert "origin" in row["axes"], row
    assert "verdict" not in row["axes"], row


def test_selecting_a_different_alternative_is_reported_on_the_origin_axis():
    """REV-1 (lead's contract): moving the selection from one alternative to another is a selection change."""

    def reselect(session: dict) -> None:
        session["decisions"][0]["selected"]["alternative"] = "through-100"

    reply = _revise(_selected(), reselect)
    row = _row(reply, "protocol_decisions", DECISION)
    assert row["code"] == "changed", row
    assert "origin" in row["axes"], row
    assert "verdict" not in row["axes"], row


def test_a_changed_selection_basis_is_an_origin_change_only():
    """REV-1 (lead's contract): re-attributing the same choice gives an origin axis and nothing else."""

    def reattribute(session: dict) -> None:
        session["decisions"][0]["selected"]["basis"] = ["user:invented other exchange"]

    reply = _revise(_selected(), reattribute)
    row = _row(reply, "protocol_decisions", DECISION)
    assert row["code"] == "changed", row
    assert row["axes"] == ["origin"], row


def test_a_changed_replacement_object_origin_is_an_origin_change_only():
    """REV-1 contract: a replacement object attributed to a new caller gives origin only."""

    def reattribute(session: dict) -> None:
        alternative = session["decisions"][0]["alternatives"][0]
        alternative["replace_objects"][0]["origin"]["ref"] = "user:invented other author"

    reply = _revise(_plan(), reattribute)
    row = _row(reply, "protocol_decisions", DECISION)
    assert row["code"] == "changed", row
    assert row["axes"] == ["origin"], row


def test_a_caller_origin_change_never_changes_a_verdict_or_a_check():
    """MUST-NOT: attribution moves no computed outcome, so the check row and compatibilities are untouched."""
    previous = _plan()

    def reattribute(session: dict) -> None:
        alternative = session["decisions"][0]["alternatives"][0]
        alternative["replace_objects"][0]["origin"]["ref"] = "user:invented other author"

    reply = _revise(previous, reattribute)
    assert _compat(reply) == _compat(run(previous))
    assert "verdict" not in _row(reply, "protocol_decisions", DECISION)["axes"]
    assert _row(reply, "protocol_checks", CHECK)["axes"] == []


def test_a_question_text_change_is_a_wording_axis_only():
    """Wording: the decision question text alone changes only wording."""

    def reword(session: dict) -> None:
        session["decisions"][0]["question"] = "Invented: how long should week-12 collection run?"

    reply = _revise(_plan(), reword)
    row = _row(reply, "protocol_decisions", DECISION)
    assert (row["code"], row["axes"]) == ("changed", ["wording"])
    assert _row(reply, "protocol_checks", CHECK)["axes"] == []


def test_an_alternative_label_change_is_a_wording_axis_only():
    """Wording: an alternative label alone changes only wording."""

    def relabel(session: dict) -> None:
        session["decisions"][0]["alternatives"][1]["label"] = "Invented relabel"

    reply = _revise(_plan(), relabel)
    row = _row(reply, "protocol_decisions", DECISION)
    assert (row["code"], row["axes"]) == ("changed", ["wording"])


def test_a_wording_change_that_also_moves_compatibility_does_not_hide_the_verdict():
    """MUST-NOT: wording is not exclusive; a simultaneous compatibility change still lists verdict."""

    def both(session: dict) -> None:
        session["decisions"][0]["question"] = "Invented: reworded question?"
        _premise("adopt:collection:alt-95", resolution="unresolved")(session)

    row = _row(_revise(_plan(), both), "protocol_decisions", DECISION)
    assert "wording" in row["axes"] and "verdict" in row["axes"], row


def test_reordering_alternatives_is_not_a_change():
    """Alternatives are matched by id, so a pure reorder changes nothing."""

    def reorder(session: dict) -> None:
        session["decisions"][0]["alternatives"].reverse()

    reply = _revise(_plan(), reorder)
    row = _row(reply, "protocol_decisions", DECISION)
    assert (row["code"], row["axes"]) == ("unchanged", [])
