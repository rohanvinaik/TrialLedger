"""Exact finite-population bounds from explicitly aligned numerical evidence.

This module knows counts, ordered summaries and subset equations. It does not read trial text, identify
clinical measurements, establish source truth or assign epistemic standing. Its caller owns the source,
binding and bridge premises. Unknown bounds remain intervals, never observed zeros. Each operator returns
typed witness expressions for a caller to bind to participant propositions.
"""

from __future__ import annotations

import math
from typing import Any

LIMIT = 1000
ALIGNMENTS = ("confirmed", "unresolved", "conflicting")
COUNT_SHAPE = {
    "required": ("ref", "universe", "lower", "upper"),
    "fields": {
        "ref": "distinct nonempty bound predicate reference",
        "universe": "same study/version/population/assessment universe as the enclosing input",
        "lower": "nonnegative integer or null (unknown lower bound)",
        "upper": "nonnegative integer or null (unknown upper bound)",
    },
}
CLAIM_SHAPE = {
    "required": ("count", "lower", "upper"),
    "fields": {
        "count": "one output count id",
        "lower": "nonnegative integer or null (no added lower restriction)",
        "upper": "nonnegative integer or null (no added upper restriction)",
    },
}
INPUTS = {
    "overlap": {
        "required": ("universe", "alignment", "total", "marginals"),
        "fields": {
            "universe": "nonempty study/version/population/assessment identity, not merely a denominator",
            "alignment": "confirmed, unresolved or conflicting; matching counts never establish alignment",
            "total": "nonnegative integer universe size",
            "marginals": "at least two distinct scoped_count objects; no statistical independence assumed",
        },
        "scoped_count": COUNT_SHAPE,
        "claim": CLAIM_SHAPE,
        "count_ids": "intersection",
    },
    "partition": {
        "required": ("universe", "alignment", "total", "disjoint", "exhaustive", "parts"),
        "fields": {
            "universe": "nonempty study/version/population/assessment identity",
            "alignment": "confirmed, unresolved or conflicting",
            "total": "nonnegative integer universe size",
            "disjoint": "boolean: explicit mutual exclusivity premise",
            "exhaustive": "boolean: explicit coverage premise; false retains a separate remainder",
            "parts": "nonempty array of scoped_count objects, refs distinct and not remainder",
        },
        "scoped_count": COUNT_SHAPE,
        "claim": CLAIM_SHAPE,
        "count_ids": "each part ref plus remainder (none of the represented parts)",
    },
    "summary": {
        "required": (
            "universe",
            "alignment",
            "total",
            "ref",
            "unit",
            "statistic",
            "median_definition",
            "number",
            "comparison",
            "exact",
        ),
        "fields": {
            "universe": "nonempty identity of the participants actually assessed for this summary",
            "alignment": "confirmed, unresolved or conflicting",
            "total": "nonnegative integer assessed population size; zero gives no summary witness",
            "ref": "nonempty measurement binding reference",
            "unit": "measurement unit as written; never converted",
            "statistic": "minimum, maximum or median; other statistics are explicitly unresolved",
            "median_definition": (
                "midpoint, unresolved or not_applicable; median requires explicit midpoint convention; "
                "minimum/maximum requires not_applicable"
            ),
            "number": "finite number as encoded; no string/boolean coercion",
            "comparison": "eq, le or ge for the requested count relative to number",
            "exact": "boolean: false refuses witness derivation from rounded/uncertain summary values",
        },
        "claim": CLAIM_SHAPE,
        "count_ids": "summary",
    },
    "population": {
        "required": ("universe", "alignment", "total", "parent_ref", "subset", "subset_relation"),
        "fields": {
            "universe": "nonempty study/version/population/assessment identity of the parent population",
            "alignment": "confirmed, unresolved or conflicting",
            "total": "nonnegative integer parent size",
            "parent_ref": "nonempty parent-membership binding, distinct from subset ref and outside",
            "subset": "scoped_count object, ref distinct from parent_ref and outside",
            "subset_relation": (
                "confirmed, unresolved or conflicting; denominator/title agreement is insufficient"
            ),
        },
        "scoped_count": COUNT_SHAPE,
        "claim": CLAIM_SHAPE,
        "count_ids": "parent_ref, subset.ref and outside (parent AND NOT subset)",
    },
}
EXAMPLES = {
    "overlap": {
        "universe": "invented:baseline",
        "alignment": "confirmed",
        "total": 100,
        "marginals": [
            {"ref": "a", "universe": "invented:baseline", "lower": 70, "upper": 70},
            {"ref": "b", "universe": "invented:baseline", "lower": 60, "upper": 60},
        ],
    },
    "partition": {
        "universe": "invented:baseline",
        "alignment": "confirmed",
        "total": 100,
        "disjoint": True,
        "exhaustive": True,
        "parts": [
            {"ref": "a", "universe": "invented:baseline", "lower": 70, "upper": 70},
            {"ref": "b", "universe": "invented:baseline", "lower": None, "upper": None},
        ],
    },
    "summary": {
        "universe": "invented:assessed",
        "alignment": "confirmed",
        "total": 101,
        "ref": "age",
        "unit": "Years",
        "statistic": "median",
        "median_definition": "midpoint",
        "number": 60,
        "comparison": "ge",
        "exact": True,
    },
    "population": {
        "universe": "invented:randomized",
        "alignment": "confirmed",
        "total": 100,
        "parent_ref": "randomized",
        "subset_relation": "confirmed",
        "subset": {"ref": "analysed", "universe": "invented:randomized", "lower": 70, "upper": 70},
    },
}


