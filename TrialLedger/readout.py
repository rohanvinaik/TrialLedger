"""landscape.xlsx: the reviewer's workbook of a landscape.json record (schema 3; refine-landscape-record
unit C).

The workbook contract.SHEETS declares, derived from the record alone and laid out for a clinical reviewer: the
Read me, the Trial index, each trial's dossier (Trial review), the listings, the readings across trials, the
Readings sheet and the Column dictionary. Each displayed value is a cell tuple (value, link, status, source,
rule, inputs); the row functions build every sheet's rows of them and the writer only lays them out. The file
is read back and refused unless every cell (its value and, for a number, its format) equals its derivation,
and its bytes are the same for the same record (the write times and the zip's member times are fixed).
"""

from __future__ import annotations

import io
import re
import zipfile
from copy import copy
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

BOLD = Font(name="Arial", size=10, bold=True)

EDGE = Side(style="thin", color="BFBFBF")

BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=EDGE)

HEADER_BORDER = Border(left=EDGE, right=EDGE, top=EDGE, bottom=Side(style="thin", color="000000"))

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
    "drug_class": "the interventions' drug classes",
}
# The key-criteria categories in clinical words: the contract's own labels.
KEY_CATEGORY_WORDS = {name: label for name, label, _readings in contract.KEY_CRITERION_CATEGORIES}
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
    known, interpolated = levels[0][1], levels[1][1]
    same = held_kind(known) == "reading" and held_kind(interpolated) == "reading"
    if same and (known["status"], known["result"]) == (interpolated["status"], interpolated["result"]):
        # the default relations change nothing: one row
        levels = levels[:1]
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
    registered; else the interpolated one when it settles on one value, labelled; else "Unresolved" (its
    reason and any values the default relations leave are in the dossier)."""
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
    settled = held_kind(interpolated) == "reading" and interpolated["status"] == "interpolated"
    if settled and not (isinstance(interpolated["result"], list) and len(interpolated["result"]) > 1):
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


def key_categories(value: Any) -> str:
    """A key criterion's categories in words, in the order first met, joined by "; " ("Performance status;
    CNS metastases"); none — "Not stated"."""
    held = value.get("categories") if isinstance(value, dict) else None
    named = [KEY_CATEGORY_WORDS.get(str(item), str(item)) for item in held or []]
    return "; ".join(dict.fromkeys(named)) or NOT_STATED


def key_reading_words(value: Any) -> str:
    """A key criterion's typed readings, each "<concept>: <values>", joined by "; "."""
    if not isinstance(value, dict):
        return value_words(value)
    return "; ".join(atom_words(item) for item in value.get("readings") or []) or NO_READING


def key_criterion_rows(study: dict[str, Any]) -> list[tuple[str, Any, str]]:
    """The dossier's Key criteria band: one row per key criterion, its categories first, then its words as
    written, its role and the readings that made it key; every criterion stays in the Eligibility listing."""
    rows = []
    held = study.get("key_criteria")
    for number, entry in enumerate(held if isinstance(held, list) else [], 1):
        role = entry.get("role")
        role_line = HEADINGS.get(str(role), "Not settled" if role == "unresolved" else value_words(role))
        lines = (
            key_categories(entry.get("reading")),
            f"As written: {value_words(entry.get('text'))}",
            f"Role: {role_line}",
            f"Reading: {key_reading_words(entry.get('reading'))}",
        )
        rows.append((f"Key criterion {number}", "\n".join(lines), READING))
    return rows


def criterion_readings(value: Any) -> str:
    """A criterion's typed readings (the record's list of readings, one per atom the banks typed), one
    "Reading: ..." per line; none — "No reading produced" (which does not mean the criterion holds no
    clinical information)."""
    readings = value if isinstance(value, list) else [value]
    lines = [
        f"Reading: {atom_words(reading['result'])}"
        for reading in readings
        if held_kind(reading) == "reading" and reading["status"] == "known" and reading["result"]
    ]
    return "\n".join(lines) or NO_READING


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
    if key == "key_criteria":
        return key_criterion_rows(study)
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
                    f"{value_words(value)}; the registry's intervention MeSH terms beside it: "
                    f"{mesh} (the registry's terms, never a drug class)"
                )
            if field.name == "studies[].key_criteria[].reading":
                words = key_reading_words(value)
            if field.name == "studies[].key_criteria[].role":
                words = HEADINGS.get(str(value), words)
            if field.name == "studies[].key_criteria[].rule":
                continue
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


# ledger.results_state's codes as the record writes a known results reading's result.
POSTED_WORDS = ("posted", "results posted")


