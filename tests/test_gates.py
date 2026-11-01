"""Gates on the auditor's answers, mention-claim phrasing, and the quote normalizer (the auditor pilot,
2026-11-01).

Positive: a named-condition claim reads in words; a "wrong_value" on a named-condition claim the rules re-
derive in the same effective section and window is overruled; a quote that differs only by markdown escapes,
whitespace, quotation marks or a trailing ellipsis lies in the envelope.
Negative: the gate never fires on another verdict, another kind, another concept, a claim whose concept the
text does not name, a claim in the other section, or a different window; an invented quote, an empty quote or
an ellipsis alone lies nowhere."""

from TrialLedger.criteria import itemize
from TrialLedger.gates import mention_value_gate
from TrialLedger.questions import ATOM_CLAIM_OPTIONS, atom_claim, envelope, normal_text, question, quote_in


def claim_question(text, concept_value, section, params=()):
    code, pieces = itemize(text)
    index = next(i for i, p in enumerate(pieces) if p[0] == "criterion")
    _, held = envelope(text, pieces, index)
    atom = ("conditions", "condition", (concept_value,), tuple(params), 0, 1)
    target = {
        "nct": "NCT1",
        "piece": index,
        "atom": 0,
        "claim": atom_claim(atom, section),
        "concept": "condition",
    }
    target |= {"values": [concept_value], "params": [list(p) for p in params], "section": section}
    return question("atom_claim", target, held, ATOM_CLAIM_OPTIONS)


def test_a_mention_claim_reads_in_words():
    atom = ("conditions", "condition", ("pregnancy_or_breastfeeding",), (), 0, 1)
    assert (
        atom_claim(atom, "exclusion")
        == "This exclusion criterion excludes participants who have: pregnancy or breastfeeding"
    )
    timed = ("conditions", "condition", ("recent_surgery",), (("window", "4 weeks"),), 0, 1)
    assert atom_claim(timed, "inclusion").endswith("to have: recent surgery (window 4 weeks)")
    ecog = ("performance_status", "ecog_ps", ("0", "1"), (), 0, 1)
    assert atom_claim(ecog, "inclusion").endswith("ecog_ps = 0 | 1")


def test_the_gate_overrules_a_value_challenge_the_rules_rederive():
    excluded = claim_question(
        "Exclusion Criteria:\n\n* Pregnant women\n", "pregnancy_or_breastfeeding", "exclusion"
    )
    assert mention_value_gate(excluded, "wrong_value")
    windowed = claim_question(
        "Exclusion Criteria:\n\n* Currently pregnant or had a pregnancy-related procedure "
        "within prior 3 months\n",
        "pregnancy_or_breastfeeding",
        "exclusion",
        (("window", "3 months"),),
    )
    assert mention_value_gate(windowed, "wrong_value")


def test_the_gate_never_fires_outside_its_rule():
    excluded = claim_question(
        "Exclusion Criteria:\n\n* Pregnant women\n", "pregnancy_or_breastfeeding", "exclusion"
    )
    assert not mention_value_gate(excluded, "unsupported")
    assert not mention_value_gate(excluded, "supported")
    assert not mention_value_gate({**excluded, "kind": "outcome_endpoint"}, "wrong_value")
    other = claim_question("Exclusion Criteria:\n\n* Pregnant women\n", "bleeding_thrombosis", "exclusion")
    assert not mention_value_gate(other, "wrong_value")
    flipped = claim_question(
        "Inclusion Criteria:\n\n* Women must have a negative serum pregnancy test\n",
        "pregnancy_or_breastfeeding",
        "inclusion",
    )
    assert not mention_value_gate(flipped, "wrong_value")
    wrong_window = claim_question(
        "Exclusion Criteria:\n\n* Pregnant women\n",
        "pregnancy_or_breastfeeding",
        "exclusion",
        (("window", "2 years"),),
    )
    assert not mention_value_gate(wrong_window, "wrong_value")
    lab = {**excluded, "target": {**excluded["target"], "concept": "lab"}}
    assert not mention_value_gate(lab, "wrong_value")


def test_a_quote_differing_only_in_form_is_found():
    texts = ["* Subjects who drink more than 3 glasses of alcohol per day (\\> 30g of alcohol per day);"]
    assert quote_in(
        "* Subjects who drink more than 3 glasses of alcohol per day (> 30g of alcohol per day);", texts
    )
    assert quote_in('"Subjects who drink   more than 3 glasses"', texts)
    assert quote_in("* Subjects who drink more than 3 glasses...", texts)
    assert quote_in("* Subjects who drink more than 3 glasses…", texts)
    assert normal_text("  a\\>b\n  c ") == "a>b c"


def test_an_invented_or_empty_quote_lies_nowhere():
    texts = ["* Subjects who drink more than 3 glasses of alcohol per day"]
    assert not quote_in("* Subjects who drink more than 4 glasses", texts)
    assert not quote_in("...", texts)
    assert not quote_in("", texts)
    assert not quote_in("unsupported", texts)
