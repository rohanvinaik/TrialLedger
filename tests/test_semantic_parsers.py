"""The shared parsers: numbers, comparators, units, reference expressions, durations, windows and intervals,
read from the original criterion text with half-open spans on it.

The criteria are real: the NSCLC criteria of tests/test_banks.py (2015-2024 Phase 3 records, as quoted there)
and the pilot's of tests/test_pilot_corrections.py (the 18-trial stratified sample); the spec's scenario
("HbA1c ≤8.0% ... within six months before randomization") is the change's own; a case marked constructed is
written here for a form no real criterion in the tests holds.

Positive: "8.0" is read as written, "six" and "twenty-four" as written numbers, "1,234.5" with its grouping;
the API's escaped comparators ("=\\<", "\\>=", "\\>", "\\<") and the word forms are read, the longest first
("less than or equal to" is ≤); units carry their UCUM form ("mL/min", "× 10^9/L" as 10*9/L, "/mm\\^3" as
/mm3, "mg/dl" as mg/dL, years as a) and a unit with none is kept as written and named unmapped ("G/L",
"half-lives"); "2.5×ULN", "3 x ULN", "1.5 × ULN" and "times the institutional upper limit of normal" are
references; a window keeps its anchor as written ("the first dose of IP", "randomization", "dosing") and its
bounds as the words give them (within: unspecified; "less than or equal to": inclusive); intervals keep their
inclusivity explicit ("≥ 18 years and \\<75 years" is [18, 75)) or unspecified ("18 to 75 years", "0\\~1",
"0 to 49%", "6 through 35 years"); ">= 1.5 x 10^9/L" is a bound with its unit; every span on every real
criterion lies in the text and holds the words its reading claims, the same on every run.
Negative: no number is read inside a name ("HbA1c", "PD-L1", "CTLA-4", "B12") or as a sign after a digit
("0-1"); "50,000" is ambiguous (a grouping mark or a decimal mark), never guessed, and "0,1" is abstained (a
decimal comma or a list); "overall" is no comparator, nor is "> =" a strict one; "× ULN" is never a unit, and
"≤ ULN" has no factor of 1; "and/or", "AST/ALT", "109/L" and "H." are no unit; a number before a factor or
digits not read ("1.5 × ULRR", "100 109/L") is no bound, and a factor after its reference ("ULN x 2.5") is
abstained, never lost; "Life expectancy ≥ 12 weeks" and "for \\< 4 weeks" are no window, and "before or after"
is no one orientation; "4 weeks prior to randomization" is ambiguous (within, or at least); "within ≥ 5 years
prior to enrollment" is abstained; "1 or 2" is no interval, nor are two bounds on one side or two different
units; a start outside the text is abstained by every reader.
"""

import pytest
from test_semantic_contracts import real_criteria

from TrialLedger.layer2.semantics import parsers
from TrialLedger.layer2.semantics.contracts import Span
from TrialLedger.layer2.semantics.parsers import (
    Parse,
    read_comparator,
    read_duration,
    read_interval,
    read_number,
    read_reference,
    read_unit,
    read_window,
)

# by name, each called through the module at the time of the call
READERS = (
    "read_number",
    "read_comparator",
    "read_unit",
    "read_reference",
    "read_duration",
    "read_window",
    "read_interval",
)
ROLES = {"read_number": "value", "read_comparator": "comparator", "read_unit": "unit"}
PILOT = (
    "* Eastern Cooperative Oncology Group (ECOG) performance status =\\< 1 (Karnofsky \\>= 70%)",
    "* Serum creatinine \\> 1.4 mg/dl (female) or \\> 1.5 mg/dl (male).",
    "* Platelet count \\> 50,000/mm\\^3 (within 6 weeks)",
    "* Subject is a male or non-pregnant, non-lactating female age 6 through 35 years",
    "* Major surgery 4 weeks prior to randomization",
    "* Treatment with anticoagulant within 7 days of dosing.",
    "* Currently pregnant or had a pregnancy-related procedure within prior 3 months",
    "* Initiation of sleep aids (melatonin, antihistamines) for \\< 4 weeks",
    "* Use of immunosuppressive drugs within 4 weeks",
)


def at(text, word, nth=0):
    """The position of the nth occurrence of word in text."""
    position = -1
    for _ in range(nth + 1):
        position = text.index(word, position + 1)
    return position


def words(text, parse):
    return [(span.role, text[span.start : span.end]) for span in parse.spans]


def reading(parse, index=0):
    return dict(parse.readings[index])


