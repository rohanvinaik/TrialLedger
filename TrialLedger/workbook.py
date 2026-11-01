"""The review workbook: the ledger projected onto a trial designer's questions (openspec add-review-workbook).

Every sheet is derived from the record being written, `studies.json`'s content, and nothing else. Every cell
is a Fact: the value shown and its warrant (TrialLedger/warrants.py), which commits to the record bytes and
the rule code that rendered it. Values are shown as the record holds them; a field the record does not hold
is named by its absence state; a computed value names its rule; a value that needs review is marked and never
filled. The record workbook's Record sheets present every value of every study, under the registry's own
category and field names; the review workbook holds the design sheets and the checks. After writing, each
workbook is read back cell by cell and every row warrant re-derived; any difference refuses the write.
"""

from __future__ import annotations

import math
import posixpath
import re
import tempfile
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font

from TrialLedger import __version__, registry, warrants
from TrialLedger.cells import FORBIDDEN_CHARACTERS, cell_number_state, cell_text_state, sheet_fits
from TrialLedger.checks import (
    CHECKS,
    CHECKS_VERSION,
    DECISIONS,
    GATHERERS,
    INTERVENTION_TYPE_LABELS,
    READS,
    at_risk,
    run_checks,
)
from TrialLedger.eligibility import split_eligibility
from TrialLedger.ledger import (
    ABSENCE_TEXT,
    absence_state,
    as_list,
    entries,
    field_state,
    get,
    location,
    results_state,
)
from TrialLedger.links import document_link, pubmed_link, reference_role, study_link

WORKBOOK_NAME = "review.xlsx"
RECORD_NAME = "record.xlsx"
NO_RESULTS = "no results posted"
WARRANT_HEADER = "Warrant"
# The root of the code and registry tables this derivation reads (warrants.derivation_files), which every
# rule's warrant commits to; and the writer whose output the file comparison re-derives.
CODE_ROOT = warrants.code_root(Path(__file__).parent)
WRITER = f"openpyxl {openpyxl.__version__} ({'lxml' if openpyxl.LXML else 'etree'} serializer)"
RESULTS_TEXT = {
    "posted": "results posted",
    "not_posted": NO_RESULTS,
    "flag_without_results": "the registry flags results as posted, but this record holds no results section",
    "results_without_flag": "this record holds a results section, but the registry's results flag is false",
    "flag_not_reported": "the results flag is not reported",
}
NEEDS_REVIEW_LINE = "needs review: not a structured field; read the eligibility text in this row"
NEEDS_REVIEW_BIOMARKERS = (
    "needs review: no structured biomarker field; see the Outcomes and Eligibility sheets"
)
CELL_REASONS = {
    "forbidden_characters": "characters a spreadsheet file cannot hold",
    "carriage_return": "a carriage return, which a spreadsheet would turn into a line feed",
    "too_long": "more characters than a spreadsheet cell holds (32,767)",
    "not_exact": "a number a spreadsheet cell cannot hold exactly",
}
NCT_LOCATION = "protocolSection.identificationModule.nctId"
P = "protocolSection"
R = "resultsSection"


class WorkbookError(Exception):
    """Why the workbook could not be written exactly. When raised inside a pull, nothing is written."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Fact:
    """One cell: the value shown, the warrant committing to its basis, a link where it has one, and where in
    studies.json the value comes from (empty for TrialLedger's own text)."""

    value: Any
    warrant: str
    url: str = ""
    where: str = ""


@dataclass(frozen=True)
class Column:
    header: str
    kind: str
    source: str


def stated_column(header: str, source: str) -> Column:
    return Column(header, "stated", source)


def computed_column(header: str, rule: str) -> Column:
    return Column(header, "computed", rule)


def literal(value: Any, where: str = "") -> Fact:
    return Fact(value, warrants.literal(str(value)), where=where)


# ── the rules a cell can be computed by, each committed to its code and the registry data it reads ─────


def _text(item: Any) -> str:
    return item if isinstance(item, str) else str(item)


def _shown(value: Any) -> Any:
    """How a field's value is shown: a list one item per line, each item exactly as the record holds it."""
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value) if value else "(empty list)"
    if isinstance(value, dict):
        return "(object; see the Record sheet)"
    return value


def _registry_form(kind: Any, name: Any) -> str:
    """'<type label>: <name>', the form the registry's arms name an intervention by; a part the record does
    not state is named as not reported, and a type outside the registry's table is shown as written."""
    label = INTERVENTION_TYPE_LABELS.get(kind) if isinstance(kind, str) else None
    if label is None:
        label = "type not reported" if kind is None else f"type {kind!r} (not a registry type)"
    return f"{label}: {name if name is not None else 'name not reported'}"


def _group_titles(module: Any) -> dict[Any, Any]:
    return {get(group, "id"): get(group, "title") for group in as_list(get(module, "groups"))}


def _analyzed(measure: Any) -> dict[Any, list[str]]:
    """Per group, '<units>: <count>' for every denominator a posted measure gives."""
    analyzed: dict[Any, list[str]] = {}
    for denom in as_list(get(measure, "denoms")):
        for count in as_list(get(denom, "counts")):
            analyzed.setdefault(get(count, "groupId"), []).append(
                f"{get(denom, 'units')}: {get(count, 'value')}"
            )
    return analyzed


def _publications(study: dict[str, Any]) -> str:
    """The record's references, one per line: '<type>: PMID <pmid>', or the citation if there is no PMID."""
    refs = as_list(get(study, P, "referencesModule", "references"))
    if not refs:
        return "no publications in the record"
    lines = []
    for ref in refs:
        kind = get(ref, "type") or "type not reported"
        pmid = get(ref, "pmid")
        lines.append(f"{kind}: PMID {pmid}" if pmid else f"{kind}: {get(ref, 'citation') or 'no citation'}")
    return "\n".join(lines)


def _check_counts(study: dict[str, Any]) -> Counter[str]:
    """How many approved checks gave each outcome for one study."""
    return Counter(result.outcome for result in run_checks(study))


def _reference_counts(study: dict[str, Any]) -> Any:
    """The record's references counted by type, one '<type>: <n>' per line, or 0."""
    counts = Counter(get(ref, "type") for ref in as_list(get(study, P, "referencesModule", "references")))
    return "\n".join(f"{kind}: {n}" for kind, n in sorted(counts.items(), key=str)) if counts else 0


def _document_count(study: dict[str, Any]) -> int:
    """How many documents the sponsor posted."""
    return len(as_list(get(study, "documentSection", "largeDocumentModule", "largeDocs")))


def _rule(name: str, *functions: Callable[..., Any], data: tuple[str, ...] = ()) -> str:
    return warrants.rule(name, __version__, CODE_ROOT, warrants.code_digest(*functions), *data)


RULE: dict[str, str] = {
    "absence_state": _rule("absence_state", absence_state, field_state, data=(registry.METADATA_DIGEST,)),
    "list_lines": _rule("list_lines", _shown),
    "results_state": _rule("results_state", results_state),
    "split_eligibility": _rule("split_eligibility", split_eligibility),
    "at_risk": _rule("at_risk", at_risk),
    "study_link": _rule("study_link", study_link),
    "pubmed_link": _rule("pubmed_link", pubmed_link),
    "document_link": _rule("document_link", document_link),
    "reference_role": _rule("reference_role", reference_role),
    "registry_form": _rule("registry_form", _registry_form, data=(registry.ENUMS_DIGEST,)),
    "group_title": _rule("group_title", _group_titles),
    "analyzed": _rule("analyzed", _analyzed),
    "publications": _rule("publications", _publications),
    "check_counts": _rule("check_counts", _check_counts, run_checks),
    "reference_counts": _rule("reference_counts", _reference_counts),
    "document_count": _rule("document_count", _document_count),
    "registry_names": _rule(
        "registry_names", registry.category, registry.title, data=(registry.METADATA_DIGEST,)
    ),
    **{check.id: _rule(check.id, *DECISIONS[check.id], GATHERERS[check.id], run_checks) for check in CHECKS},
}


# ── one study, as the projection reads it ───────────────────────────────────────────────────────────


