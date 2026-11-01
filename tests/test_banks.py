"""Banks — one criterion's text typed into atoms, or nothing. Cases are real NSCLC criteria (2015-2024).

Positive: ECOG ranges, lists, upper bounds and reversed order give their values; a gene named as the
tumour's attribute gets the state nearest it ("negative or unknown" both); a PD-L1 percentage is kept as
written; "no prior systemic therapy" is zero lines and "advanced" scope; a count or a progression gives its
lines; agent words in a prior-exposure criterion are prior agents; stage expressions span their groups; a
lab threshold keeps comparator, number and unit as written; every atom's span lies in the text; an age
beside a sex or consent mention is the age bank's ("Male or female ≥ 18 years", NCT04416035).
Negative: a lone ECOG value read first abstains ("ECOG ≥2 points", NCT03372694); a gene named as a drug's
target ("anti-PD-L1", "EGFR TKI") is never a biomarker; "eGFR" is never EGFR; "metastases" in a CNS
exclusion is never "metastatic"; resection of the stomach is never tumour resection; "No prior exposure to
anti-PD-1" is never zero prior lines; a threshold is never converted; text a
bank does not recognise gives no atom; an age in years is never a condition's window, and a window in months
is never taken for an age (NCT04325763, NCT02893332).
"""

import pytest

from TrialLedger.banks import (
    age_limits,
    biomarker_status,
    disease_setting,
    endpoint_classes,
    histology,
    named_conditions,
    organ_function,
    performance_status,
    prior_therapy,
    stated_targets,
    time_points,
    type_criterion,
)


def values(atoms, concept=None):
    return [(a[0], a[1]) for a in atoms if concept is None or a[0] == concept]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("4. Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1", ("0", "1")),
        ("2. ECOG score 0-1;", ("0", "1")),
        ("5. World Health Organization (WHO) performance status 0-2", ("0", "1", "2")),
        ("5. Eastern Cooperative Oncology Group (ECOG) performance status of ≤1.", ("0", "1")),
        (
            "8. Aged 18 to 75 years, ECOG PS: 0\\~1, estimated survival duration more than 3 months.",
            ("0", "1"),
        ),
        (
            "4. Has Eastern Cooperative Oncology group performance status of 0, 1, or 2 at the time",
            ("0", "1", "2"),
        ),
        ("8. 0-1 ECOG score;", ("0", "1")),
    ],
)
def test_performance_status_values(text, expected):
    assert values(performance_status(text)) == [("ecog_ps", expected)]


@pytest.mark.parametrize(
    "text", ["Life expectancy ≥ 12 weeks", "ECOG performance status as assessed by the PI"]
)
def test_no_performance_status_without_a_value(text):
    assert performance_status(text) == []


def test_negative_or_unknown_driver_status():
    text = (
        "3. Documented histologic or cytologic diagnosis of advanced nsNSCLC with negative or unknown "
        "sensitizing "
        "epidermal growth factor receptor (EGFR) mutation, and negative or unknown echinoderm "
        "microtubule-associated protein like 4 anaplastic lymphoma kinase (EML4 ALK) rearrangement."
    )
    found = values(biomarker_status(text))
    assert ("biomarker:EGFR", ("negative", "unknown")) in found
    assert ("biomarker:ALK", ("negative", "unknown")) in found
    assert all(states == ("negative", "unknown") for _, states in found)


@pytest.mark.parametrize(
    "text, gene, states",
    [
        (
            "* Documented ALK-positive disease according to an FDA-approved and CE-marked test",
            "ALK",
            ("positive",),
        ),
        ("* Positive EGFR gene mutation (19/21)", "EGFR", ("positive",)),
        (
            "* Documented epidermal growth receptor factor (EGFR) and anaplastic lymphoma kinase (ALK) "
            "wild-type status",
            "ALK",
            ("negative",),
        ),
        (
            "* Patients with other driver oncogenes (ALK fusion, ROS1 fusion, RET rearrangement, "
            "BRAF mutation)",
            "RET",
            ("positive",),
        ),
    ],
)
def test_driver_status(text, gene, states):
    assert (f"biomarker:{gene}", states) in values(biomarker_status(text))


