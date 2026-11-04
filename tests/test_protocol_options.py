"""Protocol alternatives (C8, OPT-1..OPT-5) through the public v2 design_session operation.

Written from the frozen contract before implementation. Every test calls `run` directly. Values are invented.
"""

import copy
import re

from tests.test_protocol_session_replay import _session
from TrialLedger.layer2 import run

ALL_REQUIRED = ("visit", "target", "window")
FORBIDDEN_WORDS = re.compile(r"\b(safe|effective|optimal|complete)\b", re.IGNORECASE)


def _through(upper: str) -> dict:
    return {"lower": None, "upper": upper, "lower_inclusive": False, "upper_inclusive": True}


def _base(required: tuple = ALL_REQUIRED, optional: bool = False) -> dict:
    """A v2 session: baseline collection through day 80, plus an optional window check when asked."""
    request = _session("84", collection_status="known")
    session = request["session"]
    protocol = session["protocol"]
    protocol["objects"][2]["support"] = ["adult"]
    claims = {
        "visit": {"id": "visit", "claim": "existence"},
        "target": {"id": "target", "claim": "nominal"},
        "window": {"id": "window", "claim": "full_window"},
    }
    protocol["checks"][0]["claims"] = [claims[name] for name in required]
    if optional:
        protocol["checks"].append(
            {
                "id": "week12-window",
                "kind": "schedule",
                "scope": copy.deepcopy(protocol["checks"][0]["scope"]),
                "objects": ["week12", "collection"],
                "bindings": [],
                "claims": [{"id": "window", "claim": "full_window"}],
                "required": False,
                "support": [],
            }
        )
    session["decisions"] = []
    return request


def _with_draft_premise(request: dict) -> dict:
    """Adds a proposed external premise `draft-reading` (not adopted by anyone)."""
    premise = copy.deepcopy(request["session"]["premises"][0])
    premise["id"] = premise["payload"]["id"] = "draft-reading"
    premise["payload"]["status"] = "proposed"
    request["session"]["premises"].append(premise)
    return request


def _replacement(base: dict, upper: str, *, ref: str, support: tuple = ("adult",)) -> dict:
    """A complete collection object: hypothesis origin, proposed standing, window edited only."""
    template = next(o for o in base["session"]["protocol"]["objects"] if o["id"] == "collection")
    item = copy.deepcopy(template)
    item["origin"] = {"kind": "hypothesis", "ref": f"user:invented {ref}", "source": None, "analysis": None}
    item["standing"] = {"status": "proposed", "resolution": "resolved", "basis": [f"user:invented {ref}"]}
    item["support"] = list(support)
    item["data"]["availability"] = [_through(upper)]
    return item


def _alt(identity: str, replace: list, checks: tuple) -> dict:
    return {
        "id": identity,
        "label": f"invented {identity}",
        "replace_objects": replace,
        "checks": list(checks),
    }


def _with_decision(base: dict, alternatives: list, selected: dict | None = None) -> dict:
    request = copy.deepcopy(base)
    session = request["session"]
    session["decisions"] = [
        {
            "kind": "protocol_options",
            "id": "collection-plan",
            "question": "Which invented collection window should the draft use?",
            "target": copy.deepcopy(session["target"]),
            "coverage": "declared_design",
            "selected": selected,
            "alternatives": alternatives,
        }
    ]
    return request


def _complete(request: dict) -> dict:
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def _decision(reply: dict) -> dict:
    """The protocol decision row, kept under result.protocol.decisions."""
    rows = [row for row in reply["result"]["protocol"]["decisions"] if row.get("kind") == "protocol_options"]
    assert len(rows) == 1, reply["result"]["protocol"]["decisions"]
    return rows[0]


def _baseline_protocol(reply: dict) -> dict:
    """The protocol result without its decision rows, which are the only part a decision may add."""
    return {key: value for key, value in reply["result"]["protocol"].items() if key != "decisions"}


def _row(decision: dict, identity: str) -> dict:
    return next(alt for alt in decision["alternatives"] if alt["id"] == identity)


def _check(alternative: dict, identity: str) -> dict:
    return next(check for check in alternative["checks"] if check["id"] == identity)


def _string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)


