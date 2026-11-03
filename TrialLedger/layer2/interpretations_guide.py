"""Discovery for explicit rival readings and their conditional clinical consequences."""

from __future__ import annotations

import json

from TrialLedger.layer2 import assertions as a

INPUTS = {
    "interpretations": {
        "required": ("study_ref", "fixed", "interpretations", "queries"),
        "fields": {
            "study_ref": "nonempty study/version identity; source truth is not certified by this label",
            "fixed": "interpretation_floor object: accepted scoped assertions and independent signals",
            "bindings": "optional array of source-bound population/definition bindings",
            "interpretations": "nonempty array of separate hypothesis frames; never conjoined with rivals",
            "queries": "nonempty array of distinct named tagged propositions",
            "context": "optional existing cohort/arm/phase context",
            "bound": "optional integer assignment bound 1..65536 per solver decision",
            "selected": "optional interpretation id chosen by the user; cannot admit a refuted frame",
        },
    },
    "interpretation_floor": {
        "required": (),
        "fields": {
            "assertions": "optional tagged ScopedAssertion array; defaults to empty",
            "signals": "optional existing signal array; defaults to empty",
        },
    },
    "interpretation": {
        "required": ("id", "label", "origin", "basis"),
        "fields": {
            "id": "distinct nonempty hypothesis id",
            "label": "clinical reading or trial-design option in ordinary language",
            "origin": "assistant, user or source; a source-attributed reading is not certified source truth",
            "basis": "nonempty array of exact source/version or declared hypothetical-premise references",
            "assumptions": "optional tagged ScopedAssertion array, assumed only within this frame",
            "signals": "optional local signal array; original support remains visible",
            "signal_claims": "optional signal/claim array; claims against each signal are checked jointly",
            "binding_uses": "optional binding/signal/scope array; matching titles or counts are insufficient",
        },
    },
    "interpretation_query": {
        "required": ("id", "body"),
        "fields": {"id": "distinct nonempty question id", "body": "tagged participant proposition"},
    },
    "interpretation_binding": {
        "required": (
            "id",
            "kind",
            "relation",
            "subjects",
            "scope",
            "sources",
            "status",
            "resolution",
            "basis",
        ),
        "fields": {
            "id": "distinct binding identity",
            "kind": "population or definition",
            "relation": "population: subset_of/same_universe/partition_of; definition: adopts",
            "subjects": "explicit ordered references consumed by the target operator",
            "scope": "study, population, arm, time and version; exact declared identities",
            "sources": "nonempty ref/version/address objects, each with optional source digest",
            "status": "known, interpolated or proposed; confirmation does not promote standing",
            "resolution": "resolved, partially_resolved, unresolved or conflicting",
            "basis": "nonempty source or premise references for this binding",
        },
    },
    "interpretation_binding_use": {
        "required": ("binding", "signal", "scope"),
        "fields": {
            "binding": "existing binding id",
            "signal": "existing fixed or local signal id",
            "scope": "declared application scope checked against the binding and target signal",
        },
    },
}


def quantity(key: str, comparison: str, number: int, unit: str) -> dict:
    """Encode a declared measurement without assigning clinical meaning from its name."""
    body = a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", key),
        a.Value("quantity", comparison, number=number, unit=unit),
    )
    return json.loads(a.canonical(body))


def premise(identity: str, body: dict, *, status: str = "proposed") -> dict:
    """An attributed invented premise; proposed hypotheses remain proposed in the input."""
    proposition = a.from_canonical(json.dumps(body))
    if not isinstance(proposition, a.PROPOSITIONS):
        raise ValueError("interpretation_example_proposition_required")
    item = a.ScopedAssertion(
        identity,
        "invented:trial-design-session-not-registry-evidence",
        "required",
        proposition,
        rule=a.Rule("invented-session-premise", "1", warrants=("invented:explicit-teaching-premise",)),
        status=status,
        resolution="resolved",
    )
    return json.loads(a.canonical(item))


def frame(identity: str, label: str, assumptions: list[dict]) -> dict:
    """One inspectable rival, with no claim that the supplied family is exhaustive."""
    return {
        "id": identity,
        "label": label,
        "origin": "assistant",
        "basis": ["invented:hypothesis-to-discuss-not-an-established-protocol"],
        "assumptions": assumptions,
        "signals": [],
        "signal_claims": [],
        "binding_uses": [],
    }


