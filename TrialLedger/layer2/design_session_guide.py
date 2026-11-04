"""Session discovery draft: examples are invented teaching premises, not NIH evidence."""

from copy import deepcopy
from typing import Any


def extend(description: dict) -> None:
    """Expose closed session inputs and runnable invented snapshots alongside existing operations."""
    description["availability"]["built"].append(
        "immutable design sessions with origin-aware projections, decision lists and full revision replay"
    )
    description["input_shapes"].update(deepcopy(INPUTS))
    description["examples"]["design_session"] = deepcopy(EXAMPLE)
    description["example_results"]["design_session"] = (
        "Invented age restriction: both alternatives are feasible and distinct; design_choice, known."
    )
    categories = {
        "design_choice": "your_call",
        "options_not_distinguished": "your_call",
        "chosen_by_person": "your_call",
        "chosen_with_open_checks": "your_call",
        "settled_within_declared_alternatives": "settled",
        "evidence_question": "not_knowable_here",
        "translation_question": "translation",
        "computation_task": "not_knowable_here",
        "blocker": "something_wrong",
    }
    description["answer_guide"]["design_session"] = {
        code: [categories[code], words] for code, words in GUIDE["answer_guide"].items()
    }
    description["result_guides"]["design_session"] = {
        **deepcopy(GUIDE["result_guide"]),
        "epistemology": deepcopy(GUIDE["epistemology"]),
        "fields": {
            "schema_version": "Closed session representation version",
            "session_id": "Stable session identity",
            "revision": "Immutable revision identity",
            "session_digest": "Canonical complete snapshot fingerprint",
            "target": "Declared clinical question identity and scope",
            "sources": "Complete retained snapshots, identities and mechanically compiled fixed floors",
            "premises": "Submitted typed premises and attributed origins",
            "effective_premises": "Prepared premises after actual support and origin checks",
            "dependency_graph": "Complete replay dependencies, distinct from sufficient proof subsets",
            "analyses": "Complete prepared child requests, results, digests and dependencies",
            "projection_ledger": "Named transformations and their precise warrant boundaries",
            "decisions": "Declared questions, actual alternative checks and their local support",
            "limits": "Declared aggregate work and output bounds",
            "limit_semantics": "Operative solver/output bounds and legacy diagnostic-only fields",
            "limits_of_claim": "Represented scope and remaining epistemic boundaries",
        },
    }
    description["use_cases"].append(
        {
            "question": "Keep our design decisions and recompute what changes when we revise a premise",
            "operation": "design_session",
            "read": "result.decisions, analyses, projection_ledger; previous_fresh, diff and work",
            "meaning": "Declared questions with local warrants, origins and full replay dependencies.",
        }
    )


INPUTS = {
    "design_session": {
        "required": ["operation", "session", "previous"],
        "fields": {
            "operation": "design_session",
            "session": "session v1",
            "previous": (
                "null or exactly {session,result,expected_resu"
                "lt_digest}; prior result is /result, not enve"
                "lope"
            ),
        },
    },
    "session": {
        "required": [
            "analyses",
            "decisions",
            "id",
            "limits",
            "parent_digest",
            "premises",
            "revision",
            "schema_version",
            "sources",
            "target",
        ],
        "fields": {
            "schema_version": 1,
            "id": "stable ID",
            "revision": "nonempty distinct revision ID",
            "parent_digest": "null initially; exact previous session canonical SHA256",
            "target": "target",
            "sources": "source[]",
            "premises": "premise[]",
            "analyses": "analysis[]",
            "decisions": "decision[]",
            "limits": {
                "max_analyses": 128,
                "max_premises": 1000,
                "max_sources": 64,
                "max_decisions": 128,
                "max_expanded_items": 10000,
                "max_solver_work": 10000000,
                "max_output_bytes": 16000000,
            },
        },
    },
    "target": {
        "required": ["kind", "ref", "scope"],
        "fields": {
            "kind": ["new_trial", "historical"],
            "ref": "nonempty identity",
            "scope": (
                "exact {study,population,arm,time,version}, each nonempty string. For a historical "
                "source_study analysis, copy study from source_assertions /result/source/study_ref "
                "for this exact snapshot, not the NCT ID alone; do not reconstruct the identity."
            ),
        },
    },
    "source": {
        "required": ["id", "study", "expected_digest"],
        "fields": {
            "id": "local source ID",
            "study": "complete retained NIH v2 study",
            "expected_digest": "exact source.snapshot digest",
        },
    },
    "premise": {
        "required": ["id", "kind", "payload", "origin", "depends_on"],
        "fields": {
            "kind": [
                "assertion",
                "binding",
                "candidate",
                "coordinate_evidence",
                "corpus_trial",
                "derived_assertion",
                "observation",
                "signal",
                "source_assertion",
            ],
            "payload": "existing typed owner shape; special shapes below",
            "origin": "origin",
            "depends_on": (
                "actual claimed support premise IDs; full anal"
                "ysis inputs separately remain replay dependen"
                "cies"
            ),
        },
    },
    "origin": {
        "required": ["kind", "ref", "source", "analysis"],
        "fields": {
            "kind": ["source_rule", "source_interpretation", "user_choice", "hypothesis", "derived"],
            "ref": (
                "nonempty attributed reference; source readings require actual digest-bound URI#RFCpointer"
            ),
            "source": "source ID or null",
            "analysis": "producer analysis ID only for derived, otherwise null",
        },
    },
    "analysis": {
        "required": ["id", "operation", "target", "parameters", "uses"],
        "fields": {
            "operation": [
                "coordinates",
                "corpus",
                "design_bounds",
                "evidence_requests",
                "entailment",
                "interpretations",
                "signals",
                "source_assertions",
            ],
            "target": "exact target object",
            "parameters": (
                "existing operation fields excluding operation, fixed and owned slots. source_study "
                "owns study AND expected_digest: omit both here. Its use.premise is the local source ID; "
                "its historical target.scope.study is the exact returned snapshot study_ref."
            ),
            "uses": "use[]",
        },
    },
    "use": {
        "required": ["premise", "slot", "projection"],
        "fields": {
            "premise": "premise ID, or source ID for source_study",
            "slot": [
                "assertions",
                "bindings",
                "candidates",
                "evidence",
                "fixed_assertions",
                "fixed_signals",
                "observations",
                "signals",
                "study",
                "trials",
            ],
            "projection": ["identity", "source_study", "coordinate_evidence_identity", "corpus_trial"],
        },
    },
    "source_assertion_payload": {
        "required": ["source", "assertion"],
        "fields": {"source": "source ID", "assertion": "actual compiled source_assertions fixed-floor ID"},
    },
    "derived_assertion_payload": {
        "required": ["analysis", "query"],
        "fields": {
            "analysis": "ordinary entailment producer ID",
            "query": (
                "exact actual proposition; only admitted ENTAILED/REFUTED projects, preserving context scope"
            ),
        },
    },
    "coordinate_evidence_payload": {
        "required": ["evidence", "standing"],
        "fields": {
            "evidence": "existing NSCLC coordinate shape without standing",
            "standing": "existing {status,resolution,basis}",
        },
    },
    "corpus_trial_payload": {
        "required": ["source", "stratum", "feature_uses", "metadata"],
        "fields": {
            "source": "same exact source ID as every feature origin",
            "stratum": "explicit comparison stratum",
            "feature_uses": (
                "[{premise,projection}], projections registere"
                "d_general_age_to_corpus/documented_assertion_"
                "to_corpus"
            ),
            "metadata": (
                "only sponsor/classes/setting_domain/class_unr"
                "esolved/eligibility_content/coverage/represen"
                "tation/predicates/start_year; pending unless "
                "named feature support exists"
            ),
        },
    },
    "decision": {
        "required": ["id", "question", "target", "coverage", "alternatives", "selected"],
        "fields": {
            "coverage": ["represented_restriction", "declared_design"],
            "alternatives": "2–16 distinct queries: [{id,label,analysis,query}]",
            "selected": "null or {alternative,origin:user,basis:[nonempty references]}",
        },
    },
}

