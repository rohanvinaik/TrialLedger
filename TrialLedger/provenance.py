"""Provenance of every rule, vocabulary and threshold (openspec/changes/add-design-surprise, Decision 1).

Each entry says where a rule came from: "external" (a cited source), "prior" (authored from domain knowledge
before exposure to the population it is measured on) or "derived" (written while reading a named population,
so that population is its development data and cannot confirm it). The banks were written while reading the
487 Phase 3 NSCLC trials of 2015-2024 (pulled 2026-10-31): they are "derived" from it, whatever domain
knowledge shaped them, and their accuracy is measured only on a population no rule was written against.
tests/test_provenance.py fails on any bank, relation, expectation or threshold without an entry here.
"""

from __future__ import annotations

DEV = (
    "derived: 487 interventional Phase 3 NSCLC trials started 2015-2024 (pulled 2026-10-31), development data"
)

PROVENANCE: dict[str, tuple[str, str, str]] = {
    # kind, origin, source or note
    "bank:performance_status": ("bank", DEV, "ECOG / WHO / Zubrod scale wording"),
    "bank:biomarker": (
        "bank",
        DEV,
        "gene symbols (HGNC), state words; negation scope from the residual's conflicts",
    ),
    "bank:prior_therapy": ("bank", DEV, "line-of-therapy wording; agent-class words"),
    "bank:setting": ("bank", DEV, "AJCC 8th edition stage groups; extent and setting words"),
    "bank:organ_function": ("bank", DEV, "analyte names and units as criteria write them"),
    "bank:conditions": ("bank", DEV, "named-condition vocabulary with time windows and CTCAE grades"),
    "bank:age": ("bank", DEV, "age limit wording"),
    "bank:histology": ("bank", DEV, "WHO lung tumour histology names"),
    "bank:endpoints": ("bank", DEV, "endpoint names and acronyms"),
    "bank:stated_targets": (
        "bank",
        DEV,
        "the prior-therapy agent vocabulary, read from an intervention's own entry",
    ),
    "itemize": (
        "parser",
        DEV,
        "the registry's eligibility headings and list markers, with measured variants",
    ),
    "classes:rxclass": (
        "source",
        "external: NLM RxClass (FDA EPC via DailyMed; MED-RT)",
        "rxnav.nlm.nih.gov",
    ),
    "relation:first_line_when_no_prior_advanced_therapy": (
        "relation",
        "prior: line-of-therapy definition",
        "approved 2026-10-31 after Codex counterexamples",
    ),
    "relation:previously_treated_when_prior_advanced_therapy_required": (
        "relation",
        "prior: line definition",
        "approved 2026-10-31",
    ),
    "relation:adjuvant_or_perioperative_when_resection_required": ("relation", "prior", "proposed"),
    "relation:neoadjuvant_or_perioperative_when_resectable_required": ("relation", "prior", "proposed"),
    "relation:advanced_when_metastatic_disease_required": ("relation", "prior: AJCC 8th edition", "approved"),
    "relation:advanced_when_stage_iv_required": ("relation", "prior: AJCC 8th edition", "approved"),
    "relation:consolidation_when_named": ("relation", "prior", "proposed"),
    "expectation:checkpoint_blockers_exclude_autoimmune_disease": (
        "expectation",
        "prior: immune-related adverse events of checkpoint blockade",
        "surfaced on development data; frozen 2026-10-31; unconfirmed",
    ),
    "threshold:STANDARD_SHARE": ("threshold", "prior: first setting", "0.9; to be set on a wider corpus"),
    "threshold:SIGNAL_MIN_TRIALS": ("threshold", "prior: first setting", "5; to be set on a wider corpus"),
    "threshold:SIGNAL_MIN_SPONSORS": ("threshold", "prior: first setting", "3; to be set on a wider corpus"),
    "threshold:expectation_support": ("threshold", "prior: first setting", "10 known observations per cell"),
}