# ── numbers ─────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, word, value, written",
    [
        ("HbA1c ≤8.0% and no myocardial infarction", "8.0", "8.0", "8.0"),
        ("5. Eastern Cooperative Oncology Group (ECOG) performance status of ≤1.", "1.", "1", "1"),
        ("within six months before randomization", "six", "6", "six"),
        ("Twenty-four hours after dosing (constructed)", "Twenty", "24", "Twenty-four"),
        ("* Creatinine clearance (eGFR) ≥ 45 mL/min", "45", "45", "45"),
        ("a total of 1,234.5 units (constructed)", "1,234", "1234.5", "1,234.5"),
        ("z-score ≥ -2 (constructed)", "-2", "-2", "-2"),
        ("QTc ≤ 0.470 s (constructed)", "0.470", "0.470", "0.470"),
        ("a dose of 1,000,000 units (constructed)", "1,000", "1000000", "1,000,000"),
        ("a six-month washout (constructed)", "six", "6", "six"),
    ],
)
def test_a_number_is_read_as_written(text, word, value, written):
    parse = read_number(text, at(text, word))
    assert parse.status == "parsed" and parse.note == ""
    assert parse.readings == ((("value", value), ("as_written", written)),)
    assert words(text, parse) == [("value", written)]


def test_a_mark_that_may_group_or_divide_is_ambiguous_never_guessed():
    text = PILOT[2]
    parse = read_number(text, at(text, "50,000"))
    assert parse == Parse(
        "number",
        "ambiguous",
        ((("value", "50000"), ("as_written", "50,000")), (("value", "50.000"), ("as_written", "50,000"))),
        (Span("value", at(text, "50,000"), at(text, "50,000") + 6),),
        at(text, "/mm"),
        "a grouping mark or a decimal mark",
    )
    assert [reading(read_number("1.500 mg (constructed)", 0), i)["value"] for i in (0, 1)] == [
        "1500",
        "1.500",
    ]


@pytest.mark.parametrize(
    "text, word, note",
    [
        ("HbA1c ≤8.0%", "1c", "inside a name"),
        ("* Histologically confirmed NSCLC with any PD-L1 TPS", "1 TPS", "inside a name"),
        ("6. No prior exposure to any anti CTLA-4, anti-PD-1", "-4", "inside a name"),
        ("6. No prior exposure to any anti CTLA-4, anti-PD-1", "4,", "inside a name"),
        ("* Severe Vitamin B12 deficiency.", "12", "inside a name"),
        ("2. ECOG score 0-1;", "-1", "a dash after a digit: a range, not a sign"),
        ("ECOG 0,1 (constructed)", "0,1", "a comma between digits: a decimal comma or a list"),
        ("1.2.3 (constructed)", "1.2", "marks that are no grouping"),
        ("1,234,5 (constructed)", "1,2", "marks that are no grouping"),
        ("1.234,567.8 (constructed)", "1.2", "marks that are neither a grouping nor one decimal mark"),
        ("0,123.5 (constructed)", "0,1", "marks that are neither a grouping nor one decimal mark"),
        ("* Other inclusion criteria may apply.", "Other", "no number"),
        ("someone (constructed)", "one", "inside a name"),
    ],
)
def test_no_number_is_read_inside_a_name_or_guessed(text, word, note):
    start = at(text, word)
    assert read_number(text, start) == Parse("number", "abstained", (), (), start, note)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("start", [-1, 9])
def test_a_start_outside_the_text_is_abstained(reader, start):
    parse = getattr(parsers, reader)("* ECOG 1", start)
    assert (parse.status, parse.readings, parse.spans, parse.end) == ("abstained", (), (), start)
    assert parse.note == "a start outside the text"


def test_the_end_of_the_text_is_inside_it():
    assert read_number("ECOG 1", 6).note == "no number"
    assert read_comparator("", 0) == Parse("comparator", "abstained", (), (), 0, "no comparator")


# ── comparators ─────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, word, sign, written",
    [
        (PILOT[0], "=\\<", "≤", "=\\<"),
        (PILOT[0], "\\>=", "≥", "\\>="),
        (PILOT[1], "\\>", ">", "\\>"),
        ("2. Age ≥ 18 years and \\<75 years male or females;", "\\<", "<", "\\<"),
        ("2. Age ≥ 18 years and \\<75 years male or females;", "≥", "≥", "≥"),
        (
            "* Any active malignancy less than or equal to 2 years before randomization",
            "less",
            "≤",
            "less than or equal to",
        ),
        ("AEs Grade 3-5 With a Difference in Incidence Rate of at Least 2%", "at Least", "≥", "at Least"),
        (
            "8. Aged 18 to 75 years, ECOG PS: 0\\~1, estimated survival duration more than 3 months.",
            "more",
            ">",
            "more than",
        ),
        (PILOT[7], "\\<", "<", "\\<"),
        ("age >or= 18 (constructed)", ">", "≥", ">or="),
        ("age \\<or= 75 (constructed)", "\\<", "≤", "\\<or="),
        ("age > or = 18 (constructed)", ">", "≥", "> or ="),
        ("no more than 2 prior regimens (constructed)", "no", "≤", "no more than"),
        ("ECOG = 0 (constructed)", "=", "=", "="),
        ("aged over 18 (constructed)", "over", ">", "over"),
    ],
)
def test_a_comparator_is_read_longest_first(text, word, sign, written):
    start = at(text, word)
    parse = read_comparator(text, start)
    assert parse.readings == ((("sign", sign), ("as_written", written)),)
    assert parse.spans == (Span("comparator", start, start + len(written)),) and parse.status == "parsed"