class Ctx:
    """One study: its record, its digest, and the facts the projection reads from it."""

    __slots__ = ("digest", "nct", "study")

    def __init__(self, study: dict[str, Any]) -> None:
        self.study = study
        self.digest = warrants.study_digest(study)
        self.nct = _text(get(study, P, "identificationModule", "nctId"))

    def field(self, *keys: str | int) -> Fact:
        """A field as the record holds it, or its absence state; warranted either way."""
        value = get(self.study, *keys)
        where = location(keys)
        if value is None:
            state = field_state(self.study, *keys)
            return Fact(
                ABSENCE_TEXT[state],
                warrants.computed(RULE["absence_state"], warrants.absent(self.digest, where, state)),
            )
        warrant = warrants.stated(self.digest, where, value)
        here = f"{where} of this row's study"
        if isinstance(value, list):
            return Fact(_shown(value), warrants.computed(RULE["list_lines"], warrant), where=here)
        return Fact(_shown(value), warrant, where=here)

    def nct_cell(self) -> Fact:
        fact = self.field(P, "identificationModule", "nctId")
        code, url = study_link(self.nct)
        if code != "ok":
            return fact
        return Fact(fact.value, warrants.computed(RULE["study_link"], fact.warrant), url, fact.where)

    def computed(self, rule_name: str, value: Any, *inputs: Fact) -> Fact:
        warrant = warrants.computed(RULE[rule_name], *(fact.warrant for fact in inputs))
        return Fact(value, warrant, where="; ".join(dict.fromkeys(f.where for f in inputs if f.where)))

    def whole(self, rule_name: str, value: Any) -> Fact:
        """A value computed from the whole study record by a named rule."""
        warrant = warrants.computed(RULE[rule_name], self.digest)
        return Fact(value, warrant, where="the whole record of this row's study")

    def checked(self, check_id: str, value: Any) -> Fact:
        """A check's outcome or detail, computed from the fields the check reads (checks.READS)."""
        warrant = warrants.computed(RULE[check_id], self.digest)
        return Fact(value, warrant, where="; ".join(READS[check_id]) + " of this row's study")

    def review(self, reason: str, *sources: Fact) -> Fact:
        return Fact(reason, warrants.review(reason, *(fact.warrant for fact in sources)))

    def results(self) -> tuple[str, Fact]:
        state = results_state(self.study.get("hasResults"), isinstance(self.study.get(R), dict))
        return state, self.computed("results_state", RESULTS_TEXT[state], self.field("hasResults"))


def _terms(ctx: Ctx, *keys: str) -> Fact:
    """The `term` of every item of a MeSH list, one per line."""
    if get(ctx.study, *keys) is None:
        return ctx.field(*keys)
    items = as_list(get(ctx.study, *keys))
    facts = [ctx.field(*keys, index, "term") for index in range(len(items))]
    return ctx.computed(
        "list_lines", "\n".join(_text(f.value) for f in facts) if facts else "(empty list)", *facts
    )


# ── the sheets ────────────────────────────────────────────────────────────────────────────────────────

Rows = Iterator[list[Fact]]


def _study_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        study = ctx.study
        status = (P, "statusModule")
        design = (P, "designModule")
        info = (*design, "designInfo")
        eligibility = (P, "eligibilityModule")
        interventions = as_list(get(study, P, "armsInterventionsModule", "interventions"))
        if interventions:
            parts = [
                (
                    ctx.field(P, "armsInterventionsModule", "interventions", i, "type"),
                    ctx.field(P, "armsInterventionsModule", "interventions", i, "name"),
                )
                for i in range(len(interventions))
            ]
            declared = ctx.computed(
                "registry_form",
                "\n".join(_registry_form(get(item, "type"), get(item, "name")) for item in interventions),
                *(fact for pair in parts for fact in pair),
            )
        else:
            declared = ctx.field(P, "armsInterventionsModule", "interventions")
        collaborators = as_list(get(study, P, "sponsorCollaboratorsModule", "collaborators"))
        collaborator_fact = (
            ctx.computed(
                "list_lines",
                "\n".join(f"{get(c, 'name')} ({get(c, 'class')})" for c in collaborators),
                ctx.field(P, "sponsorCollaboratorsModule", "collaborators"),
            )
            if collaborators
            else ctx.field(P, "sponsorCollaboratorsModule", "collaborators")
        )
        checks = _check_counts(study)
        _, results_fact = ctx.results()
        eligibility_text = ctx.field(*eligibility, "eligibilityCriteria")
        yield [
            ctx.nct_cell(),
            ctx.field(P, "identificationModule", "briefTitle"),
            ctx.field(P, "identificationModule", "acronym"),
            ctx.field(*status, "overallStatus"),
            ctx.field(*status, "whyStopped"),
            ctx.field(*design, "studyType"),
            ctx.field(*design, "phases"),
            ctx.field(*info, "primaryPurpose"),
            ctx.field(*info, "allocation"),
            ctx.field(*info, "interventionModel"),
            ctx.field(*info, "maskingInfo", "masking"),
            ctx.field(*info, "maskingInfo", "whoMasked"),
            ctx.field(*info, "observationalModel"),
            ctx.field(*info, "timePerspective"),
            ctx.field(*design, "enrollmentInfo", "count"),
            ctx.field(*design, "enrollmentInfo", "type"),
            ctx.field(*status, "startDateStruct", "date"),
            ctx.field(*status, "startDateStruct", "type"),
            ctx.field(*status, "primaryCompletionDateStruct", "date"),
            ctx.field(*status, "primaryCompletionDateStruct", "type"),
            ctx.field(*status, "completionDateStruct", "date"),
            ctx.field(*status, "completionDateStruct", "type"),
            ctx.field(P, "conditionsModule", "conditions"),
            _terms(ctx, "derivedSection", "conditionBrowseModule", "meshes"),
            _terms(ctx, "derivedSection", "conditionBrowseModule", "ancestors"),
            declared,
            _terms(ctx, "derivedSection", "interventionBrowseModule", "meshes"),
            _terms(ctx, "derivedSection", "interventionBrowseModule", "ancestors"),
            ctx.field(P, "sponsorCollaboratorsModule", "leadSponsor", "name"),
            ctx.field(P, "sponsorCollaboratorsModule", "leadSponsor", "class"),
            collaborator_fact,
            ctx.field(*eligibility, "sex"),
            ctx.field(*eligibility, "genderBased"),
            ctx.field(*eligibility, "minimumAge"),
            ctx.field(*eligibility, "maximumAge"),
            ctx.field(*eligibility, "stdAges"),
            ctx.field(*eligibility, "healthyVolunteers"),
            results_fact,
            ctx.field(*status, "resultsFirstPostDateStruct", "date"),
            ctx.field(
                "derivedSection", "miscInfoModule", "submissionTracking", "estimatedResultsFirstSubmitDate"
            ),
            ctx.field(*status, "dispFirstSubmitDate"),
            ctx.field(*status, "resultsWaived"),
            ctx.review(NEEDS_REVIEW_LINE, eligibility_text),
            ctx.review(NEEDS_REVIEW_BIOMARKERS, eligibility_text),
            ctx.whole("check_counts", checks["conflict"]),
            ctx.whole("check_counts", checks["not_checkable"]),
            ctx.whole("reference_counts", _reference_counts(study)),
            ctx.whole("document_count", _document_count(study)),
            literal(ctx.digest),
        ]


def _eligibility_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        module = (P, "eligibilityModule")
        source = ctx.field(*module, "eligibilityCriteria")
        text = get(ctx.study, *module, "eligibilityCriteria")
        if isinstance(text, str):
            code, before, inclusion, exclusion = split_eligibility(text)
            if code == "split":
                parts = [
                    ctx.computed("split_eligibility", before, source),
                    ctx.computed("split_eligibility", inclusion, source),
                    ctx.computed("split_eligibility", exclusion, source),
                    ctx.computed("split_eligibility", "(split into the three columns before)", source),
                ]
            else:
                parts = [ctx.computed("split_eligibility", "(not split)", source)] * 3 + [source]
            split = ctx.computed("split_eligibility", code, source)
        else:
            split = source
            parts = [ctx.computed("absence_state", "(no eligibility text)", source)] * 3 + [source]
        yield [
            ctx.nct_cell(),
            ctx.field(*module, "sex"),
            ctx.field(*module, "genderBased"),
            ctx.field(*module, "genderDescription"),
            ctx.field(*module, "minimumAge"),
            ctx.field(*module, "maximumAge"),
            ctx.field(*module, "stdAges"),
            ctx.field(*module, "healthyVolunteers"),
            ctx.review(NEEDS_REVIEW_LINE, source),
            split,
            *parts,
            ctx.field(*module, "studyPopulation"),
            ctx.field(*module, "samplingMethod"),
        ]


def _outcome_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        found = False
        for section, kind in (
            ("primaryOutcomes", "PRIMARY"),
            ("secondaryOutcomes", "SECONDARY"),
            ("otherOutcomes", "OTHER_PRE_SPECIFIED"),
        ):
            for index, _ in enumerate(as_list(get(ctx.study, P, "outcomesModule", section))):
                found = True
                where = (P, "outcomesModule", section, index)
                measure = ctx.field(*where, "measure")
                yield [
                    ctx.nct_cell(),
                    literal(kind),
                    literal(index + 1),
                    measure,
                    ctx.field(*where, "description"),
                    ctx.field(*where, "timeFrame"),
                    literal(location(where)),
                ]
        if not found:
            absent = ctx.field(P, "outcomesModule")
            yield [
                ctx.nct_cell(),
                absent,
                literal(""),
                literal(""),
                literal(""),
                literal(""),
                literal(f"{P}.outcomesModule"),
            ]


