"""Corrections from the auditor pilot (2026-10-31): general rules, each from a defect Claude's blind labels
found in criteria of the 18-trial stratified sample, never fitted to those trials alone.

Positive: the API's escaped less-or-equal is ≤; paired thresholds keep both with their qualifiers; a negated
mention records its polarity; a permission is marked permitted; a window needs a temporal marker; the
effective section follows the wording.
Negative: "sleep aids" is never AIDS; a vitamin deficiency is never premedication; anticoagulant use is never
a bleeding event; "childbearing potential" alone is never contraception; "acceptable method" is never a
permission; an age range is never a window; "not allowed" is never a permission."""

import pytest

from TrialLedger.banks import named_conditions, organ_function, performance_status, permitted, type_criterion
from TrialLedger.questions import atom_claim
from TrialLedger.reading import effective_section


def conditions(text):
    return {a[1][0]: dict(a[2]) for a in named_conditions(text)}


def test_an_escaped_less_or_equal_is_read():
    text = "* Eastern Cooperative Oncology Group (ECOG) performance status =\\< 1 (Karnofsky \\>= 70%)"
    assert [a[1] for a in performance_status(text)] == [("0", "1")]


def test_paired_thresholds_keep_both_with_their_qualifiers():
    atoms = organ_function("* Serum creatinine \\> 1.4 mg/dl (female) or \\> 1.5 mg/dl (male).")
    assert [dict(a[2])["value"] for a in atoms] == ["1.4", "1.5"]
    assert [dict(a[2])["qualifier"] for a in atoms] == ["female", "male"]
    single = organ_function("* Platelet count \\> 50,000/mm\\^3 (within 6 weeks)")
    assert len(single) == 1 and "qualifier" not in dict(single[0][2])


@pytest.mark.parametrize(
    "text, concept",
    [
        (
            "* Subject is a male or non-pregnant, non-lactating female age 6 through 35 years",
            "pregnancy_or_breastfeeding",
        ),
        (
            "* Women must have a negative serum pregnancy test pre-dose on day 1.",
            "pregnancy_or_breastfeeding",
        ),
        ("* Agree to use adequate contraception to avoid pregnancy.", "pregnancy_or_breastfeeding"),
        (
            "* Pregnancy at screening or unwillingness to use acceptable method of birth control",
            "contraception",
        ),
        ("* Women of childbearing potential unless using effective contraception", "contraception"),
    ],
)
def test_a_negated_mention_records_its_polarity(text, concept):
    assert conditions(text)[concept].get("text_polarity") == "excluded"


def test_a_plain_mention_records_no_polarity_and_an_age_is_no_window():
    found = conditions("* Pregnant or lactating women;")
    assert found["pregnancy_or_breastfeeding"] == {}
    assert (
        "window"
        not in conditions("* Non-pregnant female age 6 through 35 years")["pregnancy_or_breastfeeding"]
    )
    assert (
        conditions("* Major surgery 4 weeks prior to randomization")["recent_surgery"]["window"] == "4 weeks"
    )
    assert conditions("* Life expectancy ≥ 12 weeks")["life_expectancy"]["window"] == "12 weeks"


def test_vocabulary_boundaries():
    assert "hiv" not in conditions("* Initiation of sleep aids (melatonin, antihistamines) for \\< 4 weeks")
    assert "hiv" in conditions("* Known HIV infection or AIDS")
    assert "vitamin_premedication" not in conditions("* Severe Vitamin B12 deficiency.")
    assert "vitamin_premedication" in conditions(
        "* Unable to take folic acid and vitamin B12 supplementation"
    )
    anticoagulant = conditions("* Treatment with anticoagulant within 7 days of dosing.")
    assert "anticoagulant_use" in anticoagulant and "bleeding_thrombosis" not in anticoagulant
    assert "contraception" not in conditions("* Women of childbearing potential")