@pytest.mark.parametrize(
    "text",
    [
        "Overall Survival (OS)",
        "18 years",
        "ULN",
        "underlying disease (constructed)",
        "≈ 5 (constructed)",
        "> = 18 (constructed)",
        "\\> = 18 (constructed)",
        "< /= 2 (constructed)",
        "< or= 2 (constructed)",
        "= < 3 (constructed)",
    ],
)
def test_no_comparator_where_none_is_written(text):
    """Positive: "> 5" and "= 0" are read. Negative: a strict sign or "=" at the start of a form the table
    does not hold ("> =", "< /=", "= <") is never read as the strict sign: no comparator."""
    assert read_comparator(text, 0) == Parse("comparator", "abstained", (), (), 0, "no comparator")
    assert reading(read_comparator("> 5 (constructed)", 0))["sign"] == ">"
    assert reading(read_comparator("= 0 (constructed)", 0))["sign"] == "="


# ── units and references ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, word, written, ucum, mapping, dimension",
    [
        ("   * Creatinine clearance (eGFR) ≥ 45 mL/min", "mL", "mL/min", "mL/min", "ucum", "other"),
        ("* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL", "×", "× 10^9/L", "10*9/L", "ucum", "other"),
        ("* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL", "g/dL", "g/dL", "g/dL", "ucum", "other"),
        ("Creatinine ≤ 1.5 mg/dL", "mg", "mg/dL", "mg/dL", "ucum", "other"),
        (PILOT[1], "mg/dl", "mg/dl", "mg/dL", "ucum", "other"),
        (PILOT[2], "/mm", "/mm\\^3", "/mm3", "ucum", "other"),
        (PILOT[0], "%", "%", "%", "ucum", "other"),
        ("* Life expectancy ≥ 12 weeks", "weeks", "weeks", "wk", "ucum", "time"),
        ("2. Age ≥ 18 years and \\<75 years", "years", "years", "a", "ucum", "time"),
        ("Predose (2 hours) Week 3 - Week 96", "hours", "hours", "h", "ucum", "time"),
        ("tumor ≥ 4 cm", "cm", "cm", "cm", "ucum", "other"),
        ("ANC ≥ 1.5 G/L (constructed)", "G/L", "G/L", "", "unmapped", "unknown"),
        ("fibrinogen ≥ 150 IU/dL (constructed)", "IU", "IU/dL", "", "unmapped", "unknown"),
        ("HIV RNA < 50 copies/mL (constructed)", "copies", "copies/mL", "", "unmapped", "unknown"),
        ("eGFR ≥ 60 mL/min/1.73m2 (constructed)", "mL", "mL/min/1.73m2", "", "unmapped", "other"),
        ("* Absolute neutrophil count >= 1.5 x 10^9/L", "x", "x 10^9/L", "10*9/L", "ucum", "other"),
        ("platelets ≥ 100 × 10⁹/L (constructed)", "×", "× 10⁹/L", "10*9/L", "ucum", "other"),
        ("ANC ≥ 1.5 × 10e9/L (constructed)", "×", "× 10e9/L", "10*9/L", "ucum", "other"),
        ("infusion over 2 h (constructed)", "h ", "h", "h", "ucum", "time"),
        ("within 5 half-lives (constructed)", "half", "half-lives", "", "unmapped", "time"),
        ("eGFR ≥ 60 mL/min/1.73 m2 (constructed)", "mL", "mL/min/1.73 m2", "", "unmapped", "other"),
        ("10 pack-years (constructed)", "pack", "pack-years", "", "unmapped", "other"),
    ],
)
def test_a_unit_keeps_its_writing_and_names_its_ucum_form_or_none(
    text, word, written, ucum, mapping, dimension
):
    start = at(text, word)
    parse = read_unit(text, start)
    fields = (("as_written", written), ("ucum", ucum), ("mapping", mapping), ("dimension", dimension))
    assert parse == Parse(
        "unit", "parsed", (fields,), (Span("unit", start, start + len(written)),), parse.end, ""
    )
    assert parse.end == start + len(written)


