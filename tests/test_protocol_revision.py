"""Protocol revisions report independent answer_diff axes from freshly replayed snapshots (C9, REV-1).

Every premise here is an invented fixture; no clinical record, exchange or confirmation is represented.
"""

import copy

from test_protocol_session_replay import _session, adopt, adoption_premise

from TrialLedger.layer2 import run, session_state

CHECK = "week12-schedule"
DECISION = "age-policy"


def _plan(collection_status: str = "known", adopted: bool = True) -> dict:
    request = _session("84", collection_status=collection_status)
    if adopted:
        adopt(request, "collection")
    return request


def _revise(previous: dict, mutate) -> dict:
    """Run the previous v2 request, then a revision whose session is changed by mutate."""
    first = run(previous)
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
    return run(request)


def _adoption_rows(reply: dict) -> list[dict]:
    from TrialLedger.layer2 import protocol_view

    return protocol_view.view(reply["result"])["adoption"]


def _row(rows: list, identity: str) -> dict:
    matches = [row for row in rows if row["id"] == identity]
    assert len(matches) == 1, rows
    return matches[0]


def _set_window_upper(upper: str):
    """An instructed plan change: new content is a new edition, re-adopted with it when it was adopted.

    Content changed under an unchanged version is refused on every revision path (Rohan, 2026-11-04).
    """

    def mutate(session: dict) -> None:
        collection = session["protocol"]["objects"][2]
        old = collection["version"]
        collection["data"]["availability"][0]["upper"] = upper
        collection["version"] = f"{old}-through-{upper}"
        if f"adopt:collection:{old}" in collection["support"]:
            session["premises"].append(adoption_premise("collection", collection["version"]))
            collection["support"] = [f"adopt:collection:{collection['version']}"]

    return mutate


def test_a_collection_window_change_that_moves_a_claim_outcome_is_a_verdict_change():
    """Widening collection availability changes nominal's effective outcome, so verdict is set."""
    reply = _revise(_plan(), _set_window_upper("90"))
    assert reply["code"] == "complete", reply
    row = _row(reply["answer_diff"]["protocol_checks"], CHECK)
    assert row["code"] == "changed"
    assert "verdict" in row["axes"]


def test_a_standing_change_that_only_refuses_admission_is_a_requirements_change():
    """Without adoption support, a proposed plan changes admission; effective outcomes stay unresolved."""
    previous = _plan(collection_status="known", adopted=False)

    def mutate(session: dict) -> None:
        session["protocol"]["objects"][2]["standing"]["status"] = "proposed"

    reply = _revise(previous, mutate)
    assert reply["code"] == "complete", reply
    axes = _row(reply["answer_diff"]["protocol_checks"], CHECK)["axes"]
    assert "requirements" in axes
    assert "verdict" not in axes


def test_a_requirements_only_change_never_lists_verdict_for_any_decision_or_check():
    """MUST-NOT: a residual-only change is never reported as a verdict change in either section."""
    previous = _plan(collection_status="known", adopted=False)

    def mutate(session: dict) -> None:
        session["protocol"]["objects"][2]["standing"]["status"] = "proposed"

    protocol = _revise(previous, mutate)["answer_diff"]
    for row in protocol["protocol_checks"] + protocol["protocol_decisions"]:
        assert "verdict" not in row["axes"], row


def test_a_known_check_level_premise_is_a_support_change_not_a_verdict():
    """A new known premise named by the check gains support on every claim; admission and outcomes hold."""

    def mutate(session: dict) -> None:
        copy_premise = copy.deepcopy(session["premises"][0])
        copy_premise["id"] = copy_premise["payload"]["id"] = "adult-copy"
        session["premises"].append(copy_premise)
        session["protocol"]["checks"][0]["support"] = ["adult-copy"]

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "complete", reply
    axes = _row(reply["answer_diff"]["protocol_checks"], CHECK)["axes"]
    assert "support" in axes
    assert "verdict" not in axes


def test_an_origin_reference_change_is_an_origin_change_only():
    """Changing only an involved object's origin.ref sets origin, and not verdict."""

    def mutate(session: dict) -> None:
        session["protocol"]["objects"][2]["origin"]["ref"] = "user:invented week-12 plan, revised label"

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "complete", reply
    axes = _row(reply["answer_diff"]["protocol_checks"], CHECK)["axes"]
    assert "origin" in axes
    assert "verdict" not in axes


def test_an_object_version_change_is_a_scope_model_change_only():
    """Changing only an involved object's version sets scope_model, and not verdict."""

    def mutate(session: dict) -> None:
        item = session["protocol"]["objects"][2]
        item["version"] = "invented-v2"
        # The adoption names the exact object version, so it follows the new edition.
        old = next(p for p in session["premises"] if p["id"] == item["support"][0])
        old["id"] = "adopt:collection:invented-v2"
        old["payload"]["objects"] = [{"id": "collection", "version": "invented-v2"}]
        item["support"] = [old["id"]]

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "complete", reply
    axes = _row(reply["answer_diff"]["protocol_checks"], CHECK)["axes"]
    assert "scope_model" in axes
    assert "verdict" not in axes


