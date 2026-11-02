"""Declared analysis scopes, not registry classifications or automatic applicability rules."""

KNOWN_UNIVERSES = ("oncology.solid", "oncology.heme", "general")

PACK_COORDINATES = {
    "oncology.solid/setting_and_line": ("setting", "prior_advanced_lines"),
    "oncology.solid/gene_selection": tuple(
        "selection:" + gene for gene in ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2")
    ),
    "oncology.solid/nsclc_relations": (),
}
PACK_RELATIONS = {
    "oncology.solid/setting_and_line": (),
    "oncology.solid/gene_selection": (),
    "oncology.solid/nsclc_relations": (
        "first_line_when_no_prior_advanced_therapy",
        "previously_treated_when_prior_advanced_therapy_required",
        "adjuvant_or_perioperative_when_resection_required",
        "neoadjuvant_or_perioperative_when_resectable_required",
        "advanced_when_metastatic_disease_required",
        "advanced_when_stage_iv_required",
        "consolidation_when_named",
    ),
}
