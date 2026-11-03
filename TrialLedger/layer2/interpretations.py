"""Competing clinical readings in isolated, explicitly hypothetical environments.

The existing finite entailment and signal operators own the deductions. This module owns which premises
belong together and what their consequences warrant. A local assumption is never admitted to the fixed
floor, another interpretation, ordinary entailment, a source record or a corpus statement count.
"""

from __future__ import annotations

import dataclasses
import json

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail
from TrialLedger.layer2 import interpretation_bindings as binding_engine
from TrialLedger.layer2 import signals as signal_engine
from TrialLedger.layer2.design_bounds import common_result


@dataclasses.dataclass(frozen=True)
class Interpretation:
    id: str
    label: str
    origin: str
    basis: tuple[str, ...]
    assumptions: tuple[a.ScopedAssertion, ...] = ()
    signals: tuple[signal_engine.Signal, ...] = ()
    signal_claims: tuple[dict, ...] = ()
    binding_uses: tuple[binding_engine.BindingUse, ...] = ()


@dataclasses.dataclass(frozen=True)
class Query:
    id: str
    body: a.Proposition


def compatibility_state(
    floor_conflict: bool, intrinsic_conflict: bool, fixed_conflict: bool, unresolved: bool
) -> str:
    """Keep the source floor, incoherent assumptions and fixed-rule refutation distinct (pure — pinned).

    Flags are already warranted observations, not guessed clinical classifications. An unresolved binding
    cannot set a conflict flag; its available conditional calculations remain in the enclosing result.

    post: __return__ in ("floor_conflict", "incoherent", "refuted", "unresolved", "compatible")
    post: (__return__ == "floor_conflict") == floor_conflict
    post: __return__ != "compatible" or not floor_conflict
    post: __return__ != "compatible" or not intrinsic_conflict
    post: __return__ != "compatible" or not fixed_conflict
    post: __return__ != "compatible" or not unresolved
    post: floor_conflict or intrinsic_conflict or fixed_conflict or unresolved or __return__ == "compatible"
    post: __return__ != "refuted" or (not floor_conflict and not intrinsic_conflict and fixed_conflict)
    """
    if floor_conflict:
        return "floor_conflict"
    if intrinsic_conflict:
        return "incoherent"
    if fixed_conflict:
        return "refuted"
    if unresolved:
        return "unresolved"
    return "compatible"


def selection_state(selected: str | None, states: dict[str, str]) -> str:
    """A user choice cannot admit a refuted or incoherent reading (pure — pinned).

    post: __return__ in ("none", "unknown_selection", "selected", "unresolved", "refused")
    post: (__return__ == "none") == (selected is None)
    post: (__return__ == "unknown_selection") == (selected is not None and selected not in states)
    post: __return__ != "selected" or (selected is not None and states.get(selected) == "compatible")
    post: selected is None or states.get(selected) != "compatible" or __return__ == "selected"
    post: __return__ != "unresolved" or (selected is not None and states.get(selected) == "unresolved")
    post: selected is None or states.get(selected) != "unresolved" or __return__ == "unresolved"
    """
    if selected is None:
        return "none"
    if selected not in states:
        return "unknown_selection"
    state = states[selected]
    if state == "compatible":
        return "selected"
    if state == "unresolved":
        return "unresolved"
    return "refused"


def _plain(model: object) -> dict:
    return json.loads(a.canonical(model))


def _signal_premise(signal: signal_engine.Signal) -> dict:
    result = dataclasses.asdict(signal)
    if not signal.application_blockers:
        result.pop("application_blockers")
    result["bindings"] = {ref: _plain(body) for ref, body in signal.bindings.items()}
    return result


def _consistency_query() -> a.Literal:
    """A harmless query: decide checks every premise component before answering it."""
    return a.Literal(
        a.Subject("participant"), a.Predicate("demographic", "frame-consistency"), a.Value("boolean")
    )


