"""Exact one-stage binomial efficacy calculation for protocol designs (interface v1, contract C7, packet D).

The operator computes exact tail probabilities conditional on a declared fixed-n, iid binary model. It does
not validate that model, search n or k, simulate, optimize, extrapolate to adaptive stopping, or supply
planning defaults. Display strings are rounded conveniences; comparisons and canonical values use exact
rationals only.
"""

from __future__ import annotations

import copy
import math
from fractions import Fraction
from typing import Any, cast

from TrialLedger.layer2 import protocol_numbers
from TrialLedger.layer2.signals import support_state

KIND = "binomial_design"
MODEL = "fixed_n_iid_bernoulli"
DIRECTION = "greater"
RULE = "binomial.exact_one_stage_greater:1"
GUARANTEE = "exact_conditional_on_declared_model"
NOT_COMPUTED = [
    "sample_size_search",
    "sequential_or_adaptive_operating_characteristics",
    "clinical_applicability",
]
MAX_N = 512
MAX_INTERMEDIATE_BITS = 1_048_576
MAX_ASSUMPTIONS = 16
MAX_CLAIMS = 16
MAX_BASIS = 32
MAX_SCOPE = 1024
MAX_MODEL = 128
MAX_DIRECTION = 64
ROLES = ("fixed_n", "iid_binary", "alignment")
QUANTITIES = ("null_rejection_probability", "power")
COMPARISONS = ("<=", ">=")
STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
DATA_FIELDS = frozenset({"scope", "model", "direction", "n", "critical_count", "p0", "p1", "assumptions"})
ASSUMPTION_FIELDS = frozenset({"role", "ref", "version", "status", "resolution", "basis"})
CLAIM_FIELDS = frozenset({"id", "quantity", "comparison", "value"})
DISPLAY_SCALE = 10_000

# Invented, runnable example for discovery. Values are not clinical defaults; all three roles carry known,
# resolved standing only for this illustration.
EXAMPLES = {
    KIND: {
        "scope": "invented:phase2-response-example",
        "model": MODEL,
        "direction": DIRECTION,
        "n": 2,
        "critical_count": 2,
        "p0": "1/2",
        "p1": "3/4",
        "assumptions": [
            {
                "role": role,
                "ref": f"invented:{role} assumption (example)",
                "version": "1",
                "status": "known",
                "resolution": "resolved",
                "basis": ["invented:example planning choice"],
            }
            for role in ROLES
        ],
    }
}

INPUTS = {
    KIND: {
        "required": tuple(sorted(DATA_FIELDS)),
        "fields": {
            "scope": "nonempty string of at most 1024 characters",
            "model": "nonempty string; only fixed_n_iid_bernoulli computes, others unsupported_method",
            "direction": "nonempty string; only greater computes, others unsupported_method",
            "n": "strict int, 1 <= n <= 512",
            "critical_count": "strict int, 0 <= k <= n+1",
            "p0, p1": "exact rationals with 0 <= p0 < p1 <= 1",
            "assumptions": "1 to 16 unique {role, ref, version, status, resolution, basis}; role in fixed_n, "
            "iid_binary, alignment",
        },
        "claims": "0 to 16 distinct {id, quantity, comparison, value}; quantity "
        "null_rejection_probability or power; comparison <= or >=; value an exact rational in [0, 1]. "
        "Claims never change the arithmetic",
        "codes": ("computed", "satisfied", "not_satisfied", "unsupported_method", "limit"),
        "limits": {
            "max_n": MAX_N,
            "max_intermediate_bits": MAX_INTERMEDIATE_BITS,
            "work_reservation": "12 * (n + 2)",
        },
    }
}


# ----------------------------------------------------------------------------------------------------
# Input translation. Every malformed value raises a named ValueError; nothing is coerced.
# ----------------------------------------------------------------------------------------------------


def _text(value: object, limit: int, code: str) -> str:
    if type(value) is not str or not value or len(value) > limit:
        raise ValueError(code)
    return value


def _assumptions(raw: object) -> list[dict]:
    if type(raw) is not list or not 1 <= len(raw) <= MAX_ASSUMPTIONS:
        raise ValueError("binomial_invalid_assumption")
    parsed: list[dict] = []
    for item in raw:
        if type(item) is not dict or set(item) != ASSUMPTION_FIELDS:
            raise ValueError("binomial_invalid_assumption")
        item = cast(dict[str, Any], item)
        if item["role"] not in ROLES:
            raise ValueError("binomial_invalid_assumption")
        _text(item["ref"], MAX_SCOPE, "binomial_invalid_assumption")
        _text(item["version"], MAX_MODEL, "binomial_invalid_assumption")
        if item["status"] not in STATUSES or item["resolution"] not in RESOLUTIONS:
            raise ValueError("binomial_invalid_assumption")
        basis = item["basis"]
        if type(basis) is not list or not 1 <= len(basis) <= MAX_BASIS:
            raise ValueError("binomial_invalid_assumption")
        for entry in basis:
            _text(entry, MAX_SCOPE, "binomial_invalid_assumption")
        if len(set(basis)) != len(basis):
            raise ValueError("binomial_invalid_assumption")
        if any(item == prior for prior in parsed):
            raise ValueError("binomial_duplicate_assumption")
        parsed.append(item)
    return parsed


