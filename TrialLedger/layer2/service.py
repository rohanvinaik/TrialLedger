"""One JSON boundary around the rescued symbolic operations.

All conclusions are conditional on explicitly supplied typed premises. Supplying JSON
does not make an agent's interpretation a registry fact. Raw registry records and free
text are refused here; source-to-assertion compilation is a separate, unfinished step.
"""

from __future__ import annotations

import dataclasses
import json
from copy import deepcopy
from typing import Any

from TrialLedger.layer2 import assertions, coherence, entail, expectations, guide, nearmiss, profile

OPERATIONS = ("describe", "entailment", "coordinates", "corpus")
MAX_ITEMS = 1000
BASIS = "Conditional on the supplied typed premises; their source meaning is not certified by this operation."
# The same closed field sets drive request validation and the agent-facing description.
INPUTS = {
    "describe": {"required": (), "fields": {}},
    "entailment": {
        "required": ("assertions", "query"),
        "fields": {
            "assertions": "array of tagged ScopedAssertion objects",
            "query": "tagged Literal, AllOf, AnyOf, Not or Opaque object",
            "context": "context object; omitted means open cohort/phase/arm",
            "bound": f"integer from 1 to {entail.MAX_ASSIGNMENTS}; default {entail.MAX_ASSIGNMENTS}",
        },
    },
    "coordinates": {
        "required": ("domain", "evidence"),
        "fields": {"domain": "string: nsclc", "evidence": "array of evidence objects"},
    },
    "corpus": {
        "required": ("trials",),
        "fields": {
            "trials": "array of trial objects with distinct ids",
            "cells": "array of [setting string, class string] pairs; default []",
            "expectations": "array of expectation objects; default []",
        },
    },
    "context": {
        "required": (),
        "fields": {
            "cohort": "nonempty string or null",
            "phase": "nonempty string or null",
            "arm": "nonempty string or null",
        },
    },
    "evidence": {
        "required": ("section", "concept", "values", "scope", "ref"),
        "fields": {
            "section": "string from sections",
            "concept": "string from coordinate_values",
            "values": "array of that concept's allowed strings",
            "scope": "string from scopes",
            "ref": "nonempty premise/source reference string",
        },
    },
    "trial": {
        "required": ("id", "sponsor", "stratum", "elements", "basis"),
        "fields": {
            "id": "nonempty string",
            "sponsor": "nonempty string",
            "stratum": "nonempty declared comparison-set string",
            "elements": "array of typed element strings",
            "basis": "nonempty array of nonempty premise/source references",
            "classes": "array of class strings; default []",
            "class_unresolved": "boolean; default true",
            "typed": "boolean; default false; required true when eligibility elements are supplied",
            "eligibility_content": "string: present or empty; default present",
            "coverage": "coverage object; default {}",
            "representation": "object of nonempty keys to string values; default {}",
            "predicates": "object of nonempty keys to string values; default {}",
            "start_year": "string; default empty",
            "setting_domain": "array of setting strings; required nonempty if cells are requested",
        },
    },
    "coverage": {
        "required": (),
        "fields": {"inclusion": "string from coverage_states", "exclusion": "string from coverage_states"},
    },
    "expectation": {
        "required": ("id", "observations", "cell", "support", "basis"),
        "fields": {
            "id": "nonempty string",
            "observations": "array of [cell string, observation-state string] pairs",
            "cell": "nonempty string",
            "support": "positive integer",
            "basis": "nonempty array of nonempty premise/source references",
        },
    },
}
SECTIONS = ("inclusion", "exclusion", "unsectioned")
SCOPES = ("advanced", "unspecified", "")
COVERAGE_STATES = ("abbreviation_stated", "completeness_stated", "unspecified")
COORDINATE_VALUES = {
    "prior_lines": coherence.PRIOR_LINES,
    "stage": ("I", "II", "III", "IV"),
    "extent": ("metastatic", "recurrent", "advanced", "locally_advanced"),
    "resection": ("resected", "resectable"),
    "setting_word": (*coherence.SETTINGS, "consolidation"),
    "prior_agent": ("radiotherapy",),
    **{f"biomarker:{gene}": coherence.STATES for gene in coherence.SELECTED_GENES},
}
FREQUENCY_FIELDS = (
    "stratum",
    "element",
    "stating",
    "absence_established",
    "unresolved_empty",
    "unresolved_untyped",
    "unresolved_abbreviated",
    "unresolved_unspecified",
    "unresolved",
    "trials",
    "statement_rate",
    "lower",
    "upper",
    "surprisal_bits",
    "sponsors",
    "tier",
    "estimand",
)
ASSOCIATION_FIELDS = (
    "stratum",
    "class",
    "element",
    "inside_stating",
    "inside_trials",
    "outside_stating",
    "outside_trials",
    "inside_rate",
    "outside_rate",
    "difference",
    "least_favourable_difference",
    "sponsors",
    "unresolved_class_trials",
    "inside_abbreviated",
    "outside_abbreviated",
    "status",
)
PAIR_FIELDS = (
    "a",
    "b",
    "difference",
    "value_a",
    "value_b",
    "sponsor_a",
    "sponsor_b",
    "year_a",
    "year_b",
    "other_predicates_agreeing",
)


