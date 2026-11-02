"""Local NSCLC concept names retained for the typed registry.

These are identifiers and declarative vocabularies, not phrase recognizers. No entry assigns
clinical meaning to free text. The registry retains its development exposure and unpinned
source editions; membership here establishes neither eligibility nor an ontology identity.
"""

GENES = ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2", "PD-L1")

AGENT_WORDS = (
    "PD-1",
    "PD-L1",
    "CTLA-4",
    "immune checkpoint",
    "EGFR inhibitor",
    "ALK inhibitor",
    "MET inhibitor",
    "platinum",
    "docetaxel",
    "taxane",
    "pemetrexed",
    "VEGF inhibitor",
    "chemotherapy",
    "radiotherapy",
)

ANALYTES = (
    "neutrophils",
    "platelets",
    "hemoglobin",
    "creatinine clearance",
    "creatinine",
    "bilirubin",
    "AST",
    "ALT",
    "albumin",
    "leukocytes",
)

CONDITIONS = (
    "informed_consent",
    "compliance",
    "contraception",
    "pregnancy_or_breastfeeding",
    "life_expectancy",
    "measurable_disease",
    "cns_metastases",
    "other_malignancy",
    "hiv",
    "hepatitis",
    "tuberculosis",
    "active_infection",
    "autoimmune_disease",
    "pneumonitis_ild",
    "organ_transplant",
    "immunosuppression_steroids",
    "qtc",
    "cardiac_disease",
    "hypertension",
    "bleeding_thrombosis",
    "anticoagulant_use",
    "gi_perforation_fistula",
    "malabsorption",
    "hypersensitivity",
    "live_vaccine",
    "recent_surgery",
    "recent_radiotherapy",
    "unresolved_toxicity",
    "tissue_available",
    "other_investigational",
    "interacting_medication",
    "substance_or_psychiatric",
    "smoking",
    "effusion",
    "neurologic_disorder",
    "pulmonary_function",
    "weight_loss",
    "investigator_judgment",
    "serious_comorbidity",
    "sex",
    "diagnosis_confirmed",
    "prior_enrollment",
    "vitamin_premedication",
    "organ_impairment",
)

HISTOLOGY = ("non_squamous", "squamous", "adenocarcinoma", "large_cell", "small_cell")
