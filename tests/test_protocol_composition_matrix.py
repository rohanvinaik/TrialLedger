"""Composition matrix: contract reference edge x upstream attribute x pipeline stage (step-4 intent tests).

Derived from the edge-matrix audit (`~/trialledger-runs/edge-matrix/`) and Rohan's composition decisions
(2026-11-05, `openspec/changes/connect-protocol-design-workflow/interface/README.md`):

- an object listed on a check gates it by itself; an object a projection reaches through a link it follows
  gates together with everything it references transitively; objects merely named inside a listed
  object's data do not gate; receipts carry `closure`;
- standing, adoption and assessment conditions follow that set; bindings are check-local;
- every check row carries the weakest standing it rests on, apart from `conditional`;
- signals without claim rows carry `application`, `application_status` and `finding_status`, and the session
  headline never reads a conditionally applied result as settled.

The universe is one session: score (baseline base-score) <- week12 <- collection (names estimand) -> estimand,
with a schedule check over [week12, collection] and an estimand check over [estimand]. For each
upstream object and attribute a minimal pair is built that differs only in that attribute. Cells the
contract leaves open are skipped with the question text rather than asserting a guess.
"""

import copy
import json
from functools import cache

import pytest

from tests.test_protocol_condition_closure import _schedule_beside
from tests.test_protocol_end_epi import COPIED_ADDRESS, SNAPSHOT, STUDY
from tests.test_protocol_review_repairs import _revise
from tests.test_protocol_session_replay import adopt, new_edition
from tests.test_protocol_walkthrough_repairs import _estimand_with_linked_collection
from TrialLedger import clinical_delivery
from TrialLedger.layer2 import protocol_view, run

SCHEDULE, ESTIMAND = "week12-schedule", "estimand-check"
CHECKS = (SCHEDULE, ESTIMAND)
OBJECTS = ("score", "week12", "collection", "estimand", "base-score")
# Contract closure (Rohan 2026-11-05): listed objects, plus what a followed link references transitively.
CLOSURE = {
    SCHEDULE: {"week12", "collection"},
    ESTIMAND: {"estimand", "collection", "week12", "score", "base-score"},
}
LISTED = {SCHEDULE: {"week12", "collection"}, ESTIMAND: {"estimand"}}
ATTRS = (
    "condition",
    "proposed",
    "interpolated",
    "conflicting",
    "absent",
    "stale",
    "adopt_proposed",
    "hyp",
    "origin_src",
    "scope",
)
# attribute -> (status, resolution) of the object standing it sets
STANDING = {
    "proposed": ("proposed", "unresolved"),
    "hyp": ("proposed", "unresolved"),
    "interpolated": ("interpolated", "resolved"),
    "conflicting": ("known", "conflicting"),
}
PROPOSED_CLASS = ("proposed", "adopt_proposed", "hyp")
BINDING_CLASS = ("conflicting", "absent", "stale")
UNDECIDED = {
    "class": "Literal",
    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
    "predicate": {"class": "Predicate", "kind": "treatment_history", "key": "discontinued_study_drug"},
    "value": {"class": "Value", "kind": "boolean"},
    "polarity": "positive",
    "time": None,
    "qualifiers": {"class": "Always"},
    "evidence": [],
}
SOURCE_Q = "contract question: which delivery surfaces must show a source_interpretation origin (Q4)?"


# --- builders ----


def universe() -> dict:
    request = _schedule_beside(_estimand_with_linked_collection("collect"))
    adopt(request, "collection")
    protocol = request["session"]["protocol"]
    score = obj(request, "score")
    baseline = copy.deepcopy(score)
    baseline.update(id="base-score", support=[])
    protocol["objects"].append(baseline)
    adopt(request, "base-score")
    score["data"]["baseline"] = "base-score"
    score["depends_on"] = ["base-score"]
    return request


def obj(request: dict, identity: str) -> dict:
    return next(o for o in request["session"]["protocol"]["objects"] if o["id"] == identity)


