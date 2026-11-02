"""landscape.xlsx: the clinical readout of a landscape.json record (add-agent-operation 4.3).

The workbook openspec/changes/add-agent-operation/workbook-design.md decides, derived from the record alone:
Read me, Trial index, Trial review (every trial's dossier, one block per trial, one row per labelled
statement), Eligibility, Outcomes and efficacy, Biomarkers, Safety, Across-trial findings and the Evidence
register, in that order. Every cell is a value of the record, shown by a named rule, or the record's silence
in words: "Not stated", "Not posted", "Not applicable" (only where the registry's definitions establish it),
"Unresolved — <reason>", "Proposed — ...", "Interpolated — ..."; never a blank, a dash or "N/A". Where the
design names something landscape.json (schema 2) does not carry (a short title, an assay, a specimen, an
anticipated threshold, a grade, an assessment schedule), the cell says "Not stated" and the register says the
record carries no such field. Nothing is read with a model: a criterion's role is `criteria.criterion_role`,
a named rule over its own words.

Each displayed value is a cell tuple (value, link, status, source, rule, inputs); the pure row functions build
every sheet's rows of them, the evidence register is derived from those rows, and the writer only lays them
out. The file is read back and refused unless every cell equals its derivation, and its bytes are the same for
the same record (the write times and the zip's member times are fixed).
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from copy import copy
from operator import itemgetter
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.pagebreak import Break

from TrialLedger import __version__
from TrialLedger.cells import ROW_LIMIT, cell_number_state, cell_text_state
from TrialLedger.criteria import SCOPES, criterion_role
from TrialLedger.landscape import ELIGIBILITY_TEXT, SCHEMA_VERSION
from TrialLedger.links import study_link

NAME = "landscape.xlsx"
VERSION = "readout-1"
NOT_STATED = "Not stated"
NOT_POSTED = "Not posted"
NOT_APPLICABLE = "Not applicable"
REDACTED = "Not stated — withheld by the registry (a withheld study's field)"
UNRESOLVED = "Unresolved — "
# Two statuses beside landscape.STATUSES: a field the design names that landscape.json does not carry, and
# TrialLedger's own words labelling a row (a section, an item, a statement type).
ABSENT = "absent_from_record"
LABEL = "label"
NOT_CARRIED = f"landscape.json (schema {SCHEMA_VERSION}) carries no such field"
STATUS_WORDS = {
    "known": "Known: stated by the record, or read by the named rule",
    "not_stated": "Not stated: the record holds no value",
    "not_posted": "Not posted: no results or document posted",
    "unresolved": "Unresolved: the rules cannot settle it from the record",
    "proposed": "Proposed: through a relation not approved",
    "interpolated": "Interpolated: assumed by an approved relation, or a guess from a name's wording; "
    "never a reading",
    ABSENT: "Not carried: " + NOT_CARRIED + "; the cell says Not stated",
    LABEL: "TrialLedger's own label",
}
MARKER_WORDS = {"abbreviation_stated": "abbreviated", "completeness_stated": "complete"}
HEADING_WORDS = {"inclusion": "Inclusion", "exclusion": "Exclusion", "unsectioned": "No heading"}
ROLE_RULE = "criteria.criterion_role"
CATEGORY_WORDS = {
    "PRIMARY": "Primary",
    "SECONDARY": "Secondary",
    "OTHER_PRE_SPECIFIED": "Other",
    "POST_HOC": "Post hoc",
}
OUTCOME_LABELS = (("primary", "Primary", "P"), ("secondary", "Secondary", "S"), ("other", "Other", "O"))
INVESTIGATIONAL = ("EXPERIMENTAL",)
COMPARATORS = ("ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DATE_TYPES = {"ACTUAL": "actual", "ESTIMATED": "anticipated"}
_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ](.+))?)?)?")
CHUNK = 16000  # characters per continued row: at most 32,000 UTF-16 code units, inside a cell's 32,767
FOOTER_LIMIT = 255  # Excel's limit on a header's or footer's text, its codes included
SECTIONS = (
    "1 Identification",
    "2 Population",
    "3 Arms and interventions",
    "4 Eligibility criteria",
    "5 Outcomes",
    "6 Biomarkers",
    "7 Efficacy",
    "8 Safety",
    "9 Exploratory assessments",
    "10 Protocol language, publications and open questions",
)
ACROSS = "Across trials: see the Trial IDs"
COHORT = "Cohort"

# Each sheet's columns: (header, width in characters, whether each value of it is entered in the register).
ID, CATEGORY, SUMMARY, VERBATIM, KEY = 17, 18, 42, 75, 22
READ_ME_COLUMNS = (("Topic", 34, False), ("Content", VERBATIM, False), ("Row key", 12, False))
INDEX_COLUMNS = (
    ("Trial ID", ID, True),
    ("Short title", SUMMARY, True),
    ("Phase", CATEGORY, True),
    ("Status", CATEGORY, True),
    ("Eligible population", SUMMARY, True),
    ("Treatment setting and line as registered", SUMMARY, True),
    ("Investigational treatment", SUMMARY, True),
    ("Comparator", SUMMARY, True),
    ("Enrollment (actual or anticipated)", CATEGORY, True),
    ("Primary outcome", SUMMARY, True),
    ("Primary outcome time frame", SUMMARY, True),
    ("Registry results", CATEGORY, True),
    ("Results publication", SUMMARY, True),
    ("Last registry update", CATEGORY, True),
    ("Dossier", CATEGORY, False),
    ("Evidence key", KEY, False),
)
REVIEW_COLUMNS = (
    ("Trial ID", ID, False),
    ("Section", CATEGORY, False),
    ("Item", 36, False),
    ("Statement type", 14, False),
    ("Statement or value", VERBATIM, True),
    ("Evidence key", KEY, False),
)
ELIGIBILITY_COLUMNS = (
    ("Trial ID", ID, False),
    ("Cohort or arm", CATEGORY, True),
    ("Heading", 14, True),
    ("Role", 30, True),
    ("Criterion number", 14, True),
    ("Criterion as written", VERBATIM, True),
    ("Typed reading", SUMMARY, True),
    ("Parameter", 22, True),
    ("Operator", 14, True),
    ("Value", 16, True),
    ("Unit", 14, True),
    ("Qualification or ambiguity", 35, True),
    ("Evidence key", KEY, False),
)
OUTCOME_COLUMNS = (
    ("Trial ID", ID, False),
    ("Outcome ID", 14, True),
    ("Category", 14, True),
    ("Title", SUMMARY, True),
    ("Entry type", CATEGORY, True),
    ("Group or comparison", 22, True),
    ("Analysis population", 22, True),
    ("Measure", 22, True),
    ("Value or estimate", 16, True),
    ("Unit", 16, True),
    ("Denominator", 14, True),
    ("Dispersion or confidence interval", 22, True),
    ("Statistical analysis", 22, True),
    ("Registry time frame", 35, True),
    ("Explicit assessment schedule", 22, True),
    ("Qualification", 35, True),
    ("Evidence key", KEY, False),
)
BIOMARKER_COLUMNS = (
    ("Trial ID", ID, False),
    ("Biomarker", 22, True),
    ("Role", 35, True),
    ("Population", 22, True),
    ("Assay", 14, True),
    ("Specimen", 14, True),
    ("Threshold", 16, True),
    ("Timing", 22, True),
    ("Words read from", 35, True),
    ("Evidence key", KEY, False),
)
SAFETY_COLUMNS = (
    ("Trial ID", ID, False),
    ("Group", 22, True),
    ("Event category", CATEGORY, True),
    ("Organ system", 30, True),
    ("Event term as written", 30, True),
    ("Grade as reported", 16, True),
    ("Grade source", 16, True),
    ("Participants affected", 14, True),
    ("Participants at risk", 14, True),
    ("Events", 14, True),
    ("Collection method", 22, True),
    ("Reporting period", 35, True),
    ("Qualification", 35, True),
    ("Evidence key", KEY, False),
)
FINDING_COLUMNS = (
    ("Finding ID", 14, False),
    ("Type", 22, True),
    ("Criterion or design feature", 35, True),
    ("Finding", SUMMARY, True),
    ("Trial IDs", 35, True),
    ("Supporting / assessable / total", 22, True),
    ("Exceptions and unknowns", 35, True),
    ("Rule or matching basis", 35, True),
    ("Evidence key", 14, False),
)
REGISTER_COLUMNS = (
    ("Evidence ID", 30, False),
    ("Trial ID", ID, False),
    ("Sheet", CATEGORY, False),
    ("Row key", KEY, False),
    ("Field", 22, False),
    ("Value as displayed", SUMMARY, False),
    ("Status", 30, False),
    ("Source kind", CATEGORY, False),
    ("Registry field or rule and version", SUMMARY, False),
    ("Source URL", 40, False),
    ("Inputs", 35, False),
    ("Retrieval date", CATEGORY, False),
)
# Each sheet in order: its name, columns, the panes frozen (through its identifying columns) and whether its
# first column is a Trial ID (the register names the trial and its page from it).
SHEETS = (
    ("Read me", READ_ME_COLUMNS, "B2", False),
    ("Trial index", INDEX_COLUMNS, "C2", True),
    ("Trial review", REVIEW_COLUMNS, "B2", True),
    ("Eligibility", ELIGIBILITY_COLUMNS, "B2", True),
    ("Outcomes and efficacy", OUTCOME_COLUMNS, "B2", True),
    ("Biomarkers", BIOMARKER_COLUMNS, "B2", True),
    ("Safety", SAFETY_COLUMNS, "B2", True),
    ("Across-trial findings", FINDING_COLUMNS, "B2", False),
    ("Evidence register", REGISTER_COLUMNS, "B2", True),
)
SHEET_NAMES = tuple(name for name, *_ in SHEETS)
CAPACITY = ROW_LIMIT - 1  # data rows a worksheet holds below its header row
# Fields of the design that landscape.json (schema 2) does not carry, each with what the cell says instead.
NOT_IN_RECORD = (
    ("Short title", "the registry's brief title"),
    ("Last registry update", "the registry's last update date"),
    ("Posted baseline characteristics", "the results section's baseline module"),
    ("Cohort or arm a criterion applies to", "a criterion's cohort or arm"),
    ("Biomarker assay, specimen and timing", "an assay, a specimen or an assessment time for a criterion"),
    ("Planning assumptions and anticipated thresholds", "the protocol's planning statements"),
    (
        "Analysis population, denominator and statistical analysis",
        "a posted measurement's analysis population, denominators and analyses",
    ),
    ("Grade and grade source", "an adverse event's grade"),
    ("Explicit assessment schedule", "an outcome's visit schedule (a time frame is not a schedule)"),
)


class ReadoutError(Exception):
    """Why landscape.xlsx was not written: the file read back does not hold its derivation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# ── one displayed value ───────────────────────────────────────────────────────────────────────────────


def cell(
    value: Any, status: str, source: str = "", rule: str = "", inputs: str = "", link: str = ""
) -> tuple:
    """One displayed value: (value, link, status, source, rule, inputs)."""
    return (value, link, status, source, rule, inputs)


def label(text: str) -> tuple:
    """TrialLedger's own words labelling a row."""
    return cell(text, LABEL)


def absent(field: str) -> tuple:
    """A field of the design that landscape.json does not carry: "Not stated", the register says why."""
    return cell(NOT_STATED, ABSENT, field, "", NOT_CARRIED)