def _arm_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for index, _ in enumerate(as_list(get(ctx.study, P, "armsInterventionsModule", "armGroups"))):
            where = (P, "armsInterventionsModule", "armGroups", index)
            yield [
                ctx.nct_cell(),
                ctx.field(*where, "label"),
                ctx.field(*where, "type"),
                ctx.field(*where, "description"),
                ctx.field(*where, "interventionNames"),
                literal(location(where)),
            ]


def _intervention_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for index, item in enumerate(as_list(get(ctx.study, P, "armsInterventionsModule", "interventions"))):
            where = (P, "armsInterventionsModule", "interventions", index)
            kind, name = ctx.field(*where, "type"), ctx.field(*where, "name")
            yield [
                ctx.nct_cell(),
                kind,
                name,
                ctx.computed(
                    "registry_form", _registry_form(get(item, "type"), get(item, "name")), kind, name
                ),
                ctx.field(*where, "otherNames"),
                ctx.field(*where, "description"),
                ctx.field(*where, "armGroupLabels"),
                literal(location(where)),
            ]


def _site_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for index, _ in enumerate(as_list(get(ctx.study, P, "contactsLocationsModule", "locations"))):
            where = (P, "contactsLocationsModule", "locations", index)
            yield [
                ctx.nct_cell(),
                ctx.field(*where, "facility"),
                ctx.field(*where, "status"),
                ctx.field(*where, "city"),
                ctx.field(*where, "state"),
                ctx.field(*where, "zip"),
                ctx.field(*where, "country"),
                literal(location(where)),
            ]


def _no_results_row(ctx: Ctx, width: int, results_fact: Fact) -> list[Fact]:
    publications = ctx.computed("publications", _publications(ctx.study), ctx.field(P, "referencesModule"))
    return [ctx.nct_cell(), results_fact] + [literal("")] * (width - 3) + [publications]


def _outcome_result_rows(contexts: list[Ctx]) -> Rows:
    width = len(OUTCOME_RESULTS_COLUMNS)
    for ctx in contexts:
        state, results_fact = ctx.results()
        measures = as_list(get(ctx.study, R, "outcomeMeasuresModule", "outcomeMeasures"))
        if state != "posted" and not measures:
            yield _no_results_row(ctx, width, results_fact)
            continue
        for m, measure in enumerate(measures):
            base = (R, "outcomeMeasuresModule", "outcomeMeasures", m)
            titles, analyzed = _group_titles(measure), _analyzed(measure)
            groups_fact = ctx.field(*base, "groups")
            denoms_fact = ctx.field(*base, "denoms")
            for c, klass in enumerate(as_list(get(measure, "classes"))):
                for k, category in enumerate(as_list(get(klass, "categories"))):
                    for x, measurement in enumerate(as_list(get(category, "measurements"))):
                        cell = (*base, "classes", c, "categories", k, "measurements", x)
                        group = get(measurement, "groupId")
                        group_fact = ctx.field(*cell, "groupId")
                        yield [
                            ctx.nct_cell(),
                            results_fact,
                            ctx.field(*base, "type"),
                            ctx.field(*base, "title"),
                            ctx.field(*base, "description"),
                            ctx.field(*base, "timeFrame"),
                            ctx.field(*base, "populationDescription"),
                            ctx.field(*base, "reportingStatus"),
                            ctx.field(*base, "paramType"),
                            ctx.field(*base, "dispersionType"),
                            ctx.field(*base, "unitOfMeasure"),
                            ctx.field(*base, "classes", c, "title"),
                            ctx.field(*base, "classes", c, "categories", k, "title"),
                            group_fact,
                            ctx.computed(
                                "group_title",
                                _text(titles.get(group, "not reported")),
                                group_fact,
                                groups_fact,
                            ),
                            ctx.computed(
                                "analyzed",
                                "\n".join(analyzed.get(group, [])) or "not reported",
                                group_fact,
                                denoms_fact,
                            ),
                            ctx.field(*cell, "value"),
                            ctx.field(*cell, "spread"),
                            ctx.field(*cell, "lowerLimit"),
                            ctx.field(*cell, "upperLimit"),
                            ctx.field(*cell, "comment"),
                            literal(location(cell)),
                            literal(""),
                        ]


def _analysis_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for m, measure in enumerate(as_list(get(ctx.study, R, "outcomeMeasuresModule", "outcomeMeasures"))):
            titles = _group_titles(measure)
            for a, _ in enumerate(as_list(get(measure, "analyses"))):
                where = (R, "outcomeMeasuresModule", "outcomeMeasures", m, "analyses", a)
                ids = as_list(get(ctx.study, *where, "groupIds"))
                ids_fact = ctx.field(*where, "groupIds")
                yield [
                    ctx.nct_cell(),
                    ctx.field(R, "outcomeMeasuresModule", "outcomeMeasures", m, "title"),
                    ctx.computed(
                        "group_title",
                        "\n".join(f"{gid}: {titles.get(gid, 'not reported')}" for gid in ids)
                        or "not reported",
                        ids_fact,
                        ctx.field(R, "outcomeMeasuresModule", "outcomeMeasures", m, "groups"),
                    ),
                    ctx.field(*where, "groupDescription"),
                    ctx.field(*where, "paramType"),
                    ctx.field(*where, "paramValue"),
                    ctx.field(*where, "ciPctValue"),
                    ctx.field(*where, "ciNumSides"),
                    ctx.field(*where, "ciLowerLimit"),
                    ctx.field(*where, "ciUpperLimit"),
                    ctx.field(*where, "pValue"),
                    ctx.field(*where, "pValueComment"),
                    ctx.field(*where, "statisticalMethod"),
                    ctx.field(*where, "nonInferiorityType"),
                    ctx.field(*where, "dispersionType"),
                    ctx.field(*where, "dispersionValue"),
                    ctx.field(*where, "estimateComment"),
                    literal(location(where)),
                ]


def _adverse_event_rows(contexts: list[Ctx]) -> Rows:
    width = len(ADVERSE_EVENT_COLUMNS)
    for ctx in contexts:
        state, results_fact = ctx.results()
        module = get(ctx.study, R, "adverseEventsModule")
        if state != "posted" and not isinstance(module, dict):
            yield _no_results_row(ctx, width, results_fact)
            continue
        groups = [get(g, "id") for g in as_list(get(module, "eventGroups"))]
        for table, prefix in (("seriousEvents", "serious"), ("otherEvents", "other")):
            for e, event in enumerate(as_list(get(module, table))):
                where = (R, "adverseEventsModule", table, e)
                for s, stats in enumerate(as_list(get(event, "stats"))):
                    group_id = get(stats, "groupId")
                    g = groups.index(group_id) if group_id in groups else len(groups)
                    event_risk = ctx.field(*where, "stats", s, "numAtRisk")
                    table_total = ctx.field(R, "adverseEventsModule", "eventGroups", g, f"{prefix}NumAtRisk")
                    source, risk = at_risk(
                        get(stats, "numAtRisk"),
                        get(module, "eventGroups", g, f"{prefix}NumAtRisk") if g < len(groups) else None,
                    )
                    yield [
                        ctx.nct_cell(),
                        results_fact,
                        literal(prefix),
                        ctx.field(*where, "term"),
                        ctx.field(*where, "organSystem"),
                        ctx.field(*where, "sourceVocabulary"),
                        ctx.field(*where, "assessmentType"),
                        ctx.field(*where, "stats", s, "groupId"),
                        ctx.field(R, "adverseEventsModule", "eventGroups", g, "title"),
                        ctx.field(*where, "stats", s, "numAffected"),
                        ctx.computed(
                            "at_risk", risk if risk is not None else "not reported", event_risk, table_total
                        ),
                        ctx.computed(
                            "at_risk",
                            {"stated": "stated", "group_total": "group total (the event's is blank)"}.get(
                                source, "not reported"
                            ),
                            event_risk,
                            table_total,
                        ),
                        ctx.field(*where, "stats", s, "numEvents"),
                        ctx.field(*where, "notes"),
                        literal(location((*where, "stats", s))),
                        literal(""),
                    ]


def _event_group_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        module = (R, "adverseEventsModule")
        for g, _ in enumerate(as_list(get(ctx.study, *module, "eventGroups"))):
            where = (*module, "eventGroups", g)
            yield [
                ctx.nct_cell(),
                ctx.field(*where, "id"),
                ctx.field(*where, "title"),
                ctx.field(*where, "description"),
                ctx.field(*where, "deathsNumAffected"),
                ctx.field(*where, "deathsNumAtRisk"),
                ctx.field(*where, "seriousNumAffected"),
                ctx.field(*where, "seriousNumAtRisk"),
                ctx.field(*where, "otherNumAffected"),
                ctx.field(*where, "otherNumAtRisk"),
                ctx.field(*module, "frequencyThreshold"),
                ctx.field(*module, "timeFrame"),
                ctx.field(*module, "description"),
                ctx.field(*module, "allCauseMortalityComment"),
                literal(location(where)),
            ]


