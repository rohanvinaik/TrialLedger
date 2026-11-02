"""A criterion's role, read from its own words against its heading (criteria.criterion_role).

Positive: words saying the person is ineligible for this study, trial or protocol, or for enrollment or
participation, or standing alone ("are ineligible"), state an exclusion under any heading; "excluded if" and
"are excluded" do too.
Negative: "ineligible for" or "not eligible for" a therapy, a transplant, surgery or standard treatment
describes the patient and is never an exclusion: the heading decides (an inclusion requirement stays one);
a negated requirement ("must not be eligible for curative surgery") follows the negating words' rule; a
permission is never an exclusion; alternatives ("ineligible for or refused standard therapy") describe the
patient.
"""

import pytest

from TrialLedger.criteria import criterion_role


@pytest.mark.parametrize(
    "text, heading, role, words",
    [
        # trial ineligibility: an exclusion under any heading
        ("Patients who are ineligible will be withdrawn", "inclusion", "exclusion", ("ineligible",)),
        ("Subjects will be ineligible.", "unsectioned", "exclusion", ("ineligible",)),
        ("Not eligible for this study if pregnant", "inclusion", "exclusion", ("Not eligible",)),
        ("Patients are not eligible for the trial", "unsectioned", "exclusion", ("not eligible",)),
        ("Ineligible for enrollment: prior EGFR TKI", "inclusion", "exclusion", ("Ineligible",)),
        ("Ineligible to participate in the study", "inclusion", "exclusion", ("Ineligible",)),
        ("Not eligible for participation if HIV positive", "inclusion", "exclusion", ("Not eligible",)),
        ("Considered ineligible by the investigator", "inclusion", "exclusion", ("ineligible",)),
        ("Patients with brain metastases are excluded", "inclusion", "exclusion", ("are excluded",)),
    ],
)
def test_ineligibility_for_the_study_is_an_exclusion(text, heading, role, words):
    assert criterion_role(text, heading) == (role, words)


@pytest.mark.parametrize(
    "text, heading, role",
    [
        # the review's case: an inclusion requirement describing the patient
        ("Be ineligible for any available standard line of therapy", "inclusion", "inclusion"),
        ("Ineligible for standard treatment", "inclusion", "inclusion"),
        ("Ineligible for autologous stem cell transplant", "inclusion", "inclusion"),
        ("Not eligible for curative surgery or radiotherapy", "inclusion", "inclusion"),
        ("Not eligible to radical surgery and/or radical radiotherapy", "inclusion", "inclusion"),
        # alternatives describe the patient too
        ("Ineligible for or refused standard therapy", "inclusion", "inclusion"),
        # the heading still decides under an exclusion heading, and under none it stays unresolved
        ("Ineligible for transplant", "exclusion", "exclusion"),
        ("Ineligible for transplant", "unsectioned", "unresolved"),
    ],
)
def test_ineligibility_for_a_treatment_describes_the_patient(text, heading, role):
    """The heading decides, never the word "ineligible"."""
    assert criterion_role(text, heading) == (role, ())


def test_a_negated_eligibility_follows_the_negating_words():
    """A requirement stated in the negative ("must not be eligible for curative surgery") is never an
    exclusion by its "eligible" alone: unresolved under an inclusion heading, exclusion under an exclusion
    one."""
    text = "Must not be eligible for curative surgery"
    assert criterion_role(text, "inclusion") == ("unresolved", ("Must not",))
    assert criterion_role(text, "exclusion") == ("exclusion", ("Must not",))


def test_a_permission_is_never_an_exclusion():
    text = "Patients ineligible for cisplatin are allowed"
    assert criterion_role(text, "inclusion") == ("inclusion", ("are allowed",))
    assert criterion_role(text, "exclusion") == ("unresolved", ("are allowed",))
