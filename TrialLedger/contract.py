"""The contract of landscape.json schema 3 and of the workbook laid out from it (refine-landscape-record 0.4).

Units A (the record), B (universes) and C (the workbook) build against this one table, on one base. It holds:

- FIELDS: every field of the record, study level and record level. Each names where it comes from (`plain`:
  its API path templates in the registry's study JSON, list elements as "[]"; `reading`: the named rule that
  reads it, with the registry paths it reads; `run`: what the run itself records, its manifest, scope and
  self-description) and who uses it: a workbook sheet and column, the assistant through the MCP `record`
  tool's part, or a layer-two reader that exists today. A rule not yet built names the tasks.md task that
  builds it.
- SHEETS: the workbook as the reviewer reads it, each sheet's row grain and ordered columns, each column
  naming the fields it shows.
- NOT_WANTED: every registry field the record does not carry, with why; UNEXERCISED: the contract's paths no
  saved baseline body holds, with why they are carried all the same.
- UNIVERSES: the universes a trial can be assigned to, the rule packs each owns and what each pack requires,
  and the vocabulary and MeSH anchors the assignment reads (the assignment itself is unit B's).
- DISPLAY: the clinical words for every registry code the workbook shows, from the API's own enum table.

tests/test_contract.py holds the founder's two principles as gates: no false silence (every plain path
resolves in the saved baseline bodies and exists in the API's field metadata, and every metadata field is
carried or named in NOT_WANTED) and nothing nobody uses (every field has a consumer, and every consumer
exists). No rule here reads a trial; the helpers below only resolve a path template and look up words.
"""

from __future__ import annotations

from typing import Any, NamedTuple

CONTRACT_VERSION = "contract-1"
SCHEMA_VERSION = "3"


class Field(NamedTuple):
    """One field of landscape.json schema 3.

    name      — its dotted path in landscape.json, list items as "[]";
    label     — what a reviewer calls it;
    kind      — plain (a registry value, copied), reading (a named rule's reading of the trial) or run (what
                the run records about itself);
    source    — plain: the API path templates it is copied from (several when the registry keeps it in
                several lists or scopes); reading or run: the one rule or table, as module.name;
    consumers — ("sheet", sheet, column), ("mcp", record part) or ("design", module.function);
    display   — the DISPLAY dictionary its codes are shown through, "" when it shows no code;
    form      — plain: "as held", "distinct" (the distinct values, in registry order), "count" (how many
                entries) or "which list" (the name of the list that holds the entry);
    reads     — a reading's registry inputs, as API path templates;
    built_by  — for a rule not yet built, the tasks.md task that builds it.
    """

    name: str
    label: str
    kind: str
    source: tuple[str, ...]
    consumers: tuple[tuple[str, ...], ...]
    display: str = ""
    form: str = "as held"
    reads: tuple[str, ...] = ()
    built_by: str = ""


class Column(NamedTuple):
    """A workbook column: its header, as the reviewer reads it, the fields it shows, and what it shows
    (SHOWS): fields; the row's address in the record; or, repeated for each group G1 ... Gn, a group's
    fields."""

    header: str
    fields: tuple[str, ...]
    shows: str = "fields"


class Sheet(NamedTuple):
    """A workbook sheet: its name, what one row is, and its columns in order."""

    name: str
    row: str
    columns: tuple[Column, ...]


KINDS = ("plain", "reading", "run")
FORMS = ("as held", "distinct", "count", "which list")
SHOWS = {
    "fields": "the fields it names",
    "address": "the row's address in landscape.json, a JSON pointer to the node the row shows (its key)",
    "per group": "repeated for each group G1 ... Gn of the trial's module, n the most any trial has",
}
# The parts of the MCP record tool not served yet, each with the unit that builds it.
MCP_PARTS_TO_BUILD = {
    "findings": "unit F: the across-trial findings",
    "questions": "unit F: the review questions",
}

# ── where the registry keeps each value ─────────────────────────────────────────────────────────────────

ID = "protocolSection.identificationModule"
ST = "protocolSection.statusModule"
SP = "protocolSection.sponsorCollaboratorsModule"
DE = "protocolSection.descriptionModule"
DS = "protocolSection.designModule"
DI = "protocolSection.designModule.designInfo"
AI = "protocolSection.armsInterventionsModule"
OU = "protocolSection.outcomesModule"
EL = "protocolSection.eligibilityModule"
CL = "protocolSection.contactsLocationsModule"
RF = "protocolSection.referencesModule"
FL = "resultsSection.participantFlowModule"
BL = "resultsSection.baselineCharacteristicsModule"
OM = "resultsSection.outcomeMeasuresModule.outcomeMeasures[]"
AE = "resultsSection.adverseEventsModule"
LD = "documentSection.largeDocumentModule"
CB = "derivedSection.conditionBrowseModule"
IB = "derivedSection.interventionBrowseModule"
OUTCOME_LISTS = (f"{OU}.primaryOutcomes[]", f"{OU}.secondaryOutcomes[]", f"{OU}.otherOutcomes[]")
EVENT_LISTS = (f"{AE}.seriousEvents[]", f"{AE}.otherEvents[]")

# ── the sheets, by name ─────────────────────────────────────────────────────────────────────────────────

READ_ME = "Read me"
INDEX = "Trial index"
REVIEW = "Trial review"
ELIGIBILITY = "Eligibility"
REGISTERED = "Registered outcomes"
POSTED = "Posted results"
ANALYSES = "Statistical analyses"
BASELINE = "Baseline"
FLOW = "Participant flow"
GROUPS = "Groups"
SAFETY = "Safety"
BIOMARKERS = "Biomarkers"
FINDINGS = "Across-trial findings"
STANDARD = "Standard protocol language"
READINGS = "Readings"
DICTIONARY = "Column dictionary"

# Consumers many fields share.
DOSSIER = ("sheet", REVIEW, "Value")
ON_README = (("sheet", READ_ME, "Topic"), ("sheet", READ_ME, "Content"))
STUDY = ("mcp", "study")
STUDIES = ("mcp", "studies")
MANIFEST = ("mcp", "manifest")
STUDY_VIEW = ("design", "reading.study_view")
# A rule's reading is one row of the Readings sheet: the field, the words read, the rule, the result and the
# status of its value object.
ON_READINGS = tuple(
    ("sheet", READINGS, column) for column in ("Field", "Words read", "Rule and version", "Result", "Status")
)
# Safety lays out each trial's adverse-event groups G1 ... Gn across the row, three numeric cells a group, n
# the most adverse-event groups any trial of the run has; the Groups sheet names each trial's G1 ... Gn.
SAFETY_GROUP_HEADERS = ("G{n} affected", "G{n} at risk", "G{n} events")
ON_FINDINGS = tuple(
    ("sheet", FINDINGS, column)
    for column in ("Type", "Finding", "Trial IDs", "Numerator / denominator", "Population and limits", "Rule")
)

# ── the fields ──────────────────────────────────────────────────────────────────────────────────────────
# Every study field is also served whole to the assistant through the record tool's `study` part; that
# consumer is added below, so each entry names only the consumers particular to it.