def test_an_inclusion_sentence_that_excludes_says_so():
    text = (
        "* No prior treatment for Stage IV NSCLC. Participant known to have a sensitizing mutation in the "
        "epidermal growth factor receptor (EGFR) gene or an anaplastic lymphoma kinase (ALK) fusion oncogene "
        "are excluded from the study"
    )
    atoms = [a for a in biomarker_status(text) if a[0] in ("biomarker:EGFR", "biomarker:ALK")]
    assert atoms and all(("text_polarity", "excluded") in a[2] and a[1] == ("positive",) for a in atoms)


def test_a_stated_positive_outranks_an_earlier_absence_of_a_report():
    text = "b. In the absence of a previous ALK fusion positive test report, a sample must be provided"
    assert values(biomarker_status(text)) == [("biomarker:ALK", ("positive",))]


@pytest.mark.parametrize(
    "text",
    [
        "* Prior systemic treatment including a therapy targeting KRAS G12C mutation (e.g., AMG 510).",
        "* Histologically confirmed NSCLC with any PD-L1 TPS",
    ],
)
def test_a_targeted_gene_or_any_status_is_no_atom(text):
    assert [a for a in biomarker_status(text) if a[0] in ("biomarker:KRAS", "biomarker:PD-L1")] == []


def test_recurrence_after_surgery_is_not_progression_after_therapy():
    text = "  * Nodal recurrence after surgery for early stage NSCLC"
    assert values(prior_therapy(text), "prior_lines") == []


def test_a_pd_l1_percentage_is_kept_as_written():
    text = "* Documentation of program death ligand-1 (PD-L1) status of 0 to 49% by IHC performed centrally"
    atoms = [a for a in biomarker_status(text) if a[0] == "biomarker:PD-L1"]
    assert atoms and ("expression", "0to49%") in atoms[0][2]


@pytest.mark.parametrize(
    "text",
    [
        "* Has received prior therapy with an anti-PD-1, anti-PD-L1, or anti-PD-L2 agent",
        "4. Received 1 or 2 prior line(s) of an approved EGFR TKI treatment in the metastatic setting",
        "* Participants who have received prior c-Met-targeted antibodies",
        "* Creatinine clearance (eGFR) ≥ 45 mL/min",
    ],
)
def test_a_drug_target_or_egfr_lab_is_never_a_biomarker(text):
    assert biomarker_status(text) == []


def test_no_prior_systemic_therapy_is_zero_advanced_lines():
    text = "4. No prior systemic antitumor therapy for locally advanced or metastatic NSCLC."
    assert [(a[0], a[1], a[2]) for a in prior_therapy(text)] == [
        ("prior_lines", ("0",), (("scope", "advanced"),))
    ]


@pytest.mark.parametrize(
    "text, lines",
    [
        (
            "4. Received 1 or 2 prior line(s) of an approved EGFR TKI treatment in the metastatic setting",
            ("1", "2"),
        ),
        (
            "4. Previously treated with one platinum based regimen and progression occur during or "
            "after treatment",
            ("1",),
        ),
        ("5. Progression after EGFR-TKIs in patients with driver gene mutation.", ("1", "2", "3+")),
        ("5. Must be treatment-naive for locally advanced or metastatic squamous NSCLC", ("0",)),
    ],
)
def test_prior_lines(text, lines):
    assert values(prior_therapy(text), "prior_lines") == [("prior_lines", lines)]


def test_untreated_metastases_are_not_zero_prior_lines():
    assert (
        values(prior_therapy("* Active or untreated central nervous system (CNS) metastases"), "prior_lines")
        == []
    )
    assert values(prior_therapy("* Untreated advanced NSCLC"), "prior_lines") == [("prior_lines", ("0",))]


def test_no_prior_exposure_to_an_agent_is_not_zero_lines():
    text = "6. No prior exposure to any anti CTLA-4, anti-PD-1, anti-PD-L1, or anti PD L2 antibodies"
    found = prior_therapy(text)
    assert values(found, "prior_lines") == []
    assert {a[1][0] for a in found if a[0] == "prior_agent"} >= {"CTLA-4", "PD-1", "PD-L1"}


