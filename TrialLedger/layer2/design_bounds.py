"""Observed population witnesses bound declared eligibility designs, without reading clinical text.

The existing entailment engine owns all participant logic. This module owns the inverse question: which
candidate designs can accommodate reported participants under an explicit eligibility bridge? Separate
observations never add counts. No result claims the declared candidate family exhausts real protocols.
"""

from __future__ import annotations

import dataclasses
from typing import Any, NotRequired, TypedDict

from TrialLedger.layer2 import entail
from TrialLedger.layer2 import signals as signal_engine
from TrialLedger.layer2.assertions import ScopedAssertion


@dataclasses.dataclass(frozen=True)
class Observation:
    id: str
    count: int
    denominator: int
    population: str
    body: object
    context: entail.Context
    status: str
    resolution: str
    max_exceptions: int
    basis: tuple[str, ...]
    upper: int | None = None
    direction: str = "accepted"
    blockers: tuple[str, ...] = ()
    derivation: dict | None = None
    exception_check: dict | None = None


class WitnessResult(TypedDict):
    observation: str
    support: str
    state: str
    status: str
    basis: tuple[str, ...]
    decision: dict[str, Any]
    bounds: NotRequired[dict]
    direction: NotRequired[str]
    derivation: NotRequired[dict]
    exception_check: NotRequired[str]
    witness_threshold: NotRequired[dict]


class CandidateResult(TypedDict):
    id: str
    state: str
    observations: list[WitnessResult]
    query_decision: dict[str, Any]
    signal_checks: NotRequired[list[dict]]
    elimination_status: NotRequired[str]


def witness_support(count: int, exceptions: int, status: str, resolution: str) -> str:
    """Whether a typed observation supplies an eligibility witness (pure — pinned).

    Preconditions: nonnegative counts, exceptions and a validated weakest status/resolution. Positive count
    beyond the exception allowance guarantees at least one witness only when the binding is resolved and
    accepted. Zero or fully excepted counts supply none; proposed is never an accepted premise.
    """
    if count <= exceptions:
        return "no_witness"
    if status == "proposed":
        return "proposed_refused"
    if resolution != "resolved":
        return "binding_unresolved"
    return "witness"


def witness_verdict(support: str, result: str, blockers: list[str], direction: str = "accepted") -> str:
    """Combine witness support with the existing participant decision (pure — pinned).

    Inconsistency is a property of the candidate, independent of witness support. A missing witness cannot
    refute a design. An unresolved binding or solver limit cannot eliminate it. A feasible proposition need
    not be universally required: undecided_by_constraints/no_constraint_mentions_query allow a witness.
    An accepted profile already refuted by admitted necessary constraints stays refuted when additional
    criteria are withheld. Rejected profiles retain those blockers: an unknown criterion could explain
    rejection. No binding, profile, query, computation limit or unknown blocker is discarded.

    post: __return__ in ('inconsistent', 'not_ruled_out', 'unresolved', 'ruled_out')
    post: __return__ != 'ruled_out' or (support == 'witness' and result == 'REFUTED')
    post: result != 'INCONSISTENT' or __return__ == 'inconsistent'
    """
    if result == "INCONSISTENT":
        return "inconsistent"
    if support == "no_witness":
        return "not_ruled_out"
    if support != "witness":
        return "unresolved"
    if direction not in ("accepted", "rejected"):
        return "unresolved"
    if any(
        b not in ("undecided_by_constraints", "no_constraint_mentions_query")
        and not (
            direction == "accepted"
            and result == "REFUTED"
            and b.startswith(
                ("proposed_refused:", "unresolved_assertion:", "unresolved_rule:", "conflicting:")
            )
        )
        for b in blockers
    ):
        return "unresolved"
    if result == "REFUTED":
        return "ruled_out"
    if result in ("ENTAILED", "UNDETERMINED"):
        return "not_ruled_out"
    return "unresolved"


def candidate_state(verdicts: list[str]) -> str:
    """Reduce independent observations without summing their populations (pure — pinned)."""
    if "inconsistent" in verdicts:
        return "inconsistent"
    if "ruled_out" in verdicts:
        return "ruled_out"
    if "unresolved" in verdicts:
        return "unresolved"
    return "not_ruled_out"


def common_result(states: list[str], results: list[str]) -> str:
    """A participant consequence across the declared surviving candidate designs (pure — pinned).

    Empty survival is a conflict, never explosion. Unresolved candidates and inconsistent/query-limited
    evaluations block closure. Otherwise every surviving design must establish the same conclusion.
    """
    if not states:
        return "CONFLICT"
    if len(states) != len(results):
        return "UNDETERMINED"
    if "unresolved" in states:
        return "UNDETERMINED"
    if all(r == "ENTAILED" for r in results):
        return "ENTAILED"
    if all(r == "REFUTED" for r in results):
        return "REFUTED"
    return "UNDETERMINED"