@pytest.mark.parametrize(
    "text, word, note",
    [
        (
            "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN.",
            "×",
            "reference",
        ),
        ("   * Aspartate aminotransferase (AST): ≤ 3 x ULN (no liver metastases)", "x", "reference"),
        ("Total bilirubin ≤ 1.5 times the upper limit of normal (constructed)", "times", "reference"),
        ("Bilirubin ≤ ULN (constructed)", "ULN", "reference"),
        ("4. Received 1 or 2 prior line(s)", "or", "none"),
        ("1 and/or 2 prior lines (constructed)", "and", "none"),
        ("aged 18 years or older (constructed)", "older", "none"),
        ("the minimum dose (constructed)", "minimum", "none"),
        ("AST/ALT ≤ 2.5 × ULN (constructed)", "AST", "none"),
        ("Male/female aged 18 (constructed)", "Male", "none"),
        ("other inclusion/exclusion criteria (constructed)", "inclusion", "none"),
        ("he/she agrees (constructed)", "he", "none"),
        ("platelets ≥ 100 109/L (constructed)", "109", "none"),
        ("WBC ≥ 3.0 103/uL (constructed)", "103", "none"),
        ("active H. pylori infection (constructed)", "H.", "none"),
    ],
)
def test_a_reference_or_a_word_is_never_a_unit(text, word, note):
    """Positive: "× ULN" is abstained as a reference. Negative: a pair of words ("AST/ALT", "Male/female"),
    digits run on into a power of ten whose sign is not written ("109/L") and "H" are no unit."""
    start = at(text, word)
    expected = "a reference expression, never a unit" if note == "reference" else "no unit"
    assert read_unit(text, start) == Parse("unit", "abstained", (), (), start, expected)


@pytest.mark.parametrize(
    "text, word, factor, reference, written",
    [
        (
            "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN.",
            "2.5",
            "2.5",
            "ULN",
            "×ULN",
        ),
        ("   * Aspartate aminotransferase (AST): ≤ 3 x ULN (no liver metastases)", "3", "3", "ULN", "x ULN"),
        ("   * Total bilirubin (TBIL): ≤1.5 × ULN (no liver metastases)", "1.5", "1.5", "ULN", "× ULN"),
        (
            "ALT ≤ 2.5 times the institutional upper limit of normal (constructed)",
            "2.5",
            "2.5",
            "ULN",
            "times the institutional upper limit of normal",
        ),
        ("Bilirubin ≤ ULN (constructed)", "ULN", "", "ULN", "ULN"),
        ("fibrinogen ≥ 0.8 × LLN (constructed)", "0.8", "0.8", "LLN", "× LLN"),
        ("AST ≤ 3 × IULN (constructed)", "3", "3", "ULN", "× IULN"),
    ],
)
def test_a_reference_expression_is_a_reference_with_its_factor_as_written(
    text, word, factor, reference, written
):
    start = at(text, word)
    parse = read_reference(text, start)
    assert parse.status == "parsed"
    assert parse.readings == ((("factor", factor), ("reference", reference), ("as_written", written)),)
    expected = [("reference", written)] if not factor else [("value", factor), ("reference", written)]
    assert words(text, parse) == expected


def test_a_reference_carries_its_factors_ambiguity_and_needs_a_reference():
    parse = read_reference("ALT ≤ 1,500 × ULN (constructed)", 6)
    assert parse.status == "ambiguous" and [reading(parse, i)["factor"] for i in (0, 1)] == ["1500", "1.500"]
    assert parse.note == "a grouping mark or a decimal mark"
    text = "* Platelets ≥ 100 × 10^9/L"
    assert read_reference(text, at(text, "100")) == Parse(
        "reference", "abstained", (), (), at(text, "100"), "no reference expression"
    )
    assert read_reference("ECOG 0,1 × ULN (constructed)", 5).note == "no reference expression"


@pytest.mark.parametrize(
    "text, word",
    [
        ("AST ≤ ULN x 2.5 (constructed)", "ULN"),
        ("AST ≤ ULN × 3 (constructed)", "ULN"),
        ("bilirubin ≤ ULN times 1.5 (constructed)", "ULN"),
        ("AST ≤ 2 × ULN x 2.5 (constructed)", "2"),
    ],
)
def test_a_factor_after_the_reference_is_abstained_never_read_as_none(text, word):
    """Positive: "≤ ULN" alone reads factor "" (none written), and "ULN\\n* ALT" is no factor after it (a
    bullet multiplies nothing). Negative: a factor written after the reference is abstained, never lost."""
    start = at(text, word)
    assert read_reference(text, start) == Parse("reference", "abstained", (), (), start, parsers.FACTOR_AFTER)
    bulleted = "* AST ≤ ULN\n* 2 prior lines (constructed)"
    assert reading(read_reference(bulleted, at(bulleted, "ULN")))["factor"] == ""