def _flow_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        module = get(ctx.study, R, "participantFlowModule")
        titles = _group_titles(module)
        groups_fact = ctx.field(R, "participantFlowModule", "groups")
        for p, period in enumerate(as_list(get(module, "periods"))):
            base = (R, "participantFlowModule", "periods", p)
            for m, _ in enumerate(as_list(get(period, "milestones"))):
                for a, achievement in enumerate(as_list(get(period, "milestones", m, "achievements"))):
                    where = (*base, "milestones", m, "achievements", a)
                    group_fact = ctx.field(*where, "groupId")
                    yield [
                        ctx.nct_cell(),
                        ctx.field(*base, "title"),
                        literal("milestone"),
                        ctx.field(*base, "milestones", m, "type"),
                        group_fact,
                        ctx.computed(
                            "group_title",
                            _text(titles.get(get(achievement, "groupId"), "not reported")),
                            group_fact,
                            groups_fact,
                        ),
                        ctx.field(*where, "numSubjects"),
                        ctx.field(*where, "comment"),
                        literal(location(where)),
                    ]
            for d, _ in enumerate(as_list(get(period, "dropWithdraws"))):
                for r, reason in enumerate(as_list(get(period, "dropWithdraws", d, "reasons"))):
                    where = (*base, "dropWithdraws", d, "reasons", r)
                    group_fact = ctx.field(*where, "groupId")
                    yield [
                        ctx.nct_cell(),
                        ctx.field(*base, "title"),
                        literal("reason not completed"),
                        ctx.field(*base, "dropWithdraws", d, "type"),
                        group_fact,
                        ctx.computed(
                            "group_title",
                            _text(titles.get(get(reason, "groupId"), "not reported")),
                            group_fact,
                            groups_fact,
                        ),
                        ctx.field(*where, "numSubjects"),
                        ctx.field(*where, "comment"),
                        literal(location(where)),
                    ]


def _baseline_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        module = get(ctx.study, R, "baselineCharacteristicsModule")
        titles = _group_titles(module)
        groups_fact = ctx.field(R, "baselineCharacteristicsModule", "groups")
        for m, measure in enumerate(as_list(get(module, "measures"))):
            base = (R, "baselineCharacteristicsModule", "measures", m)
            for c, klass in enumerate(as_list(get(measure, "classes"))):
                for k, category in enumerate(as_list(get(klass, "categories"))):
                    for x, measurement in enumerate(as_list(get(category, "measurements"))):
                        where = (*base, "classes", c, "categories", k, "measurements", x)
                        group_fact = ctx.field(*where, "groupId")
                        yield [
                            ctx.nct_cell(),
                            ctx.field(*base, "title"),
                            ctx.field(*base, "paramType"),
                            ctx.field(*base, "dispersionType"),
                            ctx.field(*base, "unitOfMeasure"),
                            ctx.field(*base, "classes", c, "title"),
                            ctx.field(*base, "classes", c, "categories", k, "title"),
                            group_fact,
                            ctx.computed(
                                "group_title",
                                _text(titles.get(get(measurement, "groupId"), "not reported")),
                                group_fact,
                                groups_fact,
                            ),
                            ctx.field(*where, "value"),
                            ctx.field(*where, "spread"),
                            ctx.field(*where, "lowerLimit"),
                            ctx.field(*where, "upperLimit"),
                            literal(location(where)),
                        ]


def _publication_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for index, ref in enumerate(as_list(get(ctx.study, P, "referencesModule", "references"))):
            where = (P, "referencesModule", "references", index)
            pmid_fact, type_fact = ctx.field(*where, "pmid"), ctx.field(*where, "type")
            code, url = pubmed_link(get(ref, "pmid"))
            retractions = as_list(get(ref, "retractions"))
            yield [
                ctx.nct_cell(),
                Fact(
                    pmid_fact.value,
                    warrants.computed(RULE["pubmed_link"], pmid_fact.warrant),
                    url,
                    pmid_fact.where,
                )
                if code == "ok"
                else pmid_fact,
                type_fact,
                ctx.computed("reference_role", reference_role(get(ref, "type")), type_fact),
                ctx.field(*where, "citation"),
                ctx.computed(
                    "list_lines",
                    "\n".join(f"PMID {get(r, 'pmid')} ({get(r, 'source')})" for r in retractions)
                    or "none in the record",
                    ctx.field(*where, "retractions"),
                ),
                literal(location(where)),
            ]


def _document_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for index, doc in enumerate(
            as_list(get(ctx.study, "documentSection", "largeDocumentModule", "largeDocs"))
        ):
            where = ("documentSection", "largeDocumentModule", "largeDocs", index)
            filename = ctx.field(*where, "filename")
            code, url = document_link(ctx.nct, get(doc, "filename"))
            yield [
                ctx.nct_cell(),
                ctx.field(*where, "typeAbbrev"),
                ctx.field(*where, "label"),
                ctx.field(*where, "hasProtocol"),
                ctx.field(*where, "hasSap"),
                ctx.field(*where, "hasIcf"),
                ctx.field(*where, "date"),
                ctx.field(*where, "uploadDate"),
                Fact(
                    filename.value,
                    warrants.computed(RULE["document_link"], filename.warrant),
                    url,
                    filename.where,
                )
                if code == "ok"
                else filename,
                literal(location(where)),
            ]


def _check_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for result in run_checks(ctx.study):
            yield [
                ctx.nct_cell(),
                literal(result.check_id),
                ctx.checked(result.check_id, result.outcome),
                ctx.checked(result.check_id, result.detail),
            ]


def _check_rule_rows(contexts: list[Ctx]) -> Rows:
    for check in CHECKS:
        warrant = RULE[check.id]
        yield [
            Fact(check.id, warrant),
            Fact(check.relation, warrant),
            Fact(check.basis, warrant),
            Fact(check.approval, warrant),
            Fact(check.rule, warrant),
            literal(warrant),
        ]


def _record_rows(contexts: list[Ctx]) -> Rows:
    for ctx in contexts:
        for entry in entries(ctx.study):
            field = ".".join(
                part for part in entry.location.replace("[", ".[").split(".") if not part.startswith("[")
            )
            value = entry.value
            shown = value
            if value is None:
                shown = "(null in the record)"
            elif value == []:
                shown = "(empty list)"
            elif value == {}:
                shown = "(empty object)"
            warrant = warrants.stated(ctx.digest, entry.location, value)
            names = warrants.computed(RULE["registry_names"], warrant)
            here = f"{entry.location} of this row's study"
            yield [
                literal(ctx.nct, f"{NCT_LOCATION} of this row's study"),
                Fact(registry.category(field), names),
                Fact(registry.title(field), names),
                literal(entry.location, here),
                Fact(shown, warrant, where=here),
                literal(
                    "; ".join(f"{name}={role}" for name, role in entry.role),
                    f"the identifiers above {entry.location} of this row's study",
                ),
            ]


NCT_COLUMN = Column(
    "NCT Number", "stated (link)", "protocolSection.identificationModule.nctId; link: the registry page"
)

