"""Intent and finite-population oracles for numerical evidence; no clinical interpretation is assumed."""

from __future__ import annotations

import copy
import itertools
import statistics

import pytest

from TrialLedger.layer2 import numeric_evidence as n


def count(result, identity):
    return next(row for row in result["value"]["counts"] if row["id"] == identity)


def test_all_numerical_examples_are_runnable_and_never_mutated():
    for kind, original in n.EXAMPLES.items():
        data = copy.deepcopy(original)
        assert n.evaluate(kind, data)["code"] == "bounded"
        assert data == original


def test_ipass_marginals_bound_a_compound_phenotype_without_independence():
    data = copy.deepcopy(n.EXAMPLES["overlap"])
    data["total"] = 1217
    data["marginals"][0].update(ref="WHO_PS_2", lower=126, upper=126)
    data["marginals"][1].update(ref="never_smoker", lower=1140, upper=1140)
    result = n.evaluate("overlap", data)
    assert count(result, "intersection") == {"id": "intersection", "lower": 49, "upper": 126}
    assert result["value"]["witnesses"] == [
        {
            "id": "intersection",
            "lower": 49,
            "upper": 126,
            "expression": {"kind": "all_of", "refs": ["WHO_PS_2", "never_smoker"]},
        }
    ]
    assert (
        n.check("overlap", data, [{"count": "intersection", "lower": 0, "upper": 48}])["code"] == "conflict"
    )
    assert (
        n.check("overlap", data, [{"count": "intersection", "lower": 49, "upper": 49}])["code"] == "bounded"
    )


def test_frechet_bounds_match_actual_small_set_intersections():
    for total in range(5):
        sets = [frozenset(i for i in range(total) if mask & (1 << i)) for mask in range(1 << total)]
        for dimensions in (2, 3):
            actual = {}
            for chosen in itertools.product(sets, repeat=dimensions):
                sizes = tuple(map(len, chosen))
                actual.setdefault(sizes, set()).add(len(frozenset.intersection(*chosen)))
            for sizes, possible in actual.items():
                assert n.overlap_bounds(total, list(sizes), list(sizes)) == (min(possible), max(possible))


def test_incomplete_marginals_preserve_intervals_and_zero_is_only_a_bound():
    data = copy.deepcopy(n.EXAMPLES["overlap"])
    data["marginals"][0].update(lower=None, upper=None)
    result = n.evaluate("overlap", data)
    assert count(result, "intersection") == {"id": "intersection", "lower": 0, "upper": 60}
    assert data["marginals"][0]["lower"] is None
    data["marginals"][0].update(lower=110, upper=110)
    assert n.evaluate("overlap", data)["code"] == "conflict"


@pytest.mark.parametrize("lower,upper,expected", [(1, 0, "conflict"), (0, 0, "bounded"), (2, 3, "bounded")])
def test_interval_consistency_is_not_a_clinical_negative(lower, upper, expected):
    assert n.interval_state(lower, upper) == expected


@pytest.mark.parametrize(
    "alignment,universe,scopes,expected",
    [
        ("confirmed", "U", ["U", "U"], "aligned"),
        ("confirmed", "U", ["U", "V"], "universe_mismatch"),
        ("unresolved", "U", ["U"], "alignment_unresolved"),
        ("conflicting", "U", ["U"], "alignment_unresolved"),
    ],
)
def test_count_agreement_never_establishes_population_alignment(alignment, universe, scopes, expected):
    assert n.scope_state(alignment, universe, scopes) == expected


@pytest.mark.parametrize("kind", list(n.EXAMPLES))
def test_unsettled_alignment_returns_no_usable_counts_or_witnesses(kind):
    data = copy.deepcopy(n.EXAMPLES[kind])
    data["alignment"] = "unresolved"
    result = n.evaluate(kind, data)
    assert result["code"] == "unresolved" and result["blockers"] == ["alignment_unresolved"]
    assert result["value"]["counts"] == result["value"]["witnesses"] == []


def test_equal_denominators_on_different_universes_cannot_be_combined():
    data = copy.deepcopy(n.EXAMPLES["overlap"])
    data["marginals"][1]["universe"] = "a-different-cohort-with-the-same-size"
    assert n.evaluate("overlap", data)["blockers"] == ["universe_mismatch"]


def test_exhaustive_partitions_deduce_a_missing_count_from_the_total():
    result = n.evaluate("partition", n.EXAMPLES["partition"])
    assert count(result, "b") == {"id": "b", "lower": 30, "upper": 30}
    assert count(result, "remainder") == {"id": "remainder", "lower": 0, "upper": 0}
    assert result["value"]["witnesses"][-1]["expression"] == {"kind": "none_of", "refs": ["a", "b"]}