def example() -> dict:
    """Invented adult NSCLC design choices; no real trial criterion is asserted."""
    return {
        "operation": "interpretations",
        "study_ref": "invented:adult-NSCLC-draft:v1",
        "fixed": {
            "assertions": [
                premise("draft-adults", quantity("age", "ge", 18, "Years"), status="known"),
                premise("draft-PS-min", quantity("ECOG", "ge", 0, "ECOG"), status="known"),
            ],
            "signals": [],
        },
        "bindings": [],
        "interpretations": [
            frame(
                "PS0-2", "Adults with ECOG 0–2", [premise("PS-upper-2", quantity("ECOG", "le", 2, "ECOG"))]
            ),
            frame(
                "PS0-3", "Adults with ECOG 0–3", [premise("PS-upper-3", quantity("ECOG", "le", 3, "ECOG"))]
            ),
            frame(
                "under-18",
                "Every participant is under 18",
                [premise("children", quantity("age", "lt", 18, "Years"))],
            ),
        ],
        "queries": [
            {"id": "adult", "body": quantity("age", "ge", 18, "Years")},
            {"id": "PS3", "body": quantity("ECOG", "eq", 3, "ECOG")},
        ],
    }


def extend(description: dict) -> None:
    """Register the operation without using a hypothesis as an accepted source premise."""
    description["availability"]["built"].append(
        "competing interpretation frames with conditional warrants and source-bound applications"
    )
    description["use_cases"].append(
        {
            "question": "What follows under each reading, and which reading violates fixed evidence?",
            "operation": "interpretations",
            "read": "fixed, interpretations, consequences and selection",
            "meaning": "Explore rival readings without making their assumptions source facts.",
        }
    )
    description["question_vocabulary"].append(
        {
            "words": "could this wording mean either option; what would each option permit",
            "computed_by": "interpretations over an explicit fixed floor and isolated hypotheses",
            "report": "conditional consequences, refutation warrants, alternatives and open bindings",
        }
    )
    description["examples"]["interpretations"] = example()
    description["example_results"]["interpretations"] = (
        "Invented case: PS0-2 and PS0-3 remain; under-18 conflicts with the fixed adult requirement. "
        "PS3 is refuted under PS0-2 and allowed but not required under PS0-3; the choice stays open. "
        "Proposed input assumptions are retained, and surviving hypotheses do not become registry facts."
    )
    description["answer_guide"]["interpretations"] = {
        "compatible": [
            "your_call",
            "This reading fits the represented constraints; its truth is not established.",
        ],
        "refuted": ["settled", "Name the fixed constraint and hypothesis that cannot hold together."],
        "incoherent": ["translation", "The hypothesis contradicts itself; repair its stated assumptions."],
        "unresolved": [
            "by_blocker",
            "Retain conditional values; settle the particular binding, missing input or computation limit.",
        ],
        "floor_conflict": ["something_wrong", "The fixed premises conflict; no frame supplies closure."],
        "conditional": [
            "your_call",
            "Exact under this reading; retain assumptions separately from fixed evidence and user choices.",
        ],
        "selection": [
            "your_call",
            "Record the user's selected reading; rerun after changes without promoting source standing.",
        ],
    }
    description["result_guides"]["interpretations"] = {
        "fields": {
            "study_ref": "supplied study/version identity",
            "fixed": "fixed-floor consistency, independent query answers and structural signal values",
            "bindings": "original population and definition premises; no inferred identities",
            "interpretations": "original premises, binding checks, conditional values, queries and warrants",
            "remaining": "compatible and unresolved hypotheses retained as possibilities",
            "refuted": "hypotheses incompatible with supported fixed constraints",
            "incoherent": "internally inconsistent hypotheses",
            "unresolved": "hypotheses whose complete compatibility is not established",
            "consequences": "query consequences across the declared family, never assumed exhaustive",
            "selection": "explicit user selection and its admissibility; selection does not certify truth",
            "limits": "representation, hypothetical-premise and source-preservation boundaries",
        },
        "standing": (
            "Ordinary entailment still refuses proposed premises. Only explicit hypothesis frames assume "
            "them locally; originals and conditional warrants remain visible."
        ),
        "fixed_floor": (
            "Layer-one evidence and exact direct rules bound the space. Layer-two hypothesis survival "
            "does not identify a complete protocol, even with one declared survivor."
        ),
        "binding": (
            "Population correspondence and adopted definitions retain sources, scope, editions and standing. "
            "A mismatched or unknown application is unresolved, not a clinical refutation."
        ),
        "clinical_use": (
            "Keep fixed facts, consequences under each reading, and the remaining user choice together on "
            "the decision list. Ask the consequential distinguishing question, not for arithmetic approval."
        ),
        "roles": (
            "Preserve scheduled versus actual events, source versus new-draft choices, observed versus "
            "imputed measurements, and eligibility versus analysis membership."
        ),
    }
