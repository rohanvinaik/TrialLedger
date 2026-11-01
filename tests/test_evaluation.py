"""Evaluation definitions — three levels, one-to-one matching, measures with their denominators.

Positive: a gold record whose quote is the text's own words at its span, with two annotators' reads each
quoting the text at its own span and recorded as source-grounded, is usable; a gold claim and an emitted claim
of the same unit and concept whose spans overlap are paired, one to one, the longer overlap first; matched
claims with the same values and params are correct; precision from an audit of emitted claims alone is
measured with its numerator, denominator, trials, per-trial counts and bounds; recall, miss rate and complete
representation are measured against gold; parameter accuracy is per field; coverage and abstention are over
units; every measure reads its own level only, a claim of another level changing nothing; B7's thresholds read
the seeded cluster-bootstrap lower bound of the measure they name, the same on every run, once the sample
reaches the declared minimum.
Negative: when only emitted claims were audited (no gold sample), recall is not_measured (the spec's
scenario), never 0; a zero denominator is not_measured with no bounds, never 0 or 1; a quote that is not the
text at its span, an unknown level, verdict or resolution, no read, no record version, "agreed" with fewer
than two annotators or with a dissent, and a misstated agreement make a gold record unusable; matching or
judging claims of two levels, and any measure of an unknown level, is refused; a claim is never paired twice,
nor across units, concepts or levels, nor without overlap; an unpaired emitted claim is spurious only in a
unit the gold annotated (elsewhere unresolved); a threshold refuses another measure, an unknown group and a
sample under its minimum; errors concentrated in one trial fail a threshold the pooled rate meets; a measure
not measured never meets a threshold; agreement whose quotes are not the text at their spans, or of one
annotator, is model-review agreement.
"""

from dataclasses import replace

import pytest

from TrialLedger.evaluation import (
    BOOTSTRAP,
    LEVELS,
    MINIMUM_DENOMINATOR,
    THRESHOLD_MEASURE,
    THRESHOLDS,
    Claim,
    GoldRecord,
    Measure,
    Read,
    agreement_kind,
    at_level,
    bounds,
    clustered_lower_bound,
    complete_representation,
    gold_problems,
    judge,
    match,
    miss_rate,
    parameter_accuracy,
    precision,
    precision_group,
    rate,
    recall,
    threshold_verdict,
    unit_rates,
)

# A real criterion (tests/test_banks.py, a 2015-2024 Phase 3 NSCLC record) and its lab thresholds.
TEXT = "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN."
ALT = (4, 34)  # "Alanine aminotransferase (ALT)"
AST = (39, 79)  # "aspartate aminotransferase (AST)≤2.5×ULN"
PARAMS = (("comparator", "≤"), ("unit", "×ULN"), ("value", "2.5"))


def claim(span, concept="nsclc.lab.alt", params=PARAMS, source="gold", nct="NCT00000001", unit="u1"):
    return Claim("mention", nct, "v1", unit, span[0], span[1], concept, (), params, source)


def read(annotator, span, verdict="holds", quote=None):
    return Read(annotator, verdict, TEXT[span[0] : span[1]] if quote is None else quote, span[0], span[1])


def gold(span, concept="nsclc.lab.alt", resolution="agreed", **kwargs):
    made = claim(span, concept, **kwargs)
    reads = (read("claude", span), read("codex", span))
    return GoldRecord(made, TEXT[span[0] : span[1]], reads, "source_grounded", resolution)


def test_a_grounded_gold_record_is_usable_and_a_misquote_is_not():
    assert gold_problems(gold(ALT), TEXT) == ()
    assert gold_problems(replace(gold(ALT), quote="alanine aminotransferase"), TEXT) == ("quote_mismatch",)
    bad = GoldRecord(replace(claim((70, 99)), level="vibe", record_version=""), "", (), "", "maybe")
    assert gold_problems(bad, TEXT) == (
        "unknown_level",
        "unversioned_record",
        "span_out_of_bounds",
        "quote_mismatch",
        "no_annotator",
        "unknown_resolution",
        "misstated_agreement",
    )
    assert LEVELS == ("mention", "scoped_assertion", "eligibility")


