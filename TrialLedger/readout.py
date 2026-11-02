"""The clinical registry workbook derived from a schema-4 landscape record.

The index, dossiers, source eligibility passages and posted-data listings preserve source values and
absence states. Direct derivations retain their named sources in the record and dictionary. The workbook
is read back cell by cell, including numeric formats, and identical records produce identical bytes.
"""

from __future__ import annotations

import ast
import io
import posixpath
import re
import tokenize
import zipfile
from copy import copy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.pagebreak import Break

from TrialLedger import __version__, contract
from TrialLedger.cells import ROW_LIMIT, cell_number_state, cell_text_state
from TrialLedger.links import pubmed_link

NAME = "landscape.xlsx"

NOT_STATED = "Not stated"

NOT_POSTED = "Not posted"

NOT_APPLICABLE = "Not applicable"

REDACTED = "Not stated — withheld by the registry (a withheld study's field)"

UNRESOLVED = "Unresolved — "

LABEL = "label"

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ](.+))?)?)?")

FOOTER_LIMIT = 255  # Excel's limit on a header's or footer's text, its codes included

CAPACITY = ROW_LIMIT - 1  # data rows a worksheet holds below its header row


class ReadoutError(Exception):
    """Why landscape.xlsx was not written: the file read back does not hold its derivation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def cell(
    value: Any, status: str, source: str = "", rule: str = "", inputs: str = "", link: str = ""
) -> tuple:
    """One displayed value: (value, link, status, source, rule, inputs)."""
    return (value, link, status, source, rule, inputs)


def label(text: str) -> tuple:
    """TrialLedger's own words labelling a row."""
    return cell(text, LABEL)


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


FONT = Font(name="Arial", size=10)

LINK_FONT = Font(name="Arial", size=10, color="0563C1", underline="single")

BOLD = Font(name="Arial", size=10, bold=True)

EDGE = Side(style="thin", color="BFBFBF")

BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=EDGE)

HEADER_BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=Side(style="thin", color="000000"))

SECTION_EDGE = Side(style="medium", color="647B8C")

TEXT = Alignment(horizontal="left", vertical="top", wrap_text=True)

NUMBER = Alignment(horizontal="right", vertical="top")

WRITE_TIMES = re.compile(rb"<dcterms:(created|modified)\b[^>]*>[^<]*</dcterms:\1>")

ZIP_TIME = (1980, 1, 1, 0, 0, 0)


# ── landscape.json schema 3: the reviewer's workbook (refine-landscape-record 3.1-3.7) ─────────────────────
# The workbook contract.SHEETS lays out, derived from a schema-3 record alone. A registry value is held
# plain; a value the registry does not hold, or a rule's reading, is a value object (contract module
# docstring). Every code is shown through contract.DISPLAY; a reading is labelled ("Reading: ...", or the
# dossier's Basis column); a cell is blank only where its column cannot apply to its row by construction (a
# Safety group column past the trial's own groups; an unnamed class or category of a posted measure; a
# Groups column or total only adverse events have), and anything else the registry does not give is said in
# words. Every listing row's address is a JSON pointer to the node the row shows.

BOOK_VERSION = "book-4"
ABSENT_KEYS = ("status", "note")
READING_KEYS = ("status", "rule", "words", "result", "note")
NOT_REPORTED = "Not reported"
NO_GRADE = (
    "No dedicated grade field in the structured adverse-event tables; "
    "event terms or descriptions may state grades"
)
STATUS_LABELS = contract.STATUS_WORDS
REGISTRY, READING, NOTE = (contract.BASIS_WORDS[key] for key in ("registry", "reading", "note"))
# The key-criteria categories in clinical words: the contract's own labels.
# How a universe's trials are named, and what a reading defined for it is defined for.
# What would settle a coordinate the criteria leave open, in the eligibility criteria's own terms.
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
NOT_IN_DOSSIER = ("studies[].collection_presence",)  # Consumed by source availability summaries.
STOPPED = ("TERMINATED", "SUSPENDED", "WITHDRAWN")
# The dossier's one row per element of a registry list: what one element is called.
ELEMENT_WORDS = {
    "secondary_ids": "Other identifier",
    "condition_browse_leaves": "Registry condition browse term",
    "collaborators": "Collaborator",
    "officials": "Overall official",
    "arms": "Arm",
    "interventions": "Intervention",
    "registered_outcomes": "Registered outcome",
    "references": "Publication",
    "links": "Related link",
    "ipd_documents": "Shared participant data or document",
    "documents": "Posted document",
}
RESULTS_MODULES = ("posted_outcomes", "baseline", "participant_flow", "adverse_events")
HEADINGS = contract.READING_CODE_WORDS
# The clinical words of the typing banks' concepts (banks.type_criterion), a concept not listed shown with its
# underscores as spaces.


def held_kind(value: Any) -> str:
    """What a value of a schema-3 record is (pure — pinned).

    missing — None: the record holds no such key;
    absent  — a value object of exactly the keys status and note, in any order, both text: a value the
              registry does not hold;
    reading — a value object of exactly the keys status, rule, words, result and note, in any order, its
              status, rule and note text and its words a list: a rule's reading;
    plain   — anything else (an object of other keys, or of these keys in another shape): a registry value as
              the registry holds it.
    """
    if value is None:
        return "missing"
    if not isinstance(value, dict):
        return "plain"
    texts = all(isinstance(value.get(key), str) for key in ("status", "note"))
    if set(value) == set(ABSENT_KEYS) and texts:
        return "absent"
    if set(value) == set(READING_KEYS) and texts and isinstance(value["rule"], str):
        return "reading" if isinstance(value["words"], list) else "plain"
    return "plain"


def as_reading(value: Any) -> dict[str, Any] | None:
    """The value as a rule's reading (held_kind's shape), None where it is not one."""
    return value if held_kind(value) == "reading" and isinstance(value, dict) else None