STUDIES_COLUMNS = (
    NCT_COLUMN,
    stated_column("Brief Title", "protocolSection.identificationModule.briefTitle"),
    stated_column("Acronym", "protocolSection.identificationModule.acronym"),
    stated_column("Overall Status", "protocolSection.statusModule.overallStatus"),
    stated_column("Why Stopped", "protocolSection.statusModule.whyStopped"),
    stated_column("Study Type", "protocolSection.designModule.studyType"),
    stated_column("Phases", "protocolSection.designModule.phases"),
    stated_column("Primary Purpose", "protocolSection.designModule.designInfo.primaryPurpose"),
    stated_column("Allocation", "protocolSection.designModule.designInfo.allocation"),
    stated_column("Intervention Model", "protocolSection.designModule.designInfo.interventionModel"),
    stated_column("Masking", "protocolSection.designModule.designInfo.maskingInfo.masking"),
    stated_column("Who Masked", "protocolSection.designModule.designInfo.maskingInfo.whoMasked"),
    stated_column("Observational Model", "protocolSection.designModule.designInfo.observationalModel"),
    stated_column("Time Perspective", "protocolSection.designModule.designInfo.timePerspective"),
    stated_column("Enrollment", "protocolSection.designModule.enrollmentInfo.count"),
    stated_column("Enrollment Type", "protocolSection.designModule.enrollmentInfo.type"),
    stated_column("Start Date", "protocolSection.statusModule.startDateStruct.date"),
    stated_column("Start Date Type", "protocolSection.statusModule.startDateStruct.type"),
    stated_column("Primary Completion Date", "protocolSection.statusModule.primaryCompletionDateStruct.date"),
    stated_column(
        "Primary Completion Date Type", "protocolSection.statusModule.primaryCompletionDateStruct.type"
    ),
    stated_column("Completion Date", "protocolSection.statusModule.completionDateStruct.date"),
    stated_column("Completion Date Type", "protocolSection.statusModule.completionDateStruct.type"),
    stated_column("Conditions", "protocolSection.conditionsModule.conditions"),
    stated_column(
        "Condition MeSH Terms", "derivedSection.conditionBrowseModule.meshes[].term (registry-derived)"
    ),
    stated_column(
        "Condition MeSH Ancestors", "derivedSection.conditionBrowseModule.ancestors[].term (registry-derived)"
    ),
    computed_column(
        "Interventions",
        "registry_form over protocolSection.armsInterventionsModule.interventions[]: '<type label>: <name>'",
    ),
    stated_column(
        "Intervention MeSH Terms", "derivedSection.interventionBrowseModule.meshes[].term (registry-derived)"
    ),
    stated_column(
        "Intervention MeSH Ancestors",
        "derivedSection.interventionBrowseModule.ancestors[].term (registry-derived)",
    ),
    stated_column("Lead Sponsor", "protocolSection.sponsorCollaboratorsModule.leadSponsor.name"),
    stated_column("Lead Sponsor Class", "protocolSection.sponsorCollaboratorsModule.leadSponsor.class"),
    stated_column(
        "Collaborators", "protocolSection.sponsorCollaboratorsModule.collaborators[]: name (class)"
    ),
    stated_column("Sex", "protocolSection.eligibilityModule.sex"),
    stated_column("Gender Based", "protocolSection.eligibilityModule.genderBased"),
    stated_column("Minimum Age", "protocolSection.eligibilityModule.minimumAge"),
    stated_column("Maximum Age", "protocolSection.eligibilityModule.maximumAge"),
    stated_column("Age Groups", "protocolSection.eligibilityModule.stdAges (registry-derived from the ages)"),
    stated_column("Healthy Volunteers", "protocolSection.eligibilityModule.healthyVolunteers"),
    computed_column("Results", "results_state over hasResults and the presence of resultsSection"),
    stated_column("Results First Posted", "protocolSection.statusModule.resultsFirstPostDateStruct.date"),
    stated_column(
        "Results Submitted, Not Yet Posted",
        "derivedSection.miscInfoModule.submissionTracking.estimatedResultsFirstSubmitDate: «Results First "
        "Submitted Date but not yet Posted (e.g., still under QC review)»",
    ),
    stated_column(
        "Results Delay Requested",
        "protocolSection.statusModule.dispFirstSubmitDate: a certification or extension request "
        "to delay results",
    ),
    stated_column("Results Waived", "protocolSection.statusModule.resultsWaived"),
    Column(
        "Line of Therapy", "needs review", "not a structured field of the record; see the Eligibility sheet"
    ),
    Column(
        "Biomarkers", "needs review", "not a structured field; they appear inside outcomes and eligibility"
    ),
    computed_column("Approved Checks in Conflict", "count of approved edit checks with outcome conflict"),
    computed_column(
        "Approved Checks Not Checkable", "count of approved edit checks with outcome not_checkable"
    ),
    computed_column("Publications by Type", "count of protocolSection.referencesModule.references[] by type"),
    computed_column("Posted Documents", "count of documentSection.largeDocumentModule.largeDocs[]"),
    Column(
        "Record Digest",
        "warrant",
        "SHA-256 of the study's record in canonical JSON; the root of every warrant",
    ),
)

ELIGIBILITY_COLUMNS = (
    NCT_COLUMN,
    stated_column("Sex", "protocolSection.eligibilityModule.sex"),
    stated_column("Gender Based", "protocolSection.eligibilityModule.genderBased"),
    stated_column("Gender Description", "protocolSection.eligibilityModule.genderDescription"),
    stated_column("Minimum Age", "protocolSection.eligibilityModule.minimumAge"),
    stated_column("Maximum Age", "protocolSection.eligibilityModule.maximumAge"),
    stated_column("Age Groups", "protocolSection.eligibilityModule.stdAges"),
    stated_column("Healthy Volunteers", "protocolSection.eligibilityModule.healthyVolunteers"),
    Column(
        "Line of Therapy", "needs review", "not a structured field; read the eligibility text in this row"
    ),
    computed_column(
        "Split",
        "split_eligibility: split, not_split_missing, not_split_repeated or not_split_order; split only "
        "at one 'Inclusion Criteria' heading followed by one 'Exclusion Criteria' heading",
    ),
    computed_column(
        "Before the Inclusion Heading",
        "split_eligibility, part 1 of the exact text (blank when nothing precedes the heading)",
    ),
    computed_column("Inclusion Criteria", "split_eligibility, part 2 of the exact text, from its heading"),
    computed_column("Exclusion Criteria", "split_eligibility, part 3 of the exact text, from its heading"),
    stated_column("Whole Text", "protocolSection.eligibilityModule.eligibilityCriteria, when not split"),
    stated_column(
        "Study Population", "protocolSection.eligibilityModule.studyPopulation (observational studies)"
    ),
    stated_column(
        "Sampling Method", "protocolSection.eligibilityModule.samplingMethod (observational studies)"
    ),
)

OUTCOMES_COLUMNS = (
    NCT_COLUMN,
    stated_column(
        "Outcome Type", "the section the outcome is registered in (primary, secondary, other outcomes)"
    ),
    stated_column("Order", "position within its section, from 1"),
    stated_column("Measure", "protocolSection.outcomesModule.<section>[].measure"),
    stated_column("Description", "protocolSection.outcomesModule.<section>[].description"),
    stated_column("Time Frame", "protocolSection.outcomesModule.<section>[].timeFrame"),
    stated_column("Location", "the record location of the outcome"),
)

ARMS_COLUMNS = (
    NCT_COLUMN,
    stated_column("Arm Label", "protocolSection.armsInterventionsModule.armGroups[].label"),
    stated_column("Arm Type", "protocolSection.armsInterventionsModule.armGroups[].type"),
    stated_column("Description", "protocolSection.armsInterventionsModule.armGroups[].description"),
    stated_column(
        "Interventions Named", "protocolSection.armsInterventionsModule.armGroups[].interventionNames"
    ),
    stated_column("Location", "the record location of the arm"),
)

INTERVENTIONS_COLUMNS = (
    NCT_COLUMN,
    stated_column("Type", "protocolSection.armsInterventionsModule.interventions[].type"),
    stated_column("Name", "protocolSection.armsInterventionsModule.interventions[].name"),
    computed_column(
        "Registry Form", "registry_form: '<type label>: <name>', the form arms name interventions by"
    ),
    stated_column("Other Names", "protocolSection.armsInterventionsModule.interventions[].otherNames"),
    stated_column("Description", "protocolSection.armsInterventionsModule.interventions[].description"),
    stated_column("Arms Named", "protocolSection.armsInterventionsModule.interventions[].armGroupLabels"),
    stated_column("Location", "the record location of the intervention"),
)

SITES_COLUMNS = (
    NCT_COLUMN,
    stated_column("Facility", "protocolSection.contactsLocationsModule.locations[].facility"),
    stated_column("Site Status", "protocolSection.contactsLocationsModule.locations[].status"),
    stated_column("City", "protocolSection.contactsLocationsModule.locations[].city"),
    stated_column("State", "protocolSection.contactsLocationsModule.locations[].state"),
    stated_column("ZIP", "protocolSection.contactsLocationsModule.locations[].zip"),
    stated_column("Country", "protocolSection.contactsLocationsModule.locations[].country"),
    stated_column("Location", "the record location of the site"),
)

OUTCOME_RESULTS_COLUMNS = (
    NCT_COLUMN,
    computed_column("Results", "results_state; 'no results posted' when the registry's flag is false"),
    stated_column("Outcome Type", "resultsSection.outcomeMeasuresModule.outcomeMeasures[].type"),
    stated_column("Title", "outcomeMeasures[].title"),
    stated_column("Description", "outcomeMeasures[].description"),
    stated_column("Time Frame", "outcomeMeasures[].timeFrame"),
    stated_column("Population Description", "outcomeMeasures[].populationDescription"),
    stated_column("Reporting Status", "outcomeMeasures[].reportingStatus"),
    stated_column("Measure Type", "outcomeMeasures[].paramType"),
    stated_column("Dispersion Type", "outcomeMeasures[].dispersionType"),
    stated_column("Unit of Measure", "outcomeMeasures[].unitOfMeasure"),
    stated_column("Class", "outcomeMeasures[].classes[].title"),
    stated_column("Category", "outcomeMeasures[].classes[].categories[].title"),
    stated_column("Group ID", "...measurements[].groupId"),
    computed_column("Group Title", "group_title: outcomeMeasures[].groups[].title for the group id"),
    computed_column("Analyzed", "analyzed: outcomeMeasures[].denoms[] as '<units>: <count>' for the group"),
    stated_column("Value", "...measurements[].value, exactly as posted (text)"),
    stated_column("Spread", "...measurements[].spread"),
    stated_column("Lower Limit", "...measurements[].lowerLimit"),
    stated_column("Upper Limit", "...measurements[].upperLimit"),
    stated_column("Comment", "...measurements[].comment"),
    stated_column("Location", "the record location of the measurement"),
    computed_column("Publications", "publications, when no results are posted: '<type>: PMID <pmid>'"),
)

