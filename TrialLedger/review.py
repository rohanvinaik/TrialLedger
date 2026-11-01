"""The review queue: what the symbolic system cannot cleanly resolve, flagged for a domain expert or an LLM.

The founder's instruction, 2026-10-31, paraphrased: flag apparent violations and unresolvable elements, and
surface them for resolution by a human domain expert or an LLM directly; never force what this symbolic system
cannot cleanly resolve. So nothing here resolves anything. Each flag is a typed question with a closed set of
answers (the TriageGeist contract: the outside resolver is handed a bounded, well-posed question, and its
answer can be checked against the record), the evidence it rests on, and an empty answer.
"""

from __future__ import annotations

PRIORITY = {
    "coordinate_conflict": 1,
    "verified_deviation": 1,
    "expectation_unresolved": 2,
    "drug_class_unresolved": 3,
    "eligibility_abbreviated": 3,
}

Flag = tuple[
    str, str, str, str, list[str], str, list[str]
]  # kind, element, why, priority, evidence, question, options


def flags_for(
    drugs: list[tuple[str, str]],
    coordinates: dict[str, tuple[list[str], str, list[str]]],
    full_domains: dict[str, list[str]],
    observations: dict[str, tuple[str, str, list[str]]],
    known_classes: list[str],
    abbreviations: list[tuple[str, str]],
) -> list[Flag]:
    """The review flags of one trial (pure — pinned).

    `drugs` are (experimental drug, class state); `coordinates` map a coordinate to (domain, state, the
    criteria or relations that removed values); `full_domains` give each coordinate's every value;
    `observations` map an expectation to (status, reason, cited texts); `known_classes` are the classes the
    population's classified drugs carry; `abbreviations` are (scope, where and what) for each marker by which
    the record says its eligibility criteria are abbreviated. Flags, in this order:
      drug_class_unresolved   — a drug whose state is unresolved or lookup_failed: "What is <drug>'s
                                pharmacologic class?", options the known classes and "none of these";
      coordinate_conflict     — a coordinate whose domain is empty: which value the trial's criteria state,
                                options its every value and "the trial has cohorts that differ";
      expectation_unresolved  — an unresolved observation: whether the trial excludes it, options "excludes",
                                "admits", "differs by cohort", "not stated";
      verified_deviation      — an explicitly_negated observation: whether the trial admits it, options
                                "admits (confirmed)", "excludes (the reading is wrong)";
      eligibility_abbreviated — one flag for a record with any abbreviation marker, every marker its
                                evidence: whether the record says it lists only some of its criteria, as
                                read, options "abbreviated (confirmed)", "not abbreviated (the marker is
                                misread)". Wherever its silence is counted, it is unresolved.
    Each flag is (kind, element, why, priority, evidence, question, options); a trial with nothing to flag has
    an empty list.
    """
    flags: list[Flag] = []
    for drug, state in drugs:
        if state in ("unresolved", "lookup_failed"):
            flags.append(
                (
                    "drug_class_unresolved",
                    drug,
                    f"RxClass and the record's own entry give no class ({state})",
                    str(PRIORITY["drug_class_unresolved"]),
                    [],
                    f"What is the pharmacologic class (mechanism) of {drug}?",
                    [*known_classes, "none of these"],
                )
            )
    for name, (_domain, state, causes) in coordinates.items():
        if state == "conflict":
            flags.append(
                (
                    "coordinate_conflict",
                    name,
                    "the trial's criteria, or the relations, exclude every value",
                    str(PRIORITY["coordinate_conflict"]),
                    list(causes),
                    f"Which {name} do the trial's criteria state?",
                    [*full_domains.get(name, []), "the trial has cohorts that differ"],
                )
            )
    for expectation, (status, reason, cited) in observations.items():
        if status == "unresolved":
            flags.append(
                (
                    "expectation_unresolved",
                    expectation,
                    reason,
                    str(PRIORITY["expectation_unresolved"]),
                    list(cited),
                    f"Does the trial exclude what {expectation} expects it to?",
                    ["excludes", "admits", "differs by cohort", "not stated"],
                )
            )
        elif status == "explicitly_negated":
            flags.append(
                (
                    "verified_deviation",
                    expectation,
                    "the trial's criteria admit what the expectation expects excluded",
                    str(PRIORITY["verified_deviation"]),
                    list(cited),
                    "Does the trial admit it, as read?",
                    ["admits (confirmed)", "excludes (the reading is wrong)"],
                )
            )
    if abbreviations:
        scopes = sorted({scope for scope, _ in abbreviations})
        flags.append(
            (
                "eligibility_abbreviated",
                "eligibility",
                f"the record says its criteria are abbreviated ({', '.join(scopes)})",
                str(PRIORITY["eligibility_abbreviated"]),
                [f"[{scope}] {said}" for scope, said in abbreviations],
                "Does the record say it lists only some of its eligibility criteria, as read?",
                ["abbreviated (confirmed)", "not abbreviated (the marker is misread)"],
            )
        )
    return flags