def scalar_text(value: Any) -> str:
    """One item of a value as text (pure — pinned).

    None — "Not stated"; a boolean — "Yes" or "No"; a list or an object inside a value — its JSON, as held;
    anything else — its text as written.
    """
    if value is None:
        return NOT_STATED
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def plain(value: Any) -> Any:
    """A known value as a cell shows it (pure — pinned).

    An integer a cell holds exactly — the integer (a number cell; any other integer, its text); a list — each
    item's text (scalar_text), one per line; an object — "key: item" per key, one per line, in order; anything
    else — scalar_text. A value with nothing in it (an empty string, list or object, whitespace only) is "Not
    stated", never a blank.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value if cell_number_state(value) == "ok" else str(value)
    if isinstance(value, list):
        text = "\n".join(scalar_text(item) for item in value)
    elif isinstance(value, dict):
        text = "\n".join(f"{key}: {scalar_text(item)}" for key, item in value.items())
    else:
        text = scalar_text(value)
    return text if text.strip() else NOT_STATED


def shown(value: dict[str, Any]) -> tuple:
    """A landscape.json value envelope as one cell, its status in words (pure — pinned).

      known        — the value, plain;
      not_stated   — "Not applicable" when the ledger's absence state is not_applicable (the registry's
                     definitions limit the field to another study type); REDACTED when redacted; else
                     "Not stated";
      not_posted   — "Not posted";
      proposed, interpolated — "Proposed — <value>", "Interpolated — <value>";
      unresolved, or a status landscape.json does not define — "Unresolved — <the note, its codes' underscores
                     as spaces>" (the status then unresolved).
    The cell keeps the envelope's source, rule and note (as its inputs).
    """
    status, held, note = value["status"], value["value"], value["note"]
    source, rule = value["source"], value["rule"]
    if status == "known":
        return cell(plain(held), status, source, rule, note)
    if status == "not_stated":
        words = REDACTED if note == "redacted" else NOT_APPLICABLE if note == "not_applicable" else NOT_STATED
        return cell(words, status, source, rule, note)
    if status == "not_posted":
        return cell(NOT_POSTED, status, source, rule, note)
    if status in ("proposed", "interpolated"):
        return cell(f"{status.capitalize()} — {plain(held)}", status, source, rule, note)
    reason = note.replace("_", " ") if note else "the rules cannot settle it from the record"
    if status != "unresolved":
        reason = f"status {status!r} is not one landscape.json defines"
    return cell(UNRESOLVED + reason, "unresolved", source, rule, note)


def statement_type(kind: str, status: str) -> str:
    """A Trial review row's statement type (pure — pinned).

    Unresolved — the value is unresolved, proposed or interpolated: never established;
    Establishes — a reading by a named rule (`kind` "reading") that is known: a bounded reading the record
                  supports, never a clinical conclusion;
    Record says — anything else: what the record states, or that it states nothing.
    """
    if status in ("unresolved", "proposed", "interpolated"):
        return "Unresolved"
    if kind == "reading" and status == "known":
        return "Establishes"
    return "Record says"


def date_text(text: Any) -> str:
    """A registry date as the readout writes it, its precision kept (pure — pinned).

    "2026-11-01" — "01-Nov-2026"; "2026-11" — "Nov-2026"; "2026" — "2026"; a date with a time
    ("2026-10-30T09:00:03") — the date so written, then the time as written; a month outside 01-12, or any
    other text, as written; anything not text — "Not stated".
    """
    if not isinstance(text, str):
        return NOT_STATED
    found = _DATE.fullmatch(text)
    if found is None:
        return text
    year, month, day, time = found.groups()
    if month is None:
        return year
    if not 1 <= int(month) <= 12:
        return text
    written = f"{MONTHS[int(month) - 1]}-{year}" if day is None else f"{day}-{MONTHS[int(month) - 1]}-{year}"
    return written if time is None else f"{written} {time}"


def dated(value: dict[str, Any]) -> tuple:
    """A date envelope (an object of date and type, as held) as one cell (pure — pinned).

    A known object — its date (date_text) and, in brackets, its type: ACTUAL "actual", ESTIMATED
    "anticipated", any other type "type <TYPE>", none no bracket; anything else — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    kind = held.get("type")
    words = date_text(held.get("date"))
    if kind is not None:
        words += f" ({DATE_TYPES.get(kind, f'type {kind}')})"
    return cell(words, "known", value["source"], value["rule"], value["note"])


def enrolled(value: dict[str, Any]) -> tuple:
    """The enrollment envelope (an object of count and type, as held) as one cell (pure — pinned).

    A known object with an integer count — the count with its separators and, in brackets, ACTUAL "actual",
    ESTIMATED "anticipated", another type "type <TYPE>", none no bracket; with no count — "Not stated" and
    the type; anything else — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    count, kind = held.get("count"), held.get("type")
    whole = isinstance(count, int) and not isinstance(count, bool)
    words = f"{count:,}" if whole else NOT_STATED
    if kind is not None:
        words += f" ({DATE_TYPES.get(kind, f'type {kind}')})"
    return cell(words, "known", value["source"], value["rule"], value["note"])


def quoted(words: tuple[str, ...]) -> str:
    """Words read from a criterion, each in quotation marks, joined (pure — pinned)."""
    return ", ".join(f"“{word}”" for word in words)


def role_cell(text: str, heading: str) -> tuple:
    """A criterion's role beside its heading, as one cell (pure — pinned).

    criteria.criterion_role over the criterion's own words and its heading's section:
      the heading's role, read from the heading alone — "Inclusion" or "Exclusion" (known);
      a role its own words state — "<Role> — its own words: “...”", and "; written under the <Heading>
                     heading" when that heading is another (known: an exclusion under an inclusion heading),
                     or "; under no inclusion or exclusion heading" when there is none;
      unresolved — "Unresolved — its own words “...” conflict with the <Heading> heading" under a heading, or
                     "Unresolved — under no inclusion or exclusion heading" (and its words, if any).
    """
    role, words = criterion_role(text, heading)
    named = HEADING_WORDS.get(heading, heading)
    found = quoted(words)
    if role == "unresolved":
        if heading in SCOPES:
            reason = f"its own words {found} conflict with the {named} heading"
        else:
            reason = "under no inclusion or exclusion heading" + (
                f"; its own words: {found}" if words else ""
            )
        return cell(UNRESOLVED + reason, "unresolved", ELIGIBILITY_TEXT, ROLE_RULE, found)
    if not words:
        return cell(HEADING_WORDS[role], "known", ELIGIBILITY_TEXT, ROLE_RULE, "read from its heading")
    shown_role = f"{HEADING_WORDS[role]} — its own words: {found}"
    if heading not in SCOPES:
        shown_role += "; under no inclusion or exclusion heading"
    elif role != heading:
        shown_role += f"; written under the {named} heading"
    return cell(shown_role, "known", ELIGIBILITY_TEXT, ROLE_RULE, found)


def coordinate_cell(value: dict[str, Any]) -> tuple:
    """A design coordinate (the setting, the prior advanced lines) as one cell (pure — pinned).

    known — its one value; interpolated — "Interpolated — <values joined by |>" (why, in the register's
    inputs); proposed — "Proposed — <values>; <why>"; unresolved — "Unresolved — <n> values remain: <values>;
    <why>", or "Unresolved — no value remains (a conflict); <why>"; any other status — shown.
    """
    status, held, note = value["status"], value["value"], value["note"]
    if status not in ("known", "proposed", "interpolated", "unresolved") or not isinstance(held, list):
        return shown(value)
    values = " | ".join(str(item) for item in held)
    if status == "known":
        words = values or NOT_STATED
    elif status == "interpolated":
        words = f"Interpolated — {values}"
    elif status == "proposed":
        words = f"Proposed — {values}; {note}"
    elif held:
        words = f"{UNRESOLVED}{len(held)} values remain: {values}; {note}"
    else:
        words = f"{UNRESOLVED}no value remains (a conflict); {note}"
    return cell(words, status, value["source"], value["rule"], note)


def approved_coordinate(coordinates: dict[str, Any], name: str) -> dict[str, Any]:
    """A design coordinate under approved relations, as landscape.json schema 2 carries it (pure — pinned).

    The approved relations are the record's default relations, so their value is <name>_interpolated: that
    value when they narrow the coordinate (interpolated, or unresolved when they leave none); the known value
    <name>, with its own note, when they leave it as it is.
    """
    known, interpolated = coordinates[name], coordinates[f"{name}_interpolated"]
    return known if interpolated["value"] == known["value"] else interpolated


def proposals_cell(value: dict[str, Any], proposals: list[dict[str, Any]]) -> tuple:
    """A design coordinate as each proposed relation alone would narrow it, as one cell (pure — pinned).

    `value` is the coordinate under approved relations (approved_coordinate), `proposals`
    its <name>_proposed: one value for each proposed relation that narrows it.
      none narrowing it — `value` as coordinate_cell shows it, noted "no proposed relation narrows it";
      one or more      — each one's coordinate_cell words, one per line; the status unresolved when any is
                         (a conflict), else proposed; their rules and notes joined by "; ".
    """
    if not proposals:
        return coordinate_cell({**value, "note": "no proposed relation narrows it"})
    shown_each = [coordinate_cell(proposal) for proposal in proposals]
    status = "unresolved" if any(held[2] == "unresolved" for held in shown_each) else "proposed"
    return cell(
        "\n".join(held[0] for held in shown_each),
        status,
        value["source"],
        "; ".join(held[4] for held in shown_each),
        "; ".join(held[5] for held in shown_each),
    )


# ── a trial's criteria, read once for the dossier and the Eligibility listing ─────────────────────────


def numbered_criteria(study: dict[str, Any]) -> list[tuple]:
    """A trial's criteria in the eligibility text's order, numbered 1, 2, ... (pure — pinned).

    Each (number, piece, heading section, the criterion's text envelope, its atoms' envelopes), the
    inclusion, exclusion and unsectioned criteria merged by their piece number (their place in the text).
    """
    held = [
        (criterion["piece"], section, criterion["text"], criterion["atoms"])
        for section in ("inclusion", "exclusion", "unsectioned")
        for criterion in study[section]
    ]
    ordered = sorted(held, key=itemgetter(0))
    return [(number, *item) for number, item in enumerate(ordered, start=1)]


def joined(headers: tuple[str, ...], cells: tuple, source: str, rule: str) -> tuple:
    """Several cells shown as one, "<header>: <value>" per line, for a dossier row (pure — pinned).

    The status is unresolved when any cell's is unresolved, proposed or interpolated; else not_posted when
    any is not_posted; else known when any is known; else not_stated (nothing in them is stated). The source
    and rule are the given ones (the cells' own stay in their listing).
    """
    lines = [f"{header}: {held[0]}" for header, held in zip(headers, cells, strict=True)]
    statuses = {held[2] for held in cells}
    if statuses & {"unresolved", "proposed", "interpolated"}:
        status = "unresolved"
    elif "not_posted" in statuses:
        status = "not_posted"
    elif "known" in statuses:
        status = "known"
    else:
        status = "not_stated"
    return cell("\n".join(lines), status, source, rule)


ARM_FIELDS = (
    ("Label", "label"),
    ("Type", "type"),
    ("Description", "description"),
    ("Interventions", "interventionNames"),
)
INTERVENTION_FIELDS = (
    ("Type", "type"),
    ("Name", "name"),
    ("Other names", "otherNames"),
    ("Description", "description"),
    ("Arms", "armGroupLabels"),
)


def held_cell(value: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> tuple:
    """An object the record holds (an arm, an intervention) as one cell, field by field (pure — pinned).

    A known object — "<label>: <its field>" per line, in `fields`' order, a list's items joined by "; ", a
    field it does not hold (or holds empty) "Not stated"; anything else — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    lines = []
    for title, key in fields:
        item = held.get(key)
        text = "; ".join(scalar_text(part) for part in item) if isinstance(item, list) else scalar_text(item)
        lines.append(f"{title}: {text if text.strip() else NOT_STATED}")
    return cell("\n".join(lines), "known", value["source"], value["rule"], value["note"])


def class_cell(value: dict[str, Any]) -> tuple:
    """An experimental drug's class as one cell (pure — pinned).

    classified — "FDA established pharmacologic class (NLM RxClass): <classes>"; stated_by_record — "Class
    its own entry states: <classes>"; anything else — shown (unresolved, with its reason).
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    classes = "; ".join(str(item) for item in held.get("classes") or []) or NOT_STATED
    if held.get("state") == "classified":
        words = f"FDA established pharmacologic class (NLM RxClass): {classes}"
    else:
        words = f"Class its own entry states: {classes}"
    return cell(words, "known", value["source"], value["rule"], value["note"])


def modality_cell(value: dict[str, Any]) -> tuple:
    """An intervention's modality extraction as one cell (pure — pinned).

    "<property>: <value> (<polarity>; <scope>)", plain when known, "Interpolated — ..." when read from a
    name's stem; anything else — shown.
    """
    held, status = value["value"], value["status"]
    if status not in ("known", "interpolated") or not isinstance(held, dict):
        return shown(value)
    parts = [scalar_text(held.get(key)) for key in ("property", "value", "polarity", "scope")]
    words = f"{parts[0]}: {parts[1]} ({parts[2]}; {parts[3]})"
    if status == "interpolated":
        words = f"Interpolated — {words}"
    return cell(words, status, value["source"], value["rule"], value["note"])


def coverage_cell(eligibility: dict[str, Any]) -> tuple:
    """How the eligibility text was read, as one cell (pure — pinned).

    "Criteria: <itemized>; headings: <sectioning>; inclusion list: <evidence>; exclusion list: <evidence>",
    then each marker the text holds ("“<words>” says the <scope> list is abbreviated", or "complete"), codes'
    underscores as spaces; a coverage not known — shown.
    """
    itemized, coverage = eligibility["itemized"], eligibility["coverage"]
    held = coverage["value"]
    if coverage["status"] != "known" or not isinstance(held, dict):
        return shown(coverage)
    found = [
        scalar_text(item)
        for item in (itemized["value"], *map(held.get, ("sectioning", "inclusion", "exclusion")))
    ]
    words = (
        f"Criteria: {found[0]}; headings: {found[1]}; inclusion list: {found[2]}; exclusion list: {found[3]}"
    ).replace("_", " ")
    for marker in held.get("markers") or []:
        kind = MARKER_WORDS.get(marker.get("kind"), scalar_text(marker.get("kind")).replace("_", " "))
        text, scope = scalar_text(marker.get("text")), scalar_text(marker.get("scope"))
        words += f"\n“{text}” says the {scope} list is {kind}"
    return cell(words, "known", coverage["source"], coverage["rule"], coverage["note"])


def read_list_cell(value: dict[str, Any], none_read: str) -> tuple:
    """A list a rule read (endpoint classes, time points) as one cell (pure — pinned).

    Known and holding items — the items, one per line; known and empty — "Unresolved — <none_read>" (the rule
    read nothing, which is not a reading); anything else — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, list):
        return shown(value)
    if not held:
        return cell(UNRESOLVED + none_read, "unresolved", value["source"], value["rule"], value["note"])
    return cell(plain(held), "known", value["source"], value["rule"], value["note"])