def mutate(request: dict, identity: str, attr: str) -> dict:
    """A deep copy that differs from `request` in exactly one attribute of one object."""
    request = copy.deepcopy(request)
    item, session = obj(request, identity), request["session"]
    if attr == "condition":
        item["data"]["condition"] = copy.deepcopy(UNDECIDED)
    elif attr in STANDING:
        status, resolution = STANDING[attr]
        item["standing"] = {**item["standing"], "status": status, "resolution": resolution}
        if attr == "hyp":
            item["origin"] = {
                "kind": "hypothesis",
                "ref": "user:invented simulation",
                "source": None,
                "analysis": None,
            }
    elif attr == "absent":
        item["support"] = []
    elif attr == "stale":
        item["version"] += "-edited"
    elif attr == "adopt_proposed":
        record = next(p for p in session["premises"] if p["id"] in item["support"])
        record["payload"]["status"], record["payload"]["resolution"] = "proposed", "unresolved"
    elif attr == "origin_src":
        if not any(s["id"] == "registry" for s in session["sources"]):
            session["sources"].append(
                {"id": "registry", "study": copy.deepcopy(STUDY), "expected_digest": SNAPSHOT["digest"]}
            )
        item["origin"] = {
            "kind": "source_interpretation",
            "ref": COPIED_ADDRESS,
            "source": "registry",
            "analysis": None,
        }
    elif attr == "scope":
        item["scope"]["context"]["cohort"] = "post-discontinuation"
    else:
        raise KeyError(attr)
    return request


@cache
def _base() -> dict:
    return universe()


@cache
def _reply(identity: str | None, attr: str | None) -> dict:
    request = _base() if attr is None else mutate(_base(), identity, attr)
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def gates(check: str, identity: str) -> bool | None:
    return identity in CLOSURE[check]


def question(check: str, identity: str, attr: str, stage: str) -> str | None:
    if attr == "origin_src" and stage in ("S4", "S6", "S7"):
        return SOURCE_Q
    return None


def cells(stage: str, attrs=ATTRS):
    out = []
    for check in CHECKS:
        for identity in OBJECTS:
            for attr in attrs:
                if attr == "condition" and identity != "week12":
                    continue
                marks = []
                text = question(check, identity, attr, stage)
                if text:
                    marks.append(pytest.mark.skip(reason=text))
                out.append(pytest.param(check, identity, attr, id=f"{check}-{identity}-{attr}", marks=marks))
    return out


# --- observation helpers ----


def check_row(reply: dict, check: str) -> dict:
    return next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == check)


def child_of(reply: dict, check: str) -> dict:
    (child,) = check_row(reply, check)["children"]
    return child


def signal_of(reply: dict, check: str) -> dict:
    (signal,) = child_of(reply, check)["signals"]
    return signal


def rows_of(reply: dict, check: str) -> list[tuple]:
    return [
        (r["id"], r["admission"], r["effective_outcome"], r["application"], r["finding_status"])
        for r in signal_of(reply, check).get("claim_admission", [])
    ]


def headline(reply: dict, check: str) -> list[dict]:
    index = [c["id"] for c in reply["result"]["protocol"]["checks"]].index(check)
    prefix = f"/result/protocol/checks/{index}/"
    found = [
        f for f in reply["metadata"]["findings"] if f["path"].startswith(prefix) or f["path"] == prefix[:-1]
    ]
    assert found, (check, "no headline finding")
    return found


def support_entries(reply: dict, check: str) -> dict:
    entries = child_of(reply, check)["request"]["signals"][0]["support"]
    assert entries
    return {e["id"]: (e["status"], e["resolution"]) for e in entries}


def role_entries(reply: dict, check: str) -> dict:
    roles = child_of(reply, check)["receipt"]["role_support"]
    out = {}
    for rows in roles.values():
        for row in rows:
            out[row["id"]] = (row["status"], row["resolution"])
    assert out
    return out


def view_row(reply: dict, check: str) -> dict:
    return next(c for c in protocol_view.view(reply["result"])["checks"] if c["id"] == check)


def summary_row(reply: dict, check: str) -> dict:
    view = clinical_delivery.protocol_delivery_view(reply["result"])
    return next(c for c in view["check_summaries"] if c["id"] == check)


def open_texts(reply: dict, check: str) -> list[str]:
    return [i["text"] for i in protocol_view.view(reply["result"])["open_items"] if i["check"] == check]


def adoption_id(identity: str) -> str:
    return f"adopt:{identity}:invented-v1"


# --- S1 receipt ----


