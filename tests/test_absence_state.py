"""absence_state — why a field holds no value, in the registry's own terms.

Positive: a present field is reported; an absent field outside the study type is not applicable; an absent
field of a withheld study that the registry redacts is redacted.
Negative: an absent field is never "reported"; an applicable field of an ordinary study is never called
redacted or not applicable; a study of unknown type is never declared outside a field's study types.
"""

import pytest

from TrialLedger.ledger import absence_state, field_state

INT = ("INTERVENTIONAL",)


@pytest.mark.parametrize(
    "present, redacted, applies_to, study_type, status, expected",
    [
        (True, False, None, "INTERVENTIONAL", "COMPLETED", "reported"),
        (True, True, INT, "OBSERVATIONAL", "WITHHELD", "reported"),
        (False, False, INT, "OBSERVATIONAL", "COMPLETED", "not_applicable"),
        (False, True, INT, "OBSERVATIONAL", "WITHHELD", "not_applicable"),
        (False, True, None, "INTERVENTIONAL", "WITHHELD", "redacted"),
        (False, True, INT, "INTERVENTIONAL", "WITHHELD", "redacted"),
        (False, True, None, "INTERVENTIONAL", "COMPLETED", "not_reported"),
        (False, False, None, "INTERVENTIONAL", "WITHHELD", "not_reported"),
        (False, False, INT, "INTERVENTIONAL", "COMPLETED", "not_reported"),
        (False, False, INT, None, "COMPLETED", "not_reported"),
        (False, False, None, None, None, "not_reported"),
    ],
)
def test_states(present, redacted, applies_to, study_type, status, expected):
    assert absence_state(present, redacted, applies_to, study_type, status) == expected


def test_field_state_reads_the_record():
    observational = {
        "protocolSection": {
            "designModule": {"studyType": "OBSERVATIONAL"},
            "statusModule": {"overallStatus": "X"},
        }
    }
    assert field_state(observational, "protocolSection", "designModule", "designInfo", "allocation") == (
        "not_applicable"
    )
    assert field_state(observational, "protocolSection", "designModule", "studyType") == "reported"
    assert field_state(observational, "protocolSection", "eligibilityModule", "maximumAge") == "not_reported"
    withheld = {
        "protocolSection": {
            "designModule": {"studyType": "INTERVENTIONAL"},
            "statusModule": {"overallStatus": "WITHHELD"},
        }
    }
    assert field_state(withheld, "protocolSection", "eligibilityModule", "sex") == "redacted"
    assert field_state(withheld, "protocolSection", "eligibilityModule", "maximumAge") == "not_reported"