def test_nonexhaustive_partition_keeps_unrepresented_participants_separate():
    data = copy.deepcopy(n.EXAMPLES["partition"])
    data["exhaustive"] = False
    result = n.evaluate("partition", data)
    assert count(result, "b") == {"id": "b", "lower": 0, "upper": 30}
    assert count(result, "remainder") == {"id": "remainder", "lower": 0, "upper": 30}
    data["parts"] = data["parts"][:1]
    assert count(n.evaluate("partition", data), "remainder") == {"id": "remainder", "lower": 30, "upper": 30}


def test_partition_requires_explicit_disjointness_and_detects_impossible_totals():
    data = copy.deepcopy(n.EXAMPLES["partition"])
    data["disjoint"] = False
    assert n.evaluate("partition", data)["blockers"] == ["disjointness_unresolved"]
    data["disjoint"] = True
    data["parts"][1].update(lower=40, upper=40)
    assert n.evaluate("partition", data)["code"] == "conflict"


def test_partition_projection_matches_enumerated_integer_populations():
    for total in range(4):
        intervals = [(low, high) for low in range(total + 1) for high in range(low, total + 1)]
        for chosen in itertools.product(intervals, repeat=3):
            feasible = [
                values
                for values in itertools.product(range(total + 1), repeat=3)
                if sum(values) == total
                and all(low <= value <= high for value, (low, high) in zip(values, chosen, strict=True))
            ]
            lows, highs = n.partition_bounds(total, [p[0] for p in chosen], [p[1] for p in chosen])
            if feasible:
                assert lows == [min(values[i] for values in feasible) for i in range(3)]
                assert highs == [max(values[i] for values in feasible) for i in range(3)]
            else:
                assert any(low > high for low, high in zip(lows, highs, strict=True))


def test_count_claims_must_be_jointly_feasible_not_merely_pairwise_compatible():
    data = copy.deepcopy(n.EXAMPLES["partition"])
    for part in data["parts"]:
        part.update(lower=None, upper=None)
    a = {"count": "a", "lower": 80, "upper": 80}
    b = {"count": "b", "lower": 80, "upper": 80}
    assert n.check("partition", data, [a])["code"] == "bounded"
    assert n.check("partition", data, [b])["code"] == "bounded"
    assert n.check("partition", data, [a, b])["code"] == "conflict"
    contradictory = [{"count": "a", "lower": 80, "upper": None}, {"count": "a", "lower": None, "upper": 79}]
    assert n.check("partition", data, contradictory)["code"] == "conflict"


@pytest.mark.parametrize(
    "statistic,comparison,total,expected",
    [
        ("minimum", "ge", 101, (101, 101)),
        ("minimum", "le", 101, (1, 101)),
        ("minimum", "eq", 101, (1, 101)),
        ("maximum", "le", 101, (101, 101)),
        ("maximum", "ge", 101, (1, 101)),
        ("maximum", "eq", 101, (1, 101)),
        ("median", "ge", 101, (51, 101)),
        ("median", "le", 101, (51, 101)),
        ("median", "eq", 101, (1, 101)),
        ("median", "ge", 100, (50, 100)),
        ("median", "le", 100, (50, 100)),
        ("median", "eq", 100, (0, 100)),
    ],
)
def test_exact_summaries_supply_only_warranted_count_bounds(statistic, comparison, total, expected):
    assert n.summary_bounds(statistic, comparison, total) == expected


def test_summary_bounds_hold_for_all_small_observation_vectors():
    for total in range(1, 6):
        for values in itertools.product((-1, 0, 1), repeat=total):
            summaries = {"minimum": min(values), "maximum": max(values), "median": statistics.median(values)}
            for statistic, number in summaries.items():
                actual = {
                    "eq": sum(x == number for x in values),
                    "le": sum(x <= number for x in values),
                    "ge": sum(x >= number for x in values),
                }
                for comparison, count_ in actual.items():
                    low, high = n.summary_bounds(statistic, comparison, total)
                    assert low <= count_ <= high