GUIDE: dict[str, Any] = {
    "purpose": (
        "Find and retain the clinical choices left aft"
        "er exact source-bound reasoning; the person c"
        "hooses comparison sets, represented features,"
        " readings and adoptions."
    ),
    "epistemology": [
        (
            "Caller labels do not verify clinical truth or"
            " confirmation. Source facts, readings, user c"
            "hoices, hypotheses and computations retain di"
            "stinct origins."
        ),
        (
            "A new-trial restriction requires explicit use"
            "r adoption. Historical source projections req"
            "uire target.scope.study equal to the actual c"
            "tg:NCT:digest study_ref."
        ),
        (
            "Only actual claimed support and effective dec"
            "iding warrants weaken a finding. Every analys"
            "is input remains a replay dependency even if "
            "absent from a minimal proof."
        ),
        (
            "Corpus signatures compare exact representatio"
            "ns, not semantically equivalent clinical crit"
            "eria; counts remain descriptive."
        ),
        (
            "Derived ordinary conclusions retain producer "
            "cohort/arm/phase context. No hypothetical int"
            "erpretation frame can become an ordinary deri"
            "ved assertion."
        ),
    ],
    "answer_guide": {
        "design_choice": (
            "At least two feasible options differ under an"
            " actual completed pairwise XOR entailment wit"
            "h identical floor/context/bound. Choose withi"
            "n the declared represented restriction, not f"
            "ull eligibility."
        ),
        "settled_within_declared_alternatives": (
            "Exactly one declared option is feasible and t"
            "he others are refuted, for historical or new-"
            "trial targets. Name the candidate family."
        ),
        "options_not_distinguished": (
            "Multiple options fit but variation is not est"
            "ablished; inspect exact equivalence, mixed-fl"
            "oor or unfinished distinguishing checks."
        ),
        "chosen_by_person": (
            "A chosen option passed its represented restri"
            "ction check; this does not certify a complete"
            " protocol."
        ),
        "chosen_with_open_checks": (
            "The person selected this, but its feasibility stays open; retain its exact gap."
        ),
        "evidence_question": ("The supplied evidence does not settle this historical answer or feasibility."),
        "translation_question": (
            "Resolve an unsupported question, reading, source/target mismatch or incomplete encoding."
        ),
        "computation_task": (
            "Not resolved within the computation limit; it is neither evidence absence nor design freedom."
        ),
        "blocker": (
            "A criterion contradiction or refuted selected"
            " option needs attention; retain the recorded "
            "choice."
        ),
    },
    "result_guide": {
        "result/analyses": ("Actual named child requests/results, full replay dependencies and digests."),
        "result/decisions": (
            "Questions, effective alternative warrants, se"
            "lections, open alternatives and budgeted actu"
            "al pairwise distinguishing requests/results."
        ),
        "previous_fresh": (
            "Both snapshots freshly replayed; stored bytes are digest checked, never a cache."
        ),
        "diff": (
            "Stable source/premise/effective-premise/analy"
            "sis/decision IDs classified new, withdrawn, c"
            "hanged or unchanged."
        ),
        "work": (
            "Cumulative child calls and conservative solver assignment reservations; expanded JSON "
            "items are diagnostic, not an acquisition budget or observed CPU time."
        ),
        "limits": (
            "Underlying strict finite JSON caps the entire"
            " request at 4 MiB/depth64/100000 nodes before"
            " preparation. Solver/analysis and final output limits apply. Legacy max_expanded_items "
            "is accepted but nonoperative; retained source size is not new NIH acquisition. An empty "
            "session is zero-check inspection."
        ),
        "standing": (
            "Each alternative feasibility_status uses its "
            "actual effective deciding warrant; UNDETERMIN"
            "ED feasibility uses accepted considered premi"
            "ses. Decision standing uses a strongest suffi"
            "cient actual pair, all sole-survivor deciding"
            " alternatives, or checked selected option. Un"
            "known stays null. Deciding origin_refs and co"
            "mplete input_origins remain separate; selecte"
            "d origin is explicitly user_choice."
        ),
    },
    "expected": {
        "label": "Entirely invented teaching premises, no NIH evidence",
        "baseline_decision": "design_choice",
        "baseline_child_calls": 3,
        "revision_decision": "settled_within_declared_alternatives",
        "revision_fresh_child_calls": 5,
        "clinical_reading": (
            "With an explicitly chosen age18 floor, both >"
            "=65 and below65 are permitted in the represen"
            "ted age restriction. Changing that floor to65"
            " rules out the below65 alternative."
        ),
    },
}

