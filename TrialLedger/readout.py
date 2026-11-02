"""landscape.xlsx: the clinical readout of a landscape.json record (add-agent-operation 4.3), and the
reviewer's workbook of a schema-3 record (refine-landscape-record unit C, the last section of this module).

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

from TrialLedger import __version__, contract
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


# ── landscape.json schema 3: the reviewer's workbook (refine-landscape-record 3.1-3.7) ─────────────────────
# The workbook contract.SHEETS lays out, derived from a schema-3 record alone. A registry value is held
# plain; a value the registry does not hold, or a rule's reading, is a value object (contract module
# docstring). Every code is shown through contract.DISPLAY; a reading is labelled ("Reading: ...", or the
# dossier's Basis column); a cell is blank only where its column cannot apply to its row by construction (a
# Safety group column past the trial's own groups; an unnamed class or category of a posted measure; a
# Groups column or total only adverse events have), and anything else the registry does not give is said in
# words. Every listing row's address is a JSON pointer to the node the row shows. operate.write_book writes
# the schema-2 readout above until the record is schema 3.

BOOK_VERSION = "book-2"
ABSENT_KEYS = ("status", "note")
READING_KEYS = ("status", "rule", "words", "result", "note")
NOT_REPORTED = "Not reported"
NO_READING = "No reading produced"
NO_GRADE = "The registry's adverse-event tables report no grade"
STATUS_LABELS = {
    "known": "Known",
    "interpolated": "Interpolated",
    "proposed": "Proposed",
    "not_stated": "Not stated",
    "not_posted": "Not posted",
    "unresolved": "Unresolved",
}
REGISTRY, READING, NOTE = "Registry", "Reading", "Note"
SOURCE_WORDS = {
    "condition_mesh": "the condition MeSH terms",
    "free_text": "the conditions and titles",
    "intervention_mesh": "the interventions' MeSH terms",
}
UNIVERSE_LABELS = {universe.name: universe.label for universe in contract.UNIVERSES}
UNIVERSE_SHORT = {
    "oncology.solid": "Solid tumour",
    "oncology.heme": "Haematologic",
    "general": "Outside oncology",
}
# How a universe's trials are named, and what a reading defined for it is defined for.
TRIAL_WORDS = {
    "oncology.solid": "solid-tumour trials",
    "oncology.heme": "haematologic cancer trials",
    "general": "trials outside oncology",
}
DEFINED_FOR = {"oncology.solid": "solid tumours", "oncology.heme": "haematologic cancers"}
COORDINATE_WORDS = {
    "setting": "Treatment setting",
    "prior_advanced_lines": "Prior lines for advanced disease",
    "selection": "Gene selection",
}
# What would settle a coordinate the criteria leave open, in the eligibility criteria's own terms.
UNSETTLED_WORDS = {
    "setting": "the eligibility criteria do not state the treatment setting (such as adjuvant, first-line "
    "or previously treated advanced disease)",
    "prior_advanced_lines": "the eligibility criteria do not state the prior lines of therapy for advanced "
    "disease",
    "selection": "the eligibility criteria do not state a gene's mutation, fusion or other selecting state",
}
# A field shown after another in brackets, in the dossier and the index ("06-Apr-2020 (Actual)").
BESIDE = {
    "studies[].start_date.type": "studies[].start_date.date",
    "studies[].primary_completion_date.type": "studies[].primary_completion_date.date",
    "studies[].completion_date.type": "studies[].completion_date.date",
    "studies[].lead_sponsor.class": "studies[].lead_sponsor.name",
    "studies[].enrollment.type": "studies[].enrollment.count",
}
DATES = (
    "studies[].start_date.date",
    "studies[].primary_completion_date.date",
    "studies[].completion_date.date",
    "studies[].first_posted",
    "studies[].results_first_posted",
    "studies[].last_update_posted",
    "studies[].documents[].date",
    "studies[].documents[].upload_date",
)
# The dossier's facts shown for every trial, "Not stated" when the registry leaves them empty; every other
# fact is shown only when the record holds it (the record and the listings hold everything).
EXPECTED = (
    "studies[].brief_title",
    "studies[].official_title",
    "studies[].overall_status",
    "studies[].start_date.date",
    "studies[].primary_completion_date.date",
    "studies[].completion_date.date",
    "studies[].first_posted",
    "studies[].last_update_posted",
    "studies[].lead_sponsor.name",
    "studies[].phases",
    "studies[].primary_purpose",
    "studies[].allocation",
    "studies[].intervention_model",
    "studies[].masking",
    "studies[].enrollment.count",
    "studies[].conditions",
    "studies[].universe",
    "studies[].population.minimum_age",
    "studies[].population.maximum_age",
    "studies[].population.sex",
    "studies[].population.healthy_volunteers",
    "arms",
    "interventions",
    "registered_outcomes",
    "studies[].results_posted",
    "references",
)
# The internal state of a reading, shown in the Readings sheet and never as a dossier fact.
NOT_IN_DOSSIER = ("studies[].eligibility.itemized", "studies[].eligibility.coverage")
STOPPED = ("TERMINATED", "SUSPENDED", "WITHDRAWN")
# The dossier's one row per element of a registry list: what one element is called.
ELEMENT_WORDS = {
    "secondary_ids": "Other identifier",
    "collaborators": "Collaborator",
    "officials": "Overall official",
    "arms": "Arm",
    "interventions": "Intervention",
    "key_criteria": "Key criterion",
    "registered_outcomes": "Registered outcome",
    "references": "Publication",
    "links": "Related link",
    "ipd_documents": "Shared participant data or document",
    "documents": "Posted document",
}
RESULTS_MODULES = ("posted_outcomes", "baseline", "participant_flow", "adverse_events")
HEADINGS = {"inclusion": "Inclusion", "exclusion": "Exclusion", "unsectioned": "No heading"}
# The clinical words of the typing banks' concepts (banks.type_criterion), a concept not listed shown with its
# underscores as spaces.
CONCEPT_WORDS = {
    "condition": "Condition",
    "extent": "Disease extent",
    "setting_word": "Treatment setting named",
    "prior_lines": "Prior lines of therapy",
    "prior_agent": "Prior treatment",
    "ecog_ps": "Performance status (ECOG/WHO)",
    "karnofsky": "Performance status (Karnofsky)",
    "age": "Age",
    "histology": "Histology",
    "biomarker": "Biomarker",
    "organ_function": "Organ function",
}


def held_kind(value: Any) -> str:
    """What a value of a schema-3 record is (pure — pinned).

    missing — None: the record holds no such key;
    absent  — a value object of exactly (status, note): a value the registry does not hold;
    reading — a value object of exactly (status, rule, words, result, note): a rule's reading;
    plain   — anything else: a registry value as the registry holds it.
    """
    if value is None:
        return "missing"
    if isinstance(value, dict) and tuple(value) == ABSENT_KEYS:
        return "absent"
    if isinstance(value, dict) and tuple(value) == READING_KEYS:
        return "reading"
    return "plain"


def stated(value: Any) -> bool:
    """Whether the record states a value: a plain value with something in it, or a known, interpolated or
    proposed reading."""
    kind = held_kind(value)
    if kind == "plain":
        return contract.holds_value(value)
    return kind == "reading" and value["status"] in ("known", "interpolated", "proposed")


def absence_words(status: Any, note: Any) -> str:
    """A value the record does not hold, in words, from its value object's status and note (pure — pinned).

    not_stated — "Not applicable" when the note is not_applicable (the registry's definitions limit the field
                 to another study type), REDACTED when redacted, otherwise "Not stated";
    not_posted — "Not posted";
    unresolved — "Unresolved — <the note, its underscores as spaces>";
    any other status — "Unresolved — status <status> is not one the record defines".
    """
    if status == "not_stated":
        return NOT_APPLICABLE if note == "not_applicable" else REDACTED if note == "redacted" else NOT_STATED
    if status == "not_posted":
        return NOT_POSTED
    if status == "unresolved":
        reason = str(note).replace("_", " ") if note else "the rules cannot settle it from the record"
        return UNRESOLVED + reason
    return f"{UNRESOLVED}status {status} is not one the record defines"


def item_words(item: Any, dictionary: str) -> str:
    """One registry item in words (pure — pinned).

    A boolean — "Yes" or "No"; a code with a dictionary — its words (contract.display_words), or "<code> (a
    registry code without clinical words)" when the dictionary does not hold it; None — "Not stated";
    anything else — its text as held.
    """
    if isinstance(item, bool):
        return "Yes" if item else "No"
    if item is None:
        return NOT_STATED
    if dictionary:
        code, words = contract.display_words(dictionary, item)
        return words if code == "ok" else f"{words} (a registry code without clinical words)"
    return str(item)


def value_words(value: Any, dictionary: str = "", joiner: str = "; ") -> Any:
    """A plain registry value or a value object as one cell's content.

    missing — "Not stated"; absent — absence_words; a reading — "Reading: <its result>" when known, else its
    status in words (reading_words); a list — its items' words joined by `joiner`, an empty one "Not stated";
    an integer a cell holds exactly — the integer; anything else — item_words.
    """
    kind = held_kind(value)
    if kind == "missing":
        return NOT_STATED
    if kind == "absent":
        return absence_words(value["status"], value["note"])
    if kind == "reading":
        return reading_words(value, result_words(value["result"]))
    if isinstance(value, list):
        return joiner.join(item_words(item, dictionary) for item in value) or NOT_STATED
    if isinstance(value, int) and not isinstance(value, bool) and cell_number_state(value) == "ok":
        return value
    return item_words(value, dictionary)


def result_words(result: Any) -> str:
    """A reading's result as words: text with its underscores as spaces; a list's items so
    written, joined by " or "; an object's keys and values, "key: value" joined by "; "; nothing —
    "nothing"."""
    if isinstance(result, list):
        return " or ".join(result_words(item) for item in result) or "nothing"
    if isinstance(result, dict):
        return "; ".join(f"{key}: {result_words(item)}" for key, item in result.items()) or "nothing"
    if result is None or result == "":
        return "nothing"
    return str(result).replace("_", " ")


def reading_words(value: dict[str, Any], words: str) -> str:
    """A rule's reading, labelled, its result already in words.

    known — "Reading: <words>"; interpolated — "Interpolated: <words>"; proposed — "Proposed: <words>";
    not_posted, not_stated or unresolved — absence_words of its status and note.
    """
    status = value["status"]
    if status == "known":
        return f"Reading: {words}"
    if status in ("interpolated", "proposed"):
        return f"{status.capitalize()}: {words}"
    return absence_words(status, value["note"])


def basis(value: Any) -> str:
    """What a dossier value rests on, as the Basis column names it (pure — pinned): a plain registry value
    "Registry"; a known reading "Reading"; anything else its status's label (STATUS_LABELS: Not stated,
    Not posted, Unresolved, Interpolated, Proposed), an unknown status "Unresolved", a missing value "Not
    stated"."""
    kind = held_kind(value)
    if kind == "plain":
        return REGISTRY
    if kind == "missing":
        return STATUS_LABELS["not_stated"]
    if kind == "reading" and value["status"] == "known":
        return READING
    return STATUS_LABELS.get(value["status"], STATUS_LABELS["unresolved"])