@pytest.mark.parametrize(
    "text, groups",
    [
        ("2. ... diagnosis of Stage IV unresectable, recurrent or metastatic nsNSCLC", ("IV",)),
        (
            "* Complete resection of histologically confirmed Stage IB (tumor ≥ 4 cm) to Stage IIIA NSCLC",
            ("I", "II", "III"),
        ),
        (
            "* Had completely resected (R0) NSCLC AJCC/UICC v. 8 stage IIA-IIIA and IIIB (N2 disease only)",
            ("II", "III"),
        ),
        ("3. unresectable locally advanced (stage ⅢB/ⅢC), metastatic or recurrent NSCLC", ("III",)),
    ],
)
def test_stage_groups(text, groups):
    assert values(disease_setting(text), "stage")[0] == ("stage", groups)


@pytest.mark.parametrize(
    "text",
    [
        "* Patients must not have metastatic disease",
        "* Stage IB-IIIA NSCLC, excluding stage IV",
        "* Completely resected NSCLC without metastatic spread",
    ],
)
def test_a_negated_stage_or_extent_is_no_atom(text):
    found = values(disease_setting(text))
    assert ("extent", ("metastatic",)) not in found
    assert ("stage", ("IV",)) not in found


def test_an_unnegated_stage_after_a_negation_elsewhere_counts():
    text = "* No prior systemic therapy for advanced disease; must have stage IV NSCLC"
    assert ("stage", ("IV",)) in values(disease_setting(text))


def test_setting_words_and_resection():
    text = (
        "* Complete resection of histologically confirmed Stage IB to IIIA NSCLC, "
        "eligible for adjuvant therapy"
    )
    found = values(disease_setting(text))
    assert ("resection", ("resected",)) in found
    assert ("setting_word", ("adjuvant",)) in found
    assert ("setting_word", ("neoadjuvant",)) not in found


@pytest.mark.parametrize(
    "text",
    [
        "2. Active central nervous system metastases",
        "* Has any clinically significant gastrointestinal abnormalities such as major "
        "resection of the stomach",
    ],
)
def test_no_false_extent_or_resection(text):
    found = values(disease_setting(text))
    assert ("extent", ("metastatic",)) not in found
    assert all(concept != "resection" for concept, _ in found)


@pytest.mark.parametrize(
    "text",
    [
        "* Other malignancy, except adequately resected non-melanoma skin cancer",
        "* Tissue acquired by bronchoscopic clamp, surgically resected samples of lung cancer",
        "* Stage III NSCLC that cannot be completely resected by surgery",
    ],
)
def test_resection_of_another_site_a_specimen_or_negated_is_not_the_tumours(text):
    assert [a for a in disease_setting(text) if a[0] == "resection"] == []


def test_a_resection_that_was_undergone_counts():
    text = "* Patients who underwent complete resection of stage IB-IIIA NSCLC"
    assert ("resection", ("resected",)) in values(disease_setting(text))


def test_analyte_names_in_any_case_and_acronyms_as_written():
    text = "* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL; Creatinine ≤ 1.5 mg/dL"
    assert [a[1][0] for a in organ_function(text)] == ["platelets", "hemoglobin", "creatinine"]
    assert organ_function("* Egfr ≥ 45 mL/min") == []  # an acronym in another case is not the acronym


def test_an_analyte_without_a_threshold_is_no_atom():
    assert organ_function("* Platelet transfusion within 14 days before the first dose is not allowed") == []


def test_a_threshold_past_the_window_edge_is_read_whole():
    text = "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN."
    found = [(a[1][0], dict(a[2])) for a in organ_function(text)]
    assert ("ALT", {"comparator": "≤", "value": "2.5", "unit": "×ULN"}) in found
    assert ("AST", {"comparator": "≤", "value": "2.5", "unit": "×ULN"}) in found


