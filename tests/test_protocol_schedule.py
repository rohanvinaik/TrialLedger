"""Exact schedule coverage (interface v1, packet B, C5) checked against frozen acceptance fixtures."""

import copy
import json
import random
from fractions import Fraction
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_schedule

KIND = "schedule_coverage"
FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/schedule.json"
    ).read_text()
)
CASES = FIXTURE["cases"]
MALFORMED = FIXTURE["malformed"]
DEFAULT_IDS = {"existence", "nominal", "full_window"}


def interval(lower, upper, lower_inclusive=True, upper_inclusive=True):
    return {
        "lower": lower,
        "upper": upper,
        "lower_inclusive": lower_inclusive,
        "upper_inclusive": upper_inclusive,
    }


def window(permitted, available, nominal="84"):
    return {
        "scope": "draft:week-12-assessment",
        "anchor": "randomization",
        "unit": "day",
        "nominal": nominal,
        "permitted": permitted,
        "available": available,
    }


PERMITTED_77_91 = [interval("77", "91")]
COLLECTED_THROUGH_80 = [interval(None, "80", False, True)]


def rows_by_id(result):
    return {row["id"]: row for row in result["value"]["claims"]}


# ---- Fixture-driven acceptance -----------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_acceptance_case_matches_frozen_expectation(case):
    if case["claims"] is None:
        result = protocol_schedule.evaluate(KIND, case["data"])
    else:
        result = protocol_schedule.check(KIND, case["data"], case["claims"])
    expect = case["expect"]
    assert result["code"] == expect["code"]
    assert set(result) == {"code", "value", "blockers", "rule"}
    if "nominal" in expect:
        assert result["value"]["nominal"] == expect["nominal"]
    if "permitted" in expect:
        assert result["value"]["permitted"] == expect["permitted"]
    if "available" in expect:
        assert result["value"]["available"] == expect["available"]
    rows = rows_by_id(result)
    assert set(rows) == set(expect["claims"])
    for claim_id, want in expect["claims"].items():
        row = rows[claim_id]
        assert row["outcome"] == want["outcome"], claim_id
        assert row["determined_by"] == want["determined_by"], claim_id
        assert row["missing"] == want["missing"], claim_id
        assert row["feasible"] == want["feasible"], claim_id
        assert row["uncovered"] == want["uncovered"], claim_id
    assert result["value"]["work"]["used"] <= result["value"]["work"]["reserved"]


@pytest.mark.parametrize("case", MALFORMED, ids=[case["id"] for case in MALFORMED])
def test_malformed_case_refuses_with_its_exact_code(case):
    with pytest.raises(ValueError) as refusal:
        if case["claims"] is None:
            protocol_schedule.evaluate(KIND, case["data"])
        else:
            protocol_schedule.check(KIND, case["data"], case["claims"])
    assert str(refusal.value) == case["refusal"]


def test_work_reservation_is_the_stated_formula_on_every_valid_fixture_case():
    for case in CASES:
        data = case["data"]
        size = len(data["permitted"] or []) + len(data["available"] or [])
        expected = 4 * size * size + 6 * size + 8
        assert protocol_schedule.work_reservation(data) == expected, case["id"]
        if case["claims"] is None:
            result = protocol_schedule.evaluate(KIND, data)
        else:
            result = protocol_schedule.check(KIND, data, case["claims"])
        assert result["value"]["work"]["reserved"] == expected, case["id"]
        assert result["value"]["work"]["used"] <= expected, case["id"]


# ---- Authored MUST-NOT and contract tests ------------------------------------------------------


def test_permitted_output_is_the_normalized_window_never_the_feasible_part():
    result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80))
    assert result["value"]["permitted"] == [interval("77", "91")]
    existence = rows_by_id(result)["existence"]
    assert existence["feasible"] == [interval("77", "80")]
    assert existence["feasible"] != result["value"]["permitted"]


def test_existence_satisfied_does_not_establish_full_window_coverage():
    result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80))
    rows = rows_by_id(result)
    assert rows["existence"]["outcome"] == "satisfied"
    assert rows["full_window"]["outcome"] == "uncovered"
    assert rows["full_window"]["uncovered"] == [interval("80", "91", False, True)]
    assert result["code"] == "violated"
    assert "schedule_uncovered:full_window" in result["blockers"]