def least_settled(labels: list[str]) -> str:
    """The basis of a cell showing several values (pure — pinned): Unresolved when any is unresolved,
    proposed or interpolated; else Registry when any is a registry value (a registry entry the rules also
    read stays the registry's); else Reading when any is a reading; else Not posted when any is; else Not
    stated."""
    held = set(labels)
    if held & {"Unresolved", "Proposed", "Interpolated"}:
        return "Unresolved"
    for label_ in (REGISTRY, READING, "Not posted"):
        if label_ in held:
            return label_
    return "Not stated"


def at(node: Any, name: str) -> Any:
    """The value at a dotted name below `node` (no list segment), None where a key is missing."""
    for key in name.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def shown_field(study: dict[str, Any], name: str) -> tuple[Any, str]:
    """A study field (no list segment) in words and its basis: its DISPLAY words, a date as date_text, and its
    BESIDE field in brackets after it."""
    field = contract.FIELD_NAMES[name]
    value = at(study, name.removeprefix("studies[]."))
    words = value_words(value, field.display)
    if name in DATES and held_kind(value) == "plain":
        words = date_text(value)
    for beside, main in BESIDE.items():
        held = at(study, beside.removeprefix("studies[]."))
        if main == name and held_kind(held) == "plain":
            extra = value_words(held, contract.FIELD_NAMES[beside].display)
            words = f"{words:,} ({extra})" if isinstance(words, int) else f"{words} ({extra})"
    return words, basis(value)


def applies(name: str, study: dict[str, Any]) -> bool:
    """Whether a study field can apply to the trial, by the registry's own fields: who is masked only under
    masking; the last known status only when the status is unknown; why stopped only for a stopped trial."""
    status = study.get("overall_status")
    if name == "studies[].who_masked":
        return study.get("masking") != "NONE"
    if name == "studies[].last_known_status":
        return status == "UNKNOWN"
    if name == "studies[].why_stopped":
        return status in STOPPED
    return True


# ── universes and the domain readings they permit ───────────────────────────────────────────────────────


