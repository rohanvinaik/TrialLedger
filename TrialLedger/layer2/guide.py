"""How an assistant translates between a clinician and the symbolic operations (the `describe` guide).

The assistant translates; the operations reason. It restates the person's criteria and questions as typed
premises, shows them back in plain words, runs the operation and reports the computed answer in one of
four categories, citing the premise that decided it. This module holds that guide: the answer categories
and how each operation's results map to them, the clinical words that name a computed object, and a
worked session whose every request runs and returns the result stated beside it. It reads nothing,
writes nothing and decides nothing; the operations in `service` do the reasoning.
"""

from __future__ import annotations

from typing import Any

DEMONSTRATION_BASIS = "user:demonstration-brief"

ROLES = {
    "record": (
        "Layer-one source facts and fixed direct rules, cited by their workbook/record address. No "
        "language model supplies them."
    ),
    "computed": (
        "A reason result over premises the person confirmed, cited with the premise or rule that decided "
        "it. The logic is computed, not composed by the assistant."
    ),
    "translation": (
        "The assistant's restatement of the person's words as typed premises, and of results as plain "
        "language. Show material premises together in plain words; an unconfirmed reading stays proposed "
        "and is never presented as a fact or a computed result."
    ),
}

CATEGORIES = {
    "settled": (
        "The premises require it or rule it out (ENTAILED or REFUTED), or explicit evidence narrowed a "
        "coordinate. Name the deciding premise. A conclusion whose weakest premise is interpolated is "
        "'settled by default' and can be overridden."
    ),
    "something_wrong": (
        "A contradiction: the person's criteria conflict (INCONSISTENT), explicit evidence empties a "
        "coordinate (state conflict), or a registry record disagrees with itself (registry_checks "
        "conflict). Name both sides. A contradiction blocks every entailment answer until it is resolved."
    ),
    "your_call": (
        "Genuine design freedom or a choice only the person can make: allowed but not required, a "
        "proposal or proposed pattern, comparable trials that chose differently, which cohort is meant, "
        "whether to confirm a reading, or whether the criteria should address something they are silent "
        "on. Ask, offer the computed basis, and record the person's choice as theirs."
    ),
    "not_knowable_here": (
        "This evidence cannot settle it: registry silence, too few trials or sponsors, unknown "
        "membership, abstained rarity or a computation limit. Say what is missing; silence is not "
        "absence and an unknown is not false."
    ),
}

# Precedence: read every blocker and report the most specific unsettled item first.
ENTAILMENT_DECISIONS = {
    "ENTAILED": ("settled", "Your criteria require this, because of the premises in proof."),
    "REFUTED": ("settled", "Your criteria rule this out, because of the premises in proof."),
    "INCONSISTENT": (
        "something_wrong",
        "The premises in proof contradict each other. Contradiction anywhere in the supplied premises "
        "returns this for every question; resolve it first.",
    ),
    "OUT_OF_SCOPE": (
        "your_call",
        "Your criteria address this only for another cohort, arm or phase (the premises in proof); say "
        "which, and ask whether the question is about that group.",
    ),
    "UNSUPPORTED_QUERY": (
        "translation",
        "The question itself is not fully stated (unresolved or opaque content). Restate it; this is not "
        "a clinical finding.",
    ),
    "UNDETERMINED": (
        "by_blocker",
        "Neither required nor ruled out. Read every blocker and report the most specific reason below.",
    ),
}

ENTAILMENT_BLOCKERS = {
    "profile_inconsistent": (
        "translation",
        "The participant profile contradicts itself; repair it before using it as an eligibility witness.",
    ),
    "resource_bound": (
        "not_knowable_here",
        "Too large to settle within the computation limit; narrow the question.",
    ),
    "proposed_refused": (
        "your_call",
        "Depends on a reading the person has not confirmed (the named premise was set aside). Show it in "
        "plain words and ask.",
    ),
    "unresolved_rule": (
        "translation",
        "The named premise has no rule or warrant, so it was set aside; supply its origin.",
    ),
    "unresolved_assertion": (
        "translation",
        "The named premise's force or resolution is unresolved, so it was set aside; settle it with the "
        "person.",
    ),
    "conflicting": (
        "your_call",
        "The named premise is marked as having conflicting readings and was set aside; ask which applies.",
    ),
    "open_scope": (
        "your_call",
        "Depends on which cohort, arm or phase is meant; ask, then rerun with that context.",
    ),
    "unresolved_scope": (
        "translation",
        "A premise's cohort or arm reference is unresolved; settle which group it covers.",
    ),
    "unresolved_literal": (
        "translation",
        "Part of a premise is not fully stated; resolve the wording before answering.",
    ),
    "unspecified_boundary": (
        "translation",
        "A numeric limit's inclusivity matters and is unspecified; ask whether the limit is included.",
    ),
    "opaque": ("translation", "A premise holds content the operation cannot read; restate it."),
    "no_constraint_mentions_query": (
        "your_call",
        "The confirmed criteria do not address this. First check for a phrasing, unit or time-window "
        "mismatch (units are not converted; time windows must match exactly); if none, ask whether the "
        "criteria should address it.",
    ),
    "undecided_by_constraints": (
        "your_call",
        "Only when it is the sole blocker: allowed but not required. The criteria admit it without "
        "requiring it (both it and its opposite are consistent with them). Say exactly that.",
    ),
    "query_not_proposition": ("translation", "The query is not a proposition; restate it."),
}