def test_summary_preserves_measurement_identity_and_never_invents_a_positive_even_median_witness():
    data = copy.deepcopy(n.EXAMPLES["summary"])
    data.update(total=2, number=1, comparison="eq")  # observations 0 and 2 have median 1, with no value 1.
    result = n.evaluate("summary", data)
    assert count(result, "summary") == {"id": "summary", "lower": 0, "upper": 2}
    assert result["value"]["unit"] == "Years"
    assert result["value"]["witnesses"][0]["expression"] == {
        "kind": "comparison",
        "ref": "age",
        "comparison": "eq",
        "number": 1,
    }
    assert n.check("summary", data, [{"count": "summary", "lower": 1, "upper": 1}])["code"] == "conflict"
    assert n.check("summary", data, [{"count": "summary", "lower": 0, "upper": 0}])["code"] == "bounded"
    assert n.check("summary", data, [{"count": "summary", "lower": 2, "upper": 2}])["code"] == "bounded"


@pytest.mark.parametrize(
    "statistic,comparison,total,lower,upper,expected",
    [
        ("median", "eq", 2, 1, 1, "conflict"),
        ("median", "eq", 2, 0, 1, "bounded"),
        ("median", "eq", 2, 1, 2, "bounded"),
        ("median", "eq", 3, 1, 1, "bounded"),
        ("median", "le", 2, 1, 1, "bounded"),
        ("minimum", "eq", 2, 1, 1, "bounded"),
        ("maximum", "eq", 2, 1, 1, "bounded"),
        ("minimum", "eq", 2, 2, 1, "conflict"),
    ],
)
def test_summary_count_consistency_retains_the_even_median_hole(
    statistic, comparison, total, lower, upper, expected
):
    assert n.summary_count_state(statistic, comparison, total, lower, upper) == expected


def test_exact_summary_claims_match_attainable_small_populations():
    for total in range(1, 7):
        possible = {
            (statistic, comparison): set()
            for statistic in ("minimum", "maximum", "median")
            for comparison in ("eq", "le", "ge")
        }
        for values in itertools.product((-1, 0, 1), repeat=total):
            summaries = {"minimum": min(values), "maximum": max(values), "median": statistics.median(values)}
            for statistic, number in summaries.items():
                possible[statistic, "eq"].add(sum(x == number for x in values))
                possible[statistic, "le"].add(sum(x <= number for x in values))
                possible[statistic, "ge"].add(sum(x >= number for x in values))
        for (statistic, comparison), attainable in possible.items():
            data = n.EXAMPLES["summary"] | {
                "total": total,
                "statistic": statistic,
                "comparison": comparison,
                "median_definition": "midpoint" if statistic == "median" else "not_applicable",
            }
            for candidate in range(total + 1):
                result = n.check(
                    "summary", data, [{"count": "summary", "lower": candidate, "upper": candidate}]
                )
                assert result["code"] == ("bounded" if candidate in attainable else "conflict")


@pytest.mark.parametrize(
    "changes,blocker",
    [
        ({"exact": False}, "summary_not_exact"),
        ({"statistic": "confidence_interval"}, "unsupported_summary_statistic"),
        ({"statistic": "mean"}, "unsupported_summary_statistic"),
        ({"total": 0}, "empty_measurement_population"),
        ({"median_definition": "unresolved"}, "median_definition_unresolved"),
        ({"median_definition": "not_applicable"}, "median_definition_unresolved"),
    ],
)
def test_rounded_summaries_and_confidence_intervals_are_not_extrema(changes, blocker):
    data = copy.deepcopy(n.EXAMPLES["summary"])
    data.update(changes)
    result = n.evaluate("summary", data)
    assert result["code"] == "unresolved" and result["blockers"] == [blocker]
    assert result["value"]["witnesses"] == []


def test_population_difference_is_coverage_not_imputed_missingness_or_eligibility():
    result = n.evaluate("population", n.EXAMPLES["population"])
    assert count(result, "outside") == {"id": "outside", "lower": 30, "upper": 30}
    assert result["value"]["witnesses"][-1]["expression"] == {
        "kind": "difference",
        "refs": ["randomized", "analysed"],
    }
    assert set(result["value"]) == {"universe", "total", "counts", "witnesses"}


def test_population_subset_and_complement_claims_obey_one_shared_total():
    data = copy.deepcopy(n.EXAMPLES["population"])
    data["subset"].update(lower=None, upper=None)
    claims = [{"count": "analysed", "lower": 80, "upper": 80}, {"count": "outside", "lower": 30, "upper": 30}]
    assert n.check("population", data, claims[:1])["code"] == "bounded"
    assert n.check("population", data, claims[1:])["code"] == "bounded"
    assert n.check("population", data, claims)["code"] == "conflict"
    assert (
        n.check("population", data, [{"count": "randomized", "lower": None, "upper": 99}])["code"]
        == "conflict"
    )


