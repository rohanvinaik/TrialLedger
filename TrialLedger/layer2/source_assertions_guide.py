"""Public discovery for exact source anchors and separately proposed clinical readings."""

from __future__ import annotations

from TrialLedger import warrants
from TrialLedger.layer2.interpretations_guide import frame, premise, quantity

INPUTS = {
    "source_assertions": {
        "required": ("study",),
        "fields": {
            "study": "one complete raw NIH study object; retained unchanged, not landscape.json's projection",
            "expected_digest": "optional digest of that exact study; stale content is a translation refusal",
            "anchors": "optional source_anchor array; exact typed values and optional Unicode text spans",
            "interpretations": "optional source_interpretation array; rivals stay isolated and proposed",
            "bindings": "optional source_binding array; correspondence remains a proposed premise",
            "queries": "optional named tagged propositions; empty means inspection only, with analyses []",
            "context": "optional existing cohort/arm/phase context; never inferred from text",
            "bound": "optional integer assignment bound 1..65536 per solver decision",
            "selected": "optional user-selected frame; selection cannot promote its source standing",
        },
    },
    "source_anchor": {
        "required": ("id", "address", "digest", "expected"),
        "fields": {
            "id": "distinct nonempty anchor identity",
            "address": "exact RFC 6901 JSON pointer into the supplied raw study",
            "digest": "current warrants.study_digest(study), binding the anchor to the complete input",
            "expected": "exact JSON value at address, including its JSON type; no coercion",
            "span": "optional source_span, permitted only for a string-valued address",
        },
    },
    "source_span": {
        "required": ("start", "end", "text"),
        "fields": {
            "start": "zero-based inclusive Unicode code-point offset in the original string",
            "end": "exclusive Unicode code-point offset; exact original[start:end] must equal text",
            "text": "exact unchanged passage; offsets are not UTF-8 bytes or normalized text",
        },
    },
    "source_template": {
        "required": ("$source", "as"),
        "fields": {
            "$source": "existing anchor id; recursively substitutes that anchor's value or exact span text",
            "as": "integer, text or json; integers allow no decimals, commas or units",
        },
    },
    "source_interpretation": {
        "required": ("id", "label", "origin", "basis", "anchors"),
        "fields": {
            "id": "distinct frame id, as in interpretation",
            "label": "clinical reading or design option, as in interpretation",
            "origin": "assistant, user or source; attribution does not certify the reading",
            "basis": "declared rationale; compiler adds the actual source-anchor provenance",
            "anchors": "nonempty existing anchor ids; every template dependency must be declared here",
            "assumptions": "optional tagged ScopedAssertion templates, always forced to proposed",
            "signals": "optional local signal templates; every support is forced to proposed",
            "signal_claims": "optional existing signal claims, evaluated jointly within this frame",
            "binding_uses": "optional existing binding-use array; exact scope and edition remain material",
        },
    },
    "source_binding": {
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
            "anchors",
        ),
        "fields": {
            "id": "existing interpretation_binding identity",
            "kind": "population or definition",
            "relation": "subset_of, same_universe or partition_of; definition uses adopts",
            "subjects": "explicit ordered references consumed by the target operator",
            "scope": "study, population, arm, time and version; content digest is not a protocol edition",
            "sources": "declared source objects; compiler retains actual anchor provenance",
            "status": "always forced to proposed; exact quotation does not prove population correspondence",
            "resolution": "existing resolution; unresolved or mismatched applications remain unresolved",
            "basis": "declared rationale plus actual anchored source references",
            "anchors": "nonempty existing anchor ids; every binding template dependency must be declared",
        },
    },
}


