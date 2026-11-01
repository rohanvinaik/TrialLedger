"""Edit checks: approved relations among one study record's structured fields (openspec add-review-workbook).

Each relation is the registry's own, quoted in APPROVED_CHECKS with its definitions anchor: P is
https://clinicaltrials.gov/policy/protocol-definitions, R is .../results-definitions. Every decision below is
a pure function of the facts it names and returns one of four outcomes:
  "consistent"     — the rule applies and holds;
  "conflict"       — the rule applies and is violated;
  "not_applicable" — the rule's condition does not arise in this record;
  "not_checkable"  — a value the rule needs is absent, or too imprecise to decide it.
A missing input is never "consistent". A conflict changes nothing: both values stay in the record and in
every view, exactly as the registry wrote them. No check reads free text.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any, TypeGuard

from TrialLedger.ledger import get as _get
from TrialLedger.ledger import location
from TrialLedger.registry import enum_labels

CHECKS_VERSION = 2
CLOSED_STATUSES = ("COMPLETED", "TERMINATED")
# Statuses the registry assigns itself (glossary, «Last verified»; metadata overallStatus rules on Withheld),
# so they are not the responsible party's statement about recruitment.
REGISTRY_ASSIGNED_STATUSES = ("UNKNOWN", "WITHHELD")
# The registry's labels for InterventionType (/studies/enums legacyValue), which arms use to name
# interventions as "<label>: <name>" (5,362 of 5,362 sample entries, 2026-10-31).
INTERVENTION_TYPE_LABELS = enum_labels("InterventionType")

_AGE = re.compile(r"([0-9]{1,9}) (Year|Years|Month|Months|Week|Weeks|Day|Days|Hour|Hours|Minute|Minutes)")
_MONTHS_PER_UNIT = {"Year": 12, "Years": 12, "Month": 1, "Months": 1}
_MINUTES_PER_UNIT = {
    "Week": 10080,
    "Weeks": 10080,
    "Day": 1440,
    "Days": 1440,
    "Hour": 60,
    "Hours": 60,
    "Minute": 1,
    "Minutes": 1,
}
_PARTIAL_DATE = re.compile(r"([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?")


def _is_count(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# ── the decisions ────────────────────────────────────────────────────────────────────────────────────


def closed_date_actual(overall_status: str | None, date_type: str | None) -> str:
    """Whether a completed or terminated study's completion date is typed actual (pure — pinned).

    Once a study is completed (last participant's last visit) or terminated (participants no longer
    examined), its completion dates have been reached, and the responsible party «must update» them «to
    reflect the actual» date (P#LastFollowUpDate).
      "not_checkable"  — no overall status, or a closed study whose date type is not reported.
      "not_applicable" — the study is neither COMPLETED nor TERMINATED.
      "consistent"     — the date is typed ACTUAL.
      "conflict"       — the date is typed anything else (ESTIMATED).
    """
    if overall_status is None:
        return "not_checkable"
    if overall_status not in CLOSED_STATUSES:
        return "not_applicable"
    if date_type is None:
        return "not_checkable"
    return "consistent" if date_type == "ACTUAL" else "conflict"


def withdrawn_enrollment_zero(
    overall_status: str | None, enrollment_type: str | None, enrollment_count: int | None
) -> str:
    """Whether a withdrawn study's actual enrollment is zero (pure — pinned).

    Withdrawn means «halted prematurely, prior to enrollment of first participant» (P#OverallStatus), so an
    ACTUAL enrollment count can only be 0. An ESTIMATED count is a target, which the rule does not concern.
      "not_checkable"  — no status; a withdrawn study without an enrollment type, or without a whole count.
      "not_applicable" — not WITHDRAWN, or the enrollment is not typed ACTUAL.
      "consistent"     — ACTUAL enrollment 0.
      "conflict"       — ACTUAL enrollment above 0.
    """
    if overall_status is None:
        return "not_checkable"
    if overall_status != "WITHDRAWN":
        return "not_applicable"
    if enrollment_type is None:
        return "not_checkable"
    if enrollment_type != "ACTUAL":
        return "not_applicable"
    if not _is_count(enrollment_count):
        return "not_checkable"
    return "consistent" if enrollment_count == 0 else "conflict"


def phase_interventional_only(study_type: str | None, phases: Any) -> str:
    """Whether a study that is not interventional carries no phase (pure — pinned).

    Study Phase is defined only under «Interventional Study Design (For interventional studies only)». The
    rule is a prohibition, so a record with no phases satisfies it; "NA" is the registry's "Not Applicable".
      "not_checkable"  — no study type, or phases that are not a list.
      "not_applicable" — the study is INTERVENTIONAL.
      "consistent"     — no phases, or only NA.
      "conflict"       — a phase other than NA.
    """
    if study_type is None:
        return "not_checkable"
    if study_type == "INTERVENTIONAL":
        return "not_applicable"
    if phases is None:
        return "consistent"
    if not isinstance(phases, list):
        return "not_checkable"
    return "consistent" if all(phase == "NA" for phase in phases) else "conflict"


def results_flag_first_submit(has_results: bool | None, first_submit_present: bool) -> str:
    """Whether hasResults agrees with the field the registry computes it from (pure — pinned).

    The metadata defines hasResults as «FUNC Present(ResultsFirstSubmitDate)».
      "not_checkable" — hasResults is absent or not a boolean.
      "consistent"    — the flag equals the presence of resultsFirstSubmitDate.
      "conflict"      — it does not.
    """
    if not isinstance(has_results, bool):
        return "not_checkable"
    return "consistent" if has_results == first_submit_present else "conflict"


def recruiting_site_recruiting_study(overall_status: str | None, site_statuses: list[str | None]) -> str:
    """Whether a multi-site study with a recruiting site is itself recruiting (pure — pinned).

    P#OverallStatus: «If at least one facility in a multi-site clinical study has an Individual Site Status
    of "Recruiting," then the Overall Recruitment Status for the study must be "Recruiting."»
      "not_checkable"  — no overall status; an overall status the registry assigned (UNKNOWN, WITHHELD); or
                         no reported site recruiting while some site status is unreported.
      "not_applicable" — fewer than two sites, or every site reports a status and none is RECRUITING.
      "consistent"     — a site is RECRUITING and so is the study.
      "conflict"       — a site is RECRUITING and the study is not.
    """
    if overall_status is None or overall_status in REGISTRY_ASSIGNED_STATUSES:
        return "not_checkable"
    if len(site_statuses) < 2:
        return "not_applicable"
    if "RECRUITING" in site_statuses:
        return "consistent" if overall_status == "RECRUITING" else "conflict"
    return "not_checkable" if None in site_statuses else "not_applicable"


def member(value: Any, defined: list[Any]) -> str:
    """Whether a cross-reference names something the same record defines (pure — pinned).

    "not_checkable" — the reference is absent.
    "consistent"    — it is among the defined values, exactly.
    "conflict"      — it names nothing the record defines.
    """
    if value is None:
        return "not_checkable"
    return "consistent" if value in defined else "conflict"


def bounded(count: int | None, bound: int | None) -> str:
    """Whether a participant count is at most the count that contains it (pure — pinned).

    "not_checkable" — either is absent or not a whole number.
    "consistent"    — count ≤ bound.
    "conflict"      — count > bound.
    """
    if _is_count(count) and _is_count(bound):
        return "consistent" if count <= bound else "conflict"
    return "not_checkable"


def at_risk(event_at_risk: int | None, table_total: int | None) -> tuple[str, int | None]:
    """The number at risk for one adverse event in one group (pure — pinned).

    R#AdverseEventAtRisk: «Leave blank to indicate that the value specified as the total at risk in the
    arm/group for the table should be used.» A blank is never zero.
      ("stated", n)      — the event's own number at risk.
      ("group_total", n) — the event's is blank: the group's total at risk for the table.
      ("absent", None)   — both are blank.
    """
    if event_at_risk is not None:
        return "stated", event_at_risk
    if table_total is not None:
        return "group_total", table_total
    return "absent", None


def combine(outcomes: list[str]) -> str:
    """One record-level outcome from the outcomes of a check's entries (pure — pinned).

    A conflict anywhere is a conflict; otherwise any entry that could not be checked keeps the whole from
    being called consistent.
      "conflict", "not_checkable", "consistent" in that precedence; "not_applicable" when no entry was
      consistent, conflicting or uncheckable (including no entries at all).
    """
    if "conflict" in outcomes:
        return "conflict"
    if "not_checkable" in outcomes:
        return "not_checkable"
    if "consistent" in outcomes:
        return "consistent"
    return "not_applicable"


def age_magnitude(age: str | None) -> tuple[str, int | None]:
    """An age limit as a whole number within the unit family that converts exactly (pure — pinned).

    Ages are "<n> <unit>" (spec: EligibilityModule.minimumAge), n of at most nine digits; a longer number is
    unparseable. Years and months convert exactly (a year of
    age is twelve months of age); weeks, days, hours and minutes convert exactly; the two families do not.
      ("calendar", months), ("clock", minutes), ("absent", None), ("unparseable", None).
    """
    if age is None:
        return "absent", None
    match = _AGE.fullmatch(age) if isinstance(age, str) else None
    if match is None:
        return "unparseable", None
    number, unit = int(match.group(1)), match.group(2)
    if unit in _MONTHS_PER_UNIT:
        return "calendar", number * _MONTHS_PER_UNIT[unit]
    return "clock", number * _MINUTES_PER_UNIT[unit]


def age_limits_ordered(minimum_age: str | None, maximum_age: str | None) -> str:
    """Whether the minimum age is at most the maximum age (pure — pinned).

    An absent limit may mean «N/A (No limit)» or not reported (the metadata cannot tell), so it is never
    taken as either.
      "not_checkable" — either is absent or unparseable, or the units have no exact conversion.
      "consistent"    — minimum ≤ maximum.
      "conflict"      — minimum > maximum.
    """
    low_family, low = age_magnitude(minimum_age)
    high_family, high = age_magnitude(maximum_age)
    if low is None or high is None or low_family != high_family:
        return "not_checkable"
    return "consistent" if low <= high else "conflict"


def date_interval(text: str | None) -> tuple[str, tuple[int, int] | None]:
    """A registry partial date as the span of days it may denote, as day ordinals (pure — pinned).

    Dates are `yyyy`, `yyyy-MM` or `yyyy-MM-dd` (spec: PartialDate).
      ("year" | "month" | "day", (first, last)) — the precision written and the span it covers;
      ("absent", None); ("unparseable", None) for any other form or a day that does not exist.
    """
    if text is None:
        return "absent", None
    match = _PARTIAL_DATE.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        return "unparseable", None
    year, month, day = int(match.group(1)), match.group(2), match.group(3)
    try:
        if month is None:
            return "year", (date(year, 1, 1).toordinal(), date(year, 12, 31).toordinal())
        if day is None:
            last = calendar.monthrange(year, int(month))[1]
            return "month", (date(year, int(month), 1).toordinal(), date(year, int(month), last).toordinal())
        exact = date(year, int(month), int(day)).toordinal()
        return "day", (exact, exact)
    except ValueError:
        return "unparseable", None


def dates_ordered(earlier: str | None, later: str | None) -> str:
    """Whether a date that must come first does, reading partial dates as spans (pure — pinned).

    "not_checkable" — either is absent or unparseable, or the spans overlap so their order is open.
    "consistent"    — every day `earlier` may denote is on or before every day `later` may denote.
    "conflict"      — every day `earlier` may denote is after every day `later` may denote.
    """
    _, first = date_interval(earlier)
    _, second = date_interval(later)
    if first is None or second is None:
        return "not_checkable"
    if first[0] > second[1]:
        return "conflict"
    if first[1] <= second[0]:
        return "consistent"
    return "not_checkable"


def actual_dates_ordered(
    earlier: str | None, earlier_type: str | None, later: str | None, later_type: str | None
) -> str:
    """Whether two dates that must come in order do, where both record events that happened (pure — pinned).

    An ESTIMATED date is a forecast, and a forecast left standing after the event it forecast is out of date,
    not a contradiction: an estimated start still after an actual primary completion says only that the start
    was never updated. So the order is checked only between two ACTUAL dates (Codex's counterexample,
    2026-11-01, adopted).
      "not_checkable"  — a date type is not reported, or `dates_ordered` cannot decide.
      "not_applicable" — either date is typed other than ACTUAL.
      "consistent"     — both ACTUAL and in order.
      "conflict"       — both ACTUAL and certainly inverted.
    """
    if earlier_type is None or later_type is None:
        return "not_checkable"
    if earlier_type != "ACTUAL" or later_type != "ACTUAL":
        return "not_applicable"
    return dates_ordered(earlier, later)


def whole_count(text: str | None) -> int | None:
    """A participant count the registry stores as text, as a number (pure — pinned).

    The count when the text is a plain ASCII whole number; None otherwise, never a guess, and None for a
    number of more digits than Python converts to an integer.
    """
    if isinstance(text, str) and text.isascii() and text.isdigit():
        try:
            return int(text)
        except ValueError:  # past sys.get_int_max_str_digits(): no count TrialLedger can read
            return None
    return None


def reasons_account(not_completed: int | None, reasons: list[int | None]) -> str:
    """Whether the reasons for non-completion account for every participant not completed (pure — pinned).

    R#DWReason: «If reasons are provided, the total number of participants listed as Not Completed must be
    accounted for by all reasons for non-completion.»
      "not_applicable" — no reasons are provided.
      "not_checkable"  — the number not completed, or a reason's number, is not a whole number.
      "consistent"     — the reasons sum to the number not completed.
      "conflict"       — they do not.
    """
    if not reasons:
        return "not_applicable"
    counts = [reason for reason in reasons if _is_count(reason)]
    if not _is_count(not_completed) or len(counts) != len(reasons):
        return "not_checkable"
    return "consistent" if sum(counts) == not_completed else "conflict"


# ── the approved list, and the shell that gathers each check's facts from a record ────────────────────


@dataclass(frozen=True)
class Check:
    id: str
    relation: str
    rule: str  # the registry's own words, verbatim, with anchors

    @property
    def basis(self) -> str:
        return BASIS[self.id]

    @property
    def approval(self) -> str:
        return "approved" if self.id in APPROVED else "proposed"


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    outcome: str
    detail: str  # the fields and values involved, as the record holds them


CHECKS = (
    Check(
        "closed_primary_completion_actual",
        "Overall status COMPLETED or TERMINATED → primary completion date typed ACTUAL",
        "P#OverallStatus «Completed: The study has concluded normally; participants are no longer receiving "
        "an intervention or being examined (that is, last participant’s last visit has occurred)»; "
        "«Terminated: Study halted prematurely and will not resume; participants are no longer being "
        "examined or receiving intervention». P#LastFollowUpDate «Once the clinical study has reached the "
        "primary completion date, the responsible party must update the Primary Completion Date to reflect "
        "the actual primary completion date.»",
    ),
    Check(
        "closed_completion_actual",
        "Overall status COMPLETED or TERMINATED → study completion date typed ACTUAL",
        "The status definitions above. P#LastFollowUpDate «Once the clinical study has reached the study "
        "completion date, the responsible party must update the Study Completion Date to reflect the actual "
        "study completion date.»",
    ),
    Check(
        "withdrawn_actual_enrollment_zero",
        "Overall status WITHDRAWN and enrollment typed ACTUAL → enrollment 0",
        "P#OverallStatus «Withdrawn: Study halted prematurely, prior to enrollment of first participant»; "
        "P#IntEnrollment «the actual total number of participants that are enrolled in the clinical study»",
    ),
    Check(
        "phase_interventional_only",
        "Study type other than INTERVENTIONAL → no phase other than NA",
        "P#IntStudyDesign «Interventional Study Design (For interventional studies only)», containing "
        "P#StudyPhase «For a clinical trial of a drug product (including a biological product), the "
        "numerical phase of such clinical trial»",
    ),
    Check(
        "results_flag_first_submit",
        "hasResults true exactly when resultsFirstSubmitDate is present",
        "API metadata, hasResults: «FUNC Present(ResultsFirstSubmitDate)»; «Flag that indicates if a study "
        "has posted results on public site»",
    ),
    Check(
        "recruiting_site_recruiting_study",
        "Two or more locations, one RECRUITING → overall status RECRUITING",
        "P#OverallStatus «If at least one facility in a multi-site clinical study has an Individual Site "
        'Status of "Recruiting," then the Overall Recruitment Status for the study must be '
        '"Recruiting."» An overall UNKNOWN is the registry\'s own assignment (glossary, «Last verified»).',
    ),
    Check(
        "arm_interventions_declared",
        "Every intervention an arm names is '<type label>: <name>' of a declared intervention",
        "P#InterventionName «If multiple Arms or Groups have been specified, indicate which Interventions "
        "(or exposures) are in each Arm or Group of the study, using the Cross-Reference check boxes.» The "
        "label is the registry's enum table's legacyValue for the intervention's type.",
    ),
    Check(
        "intervention_arms_defined",
        "Every arm label an intervention names is the label of a defined arm",
        "P#InterventionName, as above (Arm or Group/Interventional Cross-Reference).",
    ),
    Check(
        "ae_counts_name_groups",
        "Every adverse-event count names one of the module's event groups",
        "API metadata: stats.groupId «Internal Arm/Group ID»; eventGroups.id «Internal group id». "
        "R#AdverseEventAffected «Number of participants, in each arm/group».",
    ),
    Check(
        "ae_affected_within_at_risk",
        "Per event and group: participants affected ≤ participants at risk",
        "R#AdverseEventAffected «Number of participants, in each arm/group, experiencing at least one event "
        "being reported.» R#AdverseEventAtRisk «Number of participants assessed, in each arm/group, for "
        "adverse events (that is, the denominator for calculating frequency of adverse events). Leave blank "
        "to indicate that the value specified as the total at risk in the arm/group for the table should be "
        "used.»",
    ),
    Check(
        "ae_event_within_group_total",
        "Per event and group: participants affected ≤ the group's total affected in that table",
        "R#SeriousTotalAffected «Overall number of participants affected by one or more Serious Adverse "
        "Events, for each arm/group.» R#OtherAE_Affected «Overall number of participants affected, for each "
        "arm/group, by at least one Other (Not Including Serious) Adverse Event(s) reported in the table.»",
    ),
    Check(
        "ae_events_at_least_affected",
        "Per event and group, where events are reported: events ≥ participants affected",
        "R#OtherAEEvents «Number of occurrences, in each arm/group, of the adverse event being reported.» "
        "R#AdverseEventAffected «experiencing at least one event being reported».",
    ),
    Check(
        "ae_group_totals_within_at_risk",
        "Per group: deaths, serious and other totals affected ≤ the matching total at risk",
        "R#Mortality_Affected «Overall number of participants, in each arm/group, who died due to any "
        "cause»; R#Mortality_AtRisk «included in the assessment of deaths due to any cause (that is, the "
        "denominator for calculating frequency of all-cause mortality)»; R#SeriousTotalAffected / "
        "R#SeriousAE_AtRisk and R#OtherAE_Affected / R#OtherAE_AtRisk likewise, each «(that is, the "
        "denominator for calculating frequency [...])».",
    ),
    Check(
        "flow_reasons_account",
        "Per period and group, where reasons are given: their participants sum to those not completed",
        "R#DWReason «If reasons are provided, the total number of participants listed as Not Completed must "
        "be accounted for by all reasons for non-completion.» R: Not Completed is «calculated automatically "
        "by subtracting Completed from Started».",
    ),
    Check(
        "age_limits_ordered",
        "Minimum age ≤ maximum age, where the units convert exactly",
        "P#EligibilityMinAge «The numerical value, if any, for the minimum age a potential participant must "
        "meet to be eligible for the clinical study.» P#EligibilityMaxAge «The numerical value, if any, for "
        "the maximum age a potential participant can be to be eligible for the clinical study.»",
    ),
    Check(
        "start_before_primary_completion",
        "Study start date ≤ primary completion date, both typed ACTUAL, partial dates read as intervals",
        "P#StartDate «the actual date on which the first participant was enrolled»; P#LastFollowUpDate «The "
        "date that the final participant was examined or received an intervention for the purposes of final "
        "collection of data for the primary outcome»",
    ),
    Check(
        "primary_completion_before_completion",
        "Primary completion date ≤ study completion date, both typed ACTUAL, partial dates read as intervals",
        "P#LastFollowUpDate: primary completion is final collection of data «for the primary outcome»; study "
        "completion is final collection «for the primary and secondary outcome measures and adverse events».",
    ),
)


# How each relation is grounded. "stated rule": the registry's text states it as a requirement ("must").
# "registry function": the API metadata defines one field as a function of another. "stated scope": the
# definitions limit an element to some study types. "entailed by definitions": two of the registry's
# definitions cannot both hold if the relation fails; the relation itself is TrialLedger's reading.
BASIS = {
    "closed_primary_completion_actual": "stated rule",
    "closed_completion_actual": "stated rule",
    "recruiting_site_recruiting_study": "stated rule",
    "flow_reasons_account": "stated rule",
    "results_flag_first_submit": "registry function",
    "phase_interventional_only": "stated scope",
    "withdrawn_actual_enrollment_zero": "entailed by definitions",
    "arm_interventions_declared": "entailed by definitions",
    "intervention_arms_defined": "entailed by definitions",
    "ae_counts_name_groups": "entailed by definitions",
    "ae_affected_within_at_risk": "entailed by definitions",
    "ae_event_within_group_total": "entailed by definitions",
    "ae_events_at_least_affected": "entailed by definitions",
    "ae_group_totals_within_at_risk": "entailed by definitions",
    "age_limits_ordered": "entailed by definitions",
    "start_before_primary_completion": "entailed by definitions",
    "primary_completion_before_completion": "entailed by definitions",
}

# The checks that run, approved by name here. Version 1 ran the five the registry states. Version 2
# (2026-11-01) adds the twelve its definitions entail: the founder asked that such rulings be settled from the
# registry's definitions, domain knowledge and logic, and Claude's reading and Codex's independent one agreed
# that each relation is entailed, after three conditions were met. The two date orders hold only between
# ACTUAL dates (Codex's counterexample: a stale forecast is not a contradiction). The arm cross-reference's
# "<label>: <name>" form is the API's own (2,468 of 2,468 NSCLC arm entries, 2026-11-01, beside 5,362 of 5,362
# earlier). No non-interventional study in the registry carries a phase (0 of 142,366 observational studies,
# none with expanded access, against 224,835 interventional ones with a phase, live, 2026-11-01), so the
# registry itself keeps the boundary the phase check reads.
APPROVED = frozenset(check.id for check in CHECKS)

# The pure decisions that apply each check; a check's warrant commits to their code and to run_checks'.
DECISIONS = {
    "closed_primary_completion_actual": (closed_date_actual,),
    "closed_completion_actual": (closed_date_actual,),
    "withdrawn_actual_enrollment_zero": (withdrawn_enrollment_zero,),
    "phase_interventional_only": (phase_interventional_only,),
    "results_flag_first_submit": (results_flag_first_submit,),
    "recruiting_site_recruiting_study": (recruiting_site_recruiting_study,),
    "arm_interventions_declared": (member, combine),
    "intervention_arms_defined": (member, combine),
    "ae_counts_name_groups": (member, combine),
    "ae_affected_within_at_risk": (at_risk, bounded, combine),
    "ae_event_within_group_total": (bounded, combine),
    "ae_events_at_least_affected": (bounded, combine),
    "ae_group_totals_within_at_risk": (bounded, combine),
    "flow_reasons_account": (whole_count, reasons_account, combine),
    "age_limits_ordered": (age_magnitude, age_limits_ordered),
    "start_before_primary_completion": (date_interval, dates_ordered, actual_dates_ordered),
    "primary_completion_before_completion": (date_interval, dates_ordered, actual_dates_ordered),
}


def _tally(outcomes: list[str], offenders: list[str]) -> str:
    counts = {name: outcomes.count(name) for name in ("consistent", "conflict", "not_checkable")}
    summary = ", ".join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n)
    if offenders:
        shown = "; ".join(offenders[:20]) + (
            f"; and {len(offenders) - 20} more" if len(offenders) > 20 else ""
        )
        return f"{summary}: {shown}"
    return summary or "no entries"


# ── the shell: each check's facts gathered from one record, only for the checks that run ───────────────

P = "protocolSection"
R = "resultsSection"
ARMS = (P, "armsInterventionsModule", "armGroups")
INTERVENTIONS = (P, "armsInterventionsModule", "interventions")
EVENTS = (R, "adverseEventsModule")
FLOW = (R, "participantFlowModule", "periods")


class Malformed(Exception):
    """A value a check reads is present but not of the type the registry gives it, so the check cannot run."""


def _text_at(study: Any, *path: str | int) -> str | None:
    """The text at `path` of the record, None when absent; Malformed when present and not text."""
    value = _get(study, *path)
    if value is None or isinstance(value, str):
        return value
    raise Malformed(f"{location(path)}={value!r} is not text")


def _list_at(study: Any, *path: str | int) -> list[Any]:
    """The list at `path`, empty when absent; Malformed when present and not a list."""
    value = _get(study, *path)
    if value is None:
        return []
    if not isinstance(value, list):
        raise Malformed(f"{location(path)} is not a list")
    return value


def _objects_at(study: Any, *path: str | int) -> list[dict[str, Any]]:
    """The objects listed at `path`; Malformed when the list holds anything else."""
    items = _list_at(study, *path)
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise Malformed(f"{location((*path, index))} is not an object")
    return items


def _unknown(count: int, what: str) -> str:
    return f"; {count} {what}" if count else ""


def _closed_completion(study: Any, struct: str) -> tuple[str, str]:
    overall = _text_at(study, P, "statusModule", "overallStatus")
    date_type = _text_at(study, P, "statusModule", struct, "type")
    return (
        closed_date_actual(overall, date_type),
        f"overallStatus={overall}; {struct}.type={date_type}; "
        f"{struct}.date={_get(study, P, 'statusModule', struct, 'date')}",
    )


def _gather_closed_primary_completion(study: Any) -> tuple[str, str]:
    return _closed_completion(study, "primaryCompletionDateStruct")


def _gather_closed_completion(study: Any) -> tuple[str, str]:
    return _closed_completion(study, "completionDateStruct")


def _gather_withdrawn(study: Any) -> tuple[str, str]:
    overall = _text_at(study, P, "statusModule", "overallStatus")
    kind = _text_at(study, P, "designModule", "enrollmentInfo", "type")
    count = _get(study, P, "designModule", "enrollmentInfo", "count")
    return (
        withdrawn_enrollment_zero(overall, kind, count),
        f"overallStatus={overall}; enrollmentInfo.type={kind}; enrollmentInfo.count={count}",
    )


def _gather_phase(study: Any) -> tuple[str, str]:
    study_type = _text_at(study, P, "designModule", "studyType")
    phases = _get(study, P, "designModule", "phases")
    if isinstance(phases, list) and not all(isinstance(phase, str) for phase in phases):
        raise Malformed(f"protocolSection.designModule.phases={phases!r} holds something other than text")
    return phase_interventional_only(study_type, phases), f"studyType={study_type}; phases={phases}"


def _gather_results_flag(study: Any) -> tuple[str, str]:
    has_results = _get(study, "hasResults")
    first_submit = _text_at(study, P, "statusModule", "resultsFirstSubmitDate")
    return (
        results_flag_first_submit(has_results, first_submit is not None),
        f"hasResults={has_results}; statusModule.resultsFirstSubmitDate={first_submit}",
    )


def _gather_recruiting_site(study: Any) -> tuple[str, str]:
    overall = _text_at(study, P, "statusModule", "overallStatus")
    path = (P, "contactsLocationsModule", "locations")
    statuses = [_text_at(study, *path, index, "status") for index in range(len(_objects_at(study, *path)))]
    return (
        recruiting_site_recruiting_study(overall, statuses),
        f"overallStatus={overall}; {len(statuses)} locations, {statuses.count('RECRUITING')} RECRUITING",
    )


def _gather_arm_interventions(study: Any) -> tuple[str, str]:
    declared, undetermined = [], 0
    for index in range(len(_objects_at(study, *INTERVENTIONS))):
        kind = _text_at(study, *INTERVENTIONS, index, "type")
        name = _text_at(study, *INTERVENTIONS, index, "name")
        if kind in INTERVENTION_TYPE_LABELS and name is not None:
            declared.append(f"{INTERVENTION_TYPE_LABELS[kind]}: {name}")
        else:
            undetermined += 1
    outcomes, offenders = [], []
    for a, arm in enumerate(_objects_at(study, *ARMS)):
        for n in range(len(_list_at(study, *ARMS, a, "interventionNames"))):
            name = _text_at(study, *ARMS, a, "interventionNames", n)
            outcome = member(name, declared)
            if outcome == "conflict" and undetermined:
                outcome = "not_checkable"  # it may name an intervention whose registry form is unknown
            outcomes.append(outcome)
            if outcome == "conflict":
                offenders.append(f"arm {arm.get('label')!r} names {name!r}")
    detail = _tally(outcomes, offenders) + _unknown(
        undetermined, "intervention(s) without a registry type or name"
    )
    return combine(outcomes), detail


def _gather_intervention_arms(study: Any) -> tuple[str, str]:
    labels = [_text_at(study, *ARMS, a, "label") for a in range(len(_objects_at(study, *ARMS)))]
    defined = [label for label in labels if label is not None]
    unlabelled = len(labels) - len(defined)
    outcomes, offenders = [], []
    for i, intervention in enumerate(_objects_at(study, *INTERVENTIONS)):
        for r in range(len(_list_at(study, *INTERVENTIONS, i, "armGroupLabels"))):
            label = _text_at(study, *INTERVENTIONS, i, "armGroupLabels", r)
            outcome = member(label, defined)
            if outcome == "conflict" and unlabelled:
                outcome = "not_checkable"  # it may name an arm whose label is not reported
            outcomes.append(outcome)
            if outcome == "conflict":
                offenders.append(f"intervention {intervention.get('name')!r} names arm {label!r}")
    return combine(outcomes), _tally(outcomes, offenders) + _unknown(unlabelled, "arm(s) without a label")


def _event_groups(study: Any) -> tuple[dict[str, dict[str, Any]], int]:
    """The event groups by id, and how many carry no id; Malformed when an id repeats."""
    groups = _objects_at(study, *EVENTS, "eventGroups")
    ids = [_text_at(study, *EVENTS, "eventGroups", g, "id") for g in range(len(groups))]
    named = [group_id for group_id in ids if group_id is not None]
    if len(set(named)) != len(named):
        raise Malformed(f"{location((*EVENTS, 'eventGroups'))} repeats a group id")
    by_id = {group_id: group for group_id, group in zip(ids, groups, strict=True) if group_id is not None}
    return by_id, len(ids) - len(named)


def _event_counts(study: Any) -> Iterator[tuple[str, str, str | None, dict[str, Any]]]:
    """Every count of the adverse-event tables: its table's prefix, where it is, its group id and itself."""
    for table, prefix in (("seriousEvents", "serious"), ("otherEvents", "other")):
        for e, event in enumerate(_objects_at(study, *EVENTS, table)):
            for s, stats in enumerate(_objects_at(study, *EVENTS, table, e, "stats")):
                group_id = _text_at(study, *EVENTS, table, e, "stats", s, "groupId")
                yield prefix, f"{table}[{e}] {event.get('term')!r} group {group_id}", group_id, stats


def _gather_ae_names(study: Any) -> tuple[str, str]:
    groups, unnamed = _event_groups(study)
    outcomes, offenders = [], []
    for _, where, group_id, _ in _event_counts(study):
        outcome = member(group_id, list(groups))
        if outcome == "conflict" and unnamed:
            outcome = "not_checkable"  # it may belong to a group whose id is not reported
        outcomes.append(outcome)
        if outcome == "conflict":
            offenders.append(where)
    return combine(outcomes), _tally(outcomes, offenders) + _unknown(unnamed, "event group(s) without an id")


def _gather_ae_at_risk(study: Any) -> tuple[str, str]:
    groups, _ = _event_groups(study)
    outcomes, offenders = [], []
    for prefix, where, group_id, stats in _event_counts(study):
        affected = stats.get("numAffected")
        source, risk = at_risk(stats.get("numAtRisk"), groups.get(group_id, {}).get(f"{prefix}NumAtRisk"))
        outcome = bounded(affected, risk)
        outcomes.append(outcome)
        if outcome == "conflict":
            offenders.append(f"{where}: {affected} affected > {risk} at risk ({source})")
    return combine(outcomes), _tally(outcomes, offenders)


def _gather_ae_group_total(study: Any) -> tuple[str, str]:
    groups, _ = _event_groups(study)
    outcomes, offenders = [], []
    for prefix, where, group_id, stats in _event_counts(study):
        affected = stats.get("numAffected")
        total = groups.get(group_id, {}).get(f"{prefix}NumAffected")
        outcome = bounded(affected, total)
        outcomes.append(outcome)
        if outcome == "conflict":
            offenders.append(f"{where}: {affected} affected > group total {total}")
    return combine(outcomes), _tally(outcomes, offenders)


def _gather_ae_events(study: Any) -> tuple[str, str]:
    outcomes, offenders = [], []
    for _, where, _, stats in _event_counts(study):
        occurrences = stats.get("numEvents")
        if occurrences is None:
            continue  # not reported, which is not zero
        affected = stats.get("numAffected")
        outcome = bounded(affected, occurrences)
        outcomes.append(outcome)
        if outcome == "conflict":
            offenders.append(f"{where}: {occurrences} events < {affected} affected")
    return combine(outcomes), _tally(outcomes, offenders)


def _gather_ae_group_totals(study: Any) -> tuple[str, str]:
    outcomes, offenders = [], []
    for g, group in enumerate(_objects_at(study, *EVENTS, "eventGroups")):
        group_id = _text_at(study, *EVENTS, "eventGroups", g, "id")
        for kind in ("deaths", "serious", "other"):
            affected, risk = group.get(f"{kind}NumAffected"), group.get(f"{kind}NumAtRisk")
            if affected is None and risk is None:
                continue
            outcome = bounded(affected, risk)
            outcomes.append(outcome)
            if outcome == "conflict":
                offenders.append(f"group {group_id} {kind}: {affected} affected > {risk} at risk")
    return combine(outcomes), _tally(outcomes, offenders)


def _gather_flow_reasons(study: Any) -> tuple[str, str]:
    outcomes, offenders = [], []
    for p, period in enumerate(_objects_at(study, *FLOW)):
        milestones: dict[str | None, tuple[str | int, ...]] = {}
        for m in range(len(_objects_at(study, *FLOW, p, "milestones"))):
            kind = _text_at(study, *FLOW, p, "milestones", m, "type")
            if kind in milestones:
                raise Malformed(f"{location((*FLOW, p, 'milestones'))} repeats the milestone {kind!r}")
            milestones[kind] = (*FLOW, p, "milestones", m)
        by_group: dict[str, list[int | None]] = {}
        listed: list[set[str]] = []
        for d in range(len(_objects_at(study, *FLOW, p, "dropWithdraws"))):
            reasons = (*FLOW, p, "dropWithdraws", d, "reasons")
            here: set[str] = set()
            for r, reason in enumerate(_objects_at(study, *reasons)):
                group_id = _text_at(study, *reasons, r, "groupId")
                if group_id is None:
                    raise Malformed(f"{location((*reasons, r))} names no group")
                by_group.setdefault(group_id, []).append(whole_count(reason.get("numSubjects")))
                here.add(group_id)
            listed.append(here)
        for group_id, counts in by_group.items():
            not_completed = _not_completed(study, milestones, group_id)
            if any(group_id not in here for here in listed):
                outcome = "not_checkable"  # a reason the period lists gives this group no count
            else:
                outcome = reasons_account(not_completed, counts)
            outcomes.append(outcome)
            if outcome == "conflict":
                offenders.append(
                    f"period[{p}] {period.get('title')!r} group {group_id}: reasons sum to "
                    f"{sum(c for c in counts if c is not None)}, not completed {not_completed}"
                )
    return combine(outcomes), _tally(outcomes, offenders)


def _milestone_count(
    study: Any, milestones: dict[str | None, tuple[str | int, ...]], kind: str, group_id: str
) -> tuple[str, int | None]:
    """One group's count at one milestone: ("count", n); ("not_whole", None) when the count the record
    states is not a whole number; ("absent", None) when the milestone states none for the group."""
    path = milestones.get(kind)
    if path is None:
        return "absent", None
    achievements = _objects_at(study, *path, "achievements")
    groups = [_text_at(study, *path, "achievements", a, "groupId") for a in range(len(achievements))]
    if None in groups:
        raise Malformed(f"{location(path)} states a count for no group")
    found = [
        achievement for achievement, group in zip(achievements, groups, strict=True) if group == group_id
    ]
    if len(found) > 1:
        raise Malformed(f"{location(path)} states group {group_id} more than once")
    if not found:
        return "absent", None
    count = whole_count(found[0].get("numSubjects"))
    return ("count", count) if count is not None else ("not_whole", None)


def _not_completed(
    study: Any, milestones: dict[str | None, tuple[str | int, ...]], group_id: str
) -> int | None:
    """A group's number not completed: the NOT COMPLETED milestone's when it states one, else STARTED minus
    COMPLETED (R: «calculated automatically by subtracting Completed from Started»). None when a count the
    record states is not a whole number, or one the subtraction needs is missing."""
    state, count = _milestone_count(study, milestones, "NOT COMPLETED", group_id)
    if state != "absent":
        return count
    started = _milestone_count(study, milestones, "STARTED", group_id)[1]
    completed = _milestone_count(study, milestones, "COMPLETED", group_id)[1]
    return started - completed if started is not None and completed is not None else None


def _gather_ages(study: Any) -> tuple[str, str]:
    minimum = _get(study, P, "eligibilityModule", "minimumAge")
    maximum = _get(study, P, "eligibilityModule", "maximumAge")
    return age_limits_ordered(minimum, maximum), f"minimumAge={minimum}; maximumAge={maximum}"


def _dates(study: Any, first_struct: str, second_struct: str) -> tuple[str, str]:
    first = _get(study, P, "statusModule", first_struct, "date")
    second = _get(study, P, "statusModule", second_struct, "date")
    first_type = _text_at(study, P, "statusModule", first_struct, "type")
    second_type = _text_at(study, P, "statusModule", second_struct, "type")
    return (
        actual_dates_ordered(first, first_type, second, second_type),
        f"{first_struct}.date={first}; {first_struct}.type={first_type}; "
        f"{second_struct}.date={second}; {second_struct}.type={second_type}",
    )


def _gather_start_before_primary(study: Any) -> tuple[str, str]:
    return _dates(study, "startDateStruct", "primaryCompletionDateStruct")


def _gather_primary_before_completion(study: Any) -> tuple[str, str]:
    return _dates(study, "primaryCompletionDateStruct", "completionDateStruct")


# Each check's gatherer: it reads the check's facts from one record and applies the check's decisions.
GATHERERS: dict[str, Callable[[Any], tuple[str, str]]] = {
    "closed_primary_completion_actual": _gather_closed_primary_completion,
    "closed_completion_actual": _gather_closed_completion,
    "withdrawn_actual_enrollment_zero": _gather_withdrawn,
    "phase_interventional_only": _gather_phase,
    "results_flag_first_submit": _gather_results_flag,
    "recruiting_site_recruiting_study": _gather_recruiting_site,
    "arm_interventions_declared": _gather_arm_interventions,
    "intervention_arms_defined": _gather_intervention_arms,
    "ae_counts_name_groups": _gather_ae_names,
    "ae_affected_within_at_risk": _gather_ae_at_risk,
    "ae_event_within_group_total": _gather_ae_group_total,
    "ae_events_at_least_affected": _gather_ae_events,
    "ae_group_totals_within_at_risk": _gather_ae_group_totals,
    "flow_reasons_account": _gather_flow_reasons,
    "age_limits_ordered": _gather_ages,
    "start_before_primary_completion": _gather_start_before_primary,
    "primary_completion_before_completion": _gather_primary_before_completion,
}


# The record fields each check reads: where a value it reports is to be found when a cell cannot hold it.
STATUS = "protocolSection.statusModule"
READS: dict[str, tuple[str, ...]] = {
    "closed_primary_completion_actual": (f"{STATUS}.overallStatus", f"{STATUS}.primaryCompletionDateStruct"),
    "closed_completion_actual": (f"{STATUS}.overallStatus", f"{STATUS}.completionDateStruct"),
    "withdrawn_actual_enrollment_zero": (
        f"{STATUS}.overallStatus",
        "protocolSection.designModule.enrollmentInfo",
    ),
    "phase_interventional_only": (
        "protocolSection.designModule.studyType",
        "protocolSection.designModule.phases",
    ),
    "results_flag_first_submit": ("hasResults", f"{STATUS}.resultsFirstSubmitDate"),
    "recruiting_site_recruiting_study": (
        f"{STATUS}.overallStatus",
        "protocolSection.contactsLocationsModule.locations",
    ),
    "arm_interventions_declared": (location(ARMS), location(INTERVENTIONS)),
    "intervention_arms_defined": (location(ARMS), location(INTERVENTIONS)),
    "ae_counts_name_groups": (location(EVENTS),),
    "ae_affected_within_at_risk": (location(EVENTS),),
    "ae_event_within_group_total": (location(EVENTS),),
    "ae_events_at_least_affected": (location(EVENTS),),
    "ae_group_totals_within_at_risk": (f"{location(EVENTS)}.eventGroups",),
    "flow_reasons_account": (location(FLOW),),
    "age_limits_ordered": (
        "protocolSection.eligibilityModule.minimumAge",
        "protocolSection.eligibilityModule.maximumAge",
    ),
    "start_before_primary_completion": (
        f"{STATUS}.startDateStruct",
        f"{STATUS}.primaryCompletionDateStruct",
    ),
    "primary_completion_before_completion": (
        f"{STATUS}.primaryCompletionDateStruct",
        f"{STATUS}.completionDateStruct",
    ),
}


def run_checks(study: Any, *, include_proposed: bool = False) -> list[CheckResult]:
    """The approved checks on one study record, in CHECKS order; with include_proposed, every check.

    A check that does not run is never gathered, so nothing only it reads can affect the checks that do. A
    check whose input is present but malformed is not_checkable, and its detail names the value.
    """
    results = []
    for check in CHECKS:
        if not include_proposed and check.approval != "approved":
            continue
        try:
            outcome, detail = GATHERERS[check.id](study)
        except Malformed as malformed:
            outcome, detail = "not_checkable", f"malformed input: {malformed}"
        results.append(CheckResult(check.id, outcome, detail))
    return results