_STUDY_FIELDS: tuple[Field, ...] = (
    # identity
    Field(
        "studies[].nct",
        "Trial ID (NCT number)",
        "plain",
        (f"{ID}.nctId",),
        (
            ("sheet", INDEX, "Trial ID"),
            ("sheet", INDEX, "Dossier"),
            ("sheet", REVIEW, "Trial ID"),
            ("sheet", ELIGIBILITY, "Trial ID"),
            ("sheet", REGISTERED, "Trial ID"),
            ("sheet", POSTED, "Trial ID"),
            ("sheet", ANALYSES, "Trial ID"),
            ("sheet", BASELINE, "Trial ID"),
            ("sheet", FLOW, "Trial ID"),
            ("sheet", GROUPS, "Trial ID"),
            ("sheet", SAFETY, "Trial ID"),
            ("sheet", BIOMARKERS, "Trial ID"),
            ("sheet", READINGS, "Trial ID"),
            STUDIES,
            STUDY_VIEW,
        ),
    ),
    Field(
        "studies[].link",
        "Registry page",
        "run",
        ("links.study_link",),
        (("sheet", INDEX, "Trial ID"), STUDIES),
    ),
    Field("studies[].digest", "The study record's digest", "run", ("warrants.study_digest",), ()),
    Field(
        "studies[].brief_title",
        "Brief title",
        "plain",
        (f"{ID}.briefTitle",),
        (("sheet", INDEX, "Acronym or short title"), DOSSIER),
    ),
    Field(
        "studies[].acronym",
        "Acronym",
        "plain",
        (f"{ID}.acronym",),
        (("sheet", INDEX, "Acronym or short title"), DOSSIER),
    ),
    Field("studies[].official_title", "Official title", "plain", (f"{ID}.officialTitle",), (DOSSIER,)),
    Field(
        "studies[].org_study_id",
        "Sponsor's protocol number",
        "plain",
        (f"{ID}.orgStudyIdInfo.id",),
        (DOSSIER,),
    ),
    Field(
        "studies[].secondary_ids[].id",
        "Other trial identifier",
        "plain",
        (f"{ID}.secondaryIdInfos[].id",),
        (DOSSIER,),
    ),
    Field(
        "studies[].secondary_ids[].type",
        "Kind of identifier",
        "plain",
        (f"{ID}.secondaryIdInfos[].type",),
        (DOSSIER,),
        display="SecondaryIdType",
    ),
    Field(
        "studies[].secondary_ids[].domain",
        "Issuing registry or funder",
        "plain",
        (f"{ID}.secondaryIdInfos[].domain",),
        (DOSSIER,),
    ),
    Field(
        "studies[].nct_aliases",
        "Former NCT numbers",
        "plain",
        (f"{ID}.nctIdAliases[]",),
        (DOSSIER,),
    ),
    # status and dates
    Field(
        "studies[].overall_status",
        "Overall status",
        "plain",
        (f"{ST}.overallStatus",),
        (("sheet", INDEX, "Status"), DOSSIER, STUDIES, STUDY_VIEW),
        display="Status",
    ),
    Field(
        "studies[].last_known_status",
        "Last known status (for a trial whose status is unknown)",
        "plain",
        (f"{ST}.lastKnownStatus",),
        (("sheet", INDEX, "Status"), DOSSIER),
        display="Status",
    ),
    Field("studies[].why_stopped", "Why stopped", "plain", (f"{ST}.whyStopped",), (DOSSIER,)),
    Field(
        "studies[].start_date.date",
        "Start date",
        "plain",
        (f"{ST}.startDateStruct.date",),
        (("sheet", INDEX, "Start"), DOSSIER, STUDIES, STUDY_VIEW),
    ),
    Field(
        "studies[].start_date.type",
        "Start date: actual or anticipated",
        "plain",
        (f"{ST}.startDateStruct.type",),
        (("sheet", INDEX, "Start"), DOSSIER, STUDIES),
        display="DateType",
    ),
    Field(
        "studies[].primary_completion_date.date",
        "Primary completion date",
        "plain",
        (f"{ST}.primaryCompletionDateStruct.date",),
        (DOSSIER, STUDIES),
    ),
    Field(
        "studies[].primary_completion_date.type",
        "Primary completion date: actual or anticipated",
        "plain",
        (f"{ST}.primaryCompletionDateStruct.type",),
        (DOSSIER, STUDIES),
        display="DateType",
    ),
    Field(
        "studies[].completion_date.date",
        "Study completion date",
        "plain",
        (f"{ST}.completionDateStruct.date",),
        (DOSSIER, STUDIES),
    ),
    Field(
        "studies[].completion_date.type",
        "Study completion date: actual or anticipated",
        "plain",
        (f"{ST}.completionDateStruct.type",),
        (DOSSIER, STUDIES),
        display="DateType",
    ),
    Field(
        "studies[].first_posted",
        "First posted",
        "plain",
        (f"{ST}.studyFirstPostDateStruct.date",),
        (DOSSIER,),
    ),
    Field(
        "studies[].results_first_posted",
        "Results first posted",
        "plain",
        (f"{ST}.resultsFirstPostDateStruct.date",),
        (("sheet", INDEX, "Results posted"), DOSSIER),
    ),
    Field(
        "studies[].last_update_posted",
        "Last update posted",
        "plain",
        (f"{ST}.lastUpdatePostDateStruct.date",),
        (("sheet", INDEX, "Last update posted"), DOSSIER),
    ),
    # sponsor and oversight
    Field(
        "studies[].lead_sponsor.name",
        "Lead sponsor",
        "plain",
        (f"{SP}.leadSponsor.name",),
        (("sheet", INDEX, "Sponsor"), DOSSIER, STUDIES, STUDY_VIEW),
    ),
    Field(
        "studies[].lead_sponsor.class",
        "Sponsor class",
        "plain",
        (f"{SP}.leadSponsor.class",),
        (("sheet", INDEX, "Sponsor"), DOSSIER),
        display="AgencyClass",
    ),
    Field(
        "studies[].collaborators[].name", "Collaborator", "plain", (f"{SP}.collaborators[].name",), (DOSSIER,)
    ),
    Field(
        "studies[].collaborators[].class",
        "Collaborator class",
        "plain",
        (f"{SP}.collaborators[].class",),
        (DOSSIER,),
        display="AgencyClass",
    ),
    Field(
        "studies[].dmc",
        "Data monitoring committee",
        "plain",
        ("protocolSection.oversightModule.oversightHasDmc",),
        (DOSSIER,),
    ),
    Field(
        "studies[].officials[].name",
        "Overall official",
        "plain",
        (f"{CL}.overallOfficials[].name",),
        (DOSSIER,),
    ),
    Field(
        "studies[].officials[].affiliation",
        "Official's affiliation",
        "plain",
        (f"{CL}.overallOfficials[].affiliation",),
        (DOSSIER,),
    ),
    Field(
        "studies[].officials[].role",
        "Official's role",
        "plain",
        (f"{CL}.overallOfficials[].role",),
        (DOSSIER,),
        display="OfficialRole",
    ),
    Field(
        "studies[].countries",
        "Countries",
        "plain",
        (f"{CL}.locations[].country",),
        (("sheet", INDEX, "Countries"), DOSSIER),
        form="distinct",
    ),
    Field(
        "studies[].site_count",
        "Sites",
        "plain",
        (f"{CL}.locations[]",),
        (DOSSIER,),
        form="count",
    ),
    # description
    Field("studies[].brief_summary", "Brief summary", "plain", (f"{DE}.briefSummary",), (DOSSIER,)),
    Field(
        "studies[].detailed_description",
        "Detailed description (schedules, rescue rules and design rationale, as the sponsor wrote them)",
        "plain",
        (f"{DE}.detailedDescription",),
        (DOSSIER,),
    ),
    # conditions and their MeSH terms
    Field(
        "studies[].conditions",
        "Conditions",
        "plain",
        ("protocolSection.conditionsModule.conditions[]",),
        (("sheet", INDEX, "Conditions"), DOSSIER, STUDIES),
    ),
    Field("studies[].condition_mesh", "Condition MeSH terms", "plain", (f"{CB}.meshes[].term",), (DOSSIER,)),
    Field(
        "studies[].condition_mesh_ancestors",
        "Condition MeSH ancestors",
        "plain",
        (f"{CB}.ancestors[].term",),
        (DOSSIER,),
    ),
    Field(
        "studies[].intervention_mesh",
        "Intervention MeSH terms (the registry's terms, never a drug class)",
        "plain",
        (f"{IB}.meshes[].term",),
        (DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].intervention_mesh_ancestors",
        "Intervention MeSH ancestors",
        "plain",
        (f"{IB}.ancestors[].term",),
        (DOSSIER,),
    ),
    # design
    Field(
        "studies[].phases",
        "Phase",
        "plain",
        (f"{DS}.phases[]",),
        (("sheet", INDEX, "Phase"), DOSSIER, STUDIES),
        display="Phase",
    ),
    Field(
        "studies[].primary_purpose",
        "Primary purpose",
        "plain",
        (f"{DI}.primaryPurpose",),
        (("sheet", INDEX, "Design"), DOSSIER),
        display="PrimaryPurpose",
    ),
    Field(
        "studies[].allocation",
        "Allocation",
        "plain",
        (f"{DI}.allocation",),
        (("sheet", INDEX, "Design"), DOSSIER),
        display="DesignAllocation",
    ),
    Field(
        "studies[].intervention_model",
        "Intervention model",
        "plain",
        (f"{DI}.interventionModel",),
        (("sheet", INDEX, "Design"), DOSSIER),
        display="InterventionalAssignment",
    ),
    Field(
        "studies[].intervention_model_description",
        "Intervention model, as described",
        "plain",
        (f"{DI}.interventionModelDescription",),
        (DOSSIER,),
    ),
    Field(
        "studies[].masking",
        "Masking",
        "plain",
        (f"{DI}.maskingInfo.masking",),
        (("sheet", INDEX, "Design"), DOSSIER),
        display="DesignMasking",
    ),
    Field(
        "studies[].who_masked",
        "Who is masked",
        "plain",
        (f"{DI}.maskingInfo.whoMasked[]",),
        (("sheet", INDEX, "Design"), DOSSIER),
        display="WhoMasked",
    ),
    Field(
        "studies[].masking_description",
        "Masking, as described",
        "plain",
        (f"{DI}.maskingInfo.maskingDescription",),
        (DOSSIER,),
    ),
    Field(
        "studies[].study_type",
        "Study type",
        "plain",
        (f"{DS}.studyType",),
        (DOSSIER, STUDIES),
        display="StudyType",
    ),
    Field(
        "studies[].enrollment.count",
        "Enrollment",
        "plain",
        (f"{DS}.enrollmentInfo.count",),
        (("sheet", INDEX, "Enrollment"), DOSSIER, STUDIES),
    ),
    Field(
        "studies[].enrollment.type",
        "Enrollment: actual or anticipated",
        "plain",
        (f"{DS}.enrollmentInfo.type",),
        (("sheet", INDEX, "Enrollment"), DOSSIER, STUDIES),
        display="EnrollmentType",
    ),
    # arms and interventions
    Field(
        "studies[].arms[].label",
        "Arm",
        "plain",
        (f"{AI}.armGroups[].label",),
        (DOSSIER,),
    ),
    Field(
        "studies[].arms[].type",
        "Arm type",
        "plain",
        (f"{AI}.armGroups[].type",),
        (DOSSIER, ("design", "classes.experimental_drugs")),
        display="ArmGroupType",
    ),
    Field(
        "studies[].arms[].description",
        "Arm description",
        "plain",
        (f"{AI}.armGroups[].description",),
        (DOSSIER,),
    ),
    Field(
        "studies[].arms[].interventions",
        "The arm's interventions",
        "plain",
        (f"{AI}.armGroups[].interventionNames[]",),
        (DOSSIER, ("design", "classes.experimental_drugs")),
    ),
    Field(
        "studies[].interventions[].type",
        "Intervention type",
        "plain",
        (f"{AI}.interventions[].type",),
        (DOSSIER, ("design", "classes.experimental_drugs")),
        display="InterventionType",
    ),
    Field(
        "studies[].interventions[].name",
        "Intervention",
        "plain",
        (f"{AI}.interventions[].name",),
        (DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].interventions[].description",
        "Intervention description",
        "plain",
        (f"{AI}.interventions[].description",),
        (DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].interventions[].arms",
        "Arms given it",
        "plain",
        (f"{AI}.interventions[].armGroupLabels[]",),
        (DOSSIER,),
    ),
    Field(
        "studies[].interventions[].other_names",
        "Other names",
        "plain",
        (f"{AI}.interventions[].otherNames[]",),
        (DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].interventions[].drug_class",
        "Drug class (an experimental drug's)",
        "reading",
        ("classes.drug_class",),
        (DOSSIER, *ON_READINGS),
        reads=(f"{AI}.interventions[].name", f"{AI}.interventions[].otherNames[]", f"{AI}.armGroups[].type"),
    ),
    Field(
        "studies[].interventions[].axes",
        "Drug axes: RxNorm identity, ATC and structure classes, stated targets",
        "reading",
        ("classes.drug_axes",),
        (*ON_READINGS, ("design", "design.sheets")),
        reads=(f"{AI}.interventions[].name", f"{AI}.interventions[].otherNames[]"),
    ),
    Field(
        "studies[].interventions[].modality",
        "Modality and cell properties the entry states",
        "reading",
        ("modality.entry_properties",),
        ON_READINGS,
        reads=(
            f"{AI}.interventions[].name",
            f"{AI}.interventions[].otherNames[]",
            f"{AI}.interventions[].description",
        ),
    ),
    # the population and its eligibility
    Field(
        "studies[].population.minimum_age",
        "Minimum age",
        "plain",
        (f"{EL}.minimumAge",),
        (DOSSIER,),
    ),
    Field(
        "studies[].population.maximum_age",
        "Maximum age",
        "plain",
        (f"{EL}.maximumAge",),
        (DOSSIER,),
    ),
    Field(
        "studies[].population.sex",
        "Sex",
        "plain",
        (f"{EL}.sex",),
        (DOSSIER,),
        display="Sex",
    ),
    Field(
        "studies[].population.age_groups",
        "Age groups",
        "plain",
        (f"{EL}.stdAges[]",),
        (DOSSIER,),
        display="StandardAge",
    ),
    Field(
        "studies[].population.healthy_volunteers",
        "Accepts healthy volunteers",
        "plain",
        (f"{EL}.healthyVolunteers",),
        (DOSSIER,),
    ),
    Field(
        "studies[].population.gender_based",
        "Eligibility based on gender",
        "plain",
        (f"{EL}.genderBased",),
        (DOSSIER,),
    ),
    Field(
        "studies[].population.gender_description",
        "Gender eligibility, as described",
        "plain",
        (f"{EL}.genderDescription",),
        (DOSSIER,),
    ),
    Field(
        "studies[].eligibility.text",
        "Eligibility criteria, as written",
        "plain",
        (f"{EL}.eligibilityCriteria",),
        (STUDY_VIEW,),
    ),
    Field(
        "studies[].eligibility.coverage",
        "Why the criteria could not be itemized (held only where they could not be)",
        "reading",
        ("criteria.eligibility_coverage",),
        ON_READINGS,
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    Field(
        "studies[].criteria[].heading",
        "Heading",
        "reading",
        ("criteria.itemize",),
        (("sheet", ELIGIBILITY, "Heading"),),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    Field(
        "studies[].criteria[].number",
        "Criterion number",
        "reading",
        ("criteria.itemize",),
        (("sheet", ELIGIBILITY, "Criterion number"),),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    Field(
        "studies[].criteria[].text",
        "Criterion as written",
        "reading",
        ("criteria.itemize",),
        (("sheet", ELIGIBILITY, "Criterion as written"),),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    Field(
        "studies[].criteria[].role",
        "Role",
        "reading",
        ("criteria.criterion_role",),
        (("sheet", ELIGIBILITY, "Role"), *ON_READINGS),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    Field(
        "studies[].criteria[].readings",
        "Readings (each labelled: what was read, the words, the rule)",
        "reading",
        ("banks.type_criterion",),
        (("sheet", ELIGIBILITY, "Readings"), *ON_READINGS),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
    # key criteria: the criteria whose readings fall in a key category (KEY_CRITERION_CATEGORIES)
    *(
        Field(
            f"studies[].key_criteria[].{name}",
            label,
            "reading",
            ("landscape.key_criteria",),
            (DOSSIER,),
            reads=(f"{EL}.eligibilityCriteria",),
        )
        for name, label in (
            ("text", "Key criterion, as written"),
            ("role", "Its role (inclusion or exclusion)"),
            ("reading", "Its reading: the key category and the readings in it"),
            ("rule", "The rule that read it"),
        )
    ),
    Field(
        "studies[].biomarker_mentions",
        "Biomarker mentions (words, role, rule)",
        "reading",
        ("banks.biomarker_status",),
        (
            ("sheet", BIOMARKERS, "Biomarker"),
            ("sheet", BIOMARKERS, "States"),
            ("sheet", BIOMARKERS, "Role"),
            ("sheet", BIOMARKERS, "Words read"),
            ("sheet", BIOMARKERS, "Rule"),
            *ON_READINGS,
        ),
        reads=(f"{EL}.eligibilityCriteria", *(f"{key}.measure" for key in OUTCOME_LISTS)),
    ),
    # the universe and the domain readings it permits
    Field(
        "studies[].universe",
        "Universe and the source that decided it",
        "reading",
        ("universes.assign",),
        (("sheet", INDEX, "Universe"), DOSSIER, STUDIES, *ON_READINGS),
        reads=(
            f"{CB}.meshes[].term",
            f"{CB}.ancestors[].term",
            "protocolSection.conditionsModule.conditions[]",
            f"{ID}.briefTitle",
            f"{ID}.officialTitle",
            f"{DI}.primaryPurpose",
            f"{AI}.interventions[].name",
            f"{AI}.interventions[].otherNames[]",
        ),
    ),
    # Each coordinate at the levels coherence.resolve gives it (landscape.json schema 2, kept in schema 3):
    # known (the record's own criteria and the strict relations); interpolated (the default relations added);
    # and, as a list, what each proposal alone would make of the interpolated value, never built on. The index
    # shows the known and interpolated levels, each labelled; the proposals and the reasons are the dossier's.
    *(
        Field(
            f"studies[].coordinates.{name}{suffix}",
            f"{label}{words}",
            "reading",
            ("coherence.resolve",),
            ((("sheet", INDEX, column),) if suffix != "_proposed" else ()) + (DOSSIER, *ON_READINGS),
            reads=(f"{EL}.eligibilityCriteria",),
        )
        for name, label, column in (
            ("setting", "Treatment setting, as registered", "Treatment setting"),
            ("prior_advanced_lines", "Prior lines for advanced disease", "Prior lines for advanced disease"),
            ("selection", "Gene selection (per gene)", "Gene selection"),
        )
        for suffix, words in (
            ("", ", known (the record's own criteria and the strict relations)"),
            ("_interpolated", ", interpolated (the default relations added)"),
            ("_proposed", ", as each proposal alone would narrow it (never built on)"),
        )
    ),
    # registered (planned) outcomes
    Field(
        "studies[].registered_outcomes[].category",
        "Category (primary, secondary, other)",
        "plain",
        OUTCOME_LISTS,
        (("sheet", REGISTERED, "Category"), ("sheet", INDEX, "Primary endpoint"), DOSSIER),
        form="which list",
    ),
    Field(
        "studies[].registered_outcomes[].measure",
        "Measure",
        "plain",
        tuple(f"{key}.measure" for key in OUTCOME_LISTS),
        (("sheet", REGISTERED, "Measure"), ("sheet", INDEX, "Primary endpoint"), DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].registered_outcomes[].description",
        "Description",
        "plain",
        tuple(f"{key}.description" for key in OUTCOME_LISTS),
        (("sheet", REGISTERED, "Description"),),
    ),
    Field(
        "studies[].registered_outcomes[].time_frame",
        "Time frame",
        "plain",
        tuple(f"{key}.timeFrame" for key in OUTCOME_LISTS),
        (("sheet", REGISTERED, "Time frame"), DOSSIER, STUDY_VIEW),
    ),
    Field(
        "studies[].registered_outcomes[].endpoint_classes",
        "Endpoint classes the measure names",
        "reading",
        ("banks.endpoint_classes",),
        (("sheet", REGISTERED, "Endpoint reading"), *ON_READINGS),
        reads=tuple(f"{key}.measure" for key in OUTCOME_LISTS),
    ),
    Field(
        "studies[].registered_outcomes[].time_points",
        "Time points the time frame states",
        "reading",
        ("banks.time_points",),
        (("sheet", REGISTERED, "Time-point reading"), *ON_READINGS),
        reads=tuple(f"{key}.timeFrame" for key in OUTCOME_LISTS),
    ),
    # results: whether posted
    Field(
        "studies[].results_posted",
        "Results posted",
        "reading",
        ("ledger.results_state",),
        (("sheet", INDEX, "Results posted"), DOSSIER, STUDIES),
        reads=("hasResults",),
    ),
    # posted outcome measures, their groups, denominators and measurements
    Field(
        "studies[].posted_outcomes[].type",
        "Outcome type",
        "plain",
        (f"{OM}.type",),
        (("sheet", POSTED, "Outcome type"), STUDY_VIEW),
        display="OutcomeMeasureType",
    ),
    Field(
        "studies[].posted_outcomes[].title",
        "Measure",
        "plain",
        (f"{OM}.title",),
        (("sheet", POSTED, "Measure"), ("sheet", ANALYSES, "Measure"), STUDY_VIEW),
    ),
    Field(
        "studies[].posted_outcomes[].description",
        "Measure description",
        "plain",
        (f"{OM}.description",),
        (("sheet", POSTED, "Measure description"),),
    ),
    Field(
        "studies[].posted_outcomes[].population",
        "Analysis population",
        "plain",
        (f"{OM}.populationDescription",),
        (("sheet", POSTED, "Analysis population"),),
    ),
    Field(
        "studies[].posted_outcomes[].reporting_status",
        "Reporting status",
        "plain",
        (f"{OM}.reportingStatus",),
        (("sheet", POSTED, "Reporting status"),),
        display="ReportingStatus",
    ),
    Field(
        "studies[].posted_outcomes[].anticipated_posting_date",
        "Anticipated posting date",
        "plain",
        (f"{OM}.anticipatedPostingDate",),
        (("sheet", POSTED, "Reporting status"),),
    ),
    Field(
        "studies[].posted_outcomes[].param_type",
        "Parameter",
        "plain",
        (f"{OM}.paramType",),
        (("sheet", POSTED, "Parameter"), STUDY_VIEW),
        display="MeasureParam",
    ),
    Field(
        "studies[].posted_outcomes[].dispersion_type",
        "Dispersion or interval",
        "plain",
        (f"{OM}.dispersionType",),
        (("sheet", POSTED, "Spread or limits"),),
    ),
    Field(
        "studies[].posted_outcomes[].unit",
        "Unit",
        "plain",
        (f"{OM}.unitOfMeasure",),
        (("sheet", POSTED, "Unit"), STUDY_VIEW),
    ),
    Field(
        "studies[].posted_outcomes[].time_frame",
        "Time frame",
        "plain",
        (f"{OM}.timeFrame",),
        (("sheet", POSTED, "Time frame"), STUDY_VIEW),
    ),
    Field(
        "studies[].posted_outcomes[].units_analyzed",
        "Units analyzed (other than participants)",
        "plain",
        (f"{OM}.typeUnitsAnalyzed",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].denominator_units",
        "Units of the measure's denominator",
        "plain",
        (f"{OM}.denomUnitsSelected",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].groups[].id",
        "Group ID (within the measure)",
        "plain",
        (f"{OM}.groups[].id",),
        (("sheet", GROUPS, "Group ID"), ("sheet", GROUPS, "Module"), ("sheet", GROUPS, "Column")),
    ),
    Field(
        "studies[].posted_outcomes[].groups[].title",
        "Group",
        "plain",
        (f"{OM}.groups[].title",),
        (("sheet", POSTED, "Group"), ("sheet", GROUPS, "Title"), STUDY_VIEW),
    ),
    Field(
        "studies[].posted_outcomes[].groups[].description",
        "Group description",
        "plain",
        (f"{OM}.groups[].description",),
        (("sheet", GROUPS, "Description"),),
    ),
    Field(
        "studies[].posted_outcomes[].denominators[].units",
        "Denominator units (measure)",
        "plain",
        (f"{OM}.denoms[].units",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].denominators[].counts[].group",
        "Denominator group (measure)",
        "plain",
        (f"{OM}.denoms[].counts[].groupId",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].denominators[].counts[].value",
        "Denominator (measure)",
        "plain",
        (f"{OM}.denoms[].counts[].value",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].classes[].title",
        "Class",
        "plain",
        (f"{OM}.classes[].title",),
        (("sheet", POSTED, "Class"), STUDY_VIEW),
    ),
    Field(
        "studies[].posted_outcomes[].classes[].denominators[].units",
        "Denominator units (class)",
        "plain",
        (f"{OM}.classes[].denoms[].units",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].classes[].denominators[].counts[].group",
        "Denominator group (class)",
        "plain",
        (f"{OM}.classes[].denoms[].counts[].groupId",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].classes[].denominators[].counts[].value",
        "Denominator (class)",
        "plain",
        (f"{OM}.classes[].denoms[].counts[].value",),
        (("sheet", POSTED, "Denominator"),),
    ),
    Field(
        "studies[].posted_outcomes[].classes[].categories[].title",
        "Category",
        "plain",
        (f"{OM}.classes[].categories[].title",),
        (("sheet", POSTED, "Category"), STUDY_VIEW),
    ),
    *(
        Field(
            f"studies[].posted_outcomes[].classes[].categories[].measurements[].{name}",
            label,
            "plain",
            (f"{OM}.classes[].categories[].measurements[].{key}",),
            (("sheet", POSTED, column), *((STUDY_VIEW,) if key != "comment" else ())),
        )
        for name, key, label, column in (
            ("group", "groupId", "Group ID", "Group"),
            ("value", "value", "Value", "Value"),
            ("spread", "spread", "Spread", "Spread or limits"),
            ("lower_limit", "lowerLimit", "Lower limit", "Spread or limits"),
            ("upper_limit", "upperLimit", "Upper limit", "Spread or limits"),
            ("comment", "comment", "Comment (why a value is NA, as the registry gives it)", "Comment"),
        )
    ),
    Field(
        "studies[].posted_outcomes[].endpoint_classes",
        "Endpoint classes the measure's title names",
        "reading",
        ("banks.endpoint_classes",),
        (*ON_READINGS, STUDY_VIEW),
        reads=(f"{OM}.title",),
    ),
    # statistical analyses, per posted measure
    *(
        Field(
            f"studies[].posted_outcomes[].analyses[].{name}",
            label,
            "plain",
            (f"{OM}.analyses[].{key}",),
            (("sheet", ANALYSES, column),),
            display=display,
        )
        for name, key, label, column, display in (
            ("groups", "groupIds[]", "Groups compared", "Compared groups", ""),
            ("group_description", "groupDescription", "Comparison, as described", "Compared groups", ""),
            ("method", "statisticalMethod", "Statistical method", "Method", ""),
            ("method_comment", "statisticalComment", "Method comment", "Method", ""),
            ("param_type", "paramType", "Estimated parameter", "Parameter", ""),
            ("param_value", "paramValue", "Estimate", "Estimate", ""),
            ("estimate_comment", "estimateComment", "Estimate comment", "Estimate", ""),
            (
                "dispersion_type",
                "dispersionType",
                "Estimate's dispersion",
                "Estimate",
                "AnalysisDispersionType",
            ),
            ("dispersion_value", "dispersionValue", "Estimate's dispersion value", "Estimate", ""),
            ("ci_percent", "ciPctValue", "Confidence level (%)", "Confidence interval", ""),
            ("ci_sides", "ciNumSides", "Sides", "Confidence interval", "ConfidenceIntervalNumSides"),
            ("ci_lower", "ciLowerLimit", "Lower limit", "Confidence interval", ""),
            ("ci_upper", "ciUpperLimit", "Upper limit", "Confidence interval", ""),
            ("ci_lower_comment", "ciLowerLimitComment", "Lower limit comment", "Confidence interval", ""),
            ("ci_upper_comment", "ciUpperLimitComment", "Upper limit comment", "Confidence interval", ""),
            ("p_value", "pValue", "P-value", "P-value", ""),
            ("p_value_comment", "pValueComment", "P-value comment", "P-value", ""),
            (
                "hypothesis",
                "nonInferiorityType",
                "Superiority, non-inferiority or equivalence",
                "Hypothesis",
                "NonInferiorityType",
            ),
            ("hypothesis_comment", "nonInferiorityComment", "Hypothesis comment", "Hypothesis", ""),
            ("other_description", "otherAnalysisDescription", "Other analysis", "Other analysis", ""),
        )
    ),
    # baseline characteristics
    Field(
        "studies[].baseline.population",
        "Baseline analysis population",
        "plain",
        (f"{BL}.populationDescription",),
        (("sheet", BASELINE, "Population"),),
    ),
    Field(
        "studies[].baseline.units_analyzed",
        "Units analyzed (other than participants)",
        "plain",
        (f"{BL}.typeUnitsAnalyzed",),
        (("sheet", BASELINE, "Denominator"),),
    ),
    Field(
        "studies[].baseline.groups[].id",
        "Group ID (within baseline)",
        "plain",
        (f"{BL}.groups[].id",),
        (("sheet", GROUPS, "Group ID"), ("sheet", GROUPS, "Module"), ("sheet", GROUPS, "Column")),
    ),
    Field(
        "studies[].baseline.groups[].title",
        "Group",
        "plain",
        (f"{BL}.groups[].title",),
        (("sheet", BASELINE, "Group"), ("sheet", GROUPS, "Title")),
    ),
    Field(
        "studies[].baseline.groups[].description",
        "Group description",
        "plain",
        (f"{BL}.groups[].description",),
        (("sheet", GROUPS, "Description"),),
    ),
    *(
        Field(
            f"studies[].baseline.{scope}denominators[].{name}",
            f"{label} ({where})",
            "plain",
            (f"{BL}.{path}denoms[].{key}",),
            (("sheet", BASELINE, "Denominator"),),
        )
        for scope, path, where in (
            ("", "", "baseline"),
            ("measures[].", "measures[].", "measure"),
            ("measures[].classes[].", "measures[].classes[].", "class"),
        )
        for name, key, label in (
            ("units", "units", "Denominator units"),
            ("counts[].group", "counts[].groupId", "Denominator group"),
            ("counts[].value", "counts[].value", "Denominator"),
        )
    ),
    Field(
        "studies[].baseline.measures[].title",
        "Characteristic",
        "plain",
        (f"{BL}.measures[].title",),
        (("sheet", BASELINE, "Characteristic"),),
    ),
    Field(
        "studies[].baseline.measures[].description",
        "Characteristic description",
        "plain",
        (f"{BL}.measures[].description",),
        (("sheet", BASELINE, "Characteristic"),),
    ),
    Field(
        "studies[].baseline.measures[].population",
        "Characteristic's analysis population",
        "plain",
        (f"{BL}.measures[].populationDescription",),
        (("sheet", BASELINE, "Population"),),
    ),
    Field(
        "studies[].baseline.measures[].param_type",
        "Parameter",
        "plain",
        (f"{BL}.measures[].paramType",),
        (("sheet", BASELINE, "Parameter"),),
        display="MeasureParam",
    ),
    Field(
        "studies[].baseline.measures[].dispersion_type",
        "Dispersion or interval",
        "plain",
        (f"{BL}.measures[].dispersionType",),
        (("sheet", BASELINE, "Spread or limits"),),
        display="MeasureDispersionType",
    ),
    Field(
        "studies[].baseline.measures[].unit",
        "Unit",
        "plain",
        (f"{BL}.measures[].unitOfMeasure",),
        (("sheet", BASELINE, "Unit"),),
    ),
    Field(
        "studies[].baseline.measures[].denominator_units",
        "Units of the characteristic's denominator",
        "plain",
        (f"{BL}.measures[].denomUnitsSelected",),
        (("sheet", BASELINE, "Denominator"),),
    ),
    Field(
        "studies[].baseline.measures[].classes[].title",
        "Class",
        "plain",
        (f"{BL}.measures[].classes[].title",),
        (("sheet", BASELINE, "Class"),),
    ),
    Field(
        "studies[].baseline.measures[].classes[].categories[].title",
        "Category",
        "plain",
        (f"{BL}.measures[].classes[].categories[].title",),
        (("sheet", BASELINE, "Category"),),
    ),
    *(
        Field(
            f"studies[].baseline.measures[].classes[].categories[].measurements[].{name}",
            label,
            "plain",
            (f"{BL}.measures[].classes[].categories[].measurements[].{key}",),
            (("sheet", BASELINE, column),),
        )
        for name, key, label, column in (
            ("group", "groupId", "Group ID", "Group"),
            ("value", "value", "Value", "Value"),
            ("spread", "spread", "Spread", "Spread or limits"),
            ("lower_limit", "lowerLimit", "Lower limit", "Spread or limits"),
            ("upper_limit", "upperLimit", "Upper limit", "Spread or limits"),
            ("comment", "comment", "Comment", "Comment"),
        )
    ),
    # participant flow
    Field(
        "studies[].participant_flow.recruitment_details",
        "Recruitment details",
        "plain",
        (f"{FL}.recruitmentDetails",),
        (DOSSIER,),
    ),
    Field(
        "studies[].participant_flow.pre_assignment_details",
        "Pre-assignment details",
        "plain",
        (f"{FL}.preAssignmentDetails",),
        (DOSSIER,),
    ),
    Field(
        "studies[].participant_flow.units_analyzed",
        "Units analyzed (other than participants)",
        "plain",
        (f"{FL}.typeUnitsAnalyzed",),
        (("sheet", FLOW, "Participants"),),
    ),
    Field(
        "studies[].participant_flow.groups[].id",
        "Group ID (within the flow)",
        "plain",
        (f"{FL}.groups[].id",),
        (("sheet", GROUPS, "Group ID"), ("sheet", GROUPS, "Module"), ("sheet", GROUPS, "Column")),
    ),
    Field(
        "studies[].participant_flow.groups[].title",
        "Group",
        "plain",
        (f"{FL}.groups[].title",),
        (("sheet", FLOW, "Group"), ("sheet", GROUPS, "Title")),
    ),
    Field(
        "studies[].participant_flow.groups[].description",
        "Group description",
        "plain",
        (f"{FL}.groups[].description",),
        (("sheet", GROUPS, "Description"),),
    ),
    Field(
        "studies[].participant_flow.periods[].title",
        "Period",
        "plain",
        (f"{FL}.periods[].title",),
        (("sheet", FLOW, "Period"),),
    ),
    Field(
        "studies[].participant_flow.periods[].milestones[].type",
        "Milestone",
        "plain",
        (f"{FL}.periods[].milestones[].type",),
        (("sheet", FLOW, "Milestone or reason"),),
        display="FlowMilestone",
    ),
    Field(
        "studies[].participant_flow.periods[].milestones[].comment",
        "Milestone comment",
        "plain",
        (f"{FL}.periods[].milestones[].comment",),
        (("sheet", FLOW, "Comment"),),
    ),
    *(
        Field(
            f"studies[].participant_flow.periods[].milestones[].counts[].{name}",
            label,
            "plain",
            (f"{FL}.periods[].milestones[].achievements[].{key}",),
            (("sheet", FLOW, column),),
        )
        for name, key, label, column in (
            ("group", "groupId", "Group ID", "Group"),
            ("participants", "numSubjects", "Participants", "Participants"),
            ("units", "numUnits", "Units", "Participants"),
            ("comment", "comment", "Count comment", "Comment"),
        )
    ),
    Field(
        "studies[].participant_flow.periods[].withdrawals[].reason",
        "Reason not completed",
        "plain",
        (f"{FL}.periods[].dropWithdraws[].type",),
        (("sheet", FLOW, "Milestone or reason"),),
    ),
    Field(
        "studies[].participant_flow.periods[].withdrawals[].comment",
        "Reason comment",
        "plain",
        (f"{FL}.periods[].dropWithdraws[].comment",),
        (("sheet", FLOW, "Comment"),),
    ),
    *(
        Field(
            f"studies[].participant_flow.periods[].withdrawals[].counts[].{name}",
            label,
            "plain",
            (f"{FL}.periods[].dropWithdraws[].reasons[].{key}",),
            (("sheet", FLOW, column),),
        )
        for name, key, label, column in (
            ("group", "groupId", "Group ID", "Group"),
            ("participants", "numSubjects", "Participants", "Participants"),
            ("comment", "comment", "Count comment", "Comment"),
        )
    ),
    # adverse events
    Field(
        "studies[].adverse_events.time_frame",
        "Adverse-event reporting period",
        "plain",
        (f"{AE}.timeFrame",),
        (DOSSIER,),
    ),
    Field(
        "studies[].adverse_events.frequency_threshold",
        "Threshold for reporting other adverse events (%)",
        "plain",
        (f"{AE}.frequencyThreshold",),
        (DOSSIER,),
    ),
    Field(
        "studies[].adverse_events.description",
        "Adverse-event definitions and collection, as described",
        "plain",
        (f"{AE}.description",),
        (DOSSIER,),
    ),
    Field(
        "studies[].adverse_events.all_cause_mortality_comment",
        "All-cause mortality comment",
        "plain",
        (f"{AE}.allCauseMortalityComment",),
        (DOSSIER,),
    ),
    Field(
        "studies[].adverse_events.groups[].id",
        "Group ID (within adverse events)",
        "plain",
        (f"{AE}.eventGroups[].id",),
        (("sheet", GROUPS, "Group ID"), ("sheet", GROUPS, "Module"), ("sheet", GROUPS, "Column")),
    ),
    Field(
        "studies[].adverse_events.groups[].title",
        "Group",
        "plain",
        (f"{AE}.eventGroups[].title",),
        (("sheet", GROUPS, "Title"),),
    ),
    Field(
        "studies[].adverse_events.groups[].description",
        "Group description",
        "plain",
        (f"{AE}.eventGroups[].description",),
        (("sheet", GROUPS, "Description"),),
    ),
    *(
        Field(
            f"studies[].adverse_events.groups[].{name}",
            label,
            "plain",
            (f"{AE}.eventGroups[].{key}",),
            (("sheet", GROUPS, "Totals"),),
        )
        for name, key, label in (
            ("deaths_affected", "deathsNumAffected", "Deaths (all causes)"),
            ("deaths_at_risk", "deathsNumAtRisk", "At risk of death"),
            ("serious_affected", "seriousNumAffected", "Participants with a serious adverse event"),
            ("serious_at_risk", "seriousNumAtRisk", "At risk of a serious adverse event"),
            ("other_affected", "otherNumAffected", "Participants with another adverse event"),
            ("other_at_risk", "otherNumAtRisk", "At risk of another adverse event"),
        )
    ),
    Field(
        "studies[].adverse_events.events[].table",
        "Table (serious or other)",
        "plain",
        EVENT_LISTS,
        (("sheet", SAFETY, "Table"),),
        form="which list",
    ),
    *(
        Field(
            f"studies[].adverse_events.events[].{name}",
            label,
            "plain",
            tuple(f"{key}.{path}" for key in EVENT_LISTS),
            (("sheet", SAFETY, column),),
            display=display,
        )
        for name, path, label, column, display in (
            ("organ_system", "organSystem", "Organ system", "Organ system", ""),
            ("term", "term", "Term", "Term", ""),
            ("vocabulary", "sourceVocabulary", "Vocabulary", "Vocabulary", ""),
            ("assessment", "assessmentType", "Assessment", "Assessment", "EventAssessment"),
            ("notes", "notes", "Notes", "Notes", ""),
        )
    ),
    Field(
        "studies[].adverse_events.events[].counts[].group",
        "Group ID: which group's columns (G1 ... Gn) the counts fill",
        "plain",
        tuple(f"{key}.stats[].groupId" for key in EVENT_LISTS),
        tuple(("sheet", SAFETY, header) for header in SAFETY_GROUP_HEADERS),
    ),
    *(
        Field(
            f"studies[].adverse_events.events[].counts[].{name}",
            label,
            "plain",
            tuple(f"{key}.stats[].{path}" for key in EVENT_LISTS),
            (("sheet", SAFETY, header),),
        )
        for name, path, label, header in (
            ("affected", "numAffected", "Participants affected", SAFETY_GROUP_HEADERS[0]),
            ("at_risk", "numAtRisk", "Participants at risk", SAFETY_GROUP_HEADERS[1]),
            ("events", "numEvents", "Events", SAFETY_GROUP_HEADERS[2]),
        )
    ),
    # limitations, publications, documents
    Field(
        "studies[].limitations",
        "Limitations and caveats",
        "plain",
        ("resultsSection.moreInfoModule.limitationsAndCaveats.description",),
        (DOSSIER,),
    ),
    Field(
        "studies[].references[].pmid",
        "PubMed ID",
        "plain",
        (f"{RF}.references[].pmid",),
        (("sheet", INDEX, "Publications"), DOSSIER),
    ),
    Field(
        "studies[].references[].type",
        "Reference type",
        "plain",
        (f"{RF}.references[].type",),
        (("sheet", INDEX, "Publications"), DOSSIER),
        display="ReferenceType",
    ),
    Field(
        "studies[].references[].citation",
        "Citation",
        "plain",
        (f"{RF}.references[].citation",),
        (DOSSIER,),
    ),
    Field(
        "studies[].references[].retractions[].pmid",
        "Retraction notice (PubMed ID)",
        "plain",
        (f"{RF}.references[].retractions[].pmid",),
        (DOSSIER,),
    ),
    Field(
        "studies[].references[].retractions[].source",
        "Retraction notice (source)",
        "plain",
        (f"{RF}.references[].retractions[].source",),
        (DOSSIER,),
    ),
    Field("studies[].links[].label", "Related link", "plain", (f"{RF}.seeAlsoLinks[].label",), (DOSSIER,)),
    Field(
        "studies[].links[].url", "Related link address", "plain", (f"{RF}.seeAlsoLinks[].url",), (DOSSIER,)
    ),
    Field(
        "studies[].ipd_documents[].type",
        "Available individual participant data or document",
        "plain",
        (f"{RF}.availIpds[].type",),
        (DOSSIER,),
    ),
    Field("studies[].ipd_documents[].url", "Its address", "plain", (f"{RF}.availIpds[].url",), (DOSSIER,)),
    Field(
        "studies[].ipd_documents[].comment",
        "Its comment",
        "plain",
        (f"{RF}.availIpds[].comment",),
        (DOSSIER,),
    ),
    Field(
        "studies[].no_sap",
        "The sponsor states there is no statistical analysis plan",
        "plain",
        (f"{LD}.noSap",),
        (DOSSIER,),
    ),
    *(
        Field(
            f"studies[].documents[].{name}",
            label,
            "plain",
            (f"{LD}.largeDocs[].{key}",),
            (DOSSIER,),
            display=display,
        )
        for name, key, label, display in (
            ("type", "typeAbbrev", "Posted document", "LargeDocType"),
            ("label", "label", "Document label", ""),
            ("date", "date", "Document date", ""),
        )
    ),
    Field(
        "studies[].documents[].url",
        "Document link",
        "run",
        ("links.document_link",),
        (DOSSIER,),
    ),
    # the questions the rules leave open, per study
    Field(
        "studies[].open_questions",
        "Open questions (closed questions for an expert; never answered here)",
        "reading",
        ("review.flags_for",),
        (DOSSIER, ("mcp", "questions")),
        reads=(f"{EL}.eligibilityCriteria",),
    ),
)

_RECORD_FIELDS: tuple[Field, ...] = (
    Field("schema_version", "Schema version", "run", ("contract.SCHEMA_VERSION",), (*ON_README, MANIFEST)),
    Field("request", "The search as requested", "run", ("request.request_problems",), (*ON_README, MANIFEST)),
    Field("scope", "The search as resolved", "run", ("request.resolve_scope",), ON_README),
    Field(
        "manifest.api_version",
        "Registry API version",
        "run",
        ("landscape.landscape_manifest",),
        (*ON_README, MANIFEST),
    ),
    Field(
        "manifest.data_timestamp",
        "Registry snapshot read",
        "run",
        ("landscape.landscape_manifest",),
        (*ON_README, MANIFEST),
    ),
    Field("manifest.study_digests", "Each study's digest", "run", ("warrants.study_digest",), (MANIFEST,)),
    Field("manifest.merkle_root", "The digests' Merkle root", "run", ("warrants.merkle_root",), (MANIFEST,)),
    Field(
        "manifest.code_commit", "The code's commit", "run", ("record.code_commit",), (*ON_README, MANIFEST)
    ),
    Field(
        "manifest.rule_versions",
        "Rule versions (schema, tool, design, code root, relations and their kinds, universes, display)",
        "run",
        ("landscape.RULE_VERSIONS",),
        (*ON_README, MANIFEST),
    ),
    Field(
        "manifest.retrieval",
        "How the registry was read (direct or relayed), how many studies matched and were read, and the "
        "requested-ID accounting",
        "run",
        ("operate.retrieval_coverage",),
        (*ON_README, MANIFEST),
    ),
    Field(
        "universes",
        "The universes and their rule packs, as run",
        "run",
        ("contract.UNIVERSES",),
        (*ON_README, MANIFEST),
    ),
    Field("coverage.universe", "The trials TrialLedger supports", "run", ("typematrix.UNIVERSE",), ON_README),
    Field(
        "cohort.thresholds",
        "The standard share and the signal minimums",
        "run",
        ("profile.STANDARD_SHARE",),
        (("sheet", FINDINGS, "Population and limits"),),
    ),
    *(
        Field(f"cohort.{name}", label, "reading", (rule,), (*ON_FINDINGS, ("mcp", "findings")))
        for name, label, rule in (
            ("frequency", "Criteria most trials share", "profile.frequency_rows"),
            ("mechanism_signals", "Exclusions that follow a drug's mechanism", "profile.mechanism_rows"),
            ("occupancy", "Setting and class combinations tried and untried", "profile.occupancy_rows"),
            (
                "near_misses",
                "Trials differing in one design choice, each with the status its settings rest on",
                "nearmiss.near_misses",
            ),
            ("aligned_near_misses", "Such pairs aligned by ATC class", "reading.aligned_near_miss_input"),
            ("endpoints", "Endpoints and time points across trials", "landscape.endpoint_profile"),
            ("structure_relations", "Drugs sharing a structure class", "reading.structure_relations"),
        )
    ),
    # standard protocol language: each criterion reading most trials of one universe state
    # (STANDARD_LANGUAGE_SHARE, STANDARD_LANGUAGE_MIN_TRIALS); a universe with too few trials, one row
    # saying so
    *(
        Field(
            f"standard_language[].{name}",
            label,
            "reading",
            ("landscape.standard_language",),
            (("sheet", STANDARD, column), ("mcp", "findings")),
            reads=(f"{EL}.eligibilityCriteria",),
        )
        for name, label, column in (
            ("criterion", "The criterion reading, and the universe its trials share", "Criterion"),
            ("role", "Its role (inclusion or exclusion)", "Role"),
            ("trials", "Trials stating it", "Trials stating it"),
            ("of_trials", "Of comparable trials (the universe's)", "Of comparable trials"),
            (
                "wording",
                "Representative wording: the shortest statement and a longer one",
                "Representative wording",
            ),
            ("wording_from", "Each wording's trial and criterion", "Wording from"),
            ("other_trials", "The other trials stating it", "Other trials"),
        )
    ),
    Field(
        "statuses",
        "What each status means",
        "run",
        ("landscape.STATUSES",),
        (*ON_README, ("sheet", REVIEW, "Basis"), ("mcp", "statuses")),
    ),
    Field(
        "envelope",
        "What each key of a reading's value object means",
        "run",
        ("landscape.ENVELOPE_MEANINGS",),
        (("mcp", "statuses"),),
    ),
    Field(
        "fields",
        "The field dictionary: every field's label, kind, API path or rule, once",
        "run",
        ("contract.FIELDS",),
        (
            ("mcp", "fields"),
            *ON_README,
            ("sheet", REVIEW, "Section"),
            ("sheet", REVIEW, "Fact"),
            ("sheet", DICTIONARY, "Sheet"),
            ("sheet", DICTIONARY, "Column"),
            ("sheet", DICTIONARY, "Registry field or rule"),
            ("sheet", DICTIONARY, "Definition"),
        ),
    ),
)

FIELDS: tuple[Field, ...] = (
    *(field._replace(consumers=(*field.consumers, STUDY)) for field in _STUDY_FIELDS),
    *_RECORD_FIELDS,
)
FIELD_NAMES: dict[str, Field] = {field.name: field for field in FIELDS}

# ── the workbook ────────────────────────────────────────────────────────────────────────────────────────
# A listing's key column is the row's address in the record; a blank cell only where the column cannot apply
# to the row by construction, and a value that could exist and does not, in words.

ADDRESS = "Address in the record"
# Fields several columns of one sheet show alike (a reading's row; a finding's row).
READ_ME_FIELDS = (
    "schema_version",
    "request",
    "scope",
    "manifest.api_version",
    "manifest.data_timestamp",
    "manifest.code_commit",
    "manifest.rule_versions",
    "manifest.retrieval",
    "universes",
    "coverage.universe",
    "statuses",
    "fields",
)
GROUPS_FIELDS = (
    "studies[].posted_outcomes[].groups[].id",
    "studies[].baseline.groups[].id",
    "studies[].participant_flow.groups[].id",
    "studies[].adverse_events.groups[].id",
)
ACROSS_TRIAL_FINDINGS_FIELDS = (
    "cohort.frequency",
    "cohort.mechanism_signals",
    "cohort.occupancy",
    "cohort.near_misses",
    "cohort.aligned_near_misses",
    "cohort.endpoints",
    "cohort.structure_relations",
)
READINGS_FIELDS = (
    "studies[].interventions[].drug_class",
    "studies[].interventions[].axes",
    "studies[].interventions[].modality",
    "studies[].eligibility.coverage",
    "studies[].criteria[].role",
    "studies[].criteria[].readings",
    "studies[].biomarker_mentions",
    "studies[].universe",
    "studies[].coordinates.setting",
    "studies[].coordinates.setting_interpolated",
    "studies[].coordinates.setting_proposed",
    "studies[].coordinates.prior_advanced_lines",
    "studies[].coordinates.prior_advanced_lines_interpolated",
    "studies[].coordinates.prior_advanced_lines_proposed",
    "studies[].coordinates.selection",
    "studies[].coordinates.selection_interpolated",
    "studies[].coordinates.selection_proposed",
    "studies[].registered_outcomes[].endpoint_classes",
    "studies[].registered_outcomes[].time_points",
    "studies[].posted_outcomes[].endpoint_classes",
)
SHEETS: tuple[Sheet, ...] = (
    Sheet(
        READ_ME,
        "topic",
        (
            Column("Topic", READ_ME_FIELDS),
            Column("Content", READ_ME_FIELDS),
        ),
    ),
    Sheet(
        INDEX,
        "trial",
        (
            Column("Trial ID", ("studies[].nct", "studies[].link")),
            Column("Acronym or short title", ("studies[].brief_title", "studies[].acronym")),
            Column("Sponsor", ("studies[].lead_sponsor.name", "studies[].lead_sponsor.class")),
            Column("Phase", ("studies[].phases",)),
            Column("Status", ("studies[].overall_status", "studies[].last_known_status")),
            Column("Conditions", ("studies[].conditions",)),
            Column("Universe", ("studies[].universe",)),
            Column(
                "Design",
                (
                    "studies[].primary_purpose",
                    "studies[].allocation",
                    "studies[].intervention_model",
                    "studies[].masking",
                    "studies[].who_masked",
                ),
            ),
            Column("Enrollment", ("studies[].enrollment.count", "studies[].enrollment.type")),
            Column("Start", ("studies[].start_date.date", "studies[].start_date.type")),
            Column(
                "Primary endpoint",
                ("studies[].registered_outcomes[].category", "studies[].registered_outcomes[].measure"),
            ),
            Column("Results posted", ("studies[].results_first_posted", "studies[].results_posted")),
            Column(
                "Publications",
                (
                    "studies[].references[].pmid",
                    "studies[].references[].type",
                ),
            ),
            Column("Countries", ("studies[].countries",)),
            Column("Last update posted", ("studies[].last_update_posted",)),
            Column(
                "Treatment setting",
                ("studies[].coordinates.setting", "studies[].coordinates.setting_interpolated"),
            ),
            Column(
                "Prior lines for advanced disease",
                (
                    "studies[].coordinates.prior_advanced_lines",
                    "studies[].coordinates.prior_advanced_lines_interpolated",
                ),
            ),
            Column(
                "Gene selection",
                ("studies[].coordinates.selection", "studies[].coordinates.selection_interpolated"),
            ),
            Column("Dossier", ("studies[].nct",)),
        ),
    ),
    Sheet(
        REVIEW,
        "trial × fact, in section bands (DOSSIER_SECTIONS)",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column("Section", ("fields",)),
            Column("Fact", ("fields",)),
            Column(
                "Value",
                (
                    "studies[].brief_title",
                    "studies[].acronym",
                    "studies[].official_title",
                    "studies[].org_study_id",
                    "studies[].secondary_ids[].id",
                    "studies[].secondary_ids[].type",
                    "studies[].secondary_ids[].domain",
                    "studies[].nct_aliases",
                    "studies[].overall_status",
                    "studies[].last_known_status",
                    "studies[].why_stopped",
                    "studies[].start_date.date",
                    "studies[].start_date.type",
                    "studies[].primary_completion_date.date",
                    "studies[].primary_completion_date.type",
                    "studies[].completion_date.date",
                    "studies[].completion_date.type",
                    "studies[].first_posted",
                    "studies[].results_first_posted",
                    "studies[].last_update_posted",
                    "studies[].lead_sponsor.name",
                    "studies[].lead_sponsor.class",
                    "studies[].collaborators[].name",
                    "studies[].collaborators[].class",
                    "studies[].dmc",
                    "studies[].officials[].name",
                    "studies[].officials[].affiliation",
                    "studies[].officials[].role",
                    "studies[].countries",
                    "studies[].site_count",
                    "studies[].brief_summary",
                    "studies[].detailed_description",
                    "studies[].conditions",
                    "studies[].condition_mesh",
                    "studies[].condition_mesh_ancestors",
                    "studies[].intervention_mesh",
                    "studies[].intervention_mesh_ancestors",
                    "studies[].phases",
                    "studies[].primary_purpose",
                    "studies[].allocation",
                    "studies[].intervention_model",
                    "studies[].intervention_model_description",
                    "studies[].masking",
                    "studies[].who_masked",
                    "studies[].masking_description",
                    "studies[].study_type",
                    "studies[].enrollment.count",
                    "studies[].enrollment.type",
                    "studies[].arms[].label",
                    "studies[].arms[].type",
                    "studies[].arms[].description",
                    "studies[].arms[].interventions",
                    "studies[].interventions[].type",
                    "studies[].interventions[].name",
                    "studies[].interventions[].description",
                    "studies[].interventions[].arms",
                    "studies[].interventions[].other_names",
                    "studies[].interventions[].drug_class",
                    "studies[].population.minimum_age",
                    "studies[].population.maximum_age",
                    "studies[].population.sex",
                    "studies[].population.age_groups",
                    "studies[].population.healthy_volunteers",
                    "studies[].population.gender_based",
                    "studies[].population.gender_description",
                    "studies[].key_criteria[].text",
                    "studies[].key_criteria[].role",
                    "studies[].key_criteria[].reading",
                    "studies[].key_criteria[].rule",
                    "studies[].universe",
                    "studies[].coordinates.setting",
                    "studies[].coordinates.setting_interpolated",
                    "studies[].coordinates.setting_proposed",
                    "studies[].coordinates.prior_advanced_lines",
                    "studies[].coordinates.prior_advanced_lines_interpolated",
                    "studies[].coordinates.prior_advanced_lines_proposed",
                    "studies[].coordinates.selection",
                    "studies[].coordinates.selection_interpolated",
                    "studies[].coordinates.selection_proposed",
                    "studies[].registered_outcomes[].category",
                    "studies[].registered_outcomes[].measure",
                    "studies[].registered_outcomes[].time_frame",
                    "studies[].results_posted",
                    "studies[].participant_flow.recruitment_details",
                    "studies[].participant_flow.pre_assignment_details",
                    "studies[].adverse_events.time_frame",
                    "studies[].adverse_events.frequency_threshold",
                    "studies[].adverse_events.description",
                    "studies[].adverse_events.all_cause_mortality_comment",
                    "studies[].limitations",
                    "studies[].references[].pmid",
                    "studies[].references[].type",
                    "studies[].references[].citation",
                    "studies[].references[].retractions[].pmid",
                    "studies[].references[].retractions[].source",
                    "studies[].links[].label",
                    "studies[].links[].url",
                    "studies[].ipd_documents[].type",
                    "studies[].ipd_documents[].url",
                    "studies[].ipd_documents[].comment",
                    "studies[].no_sap",
                    "studies[].documents[].type",
                    "studies[].documents[].label",
                    "studies[].documents[].date",
                    "studies[].documents[].url",
                    "studies[].open_questions",
                ),
            ),
            Column("Basis", ("statuses",)),
        ),
    ),
    Sheet(
        ELIGIBILITY,
        "criterion",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Heading", ("studies[].criteria[].heading",)),
            Column("Criterion number", ("studies[].criteria[].number",)),
            Column("Role", ("studies[].criteria[].role",)),
            Column("Criterion as written", ("studies[].criteria[].text",)),
            Column("Readings", ("studies[].criteria[].readings",)),
        ),
    ),
    Sheet(
        REGISTERED,
        "registered outcome",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Category", ("studies[].registered_outcomes[].category",)),
            Column("Measure", ("studies[].registered_outcomes[].measure",)),
            Column("Description", ("studies[].registered_outcomes[].description",)),
            Column("Time frame", ("studies[].registered_outcomes[].time_frame",)),
            Column("Endpoint reading", ("studies[].registered_outcomes[].endpoint_classes",)),
            Column("Time-point reading", ("studies[].registered_outcomes[].time_points",)),
        ),
    ),
    Sheet(
        POSTED,
        "measure × class × category × group",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Outcome type", ("studies[].posted_outcomes[].type",)),
            Column("Measure", ("studies[].posted_outcomes[].title",)),
            Column("Measure description", ("studies[].posted_outcomes[].description",)),
            Column("Analysis population", ("studies[].posted_outcomes[].population",)),
            Column(
                "Reporting status",
                (
                    "studies[].posted_outcomes[].reporting_status",
                    "studies[].posted_outcomes[].anticipated_posting_date",
                ),
            ),
            Column("Time frame", ("studies[].posted_outcomes[].time_frame",)),
            Column("Class", ("studies[].posted_outcomes[].classes[].title",)),
            Column("Category", ("studies[].posted_outcomes[].classes[].categories[].title",)),
            Column(
                "Group",
                (
                    "studies[].posted_outcomes[].groups[].title",
                    "studies[].posted_outcomes[].classes[].categories[].measurements[].group",
                ),
            ),
            Column(
                "Denominator",
                (
                    "studies[].posted_outcomes[].units_analyzed",
                    "studies[].posted_outcomes[].denominator_units",
                    "studies[].posted_outcomes[].denominators[].units",
                    "studies[].posted_outcomes[].denominators[].counts[].group",
                    "studies[].posted_outcomes[].denominators[].counts[].value",
                    "studies[].posted_outcomes[].classes[].denominators[].units",
                    "studies[].posted_outcomes[].classes[].denominators[].counts[].group",
                    "studies[].posted_outcomes[].classes[].denominators[].counts[].value",
                ),
            ),
            Column("Parameter", ("studies[].posted_outcomes[].param_type",)),
            Column("Value", ("studies[].posted_outcomes[].classes[].categories[].measurements[].value",)),
            Column(
                "Spread or limits",
                (
                    "studies[].posted_outcomes[].dispersion_type",
                    "studies[].posted_outcomes[].classes[].categories[].measurements[].spread",
                    "studies[].posted_outcomes[].classes[].categories[].measurements[].lower_limit",
                    "studies[].posted_outcomes[].classes[].categories[].measurements[].upper_limit",
                ),
            ),
            Column("Unit", ("studies[].posted_outcomes[].unit",)),
            Column("Comment", ("studies[].posted_outcomes[].classes[].categories[].measurements[].comment",)),
        ),
    ),
    Sheet(
        ANALYSES,
        "statistical analysis",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Measure", ("studies[].posted_outcomes[].title",)),
            Column(
                "Compared groups",
                (
                    "studies[].posted_outcomes[].analyses[].groups",
                    "studies[].posted_outcomes[].analyses[].group_description",
                ),
            ),
            Column(
                "Method",
                (
                    "studies[].posted_outcomes[].analyses[].method",
                    "studies[].posted_outcomes[].analyses[].method_comment",
                ),
            ),
            Column("Parameter", ("studies[].posted_outcomes[].analyses[].param_type",)),
            Column(
                "Estimate",
                (
                    "studies[].posted_outcomes[].analyses[].param_value",
                    "studies[].posted_outcomes[].analyses[].estimate_comment",
                    "studies[].posted_outcomes[].analyses[].dispersion_type",
                    "studies[].posted_outcomes[].analyses[].dispersion_value",
                ),
            ),
            Column(
                "Confidence interval",
                (
                    "studies[].posted_outcomes[].analyses[].ci_percent",
                    "studies[].posted_outcomes[].analyses[].ci_sides",
                    "studies[].posted_outcomes[].analyses[].ci_lower",
                    "studies[].posted_outcomes[].analyses[].ci_upper",
                    "studies[].posted_outcomes[].analyses[].ci_lower_comment",
                    "studies[].posted_outcomes[].analyses[].ci_upper_comment",
                ),
            ),
            Column(
                "P-value",
                (
                    "studies[].posted_outcomes[].analyses[].p_value",
                    "studies[].posted_outcomes[].analyses[].p_value_comment",
                ),
            ),
            Column(
                "Hypothesis",
                (
                    "studies[].posted_outcomes[].analyses[].hypothesis",
                    "studies[].posted_outcomes[].analyses[].hypothesis_comment",
                ),
            ),
            Column("Other analysis", ("studies[].posted_outcomes[].analyses[].other_description",)),
        ),
    ),
    Sheet(
        BASELINE,
        "characteristic × class × category × group",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column(
                "Characteristic",
                ("studies[].baseline.measures[].title", "studies[].baseline.measures[].description"),
            ),
            Column(
                "Population", ("studies[].baseline.population", "studies[].baseline.measures[].population")
            ),
            Column("Class", ("studies[].baseline.measures[].classes[].title",)),
            Column("Category", ("studies[].baseline.measures[].classes[].categories[].title",)),
            Column(
                "Group",
                (
                    "studies[].baseline.groups[].title",
                    "studies[].baseline.measures[].classes[].categories[].measurements[].group",
                ),
            ),
            Column(
                "Denominator",
                (
                    "studies[].baseline.units_analyzed",
                    "studies[].baseline.denominators[].units",
                    "studies[].baseline.denominators[].counts[].group",
                    "studies[].baseline.denominators[].counts[].value",
                    "studies[].baseline.measures[].denominators[].units",
                    "studies[].baseline.measures[].denominators[].counts[].group",
                    "studies[].baseline.measures[].denominators[].counts[].value",
                    "studies[].baseline.measures[].classes[].denominators[].units",
                    "studies[].baseline.measures[].classes[].denominators[].counts[].group",
                    "studies[].baseline.measures[].classes[].denominators[].counts[].value",
                    "studies[].baseline.measures[].denominator_units",
                ),
            ),
            Column("Parameter", ("studies[].baseline.measures[].param_type",)),
            Column("Value", ("studies[].baseline.measures[].classes[].categories[].measurements[].value",)),
            Column(
                "Spread or limits",
                (
                    "studies[].baseline.measures[].dispersion_type",
                    "studies[].baseline.measures[].classes[].categories[].measurements[].spread",
                    "studies[].baseline.measures[].classes[].categories[].measurements[].lower_limit",
                    "studies[].baseline.measures[].classes[].categories[].measurements[].upper_limit",
                ),
            ),
            Column("Unit", ("studies[].baseline.measures[].unit",)),
            Column(
                "Comment", ("studies[].baseline.measures[].classes[].categories[].measurements[].comment",)
            ),
        ),
    ),
    Sheet(
        FLOW,
        "period × milestone or reason × group",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Period", ("studies[].participant_flow.periods[].title",)),
            Column(
                "Milestone or reason",
                (
                    "studies[].participant_flow.periods[].milestones[].type",
                    "studies[].participant_flow.periods[].withdrawals[].reason",
                ),
            ),
            Column(
                "Group",
                (
                    "studies[].participant_flow.groups[].title",
                    "studies[].participant_flow.periods[].milestones[].counts[].group",
                    "studies[].participant_flow.periods[].withdrawals[].counts[].group",
                ),
            ),
            Column(
                "Participants",
                (
                    "studies[].participant_flow.units_analyzed",
                    "studies[].participant_flow.periods[].milestones[].counts[].participants",
                    "studies[].participant_flow.periods[].milestones[].counts[].units",
                    "studies[].participant_flow.periods[].withdrawals[].counts[].participants",
                ),
            ),
            Column(
                "Comment",
                (
                    "studies[].participant_flow.periods[].milestones[].comment",
                    "studies[].participant_flow.periods[].milestones[].counts[].comment",
                    "studies[].participant_flow.periods[].withdrawals[].comment",
                    "studies[].participant_flow.periods[].withdrawals[].counts[].comment",
                ),
            ),
        ),
    ),
    Sheet(
        GROUPS,
        "trial × module × group",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Module", GROUPS_FIELDS),
            Column("Group ID", GROUPS_FIELDS),
            Column("Column", GROUPS_FIELDS),
            Column(
                "Title",
                (
                    "studies[].posted_outcomes[].groups[].title",
                    "studies[].baseline.groups[].title",
                    "studies[].participant_flow.groups[].title",
                    "studies[].adverse_events.groups[].title",
                ),
            ),
            Column(
                "Description",
                (
                    "studies[].posted_outcomes[].groups[].description",
                    "studies[].baseline.groups[].description",
                    "studies[].participant_flow.groups[].description",
                    "studies[].adverse_events.groups[].description",
                ),
            ),
            Column(
                "Totals",
                (
                    "studies[].adverse_events.groups[].deaths_affected",
                    "studies[].adverse_events.groups[].deaths_at_risk",
                    "studies[].adverse_events.groups[].serious_affected",
                    "studies[].adverse_events.groups[].serious_at_risk",
                    "studies[].adverse_events.groups[].other_affected",
                    "studies[].adverse_events.groups[].other_at_risk",
                ),
            ),
        ),
    ),
    Sheet(
        SAFETY,
        "trial × table × term",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Table", ("studies[].adverse_events.events[].table",)),
            Column("Organ system", ("studies[].adverse_events.events[].organ_system",)),
            Column("Term", ("studies[].adverse_events.events[].term",)),
            Column(
                "G{n} affected",
                (
                    "studies[].adverse_events.events[].counts[].group",
                    "studies[].adverse_events.events[].counts[].affected",
                ),
                "per group",
            ),
            Column(
                "G{n} at risk",
                (
                    "studies[].adverse_events.events[].counts[].group",
                    "studies[].adverse_events.events[].counts[].at_risk",
                ),
                "per group",
            ),
            Column(
                "G{n} events",
                (
                    "studies[].adverse_events.events[].counts[].group",
                    "studies[].adverse_events.events[].counts[].events",
                ),
                "per group",
            ),
            Column("Vocabulary", ("studies[].adverse_events.events[].vocabulary",)),
            Column("Assessment", ("studies[].adverse_events.events[].assessment",)),
            Column("Notes", ("studies[].adverse_events.events[].notes",)),
        ),
    ),
    Sheet(
        BIOMARKERS,
        "biomarker mention",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Biomarker", ("studies[].biomarker_mentions",)),
            Column("States", ("studies[].biomarker_mentions",)),
            Column("Role", ("studies[].biomarker_mentions",)),
            Column("Words read", ("studies[].biomarker_mentions",)),
            Column("Rule", ("studies[].biomarker_mentions",)),
        ),
    ),
    Sheet(
        FINDINGS,
        "supported finding (below the signal minimum, one line: too few trials to assess)",
        (
            Column(ADDRESS, (), "address"),
            Column("Type", ACROSS_TRIAL_FINDINGS_FIELDS),
            Column("Finding", ACROSS_TRIAL_FINDINGS_FIELDS),
            Column("Trial IDs", ACROSS_TRIAL_FINDINGS_FIELDS),
            Column("Numerator / denominator", ACROSS_TRIAL_FINDINGS_FIELDS),
            Column(
                "Population and limits",
                (
                    "cohort.thresholds",
                    "cohort.frequency",
                    "cohort.mechanism_signals",
                    "cohort.occupancy",
                    "cohort.near_misses",
                    "cohort.aligned_near_misses",
                    "cohort.endpoints",
                    "cohort.structure_relations",
                ),
            ),
            Column("Rule", ACROSS_TRIAL_FINDINGS_FIELDS),
        ),
    ),
    Sheet(
        STANDARD,
        "criterion reading × universe (a universe with too few trials, one line saying so)",
        (
            Column(ADDRESS, (), "address"),
            *(
                Column(column, (f"standard_language[].{name}",))
                for name, column in (
                    ("criterion", "Criterion"),
                    ("role", "Role"),
                    ("trials", "Trials stating it"),
                    ("of_trials", "Of comparable trials"),
                    ("wording", "Representative wording"),
                    ("wording_from", "Wording from"),
                    ("other_trials", "Other trials"),
                )
            ),
        ),
    ),
    Sheet(
        READINGS,
        "rule reading",
        (
            Column("Trial ID", ("studies[].nct",)),
            Column(ADDRESS, (), "address"),
            Column("Field", READINGS_FIELDS),
            Column("Words read", READINGS_FIELDS),
            Column("Rule and version", READINGS_FIELDS),
            Column("Result", READINGS_FIELDS),
            Column("Status", READINGS_FIELDS),
        ),
    ),
    Sheet(
        DICTIONARY,
        "sheet × column",
        (
            Column("Sheet", ("fields",)),
            Column("Column", ("fields",)),
            Column("Registry field or rule", ("fields",)),
            Column("Definition", ("fields",)),
        ),
    ),
)

