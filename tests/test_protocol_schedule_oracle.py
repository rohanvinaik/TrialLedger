"""Independent endpoint-cell oracle for the `schedule_coverage` operator (packet B', contract C5).

Written from the frozen interface text only (`interface/operators.md` "Packet B" and the oracle section,
`contracts.md` C5, `verification.md` V3). This file never reads the production operator's source. Step one
imports nothing from TrialLedger. Step-two tests import the production module inside their own bodies, so
collection succeeds even while the module is absent. No float or Decimal is used anywhere in the oracle.
"""

import json
import random
import re
from fractions import Fraction
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/schedule.json"
)
FIXTURES = json.loads(FIXTURE.read_text())

FIELDS = {"scope", "anchor", "unit", "nominal", "permitted", "available"}
INTERVAL_KEYS = {"lower", "upper", "lower_inclusive", "upper_inclusive"}
CLAIM_NAMES = ("existence", "nominal", "full_window")
DEFAULT_CLAIMS = [{"id": name, "claim": name} for name in CLAIM_NAMES]
RULE = "schedule.exact_interval_coverage:1"
GUARANTEE = "exact_over_declared_intervals"
VIOLATED = {"no_permitted_time", "no_feasible_time", "outside_window", "not_collected", "uncovered"}
UNRESOLVED = {"unresolved", "unknown_target"}
RATIONAL_SYNTAX = re.compile(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?")
GRID = [Fraction(k, 2) for k in range(0, 21)]  # halves from 0 to 10


# --------------------------------------------------------------------------------------------------
# Oracle: parsing and validation (independent of TrialLedger, numbers are Fraction only)
# --------------------------------------------------------------------------------------------------


def _rational(raw):
    if type(raw) is not str or RATIONAL_SYNTAX.fullmatch(raw) is None:
        raise ValueError("schedule_invalid_rational")
    for part in raw.lstrip("-").split("/"):
        if int(part).bit_length() > 256:
            raise ValueError("schedule_rational_bit_limit")
    return Fraction(raw)


def _interval(raw):
    if type(raw) is not dict or set(raw) != INTERVAL_KEYS:
        raise ValueError("schedule_invalid_interval")
    li, ui = raw["lower_inclusive"], raw["upper_inclusive"]
    if type(li) is not bool or type(ui) is not bool:
        raise ValueError("schedule_invalid_interval")
    lo = None if raw["lower"] is None else _rational(raw["lower"])
    hi = None if raw["upper"] is None else _rational(raw["upper"])
    if (lo is None and li) or (hi is None and ui):
        raise ValueError("schedule_infinite_inclusive")
    if lo is not None and hi is not None and (lo > hi or (lo == hi and not (li and ui))):
        raise ValueError("schedule_empty_interval")
    return (lo, hi, li, ui)


def _union(raw):
    if raw is None:
        return None
    if type(raw) is not list:
        raise ValueError("schedule_invalid_union")
    if len(raw) > 32:
        raise ValueError("schedule_union_limit")
    return [_interval(item) for item in raw]


def _text(raw, limit):
    if type(raw) is not str or not (1 <= len(raw) <= limit):
        return None
    return raw


def _validate(data):
    if type(data) is not dict or set(data) != FIELDS:
        raise ValueError("schedule_data_fields")
    scope = _text(data["scope"], 1024)
    if scope is None:
        raise ValueError("schedule_invalid_scope")
    anchor = _text(data["anchor"], 256)
    if anchor is None:
        raise ValueError("schedule_invalid_anchor")
    unit = _text(data["unit"], 64)
    if unit is None:
        raise ValueError("schedule_invalid_unit")
    nominal = None if data["nominal"] is None else _rational(data["nominal"])
    permitted = _union(data["permitted"])
    available = _union(data["available"])
    return scope, anchor, unit, nominal, permitted, available


def _claim_list(raw):
    if type(raw) is not list or not (1 <= len(raw) <= 3):
        raise ValueError("schedule_invalid_claims")
    seen_ids, seen_names, out = set(), set(), []
    for item in raw:
        if type(item) is not dict or set(item) != {"id", "claim"}:
            raise ValueError("schedule_invalid_claims")
        cid, name = item["id"], item["claim"]
        if type(cid) is not str or cid == "" or type(name) is not str or name not in CLAIM_NAMES:
            raise ValueError("schedule_invalid_claims")
        if cid in seen_ids:
            # Contract names no code for a repeated id; treated as an invalid claim list.
            raise ValueError("schedule_invalid_claims")
        if name in seen_names:
            raise ValueError("schedule_duplicate_claim")
        seen_ids.add(cid)
        seen_names.add(name)
        out.append((cid, name))
    return out


# --------------------------------------------------------------------------------------------------
# Oracle: endpoint cells. Each endpoint is a point cell; each open gap between consecutive endpoints
# is a gap cell; the two outer cells are unbounded. Membership is decided at a representative of
# each cell (the point itself, a midpoint, or endpoint -1 / +1 for outer cells). Every interval
# endpoint is a cell boundary, so membership is constant on each cell.
# --------------------------------------------------------------------------------------------------


def _in_interval(x, interval):
    lo, hi, li, ui = interval
    if lo is not None and (x < lo or (x == lo and not li)):
        return False
    return not (hi is not None and (x > hi or (x == hi and not ui)))


def _in_set(x, intervals):
    return any(_in_interval(x, iv) for iv in intervals)


def _cells(points):
    """Cells as (kind, lo, hi, representative) over sorted unique endpoints."""
    if not points:
        return [("gap", None, None, Fraction(0))]
    cells = [("gap", None, points[0], points[0] - 1)]
    for i, p in enumerate(points):
        cells.append(("point", p, p, p))
        if i + 1 < len(points):
            q = points[i + 1]
            cells.append(("gap", p, q, (p + q) / 2))
    cells.append(("gap", points[-1], None, points[-1] + 1))
    return cells


def _flags(intervals, cells):
    if intervals is None:
        return None
    return [_in_set(cell[3], intervals) for cell in cells]


def _normalize(cells, flags):
    """Maximal runs of flagged cells. Adjacent cells merge exactly when their union is one interval."""
    out = []
    i, n = 0, len(cells)
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and flags[j + 1]:
            j += 1
        first, last = cells[i], cells[j]
        lo, li = (first[1], True) if first[0] == "point" else (first[1], False)
        hi, ui = (last[2], True) if last[0] == "point" else (last[2], False)
        out.append((lo, hi, li, ui))
        i = j + 1
    return out


def _render(value):
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _render_union(intervals):
    if intervals is None:
        return None
    return [
        {
            "lower": None if lo is None else _render(lo),
            "upper": None if hi is None else _render(hi),
            "lower_inclusive": li,
            "upper_inclusive": ui,
        }
        for lo, hi, li, ui in intervals
    ]


def _missing_permitted(available):
    return sorted(["permitted"] + (["available"] if available is None else []))


def _existence(W, C, has_intersection):
    if W == []:
        return "no_permitted_time", ["permitted"], []
    if W is None:
        return "unresolved", [], _missing_permitted(C)
    if C is None:
        return "unresolved", [], ["available"]
    if has_intersection:
        return "satisfied", ["available", "permitted"], []
    return "no_feasible_time", ["available", "permitted"], []


def _nominal(n, W, C):
    if n is None:
        return "unknown_target", ["nominal"], ["nominal"]
    if W is None:
        return "unresolved", [], _missing_permitted(C)
    if not _in_set(n, W):
        return "outside_window", ["nominal", "permitted"], []
    if C is None:
        return "unresolved", [], ["available"]
    if not _in_set(n, C):
        return "not_collected", ["available", "nominal", "permitted"], []
    return "satisfied", ["available", "nominal", "permitted"], []


def _full_window(W, C, has_difference):
    if W == []:
        return "no_permitted_time", ["permitted"], []
    if W is None:
        return "unresolved", [], _missing_permitted(C)
    if C is None:
        return "unresolved", [], ["available"]
    if not has_difference:
        return "satisfied", ["available", "permitted"], []
    return "uncovered", ["available", "permitted"], []


def _probe_points(*sets):
    """Representatives of every cell over the endpoints of the given sets."""
    points = sorted({x for S in sets if S is not None for iv in S for x in iv[:2] if x is not None})
    return [cell[3] for cell in _cells(points)]


def oracle(data, claims=None):
    """Full independent evaluation. Returns code, blockers, rule and value (without work)."""
    scope, anchor, unit, n, W, C = _validate(data)
    claim_list = _claim_list(DEFAULT_CLAIMS if claims is None else claims)
    points = sorted(
        {x for S in (W, C) if S is not None for iv in S for x in iv[:2] if x is not None}
        | ({n} if n is not None else set())
    )
    cells = _cells(points)
    cW, cC = _flags(W, cells), _flags(C, cells)
    both = W is not None and C is not None
    feasible_flags = [a and b for a, b in zip(cW, cC, strict=True)] if both else None
    uncovered_flags = [a and not b for a, b in zip(cW, cC, strict=True)] if both else None
    has_intersection = bool(feasible_flags) and any(feasible_flags)
    has_difference = bool(uncovered_flags) and any(uncovered_flags)
    rows = []
    for cid, name in claim_list:
        if name == "existence":
            outcome, det, miss = _existence(W, C, has_intersection)
        elif name == "nominal":
            outcome, det, miss = _nominal(n, W, C)
        else:
            outcome, det, miss = _full_window(W, C, has_difference)
        feasible = uncovered = None
        if both and name == "existence":
            feasible = _render_union(_normalize(cells, feasible_flags))
        if both and name == "full_window":
            uncovered = _render_union(_normalize(cells, uncovered_flags))
        rows.append(
            {
                "id": cid,
                "claim": name,
                "outcome": outcome,
                "determined_by": sorted(det),
                "missing": sorted(miss),
                "feasible": feasible,
                "uncovered": uncovered,
            }
        )
    outcomes = {row["outcome"] for row in rows}
    if outcomes & VIOLATED:
        code = "violated"
    elif outcomes & UNRESOLVED:
        code = "unresolved"
    else:
        code = "satisfied"
    blockers = set()
    for row in rows:
        if row["outcome"] in VIOLATED:
            blockers.add(f"schedule_{row['outcome']}:{row['id']}")
        elif row["outcome"] in UNRESOLVED:
            blockers.add(f"schedule_unresolved:{row['id']}")
    value = {
        "scope": scope,
        "anchor": anchor,
        "unit": unit,
        "nominal": None if n is None else _render(n),
        "permitted": None if W is None else _render_union(_normalize(cells, cW)),
        "available": None if C is None else _render_union(_normalize(cells, cC)),
        "claims": rows,
        "guarantee": GUARANTEE,
    }
    return {"code": code, "blockers": sorted(blockers), "rule": RULE, "value": value}


def reserved_work(data):
    """Work reservation R = 4(w+c)^2 + 6(w+c) + 8, with w and c the interval counts as written."""
    w = 0 if data["permitted"] is None else len(data["permitted"])
    c = 0 if data["available"] is None else len(data["available"])
    return 4 * (w + c) ** 2 + 6 * (w + c) + 8


# --------------------------------------------------------------------------------------------------
# Random valid inputs (deterministic) and comparison helpers
# --------------------------------------------------------------------------------------------------


def _raw_rational(value):
    if value is None:
        return None
    if value.denominator == 1 and value.numerator >= 0:
        return str(value.numerator)
    return _render(value)


def _random_interval(rng):
    lo = None if rng.random() < 0.08 else rng.choice(GRID)
    hi = None if rng.random() < 0.08 else rng.choice(GRID)
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    if lo is not None and hi is not None and lo == hi:
        li = ui = True
    else:
        li = lo is not None and rng.random() < 0.5
        ui = hi is not None and rng.random() < 0.5
    raw_lo = _raw_rational(lo)
    raw_hi = _raw_rational(hi)
    if raw_lo is not None and rng.random() < 0.2:
        raw_lo = f"{lo.numerator * 2}/{lo.denominator * 2}"
    return {"lower": raw_lo, "upper": raw_hi, "lower_inclusive": li, "upper_inclusive": ui}


def _random_union(rng):
    if rng.random() < 0.1:
        return None
    return [_random_interval(rng) for _ in range(rng.randint(0, 4))]


def _random_cases(count=400, seed=20261104):
    rng = random.Random(seed)
    cases = []
    for _ in range(count):
        nominal = None if rng.random() < 0.1 else _raw_rational(rng.choice(GRID))
        data = {
            "scope": "draft:random",
            "anchor": rng.choice(["randomization", "dose-1"]),
            "unit": "day",
            "nominal": nominal,
            "permitted": _random_union(rng),
            "available": _random_union(rng),
        }
        claims = None
        if rng.random() < 0.2:
            names = rng.sample(CLAIM_NAMES, rng.randint(1, 3))
            claims = [{"id": f"id-{name}", "claim": name} for name in names]
        cases.append((data, claims))
    return cases


def _fixture_cases():
    return [case for case in FIXTURES["cases"] + FIXTURES["malformed"]]


def _strip_work(result):
    """Everything the check returns except the work block (work depends on interval counts)."""
    value = {key: val for key, val in result["value"].items() if key != "work"}
    return {"code": result["code"], "value": value, "blockers": result["blockers"], "rule": result["rule"]}


def _assert_production_matches(result, expected, data):
    assert set(result) == {"code", "value", "blockers", "rule"}
    assert result["code"] == expected["code"]
    assert result["blockers"] == expected["blockers"]
    assert result["rule"] == RULE
    value = dict(result["value"])
    work = value.pop("work")
    assert value == expected["value"]
    assert set(work) == {"reserved", "used"}
    assert work["reserved"] == reserved_work(data)
    assert 0 <= work["used"] <= work["reserved"]


def _as_tuples(intervals):
    return _union(intervals) if intervals is not None else None


# --------------------------------------------------------------------------------------------------
# STEP ONE: the oracle against the fixtures. No production import in this section.
# --------------------------------------------------------------------------------------------------


def test_oracle_normalization_merges_touching_and_never_fills_gaps():
    touching = _normalize(
        _cells([Fraction(1), Fraction(2), Fraction(3)]),
        [False, True, True, True, True, True, False],
    )
    assert _render_union(touching) == [
        {"lower": "1", "upper": "3", "lower_inclusive": True, "upper_inclusive": True}
    ]
    punctured_points = [Fraction(1), Fraction(2), Fraction(3)]
    cells = _cells(punctured_points)
    flags = [False, True, True, False, True, True, False]  # [1,2) and (2,3]: point 2 excluded
    assert _render_union(_normalize(cells, flags)) == [
        {"lower": "1", "upper": "2", "lower_inclusive": True, "upper_inclusive": False},
        {"lower": "2", "upper": "3", "lower_inclusive": False, "upper_inclusive": True},
    ]


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURES["cases"] if "expect" in case],
    ids=lambda case: case["id"],
)
def test_oracle_reproduces_every_valid_fixture_case(case):
    result = oracle(case["data"], case["claims"])
    expect = case["expect"]
    assert result["code"] == expect["code"], case["id"]
    for key in ("nominal", "permitted", "available"):
        if key in expect:
            assert result["value"][key] == expect[key], (case["id"], key)
    expected_rows = expect["claims"]
    by_id = {row["id"]: row for row in result["value"]["claims"]}
    assert set(by_id) == set(expected_rows), case["id"]
    for key, expected_row in expected_rows.items():
        row = by_id[key]
        for field in ("outcome", "determined_by", "missing", "feasible", "uncovered"):
            assert row[field] == expected_row[field], (case["id"], key, field)


