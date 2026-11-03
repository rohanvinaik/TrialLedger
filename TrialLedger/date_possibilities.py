"""Possible date-check outcomes over valid completions, without identifying missing source values.

The existing four-category check remains separate. This calculation retains what can
be excluded under the vendored registry's date grammar and finite date-type domain.
"""

from __future__ import annotations

from datetime import date

OUTCOMES = ("consistent", "conflict", "not_applicable")
DATE_TYPES = ("ACTUAL", "ESTIMATED")
BASIS = (
    "Valid completions under vendored ClinicalTrials.gov API 2.0.5: "
    "TrialLedger/registry/ctg-enums.json DateType and spec/ctg-oas-v2.yaml "
    "DateType/PartialDate/PartialDateStruct. Missing types range over ACTUAL/ESTIMATED; "
    "missing dates range over valid calendar dates in years 0001-9999. "
    "Possible outcomes do not identify a missing source value or change the check headline."
)


def completion_outcomes(
    earlier_low: int,
    earlier_high: int,
    later_low: int,
    later_high: int,
    first_actual: bool,
    last_actual: bool,
    estimated: bool,
) -> tuple[str, ...]:
    """Compute outcomes from ordered date intervals and declared type choices (pure — pinned).

    pre: earlier_low <= earlier_high
    pre: later_low <= later_high
    post: all(value in ('consistent', 'conflict', 'not_applicable') for value in __return__)
    post: ('consistent' in __return__) == (first_actual and last_actual and earlier_low <= later_high)
    post: ('conflict' in __return__) == (first_actual and last_actual and earlier_high > later_low)
    post: ('not_applicable' in __return__) == estimated
    """
    possible = []
    if first_actual and last_actual:
        if earlier_low <= later_high:
            possible.append("consistent")
        if earlier_high > later_low:
            possible.append("conflict")
    if estimated:
        possible.append("not_applicable")
    return tuple(possible)


def date_order_possibilities(
    earlier: str | None,
    earlier_type: str | None,
    later: str | None,
    later_type: str | None,
) -> dict:
    """Bound check outcomes without repairing malformed input or choosing missing date types.

    Explicit non-null malformed dates or types outside the registry's enum leave the completion set
    unresolved. Validation precedes applicability, so an ESTIMATED label never hides malformed evidence.
    Null dates are unknown valid calendar dates; null types have both admitted enum completions.
    """
    # Imported at call time because checks exposes this separate information through its reporting shell.
    from TrialLedger.checks import date_interval

    blockers = []
    types = []
    for label, value in (("earlier_type", earlier_type), ("later_type", later_type)):
        if value is None:
            types.append(DATE_TYPES)
        elif isinstance(value, str) and value in DATE_TYPES:
            types.append((value,))
        else:
            blockers.append("invalid_date_type:" + label)
            types.append(())
    intervals = []
    for label, value in (("earlier", earlier), ("later", later)):
        if value is None:
            intervals.append((date.min.toordinal(), date.max.toordinal()))
        else:
            _, interval = date_interval(value)
            if interval is None:
                blockers.append("malformed_date:" + label)
            intervals.append(interval)
    if blockers:
        return {
            "code": "unresolved_input",
            "possible_outcomes": None,
            "excluded_outcomes": [],
            "blockers": blockers,
            "basis": BASIS,
        }
    first, second = intervals
    assert first is not None and second is not None
    possible = completion_outcomes(
        *first,
        *second,
        "ACTUAL" in types[0],
        "ACTUAL" in types[1],
        any("ESTIMATED" in choices for choices in types),
    )
    return {
        "code": "bounded",
        "possible_outcomes": list(possible),
        "excluded_outcomes": [outcome for outcome in OUTCOMES if outcome not in possible],
        "blockers": [],
        "basis": BASIS,
    }