def results_posted(study: dict[str, Any]) -> bool:
    """Whether the record's results reading says the trial posted results."""
    value = study.get("results_posted")
    return held_kind(value) == "reading" and value["status"] == "known" and value["result"] in POSTED_WORDS


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
MAX_PLACES = 30  # the most decimal places a spreadsheet number format shows
COUNT_FORMAT = "#,##0"


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
    held = study.get("biomarker_mentions")
    rows = []
    for k, value in enumerate(held if isinstance(held, list) else []):
        if held_kind(value) != "reading" or not isinstance(value["result"], dict):
            continue
        mention = value["result"]
        address = f"/studies/{number}/biomarker_mentions/{k}"
        words = "; ".join(f"“{word}”" for word in value.get("words") or []) or NOT_STATED
        criterion = criterion_at(study, mention.get("at"))
        if criterion is not None:
            words += (
                f" (criterion {value_words(criterion.get('number'))}: {value_words(criterion.get('text'))})"
            )
        values = (
            study["nct"],
            address,
            value_words(mention.get("biomarker")),
            value_words(mention.get("states"), "", " or "),
            HEADINGS.get(str(mention.get("role")), value_words(mention.get("role"))),
            words,
            str(value["rule"]),
        )
        rows.append(tuple(cell(item, "known", address) for item in values))
    return rows


def criterion_at(study: dict[str, Any], at: Any) -> Any:
    """The criterion a reading's "criteria/<i>" names in its own study, None where it names none."""
    criteria = study.get("criteria")
    index = str(at).removeprefix("criteria/") if isinstance(at, str) else ""
    if not index.isdigit() or not isinstance(criteria, list) or int(index) >= len(criteria):
        return None
    return criteria[int(index)]


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
    if field.endswith("criteria[].readings[]"):
        return atom_words(value["result"]) if value["result"] else NO_READING
    if field.endswith("criteria[].role"):
        return role_words(value)
    if field.endswith("biomarker_mentions[]") and isinstance(value["result"], dict):
        mention = value["result"]
        return f"{value_words(mention.get('biomarker'))}: {value_words(mention.get('states'), '', ' or ')}"
    if field == "studies[].universe" and isinstance(value["result"], dict):
        return (
            " and ".join(UNIVERSE_LABELS.get(u, u) for u in value["result"].get("universes") or []) or "none"
        )
    return result_words(value["result"])


# The Readings sheet's plain names of the fields a rule reads; the record's long definitions stay in the
# Column dictionary. A field not listed shows its contract label.
READING_FIELD_WORDS = {
    "studies[].interventions[].drug_class": "Drug class",
    "studies[].interventions[].axes": "Drug identity and classes",
    "studies[].interventions[].modality": "Modality",
    "studies[].eligibility.coverage": "Criteria abbreviated or complete",
    "studies[].criteria[].role": "Criterion role",
    "studies[].criteria[].readings": "Criterion reading",
    "studies[].biomarker_mentions": "Biomarker mention",
    "studies[].universe": "Universe",
    "studies[].coordinates.setting": "Treatment setting",
    "studies[].coordinates.setting_interpolated": "Treatment setting, with the default relations",
    "studies[].coordinates.setting_proposed": "Treatment setting, one proposed relation alone",
    "studies[].coordinates.prior_advanced_lines": "Prior lines for advanced disease",
    "studies[].coordinates.prior_advanced_lines_interpolated": "Prior lines for advanced disease, with the "
    "default relations",
    "studies[].coordinates.prior_advanced_lines_proposed": "Prior lines for advanced disease, one proposed "
    "relation alone",
    "studies[].coordinates.selection": "Gene selection",
    "studies[].coordinates.selection_interpolated": "Gene selection, with the default relations",
    "studies[].coordinates.selection_proposed": "Gene selection, one proposed relation alone",
    "studies[].registered_outcomes[].endpoint_classes": "Endpoint reading",
    "studies[].registered_outcomes[].time_points": "Time-point reading",
    "studies[].posted_outcomes[].endpoint_classes": "Posted measure's endpoint reading",
    "studies[].references[].role": "Reference role",
    "studies[].results_posted": "Results posted",
}


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
            READING_FIELD_WORDS.get(field.removesuffix("[]"), named.label if named else field),
            read or ("Its heading" if field.endswith("criteria[].role") else NOT_STATED),
            f"{rule} ({version})",
            reading_result(field, value),
            STATUS_LABELS.get(value["status"], STATUS_LABELS["unresolved"]),
        )
        rows.append(tuple(cell(item, "known", pointer) for item in values))
    return rows


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
    minimum = thresholds.get("signal_min_trials")
    if isinstance(minimum, int) and len(record["studies"]) < minimum:
        # below the signal minimum the section's rows are not findings: one line says so
        cohort = {}
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
    if not rows and isinstance(cohort_reason(record), str):
        # the record's own reason (below the signal minimum), in the Population and limits column
        reason = cohort_reason(record)
        line = (
            "/cohort",
            "Too few comparable trials to assess",
            None,
            None,
            None,
            f"{reason[:1].upper()}{reason[1:]}",
            None,
        )
        rows.append(tuple(cell(value, "known", "/cohort") for value in line))
    if not rows:
        rows.append(
            (
                cell("/cohort", "known"),
                cell("The record holds no across-trial finding for these trials", "known"),
                *(cell(None, "known"),) * 5,
            )
        )
    return rows