# The Read me, top to bottom: the search and what it found first; how to read the workbook; the statuses;
# what the registry does not report; the limit of a treatment setting or line; technical provenance last.
# Every topic is written in words, never as raw JSON.
READ_ME_TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("The search, in plain words", ("request", "scope")),
    ("What it found", ("manifest.retrieval",)),
    ("How to read this workbook", ("fields",)),
    ("What each status means", ("statuses",)),
    ("What the registry does not report", ("fields",)),
    (
        "Treatment setting and line",
        ("universes",),
    ),
    ("The trials TrialLedger supports", ("coverage.universe", "universes")),
    (
        "Technical provenance",
        (
            "schema_version",
            "manifest.api_version",
            "manifest.data_timestamp",
            "manifest.code_commit",
            "manifest.rule_versions",
        ),
    ),
)
# What the Read me says once, where a reader would look for a field the registry's API does not have.
NOT_REPORTED_BY_REGISTRY = (
    "an adverse event's grade (the registry's adverse-event tables report no grade)",
    "a visit or assessment schedule (a time frame is not a schedule)",
    "the cohort or arm a criterion applies to",
    "a biomarker's assay, specimen or timing",
    "the planning assumptions behind a sample size",
)
TREATMENT_CONTEXT_LIMIT = (
    "A treatment setting or line of therapy is the one the trial registered, read from its own words; it is "
    "never the trial's placement on today's standard of care."
)