def test_the_gold_record_keeps_each_annotators_verdict_and_quote():
    record = gold(ALT)
    assert [(r.annotator, r.verdict, r.quote) for r in record.reads] == [
        ("claude", "holds", "Alanine aminotransferase (ALT)"),
        ("codex", "holds", "Alanine aminotransferase (ALT)"),
    ]
    # an annotator may quote other words than the claim's, provided they are the text at its own span
    other = replace(record, reads=(read("claude", ALT), read("codex", (29, 34))))
    assert gold_problems(other, TEXT) == ()
    # an unsure read is kept on an adjudicated record
    adjudicated = replace(
        record, reads=(read("claude", ALT), read("codex", ALT, "unsure")), resolution="adjudicated"
    )
    assert gold_problems(adjudicated, TEXT) == ()


def test_agreed_needs_two_annotators_who_both_say_it_holds():
    alone = replace(gold(ALT), reads=(read("claude", ALT),), agreement="model_review_agreement")
    assert gold_problems(alone, TEXT) == ("agreed_without_two_annotators",)
    twice = replace(alone, reads=(read("claude", ALT), read("claude", ALT)))
    assert gold_problems(twice, TEXT) == ("agreed_without_two_annotators",)  # one annotator twice is one
    dissent = replace(gold(ALT), reads=(read("claude", ALT), read("codex", ALT, "does_not_hold")))
    assert gold_problems(dissent, TEXT) == ("agreed_without_assent",)
    odd = replace(gold(ALT), reads=(read("claude", ALT), read("codex", ALT, "maybe")))
    assert gold_problems(odd, TEXT) == ("unknown_verdict", "agreed_without_assent")
    assert gold_problems(replace(alone, resolution="unresolved"), TEXT) == ()


def test_a_misstated_agreement_is_refused():
    claimed = replace(gold(ALT), agreement="model_review_agreement")
    assert gold_problems(claimed, TEXT) == ("misstated_agreement",)
    paraphrased = replace(gold(ALT), reads=(read("claude", ALT), read("codex", ALT, quote="ALT")))
    assert gold_problems(paraphrased, TEXT) == ("misstated_agreement",)
    assert gold_problems(replace(paraphrased, agreement="model_review_agreement"), TEXT) == ()


def test_matching_is_one_to_one_longest_overlap_first():
    golds = [claim((4, 34))]
    emitted = [claim((4, 20), source="bank:x"), claim((4, 34), source="bank:x")]
    assert match(golds, emitted) == [(0, 1)]  # the longer overlap wins; the other stays unpaired
    two = [claim((4, 34)), claim((4, 34))]
    assert match(two, [claim((4, 34), source="bank:x")]) == [(0, 0)]  # ties: the earlier gold claim


def test_no_pair_across_units_concepts_levels_or_without_overlap():
    g = claim(ALT)
    assert match([g], [claim(ALT, unit="u2")]) == []
    assert match([g], [claim(ALT, concept="nsclc.lab.ast")]) == []
    with pytest.raises(ValueError, match="different levels"):
        match([g], [replace(claim(ALT), level="eligibility")])
    assert match([g], [claim((34, 39))]) == []  # touching, not overlapping: half-open spans


def test_judgements_after_matching():
    golds = [gold(ALT), gold(AST, "nsclc.lab.ast"), gold((0, 3), "nsclc.lab.x", resolution="unresolved")]
    emitted = [
        claim(ALT, source="bank:organ_function"),
        claim(AST, "nsclc.lab.ast", params=(("comparator", "<"),), source="bank:organ_function"),
        claim((0, 3), "nsclc.age", source="bank:age"),
        claim(ALT, unit="other", source="bank:organ_function"),
    ]
    assert judge(golds, emitted) == (
        ["correct", "wrong", "unresolved"],
        ["correct", "wrong", "spurious", "unresolved"],
    )