def _data(data: object) -> dict[str, Any]:
    if type(data) is not dict or set(data) != DATA_FIELDS:
        raise ValueError("binomial_data_fields")
    data = cast(dict[str, Any], data)
    scope = _text(data["scope"], MAX_SCOPE, "binomial_invalid_scope")
    model = _text(data["model"], MAX_MODEL, "binomial_invalid_model")
    direction = _text(data["direction"], MAX_DIRECTION, "binomial_invalid_direction")
    n = data["n"]
    if type(n) is not int or n < 1:
        raise ValueError("binomial_invalid_n")
    if n > MAX_N:
        raise ValueError("binomial_n_ceiling")
    k = data["critical_count"]
    if type(k) is not int or not 0 <= k <= n + 1:
        raise ValueError("binomial_invalid_critical_count")
    p0 = protocol_numbers.rational(data["p0"], "binomial")
    p1 = protocol_numbers.rational(data["p1"], "binomial")
    if not 0 <= p0 < p1 <= 1:
        raise ValueError("binomial_invalid_probabilities")
    return {
        "scope": scope,
        "model": model,
        "direction": direction,
        "n": n,
        "critical_count": k,
        "p0": p0,
        "p1": p1,
        "assumptions": _assumptions(data["assumptions"]),
    }


def _claims(raw: object) -> list[dict]:
    if type(raw) is not list or len(raw) > MAX_CLAIMS:
        raise ValueError("binomial_invalid_claims")
    parsed: list[dict] = []
    identities: set[str] = set()
    for item in raw:
        if type(item) is not dict or set(item) != CLAIM_FIELDS:
            raise ValueError("binomial_invalid_claims")
        item = cast(dict[str, Any], item)
        identity = _text(item["id"], MAX_SCOPE, "binomial_invalid_claims")
        if item["quantity"] not in QUANTITIES or item["comparison"] not in COMPARISONS:
            raise ValueError("binomial_invalid_claims")
        bound = protocol_numbers.rational(item["value"], "binomial")
        if not 0 <= bound <= 1:
            raise ValueError("binomial_invalid_claims")
        if identity in identities:
            raise ValueError("binomial_duplicate_claim")
        identities.add(identity)
        parsed.append(
            {
                "id": identity,
                "quantity": item["quantity"],
                "comparison": item["comparison"],
                "bound": bound,
            }
        )
    return parsed


# ----------------------------------------------------------------------------------------------------
# Pure classification helpers. Each names one decision and returns a fixed code.
# ----------------------------------------------------------------------------------------------------


def claim_outcome(computed: Fraction, comparison: str, bound: Fraction) -> str:
    """Compare one exact computed probability with one exact claim bound; never a display string.

    pre: comparison in ("<=", ">=")
    post: __return__ in ("satisfied", "not_satisfied")
    post: __return__ != "satisfied" or (computed <= bound if comparison == "<=" else computed >= bound)
    post: __return__ != "not_satisfied" or (computed > bound if comparison == "<=" else computed < bound)
    """
    if comparison == "<=":
        return "satisfied" if computed <= bound else "not_satisfied"
    return "satisfied" if computed >= bound else "not_satisfied"


def support_status_code(statuses: list[str]) -> str:
    """The weakest status actually declared on the assumptions; never proposed unless one is proposed.

    pre: len(statuses) >= 1 and all(status in ("known", "interpolated", "proposed") for status in statuses)
    post: __return__ in ("known", "interpolated", "proposed")
    post: (__return__ == "proposed") == ("proposed" in statuses)
    post: __return__ != "interpolated" or "interpolated" in statuses
    post: __return__ != "known" or all(status == "known" for status in statuses)
    """
    if "proposed" in statuses:
        return "proposed"
    if "interpolated" in statuses:
        return "interpolated"
    return "known"