# The dossier (Trial review), in bands: each band's heading, the listing it links to ("" for none) and the
# fields it shows, by name or by the prefix of their names. Every field the dossier shows is in one band.
DOSSIER_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Identification",
        "",
        (
            "studies[].brief_title",
            "studies[].acronym",
            "studies[].official_title",
            "studies[].org_study_id",
            "studies[].secondary_ids[].",
            "studies[].nct_aliases",
        ),
    ),
    (
        "Summary",
        "",
        ("studies[].brief_summary", "studies[].detailed_description"),
    ),
    (
        "Status and dates",
        "",
        (
            "studies[].overall_status",
            "studies[].last_known_status",
            "studies[].why_stopped",
            "studies[].start_date.",
            "studies[].primary_completion_date.",
            "studies[].completion_date.",
            "studies[].first_posted",
            "studies[].results_first_posted",
            "studies[].last_update_posted",
        ),
    ),
    (
        "Sponsor and oversight",
        "",
        (
            "studies[].lead_sponsor.",
            "studies[].collaborators[].",
            "studies[].officials[].",
            "studies[].dmc",
            "studies[].countries",
            "studies[].site_count",
        ),
    ),
    (
        "Purpose and design",
        "",
        (
            "studies[].study_type",
            "studies[].phases",
            "studies[].primary_purpose",
            "studies[].allocation",
            "studies[].intervention_model",
            "studies[].intervention_model_description",
            "studies[].masking",
            "studies[].who_masked",
            "studies[].masking_description",
            "studies[].enrollment.",
        ),
    ),
    ("Key criteria", ELIGIBILITY, ("studies[].key_criteria[].",)),
    (
        "Conditions and universe",
        READINGS,
        (
            "studies[].conditions",
            "studies[].condition_mesh",
            "studies[].condition_mesh_ancestors",
            "studies[].universe",
            "studies[].coordinates.",
        ),
    ),
    (
        "Population and eligibility",
        ELIGIBILITY,
        ("studies[].population.",),
    ),
    (
        "Arms and interventions",
        GROUPS,
        (
            "studies[].arms[].",
            "studies[].interventions[].",
            "studies[].intervention_mesh",
            "studies[].intervention_mesh_ancestors",
        ),
    ),
    ("Outcomes", REGISTERED, ("studies[].registered_outcomes[].",)),
    ("Results", POSTED, ("studies[].results_posted", "studies[].limitations")),
    ("Participant flow", FLOW, ("studies[].participant_flow.",)),
    ("Safety", SAFETY, ("studies[].adverse_events.",)),
    (
        "Publications and documents",
        "",
        (
            "studies[].references[].",
            "studies[].links[].",
            "studies[].ipd_documents[].",
            "studies[].no_sap",
            "studies[].documents[].",
        ),
    ),
    ("Open questions", "", ("studies[].open_questions",)),
)

