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

# A bank whose rules the pilot's corrections revised (add-targeted-questions, "Symbolic corrections from the
# pilot") was derived from the pilot too.
DEV_AND_PILOT = (
    DEV + "; and the 18-trial stratified pilot of 2026-10-31 (seed pilot-2026-10-31), development data"
)

PROVENANCE: dict[str, tuple[str, str, str]] = {
    # kind, origin, source or note
    "bank:performance_status": (
        "bank",
        DEV_AND_PILOT,
        "ECOG / WHO / Zubrod scale wording; the API's escaped less-or-equal (=\\<) from the pilot's labels; "
        "a lone value read first abstains, every such reading on the NSCLC records being wrong "
        "(add-bank-coverage 2.1, 2026-11-01)",
    ),
    "bank:biomarker": (
        "bank",
        DEV,
        "gene symbols (HGNC), state words; negation scope from the residual's conflicts",
    ),
    "bank:prior_therapy": ("bank", DEV, "line-of-therapy wording; agent-class words"),
    "bank:setting": ("bank", DEV, "AJCC 8th edition stage groups; extent and setting words"),
    "bank:organ_function": (
        "bank",
        DEV_AND_PILOT,
        "analyte names and units as criteria write them; the API's escaped comparators and paired thresholds "
        "with their qualifiers from the pilot's labels",
    ),
    "bank:conditions": (
        "bank",
        DEV_AND_PILOT,
        "named-condition vocabulary with time windows (a temporal marker required), CTCAE grades and in-text "
        "negation; boundaries corrected from Claude's blind labels of the pilot; a window in years whose "
        "words overlap the age bank's span is that age, never the mention's window (add-bank-coverage 2.1, "
        "2026-11-01, on the same two populations)",
    ),
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
    "pattern:eligibility_abbreviated": (
        "pattern",
        DEV,
        'criteria._ABBREVIATED: a record that says it lists only some criteria ("Key Exclusion Criteria", '
        '"other protocol-defined criteria may apply"); measured there 2026-10-31: misses three wordings (11 '
        'records) and matches "include, but are not limited to" inside a criterion\'s examples (7 records), '
        "left for the founder",
    ),
    "pattern:eligibility_complete": (
        "pattern",
        "prior: authored before measuring",
        "criteria._COMPLETE: a record that says its list is the whole of its criteria; matches nothing in "
        "the development data, so its tests are synthetic; no ascertainment rule reads it yet",
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
    "representation:near_miss": (
        "representation",
        "prior: add-design-surprise Decision 5 (declared before any pair was read)",
        "setting (one value under approved relations) and experimental drug classes (every drug's class"
        " known: RxClass, or stated by its record); predicates ECOG, histology, the checkpoint expectation;"
        " an unknown never matches; classes match only as written (the two vocabularies are not aligned)",
    ),
    "gate:mention_value": (
        "gate",
        "derived: the auditor pilot of 2026-11-01 (18 trials, seed pilot-2026-10-31), development data",
        "overrules qwen3:8b's wrong_value on a named-condition claim the rules re-derive in the same "
        "effective section and window; on the pilot 25 right and 3 wrong claims overruled; to confirm on an "
        "unseen sample",
    ),
    "fragment:nsclc_legacy": (
        "fragment",
        DEV + "; and the 18-trial stratified pilot of 2026-10-31/11-01 (seed pilot-2026-10-31), development "
        "data",
        "the seed registry fragment: the existing banks' concepts, named from their own vocabulary tables "
        "(TrialLedger/semantics/fragments/nsclc_legacy.py); audited by add-bank-coverage 2.1",
    ),
    "threshold:STANDARD_SHARE": ("threshold", "prior: first setting", "0.9; to be set on a wider corpus"),
    "threshold:SIGNAL_MIN_TRIALS": ("threshold", "prior: first setting", "5; to be set on a wider corpus"),
    "threshold:SIGNAL_MIN_SPONSORS": ("threshold", "prior: first setting", "3; to be set on a wider corpus"),
    "threshold:expectation_support": ("threshold", "prior: first setting", "10 known observations per cell"),
}

# ── concept provenance (add-bank-coverage Decision 5, founder decision B5) ─────────────────────────────
#
# Where a concept's identity comes from, apart from where a rule that recognizes it came from. An authority is
# cited by a registry concept entry (TrialLedger/semantics); a concept citing none is refused. The edition is
# None until the package that first uses the authority pins it from its source (add-bank-coverage 3.x); a
# code from an authority is refused while its edition is unpinned. No edition is invented or borrowed: the
# local namespace has none (each local concept carries its own definition date instead). Licence status is
# one of LICENCE_STATUSES:
#   open              free to use and to reproduce codes;
#   open_with_terms   free, under terms the user accepts (LOINC, UCUM: Regenstrief's terms);
#   licence_required  not usable in v1 without a licence TrialLedger does not hold (SNOMED CT: UMLS);
#   words_only        proprietary: its names are recognized as words citing the edition, its codes and tables
#                     never reproduced (DSM, AJCC);
#   local             TrialLedger's own namespace: a written definition, argument types and examples.

LICENCE_STATUSES = ("open", "open_with_terms", "licence_required", "words_only", "local")

# authority id → (name, edition or None, licence status, note). B5's open authorities first.
CONCEPT_AUTHORITIES: dict[str, tuple[str, str | None, str, str]] = {
    "loinc": ("LOINC", None, "open_with_terms", "observations; a bare analyte name may not justify a code"),
    "ucum": ("UCUM", None, "open_with_terms", "units of measure"),
    "rxnorm": ("RxNorm", None, "open", "drug identity, read through NLM's RxNav"),
    "rxclass": ("RxClass", None, "open", "drug classes, each with its named source (classes:rxclass)"),
    "mesh": ("MeSH", None, "open", "indexes and samples; never decides semantics"),
    "ncit": ("NCI Thesaurus", None, "open", "conditions, findings, procedures"),
    "hgnc": ("HGNC", None, "open", "gene symbols"),
    "hgvs": ("HGVS", None, "open", "variant nomenclature"),
    "icd10cm": ("ICD-10-CM", None, "open", "diagnoses; psychiatric diagnoses are coded here or in ICD-11"),
    "icd11": ("ICD-11", None, "open", "diagnoses"),
    "snomedct": ("SNOMED CT", None, "licence_required", "needs a UMLS licence; not required for v1"),
    "dsm": ("DSM", None, "words_only", "proprietary: diagnosis names kept as words only, coded through ICD"),
    "ajcc": (
        "AJCC Cancer Staging Manual",
        None,
        "words_only",
        "proprietary: stage groups recognized as words citing the edition, its tables never reproduced; "
        "bank:setting and two approved relations name the 8th edition in their notes, but no edition is "
        "pinned from its source yet; the oncology package (5.1) pins one (the founder, 2026-11-01: wait)",
    ),
    "who_thoracic": (
        "WHO classification of lung tumours",
        None,
        "words_only",
        "histology names as written in criteria (bank:histology); edition not cited by the bank",
    ),
    "local": (
        "TrialLedger local namespace",
        None,
        "local",
        "no edition: each concept carries its own written definition and definition date",
    ),
}

# ── rule provenance: the populations a rule was written or revised against (Decision 5, B4) ─────────────
#
# A population named here informed the rules that list it, so it never confirms them. RULE_EXPOSURE's
# populations are keys of DEVELOPMENT_POPULATIONS; `frozen` is the version and date a rule was frozen at
# (None: not frozen); `confirmed_on` names the confirmation batches it was later assessed on (none yet).

DEVELOPMENT_POPULATIONS: dict[str, str] = {
    "nsclc_phase3_2015_2024": "487 interventional Phase 3 NSCLC trials started 2015-2024 (pulled 2026-10-31)",
    "pilot_2026_10_31": "the 18-trial stratified pilot of 2026-10-31/11-01 (seed pilot-2026-10-31), all "
    "categories; its audit read every existing bank's atoms",
}

# The pilot's audit (2026-10-31/11-01) read every existing bank's atoms, so every bank lists it.
_NSCLC_AND_PILOT = ("nsclc_phase3_2015_2024", "pilot_2026_10_31")

# rule or fragment key → (populations inspected, frozen version and date or None, confirmation batches)
RULE_EXPOSURE: dict[str, tuple[tuple[str, ...], str | None, tuple[str, ...]]] = {
    "bank:performance_status": (_NSCLC_AND_PILOT, None, ()),
    "bank:biomarker": (_NSCLC_AND_PILOT, None, ()),
    "bank:prior_therapy": (_NSCLC_AND_PILOT, None, ()),
    "bank:setting": (_NSCLC_AND_PILOT, None, ()),
    "bank:organ_function": (_NSCLC_AND_PILOT, None, ()),
    "bank:conditions": (_NSCLC_AND_PILOT, None, ()),
    "bank:age": (_NSCLC_AND_PILOT, None, ()),
    "bank:histology": (_NSCLC_AND_PILOT, None, ()),
    "bank:endpoints": (_NSCLC_AND_PILOT, None, ()),
    "bank:stated_targets": (_NSCLC_AND_PILOT, None, ()),
    "gate:mention_value": (("pilot_2026_10_31",), None, ()),
    # the seed registry fragment over the existing banks' concepts (TrialLedger/semantics/fragments)
    "fragment:nsclc_legacy": (_NSCLC_AND_PILOT, None, ()),
}