def assigned(study: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    """A trial's universe reading as (its status, the universes it names) (pure — pinned): missing —
    ("missing", ()); a reading — its status and its result's universes; anything else — ("unresolved", ())."""
    value = study.get("universe")
    kind = held_kind(value)
    if kind == "missing":
        return "missing", ()
    if kind != "reading" or not isinstance(value["result"], dict):
        return "unresolved", ()
    universes = value["result"].get("universes") or []
    return value["status"], tuple(str(name) for name in universes)


def pack_applies(coordinate: str, universes: tuple[str, ...], purpose: Any) -> str:
    """Whether a pack of contract.UNIVERSES computes the coordinate for a trial (pure — pinned).

    `coordinate` is setting, prior_advanced_lines or selection (a pack's "selection:<gene>").
      applies          — a pack computing it has every requirement held: one of the trial's universes among a
                         universe requirement's values, its primary purpose among a primary-purpose one's;
      outside_universe — no pack computing it is defined for any of the trial's universes;
      other_purpose    — a pack is defined for the trial's universe, but needs another primary purpose.
    """
    in_universe = False
    for universe in contract.UNIVERSES:
        for pack in universe.packs:
            if not any(name.split(":")[0] == coordinate for name in pack.coordinates):
                continue
            kinds = {requirement.kind: requirement.values for requirement in pack.requires}
            if set(universes) & set(kinds.get("universe", ())):
                in_universe = True
                if "primary_purpose" not in kinds or purpose in kinds["primary_purpose"]:
                    return "applies"
    return "other_purpose" if in_universe else "outside_universe"


def not_applicable_words(coordinate: str, universes: tuple[str, ...], purpose: Any) -> str:
    """Why a domain reading is not made for a trial, in clinical words, from the universe table."""
    defined = []
    purposes: list[str] = []
    for universe in contract.UNIVERSES:
        for pack in universe.packs:
            if any(name.split(":")[0] == coordinate for name in pack.coordinates):
                for requirement in pack.requires:
                    if requirement.kind == "universe":
                        defined += [DEFINED_FOR.get(name, name) for name in requirement.values]
                    else:
                        purposes += [
                            item_words(code, "PrimaryPurpose").lower() for code in requirement.values
                        ]
    if pack_applies(coordinate, universes, purpose) == "other_purpose":
        kind = item_words(purpose, "PrimaryPurpose").lower()
        return f"Not read for {kind} trials (this reading is defined for {' or '.join(purposes)} trials)"
    named = " and ".join(TRIAL_WORDS.get(name, name) for name in universes) or "trials of no universe"
    return f"Not read for {named} (this reading is defined for {' and '.join(dict.fromkeys(defined))})"


def universe_words(study: dict[str, Any]) -> tuple[str, str, str]:
    """A trial's universe as (the index's short words, the dossier's words, the basis)."""
    status, universes = assigned(study)
    if status == "missing":
        return NO_READING, NO_READING, STATUS_LABELS["not_stated"]
    value = study["universe"]
    result = value.get("result") if isinstance(value.get("result"), dict) else {}
    if status != "known" or not universes:
        sources = [
            f"{SOURCE_WORDS.get(source.get('source'), source.get('source'))} name "
            + (", ".join(str(item.get("term")) for item in source.get("found") or []) or "no cancer")
            for source in result.get("sources") or []
        ]
        return (
            "Unresolved",
            "Not settled: " + ("; ".join(sources) or "no source names a domain"),
            "Unresolved",
        )
    decided = SOURCE_WORDS.get(result.get("decided_by"), str(result.get("decided_by")))
    labels = [
        UNIVERSE_LABELS.get(name, name) if name != "general" else "Outside oncology" for name in universes
    ]
    short = " + ".join(UNIVERSE_SHORT.get(name, name) for name in universes)
    found = [
        str(item.get("term"))
        for source in result.get("sources") or []
        if source.get("source") == result.get("decided_by")
        for item in source.get("found") or []
    ]
    named = [
        str(term)
        for source in result.get("sources") or []
        if source.get("source") == result.get("decided_by")
        for term in source.get("non_oncology") or []
    ]
    words = f"{' and '.join(labels)}, from {decided}"
    shown_terms = found or named
    words += f" ({', '.join(dict.fromkeys(shown_terms))})" if shown_terms else ""
    return f"{short} ({decided.removeprefix('the ')})", words, READING


def coordinate_levels(study: dict[str, Any], name: str) -> list[tuple[str, Any]]:
    """A coordinate's readings the record holds, in order: known, interpolated, then each proposal alone."""
    held = study.get("coordinates")
    coordinates = held if isinstance(held, dict) else {}
    levels = [
        ("", coordinates.get(name)),
        (" (with the default relations)", coordinates.get(f"{name}_interpolated")),
    ]
    proposed = coordinates.get(f"{name}_proposed")
    levels += [(" (one proposed relation alone, never relied on)", item) for item in proposed or []]
    return [(words, value) for words, value in levels if value is not None]


def coordinate_words(name: str, value: Any) -> str:
    """A domain reading's value in clinical words: its result as registered; an unsettled one says which words
    of the criteria would settle it; a conflict says so."""
    if held_kind(value) != "reading":
        return value_words(value)
    status, result = value["status"], value["result"]
    if status == "known":
        return f"{result_words(result)} (as registered)"
    if status in ("interpolated", "proposed"):
        return f"{status.capitalize()}: {result_words(result)} (as registered)"
    if status == "unresolved" and isinstance(result, list) and not result:
        return "Not settled: the eligibility criteria state values that conflict"
    if status == "unresolved":
        return f"Not settled: {UNSETTLED_WORDS.get(name, 'the eligibility criteria do not state it')}"
    return value_words(value)


def coordinate_short(study: dict[str, Any], name: str) -> Any:
    """The index's cell for a domain reading: "No reading produced" without a universe or a reading; "Not
    applicable" where it is not read for the trial (its reason in the dossier); the known value as
    registered; else the interpolated one, labelled; else "Unresolved" (its reason in the dossier)."""
    status, universes = assigned(study)
    if status == "missing":
        return NO_READING
    if pack_applies(name, universes, study.get("primary_purpose")) != "applies":
        return NOT_APPLICABLE
    levels = dict(coordinate_levels(study, name)[:2])
    known, interpolated = levels.get(""), levels.get(" (with the default relations)")
    if known is None:
        return NO_READING
    if held_kind(known) == "reading" and known["status"] == "known":
        return coordinate_words(name, known)
    if held_kind(interpolated) == "reading" and interpolated["status"] == "interpolated":
        return coordinate_words(name, interpolated)
    return "Unresolved"


# ── a criterion's readings ──────────────────────────────────────────────────────────────────────────────


def atom_words(atom: Any) -> str:
    """One typed reading of a criterion in clinical words: "<concept>: <values joined by ' or '>", then its
    qualifiers in brackets."""
    if not isinstance(atom, dict):
        return result_words(atom)
    concept = str(atom.get("concept", ""))
    named = CONCEPT_WORDS.get(concept, concept.replace("_", " ").capitalize())
    values = " or ".join(str(item).replace("_", " ") for item in atom.get("values") or []) or "named"
    params = atom.get("params") if isinstance(atom.get("params"), dict) else {}
    extra = "; ".join(
        f"{key.replace('_', ' ')} {str(item).replace('_', ' ')}"
        for key, item in params.items()
        if str(item).strip()
    )
    return f"{named}: {values}" + (f" ({extra})" if extra else "")


def criterion_readings(value: Any) -> str:
    """A criterion's typed readings, one "Reading: ..." per line; none — "No reading produced" (which does not
    mean the criterion holds no clinical information)."""
    if held_kind(value) != "reading" or value["status"] != "known" or not value["result"]:
        return NO_READING
    return "\n".join(f"Reading: {atom_words(atom)}" for atom in value["result"])


def role_words(value: Any) -> str:
    """A criterion's role: its heading's, or the one its own words state, with those words; unresolved in
    words."""
    if held_kind(value) != "reading":
        return value_words(value)
    if value["status"] != "known":
        words = ", ".join(f"“{word}”" for word in value.get("words") or [])
        reason = f"its own words {words} conflict with its heading" if words else "it is under no heading"
        return f"Not settled: {reason}"
    role = HEADINGS.get(str(value["result"]), result_words(value["result"]))
    words = ", ".join(dict.fromkeys(f"“{word}”" for word in value.get("words") or []))
    return f"{role} (its own words: {words})" if words else role


# ── the dossier (Trial review) ───────────────────────────────────────────────────────────────────────────

DOSSIER_FIELDS = tuple(field for field in contract.FIELDS if contract.DOSSIER in field.consumers)


def band_fields(prefixes: tuple[str, ...]) -> list[contract.Field]:
    """The dossier fields of one band, in the contract's order."""
    return [
        field
        for field in DOSSIER_FIELDS
        if any(
            field.name == prefix or (prefix.endswith((".", "[].")) and field.name.startswith(prefix))
            for prefix in prefixes
        )
    ]


def element_rows(study: dict[str, Any], key: str, fields: list[contract.Field]) -> list[tuple[str, Any, str]]:
    """A registry list as dossier rows: one per element, each field "<label>: <words>" per line (a field the
    element does not state left out); a nested list one line per item; no element — one "Not stated" row when
    the list is expected, else none."""
    elements = study.get(key)
    plural = ELEMENT_WORDS[key]
    if not isinstance(elements, list) or not elements:
        if key not in EXPECTED:
            return []
        return [(f"{plural}s", value_words(elements), basis(elements))]
    rows = []
    counts: dict[str, int] = {}
    for number, element in enumerate(elements, 1):
        lines, labels = [], []
        for field in fields:
            rest = field.name.removeprefix(f"studies[].{key}[].")
            if field.name in BESIDE:
                continue
            if "[]" in rest:
                outer, inner = rest.split("[].", 1)
                items = element.get(outer)
                held = [value_words(at(item, inner)) for item in items] if isinstance(items, list) else []
                if held:
                    lines.append(f"{field.label}: {'; '.join(str(h) for h in held)}")
                    labels.append(REGISTRY)
                continue
            value = element.get(rest)
            if not stated(value) and not (field.kind == "reading" and held_kind(value) == "reading"):
                continue
            words = value_words(value, field.display)
            if (
                field.name.endswith("drug_class")
                and held_kind(value) == "reading"
                and value["status"] != "known"
            ):
                mesh = value_words(study.get("intervention_mesh"))
                words = (
                    f"Not settled ({value_words(value)}); the registry's intervention MeSH terms beside it: "
                    f"{mesh} (the registry's terms, never a drug class)"
                )
            if field.name in DATES and held_kind(value) == "plain":
                words = date_text(value)
            lines.append(f"{field.label}: {words}")
            reading = field.kind == "reading" and held_kind(value) == "plain"
            labels.append(READING if reading else basis(value))
        fact = f"{plural} {number}"
        if key == "registered_outcomes":
            category = str(element.get("category", "registered")).capitalize()
            counts[category] = counts.get(category, 0) + 1
            fact = f"{category} outcome {counts[category]}"
            lines = [line for line in lines if not line.startswith("Category")]
        rows.append((fact, "\n".join(lines) or NOT_STATED, least_settled(labels)))
    return rows


def universe_band_rows(study: dict[str, Any]) -> list[tuple[str, Any, str]]:
    """The universe and the domain readings it permits, each with the treatment-context limit."""
    _short, words, label_ = universe_words(study)
    rows = [("Universe", words, label_)]
    status, universes = assigned(study)
    purpose = study.get("primary_purpose")
    shown_any = False
    for name, title in COORDINATE_WORDS.items():
        if status == "missing":
            rows.append((title, NO_READING, STATUS_LABELS["not_stated"]))
            continue
        if pack_applies(name, universes, purpose) != "applies":
            rows.append((title, not_applicable_words(name, universes, purpose), READING))
            continue
        levels = coordinate_levels(study, name)
        if not levels:
            rows.append((title, NO_READING, STATUS_LABELS["not_stated"]))
        for words_, value in levels:
            rows.append((f"{title}{words_}", coordinate_words(name, value), basis(value)))
            shown_any = shown_any or name != "selection"
    if shown_any:
        rows.append(("Treatment setting and line: what they are", contract.TREATMENT_CONTEXT_LIMIT, NOTE))
    return rows


TOTALS = (
    ("deaths", "Deaths (all causes)"),
    ("serious", "Serious adverse events"),
    ("other", "Other adverse events"),
)


def group_totals(group: dict[str, Any]) -> str:
    """An adverse-event group's totals, "<what>: <affected> of <at risk>" per line; a total the registry does
    not give — "Not reported"."""
    lines = []
    for prefix, words in TOTALS:
        affected, at_risk = (stat_cell(group, f"{prefix}_{part}") for part in ("affected", "at_risk"))
        unreported = affected == at_risk == NOT_REPORTED
        lines.append(f"{words}: {NOT_REPORTED if unreported else f'{affected} of {at_risk}'}")
    return "\n".join(lines)


def results_posted(study: dict[str, Any]) -> bool:
    """Whether the record's results reading says the trial posted results."""
    value = study.get("results_posted")
    return held_kind(value) == "reading" and value["status"] == "known" and value["result"] == "posted"


def results_words(study: dict[str, Any]) -> tuple[str, str]:
    """Whether results are posted, in words: "Yes, first posted <date>", "Not posted", or the reading's
    status in words."""
    value = study.get("results_posted")
    if results_posted(study):
        first = study.get("results_first_posted")
        when = f", first posted {date_text(first)}" if held_kind(first) == "plain" else ""
        return f"Yes{when}", READING
    if held_kind(value) == "reading" and value["status"] in ("not_posted", "known"):
        return NOT_POSTED, STATUS_LABELS["not_posted"]
    return value_words(value), basis(value)


def availability_rows(study: dict[str, Any], heading: str) -> list[tuple[str, Any, str]]:
    """What the band's listings hold for the trial, counted (results, flow and safety bands); a trial that
    posted no results — nothing (the Results band says so once)."""
    if not results_posted(study):
        return []
    if heading == "Results":
        held = study.get("posted_outcomes")
        outcomes = held if isinstance(held, list) else []
        values = sum(
            len(category.get("measurements") or [])
            for outcome in outcomes
            for klass in outcome.get("classes") or []
            for category in klass.get("categories") or []
        )
        analyses = sum(len(outcome.get("analyses") or []) for outcome in outcomes)
        held = study.get("baseline")
        characteristics = len(held.get("measures") or []) if isinstance(held, dict) else 0
        return [
            (
                "Posted outcome measures",
                f"{len(outcomes)} measures, {values} values (Posted results)",
                REGISTRY,
            ),
            ("Statistical analyses", f"{analyses} analyses (Statistical analyses)", REGISTRY),
            ("Baseline characteristics", f"{characteristics} characteristics (Baseline)", REGISTRY),
        ]
    if heading == "Participant flow":
        flow = study.get("participant_flow")
        if not isinstance(flow, dict):
            return [("Participant flow", NOT_STATED, STATUS_LABELS["not_stated"])]
        periods = flow.get("periods") or []
        names = "; ".join(str(value_words(period.get("title"))) for period in periods) or NOT_STATED
        return [("Periods", f"{len(periods)}: {names} (Participant flow)", REGISTRY)]
    events = study.get("adverse_events")
    if not isinstance(events, dict):
        return [("Adverse events", NOT_STATED, STATUS_LABELS["not_stated"])]
    rows = [
        (f"Group G{number}", f"{value_words(group.get('title'))}\n{group_totals(group)}", REGISTRY)
        for number, group in enumerate(events.get("groups") or [], 1)
    ]
    listed = events.get("events") or []
    serious = sum(1 for event in listed if event.get("table") == "serious")
    words = f"{serious} serious and {len(listed) - serious} other terms (Safety)"
    rows += [("Adverse-event terms", words, REGISTRY), ("Grade", NO_GRADE, REGISTRY)]
    return rows


def dossier_facts(study: dict[str, Any]) -> list[tuple[str, str, str, Any, str]]:
    """A trial's dossier, band by band (contract.DOSSIER_SECTIONS): (band, listing, fact, value, basis). An
    EXPECTED fact always; any other only when stated; a fact that cannot apply never."""
    facts = []
    posted = results_posted(study)
    for heading, listing, prefixes in contract.DOSSIER_SECTIONS:
        fields = band_fields(prefixes)
        rows: list[tuple[str, Any, str]] = []
        done: set[str] = set()
        for field in fields:
            rest = field.name.removeprefix("studies[].")
            if (
                field.name in BESIDE
                or field.name in NOT_IN_DOSSIER
                or rest.startswith(("universe", "coordinates."))
            ):
                continue
            if "[]" in rest:
                key = rest.split("[]", 1)[0]
                if key not in done:
                    done.add(key)
                    rows += element_rows(
                        study, key, [f for f in fields if f.name.startswith(f"studies[].{key}[].")]
                    )
                continue
            if field.name == "studies[].results_posted":
                rows.append((field.label, *results_words(study)))
                continue
            if field.name == "studies[].adverse_events.time_frame" and posted:
                rows.append((field.label, *shown_field(study, field.name)))
                continue
            value = at(study, rest)
            if not applies(field.name, study):
                continue
            if field.name not in EXPECTED and not stated(value):
                continue
            rows.append((field.label, *shown_field(study, field.name)))
        if heading == "Conditions and universe":
            rows += universe_band_rows(study)
        if heading in ("Results", "Participant flow", "Safety"):
            rows += availability_rows(study, heading)
        facts += [(heading, listing, fact, value, label_) for fact, value, label_ in rows]
    return facts


# ── the listings ─────────────────────────────────────────────────────────────────────────────────────────


def group_title(groups: Any, group: Any) -> str:
    """A group named within its own module, by its ID; an ID the module does not hold says so."""
    for held in groups if isinstance(groups, list) else []:
        if held.get("id") == group:
            return str(value_words(held.get("title")))
    return f"{group} (no such group in this module)"


PLAIN_DECIMAL = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
COUNT_FORMAT = "#,##0"


def registry_number(text: Any) -> tuple[str, Any, str]:
    """A registry value written as a number where it is a plain decimal (pure — pinned).

    number — the text is a plain decimal ("63.4", "63.40", "7", "-0.5": digits, an optional sign and point,
             no leading zero, no grouping comma), a negative zero excepted, with at most 15 significant
             digits: (number, the int or float, the format that shows exactly the registry's decimal places:
             "0" for none, "0.00" for two);
    text   — anything else ("NA", "<0.001", "1,500", "0.1-0.3", a number with more digits than a cell holds
             exactly): (text, the value as given, "").
    """
    if not isinstance(text, str) or not PLAIN_DECIMAL.fullmatch(text):
        return "text", text, ""
    whole, _point, places = text.lstrip("-").partition(".")
    digits = (whole + places).lstrip("0")
    value: Any = float(text) if places else int(text)
    if len(digits) > 15 or (text.startswith("-") and value == 0):
        return "text", text, ""
    return "number", value, "0." + "0" * len(places) if places else "0"


def number_cell(value: Any, address: str) -> tuple:
    """A cell of a registry value: a plain decimal as a number in its own format, anything else as text."""
    code, held, form = registry_number(value)
    if code == "number":
        return cell(held, "known", address, form)
    return cell(value, "known", address)


def numbered(values: tuple, address: str, positions: tuple[int, ...]) -> tuple:
    """A listing row's cells, the values at `positions` written by number_cell."""
    return tuple(
        number_cell(value, address) if i in positions else cell(value, "known", address)
        for i, value in enumerate(values)
    )


def denominator_words(scopes: list[Any], group: Any) -> Any:
    """A measurement's denominator: the innermost scope that gives one for its group (class, measure, module);
    a count of participants alone — the count as the registry writes it (a number cell); otherwise "<count>
    <units>", several units joined by "; "; none — "Not stated"."""
    for scope in scopes:
        found = [
            (value_words(count.get("value")), value_words(denominator.get("units")))
            for denominator in (scope.get("denominators") or [] if isinstance(scope, dict) else [])
            for count in denominator.get("counts") or []
            if count.get("group") == group
        ]
        if len(found) == 1 and found[0][1] == "Participants":
            return found[0][0]
        if found:
            return "; ".join(f"{count} {units}" for count, units in found)
    return NOT_STATED


def spread_words(kind: Any, measurement: dict[str, Any], dictionary: str = "") -> str:
    """A measurement's spread or limits: "<dispersion>: <spread>" or "<dispersion>: <lower> to
    <upper>"; neither posted — "Not applicable" when the registry's dispersion is "NA", else "Not stated"."""
    spread, lower, upper = (measurement.get(key) for key in ("spread", "lower_limit", "upper_limit"))
    named = value_words(kind, dictionary) if held_kind(kind) == "plain" else "Spread"
    if held_kind(spread) == "plain":
        return f"{named}: {value_words(spread)}"
    if held_kind(lower) == "plain" or held_kind(upper) == "plain":
        return f"{named}: {value_words(lower)} to {value_words(upper)}"
    return NOT_APPLICABLE if kind == "NA" else NOT_STATED


def title_or_blank(value: Any) -> Any:
    """A class's or category's title; an untitled one blank (None): the registry's single unnamed class or
    category has no name to show."""
    return value_words(value) if stated(value) else None


def measurement_rows(
    trial: str, base: str, module: dict[str, Any], head: tuple, scopes: tuple, extra: dict
) -> list[tuple]:
    """Each measurement of a measure (posted outcome or baseline characteristic) as one row's values: its
    head, class, category, group, denominator, parameter, value, spread, unit and comment."""
    rows = []
    groups = module.get("groups")
    measure = extra["measure"]
    for k, klass in enumerate(measure.get("classes") or []):
        for c, category in enumerate(klass.get("categories") or []):
            for m, measurement in enumerate(category.get("measurements") or []):
                group = measurement.get("group")
                address = f"{base}/classes/{k}/categories/{c}/measurements/{m}"
                values = (
                    trial,
                    address,
                    *head,
                    title_or_blank(klass.get("title")),
                    title_or_blank(category.get("title")),
                    group_title(groups, group),
                    denominator_words([klass, *scopes], group),
                    value_words(measure.get("param_type"), "MeasureParam"),
                    value_words(measurement.get("value")),
                    spread_words(measure.get("dispersion_type"), measurement, extra["dispersion"]),
                    value_words(measure.get("unit")),
                    value_words(measurement.get("comment")),
                )
                # the denominator and the value, numbers where the registry writes plain decimals
                rows.append(numbered(values, address, (len(head) + 5, len(head) + 7)))
    return rows


def posted_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Posted results rows: one per measurement (measure × class × category × group), each group
    named within its own measure, its denominator at the scope the registry gives it; a measure without
    measurements one row saying so."""
    rows = []
    held = study.get("posted_outcomes")
    for o, outcome in enumerate(held if isinstance(held, list) else []):
        status = value_words(outcome.get("reporting_status"), "ReportingStatus")
        if held_kind(outcome.get("anticipated_posting_date")) == "plain":
            status = f"{status} (anticipated {date_text(outcome['anticipated_posting_date'])})"
        head = (
            value_words(outcome.get("type"), "OutcomeMeasureType"),
            value_words(outcome.get("title")),
            value_words(outcome.get("description")),
            value_words(outcome.get("population")),
            status,
            value_words(outcome.get("time_frame")),
        )
        base = f"/studies/{number}/posted_outcomes/{o}"
        found = measurement_rows(
            study["nct"], base, outcome, head, (outcome,), {"measure": outcome, "dispersion": ""}
        )
        if not found:
            values = (
                study["nct"],
                base,
                *head,
                *(NOT_POSTED,) * 4,
                value_words(outcome.get("param_type"), "MeasureParam"),
                NOT_POSTED,
                NOT_POSTED,
                value_words(outcome.get("unit")),
                NOT_POSTED,
            )
            found = [tuple(cell(value, "known", base) for value in values)]
        rows += found
    return rows


def baseline_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Baseline rows: one per measurement (characteristic × class × category × group), each group
    named within the baseline module, its denominator at the scope the registry gives it."""
    baseline = study.get("baseline")
    if not isinstance(baseline, dict):
        return []
    rows = []
    for m, measure in enumerate(baseline.get("measures") or []):
        title = value_words(measure.get("title"))
        if stated(measure.get("description")):
            title = f"{title}\n{value_words(measure.get('description'))}"
        population = measure.get("population")
        population = population if stated(population) else baseline.get("population")
        head = (title, value_words(population))
        base = f"/studies/{number}/baseline/measures/{m}"
        extra = {"measure": measure, "dispersion": "MeasureDispersionType"}
        rows += measurement_rows(study["nct"], base, baseline, head, (measure, baseline), extra)
    return rows


def analysis_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Statistical analyses rows: one per analysis of a posted measure, its compared groups named
    within that measure; a part the registry leaves empty "Not stated" in a column's first part, left out
    after it."""
    rows = []
    held = study.get("posted_outcomes")
    for o, outcome in enumerate(held if isinstance(held, list) else []):
        groups = outcome.get("groups")
        for a, analysis in enumerate(outcome.get("analyses") or []):
            address = f"/studies/{number}/posted_outcomes/{o}/analyses/{a}"

            def part(name: str, dictionary: str = "", item: dict = analysis) -> Any:
                return value_words(item.get(name), dictionary)

            def more(*names: str, item: dict = analysis) -> str:
                return "".join(f"\n{value_words(item.get(name))}" for name in names if stated(item.get(name)))

            compared = [group_title(groups, group) for group in analysis.get("groups") or []]
            interval = NOT_STATED
            if stated(analysis.get("ci_lower")) or stated(analysis.get("ci_upper")):
                level = f"{part('ci_percent')}% " if stated(analysis.get("ci_percent")) else ""
                sides = (
                    f"{part('ci_sides', 'ConfidenceIntervalNumSides')} "
                    if stated(analysis.get("ci_sides"))
                    else ""
                )
                interval = f"{level}{sides}interval: {part('ci_lower')} to {part('ci_upper')}"
            estimate = str(part("param_value"))
            if stated(analysis.get("dispersion_value")):
                estimate += (
                    f" ({part('dispersion_type', 'AnalysisDispersionType')}: {part('dispersion_value')})"
                )
            values = (
                study["nct"],
                address,
                value_words(outcome.get("title")),
                ("; ".join(compared) or NOT_STATED) + more("group_description"),
                str(part("method")) + more("method_comment"),
                part("param_type"),
                estimate + more("estimate_comment"),
                interval + more("ci_lower_comment", "ci_upper_comment"),
                str(part("p_value")) + more("p_value_comment"),
                str(part("hypothesis", "NonInferiorityType")) + more("hypothesis_comment"),
                part("other_description"),
            )
            # an estimate or p-value that is the registry's plain decimal alone is a number
            rows.append(numbered(values, address, (6, 8)))
    return rows


FIXED_MILESTONES = tuple(contract.DISPLAY["FlowMilestone"])


def flow_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Participant flow rows: one per period × milestone (or reason not completed) × group, the
    count as the registry gives it, each group named within the flow."""
    flow = study.get("participant_flow")
    if not isinstance(flow, dict):
        return []
    rows = []
    groups = flow.get("groups")
    for p, period in enumerate(flow.get("periods") or []):
        entries = [
            # the registry's three fixed milestones in words; a sponsor's own milestone as written
            (
                "milestones",
                i,
                value_words(
                    item.get("type"), "FlowMilestone" if item.get("type") in FIXED_MILESTONES else ""
                ),
                item,
            )
            for i, item in enumerate(period.get("milestones") or [])
        ]
        entries += [
            ("withdrawals", i, f"Not completed: {value_words(item.get('reason'))}", item)
            for i, item in enumerate(period.get("withdrawals") or [])
        ]
        for kind, i, named, item in entries:
            for c, count in enumerate(item.get("counts") or []):
                address = f"/studies/{number}/participant_flow/periods/{p}/{kind}/{i}/counts/{c}"
                participants = value_words(count.get("participants"))
                if stated(count.get("units")):
                    participants = f"{participants} ({value_words(count.get('units'))} units)"
                comments = [
                    value_words(held) for held in (item.get("comment"), count.get("comment")) if stated(held)
                ]
                values = (
                    study["nct"],
                    address,
                    value_words(period.get("title")),
                    named,
                    group_title(groups, count.get("group")),
                    participants,
                    "\n".join(str(held) for held in comments) or NOT_STATED,
                )
                rows.append(numbered(values, address, (5,)))
    return rows


def safety_groups(record: dict[str, Any]) -> int:
    """n of the Safety sheet's G1 ... Gn: the most adverse-event groups any trial of the record has."""
    return max(
        (
            len(study["adverse_events"].get("groups") or [])
            for study in record["studies"]
            if isinstance(study.get("adverse_events"), dict)
        ),
        default=0,
    )


def stat_cell(count: Any, key: str) -> Any:
    """One group's count of one term (pure — pinned): the registry's number as held (a listed zero stays 0);
    a count the registry does not give for the group — "Not reported"."""
    held = count.get(key) if isinstance(count, dict) else None
    return held if held_kind(held) == "plain" else NOT_REPORTED


def safety_rows(study: dict[str, Any], number: int, n: int) -> list[tuple]:
    """A trial's Safety rows: one per table × term, then for each of its adverse-event groups G1 ... (in the
    module's order) affected, at risk and events; G columns past its own groups blank (None) by construction.
    Unlisted events are never zeros: a trial posts only the terms its tables list."""
    held = study.get("adverse_events")
    events = held if isinstance(held, dict) else {}
    groups = [group.get("id") for group in events.get("groups") or []]
    rows = []
    for e, event in enumerate(events.get("events") or []):
        address = f"/studies/{number}/adverse_events/events/{e}"
        counts = {count.get("group"): count for count in event.get("counts") or []}
        cells: list[Any] = []
        for g in range(n):
            if g >= len(groups):
                cells += [None, None, None]
                continue
            count = counts.get(groups[g])
            cells += [stat_cell(count, key) for key in ("affected", "at_risk", "events")]
        values = (
            study["nct"],
            address,
            str(event.get("table", "")).capitalize() or NOT_STATED,
            value_words(event.get("organ_system")),
            value_words(event.get("term")),
            *cells,
            value_words(event.get("vocabulary")),
            value_words(event.get("assessment"), "EventAssessment"),
            value_words(event.get("notes")),
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


def group_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Groups rows: the groups of its baseline, participant flow and adverse events, each keyed
    within its module (never matched across modules); the adverse-event groups named G1 ... with their totals.
    A posted measure's groups are named on each Posted results row instead."""
    rows = []
    for key, words in (
        ("baseline", "Baseline"),
        ("participant_flow", "Participant flow"),
        ("adverse_events", "Adverse events"),
    ):
        module = study.get(key)
        if not isinstance(module, dict):
            continue
        for g, group in enumerate(module.get("groups") or []):
            address = f"/studies/{number}/{key}/groups/{g}"
            events = key == "adverse_events"
            values = (
                study["nct"],
                address,
                words,
                value_words(group.get("id")),
                f"G{g + 1}" if events else None,
                value_words(group.get("title")),
                value_words(group.get("description")),
                group_totals(group) if events else None,
            )
            rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


def criterion_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Eligibility rows: one per criterion, its heading, number, role, words and typed readings; a
    trial whose criteria the record does not list — one row saying so."""
    held = study.get("criteria")
    criteria = held if isinstance(held, list) else []
    rows = []
    for c, criterion in enumerate(criteria):
        address = f"/studies/{number}/criteria/{c}"
        values = (
            study["nct"],
            address,
            HEADINGS.get(str(criterion.get("heading")), value_words(criterion.get("heading"))),
            value_words(criterion.get("number")),
            role_words(criterion.get("role")),
            value_words(criterion.get("text")),
            criterion_readings(criterion.get("readings")),
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    if not rows:
        address = f"/studies/{number}"
        values = (study["nct"], address, *(NOT_STATED,) * 4, NO_READING)
        rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


def registered_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Registered outcomes rows: one per outcome it planned to measure, never a result."""
    rows = []
    held = study.get("registered_outcomes")
    for o, outcome in enumerate(held if isinstance(held, list) else []):
        address = f"/studies/{number}/registered_outcomes/{o}"
        readings = []
        for name in ("endpoint_classes", "time_points"):
            value = outcome.get(name)
            if held_kind(value) == "reading" and value["status"] == "known" and not value["result"]:
                readings.append(NO_READING)
            else:
                readings.append(value_words(value) if value is not None else NO_READING)
        values = (
            study["nct"],
            address,
            str(outcome.get("category", NOT_STATED)).capitalize(),
            value_words(outcome.get("measure")),
            value_words(outcome.get("description")),
            value_words(outcome.get("time_frame")),
            *readings,
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


def biomarker_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Biomarkers rows: one per mention the rule read (the biomarker, its states, its role, the
    words read, the rule); a mention is no assay, specimen or timing, which the registry does not report."""
    value = study.get("biomarker_mentions")
    if held_kind(value) != "reading" or not isinstance(value["result"], list):
        return []
    rows = []
    for k, mention in enumerate(value["result"]):
        address = f"/studies/{number}/biomarker_mentions/result/{k}"
        values = (
            study["nct"],
            address,
            value_words(mention.get("biomarker")),
            value_words(mention.get("states"), "", " or "),
            value_words(mention.get("role")),
            f"“{value_words(mention.get('words'))}”",
            str(value["rule"]),
        )
        rows.append(tuple(cell(item, "known", address) for item in values))
    return rows


def pointer_field(pointer: str) -> str:
    """The contract field a JSON pointer into the record names: list positions as "[]"."""
    parts = []
    for part in pointer.strip("/").split("/"):
        if part.isdigit():
            parts[-1] += "[]"
        else:
            parts.append(part)
    return ".".join(parts)


def readings_of(node: Any, pointer: str) -> list[tuple[str, dict[str, Any]]]:
    """Every rule's reading below `node`, with its JSON pointer, in the record's order."""
    found = []
    stack = [(pointer, node)]
    for where, held in stack:
        if held_kind(held) == "reading":
            found.append((where, held))
        elif isinstance(held, dict):
            stack.extend((f"{where}/{key}", value) for key, value in held.items())
        elif isinstance(held, list):
            stack.extend((f"{where}/{i}", value) for i, value in enumerate(held))
    return sorted(
        found, key=lambda item: [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in item[0].split("/")]
    )


def reading_result(field: str, value: dict[str, Any]) -> str:
    """A reading's result, in the words its own sheet uses."""
    if field.endswith("criteria[].readings"):
        return (
            criterion_readings(value).replace("Reading: ", "") if value["result"] else "No reading produced"
        )
    if field.endswith("criteria[].role"):
        return role_words(value)
    if field.endswith("biomarker_mentions"):
        return f"{len(value['result'] or [])} mentions (Biomarkers)"
    if field == "studies[].universe" and isinstance(value["result"], dict):
        return (
            " and ".join(UNIVERSE_LABELS.get(u, u) for u in value["result"].get("universes") or []) or "none"
        )
    return result_words(value["result"])


def reading_rows(study: dict[str, Any], number: int, versions: dict[str, Any]) -> list[tuple]:
    """A trial's Readings rows: one per rule reading the record holds (the field, the words read, the rule
    and its version, the result, the status)."""
    rows = []
    for pointer, value in readings_of(study, f"/studies/{number}"):
        field = pointer_field(pointer)
        named = contract.FIELD_NAMES.get(field) or contract.FIELD_NAMES.get(field.removesuffix("[]"))
        words = value.get("words") or []
        read = "; ".join(f"“{word}”" for word in words if isinstance(word, str) and word.strip())
        rule = str(value["rule"])
        version = versions.get(rule.split(".")[0], f"TrialLedger {__version__}")
        values = (
            study["nct"],
            pointer,
            named.label if named else field,
            read or ("Its heading" if field.endswith("criteria[].role") else NOT_STATED),
            f"{rule} ({version})",
            reading_result(field, value),
            STATUS_LABELS.get(value["status"], STATUS_LABELS["unresolved"]),
        )
        rows.append(tuple(cell(item, "known", pointer) for item in values))
    return rows


def too_few(record: dict[str, Any], what: str, none: str) -> str:
    """The one line of an across-trial sheet the record holds no row of: below the signal minimum, "Too few
    comparable trials to assess" with the counts; at or above it, `none` (the record's section holds no row
    for these trials)."""
    cohort = record.get("cohort")
    thresholds = cohort.get("thresholds") if isinstance(cohort, dict) else None
    minimum = thresholds.get("signal_min_trials") if isinstance(thresholds, dict) else None
    sponsors = thresholds.get("signal_min_sponsors") if isinstance(thresholds, dict) else None
    trials = len(record["studies"])
    if isinstance(minimum, int) and trials >= minimum:
        return none
    need = f"; {what} need at least {minimum} comparable trials" if minimum else ""
    need += f" from {sponsors} sponsors" if minimum and sponsors else ""
    return f"Too few comparable trials to assess: {trials} trial{'s' if trials != 1 else ''} here{need}."


FINDING_TYPES = {
    "frequency": "Criteria most trials share",
    "mechanism_signals": "Exclusions that follow a drug's mechanism",
    "occupancy": "Setting and class combinations tried and untried",
    "near_misses": "Trials differing in one design choice",
    "aligned_near_misses": "Trials differing in one design choice, drug classes aligned",
    "endpoints": "Endpoints and time points across trials",
    "structure_relations": "Drugs sharing a structure class",
}
FINDING_RULES = {
    field.name.removeprefix("cohort."): field.source[0]
    for field in contract.FIELDS
    if field.name.removeprefix("cohort.") in FINDING_TYPES
}


def findings_rows(record: dict[str, Any]) -> list[tuple]:
    """The Across-trial findings: one row per supported finding of the record's cohort section, its counts in
    words; below the signal minimum, or with none, one line saying so."""
    cohort = record.get("cohort") if isinstance(record.get("cohort"), dict) else {}
    thresholds = cohort.get("thresholds") if isinstance(cohort.get("thresholds"), dict) else {}
    limits = ", ".join(f"{key.replace('_', ' ')} {value}" for key, value in thresholds.items()) or NOT_STATED
    rows = []
    for kind, words in FINDING_TYPES.items():
        for i, entry in enumerate(cohort.get(kind) or []):
            address = f"/cohort/{kind}/{i}"
            held = dict(entry) if isinstance(entry, dict) else {"value": entry}
            trials = [str(held.pop(key)) for key in ("a", "b", "ncts") if key in held]
            numbers = [
                f"{held[key]} of {held[of]}"
                for key, of in (("stating", "trials"), ("in_class_stating", "in_class"))
                if key in held
            ]
            finding = "; ".join(
                f"{key.replace('_', ' ')}: {result_words(value)}" for key, value in held.items()
            )
            values = (
                address,
                words,
                finding,
                "\n".join(trials) or NOT_STATED,
                "; ".join(numbers) or NOT_STATED,
                limits,
                FINDING_RULES.get(kind, kind),
            )
            rows.append(tuple(cell(value, "known", address) for value in values))
    if not rows:
        rows.append(
            (
                cell("/cohort", "known"),
                cell(
                    too_few(
                        record,
                        "across-trial findings",
                        "The record holds no across-trial finding for these trials",
                    ),
                    "known",
                ),
                *(cell(None, "known"),) * 5,
            )
        )
    return rows


def standard_rows(record: dict[str, Any]) -> list[tuple]:
    """The Standard protocol language rows: one per criterion most comparable trials state, with how many of
    how many, a representative wording verbatim, its trial and the others; none — one line saying so."""
    held = record.get("standard_language")
    rows = []
    for i, entry in enumerate(held if isinstance(held, list) else []):
        address = f"/standard_language/{i}"
        values = (
            value_words(entry.get("criterion")),
            HEADINGS.get(str(entry.get("role")), value_words(entry.get("role"))),
            value_words(entry.get("trials")),
            value_words(entry.get("of_trials")),
            f"“{value_words(entry.get('wording'))}”",
            value_words(entry.get("wording_from")),
            value_words(entry.get("other_trials"), "", ", "),
            address,
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    if not rows:
        line = too_few(
            record,
            "standard protocol language",
            "No criterion is stated by most comparable trials (the same universe) in this record",
        )
        rows.append((cell(line, "known"), *(cell(None, "known"),) * 6, cell("/standard_language", "known")))
    return rows


SOURCE_KIND = {"plain": "{path}", "reading": "rule {path}", "run": "recorded by the run ({path})"}


def dictionary_rows(n: int) -> list[tuple]:
    """The Column dictionary: each sheet's columns, once, with the registry fields or rules they show and
    what they hold."""
    rows = []
    for sheet in contract.SHEETS:
        if sheet.name not in BUILT:
            continue
        for column in sheet.columns:
            if column.shows == "address":
                source = "A JSON pointer into landscape.json"
                definition = "Where the row's value is in the record: ask the assistant about the row by it"
            else:
                fields = [contract.FIELD_NAMES[name] for name in column.fields]
                source = "\n".join(
                    dict.fromkeys(
                        SOURCE_KIND[field.kind].format(path=path) for field in fields for path in field.source
                    )
                )
                definition = "\n".join(dict.fromkeys(field.label for field in fields))
            header = (
                column.header.format(n="1 ... G" + str(n)) if column.shows == "per group" else column.header
            )
            rows.append(tuple(label(value) for value in (sheet.name, header, source, definition)))
    return rows


# ── the Read me and the Trial index ─────────────────────────────────────────────────────────────────────

ID_WORDS = {
    "found": "found",
    "aliased": "found under another number, {study}",
    "missing": "not found",
    "duplicate": "asked for twice",
    "malformed": "not a trial number",
}
SLOT_WORDS = {
    "drug": "Drug",
    "drug_class": "Drug class",
    "mechanism": "Mechanism",
    "condition": "Condition",
    "condition_class": "Condition class (a MeSH term, with every term under it)",
    "phase": "Phase",
    "status": "Status",
    "study_type": "Study type",
    "start_from": "Started on or after",
    "start_to": "Started on or before",
}


def search_plain_words(request: Any) -> str:
    """The search as the person asked it, in words: trials by number; each slot named in
    words, its codes through DISPLAY (Phase, Status, StudyType); any other registry setting as "<name>
    <value>"; nothing — "Not stated"."""
    if not isinstance(request, dict) or not request:
        return NOT_STATED
    lines = []
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    if params.get("filter.ids"):
        lines.append(f"Trials asked for by number: {', '.join(str(params['filter.ids']).split(','))}")
    dictionaries = {"phase": "Phase", "status": "Status", "study_type": "StudyType"}
    for slot, words in SLOT_WORDS.items():
        if slot not in request:
            continue
        held = request[slot]
        if isinstance(held, dict):
            shown_ = ", ".join(f"{key} {item}" for key, item in held.items())
        elif isinstance(held, list):
            shown_ = " or ".join(item_words(item, dictionaries.get(slot, "")) for item in held)
        else:
            shown_ = item_words(held, dictionaries.get(slot, ""))
        lines.append(f"{words}: {shown_}")
    lines += [f"Registry setting {name}: {value}" for name, value in params.items() if name != "filter.ids"]
    return "\n".join(lines) or NOT_STATED


def found_words(record: dict[str, Any]) -> str:
    """What the run found, in words: the trials matched and read, each number asked, how the pages came."""
    held = record["manifest"].get("retrieval")
    retrieval = held if isinstance(held, dict) else {}
    matched, read = retrieval.get("matched", NOT_STATED), retrieval.get("read", NOT_STATED)
    lines = [
        f"The registry matched {matched} trials; {read} were read, {len(record['studies'])} in this "
        "workbook, one row each in the Trial index."
    ]
    for entry in retrieval.get("requested_ids") or []:
        words = ID_WORDS.get(entry.get("status"), str(entry.get("status"))).format(study=entry.get("study"))
        lines.append(f"{entry.get('requested')}: {words}")
    lines.append(retrieval_mode_words(retrieval))
    classes = retrieval.get("drug_classes")
    if isinstance(classes, dict) and classes.get("state") == "not_looked_up":
        lines.append("Drug classes were not looked up in this run; each reads so, never as no class.")
    return "\n".join(lines)


HOW_TO_READ = "\n".join(
    (
        "Start with the Trial index: one row per trial, in short clinical words. A trial's Dossier link "
        "opens its Trial review: the trial's record, top to bottom, in bands; the Basis column says whether "
        "each value is the registry's, a reading by one of TrialLedger's named rules, or not stated.",
        "The listings compare trials row by row: Eligibility (every criterion, verbatim, with its readings), "
        "Registered outcomes (what each trial planned to measure, never a result), Posted results (one row "
        "per measurement, each group named within its own measure, its denominator at the scope the registry "
        "gives it), Statistical analyses, Baseline, Participant flow, Groups (the adverse-event groups named "
        "G1, G2, ...), Safety (one row per adverse-event term, then for each group G1, G2, ... the "
        "participants affected, at risk, and the events), Biomarkers, and the readings across trials.",
        "Every listing row's Address in the record is where the assistant finds that row in landscape.json: "
        "ask about a row by its address. The Readings sheet lists every reading a rule made, with the words "
        "it read; the Column dictionary says where each column comes from.",
        "A cell says in words what the registry does not give (Not stated, Not posted, Not reported, No "
        "reading produced). A blank cell is one whose column cannot apply to its row: a Safety group column "
        "past the trial's own groups, the unnamed class or category of a posted measure.",
    )
)


def provenance_words(record: dict[str, Any]) -> str:
    """The technical provenance, in words, last on the Read me."""
    manifest = record["manifest"]
    held = manifest.get("rule_versions")
    versions = held if isinstance(held, dict) else {}
    lines = [
        f"Registry: ClinicalTrials.gov API {manifest.get('api_version', NOT_STATED)}; data as of "
        f"{date_text(manifest.get('data_timestamp'))}",
        f"Record: landscape.json schema {record.get('schema_version', NOT_STATED)}; code commit "
        f"{manifest.get('code_commit', NOT_STATED)}",
        f"Workbook: {BOOK_VERSION}; clinical words {contract.DISPLAY_VERSION}; TrialLedger {__version__}",
    ]
    lines += [f"Rule version, {name}: {value}" for name, value in versions.items()]
    scope = record.get("scope")
    query = scope.get("query") if isinstance(scope, dict) else None
    if isinstance(query, dict):
        lines += [f"Registry search sent, {name}: {value}" for name, value in query.items()]
    return "\n".join(lines)


def domain_words() -> str:
    """Which trials the treatment setting, prior lines and gene selection are read for, from the universe
    table."""
    lines = []
    for universe in contract.UNIVERSES:
        read = [pack.label.lower() for pack in universe.packs]
        if read:
            lines.append(f"For {TRIAL_WORDS[universe.name]}: {'; '.join(read)}")
    lines.append(f"For {TRIAL_WORDS['general']}: none of them")
    return "\n".join(lines)


def guide_rows(record: dict[str, Any]) -> list[tuple]:
    """The Read me: contract.READ_ME_TOPICS, in order, each (topic, content) in words."""
    held = record.get("statuses")
    statuses = held if isinstance(held, dict) else {}
    coverage = (
        record.get("coverage", {}).get("universe") if isinstance(record.get("coverage"), dict) else None
    )
    supported = NOT_STATED
    if isinstance(coverage, dict):
        unsupported = coverage.get("unsupported") or {}
        supported = (
            f"{item_words(coverage.get('study_type'), 'StudyType')} studies started from "
            f"{coverage.get('start_from')} to {coverage.get('start_to')}; "
            + "; ".join(f"{item_words(kind, 'StudyType')}: {why}" for kind, why in unsupported.items())
        )
    content = {
        "The search, in plain words": search_plain_words(record.get("request")),
        "What it found": found_words(record),
        "How to read this workbook": HOW_TO_READ,
        "What each status means": "\n".join(
            f"{STATUS_LABELS.get(name, name)}: {meaning}" for name, meaning in statuses.items()
        )
        or NOT_STATED,
        "What the registry does not report": "The registry's records do not hold:\n"
        + "\n".join(f"- {item}" for item in contract.NOT_REPORTED_BY_REGISTRY)
        + "\nA posted safety table lists only the terms over its frequency threshold, and posted results "
        "only the measures the sponsor posted: neither is a complete account of harm or efficacy.",
        "Treatment setting and line": contract.TREATMENT_CONTEXT_LIMIT
        + " They are read only for the trials below; for any other trial they read Not applicable.\n"
        + domain_words(),
        "The trials TrialLedger supports": supported,
        "Technical provenance": provenance_words(record),
    }
    return [(label(topic), cell(content[topic], LABEL)) for topic, _names in contract.READ_ME_TOPICS]


def design_words(study: dict[str, Any]) -> str:
    """The index's design in short words: purpose, allocation, model, masking (who is masked)."""
    parts = [
        value_words(study.get(name), contract.FIELD_NAMES[f"studies[].{name}"].display)
        for name in ("primary_purpose", "allocation", "intervention_model")
    ]
    masking = value_words(study.get("masking"), "DesignMasking")
    if held_kind(study.get("who_masked")) == "plain" and applies("studies[].who_masked", study):
        masking += f" ({value_words(study['who_masked'], 'WhoMasked', ', ')})"
    return "; ".join(str(part) for part in [*parts, f"masking {masking}"])


def index_cells(study: dict[str, Any], dossier: str, publications: str) -> tuple:
    """One trial's Trial index row, short fields only (no cell sized by prose): `dossier` and `publications`
    are the in-workbook links to its dossier and its dossier's publications band."""
    acronym = study.get("acronym")
    short = acronym if held_kind(acronym) == "plain" else study.get("brief_title")
    status = value_words(study.get("overall_status"), "Status")
    if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):
        status = f"{status} (last known: {value_words(study['last_known_status'], 'Status')})"
    held = study.get("registered_outcomes")
    primary = [o for o in (held if isinstance(held, list) else []) if o.get("category") == "primary"]
    endpoint = value_words(primary[0].get("measure")) if primary else NOT_STATED
    endpoint = f"{endpoint} (+{len(primary) - 1} more)" if len(primary) > 1 else endpoint
    first = study.get("results_first_posted")
    results = (
        date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[0]
    )
    held = study.get("references")
    references = held if isinstance(held, list) else []
    marked = sum(1 for reference in references if reference.get("type") == "RESULT")
    cited = f"{len(references)} ({marked} marked as results)" if references else NOT_STATED
    sponsor, _ = shown_field(study, "studies[].lead_sponsor.name")
    enrollment, _ = shown_field(study, "studies[].enrollment.count")
    start, _ = shown_field(study, "studies[].start_date.date")
    update = study.get("last_update_posted")
    return (
        cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),
        cell(value_words(short), "known"),
        cell(sponsor, "known"),
        cell(value_words(study.get("phases"), "Phase", " / "), "known"),
        cell(status, "known"),
        cell(value_words(study.get("conditions")), "known"),
        cell(universe_words(study)[0], "known"),
        cell(design_words(study), "known"),
        cell(str(enrollment), "known"),
        cell(start, "known"),
        cell(endpoint, "known"),
        cell(results, "known"),
        cell(cited, "known", "", "", "", publications if references else ""),
        cell(value_words(study.get("countries")), "known"),
        cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, "known"),
        cell(coordinate_short(study, "setting"), "known"),
        cell(coordinate_short(study, "prior_advanced_lines"), "known"),
        cell(coordinate_short(study, "selection"), "known"),
        cell("Dossier", LABEL, "", "", "", dossier),
    )


# ── the plan, the writer and the read-back ──────────────────────────────────────────────────────────────


def sheet_headers(name: str, n: int) -> tuple[str, ...]:
    """A sheet's headers, as contract.SHEETS declares them, each per-group column repeated for G1 ... Gn."""
    sheet = next(held for held in contract.SHEETS if held.name == name)
    headers: list[str] = []
    per_group = [column.header for column in sheet.columns if column.shows == "per group"]
    for column in sheet.columns:
        if column.shows != "per group":
            headers.append(column.header)
        elif column.header == per_group[0]:
            headers += [header.format(n=g) for g in range(1, n + 1) for header in per_group]
    return tuple(headers)


# Each sheet's layout: frozen panes, the width of each column (characters; the rest DEFAULT_WIDTH), whether
# its text wraps (the index's does not, so no row is sized by its prose), and the most lines a row shows
# before the reader widens it (its full text is in the cell).
DEFAULT_WIDTH = 16
LINE_POINTS = 12.75
LISTING = {"Trial ID": 13, contract.ADDRESS: 22}
LAYOUT: dict[str, tuple[str, dict[str, int], bool, int]] = {
    contract.READ_ME: ("B2", {"Topic": 30, "Content": 110}, True, 40),
    contract.INDEX: (
        "B2",
        {
            "Trial ID": 13,
            "Acronym or short title": 30,
            "Sponsor": 26,
            "Phase": 15,
            "Status": 18,
            "Conditions": 28,
            "Universe": 28,
            "Design": 44,
            "Enrollment": 16,
            "Start": 20,
            "Primary endpoint": 40,
            "Results posted": 14,
            "Publications": 20,
            "Countries": 24,
            "Last update posted": 14,
            "Treatment setting": 22,
            "Prior lines for advanced disease": 22,
            "Gene selection": 18,
            "Dossier": 9,
        },
        False,
        1,
    ),
    contract.REVIEW: ("D2", {"Trial ID": 13, "Section": 22, "Fact": 30, "Value": 100, "Basis": 12}, True, 20),
    contract.ELIGIBILITY: (
        "C2",
        {
            **LISTING,
            "Heading": 11,
            "Criterion number": 10,
            "Role": 24,
            "Criterion as written": 70,
            "Readings": 44,
        },
        True,
        8,
    ),
    contract.REGISTERED: (
        "C2",
        {
            **LISTING,
            "Category": 11,
            "Measure": 40,
            "Description": 50,
            "Time frame": 30,
            "Endpoint reading": 24,
        },
        True,
        6,
    ),
    contract.POSTED: (
        "C2",
        {
            **LISTING,
            "Measure": 36,
            "Measure description": 36,
            "Analysis population": 36,
            "Time frame": 26,
            "Group": 28,
            "Denominator": 18,
            "Comment": 30,
        },
        True,
        6,
    ),
    contract.ANALYSES: (
        "C2",
        {
            **LISTING,
            "Measure": 36,
            "Compared groups": 30,
            "Method": 26,
            "Estimate": 20,
            "Confidence interval": 24,
        },
        True,
        6,
    ),
    contract.BASELINE: (
        "C2",
        {**LISTING, "Characteristic": 30, "Population": 30, "Group": 28, "Denominator": 18, "Comment": 24},
        True,
        6,
    ),
    contract.FLOW: (
        "C2",
        {**LISTING, "Period": 22, "Milestone or reason": 30, "Group": 30, "Comment": 30},
        True,
        4,
    ),
    contract.GROUPS: (
        "C2",
        {**LISTING, "Module": 24, "Column": 8, "Title": 30, "Description": 50, "Totals": 34},
        True,
        6,
    ),
    contract.SAFETY: ("F2", {**LISTING, "Table": 9, "Organ system": 28, "Term": 28}, True, 3),
    contract.BIOMARKERS: (
        "C2",
        {**LISTING, "Biomarker": 14, "States": 18, "Role": 14, "Words read": 50, "Rule": 26},
        True,
        4,
    ),
    contract.FINDINGS: (
        "B2",
        {
            contract.ADDRESS: 22,
            "Type": 30,
            "Finding": 70,
            "Trial IDs": 16,
            "Numerator / denominator": 18,
            "Population and limits": 30,
            "Rule": 26,
        },
        True,
        8,
    ),
    contract.STANDARD: (
        "B2",
        {
            "Criterion": 34,
            "Role": 11,
            "Representative wording": 60,
            "Wording from": 14,
            "Other trials": 30,
            contract.ADDRESS: 22,
        },
        True,
        6,
    ),
    contract.READINGS: (
        "C2",
        {**LISTING, "Field": 30, "Words read": 50, "Rule and version": 30, "Result": 40, "Status": 12},
        True,
        4,
    ),
    contract.DICTIONARY: (
        "C2",
        {"Sheet": 20, "Column": 28, "Registry field or rule": 60, "Definition": 50},
        True,
        8,
    ),
}
BUILT = tuple(sheet.name for sheet in contract.SHEETS)


def written_safely(rows: list[tuple]) -> list[tuple]:
    """Rows every text cell of which a spreadsheet holds exactly: a text it cannot (cells.cell_text_state:
    too long, a character no cell holds) is written as "Unresolved — not written: <why>; it is in
    landscape.json at <its address>"."""
    out = []
    for row in rows:
        fixed = []
        for held in row:
            value = held[0]
            state = cell_text_state(value) if isinstance(value, str) else "ok"
            if state != "ok":
                where = held[3] or "the row's address"
                words = (
                    f"{UNRESOLVED}not written: {state.replace('_', ' ')}; it is in landscape.json at {where}"
                )
                held = (words, *held[1:])
            fixed.append(held)
        out.append(tuple(fixed))
    return out


# What a listing no trial of the workbook has a row in says, on its one line.
EMPTY_WORDS = {
    contract.BIOMARKERS: "No biomarker is named in these trials' eligibility criteria",
    contract.POSTED: "None of these trials posted results",
    contract.ANALYSES: "None of these trials posted a statistical analysis",
    contract.BASELINE: "None of these trials posted baseline characteristics",
    contract.FLOW: "None of these trials posted a participant flow",
    contract.GROUPS: "None of these trials posted results by group",
}


def book_plan(record: dict[str, Any]) -> list[tuple]:
    """Every sheet, in contract.SHEETS' order, as (name, headers, rows, page starts): the dossier first, so
    the index links to each trial's dossier and its publications band, and each band with a listing to the
    trial's first row there; each trial's dossier starts a printed page."""
    studies = record["studies"]
    n = safety_groups(record)
    held = record["manifest"].get("rule_versions")
    versions = held if isinstance(held, dict) else {}
    listings = {
        contract.ELIGIBILITY: criterion_rows,
        contract.REGISTERED: registered_rows,
        contract.POSTED: posted_rows,
        contract.ANALYSES: analysis_rows,
        contract.BASELINE: baseline_rows,
        contract.FLOW: flow_rows,
        contract.GROUPS: group_rows,
        contract.BIOMARKERS: biomarker_rows,
    }
    rows: dict[str, list[tuple]] = {name: [] for name in BUILT}
    first: dict[tuple[str, int], int] = {}
    for i, study in enumerate(studies):
        for name, rows_of in listings.items():
            first[(name, i)] = len(rows[name])
            rows[name] += rows_of(study, i)
        first[(contract.SAFETY, i)] = len(rows[contract.SAFETY])
        rows[contract.SAFETY] += safety_rows(study, i, n)
        first[(contract.READINGS, i)] = len(rows[contract.READINGS])
        rows[contract.READINGS] += reading_rows(study, i, versions)
    review: list[tuple] = []
    starts, links_ = [], []
    for i, study in enumerate(studies):
        starts.append(len(review))
        publications = None
        shown_band = ""
        for heading, listing, fact, value, label_ in dossier_facts(study):
            if heading != shown_band and listing:
                count = sum(1 for row in rows[listing] if row[0][0] == study["nct"])
                part, row_number = place(first[(listing, i)], CAPACITY, listing)
                link = f"#'{part}'!A{row_number}" if count else ""
                words = f"{count} rows in {listing}" if count else f"No row in {listing}"
                review.append(
                    (
                        label(study["nct"]),
                        label(heading),
                        label("Detail"),
                        cell(words, LABEL, "", "", "", link),
                        label(NOTE),
                    )
                )
            shown_band = heading
            if heading == "Publications and documents" and publications is None:
                publications = len(review)
            review.append(
                (label(study["nct"]), label(heading), label(fact), cell(value, "known"), label(label_))
            )
        sheet, row_number = place(starts[-1], CAPACITY, contract.REVIEW)
        sheet_p, row_p = place(publications or starts[-1], CAPACITY, contract.REVIEW)
        links_.append((f"#'{sheet}'!A{row_number}", f"#'{sheet_p}'!A{row_p}"))
    for name in listings:
        if not rows[name]:
            words = EMPTY_WORDS.get(name, f"None of these trials has a row in {name}")
            width = len(sheet_headers(name, n))
            rows[name] = [(cell(words, LABEL), *(cell(None, LABEL),) * (width - 1))]
    rows[contract.READ_ME] = guide_rows(record)
    rows[contract.INDEX] = [index_cells(study, *held) for study, held in zip(studies, links_, strict=True)]
    rows[contract.REVIEW] = review
    rows[contract.FINDINGS] = findings_rows(record)
    rows[contract.STANDARD] = standard_rows(record)
    rows[contract.DICTIONARY] = dictionary_rows(n)
    return [
        (
            name,
            sheet_headers(name, n),
            written_safely(rows[name]),
            starts[1:] if name == contract.REVIEW else [],
        )
        for name in BUILT
    ]


def row_lines(row: tuple, widths: list[int]) -> int:
    """How many lines a wrapped row needs at the given column widths: for each text cell, the
    sum over its lines of the line's length divided by the column's width, rounded up (at least one line);
    the most of any cell."""
    most = 1
    for held, width in zip(row, widths, strict=True):
        value = held[0]
        if not isinstance(value, str):
            continue
        lines = sum(max(1, -(-len(part) // max(width, 1))) for part in value.split("\n"))
        most = max(most, lines)
    return most


def _book_styles(sheet: Any) -> dict[tuple[bool, str], Any]:
    """The cell styles of the book, made once: (header, wrap, line or number) to a style a cell copies."""
    styles = {}
    for header in (True, False):
        for kind, alignment in (
            ("wrap", TEXT),
            ("line", Alignment(horizontal="left", vertical="top", wrap_text=False)),
            ("number", NUMBER),
        ):
            template = WriteOnlyCell(sheet, value="")
            template.font = BOLD if header else FONT
            template.border = HEADER_BORDER if header else BORDER
            template.alignment = alignment
            if kind == "number":
                template.number_format = "#,##0"
            styles[(header, kind)] = template._style
    return styles


def book_format(held: tuple) -> str:
    """A number cell's format: the registry string's own decimal places (number_cell keeps them in the
    cell's fourth part), else a count's, with thousands separators."""
    return held[4] or COUNT_FORMAT


def _book_cell(sheet: Any, held: tuple, header: bool, wrap: bool, styles: dict) -> Any:
    """One written cell of the book: text forced to text, a number right-aligned in its format (book_format),
    a link kept."""
    value, link = held[0], held[1]
    written = WriteOnlyCell(sheet, value=value)
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    kind = "number" if number else "wrap" if wrap else "line"
    if isinstance(value, str):
        written.data_type = "s"
    written._style = copy(styles[(header, kind)])
    if number:
        written.number_format = book_format(held)
    if link.startswith("#"):
        written.hyperlink = Hyperlink(ref="", location=link[1:], display=str(value))
    elif link:
        written.hyperlink = link
    return written


def _write_book(plan: list[tuple], footer: tuple[str, str, str]) -> tuple[bytes, int]:
    """The book's bytes, every write time fixed, and the number of cells written."""
    book = Workbook(write_only=True)
    styles: dict = {}
    written = 0
    for name, headers, rows, starts in plan:
        freeze, widths, wrap, most = LAYOUT[name]
        width_of = [widths.get(header, DEFAULT_WIDTH) for header in headers]
        for start in range(0, max(len(rows), 1), CAPACITY):
            part_name = place(start, CAPACITY, name)[0]
            part = rows[start : start + CAPACITY]
            sheet = book.create_sheet(part_name)
            styles = styles or _book_styles(sheet)
            last = get_column_letter(len(headers))
            sheet.freeze_panes = freeze
            for number, width in enumerate(width_of, 1):
                sheet.column_dimensions[get_column_letter(number)].width = width
            sheet.auto_filter.ref = f"A1:{last}{len(part) + 1}"
            sheet.print_title_rows = "1:1"
            sheet.print_area = f"A1:{last}{len(part) + 1}"
            sheet.page_setup.orientation = "landscape"
            sheet.sheet_properties.pageSetUpPr.fitToPage = True
            sheet.page_setup.fitToWidth = 1
            sheet.page_setup.fitToHeight = 0
            sheet.oddFooter.left.text, sheet.oddFooter.center.text, sheet.oddFooter.right.text = footer
            for begin in starts:
                if start <= begin < start + len(part):
                    sheet.row_breaks.append(Break(id=begin - start + 1))
            for number, row in enumerate(part, 2):
                lines = min(most, row_lines(row, width_of)) if wrap else 1
                sheet.row_dimensions[number].height = round(lines * LINE_POINTS, 2)
            sheet.append([_book_cell(sheet, label(header), True, True, styles) for header in headers])
            for row in part:
                sheet.append([_book_cell(sheet, held, False, wrap, styles) for held in row])
            written += len(headers) * (len(part) + 1)
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


def held_type(value: Any) -> str:
    """A cell's kind for the read-back: a number (a spreadsheet keeps 40.0 as 40, shown by its format),
    text, or blank."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return "blank" if value is None else type(value).__name__


def book_problems(record: dict[str, Any], path: Path, limit: int = 20) -> list[str]:
    """Every way the file at `path` differs from the book `record` derives, cell by cell (values and their
    types, blanks as None); an empty list certifies the file."""
    try:
        opened = load_workbook(path, read_only=True)
    except Exception as error:  # a file that is not this workbook can raise almost anything; it is named
        return [f"book.unreadable: {path.name} ({type(error).__name__}: {error})"]
    problems: list[str] = []
    try:
        expected = []
        for name, headers, rows, _starts in book_plan(record):
            for start in range(0, max(len(rows), 1), CAPACITY):
                part = place(start, CAPACITY, name)[0]
                expected.append(part)
                if part not in opened.sheetnames:
                    problems.append(f"sheet {part!r} is missing")
                    continue
                # each cell as (value, number format or "" for anything not a number)
                want = [tuple((header, "") for header in headers)] + [
                    tuple(
                        (held[0], book_format(held) if isinstance(held[0], (int, float)) else "")
                        for held in row
                    )
                    for row in rows[start : start + CAPACITY]
                ]
                have = [
                    tuple(
                        (got.value, got.number_format if isinstance(got.value, (int, float)) else "")
                        for got in row
                    )
                    for row in opened[part].iter_rows()
                ]
                if len(have) != len(want):
                    problems.append(f"{part}: {len(have)} rows, the derivation {len(want)}")
                for number, (wanted, held) in enumerate(zip(want, have, strict=False), 1):
                    if tuple(wanted) != tuple(held) or any(
                        held_type(a[0]) != held_type(b[0]) for a, b in zip(wanted, held, strict=False)
                    ):
                        problems.append(f"{part} row {number}: expected {wanted!r}, found {held!r}")
                    if len(problems) >= limit:
                        return problems
        if opened.sheetnames != expected:
            problems.append(f"sheets {opened.sheetnames} differ from the derivation's {expected}")
    finally:
        opened.close()
    return problems[:limit]


def write_book(record: dict[str, Any], path: Path) -> int:
    """Write the reviewer's workbook of a schema-3 record to `path`, read it back, and return the number of
    cells written; raise ReadoutError, leaving no file, unless every cell equals its derivation."""
    footer = footer_parts(
        search_plain_words(record.get("request")).replace("\n", "; "),
        date_text(record["manifest"].get("data_timestamp")),
    )
    data, written = _write_book(book_plan(record), footer)
    path.write_bytes(data)
    problems = book_problems(record, path, limit=1)
    if problems:
        path.unlink()
        raise ReadoutError("readout.readback_mismatch", problems[0])
    return written