def test_lab_thresholds_keep_their_units():
    text = (
        "9. Laboratory tests that meet the following requirements:\n\n"
        "   * Aspartate aminotransferase (AST): ≤ 3 x ULN (no liver metastases)\n"
        "   * Total bilirubin (TBIL): ≤1.5 × ULN (no liver metastases)\n"
        "   * Creatinine clearance (eGFR) ≥ 45 mL/min"
    )
    found = [(a[1][0], dict(a[2])) for a in organ_function(text)]
    assert ("AST", {"comparator": "≤", "value": "3", "unit": "x ULN"}) in found
    assert ("bilirubin", {"comparator": "≤", "value": "1.5", "unit": "× ULN"}) in found
    assert ("creatinine clearance", {"comparator": "≥", "value": "45", "unit": "mL/min"}) in found


def test_adequate_organ_function_without_numbers_is_unspecified():
    assert values(organ_function("* Adequate hematologic and renal function")) == [
        ("organ_function_unspecified", ("adequate",))
    ]


@pytest.mark.parametrize(
    "text",
    [
        "* Other inclusion criteria may apply.",
        "* Any of the following cardiac criteria:",
        "",
    ],
)
def test_text_no_bank_recognises_gives_nothing(text):
    assert type_criterion(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "4. Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1",
        "* Documented ALK-positive disease, stage IV, after progression on platinum; AST ≤ 2.5 × ULN",
    ],
)
def test_every_atom_spans_its_words(text):
    for _bank, _concept, _values, _params, start, end in type_criterion(text):
        assert 0 <= start < end <= len(text)
        assert text[start:end].strip() == text[start:end]


@pytest.mark.parametrize(
    "text, concept, window",
    [
        ("* Written informed consent obtained prior to any screening procedures.", "informed_consent", None),
        ("* Life expectancy ≥ 12 weeks", "life_expectancy", "12 weeks"),
        (
            "* Symptomatic, untreated, or actively progressing central nervous system (CNS) metastases",
            "cns_metastases",
            None,
        ),
        (
            "7. Receipt of live attenuated vaccine within 30 days prior to the first dose of IP.",
            "live_vaccine",
            "30 days",
        ),
        (
            "* Any active malignancy less than or equal to 2 years before randomization",
            "other_malignancy",
            "2 years",
        ),
        ("* Acute bacterial or fungal infection requiring intravenous antibiotics", "active_infection", None),
    ],
)
def test_named_conditions_with_their_windows(text, concept, window):
    found = {a[1][0]: dict(a[2]) for a in named_conditions(text)}
    assert concept in found
    assert found[concept].get("window") == window


def test_a_toxicity_grade_is_kept_as_written():
    text = "* Any toxicities from prior therapy must have resolved to CTCAE grade ≤ 1"
    found = {a[1][0]: dict(a[2]) for a in named_conditions(text)}
    assert found["unresolved_toxicity"]["grade"] == "≤1"


@pytest.mark.parametrize(
    "text, params",
    [
        ("* Age ≥ 18 years", {"minimum": "18"}),
        ("2. Age ≥ 18 years and \\<75 years male or females;", {"minimum": "18", "maximum": "75"}),
        ("8. Aged 18 to 75 years, ECOG PS: 0-1", {"minimum": "18", "maximum": "75"}),
        ("1. Male or female ≥ 18 years.", {"minimum": "18"}),
    ],
)
def test_age_limits(text, params):
    assert [dict(a[2]) for a in age_limits(text)] == [params]


@pytest.mark.parametrize(
    "text",
    ["* Other malignancy within ≥ 5 years prior to enrollment", "* Life expectancy ≥ 12 weeks"],
)
def test_a_duration_is_never_an_age(text):
    assert age_limits(text) == []


@pytest.mark.parametrize(
    "text, condition, age",
    [
        # NCT04416035
        ("1. Male or female ≥ 18 years.", ("condition", ("sex",), (), 3, 17), (("minimum", "18"),)),
        # NCT03521154
        (
            "1. Male or female aged at least 18 years.",
            ("condition", ("sex",), (), 3, 17),
            (("minimum", "18"),),
        ),
        # NCT06254599
        (
            "1. At the time of signing the informed consent form (ICF), age is ≥ 18 years.",
            ("condition", ("informed_consent",), (), 30, 46),
            (("minimum", "18"),),
        ),
    ],
)
def test_an_age_beside_a_condition_is_the_age_banks(text, condition, age):
    """Positive: the age bank reads the age (add-bank-coverage 2.1). Negative: the sex or consent mention
    beside it carries no window: an age in years is not a time window, and `sex` (an Attribute) takes none."""
    assert named_conditions(text) == [condition]
    assert [atom[2] for atom in age_limits(text)] == [age]