def tier_cell(value: dict[str, Any]) -> tuple:
    """A criterion element's standard tier across the cohort as one cell (pure — pinned).

    Known — "<element>: standard tier <tier> (statement rate <r>; full-criteria interval <l> to <u>)";
    unresolved with an element — "Unresolved — <element>: <why> (...)"; the numbers, or the interval, left
    out where the profile gives none (an element not profiled); anything else — shown.
    """
    held = value["value"]
    if not isinstance(held, dict) or value["status"] not in ("known", "unresolved"):
        return shown(value)
    numbers = ""
    if held.get("statement_rate") is not None:
        numbers = f" (statement rate {held['statement_rate']}"
        if held.get("lower_bound") is not None:
            numbers += (
                f"; full-criteria interval {held['lower_bound']} to {scalar_text(held.get('upper_bound'))}"
            )
        numbers += ")"
    element = scalar_text(held.get("element"))
    if value["status"] == "known":
        words = f"{element}: standard tier {scalar_text(held.get('tier'))}{numbers}"
    else:
        words = f"{UNRESOLVED}{element}: {value['note'] or 'unresolved'}{numbers}"
    return cell(words, value["status"], value["source"], value["rule"], value["note"])


def publication_cell(value: dict[str, Any]) -> tuple:
    """A reference as one cell, linked to PubMed where it has a PMID (pure — pinned).

    "<citation>", "PMID: <pmid>" and "Role: <its registry type's role>", one per line; anything not a known
    object — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    lines = (
        scalar_text(held.get("citation")),
        f"PMID: {scalar_text(held.get('pmid'))}",
        f"Role: {scalar_text(held.get('role'))}",
    )
    link = held.get("pubmed") or ""
    return cell("\n".join(lines), "known", value["source"], value["rule"], value["note"], link)


DOCUMENT_FIELDS = (
    ("Type", "type"),
    ("Label", "label"),
    ("Protocol", "has_protocol"),
    ("Statistical analysis plan", "has_sap"),
    ("Consent form", "has_icf"),
    ("File", "filename"),
)


def document_cell(value: dict[str, Any]) -> tuple:
    """A posted document as one cell, linked to the registry's copy (pure — pinned).

    Its type, label, whether it holds the protocol, the analysis plan and the consent form, its file, then its
    date and upload date (date_text), one per line; anything not a known object — shown.
    """
    held = value["value"]
    if value["status"] != "known" or not isinstance(held, dict):
        return shown(value)
    lines = [f"{title}: {scalar_text(held.get(key))}" for title, key in DOCUMENT_FIELDS]
    lines += [f"Date: {date_text(held.get('date'))}", f"Uploaded: {date_text(held.get('upload_date'))}"]
    link = held.get("url") or ""
    return cell("\n".join(lines), "known", value["source"], value["rule"], value["note"], link)


P = "protocolSection"
REFERENCES = f"{P}.referencesModule.references"
ARMS = f"{P}.armsInterventionsModule.armGroups"
INTERVENTIONS = f"{P}.armsInterventionsModule.interventions"
OUTCOMES = f"{P}.outcomesModule"
DOCUMENTS = "documentSection.largeDocumentModule.largeDocs"
REGISTERED = (
    "Not applicable — registered endpoint",
    "",
    "known",
    OUTCOMES,
    "registry definitions: an outcome measure is a title, a description and a time frame",
    "",
)
NO_CLASS = "no rule names an endpoint class in the measure"
BIOMARKER_RULES = "banks.biomarker_status; banks.endpoint_classes"
NO_BIOMARKER = "no criterion or outcome the rules read names a biomarker"
NO_POINT = "the time frame states no number and unit the rules read"
RESULT_WORDS = "marked by the responsible party as reporting results; it supplies no efficacy values here"


def result_publications(study: dict[str, Any]) -> list[tuple]:
    """The study's results publications: references the registry types RESULT, each one cell (pure — pinned).

    "PMID <pmid>: <citation> — marked by the responsible party as reporting results; it supplies no
    efficacy values here", linked to PubMed (the citation alone when it has no PMID). A DERIVED or BACKGROUND
    reference is never one. None — an empty list.
    """
    found = []
    for value in study["publications"]:
        held = value["value"]
        if value["status"] != "known" or not isinstance(held, dict) or held.get("type") != "RESULT":
            continue
        citation = scalar_text(held.get("citation"))
        words = f"PMID {held.get('pmid')}: {citation}" if held.get("pmid") else citation
        link = held.get("pubmed") or ""
        found.append(cell(f"{words} — {RESULT_WORDS}", "known", value["source"], value["rule"], "", link))
    return found


def publication_note(study: dict[str, Any]) -> tuple:
    """The results publications beside a result that is not posted, as one cell (pure — pinned).

    "Results publication (registry type RESULT): <result_publications' words>", one per line, linked to the
    first; none — "Not stated" (the record holds no reference of registry type RESULT).
    """
    found = result_publications(study)
    if not found:
        return cell(
            NOT_STATED, "not_stated", REFERENCES, "links.reference_role", "no reference of type RESULT"
        )
    words = "\n".join(f"Results publication (registry type RESULT): {held[0]}" for held in found)
    return cell(words, "known", found[0][3], found[0][4], "", found[0][1])


# ── the dossier: one block per section, each entry (item, kind, cell) ─────────────────────────────────


def identification_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 1: identification, registry link, sponsor, phase, status, dates and enrollment (pure — pinned).

    Each (item, "record", cell): the record's own values, the registry page linked ("Not stated" when the
    study's NCT number gives no page).
    """
    nct, link = study["nct"], study["link"]
    if link:
        words = f"ClinicalTrials.gov record {nct['value']}"
        page = cell(words, "known", "studies[].link", "links.study_link", "", link)
    else:
        page = cell(NOT_STATED, "not_stated", "studies[].link", "links.study_link", "not an NCT number")
    return [
        ("Trial ID", "record", shown(nct)),
        ("Registry page", "record", page),
        ("Lead sponsor", "record", shown(study["sponsor"])),
        ("Phase", "record", shown(study["phases"])),
        ("Overall status", "record", shown(study["overall_status"])),
        ("Study type", "record", shown(study["study_type"])),
        ("Start date", "record", dated(study["start_date"])),
        ("Primary completion date", "record", dated(study["primary_completion_date"])),
        ("Completion date", "record", dated(study["completion_date"])),
        ("Enrollment (actual or anticipated)", "record", enrolled(study["enrollment"])),
    ]