@pytest.mark.parametrize(
    "case",
    [case for case in _fixture_cases() if "refusal" in case],
    ids=lambda case: case["id"],
)
def test_oracle_refuses_every_malformed_fixture_case_with_its_named_code(case):
    with pytest.raises(ValueError) as caught:
        oracle(case["data"], case["claims"])
    assert str(caught.value) == case["refusal"], case["id"]


# --------------------------------------------------------------------------------------------------
# STEP TWO: comparison with the production operator. Each body calls protocol_schedule directly.
# --------------------------------------------------------------------------------------------------


def test_production_check_matches_oracle_on_every_fixture_case():
    from TrialLedger.layer2 import protocol_schedule

    for case in FIXTURES["cases"]:
        claims = DEFAULT_CLAIMS if case["claims"] is None else case["claims"]
        result = protocol_schedule.check("schedule_coverage", case["data"], claims)
        _assert_production_matches(result, oracle(case["data"], case["claims"]), case["data"])


def test_production_check_refuses_every_malformed_fixture_case_with_its_code():
    from TrialLedger.layer2 import protocol_schedule

    for case in FIXTURES["malformed"] + [case for case in FIXTURES["cases"] if "refusal" in case]:
        claims = DEFAULT_CLAIMS if case["claims"] is None else case["claims"]
        with pytest.raises(ValueError) as caught:
            protocol_schedule.check("schedule_coverage", case["data"], claims)
        assert str(caught.value) == case["refusal"], case["id"]