def test_recall_is_not_measured_when_only_emitted_claims_were_audited():
    emitted = [claim(ALT, source="bank:organ_function"), claim(AST, "nsclc.lab.ast", source="bank:o")]
    audited = precision("mention", emitted, ["correct", "wrong"])
    assert (audited.status, audited.numerator, audited.denominator, audited.trials) == ("measured", 1, 2, 1)
    missing = recall("mention", None, emitted)
    assert missing.status == "not_measured" and missing.lower is None and missing.note
    assert recall("mention", [], emitted).status == "not_measured"


def test_recall_and_miss_rate_against_gold():
    golds = [gold(ALT), gold(AST, "nsclc.lab.ast"), gold(ALT, nct="NCT00000002")]
    emitted = [claim(ALT, source="bank:o")]
    found = recall("mention", golds, emitted)
    assert (found.numerator, found.denominator, found.trials, found.lower) == (1, 3, 2, 1 / 3)
    missed = miss_rate("mention", golds, emitted)
    assert (missed.numerator, missed.denominator) == (2, 3)
    assert miss_rate("mention", [], emitted).status == "not_measured"


def test_unresolved_labels_bound_a_rate():
    assert bounds(6, 2, 2) == (0.6, 0.8)
    assert bounds(0, 0, 0) is None
    measured = rate(
        "precision",
        "mention",
        [("A", "correct"), ("A", "unresolved"), ("B", "wrong")],
        ("correct",),
        ("wrong",),
    )
    assert (measured.lower, measured.upper, measured.trials) == (1 / 3, 2 / 3, 2)
    empty = rate("precision", "mention", [("A", "other")], ("correct",), ("wrong",))
    assert (empty.status, empty.denominator, empty.lower, empty.upper) == ("not_measured", 0, None, None)


def test_complete_representation_over_annotated_units():
    golds = [gold(ALT), gold(AST, "nsclc.lab.ast"), gold(ALT, unit="u2")]
    emitted = [claim(ALT, source="bank:o"), claim(AST, "nsclc.lab.ast", source="bank:o")]
    emitted.append(claim(ALT, unit="u2", source="bank:o"))
    assert complete_representation("mention", golds, emitted).numerator == 2
    spurious = [*emitted, claim((0, 3), "nsclc.age", unit="u2", source="bank:age")]
    found = complete_representation("mention", golds, spurious)
    assert (found.numerator, found.denominator) == (1, 2)
    assert complete_representation("mention", [], emitted).status == "not_measured"


def test_parameter_accuracy_is_per_field():
    golds = [gold(ALT), gold(AST, "nsclc.lab.ast")]
    emitted = [claim(ALT, source="bank:o"), claim(AST, "nsclc.lab.ast", params=PARAMS[:2], source="bank:o")]
    found = parameter_accuracy("mention", golds, emitted)
    assert list(found) == ["comparator", "unit", "value"]
    assert (found["value"].numerator, found["value"].denominator) == (1, 2)
    assert (found["unit"].numerator, found["unit"].denominator) == (2, 2)
    assert parameter_accuracy("mention", [gold(ALT, resolution="unresolved")], emitted[:1]) == {}


def test_coverage_and_abstention_over_units():
    units = [("NCT1", "v1", "u1"), ("NCT1", "v1", "u2"), ("NCT2", "v1", "u1")]
    emitted = [claim(ALT, nct="NCT1", source="bank:o")]
    coverage, abstention = unit_rates("mention", units, emitted, {("NCT2", "v1", "u1")})
    assert (coverage.numerator, coverage.denominator, coverage.trials) == (1, 3, 2)
    assert (abstention.numerator, abstention.denominator) == (1, 3)
    assert unit_rates("mention", [], emitted, set())[0].status == "not_measured"


def other_level(record_or_claim, level="eligibility"):
    if isinstance(record_or_claim, GoldRecord):
        return replace(record_or_claim, claim=replace(record_or_claim.claim, level=level))
    return replace(record_or_claim, level=level)