ANALYSES_COLUMNS = (
    NCT_COLUMN,
    stated_column("Outcome Title", "outcomeMeasures[].title"),
    computed_column("Groups Compared", "group_title: analyses[].groupIds with each group's title"),
    stated_column("Group Description", "analyses[].groupDescription"),
    stated_column("Estimation Parameter", "analyses[].paramType"),
    stated_column("Estimated Value", "analyses[].paramValue"),
    stated_column("CI Level (%)", "analyses[].ciPctValue"),
    stated_column("CI Sides", "analyses[].ciNumSides"),
    stated_column("CI Lower", "analyses[].ciLowerLimit"),
    stated_column("CI Upper", "analyses[].ciUpperLimit"),
    stated_column("P-Value", "analyses[].pValue"),
    stated_column("P-Value Comment", "analyses[].pValueComment"),
    stated_column("Statistical Method", "analyses[].statisticalMethod"),
    stated_column("Test Type", "analyses[].nonInferiorityType"),
    stated_column("Dispersion Type", "analyses[].dispersionType"),
    stated_column("Dispersion Value", "analyses[].dispersionValue"),
    stated_column("Estimation Comment", "analyses[].estimateComment"),
    stated_column("Location", "the record location of the analysis"),
)

ADVERSE_EVENT_COLUMNS = (
    NCT_COLUMN,
    computed_column("Results", "results_state; 'no results posted' when the registry's flag is false"),
    stated_column("Table", "serious (seriousEvents) or other (otherEvents)"),
    stated_column("Term", "...Events[].term"),
    stated_column("Organ System", "...Events[].organSystem"),
    stated_column("Source Vocabulary", "...Events[].sourceVocabulary"),
    stated_column("Assessment Type", "...Events[].assessmentType"),
    stated_column("Group ID", "...Events[].stats[].groupId"),
    stated_column("Group Title", "eventGroups[].title for the group id"),
    stated_column("Participants Affected", "...Events[].stats[].numAffected"),
    computed_column(
        "Participants at Risk",
        "at_risk: the event's numAtRisk, or when blank the group's table total (R#AdverseEventAtRisk)",
    ),
    computed_column("At Risk Source", "at_risk: stated, or group total when the event's is blank"),
    stated_column("Events", "...Events[].stats[].numEvents"),
    stated_column("Notes", "...Events[].notes"),
    stated_column("Location", "the record location of the count"),
    computed_column("Publications", "publications, when no results are posted: '<type>: PMID <pmid>'"),
)

EVENT_GROUP_COLUMNS = (
    NCT_COLUMN,
    stated_column("Group ID", "resultsSection.adverseEventsModule.eventGroups[].id"),
    stated_column("Title", "eventGroups[].title"),
    stated_column("Description", "eventGroups[].description"),
    stated_column("Deaths Affected", "eventGroups[].deathsNumAffected"),
    stated_column("Deaths at Risk", "eventGroups[].deathsNumAtRisk"),
    stated_column("Serious Affected", "eventGroups[].seriousNumAffected"),
    stated_column("Serious at Risk", "eventGroups[].seriousNumAtRisk"),
    stated_column("Other Affected", "eventGroups[].otherNumAffected"),
    stated_column("Other at Risk", "eventGroups[].otherNumAtRisk"),
    stated_column("Frequency Threshold (%)", "resultsSection.adverseEventsModule.frequencyThreshold"),
    stated_column("Time Frame", "resultsSection.adverseEventsModule.timeFrame"),
    stated_column("Reporting Description", "resultsSection.adverseEventsModule.description"),
    stated_column(
        "All-Cause Mortality Comment", "resultsSection.adverseEventsModule.allCauseMortalityComment"
    ),
    stated_column("Location", "the record location of the group"),
)

FLOW_COLUMNS = (
    NCT_COLUMN,
    stated_column("Period", "resultsSection.participantFlowModule.periods[].title"),
    stated_column("Kind", "milestone, or reason not completed (dropWithdraws)"),
    stated_column("Type", "milestones[].type, or dropWithdraws[].type"),
    stated_column("Group ID", "achievements[].groupId or reasons[].groupId"),
    computed_column("Group Title", "group_title: participantFlowModule.groups[].title for the group id"),
    stated_column("Participants", "achievements[].numSubjects or reasons[].numSubjects (text, as posted)"),
    stated_column("Comment", "achievements[].comment or reasons[].comment"),
    stated_column("Location", "the record location of the count"),
)

BASELINE_COLUMNS = (
    NCT_COLUMN,
    stated_column("Measure", "resultsSection.baselineCharacteristicsModule.measures[].title"),
    stated_column("Measure Type", "measures[].paramType"),
    stated_column("Dispersion Type", "measures[].dispersionType"),
    stated_column("Unit of Measure", "measures[].unitOfMeasure"),
    stated_column("Class", "measures[].classes[].title"),
    stated_column("Category", "measures[].classes[].categories[].title"),
    stated_column("Group ID", "...measurements[].groupId"),
    computed_column(
        "Group Title", "group_title: baselineCharacteristicsModule.groups[].title for the group id"
    ),
    stated_column("Value", "...measurements[].value (text, as posted)"),
    stated_column("Spread", "...measurements[].spread"),
    stated_column("Lower Limit", "...measurements[].lowerLimit"),
    stated_column("Upper Limit", "...measurements[].upperLimit"),
    stated_column("Location", "the record location of the measurement"),
)

PUBLICATIONS_COLUMNS = (
    NCT_COLUMN,
    Column("PMID", "stated (link)", "references[].pmid; link: its PubMed page"),
    stated_column("Type", "references[].type"),
    computed_column(
        "What the Type Says", "reference_role: the registry's terms for the type, and no further reading"
    ),
    stated_column("Citation", "references[].citation"),
    stated_column("Retractions", "references[].retractions[]: PMID (source)"),
    stated_column("Location", "the record location of the reference"),
)

DOCUMENTS_COLUMNS = (
    NCT_COLUMN,
    stated_column("Document Type", "documentSection.largeDocumentModule.largeDocs[].typeAbbrev"),
    stated_column("Label", "largeDocs[].label"),
    stated_column("Includes Protocol", "largeDocs[].hasProtocol"),
    stated_column("Includes SAP", "largeDocs[].hasSap"),
    stated_column("Includes ICF", "largeDocs[].hasIcf"),
    stated_column("Document Date", "largeDocs[].date"),
    stated_column("Uploaded", "largeDocs[].uploadDate"),
    Column("File", "stated (link)", "largeDocs[].filename; link: the registry's copy (document_link)"),
    stated_column("Location", "the record location of the document"),
)

CHECKS_COLUMNS = (
    NCT_COLUMN,
    stated_column("Check", "an approved edit check (Check Rules sheet)"),
    computed_column("Outcome", "the check's rule: consistent, conflict, not_applicable or not_checkable"),
    computed_column("Detail", "the check's rule: the fields and values it read, as the record holds them"),
)

CHECK_RULE_COLUMNS = (
    stated_column("Check", "checks.CHECKS"),
    stated_column("Relation", "the relation the check tests"),
    stated_column("Basis", "stated rule, registry function, stated scope, or entailed by definitions"),
    stated_column("Approval", "approved checks run; proposed checks run only once the founder approves them"),
    stated_column(
        "The Registry's Words", "quoted from the data element definitions (P, R) or the API metadata"
    ),
    Column(
        "Rule Warrant", "warrant", "commits to the check's id, the tool version and the code that applies it"
    ),
)

RECORD_COLUMNS = (
    stated_column("NCT Number", "protocolSection.identificationModule.nctId"),
    computed_column("Category", "registry_names: the registry's section and module names (API metadata)"),
    computed_column("Field", "registry_names: the registry's field title (API metadata)"),
    stated_column("Location", "the value's exact place in studies.json"),
    stated_column("Value", "the value exactly as the record holds it"),
    stated_column("Role", "the role the record's structure gives the value (ledger.node_role)"),
)

TEN_QUESTIONS = (
    ("1", "Patient population", "Studies (sex, ages, healthy volunteers), Eligibility, Baseline"),
    ("2–3", "Key inclusion and exclusion criteria", "Eligibility"),
    ("4", "Line of therapy", "Eligibility: needs review, the eligibility text beside it"),
    ("5", "Outcome measures and time points", "Outcomes; Outcome Results"),
    ("6", "Biomarkers and time points", "Outcomes and Eligibility: needs review to single out"),
    (
        "7",
        "Anticipated efficacy threshold",
        "Outcome Results and Analyses; across comparable trials: a later stage",
    ),
    ("8", "Safety signals", "Adverse Events; Event Groups"),
    ("9", "Exploratory biomarkers, imaging, biopsies", "Outcomes (OTHER_PRE_SPECIFIED); Arms; Interventions"),
    ("10", "Standard protocol language", "across trials: a later stage"),
)