def test_production_evaluate_equals_check_with_default_claims():
    from TrialLedger.layer2 import protocol_schedule

    for data, _ in _random_cases(count=60):
        evaluated = protocol_schedule.evaluate("schedule_coverage", data)
        checked = protocol_schedule.check("schedule_coverage", data, DEFAULT_CLAIMS)
        assert evaluated == checked


def test_production_rejects_wrong_kind_by_name():
    from TrialLedger.layer2 import protocol_schedule

    data = FIXTURES["cases"][0]["data"]
    with pytest.raises(ValueError) as caught:
        protocol_schedule.check("finite_policy", data, DEFAULT_CLAIMS)
    assert str(caught.value) == "unsupported_schedule_kind"


def test_production_matches_oracle_on_seeded_random_unions():
    from TrialLedger.layer2 import protocol_schedule

    cases = _random_cases(count=400, seed=20261104)
    assert len(cases) >= 300
    for data, claims in cases:
        expected = oracle(data, claims)
        result = protocol_schedule.check(
            "schedule_coverage", data, DEFAULT_CLAIMS if claims is None else claims
        )
        _assert_production_matches(result, expected, data)


def test_permutation_and_duplication_do_not_change_production_outputs():
    from TrialLedger.layer2 import protocol_schedule

    rng = random.Random(7)
    sources = [(case["data"], case["claims"]) for case in FIXTURES["cases"]] + _random_cases(count=120)
    for data, claims in sources:
        base = protocol_schedule.check(
            "schedule_coverage", data, DEFAULT_CLAIMS if claims is None else claims
        )
        permuted = dict(data)
        for field in ("permitted", "available"):
            if data[field] is not None:
                shuffled = list(data[field])
                rng.shuffle(shuffled)
                permuted[field] = shuffled
        duplicated = dict(permuted)
        for field in ("permitted", "available"):
            if duplicated[field]:
                copy = rng.choice(duplicated[field])
                duplicated[field] = duplicated[field] + [dict(copy)]
        for variant in (permuted, duplicated):
            result = protocol_schedule.check(
                "schedule_coverage", variant, DEFAULT_CLAIMS if claims is None else claims
            )
            assert _strip_work(result) == _strip_work(base)