def _supported_assertions(
    assertions: tuple[a.ScopedAssertion, ...], context: entail.Context
) -> tuple[tuple[a.ScopedAssertion, ...], tuple[str, ...]]:
    """Only fully bound premises may produce a refutation; retain excluded premises as blockers."""
    supported = []
    blockers = []
    for item in assertions:
        _, _, found = entail.assertion_formula(item, context)
        if item.resolution != "resolved":
            found = (*found, "premise_not_resolved:" + item.id)
        if found:
            blockers.extend(found)
        else:
            supported.append(item)
    return tuple(supported), tuple(sorted(set(blockers)))


def _assume_assertions(assertions: tuple[a.ScopedAssertion, ...]) -> tuple[a.ScopedAssertion, ...]:
    """Private hypothetical copies; original proposed standing is serialized separately."""
    return tuple(
        dataclasses.replace(item, status="interpolated") if item.status == "proposed" else item
        for item in assertions
    )


def _assume_signal(signal: signal_engine.Signal) -> signal_engine.Signal:
    return dataclasses.replace(
        signal,
        support=tuple(
            dataclasses.replace(premise, status="interpolated") if premise.status == "proposed" else premise
            for premise in signal.support
        ),
    )


def _local_calculation(signal: signal_engine.Signal, claims: list[dict] | None = None) -> dict:
    result = signal_engine.evaluate(_assume_signal(signal), claims)
    result.update(
        support=[dataclasses.asdict(premise) for premise in signal.support],
        status=entail.weakest_status(tuple(premise.status for premise in signal.support)),
        guarantee="conditional_on_interpretation",
        assumed_support=[premise.id for premise in signal.support if premise.status == "proposed"],
    )
    return result


def _gate_calculation(result: dict, checks: list[dict]) -> dict:
    applied = [row for row in checks if row["signal"] == result["id"]]
    if not applied:
        return result
    blockers = [blocker for row in applied for blocker in row["blockers"]]
    if any(row["code"] == "unresolved" for row in applied) and not blockers:
        blockers.append("binding_application_unresolved:" + result["id"])
    binding_basis = [ref for row in applied for ref in row["basis"]]
    return {
        **result,
        "ungated_code": result["code"],
        "unbound_status": result["status"],
        "code": "unresolved" if blockers else result["code"],
        "status": entail.weakest_status((result["status"], *(row["status"] for row in applied))),
        "guarantee": "conditional_on_interpretation",
        "binding_refs": [row["binding"] for row in applied],
        "assumed_bindings": [row["binding"] for row in applied if row["status"] == "proposed"],
        "binding_basis": binding_basis,
        "binding_support": applied,
        "basis": list(dict.fromkeys([*result["basis"], *binding_basis])),
        "blockers": sorted(set([*result["blockers"], *blockers])),
    }


def _query_rows(
    assertions: tuple[a.ScopedAssertion, ...],
    queries: tuple[Query, ...],
    context: entail.Context,
    bound: int,
    state: str,
    guarantee: str,
    assumptions: tuple[a.ScopedAssertion, ...] = (),
    blockers: tuple[str, ...] = (),
) -> list[dict]:
    rows = []
    for query in queries:
        decision = entail.decide(assertions, query.body, context, bound)
        admissible = decision.result if state == "compatible" else entail.UNDETERMINED
        raised = list(blockers)
        if state != "compatible":
            raised.append("interpretation_" + state)
        rows.append(
            {
                "id": query.id,
                "body": _plain(query.body),
                "result": admissible,
                "decision": dataclasses.asdict(decision),
                "warrant": {
                    "rule": "entail.decide:1",
                    "guarantee": guarantee,
                    "status": entail.weakest_status(
                        (decision.status or "known", *(item.status for item in assumptions))
                    ),
                    "assumptions": [item.id for item in assumptions],
                    "proof": list(decision.proof),
                    "blockers": sorted(set([*decision.blockers, *raised])),
                },
            }
        )
    return rows


