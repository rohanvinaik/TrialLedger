"""Valid-completion bounds retain partial information without choosing missing registry values."""

from __future__ import annotations

import copy
import itertools
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from TrialLedger.checks import actual_dates_ordered
from TrialLedger.date_possibilities import (
    BASIS,
    DATE_TYPES,
    OUTCOMES,
    completion_outcomes,
    date_order_possibilities,
)


def test_primitive_matches_exhaustive_finite_day_and_type_completion_oracle():
    intervals = [(low, high) for low in range(1, 6) for high in range(low, 6)]
    choices = (("ACTUAL",), ("ESTIMATED",), ("ACTUAL", "ESTIMATED"))
    for (first_low, first_high), (last_low, last_high), first_types, last_types in itertools.product(
        intervals, intervals, choices, choices
    ):
        observed = set()
        for first, last, first_type, last_type in itertools.product(
            range(first_low, first_high + 1), range(last_low, last_high + 1), first_types, last_types
        ):
            if first_type != "ACTUAL" or last_type != "ACTUAL":
                observed.add("not_applicable")
            elif first <= last:
                observed.add("consistent")
            else:
                observed.add("conflict")
        assert completion_outcomes(
            first_low,
            first_high,
            last_low,
            last_high,
            "ACTUAL" in first_types,
            "ACTUAL" in last_types,
            "ESTIMATED" in first_types or "ESTIMATED" in last_types,
        ) == tuple(outcome for outcome in OUTCOMES if outcome in observed)


@pytest.mark.parametrize(
    "args,possible",
    [
        (("2006-03", None, "2008-04", "ACTUAL"), ["consistent", "not_applicable"]),
        (("2006-03", "ACTUAL", "2008-04", "ACTUAL"), ["consistent"]),
        (("2006-03", "ESTIMATED", "2008-04", "ACTUAL"), ["not_applicable"]),
        (("2009", "ACTUAL", "2008-04", "ACTUAL"), ["conflict"]),
        (("2009", None, "2008-04", "ACTUAL"), ["conflict", "not_applicable"]),
        (("2008-04", "ACTUAL", "2008-04", "ACTUAL"), ["consistent", "conflict"]),
        (("2008", "ACTUAL", "2008-04", "ACTUAL"), ["consistent", "conflict"]),
        (("2008-04-01", "ACTUAL", "2008-04-01", "ACTUAL"), ["consistent"]),
        (("2008-04-02", "ACTUAL", "2008-04-01", "ACTUAL"), ["conflict"]),
        ((None, None, None, None), ["consistent", "conflict", "not_applicable"]),
        ((None, "ACTUAL", None, "ACTUAL"), ["consistent", "conflict"]),
        ((None, "ESTIMATED", None, None), ["not_applicable"]),
        (("2006-03", None, "2008-04", "ESTIMATED"), ["not_applicable"]),
        (("0001-01-01", "ACTUAL", None, "ACTUAL"), ["consistent"]),
        ((None, "ACTUAL", "9999-12-31", "ACTUAL"), ["consistent"]),
        (("9999-12-31", "ACTUAL", "0001-01-01", "ACTUAL"), ["conflict"]),
        (("2020-02-29", "ACTUAL", "2020-03", "ACTUAL"), ["consistent"]),
    ],
)
def test_public_valid_completions_and_exclusions_are_canonical(args, possible):
    result = date_order_possibilities(*args)
    assert result == {
        "code": "bounded",
        "possible_outcomes": possible,
        "excluded_outcomes": [outcome for outcome in OUTCOMES if outcome not in possible],
        "blockers": [],
        "basis": BASIS,
    }
    assert "not_checkable" not in result["excluded_outcomes"]


@pytest.mark.parametrize("bad", ["", "BOGUS", "actual", 1, False, [], {}, 1.0])
@pytest.mark.parametrize("position,label", [(1, "earlier_type"), (3, "later_type")])
def test_invalid_observed_types_have_no_exclusion_claim(bad, position, label):
    args = ["2006-03", "ACTUAL", "2008-04", "ACTUAL"]
    args[position] = bad
    result = date_order_possibilities(*args)
    assert result["code"] == "unresolved_input"
    assert result["possible_outcomes"] is None and result["excluded_outcomes"] == []
    assert result["blockers"] == ["invalid_date_type:" + label]


@pytest.mark.parametrize(
    "bad", ["", "bad", "2008-02-30", "0000", "10000", "2008-4", "2008-13", 1, False, [], {}]
)
@pytest.mark.parametrize("position,label", [(0, "earlier"), (2, "later")])
def test_nonnull_malformed_dates_cannot_be_hidden_by_estimated_type(bad, position, label):
    args = ["2006-03", "ESTIMATED", "2008-04", "ESTIMATED"]
    args[position] = bad
    result = date_order_possibilities(*args)
    assert result["code"] == "unresolved_input"
    assert result["possible_outcomes"] is None and result["excluded_outcomes"] == []
    assert result["blockers"] == ["malformed_date:" + label]


def test_all_malformed_observed_fields_have_named_deterministic_blockers():
    bad_type: Any = False
    result = date_order_possibilities("bad", "BOGUS", "2008-02-30", bad_type)
    assert result["blockers"] == [
        "invalid_date_type:earlier_type",
        "invalid_date_type:later_type",
        "malformed_date:earlier",
        "malformed_date:later",
    ]
    assert result["excluded_outcomes"] == []


def test_retained_ipass_completion_set_excludes_conflict_without_choosing_start_type():
    study = json.loads(Path("tests/fixtures/ipass-registry.json").read_text())
    original = copy.deepcopy(study)
    status = study["protocolSection"]["statusModule"]
    first, last = status["startDateStruct"], status["primaryCompletionDateStruct"]
    result = date_order_possibilities(first["date"], first.get("type"), last["date"], last.get("type"))
    assert result["possible_outcomes"] == ["consistent", "not_applicable"]
    assert result["excluded_outcomes"] == ["conflict"]
    assert (
        actual_dates_ordered(first["date"], first.get("type"), last["date"], last.get("type"))
        == "not_checkable"
    )
    assert study == original and "type" not in first
    assert "API 2.0.5" in result["basis"] and "do not identify" in result["basis"]


def test_known_actual_exact_dates_match_existing_check_outcomes():
    for first, last in itertools.product(("2001-01-01", "2001-01-02", "2001-01-03"), repeat=2):
        result = date_order_possibilities(first, "ACTUAL", last, "ACTUAL")
        assert result["possible_outcomes"] == [actual_dates_ordered(first, "ACTUAL", last, "ACTUAL")]


def test_missing_dates_are_valid_calendar_completion_ranges():
    assert date.min.toordinal() == 1
    assert date.max.toordinal() == 3652059
    assert date_order_possibilities(None, "ACTUAL", None, "ACTUAL")["possible_outcomes"] == [
        "consistent",
        "conflict",
    ]


def test_type_completion_domain_matches_the_full_vendored_date_type_codebook_entry():
    enums = json.loads(Path("TrialLedger/registry/ctg-enums.json").read_text())
    entries = [entry for entry in enums if entry["type"] == "DateType"]
    assert len(entries) == 1
    assert tuple(value["value"] for value in entries[0]["values"]) == DATE_TYPES
    assert "StartDateType" in entries[0]["pieces"]
    assert "PrimaryCompletionDateType" in entries[0]["pieces"]