def interval_state(lower: int, upper: int) -> str:
    """Name interval consistency; an empty interval is never a negative observation (pure — pinned)."""
    return "conflict" if lower > upper else "bounded"


def overlap_bounds(total: int, lowers: list[int], uppers: list[int]) -> tuple[int, int]:
    """Fréchet bounds on an intersection of at least two subsets of one universe (pure — pinned).

    Preconditions: equal nonempty lengths >=2 and each marginal interval within [0,total]. These bounds
    do not assume independence or fabricate a joint table.
    """
    return max(0, sum(lowers) - (len(lowers) - 1) * total), min(uppers)


def partition_bounds(total: int, lowers: list[int], uppers: list[int]) -> tuple[list[int], list[int]]:
    """Project integer intervals under the exact equation sum(parts)=total (pure — pinned).

    Preconditions: equal nonempty lengths. An empty projection carries lower > upper. For independent
    integer intervals and this one total equation, each projected bound is attainable whenever feasible.
    A nonexhaustive disjoint partition is represented with an explicit remainder interval [0,total].
    """
    low_sum, high_sum = sum(lowers), sum(uppers)
    return (
        [max(low, total - high_sum + high) for low, high in zip(lowers, uppers, strict=True)],
        [min(high, total - low_sum + low) for low, high in zip(lowers, uppers, strict=True)],
    )


def summary_bounds(statistic: str, comparison: str, total: int) -> tuple[int, int]:
    """Count bounds for an exact minimum, maximum or median of assessed participants (pure — pinned).

    Median means the central observation for odd N and the midpoint of the two central observations for
    even N. Its inclusive sides each contain at least ceil(N/2) observations. An even median can lie
    strictly between its two central observations. The function
    receives only supported statistics and comparisons, after validation by the operator boundary.
    """
    if (statistic == "minimum" and comparison == "ge") or (statistic == "maximum" and comparison == "le"):
        return total, total
    if statistic == "median":
        return (total % 2 if comparison == "eq" else (total + 1) // 2), total
    return 1, total


def summary_count_state(statistic: str, comparison: str, total: int, lower: int, upper: int) -> str:
    """Reject empty intervals or the singleton hole in even-median equality counts (pure — pinned).

    If an even midpoint median is observed at all, both central observations equal it. Hence an exact
    equality count of one is impossible, although its conservative count interval includes one.
    Preconditions: a supported exact summary of a positive population and an already projected interval.
    """
    if interval_state(lower, upper) == "conflict":
        return "conflict"
    if statistic == "median" and comparison == "eq" and total % 2 == 0 and lower == upper == 1:
        return "conflict"
    return "bounded"


def scope_state(alignment: str, universe: str, scopes: list[str]) -> str:
    """A binding is usable only when explicitly settled to one exact universe (pure — pinned)."""
    if alignment != "confirmed":
        return "alignment_unresolved"
    if any(scope != universe for scope in scopes):
        return "universe_mismatch"
    return "aligned"


def _object(value: Any, fields: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"not_an_object:{where}")
    if set(value) != fields:
        raise ValueError(f"fields_do_not_fit:{where}")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"not_text:{where}")
    return value


def _count(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"not_a_count:{where}")
    return value


def _list(value: Any, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"not_a_list:{where}")
    if len(value) > LIMIT:
        raise ValueError(f"resource_bound:{where}")
    return value


def _alignment(value: Any, where: str) -> str:
    if not isinstance(value, str) or value not in ALIGNMENTS:
        raise ValueError(f"invalid_alignment:{where}")
    return value


