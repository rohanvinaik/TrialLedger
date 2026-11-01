"""The seed fragment: the existing banks' concepts (TrialLedger/banks.py), as
`semantics.contracts.from_legacy` names them, labelled with their development exposure
(`provenance.RULE_EXPOSURE["fragment:nsclc_legacy"]`: the 487 Phase 3 NSCLC trials and the 18-trial pilot).
Plain data, built from the banks' own vocabulary tables so the two cannot drift; add-bank-coverage 2.1 audits
each concept and keeps, migrates or retires it.

Every concept is in TrialLedger's local namespace (the words the banks match, not an authority's codes),
except the stage groups (AJCC, words only) and the histology names (WHO lung tumour names, words only); the
banks cite no edition of either, so none is pinned. No concept carries a code. Each definition carries the
date it was written (DEFINED_ON). No version is invented: the performance-status scale's source edition is
not pinned, so it is marked `loader.UNVERSIONED`, which the build accepts and flags only for this legacy
fragment.
"""

from typing import Any

from TrialLedger.banks import AGENT_WORDS, ANALYTES, CONDITIONS, GENES, HISTOLOGY
from TrialLedger.semantics.contracts import slug
from TrialLedger.semantics.loader import FAMILIES, UNVERSIONED

_LOCAL = "local"
# The date these definitions were written (add-bank-coverage 1.2): their own date, not the fragment's version.
DEFINED_ON = "2026-11-01"
_QUALIFIERS = (("window", "duration_as_written"), ("grade", "grade_as_written"))

# The family of each named condition of bank:conditions; any other is a State. A condition's arguments are
# the window and grade the bank attaches, as far as its family takes them (loader.FAMILIES).
_CONDITION_FAMILY = {
    "informed_consent": "Commitment",
    "compliance": "Commitment",
    "contraception": "Commitment",
    "vitamin_premedication": "Commitment",
    "life_expectancy": "Measurement",
    "sex": "Attribute",
    "recent_surgery": "Event",
    "prior_enrollment": "Event",
    "organ_transplant": "Event",
    "weight_loss": "Event",
    "recent_radiotherapy": "Exposure",
    "live_vaccine": "Exposure",
    "anticoagulant_use": "Exposure",
    "immunosuppression_steroids": "Exposure",
    "interacting_medication": "Exposure",
    "other_investigational": "Exposure",
    "smoking": "Exposure",
    "qtc": "Measurement",
    "pulmonary_function": "Measurement",
    "malabsorption": "Capability",
    "tissue_available": "Capability",
    "investigator_judgment": "Relation",
}
_LAB_ARGUMENTS = (
    ("comparator", "comparator"),
    ("value", "number"),
    ("unit", "unit_as_written"),
    ("qualifier", "text_as_written"),
)

# (concept id, family, arguments, definition, authority, scale)
_ROWS: list[tuple[Any, ...]] = [
    (
        "nsclc.ecog_ps",
        "Measurement",
        (),
        "ECOG, Zubrod or WHO performance status values a criterion allows (bank:performance_status)",
        _LOCAL,
        ("ECOG/Zubrod/WHO performance status, as criteria write it", UNVERSIONED),
    ),
    (
        "nsclc.prior_lines",
        "Count",
        (("scope", "code"),),
        "prior lines of systemic therapy, 0, 1, 2 or 3+, scoped advanced or unspecified (bank:prior_therapy)",
        _LOCAL,
        None,
    ),
    (
        "nsclc.stage",
        "State",
        (("expression", "text_as_written"),),
        "the major stage groups I-IV a stage expression spans, the expression as written (bank:setting)",
        "ajcc",
        None,
    ),
    ("nsclc.extent", "State", (), "disease extent words (bank:setting)", _LOCAL, None),
    ("nsclc.setting_word", "Attribute", (), "treatment-setting words (bank:setting)", _LOCAL, None),
    ("nsclc.resection", "State", (), "resected or resectable lung tumour (bank:setting)", _LOCAL, None),
    (
        "nsclc.organ_function_unspecified",
        "State",
        (),
        '"adequate organ function" with no threshold in the criterion (bank:organ_function)',
        _LOCAL,
        None,
    ),
    (
        "nsclc.age",
        "Attribute",
        (("minimum", "number"), ("maximum", "number")),
        "an age range in years as written (bank:age)",
        _LOCAL,
        None,
    ),
]
_ROWS += [
    (
        f"nsclc.biomarker.{slug(gene)}",
        "State",
        (("expression", "text_as_written"),),
        f"{gene} status of the tumour: positive, negative or unknown, as the bank's words say "
        "(bank:biomarker)",
        _LOCAL,
        None,
    )
    for gene in GENES
]
_ROWS += [
    (
        f"nsclc.prior_agent.{slug(agent)}",
        "Exposure",
        (),
        f"prior exposure to {agent} (bank:prior_therapy)",
        _LOCAL,
        None,
    )
    for agent in AGENT_WORDS
]
_ROWS += [
    (
        f"nsclc.lab.{slug(analyte)}",
        "Measurement",
        _LAB_ARGUMENTS,
        f"a {analyte} threshold, the unit as written, never converted (bank:organ_function)",
        _LOCAL,
        None,
    )
    for analyte in ANALYTES
]
_ROWS += [
    (
        f"nsclc.condition.{slug(name)}",
        family,
        tuple(argument for argument in _QUALIFIERS if argument[0] in FAMILIES[family]),
        f"the named condition or requirement {name}, mentioned (bank:conditions)",
        _LOCAL,
        None,
    )
    for name, family in ((name, _CONDITION_FAMILY.get(name, "State")) for name in CONDITIONS)
]
_ROWS += [
    (
        f"nsclc.histology.{slug(name)}",
        "State",
        (),
        f"{name} histology, named (bank:histology)",
        "who_thoracic",
        None,
    )
    for name in HISTOLOGY
]

FRAGMENT = {
    "name": "nsclc_legacy",
    "version": "nsclc-legacy 2026-10-31",
    "exposure": "fragment:nsclc_legacy",
    "requires": [],
    "concepts": [
        {
            "concept_id": concept_id,
            "family": family,
            "arguments": [list(argument) for argument in arguments],
            "authority": authority,
            "definition": definition,
            "scale": None if scale is None else list(scale),
            "defined_on": DEFINED_ON,
        }
        for concept_id, family, arguments, definition, authority, scale in _ROWS
    ],
    "references": [],
}