def test_a_permission_is_never_a_requirement():
    text = (
        "* All lines of prior systemic therapy are permissible. "
        "Standard concurrent chemotherapy is permissible"
    )
    assert permitted(text, text.index("chemotherapy"), text.index("chemotherapy") + 12)
    assert all(("modality", "permitted") in a[3] for a in type_criterion(text))
    assert not permitted("* Prior radiotherapy is not allowed", 8, 20)
    method = "* Pregnancy at screening or unwillingness to use acceptable method of birth control"
    assert not any(("modality", "permitted") in a[3] for a in type_criterion(method))
    two = "* ECOG 0-1. Prior chemotherapy is allowed"
    assert not permitted(two, two.index("ECOG"), two.index("ECOG") + 8)


def test_the_effective_section_follows_the_wording():
    assert effective_section("inclusion", (("text_polarity", "excluded"),)) == "exclusion"
    assert effective_section("exclusion", (("text_polarity", "excluded"),)) == "inclusion"
    assert effective_section("unsectioned", (("text_polarity", "excluded"),)) == "unsectioned"
    assert (
        effective_section("exclusion", (("modality", "permitted"), ("text_polarity", "excluded")))
        == "permitted"
    )
    assert effective_section("inclusion", ()) == "inclusion"
    claim = atom_claim(
        ("c", "condition", ("pregnancy_or_breastfeeding",), (("text_polarity", "excluded"),), 0, 1),
        "exclusion",
    )
    assert claim == "This exclusion criterion excludes participants who have: pregnancy or breastfeeding"
    allowed = atom_claim(
        ("p", "prior_agent", ("chemotherapy",), (("modality", "permitted"),), 0, 1), "permitted"
    )
    assert (
        allowed
        == "This criterion permits, without requiring, participants to have: prior_agent = chemotherapy"
    )


def test_second_round_boundaries():
    """Positive: "within prior 3 months" is a window; "serious medical condition" is a serious comorbidity;
    immunosuppressive therapy is immunosuppression. Negative: "not limited to" never negates; the study's own
    investigational drug is never another trial's; an immunosuppressive disease is never therapy; "becoming
    pregnant" is never pregnancy; a serious condition is never the investigator's judgment."""
    listed = conditions("* Uncontrolled illness including, but not limited to, ongoing or active infection")
    assert "text_polarity" not in listed["active_infection"]
    window = conditions("* Currently pregnant or had a pregnancy-related procedure within prior 3 months")
    assert window["pregnancy_or_breastfeeding"]["window"] == "3 months"
    assert "other_investigational" not in conditions(
        "* Received hemostatic treatment with investigational drug"
    )
    assert "other_investigational" in conditions("* Received any investigational drug within 30 days")
    serious = conditions("7. Serious or unstable medical condition that could lead to hospitalization")
    assert "serious_comorbidity" in serious and "investigator_judgment" not in serious
    assert "investigator_judgment" in conditions(
        "* Any condition that, in the opinion of the investigator, ..."
    )
    assert "immunosuppression_steroids" not in conditions("* Contagious immunosuppressive disease (e.g. HIV)")
    assert "immunosuppression_steroids" in conditions("* Use of immunosuppressive drugs within 4 weeks")
    assert "pregnancy_or_breastfeeding" not in conditions(
        "* Subjects capable of becoming pregnant must use birth control"
    )


def test_investigational_and_premedication_phrase_classes():
    """Positive: another study's investigational drug, with words between, and premedication someone is unable
    to take, are typed; a condom is contraception; planning to become pregnant is pregnancy. Negative: the
    study's own investigational product (its administration, or treatment with it) is never another study's.
    """
    assert "other_investigational" in conditions(
        "24. Received other unmarketed investigational drug within 4 weeks"
    )
    assert "other_investigational" in conditions(
        "* Is currently participating in a study of an investigational agent"
    )
    own = "* Risk associated with study participation or investigational product administration"
    assert "other_investigational" not in conditions(own)
    assert "vitamin_premedication" in conditions(
        "* Is unable/unwilling to take folic acid, vitamin B12, and dexamethasone"
    )
    assert "contraception" in conditions(
        "* Sexually active males unless they use a condom during intercourse"
    )
    assert "pregnancy_or_breastfeeding" in conditions("* Female participants planning to become pregnant")