def test_unknown_subset_membership_and_different_scopes_do_not_become_negatives():
    data = copy.deepcopy(n.EXAMPLES["population"])
    data["subset_relation"] = "unresolved"
    assert n.evaluate("population", data)["blockers"] == ["subset_relation_unresolved"]
    data["subset_relation"] = "confirmed"
    data["subset"]["universe"] = "different:cohort"
    assert n.evaluate("population", data)["blockers"] == ["universe_mismatch"]
    data["subset"]["universe"] = data["universe"]
    data["subset"].update(lower=101, upper=101)
    assert n.evaluate("population", data)["code"] == "conflict"


@pytest.mark.parametrize("kind", list(n.EXAMPLES))
@pytest.mark.parametrize("bad", [None, [], "source text", 1, True])
def test_nonobjects_are_named_refusals(kind, bad):
    with pytest.raises(ValueError, match="not_an_object"):
        n.evaluate(kind, bad)


@pytest.mark.parametrize("kind", list(n.EXAMPLES))
def test_closed_shapes_and_missing_required_fields_are_enforced(kind):
    data = copy.deepcopy(n.EXAMPLES[kind])
    with pytest.raises(ValueError, match="fields_do_not_fit"):
        n.evaluate(kind, data | {"free_text": "not interpreted"})
    for key in n.INPUTS[kind]["required"]:
        with pytest.raises(ValueError, match="fields_do_not_fit"):
            n.evaluate(kind, {name: value for name, value in data.items() if name != key})


@pytest.mark.parametrize("bad", [-1, True, 2.0, "100", None])
def test_invalid_count_types_are_never_coerced(bad):
    data = copy.deepcopy(n.EXAMPLES["overlap"])
    data["total"] = bad
    with pytest.raises(ValueError, match="not_a_count"):
        n.evaluate("overlap", data)


@pytest.mark.parametrize("bad", [True, "60", float("inf"), float("nan"), None])
def test_malformed_summary_numbers_are_refused(bad):
    data = copy.deepcopy(n.EXAMPLES["summary"])
    data["number"] = bad
    with pytest.raises(ValueError, match="summary_number_not_finite"):
        n.evaluate("summary", data)


def test_nested_malformed_fields_duplicate_refs_and_work_limits_are_refused():
    data = copy.deepcopy(n.EXAMPLES["overlap"])
    data["marginals"].append(copy.deepcopy(data["marginals"][0]))
    with pytest.raises(ValueError, match="duplicate_ref"):
        n.evaluate("overlap", data)
    data["marginals"] = data["marginals"][:1]
    with pytest.raises(ValueError, match="overlap_needs_two"):
        n.evaluate("overlap", data)
    data["marginals"] = [{}] * 1001
    with pytest.raises(ValueError, match="resource_bound"):
        n.evaluate("overlap", data)
    with pytest.raises(ValueError, match="unknown_count"):
        n.check("summary", n.EXAMPLES["summary"], [{"count": "unbound", "lower": 0, "upper": 1}])
    with pytest.raises(ValueError, match="not_a_list"):
        n.check("summary", n.EXAMPLES["summary"], {})
    with pytest.raises(ValueError, match="unsupported_numeric_kind"):
        n.evaluate("unknown", {})


@pytest.mark.parametrize("bad", [True, 2.0, -1, "1"])
def test_nested_counts_and_candidate_bounds_refuse_coercion(bad):
    data = copy.deepcopy(n.EXAMPLES["partition"])
    data["parts"][0]["lower"] = bad
    with pytest.raises(ValueError, match="not_a_count"):
        n.evaluate("partition", data)
    with pytest.raises(ValueError, match="not_a_count"):
        n.check("summary", n.EXAMPLES["summary"], [{"count": "summary", "lower": bad, "upper": None}])


@pytest.mark.parametrize("field", ["disjoint", "exhaustive"])
@pytest.mark.parametrize("bad", [None, 0, 1, "true"])
def test_partition_premise_flags_are_never_truthiness_coerced(field, bad):
    data = n.EXAMPLES["partition"] | {field: bad}
    with pytest.raises(ValueError, match="partition_flags_not_boolean"):
        n.evaluate("partition", data)


def test_summary_large_exact_integer_retains_the_encoded_number():
    number = 10**100
    data = n.EXAMPLES["summary"] | {"number": number}
    assert n.evaluate("summary", data)["value"]["witnesses"][0]["expression"]["number"] == number
