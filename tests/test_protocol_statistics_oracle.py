"""Independent oracle for the binomial_design operator (interface v1, V3 and packet D').

The oracle never imports the production module at import time. Step-one tests use only
this file and the fixture. Step-two tests import TrialLedger.layer2.protocol_statistics
inside each test body and call evaluate/check directly.

The oracle enumerates all 2**n binary outcome vectors, multiplies exact Fraction factors
p or (1 - p) per vector, and sums the probabilities of vectors with at least k successes.
It uses no math.comb, no closed form, no floats and no Decimal.
"""

import itertools
import json
from fractions import Fraction
from functools import cache
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/binomial.json"
)
FIXTURE_DATA = json.loads(FIXTURE.read_text())

ORACLE_MAX_N = 10
GRID = [
    Fraction(0),
    Fraction(1, 3),
    Fraction(2, 5),
    Fraction(1, 2),
    Fraction(3, 4),
    Fraction(9, 10),
    Fraction(1),
]
N_RANGE = range(1, ORACLE_MAX_N + 1)
ROLES = ("fixed_n", "iid_binary", "alignment")


@cache
def _vector_probabilities(n, p):
    """(success_count, exact probability) for each of the 2**n outcome vectors."""
    q = 1 - p
    rows = []
    for vector in itertools.product((0, 1), repeat=n):
        probability = Fraction(1)
        for outcome in vector:
            probability *= p if outcome else q
        rows.append((sum(vector), probability))
    return tuple(rows)


def oracle_tail(n, k, p):
    """Exact P(successes >= k) under n i.i.d. Bernoulli(p) trials, by enumeration."""
    return sum(
        (probability for successes, probability in _vector_probabilities(n, p) if successes >= k),
        Fraction(0),
    )


def oracle_exactly(n, count, p):
    """Exact P(successes == count) under n i.i.d. Bernoulli(p) trials, by enumeration."""
    return sum(
        (probability for successes, probability in _vector_probabilities(n, p) if successes == count),
        Fraction(0),
    )


def canonical(value):
    """Canonical rational string for an exact Fraction: reduced, no '/1', zero as '0'."""
    return str(Fraction(value))


def _assumptions():
    return [
        {
            "role": role,
            "ref": f"user:{role} assumption (oracle test)",
            "version": "1",
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:simulated planning choice (oracle test)"],
        }
        for role in ROLES
    ]


def _data(n, k, p0, p1):
    return {
        "scope": "draft:oracle-check",
        "model": "fixed_n_iid_bernoulli",
        "direction": "greater",
        "n": n,
        "critical_count": k,
        "p0": canonical(p0),
        "p1": canonical(p1),
        "assumptions": _assumptions(),
    }


def _valid_pairs():
    return [(a, b) for a in GRID for b in GRID if a < b]


# ---------------------------------------------------------------------------
# STEP ONE: oracle against fixtures and STA-1 (no production import)
# ---------------------------------------------------------------------------


def test_oracle_reproduces_every_fixture_expectation_with_n_at_most_10():
    mismatches = []
    checked = 0
    for case in FIXTURE_DATA["cases"]:
        expect = case["expect"]
        if "null_rejection_probability" not in expect or "power" not in expect:
            continue
        data = case["data"]
        n = data["n"]
        if n > ORACLE_MAX_N:
            continue
        k = data["critical_count"]
        p0 = Fraction(data["p0"])
        p1 = Fraction(data["p1"])
        got_null = canonical(oracle_tail(n, k, p0))
        got_power = canonical(oracle_tail(n, k, p1))
        checked += 1
        if got_null != expect["null_rejection_probability"]:
            mismatches.append(
                f"{case['id']} null: oracle {got_null} vs fixture {expect['null_rejection_probability']}"
            )
        if got_power != expect["power"]:
            mismatches.append(f"{case['id']} power: oracle {got_power} vs fixture {expect['power']}")
    assert checked >= 6, f"expected several fixture cases with n<=10, found {checked}"
    assert mismatches == [], "oracle disagrees with fixture:\n" + "\n".join(mismatches)


def test_oracle_matches_sta1_exact_numbers():
    half, three_quarters = Fraction(1, 2), Fraction(3, 4)
    assert oracle_tail(2, 2, half) == Fraction(1, 4)
    assert oracle_tail(2, 2, three_quarters) == Fraction(9, 16)
    assert oracle_tail(2, 1, half) == Fraction(3, 4)
    assert oracle_tail(2, 1, three_quarters) == Fraction(15, 16)


# ---------------------------------------------------------------------------
# Oracle self-checks (still no production import)
# ---------------------------------------------------------------------------


def test_oracle_normalization_k_zero_is_exactly_one():
    for n in N_RANGE:
        for p in GRID:
            assert oracle_tail(n, 0, p) == 1, (n, p)


def test_oracle_k_n_plus_one_is_exactly_zero():
    for n in N_RANGE:
        for p in GRID:
            assert oracle_tail(n, n + 1, p) == 0, (n, p)


def test_oracle_is_non_increasing_in_k():
    for n in N_RANGE:
        for p in GRID:
            tails = [oracle_tail(n, k, p) for k in range(n + 2)]
            for lower, higher in zip(tails, tails[1:], strict=False):
                assert lower >= higher, (n, p, tails)