def stated(value: Any) -> bool:
    """Whether the record holds a nonempty source value or a known direct derivation."""
    kind = held_kind(value)
    if kind == "plain":
        return contract.holds_value(value)
    return kind == "reading" and value["status"] == "known"


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
    an integer a cell holds exactly — the integer; an object, or an object in a list, its keys and values in
    words (result_words), never its JSON; anything else — item_words.
    """
    kind = held_kind(value)
    if kind == "missing":
        return NOT_STATED
    if kind == "absent":
        return absence_words(value["status"], value["note"])
    if kind == "reading":
        return reading_words(value, result_words(value["result"]))
    if isinstance(value, dict):
        return result_words(value)
    if isinstance(value, list):
        return (
            joiner.join(
                str(value_words(item)) if isinstance(item, (dict, list)) else item_words(item, dictionary)
                for item in value
            )
            or NOT_STATED
        )
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
        return (
            "; ".join(f"{str(key).replace('_', ' ')}: {result_words(item)}" for key, item in result.items())
            or "nothing"
        )
    if result is None or result == "":
        return "nothing"
    return str(result).replace("_", " ")


def reading_words(value: dict[str, Any], words: str) -> str:
    """A rule's reading, labelled, its result already in words.

    known — "Reading: <words>"; an absent or unresolved direct derivation retains its source state.
    """
    status = value["status"]
    if status == "known":
        return f"Reading: {words}"
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
        if main == name and (held_kind(held) == "plain" or beside == "studies[].enrollment.type"):
            extra = value_words(held, contract.FIELD_NAMES[beside].display)
            if words == extra and held_kind(value) != "plain" and held_kind(held) != "plain":
                continue
            words = f"{words:,} ({extra})" if isinstance(words, int) else f"{words} ({extra})"
    if "\n\n" in str(words):
        words = f"{words}\n[End of field]"
    return words, basis(value)


def applies(name: str, study: dict[str, Any]) -> bool:
    """Whether a study field can apply to the trial, by the registry's own fields: who is masked only under
    masking; the last known status only when the status is unknown; why stopped only for a stopped trial."""
    value = at(study, name.removeprefix("studies[]."))
    if name == "studies[].who_masked" and stated(value):
        return True
    if held_kind(value) == "absent" and value.get("note") == "not_applicable":
        return False
    status = study.get("overall_status")
    if name == "studies[].who_masked":
        return study.get("masking") != "NONE"
    if name == "studies[].last_known_status":
        return status == "UNKNOWN"
    if name == "studies[].why_stopped":
        return status in STOPPED
    return True


# ── universes and the domain readings they permit ───────────────────────────────────────────────────────


# ── a criterion's readings ──────────────────────────────────────────────────────────────────────────────


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


def drug_class_words(value: Any) -> tuple[str, str]:
    """Readable canonical identities and class assertions; unresolved attribution stays explicit."""
    reading = as_reading(value)
    result = reading["result"] if reading is not None else None
    if not isinstance(result, dict):
        return f"{UNRESOLVED}RxNav identity/class evidence is not available", STATUS_LABELS["unresolved"]
    state = result.get("state", "unresolved")
    if (
        reading is not None
        and reading["status"] != "known"
        and (state == "classified" or reading["status"] != "unresolved")
    ):
        return absence_words(reading["status"], reading["note"]), basis(reading)
    classes = result.get("classes", [])
    if (
        not isinstance(classes, list)
        or (state == "classified" and not classes)
        or any(
            not isinstance(row, (list, tuple))
            or len(row) != 4
            or not all(isinstance(part, str) for part in row)
            for row in classes
        )
    ):
        return f"{UNRESOLVED}RxNav class result has an unsupported shape", STATUS_LABELS["unresolved"]
    settled = reading is not None and reading["status"] == "known" and state == "classified"
    lines = [
        {
            "classified": "Classes attributed to the exact RxNorm concept",
            "conflict": "Unresolved — recorded names resolve to conflicting concepts",
            "lookup_failed": "Unresolved — a required lookup failed",
            "not_looked_up": "Unresolved — drug identities and classes were not looked up",
        }.get(state, "Unresolved — no class assertion is established for the recorded intervention")
    ]
    roles = {
        "own": "Recorded name",
        "confirms": "Same RxNorm concept",
        "related_form": "Related form, distinct concept",
        "alias_is_combination": "Different combination concept",
        "alias_is_one_ingredient": "Component only, not the combination",
        "alias_other_concept": "Different concept",
        "alias_not_resolved": "Alias identity unresolved",
    }
    for identity in result.get("identities", []):
        name = identity["name"]
        role = roles.get(identity.get("role"), "Identity")
        canonical = identity.get("canonical_name")
        if canonical and identity.get("code") in ("lookup_candidate", "not_recorded"):
            lines.append(
                f"Lookup candidate for {name}: {canonical} (RxNorm {identity['rxcui']}); "
                "recorded-name identity is not established"
            )
        elif canonical:
            kind = str(identity.get("code", "")).replace("_", " ")
            lines.append(f"{role}: {name} → {canonical} ({kind}; RxNorm {identity['rxcui']})")
        else:
            code = str(identity.get("code", "unresolved")).replace("_", " ")
            lines.append(f"{role}: {name} — {code}")
    for row in classes:
        words = contract.RXNAV_CLASS_DISPLAY_FORM.format(
            id=row[0], name=row[1], relation=row[2], source=row[3]
        )
        lines.append(words if settled else f"Source class candidate: {words} — attribution unresolved")
    shown = set()
    standings = {
        "not_inherited": "asserted of a related ingredient, not inherited by this intervention",
        "other_entity": "asserted of another entity",
        "identity_unresolved": "intervention identity unresolved",
        "identity_lookup_failed": "intervention identity lookup failed",
        "identity_conflict": "recorded identities conflict",
    }
    for assertion in result.get("assertions", []):
        key = tuple(
            assertion.get(part) for part in ("class_id", "relation", "source", "subject_rxcui", "standing")
        )
        if assertion.get("standing") == "known" or key in shown:
            continue
        shown.add(key)
        words = standings.get(assertion.get("standing"), "attribution unresolved")
        lines.append(
            f"Source assertion: {assertion['class_name']} for {assertion['subject_name']} "
            f"(RxNorm {assertion['subject_rxcui']}; {assertion['source']}, {assertion['relation']}) — {words}"
        )
    for query in result.get("queries", []):
        if query.get("code") in ("lookup_failed", "malformed"):
            words = str(query["code"]).replace("_", " ")
            lines.append(f"{query['queried_name']} / {query['source']}: {words}")
    label_ = READING if settled else STATUS_LABELS["unresolved"]
    if reading is not None and reading["status"] != "known":
        label_ = basis(reading)
    return "\n".join(lines), label_


def registry_check_summary(value: Any) -> tuple[str, str]:
    """Keep the four check outcomes distinct; uncheckable is never consistent."""
    reading = as_reading(value)
    result = reading["result"] if reading is not None else None
    rows = result.get("checks") if isinstance(result, dict) else None
    if not isinstance(rows, list):
        return f"{UNRESOLVED}Registry checks are not available", STATUS_LABELS["unresolved"]
    outcomes = ("conflict", "not_checkable", "consistent", "not_applicable")
    words = [f"{len(rows)} approved structured checks"]
    words += [
        f"{sum(row['outcome'] == outcome for row in rows)} {outcome.replace('_', ' ')}"
        for outcome in outcomes
    ]
    return "; ".join(words), READING


def element_rows(study: dict[str, Any], key: str, fields: list[contract.Field]) -> list[tuple[str, Any, str]]:
    """A registry list as dossier rows: one per element, each field "<label>: <words>" per line (a field the
    element does not state left out); a nested list one line per item; no element — one "Not stated" row when
    the list is expected, else none."""
    elements = study.get(key)
    plural = ELEMENT_WORDS[key]
    if not isinstance(elements, list) or not elements:
        if key not in EXPECTED:
            return []
        stated_as = basis(elements) if held_kind(elements) != "plain" else STATUS_LABELS["not_stated"]
        return [(f"{plural}s", value_words(elements), stated_as)]
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
            if (
                not stated(value)
                and not (field.kind == "reading" and held_kind(value) == "reading")
                and not field.name.endswith("drug_class")
            ):
                continue
            words = value_words(value, field.display)
            if field.name.endswith("drug_class"):
                words, source_basis = drug_class_words(value)
            if field.name in DATES and held_kind(value) == "plain":
                words = date_text(value)
            lines.append(f"{field.label}: {words}" + ("\n[End of field]" if "\n\n" in str(words) else ""))
            reading = field.kind == "reading" and held_kind(value) == "plain"
            labels.append(
                source_basis if field.name.endswith("drug_class") else READING if reading else basis(value)
            )
        fact = f"{plural} {number}"
        if key == "registered_outcomes":
            category = str(element.get("category", "registered")).capitalize()
            counts[category] = counts.get(category, 0) + 1
            fact = f"{category} outcome {counts[category]}"
            lines = [line for line in lines if not line.startswith("Category")]
        rows.append((fact, "\n".join(lines) or NOT_STATED, least_settled(labels)))
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


# ledger.results_state's codes as the record writes a known results reading's result.
POSTED_WORDS = ("posted", "results posted")


def results_posted(study: dict[str, Any]) -> bool:
    """Whether the record's results reading says the trial posted results."""
    reading = as_reading(study.get("results_posted"))
    return reading is not None and reading["status"] == "known" and reading["result"] in POSTED_WORDS


