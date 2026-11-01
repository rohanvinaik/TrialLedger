"""Bank readings a clinical reader's test of twenty lung-cancer trials found wrong (2026-11-01), now right.

Positive: a liver criterion naming AST and ALT by full name and abbreviation, with one shared threshold,
reads as one AST and one ALT atom, each with the threshold and its "× upper limit of normal"; a run of
analytes joined by "and" shares the threshold after the last; a second threshold joined by "or" still belongs
to its analyte.
Negative: imaging done "to rule out metastatic disease" never states metastatic disease; an analyte never
takes the threshold of another analyte named between; no analyte is read twice against one threshold; a
threshold whose unit is "upper limit normal" never loses it.
"""

from TrialLedger.banks import disease_setting, organ_function

# NCT02595944 (ANVIL), inclusion criteria 15 and 3, as the registry writes them.
LIVER = (
    "* Serum aspartate transaminase (aspartate aminotransferase \\[AST\\]) and serum alanine transaminase "
    "(alanine aminotransferase \\[ALT\\]) =\\< 2.5 x upper limit normal "
    "(within 2 weeks prior to randomization)"
)
IMAGING = (
    "* Baseline chest CT must be performed within 1 month (30 days) prior to randomization to ensure no "
    "evidence of disease; if clinically indicated, additional imaging studies must be performed to rule out "
    "metastatic disease"
)


def labs(text):
    return [(atom[1][0], dict(atom[2])) for atom in organ_function(text) if atom[0] == "lab"]


def test_a_shared_liver_threshold_reads_once_per_analyte_with_its_reference():
    assert labs(LIVER) == [
        ("AST", {"comparator": "≤", "value": "2.5", "unit": "x upper limit normal"}),
        ("ALT", {"comparator": "≤", "value": "2.5", "unit": "x upper limit normal"}),
    ]


def test_ruling_out_metastatic_disease_states_no_extent():
    assert [atom for atom in disease_setting(IMAGING) if atom[0] == "extent"] == []
    assert [atom[1] for atom in disease_setting("Metastatic disease is required")] == [("metastatic",)]


def test_an_analyte_never_takes_the_next_analytes_threshold():
    found = labs("Hemoglobin >= 9 g/dL, platelets >= 100,000/mm3 and ANC >= 1500/mm3")
    assert found == [
        ("hemoglobin", {"comparator": "≥", "value": "9", "unit": "g/dL"}),
        ("platelets", {"comparator": "≥", "value": "100,000", "unit": "/mm3"}),
        ("neutrophils", {"comparator": "≥", "value": "1500", "unit": "/mm3"}),
    ]


def test_a_second_threshold_joined_by_or_still_belongs_to_its_analyte():
    found = labs("Total bilirubin <= 1.5 x ULN or <= 3 x ULN in Gilbert's syndrome")
    assert [value["value"] for name, value in found if name == "bilirubin"] == ["1.5", "3"]


def test_a_run_joined_by_and_shares_the_threshold():
    assert [name for name, _ in labs("AST and ALT <= 2.5 x ULN")] == ["AST", "ALT"]