@dataclass(frozen=True)
class Sheet:
    name: str
    purpose: str
    columns: tuple[Column, ...]
    rows: Callable[[list[Ctx]], Rows]
    warranted: bool = True  # a last column carries each row's warrant


SHEETS: tuple[Sheet, ...] = (
    Sheet("Studies", "one row per study: the design axes", STUDIES_COLUMNS, _study_rows),
    Sheet(
        "Eligibility", "population limits and the eligibility text", ELIGIBILITY_COLUMNS, _eligibility_rows
    ),
    Sheet(
        "Outcomes", "every registered outcome with its type and time frame", OUTCOMES_COLUMNS, _outcome_rows
    ),
    Sheet("Arms", "every arm or group", ARMS_COLUMNS, _arm_rows),
    Sheet("Interventions", "every declared intervention", INTERVENTIONS_COLUMNS, _intervention_rows),
    Sheet("Sites", "every location", SITES_COLUMNS, _site_rows),
    Sheet(
        "Outcome Results",
        "every posted outcome measurement, per group",
        OUTCOME_RESULTS_COLUMNS,
        _outcome_result_rows,
    ),
    Sheet("Analyses", "every posted statistical analysis", ANALYSES_COLUMNS, _analysis_rows),
    Sheet(
        "Adverse Events",
        "every serious and other adverse event, per group",
        ADVERSE_EVENT_COLUMNS,
        _adverse_event_rows,
    ),
    Sheet("Event Groups", "adverse-event totals per group", EVENT_GROUP_COLUMNS, _event_group_rows),
    Sheet("Participant Flow", "milestones and reasons not completed, per group", FLOW_COLUMNS, _flow_rows),
    Sheet("Baseline", "every posted baseline measurement, per group", BASELINE_COLUMNS, _baseline_rows),
    Sheet(
        "Publications",
        "every linked publication, typed in the registry's terms",
        PUBLICATIONS_COLUMNS,
        _publication_rows,
    ),
    Sheet(
        "Documents",
        "every posted protocol, analysis plan and consent form",
        DOCUMENTS_COLUMNS,
        _document_rows,
    ),
    Sheet("Checks", "every approved edit check on every study", CHECKS_COLUMNS, _check_rows),
    Sheet(
        "Check Rules",
        "the edit checks, their basis, approval and warrant",
        CHECK_RULE_COLUMNS,
        _check_rule_rows,
        False,
    ),
    Sheet(
        "Record",
        "every value of every study, in the registry's own categories",
        RECORD_COLUMNS,
        _record_rows,
        False,
    ),
)


@dataclass(frozen=True)
class Book:
    """One workbook file: its name, its title on its About sheet, and the sheets after its About sheet."""

    name: str
    title: str
    sheets: tuple[Sheet, ...]


REVIEW = Book(
    WORKBOOK_NAME,
    "TrialLedger review workbook: the design questions, study by study",
    tuple(sheet for sheet in SHEETS if sheet.name != "Record"),
)
RECORD = Book(
    RECORD_NAME,
    "TrialLedger record workbook: every value of every study, in the registry's own categories",
    tuple(sheet for sheet in SHEETS if sheet.name == "Record"),
)
BOOKS = (REVIEW, RECORD)


def _about_rows(record: dict[str, Any], book: Book) -> Iterator[list[Fact]]:
    provenance = record.get("provenance") or {}
    yield [
        literal(book.title),
        literal(f"TrialLedger {__version__}; edit checks version {CHECKS_VERSION}"),
        literal(""),
        literal(""),
    ]
    for key in (
        "source",
        "query",
        "api_version",
        "data_timestamp",
        "retrieved_at",
        "study_count",
        "tool",
        "writer",
        "code_root",
        "code_commit",
        "merkle_root",
        "record_root",
    ):
        value = provenance.get(key)
        shown = "; ".join(f"{k}={v}" for k, v in value.items()) if isinstance(value, dict) else value
        yield [
            literal("provenance"),
            literal(key),
            literal(shown if shown is not None else "not recorded", f"provenance.{key}"),
            literal(""),
        ]
    for index, entry in enumerate(provenance.get("requested_ids") or []):
        study = f" (study {entry['study']})" if entry["status"] == "aliased" else ""
        yield [
            literal("requested id"),
            literal(entry["requested"]),
            literal(f"{entry['status']}{study}", f"provenance.requested_ids[{index}]"),
            literal(""),
        ]
    for name, meaning in (
        ("stated", "read from a structured field of the record; the column's source names it"),
        ("computed", "derived by the named rule from the named fields"),
        ("needs review", "not determinable from structured fields; never filled"),
        ("not reported", "the record holds no value; never read as zero, none or no"),
        ("not applicable to this study type", "the registry's definitions limit the field"),
        ("redacted (withheld study)", "the registry redacts the field for withheld studies"),
        ("lists", "a list field shows one item per line, each exactly as the record holds it"),
        (
            "not written",
            "a value a cell cannot hold exactly is replaced by the reason and where the value is in "
            "studies.json; nothing is cut, cleaned or rounded",
        ),
        (
            "warrants",
            "every row's Warrant commits to the record bytes and the code behind each of its cells; a "
            "Record row's value is warranted by SHA-256 over the length-prefixed parts 'stated', its "
            "study's Record Digest, its Location and its Value in canonical JSON. The code root commits to "
            "the code and registry tables that derived this file (code_commit names their git commit), and "
            "the record root to the provenance, every study and studies.csv. `trialledger verify <folder>` "
            "re-derives all of them from studies.json, and this file byte for byte",
        ),
    ):
        yield [literal("how to read"), literal(name), literal(meaning), literal("")]
    for other in BOOKS:
        if other is not book:
            yield [literal("companion file"), literal(other.name), literal(other.title), literal("")]
    if book is REVIEW:
        for number, question, where in TEN_QUESTIONS:
            yield [literal("the ten questions"), literal(number), literal(question), literal(where)]
    for sheet in book.sheets:
        yield [literal("sheet"), literal(sheet.name), literal(sheet.purpose), literal("")]
        for column in sheet.columns:
            yield [
                literal("column"),
                literal(f"{sheet.name} › {column.header}"),
                literal(column.kind),
                literal(column.source),
            ]
        if sheet.warranted:
            yield [
                literal("column"),
                literal(f"{sheet.name} › {WARRANT_HEADER}"),
                literal("warrant"),
                literal("commits to every cell's warrant in the row"),
            ]


# ── writing, and reading back ─────────────────────────────────────────────────────────────────────────


def _planned(
    record: dict[str, Any], contexts: list[Ctx], book: Book
) -> Iterator[tuple[str, list[str] | None, Iterable[list[Fact]]]]:
    """Each worksheet of `book` to write: its name, its header (None for About) and its rows of Facts."""
    yield "About", None, _about_rows(record, book)
    for sheet in book.sheets:
        header = [column.header for column in sheet.columns] + ([WARRANT_HEADER] if sheet.warranted else [])
        if sheet.warranted:
            rows = (
                facts + [literal(warrants.row(sheet.name, [f.warrant for f in facts]))]
                for facts in sheet.rows(contexts)
            )
        else:
            rows = sheet.rows(contexts)
        yield sheet.name, header, rows


def _printable(text: str) -> str:
    """`text` with each character a cell cannot hold written as its escape, for naming a location."""
    escaped = FORBIDDEN_CHARACTERS.sub(lambda match: f"\\u{ord(match.group()):04x}", text)
    return escaped.replace("\r", "\\r")


def _encoded(fact: Fact) -> Any:
    """What a cell must hold: the value, or the reason it cannot hold it exactly and where the value is."""
    value = fact.value
    if isinstance(value, str):
        state = cell_text_state(value)
    elif isinstance(value, (int, float)):
        state = cell_number_state(value)
    else:
        state = "ok"
    if state == "ok":
        return value
    where = f"it is in studies.json: {_printable(fact.where)}" if fact.where else "TrialLedger's own text"
    return f"(not written: {CELL_REASONS[state]}; {where})"


def _chunks(
    name: str, header: list[str] | None, rows: Iterable[list[Fact]]
) -> Iterator[tuple[str, list[list[Fact]]]]:
    """A sheet's rows split over numbered worksheets, so no worksheet exceeds the row limit."""
    part, buffer, number = name, [], 1
    reserved = 1 if header is not None else 0
    for row in rows:
        if sheet_fits(len(buffer) + reserved) != "fits":
            yield part, buffer
            number += 1
            part, buffer = f"{name} {number}", []
        buffer.append(row)
    yield part, buffer