def example() -> dict:
    """Invented source with exact adult-age structure and two explicitly hypothetical readings."""
    passage = "Participants must be adults. Performance status is not specified here."
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"minimumAge": "18 Years", "eligibilityCriteria": passage},
        }
    }
    digest = warrants.study_digest(study)
    adults = frame(
        "adults",
        "Read this as requiring adults",
        [premise("adult-reading", quantity("age", "ge", 18, "Years"))],
    )
    children = frame(
        "under-18",
        "Hypothetically require everyone to be under 18",
        [premise("child-reading", quantity("age", "lt", 18, "Years"))],
    )
    for reading in (adults, children):
        reading["anchors"] = ["eligibility-passage"]
        reading["basis"] = ["invented:teaching-reading-not-established-protocol"]
    return {
        "operation": "source_assertions",
        "study": study,
        "expected_digest": digest,
        "anchors": [
            {
                "id": "eligibility-passage",
                "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
                "digest": digest,
                "expected": passage,
                "span": {"start": 0, "end": len(passage), "text": passage},
            }
        ],
        "interpretations": [adults, children],
        "queries": [{"id": "adult", "body": quantity("age", "ge", 18, "Years")}],
    }


def extend(description: dict) -> None:
    """Describe the bridge without running a compiler or solver during discovery."""
    description["availability"]["built"].append(
        "raw-study source anchors and exact age facts feeding isolated proposed interpretation frames"
    )
    description["use_cases"].append(
        {
            "question": "What does this source establish, and what follows under each proposed reading?",
            "operation": "source_assertions",
            "read": "source, anchors, fixed, coverage, requests and analyses",
            "meaning": "Keep source-preserving direct facts apart from conditional clinical interpretations.",
        }
    )
    description["question_vocabulary"].append(
        {
            "words": "use this record; anchor this passage; compare possible readings",
            "computed_by": "source_assertions compilation followed by existing entailment or interpretations",
            "report": "exact source, direct rules, proposed frames, conditional consequences and gaps",
        }
    )
    description["examples"]["source_assertions"] = example()
    description["example_results"]["source_assertions"] = (
        "Invented source: exact structured minimumAge establishes age >=18 Years under the registry's "
        "general eligibility field rule. The under-18 hypothesis conflicts with that floor. The adult "
        "hypothesis remains proposed. Neither the quotation nor this check certifies a complete protocol."
    )
    description["answer_guide"]["source_assertions"] = {
        "fixed": ["settled", "Name the exact structured source field and its direct rule; retain its scope."],
        "anchor": [
            "source",
            "The quotation matches this snapshot; its clinical meaning is a separate premise.",
        ],
        "proposed": [
            "your_call",
            "Show each reading's conditional consequences and ask the material distinguishing question.",
        ],
        "coverage_gap": [
            "not_knowable_here",
            "Uncompiled content is retained; missing compilation is not clinical absence.",
        ],
        "refused": [
            "translation",
            "Repair the named missing, stale, mistyped or misaligned source anchor and rerun.",
        ],
        "binding": [
            "your_call",
            "Population, time and edition correspondence remain explicit proposed premises.",
        ],
    }
    description["result_guides"]["source_assertions"] = {
        "fields": {
            "source": "input-content identity, exact digest and version metadata; input stays unchanged",
            "anchors": "validated exact source values and optional unchanged Unicode spans",
            "fixed": "only source-defined direct facts; currently exact structured minimum/maximum age",
            "interpretations": "hydrated isolated frames with assumptions and signal support forced proposed",
            "bindings": "source-bound correspondence premises forced proposed",
            "coverage": "compiled locations and retained uncompiled content/gaps; not a complete text reader",
            "submitted": "the supplied representations retained for inspection",
            "requests": "public reasoning requests generated from the fixed floor and proposed frames",
            "analyses": "complete downstream run envelopes in request order; empty for inspection-only input",
            "limits": "source preservation, direct rules, proposed standing and compilation coverage",
        },
        "standing": "Exact anchors establish source alignment, never a clinical reading's intended meaning.",
        "source_identity": "The digest identifies content, not a protocol edition or current registry truth.",
        "direct_rules": "Exact NIH integer age grammar is supported; unsupported syntax is not normalized.",
        "conditional": "A sole survivor remains conditional on the declared family and its bindings.",
        "clinical_use": "Keep source evidence, conditional consequences and choices on the decision list.",
    }