def _claim_checks(
    interpretation: Interpretation,
    fixed_signals: tuple[signal_engine.Signal, ...],
    binding_checks: list[dict],
) -> tuple[list[dict], bool, bool]:
    fixed_ids = {signal.id for signal in fixed_signals}
    signals = {signal.id: signal for signal in (*fixed_signals, *interpretation.signals)}
    grouped: dict[str, list[dict]] = {}
    for row in interpretation.signal_claims:
        if row["signal"] not in signals:
            raise ValueError("unknown_interpretation_signal_claim")
        grouped.setdefault(row["signal"], []).append(row["claim"])
    checks = []
    intrinsic_conflict = fixed_conflict = False
    for identity, claims in grouped.items():
        signal = signals[identity]
        result = (
            signal_engine.evaluate(signal, claims)
            if identity in fixed_ids
            else _local_calculation(signal, claims)
        )
        checked = _gate_calculation(result, binding_checks)
        checks.append({**checked, "claims": claims})
        if checked["code"] == "conflict":
            if identity in fixed_ids:
                fixed_conflict = True
            else:
                intrinsic_conflict = True
    return checks, intrinsic_conflict, fixed_conflict


def _frame_row(
    study_ref: str,
    interpretation: Interpretation,
    fixed_assertions: tuple[a.ScopedAssertion, ...],
    fixed_signals: tuple[signal_engine.Signal, ...],
    queries: tuple[Query, ...],
    bindings: tuple[binding_engine.Binding, ...],
    context: entail.Context,
    bound: int,
    floor_conflict: bool,
    floor_blockers: tuple[str, ...],
) -> dict:
    assumed = _assume_assertions(interpretation.assumptions)
    local_assertions, local_blockers = _supported_assertions(assumed, context)
    combined = (*fixed_assertions, *local_assertions)
    intrinsic = entail.decide(local_assertions, _consistency_query(), context, bound)
    consistency = entail.decide(combined, _consistency_query(), context, bound)
    binding_checks = binding_engine.check_uses(
        bindings, interpretation.binding_uses, (*fixed_signals, *interpretation.signals), study_ref
    )
    used_signal_ids = {use.signal for use in interpretation.binding_uses}
    calculations = [
        _gate_calculation(signal_engine.evaluate(signal), binding_checks)
        for signal in fixed_signals
        if signal.id in used_signal_ids
    ]
    calculations.extend(
        _gate_calculation(_local_calculation(signal), binding_checks) for signal in interpretation.signals
    )
    checks, claim_intrinsic, claim_fixed = _claim_checks(interpretation, fixed_signals, binding_checks)
    checked_ids = {row["id"] for row in checks}
    # A joint claim is the hypothesized completion of its signal. Retain the uncompleted calculation as
    # context, but do not let its unknown prerequisites overrule the completed check.
    for row in calculations:
        row["role"] = "baseline_context" if row["id"] in checked_ids else "active_premise"
    active_calculations = [row for row in calculations if row["id"] not in checked_ids]
    blockers = set((*floor_blockers, *local_blockers))
    for row in [*active_calculations, *checks, *binding_checks]:
        if row["code"] == "unresolved":
            blockers.update(row["blockers"] or ["unresolved_signal:" + row.get("id", row.get("binding", ""))])
    if "resource_bound" in (*intrinsic.blockers, *consistency.blockers):
        blockers.add("resource_bound")
    intrinsic_conflict = (
        intrinsic.result == entail.INCONSISTENT
        or claim_intrinsic
        or any(row["code"] == "conflict" for row in active_calculations)
    )
    state = compatibility_state(
        floor_conflict,
        intrinsic_conflict,
        consistency.result == entail.INCONSISTENT or claim_fixed,
        bool(blockers),
    )
    fixed_by_id = {item.id: item for item in fixed_assertions}
    used_fixed = [identity for identity in consistency.proof if identity in fixed_by_id]
    signal_floor = [row for row in checks if row["id"] in {signal.id for signal in fixed_signals}]
    fixed_statuses = [fixed_by_id[identity].status for identity in used_fixed]
    fixed_statuses.extend(row["status"] for row in signal_floor)
    queries_result = _query_rows(
        combined,
        queries,
        context,
        bound,
        state,
        "conditional_on_interpretation",
        interpretation.assumptions,
        tuple(sorted(blockers)),
    )
    return {
        "id": interpretation.id,
        "label": interpretation.label,
        "origin": interpretation.origin,
        "state": state,
        "premises": {
            "basis": list(interpretation.basis),
            "assumptions": [_plain(item) for item in interpretation.assumptions],
            "signals": [_signal_premise(signal) for signal in interpretation.signals],
            "signal_claims": list(interpretation.signal_claims),
            "binding_uses": [dataclasses.asdict(use) for use in interpretation.binding_uses],
        },
        "bindings": binding_checks,
        "signals": calculations,
        "signal_checks": checks,
        "queries": queries_result,
        "warrant": {
            "rule": "interpretations.compatibility:1",
            "guarantee": "conditional_on_fixed_and_interpretation_premises",
            "fixed_status": entail.weakest_status(tuple(fixed_statuses)),
            "status": entail.weakest_status(
                tuple(fixed_statuses)
                + tuple(item.status for item in interpretation.assumptions)
                + tuple(row["status"] for row in [*calculations, *binding_checks])
                + ("interpolated",)
            ),
            "fixed_premises": used_fixed,
            "assumptions": [item.id for item in interpretation.assumptions],
            "bindings": [row["binding"] for row in binding_checks],
            "basis": list(interpretation.basis),
            "consistency": dataclasses.asdict(consistency),
            "intrinsic_consistency": dataclasses.asdict(intrinsic),
            "signal_rules": [{"id": row["id"], "rule": row["rule"]} for row in [*calculations, *checks]],
            "blockers": sorted(blockers),
        },
    }