COORDINATE_STATES = {
    "known.resolved": ("settled", "Explicit premises narrowed it to one value; cite the causes."),
    "known.unresolved": ("your_call", "Explicit premises left these values; the remaining choice is open."),
    "known.conflict": ("something_wrong", "Explicit premises leave no value; name the conflicting causes."),
    "known.unnarrowed": ("not_knowable_here", "The supplied evidence does not narrow this coordinate."),
    "interpolated.resolved": (
        "settled",
        "Settled by default: one value remains after defaults. Current NSCLC relations are defaults or "
        "proposals, never strict deductions; say 'by default' and that the person can override it.",
    ),
    "interpolated.unresolved": (
        "your_call",
        "Defaults narrowed it to these values but no further; the remaining choice is open.",
    ),
    "interpolated.conflict": ("something_wrong", "Defaults leave no value; name the conflicting causes."),
    "interpolated.unnarrowed": ("not_knowable_here", "Even with defaults, the evidence does not narrow it."),
    "proposals": ("your_call", "A suggested narrowing, shown separately; never used as a premise."),
}

CORPUS_RESULTS = {
    "frequency.statement_rate": (
        "settled",
        "As counted: stating trials over trials in the declared set, with distinct sponsors.",
    ),
    "frequency.range": (
        "not_knowable_here",
        "When lower < upper, unresolved silences keep the full-criteria rate open within [lower, upper]; "
        "report the range, never the statement rate alone. When lower equals upper, the range is closed.",
    ),
    "frequency.tier": (
        "settled",
        "met / not_met / unresolved against the corpus threshold: a corpus setting, not clinical necessity.",
    ),
    "associations.proposed": (
        "your_call",
        "A pattern with support, offered for consideration; not a causal or clinical rule.",
    ),
    "associations.below_support": (
        "not_knowable_here",
        "Too few stating trials or sponsors to call it a pattern.",
    ),
    "associations.unresolved": (
        "not_knowable_here",
        "Abbreviated silences could reverse the comparison.",
    ),
    "occupancy.occupied": ("settled", "Within this supplied set, a trial definitely occupies the cell."),
    "occupancy.unknown": ("not_knowable_here", "Only possible members; membership is unresolved."),
    "occupancy.empty": (
        "settled",
        "No trial in this supplied set could fit. That is not infeasibility or unmet need.",
    ),
    "near_misses": (
        "your_call",
        "Comparable trials (under the declared representation) chose differently on one feature; "
        "nothing else is proved equal.",
    ),
    "expectations.abstain": ("not_knowable_here", "Too few known observations to state a rarity."),
    "expectations.cell_or_parent": (
        "settled",
        "A computed rarity in bits within the declared cell (or the labelled parent when the cell lacks "
        "support). Rarity is not relevance.",
    ),
}

DECISION_LIST = {
    "purpose": (
        "TrialLedger does not make the person's clinical decisions; it finds them. The decision list is a "
        "design session's main deliverable: each choice that needs clinical judgment, with its evidence "
        "assembled and its consequences computed. Keep it as the session proceeds; hand it over at the end."
    ),
    "entry": {
        "decision": "The choice in clinical words, e.g. 'What ECOG range do we intend?'",
        "evidence": (
            "What the compared trials document, with record addresses, and where the registry is silent."
        ),
        "consequence": (
            "The computed result for each option under consideration, with its deciding premises."
        ),
        "status": "Open, or chosen by the person (their premise, with its origin).",
    },
    "routing": {
        "something_wrong": "Listed first, as a blocker to resolve before other answers are relied on.",
        "your_call": "Becomes an entry.",
        "not_knowable_here": "Recorded as an evidence gap on the entry it affects.",
        "settled": "Cited as context from the entry it informs.",
    },
    "revision": (
        "When the person settles a decision, record it as their premise and recompute what depends on it."
    ),
}