def population_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 2: the eligible population and setting; separately, the enrolled population (pure — pinned).

    The conditions and the population fields as the record states them; the setting and the prior lines for
    advanced disease under approved relations (approved_coordinate) and with each proposed one alone
    (<name>_proposed; coordinate_cell, proposals_cell, readings); then the
    actual enrollment (the enrollment only when its type is ACTUAL, else "Not stated") and the posted
    baseline characteristics ("Not posted" when no results are posted, else not carried by the record).
    """
    population, enrollment = study["population"], study["enrollment"]
    coordinates = study["line_of_therapy_and_setting"]
    setting = approved_coordinate(coordinates, "setting")
    lines = approved_coordinate(coordinates, "prior_advanced_lines")
    held = enrollment["value"]
    if enrollment["status"] == "known" and isinstance(held, dict) and held.get("type") == "ACTUAL":
        actual = enrolled(enrollment)
    else:
        words = f"{NOT_STATED} — the registered enrollment is not actual"
        actual = cell(words, "not_stated", enrollment["source"])
    if study["efficacy"]["results"]["status"] == "not_posted":
        baseline = cell(NOT_POSTED, "not_posted", "hasResults", "ledger.results_state")
    else:
        baseline = absent("Posted baseline characteristics")
    return [
        ("Conditions", "record", shown(study["conditions"])),
        ("Minimum age", "record", shown(population["minimum_age"])),
        ("Maximum age", "record", shown(population["maximum_age"])),
        ("Sex", "record", shown(population["sex"])),
        ("Gender-based eligibility", "record", shown(population["gender_based"])),
        ("Gender eligibility description", "record", shown(population["gender_description"])),
        ("Healthy volunteers", "record", shown(population["healthy_volunteers"])),
        ("Standard age groups", "record", shown(population["std_ages"])),
        ("Treatment setting (approved relations)", "reading", coordinate_cell(setting)),
        (
            "Treatment setting with proposed relations",
            "reading",
            proposals_cell(setting, coordinates["setting_proposed"]),
        ),
        ("Prior lines for advanced disease (approved relations)", "reading", coordinate_cell(lines)),
        (
            "Prior lines for advanced disease with proposed relations",
            "reading",
            proposals_cell(lines, coordinates["prior_advanced_lines_proposed"]),
        ),
        ("Enrolled population: actual enrollment", "record", actual),
        ("Enrolled population: posted baseline characteristics", "record", baseline),
    ]


def arm_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 3: each arm, then each intervention with its drug class and modality where read (pure — pinned).

    An arm or an intervention field by field (held_cell); an experimental drug's class (class_cell; an
    intervention that is not one has no class row); each modality extraction (modality_cell). No arm, or no
    intervention, is one "Not stated" row.
    """
    entries = [(f"Arm {n}", "record", held_cell(arm, ARM_FIELDS)) for n, arm in enumerate(study["arms"], 1)]
    if not entries:
        entries.append(("Arms", "record", cell(NOT_STATED, "not_stated", ARMS)))
    if not study["interventions"]:
        entries.append(("Interventions", "record", cell(NOT_STATED, "not_stated", INTERVENTIONS)))
    for n, item in enumerate(study["interventions"], 1):
        entries.append((f"Intervention {n}", "record", held_cell(item["entry"], INTERVENTION_FIELDS)))
        klass = item["drug_class"]
        if klass["value"] is not None:
            entries.append((f"Intervention {n} drug class", "reading", class_cell(klass)))
        for m, modality in enumerate(item["modality"], 1):
            entries.append((f"Intervention {n} modality {m}", "reading", modality_cell(modality)))
    return entries


def criteria_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 4: how the text was read; inclusion criteria, exclusion criteria, then criteria whose role is
    unresolved (pure — pinned).

    Each criterion keeps its number (numbered_criteria) and names its heading; it goes under the role its own
    words and its heading give (criteria.criterion_role), and a role read from its words, or unresolved, has
    its own row (role_cell). A text with no criterion is shown whole.
    """
    numbered = numbered_criteria(study)
    entries = [("Eligibility text, as read", "reading", coverage_cell(study["eligibility"]))]
    if not numbered:
        whole = shown(study["eligibility"]["text"])
        entries.append(("Eligibility text (no criterion itemized)", "record", whole))
    groups: dict[str, list[tuple]] = {"inclusion": [], "exclusion": [], "unresolved": []}
    for number, _piece, heading, text, _atoms in numbered:
        role, words = criterion_role(text["value"], heading)
        groups[role].append((number, heading, text, role != heading or bool(words)))
    for role in ("inclusion", "exclusion", "unresolved"):
        for number, heading, text, read in groups[role]:
            entries.append((f"Criterion {number} (heading: {HEADING_WORDS[heading]})", "record", shown(text)))
            if read:
                entries.append((f"Criterion {number} role", "reading", role_cell(text["value"], heading)))
    return entries


def outcome_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 5: the primary, secondary and other registered outcomes, each with its registered time frame
    (pure — pinned).

    Per outcome: its measure, time frame and description as registered, and the endpoint classes and time
    points the rules read (read_list_cell). No outcome is one "Not stated" row; the explicit assessment
    schedule is not carried by the record (a time frame is never a visit schedule).
    """
    entries = []
    for kind, word, _ in OUTCOME_LABELS:
        for n, outcome in enumerate(study["outcomes"][kind], 1):
            name = f"{word} outcome {n}"
            classes = read_list_cell(outcome["endpoint_classes"], NO_CLASS)
            points = read_list_cell(outcome["time_points"], NO_POINT)
            entries += [
                (f"{name}: measure", "record", shown(outcome["measure"])),
                (f"{name}: registered time frame", "record", shown(outcome["time_frame"])),
                (f"{name}: description", "record", shown(outcome["description"])),
                (f"{name}: endpoint class read", "reading", classes),
                (f"{name}: time points read", "reading", points),
            ]
    if not entries:
        entries.append(("Registered outcomes", "record", cell(NOT_STATED, "not_stated", OUTCOMES)))
    entries.append(("Explicit assessment schedule", "record", absent("Explicit assessment schedule")))
    return entries


# ── facts shared by a listing and the dossier ─────────────────────────────────────────────────────────

BIOMARKER_HEADERS = tuple(header for header, *_ in BIOMARKER_COLUMNS[1:-1])
SAFETY_HEADERS = tuple(header for header, *_ in SAFETY_COLUMNS[1:-1])
OBSERVED_HEADERS = (
    "Category",
    "Group",
    "Measure",
    "Value",
    "Unit",
    "Dispersion",
    "Time frame",
    "Denominator",
    "Statistical analysis",
    "Class and category",
)


def biomarker_facts(study: dict[str, Any]) -> list[tuple]:
    """Each biomarker mention, as the Biomarkers listing's cells after the Trial ID (pure — pinned).

    (biomarker, role, population, assay, specimen, threshold, timing, words read from):
      a criterion's biomarker atom — role "Eligibility", population its effective section and the states it
          allows, threshold its params as the bank read them (else "Not stated"), the span it was read from;
      a primary or secondary outcome naming a biomarker endpoint — role "Unresolved" (measured by an outcome;
          the record does not say whether for response or safety), timing its time frame;
      an other pre-specified outcome naming one — role "Exploratory".
    Assay and specimen, and an eligibility mention's timing, are not carried by the record. No mention is one
    row of "Not stated".
    """
    roles = study["biomarkers"]
    facts = []
    for value in roles["eligibility"]:
        held, source, rule = value["value"], value["source"], value["rule"]
        states = ", ".join(str(state) for state in held["states"]) or "states not stated"
        params = "; ".join(f"{key} {item}" for key, item in held["params"].items())
        threshold = (
            cell(params, "known", source, rule) if params else cell(NOT_STATED, "not_stated", source, rule)
        )
        words = f"“{held['span']}” (criterion piece {held['piece']})"
        facts.append(
            (
                cell(held["biomarker"], "known", source, rule),
                cell("Eligibility", "known", source, rule),
                cell(f"{held['section']}: {states}", "known", source, rule),
                absent("Biomarker assay"),
                absent("Biomarker specimen"),
                threshold,
                absent("Biomarker timing"),
                cell(words, "known", source, rule, value["note"]),
            )
        )
    for role, values in (("outcome", roles["outcome"]), ("exploratory", roles["exploratory"])):
        for value in values:
            held, source, rule = value["value"], value["source"], value["rule"]
            if role == "exploratory":
                shown_role = cell("Exploratory (an other pre-specified outcome)", "known", source, rule)
            else:
                reason = (
                    f"measured by a {scalar_text(held['outcome_type'])} outcome; the record does not say "
                    "whether for response or safety"
                )
                shown_role = cell(UNRESOLVED + reason, "unresolved", source, rule)
            facts.append(
                (
                    cell(held["measure"], "known", source, rule),
                    shown_role,
                    cell(NOT_STATED, "not_stated", source, rule, "an outcome names no population"),
                    absent("Biomarker assay"),
                    absent("Biomarker specimen"),
                    cell(NOT_STATED, "not_stated", source, rule, "no threshold read"),
                    cell(plain(held["time_frame"]), "known", source, rule),
                    cell(held["measure"], "known", source, rule),
                )
            )
    if not facts:
        none = cell(NOT_STATED, "not_stated", ELIGIBILITY_TEXT, BIOMARKER_RULES, NO_BIOMARKER)
        facts.append((none,) * len(BIOMARKER_HEADERS))
    return facts


def dispersion_text(held: dict[str, Any]) -> str:
    """A posted measurement's dispersion as written (pure — pinned).

    "<dispersion type>: <spread>" when a spread is posted, "<dispersion type>: <lower> to <upper>" when limits
    are, a missing limit "Not stated"; neither — "Not stated".
    """
    kind = scalar_text(held.get("dispersion_type"))
    if held.get("spread") is not None:
        return f"{kind}: {held['spread']}"
    if held.get("lower_limit") is not None or held.get("upper_limit") is not None:
        return f"{kind}: {scalar_text(held.get('lower_limit'))} to {scalar_text(held.get('upper_limit'))}"
    return NOT_STATED


def observed_facts(value: dict[str, Any]) -> tuple:
    """One posted measurement as cells (pure — pinned).

    (category, group, measure, value, unit, dispersion, time frame, denominator, statistical analysis, class
    and category): the outcome type in words, the arm (else "Group <id>"), the parameter type, the value, the
    unit, dispersion_text, the time frame, each as posted ("Not stated" for what is not); the denominator and
    the statistical analysis are not carried by the record.
    """
    held, source, rule = value["value"], value["source"], value["rule"]
    kind = held.get("outcome_type")
    group = held.get("arm") if held.get("arm") is not None else f"Group {scalar_text(held.get('group_id'))}"
    parts = [str(part) for part in (held.get("class"), held.get("category")) if part is not None]
    return (
        cell(CATEGORY_WORDS.get(kind, scalar_text(kind)), "known", source, rule),
        cell(group, "known", source, rule),
        cell(scalar_text(held.get("param_type")), "known", source, rule),
        cell(scalar_text(held.get("value")), "known", source, rule),
        cell(scalar_text(held.get("unit")), "known", source, rule),
        cell(dispersion_text(held), "known", source, rule),
        cell(scalar_text(held.get("time_frame")), "known", source, rule),
        absent("Denominator"),
        absent("Statistical analysis"),
        cell(" / ".join(parts) or NOT_STATED, "known", source, rule),
    )