class RequestError(ValueError):
    """A named problem with the symbolic request, never a negative clinical finding."""


def _object(value: Any, allowed: set[str], required: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RequestError(f"not_an_object:{where}")
    if set(value) - allowed:
        raise RequestError(f"unknown_field:{where}")
    if required - set(value):
        raise RequestError(f"missing_field:{where}")
    return value


def _input(value: Any, shape: str, where: str) -> dict[str, Any]:
    description = INPUTS[shape]
    fields = set(description["fields"])
    if shape in OPERATIONS:
        fields.add("operation")
    return _object(value, fields, set(description["required"]), where)


def _text(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        raise RequestError(f"not_text:{where}")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise RequestError(f"not_a_list:{where}")
    if len(value) > MAX_ITEMS:
        raise RequestError(f"resource_bound:{where}")
    return value


def _texts(value: Any, where: str) -> list[str]:
    return [_text(item, where) for item in _list(value, where)]


def _model(value: Any) -> object:
    if not isinstance(value, dict):
        raise RequestError("model_object_required")
    return assertions.from_canonical(json.dumps(value, allow_nan=False))


def _entailment(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "entailment", "request")
    given = []
    for value in _list(request["assertions"], "assertions"):
        item = _model(value)
        if not isinstance(item, assertions.ScopedAssertion):
            raise RequestError("assertions_required")
        given.append(item)
    context = _input(request.get("context", {}), "context", "context")
    for key, value in context.items():
        if value is not None:
            _text(value, key)
    bound = request.get("bound", entail.MAX_ASSIGNMENTS)
    if type(bound) is not int or not 1 <= bound <= entail.MAX_ASSIGNMENTS:
        raise RequestError("invalid_resource_bound")
    decision = entail.decide(tuple(given), _model(request["query"]), entail.Context(**context), bound)
    return {"basis": BASIS, "decision": dataclasses.asdict(decision), "premises": request["assertions"]}


def _coordinates(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "coordinates", "request")
    if request["domain"] != "nsclc":
        raise RequestError("unsupported_domain")
    given = _list(request["evidence"], "evidence")
    evidence = []
    for index, raw in enumerate(given):
        item = _input(raw, "evidence", f"evidence:{index}")
        section, concept = item["section"], item["concept"]
        if section not in SECTIONS:
            raise RequestError(f"unsupported_section:{index}")
        if not isinstance(concept, str) or concept not in COORDINATE_VALUES:
            raise RequestError(f"unsupported_concept:{index}")
        values = _texts(item["values"], f"evidence:{index}:values")
        if not set(values) <= set(COORDINATE_VALUES[concept]):
            raise RequestError(f"unsupported_value:{index}")
        scope = _text(item["scope"], f"evidence:{index}:scope", empty=True)
        if scope not in SCOPES:
            raise RequestError(f"unsupported_scope:{index}")
        evidence.append((section, concept, tuple(values), scope, _text(item["ref"], f"evidence:{index}:ref")))
    coordinates = coherence.resolve(evidence)
    return {
        "basis": BASIS,
        "domain": "nsclc",
        "premises": given,
        "coordinates": coordinates,
        "relations": [dataclasses.asdict(item) for item in coherence.RELATIONS],
    }


def _trial(raw: Any, index: int) -> dict[str, Any]:
    item = _input(raw, "trial", f"trial:{index}")
    for key in ("id", "sponsor", "stratum"):
        _text(item[key], f"trial:{index}:{key}")
    _texts(item["basis"], f"trial:{index}:basis")
    if not item["basis"]:
        raise RequestError(f"missing_basis:{index}")
    item = dict(item)
    for key in ("elements", "classes", "setting_domain"):
        item[key] = _texts(item.get(key, []), f"trial:{index}:{key}")
    for key, default in (("typed", False), ("class_unresolved", True)):
        item[key] = item.get(key, default)
        if type(item[key]) is not bool:
            raise RequestError(f"not_boolean:trial:{index}:{key}")
    if (
        any(element.split(":", 1)[0] in profile.ELIGIBILITY_SECTIONS for element in item["elements"])
        and not item["typed"]
    ):
        raise RequestError(f"elements_without_typed_premises:{index}")
    if not item["class_unresolved"] and not item["classes"]:
        raise RequestError(f"classes_not_established:{index}")
    item["eligibility_content"] = item.get("eligibility_content", "present")
    if item["eligibility_content"] not in ("present", "empty"):
        raise RequestError(f"unsupported_content:{index}")
    item["coverage"] = _input(item.get("coverage", {}), "coverage", "coverage")
    if any(value not in COVERAGE_STATES for value in item["coverage"].values()):
        raise RequestError(f"unsupported_coverage:{index}")
    for key in ("representation", "predicates"):
        value = item.get(key, {})
        if not isinstance(value, dict) or not all(
            isinstance(k, str) and k and isinstance(v, str) for k, v in value.items()
        ):
            raise RequestError(f"not_text_mapping:{index}:{key}")
        item[key] = value
    item["start_year"] = _text(item.get("start_year", ""), f"trial:{index}:start_year", empty=True)
    return item


def _corpus(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "corpus", "request")
    given = _list(request["trials"], "trials")
    trials = [_trial(raw, index) for index, raw in enumerate(given)]
    ids = [item["id"] for item in trials]
    if len(set(ids)) != len(ids):
        raise RequestError("duplicate_trial_id")
    typed = [
        (
            t["id"],
            t["sponsor"],
            t["stratum"],
            t["typed"],
            t["elements"],
            t["classes"],
            t["class_unresolved"],
            t["eligibility_content"],
            tuple(t["coverage"].items()),
        )
        for t in trials
    ]
    pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]
    cells = []
    for raw in _list(request.get("cells", []), "cells"):
        held = _texts(raw, "cell")
        if len(held) != 2:
            raise RequestError("cell_needs_setting_and_class")
        cells.append((held[0], held[1]))
    if cells and any(not t["setting_domain"] for t in trials):
        raise RequestError("occupancy_requires_nonempty_setting_domains")
    occupancy_trials = [
        (t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))
        for t in trials
    ]
    observations = []
    for raw in _list(request.get("expectations", []), "expectations"):
        item = _input(raw, "expectation", "expectation")
        _text(item["id"], "expectation:id")
        _text(item["cell"], "expectation:cell")
        if not _texts(item["basis"], "expectation:basis"):
            raise RequestError("missing_expectation_basis")
        if type(item["support"]) is not int or item["support"] < 1:
            raise RequestError("invalid_expectation_support")
        rows = []
        for row in _list(item["observations"], "observations"):
            pair = _texts(row, "observation")
            if len(pair) != 2 or pair[1] not in expectations.STATUSES:
                raise RequestError("invalid_observation")
            rows.append((pair[0], pair[1]))
        observations.append(
            {
                "id": item["id"],
                "basis": item["basis"],
                "rarity": expectations.conditional_rarity(rows, item["cell"], item["support"]),
            }
        )
    return {
        "basis": BASIS,
        "premises": given,
        "frequency": [dict(zip(FREQUENCY_FIELDS, row, strict=True)) for row in profile.frequency_rows(typed)],
        "associations": [
            dict(zip(ASSOCIATION_FIELDS, row, strict=True)) for row in profile.mechanism_rows(typed)
        ],
        "near_misses": [dict(zip(PAIR_FIELDS, row, strict=True)) for row in nearmiss.near_misses(pairs)],
        "occupancy": [
            dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))
            for row in profile.occupancy_rows(cells, occupancy_trials)
        ],
        "expectations": observations,
        "limits": (
            "Statement rates and proposed associations are not clinical importance, causation, "
            "or permission to reuse protocol language."
        ),
    }