def cohort_reason(record: dict[str, Any]) -> Any:
    """The record's reason the cohort holds no finding (cohort.reason), None where it gives none."""
    cohort = record.get("cohort")
    return cohort.get("reason") if isinstance(cohort, dict) else None


def recurring_rows(record: dict[str, Any]) -> list[tuple]:
    """The Recurring criteria rows: one per element more than half of a group of comparable trials state, with
    how many of how many, the grouping in words, and examples of whole criteria (each may carry further
    requirements; never reusable text) with their trials; a group too small, one line saying why; none at
    all, one line saying so."""
    held = record.get("recurring_criteria")
    rows = []
    for i, entry in enumerate(held if isinstance(held, list) else []):
        address = f"/recurring_criteria/{i}"
        element = entry.get("element") if isinstance(entry.get("element"), dict) else {}
        words = str(element.get("words") or NOT_STATED)
        if element.get("key") is None:
            # a group too small (or of no established condition): its counts and examples cannot apply
            line = f"{words[:1].upper()}{words[1:]}"
            grouping = value_words(entry.get("grouping"))
            values = (line, None, None, value_words(entry.get("of_trials")), grouping, None, None, None)
        else:
            examples = [e for e in entry.get("examples") or [] if isinstance(e, dict)]
            places = [e.get("criterion") if isinstance(e.get("criterion"), dict) else {} for e in examples]
            sources = [
                f"{e.get('trial')}, {HEADINGS.get(str(place.get('heading')), 'no heading').lower()} "
                f"criterion {place.get('number')}"
                for e, place in zip(examples, places, strict=True)
            ]
            # each example a whole criterion on its own line, after its trial and criterion number
            wordings = [f"{source}: “{e.get('text')}”" for source, e in zip(sources, examples, strict=True)]
            values = (
                words,
                HEADINGS.get(str(entry.get("role")), value_words(entry.get("role"))),
                value_words(entry.get("trials")),
                value_words(entry.get("of_trials")),
                value_words(entry.get("grouping")),
                "\n".join(wordings) or NOT_STATED,
                "\n".join(sources) or NOT_STATED,
                value_words(entry.get("other_trials"), "", ", "),
            )
        rows.append(tuple(cell(value, "known", address) for value in (*values, address)))
    if not rows:
        line = "No criterion is stated by more than half of a group of comparable trials in this record"
        rows.append((cell(line, "known"), *(cell(None, "known"),) * 7, cell("/recurring_criteria", "known")))
    return rows


SOURCE_KIND = {"plain": "{path}", "reading": "rule {path}", "run": "recorded by the run ({path})"}


def dictionary_rows(n: int) -> list[tuple]:
    """The Column dictionary: each sheet's columns, once, with the registry fields or rules they show and
    what they hold."""
    rows = []
    for sheet in contract.SHEETS:
        # the Read me's topics are not columns of record fields
        if sheet.name not in BUILT or sheet.name == contract.READ_ME:
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
        "Recurring criteria lists the readings more than half of a group of comparable trials state, each "
        "with whole criteria as examples: it is starting material for standard protocol language, never "
        "established reusable text, and each example may carry further requirements.",
        "Every listing row's Address in the record is where the assistant finds that row in landscape.json: "
        "ask about a row by its address. The Readings sheet lists every reading a rule made, with the words "
        "it read; the Column dictionary says where each column comes from.",
        "A cell says in words what the registry does not give (Not stated, Not posted, Not reported, No "
        "reading produced). A blank cell is one whose column cannot apply to its row: a Safety group column "
        "past the trial's own groups, the unnamed class or category of a posted measure.",
    )
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
    contract.RECURRING: (
        "B2",
        {
            "Element": 34,
            "Role": 11,
            "Grouping": 40,
            contract.RECURRING_EXAMPLE: 60,
            "Examples from": 14,
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
    rows[contract.RECURRING] = recurring_rows(record)
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