# ── durations and windows ───────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, word, value, unit, ucum, mapping",
    [
        ("7. Receipt of live attenuated vaccine within 30 days prior", "30", "30", "days", "d", "ucum"),
        ("within six months before randomization", "six", "6", "months", "mo", "ucum"),
        ("* Life expectancy ≥ 12 weeks", "12", "12", "weeks", "wk", "ucum"),
        ("a 4-week washout (constructed)", "4", "4", "week", "wk", "ucum"),
        ("within 5 half-lives (constructed)", "5", "5", "half-lives", "", "unmapped"),
    ],
)
def test_a_duration_is_a_number_then_a_unit_of_time(text, word, value, unit, ucum, mapping):
    parse = read_duration(text, at(text, word))
    assert parse.readings == ((("value", value), ("unit", unit), ("ucum", ucum), ("mapping", mapping)),)
    assert [role for role, _ in words(text, parse)] == ["value", "unit"] and parse.status == "parsed"


@pytest.mark.parametrize(
    "text, word, note",
    [
        ("   * Creatinine clearance (eGFR) ≥ 45 mL/min", "45", "no unit of time after the number"),
        ("4. Received 1 or 2 prior line(s)", "1", "no unit of time after the number"),
        ("* Written informed consent obtained prior to any screening procedures.", "prior", "no number"),
        ("PD-L1 status (constructed)", "1", "inside a name"),
    ],
)
def test_no_duration_without_a_number_and_a_unit_of_time(text, word, note):
    start = at(text, word)
    assert read_duration(text, start) == Parse("duration", "abstained", (), (), start, note)


def test_a_duration_carries_its_numbers_ambiguity():
    parse = read_duration("1,500 days (constructed)", 0)
    assert parse.status == "ambiguous" and [reading(parse, i)["value"] for i in (0, 1)] == ["1500", "1.500"]


def window(text, word):
    parse = read_window(text, at(text, word))
    return parse, [reading(parse, i) for i in range(len(parse.readings))]


def test_a_window_keeps_its_anchor_as_written():
    text = "7. Receipt of live attenuated vaccine within 30 days prior to the first dose of IP."
    parse, (only,) = window(text, "within")
    assert parse.status == "parsed" and parse.note == ""
    assert only == {
        "marker": "within",
        "orientation": "before",
        "anchor": "the first dose of IP",
        "lower": "0",
        "lower_inclusive": "unspecified",
        "upper": "30",
        "upper_inclusive": "unspecified",
        "value": "30",
        "unit": "days",
        "ucum": "d",
        "mapping": "ucum",
    }
    assert words(text, parse) == [
        ("window", "within 30 days prior to the first dose of IP"),
        ("value", "30"),
        ("unit", "days"),
        ("qualifier", "the first dose of IP"),
    ]
    assert parse.end == at(text, "IP.") + 2


def test_the_specs_window_and_a_comparators_bounds():
    text = "HbA1c ≤8.0% and no myocardial infarction within six months before randomization"
    parse, (only,) = window(text, "within")
    assert (only["orientation"], only["anchor"], only["value"], only["unit"]) == (
        "before",
        "randomization",
        "6",
        "months",
    )
    assert parse.spans[0] == Span("window", 41, len(text))  # the span the contract's scenario holds
    text = "* Any active malignancy less than or equal to 2 years before randomization"
    parse, (only,) = window(text, "less")
    assert (only["marker"], only["lower"], only["lower_inclusive"]) == (
        "less than or equal to",
        "0",
        "unspecified",
    )
    assert (only["upper"], only["upper_inclusive"], only["anchor"]) == ("2", "inclusive", "randomization")
    assert words(text, parse)[1] == ("comparator", "less than or equal to")


@pytest.mark.parametrize(
    "text, word, orientation, anchor, upper",
    [
        (PILOT[5], "within", "unspecified", "dosing", "7"),
        (PILOT[6], "within", "before", "unresolved", "3"),
        (PILOT[8], "within", "unspecified", "unresolved", "4"),
        (PILOT[2], "within", "unspecified", "unresolved", "6"),
        (
            "* Platelet transfusion within 14 days before the first dose is not allowed",
            "within",
            "before",
            "the first dose",
            "14",
        ),
        (
            "within 2 years after diagnosis of chronic pancreatitis (constructed)",
            "within",
            "after",
            "diagnosis of chronic pancreatitis",
            "2",
        ),
        ("surgery 3 months ago, or (constructed)", "3", "before", "unresolved", ""),
        ("within 4 weeks before and during the study (constructed)", "within", "before", "unresolved", "4"),
        ("in the past 6 months (constructed)", "in", "before", "unresolved", "6"),
    ],
)
def test_a_windows_orientation_and_anchor_are_never_assumed(text, word, orientation, anchor, upper):
    parse, readings = window(text, word)
    assert (readings[0]["orientation"], readings[0]["anchor"]) == (orientation, anchor)
    assert readings[0]["upper"] == upper or parse.status == "ambiguous"


