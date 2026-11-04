"""Small Python conveniences for the existing assertion model, without clinical translation.

Every substantive choice remains an argument: subject, predicate, comparison, units,
force, applicability, cohort and provenance. Status defaults to proposed. Provenance
uses the model's existing criterion_ref, Rule and Evidence objects, not a new origin
ontology. `expanded` exposes the exact canonical JSON used in a reasoning request.
"""

from __future__ import annotations

import json
from typing import Any

from TrialLedger.layer2.assertions import (
    AllOf as AllOf,
)
from TrialLedger.layer2.assertions import (
    Always as Always,
)
from TrialLedger.layer2.assertions import (
    AnyOf as AnyOf,
)
from TrialLedger.layer2.assertions import (
    Branch,
    Condition,
    Evidence,
    Literal,
    ModelError,
    Predicate,
    Proposition,
    Rule,
    Scope,
    ScopedAssertion,
    Span,
    Subject,
    TemporalScope,
    Value,
    canonical,
    model_problem,
)
from TrialLedger.layer2.assertions import (
    Not as Not,
)

UNRESOLVED_BRANCH = Branch("unresolved")


def _text(value: object, code: str) -> None:
    """Reject malformed vocabulary containers before the model's vocabulary lookup."""
    if not isinstance(value, str):
        raise ModelError(code)


def quantity(*, number: int | float, comparison: str, unit: str, inclusivity: str) -> Value:
    """An exact quantity as written; no unit conversion or inferred boundary."""
    _text(comparison, "comparison_not_text")
    _text(inclusivity, "inclusivity_not_text")
    return Value("quantity", comparison=comparison, number=number, unit=unit, inclusivity=inclusivity)


def enum_value(*, members: tuple[str, ...], comparison: str) -> Value:
    """One value from an open domain; `in` states one of the supplied alternatives."""
    _text(comparison, "comparison_not_text")
    return Value("enum", comparison=comparison, members=members)


def enum_set_value(*, members: tuple[str, ...], comparison: str) -> Value:
    """A set-valued restriction; `in` retains every supplied member, not one of them."""
    _text(comparison, "comparison_not_text")
    return Value("enum_set", comparison=comparison, members=members)


def literal(
    *,
    subject: Subject,
    predicate: Predicate,
    value: Value,
    polarity: str,
    time: TemporalScope | None,
    qualifiers: Condition,
    evidence: tuple[Evidence, ...],
) -> Literal:
    """Prepare one explicitly qualified proposition using the model's validation."""
    _text(polarity, "polarity_not_text")
    return Literal(subject, predicate, value, polarity, time, qualifiers, evidence)


def scoped_assertion(
    *,
    id: str,
    criterion_ref: str,
    modality: str,
    body: Proposition,
    cohort: Scope,
    applicability: Condition,
    rule: Rule,
    status: str = "proposed",
    resolution: str = "unresolved",
    branch: Branch = UNRESOLVED_BRANCH,
    span: tuple[Span, ...] = (),
) -> ScopedAssertion:
    """Keep force, scope and origin explicit; construction never confirms a reading.

    `criterion_ref` and `rule` are the caller's attributed provenance. Supplying a
    known status does not independently authenticate that attribution or consent.
    """
    _text(modality, "modality_not_text")
    _text(status, "status_not_text")
    _text(resolution, "resolution_not_text")
    return ScopedAssertion(
        id=id,
        criterion_ref=criterion_ref,
        modality=modality,
        body=body,
        cohort=cohort,
        applicability=applicability,
        rule=rule,
        status=status,
        resolution=resolution,
        branch=branch,
        span=span,
    )


def expanded(item: object) -> dict[str, Any]:
    """Return inspectable canonical JSON of a validated model object, never a prose reading."""
    problem = model_problem(item)
    if problem != "ok":
        raise ModelError(problem)
    return json.loads(canonical(item))
