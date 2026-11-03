"""Discoverable partial evidence contracts, separate from source retrieval and clinical binding."""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import signals

INPUTS = {
    "signals": {
        "required": ("signals",),
        "fields": {
            "signals": "array of source-supported signal objects",
            "study_ref": "required nonempty identity when bindings or binding_uses supplied",
            "bindings": "optional interpretation_binding declarations",
            "binding_uses": "optional interpretation_binding_use; proposed refused outside frames",
        },
    },
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


def binding_example() -> dict:
    """Invented subset relation; compatibility never establishes population identity."""
    request = example("population")
    scope = {
        "study": "invented:study",
        "population": "invented:randomized",
        "arm": "all",
        "time": "entry",
        "version": "v1",
    }
    request.update(
        study_ref=scope["study"],
        bindings=[
            {
                "id": "analysed-subset",
                "kind": "population",
                "relation": "subset_of",
                "subjects": ["randomized", "analysed"],
                "scope": scope.copy(),
                "sources": [
                    {"ref": "invented:population-definition", "version": "v1", "address": "/definition"}
                ],
                "status": "interpolated",
                "resolution": "resolved",
                "basis": ["invented:working-population-reading"],
            }
        ],
        binding_uses=[{"binding": "analysed-subset", "signal": "invented-population", "scope": scope.copy()}],
    )
    return request


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
    description["binding_example"] = binding_example()
    description["result_guides"]["signals"]["optional_fields"] = {
        "binding_checks": "Full application checks; proposed bindings are refused outside frames",
        "binding_premises": "Unchanged study identity, bindings and application scopes",
        "operator_support": "Deciding internal support/ids; the outer wrapper cannot promote a local reading",
        "admission": "Support gate and application blockers, including equal raw/effective codes",
    }
    description["result_guides"]["signals"]["stages"] = (
        "Each transition retains raw/effective population checks, exact person/person-period/cluster unit, "
        "scope and local support. A permitted pathway supplies no subset arithmetic. A declared subset "
        "is checked for count compatibility, not proved identity or individual progression. Read each "
        "transition's metadata separately. Empty graphs are inspection with no clinical findings. "
        "gate_ref is retained as a premise reference; its clinical condition is not evaluated here."
    )
    description["result_guides"]["signals"]["binding_preflight"] = (
        "Supply bindings and binding_uses with study_ref to check population/definition applications. "
        "Gate arithmetic, candidate claims and derived witnesses together. A mismatched scope remains "
        "unresolved even when raw arithmetic conflicts; compatibility does not establish identity."
    )
    description["result_guides"]["signals"]["decision_table"] = (
        "Explicit finite equality domains and feasible-combination constraints precede coverage, "
        "different-action overlap and action reachability. Same-action overlap is diagnostic. "
        "Read each completed check beside unfinished ones. Static coverage does not establish "
        "sequential termination, clinical appropriateness or statistical operating characteristics. "
        "Nonempty candidate claims are refused; no concrete participant countermodel is fabricated."
    )
    description["result_guides"]["signals"]["estimand"] = (
        "Five supplied definition references and event strategies are declarations, not verified medical "
        "completeness. Explicit requirement rules bind event, variable, window and observed/imputed/derived "
        "mode. Read relevance, collection alignment and actual input separately with their own support "
        "and blockers. A stopped required collection is a plan mismatch; unavailable relevant data, "
        "not-required data and structural nonexistence are different states. Only adopted dependency "
        "rules establish dependency conflicts. Strategy names generate no requirements. Estimation "
        "always remains not_computed. Empty requirements/dependencies are inspection."
    )