def safety_facts(study: dict[str, Any]) -> list[tuple]:
    """Each posted adverse-event row, as the Safety listing's cells after the Trial ID (pure — pinned).

    (group, event category, organ system, event term, grade, grade source, affected, at risk, events,
    collection method, reporting period, qualification). Per event group: its all-cause deaths, serious and
    other totals, each "group total"; then per event and group, as posted. Counts are integers as posted
    ("Not stated" where none: an at-risk count is never filled from a group's total); a grade is never
    carried by the record, and seriousness never stands in for it. Results not posted, or unresolved: one
    row, every value the results' own words, the qualification the results publications.
    """
    safety = study["safety"]
    period = shown(safety["time_frame"])
    results = safety["results"]
    if results["status"] != "known":
        state = shown(results)
        return [(state,) * 11 + (publication_note(study),)]
    facts = []
    for value in safety["groups"]:
        held, source, rule = value["value"], value["source"], value["rule"]
        group = cell(scalar_text(held.get("title")), "known", source, rule)
        for prefix, category, term in (
            ("deaths", "Deaths (all causes)", "All-cause mortality, group total"),
            ("serious", "Serious", "Any serious adverse event, group total"),
            ("other", "Other", "Any other adverse event, group total"),
        ):
            facts.append(
                (
                    group,
                    cell(category, "known", source, rule),
                    cell("All organ systems (group total)", "known", source, rule),
                    cell(term, "known", source, rule),
                    absent("Grade"),
                    absent("Grade source"),
                    cell(plain(held.get(f"{prefix}_affected")), "known", source, rule),
                    cell(plain(held.get(f"{prefix}_at_risk")), "known", source, rule),
                    absent("Events in a group total"),
                    absent("Collection method of a group total"),
                    period,
                    cell(NOT_STATED, "not_stated", source, rule),
                )
            )
    for value in safety["events"]:
        held, source, rule = value["value"], value["source"], value["rule"]
        group = (
            held.get("arm") if held.get("arm") is not None else f"Group {scalar_text(held.get('group_id'))}"
        )
        facts.append(
            (
                cell(group, "known", source, rule),
                cell(scalar_text(held.get("table")).capitalize(), "known", source, rule),
                cell(scalar_text(held.get("organ_system")), "known", source, rule),
                cell(scalar_text(held.get("term")), "known", source, rule),
                absent("Grade"),
                absent("Grade source"),
                cell(plain(held.get("affected")), "known", source, rule),
                cell(plain(held.get("at_risk")), "known", source, rule),
                cell(plain(held.get("events")), "known", source, rule),
                cell(scalar_text(held.get("assessment_type")), "known", source, rule),
                period,
                cell(f"Vocabulary: {scalar_text(held.get('source_vocabulary'))}", "known", source, rule),
            )
        )
    if not facts:
        none = cell(NOT_STATED, "not_stated", "resultsSection.adverseEventsModule", "", "no event posted")
        facts.append((none,) * 10 + (period, none))
    return facts


# ── the rest of the dossier ───────────────────────────────────────────────────────────────────────────


def biomarker_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 6: each biomarker mention, its role, population, assay, specimen, threshold and timing
    (pure — pinned).

    One row per biomarker_facts mention, its cells joined under the listing's headers ("reading" kind); no
    mention — one "Not stated" row.
    """
    roles = study["biomarkers"]
    if not (roles["eligibility"] or roles["outcome"] or roles["exploratory"]):
        return [
            (
                "Biomarkers",
                "record",
                cell(NOT_STATED, "not_stated", ELIGIBILITY_TEXT, BIOMARKER_RULES, NO_BIOMARKER),
            )
        ]
    entries = []
    for n, facts in enumerate(biomarker_facts(study), 1):
        value = joined(BIOMARKER_HEADERS, facts, facts[1][3], facts[1][4])
        entries.append((f"Biomarker {n}: {facts[0][0]}", "reading", value))
    return entries


def efficacy_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 7: planning assumptions (not carried by the record), then, separately, the registry's results
    and each posted observed result (pure — pinned).

    The results' state; each results publication (result_publications) beside it, or "Not stated"; each
    posted measurement (observed_facts joined) with its measure and group.
    """
    efficacy = study["efficacy"]
    entries = [
        ("Planning assumptions and anticipated thresholds", "record", absent("Planning assumptions")),
        ("Registry results", "record", shown(efficacy["results"])),
    ]
    found = result_publications(study)
    item = "Results publication (registry type RESULT)"
    entries += [(item, "record", held) for held in found] or [(item, "record", publication_note(study))]
    for n, value in enumerate(efficacy["measurements"], 1):
        facts = observed_facts(value)
        name = f"Observed result {n}: {scalar_text(value['value'].get('measure'))} — {facts[1][0]}"
        entries.append((name, "record", joined(OBSERVED_HEADERS, facts, value["source"], value["rule"])))
    return entries