def test_base_receipts_carry_the_contract_closure_and_its_adoption_premises():
    schedule = child_of(_reply(None, None), SCHEDULE)["receipt"]
    assert sorted(schedule["closure"]) == sorted(CLOSURE[SCHEDULE])
    assert schedule["premises"] == [adoption_id("week12"), adoption_id("collection")]
    estimand = child_of(_reply(None, None), ESTIMAND)["receipt"]
    assert sorted(estimand["closure"]) == sorted(CLOSURE[ESTIMAND])
    assert estimand["closure"][0] == "estimand"
    assert {adoption_id(o) for o in CLOSURE[ESTIMAND]} <= set(estimand["premises"])
    assert estimand["conditions"] == [] and schedule["conditions"] == []


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S1", ("proposed",)))
def test_s1_the_closure_names_exactly_what_gates(check, identity, attr):
    closure = set(child_of(_reply(identity, attr), check)["receipt"]["closure"])
    assert (identity in closure) is gates(check, identity)


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S1"))
def test_s1_receipt_carries_the_attribute_or_reports_the_check_not_computed(check, identity, attr):
    reply = _reply(identity, attr)
    if attr == "scope" and gates(check, identity) and gates(check, identity):
        row = check_row(reply, check)
        assert row["children"] == []
        assert [u["code"] for u in row["unresolved"]] == ["projection_scope_mismatch"]
        assert row["unresolved"][0]["objects"] == [identity]
        return
    receipt = child_of(reply, check)["receipt"]
    base = child_of(_reply(None, None), check)["receipt"]
    if attr == "condition":
        assert [c["object"] for c in receipt["conditions"]] == ["week12"]
        return
    assert receipt["conditions"] == []
    if gates(check, identity) and attr in STANDING:
        assert role_entries(reply, check)[f"object:{identity}"] == STANDING[attr]
    elif gates(check, identity) and attr == "absent":
        assert adoption_id(identity) not in receipt["premises"]
        assert adoption_id(identity) in base["premises"]
    elif gates(check, identity) and attr == "stale":
        assert any(i.startswith(f"stale_adoption:{identity}:") for i in role_entries(reply, check))
    else:
        assert role_entries(reply, check).keys() == role_entries(_reply(None, None), check).keys()
        assert {k: v for k, v in receipt.items() if k != "role_support"} == {
            k: v for k, v in base.items() if k != "role_support"
        } or attr == "adopt_proposed"


# --- S2 child signal support ----


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S2"))
def test_s2_child_signal_support_carries_the_attribute_for_gating_objects_only(check, identity, attr):
    reply, base = _reply(identity, attr), _reply(None, None)
    if attr == "scope" and gates(check, identity) and gates(check, identity):
        assert check_row(reply, check)["children"] == []
        return
    got, before = support_entries(reply, check), support_entries(base, check)
    assert before
    if not gates(check, identity) or attr in ("condition", "origin_src", "scope"):
        assert got == before
    elif attr in STANDING:
        assert got[f"object:{identity}"] == STANDING[attr]
        assert {k: v for k, v in got.items() if k != f"object:{identity}"} == {
            k: v for k, v in before.items() if k != f"object:{identity}"
        }
    elif attr == "absent":
        assert got[f"adoption:{identity}"] == ("known", "unresolved")
        assert f"premise:{adoption_id(identity)}" not in got
    elif attr == "stale":
        stale = [v for k, v in got.items() if k.startswith(f"stale_adoption:{identity}:")]
        assert stale == [("known", "unresolved")]
    elif attr == "adopt_proposed":
        assert got[f"premise:{adoption_id(identity)}"] == ("proposed", "unresolved")


# --- S3 admission and application (claim rows and plain-signal fields) ----