def _consequences(
    fixed_queries: list[dict], frames: list[dict], floor_conflict: bool, selected: str | None, selection: str
) -> list[dict]:
    surviving = [row for row in frames if row["state"] in ("compatible", "unresolved")]
    chosen = [row for row in surviving if row["id"] == selected] if selected is not None else surviving
    consequences = []
    for index, fixed in enumerate(fixed_queries):
        if not floor_conflict and fixed["result"] == entail.UNSUPPORTED_QUERY:
            consequences.append({**fixed, "frames": [], "basis": "query_translation"})
            continue
        if not floor_conflict and fixed["result"] in (entail.ENTAILED, entail.REFUTED):
            consequences.append({**fixed, "frames": [], "basis": "fixed_floor"})
            continue
        state = common_result(
            ["unresolved" if row["state"] == "unresolved" else "not_ruled_out" for row in chosen],
            [row["queries"][index]["result"] for row in chosen],
        )
        if floor_conflict or selection == "refused":
            state = "CONFLICT" if floor_conflict else entail.UNDETERMINED
        consequences.append(
            {
                "id": fixed["id"],
                "body": fixed["body"],
                "result": state,
                "frames": [row["id"] for row in chosen],
                "basis": "selected_interpretation"
                if selected is not None
                else "declared_interpretation_family",
                "warrant": {
                    "rule": "interpretations.common:1",
                    "guarantee": "conditional_on_declared_family_not_exhaustive",
                    "status": entail.weakest_status(tuple(row["warrant"]["status"] for row in frames)),
                    "blockers": sorted(
                        {
                            blocker
                            for row in chosen
                            for blocker in row["queries"][index]["warrant"]["blockers"]
                        }
                        | ({"fixed_floor_conflict"} if floor_conflict else set())
                        | ({"selected_interpretation_refused"} if selection == "refused" else set())
                    ),
                },
            }
        )
    return consequences