# ── key criteria and standard protocol language (refine-landscape-record design §4a, task 1.8) ────────
# The categories of a key criterion: each its name, the words a reviewer reads, and the readings that fall in
# it, as (concept, values): a concept ending ":" matches every concept it begins (biomarker:EGFR), an empty
# values tuple any value, otherwise a reading falls in when one of its values is listed.
KEY_CRITERION_CATEGORIES: tuple[tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    ("performance_status", "Performance status", (("ecog_ps", ()),)),
    ("biomarker_selection", "Biomarker selection", (("biomarker:", ()),)),
    ("prior_therapy_and_line", "Prior therapy and line", (("prior_agent", ()), ("prior_lines", ()))),
    ("measurable_disease", "Measurable disease", (("condition", ("measurable_disease",)),)),
    ("organ_function", "Organ-function thresholds", (("lab", ()), ("condition", ("organ_impairment",)))),
    ("cns_metastases", "CNS metastases", (("condition", ("cns_metastases",)),)),
    (
        "autoimmune_and_immunosuppression",
        "Autoimmune disease and immunosuppression",
        (("condition", ("autoimmune_disease", "immunosuppression_steroids")),),
    ),
    ("hiv_and_hepatitis", "HIV, hepatitis B and C", (("condition", ("hiv", "hepatitis")),)),
    ("cardiac_history", "Cardiac history", (("condition", ("cardiac_disease", "qtc")),)),
)
# Standard protocol language: a criterion reading is standard within a universe when at least this share of
# the universe's trials state it and at least this many trials do; a universe with fewer trials has none.
STANDARD_LANGUAGE_SHARE = 0.5
STANDARD_LANGUAGE_MIN_TRIALS = 3