def support_resolution_code(resolutions: list[str], role_missing: bool) -> str:
    """The worst declared resolution, raised to at least unresolved when a required role is missing.

    pre: len(resolutions) >= 1 and all(value in RESOLUTIONS for value in resolutions)
    post: __return__ in ("conflicting", "unresolved", "partially_resolved", "resolved")
    post: __return__ == "conflicting" or "conflicting" not in resolutions
    post: __return__ in ("conflicting", "unresolved") or not (role_missing or "unresolved" in resolutions)
    post: not role_missing or __return__ != "resolved"
    post: __return__ != "resolved" or all(value == "resolved" for value in resolutions)
    """
    order = ("conflicting", "unresolved", "partially_resolved", "resolved")
    worst = next(value for value in order if value in resolutions) if resolutions else "resolved"
    if role_missing and worst in ("resolved", "partially_resolved"):
        return "unresolved"
    return worst


def application_code(reasons: list[str]) -> str:
    """Withheld exactly when some reason names a missing role or a non-accepted assumption.

    pre: all(isinstance(reason, str) for reason in reasons)
    post: __return__ in ("withheld", "not_withheld_by_assumptions")
    post: (__return__ == "withheld") == bool(reasons)
    """
    return "withheld" if reasons else "not_withheld_by_assumptions"


def result_code(limited: bool, outcomes: list[str]) -> str:
    """Name the whole result from the limit flag and claim outcomes, without computing any probability.

    pre: all(outcome in ("satisfied", "not_satisfied", "limit") for outcome in outcomes)
    pre: not limited or all(outcome == "limit" for outcome in outcomes)
    post: __return__ in ("limit", "not_satisfied", "satisfied", "computed")
    post: __return__ != "limit" or limited
    post: __return__ != "not_satisfied" or "not_satisfied" in outcomes
    post: __return__ != "satisfied" or (bool(outcomes) and all(o == "satisfied" for o in outcomes))
    post: __return__ != "computed" or not outcomes
    """
    if limited:
        return "limit"
    if "not_satisfied" in outcomes:
        return "not_satisfied"
    if outcomes:
        return "satisfied"
    return "computed"


# ----------------------------------------------------------------------------------------------------
# Exact arithmetic with work counting and bit ceiling.
# ----------------------------------------------------------------------------------------------------


class _Exceeded(Exception):
    """Internal: an exact intermediate passed MAX_INTERMEDIATE_BITS. Converted to code `limit` by check."""


class _Work:
    """Counts one charged Fraction operation (*, + or **) and checks bit growth after each."""

    def __init__(self) -> None:
        self.used = 0

    def _charge(self, value: Fraction) -> Fraction:
        self.used += 1
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_INTERMEDIATE_BITS:
            raise _Exceeded
        return value

    def mul(self, left: int | Fraction, right: Fraction) -> Fraction:
        return self._charge(left * right)

    def add(self, left: Fraction, right: Fraction) -> Fraction:
        return self._charge(left + right)

    def power(self, base: Fraction, exponent: int) -> Fraction:
        return self._charge(base**exponent)


def _tail(work: _Work, n: int, k: int, p: Fraction) -> Fraction:
    """Exact Pr(X >= k) for X ~ Binomial(n, p), each term computed directly (never by dividing by p or q)."""
    q = 1 - p
    total: Fraction | None = None
    for i in range(k, n + 1):
        term = work.mul(work.mul(math.comb(n, i), work.power(p, i)), work.power(q, n - i))
        total = term if total is None else work.add(total, term)
    return Fraction(0) if total is None else total


def _estimated_bits(n: int, p0: Fraction, p1: Fraction) -> int:
    """Pre-computation bound B = n*b + n + 2, with b the widest numerator or denominator of p and 1-p.

    pre: n >= 1
    post: __return__ >= n + 2
    """
    widths = [
        abs(part).bit_length() for p in (p0, 1 - p0, p1, 1 - p1) for part in (p.numerator, p.denominator)
    ]
    return n * max(widths) + n + 2


def _display(value: Fraction) -> str:
    """Round half-even to 4 decimal places using exact integer arithmetic on the scaled rational."""
    scaled = round(value * DISPLAY_SCALE)
    whole, fraction = divmod(scaled, DISPLAY_SCALE)
    return f"{whole}.{fraction:04d}"


def _envelope(
    code: str,
    value: dict,
    blockers: list[str],
    support_status: str | None,
    determining_ids: list[str],
    support_resolution: str | None,
) -> dict:
    return {
        "code": code,
        "value": value,
        "blockers": sorted(set(blockers)),
        "rule": RULE,
        "support_status": support_status,
        "determining_ids": determining_ids,
        "support_resolution": support_resolution,
    }


# ----------------------------------------------------------------------------------------------------
# Public operator contract (signals module contract).
# ----------------------------------------------------------------------------------------------------


def work_reservation(data: dict) -> int:
    """Reserved work R = 12 * (n + 2); raises the same translation codes as check for malformed data."""
    return 12 * (_data(data)["n"] + 2)