def safety_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 8: the reporting period, the registry's results, then each posted adverse-event row with its
    denominators and counts apart (pure — pinned).

    One row per safety_facts row, its cells joined under the listing's headers ("record" kind); results not
    posted (or unresolved) — the results' row alone says so.
    """
    safety = study["safety"]
    entries = [
        ("Reporting period", "record", shown(safety["time_frame"])),
        ("Registry results", "record", shown(safety["results"])),
    ]
    if safety["results"]["status"] != "known":
        return entries
    for n, facts in enumerate(safety_facts(study), 1):
        name = f"Safety row {n}: {facts[1][0]}, {facts[3][0]} — {facts[0][0]}"
        entries.append((name, "record", joined(SAFETY_HEADERS, facts, facts[3][3], facts[3][4])))
    return entries


def exploratory_entries(study: dict[str, Any]) -> list[tuple]:
    """Block 9: exploratory assessments, the other pre-specified outcomes with their registry category
    (pure — pinned).

    Each with its measure and registered time frame; none — one "Not stated" row.
    """
    entries = []
    for n, outcome in enumerate(study["exploratory_measures"], 1):
        facts = (shown(outcome["measure"]), shown(outcome["time_frame"]))
        value = joined(("Measure", "Registered time frame"), facts, facts[0][3], "")
        entries.append((f"Exploratory {n} (registry category: other pre-specified)", "record", value))
    if not entries:
        source = f"{OUTCOMES}.otherOutcomes"
        entries.append(("Exploratory assessments", "record", cell(NOT_STATED, "not_stated", source)))
    return entries


def language_entries(study: dict[str, Any], questions: list[dict[str, Any]]) -> list[tuple]:
    """Block 10: standard protocol language, publications, protocol and analysis plan, open questions
    (pure — pinned).

    Each criterion element's standard tier across the cohort (tier_cell, by criterion number); each
    reference (publication_cell); each posted document (document_cell), none — "Not posted"; each review
    question of this trial (`questions` are the record's review queue rows), unresolved, never answered.
    """
    numbers = {piece: number for number, piece, *_ in numbered_criteria(study)}
    entries = [
        (
            f"Criterion {numbers.get(entry['piece'], entry['piece'])}: standard language",
            "reading",
            tier_cell(element),
        )
        for entry in study["standard_language"]
        for element in entry["elements"]
    ]
    entries += [
        (
            f"Publication {n} (registry type {scalar_text(value['value'].get('type'))})",
            "record",
            publication_cell(value),
        )
        for n, value in enumerate(study["publications"], 1)
    ] or [("Publications", "record", cell(NOT_STATED, "not_stated", REFERENCES))]
    documents = [
        (f"Document {n}", "record", document_cell(value)) for n, value in enumerate(study["documents"], 1)
    ]
    posted = cell(NOT_POSTED, "not_posted", DOCUMENTS, "", "no document posted")
    entries += documents or [("Protocol and statistical analysis plan", "record", posted)]
    nct = study["nct"]["value"]
    asked = [row for row in questions if row["nct"] == nct]
    for n, row in enumerate(asked, 1):
        options = " | ".join(scalar_text(option) for option in row["options"]) or NOT_STATED
        evidence = "; ".join(scalar_text(item) for item in row["evidence"]) or NOT_STATED
        words = (
            f"{scalar_text(row['question'])}\nOptions: {options}\nWhy: {scalar_text(row['why'])}\n"
            f"Evidence: {evidence}"
        )
        value = cell(UNRESOLVED + words, "unresolved", "review_queue", "review.flags_for", row["element"])
        entries.append((f"Open question {n}: {scalar_text(row['kind'])}", "reading", value))
    return entries


DOSSIER = (
    identification_entries,
    population_entries,
    arm_entries,
    criteria_entries,
    outcome_entries,
    biomarker_entries,
    efficacy_entries,
    safety_entries,
    exploratory_entries,
)


def review_rows(study: dict[str, Any], questions: list[dict[str, Any]]) -> list[tuple]:
    """A trial's dossier as Trial review rows, read top to bottom in the design's order (pure — pinned).

    Each block (DOSSIER, then language_entries) under its section's name; each row (Trial ID, section, item,
    statement type, statement or value, evidence key), the statement type statement_type's of the entry's
    kind and its cell's status, the key "<Trial ID>-R<nnn>" numbered from 1 in order.
    """
    trial = plain(study["nct"]["value"])
    blocks = [block(study) for block in DOSSIER] + [language_entries(study, questions)]
    rows = []
    for section, entries in zip(SECTIONS, blocks, strict=True):
        for item, kind, value in entries:
            key = f"{trial}-R{len(rows) + 1:03d}"
            kind_words = statement_type(kind, value[2])
            rows.append((label(trial), label(section), label(item), label(kind_words), value, label(key)))
    return rows


# ── the listings ──────────────────────────────────────────────────────────────────────────────────────


def arm_treatments(arms: list[dict[str, Any]], types: tuple[str, ...], none: str) -> tuple:
    """The arms of the given registry types, with their interventions, as one cell (pure — pinned).

    "<label> (<type>): <intervention names joined by '; '>" per arm whose type is one of `types`, one per
    line; no arm at all — "Not stated"; arms, none of these types — `none` (known: the arms say so).
    """
    if not arms:
        return cell(NOT_STATED, "not_stated", ARMS)
    lines = []
    for value in arms:
        held = value["value"]
        if value["status"] == "known" and isinstance(held, dict) and held.get("type") in types:
            names = "; ".join(str(name) for name in held.get("interventionNames") or []) or NOT_STATED
            lines.append(f"{scalar_text(held.get('label'))} ({held['type']}): {names}")
    return cell("\n".join(lines) or none, "known", ARMS, "readout.arm_treatments", ", ".join(types))


def population_cell(study: dict[str, Any]) -> tuple:
    """The eligible population as the index summarizes it, one field per line (pure — pinned).

    Conditions, ages (minimum to maximum), sex and healthy volunteers, each shown as the record states it.
    """
    population = study["population"]
    facts = (
        shown(study["conditions"]),
        cell(
            f"{shown(population['minimum_age'])[0]} to {shown(population['maximum_age'])[0]}",
            "known",
            "protocolSection.eligibilityModule",
        ),
        shown(population["sex"]),
        shown(population["healthy_volunteers"]),
    )
    return joined(("Conditions", "Ages", "Sex", "Healthy volunteers"), facts, "protocolSection", "")


def index_row(study: dict[str, Any], dossier: tuple[str, int]) -> tuple:
    """One trial's Trial index row, the landscape table's (pure — pinned).

    The Trial ID linked to its registry page; the short title and last update (not carried by the record);
    phase; status; eligible population (population_cell); the setting and prior lines as registered
    (approved_coordinate); the investigational and comparator arms (arm_treatments); enrollment, labelled
    actual or anticipated; the primary outcomes and their time frames, numbered; the registry's results; the
    results publication beside them (publication_note); the dossier's first row, `dossier` (its sheet and
    row), linked inside the workbook; the evidence key "<Trial ID>-I".
    """
    trial = plain(study["nct"]["value"])
    coordinates = study["line_of_therapy_and_setting"]
    setting = joined(
        ("Setting", "Prior lines for advanced disease"),
        (
            coordinate_cell(approved_coordinate(coordinates, "setting")),
            coordinate_cell(approved_coordinate(coordinates, "prior_advanced_lines")),
        ),
        ELIGIBILITY_TEXT,
        "coherence.resolve under approved relations",
    )
    primary = study["outcomes"]["primary"]
    if primary:
        measures = [(n, shown(o["measure"]), shown(o["time_frame"])) for n, o in enumerate(primary, 1)]
        measure = cell(
            "\n".join(f"{n}. {m[0]}" for n, m, _ in measures), "known", f"{OUTCOMES}.primaryOutcomes"
        )
        frame = cell(
            "\n".join(f"{n}. {f[0]}" for n, _, f in measures), "known", f"{OUTCOMES}.primaryOutcomes"
        )
    else:
        measure = frame = cell(NOT_STATED, "not_stated", f"{OUTCOMES}.primaryOutcomes")
    page = study["link"]
    sheet, row = dossier
    return (
        cell(trial, "known", "protocolSection.identificationModule.nctId", "links.study_link", "", page),
        absent("Short title"),
        shown(study["phases"]),
        shown(study["overall_status"]),
        population_cell(study),
        setting,
        arm_treatments(study["arms"], INVESTIGATIONAL, "No arm of the experimental type"),
        arm_treatments(study["arms"], COMPARATORS, "No comparator arm registered"),
        enrolled(study["enrollment"]),
        measure,
        frame,
        shown(study["efficacy"]["results"]),
        publication_note(study),
        absent("Last registry update"),
        cell(f"{sheet}, row {row}", LABEL, "", "", "", f"#'{sheet}'!A{row}"),
        label(f"{trial}-I"),
    )


def atom_cells(atoms: list[dict[str, Any]]) -> tuple:
    """A criterion's typed reading, parameter, operator, value, unit and qualification (pure — pinned).

    One line per atom the banks typed, in each of the six cells: "<concept> = <values joined by |>
    (<effective section>)"; the concept and its values; the comparator ("Not stated" when the bank read none);
    the value, or "<minimum> to <maximum>", or either bound alone; the unit; every other parameter ("<name>
    <value>"). Known, read by the atom's bank. No atom — "Unresolved — no rule typed this criterion" and five
    "Not stated".
    """
    if not atoms:
        untyped = cell(UNRESOLVED + "no rule typed this criterion", "unresolved", ELIGIBILITY_TEXT, "banks")
        none = cell(NOT_STATED, "not_stated", ELIGIBILITY_TEXT, "banks", "no atom")
        return (untyped, none, none, none, none, none)
    lines: list[list[str]] = [[], [], [], [], [], []]
    for value in atoms:
        held = value["value"]
        params = dict(held["params"])
        values = "|".join(str(item) for item in held["values"])
        lines[0].append(f"{held['concept']} = {values} ({held['section']})")
        lines[1].append(f"{held['concept']}: {', '.join(str(item) for item in held['values'])}")
        lines[2].append(params.pop("comparator", NOT_STATED))
        low, high = params.pop("minimum", None), params.pop("maximum", None)
        bounds = f"{low} to {high}" if low is not None and high is not None else low or high
        lines[3].append(params.pop("value", None) or bounds or NOT_STATED)
        lines[4].append(params.pop("unit", NOT_STATED))
        lines[5].append("; ".join(f"{key} {item}" for key, item in params.items()) or NOT_STATED)
    rule = "; ".join(dict.fromkeys(value["rule"] for value in atoms))
    return tuple(
        cell("\n".join(str(line) for line in column), "known", ELIGIBILITY_TEXT, rule) for column in lines
    )


def eligibility_rows(study: dict[str, Any]) -> list[tuple]:
    """A trial's Eligibility listing: one row per criterion, its heading and its role apart (pure — pinned).

    (Trial ID, cohort or arm (not carried by the record), heading, role (role_cell), criterion number,
    criterion as written, typed reading, parameter, operator, value, unit, qualification (atom_cells),
    evidence key "<Trial ID>-E<nnn>"), in the text's order. A text with no criterion is one row: the text
    whole (or "Not stated"), its role unresolved.
    """
    trial = plain(study["nct"]["value"])
    cohort = absent("Cohort or arm a criterion applies to")
    rows = []
    for number, piece, heading, text, atoms in numbered_criteria(study):
        rows.append(
            (
                label(trial),
                cohort,
                cell(HEADING_WORDS[heading], "known", ELIGIBILITY_TEXT, "criteria.itemize", f"piece {piece}"),
                role_cell(text["value"], heading),
                cell(number, "known", ELIGIBILITY_TEXT, "criteria.itemize", f"piece {piece}"),
                shown(text),
                *atom_cells(atoms),
                label(f"{trial}-E{number:03d}"),
            )
        )
    if not rows:
        whole = shown(study["eligibility"]["text"])
        reason = "the eligibility text holds no list of criteria"
        unread = cell(UNRESOLVED + reason, "unresolved", ELIGIBILITY_TEXT, "criteria.itemize")
        none = cell(NOT_STATED, "not_stated", ELIGIBILITY_TEXT, "criteria.itemize", "not itemized")
        heading = cell(HEADING_WORDS["unsectioned"], "known", ELIGIBILITY_TEXT, "criteria.itemize")
        rows.append(
            (label(trial), cohort, heading, unread, none, whole, *atom_cells([]), label(f"{trial}-E001"))
        )
    return rows


def outcome_rows(study: dict[str, Any]) -> list[tuple]:
    """A trial's Outcomes and efficacy listing: registered endpoints, the planning statement, then observed
    results, never in one column (pure — pinned).

    Each registered outcome (ID P1, S1, O1, ...): its title and registered time frame, "Not applicable" for a
    value (a registered endpoint carries none), its description and the endpoint classes read as its
    qualification. One anticipated row (planning assumptions are not carried by the record). Each posted
    measurement (ID R1, ...): observed_facts. Results not posted, or unresolved: one observed row of the
    results' own words, the results publications its qualification. The explicit assessment schedule is
    never carried; the evidence key is "<Trial ID>-O<nnn>".
    """
    trial = plain(study["nct"]["value"])
    schedule = absent("Explicit assessment schedule")
    entries = []
    for kind, word, prefix in OUTCOME_LABELS:
        for n, outcome in enumerate(study["outcomes"][kind], 1):
            qualification = joined(
                ("Description", "Endpoint class read"),
                (shown(outcome["description"]), read_list_cell(outcome["endpoint_classes"], NO_CLASS)),
                outcome["description"]["source"],
                "",
            )
            entries.append(
                (
                    cell(f"{prefix}{n}", LABEL),
                    cell(word, "known", f"{OUTCOMES}.{kind}Outcomes"),
                    shown(outcome["measure"]),
                    cell("Registered endpoint", "known", f"{OUTCOMES}.{kind}Outcomes"),
                    *(REGISTERED,) * 8,
                    shown(outcome["time_frame"]),
                    schedule,
                    qualification,
                )
            )
    planning = absent("Planning assumptions and anticipated thresholds")
    entries.append(
        (
            cell("A1", LABEL),
            planning,
            cell("Planning assumptions and anticipated thresholds", LABEL),
            cell("Anticipated", "known", "readout.outcome_rows"),
            *(planning,) * 10,
            planning,
        )
    )
    results = study["efficacy"]["results"]
    if results["status"] != "known":
        state = shown(results)
        title = cell("Registry results", LABEL)
        entries.append(
            (cell("R1", LABEL), state, title, cell("Observed", "known", "hasResults"), *(state,) * 10)
            + (publication_note(study),)
        )
    for n, value in enumerate(study["efficacy"]["measurements"], 1):
        facts = observed_facts(value)
        source, rule = value["source"], value["rule"]
        entries.append(
            (
                cell(f"R{n}", LABEL),
                facts[0],
                cell(scalar_text(value["value"].get("measure")), "known", source, rule),
                cell("Observed", "known", source, rule),
                facts[1],
                absent("Analysis population"),
                *facts[2:5],
                facts[7],
                facts[5],
                facts[8],
                facts[6],
                schedule,
                facts[9],
            )
        )
    return [(label(trial), *entry, label(f"{trial}-O{n:03d}")) for n, entry in enumerate(entries, 1)]


def listing_rows(study: dict[str, Any], facts: list[tuple], code: str) -> list[tuple]:
    """Facts as a listing's rows: the Trial ID first, the evidence key "<Trial ID>-<code><nnn>" last
    (pure — pinned)."""
    trial = plain(study["nct"]["value"])
    return [(label(trial), *row, label(f"{trial}-{code}{n:03d}")) for n, row in enumerate(facts, 1)]


# ── across trials ─────────────────────────────────────────────────────────────────────────────────────

FREQUENCY_RULE = "profile.frequency_rows"


def trials_stating(record: dict[str, Any]) -> dict[str, list[str]]:
    """Each cohort element's trials, from each trial's own readings (pure — pinned).

    An eligibility element: the trials whose standard language holds it; a primary endpoint element
    ("primary:endpoint:<class>"): the trials one of whose primary outcomes the rules read as that class. Each
    trial once, in the record's order.
    """
    stating: dict[str, list[str]] = {}
    for study in record["studies"]:
        nct = study["nct"]["value"]
        keys = [
            element["value"]["element"]
            for entry in study["standard_language"]
            for element in entry["elements"]
            if isinstance(element["value"], dict)
        ]
        keys += [
            f"primary:endpoint:{klass}"
            for outcome in study["outcomes"]["primary"]
            for klass in outcome["endpoint_classes"]["value"] or []
        ]
        for key in keys:
            trials = stating.setdefault(key, [])
            if nct not in trials:
                trials.append(nct)
    return stating


def frequency_finding(row: dict[str, Any], stating: dict[str, list[str]]) -> tuple:
    """A common-criterion row of the cohort profile as a finding's eight values (pure — pinned).

    (type, element, finding, its status, trials, supporting / assessable / total, exceptions and unknowns,
    basis). The finding: stated by S of N trials, its statement rate, its full-criteria interval where the
    profile gives one, its standard tier (or none: a statement rate only), "Unresolved — ..." when the tier is
    unresolved; the trials (trials_stating) for the all-trials stratum only, else ""; assessable is stating
    plus absent ("Not stated" when the profile counts neither); with no absent count, the exceptions are "Not
    stated" (a statement rate only); every other missing count "Not stated".
    """
    t = {key: scalar_text(item) for key, item in row.items()}
    words = f"Stated by {t['stating']} of {t['trials']} trials (statement rate {t['statement_rate']}"
    if row["lower_bound"] is not None:
        words += f"; full-criteria interval {t['lower_bound']} to {t['upper_bound']}"
    tier = row["standard_tier"]
    words += f"); standard tier {tier}" if tier else "); no standard tier (a statement rate only)"
    unresolved = tier == "unresolved"
    counted = isinstance(row["stating"], int) and isinstance(row["absent"], int)
    assessable = str(row["stating"] + row["absent"]) if counted else NOT_STATED
    trials = "\n".join(stating.get(row["element"], [])) if row["stratum"] == "all trials" else ""
    if row["absent"] is None:
        unknowns = "Not stated: a statement rate only, no silence is counted"
    else:
        unknowns = (
            f"Absent in {t['absent']}; unresolved in {t['unresolved']} (empty {t['unresolved_empty']}, "
            f"no rule match {t['unresolved_no_rule_match']}, abbreviated {t['unresolved_abbreviated']}, "
            f"unspecified {t['unresolved_unspecified']})"
        )
    return (
        f"Common criterion ({t['stratum']})",
        t["element"],
        (UNRESOLVED + words) if unresolved else words,
        "unresolved" if unresolved else "known",
        trials,
        f"{t['stating']} / {assessable} / {t['trials']}",
        unknowns,
        f"{FREQUENCY_RULE}; estimand {t['estimand']}; sponsors {t['sponsors']}",
    )


def mechanism_finding(row: dict[str, Any]) -> tuple:
    """A mechanism comparison of the cohort profile as a finding's eight values (pure — pinned).

    Proposed ("Proposed — ...") when the profile proposes it, else "Unresolved — <its status>: ..."; its
    trials are not carried by the record (""); supporting / assessable / total is in-class stating / in
    class / in class and others ("Not stated" for a count missing).
    """
    t = {key: scalar_text(item) for key, item in row.items()}
    words = (
        f"Stated by {t['in_class_stating']} of {t['in_class']} trials in the class and "
        f"{t['others_stating']} of {t['others']} others; difference {t['difference']} (least favourable "
        f"{t['least_favourable_difference']})"
    )
    proposed = row["status"] == "proposed"
    counted = isinstance(row["in_class"], int) and isinstance(row["others"], int)
    total = str(row["in_class"] + row["others"]) if counted else NOT_STATED
    return (
        "Mechanism-linked exclusion",
        f"{t['class']}: {t['element']} ({t['stratum']})",
        f"Proposed — {words}" if proposed else f"{UNRESOLVED}{t['status']}: {words}",
        "proposed" if proposed else "unresolved",
        "",
        f"{t['in_class_stating']} / {t['in_class']} / {total}",
        (
            f"Unresolved class trials {t['unresolved_class_trials']}; abbreviated in the class "
            f"{t['abbreviated_in_class']}, in others {t['abbreviated_in_others']}"
        ),
        f"profile.mechanism_rows; sponsors {t['sponsors']}",
    )


def pair_finding(row: dict[str, Any], kind: str) -> tuple:
    """A near-miss trial pair as a finding's eight values (pure — pinned).

    `kind` names how the pair was matched ("as written", "aligned by ATC class"); the finding names each
    trial's value of the one difference and how many other predicates agree, and says that registry
    similarity is not clinical comparability; its trials are the two; an aligned pair's bases are named.
    """
    t = {key: scalar_text(item) or NOT_STATED for key, item in row.items()}
    basis = "nearmiss.near_misses"
    if "basis_a" in row:
        basis += f"; bases {t['basis_a']}, {t['basis_b']}"
    return (
        f"Trial pair ({kind})",
        t["difference"],
        (
            f"{t['a']}: {t['value_a']}; {t['b']}: {t['value_b']}; {t['predicates_agreeing']} other "
            "predicates agree. Registry similarity, not clinical comparability: they may differ in what is "
            "not represented"
        ),
        "known",
        f"{t['a']}\n{t['b']}",
        "2 trials compared",
        (
            f"Sponsors: {t['sponsor_a']} / {t['sponsor_b']}; start years {t['start_year_a']} / "
            f"{t['start_year_b']}"
        ),
        basis,
    )


def finding_rows(record: dict[str, Any]) -> list[tuple]:
    """The Across-trial findings: every common-criterion row, mechanism comparison and trial pair the cohort
    holds, with its numbers (pure — pinned).

    frequency_finding, mechanism_finding and pair_finding (as written, then aligned), each row (finding ID
    "F<nnn>", type, criterion or design feature, finding, trial IDs (not carried by the record when the
    finding names none), supporting / assessable / total, exceptions and unknowns, rule or matching basis,
    evidence key: its finding ID). None — one row of "Not stated".
    """
    cohort = record["cohort"]
    stating = trials_stating(record)
    found = [frequency_finding(row, stating) for row in cohort["frequency"]]
    found += [mechanism_finding(row) for row in cohort["mechanism_signals"]]
    found += [pair_finding(row, "as written") for row in cohort["near_misses"]]
    found += [pair_finding(row, "aligned by ATC class") for row in cohort["aligned_near_misses"]]
    rows = []
    for n, (kind, feature, words, status, trials, counts, unknowns, basis) in enumerate(found, 1):
        shown_trials = (
            cell(trials, "known", "cohort", basis) if trials else absent("Trials of a cohort finding")
        )
        rows.append(
            (
                label(f"F{n:03d}"),
                cell(kind, "known", "cohort", basis),
                cell(feature, "known", "cohort", basis),
                cell(words, status, "cohort", basis),
                shown_trials,
                cell(counts, "known", "cohort", basis),
                cell(unknowns, "known", "cohort", basis),
                cell(basis, "known", "cohort", basis),
                label(f"F{n:03d}"),
            )
        )
    if not rows:
        none = cell(
            NOT_STATED, "not_stated", "cohort", "", "no common criterion, mechanism comparison or pair"
        )
        rows.append((label("F001"), *(none,) * 7, label("F001")))
    return rows


# ── the Read me, the register and the plan ────────────────────────────────────────────────────────────


def search_words(request: Any, scope: Any) -> str:
    """The search as run, in words (pure — pinned).

    The scope's registry query when it holds one ("<parameter>=<value>" per parameter, joined by "; ", or
    its text), else the request as given (its JSON, keys sorted); neither — "Not stated".
    """
    query = scope.get("query") if isinstance(scope, dict) else None
    if isinstance(query, dict) and query:
        return "; ".join(f"{key}={item}" for key, item in query.items())
    if isinstance(query, str) and query.strip():
        return query
    if request in (None, {}, [], ""):
        return NOT_STATED
    return json.dumps(request, ensure_ascii=False, sort_keys=True)


RETRIEVAL_MODE_WORDS = {
    "direct": "Direct: TrialLedger fetched every page from ClinicalTrials.gov itself and checked each "
    "against the registry's own counts, page order and export.",
    "relay": "Relayed: an assistant fetched each page and saved it for TrialLedger. TrialLedger checked "
    "each relayed page's form, its counts, the order of the pages and the exact trials it holds, but not "
    "each value against the registry: a page altered in transit would not be noticed. The trials' drug "
    "classes were not looked up.",
}


def retrieval_mode_words(retrieval: Any) -> str:
    """How the record's pages reached TrialLedger, in words (pure — pinned): RETRIEVAL_MODE_WORDS for the
    manifest retrieval's mode, direct or relay; "Not stated" for a retrieval without one."""
    mode = retrieval.get("mode") if isinstance(retrieval, dict) else None
    return RETRIEVAL_MODE_WORDS.get(mode, NOT_STATED) if isinstance(mode, str) else NOT_STATED