def _examples() -> dict[str, dict[str, Any]]:
    """Executable typed examples, constructed through the existing validated object model."""
    female = assertions.Literal(
        assertions.Subject("participant"),
        assertions.Predicate("demographic", "eligible_sex"),
        assertions.Value("enum", members=("female",)),
    )
    premise = assertions.ScopedAssertion(
        "population",
        "user:example-brief",
        "required",
        female,
        rule=assertions.Rule("user-choice", "1", warrants=("user:example-brief",)),
        status="known",
        resolution="resolved",
    )
    male = dataclasses.replace(female, value=assertions.Value("enum", members=("male",)))
    return {
        "entailment": {
            "operation": "entailment",
            "assertions": [json.loads(assertions.canonical(premise))],
            "query": json.loads(assertions.canonical(male)),
        },
        "coordinates": {
            "operation": "coordinates",
            "domain": "nsclc",
            "evidence": [
                {
                    "section": "inclusion",
                    "concept": "prior_lines",
                    "values": ["0"],
                    "scope": "advanced",
                    "ref": "user:example-no-prior",
                },
                {
                    "section": "inclusion",
                    "concept": "extent",
                    "values": ["advanced"],
                    "scope": "",
                    "ref": "user:example-advanced",
                },
            ],
        },
        "corpus": {
            "operation": "corpus",
            "trials": [
                {
                    "id": "example-a",
                    "sponsor": "example-sponsor-a",
                    "stratum": "user-declared-example-set",
                    "elements": ["inclusion:ecog_ps=0|1"],
                    "typed": True,
                    "basis": ["user:example-typed-premises"],
                },
                {
                    "id": "example-b",
                    "sponsor": "example-sponsor-b",
                    "stratum": "user-declared-example-set",
                    "elements": [],
                    "basis": ["user:example-typed-premises"],
                },
            ],
        },
    }