# ── what the record does not carry, and why ─────────────────────────────────────────────────────────────
# Every field of the API's metadata is carried (a plain field's path, or a path a reading reads) or named
# here, by its path or the path of the structure that holds it.

NOT_WANTED: dict[str, str] = {
    f"{ID}.orgStudyIdInfo.type": "the funding type of the sponsor's own number; the number is carried",
    f"{ID}.orgStudyIdInfo.link": "a system link to a funding database; the number is carried",
    f"{ID}.secondaryIdInfos[].link": "a system link to a funding database; the identifier is carried",
    f"{ID}.organization": "the registering account; the lead sponsor and collaborators are carried",
    f"{ST}.statusVerifiedDate": "the sponsor's verification of the record; the last update posted is carried",
    f"{ST}.delayedPosting": "a posting-delay flag for device trials",
    f"{ST}.expandedAccessInfo": "expanded-access availability, outside an interventional trial's record",
    f"{ST}.studyFirstSubmitDate": "a submission date (not wanted)",
    f"{ST}.studyFirstSubmitQcDate": "a quality-control date (not wanted)",
    f"{ST}.studyFirstPostDateStruct.type": "the type of a date the registry posted; the date is carried",
    f"{ST}.resultsWaived": "a waiver flag of the results submission process",
    f"{ST}.resultsFirstSubmitDate": "a submission date (not wanted)",
    f"{ST}.resultsFirstSubmitQcDate": "a quality-control date (not wanted)",
    f"{ST}.resultsFirstPostDateStruct.type": "the type of a date the registry posted; the date is carried",
    f"{ST}.dispFirstSubmitDate": "a disposition date (not wanted)",
    f"{ST}.dispFirstSubmitQcDate": "a disposition date (not wanted)",
    f"{ST}.dispFirstPostDateStruct": "a disposition date (not wanted)",
    f"{ST}.lastUpdateSubmitDate": "a submission date; the last update posted is carried",
    f"{ST}.lastUpdatePostDateStruct.type": "the type of a date the registry posted; the date is carried",
    f"{SP}.responsibleParty": "the responsible party (not wanted); the sponsor and the officials are carried",
    "protocolSection.oversightModule.isFdaRegulatedDrug": "a regulatory filing flag, not a design fact",
    "protocolSection.oversightModule.isFdaRegulatedDevice": "a regulatory filing flag, not a design fact",
    "protocolSection.oversightModule.isUnapprovedDevice": "a regulatory filing flag, not a design fact",
    "protocolSection.oversightModule.isPpsd": "a regulatory filing flag (pediatric postmarket surveillance)",
    "protocolSection.oversightModule.isUsExport": "an export flag (not wanted: export and violation flags)",
    "protocolSection.oversightModule.fdaaa801Violation": "a violation flag (not wanted)",
    "protocolSection.conditionsModule.keywords[]": "the sponsor's keywords (not wanted); conditions and MeSH "
    "terms are carried",
    f"{DS}.nPtrsToThisExpAccNctId": "a count of expanded-access records pointing here",
    f"{DS}.expandedAccessTypes": "expanded-access types, outside an interventional trial's record",
    f"{DS}.patientRegistry": "an observational patient-registry flag",
    f"{DS}.targetDuration": "an observational registry's follow-up duration",
    f"{DI}.observationalModel": "an observational design field; an interventional design is carried",
    f"{DI}.timePerspective": "an observational design field (not needed)",
    f"{DS}.bioSpec": "an observational study's specimen retention",
    f"{EL}.studyPopulation": "an observational study's population description",
    f"{EL}.samplingMethod": "an observational study's sampling method",
    f"{CL}.centralContacts[]": "contacts (not wanted: facility names and contacts)",
    f"{CL}.locations[].facility": "facility names (not wanted); countries and the site count are carried",
    f"{CL}.locations[].status": "a site's own recruitment status; the trial's status is carried",
    f"{CL}.locations[].city": "a site's city; countries and the site count are carried",
    f"{CL}.locations[].state": "a site's state; countries and the site count are carried",
    f"{CL}.locations[].zip": "a site's postal code",
    f"{CL}.locations[].contacts[]": "contacts (not wanted: facility names and contacts)",
    f"{CL}.locations[].geoPoint": "a site's map coordinates",
    f"{RF}.availIpds[].id": "the data set's own identifier; its type, link and comment are carried",
    "protocolSection.ipdSharingStatementModule": "the plan to share individual participant data (not wanted: "
    "IPD-sharing process details); data a sponsor has made available is carried",
    f"{OM}.calculatePct": "the registry's instruction to compute percentages; values are carried as posted",
    f"{BL}.measures[].calculatePct": "the registry's instruction to compute percentages; values are carried "
    "as posted",
    f"{OM}.analyses[].testedNonInferiority": "a legacy flag the hypothesis type replaces",
    "resultsSection.moreInfoModule.certainAgreement": "the investigators' publication agreement with the "
    "sponsor (not wanted)",
    "resultsSection.moreInfoModule.pointOfContact": "the results point of contact (not wanted: contacts)",
    "annotationSection": "the registry's annotations of unposted results and violations (not wanted: QC and "
    "violation records)",
    f"{LD}.largeDocs[].size": "document file sizes (not wanted)",
    f"{LD}.largeDocs[].hasProtocol": "restates the document's type, which is carried",
    f"{LD}.largeDocs[].hasSap": "restates the document's type, which is carried",
    f"{LD}.largeDocs[].hasIcf": "restates the document's type, which is carried",
    f"{LD}.largeDocs[].uploadDate": "the upload's date (not wanted); the document's own date is carried",
    f"{LD}.largeDocs[].filename": "the file's name; the document's link, built from it, is carried",
    "derivedSection.miscInfoModule": "the registry's version and submission tracking (not wanted: "
    "miscellaneous info)",
    f"{CB}.meshes[].id": "the MeSH descriptor's identifier; its term is carried and names it",
    f"{CB}.ancestors[].id": "the MeSH descriptor's identifier; its term is carried and names it",
    f"{CB}.browseLeaves[]": "the registry's browse index; the MeSH terms and ancestors are carried, "
    "and API v2 served no browse leaves in the baseline runs",
    f"{CB}.browseBranches[]": "the registry's browse branches; API v2 served none in the baseline runs",
    f"{IB}.meshes[].id": "the MeSH descriptor's identifier; its term is carried and names it",
    f"{IB}.ancestors[].id": "the MeSH descriptor's identifier; its term is carried and names it",
    f"{IB}.browseLeaves[]": "the registry's browse index; the MeSH terms and ancestors are carried, "
    "and API v2 served no browse leaves in the baseline runs",
    f"{IB}.browseBranches[]": "the registry's browse branches (pharmacological action); "
    "API v2 served none in the baseline runs (probed again 2026-11-01)",
}