def expected_admission(attr: str) -> tuple[str, str, str]:
    """(admission code, signal status, finding status) a gating attribute yields."""
    if attr in PROPOSED_CLASS:
        return "proposed_refused", "proposed", "proposed"
    if attr == "interpolated":
        return "accepted", "interpolated", "interpolated"
    if attr in BINDING_CLASS:
        return "binding_unresolved", "known", "known"
    return "accepted", "known", "known"  # condition, origin_src


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S3"))
def test_s3_admission_and_application_follow_the_attribute(check, identity, attr):
    reply, base = _reply(identity, attr), _reply(None, None)
    if attr == "scope" and gates(check, identity) and gates(check, identity):
        assert check_row(reply, check)["children"] == []
        return
    signal = signal_of(reply, check)
    if not gates(check, identity) or attr == "origin_src":
        assert signal == signal_of(base, check)
        assert signal_of(base, check)["admission"]["code"] == "accepted"
        return
    code, status, finding = expected_admission(attr)
    assert (signal["admission"]["code"], signal["status"]) == (code, status)
    conditional = "conditional" if attr == "condition" else "unconditional"
    rows = rows_of(reply, check)
    if check == SCHEDULE:
        assert rows and {(r[1], r[3], r[4]) for r in rows} == {(code, conditional, finding)}
        if attr in PROPOSED_CLASS + BINDING_CLASS:
            assert {r[2] for r in rows} == {"unresolved"}
        else:
            assert [r[2] for r in rows] == [r[2] for r in rows_of(base, check)]
    else:
        assert rows == []
        assert (signal["application"], signal["finding_status"]) == (conditional, finding)
        assert signal["application_status"] is None


# --- S4 plan alternatives ----


def with_alternative(request: dict, replacement: dict) -> dict:
    request = copy.deepcopy(request)
    session = request["session"]
    session["decisions"] = [
        {
            "kind": "protocol_options",
            "id": "plan",
            "question": "Which invented plan?",
            "target": copy.deepcopy(session["target"]),
            "coverage": "declared_design",
            "selected": None,
            "alternatives": [
                {"id": "as-is", "label": "as drafted", "replace_objects": [], "checks": list(CHECKS)},
                {"id": "var", "label": "replaced", "replace_objects": [replacement], "checks": list(CHECKS)},
            ],
        }
    ]
    return request


@cache
def _alternatives(identity: str, attr: str) -> dict:
    variant = mutate(_base(), identity, attr)
    reply = run(with_alternative(_base(), obj(variant, identity)))
    assert reply["code"] == "complete", reply.get("problems")
    (decision,) = reply["result"]["protocol"]["decisions"]
    return {a["id"]: a for a in decision["alternatives"]}


ALT_ATTRS = tuple(a for a in ATTRS if a not in ("adopt_proposed", "origin_src"))


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S4", ALT_ATTRS))
def test_s4_a_replacement_is_a_named_hypothetical_and_carries_the_attribute(check, identity, attr):
    alts = _alternatives(identity, attr)
    fixed, var = alts["as-is"], alts["var"]
    assert (fixed["frame"], fixed["assumption_refs"]) == ("fixed", [])
    assert (var["frame"], var["assumption_refs"], var["unconditional_application"]) == (
        "hypothetical",
        [identity],
        "withheld",
    )
    mine = next(c for c in var["checks"] if c["id"] == check)
    before = next(c for c in fixed["checks"] if c["id"] == check)
    assert before["claims"] or check == ESTIMAND
    if not gates(check, identity):
        assert mine["claims"] == before["claims"] and mine["conditional_claims"] == []
        return
    if attr == "condition":
        assert check in var["conditional_checks"]
        expected = (
            ["visit", "target", "window"] if check == SCHEDULE else [f"{ESTIMAND}:estimand_declaration"]
        )
        assert mine["conditional_claims"] == expected
        assert {c["application"] for c in mine["claims"]} <= {"conditional"}
    if attr == "scope" and check == SCHEDULE:
        assert mine["claims"] == [] and (mine.get("children") or []) == []
        return
    if check == SCHEDULE:
        assert mine["claims"]
        for claim in mine["claims"]:
            assert claim["finding_status"] == "proposed", "an assumed replacement stays proposed"
            assert f"object:{identity}" in claim["assumed"]
            if attr == "absent":
                assert f"adoption:{identity}" in claim["assumed"]
            if attr == "stale":
                assert (claim["admission"], claim["effective_outcome"]) == (
                    "binding_unresolved",
                    "unresolved",
                )


# --- S5 revision answer_diff ----


def revise(identity: str, attr: str) -> dict:
    def edit(session: dict) -> None:
        mutated = mutate({"session": session}, identity, attr)["session"]
        session.clear()
        session.update(copy.deepcopy(mutated))
        session["revision"] = "two"
        if attr in ("condition", "scope"):
            new_edition(session, identity)

    return _revise(copy.deepcopy(_base()), edit)


@cache
def _revision(identity: str, attr: str) -> dict:
    return revise(identity, attr)["answer_diff"]