def test_open_and_closed_collection_at_day_91_change_full_window():
    closed = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, [interval(None, "91", False, True)]))
    open_end = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, [interval(None, "91", False, False)]))
    assert rows_by_id(closed)["full_window"]["outcome"] == "satisfied"
    assert rows_by_id(closed)["full_window"]["uncovered"] == []
    assert rows_by_id(open_end)["full_window"]["outcome"] == "uncovered"
    assert rows_by_id(open_end)["full_window"]["uncovered"] == [interval("91", "91")]


def test_null_available_is_unresolved_but_empty_available_is_no_feasible_time():
    unknown = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, None))
    assert rows_by_id(unknown)["existence"]["outcome"] == "unresolved"
    assert rows_by_id(unknown)["existence"]["missing"] == ["available"]
    assert rows_by_id(unknown)["full_window"]["outcome"] == "unresolved"
    assert unknown["code"] == "unresolved"

    explicit_none = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, []))
    assert rows_by_id(explicit_none)["existence"]["outcome"] == "no_feasible_time"
    assert rows_by_id(explicit_none)["existence"]["feasible"] == []
    assert rows_by_id(explicit_none)["full_window"]["outcome"] == "uncovered"
    assert rows_by_id(explicit_none)["full_window"]["uncovered"] == [interval("77", "91")]
    assert explicit_none["code"] == "violated"


def test_null_nominal_is_unknown_target_with_no_midpoint_or_default():
    result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80, nominal=None))
    assert result["value"]["nominal"] is None
    nominal = rows_by_id(result)["nominal"]
    assert nominal["outcome"] == "unknown_target"
    assert nominal["determined_by"] == ["nominal"]
    assert nominal["missing"] == ["nominal"]
    assert nominal["feasible"] is None and nominal["uncovered"] is None
    assert "schedule_unresolved:nominal" in result["blockers"]
    assert not any(name.startswith("schedule_satisfied") for name in result["blockers"])


def test_known_outside_window_survives_unknown_collection():
    result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, None, nominal="100"))
    nominal = rows_by_id(result)["nominal"]
    assert nominal["outcome"] == "outside_window"
    assert nominal["determined_by"] == ["nominal", "permitted"]
    assert nominal["missing"] == []
    assert "schedule_outside_window:nominal" in result["blockers"]
    assert result["code"] == "violated"


def test_input_dictionary_is_not_mutated():
    data = window(PERMITTED_77_91, [interval(None, "80", False, True), interval("90", "95")])
    before = copy.deepcopy(data)
    protocol_schedule.check(
        KIND, data, [{"id": "a", "claim": "full_window"}, {"id": "b", "claim": "existence"}]
    )
    protocol_schedule.evaluate(KIND, data)
    protocol_schedule.work_reservation(data)
    assert data == before


def test_bool_inclusive_flags_and_float_bounds_refuse_directly():
    with pytest.raises(ValueError) as string_flag:
        protocol_schedule.evaluate(KIND, window([interval("77", "91", "true", True)], None))
    assert str(string_flag.value) == "schedule_invalid_interval"
    with pytest.raises(ValueError) as int_flag:
        protocol_schedule.evaluate(KIND, window([interval("77", "91", 0, True)], None))
    assert str(int_flag.value) == "schedule_invalid_interval"
    with pytest.raises(ValueError) as float_upper:
        protocol_schedule.evaluate(KIND, window([interval("77", 91.0)], None))
    assert str(float_upper.value) == "schedule_invalid_rational"
    with pytest.raises(ValueError) as float_lower_for_reservation:
        protocol_schedule.work_reservation(window([interval(77.5, "91")], None))
    assert str(float_lower_for_reservation.value) == "schedule_invalid_rational"


def test_infinite_ends_render_as_null_and_stay_open():
    unbounded = [interval(None, None, False, False)]
    result = protocol_schedule.evaluate(KIND, window(unbounded, []))
    assert rows_by_id(result)["full_window"]["uncovered"] == unbounded
    assert rows_by_id(result)["existence"]["feasible"] == []


def test_unsupported_kind_and_invalid_claims_refuse():
    with pytest.raises(ValueError) as wrong_kind:
        protocol_schedule.evaluate("finite_policy", window(PERMITTED_77_91, None))
    assert str(wrong_kind.value) == "unsupported_schedule_kind"
    with pytest.raises(ValueError) as duplicate_id:
        protocol_schedule.check(
            KIND,
            window(PERMITTED_77_91, None),
            [{"id": "same", "claim": "existence"}, {"id": "same", "claim": "nominal"}],
        )
    assert str(duplicate_id.value) == "schedule_duplicate_claim"
    with pytest.raises(ValueError) as no_claims:
        protocol_schedule.check(KIND, window(PERMITTED_77_91, None), None)
    assert str(no_claims.value) == "schedule_invalid_claims"