def test_oracle_is_non_decreasing_in_p_over_rational_grid():
    for n in N_RANGE:
        for k in range(n + 2):
            tails = [oracle_tail(n, k, p) for p in GRID]
            for smaller, larger in zip(tails, tails[1:], strict=False):
                assert smaller <= larger, (n, k, tails)


def test_oracle_difference_between_k_and_k_minus_one_is_exact_mass_at_k_minus_one():
    for n in N_RANGE:
        for p in GRID:
            for k in range(1, n + 2):
                difference = oracle_tail(n, k - 1, p) - oracle_tail(n, k, p)
                assert difference == oracle_exactly(n, k - 1, p), (n, k, p)


# ---------------------------------------------------------------------------
# STEP TWO: comparison with the production module (module may be absent)
# ---------------------------------------------------------------------------


def test_production_null_and_power_match_oracle_for_all_n_k_and_grid_pairs():
    from TrialLedger.layer2 import protocol_statistics

    mismatches = []
    for n in N_RANGE:
        for k in range(n + 2):
            for p0, p1 in _valid_pairs():
                result = protocol_statistics.evaluate("binomial_design", _data(n, k, p0, p1))
                want_null = canonical(oracle_tail(n, k, p0))
                want_power = canonical(oracle_tail(n, k, p1))
                got_null = result["value"]["null_rejection_probability"]
                got_power = result["value"]["power"]
                if result["code"] != "computed" or got_null != want_null or got_power != want_power:
                    mismatches.append(
                        f"n={n} k={k} p0={canonical(p0)} p1={canonical(p1)}: "
                        f"code={result['code']} null={got_null} (oracle {want_null}) "
                        f"power={got_power} (oracle {want_power})"
                    )
    assert mismatches == [], f"{len(mismatches)} mismatches, first: {mismatches[:5]}"


def test_check_decides_claims_equal_to_exact_probability_for_both_comparisons():
    from TrialLedger.layer2 import protocol_statistics

    problems = []
    for n in N_RANGE:
        for k in range(n + 2):
            for p0, p1 in _valid_pairs():
                null = oracle_tail(n, k, p0)
                power = oracle_tail(n, k, p1)
                claims = [
                    {
                        "id": "a-le",
                        "quantity": "null_rejection_probability",
                        "comparison": "<=",
                        "value": canonical(null),
                    },
                    {
                        "id": "a-ge",
                        "quantity": "null_rejection_probability",
                        "comparison": ">=",
                        "value": canonical(null),
                    },
                    {"id": "p-le", "quantity": "power", "comparison": "<=", "value": canonical(power)},
                    {"id": "p-ge", "quantity": "power", "comparison": ">=", "value": canonical(power)},
                ]
                result = protocol_statistics.check("binomial_design", _data(n, k, p0, p1), claims)
                outcomes = {row["id"]: row["outcome"] for row in result["value"]["claims"]}
                if outcomes != {
                    "a-le": "satisfied",
                    "a-ge": "satisfied",
                    "p-le": "satisfied",
                    "p-ge": "satisfied",
                }:
                    problems.append(f"n={n} k={k} p0={canonical(p0)} p1={canonical(p1)}: {outcomes}")
                if result["code"] != "satisfied":
                    problems.append(
                        f"n={n} k={k} p0={canonical(p0)} p1={canonical(p1)}: code {result['code']}"
                    )
    assert problems == [], f"{len(problems)} problems, first: {problems[:5]}"


def test_check_refuses_a_claim_strictly_below_the_exact_probability_with_le_and_accepts_with_ge():
    from TrialLedger.layer2 import protocol_statistics

    problems = []
    for n in N_RANGE:
        for k in range(1, n + 2):
            for p0, p1 in _valid_pairs():
                null = oracle_tail(n, k, p0)
                if null == 0:
                    continue
                half_value = null / 2
                claims = [
                    {
                        "id": "below-le",
                        "quantity": "null_rejection_probability",
                        "comparison": "<=",
                        "value": canonical(half_value),
                    },
                    {
                        "id": "below-ge",
                        "quantity": "null_rejection_probability",
                        "comparison": ">=",
                        "value": canonical(half_value),
                    },
                ]
                result = protocol_statistics.check("binomial_design", _data(n, k, p0, p1), claims)
                outcomes = {row["id"]: row["outcome"] for row in result["value"]["claims"]}
                if outcomes != {"below-le": "not_satisfied", "below-ge": "satisfied"}:
                    problems.append(f"n={n} k={k} p0={canonical(p0)} p1={canonical(p1)}: {outcomes}")
                if result["code"] != "not_satisfied":
                    problems.append(
                        f"n={n} k={k} p0={canonical(p0)} p1={canonical(p1)}: code {result['code']}"
                    )
    assert problems == [], f"{len(problems)} problems, first: {problems[:5]}"


def test_evaluate_equals_check_with_no_claims():
    from TrialLedger.layer2 import protocol_statistics

    for n in N_RANGE:
        for k in range(n + 2):
            for p0, p1 in _valid_pairs():
                data = _data(n, k, p0, p1)
                assert protocol_statistics.evaluate("binomial_design", data) == protocol_statistics.check(
                    "binomial_design", data, []
                ), (n, k, p0, p1)