EXAMPLE = {
    "operation": "design_session",
    "session": {
        "schema_version": 1,
        "id": "design",
        "revision": "one",
        "parent_digest": None,
        "target": {
            "kind": "new_trial",
            "ref": "draft",
            "scope": {
                "study": "draft",
                "population": "general",
                "arm": "all",
                "time": "entry",
                "version": "v1",
            },
        },
        "sources": [],
        "premises": [
            {
                "id": "adult",
                "kind": "assertion",
                "payload": {
                    "applicability": {"class": "Always"},
                    "body": {
                        "class": "Literal",
                        "evidence": [],
                        "polarity": "positive",
                        "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                        "qualifiers": {"class": "Always"},
                        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                        "time": None,
                        "value": {
                            "class": "Value",
                            "comparison": "ge",
                            "inclusivity": "unspecified",
                            "kind": "quantity",
                            "members": [],
                            "number": 18.0,
                            "unit": "Years",
                            "upper": None,
                        },
                    },
                    "branch": {"class": "Branch", "node": "unresolved", "path": []},
                    "class": "ScopedAssertion",
                    "cohort": {"class": "Scope", "kind": "all_participants", "parts": [], "ref": ""},
                    "criterion_ref": "user:adult",
                    "id": "adult",
                    "modality": "required",
                    "resolution": "resolved",
                    "rule": {
                        "answers": [],
                        "class": "Rule",
                        "id": "user-explicit",
                        "premises": [],
                        "version": "1",
                        "warrants": [],
                    },
                    "span": [],
                    "status": "known",
                },
                "origin": {"kind": "user_choice", "ref": "user:adult", "source": None, "analysis": None},
                "depends_on": [],
            }
        ],
        "analyses": [
            {
                "id": "older",
                "operation": "entailment",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "parameters": {
                    "query": {
                        "class": "Literal",
                        "evidence": [],
                        "polarity": "positive",
                        "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                        "qualifiers": {"class": "Always"},
                        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                        "time": None,
                        "value": {
                            "class": "Value",
                            "comparison": "ge",
                            "inclusivity": "unspecified",
                            "kind": "quantity",
                            "members": [],
                            "number": 65.0,
                            "unit": "Years",
                            "upper": None,
                        },
                    },
                    "bound": 128,
                },
                "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
            },
            {
                "id": "younger",
                "operation": "entailment",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "parameters": {
                    "query": {
                        "class": "Not",
                        "part": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                    },
                    "bound": 128,
                },
                "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
            },
        ],
        "decisions": [
            {
                "id": "age-policy",
                "question": "Should the represented age restriction require age 65?",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "coverage": "represented_restriction",
                "alternatives": [
                    {
                        "id": "older",
                        "label": "65 or older",
                        "analysis": "older",
                        "query": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                    },
                    {
                        "id": "younger",
                        "label": "Below 65",
                        "analysis": "younger",
                        "query": {
                            "class": "Not",
                            "part": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                        },
                    },
                ],
                "selected": None,
            }
        ],
        "limits": {
            "max_analyses": 128,
            "max_premises": 1000,
            "max_sources": 64,
            "max_decisions": 128,
            "max_expanded_items": 10000,
            "max_solver_work": 10000000,
            "max_output_bytes": 16000000,
        },
    },
    "previous": None,
}

