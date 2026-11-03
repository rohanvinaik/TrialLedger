"""Discoverable partial evidence contracts, separate from source retrieval and clinical binding."""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import signals

INPUTS = {
    "signals": {"required": ("signals",), "fields": {"signals": "array of source-supported signal objects"}},
    "signal": {
        "required": ("id", "kind", "data", "support"),
        "fields": {
            "id": "distinct nonempty string",
            "kind": "one of signal_kinds",
            "data": "kind-specific typed input; see operator_inputs",
            "support": "nonempty array of independently identified support objects",
            "bindings": "optional object mapping mathematical ref ids to tagged participant propositions",
        },
    },
    "support": {
        "required": ("id", "status", "resolution", "basis"),
        "fields": {
            "id": "distinct premise/source-binding id",
            "status": "known/interpolated/proposed",
            "resolution": "resolved/partially_resolved/unresolved/conflicting",
            "basis": "nonempty exact source/version or user-premise references",
        },
    },
    "signal_claim": {
        "required": ("signal", "claim"),
        "fields": {
            "signal": "existing signal id",
            "claim": "typed candidate claim; all claims per signal checked jointly",
        },
    },
    "derived_observation": {
        "required": ("id", "denominator", "population", "context", "bridge", "derivation"),
        "fields": {
            "id": "distinct observation id",
            "denominator": "same positive total as the signal",
            "population": "same universe identifier as the signal",
            "context": "bound entry context",
            "bridge": "explicit eligibility bridge; its standing is retained",
            "derivation": "signal/witness selector; body and interval come from the calculation",
            "direction": "accepted (default) or rejected",
        },
    },
    "derivation": {
        "required": ("signal", "witness"),
        "fields": {
            "signal": "source-supported signal id",
            "witness": "named witness emitted by that operator",
        },
    },
}


def example(kind: str = "overlap") -> dict:
    return {
        "operation": "signals",
        "signals": [
            {
                "id": "invented-" + kind,
                "kind": kind,
                "data": deepcopy(signals.operator(kind).EXAMPLES[kind]),
                "support": [
                    {
                        "id": "invented-inputs",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["user:invented-typed-demonstration-not-clinical-evidence"],
                    }
                ],
            }
        ],
    }


def extend(description: dict) -> None:
    description["availability"]["built"].append("typed partial-evidence bounds and graph/dependency checks")
    description["use_cases"].append(
        {
            "question": "What do partial distributions, populations, sequences and prerequisites constrain?",
            "operation": "signals",
            "read": "signals: value, rule, status, basis and blockers",
            "meaning": "Independent typed operators whose results can constrain declared designs.",
        }
    )
    description["examples"]["signals"] = example()
    description["example_results"]["signals"] = (
        "Bounded overlap; no independence or exact joint count assumed."
    )
    description["answer_guide"]["signals"] = {
        "bounded": ["settled", "A mathematical interval under supplied bindings; retain weakest support."],
        "consistent": [
            "your_call",
            "No contradiction under these declared structural facts; not a recovered protocol.",
        ],
        "conflict": ["something_wrong", "Name the contradictory counts, relations or required inputs."],
        "unresolved": ["by_blocker", "Confirm proposals, repair bindings or narrow a computation limit."],
    }
    description["result_guides"]["signals"] = {
        "fields": {
            "basis": "conditional premise boundary",
            "premises": "unchanged input signals",
            "signals": "per-operator value, standing, source references, rule and blockers",
            "limits": "typed, source-bound mathematical/structural operation; not a clinical reader",
        },
        "intervals": (
            "Bounds are not exact counts; [0,N] is not observed zero. "
            "Unresolved derivations keep null bounds."
        ),
        "bindings": "A universe binds study/version/population/assessment; denominators do not bind it.",
        "standing": "Support is checked independently; every dependent result retains its weakest status.",
        "consumers": "Use design_bounds.signals, derived observations and candidate.signal_claims.",
        "source_boundary": "Source records and corpus statement counts remain unchanged.",
    }
    description["signal_kinds"] = list(signals.MODULES)
    description["operator_inputs"] = {
        kind: deepcopy(signals.operator(kind).INPUTS[kind]) for kind in signals.MODULES
    }
    description["signal_examples"] = {kind: example(kind) for kind in signals.MODULES}