def results_words(study: dict[str, Any]) -> tuple[str, str]:
    """Whether results are posted, in words: "Yes, first posted <date>", "Not posted", or the reading's
    status in words."""
    value = study.get("results_posted")
    if results_posted(study):
        first = study.get("results_first_posted")
        when = f", first posted {date_text(first)}" if held_kind(first) == "plain" else ""
        return f"Yes{when}", READING
    reading = as_reading(value)
    if reading is not None and reading["status"] in ("not_posted", "known"):
        return NOT_POSTED, STATUS_LABELS["not_posted"]
    return value_words(value), basis(value)


def collection_state(study: dict[str, Any], pointers: tuple[str, ...]) -> str:
    """Reporting state of counted source arrays; an extracted [] does not establish source presence."""
    reading = as_reading(study.get("collection_presence"))
    if reading is None or reading["status"] != "known" or not isinstance(reading["result"], dict):
        return "untracked"
    states = [reading["result"].get(pointer) for pointer in pointers]
    if "malformed" in states:
        return "malformed"
    if "not_stated" in states:
        return "not_stated"
    if any(state not in ("stated", "stated_empty") for state in states):
        return "untracked"
    return "stated"


def collection_summary(study: dict[str, Any], pointers: tuple[str, ...], words: str) -> tuple[str, str]:
    """A collection count only when its source arrays are reported; otherwise its named reporting state."""
    state = collection_state(study, pointers)
    if state == "stated":
        return words, REGISTRY
    if state == "not_stated":
        return NOT_STATED, STATUS_LABELS["not_stated"]
    reason = (
        "source collection is malformed"
        if state == "malformed"
        else "source collection reporting was not tracked"
    )
    return f"{UNRESOLVED}{reason}", STATUS_LABELS["unresolved"]


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
        baseline_present = held_kind(held) == "plain" and isinstance(held, dict)
        characteristics = len(held.get("measures") or []) if baseline_present else 0
        outcome_pointer = "/resultsSection/outcomeMeasuresModule/outcomeMeasures"
        outcome_summary = collection_summary(
            study, (outcome_pointer,), f"{len(outcomes)} measures, {values} values (Posted results)"
        )
        value_pointers = [outcome_pointer]
        for number, outcome in enumerate(outcomes):
            classes_pointer = f"{outcome_pointer}/{number}/classes"
            value_pointers.append(classes_pointer)
            for class_number, klass in enumerate(outcome.get("classes") or []):
                categories_pointer = f"{classes_pointer}/{class_number}/categories"
                value_pointers.append(categories_pointer)
                for category_number, _category in enumerate(klass.get("categories") or []):
                    value_pointers.append(f"{categories_pointer}/{category_number}/measurements")
        if (
            collection_state(study, (outcome_pointer,)) == "stated"
            and collection_state(study, tuple(value_pointers)) != "stated"
        ):
            words, label = collection_summary(study, tuple(value_pointers), "")
            outcome_summary = (f"{len(outcomes)} measures; value count: {words} (Posted results)", label)
        analysis_summary = collection_summary(
            study,
            (outcome_pointer, *(f"{outcome_pointer}/{number}/analyses" for number in range(len(outcomes)))),
            f"{analyses} analyses (Statistical analyses)",
        )
        baseline_summary = collection_summary(
            study,
            ("/resultsSection/baselineCharacteristicsModule/measures",),
            f"{characteristics} characteristics (Baseline)",
        )
        return [
            (
                "Posted outcome measures",
                *(
                    outcome_summary
                    if isinstance(study.get("posted_outcomes"), list)
                    else (value_words(study.get("posted_outcomes")), basis(study.get("posted_outcomes")))
                ),
            ),
            (
                "Statistical analyses",
                *(
                    analysis_summary
                    if isinstance(study.get("posted_outcomes"), list)
                    else (value_words(study.get("posted_outcomes")), basis(study.get("posted_outcomes")))
                ),
            ),
            (
                "Baseline characteristics",
                *(baseline_summary if baseline_present else (value_words(held), basis(held))),
            ),
        ]
    if heading == "Participant flow":
        flow = study.get("participant_flow")
        if held_kind(flow) != "plain" or not isinstance(flow, dict):
            return [("Participant flow", value_words(flow), basis(flow))]
        periods = flow.get("periods") or []
        pointer = "/resultsSection/participantFlowModule/periods"
        if collection_state(study, (pointer,)) != "stated":
            return [("Participant flow", *collection_summary(study, (pointer,), ""))]
        names = "; ".join(str(value_words(period.get("title"))) for period in periods) or NOT_STATED
        return [("Periods", f"{len(periods)}: {names} (Participant flow)", REGISTRY)]
    events = study.get("adverse_events")
    if held_kind(events) != "plain" or not isinstance(events, dict):
        return [("Adverse events", value_words(events), basis(events))]
    rows = [
        (f"Group G{number}", f"{value_words(group.get('title'))}\n{group_totals(group)}", REGISTRY)
        for number, group in enumerate(events.get("groups") or [], 1)
    ]
    listed = events.get("events") or []
    pointers = (
        "/resultsSection/adverseEventsModule/seriousEvents",
        "/resultsSection/adverseEventsModule/otherEvents",
    )
    if collection_state(study, pointers) != "stated":
        return rows + [("Adverse events", *collection_summary(study, pointers, ""))]
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
            if field.name in BESIDE or field.name in NOT_IN_DOSSIER:
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
            if field.name == "studies[].registry_checks":
                rows.append((field.label, *registry_check_summary(study.get("registry_checks"))))
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
MAX_PLACES = 30  # the most decimal places a spreadsheet number format shows
COUNT_FORMAT = contract.NUMBER_FORMATS["count"]


def registry_number(text: Any) -> tuple[str, Any, str]:
    """A registry value written as a number where it is a plain decimal (pure — pinned).

    number — the text is a plain decimal ("63.4", "63.40", "7", "-0.5": digits, an optional sign and point,
             no leading zero, no grouping comma), a negative zero excepted, with at most 15 significant
             digits and at most MAX_PLACES decimal places, whose number written with the text's own decimal
             places gives back exactly the text: (number, the int or float, the format that shows exactly the
             registry's decimal places: "0" for none, "0.00" for two);
    text   — anything else ("NA", "<0.001", "1,500", "0.1-0.3", a number with more digits than a cell holds
             exactly, one a float underflows to zero or overflows, more decimal places than a format shows):
             (text, the value as given, "").
    """
    if not isinstance(text, str) or not PLAIN_DECIMAL.fullmatch(text):
        return "text", text, ""
    whole, _point, places = text.lstrip("-").partition(".")
    digits = (whole + places).lstrip("0")
    if len(digits) > 15 or len(places) > MAX_PLACES:
        return "text", text, ""
    value: Any = float(text) if places else int(text)
    shown = f"{value:.{len(places)}f}" if places else str(value)
    if shown != text or (text.startswith("-") and value == 0):
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
    """All denominators for the measurement's group, innermost first.

    A single participants count remains numeric. Additional scope counts are labelled and
    never substituted for, or silently dropped beside, the innermost denominator.
    """
    found, qualifiers = [], []
    for index, scope in enumerate(scopes):
        values = [
            (value_words(count.get("value")), value_words(denominator.get("units")))
            for denominator in (scope.get("denominators") or [] if isinstance(scope, dict) else [])
            for count in denominator.get("counts") or []
            if count.get("group") == group
        ]
        if values:
            found.append((index, values))
        if isinstance(scope, dict):
            for key, label_ in contract.DENOMINATOR_QUALIFIER_LABELS.items():
                if stated(scope.get(key)):
                    qualifiers.append(
                        contract.DENOMINATOR_QUALIFIER_FORM.format(
                            scope=contract.DENOMINATOR_SCOPE_LABELS[index],
                            label=label_,
                            value=value_words(scope[key]),
                        )
                    )
    if not found and not qualifiers:
        return NOT_STATED
    if not qualifiers and len(found) == 1 and len(found[0][1]) == 1 and found[0][1][0][1] == "Participants":
        return found[0][1][0][0]
    lines = []
    for index, values in found:
        words = "; ".join(
            f"{count} {units}" if units != NOT_STATED else f"{count} (units not stated)"
            for count, units in values
        )
        if len(found) > 1 or qualifiers:
            scope = contract.DENOMINATOR_SCOPE_LABELS[index]
            words = contract.DENOMINATOR_SCOPE_FORM.format(scope=scope, value=words)
        lines.append(words)
    return "; ".join([*(lines or [NOT_STATED]), *qualifiers])