def test_an_unmarked_window_is_ambiguous_within_or_at_least():
    text = PILOT[4]
    parse, (within, at_least) = window(text, "4")
    assert parse.status == "ambiguous"
    assert parse.note == "a duration and an orientation with no marker: within it, or at least it"
    assert (within["lower"], within["upper"], within["upper_inclusive"]) == ("0", "4", "unspecified")
    assert (at_least["lower"], at_least["lower_inclusive"], at_least["upper"]) == ("4", "unspecified", "")
    assert within["anchor"] == at_least["anchor"] == "randomization" and within["marker"] == ""


def test_an_at_least_window_is_inclusive_by_its_comparator():
    parse, (only,) = window("stable for at least 4 weeks prior to enrollment (constructed)", "at least")
    assert (only["lower"], only["lower_inclusive"], only["upper"], only["upper_inclusive"]) == (
        "4",
        "inclusive",
        "",
        "",
    )
    parse, (only,) = window("treated more than 2 weeks before Day 1 (constructed)", "more")
    assert (only["lower"], only["lower_inclusive"], only["anchor"]) == ("2", "exclusive", "Day 1")
    parse, (only,) = window("less than 4 weeks before Day 1 (constructed)", "less")
    assert (only["upper"], only["upper_inclusive"]) == ("4", "exclusive")
    parse, (only,) = window("exactly = 2 weeks before Day 1 (constructed)", "=")
    assert (only["lower"], only["upper"], only["lower_inclusive"]) == ("2", "2", "inclusive")


@pytest.mark.parametrize(
    "text, word, note",
    [
        (
            "* Other malignancy within ≥ 5 years prior to enrollment",
            "within",
            "a window marker and a comparator together: the bound is unclear",
        ),
        ("* Life expectancy ≥ 12 weeks", "≥", "a duration with no marker and no direction: no window"),
        (PILOT[7], "\\<", "a duration with no marker and no direction: no window"),
        (
            "a history of 2 years of smoking (constructed)",
            "2",
            "a duration with no marker and no direction: no window",
        ),
        ("* Written informed consent obtained prior to any screening procedures.", "prior", "no duration"),
        ("within the study (constructed)", "within", "no duration"),
        (
            "within 14 days before or after randomization (constructed)",
            "within",
            "a window on both sides of its anchor: no one orientation",
        ),
        (
            "within 28 days prior to or after the first dose (constructed)",
            "within",
            "a window on both sides of its anchor: no one orientation",
        ),
        (
            "4 weeks before and/or following surgery (constructed)",
            "4",
            "a window on both sides of its anchor: no one orientation",
        ),
        (
            "within 7 days before/after dosing (constructed)",
            "within",
            "a window on both sides of its anchor: no one orientation",
        ),
    ],
)
def test_no_window_is_read_where_none_is_written(text, word, note):
    start = at(text, word)
    assert read_window(text, start) == Parse("window", "abstained", (), (), start, note)


def test_a_window_carries_its_numbers_ambiguity():
    parse = read_window("within 1,500 days before Day 1 (constructed)", 0)
    assert parse.status == "ambiguous" and parse.note == "a grouping mark or a decimal mark"
    assert [reading(parse, i)["upper"] for i in (0, 1)] == ["1500", "1.500"]


# ── intervals ───────────────────────────────────────────────────────────────────────────────────────


def interval(text, word):
    parse = read_interval(text, at(text, word))
    return parse, reading(parse) if parse.readings else {}


def sides(found):
    return (found["lower"], found["lower_inclusive"], found["upper"], found["upper_inclusive"])


