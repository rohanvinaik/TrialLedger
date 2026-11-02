"""Retained NSCLC concept vocabulary for typed layer-two representations.

This fragment is plain data, built from layer2.semantics.vocabulary. No clinical recognizer or eligibility
reader survives here. The historical namespace and exposure record identify where these local definitions
came from; they do not make a word match into a patient fact. See the consolidated source-binding and
assertion design in openspec/changes/add-design-synthesis/design.md.

Concept definitions and argument signatures are retained for explicitly typed atoms. Most concepts are
local names rather than authority codes. Stage and histology labels retain their historical authority
notes without inventing a pinned edition or reproducing proprietary tables. DEFINED_ON records the local
definition date. The performance-status scale remains explicitly unversioned, accepted and flagged only
under the registry loader's legacy-fragment policy. No source interpretation or clinical warrant is implied
by loading this vocabulary.
"""

from typing import Any

from TrialLedger.layer2.semantics.contracts import slug
from TrialLedger.layer2.semantics.loader import FAMILIES, UNVERSIONED
from TrialLedger.layer2.semantics.vocabulary import AGENT_WORDS, ANALYTES, CONDITIONS, GENES, HISTOLOGY

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