def spread_words(kind: Any, measurement: dict[str, Any], dictionary: str = "") -> str:
    """A measurement's dispersion, retaining both a spread and limits when posted.

    Missing endpoints stay explicit; NA applies only when no dispersion value is present.
    """
    spread, lower, upper = (measurement.get(key) for key in ("spread", "lower_limit", "upper_limit"))
    named = value_words(kind, dictionary) if held_kind(kind) == "plain" else "Spread"
    parts = []
    if held_kind(spread) == "plain":
        parts.append(f"{named}: {value_words(spread)}")
    if held_kind(lower) == "plain" or held_kind(upper) == "plain":
        limit_label = f"{named} limits" if parts else named
        parts.append(f"{limit_label}: {value_words(lower)} to {value_words(upper)}")
    if parts:
        return "; ".join(parts)
    if kind == "NA":
        return NOT_APPLICABLE
    return f"{named}: {NOT_STATED}" if stated(kind) else NOT_STATED


def title_or_blank(value: Any) -> Any:
    """A class's or category's title; an untitled one blank (None): the registry's single unnamed class or
    category has no name to show."""
    return value_words(value) if stated(value) else None


def measurement_rows(
    trial: str, base: str, module: dict[str, Any], head: tuple, scopes: tuple, extra: dict
) -> list[tuple]:
    """Measurements with their class, category, group and all denominator scopes.

    An empty measure, class or category has one explicitly unmeasured row at that
    level's own address. Such a row never asserts a group or quantitative result.
    """
    rows = []
    groups = module.get("groups")
    measure = extra["measure"]
    classes = measure.get("classes") or []
    for k, klass in enumerate(classes or [{}]):
        class_base = f"{base}/classes/{k}" if classes else base
        categories = klass.get("categories") or []
        for c, category in enumerate(categories or [{}]):
            category_base = f"{class_base}/categories/{c}" if categories else class_base
            measurements = category.get("measurements") or []
            for m, measurement in enumerate(measurements):
                group = measurement.get("group")
                address = f"{category_base}/measurements/{m}"
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
                rows.append(numbered(values, address, (len(head) + 5, len(head) + 7)))
            if not measurements:
                denominator_scopes = [klass, *scopes]
                group_ids = dict.fromkeys(
                    count.get("group")
                    for scope in denominator_scopes
                    if isinstance(scope, dict)
                    for denominator in scope.get("denominators") or []
                    for count in denominator.get("counts") or []
                )
                denominators = "\n".join(
                    f"{group_title(groups, group)}: {denominator_words(denominator_scopes, group)}"
                    for group in group_ids
                ) or denominator_words(denominator_scopes, None)
                values = (
                    trial,
                    category_base,
                    *head,
                    title_or_blank(klass.get("title")),
                    title_or_blank(category.get("title")),
                    contract.MEASUREMENT_PLACEHOLDER_WORDS["group"],
                    denominators,
                    value_words(measure.get("param_type"), "MeasureParam"),
                    contract.MEASUREMENT_PLACEHOLDER_WORDS["value"],
                    spread_words(measure.get("dispersion_type"), {}, extra["dispersion"])
                    if stated(measure.get("dispersion_type"))
                    else NOT_APPLICABLE,
                    value_words(measure.get("unit")),
                    NOT_APPLICABLE,
                )
                rows.append(tuple(cell(value, "known", category_base) for value in values))
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
        population_words = contract.BASELINE_POPULATION_FORM.format(
            label=contract.BASELINE_POPULATION_LABELS[0], value=value_words(population)
        )
        if stated(baseline.get("population")):
            population_words += "\n" + contract.BASELINE_POPULATION_FORM.format(
                label=contract.BASELINE_POPULATION_LABELS[1], value=value_words(baseline.get("population"))
            )
        head = (title, population_words)
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
            if any(
                stated(analysis.get(key)) for key in contract.CONFIDENCE_COMPONENT_POLICY["show_when_any"]
            ):
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
                if stated(flow.get("units_analyzed")):
                    participants = (
                        f"{participants}; Units analyzed (other than participants): "
                        f"{value_words(flow.get('units_analyzed'))}"
                    )
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
    """One Safety row per event and source count or group in this trial's adverse-events module.

    Group IDs are resolved within that module; no group is matched across studies or results modules. A
    missing count stays "Not reported", while a listed zero stays zero. `n` is retained for callers that
    also build workbook sheets with run-wide layout parameters.
    """
    held = study.get("adverse_events")
    events = held if isinstance(held, dict) else {}
    groups = [group for group in events.get("groups") or [] if isinstance(group, dict)]
    rows = []
    for e, event in enumerate(events.get("events") or []):
        event_address = f"/studies/{number}/adverse_events/events/{e}"
        counts = event.get("counts") or []

        def append_row(
            group_id: Any,
            group: dict[str, Any] | None,
            count: Any,
            address: str,
            event: dict[str, Any] = event,
        ) -> None:
            if group is None:
                group_title = "Unresolved — no unique adverse-event source group is available"
                group_description = (
                    "Unresolved — no unique adverse-event source group description is available"
                )
            else:
                group_title = value_words(group.get("title"))
                group_description = value_words(group.get("description"))
            values = (
                study["nct"],
                address,
                contract.WHICH_LIST_WORDS.get(str(event.get("table")), value_words(event.get("table"))),
                value_words(event.get("term")),
                group_title,
                stat_cell(count if isinstance(count, dict) else None, "affected"),
                stat_cell(count if isinstance(count, dict) else None, "at_risk"),
                stat_cell(count if isinstance(count, dict) else None, "events"),
                value_words(events.get("time_frame")),
                value_words(event.get("organ_system")),
                group_description,
                value_words(group_id),
                value_words(events.get("frequency_threshold")),
                value_words(event.get("vocabulary")),
                value_words(event.get("assessment"), "EventAssessment"),
                value_words(event.get("notes")),
            )
            rows.append(tuple(cell(value, "known", address) for value in values))

        for c, count in enumerate(counts):
            count_group = count.get("group") if isinstance(count, dict) else None
            matches = [group for group in groups if group.get("id") == count_group]
            group = matches[0] if len(matches) == 1 else None
            count_address = f"{event_address}/counts/{c}"
            append_row(count_group, group, count, count_address)

        for group_index, group in enumerate(groups):
            group_id = group.get("id")
            has_count = any(
                (count.get("group") if isinstance(count, dict) else None) == group_id for count in counts
            )
            if has_count:
                continue
            duplicate = sum(1 for other in groups if other.get("id") == group_id) > 1
            if duplicate and any(prior.get("id") == group_id for prior in groups[:group_index]):
                continue
            append_row(
                group_id,
                None if duplicate else group,
                None,
                event_address,
            )

        if not groups and not counts:
            append_row(
                None,
                None,
                None,
                event_address,
            )
    return rows


