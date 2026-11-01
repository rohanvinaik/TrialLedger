"""landscape.json: the record of truth an agent answers from (add-agent-operation, Decisions 7 and 8).

One record per run: the request; the resolved scope (request resolution's, carried as given); the manifest
(the data timestamp, the API version, each study's digest, their Merkle root, the code commit, the rule
versions, the retrieval coverage); per study, the ten-point extract and its extras; across the cohort, the
profile as `profile.py` computes it for design.xlsx; the review queue's closed questions; coverage per trial
type from the supported-type matrix; and its self-description: `statuses` (what each status means),
`envelope` (what each key of a value means) and `fields`, which describes every field: its meaning, its value
type, the statuses it may carry and its source.

Every value a person reads is an envelope: the value, its status, its source (its location in the study
record), the rule that read it ("" when the value is the record's own, exactly as held), a note (an absence
state, or why it is unresolved), and the study's registry link. Statuses (STATUSES): known, interpolated,
proposed, not_stated, not_posted, unresolved. Nothing here reads a study differently from the reading the
workbooks are laid out from (`reading.read_population`): the extract is assembled from that reading and the
record's own fields. A registered outcome is planned, never efficacy: planned outcomes and posted results are
different fields, and a study without posted results states "no results posted".
"""

from __future__ import annotations

import copy
from typing import Any

from TrialLedger import __version__, warrants
from TrialLedger.coherence import RELATIONS, SETTINGS
from TrialLedger.design import VERSION as DESIGN_VERSION
from TrialLedger.design import _profile_trials
from TrialLedger.ledger import as_list, field_state, get, location, results_state
from TrialLedger.links import document_link, pubmed_link, reference_role, study_link
from TrialLedger.profile import (
    SIGNAL_MIN_SPONSORS,
    SIGNAL_MIN_TRIALS,
    STANDARD_SHARE,
    element_key,
    frequency_rows,
    mechanism_rows,
    occupancy_rows,
)
from TrialLedger.reading import effective_section
from TrialLedger.symbolic import _axes
from TrialLedger.typematrix import UNIVERSE, declared_manifest, study_coordinates, universe_status
from TrialLedger.workbook import CODE_ROOT, NO_RESULTS, RESULTS_TEXT

SCHEMA_VERSION = "1"
JSON_NAME = "landscape.json"
P = "protocolSection"
R = "resultsSection"
ELIGIBILITY_TEXT = f"{P}.eligibilityModule.eligibilityCriteria"
# What each key of a value's envelope means, in the envelope's order; the record carries it as `envelope`.
ENVELOPE_MEANINGS = {
    "value": "the value: the record's own when the rule is empty, else what the rule read; null only when "
    "the status is not_stated or unresolved (nothing stated, or nothing the rules could settle)",
    "status": "how far the value can be relied on: one of `statuses`, and one its field admits (`fields`)",
    "source": "where the value was read: its field path in the study record (list positions as [i]), or what "
    "the rule read",
    "rule": 'the named rule that read the value; "" when it is the record\'s own, exactly as held',
    "note": "for a value not stated, the ledger's absence state (not_reported, not_applicable, redacted); "
    "for one unresolved or proposed, why; otherwise empty or where it was read (a criterion's piece)",
    "link": "the study's registry page, where the value can be checked against the registry",
}
ENVELOPE = tuple(ENVELOPE_MEANINGS)
STATUSES = {
    "known": "read from the record as it holds it, or derived from it by a named rule the founder approved",
    "interpolated": "a guess from a rule over the record's wording (a name's stem), never a reading",
    "proposed": "derived through a relation that is proposed, not approved: shown, never reported as known",
    "not_stated": "the record holds no value; the note gives the ledger's absence state; never zero or no",
    "not_posted": "no results are posted for the study (the registry's own flag): nothing is reported",
    "unresolved": "the rules cannot settle it from the record; the note says why; it is not an absence",
}
NOT_EXPERIMENTAL = (
    "not an experimental arm's drug, biological or genetic intervention: only those are classed"
)
UNTYPED = "no bank typed this criterion: no element to measure"
OUTCOME_KINDS = (
    ("primary", "primaryOutcomes"),
    ("secondary", "secondaryOutcomes"),
    ("other", "otherOutcomes"),
)
EVENT_TABLES = (("serious", "seriousEvents"), ("other", "otherEvents"))
ALL_TRIALS = "all trials"  # the stratum design.xlsx's profile names the whole cohort by
# The columns of each cohort table, in the order of its rows' values.
FREQUENCY_COLUMNS = (
    "stratum",
    "element",
    "stating",
    "absent",
    "unresolved_empty",
    "unresolved_no_rule_match",
    "unresolved_abbreviated",
    "unresolved_unspecified",
    "unresolved",
    "trials",
    "statement_rate",
    "lower_bound",
    "upper_bound",
    "surprisal_bits",
    "sponsors",
    "standard_tier",
    "estimand",
)
MECHANISM_COLUMNS = (
    "stratum",
    "class",
    "element",
    "in_class_stating",
    "in_class",
    "others_stating",
    "others",
    "rate_in_class",
    "rate_in_others",
    "difference",
    "least_favourable_difference",
    "sponsors",
    "unresolved_class_trials",
    "abbreviated_in_class",
    "abbreviated_in_others",
    "status",
)
OCCUPANCY_COLUMNS = ("setting", "class", "occupying", "could_fall_here", "state")
NEAR_MISS_COLUMNS = (
    "a",
    "b",
    "difference",
    "value_a",
    "value_b",
    "sponsor_a",
    "sponsor_b",
    "start_year_a",
    "start_year_b",
    "predicates_agreeing",
)
ALIGNED_COLUMNS = (*NEAR_MISS_COLUMNS, "basis_a", "basis_b")
ENDPOINT_COLUMNS = ("outcome_type", "endpoint_class", "trials", "ncts", "outcomes", "time_points")
STRUCTURE_COLUMNS = ("rxcui_a", "name_a", "rxcui_b", "name_b", "taxonomy", "class", "release")
REVIEW_COLUMNS = ("nct", "kind", "element", "why", "priority", "evidence", "question", "options", "answer")
UNIVERSE_COLUMNS = ("nct", "universe", "coordinates")
MANIFEST_KEYS = (
    "api_version",
    "data_timestamp",
    "study_digests",
    "merkle_root",
    "code_commit",
    "rule_versions",
    "retrieval",
)
RULE_VERSIONS = {
    "landscape_schema": SCHEMA_VERSION,
    "trialledger": __version__,
    "design": DESIGN_VERSION,
    "derivation_code_root": CODE_ROOT,
    "relations": {relation.id: relation.approval for relation in RELATIONS},
}

# The keys of each object value, in order: `fields` names them, and tests/test_landscape.py holds every value
# of a record to them. AS_HELD marks an object the record holds, shown exactly as it holds it.
AS_HELD = "as the record holds it"
COVERAGE_KEYS = ("content", "sectioning", "inclusion", "exclusion", "markers")
ATOM_KEYS = ("bank", "concept", "values", "params", "span", "section", "element")
BIOMARKER_KEYS = ("biomarker", "states", "params", "span", "piece", "section")
BIOMARKER_OUTCOME_KEYS = ("outcome_type", "measure", "time_frame", "time_points")
MEASUREMENT_KEYS = (
    "outcome_type",
    "measure",
    "time_frame",
    "unit",
    "param_type",
    "dispersion_type",
    "arm",
    "group_id",
    "class",
    "category",
    "value",
    "spread",
    "lower_limit",
    "upper_limit",
    "endpoint_classes",
)
EVENT_GROUP_KEYS = (
    "group_id",
    "title",
    "deaths_affected",
    "deaths_at_risk",
    "serious_affected",
    "serious_at_risk",
    "other_affected",
    "other_at_risk",
)
EVENT_KEYS = (
    "table",
    "term",
    "organ_system",
    "source_vocabulary",
    "assessment_type",
    "group_id",
    "arm",
    "affected",
    "at_risk",
    "events",
)
TIER_KEYS = ("element", "tier", "statement_rate", "lower_bound", "upper_bound")
CLASS_KEYS = ("state", "classes", "resolved_by")
AXES_KEYS = ("drug", "identity", "reason", "names", "classes", "targets", "alignment", "atc")
MODALITY_KEYS = ("property", "value", "polarity", "scope", "warrant")
PUBLICATION_KEYS = ("pmid", "type", "role", "citation", "pubmed")
DOCUMENT_KEYS = (
    "type",
    "label",
    "has_protocol",
    "has_sap",
    "has_icf",
    "date",
    "upload_date",
    "filename",
    "url",
)

# ── the self-description: every field, its meaning, type, statuses and source ─────────────────────────