def read_me_rows(record: dict[str, Any]) -> list[tuple]:
    """The Read me: one row per topic (pure — pinned).

    What the workbook is; the search as run; the request; the retrieval date and the registry version; the
    trials read and the record's code; the retrieval's coverage and its mode (retrieval_mode_words); scope
    surprises (combined phases, trials outside the supported universe); what each status and statement type
    means; how to read a dossier; each sheet; the design's fields the record does not carry.
    Each (topic, content, row key "M<nn>").
    """
    manifest = record["manifest"]
    studies = record["studies"]
    combined = [
        f"{study['nct']['value']}: {', '.join(str(phase) for phase in study['phases']['value'])}"
        for study in studies
        if isinstance(study["phases"]["value"], list) and len(study["phases"]["value"]) > 1
    ]
    outside = [
        f"{row['nct']}: {str(row['universe']).replace('_', ' ')}"
        for row in record["coverage"]["studies"]
        if row["universe"] != "in_universe"
    ]
    topics = [
        (
            "What this workbook is",
            "A registry readout of the trials one search found on ClinicalTrials.gov, derived from "
            "landscape.json alone. Each value is a field of a registry record or a named rule's reading of "
            "such fields; nothing is summarized or inferred, and no language model read any trial. It is not "
            "a study report: a registered outcome is never a result.",
        ),
        ("Search as run", search_words(record["request"], record["scope"])),
        ("Request", json.dumps(record["request"], ensure_ascii=False, sort_keys=True)),
        (
            "Retrieval date",
            f"{date_text(manifest['data_timestamp'])} (the registry's data timestamp); ClinicalTrials.gov "
            f"API {manifest['api_version']}",
        ),
        ("Trials", f"{len(studies):,} trials, one row each in the Trial index"),
        ("Record", f"landscape.json schema {SCHEMA_VERSION}; code commit {manifest['code_commit']}"),
        ("Retrieval coverage", plain(manifest["retrieval"]) if manifest["retrieval"] else NOT_STATED),
        ("Retrieval mode", retrieval_mode_words(manifest["retrieval"])),
        (
            "Scope surprise: combined phases",
            "\n".join(combined) or "No trial here registers more than one phase",
        ),
        (
            "Scope surprise: outside the supported universe",
            "\n".join(outside) or "Every trial here is inside the supported universe",
        ),
        *(
            (f"Status: {words.partition(': ')[0]}", words.partition(": ")[2])
            for status, words in STATUS_WORDS.items()
            if status != LABEL
        ),
        (
            "Status in the cell",
            "A known value reads plainly. Otherwise the cell says why, in words: Not stated (the record says "
            "nothing), Not posted (no results or document posted), Not applicable (only where the registry's "
            "definitions establish it), Unresolved — <reason>, Proposed — ..., Interpolated — .... Never a "
            "blank, zero, dash or N/A. Nothing depends on colour, comments or hover text.",
        ),
        ("Statement type: Record says", "What the registry record states, or that it states nothing"),
        (
            "Statement type: Establishes",
            "A bounded reading a named rule makes of the record; never a clinical conclusion",
        ),
        ("Statement type: Unresolved", "What the rules cannot settle from the record, with the reason"),
        (
            "How to read a trial's dossier",
            "Filter the Trial index, then follow a trial's Dossier link (or filter Trial review on its Trial "
            "ID) and read its block top to bottom: identification; population and setting, then the enrolled "
            "population; arms and interventions; inclusion, exclusion and unresolved criteria; outcomes; "
            "biomarkers; efficacy (planning, then observed); safety; exploratory assessments; protocol "
            "language, publications and open questions. Each trial starts a new printed page.",
        ),
        (
            "Evidence keys",
            "Every listing row ends with its evidence key; the Evidence register holds, per displayed value, "
            "its status, its source (registry field or rule, with versions), the registry page and inputs.",
        ),
        *(
            (f"Sheet: {name}", f"{len(columns)} columns: " + "; ".join(h for h, *_ in columns))
            for name, columns, *_ in SHEETS
        ),
        *(
            (f"Not carried by the record: {field}", f"{what} — {NOT_CARRIED}; the cell says Not stated")
            for field, what in NOT_IN_RECORD
        ),
    ]
    return [
        (label(topic), cell(content, LABEL), label(f"M{n:02d}"))
        for n, (topic, content) in enumerate(topics, 1)
    ]


def register_rows(
    sheet: str, columns: tuple, rows: list[tuple], by_trial: bool, versions: tuple[str, str, str]
) -> list[tuple]:
    """The Evidence register's rows for one sheet: one per displayed value (pure — pinned).

    For each row and each column the sheet enters in the register: (evidence ID "<row key>/<field>", Trial
    ID (the row's first cell when `by_trial`, else "Cohort"), sheet, row key, field, the value as displayed,
    its status in words, its source kind (registry field, rule, TrialLedger's own words, or not carried by
    the record), the registry field or rule with its version, the registry page (links.study_link of the
    Trial ID; across trials, ACROSS), the inputs (the cell's own, else "Not stated") and the retrieval
    date). `versions` is (the registry API's version, TrialLedger's, the retrieval date).
    """
    api, tool, retrieved = versions
    found = []
    for row in rows:
        key = row[-1][0]
        trial = row[0][0] if by_trial else COHORT
        url = study_link(trial)[1] if by_trial else ACROSS
        for (header, _width, entered), held in zip(columns, row, strict=True):
            if not entered:
                continue
            value, _link, status, source, rule, inputs = held
            if status == ABSENT:
                kind, basis = (
                    "Not carried by the record",
                    f"{source} (landscape.json schema {SCHEMA_VERSION})",
                )
            elif rule:
                kind, basis = "Rule", f"{rule} (TrialLedger {tool}; {VERSION})"
            elif source:
                kind, basis = "Registry field", f"{source} (ClinicalTrials.gov API {api})"
            else:
                kind, basis = "TrialLedger's own words", f"TrialLedger {tool}; {VERSION}"
            found.append(
                tuple(
                    cell(part, LABEL)
                    for part in (
                        f"{key}/{header}",
                        trial,
                        sheet,
                        key,
                        header,
                        value,
                        STATUS_WORDS.get(status, status),
                        kind,
                        basis,
                        url or NOT_STATED,
                        inputs or NOT_STATED,
                        retrieved,
                    )
                )
            )
    return found