def posted_groups(study: dict[str, Any], number: int) -> list[tuple[tuple[Any, Any], str, list[str]]]:
    """A trial's posted-outcome groups once per distinct (title, description): each with the address of its
    first occurrence and every measure it appears in ("<measure title> (<address>)"), in the record's
    order."""
    found: dict[tuple[Any, Any], tuple[str, list[str]]] = {}
    held = study.get("posted_outcomes")
    for o, outcome in enumerate(held if isinstance(held, list) else []):
        for g, group in enumerate(outcome.get("groups") or []):
            key = (json_key(group.get("title")), json_key(group.get("description")))
            address = f"/studies/{number}/posted_outcomes/{o}/groups/{g}"
            measure = f"{value_words(outcome.get('title'))} ({address})"
            if key not in found:
                found[key] = (address, [])
            if measure not in found[key][1]:
                found[key][1].append(measure)
    return [(key, address, measures) for key, (address, measures) in found.items()]


def json_key(value: Any) -> Any:
    """A value as a hashable key: text as it is, anything else its words."""
    return value if isinstance(value, str) else str(value_words(value))


def group_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """A trial's Groups rows: each posted-outcome group once per distinct title and description
    (posted_groups), with the measures it appears in; then the groups of its baseline, participant flow and
    adverse events, each keyed within its module (never matched across modules); the adverse-event groups
    named G1 ... with their totals."""
    rows = []
    held = study.get("posted_outcomes")
    outcomes = held if isinstance(held, list) else []
    for (title, description), address, measures in posted_groups(study, number):
        ids = [
            str(group.get("id"))
            for outcome in outcomes
            for group in outcome.get("groups") or []
            if (json_key(group.get("title")), json_key(group.get("description"))) == (title, description)
        ]
        values = (
            study["nct"],
            address,
            "Posted results",
            ", ".join(dict.fromkeys(ids)),
            None,
            title,
            description,
            "\n".join(measures),
            None,
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
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
                None,
                group_totals(group) if events else None,
            )
            rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