def bound_designs(
    candidates: list[tuple[str, tuple[ScopedAssertion, ...]]],
    observations: list[Observation],
    query: object,
    context: entail.Context,
    bound: int,
    signals: list[signal_engine.Signal] | None = None,
    claims: dict[str, list[dict]] | None = None,
    computed_signals: list[dict] | None = None,
) -> dict:
    """Compose scoped participant proofs, witness eliminations and the surviving design consequences.

    Validation is owned by service. Each observation's status is the weakest of source and bridge support;
    its basis retains both. Results preserve complete decisions, including blockers and premise ids.
    """
    rows: list[CandidateResult] = []
    elimination_statuses: list[str] = []
    signal_map = {signal.id: signal for signal in signals or []}
    source_results = (
        computed_signals
        if computed_signals is not None
        else [signal_engine.evaluate(signal) for signal in signals or []]
    )
    for identity, assertions in candidates:
        evidence: list[WitnessResult] = []
        for observation in observations:
            decision = entail.eligibility_witness(
                assertions, observation.body, observation.context, observation.direction, bound
            )
            support = (
                "binding_unresolved"
                if observation.blockers
                else witness_support(
                    observation.count, observation.max_exceptions, observation.status, observation.resolution
                )
            )
            verdict = witness_verdict(
                support, decision.result, list(decision.blockers), observation.direction
            )
            status = (
                decision.status or "known"
                if verdict == "inconsistent"
                else entail.weakest_status((observation.status, decision.status or "known"))
            )
            evidence.append(
                {
                    "observation": observation.id,
                    "support": support,
                    "state": verdict,
                    "status": status,
                    "basis": observation.basis,
                    "decision": dataclasses.asdict(decision),
                }
            )
            if observation.upper is not None or observation.derivation is not None:
                evidence[-1]["bounds"] = {
                    "lower": observation.derivation["lower"] if observation.derivation else observation.count,
                    "upper": observation.upper,
                }
            if observation.direction != "accepted":
                evidence[-1]["direction"] = observation.direction
            if observation.derivation is not None:
                evidence[-1]["derivation"] = observation.derivation
            if observation.exception_check is not None:
                evidence[-1]["exception_check"] = observation.exception_check["id"]
                evidence[-1]["witness_threshold"] = {
                    "count_lower": observation.count,
                    "supplied_exception_upper": observation.exception_check["upper"],
                    "maximum_exceptions_for_witness": observation.count - 1 if observation.count else None,
                    "requires": "accepted, resolved, same-predicate and same-scope bridge",
                }
            if observation.blockers:
                evidence[-1]["decision"]["blockers"] = tuple(
                    sorted(set(decision.blockers) | set(observation.blockers))
                )
        state = candidate_state([row["state"] for row in evidence])
        grouped: dict[str, list[dict]] = {}
        for claim in (claims or {}).get(identity, []):
            if claim["signal"] not in signal_map:
                raise ValueError("unknown_candidate_signal")
            grouped.setdefault(claim["signal"], []).append(claim["claim"])
        checks = [signal_engine.evaluate(signal_map[ref], additions) for ref, additions in grouped.items()]
        signal_states = [
            "ruled_out"
            if check["code"] == "conflict"
            else "unresolved"
            if check["code"] == "unresolved"
            else "not_ruled_out"
            for check in checks
        ]
        state = candidate_state([state, *signal_states])
        consequence = entail.decide(assertions, query, context, bound)
        # Even when observations have no witnesses, contradictory candidate criteria remain visible.
        if consequence.result == "INCONSISTENT":
            state = "inconsistent"
        elif state == "not_ruled_out" and any(
            b not in ("undecided_by_constraints", "no_constraint_mentions_query")
            for b in consequence.blockers
        ):
            state = "unresolved"
        elimination_status = None
        if state in ("ruled_out", "inconsistent"):
            reasons = [row["status"] for row in evidence if row["state"] == state]
            elimination_status = entail.weakest_status(
                tuple(
                    reasons + [check["status"] for check in checks if check["code"] == "conflict"]
                    or [consequence.status or "known"]
                )
            )
            elimination_statuses.append(elimination_status)
        rows.append(
            {
                "id": identity,
                "state": state,
                "observations": evidence,
                "query_decision": dataclasses.asdict(consequence),
            }
        )
        if signals:
            rows[-1]["signal_checks"] = checks
        if elimination_status is not None:
            rows[-1]["elimination_status"] = elimination_status
    remaining = [row for row in rows if row["state"] not in ("ruled_out", "inconsistent")]
    result = common_result(
        [row["state"] for row in remaining], [row["query_decision"]["result"] for row in remaining]
    )
    statuses = elimination_statuses + [row["query_decision"]["status"] or "known" for row in remaining]
    conflicts = [result for result in source_results if result["code"] == "conflict"]
    exception_checks = [o.exception_check for o in observations if o.exception_check is not None]
    exception_conflicts = [c for c in exception_checks if c["code"] in ("conflict", "attribution_conflict")]
    if conflicts:
        result = "CONFLICT"
        statuses.extend(result["status"] for result in conflicts)
    if exception_conflicts:
        result = "CONFLICT"
        statuses.extend(check["status"] for check in exception_conflicts)
    consequence_payload: dict[str, Any] = {
        "result": result,
        "status": entail.weakest_status(tuple(statuses)) if result != "UNDETERMINED" else None,
        "basis": "All remaining declared candidate designs; includes the support of eliminations.",
    }
    response: dict[str, Any] = {
        "candidates": rows,
        "remaining": [row["id"] for row in remaining],
        "consequence": consequence_payload,
    }
    if signals:
        response["signals"] = source_results
    if exception_checks:
        response["exception_checks"] = exception_checks
    if conflicts:
        consequence_payload["basis"] = (
            "Input signal conflict; not proof that every real protocol is impossible."
        )
        consequence_payload["blockers"] = ["signal_conflict:" + item["id"] for item in conflicts]
    if exception_conflicts:
        consequence_payload["basis"] = (
            "Input exception-bridge conflict; not proof that every real protocol is impossible."
        )
        consequence_payload.setdefault("blockers", []).extend(
            "exception_bridge_conflict:" + check["observation"] for check in exception_conflicts
        )
    return response