@pytest.mark.parametrize(
    "text, condition, window",
    [
        # NCT04325763
        (
            "1. 18-75 years old ; Eastern Cooperative Oncology Group (ECOG) performance status of 0 to 1; "
            "Life expectancy ≥ 3 months.",
            ("condition", ("life_expectancy",), (("window", "3 months"),), 93, 108),
            "≥ 3 months",
        ),
        # NCT02893332
        (
            "* Men and women of childbearing age must be willing to use effective contraception while on "
            "treatment and for at least 3 months thereafter",
            ("condition", ("contraception",), (("window", "3 months"),), 69, 82),
            "for at least 3 months",
        ),
    ],
)
def test_a_window_in_months_is_never_taken_for_an_age(text, condition, window):
    """Positive: a window in months keeps its window even where the age bank reads its number as an age.
    Negative: only a window in years can be the age, so these are never dropped.

    Where the age bank reads one at all: its minimum 3 is read from the window's words, a defect recorded
    in the 2.1 audit and owned by 3.1 and 3.2. Once fixed, the age bank reads nothing here and the window
    stays."""
    assert named_conditions(text) == [condition]
    window_start = text.index(window)
    for _concept, _values, _params, start, end in age_limits(text):
        assert start < window_start + len(window) and window_start < end  # the age read overlaps the window


def test_a_window_in_years_apart_from_the_age_is_kept():
    """Positive: a window in years whose words are not the age's is the condition's window, the age before it
    or after it. Negative: neither is taken for the age. Authored (no real criterion of the NSCLC or pilot
    records holds an age beside a window in years apart from it, measured 2026-11-01); the contract and
    registry tests read these texts too."""
    excluded = (("window", "5 years"), ("text_polarity", "excluded"))
    first = "* Age ≥ 18 years; no other malignancy within 5 years"
    assert named_conditions(first) == [("condition", ("other_malignancy",), excluded, 21, 37)]
    assert [atom[3:] for atom in age_limits(first)] == [(6, 16)]
    last = "* No other malignancy within 5 years; age ≥ 18 years"
    assert named_conditions(last) == [("condition", ("other_malignancy",), excluded, 5, 21)]
    assert [atom[3:] for atom in age_limits(last)] == [(42, 52)]


def test_an_age_in_capitalised_years_is_the_age_banks_too():
    """Positive: "Years", as the registry's own age fields write it, is the age bank's like "years". Negative:
    the sex mention beside it carries no window. Authored (no criterion of the NSCLC or pilot records writes
    it beside a mention, measured 2026-11-01)."""
    text = "* Male or female ≥ 18 Years"
    assert named_conditions(text) == [("condition", ("sex",), (), 2, 16)]
    assert age_limits(text) == [("age", ("stated",), (("minimum", "18"),), 17, 27)]


def test_histology_names_and_non_small_cell_is_not_small_cell():
    text = "* Stage IV non-squamous or squamous NSCLC; mixed small-cell lung cancer histology excluded"
    assert [a[1][0] for a in histology(text)] == ["non_squamous", "squamous", "small_cell"]
    assert histology("* Histologically confirmed non-small cell lung cancer") == []


def test_another_sites_squamous_carcinoma_is_not_histology():
    assert histology("* Other malignancy except treated squamous cell carcinoma of the skin") == []


def test_a_documented_status_is_known_either_way():
    assert values(biomarker_status("3. Confirmed tumor PD-L1 status prior to randomization.")) == [
        ("biomarker:PD-L1", ("negative", "positive"))
    ]


