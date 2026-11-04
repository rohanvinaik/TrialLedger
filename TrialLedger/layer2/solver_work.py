"""Conservative assignment/check reservations over the existing finite solver representation.

This module neither executes a solver nor changes its semantic assignment bound.
Unsupported expansions retain the caller's conservative ceiling in design_session.
"""

from __future__ import annotations

from typing import cast

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, entail_explanations, session_state


def partition_product(sizes: list[int], ceiling: int) -> int:
    """Cap an exact finite partition product without materializing its assignments (pure).

    pre: type(ceiling) is int and ceiling > 0
    pre: all(type(size) is int and size > 0 for size in sizes)
    post: 1 <= __return__ <= ceiling
    """
    if type(ceiling) is not int or ceiling < 1:
        raise ValueError("invalid_partition_ceiling")
    if type(sizes) is not list or any(type(size) is not int or size < 1 for size in sizes):
        raise ValueError("invalid_partition_sizes")
    total = 1
    for size in sizes:
        total = min(ceiling, total * size)
    return total


def _partition_space(formulas: list[tuple], ceiling: int) -> int:
    """The same partition cardinalities used by entail._satisfiable, without enumeration.

    A Boolean has two representatives; m distinct numeric thresholds have 2m+1
    exact rational cells; m enum members retain one additional unlisted member.
    Formula atoms are produced by the existing typed compiler, never raw text.
    """
    domains: dict[str, tuple[str, set]] = {}
    for formula in formulas:
        for family, key, payload in entail._atoms(formula):
            existing, values = domains.setdefault(key, (family, set()))
            if family != existing:
                raise ValueError("mixed_partition_family")
            if family == "measure":
                values.add(payload)
            elif family == "enum":
                values.update(payload)
    sizes = [
        2 if family == "bool" else 2 * len(values) + 1 if family == "measure" else len(values) + 1
        for family, values in domains.values()
    ]
    return partition_product(sizes, ceiling)


def _models(values: object) -> tuple[a.ScopedAssertion, ...]:
    if type(values) is not list:
        raise ValueError("assertions_not_a_list")
    parsed = tuple(a.from_canonical(session_state.canonical(value)) for value in values)
    if not all(isinstance(value, a.ScopedAssertion) for value in parsed):
        raise ValueError("assertion_model_needed")
    return cast(tuple[a.ScopedAssertion, ...], parsed)


def _query(value: object) -> object:
    parsed = a.from_canonical(session_state.canonical(value))
    if not isinstance(parsed, a.PROPOSITIONS):
        raise ValueError("query_model_needed")
    return parsed


def _context(value: object) -> entail.Context:
    if type(value) is not dict or not set(value) <= {"cohort", "arm", "phase"}:
        raise ValueError("invalid_context")
    if any(item is not None and (type(item) is not str or not item) for item in value.values()):
        raise ValueError("invalid_context_value")
    return entail.Context(**cast(dict, value))


def _formulas(assertions: tuple[a.ScopedAssertion, ...], context: entail.Context) -> dict[str, tuple]:
    out = {}
    for index, item in enumerate(assertions):
        code, formula, _ = entail.assertion_formula(item, context)
        if code == "constraint":
            out[str(index)] = formula
    return out


def _decision_space(
    assertions: tuple[a.ScopedAssertion, ...], query: object, context: entail.Context, ceiling: int
) -> int:
    """Bound every component checked by decide, including its query and proof subsets."""
    formulas = _formulas(assertions, context)
    asked, _ = entail.proposition_formula(query)

    def variables(formula: tuple) -> set:
        return {key for _, key, _ in entail._atoms(formula)}

    groups = entail._components(
        [(entail.QUERY, variables(asked))] + [(key, variables(formula)) for key, formula in formulas.items()]
    )
    return max(
        _partition_space(
            [formulas[key] for key in group if key != entail.QUERY]
            + ([asked] if entail.QUERY in group else []),
            ceiling,
        )
        for group in groups
    )