def test_widening_available_never_removes_feasibility_or_adds_uncovered_cells():
    from TrialLedger.layer2 import protocol_schedule

    rng = random.Random(11)
    checked = 0
    for data, _ in _random_cases(count=300, seed=4):
        if data["available"] is None or data["permitted"] is None:
            continue
        extra = _random_interval(rng)
        widened = dict(data, available=data["available"] + [extra])
        before = {
            row["id"]: row
            for row in protocol_schedule.check("schedule_coverage", data, DEFAULT_CLAIMS)["value"]["claims"]
        }
        after = {
            row["id"]: row
            for row in protocol_schedule.check("schedule_coverage", widened, DEFAULT_CLAIMS)["value"][
                "claims"
            ]
        }
        if before["existence"]["outcome"] == "satisfied":
            assert after["existence"]["outcome"] == "satisfied"
        W = _as_tuples(data["permitted"])
        C = _as_tuples(data["available"])
        probes = _probe_points(W, C, _as_tuples([extra]))
        feasible_before = _as_tuples(before["existence"]["feasible"])
        feasible_after = _as_tuples(after["existence"]["feasible"])
        for x in probes:
            if _in_set(x, feasible_before):
                assert _in_set(x, feasible_after)
        uncovered_before = _as_tuples(before["full_window"]["uncovered"])
        uncovered_after = _as_tuples(after["full_window"]["uncovered"])
        for x in probes:
            if _in_set(x, uncovered_after):
                assert _in_set(x, uncovered_before)
        checked += 1
    assert checked > 100


def test_changing_nominal_never_changes_existence_or_full_window_rows():
    from TrialLedger.layer2 import protocol_schedule

    rng = random.Random(13)
    for data, claims in _random_cases(count=200, seed=99):
        other = dict(data, nominal=_raw_rational(rng.choice(GRID)) if rng.random() < 0.8 else None)
        active = DEFAULT_CLAIMS if claims is None else claims
        first = protocol_schedule.check("schedule_coverage", data, active)
        second = protocol_schedule.check("schedule_coverage", other, active)
        rows_first = {row["id"]: row for row in first["value"]["claims"]}
        rows_second = {row["id"]: row for row in second["value"]["claims"]}
        for cid, row in rows_first.items():
            if row["claim"] in ("existence", "full_window"):
                assert rows_second[cid] == row
