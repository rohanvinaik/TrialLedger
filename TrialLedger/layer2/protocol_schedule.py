"""Exact schedule coverage for one assessment: feasible time and full-window coverage (packet B, C5).

The operator compares declared rational intervals only. It never converts units or anchors, samples days, or
narrows the permitted window to its feasible part. Each claim row names the inputs that decided it.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, cast

from TrialLedger.layer2 import protocol_numbers

KIND = "schedule_coverage"
RULE = "schedule.exact_interval_coverage:1"
GUARANTEE = "exact_over_declared_intervals"
FIELDS = ("scope", "anchor", "unit", "nominal", "permitted", "available")
CLAIM_KINDS = ("existence", "nominal", "full_window")
VIOLATED_OUTCOMES = ("no_permitted_time", "no_feasible_time", "outside_window", "not_collected", "uncovered")
UNRESOLVED_OUTCOMES = ("unresolved", "unknown_target")
MAX_SCOPE = 1024
MAX_ANCHOR = 256
MAX_UNIT = 64
NEG = (-1, None)
POS = (1, None)
INPUTS = {
    KIND: {
        "required": FIELDS,
        "optional": (),
        "fields": {
            "scope": "nonempty opaque validated scope identity, at most 1024 characters",
            "anchor": "nonempty exact event identity, at most 256 characters, never interpreted",
            "unit": "nonempty exact unit identity, at most 64 characters, compared by equality only",
            "nominal": "exact rational string, or null for no declared nominal target (never defaulted)",
            "permitted": "interval union of the permitted window; null is unknown, [] is explicitly none",
            "available": "interval union of collection; null is unknown, [] is explicitly no collection",
        },
        "claims": {
            "required": "1 to 3 {id, claim}; claim in existence, nominal, full_window, each at most once",
            "default": "existence, nominal and full_window with the ids of those names",
        },
        "outcomes": {
            "existence": ("satisfied", "no_feasible_time", "no_permitted_time", "unresolved"),
            "nominal": ("satisfied", "not_collected", "outside_window", "unknown_target", "unresolved"),
            "full_window": ("satisfied", "uncovered", "no_permitted_time", "unresolved"),
        },
        "limits": {"union_intervals": 32, "work": "4*(w+c)**2 + 6*(w+c) + 8 endpoint comparisons"},
    }
}

EXAMPLES = {
    KIND: {
        "scope": "invented:week-12-assessment",
        "anchor": "invented:randomization",
        "unit": "invented-day",
        "nominal": "84",
        "permitted": [{"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}],
        "available": [{"lower": None, "upper": "80", "lower_inclusive": False, "upper_inclusive": True}],
    }
}


class _Work:
    """Counts each endpoint comparison, the only operation charged against the reservation."""

    __slots__ = ("used",)

    def __init__(self) -> None:
        self.used = 0

    def cmp(self, x: tuple, y: tuple) -> int:
        """Compare two endpoint keys (kind -1 for -inf, 0 finite, 1 for +inf) and charge one comparison.

        pre: x[0] in (-1, 0, 1) and y[0] in (-1, 0, 1)
        post: __return__ in (-1, 0, 1)
        post: __return__ == 0 or x != y
        """
        self.used += 1
        if x[0] != y[0]:
            return -1 if x[0] < y[0] else 1
        if x[0] != 0:
            return 0
        return (x[1] > y[1]) - (x[1] < y[1])


def existence_outcome(w_known: bool, w_empty: bool, c_known: bool, overlap: bool) -> str:
    """Classify the existence row of a schedule: is there a permitted assessment time that is collected?

    pre: not w_empty or w_known
    pre: not overlap or (w_known and c_known and not w_empty)
    post: __return__ in ('no_permitted_time', 'unresolved', 'satisfied', 'no_feasible_time')
    post: __return__ != 'no_permitted_time' or (w_known and w_empty)
    post: __return__ != 'satisfied' or overlap
    """
    if w_known and w_empty:
        return "no_permitted_time"
    if not (w_known and c_known):
        return "unresolved"
    return "satisfied" if overlap else "no_feasible_time"


def nominal_outcome(n_known: bool, w_known: bool, in_w: bool, c_known: bool, in_c: bool) -> str:
    """Classify the nominal row; a known target outside the window survives unknown collection.

    pre: not in_w or (n_known and w_known)
    pre: not in_c or in_w
    post: __return__ in ('unknown_target', 'unresolved', 'outside_window', 'not_collected', 'satisfied')
    post: __return__ != 'unknown_target' or not n_known
    post: __return__ != 'outside_window' or (n_known and w_known and not in_w)
    post: __return__ != 'satisfied' or (in_w and in_c)
    """
    if not n_known:
        return "unknown_target"
    if not w_known:
        return "unresolved"
    if not in_w:
        return "outside_window"
    if not c_known:
        return "unresolved"
    return "satisfied" if in_c else "not_collected"


def full_window_outcome(w_known: bool, w_empty: bool, c_known: bool, covered: bool) -> str:
    """Classify full-window coverage; an empty permitted window is never vacuous success.

    pre: not w_empty or w_known
    pre: not covered or (w_known and c_known and not w_empty)
    post: __return__ in ('no_permitted_time', 'unresolved', 'satisfied', 'uncovered')
    post: __return__ != 'no_permitted_time' or (w_known and w_empty)
    post: __return__ != 'satisfied' or covered
    """
    if w_known and w_empty:
        return "no_permitted_time"
    if not (w_known and c_known):
        return "unresolved"
    return "satisfied" if covered else "uncovered"


def determined_by(claim: str, outcome: str) -> list[str]:
    """Name the minimal input roles a row's outcome depends on, sorted.

    pre: claim in ('existence', 'nominal', 'full_window')
    pre: outcome in ('satisfied', 'no_feasible_time', 'no_permitted_time', 'uncovered', 'not_collected',
         'outside_window', 'unknown_target', 'unresolved')
    post: __return__ == sorted(__return__)
    post: outcome != 'unresolved' or __return__ == []
    """
    if outcome == "unresolved":
        return []
    if outcome == "unknown_target":
        return ["nominal"]
    if outcome == "no_permitted_time":
        return ["permitted"]
    if outcome == "outside_window":
        return ["nominal", "permitted"]
    if claim == "nominal":
        return ["available", "nominal", "permitted"]
    return ["available", "permitted"]


def missing_inputs(outcome: str, w_known: bool, c_known: bool) -> list[str]:
    """Name the unknown inputs that prevent a row from being decided, sorted.

    pre: outcome in ('satisfied', 'no_feasible_time', 'no_permitted_time', 'uncovered', 'not_collected',
         'outside_window', 'unknown_target', 'unresolved')
    post: __return__ == sorted(__return__)
    post: outcome != 'unresolved' or __return__ != []
    post: outcome == 'unknown_target' or outcome == 'unresolved' or __return__ == []
    """
    if outcome == "unknown_target":
        return ["nominal"]
    if outcome != "unresolved":
        return []
    missing = []
    if not w_known:
        missing.append("permitted")
    if not c_known:
        missing.append("available")
    return sorted(missing)


def outcome_class(outcome: str) -> str:
    """Group a row outcome into the aggregate classes used by the code and blockers (pure).

    pre: outcome in ('satisfied', 'no_feasible_time', 'no_permitted_time', 'uncovered', 'not_collected',
         'outside_window', 'unknown_target', 'unresolved')
    post: __return__ in ('violated', 'unresolved', 'satisfied')
    post: (__return__ == 'satisfied') == (outcome == 'satisfied')
    post: __return__ != 'violated' or outcome in ('no_permitted_time', 'no_feasible_time', 'outside_window',
          'not_collected', 'uncovered')
    """
    if outcome == "satisfied":
        return "satisfied"
    if outcome in UNRESOLVED_OUTCOMES:
        return "unresolved"
    return "violated"


def schedule_code(classes: list[str]) -> str:
    """Aggregate row classes: any violation wins, then any unresolved row, else satisfied (pure).

    pre: all(c in ('violated', 'unresolved', 'satisfied') for c in classes)
    post: __return__ in ('violated', 'unresolved', 'satisfied')
    post: __return__ != 'violated' or 'violated' in classes
    post: __return__ != 'satisfied' or all(c == 'satisfied' for c in classes)
    """
    if "violated" in classes:
        return "violated"
    if "unresolved" in classes:
        return "unresolved"
    return "satisfied"


def _claim_rows(claims: object) -> list[tuple[str, str]]:
    if type(claims) is not list or not 1 <= len(claims) <= len(CLAIM_KINDS):
        raise ValueError("schedule_invalid_claims")
    ids: set[str] = set()
    kinds: set[str] = set()
    rows = []
    for item in claims:
        if type(item) is not dict or set(item) != {"id", "claim"}:
            raise ValueError("schedule_invalid_claims")
        item = cast(dict[str, Any], item)
        identity, claim = item["id"], item["claim"]
        if type(identity) is not str or not identity or type(claim) is not str:
            raise ValueError("schedule_invalid_claims")
        if claim not in CLAIM_KINDS:
            raise ValueError("schedule_invalid_claims")
        if identity in ids or claim in kinds:
            raise ValueError("schedule_duplicate_claim")
        ids.add(identity)
        kinds.add(claim)
        rows.append((identity, claim))
    return rows


def _keys(raw: list | None) -> list | None:
    """Endpoint-keyed intervals (lo, hi, lower_inclusive, upper_inclusive); infinity is kind -1 or +1."""
    if raw is None:
        return None
    keyed = []
    for lower, upper, lower_inclusive, upper_inclusive in raw:
        lo = NEG if lower is None else (0, lower)
        hi = POS if upper is None else (0, upper)
        keyed.append((lo, hi, lower_inclusive, upper_inclusive))
    return keyed


def _parse(data: object) -> dict:
    if type(data) is not dict or set(data) != set(FIELDS):
        raise ValueError("schedule_data_fields")
    data = cast(dict[str, Any], data)
    scope, anchor, unit = data["scope"], data["anchor"], data["unit"]
    if type(scope) is not str or not 0 < len(scope) <= MAX_SCOPE:
        raise ValueError("schedule_invalid_scope")
    if type(anchor) is not str or not 0 < len(anchor) <= MAX_ANCHOR:
        raise ValueError("schedule_invalid_anchor")
    if type(unit) is not str or not 0 < len(unit) <= MAX_UNIT:
        raise ValueError("schedule_invalid_unit")
    nominal = None if data["nominal"] is None else protocol_numbers.rational(data["nominal"], "schedule")
    permitted = protocol_numbers.union(data["permitted"], "schedule")
    available = protocol_numbers.union(data["available"], "schedule")
    intervals = (permitted or []) + (available or [])
    # One charged comparison per interval whose two finite endpoints the shared parser compared.
    charge = sum(1 for lower, upper, _, _ in intervals if lower is not None and upper is not None)
    return {
        "scope": scope,
        "anchor": anchor,
        "unit": unit,
        "nominal": nominal,
        "permitted": _keys(permitted),
        "available": _keys(available),
        "charge": charge,
    }


def _reservation(parsed: dict) -> int:
    size = len(parsed["permitted"] or []) + len(parsed["available"] or [])
    return 4 * size * size + 6 * size + 8


def _lower_before(a: tuple, b: tuple, work: _Work) -> bool:
    c = work.cmp(a[0], b[0])
    return c < 0 or (c == 0 and a[2] and not b[2])


def _merge_sorted(ordered: list, work: _Work) -> list:
    """Merge a lower-sorted list only where the union is one interval; never fill a gap."""
    if not ordered:
        return []
    merged = [ordered[0]]
    for item in ordered[1:]:
        lo, hi, li, ui = merged[-1]
        c = work.cmp(item[0], hi)
        if c < 0 or (c == 0 and (ui or item[2])):
            c2 = work.cmp(item[1], hi)
            if c2 > 0:
                merged[-1] = (lo, item[1], li, item[3])
            elif c2 == 0:
                merged[-1] = (lo, hi, li, ui or item[3])
        else:
            merged.append(item)
    return merged


def _normalize(items: list, work: _Work) -> list:
    ordered: list = []
    for item in items:
        pos = len(ordered)
        while pos > 0 and _lower_before(item, ordered[pos - 1], work):
            pos -= 1
        ordered.insert(pos, item)
    return _merge_sorted(ordered, work)


def _member(ivs: list, value: Fraction, work: _Work) -> bool:
    point = (0, value)
    for lo, hi, li, ui in ivs:
        c = work.cmp(lo, point)
        if c > 0 or (c == 0 and not li):
            continue
        c2 = work.cmp(point, hi)
        if c2 < 0 or (c2 == 0 and ui):
            return True
    return False


def _intersect(a: list, b: list, work: _Work) -> list:
    """Exact intersection of two normalized, lower-sorted unions by a two-pointer sweep."""
    out: list = []
    i = j = 0
    while i < len(a) and j < len(b):
        lo_a, hi_a, li_a, ui_a = a[i]
        lo_b, hi_b, li_b, ui_b = b[j]
        c = work.cmp(lo_a, lo_b)
        if c > 0:
            lo, li = lo_a, li_a
        elif c < 0:
            lo, li = lo_b, li_b
        else:
            lo, li = lo_a, li_a and li_b
        ch = work.cmp(hi_a, hi_b)
        if ch < 0:
            hi, ui = hi_a, ui_a
        elif ch > 0:
            hi, ui = hi_b, ui_b
        else:
            hi, ui = hi_a, ui_a and ui_b
        cn = work.cmp(lo, hi)
        if cn < 0 or (cn == 0 and li and ui):
            out.append((lo, hi, li, ui))
        if ch < 0:
            i += 1
        elif ch > 0:
            j += 1
        else:
            i += 1
            j += 1
    return _merge_sorted(out, work)


def _complement(ivs: list, work: _Work) -> list:
    """Gaps of a normalized union; a gap between touching-but-separate pieces may be a single point."""
    if not ivs:
        return [(NEG, POS, False, False)]
    gaps = []
    first = ivs[0]
    if first[0][0] == 0:
        gaps.append((NEG, first[0], False, not first[2]))
    for left, right in zip(ivs, ivs[1:], strict=False):
        lo, hi = left[1], right[0]
        c = work.cmp(lo, hi)
        if c < 0 or (c == 0 and not left[3] and not right[2]):
            gaps.append((lo, hi, not left[3], not right[2]))
    last = ivs[-1]
    if last[1][0] == 0:
        gaps.append((last[1], POS, not last[3], False))
    return gaps


def _difference(a: list, b: list, work: _Work) -> list:
    if not a:
        return []
    return _intersect(a, _complement(b, work), work)


def _render(ivs: list | None) -> list | None:
    if ivs is None:
        return None
    return protocol_numbers.render_union(
        [(None if lo[0] == -1 else lo[1], None if hi[0] == 1 else hi[1], li, ui) for lo, hi, li, ui in ivs]
    )


def _row(identity: str, claim: str, outcome: str, w_known: bool, c_known: bool, feasible, uncovered) -> dict:
    return {
        "id": identity,
        "claim": claim,
        "outcome": outcome,
        "determined_by": determined_by(claim, outcome),
        "missing": missing_inputs(outcome, w_known, c_known),
        "feasible": _render(feasible),
        "uncovered": _render(uncovered),
    }


def _blocker(row: dict) -> str | None:
    klass = outcome_class(row["outcome"])
    if klass == "violated":
        return "schedule_" + row["outcome"] + ":" + row["id"]
    if klass == "unresolved":
        return "schedule_unresolved:" + row["id"]
    return None


def work_reservation(data: dict) -> int:
    """Reserved endpoint comparisons: 4*(w+c)**2 + 6*(w+c) + 8, where w and c are interval counts.

    pre: data is a dict with exactly the schedule_coverage data fields
    post: __return__ >= 8
    post: __return__ == 4 * (len(data['permitted'] or []) + len(data['available'] or [])) ** 2 + 6 * (
          len(data['permitted'] or []) + len(data['available'] or [])) + 8 when data is valid
    """
    return _reservation(_parse(data))


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Evaluate the named schedule claims exactly and return the plain result envelope.

    pre: kind == 'schedule_coverage'
    post: set(__return__) == {'code', 'value', 'blockers', 'rule'}
    post: __return__['value']['work']['used'] <= __return__['value']['work']['reserved']
    post: __return__['blockers'] == sorted(set(__return__['blockers']))
    """
    if kind != KIND:
        raise ValueError("unsupported_schedule_kind")
    parsed = _parse(data)
    requested = _claim_rows(claims)
    reserved = _reservation(parsed)
    work = _Work()
    work.used += parsed["charge"]
    permitted = None if parsed["permitted"] is None else _normalize(parsed["permitted"], work)
    available = None if parsed["available"] is None else _normalize(parsed["available"], work)
    nominal = parsed["nominal"]
    w_known = permitted is not None
    w_empty = w_known and not permitted
    c_known = available is not None
    rows = []
    for identity, claim in requested:
        if claim == "existence":
            feasible = _intersect(permitted, available, work) if w_known and c_known else None
            outcome = existence_outcome(w_known, w_empty, c_known, bool(feasible))
            rows.append(_row(identity, claim, outcome, w_known, c_known, feasible, None))
        elif claim == "nominal":
            n_known = nominal is not None
            in_w = in_c = False
            if n_known and w_known:
                in_w = _member(permitted, nominal, work)
            if in_w and c_known:
                in_c = _member(available, nominal, work)
            outcome = nominal_outcome(n_known, w_known, in_w, c_known, in_c)
            rows.append(_row(identity, claim, outcome, w_known, c_known, None, None))
        else:
            uncovered = _difference(permitted, available, work) if w_known and c_known else None
            outcome = full_window_outcome(w_known, w_empty, c_known, uncovered == [])
            rows.append(_row(identity, claim, outcome, w_known, c_known, None, uncovered))
    blockers = sorted({blocker for blocker in (_blocker(row) for row in rows) if blocker is not None})
    value = {
        "scope": parsed["scope"],
        "anchor": parsed["anchor"],
        "unit": parsed["unit"],
        "nominal": None if nominal is None else protocol_numbers.render(nominal),
        "permitted": _render(permitted),
        "available": _render(available),
        "claims": rows,
        "work": {"reserved": reserved, "used": work.used},
        "guarantee": GUARANTEE,
    }
    return {
        "code": schedule_code([outcome_class(row["outcome"]) for row in rows]),
        "value": value,
        "blockers": blockers,
        "rule": RULE,
    }


def evaluate(kind: str, data: dict) -> dict:
    """The default claims: existence, nominal and full_window, each under its own name."""
    default = [{"id": claim, "claim": claim} for claim in CLAIM_KINDS]
    return check(kind, data, default)
