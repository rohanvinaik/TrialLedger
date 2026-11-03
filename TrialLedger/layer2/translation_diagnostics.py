"""Candidate typed-identity mismatches, without decisions, clinical aliases or premise admission.

The entailment consumer may attach these rows when no constraint mentions its query. A row locates a
structural difference; it does not establish that the two literals ought to be the same clinical concept.
Proposed, descriptive and unresolved premises remain exactly those kinds of supplied material.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator
from typing import Any

from TrialLedger.layer2.assertions import (
    AllOf,
    AnyOf,
    Condition,
    Literal,
    Not,
    Proposition,
    ScopedAssertion,
    canonical,
)

Path = tuple[str | int, ...]
_MEASURED = frozenset({"quantity", "interval"})


def _plain(item: object) -> Any:
    """The existing tagged serialization, detached from the immutable model object."""
    return json.loads(canonical(item))


def _time(literal: Literal) -> str:
    """The exact temporal identity used by entail._literal_formula, excluding epistemic metadata."""
    return (
        canonical(dataclasses.replace(literal.time, certainty="unresolved", evidence=()))
        if literal.time is not None
        else ""
    )


def _literals(item: Condition, path: Path) -> Iterator[tuple[Path, Literal]]:
    """Locate literals without flattening their containing logical structure into assertions."""
    if isinstance(item, Literal):
        yield path, item
        yield from _literals(item.qualifiers, (*path, "qualifiers"))
    elif isinstance(item, AllOf | AnyOf):
        for index, part in enumerate(item.parts):
            yield from _literals(part, (*path, "parts", index))
    elif isinstance(item, Not):
        yield from _literals(item.part, (*path, "part"))


def mismatch_dimensions(premise: Literal, query: Literal) -> tuple[str, ...]:
    """Name only subject/unit/time differences under an exact resolved predicate identity.

    Unit participates in the solver's identity only for quantity/interval values. This function never
    compares predicate spelling approximately, converts a unit or chooses a clinical correspondence.

    post: all(d in ('subject', 'unit', 'time') for d in __return__)
    post: len(__return__) == len(set(__return__))
    """
    if premise.predicate.kind == "unresolved" or premise.predicate != query.predicate:
        return ()
    dimensions = []
    if premise.subject != query.subject:
        dimensions.append("subject")
    if (
        premise.value.kind in _MEASURED
        and query.value.kind in _MEASURED
        and premise.value.unit != query.value.unit
    ):
        dimensions.append("unit")
    if _time(premise) != _time(query):
        dimensions.append("time")
    return tuple(dimensions)


def _identity(literal: Literal) -> dict[str, Any]:
    """Display the relevant exact components; null unit means a non-measurement value family."""
    time = _time(literal)
    return {
        "subject": _plain(literal.subject),
        "predicate": _plain(literal.predicate),
        "unit": literal.value.unit if literal.value.kind in _MEASURED else None,
        "time": json.loads(time) if time else None,
    }


def diagnose(
    assertions: tuple[ScopedAssertion, ...] | list[ScopedAssertion], query: Proposition
) -> list[dict[str, Any]]:
    """Return candidate mismatch locations; no row is an inference, a conversion or an admitted premise.

    Both bodies and applicability are inspected, including qualifiers and nested Boolean operators.
    Paths retain the occurrence's location rather than asserting each nested literal independently.
    All submitted standings are reported unchanged, including proposed/conflicting/unresolved material.
    The caller controls whether these diagnostics are relevant to its decision; an empty list says only
    that this structural check found no same-predicate subject/unit/time difference.
    """
    asked = tuple(_literals(query, ()))
    rows = []
    for assertion in sorted(assertions, key=lambda item: item.id):
        held = (
            *_literals(assertion.body, ("body",)),
            *_literals(assertion.applicability, ("applicability",)),
        )
        for premise_path, premise in held:
            for query_path, literal in asked:
                dimensions = mismatch_dimensions(premise, literal)
                if not dimensions:
                    continue
                rows.append(
                    {
                        "code": "candidate_translation_mismatch",
                        "premise": assertion.id,
                        "dimensions": list(dimensions),
                        "predicate": _plain(literal.predicate),
                        "premise_path": list(premise_path),
                        "query_path": list(query_path),
                        "premise_identity": _identity(premise),
                        "query_identity": _identity(literal),
                        "premise_literal": _plain(premise),
                        "query_literal": _plain(literal),
                        "status": assertion.status,
                        "resolution": assertion.resolution,
                        "modality": assertion.modality,
                        "criterion_ref": assertion.criterion_ref,
                        "cohort": _plain(assertion.cohort),
                        "rule": _plain(assertion.rule) if assertion.rule is not None else None,
                    }
                )
    return rows