VERDICT_ATTRS = PROPOSED_CLASS + BINDING_CLASS + ("condition",)


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S5"))
def test_s5_answer_diff_axes_follow_the_attribute(check, identity, attr):
    row = next(r for r in _revision(identity, attr)["protocol_checks"] if r["id"] == check)
    if attr == "origin_src":
        assert "verdict" not in row["axes"]
        assert ("origin" in row["axes"]) is gates(check, identity)
        return
    if not gates(check, identity):
        assert (row["code"], row["axes"], row["changes"]) == ("unchanged", [], [])
        return
    assert row["code"] == "changed"
    axes = set(row["axes"])
    assert "support" in axes
    if attr in VERDICT_ATTRS or (attr == "scope" and gates(check, identity)):
        assert "verdict" in axes
    if attr == "interpolated":
        assert "verdict" not in axes
    if attr == "hyp":
        assert "origin" in axes
    if attr in ("condition", "stale", "scope"):
        assert "scope_model" in axes


@pytest.mark.parametrize(
    ("check", "identity"),
    [pytest.param(c, o, id=f"{c}-{o}") for c in CHECKS for o in CLOSURE[c]],
)
def test_s5_a_hypothesis_origin_is_an_origin_change_on_every_gating_check(check, identity):
    row = next(r for r in _revision(identity, "hyp")["protocol_checks"] if r["id"] == check)
    assert "origin" in row["axes"]


# --- S6 delivery: protocol view and clinical delivery view ----


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S6"))
def test_s6_delivery_rows_carry_standing_conditionality_and_open_items(check, identity, attr):
    reply, base = _reply(identity, attr), _reply(None, None)
    if not gates(check, identity) or attr == "origin_src":
        assert view_row(reply, check) == view_row(base, check)
        assert summary_row(reply, check) == summary_row(base, check)
        assert open_texts(reply, check) == open_texts(base, check)
        assert summary_row(base, check)["standing"] == "known"
        return
    if attr == "scope" and gates(check, identity):
        assert view_row(reply, check)["standing"] is None
        assert summary_row(reply, check)["standing"] is None
        assert any("different scopes" in t for t in open_texts(reply, check))
        return
    view, summary = view_row(reply, check), summary_row(reply, check)
    texts = open_texts(reply, check)
    if attr != "interpolated":  # its qualifier is the row's standing, not extra open text
        assert texts != open_texts(base, check)
    if attr in PROPOSED_CLASS:
        assert (view["standing"], summary["standing"], summary["conditional"]) == (
            "proposed",
            "proposed",
            False,
        )
    elif attr == "interpolated":
        assert (view["standing"], summary["standing"], summary["conditional"]) == (
            "interpolated",
            "interpolated",
            False,
        )
    elif attr == "condition":
        assert (summary["standing"], summary["conditional"]) == ("known", True)
        assert any(t.startswith("If the declared condition applies") for t in texts)
        inherited = ["week12"] if check == ESTIMAND else []
        assert view["inherited_conditions"] == inherited and view["applicability_binding"] is False
        assert any("declare a condition_applicability binding" in t for t in texts) is (check == ESTIMAND)
    elif attr in BINDING_CLASS:
        assert summary["code"] == "unresolved"
        assert texts
        assert (view["standing"], summary["standing"]) == ("known", "known")
    if attr in PROPOSED_CLASS + BINDING_CLASS:
        cause = {
            "absent": f"adoption:{identity}",
            "conflicting": f"object:{identity}",
            "proposed": f"object:{identity}",
            "hyp": f"object:{identity}",
            "adopt_proposed": f"premise:{adoption_id(identity)}",
        }.get(attr)
        for row in (view, summary):
            assert row["resolution"] == "unresolved"
            if cause:
                assert cause in row["resolution_causes"]
            else:
                assert any(c.startswith(f"stale_adoption:{identity}:") for c in row["resolution_causes"])
        text = protocol_view.standing_text(view)
        assert text.startswith(view["standing"] + ", unresolved (") and text.endswith(")")
    else:
        assert (view["resolution"], view["resolution_causes"]) == ("resolved", [])
        assert (summary["resolution"], summary["resolution_causes"]) == ("resolved", [])
        assert protocol_view.standing_text(view) == view["standing"]


# --- S7 session headline ----