def fitted(rows: list[tuple]) -> list[tuple]:
    """Rows every cell of which a spreadsheet holds exactly, a passage too long for one cell continued on
    numbered rows (pure — pinned).

    A text a cell cannot hold for a character or a carriage return (cells.cell_text_state) is written as
    "Unresolved — not written: <reason>; it is in landscape.json at <source>". A text over a cell's limit is
    cut into CHUNK-character parts: the row is repeated once per part, each repeat holding the next part of
    every such text (or, past its end, "(continued in the rows above)"), its other cells as they are, its
    key (the last cell) followed by " (continued <n>)". Any other row is kept as it is.
    """
    out = []
    for row in rows:
        parts: list[list[str] | None] = []
        changed = list(row)
        for index, held in enumerate(row):
            value = held[0]
            state = cell_text_state(value) if isinstance(value, str) else "ok"
            if state == "too_long":
                parts.append([value[start : start + CHUNK] for start in range(0, len(value), CHUNK)])
                continue
            if state != "ok":
                reason = state.replace("_", " ")
                words = f"{UNRESOLVED}not written: {reason}; it is in landscape.json at {held[3] or held[4]}"
                changed[index] = cell(words, "unresolved", held[3], held[4], held[5])
            parts.append(None)
        count = max([len(part) for part in parts if part is not None], default=1)
        for number in range(count):
            copy = []
            for held, part in zip(changed, parts, strict=True):
                if part is None:
                    copy.append(held)
                else:
                    text = part[number] if number < len(part) else "(continued in the rows above)"
                    copy.append((text, *held[1:]))
            if number:
                key = copy[-1]
                copy[-1] = (f"{key[0]} (continued {number + 1})", *key[1:])
            out.append(tuple(copy))
    return out


def place(index: int, capacity: int, sheet: str) -> tuple[str, int]:
    """Where a sheet's data row `index` (from 0) is written: the numbered sheet and its row (pure — pinned).

    Each worksheet holds `capacity` data rows below its header; the first is named `sheet`, the next "<sheet>
    2", and so on; the row counts from 1 with the header as row 1.
    """
    part, offset = divmod(index, capacity)
    return (sheet if part == 0 else f"{sheet} {part + 1}"), offset + 2


def footer_parts(search: str, retrieved: str) -> tuple[str, str, str]:
    """The printed footer's left, centre and right text (pure — pinned).

    Left: "Search: <search>"; centre: the sheet and page ("&A, page &P of &N"); right: "Retrieved
    <retrieval date>". A literal "&" is written "&&". When the whole footer (with its section codes) would
    exceed Excel's 255 characters, the left reads "Search: see the Read me sheet".
    """
    left = "Search: " + search.replace("&", "&&")
    centre = "&A, page &P of &N"
    right = "Retrieved " + retrieved.replace("&", "&&")
    if len(f"&L{left}&C{centre}&R{right}") > FOOTER_LIMIT:
        left = "Search: see the Read me sheet"
    return left, centre, right


LISTINGS = (
    ("Trial index", "I"),
    ("Trial review", "R"),
    ("Eligibility", "E"),
    ("Outcomes and efficacy", "O"),
    ("Biomarkers", "B"),
    ("Safety", "S"),
    ("Across-trial findings", "F"),
)


def readout_plan(record: dict[str, Any]) -> list[tuple]:
    """Every sheet of landscape.xlsx, in order, as (name, columns, rows, page starts) (pure — pinned).

    The rows are the row functions' over the record, fitted; Trial review is built first, so each index row
    links to its trial's first dossier row (place, at CAPACITY rows a worksheet); `page starts` are the
    Trial review rows (from 0) where a trial's dossier begins after the first, each printed on a new page;
    the Evidence register enters every value of every listing.
    """
    studies, questions = record["studies"], record["review_queue"]
    review: list[tuple] = []
    starts = []
    for study in studies:
        starts.append(len(review))
        review += fitted(review_rows(study, questions))
    index = fitted(
        [
            index_row(study, place(start, CAPACITY, "Trial review"))
            for study, start in zip(studies, starts, strict=True)
        ]
    )
    rows = {
        "Read me": fitted(read_me_rows(record)),
        "Trial index": index,
        "Trial review": review,
        "Eligibility": fitted([row for study in studies for row in eligibility_rows(study)]),
        "Outcomes and efficacy": fitted([row for study in studies for row in outcome_rows(study)]),
        "Biomarkers": fitted(
            [row for study in studies for row in listing_rows(study, biomarker_facts(study), "B")]
        ),
        "Safety": fitted([row for study in studies for row in listing_rows(study, safety_facts(study), "S")]),
        "Across-trial findings": fitted(finding_rows(record)),
    }
    manifest = record["manifest"]
    versions = (str(manifest["api_version"]), __version__, date_text(manifest["data_timestamp"]))
    columns = {name: held for name, held, *_ in SHEETS}
    register = []
    for name, _code in LISTINGS:
        register += register_rows(name, columns[name], rows[name], name != "Across-trial findings", versions)
    rows["Evidence register"] = fitted(register)
    return [
        (name, held, rows[name], starts[1:] if name == "Trial review" else []) for name, held, *_ in SHEETS
    ]


# ── writing, and reading back ─────────────────────────────────────────────────────────────────────────

FONT = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
EDGE = Side(style="thin", color="BFBFBF")
BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=EDGE)
HEADER_BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=Side(style="thin", color="000000"))
TEXT = Alignment(horizontal="left", vertical="top", wrap_text=True)
NUMBER = Alignment(horizontal="right", vertical="top")
WRITE_TIMES = re.compile(rb"<dcterms:(created|modified)\b[^>]*>[^<]*</dcterms:\1>")
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _styles(sheet: Any) -> dict[tuple[bool, bool], Any]:
    """The four cell styles, made once per workbook: (header, text) to a style a cell copies."""
    styles = {}
    for header in (True, False):
        for text in (True, False):
            template = WriteOnlyCell(sheet, value="")
            template.font = BOLD if header else FONT
            template.border = HEADER_BORDER if header else BORDER
            template.alignment = TEXT if text else NUMBER
            if not text:
                template.number_format = "#,##0"
            styles[(header, text)] = template._style
    return styles


def _cell(sheet: Any, held: tuple, header: bool, styles: dict[tuple[bool, bool], Any]) -> Any:
    """One written cell: text forced to text (never a formula), a number right-aligned with separators."""
    value, link = held[0], held[1]
    written = WriteOnlyCell(sheet, value=value)
    text = isinstance(value, str)
    if text:
        written.data_type = "s"
    written._style = copy(styles[(header, text)])
    if link.startswith("#"):
        written.hyperlink = Hyperlink(ref="", location=link[1:], display=str(value))
    elif link:
        written.hyperlink = link
    return written


def _write(plan: list[tuple], footer: tuple[str, str, str]) -> tuple[bytes, int]:
    """The workbook's bytes, every write time fixed, and the number of cells written."""
    book = Workbook(write_only=True)
    styles: dict[tuple[bool, bool], Any] = {}
    written = 0
    for name, columns, rows, starts in plan:
        for start in range(0, max(len(rows), 1), CAPACITY):
            part_name = place(start, CAPACITY, name)[0]
            part = rows[start : start + CAPACITY]
            sheet = book.create_sheet(part_name)
            styles = styles or _styles(sheet)
            last = get_column_letter(len(columns))
            sheet.freeze_panes = next(freeze for title, _, freeze, _ in SHEETS if title == name)
            for number, (_header, width, _entered) in enumerate(columns, 1):
                sheet.column_dimensions[get_column_letter(number)].width = width
            sheet.auto_filter.ref = f"A1:{last}{len(part) + 1}"
            sheet.print_title_rows = "1:1"
            sheet.print_area = f"A1:{last}{len(part) + 1}"
            sheet.page_setup.orientation = "landscape"
            sheet.oddFooter.left.text, sheet.oddFooter.center.text, sheet.oddFooter.right.text = footer
            for begin in starts:
                if start <= begin < start + len(part):
                    sheet.row_breaks.append(Break(id=begin - start + 1))
            sheet.append([_cell(sheet, label(header), True, styles) for header, *_ in columns])
            for row in part:
                sheet.append([_cell(sheet, held, False, styles) for held in row])
            written += len(columns) * (len(part) + 1)
    book.properties.creator = "TrialLedger"
    raw = io.BytesIO()
    book.save(raw)
    fixed = io.BytesIO()
    with zipfile.ZipFile(raw) as source, zipfile.ZipFile(fixed, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = WRITE_TIMES.sub(b"", data)
            target.writestr(zipfile.ZipInfo(info.filename, date_time=ZIP_TIME), data, zipfile.ZIP_DEFLATED)
    return fixed.getvalue(), written


def readout_problems(record: dict[str, Any], path: Path, limit: int = 20) -> list[str]:
    """Every way the file at `path` differs from the workbook `record` derives, cell by cell: the sheets in
    order, each row's values (text as text, a count as an integer). An empty list certifies the file."""
    try:
        opened = load_workbook(path, read_only=True)
    except Exception as error:  # a file that is not this workbook can raise almost anything; it is named
        return [f"readout.unreadable: {path.name} ({type(error).__name__}: {error})"]
    problems: list[str] = []
    try:
        expected = []
        for name, columns, rows, _starts in readout_plan(record):
            for start in range(0, max(len(rows), 1), CAPACITY):
                part = place(start, CAPACITY, name)[0]
                expected.append(part)
                if part not in opened.sheetnames:
                    problems.append(f"sheet {part!r} is missing")
                    continue
                want = [tuple(header for header, *_ in columns)] + [
                    tuple(held[0] for held in row) for row in rows[start : start + CAPACITY]
                ]
                have = list(opened[part].iter_rows(values_only=True))
                if len(have) != len(want):
                    problems.append(f"{part}: {len(have)} rows, the derivation {len(want)}")
                for number, (wanted, held) in enumerate(zip(want, have, strict=False), 1):
                    if tuple(wanted) != tuple(held) or any(
                        type(a) is not type(b) for a, b in zip(wanted, held, strict=False)
                    ):
                        problems.append(f"{part} row {number}: expected {wanted!r}, found {held!r}")
                    if len(problems) >= limit:
                        return problems
        if opened.sheetnames != expected:
            problems.append(f"sheets {opened.sheetnames} differ from the derivation's {expected}")
    finally:
        opened.close()
    return problems[:limit]


def write_readout(record: dict[str, Any], path: Path) -> int:
    """Write landscape.xlsx for a landscape.json record to `path`, read it back, and return the number of
    cells written; raise ReadoutError, leaving no file, unless every cell equals its derivation."""
    manifest = record["manifest"]
    footer = footer_parts(
        search_words(record["request"], record["scope"]), date_text(manifest["data_timestamp"])
    )
    data, written = _write(readout_plan(record), footer)
    path.write_bytes(data)
    problems = readout_problems(record, path, limit=1)
    if problems:
        path.unlink()
        raise ReadoutError("readout.readback_mismatch", problems[0])
    return written