def test_every_measure_reads_its_own_level_only():
    golds = [gold(ALT), gold(AST, "nsclc.lab.ast")]
    emitted = [claim(ALT, source="bank:o"), claim(AST, "nsclc.lab.ast", params=PARAMS[:2], source="bank:o")]
    # the same claims again at the eligibility level, all wrong or unmatched there
    noise_gold = [other_level(gold((0, 3), "nsclc.age"))]
    noise_emitted = [other_level(claim(ALT, params=(), source="bank:o")), other_level(claim((40, 50)))]
    mixed_gold, mixed_emitted = golds + noise_gold, emitted + noise_emitted
    assert at_level("mention", mixed_gold, mixed_emitted) == (golds, emitted)
    assert recall("mention", mixed_gold, mixed_emitted) == recall("mention", golds, emitted)
    assert miss_rate("mention", mixed_gold, mixed_emitted) == miss_rate("mention", golds, emitted)
    whole = complete_representation("mention", golds, emitted)
    assert complete_representation("mention", mixed_gold, mixed_emitted) == whole
    assert parameter_accuracy("mention", mixed_gold, mixed_emitted) == parameter_accuracy(
        "mention", golds, emitted
    )
    verdicts = ["correct", "wrong", "wrong", "spurious"]
    assert precision("mention", mixed_emitted, verdicts) == precision("mention", emitted, verdicts[:2])
    units = [("NCT00000001", "v1", "u1")]
    assert (
        unit_rates("mention", units, noise_emitted, set())[0].numerator == 0
    )  # another level covers nothing
    eligibility = recall("eligibility", mixed_gold, mixed_emitted)
    assert (eligibility.numerator, eligibility.denominator) == (0, 1)


def test_mixing_levels_is_refused():
    with pytest.raises(ValueError, match="unknown level"):
        at_level("mentions", [gold(ALT)], [claim(ALT)])
    assert at_level("eligibility", None, [claim(ALT)]) == ([], [])
    with pytest.raises(ValueError, match="different levels"):
        judge([gold(ALT)], [other_level(claim(ALT, source="bank:o"))])
    with pytest.raises(ValueError, match="different levels"):
        match([claim(ALT), other_level(claim(AST))], [])
    for measure in (recall, miss_rate, complete_representation, parameter_accuracy):
        with pytest.raises(ValueError, match="unknown level"):
            measure("mentions", [gold(ALT)], [])
    with pytest.raises(ValueError, match="unknown level"):
        precision("all", [claim(ALT)], ["correct"])
    with pytest.raises(ValueError, match="unknown level"):
        unit_rates("all", [], [], set())


def judged(spec):
    """Items `(nct, judgement)` from per-trial counts (nct, correct, wrong, unresolved)."""
    out = []
    for nct, correct, wrong, unresolved in spec:
        out += [(nct, "correct")] * correct + [(nct, "wrong")] * wrong + [(nct, "unresolved")] * unresolved
    return out


def precision_of(spec):
    return rate("precision", "mention", judged(spec), ("correct",), ("wrong", "spurious"))


CLEAN = [(f"NCT{i:08}", 10, 0, 0) for i in range(9)]
SEEDED = (str(BOOTSTRAP["seed"]), int(BOOTSTRAP["resamples"]), int(BOOTSTRAP["lower_rank"]))


def test_a_measure_carries_its_per_trial_counts():
    measured = precision_of([("B", 1, 1, 0), ("A", 2, 0, 1)])
    assert measured.clusters == (("A", 2, 0, 1), ("B", 1, 1, 0))
    assert precision_of([]).clusters == ()


def test_the_lower_bound_is_a_seeded_cluster_bootstrap():
    assert BOOTSTRAP == {"seed": "evaluation-bootstrap-2026-11-01", "resamples": 2000, "lower_rank": 50}
    spread = precision_of([*CLEAN, ("NCT00000009", 9, 1, 0)]).clusters
    assert clustered_lower_bound(spread, *SEEDED) == 0.97
    assert clustered_lower_bound(spread, *SEEDED) == clustered_lower_bound(spread, *SEEDED)  # every run
    one = (("A", 3, 1, 0),)
    assert clustered_lower_bound(one, "s", 10, 1) == 0.75  # one trial: every draw is that trial
    # unresolved items count as misses: the bound is under C/(C+W), never the unresolved bound alone
    assert clustered_lower_bound((("A", 3, 0, 1),), "s", 10, 10) == 0.75
    assert clustered_lower_bound((), "s", 10, 1) is None
    assert clustered_lower_bound(one, "s", 10, 11) is None
    assert clustered_lower_bound(one, "s", 0, 1) is None
    assert clustered_lower_bound((("A", 0, 0, 0),), "s", 10, 1) is None