NOTABLE = (
    "'Notable' is computed for design features: an observation is notable when it is rare within a "
    "declared comparison cell (reason corpus expectations: rarity from the cell or its labelled parent, "
    "abstaining without support) and/or when it departs from a declared expectation with no recorded "
    "explanation (deviation status verified_deviation, from the Python building block "
    "TrialLedger.layer2.expectations.deviation_status, which reason does not yet expose). Through reason "
    "or MCP alone, only the rarity half is computed: do not apply the deviation rules by hand and call "
    "the result computed. Expectations and observation states are supplied by the caller, so confirm "
    "them with the person first. 'Significance' is reserved for the founder's derivational significance "
    "(SIGNIFICANCE_WEIGHTING), which is designed but not yet built here; rarity is not significance."
)

QUESTION_VOCABULARY = [
    {
        "words": "could this patient enroll; is X allowed; must everyone have X; does X fit our brief",
        "computed_by": "entailment over the person's confirmed criteria",
        "report": "settled / allowed but not required / depends on, with the deciding premise",
    },
    {
        "words": "do my criteria contradict each other; is the draft consistent",
        "computed_by": "entailment (INCONSISTENT appears for any question while a contradiction stands)",
        "report": "the contradicting premises, both sides",
    },
    {
        "words": "does this record disagree with itself",
        "computed_by": "layer-one registry_checks in the record",
        "report": "the check, both values and its outcome",
    },
    {
        "words": "what treatment setting do these NSCLC criteria imply; which settings remain possible",
        "computed_by": "coordinates (NSCLC only)",
        "report": "explicit narrowing, 'by default' settings and separate proposals",
    },
    {
        "words": "how common or standard is criterion X in these trials",
        "computed_by": "corpus frequency over a declared comparison set",
        "report": "statement rate with its range; silence keeps the range open",
    },
    {
        "words": "is X more common with drug class Y",
        "computed_by": "corpus associations",
        "report": "proposed / below support / unresolved, with counts",
    },
    {
        "words": "unusual; rare",
        "computed_by": "corpus frequency surprisal_bits and expectations rarity",
        "report": "bits within the declared set, or abstention",
    },
    {
        "words": "notable",
        "computed_by": "see notable",
        "report": "rarity and, where computed, deviation status",
    },
    {
        "words": "gap; white space; nobody has tried",
        "computed_by": "corpus occupancy over declared setting/class cells",
        "report": "occupied / unknown / empty within this set; empty is not unmet need",
    },
    {
        "words": "which trials differ only in X; closest comparators",
        "computed_by": "corpus near_misses under a declared representation",
        "report": "the pair, the one differing feature, sponsors and years",
    },
    {
        "words": "significant (derivational significance)",
        "computed_by": "not yet built",
        "report": "say it is not computed yet; offer rarity or deviation if that is what is meant",
    },
    {
        "words": "good; appropriate; best",
        "computed_by": "decompose into computed parts (fits the brief, how common, class pattern, gaps)",
        "report": "the computed parts with their basis; label any remaining judgment as the assistant's",
    },
    {
        "words": "did it work; were the results notable",
        "computed_by": "no computed object: read posted outcomes and safety from the record",
        "report": "values with groups, denominators, units and periods; label interpretation as reading",
    },
]


def _rule() -> dict[str, Any]:
    return {"class": "Rule", "id": "user-choice", "version": "1", "warrants": [DEMONSTRATION_BASIS]}


def _literal(kind: str, key: str, value: dict[str, Any]) -> dict[str, Any]:
    return {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant"},
        "predicate": {"class": "Predicate", "kind": kind, "key": key},
        "value": {"class": "Value", **value},
    }


def _premise(
    ident: str, body: dict[str, Any], modality: str = "required", status: str = "known", cohort: str = ""
) -> dict[str, Any]:
    premise = {
        "class": "ScopedAssertion",
        "id": ident,
        "criterion_ref": f"{DEMONSTRATION_BASIS}#{ident}",
        "modality": modality,
        "body": body,
        "rule": _rule(),
        "status": status,
        "resolution": "resolved",
    }
    if cohort:
        premise["cohort"] = {"class": "Scope", "kind": "cohort_ref", "ref": cohort}
    return premise


