"""Discovery and an invented, runnable baseline-witness design conversation."""

from __future__ import annotations

import json

from TrialLedger.layer2 import assertions as a

INPUTS = {
    "design_bounds": {
        "required": ("study_ref", "candidates", "observations", "query"),
        "fields": {
            "study_ref": "nonempty study/version reference; all inputs concern this study",
            "candidates": "nonempty candidate array; declared alternatives, not all real protocols",
            "observations": "nonempty observation array; counts never sum across observations",
            "query": "tagged participant proposition: must it hold under every remaining candidate design?",
            "context": "context for the consequence query; default open cohort/phase/arm",
            "bound": "integer 1..65536 per entailment decision; default 65536",
        },
    },
    "candidate": {
        "required": ("id", "assertions"),
        "fields": {"id": "distinct nonempty string", "assertions": "array of tagged ScopedAssertion objects"},
    },
    "observation": {
        "required": (
            "id",
            "count",
            "denominator",
            "population",
            "body",
            "context",
            "status",
            "basis",
            "bridge",
        ),
        "fields": {
            "id": "distinct nonempty string",
            "count": "nonnegative integer <= denominator; count of participants satisfying body",
            "denominator": "positive integer for this population/group; never an event count",
            "population": "nonempty reference identifying the baseline population and local group",
            "body": "tagged participant proposition preserving scale, qualifiers and assessment time",
            "context": "entry context bound to the observed population; no automatic cross-module group join",
            "status": "known, interpolated or proposed; the observation's standing",
            "basis": "nonempty array of exact source/version or premise references",
            "bridge": "bridge object: caller binds observed population, predicate and time to eligibility",
        },
    },
    "bridge": {
        "required": ("status", "resolution", "max_exceptions", "basis"),
        "fields": {
            "status": "known, interpolated or proposed; confirmation never upgrades a default",
            "resolution": "resolved, partially_resolved, unresolved or conflicting",
            "max_exceptions": "integer 0..denominator; maximum participants not serving as witnesses",
            "basis": "nonempty references warranting population, measurement, time and exception bound",
        },
    },
}

ANSWERS = {
    "ruled_out": [
        "settled",
        "Candidate excludes witnesses beyond its exception allowance; report its status and proofs.",
    ],
    "not_ruled_out": [
        "your_call",
        "Candidate is not eliminated by these observations; its actual use remains unestablished.",
    ],
    "unresolved": [
        "by_blocker",
        "Use support_guide and solver blockers: confirmation is your call; binding repair is translation.",
    ],
    "inconsistent": ["something_wrong", "Candidate criteria contradict each other; name their proof ids."],
    "CONFLICT": [
        "something_wrong",
        "No declared candidate survives; revise candidates or premises, never conclude everything.",
    ],
    "ENTAILED": [
        "settled",
        "Query holds for every remaining declared design; include eliminations' weakest standing.",
    ],
    "REFUTED": [
        "settled",
        "Query is excluded by every remaining declared design; include eliminations' weakest standing.",
    ],
    "UNDETERMINED": [
        "by_blocker",
        "Disagreement is your call; inspect each query decision for translation or computation blockers.",
    ],
}


def example() -> dict:
    """Invented counts and rules, deliberately not an IPASS protocol reconstruction."""

    def score(comparison, number):
        return a.Literal(
            a.Subject("participant"),
            a.Predicate("measurement", "example_scale"),
            a.Value("quantity", comparison, number=number, unit="example_scale"),
        )

    def model(item):
        return json.loads(a.canonical(item))

    candidates = []
    # Removing the lower-bound candidate leaves two upper cutoffs; the exact cutoff stays open.
    for identity, comparison, number in (
        ("at_least_3", "ge", 3),
        ("at_most_2", "le", 2),
        ("at_most_3", "le", 3),
    ):
        item = a.ScopedAssertion(
            identity,
            "user:invented-candidate",
            "required",
            score(comparison, number),
            rule=a.Rule("invented-candidate", "1", warrants=("user:invented-candidate",)),
            status="known",
            resolution="resolved",
        )
        candidates.append({"id": identity, "assertions": [model(item)]})
    return {
        "operation": "design_bounds",
        "study_ref": "invented:study-version-not-registry-evidence",
        "candidates": candidates,
        "observations": [
            {
                "id": "score_2",
                "count": 12,
                "denominator": 100,
                "population": "invented:baseline-total",
                "body": model(score("eq", 2)),
                "context": {},
                "status": "known",
                "basis": ["invented:baseline-cell"],
                "bridge": {
                    "status": "interpolated",
                    "resolution": "resolved",
                    "max_exceptions": 0,
                    "basis": ["user:invented-assumption-of-aligned-eligibility-witnesses"],
                },
            }
        ],
        "query": model(score("le", 3)),
    }


def extend(description: dict) -> None:
    """Join discoverable input, worked reasoning, result categories and decision-list consumers."""
    description["availability"]["built"].append("baseline witness bounds over declared candidate designs")
    description["question_vocabulary"].append(
        {
            "words": "what does baseline participation establish about missing eligibility restrictions",
            "computed_by": "design_bounds over declared candidates and explicit eligibility bridges",
            "report": "eliminated designs, bridge standing, alternatives and conditional consequences",
        }
    )
    description["use_cases"].append(
        {
            "question": "What can baseline participants rule out about missing eligibility restrictions?",
            "operation": "design_bounds",
            "read": "candidates, remaining and consequence",
            "meaning": "Conditional bounds from explicit bridges; observed maxima do not establish cutoffs.",
        }
    )
    description["examples"]["design_bounds"] = example()
    description["example_results"]["design_bounds"] = (
        "Invented demonstration: at_least_3 ruled_out; at_most_2 and at_most_3 remain; "
        "query <=3 becomes ENTAILED/interpolated. Exact upper cutoff stays open."
    )
    description["answer_guide"]["design_bounds"] = {key: list(value) for key, value in ANSWERS.items()}
    description["result_guides"]["design_bounds"] = {
        "fields": {
            "basis": "conditional premises",
            "study_ref": "supplied study/version",
            "premises": "unchanged request",
            "candidates": "each candidate's state, witness proofs and query decision",
            "remaining": "not eliminated ids",
            "consequence": "common query result and weakest standing",
            "limits": "declared-family and source-binding boundary",
        },
        "standing": (
            "Observation and bridge keep separate origins. A default in an elimination keeps its dependent "
            "consequence interpolated."
        ),
        "counts": (
            "Count beyond max_exceptions supplies a witness. Zero never excludes. Overlapping observations "
            "never sum or vote."
        ),
        "binding": (
            "Confirm population, participant-count interpretation, scale, assessment time and exception "
            "allowance before accepting the bridge. Unknown bindings stay proposed/unresolved."
        ),
        "scope": (
            "study_ref binds this analysis. Context and proposition preserve cohort/arm/phase/time; "
            "WHO PS never becomes ECOG without a warranted explicit mapping."
        ),
        "reuse": (
            "Put eliminations and open cutoffs on the decision list; revise and rerun. Never put derived "
            "bounds into source-text statement-frequency inputs."
        ),
        "support_guide": {
            "witness": ["settled", "At least one eligible witness under the bridge; retain its status."],
            "no_witness": ["not_knowable_here", "Count does not exceed exceptions; no exclusion follows."],
            "proposed_refused": ["your_call", "Confirm the proposed observation or bridge reading."],
            "binding_unresolved": ["translation", "Resolve population, scale, time or bridge conflicts."],
        },
        "solver_blockers": description["answer_guide"]["entailment"]["blockers"],
    }