def criterion_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """Verbatim source passages for readable display; the complete text also appears in the dossier."""
    held = study.get("criteria")
    rows = []
    for index, criterion in enumerate(held if isinstance(held, list) else []):
        address = f"/studies/{number}/criteria/{index}"
        values = (
            study["nct"],
            address,
            HEADINGS.get(str(criterion.get("heading")), value_words(criterion.get("heading"))),
            value_words(criterion.get("number")),
            value_words(criterion.get("text")),
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    if not rows:
        address = f"/studies/{number}"
        rows.append(
            tuple(
                cell(value, "known", address)
                for value in (study["nct"], address, NOT_STATED, NOT_STATED, NOT_STATED)
            )
        )
    return rows


def check_detail_words(detail: str) -> str:
    """Render literal containers inside a check diagnostic as prose; retain all scalar values.

    This is presentation of Python literal syntax emitted by the existing checks, never clinical parsing.
    Exact diagnostic text and structured source inputs remain in the record.
    """

    def words(value: Any) -> str:
        if isinstance(value, dict):
            return (
                "; ".join(f"{key}: {words(item)}" for key, item in value.items()) or "explicitly empty object"
            )
        if isinstance(value, set):
            value = sorted(value, key=repr)
        if isinstance(value, (list, tuple, set)):
            return "; ".join(words(item) for item in value) or "explicitly empty list"
        return "null" if value is None else str(value)

    starts, edits = [], []
    offsets = [0]
    for line in detail.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    try:
        for token in tokenize.generate_tokens(io.StringIO(detail).readline):
            if token.type != tokenize.OP:
                continue
            if token.string in ("[", "{", "("):
                starts.append(offsets[token.start[0] - 1] + token.start[1])
            elif token.string in ("]", "}", ")") and starts:
                start = starts.pop()
                if starts:
                    continue
                end = offsets[token.end[0] - 1] + token.end[1]
                try:
                    value = ast.literal_eval(detail[start:end])
                except (ValueError, SyntaxError):
                    continue
                if isinstance(value, (dict, list, tuple, set)):
                    edits.append((start, end, words(value)))
    except (tokenize.TokenError, IndentationError):
        return detail
    for start, end, text in reversed(edits):
        detail = detail[:start] + text + detail[end:]
    return detail


def registry_check_rows(study: dict[str, Any], i: int) -> list[tuple]:
    """One approved registry check per row, with its source-input addresses and cited rule."""
    reading = as_reading(study.get("registry_checks"))
    result = reading["result"] if reading is not None else None
    checks_ = result.get("checks") if isinstance(result, dict) else None
    if not isinstance(checks_, list):
        return []
    return [
        (
            label(study["nct"]),
            label(f"/studies/{i}/registry_checks/result/checks/{j}"),
            label(check["label"]),
            label(check["outcome"].replace("_", " ").capitalize()),
            cell(check_detail_words(check["detail"]), "known"),
            label("\n".join(check["source"])),
            label(f"{check['basis']}\n{check['rule']}"),
        )
        for j, check in enumerate(checks_)
    ]


def registered_rows(study: dict[str, Any], number: int) -> list[tuple]:
    """Source outcomes the study planned to measure, without clinical endpoint classification."""
    rows = []
    held = study.get("registered_outcomes")
    for index, outcome in enumerate(held if isinstance(held, list) else []):
        address = f"/studies/{number}/registered_outcomes/{index}"
        values = (
            study["nct"],
            address,
            contract.WHICH_LIST_WORDS.get(str(outcome.get("category")), value_words(outcome.get("category"))),
            value_words(outcome.get("measure")),
            value_words(outcome.get("description")),
            value_words(outcome.get("time_frame")),
        )
        rows.append(tuple(cell(value, "known", address) for value in values))
    return rows


# The Readings sheet's plain names of the fields a rule reads; the record's long definitions stay in the
# Column dictionary. A field not listed shows its contract label.


SOURCE_KIND = {"plain": "{path}", "reading": "rule {path}", "run": "recorded by the run ({path})"}


def dictionary_rows(n: int, record: dict[str, Any] | None = None) -> list[tuple]:
    """The Column dictionary: each sheet's columns, once, with the registry fields or rules they show and
    what they hold."""
    rows = []
    for sheet in contract.SHEETS:
        # the Read me's topics are not columns of record fields
        if sheet.name not in BUILT or sheet.name == contract.READ_ME:
            continue
        for column in sheet.columns:
            if (
                sheet.name == contract.INDEX
                and record is not None
                and column.header not in sheet_headers(sheet.name, n, record)
            ):
                continue
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


HOW_TO_READ = (
    "Start with the Trial index, then follow each Dossier link to the complete Trial review. "
    "The dossier includes the full eligibility criteria and narrative descriptions verbatim; "
    "long values continue across numbered parts in order. Eligibility lists structural source pieces "
    "without clinical interpretation; headings describe only the source section. Registered outcomes "
    "are planned measurements, never results. Posted results, Statistical analyses, Baseline, Participant "
    "flow, Groups and Safety retain the posted measurements, denominators, groups and source comments. "
    "Safety has one row for each event and its declared source group; the group title links to that "
    "trial's definition. Every listing row has an address in landscape.json. Address columns are hidden "
    "by default; unhide a column to inspect its exact record pointer. The Column dictionary names "
    "its registry "
    "fields or direct derivation. A direct derivation records its named rule and source in the JSON. "
    "Source collection reporting distinguishes absent, malformed and explicitly empty arrays; an empty "
    "list is not evidence of no harm or efficacy. This registry report contains no inferred eligibility "
    "requirements, biomarker roles, treatment settings, clinical selections or across-trial recommendations. "
    "Not stated is never none; Not posted is never no effect. For a long listing cell, expand the formula "
    "bar or retrieve the complete value by its record address."
)


def version_words(value: Any) -> str:
    """A rule version as written: a table of versions as "name version" pairs joined by "; "."""
    if isinstance(value, dict):
        return "; ".join(f"{str(key).replace('_', ' ')} {version_words(item)}" for key, item in value.items())
    return str(value)


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
    lines += [
        f"Rule version, {name.replace('_', ' ')}: {version_words(value)}" for name, value in versions.items()
    ]
    scope = record.get("scope")
    query = scope.get("query") if isinstance(scope, dict) else None
    if isinstance(query, dict):
        lines += [f"Registry search sent, {name}: {value}" for name, value in query.items()]
    return "\n".join(lines)


def guide_rows(record: dict[str, Any]) -> list[tuple]:
    """Source-reporting guide, direct derivation policy and provenance."""
    held = record.get("statuses")
    statuses = held if isinstance(held, dict) else {}
    content = {
        "The search, in plain words": search_plain_words(record.get("request")),
        "What it found": found_words(record),
        "How to read this workbook": HOW_TO_READ,
        "What each status means": "\n".join(
            f"{STATUS_LABELS.get(name, name)}: {meaning}" for name, meaning in statuses.items()
        )
        or NOT_STATED,
        "What the registry does not report": "The structured tables and field labels alone "
        "do not establish:\n"
        + "\n".join(f"- {item}" for item in contract.NOT_REPORTED_BY_REGISTRY)
        + "\nLiteral descriptions, eligibility criteria and attached protocols may state these details. "
        "The source narrative remains visible verbatim; "
        "a missing extraction is no evidence of source absence. "
        "A posted safety table lists only the terms over its frequency threshold, and posted results only "
        "the measures the sponsor posted: neither is a complete account of harm or efficacy.",
        "Technical provenance": provenance_words(record),
    }
    return [(label(topic), cell(content[topic], LABEL)) for topic, _fields in contract.READ_ME_TOPICS]


def design_words(study: dict[str, Any]) -> str:
    """The index's design in short words: purpose, allocation, model, masking (who is masked)."""
    design_fields = contract.INDEX_SILENT_DESIGN_FIELDS
    if not any(stated(study.get(name)) for name in design_fields):
        kind = value_words(study.get("study_type"), "StudyType")
        if study.get("study_type") not in ("OBSERVATIONAL", "EXPANDED_ACCESS") or any(
            applies(f"studies[].{name}", study) for name in design_fields if name != "who_masked"
        ):
            return contract.INDEX_SILENT_DESIGN_FORM.format(study_type=kind)
    parts = [
        value_words(study.get(name), contract.FIELD_NAMES[f"studies[].{name}"].display)
        for name in ("primary_purpose", "allocation", "intervention_model")
        if applies(f"studies[].{name}", study)
    ]
    masking = value_words(study.get("masking"), "DesignMasking")
    who_masked_present = stated(study.get("who_masked"))
    masking_present = stated(study.get("masking"))
    if who_masked_present and masking_present and study.get("masking") != "NONE":
        masking += f" ({value_words(study['who_masked'], 'WhoMasked', ', ')})"
    if applies("studies[].masking", study):
        parts.append(f"masking {masking}")
    if who_masked_present and (not masking_present or study.get("masking") == "NONE"):
        parts.append(
            f"{contract.FIELD_NAMES['studies[].who_masked'].label}: "
            f"{value_words(study['who_masked'], 'WhoMasked', ', ')}"
        )
    if not parts:
        kind = value_words(study.get("study_type"), "StudyType")
        if study.get("study_type") not in ("OBSERVATIONAL", "EXPANDED_ACCESS"):
            return contract.INDEX_SILENT_DESIGN_FORM.format(study_type=kind)
        return f"{kind} — interventional design fields not applicable"
    return "; ".join(str(part) for part in parts)


def index_cells(study: dict[str, Any], dossier: str, publications: str) -> tuple:
    """One trial's compact index row, with full displayed text allowed to wrap: `dossier` and
    `publications` link to its dossier and its dossier's publications band."""
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
    enrollment = value_words(at(study, "enrollment.count"))
    enrollment_type = value_words(at(study, "enrollment.type"), "EnrollmentType")
    start, _ = shown_field(study, "studies[].start_date.date")
    update = study.get("last_update_posted")
    design = design_words(study)
    return (
        cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),
        cell(value_words(short), "known"),
        cell(sponsor, "known"),
        cell(value_words(study.get("phases"), "Phase", " / "), "known"),
        cell(status, "known"),
        cell(value_words(study.get("conditions")), "known"),
        cell(design, "known"),
        cell(enrollment, "known"),
        cell(enrollment_type, "known"),
        cell(start, "known"),
        cell(endpoint, "known"),
        cell(results, "known"),
        cell(cited, "known", "", "", "", publications if references else ""),
        cell(value_words(study.get("countries")), "known"),
        cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, "known"),
        cell("Dossier", LABEL, "", "", "", dossier),
    )


# ── the plan, the writer and the read-back ──────────────────────────────────────────────────────────────