def test_only_requested_claims_decide_the_code_and_rows_keep_caller_order():
    claims = [{"id": "later", "claim": "full_window"}, {"id": "first", "claim": "existence"}]
    result = protocol_schedule.check(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80), claims)
    assert [row["id"] for row in result["value"]["claims"]] == ["later", "first"]
    assert result["code"] == "violated"
    only_existence = protocol_schedule.check(
        KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80), [{"id": "v", "claim": "existence"}]
    )
    assert only_existence["code"] == "satisfied"
    assert only_existence["blockers"] == []


def test_result_and_row_field_order_are_fixed():
    result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80))
    assert list(result) == ["code", "value", "blockers", "rule"]
    assert result["rule"] == "schedule.exact_interval_coverage:1"
    assert list(result["value"]) == [
        "scope",
        "anchor",
        "unit",
        "nominal",
        "permitted",
        "available",
        "claims",
        "work",
        "guarantee",
    ]
    assert result["value"]["guarantee"] == "exact_over_declared_intervals"
    for row in result["value"]["claims"]:
        assert list(row) == [
            "id",
            "claim",
            "outcome",
            "determined_by",
            "missing",
            "feasible",
            "uncovered",
        ]


def test_work_reservation_counts_intervals_of_both_unions():
    data = window([interval("0", "1"), interval("2", "3"), interval("4", "5")], [interval("0", "9")])
    assert protocol_schedule.work_reservation(data) == 4 * 16 + 6 * 4 + 8


def test_nominal_value_does_not_change_existence_or_full_window():
    rows = []
    for nominal in ("84", "5", None, "200"):
        result = protocol_schedule.evaluate(KIND, window(PERMITTED_77_91, COLLECTED_THROUGH_80, nominal))
        by_id = rows_by_id(result)
        rows.append((by_id["existence"], by_id["full_window"]))
    assert all(pair == rows[0] for pair in rows)


def test_pure_outcome_helpers_return_named_codes():
    assert protocol_schedule.outcome_class("uncovered") == "violated"
    assert protocol_schedule.outcome_class("unknown_target") == "unresolved"
    assert protocol_schedule.outcome_class("satisfied") == "satisfied"
    assert protocol_schedule.schedule_code(["satisfied", "unresolved"]) == "unresolved"
    assert protocol_schedule.schedule_code(["violated", "unresolved"]) == "violated"
    assert protocol_schedule.existence_outcome(True, True, True, False) == "no_permitted_time"
    assert protocol_schedule.nominal_outcome(True, True, False, False, False) == "outside_window"


# ---- Seeded random unions, checked pointwise against independent membership -------------------


def _random_union(rng, max_intervals=4, allow_empty=True):
    count = rng.randint(0 if allow_empty else 1, max_intervals)
    raw = []
    for _ in range(count):
        lower = None if rng.random() < 0.15 else rng.randint(0, 6)
        upper = None if rng.random() < 0.15 else rng.randint(0, 6)
        if lower is not None and upper is not None and lower > upper:
            lower, upper = upper, lower
        lower_inclusive = False if lower is None else rng.random() < 0.5
        upper_inclusive = False if upper is None else rng.random() < 0.5
        if lower is not None and upper is not None and lower == upper:
            lower_inclusive = upper_inclusive = True
        raw.append(
            interval(
                None if lower is None else str(lower),
                None if upper is None else str(upper),
                lower_inclusive,
                upper_inclusive,
            )
        )
    return raw


def _member(point, raw):
    for entry in raw:
        lower = None if entry["lower"] is None else Fraction(entry["lower"])
        upper = None if entry["upper"] is None else Fraction(entry["upper"])
        low_ok = lower is None or point > lower or (point == lower and entry["lower_inclusive"])
        high_ok = upper is None or point < upper or (point == upper and entry["upper_inclusive"])
        if low_ok and high_ok:
            return True
    return False


def _points():
    return [Fraction(k, 2) for k in range(-4, 29)]


def _as_raw(rendered):
    return [] if rendered is None else rendered