@pytest.mark.parametrize(("check", "identity", "attr"), cells("S7"))
def test_s7_the_session_headline_never_reads_a_degraded_check_as_settled(check, identity, attr):
    reply, base = _reply(identity, attr), _reply(None, None)
    found = headline(reply, check)
    if attr == "scope" and gates(check, identity) and gates(check, identity):
        assert [(f["kind"], f["disposition"]) for f in found] == [("protocol_check", "open")]
        assert [c["code"] for c in found[0]["causes"]] == ["projection_scope_mismatch"]
        return
    if not gates(check, identity) or attr == "origin_src":
        assert found == headline(base, check)
        assert any(f["disposition"] == "settled" for f in headline(base, check))
        return
    dispositions = {f["disposition"] for f in found}
    assert "settled" not in dispositions
    standings = {f["standing"] for f in found if f["standing"] is not None}
    if attr in PROPOSED_CLASS:
        assert standings == {"proposed"}
    elif attr == "interpolated":
        assert standings == {"interpolated"} and "conditional" in dispositions
    elif attr == "condition":
        assert "conditional" in dispositions
    else:
        assert dispositions == {"open"}


@pytest.mark.parametrize(
    ("identity", "attr"),
    [
        pytest.param(o, a, id=f"{o}-{a}", marks=[])
        for o in OBJECTS
        for a in ATTRS
        if a != "condition" or o == "week12"
    ],
)
def test_s7_the_summary_counts_fewer_settled_findings_exactly_when_something_gates(identity, attr):
    base = _reply(None, None)["summary"]["dispositions"]
    got = _reply(identity, attr)["summary"]["dispositions"]
    assert base["settled"] == 4
    if attr == "origin_src":
        assert got == base
    elif attr == "scope":
        schedule_listed = identity in LISTED[SCHEDULE]
        # Rohan (2026-11-05): a scope mismatch anywhere in the gating closure makes the check unresolved; the
        # estimand's closure is itself, its linked collection, and everything that references transitively.
        estimand_refused = identity in ("estimand", "collection", "week12", "score", "base-score")
        assert (got["settled"] < base["settled"]) is (schedule_listed or estimand_refused)
    else:
        assert any(gates(c, identity) for c in CHECKS)
        assert got["settled"] < base["settled"]


# --- adversarial compositions ----


def _with_condition(request: dict) -> dict:
    obj(request, "week12")["data"]["condition"] = copy.deepcopy(UNDECIDED)
    return request


def test_condition_plus_stale_linked_collection_plus_a_hypothetical_replacement_keep_all_three_visible():
    request = _with_condition(copy.deepcopy(_base()))
    obj(request, "collection")["version"] += "-edited"  # adoption still names the old edition
    replacement = copy.deepcopy(obj(request, "week12"))
    replacement["data"]["condition"] = None
    replacement["origin"] = {
        "kind": "hypothesis",
        "ref": "user:invented simulation",
        "source": None,
        "analysis": None,
    }
    replacement["standing"] = {**replacement["standing"], "status": "proposed", "resolution": "unresolved"}
    reply = run(with_alternative(request, replacement))
    assert reply["code"] == "complete", reply.get("problems")
    # fixed plan: both the condition and the stale linked collection reach both checks
    for check in CHECKS:
        child = child_of(reply, check)
        assert [c["object"] for c in child["receipt"]["conditions"]] == ["week12"]
        assert signal_of(reply, check)["admission"]["code"] == "binding_unresolved"
        assert not any(f["disposition"] == "settled" for f in headline(reply, check))
        assert any(k.startswith("stale_adoption:collection:") for k in support_entries(reply, check))
    schedule_rows = rows_of(reply, SCHEDULE)
    assert {(r[1], r[2], r[3]) for r in schedule_rows} == {
        ("binding_unresolved", "unresolved", "conditional")
    }
    assert signal_of(reply, ESTIMAND)["application"] == "conditional"
    assert (
        summary_row(reply, SCHEDULE)["conditional"] is True
        and summary_row(reply, ESTIMAND)["conditional"] is True
    )
    assert any("older version" in t for t in open_texts(reply, SCHEDULE))
    assert any(t.startswith("If the declared condition applies") for t in open_texts(reply, SCHEDULE))
    # the alternative names its hypothetical replacement, not the fixed plan's condition as fact
    (decision,) = reply["result"]["protocol"]["decisions"]
    alts = {a["id"]: a for a in decision["alternatives"]}
    assert (alts["var"]["frame"], alts["var"]["assumption_refs"]) == ("hypothetical", ["week12"])
    assert alts["var"]["unconditional_application"] == "withheld"
    assert alts["var"]["conditional_checks"] == []
    claims = next(c for c in alts["var"]["checks"] if c["id"] == SCHEDULE)["claims"]
    assert claims and all("object:week12" in c["assumed"] for c in claims)
    assert {(c["admission"], c["finding_status"]) for c in claims} == {("binding_unresolved", "proposed")}
    assert alts["as-is"]["frame"] == "fixed"
    assert set(alts["as-is"]["conditional_checks"]) == set(CHECKS)


