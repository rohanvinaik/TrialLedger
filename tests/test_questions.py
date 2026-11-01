"""Targeted questions: the envelope and answer validation.

Positive: the envelope holds the target with its offsets, its section heading, the scoping lines before it, a
stem it continues and siblings an explicit "or"/"and" joins it to; a valid answer is a closed verdict with a
quote found verbatim in the envelope.
Negative: nothing else of the trial enters the envelope; a heading is not a criterion; an envelope over budget
is refused, never truncated; a malformed answer, an unknown verdict or a quote not in the envelope is a named
error, never a verdict.
"""

import json

from TrialLedger.criteria import itemize
from TrialLedger.questions import (
    ATOM_CLAIM_OPTIONS,
    answer_schema,
    atom_claim,
    envelope,
    question,
    validate_answer,
)

TEXT = """Inclusion Criteria:

* Age >= 18 years
* Patients must satisfy either:
  a. Previous treatment with X; or
  b. Documented intolerance to X.
Cohort B only:
* ECOG 0-1
* Measurable disease, or
* Evaluable disease

Exclusion Criteria:

* Active autoimmune disease
"""


def pieces():
    code, found = itemize(TEXT)
    assert code == "itemized"
    return found


def index_of(found, start_text):
    return next(i for i, p in enumerate(found) if TEXT[p[2] : p[3]].startswith(start_text))


def test_the_envelope_holds_the_target_its_heading_and_its_scoping_lines():
    found = pieces()
    code, held = envelope(TEXT, found, index_of(found, "* ECOG"))
    assert code == "ok"
    assert held["target"]["text"] == "* ECOG 0-1"
    assert TEXT[held["target"]["start"] : held["target"]["end"]] == "* ECOG 0-1"
    assert held["headings"] == ["Inclusion Criteria:"]
    assert held["scoping"] == ["Cohort B only:"]
    assert held["stem"] == "" and held["siblings"] == []


def test_a_stem_with_its_alternatives_travels_inside_the_target():
    found = pieces()
    code, held = envelope(TEXT, found, index_of(found, "* Patients must"))
    assert code == "ok" and "b. Documented intolerance" in held["target"]["text"]
    assert held["scoping"] == []


def test_an_explicit_or_brings_its_sibling():
    found = pieces()
    _, first = envelope(TEXT, found, index_of(found, "* Measurable"))
    _, second = envelope(TEXT, found, index_of(found, "* Evaluable"))
    assert first["siblings"] == ["* Evaluable disease"]
    assert second["siblings"] == ["* Measurable disease, or"]


def test_nothing_else_of_the_trial_enters_and_the_exclusion_heading_is_its_own():
    found = pieces()
    _, held = envelope(TEXT, found, index_of(found, "* Active"))
    assert held["headings"] == ["Exclusion Criteria:"]
    assert held["scoping"] == [] and held["siblings"] == []
    assert "Age" not in json.dumps(held)


def test_a_heading_is_not_a_criterion_and_a_large_envelope_is_refused():
    found = pieces()
    assert envelope(TEXT, found, 0) == ("not_a_criterion", {})
    assert envelope(TEXT, found, index_of(found, "* ECOG"), budget=10) == ("envelope_over_budget", {})


def test_the_claim_says_the_polarity_of_its_section():
    atom = ("performance_status", "ecog_ps", ("0", "1"), (), 0, 1)
    assert (
        atom_claim(atom, "inclusion")
        == "This inclusion criterion requires participants to have: ecog_ps = 0 | 1"
    )
    assert atom_claim(atom, "exclusion").startswith("This exclusion criterion excludes participants with:")
    lab = ("organ_function", "alt", ("x",), (("comparator", "<="), ("unit", "ULN")), 0, 1)
    assert atom_claim(lab, "unsectioned").endswith("alt = x (comparator <=; unit ULN)")


def test_a_question_is_identified_by_what_the_model_sees():
    found = pieces()
    _, held = envelope(TEXT, found, index_of(found, "* ECOG"))
    first = question("atom_claim", {"claim": "c"}, held, ATOM_CLAIM_OPTIONS)
    assert first == question("atom_claim", {"claim": "c"}, held, ATOM_CLAIM_OPTIONS)
    assert first["id"] != question("atom_claim", {"claim": "d"}, held, ATOM_CLAIM_OPTIONS)["id"]
    assert answer_schema(ATOM_CLAIM_OPTIONS)["properties"]["verdict"]["enum"] == list(ATOM_CLAIM_OPTIONS)


def test_a_valid_answer_quotes_the_envelope():
    found = pieces()
    _, held = envelope(TEXT, found, index_of(found, "* ECOG"))
    good = json.dumps({"verdict": "supported", "quote": "ECOG 0-1"})
    assert validate_answer(good, ATOM_CLAIM_OPTIONS, held) == ("ok", "supported", "ECOG 0-1")
    scoped = json.dumps({"verdict": "insufficient_context", "quote": ""})
    assert validate_answer(scoped, ATOM_CLAIM_OPTIONS, held) == ("ok", "insufficient_context", "")


def test_a_bad_answer_is_a_named_error():
    found = pieces()
    _, held = envelope(TEXT, found, index_of(found, "* ECOG"))
    assert validate_answer("not json", ATOM_CLAIM_OPTIONS, held) == ("malformed", "", "")
    assert validate_answer("[]", ATOM_CLAIM_OPTIONS, held) == ("malformed", "", "")
    extra = json.dumps({"verdict": "supported", "quote": "ECOG", "why": "x"})
    assert validate_answer(extra, ATOM_CLAIM_OPTIONS, held) == ("malformed", "", "")
    typed = json.dumps({"verdict": 1, "quote": "ECOG"})
    assert validate_answer(typed, ATOM_CLAIM_OPTIONS, held) == ("malformed", "", "")
    unknown = json.dumps({"verdict": "probably", "quote": "ECOG"})
    assert validate_answer(unknown, ATOM_CLAIM_OPTIONS, held) == ("unknown_verdict", "", "")
    invented = json.dumps({"verdict": "supported", "quote": "ECOG 0-2"})
    assert validate_answer(invented, ATOM_CLAIM_OPTIONS, held) == ("quote_not_in_envelope", "", "")
    bare = json.dumps({"verdict": "supported", "quote": " "})
    assert validate_answer(bare, ATOM_CLAIM_OPTIONS, held) == ("quote_not_in_envelope", "", "")


def test_a_stem_at_the_same_level_is_carried_and_is_not_a_sibling():
    """Positive: a bullet ending in a colon is the stem of the bullet after it. Negative: the stem is never
    also counted as a joined sibling."""
    text = (
        "Inclusion Criteria:\n\n* Must meet one of the following:\n* Prior treatment with X, or\n"
        "* Intolerance to X\n"
    )
    code, found = itemize(text)
    assert code == "itemized"
    at = next(i for i, p in enumerate(found) if text[p[2] : p[3]].startswith("* Prior"))
    _, held = envelope(text, found, at)
    assert held["stem"] == "* Must meet one of the following:"
    assert held["siblings"] == ["* Intolerance to X"]