def test_thresholds_read_the_clustered_lower_bound_of_their_own_measure():
    assert THRESHOLDS["precision_lower_bound"] == {"consequential": 0.95, "other": 0.90}
    assert THRESHOLD_MEASURE == {"precision_lower_bound": "precision", "recall_target": "recall"}
    spread = precision_of([*CLEAN, ("NCT00000009", 9, 1, 0)])  # 99 of 100, the error alone in one trial
    assert threshold_verdict(spread, "precision_lower_bound", precision_group("polarity")) == "meets"
    assert precision_group("polarity") == "consequential" and precision_group("unit") == "other"
    found = recall("mention", [gold(ALT, nct=f"NCT{i:08}") for i in range(30)], [])
    assert threshold_verdict(found, "recall_target", "general_packages") == "below"


def test_errors_in_one_trial_fail_a_threshold_the_pooled_rate_meets():
    concentrated = precision_of([*CLEAN, ("NCT00000009", 5, 5, 0)])  # 95 of 100, the errors in one trial
    assert concentrated.lower == 0.95  # the pooled rate is at the consequential threshold
    assert threshold_verdict(concentrated, "precision_lower_bound", "consequential") == "below"
    assert threshold_verdict(concentrated, "precision_lower_bound", "other") == "below"


def test_a_threshold_refuses_another_measure_a_small_sample_and_an_unknown_group():
    spread = precision_of([*CLEAN, ("NCT00000009", 9, 1, 0)])
    assert (
        threshold_verdict(replace(spread, name="recall"), "precision_lower_bound", "other") == "wrong_measure"
    )
    assert threshold_verdict(spread, "recall_target", "general_packages") == "wrong_measure"
    assert threshold_verdict(spread, "precision_lower_bound", "polarity") == "unknown_threshold"
    assert threshold_verdict(spread, "f1_floor", "other") == "unknown_threshold"
    assert MINIMUM_DENOMINATOR["precision_lower_bound"] == {"items": 30, "trials": 5}
    few_items = precision_of([(f"NCT{i:08}", 5, 0, 0) for i in range(5)])  # 25 items, all correct
    assert threshold_verdict(few_items, "precision_lower_bound", "other") == "insufficient_denominator"
    few_trials = precision_of([(f"NCT{i:08}", 10, 0, 0) for i in range(4)])  # 40 items in 4 trials
    assert threshold_verdict(few_trials, "precision_lower_bound", "other") == "insufficient_denominator"
    unmeasured = Measure("precision", "mention", 0, 0, 0, None, None, "not_measured", "")
    assert threshold_verdict(unmeasured, "precision_lower_bound", "other") == "not_measured"
    no_clusters = replace(spread, clusters=())
    assert threshold_verdict(no_clusters, "precision_lower_bound", "other") == "not_measured"


def test_agreement_is_source_grounded_only_with_quotes_at_their_spans():
    assert agreement_kind(TEXT, [read("claude", ALT), read("codex", (71, 79))]) == "source_grounded"
    assert (
        agreement_kind(TEXT, [read("claude", ALT), read("codex", ALT, quote="")]) == "model_review_agreement"
    )
    assert agreement_kind(TEXT, [read("claude", ALT), read("codex", ALT, quote="ALT ≤ 2.5 ULN")]) == (
        "model_review_agreement"
    )
    # words that stand elsewhere in the text are not the text at the read's span
    moved = read("codex", (0, 3), quote="ALT")
    assert agreement_kind(TEXT, [read("claude", ALT), moved]) == "model_review_agreement"
    assert agreement_kind(TEXT, [read("claude", ALT)]) == "model_review_agreement"
    assert agreement_kind(TEXT, [read("claude", ALT), read("claude", AST)]) == "model_review_agreement"
    assert agreement_kind(TEXT, [read("claude", ALT), read("codex", (70, 99))]) == "model_review_agreement"