@pytest.mark.parametrize(
    "text, word, expected, unit",
    [
        (
            "2. Age ≥ 18 years and \\<75 years male or females;",
            "≥",
            ("18", "inclusive", "75", "exclusive"),
            "years",
        ),
        ("8. Aged 18 to 75 years, ECOG PS: 0-1", "18", ("18", "unspecified", "75", "unspecified"), "years"),
        (
            "8. Aged 18 to 75 years, ECOG PS: 0\\~1, estimated",
            "0\\~",
            ("0", "unspecified", "1", "unspecified"),
            "",
        ),
        ("2. ECOG score 0-1;", "0-1", ("0", "unspecified", "1", "unspecified"), ""),
        (
            "* Documentation of program death ligand-1 (PD-L1) status of 0 to 49% by IHC",
            "0 to",
            ("0", "unspecified", "49", "unspecified"),
            "%",
        ),
        (PILOT[3], "6", ("6", "unspecified", "35", "unspecified"), "years"),
        ("   * Creatinine clearance (eGFR) ≥ 45 mL/min", "≥", ("45", "inclusive", "", ""), "mL/min"),
        (PILOT[1], "\\>", ("1.4", "exclusive", "", ""), "mg/dl"),
        (PILOT[7], "\\<", ("", "", "4", "exclusive"), "weeks"),
        (
            "between 18 and 75 years inclusive (constructed)",
            "between",
            ("18", "inclusive", "75", "inclusive"),
            "years",
        ),
        (
            "from 2 to 4 weeks (exclusive) (constructed)",
            "from",
            ("2", "exclusive", "4", "exclusive"),
            "weeks",
        ),
        ("aged 18 years or older (constructed)", "18", ("18", "inclusive", "", ""), "years"),
        ("2 or more prior lines (constructed)", "2", ("2", "inclusive", "", ""), ""),
        ("3 or less (constructed)", "3", ("", "", "3", "inclusive"), ""),
        ("ECOG = 0 (constructed)", "=", ("0", "inclusive", "0", "inclusive"), ""),
        ("≥ 18 and ≤ 75 years (constructed)", "≥", ("18", "inclusive", "75", "inclusive"), "years"),
        ("< 75 years and > 18 years (constructed)", "<", ("18", "exclusive", "75", "exclusive"), "years"),
    ],
)
def test_an_interval_keeps_its_inclusivity_explicit_or_unspecified(text, word, expected, unit):
    parse, found = interval(text, word)
    assert parse.status == "parsed" and sides(found) == expected
    assert (found["unit"], found["reference"]) == (unit, "")


def test_an_interval_holds_its_spans_and_its_unit_once():
    text = "2. Age ≥ 18 years and \\<75 years male or females;"
    parse, found = interval(text, "≥")
    assert words(text, parse) == [
        ("comparator", "≥"),
        ("value", "18"),
        ("unit", "years"),
        ("comparator", "\\<"),
        ("value", "75"),
        ("unit", "years"),
    ]
    assert (found["ucum"], found["mapping"]) == ("a", "ucum") and parse.end == at(text, " male")


def test_a_reference_bound_is_a_reference_never_a_unit():
    text = "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN."
    parse, found = interval(text, "≤")
    assert sides(found) == ("", "", "2.5", "inclusive") and (found["unit"], found["reference"]) == ("", "ULN")
    assert words(text, parse) == [("comparator", "≤"), ("value", "2.5"), ("reference", "×ULN")]
    parse, found = interval("Bilirubin ≤ ULN (constructed)", "≤")
    assert sides(found) == ("", "", "", "inclusive") and found["reference"] == "ULN"  # no factor of 1
    text = "* Absolute neutrophil count >= 1.5 x 10^9/L"
    parse, found = interval(text, ">=")
    assert sides(found) == ("1.5", "inclusive", "", "") and (found["ucum"], found["reference"]) == (
        "10*9/L",
        "",
    )
    assert words(text, parse) == [("comparator", ">="), ("value", "1.5"), ("unit", "x 10^9/L")]
    parse, found = interval("≥ 100\n* Hemoglobin ≥ 9 g/dL (constructed)", "≥")
    assert sides(found) == ("100", "inclusive", "", "") and found["unit"] == ""  # a bullet multiplies nothing


def test_an_intervals_ambiguity_is_every_reading():
    parse = read_interval(PILOT[2], at(PILOT[2], "\\>"))
    assert parse.status == "ambiguous" and [reading(parse, i)["lower"] for i in (0, 1)] == ["50000", "50.000"]
    assert reading(parse)["ucum"] == "/mm3"
    point = read_interval("= 1,500 (constructed)", 0)
    assert [(reading(point, i)["lower"], reading(point, i)["upper"]) for i in (0, 1)] == [
        ("1500", "1500"),
        ("1.500", "1.500"),
    ]
    both = read_interval("1,500 to 2,500 (constructed)", 0)
    assert len(both.readings) == 4 and both.note == "a grouping mark or a decimal mark"