def _interval(lower: Any, upper: Any, total: int, where: str) -> tuple[int, int]:
    low = 0 if lower is None else _count(lower, where + ":lower")
    high = total if upper is None else _count(upper, where + ":upper")
    return low, high


def _rows(value: Any, total: int, where: str) -> tuple[list[str], list[str], list[int], list[int]]:
    refs, scopes, lows, highs = [], [], [], []
    for raw in _list(value, where):
        row = _object(raw, set(COUNT_SHAPE["required"]), where)
        refs.append(_text(row["ref"], where + ":ref"))
        scopes.append(_text(row["universe"], where + ":universe"))
        low, high = _interval(row["lower"], row["upper"], total, where)
        lows.append(low)
        highs.append(high)
    if len(set(refs)) != len(refs):
        raise ValueError(f"duplicate_ref:{where}")
    return refs, scopes, lows, highs


def _claims(
    claims: Any, ids: list[str], lows: list[int], highs: list[int], total: int
) -> tuple[list[int], list[int]]:
    lows, highs = list(lows), list(highs)
    for raw in _list(claims, "claims"):
        claim = _object(raw, set(CLAIM_SHAPE["required"]), "claim")
        identity = _text(claim["count"], "claim:count")
        if identity not in ids:
            raise ValueError("unknown_count:claim")
        low, high = _interval(claim["lower"], claim["upper"], total, "claim")
        index = ids.index(identity)
        lows[index], highs[index] = max(lows[index], low), min(highs[index], high)
    return lows, highs


def _result(kind: str, code: str, value: dict, blockers: list[str] | None = None) -> dict:
    return {"code": code, "value": value, "blockers": blockers or [], "rule": f"numeric.{kind}:1"}


def _finish(
    kind: str,
    data: dict,
    ids: list[str],
    lows: list[int],
    highs: list[int],
    expressions: list[dict],
    scopes: list[str],
    claims: list[dict],
    *,
    sum_total: bool = False,
    blocker: str = "",
) -> dict:
    value = {"universe": data["universe"], "total": data["total"], "counts": [], "witnesses": []}
    lows, highs = _claims(claims, ids, lows, highs, data["total"])
    scope = scope_state(data["alignment"], data["universe"], scopes)
    if scope != "aligned" or blocker:
        return _result(
            kind, "unresolved", value, [b for b in (scope if scope != "aligned" else "", blocker) if b]
        )
    if any(interval_state(low, high) == "conflict" for low, high in zip(lows, highs, strict=True)):
        return _result(kind, "conflict", value, ["inconsistent_count_bounds"])
    if sum_total:
        lows, highs = partition_bounds(data["total"], lows, highs)
    if any(interval_state(low, high) == "conflict" for low, high in zip(lows, highs, strict=True)):
        return _result(kind, "conflict", value, ["inconsistent_population_total"])
    value["counts"] = [
        {"id": ref, "lower": low, "upper": high} for ref, low, high in zip(ids, lows, highs, strict=True)
    ]
    value["witnesses"] = [
        {"id": ref, "lower": low, "upper": high, "expression": expression}
        for ref, low, high, expression in zip(ids, lows, highs, expressions, strict=True)
    ]
    if kind == "summary":
        value["unit"] = data["unit"]
    return _result(kind, "bounded", value)


def _overlap(data: dict, claims: list[dict]) -> dict:
    refs, scopes, lows, highs = _rows(data["marginals"], data["total"], "marginals")
    if len(refs) < 2:
        raise ValueError("overlap_needs_two_marginals")
    # A marginal must itself be feasible in the universe before applying the Fréchet projection.
    marginal_conflict = any(low > min(high, data["total"]) for low, high in zip(lows, highs, strict=True))
    low, high = overlap_bounds(data["total"], lows, [min(high, data["total"]) for high in highs])
    if marginal_conflict:
        low, high = 1, 0
    return _finish(
        "overlap", data, ["intersection"], [low], [high], [{"kind": "all_of", "refs": refs}], scopes, claims
    )


def _partition(data: dict, claims: list[dict]) -> dict:
    if type(data["disjoint"]) is not bool or type(data["exhaustive"]) is not bool:
        raise ValueError("partition_flags_not_boolean")
    refs, scopes, lows, highs = _rows(data["parts"], data["total"], "parts")
    if not refs or "remainder" in refs:
        raise ValueError("partition_parts_empty_or_reserved")
    ids = [*refs, "remainder"]
    expressions = [{"kind": "all_of", "refs": [ref]} for ref in refs]
    expressions.append({"kind": "none_of", "refs": refs})
    return _finish(
        "partition",
        data,
        ids,
        [*lows, 0],
        [*highs, 0 if data["exhaustive"] else data["total"]],
        expressions,
        scopes,
        claims,
        sum_total=True,
        blocker="disjointness_unresolved" if not data["disjoint"] else "",
    )