def resolve(
    study_ref: str,
    fixed_assertions: tuple[a.ScopedAssertion, ...],
    fixed_signals: tuple[signal_engine.Signal, ...],
    interpretations: tuple[Interpretation, ...],
    queries: tuple[Query, ...],
    bindings: tuple[binding_engine.Binding, ...] = (),
    context: entail.Context = entail.EVERYONE,
    bound: int = entail.MAX_ASSIGNMENTS,
    selected: str | None = None,
) -> dict:
    """Evaluate an immutable snapshot of fixed evidence and competing hypothetical readings.

    Public shape validation belongs to service. This boundary also refuses duplicate identities and an
    unknown selection because proof references must remain unambiguous for Python callers as well.
    """
    frame_ids = [frame.id for frame in interpretations]
    query_ids = [query.id for query in queries]
    if len(set(frame_ids)) != len(frame_ids) or len(set(query_ids)) != len(query_ids):
        raise ValueError("duplicate_interpretation_or_query_id")
    if not interpretations or not queries:
        raise ValueError("empty_interpretation_inputs")
    if selected is not None and selected not in frame_ids:
        raise ValueError("unknown_selected_interpretation")
    fixed_ids = [item.id for item in fixed_assertions]
    fixed_signal_ids = [signal.id for signal in fixed_signals]
    if len(set(fixed_ids)) != len(fixed_ids) or len(set(fixed_signal_ids)) != len(fixed_signal_ids):
        raise ValueError("duplicate_fixed_premise_id")
    for frame in interpretations:
        ids = [*fixed_ids, *(item.id for item in frame.assumptions)]
        signal_ids = [*fixed_signal_ids, *(signal.id for signal in frame.signals)]
        if len(set(ids)) != len(ids) or len(set(signal_ids)) != len(signal_ids):
            raise ValueError("duplicate_interpretation_premise_id")
    supported_fixed, floor_blockers = _supported_assertions(fixed_assertions, context)
    floor = entail.decide(supported_fixed, _consistency_query(), context, bound)
    fixed_calculations = [signal_engine.evaluate(signal) for signal in fixed_signals]
    floor_conflict = floor.result == entail.INCONSISTENT or any(
        row["code"] == "conflict" for row in fixed_calculations
    )
    if "resource_bound" in floor.blockers:
        floor_blockers = (*floor_blockers, "resource_bound")
    fixed_queries = _query_rows(
        supported_fixed,
        queries,
        context,
        bound,
        "floor_conflict" if floor_conflict else "compatible",
        "fixed_floor",
    )
    frames = [
        _frame_row(
            study_ref,
            frame,
            supported_fixed,
            fixed_signals,
            queries,
            bindings,
            context,
            bound,
            floor_conflict,
            floor_blockers,
        )
        for frame in interpretations
    ]
    choice = selection_state(selected, {row["id"]: row["state"] for row in frames})
    return {
        "study_ref": study_ref,
        "fixed": {
            "assertions": [_plain(item) for item in fixed_assertions],
            "consistency": dataclasses.asdict(floor),
            "queries": fixed_queries,
            "signals": fixed_calculations,
            "blockers": list(floor_blockers),
        },
        "bindings": [dataclasses.asdict(binding) for binding in bindings],
        "interpretations": frames,
        "remaining": [row["id"] for row in frames if row["state"] in ("compatible", "unresolved")],
        "refuted": [row["id"] for row in frames if row["state"] == "refuted"],
        "incoherent": [row["id"] for row in frames if row["state"] == "incoherent"],
        "unresolved": [row["id"] for row in frames if row["state"] == "unresolved"],
        "selection": {"id": selected, "state": choice, "origin": "user_choice" if selected else None},
        "consequences": _consequences(fixed_queries, frames, floor_conflict, selected, choice),
        "limits": (
            "Exact conditional checks over declared readings; compatibility is not source truth or clinical "
            "recommendation. The interpretation family is not assumed exhaustive. No automatic text reading, "
            "source correction, source mutation or corpus-frequency admission."
        ),
    }