@pytest.mark.parametrize(
    "text, word, note",
    [
        (
            "4. Received 1 or 2 prior line(s) of an approved EGFR TKI",
            "1",
            "a number alone states no interval",
        ),
        ("* Other inclusion criteria may apply.", "Other", "no bound"),
        ("≥ 18 and ≥ 21 (constructed)", "≥", "two bounds on one side"),
        ("= 1 and ≤ 2 (constructed)", "=", "two bounds on one side"),
        ("18 years to 6 months (constructed)", "18", "bounds in two different units"),
        ("≥ 18 years and < 6 months (constructed)", "≥", "bounds in two different units"),
        ("at least the following (constructed)", "at", "a comparator with no bound"),
        ("between 18 and adulthood (constructed)", "between", "a number alone states no interval"),
        ("between the visits (constructed)", "between", "no bound"),
        ("ALT ≤ 1.5 × ULRR (constructed)", "≤", parsers.UNREAD_AFTER),
        ("ALT ≤ 1.5 × upper limit of reference range (constructed)", "≤", parsers.UNREAD_AFTER),
        ("≤ 3 times the normal upper limit (constructed)", "≤", parsers.UNREAD_AFTER),
        ("AST ≤ 2.5-fold ULN (constructed)", "≤", parsers.UNREAD_AFTER),
        ("AST ≤ 2.5 x upper limit of institutional normal (constructed)", "≤", parsers.UNREAD_AFTER),
        ("ANC ≥ 1.5 x 10 9/L (constructed)", "≥", parsers.UNREAD_AFTER),
        ("platelets ≥ 100 109/L (constructed)", "≥", parsers.UNREAD_AFTER),
        ("platelets 100 000/mm3 to 400 000/mm3 (constructed)", "100", parsers.UNREAD_AFTER),
        ("platelets 100 to 400 000/mm3 (constructed)", "100", parsers.UNREAD_AFTER),
        ("≥ 18 and ≤ 2.5 × ULRR (constructed)", "≥", parsers.UNREAD_AFTER),
        ("AST ≤ ULN x 2.5 (constructed)", "≤", parsers.FACTOR_AFTER),
        ("AST ULN x 2.5 (constructed)", "ULN", parsers.FACTOR_AFTER),
    ],
)
def test_no_interval_is_read_where_none_is_written(text, word, note):
    start = at(text, word)
    assert read_interval(text, start) == Parse("interval", "abstained", (), (), start, note)


def test_a_bound_on_another_thing_is_not_a_second_bound():
    """Positive: "≥ 9 g/dL and platelets ≥ 100" reads one bound. Negative: the platelets' is not its upper."""
    text = "Hemoglobin ≥ 9 g/dL and platelets ≥ 100 (constructed)"
    parse, found = interval(text, "≥")
    assert sides(found) == ("9", "inclusive", "", "") and found["unit"] == "g/dL"
    assert parse.end == at(text, " and")


# ── every real criterion ────────────────────────────────────────────────────────────────────────────


def test_every_span_on_every_real_criterion_holds_its_words_the_same_on_every_run():
    """Positive: on every real criterion, at every position, every reader's spans lie in the text and are
    non-empty, a value span holds the as-written number, a comparator span the as-written comparator, a unit
    span the as-written unit; two runs give equal parses. Negative: no reading carries a float, a bool or an
    empty field name, and an abstained parse carries no reading and no span."""
    texts = sorted({*real_criteria(), *PILOT})
    assert len(texts) > 90  # every quoted criterion of test_banks.py, and the pilot's
    for text in texts:
        for start in range(len(text) + 1):
            for reader in READERS:
                parse = getattr(parsers, reader)(text, start)
                assert parse == getattr(parsers, reader)(text, start)
                if parse.status == "abstained":
                    assert (parse.readings, parse.spans, parse.end) == ((), (), start)
                    continue
                assert len(parse.readings) == (1 if parse.status == "parsed" else len(parse.readings)) >= 1
                assert all(0 <= s.start < s.end <= len(text) for s in parse.spans), (text, start, reader)
                for fields in parse.readings:
                    assert all(name and isinstance(value, str) for name, value in fields)
                first = dict(parse.readings[0])
                held = {span.role: text[span.start : span.end] for span in parse.spans}
                if reader in ROLES:
                    assert held[ROLES[reader]] == first["as_written"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("leſs than 5 (constructed)", (("sign", "<"), ("as_written", "leſs than"))),
        ("hıgher than 2 (constructed)", (("sign", ">"), ("as_written", "hıgher than"))),
        ("at least 4 (constructed)", (("sign", "≥"), ("as_written", "at least"))),
    ],
)
def test_a_comparator_folded_by_case_is_still_a_named_result(text, expected):
    """Positive: a form case-insensitive matching folds ("leſs than", "hıgher than") or spaces with a no-break
    space is read as the form it matched. Negative: it never raises for want of a table key."""
    assert read_comparator(text, 0).readings == (expected,)


@pytest.mark.parametrize(
    "text",
    [
        "fıve (constructed)",
        "ſixty (constructed)",
        "twenty-fıve (constructed)",
        "one-third (constructed)",
        "two-thirds of the dose (constructed)",
        "twenty-something (constructed)",
        "twenty-one-thirds (constructed)",
    ],
)
def test_a_number_word_not_read_whole_is_no_number_never_a_wrong_one(text):
    """Positive: "twenty people" is 20 and "Twenty Four" 24. Negative: a number word in other letters, a
    fraction, or a tens word before a hyphenated word is abstained, never read as part of itself."""
    assert read_number(text, 0) == Parse("number", "abstained", (), (), 0, "no number")
    assert reading(read_number("twenty people (constructed)", 0))["value"] == "20"
    assert reading(read_number("Twenty Four hours (constructed)", 0))["value"] == "24"