def test_random_unions_match_pointwise_set_semantics_and_stay_normalized():
    rng = random.Random(20260704)
    for _ in range(250):
        permitted = _random_union(rng)
        available = None if rng.random() < 0.2 else _random_union(rng)
        result = protocol_schedule.evaluate(KIND, window(permitted, available))
        value = result["value"]
        assert value["work"]["used"] <= value["work"]["reserved"]
        for point in _points():
            assert _member(point, value["permitted"]) == _member(point, permitted)
        if available is None:
            assert rows_by_id(result)["existence"]["feasible"] is None
            assert rows_by_id(result)["full_window"]["uncovered"] is None
            continue
        feasible = rows_by_id(result)["existence"]["feasible"]
        uncovered = rows_by_id(result)["full_window"]["uncovered"]
        for point in _points():
            in_w = _member(point, permitted)
            in_c = _member(point, available)
            assert _member(point, _as_raw(feasible)) == (in_w and in_c)
            assert _member(point, _as_raw(uncovered)) == (in_w and not in_c)
        for rendered in (value["permitted"], value["available"], feasible or [], uncovered or []):
            for left, right in zip(rendered, rendered[1:], strict=False):
                left_upper = None if left["upper"] is None else Fraction(left["upper"])
                right_lower = None if right["lower"] is None else Fraction(right["lower"])
                assert left_upper is not None and right_lower is not None
                mergeable = right_lower < left_upper or (
                    right_lower == left_upper and (left["upper_inclusive"] or right["lower_inclusive"])
                )
                assert not mergeable, (left, right)


def test_permutation_and_duplication_do_not_change_outputs():
    rng = random.Random(7)
    for _ in range(60):
        permitted = _random_union(rng, allow_empty=False)
        available = _random_union(rng)
        base = protocol_schedule.evaluate(KIND, window(permitted, available))
        shuffled = list(permitted)
        rng.shuffle(shuffled)
        again = protocol_schedule.evaluate(KIND, window(shuffled, available))
        duplicated = protocol_schedule.evaluate(KIND, window(permitted + permitted[:1], available))
        assert again["value"]["permitted"] == base["value"]["permitted"]
        assert again["value"]["claims"] == base["value"]["claims"]
        assert duplicated["value"]["permitted"] == base["value"]["permitted"]
        assert duplicated["value"]["claims"] == base["value"]["claims"]
        assert duplicated["code"] == base["code"]


def test_widening_collection_never_removes_feasibility_or_adds_uncovered_time():
    rng = random.Random(11)
    for _ in range(60):
        permitted = _random_union(rng, allow_empty=False)
        narrow = _random_union(rng)
        wide = narrow + [interval(None, None, False, False)]
        small = protocol_schedule.evaluate(KIND, window(permitted, narrow))
        big = protocol_schedule.evaluate(KIND, window(permitted, wide))
        assert big["value"]["permitted"] == small["value"]["permitted"]
        assert rows_by_id(big)["full_window"]["uncovered"] == []
        assert rows_by_id(small)["existence"]["outcome"] in ("satisfied", "no_feasible_time")
        assert rows_by_id(big)["existence"]["outcome"] == "satisfied"
        assert rows_by_id(big)["nominal"]["outcome"] in ("satisfied", "outside_window")


def test_union_limit_boundary_is_accepted_and_one_more_refuses():
    thirty_two = [interval(str(2 * k), str(2 * k + 1)) for k in range(32)]
    result = protocol_schedule.evaluate(KIND, window(thirty_two, None))
    assert len(result["value"]["permitted"]) == 32
    with pytest.raises(ValueError) as over:
        protocol_schedule.evaluate(KIND, window(thirty_two + [interval("100", "101")], None))
    assert str(over.value) == "schedule_union_limit"


def test_repeated_claim_id_with_different_kinds_refuses_as_duplicate_claim():
    with pytest.raises(ValueError) as repeated:
        protocol_schedule.check(
            KIND,
            window(PERMITTED_77_91, None),
            [{"id": "same", "claim": "existence"}, {"id": "same", "claim": "full_window"}],
        )
    assert str(repeated.value) == "schedule_duplicate_claim"


def test_invented_example_runs_through_check_and_evaluate_without_mutation():
    example = copy.deepcopy(protocol_schedule.EXAMPLES[KIND])
    before = copy.deepcopy(protocol_schedule.EXAMPLES[KIND])
    evaluated = protocol_schedule.evaluate(KIND, protocol_schedule.EXAMPLES[KIND])
    checked = protocol_schedule.check(
        KIND,
        protocol_schedule.EXAMPLES[KIND],
        [{"id": "visit", "claim": "existence"}, {"id": "coverage", "claim": "full_window"}],
    )
    assert protocol_schedule.EXAMPLES[KIND] == before == example
    assert evaluated["code"] == "violated"
    assert checked["code"] == "violated"
    assert evaluated["value"]["scope"] == "invented:week-12-assessment"