@pytest.mark.parametrize(
    "measure, classes",
    [
        ("Overall Survival (OS)", ["overall_survival"]),
        (
            "Primary Efficacy Analysis of Overall Response Rate ( ORR) of MYL-1402O",
            ["objective_response_rate"],
        ),
        ("Disease-free Survival (DFS), as Assessed by the Investigator", ["disease_free_survival"]),
        ("AEs Grade 3-5 With a Difference in Incidence Rate of at Least 2%", ["safety"]),
        ("Plasma Concentration of Alectinib", ["pharmacokinetics"]),
        ("Lung cancer-specific quality of life of the regimens treated subjects", ["quality_of_life"]),
        ("PFS", ["progression_free_survival"]),
    ],
)
def test_endpoint_classes(measure, classes):
    assert endpoint_classes(measure) == classes


@pytest.mark.parametrize("measure", ["The expression level of the subjects' specimens", "os pro"])
def test_no_endpoint_is_guessed(measure):
    assert endpoint_classes(measure) == []


@pytest.mark.parametrize(
    "frame, points",
    [
        ("Up to approximately 3 years", ["3 year"]),
        ("18 weeks after first dosing per patient", ["18 week"]),
        ("Predose (2 hours) Week 3 - Week 96", ["2 hour"]),
        ("6 months, 12 months and 18 months", ["6 month", "12 month", "18 month"]),
        ("Throughout the study", []),
    ],
)
def test_time_points(frame, points):
    assert time_points(frame) == points


def test_stated_targets_read_the_record_and_skip_generic_therapy():
    text = "SCT-I10A is a recombinant humanized anti-PD-1 monoclonal antibody given with chemotherapy"
    assert stated_targets(text) == ["PD-1"]
    assert stated_targets("Standard platinum-based chemotherapy") == ["platinum"]
    assert stated_targets("Best supportive care") == []


def test_an_age_that_only_touches_a_window_is_not_its_words():
    """Positive: spans are half-open, so an age read up to where a window in years begins ("≥ 40 " then
    "within 5 years") shares none of its words, and the window stays the condition's. Negative: the age is
    not taken for that window. Authored (no criterion of the NSCLC or pilot records has such a pair,
    measured 2026-11-01)."""
    text = "* Other malignancy at age ≥ 40 within 5 years"
    assert age_limits(text) == [("age", ("stated",), (("minimum", "40"),), 26, 31)]
    assert text.index("within") == 31
    assert named_conditions(text) == [("condition", ("other_malignancy",), (("window", "5 years"),), 2, 18)]


@pytest.mark.parametrize(
    "text",
    [
        "* The score of ECOG ≥2 points",  # NCT03372694, NCT03244605
        "4. ECOG PS \\< 1",  # NCT03469960
        "6. ECOG 0～1;",  # NCT05157776
        "* The patient must have an ECOG performance status of 0, 1.",  # NCT02273375
        "6. Eastern Cooperative Oncology Group (ECOG) performance status zero (0) to 1.",  # NCT06564324
        "* Good performance status better than Eastern Cooperative Group (ECOG) of 2 or a general status of "
        "Karnofsky (KPS) \\> 70 %",  # NCT02448992
        # NCT03195491
        "* Eastern Cooperative Oncology Group (ECOG) Performance Status of less than or equal to 1",
    ],
)
def test_a_lone_performance_status_value_read_first_abstains(text):
    """Negative (add-bank-coverage 2.1, B7): a lone value read first gives no atom; on the NSCLC records every
    such reading left words unread and was wrong. Positive: a range, list or upper bound still reads
    (test_performance_status_values)."""
    assert performance_status(text) == []


def test_performance_status_reads_the_whole_expression_before_the_scale():
    """Positive: "of 0 or 1 on the ECOG" reads 0 and 1, not the 1 nearest the name; "0-1 ECOG" still reads.
    Negative: an expression ending more than 12 characters before the name is not read."""
    text = "Has a performance status of 0 or 1 on the Eastern Cooperative Oncology Group (ECOG) scale."
    assert [atom[:3] for atom in performance_status(text)] == [("ecog_ps", ("0", "1"), ())]
    assert [atom[1] for atom in performance_status("0-1 ECOG score")] == [("0", "1")]
    assert performance_status("Score 2 at baseline, assessed by the ECOG investigators") == []