def _decision_work(
    assertions: tuple[a.ScopedAssertion, ...],
    query: object,
    context: entail.Context,
    bound: int,
    explanations: bool,
) -> int:
    # n consistency components, two query directions and known-first proof
    # minimization require at most 2n+4 calls for one ordinary decide.
    calls = 2 * len(assertions) + 4
    space = _decision_space(assertions, query, context, bound)
    if not explanations:
        return calls * space
    conditions = entail_explanations.planned_conditions(assertions, query, context)
    # The shared plan's atoms already lie in the original query component.
    # Its global/implication checks add no partition cells. Intrinsic query
    # feasibility is one additional bounded enumeration.
    return (calls * (2 * len(conditions) + 1) + 1) * space


def _entailment(request: dict, bound: int) -> int:
    return _decision_work(
        _models(request["assertions"]),
        _query(request["query"]),
        _context(request.get("context", {})),
        bound,
        True,
    )


def _interpretations(request: dict, bound: int) -> int:
    from TrialLedger.layer2 import interpretations

    context = _context(request.get("context", {}))
    fixed, _ = interpretations._supported_assertions(_models(request["fixed"]["assertions"]), context)
    queries = [_query(row["body"]) for row in request["queries"]]
    probe = interpretations._consistency_query()
    total = _decision_work(fixed, probe, context, bound, False)
    total += sum(_decision_work(fixed, query, context, bound, True) for query in queries)
    for frame in request["interpretations"]:
        assumed = interpretations._assume_assertions(_models(frame["assumptions"]))
        local, _ = interpretations._supported_assertions(assumed, context)
        combined = (*fixed, *local)
        total += _decision_work(local, probe, context, bound, False)
        total += _decision_work(combined, probe, context, bound, False)
        total += sum(_decision_work(combined, query, context, bound, True) for query in queries)
    return total


def _design_bounds(request: dict, bound: int) -> int:
    context = _context(request.get("context", {}))
    query = _query(request["query"])
    total = 0
    for candidate in request["candidates"]:
        models = _models(candidate["assertions"])
        for observation in request["observations"]:
            # Derived witness bodies are compiled by the signal owner later.
            # Preserve a conservative per-call ceiling until that body is known.
            space = bound
            if "body" in observation:
                profile = _query(observation["body"])
                witness_context = _context(observation.get("context", {}))
                if observation.get("direction", "accepted") == "accepted":
                    space = _decision_space(models, profile, witness_context, bound)
                else:
                    formulas = list(_formulas(models, witness_context).values())
                    profile_formula, _ = entail.proposition_formula(profile)
                    space = _partition_space([*formulas, profile_formula], bound)
            # Eligibility witnesses include an intrinsic profile check; negative
            # witnesses may conjoin all candidate components and minimize a proof.
            calls = (
                2 * len(models) + 5
                if observation.get("direction", "accepted") == "accepted"
                else 3 * len(models) + 8
            )
            total += calls * space
        total += _decision_work(models, query, context, bound, True)
    return total


def logical_reservation(request: dict, bound: int) -> int | None:
    """An upper bound for an expanded supported request, or None for ceiling fallback.

    Source compilation is a pure preparation step; no solver executes here.
    Unknown/malformed expansions do not receive an invented smaller reservation.
    """
    operation = request["operation"]
    try:
        if operation == "entailment":
            return _entailment(request, bound)
        if operation == "interpretations":
            return _interpretations(request, bound)
        if operation == "design_bounds":
            return _design_bounds(request, bound)
        if operation == "source_assertions":
            from TrialLedger.layer2 import source_assertions

            prepared = source_assertions.prepare(request)
            values = [logical_reservation(child, bound) for child in prepared["requests"]]
            if any(value is None for value in values):
                return None
            return sum(value for value in values if value is not None)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return None
    return None
