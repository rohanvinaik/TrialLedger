"""Metamorphic checks on the protocol workflow: what must not change when the session is restated.

- An unrelated added object, check or decision changes no other check's results, delivery rows or
  headline rows.
- Renaming ids, or reordering objects, checks, support, premises or alternatives, changes nothing
  but ids/order.
- Duplicating an identical adoption record changes nothing.

Results are compared as canonical, order-insensitive snapshots after normalising ids and digests, over the
receipts, signals and claim rows, the session headline (`metadata.findings`), the protocol view, the clinical
delivery summaries, the open items, the adoption rows and the plan alternatives.
"""

import copy
import json
import re

import pytest

from tests.test_protocol_composition_matrix import (
    CHECKS,
    ESTIMAND,
    SCHEDULE,
    mutate,
    obj,
    universe,
    with_alternative,
)
from TrialLedger import clinical_delivery
from TrialLedger.layer2 import protocol_view, run

HEX = re.compile(r"[0-9a-f]{32,}")
DROP = {"work", "bytes", "artifact", "canonical_ref", "session_id"}
PREFIX = "zq-"
REQUIRED = [SCHEDULE, ESTIMAND, "extra-schedule"]


def clean(x):
    if isinstance(x, dict):
        return {
            k: clean(v) for k, v in x.items() if k not in DROP and k != "digest" and not k.endswith("_digest")
        }
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, str):
        return HEX.sub("#", x)
    return x