def _age(comparison: str, years: float) -> dict[str, Any]:
    return _literal(
        "demographic", "age", {"kind": "quantity", "comparison": comparison, "number": years, "unit": "years"}
    )


def _ecog(comparison: str, score: float) -> dict[str, Any]:
    return _literal("measurement", "ecog_ps", {"kind": "quantity", "comparison": comparison, "number": score})


def _mutation(comparison: str, members: list[str]) -> dict[str, Any]:
    return _literal(
        "disease_attribute",
        "egfr_mutation_type",
        {"kind": "enum", "comparison": comparison, "members": members},
    )


def _holds(kind: str, key: str) -> dict[str, Any]:
    return _literal(kind, key, {"kind": "boolean"})


def worked_session() -> dict[str, Any]:
    """A clinician's draft brief, the assistant's confirmed encoding and the questions it answers."""
    brief = [
        _premise("age", _age("ge", 18)),
        _premise("ecog", {"class": "AllOf", "parts": [_ecog("ge", 0), _ecog("le", 1)]}),
        _premise("egfr", _mutation("in", ["exon19_deletion", "L858R"])),
        _premise("prior_osimertinib", _holds("treatment_history", "prior_osimertinib")),
        _premise(
            "brain_metastases",
            _holds("condition_status", "symptomatic_brain_metastases"),
            modality="excluded",
        ),
        _premise(
            "prior_chemotherapy", _holds("treatment_history", "prior_chemo_advanced"), modality="excluded"
        ),
    ]
    either_mutation = _premise(
        "egfr",
        {
            "class": "AnyOf",
            "parts": [
                _holds("disease_attribute", "exon19_deletion"),
                _holds("disease_attribute", "L858R"),
            ],
        },
    )
    cohorts = [
        _premise(
            f"ecog_{cohort}", {"class": "AllOf", "parts": [_ecog("ge", 0), _ecog("le", upper)]}, cohort=cohort
        )
        for cohort, upper in (("A", 1), ("B", 2))
    ]

    def ask(request: dict[str, Any], **fields: Any) -> dict[str, Any]:
        return {"request": {"operation": "entailment", **request}, **fields}

    steps = [
        ask(
            {"assertions": brief, "query": _age("lt", 18)},
            ask_plain="Could a 16-year-old enroll?",
            expect={"result": "REFUTED", "proof": ["age"], "blockers": []},
            say="No: the age criterion (18 or older) rules it out.",
        ),
        ask(
            {"assertions": brief, "query": _age("ge", 65)},
            ask_plain="Must everyone be at least 65?",
            expect={"result": "UNDETERMINED", "proof": ["age"], "blockers": ["undecided_by_constraints"]},
            say=("No minimum of 65 is required: the age criterion allows adults both below and above 65."),
        ),
        ask(
            {"assertions": brief, "query": _ecog("eq", 2)},
            ask_plain="Could a patient with ECOG 2 enroll?",
            expect={"result": "REFUTED", "proof": ["ecog"], "blockers": []},
            say="No: the performance-status criterion (ECOG 0-1) rules it out.",
        ),
        ask(
            {"assertions": brief, "query": _mutation("eq", ["exon19_deletion"])},
            ask_plain="Must everyone have an exon 19 deletion?",
            expect={"result": "UNDETERMINED", "proof": ["egfr"], "blockers": ["undecided_by_constraints"]},
            say="Allowed but not required: either listed mutation qualifies.",
        ),
        ask(
            {"assertions": brief, "query": _mutation("eq", ["exon20_insertion"])},
            ask_plain="Would an EGFR exon 20 insertion qualify? (reading: one qualifying mutation type)",
            expect={"result": "REFUTED", "proof": ["egfr"], "blockers": []},
            say=(
                "No, under the reading that each patient's mutation type is one of exon 19 deletion or "
                "L858R. That reading assumes one mutation per patient; confirm it before relying on it."
            ),
        ),
        ask(
            {"assertions": [either_mutation], "query": _holds("disease_attribute", "exon20_insertion")},
            ask_plain="Would an EGFR exon 20 insertion qualify? (reading: has exon 19 deletion or L858R)",
            expect={"result": "UNDETERMINED", "proof": [], "blockers": ["no_constraint_mentions_query"]},
            say=(
                "Your criteria do not address exon 20 under this reading: a patient could carry it "
                "alongside a qualifying mutation. The two readings give different answers, so this is the "
                "person's call; ask which they mean."
            ),
        ),
        ask(
            {"assertions": [_premise("age", _age("ge", 18), status="proposed")], "query": _age("lt", 18)},
            ask_plain="Could a 16-year-old enroll? (age reading not yet confirmed)",
            expect={
                "result": "UNDETERMINED",
                "proof": [],
                "blockers": ["no_constraint_mentions_query", "proposed_refused:age"],
            },
            say=(
                "Depends on a reading you have not confirmed: I read the age criterion as 18 or older. Is "
                "that right? Nothing is concluded from an unconfirmed reading."
            ),
        ),
        ask(
            {"assertions": cohorts, "query": _ecog("eq", 2), "context": {"cohort": "A"}},
            ask_plain="Could an ECOG 2 patient enroll in cohort A?",
            expect={"result": "REFUTED", "proof": ["ecog_A"], "blockers": []},
            say="No: cohort A requires ECOG 0-1.",
        ),
        ask(
            {"assertions": cohorts, "query": _ecog("eq", 2)},
            ask_plain="Could an ECOG 2 patient enroll? (no cohort named)",
            expect={
                "result": "UNDETERMINED",
                "proof": ["ecog_A", "ecog_B"],
                "blockers": [
                    "open_scope:cohort_ref:A",
                    "open_scope:cohort_ref:B",
                    "undecided_by_constraints",
                ],
            },
            say=(
                "Depends on the cohort: no in cohort A (ECOG 0-1), allowed in cohort B (ECOG 0-2). Which one?"
            ),
        ),
        ask(
            {"assertions": [*brief, _premise("paediatric", _age("le", 17))], "query": _ecog("eq", 0)},
            ask_plain="Could an ECOG 0 patient enroll? (draft accidentally also requires age 17 or under)",
            expect={"result": "INCONSISTENT", "proof": ["age", "paediatric"], "blockers": []},
            say=(
                "Something is wrong: the criteria contradict each other (18 or older versus 17 or under), "
                "so no question can be answered until one is corrected."
            ),
        ),
    ]
    return {
        "premise_origin": (
            "A demonstration brief, treated as confirmed by the person for this illustration; not registry "
            "facts or a recommended protocol."
        ),
        "brief_in_plain_words": [
            "Adults aged 18 or older.",
            "ECOG performance status 0-1.",
            "EGFR mutation type exon 19 deletion or L858R.",
            "Prior osimertinib required.",
            "Exclude symptomatic brain metastases.",
            "Exclude prior chemotherapy for advanced disease.",
        ],
        "pattern": (
            "Restate the criteria in plain words; ask about each ambiguity (one mutation or compound? which "
            "cohort? is the limit inclusive?); encode only what the person confirms; run; answer in the "
            "person's terms with the deciding premise and category; add each open choice to the decision "
            "list; rerun when a premise changes."
        ),
        "steps": steps,
    }