# The contract's API paths that no saved baseline body holds, each carried all the same, with why. The gate
# holds this table to exactly the paths that do not resolve, so it can neither grow nor go stale unnoticed.
UNEXERCISED: dict[str, str] = {
    f"{EL}.genderDescription": "held only where eligibility is gender-based; the one such baseline trial "
    "describes nothing",
    f"{OM}.analyses[].dispersionType": "the estimate's dispersion, part of its estimate; "
    "no baseline analysis states one",
    f"{OM}.analyses[].dispersionValue": "the estimate's dispersion value; no baseline analysis states one",
    f"{OM}.analyses[].ciLowerLimitComment": "why a confidence limit is NA, as the registry keeps it; no "
    "baseline analysis has one",
    f"{OM}.analyses[].ciUpperLimitComment": "why a confidence limit is NA, as the registry keeps it; no "
    "baseline analysis has one",
    f"{BL}.typeUnitsAnalyzed": "baseline units other than participants (eyes, lesions); "
    "no baseline trial has them",
    f"{BL}.measures[].denomUnitsSelected": "a characteristic's own denominator units; "
    "no baseline trial states them",
    f"{BL}.measures[].denoms[].units": "a denominator at the characteristic's scope; "
    "the baseline trials give theirs at the module and class scopes",
    f"{BL}.measures[].denoms[].counts[].groupId": "a denominator at the characteristic's scope; the baseline "
    "trials give theirs at the module and class scopes",
    f"{BL}.measures[].denoms[].counts[].value": "a denominator at the characteristic's scope; the baseline "
    "trials give theirs at the module and class scopes",
    f"{FL}.typeUnitsAnalyzed": "flow units other than participants; no baseline trial has them",
    f"{FL}.periods[].milestones[].achievements[].numUnits": "flow counts of units other than participants; "
    "no baseline trial has them",
    f"{FL}.periods[].dropWithdraws[].comment": "a reason's comment; no baseline trial has one",
    f"{FL}.periods[].dropWithdraws[].reasons[].comment": "a comment on a reason's count; "
    "no baseline trial has one",
    f"{AE}.allCauseMortalityComment": "the all-cause mortality comment design §1 adds; no baseline trial "
    "posts one",
    f"{AE}.seriousEvents[].notes": "a serious event's notes; the baseline trials note only other events",
    f"{RF}.references[].retractions[].pmid": "a retraction notice for a cited publication; no baseline "
    "reference is retracted, and a reviewer must see one",
    f"{RF}.references[].retractions[].source": "a retraction notice for a cited publication; no baseline "
    "reference is retracted, and a reviewer must see one",
    f"{LD}.noSap": "the sponsor's statement that there is no statistical analysis plan; no baseline trial "
    "makes it",
}

# ── universes (the Regenesis port: a universe names the rule packs it owns; no rule outside it applies) ──


class Requirement(NamedTuple):
    """What a pack requires of a trial before its coordinates are computed: a kind (REQUIREMENT_KINDS) and
    the values that satisfy it."""

    kind: str
    values: tuple[str, ...]


class Pack(NamedTuple):
    """A rule pack: its name, label, the coherence coordinates it computes, the coherence relations it owns,
    and its requirements, all of which must hold."""

    name: str
    label: str
    coordinates: tuple[str, ...]
    relations: tuple[str, ...]
    requires: tuple[Requirement, ...]


class Universe(NamedTuple):
    """A universe: its name, label, version and the packs it owns."""

    name: str
    label: str
    version: str
    packs: tuple[Pack, ...]


UNIVERSE_TABLE_VERSION = "universes-1"
REQUIREMENT_KINDS = {
    "universe": "the trial is assigned to one of these universes (membership is not permission: each pack "
    "states the rest)",
    "primary_purpose": "the registry's primary purpose is one of these codes (the PrimaryPurpose enum)",
}
SELECTED_GENES = ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2")
NSCLC_RELATIONS = (
    "first_line_when_no_prior_advanced_therapy",
    "previously_treated_when_prior_advanced_therapy_required",
    "adjuvant_or_perioperative_when_resection_required",
    "neoadjuvant_or_perioperative_when_resectable_required",
    "advanced_when_metastatic_disease_required",
    "advanced_when_stage_iv_required",
    "consolidation_when_named",
)
TREATMENT = Requirement("primary_purpose", ("TREATMENT",))
UNIVERSES: tuple[Universe, ...] = (
    Universe(
        "oncology.solid",
        "Solid-tumour oncology",
        "1",
        (
            Pack(
                "setting_and_line",
                "Treatment setting and prior lines for advanced disease",
                ("setting", "prior_advanced_lines"),
                (),
                (Requirement("universe", ("oncology.solid",)), TREATMENT),
            ),
            Pack(
                "gene_selection",
                "Selection by a gene's state",
                tuple(f"selection:{gene}" for gene in SELECTED_GENES),
                (),
                (Requirement("universe", ("oncology.solid",)),),
            ),
            Pack(
                "nsclc_relations",
                "The setting relations of non-small cell lung cancer",
                (),
                NSCLC_RELATIONS,
                (Requirement("universe", ("oncology.solid",)), TREATMENT),
            ),
        ),
    ),
    Universe(
        "oncology.heme",
        "Haematologic oncology",
        "1",
        (
            Pack(
                "prior_lines",
                "Prior lines of therapy",
                ("prior_advanced_lines",),
                (),
                (Requirement("universe", ("oncology.heme",)), TREATMENT),
            ),
        ),
    ),
    Universe("general", "General: no domain readings apply", "1", ()),
)
# Coordinates a pack computes that coherence.py does not hold yet: none in this version.
NEW_COORDINATES: tuple[str, ...] = ()