def test_an_unadopted_linked_assessment_plus_a_proposed_estimand_name_both_causes():
    request = copy.deepcopy(_base())
    obj(request, "week12")["support"] = []
    estimand = obj(request, "estimand")
    estimand["standing"] = {**estimand["standing"], "status": "proposed", "resolution": "unresolved"}
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    signal = signal_of(reply, ESTIMAND)
    blockers = signal["blockers"]
    assert any(b.startswith("binding_unresolved:") for b in blockers), blockers  # simultaneous cause kept
    assert any(
        c["code"].startswith("binding_unresolved:") for f in headline(reply, ESTIMAND) for c in f["causes"]
    )
    assert any("binding unresolved" in t for t in open_texts(reply, ESTIMAND))
    assert any(b.startswith("proposed_refused:") for b in blockers)
    assert signal["status"] == "proposed" and signal["finding_status"] == "proposed"
    entries = support_entries(reply, ESTIMAND)
    assert entries["adoption:week12"] == ("known", "unresolved") and entries["object:estimand"] == (
        "proposed",
        "unresolved",
    )
    assert summary_row(reply, ESTIMAND)["standing"] == "proposed"
    assert not any(f["disposition"] == "settled" for f in headline(reply, ESTIMAND))
    # the schedule check does not list the estimand, so only the unadopted assessment reaches it
    assert signal_of(reply, SCHEDULE)["admission"]["code"] == "binding_unresolved"
    assert signal_of(reply, SCHEDULE)["status"] == "known"
    assert "object:estimand" not in support_entries(reply, SCHEDULE)
    assert any(t for t in open_texts(reply, ESTIMAND))


def _definition_session() -> dict:
    from tests.test_protocol_definition_relations import _with_relation

    return _with_relation("implies", "relapse-check", "retreatment-check")


def test_a_scope_mismatch_plus_a_definition_relation_over_the_affected_check_is_named_never_decided():
    base = run(_definition_session())
    assert base["code"] == "complete", base.get("problems")
    (base_row,) = base["result"]["definition_checks"]
    assert (base_row["code"], base_row["status"], base_row["blockers"]) == ("consistent", "known", [])
    request = _definition_session()
    relapse = obj(request, "relapse-rule")
    relapse["scope"]["context"]["cohort"] = "post-discontinuation"
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    (row,) = reply["result"]["definition_checks"]
    assert row["code"] != "consistent"
    assert "definition_protocol_child_missing:relapse-check" in row["blockers"]
    affected = check_row(reply, "relapse-check")
    assert affected["children"] == []
    assert [u["code"] for u in affected["unresolved"]] == ["projection_scope_mismatch"]
    untouched = check_row(reply, "retreatment-check")
    assert untouched == check_row(base, "retreatment-check")
    assert json.dumps(row["declaration"], sort_keys=True) == json.dumps(
        base_row["declaration"], sort_keys=True
    )
    findings = [
        f
        for f in reply["metadata"]["findings"]
        if f["kind"] == "protocol_check"
        and f["path"].endswith(
            f"checks/{[c['id'] for c in reply['result']['protocol']['checks']].index('relapse-check')}"
        )
    ]
    assert [f["disposition"] for f in findings] == ["open"]


def test_a_proposed_policy_operand_plus_a_definition_relation_keeps_the_relation_proposed():
    request = _definition_session()
    relapse = obj(request, "relapse-rule")
    relapse["standing"] = {**relapse["standing"], "status": "proposed", "resolution": "unresolved"}
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    (row,) = reply["result"]["definition_checks"]
    assert (row["code"], row["status"]) == ("consistent", "proposed")