def canon(x):
    """Order-insensitive canonical form: dict keys sorted, list members sorted by their JSON."""
    if isinstance(x, dict):
        return {k: canon(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return sorted((canon(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))
    return x


def snapshot(reply: dict) -> dict:
    """Per-check results, delivery rows, headline rows and decision rows, keyed by stable ids."""
    assert reply["code"] == "complete", reply.get("problems")
    result = reply["result"]
    checks = result["protocol"]["checks"]
    index = {i: c["id"] for i, c in enumerate(checks)}
    snap: dict = {"checks": {}, "headline": {}, "view": {}, "delivery": {}, "open": {}}
    for check in checks:
        children = [
            {
                "receipt": child["receipt"],
                "signals": child["signals"],
                "conditions": child["conditions"],
                "applicability": child["applicability"],
                "refusal": child["refusal"],
                "support": [s.get("support") for s in child["request"]["signals"]],
            }
            for child in check["children"]
        ]
        snap["checks"][check["id"]] = clean(
            {"row": {k: v for k, v in check.items() if k != "children"}, "children": children}
        )
    for finding in reply["metadata"]["findings"]:
        match = re.match(r"/result/protocol/checks/(\d+)(.*)", finding["path"])
        owner = index[int(match.group(1))] if match else "session"
        path = match.group(2) if match else finding["path"]
        tidy = json.loads(
            re.sub(
                r"/result/protocol/checks/(\d+)",
                lambda m: f"/check:{index[int(m.group(1))]}",
                json.dumps({**finding, "path": path}),
            )
        )
        snap["headline"].setdefault(owner, []).append(clean(tidy))
    view = protocol_view.view(result)
    delivery = clinical_delivery.protocol_delivery_view(result)
    snap["view"] = {c["id"]: clean(c) for c in view["checks"]}
    snap["delivery"] = {c["id"]: clean(c) for c in delivery["check_summaries"]}
    for item in view["open_items"]:
        snap["open"].setdefault(item["check"] or "<session>", []).append(item["text"])
    snap["adoption"] = {row["object"]: clean(row) for row in view["adoption"]}
    snap["decisions"] = {
        d["id"]: {
            a["id"]: clean(
                {
                    **{k: v for k, v in a.items() if k not in ("checks", "candidate_digest", "replacements")},
                    "checks": {
                        c["id"]: {k: v for k, v in c.items() if k not in ("children", "request", "receipt")}
                        for c in a["checks"]
                    },
                }
            )
            for a in d["alternatives"]
        }
        for d in result["protocol"]["decisions"]
    }
    snap["summary"] = clean(reply["summary"])
    decisions = {i: d["id"] for i, d in enumerate(result["protocol"]["decisions"])}
    text = re.sub(
        r"/protocol/checks/(\d+)", lambda m: f"/protocol/checks/@{index[int(m.group(1))]}", json.dumps(snap)
    )
    text = re.sub(
        r"/protocol/decisions/(\d+)", lambda m: f"/protocol/decisions/@{decisions[int(m.group(1))]}", text
    )
    return json.loads(text)


def same(a, b):
    assert json.dumps(canon(a), sort_keys=True) == json.dumps(canon(b), sort_keys=True)


def without(snap: dict, check: str, objects: tuple[str, ...] = (), decision: str | None = None) -> dict:
    out = copy.deepcopy(snap)
    for section in ("checks", "headline", "view", "delivery", "open"):
        out[section].pop(check, None)
    for obj_id in objects:
        out["adoption"].pop(obj_id, None)
    if decision:
        out["decisions"].pop(decision, None)
        out["headline"]["session"] = [
            f for f in out["headline"]["session"] if f"/protocol/decisions/@{decision}" not in json.dumps(f)
        ]
    out.pop("summary")
    return out


def plan_request(request: dict) -> dict:
    """The universe plus a plan decision replacing the collection by a hypothetical edition."""
    replacement = copy.deepcopy(obj(request, "collection"))
    replacement["origin"] = {
        "kind": "hypothesis",
        "ref": "user:invented simulation",
        "source": None,
        "analysis": None,
    }
    replacement["standing"] = {**replacement["standing"], "status": "proposed", "resolution": "unresolved"}
    return with_alternative(request, replacement)


# --- unrelated additions ----


def add_unrelated(request: dict, *, front: bool, check: bool = True, decision: bool = False) -> dict:
    """An independent score <- week12 <- collection chain, optionally with its own schedule check and plan."""
    request = copy.deepcopy(request)
    protocol, session = request["session"]["protocol"], request["session"]
    names = {"score": "extra-score", "week12": "extra-week12", "collection": "extra-collection"}
    added = []
    for old, new in names.items():
        item = copy.deepcopy(obj(request, old))
        item.update(
            id=new,
            support=[f"adopt:{new}:invented-v1"],
            depends_on=[names.get(d, d) for d in item["depends_on"]],
        )
        if old == "score":
            item["data"]["baseline"] = None
        if old == "week12":
            item["data"]["measurement"] = "extra-score"
        if old == "collection":
            item["data"]["assessment"] = "extra-week12"
            item["data"]["event_handling"] = None
        record = copy.deepcopy(next(p for p in session["premises"] if p["id"] == f"adopt:{old}:invented-v1"))
        record["id"] = f"adopt:{new}:invented-v1"
        record["payload"]["objects"] = [{"id": new, "version": "invented-v1"}]
        session["premises"].append(record)
        added.append(item)
    protocol["objects"][0:0] = added if front else []
    protocol["objects"] += [] if front else added
    if check:
        extra = copy.deepcopy(next(c for c in protocol["checks"] if c["id"] == SCHEDULE))
        extra.update(id="extra-schedule", objects=["extra-week12", "extra-collection"], required=not decision)
        if front:
            protocol["checks"].insert(0, extra)
        else:
            protocol["checks"].append(extra)
    if decision:
        replacement = copy.deepcopy(added[-1])
        replacement["standing"] = {
            **replacement["standing"],
            "status": "proposed",
            "resolution": "unresolved",
        }
        replacement["origin"] = {
            "kind": "hypothesis",
            "ref": "user:invented simulation",
            "source": None,
            "analysis": None,
        }
        session["decisions"] = [
            {
                "kind": "protocol_options",
                "id": "extra-plan",
                "question": "Which invented extra plan?",
                "target": copy.deepcopy(session["target"]),
                "coverage": "declared_design",
                "selected": None,
                "alternatives": [
                    {"id": "as-is", "label": "as drafted", "replace_objects": [], "checks": REQUIRED},
                    {"id": "var", "label": "replaced", "replace_objects": [replacement], "checks": REQUIRED},
                ],
            }
        ]
    return request


VARIANTS = {
    "base": lambda r: r,
    "proposed-week12": lambda r: mutate(r, "week12", "proposed"),
    "condition-week12": lambda r: mutate(r, "week12", "condition"),
    "stale-collection": lambda r: mutate(r, "collection", "stale"),
    "interpolated-score": lambda r: mutate(r, "score", "interpolated"),
}


@pytest.mark.parametrize("front", [False, True], ids=["appended", "prepended"])
@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_an_unrelated_object_and_check_change_no_other_check_row_or_headline(variant, front):
    base = VARIANTS[variant](universe())
    before = snapshot(run(base))
    reply = run(add_unrelated(base, front=front))
    after = snapshot(reply)
    # the addition is real: its own rows exist
    assert after["checks"]["extra-schedule"]["children"] and after["headline"]["extra-schedule"]
    assert after["delivery"]["extra-schedule"] and after["view"]["extra-schedule"]
    assert set(after["adoption"]) - set(before["adoption"]) == {
        "extra-score",
        "extra-week12",
        "extra-collection",
    }
    assert before["checks"] and before["headline"] and before["delivery"]
    same(
        without(after, "extra-schedule", ("extra-score", "extra-week12", "extra-collection")),
        without(before, "none"),
    )
    assert after["summary"]["findings"] > before["summary"]["findings"]


def test_an_unrelated_object_alone_adds_only_its_adoption_row():
    base = universe()
    before = snapshot(run(base))
    after = snapshot(run(add_unrelated(base, front=False, check=False)))
    assert set(after["adoption"]) - set(before["adoption"]) == {
        "extra-score",
        "extra-week12",
        "extra-collection",
    }
    assert before["headline"] and before["checks"]
    same(without(after, "none", ("extra-score", "extra-week12", "extra-collection")), without(before, "none"))
    assert after["summary"] == before["summary"]


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_an_unrelated_decision_changes_no_other_check_or_decision(variant):
    base = plan_request(VARIANTS[variant](universe()))
    before = snapshot(run(base))
    # `with_alternative` already gave the session a decision; the unrelated one is added beside it
    extra = add_unrelated(base, front=False, decision=True)
    extra["session"]["decisions"] = base["session"]["decisions"] + extra["session"]["decisions"]
    after = snapshot(run(extra))
    assert set(after["decisions"]) == {"plan", "extra-plan"} and set(before["decisions"]) == {"plan"}
    assert after["decisions"]["extra-plan"]["var"]["frame"] == "hypothetical"
    assert any("/protocol/decisions/@extra-plan" in json.dumps(f) for f in after["headline"]["session"])
    assert before["decisions"]["plan"]["var"]["frame"] == "hypothetical"
    same(
        without(after, "extra-schedule", ("extra-score", "extra-week12", "extra-collection"), "extra-plan"),
        without(before, "none"),
    )


# --- renaming ----


def rename_object(item: dict, P) -> None:
    kind, data = item["kind"], item["data"]
    item["id"] = P(item["id"])
    item["depends_on"] = [P(d) for d in item["depends_on"]]
    item["support"] = [P(s) for s in item["support"]]
    if kind == "measurement" and data.get("baseline"):
        data["baseline"] = P(data["baseline"])
    elif kind == "assessment":
        data["measurement"] = P(data["measurement"])
    elif kind == "collection":
        data["assessment"] = P(data["assessment"])
        if isinstance(data.get("event_handling"), dict):
            data["event_handling"]["estimand"] = P(data["event_handling"]["estimand"])


def rename(request: dict, prefix: str = PREFIX) -> dict:
    """Structural rename of every object, premise, check, section and decision id (never a text replace)."""
    request = copy.deepcopy(request)
    session = request["session"]

    def P(x):
        return prefix + x if isinstance(x, str) else x

    for item in session["protocol"]["objects"]:
        rename_object(item, P)
    for premise in session["premises"]:
        if premise["kind"] == "adoption":  # the example's other premises are referenced by its analyses
            premise["id"] = P(premise["id"])
            premise["depends_on"] = [P(d) for d in premise.get("depends_on", [])]
            premise["payload"]["objects"] = [{**o, "id": P(o["id"])} for o in premise["payload"]["objects"]]
    for check in session["protocol"]["checks"]:
        check["id"] = P(check["id"])
        check["objects"] = [P(o) for o in check["objects"]]
        check["support"] = [P(s) for s in check["support"]]
    for section in session["protocol"]["sections"]:
        section["objects"] = [P(o) for o in section["objects"]]
    for decision in session["decisions"]:
        if decision.get("kind") != "protocol_options":
            continue
        decision["id"] = P(decision["id"])
        for alt in decision["alternatives"]:
            alt["id"] = P(alt["id"])
            alt["checks"] = [P(c) for c in alt["checks"]]
            for item in alt["replace_objects"]:
                rename_object(item, P)
    return request


def unprefixed(snap: dict, prefix: str = PREFIX) -> dict:
    return json.loads(json.dumps(snap).replace(prefix, ""))


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_renaming_every_id_changes_nothing_but_the_ids(variant):
    base = plan_request(VARIANTS[variant](universe()))
    before = snapshot(run(base))
    renamed = rename(base)
    after = snapshot(run(renamed))
    assert any(PREFIX in json.dumps(v) for v in after["checks"].values()), (
        "the rename is visible in the result"
    )
    assert set(after["checks"]) == {PREFIX + c for c in CHECKS}
    assert before["headline"] and before["decisions"]["plan"]["var"]["assumption_refs"] == ["collection"]
    same(unprefixed(after), before)


# --- reordering ----


def reorder(request: dict) -> dict:
    request = copy.deepcopy(request)
    session = request["session"]
    protocol = session["protocol"]
    protocol["objects"].reverse()
    protocol["checks"].reverse()
    protocol["sections"].reverse()
    session["premises"].reverse()
    for item in protocol["objects"]:
        item["support"].reverse()
        item["depends_on"].reverse()
    for check in protocol["checks"]:
        check["objects"].reverse()
    for section in protocol["sections"]:
        section["objects"].reverse()
    for decision in session["decisions"]:
        if decision.get("kind") == "protocol_options":
            decision["alternatives"].reverse()
            for alt in decision["alternatives"]:
                alt["checks"].reverse()
    return request


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_reordering_objects_checks_support_premises_and_alternatives_changes_nothing(variant):
    base = plan_request(VARIANTS[variant](universe()))
    before = snapshot(run(base))
    shuffled = reorder(base)
    assert [c["id"] for c in shuffled["session"]["protocol"]["checks"]] == [ESTIMAND, SCHEDULE]
    after = snapshot(run(shuffled))
    assert before["checks"] and before["decisions"]["plan"] and before["headline"]
    same(after, before)


def test_reordering_two_alternatives_keeps_each_alternatives_own_result():
    base = plan_request(universe())
    extra = copy.deepcopy(base["session"]["decisions"][0]["alternatives"][1])
    extra.update(id="late", label="a later edition")
    extra["replace_objects"][0]["data"]["availability"][0]["upper"] = "95"
    extra["replace_objects"][0]["version"] = "invented-v1-late"
    record = copy.deepcopy(
        next(p for p in base["session"]["premises"] if p["id"] == "adopt:collection:invented-v1")
    )
    record.update(id="adopt:collection:invented-v1-late")
    record["payload"]["objects"] = [{"id": "collection", "version": "invented-v1-late"}]
    base["session"]["premises"].append(record)
    extra["replace_objects"][0]["support"] = ["adopt:collection:invented-v1-late"]
    base["session"]["decisions"][0]["alternatives"].append(extra)
    before = snapshot(run(base))
    assert set(before["decisions"]["plan"]) == {"as-is", "var", "late"}
    swapped = copy.deepcopy(base)
    swapped["session"]["decisions"][0]["alternatives"].reverse()
    same(snapshot(run(swapped)), before)
    assert before["decisions"]["plan"]["late"] != before["decisions"]["plan"]["var"]


# --- duplicate adoption ----


def duplicate_adoption(request: dict, identity: str) -> dict:
    request = copy.deepcopy(request)
    session = request["session"]
    original = next(p for p in session["premises"] if p["id"] == f"adopt:{identity}:invented-v1")
    twin = copy.deepcopy(original)
    twin["id"] = f"adopt:{identity}:invented-v1-twin"
    session["premises"].append(twin)
    obj(request, identity)["support"].append(twin["id"])
    return request


def dedupe(x):
    if isinstance(x, dict):
        return {k: dedupe(v) for k, v in x.items()}
    if isinstance(x, list):
        seen, out = set(), []
        for v in map(dedupe, x):
            key = json.dumps(v, sort_keys=True)
            if key not in seen:
                seen.add(key)
                out.append(v)
        return out
    return x


@pytest.mark.parametrize("identity", ["score", "week12", "collection", "estimand"])
@pytest.mark.parametrize("variant", ["base", "proposed-week12", "stale-collection"])
def test_a_duplicate_identical_adoption_record_changes_nothing(variant, identity):
    base = VARIANTS[variant](universe())
    if variant == "stale-collection" and identity == "collection":
        pytest.skip("the stale object has no current adoption record to duplicate in the same edition")
    before = snapshot(run(base))
    doubled = duplicate_adoption(base, identity)
    after = snapshot(run(doubled))
    text = json.dumps(after).replace("-twin", "")
    assert "invented-v1-twin" in json.dumps(after), "the duplicate is visible before ids are normalised"
    same(dedupe(json.loads(text)), dedupe(before))


def test_a_duplicate_of_a_proposed_adoption_stays_proposed_and_a_known_twin_does_not_promote_it():
    base = mutate(universe(), "week12", "adopt_proposed")
    before = snapshot(run(base))
    doubled = duplicate_adoption(base, "week12")
    after = snapshot(run(doubled))
    assert before["delivery"][SCHEDULE]["standing"] == "proposed"
    assert after["delivery"][SCHEDULE]["standing"] == "proposed"
    assert after["delivery"][ESTIMAND]["standing"] == "proposed"
    assert after["checks"][SCHEDULE]["children"][0]["signals"][0]["admission"]["code"] == "proposed_refused"