def _describe(request: dict[str, Any]) -> dict[str, Any]:
    """Describe this actual boundary, not a promise of the unfinished automated writer."""
    _input(request, "describe", "request")
    example_basis = ["user:invented-demonstration-premises-not-registry-facts"]
    comparison = {
        "operation": "corpus",
        "trials": [
            {
                "id": f"invented-class-a-{index}",
                "sponsor": f"invented-sponsor-{index}",
                "stratum": "invented-comparison-set",
                "elements": ["inclusion:example_requirement=yes"],
                "typed": True,
                "classes": ["invented-class-a"],
                "class_unresolved": False,
                "basis": example_basis,
            }
            for index in range(profile.SIGNAL_MIN_TRIALS)
        ]
        + [
            {
                "id": "invented-class-b",
                "sponsor": "invented-outside-sponsor",
                "stratum": "invented-comparison-set",
                "elements": ["inclusion:another_example_requirement=yes"],
                "typed": True,
                "classes": ["invented-class-b"],
                "class_unresolved": False,
                "basis": example_basis,
            }
        ],
    }
    matched = {
        "operation": "corpus",
        "trials": [
            {
                "id": f"invented-match-{index}",
                "sponsor": f"invented-sponsor-{index}",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "representation": {"setting": "example-setting", "drug_class": "example-class"},
                "predicates": {"example_score_limit": value, "example_other_choice": "same"},
                "start_year": str(2020 + index),
            }
            for index, value in enumerate(("0|1", "0|2"))
        ],
    }
    occupancy = {
        "operation": "corpus",
        "trials": [
            {
                "id": "invented-definite",
                "sponsor": "invented-sponsor-a",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "classes": ["invented-class"],
                "class_unresolved": False,
                "setting_domain": ["example-setting-a"],
            },
            {
                "id": "invented-possible",
                "sponsor": "invented-sponsor-b",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "setting_domain": ["example-setting-a", "example-setting-b"],
            },
        ],
        "cells": [
            [setting, "invented-class"]
            for setting in ("example-setting-a", "example-setting-b", "example-setting-c")
        ],
    }
    rarity = {
        "operation": "corpus",
        "trials": [],
        "expectations": [
            {
                "id": "invented-declared-expectation",
                "observations": [
                    ["example-cell", "present"],
                    ["example-cell", "explicitly_negated"],
                    ["example-cell", "unresolved"],
                    ["example-cell", "not_applicable"],
                ],
                "cell": "example-cell",
                "support": 2,
                "basis": example_basis,
            }
        ],
    }
    model = {}
    for name, cls in assertions.CLASSES.items():
        fields = dataclasses.fields(cls)
        model[name] = {
            "fields": {field.name: str(field.type) for field in fields},
            "required": [
                field.name
                for field in fields
                if (field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING)
                or (cls is assertions.ScopedAssertion and field.name == "rule")
            ],
        }
    return {
        "basis": BASIS,
        "clinical_use": (
            "Symbolic reasoning about trial design, operated by the assistant in conversation. The "
            "assistant translates: it restates the person's criteria and questions as typed premises, shows "
            "them back in plain words and encodes only what the person confirms. The operations reason: "
            "every answer is computed and lands in one of four categories (settled, something wrong, your "
            "call, not knowable from this evidence) with the premise that decided it. They abstain exactly "
            "where the premises do not settle a question: 'must everyone be at least 65?' against a brief "
            "requiring 18 or older is allowed but not required, neither yes nor no. Read answer_guide, "
            "question_vocabulary and worked_session before the first request."
        ),
        "answer_guide": guide.answer_guide(),
        "question_vocabulary": deepcopy(guide.QUESTION_VOCABULARY),
        "worked_session": guide.worked_session(),
        "operation_field": {"type": "string", "required": True, "values": list(OPERATIONS)},
        "input_shapes": deepcopy(INPUTS),
        "limits": {
            "maximum_list_items": MAX_ITEMS,
            "maximum_assignments": entail.MAX_ASSIGNMENTS,
            "unknown_fields": "refused",
        },
        "vocabularies": {
            "sections": SECTIONS,
            "scopes": SCOPES,
            "coordinate_values": deepcopy(COORDINATE_VALUES),
            "coverage_states": COVERAGE_STATES,
            "observation_states": expectations.STATUSES,
            "modalities": sorted(assertions.MODALITIES),
            "polarities": sorted(assertions.POLARITIES),
            "statuses": sorted(assertions.STATUSES),
            "resolutions": sorted(assertions.RESOLUTIONS),
            "subject_kinds": sorted(assertions.SUBJECT_KINDS),
            "predicate_kinds": sorted(assertions.PREDICATE_KINDS),
            "value_kinds": sorted(assertions.VALUE_KINDS),
            "comparisons_by_value_kind": {
                kind: sorted(values) for kind, values in assertions.KIND_COMPARISONS.items()
            },
            "scope_kinds": sorted(assertions.SCOPE_KINDS),
            "evidence_kinds": sorted(assertions.EVIDENCE_KINDS),
            "orientations": sorted(assertions.ORIENTATIONS),
            "anchors": sorted(assertions.ANCHOR_KINDS),
            "inclusivities": sorted(assertions.INCLUSIVITIES),
            "certainties": sorted(assertions.CERTAINTIES),
            "branch_nodes": sorted(assertions.BRANCH_NODES),
        },
        "tagged_model": {
            "encoding": (
                "An object has a class tag from this table; JSON arrays become immutable tuples. "
                "Model defaults apply to omitted optional fields, then all values are validated. "
                "Quantities need finite numbers; intervals need ordered bounds; enumerations need "
                "members fitting the comparison. A boolean literal states that its predicate holds: give "
                "no members or number (otherwise boolean_with_operand); use polarity negative or Not for "
                "'does not hold'. Units are compared as written, never converted; time scopes match only "
                "when identical."
            ),
            "classes": model,
        },
        "premise_status": {
            "known": (
                "Given or deduced relative to explicitly supplied premises; "
                "this operation does not certify their source meaning."
            ),
            "interpolated": (
                "A default remains a default; a consequence cannot become stronger than its premises."
            ),
            "proposed": "A proposal is shown separately and is not an entailment premise.",
        },
        "availability": {
            "built": [
                "scoped entailment with proof/blockers",
                "explicit NSCLC coordinate closure",
                "typed corpus calculations",
            ],
            "designed_not_integrated": [
                "automatic source-to-assertion compilation",
                "complete brief-to-warranted-protocol workflow",
            ],
        },
        "use_cases": [
            {
                "question": (
                    "Does a proposed inclusion, exclusion or other design choice follow from the premises?"
                ),
                "operation": "entailment",
                "read": "decision.result, decision.status, decision.proof and decision.blockers",
                "meaning": (
                    "A conditional logical consequence, contradiction or unresolved question; not "
                    "automatic source interpretation."
                ),
            },
            {
                "question": "Which NSCLC setting, prior-treatment and gene-selection values remain possible?",
                "operation": "coordinates",
                "read": "coordinates: known domains, interpolated domains and each separate proposal",
                "meaning": (
                    "Explicit applicable evidence narrows the space; defaults and proposals retain their "
                    "own standing."
                ),
            },
            {
                "question": "How commonly do the selected comparable records state an element?",
                "operation": "corpus",
                "read": "frequency",
                "meaning": (
                    "Statement rates, eligibility silence bounds and corpus rarity, not clinical "
                    "importance or permission to reuse wording."
                ),
            },
            {
                "question": "Is an element stated more often within a declared drug class than outside it?",
                "operation": "corpus",
                "read": "associations",
                "meaning": (
                    "A proposed statement-rate association with support and unresolved counts, not a "
                    "causal or clinical rule."
                ),
            },
            {
                "question": (
                    "Which trials match on our declared comparison features but differ in one shared "
                    "known design choice?"
                ),
                "operation": "corpus",
                "read": "near_misses",
                "meaning": (
                    "One difference under the supplied representation; other missing or unshared "
                    "predicates are not proved equal."
                ),
            },
            {
                "question": (
                    "Is a declared setting/class cell occupied, possibly occupied or empty within this "
                    "supplied corpus?"
                ),
                "operation": "corpus",
                "read": "occupancy",
                "meaning": (
                    "Unknown membership prevents an empty verdict; empty does not establish infeasible or"
                    " underserved."
                ),
            },
            {
                "question": (
                    "How unusual is a present or non-present observation of an explicitly declared "
                    "expectation?"
                ),
                "operation": "corpus",
                "read": "expectations",
                "meaning": (
                    "Conditional corpus rarity with a cell/parent/abstain result; not derivational "
                    "significance or an explanation of a deviation."
                ),
            },
        ],
        "result_guides": {
            "envelope": {
                "code": (
                    "complete means the operation ran; refused means malformed or unsupported input, "
                    "never a negative clinical finding"
                ),
                "operation": "the requested operation",
                "result": "the operation result, or null on refusal",
                "problems": "named refusal reasons; empty on completion",
            },
            "entailment": {
                "fields": {
                    "basis": BASIS,
                    "premises": "supplied tagged assertions, retained unchanged",
                    "decision": {
                        "result": list(entail.RESULTS),
                        "query": "canonical JSON string of the query; empty when it is not a proposition",
                        "status": (
                            "weakest supporting premise status for a conclusion/inconsistency; null otherwise"
                        ),
                        "proof": (
                            "assertion ids used, or considered for an undetermined query; not a "
                            "reconstructed source quote"
                        ),
                        "blockers": (
                            "named reasons, read together (answer_guide.entailment.blockers): "
                            "undecided_by_constraints, no_constraint_mentions_query, resource_bound, "
                            "query_not_proposition, and per item proposed_refused, unresolved_rule, "
                            "unresolved_assertion, conflicting, open_scope, unresolved_scope, "
                            "unresolved_literal, unspecified_boundary, opaque"
                        ),
                    },
                },
                "semantics": (
                    "Required A OR B does not entail A alone. An exclusion negates the whole body. "
                    "Applicability is not itself required. Permission/definition/description alone impose"
                    " no constraint. Cohort, arm, time, subject and units stay distinct; units are not "
                    "converted here. Inconsistency never licenses entailment by explosion."
                ),
            },
            "coordinates": {
                "fields": {
                    "basis": BASIS,
                    "domain": "nsclc only; the caller declares applicability",
                    "premises": "supplied evidence objects, retained unchanged",
                    "coordinates": "setting, prior_advanced_lines and selection:<gene> for each gene",
                    "relations": (
                        "each actual rule's id, statement, basis, approval, kind, needs, lines_within, "
                        "narrows, allowed, needs_any and forbids"
                    ),
                },
                "coordinate_row": {
                    "domain": "known-level remaining values",
                    "state": "resolved, unnarrowed, unresolved or conflict (empty domain)",
                    "causes": "[coordinate, removed values, premise ref or relation id] rows",
                    "interpolated": (
                        "domain, state and additional causes after defaults; never replaces the known domain"
                    ),
                    "proposals": (
                        "each narrowing proposal separately: relation, domain, state, causes; never "
                        "combined or used as a premise"
                    ),
                },
                "semantics": (
                    "Inclusion retains and exclusion removes explicitly supplied prior-line or "
                    "gene-selection values. Other facts activate the listed NSCLC relations. Current "
                    "stored relations are defaults or proposals, not strict clinical deductions."
                ),
            },
            "corpus": {
                "fields": [
                    "basis",
                    "premises",
                    "frequency",
                    "associations",
                    "near_misses",
                    "occupancy",
                    "expectations",
                    "limits",
                ],
                "frequency": {
                    "row_fields": FREQUENCY_FIELDS,
                    "meaning": (
                        "Within each declared stratum, stating/trials is the statement rate. Eligibility "
                        "lower/upper bound full-criteria frequency; absence_established is currently "
                        "zero. Empty, untyped, abbreviated and unspecified silences remain unresolved. "
                        "Non-eligibility elements have no eligibility bounds or tier. Surprisal is "
                        "-log2(statement rate), not importance."
                    ),
                    "tier_threshold": profile.STANDARD_SHARE,
                    "tier": (
                        "met if the unrounded lower bound reaches the threshold, not_met if the upper is "
                        "below it, otherwise unresolved; this is a corpus setting, not clinical necessity"
                    ),
                },
                "associations": {
                    "row_fields": ASSOCIATION_FIELDS,
                    "meaning": (
                        "Within each stratum's typed, resolved-class trials, compare inside/outside "
                        "statement rates. Unresolved-class trials are counted separately; abbreviated "
                        "silences give the least-favourable difference. Only positive or potentially "
                        "positive comparisons are listed; no row is not proof of no relation."
                    ),
                    "support": {
                        "stating_trials": profile.SIGNAL_MIN_TRIALS,
                        "distinct_sponsors": profile.SIGNAL_MIN_SPONSORS,
                    },
                    "status": (
                        "proposed when the least-favourable comparison holds with support; below_support "
                        "when it holds without support; unresolved when abbreviated silences could "
                        "reverse it"
                    ),
                },
                "near_misses": {
                    "row_fields": PAIR_FIELDS,
                    "meaning": (
                        "Representation must be nonempty, have identical keys and known equal values. "
                        "Exactly one shared known predicate differs; other_predicates_agreeing counts the"
                        " shared known equal predicates. Sponsor and year accompany each pair. The "
                        "representation, not stratum, determines matching; no causal conclusion is made."
                    ),
                },
                "occupancy": {
                    "row_fields": ["setting", "class", "occupants", "possible", "state"],
                    "meaning": (
                        "Counts of definite and possible members for every requested cell: occupied with "
                        "a definite member, otherwise unknown with a possible member, otherwise empty. "
                        "This applies to the supplied corpus, not the whole registry."
                    ),
                },
                "expectations": {
                    "row_fields": ["id", "basis", "rarity"],
                    "rarity_positions": [
                        "source",
                        "P(present)",
                        "known_count",
                        "present_bits",
                        "non_present_bits",
                    ],
                    "meaning": (
                        "source is cell if its support is met, otherwise parent over all supplied known "
                        "observations, otherwise abstain. present, explicitly_negated and not_documented "
                        "count as known; unresolved/not_applicable do not. Non-present here includes "
                        "not_documented: it is not proof of admission or clinical absence. A "
                        "never-observed event has null bits. Observation rows are supplied independently,"
                        " not automatically derived from trials."
                    ),
                },
                "input_notes": {
                    "stratum": (
                        "caller-declared comparable population, shared by frequency and associations; the"
                        " operation does not establish clinical comparability"
                    ),
                    "elements": (
                        "exact strings; inclusion:, exclusion:, permitted: and unsectioned: prefixes "
                        "select eligibility silence accounting; other prefixes get statement rates only"
                    ),
                    "typed_and_basis": (
                        "declare supplied representation/provenance; neither the flag nor a reference "
                        "certifies source meaning"
                    ),
                    "classes": (
                        "caller-supplied class memberships; class_unresolved=true excludes the trial from"
                        " inside/outside comparisons and preserves possible occupancy"
                    ),
                    "representation_and_predicates": (
                        "caller-declared exact feature values; empty values are unknown and missing "
                        "predicates are not assumed equal"
                    ),
                },
            },
        },
        "capability_examples": {
            "associations": {
                "premise_origin": "Invented typed demonstration, not clinical evidence or a class claim.",
                "request": comparison,
                "expect": (
                    "inclusion:example_requirement=yes has an invented-class-a association with status "
                    "proposed, inside rate 1 and outside rate 0"
                ),
            },
            "near_misses": {
                "premise_origin": "Invented comparison features and design choices, not trial facts.",
                "request": matched,
                "expect": (
                    "one pair differing in example_score_limit, with one other shared known predicate "
                    "agreeing"
                ),
            },
            "occupancy": {
                "premise_origin": "Invented membership domains, not a registry search or unmet-need claim.",
                "request": occupancy,
                "expect": "example-setting-a occupied, example-setting-b unknown, example-setting-c empty",
            },
            "expectations": {
                "premise_origin": (
                    "Invented declared observation statuses, not an automatically read clinical expectation."
                ),
                "request": rarity,
                "expect": (
                    "rarity [cell, 0.5, 2, 1.0, 1.0]; unresolved and not_applicable do not enter the "
                    "denominator"
                ),
            },
        },
        "developer_building_blocks": {
            "availability": (
                "Retained Python entrypoints, not additional reason/CLI/MCP operations. Their caller must"
                " supply the stated typed inputs. None is an automatic source-to-assertion compiler."
            ),
            "entries": [
                {
                    "purpose": "Construct, validate and serialize complete scoped premises",
                    "entrypoints": [
                        "TrialLedger.layer2.assertions.ScopedAssertion",
                        "TrialLedger.layer2.assertions.canonical",
                        "TrialLedger.layer2.assertions.from_canonical",
                    ],
                    "precondition": (
                        "Preserve the proposition's referent, Boolean alternatives, modality, "
                        "applicability, cohort/time scope and actual provenance; serialization does not "
                        "certify them."
                    ),
                },
                {
                    "purpose": (
                        "Read a literal number, comparator, unit, reference expression, duration, window "
                        "or interval"
                    ),
                    "entrypoints": [
                        f"TrialLedger.layer2.semantics.parsers.read_{kind}"
                        for kind in (
                            "number",
                            "comparator",
                            "unit",
                            "reference",
                            "duration",
                            "window",
                            "interval",
                        )
                    ],
                    "precondition": (
                        "Supply the original text and expression start offset. Returns "
                        "Parse(kind,status,readings,spans,end,note), retaining alternatives/abstention. A"
                        " local literal reading does not settle clinical attachment, force or scope."
                    ),
                },
                {
                    "purpose": "Validate evidence spans and versioned concept/predicate signatures",
                    "entrypoints": [
                        "TrialLedger.layer2.semantics.contracts.atom_problems",
                        "TrialLedger.layer2.semantics.contracts.result_problems",
                        "TrialLedger.layer2.semantics.loader.load_fragments",
                        "TrialLedger.layer2.semantics.loader.compile_registry",
                        "TrialLedger.layer2.predicates.predicate_registry",
                        "TrialLedger.layer2.predicates.atom_literal",
                    ],
                    "precondition": (
                        "Supply contract atoms plus original text, or declared fragments/mappings. "
                        "atom_literal(mapping,atom) returns a candidate literal, named mapping code and "
                        "unread operands; no clinical assertion is authorised. Local registries retain "
                        "authority, edition and historical exposure limits."
                    ),
                },
                {
                    "purpose": "Resolve a source-bound indication and declared rule-pack applicability",
                    "entrypoints": [
                        "TrialLedger.layer2.indications.MeshLookup",
                        "TrialLedger.layer2.indications.resolve_indication",
                        "TrialLedger.layer2.universes.assign",
                        "TrialLedger.layer2.universes.pack_scope",
                    ],
                    "precondition": (
                        "MeshLookup(cache,year=...).lookup(label) explicitly fetches/caches fixed-year "
                        "exact MeSH identities. "
                        "resolve_indication(conditions,lookups,declared_indications,registry_mesh,own_assertions)"
                        " and assign(study,lookups=...) consume supplied source identities. No "
                        "supplied/resolved lookup means unresolved, not an automatic category."
                    ),
                },
                {
                    "purpose": "Use declared closure tables and explicit status-consumption policies",
                    "entrypoints": [
                        "TrialLedger.layer2.coherence.resolve",
                        "TrialLedger.layer2.coherence.close",
                        "TrialLedger.layer2.coherence.accepted_value",
                        "TrialLedger.layer2.coherence.level_status",
                        "TrialLedger.layer2.coherence.weakest",
                    ],
                    "precondition": (
                        "Supply typed evidence and applicable Assignment/custom Relation tables. "
                        "accepted_value(row,accepts) permits known or known+interpolated, never "
                        "proposals. reason coordinates uses the existing NSCLC table; it does not accept "
                        "a new rule table."
                    ),
                },
                {
                    "purpose": "Configure typed corpus calculations and element identities directly",
                    "entrypoints": [
                        "TrialLedger.layer2.profile.element_key",
                        "TrialLedger.layer2.profile.frequency_rows",
                        "TrialLedger.layer2.profile.mechanism_rows",
                        "TrialLedger.layer2.profile.occupancy_rows",
                        "TrialLedger.layer2.nearmiss.near_misses",
                    ],
                    "precondition": (
                        "Supply the documented typed tuple shapes. Python frequency_rows accepts "
                        "standard_share; mechanism_rows accepts min_trials/min_sponsors. reason corpus "
                        "uses the module's declared defaults, not request-supplied clinical thresholds."
                    ),
                },
                {
                    "purpose": "Classify an already established observation's deviation status",
                    "entrypoints": [
                        "TrialLedger.layer2.expectations.deviation_status",
                        "TrialLedger.layer2.expectations.conditional_rarity",
                    ],
                    "precondition": (
                        "deviation_status(status,qualifiers,audit) requires a supplied documented "
                        "observation state, count of supported qualifiers and separate audit outcome. It "
                        "returns "
                        "invalid_extraction/not_applicable/scope_unresolved/conforms/omission/explanation_supported/verified_deviation."
                        " It does not read text, discover expectations or explain an unexplained "
                        "deviation. Historical FROZEN expectation metadata is unconfirmed and is not "
                        "automatically applied by reason."
                    ),
                },
                {
                    "purpose": "Form bounded review questions from unresolved supplied findings",
                    "entrypoints": ["TrialLedger.layer2.review.flags_for"],
                    "precondition": (
                        "Supply drugs/classes, coordinate domains/causes, observation statuses, known "
                        "class choices and explicit abbreviation evidence. Returns kind, element, reason,"
                        " priority, evidence, question and options; it resolves nothing and does not "
                        "consume an answer."
                    ),
                },
                {
                    "purpose": "Evaluate source-grounded claims and record declared type coverage",
                    "entrypoints": [
                        "TrialLedger.layer2.evaluation.gold_problems",
                        "TrialLedger.layer2.evaluation.judge",
                        "TrialLedger.layer2.evaluation.recall",
                        "TrialLedger.layer2.evaluation.precision",
                        "TrialLedger.layer2.evaluation.unit_rates",
                        "TrialLedger.layer2.evaluation.complete_representation",
                        "TrialLedger.layer2.evaluation.parameter_accuracy",
                        "TrialLedger.layer2.evaluation.threshold_verdict",
                        "TrialLedger.layer2.typematrix.study_coordinates",
                        "TrialLedger.layer2.typematrix.declared_manifest",
                        "TrialLedger.layer2.typematrix.manifest_problems",
                    ],
                    "precondition": (
                        "Supply separate annotation levels, original text, versioned gold/emitted claims "
                        "and explicit review judgments. Missing denominators stay not_measured. "
                        "Threshold/coverage policy is developer data, not a clinical correctness warrant "
                        "or a limit on layer-one reporting across study types."
                    ),
                },
            ],
        },
        "examples": _examples(),
        "example_results": {
            "entailment": "REFUTED, proof population",
            "coordinates": "default advanced_first_line remains interpolated",
            "corpus": "statement rate 0.5; full-criteria interval [0.5, 1.0]",
        },
    }


def run(request: object) -> dict[str, Any]:
    """Run one existing symbolic operation, or return a named refusal for malformed/unsupported input."""
    operation = request.get("operation") if isinstance(request, dict) else None
    try:
        if not isinstance(request, dict):
            raise RequestError("request_not_an_object")
        if operation not in OPERATIONS:
            raise RequestError("unsupported_operation")
        function = {
            "describe": _describe,
            "entailment": _entailment,
            "coordinates": _coordinates,
            "corpus": _corpus,
        }[operation]
        result = function(request)
        return {"code": "complete", "operation": operation, "result": result, "problems": []}
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        return {
            "code": "refused",
            "operation": operation if isinstance(operation, str) else "",
            "result": None,
            "problems": [str(error)],
        }