# The three sources the assignment reads, in order, each recorded with what it found.
ASSIGNMENT_SOURCES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "condition_mesh",
        "the condition MeSH terms and their ancestors",
        (f"{CB}.meshes[].term", f"{CB}.ancestors[].term"),
    ),
    (
        "free_text",
        "the free-text conditions and the titles, matched against the declared vocabulary",
        ("protocolSection.conditionsModule.conditions[]", f"{ID}.briefTitle", f"{ID}.officialTitle"),
    ),
    (
        "drug_class",
        "for a treatment trial, its drugs' ATC classes as RxNav gives them for the intervention's name and "
        "other names (antineoplastic agents, L01; endocrine therapy, L02); in relay mode not looked up",
        (f"{AI}.interventions[].name", f"{AI}.interventions[].otherNames[]", f"{DI}.primaryPurpose"),
    ),
)
# How the sources decide, in order (the rule unit B builds as universes.assign).
ASSIGNMENT_CASES: tuple[tuple[str, str], ...] = (
    (
        "oncology",
        "a condition source (the condition MeSH terms or the free-text conditions) finds an oncology signal; "
        "or only the titles or a drug's class do, and no condition is positively outside oncology: each "
        "oncology universe a source names (several: the union, each reading tagged with its pack)",
    ),
    (
        "general",
        "positive evidence of a non-oncology domain (a condition MeSH term, or a free-text condition that is "
        "a disease) and no oncology signal from any source",
    ),
    (
        "unresolved",
        "no usable condition (no condition MeSH term, and every free-text condition empty or in "
        "NOT_DISEASE_CONDITIONS) and no oncology signal; or the sources disagree (the conditions are "
        "positively outside oncology while only the titles or a drug's class signal it): "
        "each source's finding shown",
    ),
)
# Words of the oncology vocabulary, each with how it matches a word of the text (TERM_MATCHES),
# case-insensitively; HAEMATOLOGIC_TERMS name the haematologic universe, the rest solid tumours.
TERM_MATCHES = {
    "word": "the whole word",
    "prefix": "a word beginning with it",
    "within": "anywhere within a word",
}
ONCOLOGY_TERMS: tuple[tuple[str, str], ...] = (
    ("neoplasm", "prefix"),
    ("cancer", "prefix"),
    ("carcinoma", "within"),
    ("tumour", "prefix"),
    ("tumor", "prefix"),
    ("lymphoma", "within"),
    ("leukaemia", "within"),
    ("leukemia", "within"),
    ("myeloma", "within"),
    ("sarcoma", "within"),
    ("malignan", "prefix"),
    ("NSCLC", "word"),
    ("SCLC", "word"),
    ("melanoma", "within"),
    ("glioma", "within"),
    ("blastoma", "within"),
    ("mesothelioma", "within"),
)
HAEMATOLOGIC_TERMS = ("lymphoma", "leukaemia", "leukemia", "myeloma")
# Free-text conditions that name no disease (an outcome, a treatment, a biomarker, a drug), as the baseline
# trials write them; matched whole, case-insensitively. Such a condition is no evidence of any domain.
NOT_DISEASE_CONDITIONS: tuple[tuple[str, str], ...] = (
    ("Progression Free Survival", "an outcome"),
    ("Overall Survival", "an outcome"),
    ("Anticancer Treatment", "a treatment"),
    ("c-MET", "a biomarker"),
    ("MET Positive", "a biomarker"),
    ("EGFR Activating Mutation", "a biomarker"),
    ("EGFR Gene Mutation", "a biomarker"),
    ("EGFR-TKI Resistant Mutation", "a biomarker"),
    ("AZD9291", "a drug"),
)
# Anchors: a condition MeSH term at or under which the source's terms fall, or the ATC class a drug's ATC
# code begins with. The registry's intervention MeSH ancestors are the MeSH structure tree (Quinazolines,
# Heterocyclic Compounds, ...); pharmacological action came in the browse branches, which API v2 did not
# serve in the baseline runs nor when probed on 2026-11-01, so a drug's class is read from RxNav's ATC answer.
# A solid-tumour anchor that names no kind of tumour (universes.UNSPECIFIC_ANCHORS: Neoplasms, an ATC class)
# counts as haematologic where a haematologic anchor holds.
MESH_ANCHORS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "oncology.heme",
        "condition_mesh",
        ("Hematologic Neoplasms", "Lymphoma", "Leukemia", "Multiple Myeloma"),
    ),
    ("oncology.solid", "condition_mesh", ("Neoplasms",)),
    ("oncology.solid", "drug_class", ("L01", "L02")),
)
# Anchors no saved baseline body holds, each with why; the gate holds this table to exactly those.
UNOBSERVED_ANCHORS: dict[str, str] = {
    "Hematologic Neoplasms": "the baseline's lymphoma and leukaemia trial reaches Lymphoma and Leukemia, not "
    "this term",
    "Multiple Myeloma": "no baseline trial is in myeloma",
    "L01": "an ATC class (antineoplastic agents), held by RxNav's answer for a drug's name (the run's "
    "classes.json), never by the registry's body",
    "L02": "an ATC class (endocrine therapy for cancer), held by RxNav's answer for a drug's name, never by "
    "the registry's body",
}

# ── the clinical words for the registry's codes ─────────────────────────────────────────────────────────
# From the API's enum table (GET /api/v2/studies/enums, fetched 2026-11-01, the same bytes as
# TrialLedger/registry/ctg-enums.json): its legacy words in sentence case, the API's exceptions honoured (an
# ESTIMATED start, completion or enrollment reads "Anticipated"), "N/A" written as "Not applicable", and the
# codes the API gives no words for (AgencyClass) written out. FlowMilestone and LargeDocType are the
# registry's fixed values of text fields, not enums of the API; their sources say so.

DISPLAY_VERSION = "display-1"
DISPLAY: dict[str, dict[str, str]] = {
    "Phase": {
        "NA": "Not applicable",
        "EARLY_PHASE1": "Early phase 1",
        "PHASE1": "Phase 1",
        "PHASE2": "Phase 2",
        "PHASE3": "Phase 3",
        "PHASE4": "Phase 4",
    },
    "Status": {
        "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
        "COMPLETED": "Completed",
        "ENROLLING_BY_INVITATION": "Enrolling by invitation",
        "NOT_YET_RECRUITING": "Not yet recruiting",
        "RECRUITING": "Recruiting",
        "SUSPENDED": "Suspended",
        "TERMINATED": "Terminated",
        "WITHDRAWN": "Withdrawn",
        "AVAILABLE": "Available",
        "NO_LONGER_AVAILABLE": "No longer available",
        "TEMPORARILY_NOT_AVAILABLE": "Temporarily not available",
        "APPROVED_FOR_MARKETING": "Approved for marketing",
        "WITHHELD": "Withheld",
        "UNKNOWN": "Unknown status",
    },
    "StudyType": {
        "EXPANDED_ACCESS": "Expanded access",
        "INTERVENTIONAL": "Interventional",
        "OBSERVATIONAL": "Observational",
    },
    "DateType": {"ACTUAL": "Actual", "ESTIMATED": "Anticipated"},
    "EnrollmentType": {"ACTUAL": "Actual", "ESTIMATED": "Anticipated"},
    "AgencyClass": {
        "NIH": "NIH",
        "FED": "US federal government",
        "OTHER_GOV": "Other government",
        "INDIV": "Individual",
        "INDUSTRY": "Industry",
        "NETWORK": "Network",
        "AMBIG": "Ambiguous",
        "OTHER": "Other",
        "UNKNOWN": "Unknown",
    },
    "SecondaryIdType": {
        "NIH": "US NIH grant/contract",
        "FDA": "US FDA grant/contract",
        "VA": "US VA grant/contract",
        "CDC": "US CDC grant/contract",
        "AHRQ": "US AHRQ grant/contract",
        "SAMHSA": "US SAMHSA grant/contract",
        "OTHER_GRANT": "Other grant/funding number",
        "EUDRACT_NUMBER": "EudraCT number",
        "CTIS": "EU trial (CTIS) number",
        "REGISTRY": "Registry identifier",
        "OTHER": "Other identifier",
    },
    "DesignAllocation": {
        "RANDOMIZED": "Randomized",
        "NON_RANDOMIZED": "Non-randomized",
        "NA": "Not applicable",
    },
    "InterventionalAssignment": {
        "SINGLE_GROUP": "Single group assignment",
        "PARALLEL": "Parallel assignment",
        "CROSSOVER": "Crossover assignment",
        "FACTORIAL": "Factorial assignment",
        "SEQUENTIAL": "Sequential assignment",
    },
    "PrimaryPurpose": {
        "TREATMENT": "Treatment",
        "PREVENTION": "Prevention",
        "DIAGNOSTIC": "Diagnostic",
        "ECT": "Educational/counseling/training",
        "SUPPORTIVE_CARE": "Supportive care",
        "SCREENING": "Screening",
        "HEALTH_SERVICES_RESEARCH": "Health services research",
        "BASIC_SCIENCE": "Basic science",
        "DEVICE_FEASIBILITY": "Device feasibility",
        "OTHER": "Other",
    },
    "DesignMasking": {
        "NONE": "None (open label)",
        "SINGLE": "Single",
        "DOUBLE": "Double",
        "TRIPLE": "Triple",
        "QUADRUPLE": "Quadruple",
    },
    "WhoMasked": {
        "PARTICIPANT": "Participant",
        "CARE_PROVIDER": "Care provider",
        "INVESTIGATOR": "Investigator",
        "OUTCOMES_ASSESSOR": "Outcomes assessor",
    },
    "ArmGroupType": {
        "EXPERIMENTAL": "Experimental",
        "ACTIVE_COMPARATOR": "Active comparator",
        "PLACEBO_COMPARATOR": "Placebo comparator",
        "SHAM_COMPARATOR": "Sham comparator",
        "NO_INTERVENTION": "No intervention",
        "OTHER": "Other",
    },
    "InterventionType": {
        "BEHAVIORAL": "Behavioral",
        "BIOLOGICAL": "Biological",
        "COMBINATION_PRODUCT": "Combination product",
        "DEVICE": "Device",
        "DIAGNOSTIC_TEST": "Diagnostic test",
        "DIETARY_SUPPLEMENT": "Dietary supplement",
        "DRUG": "Drug",
        "GENETIC": "Genetic",
        "PROCEDURE": "Procedure",
        "RADIATION": "Radiation",
        "OTHER": "Other",
    },
    "Sex": {"FEMALE": "Female", "MALE": "Male", "ALL": "All"},
    "StandardAge": {"CHILD": "Child", "ADULT": "Adult", "OLDER_ADULT": "Older adult"},
    "OfficialRole": {
        "STUDY_CHAIR": "Study chair",
        "STUDY_DIRECTOR": "Study director",
        "PRINCIPAL_INVESTIGATOR": "Principal investigator",
        "SUB_INVESTIGATOR": "Sub-investigator",
    },
    "ReferenceType": {"BACKGROUND": "Background", "RESULT": "Result", "DERIVED": "Derived"},
    "OutcomeMeasureType": {
        "PRIMARY": "Primary",
        "SECONDARY": "Secondary",
        "OTHER_PRE_SPECIFIED": "Other pre-specified",
        "POST_HOC": "Post hoc",
    },
    "ReportingStatus": {"NOT_POSTED": "Not posted", "POSTED": "Posted"},
    "MeasureParam": {
        "GEOMETRIC_MEAN": "Geometric mean",
        "GEOMETRIC_LEAST_SQUARES_MEAN": "Geometric least squares mean",
        "LEAST_SQUARES_MEAN": "Least squares mean",
        "LOG_MEAN": "Log mean",
        "MEAN": "Mean",
        "MEDIAN": "Median",
        "NUMBER": "Number",
        "COUNT_OF_PARTICIPANTS": "Count of participants",
        "COUNT_OF_UNITS": "Count of units",
    },
    "MeasureDispersionType": {
        "NA": "Not applicable",
        "STANDARD_DEVIATION": "Standard deviation",
        "STANDARD_ERROR": "Standard error",
        "INTER_QUARTILE_RANGE": "Inter-quartile range",
        "FULL_RANGE": "Full range",
        "CONFIDENCE_80": "80% confidence interval",
        "CONFIDENCE_90": "90% confidence interval",
        "CONFIDENCE_95": "95% confidence interval",
        "CONFIDENCE_975": "97.5% confidence interval",
        "CONFIDENCE_99": "99% confidence interval",
        "CONFIDENCE_OTHER": "Other confidence interval level",
        "GEOMETRIC_COEFFICIENT": "Geometric coefficient of variation",
    },
    "AnalysisDispersionType": {
        "STANDARD_DEVIATION": "Standard deviation",
        "STANDARD_ERROR_OF_MEAN": "Standard error of the mean",
    },
    "ConfidenceIntervalNumSides": {"ONE_SIDED": "1-sided", "TWO_SIDED": "2-sided"},
    "NonInferiorityType": {
        "SUPERIORITY": "Superiority",
        "NON_INFERIORITY": "Non-inferiority",
        "EQUIVALENCE": "Equivalence",
        "OTHER": "Other",
        "NON_INFERIORITY_OR_EQUIVALENCE": "Non-inferiority or equivalence",
        "SUPERIORITY_OR_OTHER": "Superiority or other",
        "NON_INFERIORITY_OR_EQUIVALENCE_LEGACY": "Non-inferiority or equivalence (legacy)",
        "SUPERIORITY_OR_OTHER_LEGACY": "Superiority or other (legacy)",
    },
    "EventAssessment": {
        "NON_SYSTEMATIC_ASSESSMENT": "Non-systematic assessment",
        "SYSTEMATIC_ASSESSMENT": "Systematic assessment",
    },
    "FlowMilestone": {"STARTED": "Started", "COMPLETED": "Completed", "NOT COMPLETED": "Not completed"},
    "LargeDocType": {
        "Prot": "Protocol",
        "SAP": "Statistical analysis plan",
        "ICF": "Informed consent form",
        "Prot_SAP": "Protocol and statistical analysis plan",
        "Prot_ICF": "Protocol and informed consent form",
        "SAP_ICF": "Statistical analysis plan and informed consent form",
        "Prot_SAP_ICF": "Protocol, statistical analysis plan and informed consent form",
    },
}
# The dictionaries that are not enums of the API, each with its source.
DISPLAY_NOT_API_ENUMS = {
    "FlowMilestone": "the registry's three fixed milestones of a participant-flow period (the sponsor's own "
    "milestones are shown as written)",
    "LargeDocType": "the registry's document type abbreviations (typeAbbrev), one document or several in one "
    "file",
}

# ── the helpers: a path template resolved in a study body, and a code's words ─────────────────────────


def template_values(body: Any, template: str) -> list[Any]:
    """Every value a study body holds at an API path template, in the body's order (pure — pinned).

    `template` is dotted; a segment ending in "[]" names a list whose elements are each followed. A segment
    the body does not hold, or a "[]" segment that is not a list, contributes nothing; a value held is
    returned as held, None and empty values among them.
    """
    nodes = [body]
    for segment in template.split("."):
        name = segment.removesuffix("[]")
        following: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict) or name not in node:
                continue
            held = node[name]
            if segment.endswith("[]"):
                following.extend(held if isinstance(held, list) else [])
            else:
                following.append(held)
        nodes = following
    return nodes


def holds_value(value: Any) -> bool:
    """Whether a value is held: anything but None, an empty string, list or object (pure — pinned).

    Zero and False are values: a listed zero and "no data monitoring committee" are held."""
    if value is None:
        return False
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    return True


def resolves(body: Any, template: str) -> bool:
    """Whether a study body holds a value at an API path template (pure — pinned)."""
    return any(holds_value(value) for value in template_values(body, template))


def display_words(dictionary: str, code: Any) -> tuple[str, str]:
    """A registry code in clinical words, through DISPLAY (pure — pinned).

    ok                — (ok, its words);
    not_in_dictionary — the dictionary holds no such code: (not_in_dictionary, the code as written);
    no_dictionary     — DISPLAY has no such dictionary: (no_dictionary, the code as written).
    A code that is not a string is in no dictionary.
    """
    words = DISPLAY.get(dictionary)
    if words is None:
        return "no_dictionary", str(code)
    if not isinstance(code, str) or code not in words:
        return "not_in_dictionary", str(code)
    return "ok", words[code]