def test_opt1_two_replacements_yield_fresh_separately_retained_candidates_and_leave_the_baseline_unchanged():
    """OPT-1: distinct replacements give distinct fresh candidates; the baseline is untouched."""
    base = _base()
    early = _replacement(base, "95", ref="through 95")
    late = _replacement(base, "100", ref="through 100")
    alternatives = [
        _alt("through-95", [early], ("week12-schedule",)),
        _alt("through-100", [late], ("week12-schedule",)),
    ]
    reply = _complete(_with_decision(base, alternatives))
    without = _complete(base)

    assert _baseline_protocol(reply) == _baseline_protocol(without)

    decision = _decision(reply)
    first, second = _row(decision, "through-95"), _row(decision, "through-100")
    assert first["candidate_digest"] != second["candidate_digest"]

    baseline_children = {
        child["request_digest"]
        for check in without["result"]["protocol"]["checks"]
        for child in check["children"]
    }
    for alt in (first, second):
        child = _check(alt, "week12-schedule")["children"][0]
        assert child["request_digest"] not in baseline_children
    assert (
        _check(first, "week12-schedule")["children"][0]["result_digest"]
        != _check(second, "week12-schedule")["children"][0]["result_digest"]
    )


def test_opt2_a_required_check_left_undetermined_makes_its_alternative_undetermined():
    """OPT-2: a replacement supported by a proposed premise leaves its required claims unadmitted."""
    base = _with_draft_premise(_base())
    unsupported = _replacement(base, "95", ref="unsupported window", support=("adult", "draft-reading"))
    supported = _replacement(base, "95", ref="supported window")
    alternatives = [
        _alt("supported", [supported], ("week12-schedule",)),
        _alt("unsupported", [unsupported], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    assert _row(decision, "unsupported")["compatibility"] == "undetermined"
    assert _check(_row(decision, "unsupported"), "week12-schedule")["check_code"] == "undetermined"


def test_opt2_all_required_checks_satisfied_gives_only_declared_check_compatibility():
    """OPT-2: satisfied required checks give only declared-check compatibility."""
    base = _base()
    window = _replacement(base, "95", ref="through 95")
    alternatives = [
        _alt("through-95", [window], ("week12-schedule",)),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    row = _row(decision, "through-95")
    assert row["compatibility"] == "compatible_under_declared_checks"
    assert _check(row, "week12-schedule")["check_code"] == "satisfied"


def test_opt2_a_violated_optional_context_check_does_not_change_compatibility():
    """OPT-2: an optional context check that fails is reported beside compatibility without altering it."""
    base = _base(required=("visit",), optional=True)
    checks = ("week12-schedule", "week12-window")
    alternatives = [
        _alt("baseline-as-declared", [], checks),
        _alt("through-95", [_replacement(base, "95", ref="through 95")], checks),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    baseline = _row(decision, "baseline-as-declared")
    assert _check(baseline, "week12-window")["required"] is False
    assert _check(baseline, "week12-window")["check_code"] == "violated"
    assert baseline["compatibility"] == "compatible_under_declared_checks"
    assert _check(baseline, "week12-schedule")["check_code"] == "satisfied"


def test_opt2_no_alternative_is_ever_described_as_safe_effective_optimal_or_complete():
    """OPT-2 MUST-NOT: no alternative row or the decision uses safe/effective/optimal/complete."""
    base = _base()
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    for value in _string_values(
        {"alternatives": decision["alternatives"], "disposition": decision["disposition"]}
    ):
        assert not FORBIDDEN_WORDS.search(value), value


def test_opt3_a_selected_incompatible_alternative_stays_selected_and_blocks_the_decision():
    """OPT-3: selection is retained verbatim, and an incompatible selected alternative is a blocker."""
    base = _base()
    selection = {"alternative": "through-80-edit", "origin": "user", "basis": ["user:invented choice"]}
    alternatives = [
        _alt("through-80-edit", [_replacement(base, "80", ref="through 80")], ("week12-schedule",)),
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives, selected=selection)))

    assert decision["selection"] == selection
    assert _row(decision, "through-80-edit")["compatibility"] == "incompatible_under_declared_checks"
    assert decision["disposition"] == "blocker"


def test_opt4_an_unchosen_hypothetical_replacement_is_a_hypothetical_frame_with_withheld_application():
    """OPT-4: a hypothesis replacement is hypothetical, names its assumption, and is withheld."""
    base = _base()
    alternatives = [
        _alt("baseline-as-declared", [], ("week12-schedule",)),
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    hypothetical = _row(decision, "through-95")
    assert hypothetical["frame"] == "hypothetical"
    assert hypothetical["assumption_refs"] == ["collection"]
    assert hypothetical["unconditional_application"] == "withheld"
    assert _check(hypothetical, "week12-schedule")["check_code"] == "satisfied"

    fixed = _row(decision, "baseline-as-declared")
    assert fixed["frame"] == "fixed"
    assert fixed["assumption_refs"] == []


def test_opt4_hypothesis_standing_stays_proposed_and_proposed_external_support_is_not_lifted():
    """OPT-4: replacement standing is never promoted; proposed external support is not lifted."""
    base = _with_draft_premise(_base())
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt(
            "unsupported",
            [_replacement(base, "95", ref="unsupported", support=("adult", "draft-reading"))],
            ("week12-schedule",),
        ),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    hypothetical = _check(_row(decision, "through-95"), "week12-schedule")
    existence = next(claim for claim in hypothetical["claims"] if claim["claim"] == "existence")
    assert existence["finding_status"] == "proposed"

    unsupported = _row(decision, "unsupported")
    assert unsupported["compatibility"] == "undetermined"
    existence = next(
        claim for claim in _check(unsupported, "week12-schedule")["claims"] if claim["claim"] == "existence"
    )
    assert existence["admission"] == "proposed_refused"


def test_opt5_an_alternative_omitting_a_required_check_is_refused():
    """OPT-5: dropping a required check from one alternative is a named refusal."""
    base = _base(optional=True)
    alternatives = [
        _alt(
            "through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule", "week12-window")
        ),
        _alt("optional-only", [], ("week12-window",)),
    ]
    reply = run(_with_decision(base, alternatives))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_option_missing_required_check"]


def test_opt5_differing_optional_context_checks_are_refused():
    """OPT-5: optional context checks must be listed identically by every alternative."""
    base = _base(optional=True)
    alternatives = [
        _alt(
            "through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule", "week12-window")
        ),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    reply = run(_with_decision(base, alternatives))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_option_context_mismatch"]


def test_opt5_a_replacement_that_changes_kind_is_refused():
    """OPT-5: a replacement may never change an object's kind."""
    base = _base()
    changed = copy.deepcopy(_replacement(base, "95", ref="through 95"))
    changed["kind"] = "assessment"
    alternatives = [
        _alt("through-95", [changed], ("week12-schedule",)),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    reply = run(_with_decision(base, alternatives))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_option_kind_changed"]


def test_opt5_a_replacement_for_an_unknown_object_is_refused():
    """OPT-5: replacements must name an object that already exists in the session protocol."""
    base = _base()
    unknown = copy.deepcopy(_replacement(base, "95", ref="through 95"))
    unknown["id"] = "nonexistent"
    alternatives = [
        _alt("through-95", [unknown], ("week12-schedule",)),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    reply = run(_with_decision(base, alternatives))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_option_unknown_object"]


def test_opt5_a_single_alternative_is_refused_by_count():
    """OPT-5: a protocol option decision needs at least two alternatives."""
    base = _base()
    alternatives = [_alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",))]
    reply = run(_with_decision(base, alternatives))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_option_count"]


def test_two_compatible_alternatives_with_different_content_are_a_design_choice():
    """Disposition: two compatible alternatives whose candidates differ give design_choice."""
    base = _base()
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("through-100", [_replacement(base, "100", ref="through 100")], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    assert _row(decision, "through-95")["compatibility"] == "compatible_under_declared_checks"
    assert _row(decision, "through-100")["compatibility"] == "compatible_under_declared_checks"
    assert decision["disposition"] == "design_choice"


def test_two_compatible_alternatives_with_identical_candidates_are_not_a_design_choice():
    """Disposition: identical candidate content is not a design choice, whatever the labels."""
    base = _base()
    alternatives = [
        _alt("through-95-first", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("through-95-second", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    first, second = _row(decision, "through-95-first"), _row(decision, "through-95-second")
    assert first["candidate_digest"] == second["candidate_digest"]
    assert decision["disposition"] != "design_choice"


def test_a_conditional_required_check_whose_claims_pass_is_compatible_and_listed_as_conditional():
    """Conditional claims: passing conditional claims satisfy the check and stay listed as conditional."""
    base = _base()
    condition = {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
        "predicate": {"class": "Predicate", "kind": "treatment_history", "key": "discontinued_study_drug"},
        "value": {"class": "Value", "kind": "boolean"},
        "polarity": "positive",
        "time": None,
        "qualifiers": {"class": "Always"},
        "evidence": [],
    }
    base["session"]["protocol"]["objects"][1]["data"]["condition"] = condition
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("baseline-as-declared", [], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))

    row = _row(decision, "through-95")
    check = _check(row, "week12-schedule")
    assert {claim["application"] for claim in check["claims"]} == {"conditional"}
    assert check["check_code"] == "satisfied"
    assert row["compatibility"] == "compatible_under_declared_checks"
    assert "week12-schedule" in row["conditional_checks"]
    assert check["conditional_claims"]