STATED = ("known", "not_stated")
KNOWN = ("known",)
RESOLVED = ("known", "unresolved")
WITH_PROPOSED = ("known", "proposed", "unresolved")
RESULTS = ("known", "not_posted", "not_stated", "unresolved")
MODALITY = ("known", "interpolated")
ROWS = "list of row: "

_CRITERION = (
    ("piece", "integer", (), "criteria.itemize", "the criterion's piece number in the eligibility text"),
    ("text", "value(string)", KNOWN, ELIGIBILITY_TEXT, "the criterion's exact text, itemized"),
    (
        "atoms",
        "list of value(object: " + ", ".join(ATOM_KEYS) + ")",
        KNOWN,
        ELIGIBILITY_TEXT,
        "each atom a bank typed: bank, concept, values, params, its span, effective section and element",
    ),
)
_OUTCOME = (
    ("measure", "value(string)", STATED, f"{P}.outcomesModule.<type>Outcomes[i].measure", "the measure"),
    ("time_frame", "value(string)", STATED, f"{P}.outcomesModule.<type>Outcomes[i].timeFrame", "time frame"),
    ("description", "value(string)", STATED, f"{P}.outcomesModule.<type>Outcomes[i].description", "as given"),
    (
        "endpoint_classes",
        "value(list of string)",
        KNOWN,
        "banks.endpoint_classes over the measure",
        "the endpoint classes the measure's title names; an empty list when it names none, never a guess",
    ),
    (
        "time_points",
        "value(list of string)",
        KNOWN,
        "banks.time_points over the time frame",
        "the time points the time frame states as number then unit",
    ),
)
FIELD_TABLE: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    ("schema_version", "string", (), "landscape.SCHEMA_VERSION", "the version of this record's schema"),
    ("request", "opaque", (), "the request as given", "the user's request, as the agent gave it"),
    ("scope", "opaque", (), "request resolution", "every expansion of the request, its source and query"),
    ("manifest", "section", (), "the run", "what the record was read from and by"),
    ("manifest.api_version", "string", (), "/version: apiVersion", "the registry API's version"),
    ("manifest.data_timestamp", "string", (), "/version: dataTimestamp", "the registry snapshot read"),
    (
        "manifest.study_digests",
        "list of string",
        (),
        "warrants.study_digest",
        "each study's digest, in order",
    ),
    ("manifest.merkle_root", "string", (), "warrants.merkle_root", "the Merkle root of the study digests"),
    ("manifest.code_commit", "string", (), "record.code_commit", "the code's git commit, marked when dirty"),
    ("manifest.rule_versions", "object", (), "landscape.RULE_VERSIONS", "schema, tool, design, code root"),
    ("manifest.retrieval", "object", (), "the pull", "how many studies matched and how many were read"),
    ("studies", "list of section", (), "each study record", "every study read, in the pull's order"),
    ("studies[].nct", "value(string)", STATED, f"{P}.identificationModule.nctId", "the NCT number"),
    ("studies[].digest", "string", (), "warrants.study_digest", "the study record's digest"),
    ("studies[].link", "string", (), "links.study_link", "the study's registry page"),
    ("studies[].population", "section", (), f"{P}.eligibilityModule", "point 1: the patient population"),
    *(
        (f"studies[].population.{name}", f"value({kind})", STATED, f"{P}.eligibilityModule.{key}", meaning)
        for name, key, kind, meaning in (
            ("minimum_age", "minimumAge", "string", "the minimum age, as written"),
            ("maximum_age", "maximumAge", "string", "the maximum age, as written"),
            ("std_ages", "stdAges", "list of string", "the registry's standard age groups"),
            ("sex", "sex", "string", "the sexes eligible"),
            ("gender_based", "genderBased", "boolean", "whether eligibility is based on gender"),
            ("gender_description", "genderDescription", "string", "the gender eligibility description"),
            ("healthy_volunteers", "healthyVolunteers", "boolean", "whether healthy volunteers are accepted"),
        )
    ),
    ("studies[].eligibility", "section", (), ELIGIBILITY_TEXT, "the eligibility text and how it was read"),
    ("studies[].eligibility.text", "value(string)", STATED, ELIGIBILITY_TEXT, "the whole eligibility text"),
    (
        "studies[].eligibility.itemized",
        "value(string)",
        KNOWN,
        "criteria.itemize",
        "itemized (criteria found), no_list_markers (prose only) or empty",
    ),
    (
        "studies[].eligibility.coverage",
        "value(object: " + ", ".join(COVERAGE_KEYS) + ")",
        KNOWN,
        "criteria.eligibility_coverage",
        "content, sectioning, and per section whether the record says its list is abbreviated or complete",
    ),
    *(
        entry
        for section, point in (
            ("inclusion", "point 2: inclusion criteria"),
            ("exclusion", "point 3: exclusion criteria"),
            ("unsectioned", "criteria under no inclusion or exclusion heading"),
        )
        for entry in (
            (f"studies[].{section}", "list of section", (), "criteria.itemize", f"{point}, as itemized"),
            *((f"studies[].{section}[].{n}", t, s, src, m) for n, t, s, src, m in _CRITERION),
        )
    ),
    (
        "studies[].line_of_therapy_and_setting",
        "section",
        (),
        "coherence.resolve",
        "point 4: the design coordinates, each a domain of still-possible values",
    ),
    *(
        entry
        for name, meaning in (
            ("setting", "the treatment setting"),
            ("prior_advanced_lines", "the prior lines of therapy for advanced disease"),
        )
        for entry in (
            (
                f"studies[].line_of_therapy_and_setting.{name}",
                "value(list of string)",
                RESOLVED,
                "coherence.resolve under approved relations",
                f"{meaning}: known when one value remains, unresolved when several or none (a conflict)",
            ),
            (
                f"studies[].line_of_therapy_and_setting.{name}_with_proposed_relations",
                "value(list of string)",
                WITH_PROPOSED,
                "coherence.resolve with proposed relations added",
                f"{meaning} as proposed relations would narrow it: the approved value's status when they do "
                "not narrow it, proposed when they narrow it, unresolved when they leave none (a conflict)",
            ),
        )
    ),
    (
        "studies[].outcomes",
        "section",
        (),
        f"{P}.outcomesModule",
        "point 5: the registered (planned) outcomes",
    ),
    *(
        entry
        for kind, meaning in (
            ("primary", "primary outcomes"),
            ("secondary", "secondary outcomes"),
            ("other", "other pre-specified outcomes"),
        )
        for entry in (
            (
                f"studies[].outcomes.{kind}",
                "list of section",
                (),
                f"{P}.outcomesModule",
                f"planned {meaning}",
            ),
            *((f"studies[].outcomes.{kind}[].{n}", t, s, src, m) for n, t, s, src, m in _OUTCOME),
        )
    ),
    ("studies[].biomarkers", "section", (), "the banks and the outcomes", "point 6: biomarkers by role"),
    (
        "studies[].biomarkers.eligibility",
        "list of value(object: " + ", ".join(BIOMARKER_KEYS) + ")",
        KNOWN,
        "banks.biomarker_status over the criteria",
        "each biomarker a criterion states, with the states it allows and its effective section",
    ),
    (
        "studies[].biomarkers.outcome",
        "list of value(object: " + ", ".join(BIOMARKER_OUTCOME_KEYS) + ")",
        KNOWN,
        "banks.endpoint_classes (biomarker_endpoint) over primary and secondary outcomes",
        "each primary or secondary outcome whose measure names a biomarker endpoint",
    ),
    (
        "studies[].biomarkers.exploratory",
        "list of value(object: " + ", ".join(BIOMARKER_OUTCOME_KEYS) + ")",
        KNOWN,
        "banks.endpoint_classes (biomarker_endpoint) over other pre-specified outcomes",
        "each other pre-specified outcome whose measure names a biomarker endpoint",
    ),
    ("studies[].efficacy", "section", (), R, "point 7: posted outcome results; never a registered outcome"),
    (
        "studies[].efficacy.results",
        "value(string)",
        RESULTS,
        "ledger.results_state over hasResults and the results section",
        'whether results are posted: "results posted", or "no results posted" (not_posted)',
    ),
    (
        "studies[].efficacy.measurements",
        "list of value(object: " + ", ".join(MEASUREMENT_KEYS) + ")",
        KNOWN,
        f"{R}.outcomeMeasuresModule",
        "each posted measurement per arm (group), with its measure's type, title, time frame, unit and class",
    ),
    ("studies[].safety", "section", (), f"{R}.adverseEventsModule", "point 8: posted adverse events per arm"),
    (
        "studies[].safety.results",
        "value(string)",
        RESULTS,
        "ledger.results_state over hasResults and the results section",
        'whether results are posted: "results posted", or "no results posted" (not_posted)',
    ),
    (
        "studies[].safety.time_frame",
        "value(string)",
        STATED,
        f"{R}.adverseEventsModule.timeFrame",
        "the adverse events' time frame",
    ),
    (
        "studies[].safety.groups",
        "list of value(object: " + ", ".join(EVENT_GROUP_KEYS) + ")",
        KNOWN,
        f"{R}.adverseEventsModule.eventGroups",
        "each arm's (event group's) deaths, serious and other events: affected and at risk, as stated",
    ),
    (
        "studies[].safety.events",
        "list of value(object: " + ", ".join(EVENT_KEYS) + ")",
        KNOWN,
        f"{R}.adverseEventsModule.seriousEvents and otherEvents",
        "each adverse event per arm: its table, term, organ system, affected, at risk and events, as stated",
    ),
    (
        "studies[].exploratory_measures",
        "list of section",
        (),
        f"{P}.outcomesModule.otherOutcomes",
        "point 9: the other pre-specified outcomes",
    ),
    *(
        (f"studies[].exploratory_measures[].{n}", t, s, src.replace("<type>", "other"), m)
        for n, t, s, src, m in _OUTCOME
    ),
    (
        "studies[].standard_language",
        "list of section",
        (),
        "profile.frequency_rows over all trials",
        "point 10: each criterion's elements with their standard tier across the cohort",
    ),
    (
        "studies[].standard_language[].piece",
        "integer",
        (),
        "criteria.itemize",
        "the criterion's piece number",
    ),
    ("studies[].standard_language[].section", "string", (), "criteria.itemize", "the criterion's section"),
    (
        "studies[].standard_language[].elements",
        "list of value(object: " + ", ".join(TIER_KEYS) + ")",
        RESOLVED,
        "profile.frequency_rows (all trials), keyed by profile.element_key",
        "each element: its tier (met, not_met, unresolved), statement rate and full-criteria interval",
    ),
    *(
        (f"studies[].{name}", f"value({kind})", STATED, source, meaning)
        for name, kind, source, meaning in (
            ("sponsor", "string", f"{P}.sponsorCollaboratorsModule.leadSponsor.name", "the lead sponsor"),
            ("phases", "list of string", f"{P}.designModule.phases", "the phases"),
            ("overall_status", "string", f"{P}.statusModule.overallStatus", "the recruitment status"),
            ("study_type", "string", f"{P}.designModule.studyType", "the study type"),
            ("conditions", "list of string", f"{P}.conditionsModule.conditions", "the conditions"),
            (
                "start_date",
                "object: " + AS_HELD,
                f"{P}.statusModule.startDateStruct",
                "the start date and its type",
            ),
            (
                "primary_completion_date",
                "object: " + AS_HELD,
                f"{P}.statusModule.primaryCompletionDateStruct",
                "the primary completion date and its type",
            ),
            (
                "completion_date",
                "object: " + AS_HELD,
                f"{P}.statusModule.completionDateStruct",
                "the completion date and its type",
            ),
            (
                "enrollment",
                "object: " + AS_HELD,
                f"{P}.designModule.enrollmentInfo",
                "the enrollment count and its type",
            ),
        )
    ),
    (
        "studies[].arms",
        "list of value(object: " + AS_HELD + ")",
        STATED,
        f"{P}.armsInterventionsModule.armGroups",
        "each arm as the record holds it",
    ),
    (
        "studies[].interventions",
        "list of section",
        (),
        f"{P}.armsInterventionsModule.interventions",
        "each intervention with its drug class, axes and modality",
    ),
    (
        "studies[].interventions[].entry",
        "value(object: " + AS_HELD + ")",
        STATED,
        f"{P}.armsInterventionsModule.interventions[i]",
        "the intervention as the record holds it",
    ),
    (
        "studies[].interventions[].drug_class",
        "value(object: " + ", ".join(CLASS_KEYS) + ")",
        RESOLVED,
        "classes.drug_class (NLM RxClass), else banks.stated_targets",
        "an experimental drug's FDA established pharmacologic class, or the class its own entry states",
    ),
    (
        "studies[].interventions[].axes",
        "value(object: " + ", ".join(AXES_KEYS) + ")",
        RESOLVED,
        "classes.drug_axes through reading.drug_axes_view",
        "an experimental drug's RxNorm identity, ATC and structure classes and its own entry's targets",
    ),
    (
        "studies[].interventions[].modality",
        "list of value(object: " + ", ".join(MODALITY_KEYS) + ")",
        MODALITY,
        "modality.entry_properties",
        "each modality facet or cell property its entry states (known) or a name stem hints (interpolated)",
    ),
    (
        "studies[].publications",
        "list of value(object: " + ", ".join(PUBLICATION_KEYS) + ")",
        KNOWN,
        f"{P}.referencesModule.references",
        "each reference with its registry type, that type's role in the registry's terms and PubMed link",
    ),
    (
        "studies[].documents",
        "list of value(object: " + ", ".join(DOCUMENT_KEYS) + ")",
        KNOWN,
        "documentSection.largeDocumentModule.largeDocs",
        "each posted document with its link",
    ),
    ("cohort", "section", (), "profile.py", "the cohort profile, as design.xlsx's sheets compute it"),
    ("cohort.thresholds", "object", (), "profile.py", "the standard share and the signal supports"),
    (
        "cohort.frequency",
        ROWS + ", ".join(FREQUENCY_COLUMNS),
        (),
        "profile.frequency_rows",
        "each element's statement rate and full-criteria interval with its silences, over all trials and by "
        "known setting",
    ),
    (
        "cohort.mechanism_signals",
        ROWS + ", ".join(MECHANISM_COLUMNS),
        (),
        "profile.mechanism_rows",
        "statement-rate comparisons by experimental class, bounded against abbreviated silences; proposals",
    ),
    (
        "cohort.occupancy",
        ROWS + ", ".join(OCCUPANCY_COLUMNS),
        (),
        "profile.occupancy_rows",
        "each setting and class cell",
    ),
    (
        "cohort.near_misses",
        ROWS + ", ".join(NEAR_MISS_COLUMNS),
        (),
        "nearmiss.near_misses",
        "pairs whose representation is known and equal and that differ in one predicate",
    ),
    (
        "cohort.aligned_near_misses",
        ROWS + ", ".join(ALIGNED_COLUMNS),
        (),
        "nearmiss.near_misses over reading.aligned_near_miss_input",
        "pairs aligned by ATC class, each with its basis",
    ),
    (
        "cohort.endpoints",
        ROWS + ", ".join(ENDPOINT_COLUMNS),
        (),
        "landscape.endpoint_profile over the planned outcomes",
        "each outcome type and endpoint class: the trials and outcomes naming it and their time points",
    ),
    (
        "cohort.structure_relations",
        ROWS + ", ".join(STRUCTURE_COLUMNS),
        (),
        "reading.structure_relations",
        "distinct drugs sharing a known structure class",
    ),
    (
        "review_queue",
        ROWS + ", ".join(REVIEW_COLUMNS),
        (),
        "review.flags_for",
        "what the rules cannot cleanly resolve, as closed questions for an expert or a model; never answered",
    ),
    ("coverage", "section", (), "typematrix.py", "the supported-type matrix"),
    ("coverage.universe", "object", (), "typematrix.UNIVERSE", "v1's declared universe"),
    (
        "coverage.types",
        ROWS + ", ".join(("axis", "value", "status", "reason", "evidence")),
        (),
        "typematrix.declared_manifest",
        "every declared value of every axis: supported, unsupported (with its reason) or unmeasured",
    ),
    (
        "coverage.studies",
        ROWS + ", ".join(UNIVERSE_COLUMNS),
        (),
        "typematrix.universe_status and study_coordinates",
        "each study's type coordinates and whether it is in v1's universe, or why not",
    ),
    ("statuses", "object", (), "landscape.STATUSES", "what each status a value can carry means"),
    ("envelope", "object", (), "landscape.ENVELOPE_MEANINGS", "what each key of a value's envelope means"),
    (
        "fields",
        "object",
        (),
        "landscape.FIELDS",
        "this description of every field by its path (list items as []): its meaning; its type (value(T): an "
        "envelope whose value is a T; section: an object of described fields; object: k1, ...: an object "
        "with exactly those keys, in order; list of row: c1, ...: objects with exactly those columns; "
        "opaque: carried as given); the statuses its values may carry; and its source",
    ),
)
FIELDS: dict[str, dict[str, Any]] = {
    path: {"meaning": meaning, "type": kind, "statuses": list(statuses), "source": source}
    for path, kind, statuses, source, meaning in FIELD_TABLE
}
SECTIONS = tuple(path for path in FIELDS if "." not in path)
# Each section's described keys, keyed by its prefix: "" the record, "studies[]" a study, "manifest" itself.
CHILDREN: dict[str, tuple[str, ...]] = {
    parent: tuple(path.rpartition(".")[2] for path in FIELDS if path.rpartition(".")[0] == parent)
    for parent in dict.fromkeys(path.rpartition(".")[0] for path in FIELDS)
}
# The levels schema_problems walks: a node of a field path is reached at one level a segment and one more a
# list, and a list field's items one level further.
WALK_DEPTH = 2 + max(len(path.split(".")) + path.count("[]") for path in FIELDS)
# The fields that hold posted results: every value in them must come from the results section.
POSTED_FIELDS = ("studies[].efficacy.measurements", "studies[].safety.groups", "studies[].safety.events")


