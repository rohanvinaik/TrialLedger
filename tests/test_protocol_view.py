"""Direct-call tests for the pure clinical protocol view (packet F)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_view

RESULTS = (
    Path(__file__).resolve().parent.parent
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results"
)
NAMES = sorted(p.stem for p in RESULTS.glob("*.json"))
FORBIDDEN = re.compile(r"\b(complete|safe|valid|adequate|approved|medically)\b", re.IGNORECASE)
ALL_SECTIONS = [
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
]


def load(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text())["result"]


def coverage(name: str) -> dict:
    return {s["id"]: s["coverage"] for s in protocol_view.view(load(name))["sections"]}


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from strings(key)
            yield from strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from strings(item)


def claim(out: dict, check: str, claim_id: str) -> dict:
    row = next(c for c in out["checks"] if c["id"] == check)
    return next(c for c in row["claims"] if c["id"] == claim_id)


def test_fixtures_present():
    assert len(NAMES) == 8


def test_not_protocol_result_raises_named_error():
    with pytest.raises(ValueError, match="view_not_protocol_result"):
        protocol_view.view({"decisions": []})


@pytest.mark.parametrize("name", NAMES)
def test_exact_keys_and_all_eight_sections_in_order(name):
    out = protocol_view.view(load(name))
    assert set(out) == {
        "schema_version",
        "sections",
        "checks",
        "schedule",
        "open_items",
        "adoption",
        "limits_of_claim",
    }
    assert out["schema_version"] == 1
    assert [s["id"] for s in out["sections"]] == ALL_SECTIONS
    for s in out["sections"]:
        assert set(s) == {
            "id",
            "declared",
            "coverage",
            "findings",
            "findings_text",
            "findings_detail",
            "reasons",
            "objects",
            "checks",
        }


@pytest.mark.parametrize("name", NAMES)
def test_limits_of_claim_extended_exactly(name):
    result = load(name)
    out = protocol_view.view(result)
    assert out["limits_of_claim"] == result["protocol"]["limits_of_claim"] + [
        "Coverage and violations are over the declared variables, objects and claims only.",
        "Rendered decimals are rounded displays; exact rationals are canonical.",
    ]


EXPECTED_COVERAGE = {
    "efficacy-binomial-and-external": {"endpoints": "open", "efficacy": "not_computed"},
    "policy-violation-known": {"safety": "specified"},
    "policy-violation-proposed": {"safety": "open"},
    "policy-work-limit": {"safety": "not_computed"},
    # Corrected after review: a checked conditional obligation is specified, not open.
    "schedule-conditional-assessment": {"assessments": "specified"},
    "decision-plan-comparison": {"assessments": "specified"},
    "schedule-refuted-and-conditional": {
        "assessments": "open",
        "safety": "open",
        "exploratory": "not_applicable",
    },
    "schedule-scope-mismatch-unresolved": {"assessments": "open"},
}


@pytest.mark.parametrize("name", NAMES)
def test_full_section_table(name):
    got = coverage(name)
    expected = {sid: EXPECTED_COVERAGE[name].get(sid, "not_requested") for sid in ALL_SECTIONS}
    assert got == expected


def test_section_reasons_and_checks():
    sections = {s["id"]: s for s in protocol_view.view(load("efficacy-binomial-and-external"))["sections"]}
    assert sections["efficacy"]["reasons"] == ["not_computed:survival-method"]
    assert sections["efficacy"]["checks"] == ["efficacy-exact", "survival-method"]
    assert sections["endpoints"]["reasons"] == [
        "claim_unresolved:efficacy-exact:alpha",
        "claim_unresolved:efficacy-exact:power",
    ]
    sched = {s["id"]: s for s in protocol_view.view(load("schedule-refuted-and-conditional"))["sections"]}
    assert sched["safety"]["reasons"] == ["no_objects_declared"]
    assert sched["exploratory"]["reasons"] == ["user:simulated choice (fixture)"]
    assert sched["exploratory"]["declared"] == "not_applicable"
    assert sched["population"]["declared"] == "not_requested"
    assert sched["population"]["reasons"] == []


def test_work_limit_section_is_not_computed():
    out = protocol_view.view(load("policy-work-limit"))
    assert coverage("policy-work-limit")["safety"] == "not_computed"
    assert claim(out, "big-safety", "coverage")["wording"] == "Not computed within the declared work limit."
    assert any(i["kind"] == "section" and "not_computed" in i["text"] for i in out["open_items"])


def test_external_method_not_computed_with_missing_inputs():
    out = protocol_view.view(load("efficacy-binomial-and-external"))
    item = next(i for i in out["open_items"] if i["kind"] == "not_computed")
    assert item["check"] == "survival-method"
    assert "accrual_rate" in item["text"] and "dropout" in item["text"]
    row = next(c for c in out["checks"] if c["id"] == "survival-method")
    assert row["not_computed"]["missing"] == ["accrual_rate", "dropout"]
    assert row["summary"] is None and row["claims"] == []


def test_binomial_claims_refused_with_arithmetic_kept_in_child():
    out = protocol_view.view(load("efficacy-binomial-and-external"))
    for cid in ("alpha", "power"):
        row = claim(out, "efficacy-exact", cid)
        assert row["effective_outcome"] == "unresolved"
        assert row["wording"] == "Not applied: the deciding support is binding_unresolved."
        assert row["standing_support"] == [
            "object:efficacy",
            "object:response",
            "premise:adopt:efficacy:fixture-v1",
            "premise:adopt:response:fixture-v1",
            "premise:adult",  # the efficacy assumption, unchanged by the adoption rule
        ]
    assert claim(out, "efficacy-exact", "power")["outcome"] == "not_satisfied"


def test_scope_mismatch_has_no_schedule_numbers():
    out = protocol_view.view(load("schedule-scope-mismatch-unresolved"))
    (row,) = out["schedule"]
    assert row["conditionality"] == "not projected: projection_scope_mismatch"
    for key in ("nominal", "permitted", "availability", "feasible", "full_coverage_gap"):
        assert row[key] == "not computed"
    assert coverage("schedule-scope-mismatch-unresolved")["assessments"] == "open"
    item = out["open_items"][0]
    assert item["kind"] == "unresolved_projection" and "projection_scope_mismatch" in item["text"]
    assert out["checks"][0]["summary"] is None and out["checks"][0]["refs"] == []


def test_conditional_assessment_prefix_and_specified_section():
    out = protocol_view.view(load("schedule-conditional-assessment"))
    prefix = "If the declared condition applies: "
    row = next(c for c in out["checks"] if c["id"] == "week12-schedule")
    assert row["conditions"]
    assert all(c["application"] == "conditional" and c["wording"].startswith(prefix) for c in row["claims"])
    assert claim(out, "week12-schedule", "window")["wording"] == (
        prefix + "Planned collection does not cover part of the permitted window: (80, 91]."
    )
    assert out["schedule"][0]["conditionality"] == "conditional"
    assert coverage("schedule-conditional-assessment")["assessments"] == "specified"
    assert [i["kind"] for i in out["open_items"] if i["kind"] == "claim_conditional"] == [
        "claim_conditional"
    ] * 3


def test_proposed_prohibition_is_refused_while_coverage_stays_covered():
    out = protocol_view.view(load("policy-violation-proposed"))
    row = claim(out, "interim-safety", "prohibition")
    assert row["wording"] == "Not applied: the deciding support is proposed_refused."
    assert row["effective_outcome"] == "unresolved" and row["outcome"] == "violation"
    assert (
        claim(out, "interim-safety", "coverage")["wording"]
        == "Every reachable declared situation has a rule."
    )
    assert claim(out, "interim-safety", "coverage")["effective_outcome"] == "covered"
    assert "violation" not in row["wording"]
    assert coverage("policy-violation-proposed")["safety"] == "open"


def test_known_violation_is_specified_and_in_open_items():
    out = protocol_view.view(load("policy-violation-known"))
    assert coverage("policy-violation-known")["safety"] == "specified"
    row = claim(out, "interim-safety", "prohibition")
    assert row["wording"] == "1 declared prohibition violation(s) in reachable declared situations."
    failures = [i for i in out["open_items"] if i["kind"] == "claim_failure"]
    assert [(i["check"], i["claim"]) for i in failures] == [("interim-safety", "prohibition")]
    assert failures[0]["ref"] == "/protocol/checks/0/children/0/result"


@pytest.mark.parametrize("name", ["schedule-refuted-and-conditional", "schedule-conditional-assessment"])
def test_schedule_row_numbers(name):
    (row,) = protocol_view.view(load(name))["schedule"]
    assert list(row) == list(protocol_view.SCHEDULE_KEYS)
    assert row["permitted"] == "[77, 91]"
    assert row["availability"] == "(-∞, 80]"
    assert row["feasible"] == "[77, 80]"
    assert row["full_coverage_gap"] == "(80, 91]"
    assert (row["cohort"], row["arm"], row["phase"]) == ("all (open)",) * 3
    assert (row["measurement"], row["mode"], row["anchor"], row["unit"]) == (
        "score",
        "observed",
        "randomization",
        "day",
    )
    assert row["assessment"] == "week12" and row["collection"] == "collection"
    assert row["refs"][0]["result"] == "/protocol/checks/0/children/0/result"
    assert row["origin"]["assessment"] == {"kind": "user_choice", "ref": "user:simulated choice (fixture)"}


def test_schedule_refuted_row_specifics():
    (row,) = protocol_view.view(load("schedule-refuted-and-conditional"))["schedule"]
    assert row["nominal"] == "100" and row["nominal_outcome"] == "outside_window"
    assert row["conditionality"] == "unconditional"
    assert row["standing"] == {"assessment": "known", "collection": "proposed"}


def test_original_permitted_window_is_never_replaced_by_feasible():
    for name in ("schedule-refuted-and-conditional", "schedule-conditional-assessment"):
        (row,) = protocol_view.view(load(name))["schedule"]
        assert row["permitted"] != row["feasible"]
        assert row["permitted"] == "[77, 91]"


def test_refused_raw_outcome_never_shown_as_effective():
    for name in NAMES:
        out = protocol_view.view(load(name))
        for check in out["checks"]:
            for row in check["claims"]:
                if row["admission"] != "accepted" and row["effective_outcome"] == "unresolved":
                    assert row["effective_outcome"] != row["outcome"]
                    assert row["wording"].startswith("Not applied: the deciding support is ")
                    assert row["outcome"] not in row["wording"]


def test_open_items_order():
    out = protocol_view.view(load("efficacy-binomial-and-external"))
    kinds = [i["kind"] for i in out["open_items"]]
    assert kinds == ["not_computed", "claim_unsettled", "claim_unsettled", "section", "section"]
    out = protocol_view.view(load("schedule-conditional-assessment"))
    kinds = [i["kind"] for i in out["open_items"]]
    # The conditional section is specified (checked as a conditional obligation), so no section item.
    assert kinds == ["claim_conditional"] * 3 + ["claim_failure"] * 2
    for item in out["open_items"]:
        assert set(item) == {"kind", "check", "claim", "text", "ref"}


@pytest.mark.parametrize("name", NAMES)
def test_no_certificate_wording_anywhere(name):
    out = protocol_view.view(load(name))
    for text in strings(out):
        assert FORBIDDEN.search(text) is None, text


@pytest.mark.parametrize("name", NAMES)
def test_caller_labels_never_in_computed_wording(name):
    result = load(name)
    out = protocol_view.view(result)
    labels = {c["id"] for c in result["protocol"]["checks"]} | {
        o["id"] for o in result["protocol"]["objects"]
    }
    labels -= {
        "score",
        "efficacy",
        "response",
        "survival",
        "collection",
    }  # ordinary words; checked below by exact template match
    texts = [r["wording"] for c in out["checks"] for r in c["claims"]] + [
        i["text"] for i in out["open_items"]
    ]
    for label in labels:
        assert all(label not in t for t in texts), label


@pytest.mark.parametrize("name", NAMES)
def test_wording_table_covers_every_fixture_outcome(name):
    out = protocol_view.view(load(name))
    for check in out["checks"]:
        for row in check["claims"]:
            assert not re.match(r"^(If the declared condition applies: )?Outcome: ", row["wording"]), row


@pytest.mark.parametrize("name", NAMES)
def test_input_not_mutated(name):
    result = load(name)
    before = copy.deepcopy(result)
    protocol_view.view(result)
    assert result == before


@pytest.mark.parametrize("name", NAMES)
def test_deterministic(name):
    result = load(name)
    assert protocol_view.view(result) == protocol_view.view(copy.deepcopy(result))


@pytest.mark.parametrize("name", NAMES)
def test_output_shares_no_structure_with_input(name):
    result = load(name)
    out = protocol_view.view(result)
    for check in out["checks"]:
        for row in check["claims"]:
            row["standing_support"].append("mutated")
        check["conditions"].append("mutated")
    assert result == load(name)


# Synthetic rows: the fixtures never reach every wording-table row, so set the effective outcome on a copy
# of a fixture's own claim row and check the fixed template. Numbers are read from the child value.
def wording_for(name, check_index, claim_id, outcome, **value_edits):
    result = load(name)
    child = result["protocol"]["checks"][check_index]["children"][0]
    signal = child["signals"][0]
    row = next(r for r in signal["claim_admission"] if r["id"] == claim_id)
    row.update(outcome=outcome, effective_outcome=outcome, admission="accepted", application="unconditional")
    value = child["result"]["result"]["signals"][0]["value"]
    vrow = next(r for r in value["claims"] if r["id"] == claim_id)
    vrow.update(outcome=outcome, **value_edits)
    out = protocol_view.view(result)
    return claim(out, result["protocol"]["checks"][check_index]["id"], claim_id)["wording"]


@pytest.mark.parametrize(
    ("claim_id", "outcome", "expected"),
    [
        ("visit", "satisfied", "At least one permitted assessment time falls within planned collection."),
        ("visit", "no_feasible_time", "No permitted assessment time falls within planned collection."),
        ("visit", "no_permitted_time", "The permitted window is empty, so no assessment is permitted."),
        ("window", "no_permitted_time", "The permitted window is empty, so no assessment is permitted."),
        ("window", "satisfied", "Planned collection covers every permitted assessment time."),
        (
            "target",
            "satisfied",
            "The nominal target is inside the permitted window and within planned collection.",
        ),
        ("target", "unknown_target", "No nominal target is declared."),
        ("target", "something_new", "Outcome: something_new."),
    ],
)
def test_synthetic_schedule_wording(claim_id, outcome, expected):
    claim_kind = {"visit": "existence", "target": "nominal", "window": "full_window"}[claim_id]
    assert claim_kind
    assert wording_for("schedule-refuted-and-conditional", 0, claim_id, outcome) == expected


def test_synthetic_policy_wording():
    name = "policy-violation-known"
    assert wording_for(name, 0, "coverage", "gap", violations_found=3) == (
        "3 reachable declared situation(s) have no rule."
    )
    assert wording_for(name, 0, "exclusivity", "competing", violations_found=2) == (
        "2 reachable declared situation(s) enable more than one rule."
    )
    assert wording_for(name, 0, "prohibition", "clear") == (
        "No declared prohibition is violated in reachable declared situations."
    )
    assert wording_for(name, 0, "prohibition", "not_declared") == "No prohibition is declared."
    assert wording_for(
        name, 0, "termination", "not_established", reasons=["dead_end", "reachable_cycle"]
    ) == ("Termination is not established in the declared model: dead_end, reachable_cycle.")


def test_synthetic_bound_wording_uses_canonical_rational_and_decimal():
    name = "efficacy-binomial-and-external"
    got = wording_for(name, 0, "alpha", "satisfied")
    assert got == (
        "The exact null rejection probability 951937324593/95367431640625 (0.0100) "
        "meets the declared bound <= 1/20."
    )
    got = wording_for(name, 0, "power", "not_satisfied")
    assert got == (
        "The exact power 38566710919168/95367431640625 (0.4044) does not meet the declared bound >= 4/5."
    )


def test_interval_text_rules():
    f = protocol_view.interval_text
    assert f(None) == "unknown"
    assert f([]) == "none"
    assert f([{"lower": "91", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}]) == "{91}"
    assert (
        f([{"lower": "80", "upper": "91", "lower_inclusive": False, "upper_inclusive": True}]) == "(80, 91]"
    )
    assert (
        f([{"lower": "1/2", "upper": None, "lower_inclusive": True, "upper_inclusive": False}]) == "[1/2, +∞)"
    )
    two = [
        {"lower": None, "upper": "3", "lower_inclusive": False, "upper_inclusive": False},
        {"lower": "4", "upper": "6/2", "lower_inclusive": True, "upper_inclusive": True},
    ]
    assert f(two) == "(-∞, 3) ∪ [4, 3]"


def test_comparison_text_uses_canonical_rational_not_display():
    result = load("efficacy-binomial-and-external")
    value = result["protocol"]["checks"][0]["children"][0]["result"]["result"]["signals"][0]["value"]
    value["display"]["power"] = "0.9999"
    value["claims"][1]["outcome"] = "satisfied"
    row = result["protocol"]["checks"][0]["children"][0]["signals"][0]["claim_admission"][1]
    row.update(effective_outcome="not_satisfied", admission="accepted")
    wording = claim(protocol_view.view(result), "efficacy-exact", "power")["wording"]
    assert "38566710919168/95367431640625" in wording and "does not meet" in wording


def test_an_undetermined_claim_reads_as_not_determined_never_as_refused():
    import copy as _copy
    import json as _json
    from pathlib import Path as _Path

    path = _Path(__file__).resolve().parents[1] / (
        "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results/schedule-refuted-and-conditional.json"
    )
    result = _copy.deepcopy(_json.loads(path.read_text())["result"])
    row = result["protocol"]["checks"][0]["children"][0]["signals"][0]["claim_admission"][0]
    row.update(outcome="unresolved", admission="undetermined", effective_outcome="unresolved")
    claims = protocol_view.view(result)["checks"][0]["claims"]
    assert claims[0]["wording"] == "Not determined: an input this claim needs is not declared."
    assert "Not applied" not in claims[0]["wording"]


def _sections(name: str) -> dict:
    import json as _json
    from pathlib import Path as _Path

    path = _Path(__file__).resolve().parents[1] / (
        f"openspec/changes/connect-protocol-design-workflow/interface/fixtures/results/{name}.json"
    )
    result = _json.loads(path.read_text())["result"]
    return {s["id"]: s for s in protocol_view.view(result)["sections"]}


def test_a_known_prohibited_dose_never_reads_as_specified_alone():
    safety = _sections("policy-violation-known")["safety"]
    assert safety["coverage"] == "specified"
    assert safety["findings"] == "conflict_found"
    assert safety["findings_detail"][0]["outcome"] == "violation"
    assert safety["findings"] != "none_found_in_declared_checks"


def test_a_schedule_gap_is_a_repair_choice_beside_open_coverage():
    assessments = _sections("schedule-refuted-and-conditional")["assessments"]
    assert assessments["findings"] == "repair_choice_open"
    assert {d["outcome"] for d in assessments["findings_detail"]} == {"outside_window"}


def test_refused_or_uncomputed_findings_are_not_counted_as_known():
    assert _sections("policy-violation-proposed")["safety"]["findings"] == "not_checked"
    assert _sections("policy-work-limit")["safety"]["findings"] == "not_checked"
    assert _sections("schedule-refuted-and-conditional")["exploratory"]["findings"] == "not_checked"


def test_section_findings_precedence():
    assert protocol_view.section_findings("specified", 1, 1) == "conflict_found"
    assert protocol_view.section_findings("open", 0, 2) == "repair_choice_open"
    assert protocol_view.section_findings("specified", 0, 0) == "none_found_in_declared_checks"
    assert protocol_view.section_findings("open", 0, 0) == "not_checked"
    assert protocol_view.section_findings("not_computed", 0, 0) == "not_checked"


def test_a_not_applicable_claim_has_its_own_wording_and_no_section_finding():
    import copy as _copy

    result = _copy.deepcopy(load("schedule-conditional-assessment"))
    for row in result["protocol"]["checks"][0]["children"][0]["signals"][0]["claim_admission"]:
        row["application"] = "not_applicable"
    out = protocol_view.view(result)
    assert {c["wording"] for c in out["checks"][0]["claims"]} == {
        "Not applicable: the declared condition does not hold in this scope."
    }
    section = next(s for s in out["sections"] if s["id"] == "assessments")
    assert section["findings_detail"] == []