def _summary(data: dict, claims: list[dict]) -> dict:
    ref = _text(data["ref"], "summary:ref")
    _text(data["unit"], "summary:unit")
    statistic = _text(data["statistic"], "summary:statistic")
    definition = data["median_definition"]
    if definition not in ("midpoint", "unresolved", "not_applicable"):
        raise ValueError("summary_definition_unsupported")
    if statistic in ("minimum", "maximum") and definition != "not_applicable":
        raise ValueError("summary_definition_incompatible")
    number = data["number"]
    if type(number) not in (int, float) or (isinstance(number, float) and not math.isfinite(number)):
        raise ValueError("summary_number_not_finite")
    if data["comparison"] not in ("eq", "le", "ge"):
        raise ValueError("summary_comparison_unsupported")
    if type(data["exact"]) is not bool:
        raise ValueError("summary_exactness_not_boolean")
    blocker = (
        "unsupported_summary_statistic"
        if statistic not in ("minimum", "maximum", "median")
        else "median_definition_unresolved"
        if statistic == "median" and definition != "midpoint"
        else "summary_not_exact"
        if not data["exact"]
        else "empty_measurement_population"
        if not data["total"]
        else ""
    )
    low, high = (
        summary_bounds(statistic, data["comparison"], data["total"]) if not blocker else (0, data["total"])
    )
    lows, highs = _claims(claims, ["summary"], [low], [high], data["total"])
    if (
        not blocker
        and summary_count_state(statistic, data["comparison"], data["total"], lows[0], highs[0]) == "conflict"
    ):
        lows, highs = [1], [0]
    return _finish(
        "summary",
        data,
        ["summary"],
        lows,
        highs,
        [{"kind": "comparison", "ref": ref, "comparison": data["comparison"], "number": number}],
        [data["universe"]],
        [],
        blocker=blocker,
    )


def _population(data: dict, claims: list[dict]) -> dict:
    parent = _text(data["parent_ref"], "parent_ref")
    relation = _alignment(data["subset_relation"], "subset_relation")
    refs, scopes, lows, highs = _rows([data["subset"]], data["total"], "subset")
    if parent == refs[0] or "outside" in (parent, refs[0]):
        raise ValueError("population_refs_duplicate_or_reserved")
    # Parent is fixed at total; subset and outside must sum to it. Keep a parent claim as its own check.
    ids = [parent, refs[0], "outside"]
    expressions = [
        {"kind": "all_of", "refs": [parent]},
        {"kind": "all_of", "refs": refs},
        {"kind": "difference", "refs": [parent, refs[0]]},
    ]
    all_lows, all_highs = _claims(
        claims, ids, [data["total"], *lows, 0], [data["total"], *highs, data["total"]], data["total"]
    )
    if interval_state(all_lows[0], all_highs[0]) == "conflict":
        # Preserve the normal binding guards: a disputed subset relation cannot establish a conflict.
        all_lows[1], all_highs[1] = 1, 0
    result = _finish(
        "population",
        data,
        ids[1:],
        all_lows[1:],
        all_highs[1:],
        expressions[1:],
        scopes,
        [],
        sum_total=True,
        blocker="subset_relation_unresolved" if relation != "confirmed" else "",
    )
    if result["code"] == "bounded":
        result["value"]["counts"].insert(0, {"id": parent, "lower": data["total"], "upper": data["total"]})
        result["value"]["witnesses"].insert(
            0, {"id": parent, "lower": data["total"], "upper": data["total"], "expression": expressions[0]}
        )
    return result


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Evaluate all candidate count restrictions together under the source equations.

    Claims are {count: output id, lower: integer/null, upper: integer/null}. A conflict is an empty feasible
    set, not a clinical negative. This function validates full inputs and never mutates source dictionaries.
    """
    if not isinstance(kind, str) or kind not in INPUTS:
        raise ValueError("unsupported_numeric_kind")
    data = _object(data, set(INPUTS[kind]["required"]), kind)
    _text(data["universe"], "universe")
    _alignment(data["alignment"], "alignment")
    _count(data["total"], "total")
    return {"overlap": _overlap, "partition": _partition, "summary": _summary, "population": _population}[
        kind
    ](data, claims)


def evaluate(kind: str, data: dict) -> dict:
    """Compute source-bound numerical consequences without adding any candidate restrictions."""
    return check(kind, data, [])