def _collection_plan() -> dict:
    """A v2 plan whose protocol_options decision offers two invented collection windows."""
    request = _plan()
    session = request["session"]
    template = copy.deepcopy(session["protocol"]["objects"][2])

    def replacement(upper: str, ref: str) -> dict:
        item = copy.deepcopy(template)
        item["origin"] = {
            "kind": "hypothesis",
            "ref": f"user:invented {ref}",
            "source": None,
            "analysis": None,
        }
        item["standing"] = {"status": "proposed", "resolution": "resolved", "basis": [f"user:invented {ref}"]}
        item["support"] = list(template["support"])
        item["data"]["availability"] = [
            {"lower": None, "upper": upper, "lower_inclusive": False, "upper_inclusive": True}
        ]
        return item

    def alternative(identity: str, upper: str) -> dict:
        return {
            "id": identity,
            "label": f"invented {identity}",
            "replace_objects": [replacement(upper, identity)],
            "checks": [CHECK],
        }

    session["decisions"] = [
        {
            "kind": "protocol_options",
            "id": DECISION,
            "question": "Which invented collection window should the draft use?",
            "target": copy.deepcopy(session["target"]),
            "coverage": "declared_design",
            "selected": None,
            "alternatives": [alternative("through-95", "95"), alternative("through-100", "100")],
        }
    ]
    return request


def test_a_decision_label_change_is_wording_only_and_never_a_verdict():
    """Changing only one protocol_options alternative label reports wording alone, never a verdict."""

    def mutate(session: dict) -> None:
        session["decisions"][0]["alternatives"][0]["label"] = "invented through 95, relabelled"

    reply = _revise(_collection_plan(), mutate)
    assert reply["code"] == "complete", reply
    row = _row(reply["answer_diff"]["protocol_decisions"], DECISION)
    assert row["code"] == "changed"
    assert row["axes"] == ["wording"]


def test_reordering_equivalent_claims_is_an_input_only_change():
    """Reordering claims changes request bytes but no admitted outcome, so only input is set."""

    def mutate(session: dict) -> None:
        session["protocol"]["checks"][0]["claims"].reverse()

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "complete", reply
    row = _row(reply["answer_diff"]["protocol_checks"], CHECK)
    assert row["code"] == "changed"
    assert row["axes"] == ["input"]


def test_both_snapshots_are_freshly_replayed_with_their_protocol_sections():
    """previous_fresh is a new replay of the prior request, carrying its own protocol section."""
    previous = _plan()
    reply = _revise(previous, _set_window_upper("90"))
    assert reply["code"] == "complete", reply
    assert reply["previous_fresh"]["protocol"]["checks"]
    assert reply["previous_fresh"]["protocol"] == run(previous)["result"]["protocol"]
    assert "protocol_checks" in reply["answer_diff"] and "protocol_decisions" in reply["answer_diff"]


def test_a_mixed_version_one_to_version_two_revision_stays_refused():
    """MUST-NOT: a v1 snapshot revised into v2 is refused rather than migrated (CMP-1)."""
    guide = run({"operation": "describe", "view": "design_session"})["result"]
    first_request = copy.deepcopy(guide["example"])
    first = run(first_request)
    revised = copy.deepcopy(first_request)
    revised["session"]["schema_version"] = 2
    revised["session"]["protocol"] = {"schema_version": 1, "objects": [], "checks": [], "sections": []}
    revised["session"]["revision"] = "two"
    revised["session"]["parent_digest"] = session_state.digest(first_request["session"])
    revised["previous"] = {
        "session": copy.deepcopy(first_request["session"]),
        "result": first["result"],
        "expected_result_digest": first["result_digest"],
    }
    reply = run(revised)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["mixed_session_version_revision"]


def test_content_changed_under_the_same_version_is_refused_on_the_direct_revision_path():
    """REV-1: the edition guard is not only a shortcut rule; a direct canonical revision is refused too."""

    def mutate(session: dict) -> None:
        session["protocol"]["objects"][2]["data"]["availability"][0]["upper"] = "90"

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["changed_protocol_object_version_required:collection"]


def test_scope_and_dependency_changes_are_governed_content_too():
    """REV-1: kind, scope and depends_on belong to the adopted definition; only attribution is excluded."""

    def scope(session: dict) -> None:
        session["protocol"]["objects"][2]["scope"]["context"]["cohort"] = "invented-cohort-a"

    def dependencies(session: dict) -> None:
        session["protocol"]["objects"][2]["depends_on"] = ["week12", "score"]

    for mutate in (scope, dependencies):
        reply = _revise(_plan(), mutate)
        assert reply["code"] == "refused", mutate.__name__
        assert reply["problems"] == ["changed_protocol_object_version_required:collection"], mutate.__name__


def test_attribution_only_changes_keep_the_edition_and_its_adoption():
    """REV-1: a new origin or standing under the same version is a changed warrant, not a new edition."""

    def mutate(session: dict) -> None:
        collection = session["protocol"]["objects"][2]
        collection["origin"] = {
            "kind": "user_choice",
            "ref": "user:invented re-attribution",
            "source": None,
            "analysis": None,
        }
        collection["standing"] = {
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented review"],
        }

    reply = _revise(_plan(), mutate)
    assert reply["code"] == "complete", reply.get("problems")
    adoption = {row["object"]: row for row in _adoption_rows(reply)}
    assert adoption["collection"]["adoption"] != "stale_version"
