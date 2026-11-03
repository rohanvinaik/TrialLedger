"""Observed population witnesses bound declared eligibility designs, without reading clinical text.

The existing entailment engine owns all participant logic. This module owns the inverse question: which
candidate designs can accommodate reported participants under an explicit eligibility bridge? Separate
observations never add counts. No result claims the declared candidate family exhausts real protocols.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TypedDict

from TrialLedger.layer2 import entail
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


class WitnessResult(TypedDict):
    observation: str
    support: str
    state: str
    status: str
    basis: tuple[str, ...]
    decision: dict[str, Any]


class CandidateResult(TypedDict):
    id: str
    state: str
    observations: list[WitnessResult]
    query_decision: dict[str, Any]


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


def witness_verdict(support: str, result: str, blockers: list[str]) -> str:
    """Combine witness support with the existing participant decision (pure — pinned).

    Inconsistency is a property of the candidate, independent of witness support. A missing witness cannot
    refute a design. An unresolved binding or solver limit cannot eliminate it. A feasible proposition need
    not be universally required: undecided_by_constraints/no_constraint_mentions_query allow a witness.
    """
    if result == "INCONSISTENT":
        return "inconsistent"
    if support == "no_witness":
        return "not_ruled_out"
    if support != "witness":
        return "unresolved"
    if any(b not in ("undecided_by_constraints", "no_constraint_mentions_query") for b in blockers):
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
) -> dict:
    """Compose scoped participant proofs, witness eliminations and the surviving design consequences.

    Validation is owned by service. Each observation's status is the weakest of source and bridge support;
    its basis retains both. Results preserve complete decisions, including blockers and premise ids.
    """
    rows: list[CandidateResult] = []
    elimination_statuses: list[str] = []
    for identity, assertions in candidates:
        evidence: list[WitnessResult] = []
        for observation in observations:
            decision = entail.decide(assertions, observation.body, observation.context, bound)
            support = witness_support(
                observation.count, observation.max_exceptions, observation.status, observation.resolution
            )
            verdict = witness_verdict(support, decision.result, list(decision.blockers))
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
        state = candidate_state([row["state"] for row in evidence])
        consequence = entail.decide(assertions, query, context, bound)
        # Even when observations have no witnesses, contradictory candidate criteria remain visible.
        if consequence.result == "INCONSISTENT":
            state = "inconsistent"
        elif state == "not_ruled_out" and any(
            b not in ("undecided_by_constraints", "no_constraint_mentions_query")
            for b in consequence.blockers
        ):
            state = "unresolved"
        if state in ("ruled_out", "inconsistent"):
            reasons = [row["status"] for row in evidence if row["state"] == state]
            elimination_statuses.append(
                entail.weakest_status(tuple(reasons or [consequence.status or "known"]))
            )
        rows.append(
            {
                "id": identity,
                "state": state,
                "observations": evidence,
                "query_decision": dataclasses.asdict(consequence),
            }
        )
    remaining = [row for row in rows if row["state"] not in ("ruled_out", "inconsistent")]
    result = common_result(
        [row["state"] for row in remaining], [row["query_decision"]["result"] for row in remaining]
    )
    statuses = elimination_statuses + [row["query_decision"]["status"] or "known" for row in remaining]
    return {
        "candidates": rows,
        "remaining": [row["id"] for row in remaining],
        "consequence": {
            "result": result,
            "status": entail.weakest_status(tuple(statuses)) if result != "UNDETERMINED" else None,
            "basis": "All remaining declared candidate designs; includes the support of eliminations.",
        },
    }