def contexts_for(record: dict[str, Any]) -> list[Ctx]:
    return [Ctx(study) for study in as_list(record.get("studies"))]


def write_workbook(record: dict[str, Any], path: Path, book: Book = REVIEW) -> int:
    """Write `record`'s `book` to `path` and certify it; raise WorkbookError on any difference. Returns the
    number of cells written."""
    contexts = contexts_for(record)
    cells = _write(record, path, contexts, book)
    problems = certify(record, path, book=book, contexts=contexts, limit=1)
    if problems:
        raise WorkbookError("workbook.readback_mismatch", problems[0])
    return cells


def _write(record: dict[str, Any], path: Path, contexts: list[Ctx], book: Book) -> int:
    output = Workbook(write_only=True)
    bold = Font(bold=True)
    written = 0
    for name, header, rows in _planned(record, contexts, book):
        for part, part_rows in _chunks(name, header, rows):
            sheet = output.create_sheet(part)
            if header is not None:
                sheet.freeze_panes = "B2"
                cells = []
                for text in header:
                    cell = WriteOnlyCell(sheet, value=text)
                    cell.data_type = "s"
                    cell.font = bold
                    cells.append(cell)
                sheet.append(cells)
                written += len(cells)
            for facts in part_rows:
                sheet.append([_cell(sheet, fact) for fact in facts])
                written += len(facts)
    output.save(path)
    return written


def _cell(sheet: Any, fact: Fact) -> Any:
    encoded = _encoded(fact)
    cell = WriteOnlyCell(sheet, value=encoded)
    if isinstance(encoded, str):
        cell.data_type = "s"  # never a formula or an error code: text is text
        if fact.url and encoded == fact.value:
            cell.hyperlink = fact.url
    return cell


# Reading a file that is not this workbook can raise almost anything from the zip, XML and spreadsheet
# readers (a missing shared string, an unknown compression method, a broken part); each is named as a
# problem, never passed on. The derivation runs outside these handlers, so only reading is caught.
READ_ERRORS = (Exception,)


def _unreadable(path: Path, error: BaseException) -> str:
    return (
        f"workbook.unreadable: {path.name} cannot be read as this workbook ({type(error).__name__}: {error})"
    )


def _same(want: Any, have: Any) -> bool:
    """Whether a cell read back holds exactly what was written: the same kind of value and the same value.
    A float compares as the double it is (an integral one reads back as an int); a boolean is never taken
    for a number, nor a number for a boolean, nor text for either."""
    if isinstance(want, bool) or isinstance(have, bool):
        return type(want) is type(have) and want == have
    if isinstance(want, float):
        if not isinstance(have, (int, float)):
            return False
        held = float(have)
        return held == want and math.copysign(1.0, held) == math.copysign(1.0, want)
    return type(want) is type(have) and want == have


def _row_problems(part: str, want_rows: list[list[Any]], got: Iterator[Any], room: int) -> list[str]:
    problems: list[str] = []
    for number, want in enumerate(want_rows, start=1):
        have = next(got, None)
        if have is None:
            problems.append(f"{part} row {number} is missing")
            return problems
        expected = [None if value == "" else value for value in want]
        found = list(have) + [None] * max(0, len(expected) - len(have))
        exact = all(_same(w, h) for w, h in zip(expected, found, strict=False))
        if not exact or any(value is not None for value in found[len(expected) :]):
            problems.append(f"{part} row {number}: expected {expected!r}, found {list(have)!r}")
            if len(problems) >= room:
                return problems
    if next(got, None) is not None:
        problems.append(f"{part} holds rows that the record does not derive")
    return problems


def certify(
    record: dict[str, Any],
    path: Path,
    *,
    book: Book = REVIEW,
    contexts: list[Ctx] | None = None,
    limit: int = 20,
) -> list[str]:
    """Re-derive every sheet of `book` from `record` and compare it with `path`, cell by cell: the kind of
    value and the value, the warrants included.

    Returns the differences found, at most `limit`; an empty list certifies what the cells hold. A file that
    cannot be read as this workbook is named, never raised. Links, formats and layout are compared by
    file_problems.
    """
    contexts = contexts if contexts is not None else contexts_for(record)
    try:
        opened = load_workbook(path, read_only=True)
    except READ_ERRORS as error:
        return [_unreadable(path, error)]
    problems: list[str] = []
    try:
        expected_names = []
        for name, header, rows in _planned(record, contexts, book):
            for part, part_rows in _chunks(name, header, rows):
                expected_names.append(part)
                if part not in opened.sheetnames:
                    problems.append(f"{path.name}: sheet {part!r} is missing")
                    continue
                want_rows = ([header] if header is not None else []) + [
                    [_encoded(fact) for fact in facts] for facts in part_rows
                ]
                try:
                    found = _row_problems(
                        part, want_rows, opened[part].iter_rows(values_only=True), limit - len(problems)
                    )
                except READ_ERRORS as error:
                    return [*problems, _unreadable(path, error)][:limit]
                problems.extend(found)
                if len(problems) >= limit:
                    return problems[:limit]
        if opened.sheetnames != expected_names:
            problems.append(
                f"{path.name}: sheets {opened.sheetnames} differ from the derivation's {expected_names}"
            )
    finally:
        opened.close()
    return problems[:limit]


# The write times openpyxl stamps into docProps/core.xml: the only bytes two writes of one record differ in.
_WRITE_TIMES = re.compile(rb"<dcterms:(created|modified)\b[^>]*>[^<]*</dcterms:\1>")
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PACKAGE_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def file_problems(record: dict[str, Any], path: Path, book: Book = REVIEW) -> list[str]:
    """Whether `path` is, part for part and byte for byte, the file this version writes for `record`'s `book`,
    the write times in docProps/core.xml aside. certify compares what the cells hold; this compares everything
    else a reader is shown, links, formats and layout included, and any part added to the file."""
    with tempfile.TemporaryDirectory() as scratch:
        fresh = Path(scratch) / book.name
        _write(record, fresh, contexts_for(record), book)
        try:
            with zipfile.ZipFile(path) as have, zipfile.ZipFile(fresh) as want:
                if have.namelist() != want.namelist():
                    added = sorted(set(have.namelist()) - set(want.namelist()))
                    missing = sorted(set(want.namelist()) - set(have.namelist()))
                    return [
                        f"workbook.file_differs: {path.name}: the file's parts are not those this version "
                        f"writes (added {added}, missing {missing}, or in another order)"
                    ]
                labels = _part_labels(want)
                problems = []
                for name in want.namelist():
                    offset = _first_difference(have, want, name)
                    if offset is not None:
                        problems.append(
                            f"workbook.file_differs: {path.name}: {name}{labels.get(name, '')} differs from "
                            f"what this version writes for the record, from byte {offset}: a change beyond "
                            "the cell values (a link, a format, the layout)"
                        )
                return problems
        except READ_ERRORS as error:
            return [_unreadable(path, error)]


def _part_labels(archive: zipfile.ZipFile) -> dict[str, str]:
    """Each worksheet's parts in the archive (its XML and its links), labelled with the sheet's name."""
    relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.get("Id"): rel.get("Target", "") for rel in relations.iter(f"{_PACKAGE_REL}Relationship")}
    labels = {}
    for sheet in ElementTree.fromstring(archive.read("xl/workbook.xml")).iter(f"{_MAIN}sheet"):
        target = targets.get(sheet.get(f"{_DOC_REL}id"), "")
        member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(f"xl/{target}")
        links = posixpath.join(posixpath.dirname(member), "_rels", posixpath.basename(member) + ".rels")
        labels[member] = f" (the {sheet.get('name')} sheet)"
        labels[links] = f" (the {sheet.get('name')} sheet's links)"
    return labels


def _first_difference(have: zipfile.ZipFile, want: zipfile.ZipFile, name: str) -> int | None:
    """The first byte at which one part differs between two archives, or None when it is the same."""
    if name == "docProps/core.xml":
        streams = [_WRITE_TIMES.sub(b"", have.read(name))], [_WRITE_TIMES.sub(b"", want.read(name))]
        pairs: Iterator[tuple[bytes, bytes]] = zip(*streams, strict=True)
    else:
        pairs = _chunk_pairs(have, want, name)
    offset = 0
    for ours, theirs in pairs:
        if ours != theirs:
            return offset + next(
                (i for i, (a, b) in enumerate(zip(ours, theirs, strict=False)) if a != b),
                min(len(ours), len(theirs)),
            )
        offset += len(ours)
    return None


def _chunk_pairs(have: zipfile.ZipFile, want: zipfile.ZipFile, name: str) -> Iterator[tuple[bytes, bytes]]:
    with have.open(name) as ours, want.open(name) as theirs:
        while True:
            pair = ours.read(1 << 20), theirs.read(1 << 20)
            yield pair
            if not pair[0] or not pair[1]:
                return