REVISION_EXAMPLE = {
    "operation": "design_session",
    "session": {
        "schema_version": 1,
        "id": "design",
        "revision": "two",
        "parent_digest": "b71ac637afebd383a3c542f7b2a24e256452cac8692f09a9296a7c2836feb161",
        "target": {
            "kind": "new_trial",
            "ref": "draft",
            "scope": {
                "study": "draft",
                "population": "general",
                "arm": "all",
                "time": "entry",
                "version": "v1",
            },
        },
        "sources": [],
        "premises": [
            {
                "id": "adult",
                "kind": "assertion",
                "payload": {
                    "applicability": {"class": "Always"},
                    "body": {
                        "class": "Literal",
                        "evidence": [],
                        "polarity": "positive",
                        "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                        "qualifiers": {"class": "Always"},
                        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                        "time": None,
                        "value": {
                            "class": "Value",
                            "comparison": "ge",
                            "inclusivity": "unspecified",
                            "kind": "quantity",
                            "members": [],
                            "number": 65.0,
                            "unit": "Years",
                            "upper": None,
                        },
                    },
                    "branch": {"class": "Branch", "node": "unresolved", "path": []},
                    "class": "ScopedAssertion",
                    "cohort": {"class": "Scope", "kind": "all_participants", "parts": [], "ref": ""},
                    "criterion_ref": "user:adult",
                    "id": "adult",
                    "modality": "required",
                    "resolution": "resolved",
                    "rule": {
                        "answers": [],
                        "class": "Rule",
                        "id": "user-explicit",
                        "premises": [],
                        "version": "1",
                        "warrants": [],
                    },
                    "span": [],
                    "status": "known",
                },
                "origin": {"kind": "user_choice", "ref": "user:adult", "source": None, "analysis": None},
                "depends_on": [],
            }
        ],
        "analyses": [
            {
                "id": "older",
                "operation": "entailment",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "parameters": {
                    "query": {
                        "class": "Literal",
                        "evidence": [],
                        "polarity": "positive",
                        "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                        "qualifiers": {"class": "Always"},
                        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                        "time": None,
                        "value": {
                            "class": "Value",
                            "comparison": "ge",
                            "inclusivity": "unspecified",
                            "kind": "quantity",
                            "members": [],
                            "number": 65.0,
                            "unit": "Years",
                            "upper": None,
                        },
                    },
                    "bound": 128,
                },
                "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
            },
            {
                "id": "younger",
                "operation": "entailment",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "parameters": {
                    "query": {
                        "class": "Not",
                        "part": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                    },
                    "bound": 128,
                },
                "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
            },
        ],
        "decisions": [
            {
                "id": "age-policy",
                "question": "Should the represented age restriction require age 65?",
                "target": {
                    "kind": "new_trial",
                    "ref": "draft",
                    "scope": {
                        "study": "draft",
                        "population": "general",
                        "arm": "all",
                        "time": "entry",
                        "version": "v1",
                    },
                },
                "coverage": "represented_restriction",
                "alternatives": [
                    {
                        "id": "older",
                        "label": "65 or older",
                        "analysis": "older",
                        "query": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                    },
                    {
                        "id": "younger",
                        "label": "Below 65",
                        "analysis": "younger",
                        "query": {
                            "class": "Not",
                            "part": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                        },
                    },
                ],
                "selected": None,
            }
        ],
        "limits": {
            "max_analyses": 128,
            "max_premises": 1000,
            "max_sources": 64,
            "max_decisions": 128,
            "max_expanded_items": 10000,
            "max_solver_work": 10000000,
            "max_output_bytes": 16000000,
        },
    },
    "previous": {
        "session": {
            "schema_version": 1,
            "id": "design",
            "revision": "one",
            "parent_digest": None,
            "target": {
                "kind": "new_trial",
                "ref": "draft",
                "scope": {
                    "study": "draft",
                    "population": "general",
                    "arm": "all",
                    "time": "entry",
                    "version": "v1",
                },
            },
            "sources": [],
            "premises": [
                {
                    "id": "adult",
                    "kind": "assertion",
                    "payload": {
                        "applicability": {"class": "Always"},
                        "body": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 18.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                        "branch": {"class": "Branch", "node": "unresolved", "path": []},
                        "class": "ScopedAssertion",
                        "cohort": {"class": "Scope", "kind": "all_participants", "parts": [], "ref": ""},
                        "criterion_ref": "user:adult",
                        "id": "adult",
                        "modality": "required",
                        "resolution": "resolved",
                        "rule": {
                            "answers": [],
                            "class": "Rule",
                            "id": "user-explicit",
                            "premises": [],
                            "version": "1",
                            "warrants": [],
                        },
                        "span": [],
                        "status": "known",
                    },
                    "origin": {"kind": "user_choice", "ref": "user:adult", "source": None, "analysis": None},
                    "depends_on": [],
                }
            ],
            "analyses": [
                {
                    "id": "older",
                    "operation": "entailment",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "parameters": {
                        "query": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                        "bound": 128,
                    },
                    "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
                },
                {
                    "id": "younger",
                    "operation": "entailment",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "parameters": {
                        "query": {
                            "class": "Not",
                            "part": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                        },
                        "bound": 128,
                    },
                    "uses": [{"premise": "adult", "slot": "assertions", "projection": "identity"}],
                },
            ],
            "decisions": [
                {
                    "id": "age-policy",
                    "question": "Should the represented age restriction require age 65?",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "coverage": "represented_restriction",
                    "alternatives": [
                        {
                            "id": "older",
                            "label": "65 or older",
                            "analysis": "older",
                            "query": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                        },
                        {
                            "id": "younger",
                            "label": "Below 65",
                            "analysis": "younger",
                            "query": {
                                "class": "Not",
                                "part": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 65.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                            },
                        },
                    ],
                    "selected": None,
                }
            ],
            "limits": {
                "max_analyses": 128,
                "max_premises": 1000,
                "max_sources": 64,
                "max_decisions": 128,
                "max_expanded_items": 10000,
                "max_solver_work": 10000000,
                "max_output_bytes": 16000000,
            },
        },
        "result": {
            "schema_version": 1,
            "session_id": "design",
            "revision": "one",
            "session_digest": ("b71ac637afebd383a3c542f7b2a24e256452cac8692f09a9296a7c2836feb161"),
            "target": {
                "kind": "new_trial",
                "ref": "draft",
                "scope": {
                    "study": "draft",
                    "population": "general",
                    "arm": "all",
                    "time": "entry",
                    "version": "v1",
                },
            },
            "sources": [],
            "premises": [
                {
                    "id": "adult",
                    "kind": "assertion",
                    "payload": {
                        "applicability": {"class": "Always"},
                        "body": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 18.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                        "branch": {"class": "Branch", "node": "unresolved", "path": []},
                        "class": "ScopedAssertion",
                        "cohort": {"class": "Scope", "kind": "all_participants", "parts": [], "ref": ""},
                        "criterion_ref": "user:adult",
                        "id": "adult",
                        "modality": "required",
                        "resolution": "resolved",
                        "rule": {
                            "answers": [],
                            "class": "Rule",
                            "id": "user-explicit",
                            "premises": [],
                            "version": "1",
                            "warrants": [],
                        },
                        "span": [],
                        "status": "known",
                    },
                    "origin": {"kind": "user_choice", "ref": "user:adult", "source": None, "analysis": None},
                    "depends_on": [],
                }
            ],
            "effective_premises": [
                {
                    "id": "adult",
                    "kind": "assertion",
                    "payload": {
                        "applicability": {"class": "Always"},
                        "body": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 18.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                        "branch": {"class": "Branch", "node": "unresolved", "path": []},
                        "class": "ScopedAssertion",
                        "cohort": {"class": "Scope", "kind": "all_participants", "parts": [], "ref": ""},
                        "criterion_ref": "user:adult",
                        "id": "adult",
                        "modality": "required",
                        "resolution": "resolved",
                        "rule": {
                            "answers": [],
                            "class": "Rule",
                            "id": "user-explicit",
                            "premises": [],
                            "version": "1",
                            "warrants": [],
                        },
                        "span": [],
                        "status": "known",
                    },
                    "standing": {"status": "known", "resolution": "resolved", "basis": ["user:adult"]},
                    "origin": {"kind": "user_choice", "ref": "user:adult", "source": None, "analysis": None},
                    "depends_on": [],
                    "dependency_support": None,
                }
            ],
            "dependency_graph": {
                "premise:adult": [],
                "analysis:older": ["premise:adult"],
                "analysis:younger": ["premise:adult"],
            },
            "analyses": [
                {
                    "id": "older",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "request": {
                        "operation": "entailment",
                        "query": {
                            "class": "Literal",
                            "evidence": [],
                            "polarity": "positive",
                            "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                            "qualifiers": {"class": "Always"},
                            "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                            "time": None,
                            "value": {
                                "class": "Value",
                                "comparison": "ge",
                                "inclusivity": "unspecified",
                                "kind": "quantity",
                                "members": [],
                                "number": 65.0,
                                "unit": "Years",
                                "upper": None,
                            },
                        },
                        "bound": 128,
                        "assertions": [
                            {
                                "applicability": {"class": "Always"},
                                "body": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 18.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                                "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                "class": "ScopedAssertion",
                                "cohort": {
                                    "class": "Scope",
                                    "kind": "all_participants",
                                    "parts": [],
                                    "ref": "",
                                },
                                "criterion_ref": "user:adult",
                                "id": "adult",
                                "modality": "required",
                                "resolution": "resolved",
                                "rule": {
                                    "answers": [],
                                    "class": "Rule",
                                    "id": "user-explicit",
                                    "premises": [],
                                    "version": "1",
                                    "warrants": [],
                                },
                                "span": [],
                                "status": "known",
                            }
                        ],
                    },
                    "result": {
                        "code": "complete",
                        "metadata": {
                            "findings": [
                                {
                                    "causes": [{"code": "undecided_by_constraints", "kind": "constraint"}],
                                    "completion": "complete",
                                    "disposition": "open",
                                    "kind": "logical",
                                    "logical_result": "UNDETERMINED",
                                    "path": "/result/decision",
                                    "standing": None,
                                }
                            ],
                            "kind": "reasoning",
                            "version": 1,
                        },
                        "operation": "entailment",
                        "problems": [],
                        "result": {
                            "basis": (
                                "Conditional on the supplied typed premises; t"
                                "heir source meaning is not certified by this "
                                "operation."
                            ),
                            "decision": {
                                "blockers": ["undecided_by_constraints"],
                                "proof": ["adult"],
                                "query": (
                                    '{"class":"Literal","evidence":[],"polarity":"'
                                    'positive","predicate":{"class":"Predicate","k'
                                    'ey":"age","kind":"measurement"},"qualifiers":'
                                    '{"class":"Always"},"subject":{"class":"Subjec'
                                    't","kind":"participant","referent":""},"time"'
                                    ':null,"value":{"class":"Value","comparison":"'
                                    'ge","inclusivity":"unspecified","kind":"quant'
                                    'ity","members":[],"number":65.0,"unit":"Years'
                                    '","upper":null}}'
                                ),
                                "result": "UNDETERMINED",
                                "status": None,
                            },
                            "premises": [
                                {
                                    "applicability": {"class": "Always"},
                                    "body": {
                                        "class": "Literal",
                                        "evidence": [],
                                        "polarity": "positive",
                                        "predicate": {
                                            "class": "Predicate",
                                            "key": "age",
                                            "kind": "measurement",
                                        },
                                        "qualifiers": {"class": "Always"},
                                        "subject": {
                                            "class": "Subject",
                                            "kind": "participant",
                                            "referent": "",
                                        },
                                        "time": None,
                                        "value": {
                                            "class": "Value",
                                            "comparison": "ge",
                                            "inclusivity": "unspecified",
                                            "kind": "quantity",
                                            "members": [],
                                            "number": 18.0,
                                            "unit": "Years",
                                            "upper": None,
                                        },
                                    },
                                    "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                    "class": "ScopedAssertion",
                                    "cohort": {
                                        "class": "Scope",
                                        "kind": "all_participants",
                                        "parts": [],
                                        "ref": "",
                                    },
                                    "criterion_ref": "user:adult",
                                    "id": "adult",
                                    "modality": "required",
                                    "resolution": "resolved",
                                    "rule": {
                                        "answers": [],
                                        "class": "Rule",
                                        "id": "user-explicit",
                                        "premises": [],
                                        "version": "1",
                                        "warrants": [],
                                    },
                                    "span": [],
                                    "status": "known",
                                }
                            ],
                        },
                    },
                    "request_digest": ("b82397a5cea1546ff5691a6f9358c3fcdc5737f301d52ddd5020a23cb3361a6d"),
                    "result_digest": ("9dbd9b152627db0df4eb3f2ec0e3de3950a33ba7f104923e946417dd5821fee2"),
                    "dependencies": ["premise:adult"],
                },
                {
                    "id": "younger",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "request": {
                        "operation": "entailment",
                        "query": {
                            "class": "Not",
                            "part": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                        },
                        "bound": 128,
                        "assertions": [
                            {
                                "applicability": {"class": "Always"},
                                "body": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 18.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                                "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                "class": "ScopedAssertion",
                                "cohort": {
                                    "class": "Scope",
                                    "kind": "all_participants",
                                    "parts": [],
                                    "ref": "",
                                },
                                "criterion_ref": "user:adult",
                                "id": "adult",
                                "modality": "required",
                                "resolution": "resolved",
                                "rule": {
                                    "answers": [],
                                    "class": "Rule",
                                    "id": "user-explicit",
                                    "premises": [],
                                    "version": "1",
                                    "warrants": [],
                                },
                                "span": [],
                                "status": "known",
                            }
                        ],
                    },
                    "result": {
                        "code": "complete",
                        "metadata": {
                            "findings": [
                                {
                                    "causes": [{"code": "undecided_by_constraints", "kind": "constraint"}],
                                    "completion": "complete",
                                    "disposition": "open",
                                    "kind": "logical",
                                    "logical_result": "UNDETERMINED",
                                    "path": "/result/decision",
                                    "standing": None,
                                }
                            ],
                            "kind": "reasoning",
                            "version": 1,
                        },
                        "operation": "entailment",
                        "problems": [],
                        "result": {
                            "basis": (
                                "Conditional on the supplied typed premises; t"
                                "heir source meaning is not certified by this "
                                "operation."
                            ),
                            "decision": {
                                "blockers": ["undecided_by_constraints"],
                                "proof": ["adult"],
                                "query": (
                                    '{"class":"Not","part":{"class":"Literal","evi'
                                    'dence":[],"polarity":"positive","predicate":{'
                                    '"class":"Predicate","key":"age","kind":"measu'
                                    'rement"},"qualifiers":{"class":"Always"},"sub'
                                    'ject":{"class":"Subject","kind":"participant"'
                                    ',"referent":""},"time":null,"value":{"class":'
                                    '"Value","comparison":"ge","inclusivity":"unsp'
                                    'ecified","kind":"quantity","members":[],"numb'
                                    'er":65.0,"unit":"Years","upper":null}}}'
                                ),
                                "result": "UNDETERMINED",
                                "status": None,
                            },
                            "premises": [
                                {
                                    "applicability": {"class": "Always"},
                                    "body": {
                                        "class": "Literal",
                                        "evidence": [],
                                        "polarity": "positive",
                                        "predicate": {
                                            "class": "Predicate",
                                            "key": "age",
                                            "kind": "measurement",
                                        },
                                        "qualifiers": {"class": "Always"},
                                        "subject": {
                                            "class": "Subject",
                                            "kind": "participant",
                                            "referent": "",
                                        },
                                        "time": None,
                                        "value": {
                                            "class": "Value",
                                            "comparison": "ge",
                                            "inclusivity": "unspecified",
                                            "kind": "quantity",
                                            "members": [],
                                            "number": 18.0,
                                            "unit": "Years",
                                            "upper": None,
                                        },
                                    },
                                    "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                    "class": "ScopedAssertion",
                                    "cohort": {
                                        "class": "Scope",
                                        "kind": "all_participants",
                                        "parts": [],
                                        "ref": "",
                                    },
                                    "criterion_ref": "user:adult",
                                    "id": "adult",
                                    "modality": "required",
                                    "resolution": "resolved",
                                    "rule": {
                                        "answers": [],
                                        "class": "Rule",
                                        "id": "user-explicit",
                                        "premises": [],
                                        "version": "1",
                                        "warrants": [],
                                    },
                                    "span": [],
                                    "status": "known",
                                }
                            ],
                        },
                    },
                    "request_digest": ("87df278f8b1fec367ddddecb6f290a01057b525e7e48c06e908a96afcb45bf70"),
                    "result_digest": ("116189a6f8923a85b9a9ed1747dcabe8334923e2e44ac83d6bb26cdabaa8c785"),
                    "dependencies": ["premise:adult"],
                },
            ],
            "projection_ledger": [
                {
                    "analysis": "older",
                    "projections": [
                        {
                            "premise": "adult",
                            "slot": "assertions",
                            "projection": "identity",
                            "value": {
                                "applicability": {"class": "Always"},
                                "body": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 18.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                                "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                "class": "ScopedAssertion",
                                "cohort": {
                                    "class": "Scope",
                                    "kind": "all_participants",
                                    "parts": [],
                                    "ref": "",
                                },
                                "criterion_ref": "user:adult",
                                "id": "adult",
                                "modality": "required",
                                "resolution": "resolved",
                                "rule": {
                                    "answers": [],
                                    "class": "Rule",
                                    "id": "user-explicit",
                                    "premises": [],
                                    "version": "1",
                                    "warrants": [],
                                },
                                "span": [],
                                "status": "known",
                            },
                            "details": [],
                        }
                    ],
                },
                {
                    "analysis": "younger",
                    "projections": [
                        {
                            "premise": "adult",
                            "slot": "assertions",
                            "projection": "identity",
                            "value": {
                                "applicability": {"class": "Always"},
                                "body": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 18.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                                "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                "class": "ScopedAssertion",
                                "cohort": {
                                    "class": "Scope",
                                    "kind": "all_participants",
                                    "parts": [],
                                    "ref": "",
                                },
                                "criterion_ref": "user:adult",
                                "id": "adult",
                                "modality": "required",
                                "resolution": "resolved",
                                "rule": {
                                    "answers": [],
                                    "class": "Rule",
                                    "id": "user-explicit",
                                    "premises": [],
                                    "version": "1",
                                    "warrants": [],
                                },
                                "span": [],
                                "status": "known",
                            },
                            "details": [],
                        }
                    ],
                },
            ],
            "decisions": [
                {
                    "id": "age-policy",
                    "question": "Should the represented age restriction require age 65?",
                    "target": {
                        "kind": "new_trial",
                        "ref": "draft",
                        "scope": {
                            "study": "draft",
                            "population": "general",
                            "arm": "all",
                            "time": "entry",
                            "version": "v1",
                        },
                    },
                    "coverage": "represented_restriction",
                    "alternatives": [
                        {
                            "id": "older",
                            "label": "65 or older",
                            "analysis": "older",
                            "query": {
                                "class": "Literal",
                                "evidence": [],
                                "polarity": "positive",
                                "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                "qualifiers": {"class": "Always"},
                                "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                "time": None,
                                "value": {
                                    "class": "Value",
                                    "comparison": "ge",
                                    "inclusivity": "unspecified",
                                    "kind": "quantity",
                                    "members": [],
                                    "number": 65.0,
                                    "unit": "Years",
                                    "upper": None,
                                },
                            },
                            "code": "feasible",
                            "warrant": {
                                "blockers": ["undecided_by_constraints"],
                                "proof": ["adult"],
                                "query": (
                                    '{"class":"Literal","evidence":[],"polarity":"'
                                    'positive","predicate":{"class":"Predicate","k'
                                    'ey":"age","kind":"measurement"},"qualifiers":'
                                    '{"class":"Always"},"subject":{"class":"Subjec'
                                    't","kind":"participant","referent":""},"time"'
                                    ':null,"value":{"class":"Value","comparison":"'
                                    'ge","inclusivity":"unspecified","kind":"quant'
                                    'ity","members":[],"number":65.0,"unit":"Years'
                                    '","upper":null}}'
                                ),
                                "result": "UNDETERMINED",
                                "status": None,
                            },
                            "feasibility_status": "known",
                            "origin_refs": [
                                {
                                    "premise": "adult",
                                    "origin": {
                                        "kind": "user_choice",
                                        "ref": "user:adult",
                                        "source": None,
                                        "analysis": None,
                                    },
                                }
                            ],
                            "analysis_result_digest": (
                                "9dbd9b152627db0df4eb3f2ec0e3de3950a33ba7f104923e946417dd5821fee2"
                            ),
                        },
                        {
                            "id": "younger",
                            "label": "Below 65",
                            "analysis": "younger",
                            "query": {
                                "class": "Not",
                                "part": {
                                    "class": "Literal",
                                    "evidence": [],
                                    "polarity": "positive",
                                    "predicate": {"class": "Predicate", "key": "age", "kind": "measurement"},
                                    "qualifiers": {"class": "Always"},
                                    "subject": {"class": "Subject", "kind": "participant", "referent": ""},
                                    "time": None,
                                    "value": {
                                        "class": "Value",
                                        "comparison": "ge",
                                        "inclusivity": "unspecified",
                                        "kind": "quantity",
                                        "members": [],
                                        "number": 65.0,
                                        "unit": "Years",
                                        "upper": None,
                                    },
                                },
                            },
                            "code": "feasible",
                            "warrant": {
                                "blockers": ["undecided_by_constraints"],
                                "proof": ["adult"],
                                "query": (
                                    '{"class":"Not","part":{"class":"Literal","evi'
                                    'dence":[],"polarity":"positive","predicate":{'
                                    '"class":"Predicate","key":"age","kind":"measu'
                                    'rement"},"qualifiers":{"class":"Always"},"sub'
                                    'ject":{"class":"Subject","kind":"participant"'
                                    ',"referent":""},"time":null,"value":{"class":'
                                    '"Value","comparison":"ge","inclusivity":"unsp'
                                    'ecified","kind":"quantity","members":[],"numb'
                                    'er":65.0,"unit":"Years","upper":null}}}'
                                ),
                                "result": "UNDETERMINED",
                                "status": None,
                            },
                            "feasibility_status": "known",
                            "origin_refs": [
                                {
                                    "premise": "adult",
                                    "origin": {
                                        "kind": "user_choice",
                                        "ref": "user:adult",
                                        "source": None,
                                        "analysis": None,
                                    },
                                }
                            ],
                            "analysis_result_digest": (
                                "116189a6f8923a85b9a9ed1747dcabe8334923e2e44ac83d6bb26cdabaa8c785"
                            ),
                        },
                    ],
                    "selected": None,
                    "standing": "known",
                    "determining_alternatives": ["older", "younger"],
                    "determining_distinctions": [0],
                    "origin_refs": [
                        {
                            "premise": "adult",
                            "origin": {
                                "kind": "user_choice",
                                "ref": "user:adult",
                                "source": None,
                                "analysis": None,
                            },
                        }
                    ],
                    "origin": {
                        "kind": "computed",
                        "refs": [
                            {
                                "premise": "adult",
                                "origin": {
                                    "kind": "user_choice",
                                    "ref": "user:adult",
                                    "source": None,
                                    "analysis": None,
                                },
                            }
                        ],
                    },
                    "input_origins": [
                        {
                            "premise": "adult",
                            "origin": {
                                "kind": "user_choice",
                                "ref": "user:adult",
                                "source": None,
                                "analysis": None,
                            },
                        }
                    ],
                    "distinctions": [
                        {
                            "alternatives": ["older", "younger"],
                            "dependencies": ["analysis:older", "analysis:younger"],
                            "request": {
                                "operation": "entailment",
                                "bound": 128,
                                "assertions": [
                                    {
                                        "applicability": {"class": "Always"},
                                        "body": {
                                            "class": "Literal",
                                            "evidence": [],
                                            "polarity": "positive",
                                            "predicate": {
                                                "class": "Predicate",
                                                "key": "age",
                                                "kind": "measurement",
                                            },
                                            "qualifiers": {"class": "Always"},
                                            "subject": {
                                                "class": "Subject",
                                                "kind": "participant",
                                                "referent": "",
                                            },
                                            "time": None,
                                            "value": {
                                                "class": "Value",
                                                "comparison": "ge",
                                                "inclusivity": "unspecified",
                                                "kind": "quantity",
                                                "members": [],
                                                "number": 18.0,
                                                "unit": "Years",
                                                "upper": None,
                                            },
                                        },
                                        "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                        "class": "ScopedAssertion",
                                        "cohort": {
                                            "class": "Scope",
                                            "kind": "all_participants",
                                            "parts": [],
                                            "ref": "",
                                        },
                                        "criterion_ref": "user:adult",
                                        "id": "adult",
                                        "modality": "required",
                                        "resolution": "resolved",
                                        "rule": {
                                            "answers": [],
                                            "class": "Rule",
                                            "id": "user-explicit",
                                            "premises": [],
                                            "version": "1",
                                            "warrants": [],
                                        },
                                        "span": [],
                                        "status": "known",
                                    }
                                ],
                                "query": {
                                    "class": "AnyOf",
                                    "parts": [
                                        {
                                            "class": "AllOf",
                                            "parts": [
                                                {
                                                    "class": "Literal",
                                                    "evidence": [],
                                                    "polarity": "positive",
                                                    "predicate": {
                                                        "class": "Predicate",
                                                        "key": "age",
                                                        "kind": "measurement",
                                                    },
                                                    "qualifiers": {"class": "Always"},
                                                    "subject": {
                                                        "class": "Subject",
                                                        "kind": "participant",
                                                        "referent": "",
                                                    },
                                                    "time": None,
                                                    "value": {
                                                        "class": "Value",
                                                        "comparison": "ge",
                                                        "inclusivity": "unspecified",
                                                        "kind": "quantity",
                                                        "members": [],
                                                        "number": 65.0,
                                                        "unit": "Years",
                                                        "upper": None,
                                                    },
                                                },
                                                {
                                                    "class": "Not",
                                                    "part": {
                                                        "class": "Not",
                                                        "part": {
                                                            "class": "Literal",
                                                            "evidence": [],
                                                            "polarity": "positive",
                                                            "predicate": {
                                                                "class": "Predicate",
                                                                "key": "age",
                                                                "kind": "measurement",
                                                            },
                                                            "qualifiers": {"class": "Always"},
                                                            "subject": {
                                                                "class": "Subject",
                                                                "kind": "participant",
                                                                "referent": "",
                                                            },
                                                            "time": None,
                                                            "value": {
                                                                "class": "Value",
                                                                "comparison": "ge",
                                                                "inclusivity": "unspecified",
                                                                "kind": "quantity",
                                                                "members": [],
                                                                "number": 65.0,
                                                                "unit": "Years",
                                                                "upper": None,
                                                            },
                                                        },
                                                    },
                                                },
                                            ],
                                        },
                                        {
                                            "class": "AllOf",
                                            "parts": [
                                                {
                                                    "class": "Not",
                                                    "part": {
                                                        "class": "Literal",
                                                        "evidence": [],
                                                        "polarity": "positive",
                                                        "predicate": {
                                                            "class": "Predicate",
                                                            "key": "age",
                                                            "kind": "measurement",
                                                        },
                                                        "qualifiers": {"class": "Always"},
                                                        "subject": {
                                                            "class": "Subject",
                                                            "kind": "participant",
                                                            "referent": "",
                                                        },
                                                        "time": None,
                                                        "value": {
                                                            "class": "Value",
                                                            "comparison": "ge",
                                                            "inclusivity": "unspecified",
                                                            "kind": "quantity",
                                                            "members": [],
                                                            "number": 65.0,
                                                            "unit": "Years",
                                                            "upper": None,
                                                        },
                                                    },
                                                },
                                                {
                                                    "class": "Not",
                                                    "part": {
                                                        "class": "Literal",
                                                        "evidence": [],
                                                        "polarity": "positive",
                                                        "predicate": {
                                                            "class": "Predicate",
                                                            "key": "age",
                                                            "kind": "measurement",
                                                        },
                                                        "qualifiers": {"class": "Always"},
                                                        "subject": {
                                                            "class": "Subject",
                                                            "kind": "participant",
                                                            "referent": "",
                                                        },
                                                        "time": None,
                                                        "value": {
                                                            "class": "Value",
                                                            "comparison": "ge",
                                                            "inclusivity": "unspecified",
                                                            "kind": "quantity",
                                                            "members": [],
                                                            "number": 65.0,
                                                            "unit": "Years",
                                                            "upper": None,
                                                        },
                                                    },
                                                },
                                            ],
                                        },
                                    ],
                                },
                            },
                            "result": {
                                "code": "complete",
                                "metadata": {
                                    "findings": [
                                        {
                                            "causes": [],
                                            "completion": "complete",
                                            "disposition": "settled",
                                            "kind": "logical",
                                            "logical_result": "ENTAILED",
                                            "path": "/result/decision",
                                            "standing": "known",
                                        }
                                    ],
                                    "kind": "reasoning",
                                    "version": 1,
                                },
                                "operation": "entailment",
                                "problems": [],
                                "result": {
                                    "basis": (
                                        "Conditional on the supplied typed premises; t"
                                        "heir source meaning is not certified by this "
                                        "operation."
                                    ),
                                    "decision": {
                                        "blockers": [],
                                        "proof": [],
                                        "query": (
                                            '{"class":"AnyOf","parts":[{"class":"AllOf","p'
                                            'arts":[{"class":"Literal","evidence":[],"pola'
                                            'rity":"positive","predicate":{"class":"Predic'
                                            'ate","key":"age","kind":"measurement"},"quali'
                                            'fiers":{"class":"Always"},"subject":{"class":'
                                            '"Subject","kind":"participant","referent":""}'
                                            ',"time":null,"value":{"class":"Value","compar'
                                            'ison":"ge","inclusivity":"unspecified","kind"'
                                            ':"quantity","members":[],"number":65.0,"unit"'
                                            ':"Years","upper":null}},{"class":"Not","part"'
                                            ':{"class":"Not","part":{"class":"Literal","ev'
                                            'idence":[],"polarity":"positive","predicate":'
                                            '{"class":"Predicate","key":"age","kind":"meas'
                                            'urement"},"qualifiers":{"class":"Always"},"su'
                                            'bject":{"class":"Subject","kind":"participant'
                                            '","referent":""},"time":null,"value":{"class"'
                                            ':"Value","comparison":"ge","inclusivity":"uns'
                                            'pecified","kind":"quantity","members":[],"num'
                                            'ber":65.0,"unit":"Years","upper":null}}}}]},{'
                                            '"class":"AllOf","parts":[{"class":"Not","part'
                                            '":{"class":"Literal","evidence":[],"polarity"'
                                            ':"positive","predicate":{"class":"Predicate",'
                                            '"key":"age","kind":"measurement"},"qualifiers'
                                            '":{"class":"Always"},"subject":{"class":"Subj'
                                            'ect","kind":"participant","referent":""},"tim'
                                            'e":null,"value":{"class":"Value","comparison"'
                                            ':"ge","inclusivity":"unspecified","kind":"qua'
                                            'ntity","members":[],"number":65.0,"unit":"Yea'
                                            'rs","upper":null}}},{"class":"Not","part":{"c'
                                            'lass":"Literal","evidence":[],"polarity":"pos'
                                            'itive","predicate":{"class":"Predicate","key"'
                                            ':"age","kind":"measurement"},"qualifiers":{"c'
                                            'lass":"Always"},"subject":{"class":"Subject",'
                                            '"kind":"participant","referent":""},"time":nu'
                                            'll,"value":{"class":"Value","comparison":"ge"'
                                            ',"inclusivity":"unspecified","kind":"quantity'
                                            '","members":[],"number":65.0,"unit":"Years","'
                                            'upper":null}}}]}]}'
                                        ),
                                        "result": "ENTAILED",
                                        "status": "known",
                                    },
                                    "premises": [
                                        {
                                            "applicability": {"class": "Always"},
                                            "body": {
                                                "class": "Literal",
                                                "evidence": [],
                                                "polarity": "positive",
                                                "predicate": {
                                                    "class": "Predicate",
                                                    "key": "age",
                                                    "kind": "measurement",
                                                },
                                                "qualifiers": {"class": "Always"},
                                                "subject": {
                                                    "class": "Subject",
                                                    "kind": "participant",
                                                    "referent": "",
                                                },
                                                "time": None,
                                                "value": {
                                                    "class": "Value",
                                                    "comparison": "ge",
                                                    "inclusivity": "unspecified",
                                                    "kind": "quantity",
                                                    "members": [],
                                                    "number": 18.0,
                                                    "unit": "Years",
                                                    "upper": None,
                                                },
                                            },
                                            "branch": {"class": "Branch", "node": "unresolved", "path": []},
                                            "class": "ScopedAssertion",
                                            "cohort": {
                                                "class": "Scope",
                                                "kind": "all_participants",
                                                "parts": [],
                                                "ref": "",
                                            },
                                            "criterion_ref": "user:adult",
                                            "id": "adult",
                                            "modality": "required",
                                            "resolution": "resolved",
                                            "rule": {
                                                "answers": [],
                                                "class": "Rule",
                                                "id": "user-explicit",
                                                "premises": [],
                                                "version": "1",
                                                "warrants": [],
                                            },
                                            "span": [],
                                            "status": "known",
                                        }
                                    ],
                                },
                            },
                            "request_digest": (
                                "fe34c64bd1974bbedac4535672143bd793c3cab6fdeafd17cef6551ff1c754b9"
                            ),
                            "result_digest": (
                                "c3838d1f6ae706e97fba10a962063606cec588d8965f6b7032939c8ead56a4d5"
                            ),
                            "code": "distinguishable_under_floor",
                            "support_status": "known",
                            "origin_refs": [],
                        }
                    ],
                    "open_alternatives": [],
                    "code": "design_choice",
                    "coverage_limit": (
                        "Only caller-declared represented constructs; not complete clinical eligibility."
                    ),
                }
            ],
            "limits": {
                "max_analyses": 128,
                "max_premises": 1000,
                "max_sources": 64,
                "max_decisions": 128,
                "max_expanded_items": 10000,
                "max_solver_work": 10000000,
                "max_output_bytes": 16000000,
            },
            "limits_of_claim": [
                ("Caller labels do not independently verify source truth or confirmation."),
                ("Exact representation comparison is not clinical semantic equivalence."),
                "A represented restriction is not full patient eligibility.",
                (
                    "All analysis inputs are replay dependencies; "
                    "only claimed support or actual deciding warra"
                    "nts weaken a finding."
                ),
            ],
        },
        "expected_result_digest": ("aa07054696dd9f3aa56cdec9327aa895fdb2bdab49e6152b5a0a1f1ed0df701e"),
    },
}