# ── the envelope and the decisions on one value ───────────────────────────────────────────────────────


def envelope(value: Any, status: str, source: str, rule: str, note: str, link: str) -> dict[str, Any]:
    """One value as the record shows it: the value, its status, its source, its rule, a note and its link."""
    return {"value": value, "status": status, "source": source, "rule": rule, "note": note, "link": link}


def stated(study: dict[str, Any], path: tuple[str | int, ...], link: str) -> dict[str, Any]:
    """A field of a study record as the record holds it, with its status (pure — pinned).

    known      — the record holds a value at `path` (an empty list among them): that value, exactly as held.
    not_stated — it holds none: value None, the note the ledger's absence state (not_reported, not_applicable
                 to this study type, or redacted for a withheld study), never read as zero, none or no.
    The source is the value's location in the record; the rule is "" (read as stated).
    """
    held = get(study, *path)
    if held is None:
        return envelope(None, "not_stated", location(path), "", field_state(study, *path), link)
    return envelope(held, "known", location(path), "", "", link)


def coordinate_values(row: dict[str, Any], source: str, link: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """One design coordinate as the reading resolved it, under approved relations and with proposed ones added
    (pure — pinned).

    `row` is coherence.resolve's for the coordinate. The approved value is its domain, as a list:
      known      — one value remains (resolved);
      unresolved — several remain (unnarrowed or unresolved), or none (a conflict); the note names the state
                   and every removal's cause.
    The value with proposed relations is the domain they leave, its note the proposed state and causes:
      the approved value's status — no proposed relation narrows it (noted so);
      proposed                    — they narrow it to one or more values;
      unresolved                  — they narrow it to none (a conflict), as a conflict is under approved ones.
    A proposed narrowing is never known.
    """
    domain, narrower = list(row["domain"]), list(row["with_proposed"])
    causes = [f"{'|'.join(removed)} removed by {cause}" for _, removed, cause in row["causes"]]
    status = "known" if row["state"] == "resolved" else "unresolved"
    approved = envelope(
        domain,
        status,
        source,
        "coherence.resolve under approved relations",
        "; ".join([row["state"], *causes]),
        link,
    )
    rule = "coherence.resolve with proposed relations added"
    if narrower == domain:
        return approved, envelope(narrower, status, source, rule, "no proposed relation narrows it", link)
    proposed = [f"{'|'.join(removed)} removed by {cause}" for _, removed, cause in row["proposed_causes"]]
    note = "; ".join([row["proposed_state"], *proposed])
    return approved, envelope(narrower, "proposed" if narrower else "unresolved", source, rule, note, link)


def results_value(state: str, link: str) -> dict[str, Any]:
    """Whether a study's results are posted, from ledger.results_state's code (pure — pinned).

    posted            — "results posted", known;
    not_posted        — "no results posted", not_posted: nothing posted is reported, and a registered outcome
                        is never put in its place;
    flag_not_reported — the words for it, not_stated (the registry's flag is absent), the code as its note;
    any other code    — its words (the flag and the results section disagree), unresolved, the code its note.
    """
    rule = "ledger.results_state"
    if state == "posted":
        return envelope(RESULTS_TEXT[state], "known", "hasResults", rule, "", link)
    if state == "not_posted":
        return envelope(NO_RESULTS, "not_posted", "hasResults", rule, "", link)
    status = "not_stated" if state == "flag_not_reported" else "unresolved"
    return envelope(RESULTS_TEXT[state], status, "hasResults", rule, state, link)


def standard_values(elements: list[str], tiers: dict[str, tuple], link: str) -> list[dict[str, Any]]:
    """A criterion's elements with their standard tier across the cohort (pure — pinned).

    `elements` are the criterion's element keys (profile.element_key of each atom, in atom order; each counted
    once); `tiers` maps an element to (statement rate, lower bound, upper bound, tier) from the cohort's
    frequency rows over all trials. Each element's value: known when its tier is met or not_met, unresolved
    when it is unresolved (the interval straddles the standard share) or the element is not in the profile. A
    criterion no bank typed has no element: one unresolved value, None, saying so; never not_met.
    """
    rule = "profile.frequency_rows (all trials), keyed by profile.element_key"
    if not elements:
        return [envelope(None, "unresolved", ELIGIBILITY_TEXT, rule, UNTYPED, link)]
    values = []
    for element in dict.fromkeys(elements):
        found = tiers.get(element)
        if found is None:
            unprofiled = {"element": element, "tier": None, "statement_rate": None, "lower_bound": None}
            unprofiled["upper_bound"] = None
            values.append(envelope(unprofiled, "unresolved", ELIGIBILITY_TEXT, rule, "not profiled", link))
            continue
        rate, lower, upper, tier = found
        value = {
            "element": element,
            "tier": tier,
            "statement_rate": rate,
            "lower_bound": lower,
            "upper_bound": upper,
        }
        status = "known" if tier in ("met", "not_met") else "unresolved"
        values.append(
            envelope(value, status, ELIGIBILITY_TEXT, rule, "" if status == "known" else tier, link)
        )
    return values


def biomarker_values(
    criteria: list[tuple], outcomes: list[tuple], link: str
) -> dict[str, list[dict[str, Any]]]:
    """A study's biomarkers by role, as the banks and the outcomes give them (pure — pinned).

    `criteria` are the reading's (piece, section, text, atoms); `outcomes` its (type, measure, time frame,
    endpoint classes, time points), primary then secondary then other, each in record order.
      eligibility — each biomarker atom a criterion states: the biomarker, the states it allows, its params,
                    its span, its piece and its effective section (reading.effective_section: a permission is
                    "permitted", a negated mention the other section);
      outcome     — each primary or secondary outcome whose measure names a biomarker endpoint;
      exploratory — each other pre-specified outcome whose measure names one.
    Every value known, with the field it was read from and the bank that read it.
    """
    roles: dict[str, list[dict[str, Any]]] = {"eligibility": [], "outcome": [], "exploratory": []}
    for piece, section, text, atoms in criteria:
        for _bank, concept, values, params, start, end in atoms:
            if not concept.startswith("biomarker:"):
                continue
            value = {
                "biomarker": concept.removeprefix("biomarker:"),
                "states": list(values),
                "params": dict(params),
                "span": text[start:end],
                "piece": piece,
                "section": effective_section(section, params),
            }
            roles["eligibility"].append(
                envelope(value, "known", ELIGIBILITY_TEXT, "banks.biomarker_status", f"piece {piece}", link)
            )
    keys = dict(OUTCOME_KINDS)
    seen = {kind: 0 for kind in keys}
    for kind, measure, frame, classes, points in outcomes:
        index = seen[kind]
        seen[kind] = index + 1
        if "biomarker_endpoint" not in classes:
            continue
        value = {"outcome_type": kind, "measure": measure, "time_frame": frame, "time_points": list(points)}
        source = f"{P}.outcomesModule.{keys[kind]}[{index}]"
        role = "exploratory" if kind == "other" else "outcome"
        roles[role].append(envelope(value, "known", source, "banks.endpoint_classes", "", link))
    return roles


def drug_class_value(found: tuple | None, source: str, link: str) -> dict[str, Any]:
    """An intervention's drug class as the reading found it (pure — pinned).

    `found` is the reading's (drug, state, classes, resolved by) for an experimental drug, None for any other
    intervention. classified (NLM RxClass's FDA established pharmacologic class) and stated_by_record (the
    class the intervention's own description states, which counts as known by the founder's decision of
    2026-10-31) are known; unresolved and lookup_failed are unresolved, the state as the note; an intervention
    that is not an experimental drug is unresolved, never classed.
    """
    if found is None:
        return envelope(None, "unresolved", source, "classes.experimental_drugs", NOT_EXPERIMENTAL, link)
    _drug, state, classes, resolved_by = found
    value = {"state": state, "classes": list(classes), "resolved_by": resolved_by}
    if state == "classified":
        return envelope(value, "known", source, "classes.drug_class (NLM RxClass, has_epc)", "", link)
    if state == "stated_by_record":
        return envelope(
            value, "known", source, "banks.stated_targets (the entry's own description)", "", link
        )
    return envelope(value, "unresolved", source, "classes.drug_class (NLM RxClass, has_epc)", state, link)


def axes_value(axes: dict[str, Any] | None, source: str, link: str) -> dict[str, Any]:
    """An intervention's drug axes as the reading gives them (pure — pinned).

    `axes` is the reading's drug_axes_view for an experimental drug, None for any other intervention. The
    value is the axes as the resolve JSON renders them; known when its own name's RxNorm identity is
    resolved, otherwise unresolved with the identity code and its reason as the note (not_looked_up, a
    conflict, an unresolved own name, a failed lookup); an intervention that is not an experimental drug is
    unresolved, never given axes.
    """
    rule = "classes.drug_axes through reading.drug_axes_view"
    if axes is None:
        return envelope(None, "unresolved", source, "classes.experimental_drugs", NOT_EXPERIMENTAL, link)
    if axes["identity"] == "resolved":
        return envelope(_axes(axes), "known", source, rule, "", link)
    return envelope(_axes(axes), "unresolved", source, rule, f"{axes['identity']}: {axes['reason']}", link)


def endpoint_profile(trials: list[tuple[str, list[tuple]]]) -> list[tuple]:
    """Each planned outcome type and endpoint class across the cohort, with its time points (pure — pinned).

    `trials` are (nct, the reading's outcomes: (type, measure, time frame, endpoint classes, time points)). An
    outcome counts under each class its measure names, or under "(no endpoint class)" when it names none. Rows
    (outcome type, endpoint class, trials naming it, their NCT numbers sorted, outcomes naming it, each time
    point with how many of those outcomes state it, sorted by point), ordered primary, secondary, other, then
    by descending trials, then by class.
    """
    held: dict[tuple[str, str], tuple[set[str], list[int], dict[str, int]]] = {}
    for nct, outcomes in trials:
        for kind, _measure, _frame, classes, points in outcomes:
            for klass in classes or ["(no endpoint class)"]:
                ncts, count, times = held.setdefault((kind, klass), (set(), [0], {}))
                ncts.add(nct)
                count[0] += 1
                for point in dict.fromkeys(points):
                    times[point] = times.get(point, 0) + 1
    order = [kind for kind, _ in OUTCOME_KINDS]
    # each (type, class) is one row, so the keys never tie and the rows are never compared
    keyed = sorted(
        (
            (order.index(kind), -len(ncts), klass),
            (kind, klass, len(ncts), sorted(ncts), count[0], sorted(times.items())),
        )
        for (kind, klass), (ncts, count, times) in held.items()
    )
    return [row for _, row in keyed]


# ── the per-study extract ─────────────────────────────────────────────────────────────────────────────


def criterion_sections(criteria: list[tuple], link: str) -> dict[str, list[dict[str, Any]]]:
    """A study's criteria as itemized, by section, each with the atoms the banks typed (pure — pinned).

    `criteria` are the reading's (piece, section, text, atoms). Each criterion goes to its own section
    (inclusion, exclusion or unsectioned), in order, as its piece number, its exact text and its atoms; each
    atom with its bank, concept, values, params, the span it rests on, its effective section
    (reading.effective_section) and its element key (profile.element_key), every value known.
    """
    sections: dict[str, list[dict[str, Any]]] = {"inclusion": [], "exclusion": [], "unsectioned": []}
    for piece, section, text, atoms in criteria:
        typed = []
        for bank, concept, values, params, start, end in atoms:
            effective = effective_section(section, params)
            value = {
                "bank": bank,
                "concept": concept,
                "values": list(values),
                "params": dict(params),
                "span": text[start:end],
                "section": effective,
                "element": element_key(effective, concept, values, params),
            }
            typed.append(envelope(value, "known", ELIGIBILITY_TEXT, f"banks.{bank}", f"piece {piece}", link))
        sections[section].append(
            {
                "piece": piece,
                "text": envelope(text, "known", ELIGIBILITY_TEXT, "criteria.itemize", f"piece {piece}", link),
                "atoms": typed,
            }
        )
    return sections


def outcome_sections(
    study: dict[str, Any], outcomes: list[tuple], link: str
) -> dict[str, list[dict[str, Any]]]:
    """A study's registered outcomes, primary, secondary and other apart: planned, never posted results
    (pure — pinned).

    `outcomes` are the reading's (type, measure, time frame, endpoint classes, time points), each type's in
    record order, so the i-th of a type is the record's i-th outcome of that section. Each outcome: its
    measure, time frame and description as the record states them, and the endpoint classes and time points
    the banks read from them (known; an empty list when they name none).
    """
    sections: dict[str, list[dict[str, Any]]] = {}
    for kind, key in OUTCOME_KINDS:
        planned = [outcome for outcome in outcomes if outcome[0] == kind]
        entries = []
        for index, (_kind, _measure, _frame, classes, points) in enumerate(planned):
            base = (P, "outcomesModule", key, index)
            entries.append(
                {
                    "measure": stated(study, (*base, "measure"), link),
                    "time_frame": stated(study, (*base, "timeFrame"), link),
                    "description": stated(study, (*base, "description"), link),
                    "endpoint_classes": envelope(
                        list(classes),
                        "known",
                        location((*base, "measure")),
                        "banks.endpoint_classes",
                        "",
                        link,
                    ),
                    "time_points": envelope(
                        list(points), "known", location((*base, "timeFrame")), "banks.time_points", "", link
                    ),
                }
            )
        sections[kind] = entries
    return sections


def posted_measurements(study: dict[str, Any], results: list[tuple], link: str) -> list[dict[str, Any]]:
    """Each posted outcome measurement per arm, from the results section only (pure — pinned).

    The record's outcome measures are walked in the reading's own order (measure, class, category,
    measurement), so each measurement pairs with the reading's result row (`results`), whose endpoint classes
    it takes; a different count raises ValueError rather than mislabel one. Each value: the measure's type,
    title, time frame, unit, parameter and dispersion types, the arm (its group's title, None when the groups
    do not name it), the group id, class and category titles, the value, spread and limits as stated, and
    the endpoint classes; known, its source the measurement's place in the results section.
    """
    walked = []
    for m, measure in enumerate(as_list(get(study, R, "outcomeMeasuresModule", "outcomeMeasures"))):
        groups = {get(group, "id"): get(group, "title") for group in as_list(get(measure, "groups"))}
        for c, klass in enumerate(as_list(get(measure, "classes"))):
            for k, category in enumerate(as_list(get(klass, "categories"))):
                for x, measurement in enumerate(as_list(get(category, "measurements"))):
                    path = (R, "outcomeMeasuresModule", "outcomeMeasures", m, "classes", c, "categories", k)
                    value = {
                        "outcome_type": get(measure, "type"),
                        "measure": get(measure, "title"),
                        "time_frame": get(measure, "timeFrame"),
                        "unit": get(measure, "unitOfMeasure"),
                        "param_type": get(measure, "paramType"),
                        "dispersion_type": get(measure, "dispersionType"),
                        "arm": groups.get(get(measurement, "groupId")),
                        "group_id": get(measurement, "groupId"),
                        "class": get(klass, "title"),
                        "category": get(category, "title"),
                        "value": get(measurement, "value"),
                        "spread": get(measurement, "spread"),
                        "lower_limit": get(measurement, "lowerLimit"),
                        "upper_limit": get(measurement, "upperLimit"),
                    }
                    walked.append((value, location((*path, "measurements", x))))
    return [
        envelope(
            {**value, "endpoint_classes": list(row[1])},
            "known",
            source,
            "landscape.posted_measurements",
            "",
            link,
        )
        for (value, source), row in zip(walked, results, strict=True)
    ]


def posted_events(study: dict[str, Any], link: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Each arm's posted adverse-event totals and each event per arm, from the results section only
    (pure — pinned).

    Groups: each event group's id, title, and deaths, serious and other events affected and at risk, as
    stated. Events: each serious then other event's statistics per group: the table, term, organ system,
    vocabulary, assessment type, group id, the arm (its group's title, None when the groups do not name it),
    affected, at risk and events as stated (None where the record holds none; an event's blank at-risk count
    is never filled from its group's total). Every value known, its source its place in the results section.
    """
    module = (R, "adverseEventsModule")
    rule = "landscape.posted_events"
    titles = {get(g, "id"): get(g, "title") for g in as_list(get(study, *module, "eventGroups"))}
    groups = [
        envelope(
            {
                "group_id": get(group, "id"),
                "title": get(group, "title"),
                **{
                    f"{prefix}_{kind}": get(group, f"{prefix}Num{field}")
                    for prefix in ("deaths", "serious", "other")
                    for kind, field in (("affected", "Affected"), ("at_risk", "AtRisk"))
                },
            },
            "known",
            location((*module, "eventGroups", g)),
            rule,
            "",
            link,
        )
        for g, group in enumerate(as_list(get(study, *module, "eventGroups")))
    ]
    events = [
        envelope(
            {
                "table": table,
                "term": get(event, "term"),
                "organ_system": get(event, "organSystem"),
                "source_vocabulary": get(event, "sourceVocabulary"),
                "assessment_type": get(event, "assessmentType"),
                "group_id": get(stats, "groupId"),
                "arm": titles.get(get(stats, "groupId")),
                "affected": get(stats, "numAffected"),
                "at_risk": get(stats, "numAtRisk"),
                "events": get(stats, "numEvents"),
            },
            "known",
            location((*module, key, e, "stats", s)),
            rule,
            "",
            link,
        )
        for table, key in EVENT_TABLES
        for e, event in enumerate(as_list(get(study, *module, key)))
        for s, stats in enumerate(as_list(get(event, "stats")))
    ]
    return groups, events


def intervention_sections(study: dict[str, Any], view: dict[str, Any], link: str) -> list[dict[str, Any]]:
    """Each intervention entry with its drug class, axes and modality as the reading gives them
    (pure — pinned).

    The entry as the record holds it; its drug class (drug_class_value) and axes (axes_value) when it is an
    experimental drug of the reading (matched by its own name), else unresolved, never classed; and every
    modality or cell extraction the reading read from that entry (its name, other names or description),
    each with the extraction's own status (known, or interpolated from a name stem), location and rule.
    """
    drugs = {found[0]: found for found in view["drugs"]}
    axes = {held["drug"]: held for held in view["drug_axes"]}
    entries = []
    for index, item in enumerate(as_list(get(study, P, "armsInterventionsModule", "interventions"))):
        base = (P, "armsInterventionsModule", "interventions", index)
        source = location(base)
        name = get(item, "name")
        name = name if isinstance(name, str) else None
        modality = [
            envelope(
                {"property": e[1], "value": e[2], "polarity": e[3], "scope": e[4], "warrant": e[8]},
                e[7],
                e[5],
                e[6],
                "",
                link,
            )
            for e in view["properties"]
            if e[5].startswith(f"{source}.")
        ]
        entries.append(
            {
                "entry": stated(study, base, link),
                "drug_class": drug_class_value(drugs.get(name), source, link),
                "axes": axes_value(axes.get(name), source, link),
                "modality": modality,
            }
        )
    return entries


def reference_values(study: dict[str, Any], nct: str, link: str) -> tuple[list, list]:
    """A study's publications with their registry type and its role, and its posted documents with their
    links (pure — pinned).

    Publications: each reference's PMID, type, the type's role in the registry's terms (links.reference_role:
    a DERIVED reference is never called a results publication), citation and PubMed link ("" for no PMID).
    Documents: each posted document's type, label, protocol, SAP and consent flags, dates, file name and the
    registry's copy (links.document_link: "" when it cannot be linked). Every value known.
    """
    references = []
    for index, ref in enumerate(as_list(get(study, P, "referencesModule", "references"))):
        value = {
            "pmid": get(ref, "pmid"),
            "type": get(ref, "type"),
            "role": reference_role(get(ref, "type")),
            "citation": get(ref, "citation"),
            "pubmed": pubmed_link(get(ref, "pmid"))[1],
        }
        source = location((P, "referencesModule", "references", index))
        references.append(envelope(value, "known", source, "links.reference_role", "", link))
    documents = []
    for index, doc in enumerate(as_list(get(study, "documentSection", "largeDocumentModule", "largeDocs"))):
        value = {
            "type": get(doc, "typeAbbrev"),
            "label": get(doc, "label"),
            "has_protocol": get(doc, "hasProtocol"),
            "has_sap": get(doc, "hasSap"),
            "has_icf": get(doc, "hasIcf"),
            "date": get(doc, "date"),
            "upload_date": get(doc, "uploadDate"),
            "filename": get(doc, "filename"),
            "url": document_link(nct, get(doc, "filename"))[1],
        }
        source = location(("documentSection", "largeDocumentModule", "largeDocs", index))
        documents.append(envelope(value, "known", source, "links.document_link", "", link))
    return references, documents


def study_extract(study: dict[str, Any], view: dict[str, Any], tiers: dict[str, tuple]) -> dict[str, Any]:
    """One study's ten-point extract and its extras, from its record and the reading's view of it
    (pure — pinned).

    `view` is reading.study_view's for `study`; `tiers` the cohort's standard tiers (standard_values). The ten
    points: population; inclusion, exclusion (and unsectioned) criteria as itemized with their atoms; line of
    therapy and setting as the design coordinates; planned outcomes; biomarkers by role; efficacy (posted
    measurements, or "no results posted"); safety (posted adverse events, or "no results posted");
    exploratory measures (the other pre-specified outcomes); standard protocol language (each criterion's
    elements and tiers). The extras: sponsor, phases, status, type, conditions, dates, enrollment, arms,
    interventions with their classes, axes and modality, publications and documents. Every value an envelope
    with its status, source and the study's registry link.
    """
    nct = view["nct"]
    link = study_link(nct)[1]
    eligibility = (P, "eligibilityModule")
    coverage = view["coverage"]
    outcomes = outcome_sections(study, view["outcomes"], link)
    state = results_state(study.get("hasResults"), isinstance(study.get(R), dict))
    groups, events = posted_events(study, link)
    references, documents = reference_values(study, nct, link)
    coordinates = {}
    for name in ("setting", "prior_advanced_lines"):
        approved, proposed = coordinate_values(view["coordinates"][name], ELIGIBILITY_TEXT, link)
        coordinates[name] = approved
        coordinates[f"{name}_with_proposed_relations"] = proposed
    standard = []
    for piece, section, _text, atoms in view["criteria"]:
        elements = [element_key(effective_section(section, a[3]), a[1], a[2], a[3]) for a in atoms]
        standard.append(
            {"piece": piece, "section": section, "elements": standard_values(elements, tiers, link)}
        )
    return {
        "nct": stated(study, (P, "identificationModule", "nctId"), link),
        "digest": view["digest"],
        "link": link,
        "population": {
            name: stated(study, (*eligibility, key), link)
            for name, key in (
                ("minimum_age", "minimumAge"),
                ("maximum_age", "maximumAge"),
                ("std_ages", "stdAges"),
                ("sex", "sex"),
                ("gender_based", "genderBased"),
                ("gender_description", "genderDescription"),
                ("healthy_volunteers", "healthyVolunteers"),
            )
        },
        "eligibility": {
            "text": stated(study, (*eligibility, "eligibilityCriteria"), link),
            "itemized": envelope(view["itemize"], "known", ELIGIBILITY_TEXT, "criteria.itemize", "", link),
            "coverage": envelope(
                {
                    "content": coverage["content"],
                    "sectioning": coverage["sectioning"],
                    **dict(coverage["evidence"]),
                    "markers": [
                        {"kind": k, "scope": sc, "piece": p, "start": s, "end": e, "text": t}
                        for k, sc, p, s, e, t in coverage["markers"]
                    ],
                },
                "known",
                ELIGIBILITY_TEXT,
                "criteria.eligibility_coverage",
                "",
                link,
            ),
        },
        **criterion_sections(view["criteria"], link),
        "line_of_therapy_and_setting": coordinates,
        "outcomes": outcomes,
        "biomarkers": biomarker_values(view["criteria"], view["outcomes"], link),
        "efficacy": {
            "results": results_value(state, link),
            "measurements": posted_measurements(study, view["results"], link),
        },
        "safety": {
            "results": results_value(state, link),
            "time_frame": stated(study, (R, "adverseEventsModule", "timeFrame"), link),
            "groups": groups,
            "events": events,
        },
        "exploratory_measures": outcomes["other"],
        "standard_language": standard,
        "sponsor": stated(study, (P, "sponsorCollaboratorsModule", "leadSponsor", "name"), link),
        "phases": stated(study, (P, "designModule", "phases"), link),
        "overall_status": stated(study, (P, "statusModule", "overallStatus"), link),
        "study_type": stated(study, (P, "designModule", "studyType"), link),
        "conditions": stated(study, (P, "conditionsModule", "conditions"), link),
        "start_date": stated(study, (P, "statusModule", "startDateStruct"), link),
        "primary_completion_date": stated(study, (P, "statusModule", "primaryCompletionDateStruct"), link),
        "completion_date": stated(study, (P, "statusModule", "completionDateStruct"), link),
        "enrollment": stated(study, (P, "designModule", "enrollmentInfo"), link),
        "arms": [
            stated(study, (P, "armsInterventionsModule", "armGroups", index), link)
            for index, _ in enumerate(as_list(get(study, P, "armsInterventionsModule", "armGroups")))
        ],
        "interventions": intervention_sections(study, view, link),
        "publications": references,
        "documents": documents,
    }


# ── the cohort, the record and its manifest ───────────────────────────────────────────────────────────


def cohort_section(reading: dict[str, Any]) -> dict[str, Any]:
    """The cohort profile as design.xlsx's sheets compute it, as named rows (pure — pinned).

    The frequency and mechanism rows over every trial ("all trials") then by known setting, from the same
    trials as design.xlsx's Profile and Mechanism Signals sheets (design._profile_trials); the occupancy of
    every setting and observed class cell, as its Occupancy sheet computes it; the near-miss pairs as written
    and aligned; the planned endpoints and time points by class (endpoint_profile); the structure relations;
    and the thresholds the tiers and signals were read at. Comparable posted results wait on the endpoint
    bank (add-coherence-engine 5.3) and are not here.
    """
    views = reading["views"]
    frequency, mechanism = [], []
    for by_setting in (False, True):
        trials = _profile_trials(views, by_setting)
        frequency += frequency_rows(trials)
        mechanism += mechanism_rows(trials)
    occupancy_trials = [
        (
            v["nct"],
            v["coordinates"]["setting"]["domain"],
            tuple(sorted({c for _, s, e, _ in v["drugs"] if s == "classified" for c in e}))
            if v["drugs"] and all(s == "classified" for _, s, _, _ in v["drugs"])
            else (),
        )
        for v in views
    ]
    observed = sorted({c for _, _, classes in occupancy_trials for c in classes})
    cells = [(setting, klass) for setting in SETTINGS for klass in observed]
    endpoints = endpoint_profile([(v["nct"], v["outcomes"]) for v in views])
    return {
        "thresholds": {
            "standard_share": STANDARD_SHARE,
            "signal_min_trials": SIGNAL_MIN_TRIALS,
            "signal_min_sponsors": SIGNAL_MIN_SPONSORS,
        },
        "frequency": [dict(zip(FREQUENCY_COLUMNS, row, strict=True)) for row in frequency],
        "mechanism_signals": [dict(zip(MECHANISM_COLUMNS, row, strict=True)) for row in mechanism],
        "occupancy": [
            dict(zip(OCCUPANCY_COLUMNS, row, strict=True)) for row in occupancy_rows(cells, occupancy_trials)
        ],
        "near_misses": [dict(zip(NEAR_MISS_COLUMNS, pair, strict=True)) for pair in reading["pairs"]],
        "aligned_near_misses": [
            dict(zip(ALIGNED_COLUMNS, pair, strict=True)) for pair in reading["aligned_pairs"]
        ],
        "endpoints": [
            dict(zip(ENDPOINT_COLUMNS, (*row[:5], dict(row[5])), strict=True)) for row in endpoints
        ],
        "structure_relations": [
            dict(zip(STRUCTURE_COLUMNS, row, strict=True)) for row in reading["structure_relations"]
        ],
    }


def landscape_manifest(
    studies: list[dict[str, Any]],
    api_version: str,
    data_timestamp: str,
    code_commit: str,
    retrieval: dict[str, Any],
    rule_versions: dict[str, Any],
) -> dict[str, Any]:
    """The manifest of a record: what it was read from and by (pure — pinned).

    The API version and data timestamp of the registry snapshot read, each study's digest in order and their
    Merkle root (as `trialledger resolve` names them), the code commit, the rule versions (the command passes
    RULE_VERSIONS: the schema, the tool, the design rules, the derivation code root and every relation's
    approval; a copy, so the record never shares them) and the retrieval coverage as the pull gives it
    (`retrieval`, carried as given).
    """
    digests = [warrants.study_digest(study) for study in studies]
    return {
        "api_version": api_version,
        "data_timestamp": data_timestamp,
        "study_digests": digests,
        "merkle_root": warrants.merkle_root(digests),
        "code_commit": code_commit,
        "rule_versions": copy.deepcopy(rule_versions),
        "retrieval": retrieval,
    }


def landscape_record(
    reading: dict[str, Any],
    studies: list[dict[str, Any]],
    request: Any,
    scope: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """landscape.json: the record of truth for one run, schema v1 (pure — pinned).

    `reading` is reading.read_population's over `studies`, in the same order: a reading whose views' digests
    are not the studies' digests, in order (other studies, another order, another count), raises ValueError
    and pairs nothing. `request` and `scope` are carried as given (request resolution's); `manifest` is
    landscape_manifest's. The record: the schema version, the request, the scope, the manifest, each study's
    extract (study_extract, its standard tiers those of the cohort's frequency rows over all trials), the
    cohort (cohort_section), the review queue (every review flag of every study, its answer None: nothing in
    it is answered here), coverage (v1's universe, every declared type's status, and each study's type
    coordinates and universe status at the manifest's data timestamp, open-ended when it names none), and
    the record's self-description: `statuses` (what each status means), `envelope` (what each key of a
    value means) and `fields` (every field's meaning, type, statuses and source).
    """
    views = reading["views"]
    if [view["digest"] for view in views] != [warrants.study_digest(study) for study in studies]:
        raise ValueError("the reading is not of these studies, in this order")
    cohort = cohort_section(reading)
    tiers = {
        row["element"]: (row["statement_rate"], row["lower_bound"], row["upper_bound"], row["standard_tier"])
        for row in cohort["frequency"]
        if row["stratum"] == ALL_TRIALS
    }
    present = manifest.get("data_timestamp")
    present = present if isinstance(present, str) and present else None
    paired = list(zip(studies, views, strict=True))
    return {
        "schema_version": SCHEMA_VERSION,
        "request": request,
        "scope": scope,
        "manifest": manifest,
        "studies": [study_extract(study, view, tiers) for study, view in paired],
        "cohort": cohort,
        "review_queue": [
            dict(zip(REVIEW_COLUMNS, (view["nct"], k, el, why, int(pr), ev, q, opts, None), strict=True))
            for view, flags in zip(views, reading["flags"], strict=True)
            for k, el, why, pr, ev, q, opts in flags
        ],
        "coverage": {
            "universe": copy.deepcopy(UNIVERSE),
            "types": declared_manifest()["rows"],
            "studies": [
                dict(
                    zip(
                        UNIVERSE_COLUMNS,
                        (view["nct"], universe_status(study, present), study_coordinates(study)),
                        strict=True,
                    )
                )
                for study, view in paired
            ],
        },
        "statuses": dict(STATUSES),
        "envelope": dict(ENVELOPE_MEANINGS),
        "fields": copy.deepcopy(FIELDS),
    }


# ── the validator ─────────────────────────────────────────────────────────────────────────────────────


def type_holds(kind: str, value: Any) -> bool:
    """Whether a value is of a field's described type (pure — pinned).

      opaque                  — anything: carried as given;
      string, boolean, object — a str, a bool, a dict;
      integer                 — an int that is not a bool;
      list of string          — a list of str;
      object: <AS_HELD>       — a dict, shown as the record holds it;
      object: k1, k2, ...     — a dict holding exactly those keys, in that order;
      row: c1, c2, ...        — a table's row: likewise, exactly those columns, in that order;
      list of row: c1, ...    — a list of such rows.
    Any other kind (a section, a value envelope, a list of either: the walk checks those) holds nothing.
    """
    if kind == "opaque":
        return True
    if kind in ("string", "boolean", "object"):
        return isinstance(value, {"string": str, "boolean": bool, "object": dict}[kind])
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "list of string":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if kind == f"object: {AS_HELD}":
        return isinstance(value, dict)
    if kind.startswith(("object: ", "row: ")):
        return isinstance(value, dict) and list(value) == kind.partition(": ")[2].split(", ")
    if kind.startswith("list of row: "):
        row = kind.removeprefix("list of ")
        return isinstance(value, list) and all(type_holds(row, item) for item in value)
    return False


def envelope_problems(node: Any, field: str, where: str, link: str) -> list[tuple[str, str]]:
    """Every way one value departs from its field's envelope, by code (pure — pinned).

    `node` is the value at `where`, `field` its described path (in FIELDS, as a value(T) or a list of them),
    `link` its study's own registry page (links.study_link of the study's NCT number):
      malformed_value         — not an envelope (exactly value, status, source, rule, note, link, in order):
                                nothing else is read;
      unknown_status          — a status outside STATUSES;
      status_not_allowed      — a status its field does not admit (a posted measurement is never not_posted);
      wrong_value_type        — a value not of the field's T (type_holds), or null with a status other than
                                not_stated or unresolved;
      no_source               — neither a source nor a rule;
      no_link                 — no link; wrong_link: a link that is not the study's own;
      posted_not_from_results — a posted measurement or event whose source is not in the results section.
    """
    if not isinstance(node, dict) or tuple(node) != ENVELOPE:
        return [("malformed_value", where)]
    found = []
    status, value = node["status"], node["value"]
    if not isinstance(status, str) or status not in STATUSES:
        found.append(("unknown_status", where))
    elif status not in FIELDS[field]["statuses"]:
        found.append(("status_not_allowed", where))
    inner = FIELDS[field]["type"].removeprefix("list of ").removeprefix("value(").removesuffix(")")
    if (value is None and status not in ("not_stated", "unresolved")) or not (
        value is None or type_holds(inner, value)
    ):
        found.append(("wrong_value_type", where))
    if not node["source"] and not node["rule"]:
        found.append(("no_source", where))
    if not node["link"]:
        found.append(("no_link", where))
    elif node["link"] != link:
        found.append(("wrong_link", where))
    if field in POSTED_FIELDS and not str(node["source"]).startswith(f"{R}."):
        found.append(("posted_not_from_results", where))
    return found


def results_problems(study: dict[str, Any], where: str) -> list[tuple[str, str]]:
    """Whether a study's efficacy and safety say the same of its results, and post nothing when it has no
    results section (pure — pinned).

    `study` is one study section of a record, `where` its path ("studies[i]"); only the shapes the walk admits
    are read (anything else the walk names):
      results_differ         — efficacy.results is not safety.results;
      results_inconsistent   — efficacy.results is not what results_value gives for the state its
                               status names (known: posted; not_posted: not_posted; any other: the state
                               in its note);
      posted_without_results — a posted list (efficacy.measurements, safety.groups or safety.events) holding
                               anything while the state is not_posted or flag_without_results (no results
                               section).
    """
    efficacy, safety = study.get("efficacy"), study.get("safety")
    if not (isinstance(efficacy, dict) and isinstance(safety, dict)):
        return []
    found = []
    held = efficacy.get("results")
    if held != safety.get("results"):
        found.append(("results_differ", f"{where}.safety.results"))
    if not (isinstance(held, dict) and tuple(held) == ENVELOPE):
        return found
    status = held["status"]
    state = "posted" if status == "known" else "not_posted" if status == "not_posted" else held["note"]
    if not isinstance(state, str) or state not in RESULTS_TEXT or held != results_value(state, held["link"]):
        found.append(("results_inconsistent", f"{where}.efficacy.results"))
        return found
    if state in ("not_posted", "flag_without_results"):
        posted = (
            (efficacy, "efficacy", "measurements"),
            (safety, "safety", "groups"),
            (safety, "safety", "events"),
        )
        found += [
            ("posted_without_results", f"{where}.{name}.{key}")
            for section, name, key in posted
            if section.get(key)
        ]
    return found


def study_mismatches(record: dict[str, Any]) -> list[tuple[str, str]]:
    """Whether the sections that name studies name the record's studies (pure — pinned).

    The studies' NCT numbers are their `nct` values, in order (None where a study holds none):
      study_mismatch at coverage.studies — its rows' NCT numbers are not the studies', in order;
      study_mismatch at review_queue[i]  — a review question of a study the record does not hold.
    A section not of its type is the walk's to name, so it is not read here.
    """
    studies = record.get("studies")
    if not isinstance(studies, list):
        return []
    held = [study.get("nct") if isinstance(study, dict) else None for study in studies]
    ncts = [nct.get("value") if isinstance(nct, dict) else None for nct in held]
    found = []
    coverage = record.get("coverage")
    rows = coverage.get("studies") if isinstance(coverage, dict) else None
    if isinstance(rows, list) and [row.get("nct") if isinstance(row, dict) else None for row in rows] != ncts:
        found.append(("study_mismatch", "coverage.studies"))
    queue = record.get("review_queue")
    for index, row in enumerate(queue if isinstance(queue, list) else []):
        if isinstance(row, dict) and row.get("nct") not in ncts:
            found.append(("study_mismatch", f"review_queue[{index}]"))
    return found


def schema_problems(record: Any) -> tuple[tuple[str, str], ...]:
    """Every way a record departs from schema v1 that the record itself shows, each by its code and where
    (pure — pinned).

    Walked from the root level by level (breadth first; WALK_DEPTH levels reach every node a described field
    can hold, so the walk ends whatever it is given), every node against its field in FIELDS (its path with
    list positions as "[]"; each problem names the concrete path, positions as "[i]"):
      unknown_schema_version   — schema_version is not SCHEMA_VERSION;
      statuses_differ, envelope_differ, fields_differ — the record's own description is not the schema's;
      undescribed_field        — a key of a section that FIELDS does not describe;
      missing_field            — a described key of a section that the section lacks;
      wrong_type               — a section that is not an object, a list field that is not a list, or any
                                 other field not of its type (type_holds: strings, integers, objects with
                                 their keys, rows with their columns);
      wrong_link (a study's)   — a study's link that is not links.study_link of its own NCT number (null too);
      each value's problems    — envelope_problems, every value held to its study's own link;
      each study's results     — results_problems: efficacy and safety agree, and nothing is posted without a
                                 results section;
      study_mismatch           — study_mismatches: coverage and the review queue name the record's studies;
      digest_mismatch          — the manifest's study digests are not the studies' digests, in order;
      root_mismatch            — the manifest's Merkle root is not the root of its study digests.
    A record that is not an object: (("not_an_object", ""),). A record with no problem: ().
    The record is checked against the schema and against itself, never against the study records it was read
    from: a value changed alike everywhere it appears (both results states, or a study's NCT number with its
    link and every value's) passes here; re-deriving the record from the studies its manifest names finds it.
    """
    if not isinstance(record, dict):
        return (("not_an_object", ""),)
    found: list[tuple[str, str]] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        found.append(("unknown_schema_version", "schema_version"))
    for name, described in (("statuses", STATUSES), ("envelope", ENVELOPE_MEANINGS), ("fields", FIELDS)):
        if record.get(name) != described:
            found.append((f"{name}_differ", name))
    # (prefix of a section's children, the field described, the concrete path, the node, its type, the link),
    # one level of the record at a time: every node is reached by the level of its depth, so WALK_DEPTH levels
    # reach every node a described field can hold, and the walk ends whatever the record holds
    frontier: list[tuple[str, str, str, Any, str, str]] = [("", "", "", record, "section", "")]
    for _level in range(WALK_DEPTH):
        following: list[tuple[str, str, str, Any, str, str]] = []
        for prefix, field, where, node, kind, link in frontier:
            if kind == "section":
                if not isinstance(node, dict):
                    found.append(("wrong_type", where))
                    continue
                if prefix == "studies[]":
                    nct = node.get("nct")
                    link = study_link(nct.get("value") if isinstance(nct, dict) else None)[1]
                    found += results_problems(node, where)
                children = CHILDREN.get(prefix, ())
                found += [
                    ("undescribed_field", f"{where}.{key}".lstrip(".")) for key in node if key not in children
                ]
                for key in children:
                    path = f"{prefix}.{key}".lstrip(".")
                    here = f"{where}.{key}".lstrip(".")
                    if key not in node:
                        found.append(("missing_field", here))
                        continue
                    described, held = FIELDS[path]["type"], node[key]
                    walked = described in ("section", "list of section") or described.startswith(
                        ("value", "list of value")
                    )
                    if path == "studies[].link":
                        if held != link:
                            found.append(("wrong_link", here))
                    elif not walked:
                        if not type_holds(described, held):
                            found.append(("wrong_type", here))
                    elif described.startswith("list of") and not isinstance(held, list):
                        found.append(("wrong_type", here))
                    else:
                        following.append((path, path, here, held, described, link))
            elif kind.startswith("list of"):
                element = "section" if kind == "list of section" else kind.removeprefix("list of ")
                following += [
                    (f"{prefix}[]", field, f"{where}[{i}]", item, element, link)
                    for i, item in enumerate(node)
                ]
            else:
                found += envelope_problems(node, field, where, link)
        frontier = following
    found += study_mismatches(record)
    manifest, studies = record.get("manifest"), record.get("studies")
    if isinstance(manifest, dict) and isinstance(studies, list):
        digests = manifest.get("study_digests")
        if digests != [study.get("digest") if isinstance(study, dict) else None for study in studies]:
            found.append(("digest_mismatch", "manifest.study_digests"))
        if not (
            isinstance(digests, list)
            and all(isinstance(d, str) for d in digests)
            and manifest.get("merkle_root") == warrants.merkle_root(digests)
        ):
            found.append(("root_mismatch", "manifest.merkle_root"))
    return tuple(found)