def answer_guide() -> dict[str, Any]:
    """The roles, the four categories and how every operation's results map to them."""
    return {
        "roles": ROLES,
        "categories": CATEGORIES,
        "entailment": {
            "decisions": {name: list(value) for name, value in ENTAILMENT_DECISIONS.items()},
            "blockers": {name: list(value) for name, value in ENTAILMENT_BLOCKERS.items()},
            "precedence": (
                "Refused envelope first (fix the request; never a clinical answer). Then INCONSISTENT. For "
                "UNDETERMINED, report the most specific blocker: proposed_refused, unresolved_rule, "
                "unresolved_assertion, conflicting, open_scope, unresolved_scope, unresolved_literal, "
                "unspecified_boundary, opaque, resource_bound, no_constraint_mentions_query; "
                "undecided_by_constraints alone means allowed but not required."
            ),
        },
        "translation": (
            "Items marked translation are encoding problems for the assistant to settle with the person "
            "before answering. They are not clinical answers and fall in none of the four categories."
        ),
        "coordinates": {name: list(value) for name, value in COORDINATE_STATES.items()},
        "corpus": {name: list(value) for name, value in CORPUS_RESULTS.items()},
        "decision_list": DECISION_LIST,
        "notable": NOTABLE,
        "confirmation": (
            "Entailment refuses a proposed premise, based on the caller-supplied status flag; it does not "
            "independently verify confirmation or source truth. Confirming a reading makes it the person's "
            "accepted premise, never a registry fact. Coordinates evidence and corpus trials carry only a "
            "reference and a caller-set typed flag, so the operation cannot tell a confirmed premise from "
            "an unconfirmed reading there: confirm with the person before running, and keep the origin in "
            "ref/basis."
        ),
    }