def sheet_headers(name: str, n: int, record: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Declared headers; each safety source group is represented by a row rather than repeated columns."""
    sheet = next(held for held in contract.SHEETS if held.name == name)
    headers = []
    per_group = [column.header for column in sheet.columns if column.shows == "per group"]
    for column in sheet.columns:
        if column.shows != "per group":
            headers.append(column.header)
        elif column.header == per_group[0]:
            headers.extend(header.format(n=group) for group in range(1, n + 1) for header in per_group)
    return tuple(headers)


# Each sheet's layout: frozen panes, the width of each column (characters; the rest DEFAULT_WIDTH), whether
# its text wraps (the index's does not, so no row is sized by its prose), and the most lines a row shows
# before the reader widens it (its full text is in the cell).
DEFAULT_WIDTH = 16
LINE_POINTS = 12.75
LISTING = {"Trial ID": 13, contract.ADDRESS: 22}
LAYOUT: dict[str, tuple[str, dict[str, int], bool, int]] = {
    "Read me": ("B2", {"Topic": 30, "Content": 110}, True, 40),
    "Trial index": (
        "B2",
        {
            "Trial ID": 13,
            "Acronym or short title": 30,
            "Sponsor": 26,
            "Phase": 15,
            "Status": 18,
            "Conditions": 28,
            "Design": 44,
            "Enrollment": 16,
            "Enrollment type": 16,
            "Start": 20,
            "Primary endpoint": 40,
            "Results posted": 14,
            "Publications": 20,
            "Countries": 24,
            "Last update posted": 14,
            "Dossier": 9,
        },
        True,
        1,
    ),
    "Trial review": ("D2", {"Trial ID": 13, "Section": 22, "Fact": 30, "Value": 100, "Basis": 12}, True, 20),
    "Eligibility": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Source section": 16,
            "Passage": 12,
            "Source passage": 100,
        },
        True,
        8,
    ),
    "Registered outcomes": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Category": 11,
            "Measure": 40,
            "Description": 50,
            "Time frame": 30,
        },
        True,
        6,
    ),
    "Posted results": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Measure": 36,
            "Measure description": 36,
            "Analysis population": 36,
            "Time frame": 26,
            "Group": 28,
            "Denominator (participants unless otherwise specified)": 18,
            "Comment": 30,
        },
        True,
        6,
    ),
    "Statistical analyses": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Measure": 36,
            "Compared groups": 30,
            "Method": 26,
            "Estimate": 20,
            "Confidence interval": 24,
        },
        True,
        6,
    ),
    "Baseline": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Characteristic": 30,
            "Population": 30,
            "Group": 28,
            "Denominator (participants unless otherwise specified)": 18,
            "Comment": 24,
        },
        True,
        6,
    ),
    "Participant flow": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Period": 22,
            "Milestone or reason": 30,
            "Group": 30,
            "Comment": 30,
        },
        True,
        4,
    ),
    "Groups": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 22,
            "Module": 24,
            "Column": 8,
            "Title": 30,
            "Description": 50,
            "Outcome measures": 60,
            "Totals": 34,
        },
        True,
        6,
    ),
    "Safety": (
        "F2",
        {
            "Trial ID": 13,
            "Address in the record": 28,
            "Table": 12,
            "Organ system": 32,
            "Term": 30,
            "Group ID": 14,
            "Group": 38,
            "Group description": 60,
            "Affected": 12,
            "At risk": 12,
            "Events": 12,
            "Reporting period": 36,
            "Frequency threshold": 20,
            "Vocabulary": 18,
            "Assessment": 24,
            "Notes": 36,
        },
        True,
        4,
    ),
    "Registry checks": (
        "C2",
        {
            "Trial ID": 13,
            "Address in the record": 24,
            "Check": 55,
            "Outcome": 18,
            "Detail": 70,
            "Source fields": 60,
            "Rule basis": 90,
        },
        True,
        8,
    ),
    "Column dictionary": (
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


def dossier_value_parts(value: Any) -> list[Any]:
    """Exact contiguous display slices of a dossier value, each within its readable row budget.

    Text a cell cannot preserve follows written_safely's existing refusal, never a bypass by splitting.
    Prefer a whitespace boundary near the fitting end; keep that whitespace in the preceding slice.
    """
    if not isinstance(value, str) or cell_text_state(value) != "ok":
        return [value]
    width = LAYOUT[contract.REVIEW][1]["Value"]
    parts = []
    start = 0
    while start < len(value):
        low, high = 1, min(len(value) - start, width * contract.DOSSIER_LINES_PER_ROW)
        while low < high:
            end = (low + high + 1) // 2
            if row_lines(((value[start : start + end],),), [width]) <= contract.DOSSIER_LINES_PER_ROW:
                low = end
            else:
                high = end - 1
        end = start + low
        if end < len(value):
            boundary = next(
                (i + 1 for i in range(end - 1, start + low // 2 - 1, -1) if value[i].isspace()),
                end,
            )
            end = boundary
        parts.append(value[start:end])
        start = end
    return parts or [value]


EMPTY_WORDS = contract.EMPTY_LISTING_WORDS


def group_target(record: dict[str, Any], sheet: str, address: str) -> str:
    """The address of the Groups row a listing row's Group cell links to (contract.GROUP_LINKS): from the
    row's address, its group ID within its own module; for a posted measure, the first occurrence of the
    group's title and description in its trial (posted_groups); "" where the row names no group."""
    parts = str(address).strip("/").split("/")
    if len(parts) < 3 or parts[0] != "studies" or not parts[1].isdigit():
        return ""
    number = int(parts[1])
    study = record["studies"][number]
    found, node, _template, _indices = resolve_address(record, parts)
    group_id = node.get("group") if found and isinstance(node, dict) else None
    if sheet == contract.POSTED and len(parts) == 10:
        outcome = study["posted_outcomes"][int(parts[3])]
        group = next((g for g in outcome.get("groups") or [] if g.get("id") == group_id), None)
        if group is None:
            return ""
        key = (json_key(group.get("title")), json_key(group.get("description")))
        return next((at for held, at, _m in posted_groups(study, number) if held == key), "")
    module = parts[2]
    groups = study.get(module, {}).get("groups") if isinstance(study.get(module), dict) else None
    for g, group in enumerate(groups or []):
        if group.get("id") == group_id:
            return f"/studies/{number}/{module}/groups/{g}"
    return ""


def resolve_address(record: Any, parts: list[str]) -> tuple[bool, Any, str, list[int]]:
    """The node a JSON pointer's parts name in the record: (found, node, its template, its list indices)."""
    node, template, indices = record, [], []
    for part in parts:
        if isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
            template[-1] += "[]"
            indices.append(int(part))
        elif isinstance(node, dict) and part in node:
            node = node[part]
            template.append(part)
        else:
            return False, None, "", []
    return True, node, ".".join(template), indices


def linked_groups(record: dict[str, Any], sheet: str, rows: list[tuple], groups: list[tuple]) -> list[tuple]:
    """A listing's rows whose Group cell (the group's title) links to its group's row in the Groups sheet
    (group_target); the group's ID stays bound in the row's address."""
    if sheet == contract.SAFETY:
        definitions = {}
        for index, row in enumerate(groups):
            if row[2][0] == "Adverse events":
                part, number = place(index, CAPACITY, contract.GROUPS)
                definitions.setdefault((row[0][0], row[3][0]), []).append(f"#'{part}'!A{number}")
        group_id = sheet_headers(sheet, 0).index("Group ID")
        group_title = sheet_headers(sheet, 0).index("Group")
        linked = []
        for row in rows:
            fixed = list(row)
            targets = definitions.get((row[0][0], row[group_id][0]), [])
            if len(targets) == 1:
                held = fixed[group_title]
                fixed[group_title] = (held[0], targets[0], *held[2:])
            linked.append(tuple(fixed))
        return linked
    at_group = sheet_headers(sheet, 0).index("Group")
    where = {}
    for index, row in enumerate(groups):
        part, number = place(index, CAPACITY, contract.GROUPS)
        where[row[1][0]] = f"#'{part}'!A{number}"
    linked = []
    for row in rows:
        link = where.get(group_target(record, sheet, row[1][0]), "")
        held = row[at_group]
        linked.append((*row[:at_group], (held[0], link, *held[2:]), *row[at_group + 1 :]))
    return linked


def dossier_links(study: dict[str, Any]) -> dict[str, str]:
    """Copied document/link URLs and the existing direct PubMed link rule, keyed by their dossier fact."""
    targets = {}
    for key, field in contract.DOSSIER_SOURCE_LINK_FIELDS.items():
        held = study.get(key)
        for number, item in enumerate(held if isinstance(held, list) else [], 1):
            if not isinstance(item, dict):
                continue
            url = item.get(field)
            if not isinstance(url, str):
                continue
            try:
                parsed = urlsplit(url)
            except ValueError:
                continue
            if parsed.scheme in ("http", "https") and parsed.netloc:
                targets[f"{ELEMENT_WORDS[key]} {number}"] = url
    held = study.get("references")
    for number, item in enumerate(held if isinstance(held, list) else [], 1):
        if not isinstance(item, dict):
            continue
        code, url = pubmed_link(item.get("pmid"))
        if code == "ok":
            targets[f"{ELEMENT_WORDS['references']} {number}"] = url
    return targets


def book_plan(record: dict[str, Any]) -> list[tuple]:
    """Every sheet, in contract.SHEETS' order, as (name, headers, rows, page starts): the dossier first, so
    the index links to each trial's dossier and its publications band, and each band with a listing to the
    trial's first row there; each trial's dossier starts a printed page."""
    studies = record["studies"]
    n = safety_groups(record)
    listings = {
        contract.ELIGIBILITY: criterion_rows,
        contract.REGISTERED: registered_rows,
        contract.POSTED: posted_rows,
        contract.ANALYSES: analysis_rows,
        contract.BASELINE: baseline_rows,
        contract.FLOW: flow_rows,
        contract.GROUPS: group_rows,
        "Registry checks": registry_check_rows,
    }
    rows: dict[str, list[tuple]] = {name: [] for name in BUILT}
    first: dict[tuple[str, int], int] = {}
    for i, study in enumerate(studies):
        for name, rows_of in listings.items():
            first[(name, i)] = len(rows[name])
            rows[name] += rows_of(study, i)
        first[(contract.SAFETY, i)] = len(rows[contract.SAFETY])
        rows[contract.SAFETY] += safety_rows(study, i, n)
    review: list[tuple] = []
    starts, links_ = [], []
    for i, study in enumerate(studies):
        starts.append(len(review))
        publications = None
        source_links = dossier_links(study)
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
            parts = dossier_value_parts(value)
            for part_number, part_value in enumerate(parts, 1):
                part_fact = (
                    contract.DOSSIER_PART_FORM.format(fact=fact, part=part_number, count=len(parts))
                    if len(parts) > 1
                    else fact
                )
                review.append(
                    (
                        label(study["nct"]),
                        label(heading),
                        label(part_fact),
                        cell(part_value, "known", link=source_links.get(fact, "")),
                        label(label_),
                    )
                )
        sheet, row_number = place(starts[-1], CAPACITY, contract.REVIEW)
        sheet_p, row_p = place(publications or starts[-1], CAPACITY, contract.REVIEW)
        links_.append((f"#'{sheet}'!A{row_number}", f"#'{sheet_p}'!A{row_p}"))
    for linked_sheet in contract.GROUP_LINKS:
        rows[linked_sheet] = linked_groups(record, linked_sheet, rows[linked_sheet], rows[contract.GROUPS])
    for name, words in EMPTY_WORDS.items():
        if not rows[name]:
            # the contract's one line: its words in the first column, no address, the rest blank
            width = len(sheet_headers(name, n))
            rows[name] = [(cell(words, LABEL), *(cell(None, LABEL),) * (width - 1))]
    rows[contract.READ_ME] = guide_rows(record)
    rows[contract.INDEX] = [index_cells(study, *held) for study, held in zip(studies, links_, strict=True)]
    rows[contract.REVIEW] = review
    rows[contract.DICTIONARY] = dictionary_rows(n, record)
    plan = []
    for name in BUILT:
        full_headers = sheet_headers(name, n)
        headers = sheet_headers(name, n, record)
        indices = tuple(full_headers.index(header) for header in headers)
        projected = [tuple(row[index] for index in indices) for row in rows[name]]
        plan.append((name, headers, written_safely(projected), starts[1:] if name == contract.REVIEW else []))
    return plan


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
        written.hyperlink = Hyperlink(
            ref="",
            location=link[1:],
            display=str(value),
            tooltip="Groups: open this group definition" if link.startswith(f"#'{contract.GROUPS}") else None,
        )
    elif link:
        written.hyperlink = link
    if link:
        written.font = LINK_FONT
    return written


def _write_book(plan: list[tuple], footer: tuple[str, str, str]) -> tuple[bytes, int]:
    """The book's bytes, every write time fixed, and the number of cells written."""
    book = Workbook(write_only=True)
    styles: dict = {}
    written = 0
    for name, headers, rows, starts in plan:
        freeze, widths, wrap, _most = LAYOUT[name]
        width_of = [widths.get(header, DEFAULT_WIDTH) for header in headers]
        for start in range(0, max(len(rows), 1), CAPACITY):
            part_name = place(start, CAPACITY, name)[0]
            part = rows[start : start + CAPACITY]
            sheet = book.create_sheet(part_name)
            styles = styles or _book_styles(sheet)
            last = get_column_letter(len(headers))
            sheet.freeze_panes = freeze
            for number, width in enumerate(width_of, 1):
                column = sheet.column_dimensions[get_column_letter(number)]
                column.width = width
                column.hidden = headers[number - 1] == contract.ADDRESS
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
                summary = len(row) > 1 and all(held[0] is None for held in row[1:])
                if summary:
                    sheet.merged_cells.add(f"A{number}:{last}{number}")
                    row_for_height = (row[0],)
                    row_widths = [
                        sum(
                            width
                            for header, width in zip(headers, width_of, strict=True)
                            if header != contract.ADDRESS
                        )
                    ]
                else:
                    visible = [
                        (held, width)
                        for header, held, width in zip(headers, row, width_of, strict=True)
                        if header != contract.ADDRESS
                    ]
                    row_for_height = tuple(held for held, _width in visible)
                    row_widths = [width for _held, width in visible]
                lines = row_lines(row_for_height, row_widths) if wrap else 1
                sheet.row_dimensions[number].height = min(
                    contract.MAX_ROW_HEIGHT_POINTS, round(lines * LINE_POINTS, 2)
                )
            visible_headers = [
                (label(header), width)
                for header, width in zip(headers, width_of, strict=True)
                if header != contract.ADDRESS
            ]
            header_lines = row_lines(
                tuple(held for held, _width in visible_headers),
                [width for _held, width in visible_headers],
            )
            sheet.row_dimensions[1].height = min(
                contract.MAX_ROW_HEIGHT_POINTS, round(header_lines * LINE_POINTS, 2)
            )
            sheet.append([_book_cell(sheet, label(header), True, True, styles) for header in headers])
            previous_outcome = None
            address_index = headers.index(contract.ADDRESS) if contract.ADDRESS in headers else None
            for row in part:
                written_row = [_book_cell(sheet, held, False, wrap, styles) for held in row]
                if name == contract.POSTED and address_index is not None:
                    address = row[address_index][0]
                    parts = address.strip("/").split("/") if isinstance(address, str) else []
                    outcome = (
                        tuple(parts[:4])
                        if len(parts) >= 4
                        and parts[0] == "studies"
                        and parts[1].isdigit()
                        and parts[2] == "posted_outcomes"
                        and parts[3].isdigit()
                        else None
                    )
                    if outcome is not None and outcome != previous_outcome:
                        for written_cell in written_row:
                            edge = copy(written_cell.border)
                            edge.top = SECTION_EDGE
                            written_cell.border = edge
                    previous_outcome = outcome
                sheet.append(written_row)
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


def _column_hidden(path: Path, sheet: str, number: int) -> bool:
    """Whether a workbook column is hidden, reading only the target sheet's XML header."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet_node = next(
            (
                node
                for node in workbook.iter()
                if node.tag.rsplit("}", 1)[-1] == "sheet" and node.get("name") == sheet
            ),
            None,
        )
        if sheet_node is None:
            return False
        relationship = next((value for key, value in sheet_node.attrib.items() if key.endswith("}id")), None)
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            (node.get("Target") for node in relationships if node.get("Id") == relationship),
            None,
        )
        if not isinstance(target, str):
            return False
        target = (
            target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        )
        with archive.open(target) as source:
            for _event, node in ET.iterparse(source, events=("start",)):
                if node.tag.rsplit("}", 1)[-1] == "sheetData":
                    break
                if node.tag.rsplit("}", 1)[-1] != "col":
                    continue
                start, end = int(node.get("min", "0")), int(node.get("max", "0"))
                if start <= number <= end:
                    return node.get("hidden") in {"1", "true", "True"}
    return False


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
                if contract.ADDRESS in headers:
                    address_column = headers.index(contract.ADDRESS) + 1
                    if not _column_hidden(path, part, address_column):
                        problems.append(f"{part}: address column is not hidden")
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