def evaluate(kind: str, data: dict) -> dict:
    """The operator result with no claims."""
    return check(kind, data, [])


def validate(kind: str, data: dict, claims: list[dict]) -> None:
    """Admission-time input check: the named refusals check() would raise, without computing anything.

    Parses the data and the requested claims exactly as check() does, so a malformed declaration is refused
    before any work is reserved or any claim is evaluated (PAH cold audit: parameters refused only at run).
    """
    if kind != KIND:
        raise ValueError("unsupported_binomial_kind")
    _data(data)
    _claims(claims)


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Exact tails and claim outcomes; claims compare exact rationals and never change the arithmetic.

    pre: kind == KIND, else ValueError("unsupported_binomial_kind")
    post: __return__["code"] in ("unsupported_method", "limit", "not_satisfied", "satisfied", "computed")
    post: __return__["support_status"] in (None, "known", "interpolated", "proposed")
    """
    if kind != KIND:
        raise ValueError("unsupported_binomial_kind")
    parsed = _data(data)
    bounds = _claims(claims)
    assumptions = parsed["assumptions"]
    roles = {item["role"] for item in assumptions}
    missing = [role for role in ROLES if role not in roles]
    refs = list(dict.fromkeys(item["ref"] for item in assumptions))
    coverage = {role: "missing" if role in missing else "declared" for role in ROLES}

    if parsed["model"] != MODEL or parsed["direction"] != DIRECTION:
        value = {
            "scope": parsed["scope"],
            "model": parsed["model"],
            "direction": parsed["direction"],
            "computed": False,
            "reason": "unsupported_method",
            "assumptions": copy.deepcopy(assumptions),
        }
        return _envelope("unsupported_method", value, ["binomial_unsupported_method"], None, [], None)

    not_accepted = [
        f"assumption_not_accepted:{item['ref']}"
        for item in assumptions
        if support_state([item["status"]], [item["resolution"]]) != "accepted"
    ]
    reasons = sorted([f"assumption_missing:{role}" for role in missing] + not_accepted)
    application = {"code": application_code(reasons), "reasons": reasons}
    support = support_status_code([item["status"] for item in assumptions])
    resolution = support_resolution_code(
        [item["resolution"] for item in assumptions], role_missing=bool(missing)
    )

    n, k, p0, p1 = parsed["n"], parsed["critical_count"], parsed["p0"], parsed["p1"]
    reserved = 12 * (n + 2)
    work = _Work()
    limited = _estimated_bits(n, p0, p1) > MAX_INTERMEDIATE_BITS
    null_tail = power_tail = Fraction(0)
    if not limited:
        try:
            null_tail = _tail(work, n, k, p0)
            power_tail = _tail(work, n, k, p1)
        except _Exceeded:
            limited = True

    rows = []
    for claim in bounds:
        if limited:
            computed = None
            outcome = "limit"
        else:
            computed = null_tail if claim["quantity"] == "null_rejection_probability" else power_tail
            outcome = claim_outcome(computed, claim["comparison"], claim["bound"])
        rows.append(
            {
                "id": claim["id"],
                "quantity": claim["quantity"],
                "comparison": claim["comparison"],
                "value": protocol_numbers.render(claim["bound"]),
                "computed": None if computed is None else protocol_numbers.render(computed),
                "outcome": outcome,
            }
        )

    code = result_code(limited, [row["outcome"] for row in rows])
    blockers = [f"binomial_assumption_missing:{role}" for role in missing]
    blockers += [
        f"binomial_claim_not_satisfied:{row['id']}" for row in rows if row["outcome"] == "not_satisfied"
    ]
    if limited:
        blockers.append("binomial_bit_limit")
    value = {
        "scope": parsed["scope"],
        "model": MODEL,
        "direction": DIRECTION,
        "n": n,
        "critical_count": k,
        "p0": protocol_numbers.render(p0),
        "p1": protocol_numbers.render(p1),
        "null_rejection_probability": None if limited else protocol_numbers.render(null_tail),
        "power": None if limited else protocol_numbers.render(power_tail),
        "display": None
        if limited
        else {
            "null_rejection_probability": _display(null_tail),
            "power": _display(power_tail),
            "rounding": "half_even_4dp",
        },
        "claims": rows,
        "assumptions": copy.deepcopy(assumptions),
        "assumption_coverage": coverage,
        "application": application,
        "work": {"reserved": reserved, "used": work.used, "max_bits": MAX_INTERMEDIATE_BITS},
        "guarantee": GUARANTEE,
        "not_computed": list(NOT_COMPUTED),
    }
    if limited:
        return _envelope("limit", value, blockers, None, refs, None)
    return _envelope(code, value, blockers, support, refs, resolution)
