"""Preservation, checked independently: registry value → record value → displayed cell
(refine-landscape-record 1.7 and 3.6).

The target the record (unit A) and the workbook (unit C) are held to, written from TrialLedger/contract.py and
its hand-checked examples, never from the code that builds the record or the workbook. This module walks the
registry's study JSON itself, following each plain field's API path templates in contract.FIELDS, and reads
landscape.json and landscape.xlsx as data:

- registry → record (`study_findings`): every value the registry holds at a plain field's path is in the
  record at the same place, exactly (type and precision: the registry's "63.4" is the string "63.4", never
  63.4 or "63"; its "NA" stays "NA", with its comment). A measurement, a denominator count, a flow count or
  an adverse-event count is placed by its group ID within its parent, so a value under the wrong group is
  caught; a value the record says is not stated must be one the registry does not hold; a value the record
  holds must be one the registry holds. The adverse-event tables and the registered outcomes, which the
  registry keeps in several lists, are matched by the record's own list name (`WHICH_LIST`) and the position
  within that list.
- record → cell (`cell_findings`): each listing row's address (a JSON pointer in its "Address in the record"
  column) resolves in the record, the row's trial is the addressed study, and each column shows the values of
  the fields contract.SHEETS names for it, at the addressed node, its ancestors, or (for a measurement's
  denominator and group) the entries of the same group; codes through contract.DISPLAY. Safety's per-group
  cells hold each group's counts exactly, "Not reported" where the registry gives no count for a group, and
  are blank only past the trial's last group. A listing over a top-level list of the record (the recurring
  criteria) is read the same way, each of a row's representative wordings shown. The Trial index is checked
  trial by trial and the Trial review fact by fact (a fact of one value against the record's value of its
  label, a numbered fact's every "Label: value" line against its list entry, every fact the registry holds
  given its row).
- what a cell may say: a status the record holds in place of a value (not stated, not posted, unresolved, a
  criterion with no reading) is shown in exactly its own words, never in others; a registry decimal written
  as a number cell keeps its value exactly and the decimals the registry wrote ("66.0", not 66), and a value
  a number cannot hold exactly (1e-400) is written as text; no cell shows the record's JSON.

Two depths. A complete record (a run's output) must carry every value the registry holds. An excerpt (the
contract's worked examples, cut from the bodies by hand) is held to what it carries: every value it holds must
be the registry's, and a field it carries somewhere must be carried at every node it holds.

Each disagreement is a named finding (FINDING_WORDS). The decisions are pure, over literal values, beside the
shells that walk the JSON and read the workbook.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, NamedTuple

from TrialLedger import contract
from TrialLedger.contract import FIELDS, SHEETS

# The record's name for each list the registry keeps one kind of entry in, by the registry list's key. The
# contract names the record's field (`form` "which list") but not its values; these are the values the
# contract's example holds ("serious") and their siblings.
WHICH_LIST = {
    "primaryOutcomes": "primary",
    "secondaryOutcomes": "secondary",
    "otherOutcomes": "other",
    "seriousEvents": "serious",
    "otherEvents": "other",
}
# How the workbook shows each list name (the Safety example: "Serious").
WHICH_LIST_WORDS = {"primary": "Primary", "secondary": "Secondary", "other": "Other", "serious": "Serious"}
# The keys of a value object: a rule's reading, or a value that is not simply known.
VALUE_OBJECT_KEYS = ("status", "rule", "words", "result", "note")
# The words a cell shows for a group's adverse-event count the registry does not give.
NOT_REPORTED = "Not reported"
# Each listing's row grain: the record's node one row shows, as a path template. A listing row's address must
# name a node of one of these, and (in a complete record) every such node has exactly one row.
LISTING_GRAINS: dict[str, tuple[str, ...]] = {
    contract.ELIGIBILITY: ("studies[].criteria[]",),
    contract.REGISTERED: ("studies[].registered_outcomes[]",),
    contract.POSTED: ("studies[].posted_outcomes[].classes[].categories[].measurements[]",),
    contract.ANALYSES: ("studies[].posted_outcomes[].analyses[]",),
    contract.BASELINE: ("studies[].baseline.measures[].classes[].categories[].measurements[]",),
    contract.FLOW: (
        "studies[].participant_flow.periods[].milestones[].counts[]",
        "studies[].participant_flow.periods[].withdrawals[].counts[]",
    ),
    contract.GROUPS: (
        "studies[].posted_outcomes[].groups[]",
        "studies[].baseline.groups[]",
        "studies[].participant_flow.groups[]",
        "studies[].adverse_events.groups[]",
    ),
    contract.SAFETY: ("studies[].adverse_events.events[]",),
}
# Listings whose rows show a reading or a finding: their address must resolve and name the row's trial; their
# columns are a reading's own parts, which the Readings and Biomarkers checks of acceptance/reviewer.py read.
ADDRESSED_ONLY = ()
# The Groups sheet's columns read by their own rule (_groups_column), not from the fields they name.
GROUPS_OWN = ("Module", "Column")
SAFETY_CELL = re.compile(r"G(\d+) (affected|at risk|events)")
SAFETY_STAT = {"affected": "affected", "at risk": "at_risk", "events": "events"}

FINDING_WORDS = {
    # registry → record
    "mismatch": "the record holds a different value from the registry's",
    "misplaced": "the record holds, here, the value the registry gives another group or entry",
    "dropped": "the registry holds a value the record does not carry",
    "false_absence": "the record says not stated where the registry holds a value",
    "invented": "the record holds a value where the registry holds none",
    "no_body": "the record holds a study whose registry body was not given",
    "study_missing": "a registry body's study is not in the record",
    # record → cell
    "address_unreadable": "the row's address is not a JSON pointer",
    "address_unresolved": "the row's address names no node of the record",
    "wrong_grain": "the row's address names a node this listing does not show",
    "trial_differs": "the row's trial is not the study its address names",
    "row_missing": "a node of the record this listing shows has no row",
    "row_repeated": "a node of the record has more than one row",
    "column_missing": "a column the contract names is not in the sheet",
    "sheet_missing": "a listing the contract names is not in the workbook",
    "blank": "the cell is blank where the record holds a value",
    "unexplained_blank": "the cell is blank where a value could exist (an absence is written in words)",
    "not_blank": "the cell holds something where its column cannot apply to the row",
    "retyped": "the cell holds the value as another type (a number for the registry's text, or the reverse)",
    "number_differs": "the cell holds a different number from the record's",
    "decimals_differ": "the cell holds the record's number but shows other decimals than the registry wrote",
    "wrong_words": "the cell's words are not those of the status the record holds (an absence, an unresolved "
    "value, a criterion with no reading)",
    "not_shown": "the cell does not show the record's value exactly",
    "raw_record": "the cell shows a piece of the record's JSON instead of words",
    "fact_missing": "a dossier fact the record holds has no row",
    "continuation_invalid": "a dossier continuation has missing, repeated, reordered or inconsistent parts",
    "format_differs": "the number cell's format is not the contract's (a count in General, a registry "
    "decimal in the format of its own decimal places)",
    "wrong_link": "the cell's link points at another row than the record's own group",
}
# What follows a status's words before its reason (contract.REASON_FORM: "<Status> — <reason>").
REASON_SEPARATOR = contract.REASON_FORM.format(status="", reason="")


class Finding(NamedTuple):
    """One disagreement: its code (FINDING_WORDS), the trial, the field or sheet and column, where (a key into
    the record, or a row's address), and the values expected and held."""

    code: str
    nct: str
    field: str
    where: str
    expected: Any
    held: Any


# ── the pure decisions ──────────────────────────────────────────────────────────────────────────────────


def same_value(left: Any, right: Any) -> bool:
    """Whether two JSON values are the same value of the same type, all the way down (0 is not False, 7 is not
    7.0, "7" is not 7)."""
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_value(left[key], right[key]) for key in left)
    return left == right


def value_verdict(
    registry_held: bool,
    registry_value: Any,
    record_holds: str,
    record_value: Any,
    siblings: list[Any],
    required: bool,
) -> str:
    """One registry value against the record's value at the same place (pure; its two-sign tests are in
    tests/test_acceptance_preserve.py, and Detective's converge ends INCOMPLETE on it, harvest_cut).

    registry_held  — whether the registry holds a value there (contract.holds_value);
    record_holds   — "value" (a plain value), "value_object" (a status object: not stated, unresolved, ...)
                     or "absent" (the record has no key there);
    siblings       — the registry's values at the other entries of the same list (other groups, other
                     measurements), to tell a misplaced value from a wrong one;
    required       — whether the record must carry the value (always, in a complete record; in an excerpt,
                     only where it holds the node and carries the field elsewhere).
    Codes: match; misplaced (the record's value is a sibling's); mismatch; false_absence (a status object
    where the registry holds a value); dropped (absent where required); not_in_excerpt (absent, not required);
    invented (a value where the registry holds none); silent (neither holds a value, or the record says why).
    """
    if not registry_held:
        if record_holds == "value":
            return "invented"
        return "silent"
    if record_holds == "absent":
        return "dropped" if required else "not_in_excerpt"
    if record_holds == "value_object":
        return "false_absence"
    if same_value(registry_value, record_value):
        return "match"
    if any(same_value(sibling, record_value) for sibling in siblings):
        return "misplaced"
    return "mismatch"


def pointer_steps(pointer: str) -> tuple[str, list[str]]:
    """A JSON pointer (RFC 6901) split into its reference tokens (pure — pinned).

    Codes: ok (with the tokens, "~1" read as "/" and "~0" as "~"; "" is the whole document, no tokens);
    not_a_pointer (a non-empty pointer not starting with "/"); bad_escape (a "~" not followed by 0 or 1).
    """
    if pointer == "":
        return "ok", []
    if not pointer.startswith("/"):
        return "not_a_pointer", []
    tokens = []
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            return "bad_escape", []
        tokens.append(raw.replace("~1", "/").replace("~0", "~"))
    return "ok", tokens


def shows_text(cell: str, text: str) -> bool:
    """Whether a cell's text shows a value's text exactly: as written, and a number not as part of a longer
    one ("7" is not shown by "17", "63.4" not by "63.40")."""
    for found in re.finditer(re.escape(text), cell):
        before = cell[found.start() - 1] if found.start() > 0 else ""
        after = cell[found.end() :]
        if text[:1].isdigit() and (before.isdigit() or before == "."):
            continue
        if text[-1:].isdigit() and (after[:1].isdigit() or re.match(r"\.\d", after)):
            continue
        return True
    return False


def displayed_number(value: Any, number_format: str) -> str | None:
    """The text a spreadsheet shows for a number under its number format (pure — pinned).

    "General" shows an integral value without decimals and any other as its shortest exact decimal (63.4,
    not 63.40); a format of zeros with N zeros after its point ("0", "0.0", "0.00", optionally "#,##0.0")
    shows N decimals. None for a format this reading does not know, or a value that is not a number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if number_format == "General":
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return str(value) if isinstance(value, int) else repr(value)
    shape = re.fullmatch(r"(?:#,##)?0(?:\.(0+))?", number_format)
    if shape is None:
        return None
    return f"{value:.{len(shape.group(1) or '')}f}"


def number_agrees(text: str, value: Any, number_format: str) -> str:
    """A registry number written as text against the number a cell holds (pure — pinned).

    Codes: same (the cell's number is the text's value exactly and shows it with the same decimals);
    decimals_differ (the value is exact but the cell shows other decimals: "66.0" as 66); value_differs (the
    cell's number is not the text's value, as a value a cell cannot hold exactly, 1e-400, never is); not_a_
    number (the text is not a finite decimal number, or the cell holds no number).
    """
    try:
        wanted = Decimal(text)
    except InvalidOperation:
        return "not_a_number"
    if not wanted.is_finite() or isinstance(value, bool) or not isinstance(value, (int, float)):
        return "not_a_number"
    held = Decimal(value) if isinstance(value, int) else Decimal(repr(value))
    if held != wanted:
        return "value_differs"
    return "same" if displayed_number(value, number_format) == text else "decimals_differ"


def cell_verdict(
    cell: Any,
    texts: list[str],
    numbers: list[Any],
    status_words: list[str],
    by_construction: bool,
    number_format: str = "General",
) -> str:
    """What a displayed cell shows of the record's values (pure — pinned).

    cell            — the cell as read back: None (blank), text, or a number;
    texts           — the record's values the cell must show (codes already in their words);
    numbers         — the record's numbers the cell must hold as numbers, exactly (the Safety counts);
    status_words    — the words of a status the record holds here instead of a value (an absence, an
                      unresolved value, a criterion with no reading): where the record holds no value to
                      show, the cell must be exactly one of them, or one of them followed by " — " and why
                      ("Unresolved — the name is not in RxNorm"); beside values they are not required;
    by_construction — whether the column cannot apply to the row (a group past the trial's last);
    number_format   — the cell's number format, for a number written for a registry decimal.
    Codes: shown; blank_by_construction; not_blank; blank (a value to show, none shown); unexplained_blank
    (nothing to show, yet an absence must be worded); retyped; number_differs; decimals_differ;
    wrong_words (other words than the status's); not_shown.

    A nonempty whitespace-only source text copied identically is shown, not a missing cell.
    """
    blank = cell is None or (isinstance(cell, str) and not cell.strip())
    if by_construction:
        return "blank_by_construction" if blank else "not_blank"
    if (
        blank
        and isinstance(cell, str)
        and cell
        and texts
        and not numbers
        and all(cell == text for text in texts)
    ):
        return "shown"
    if blank:
        return "blank" if texts or numbers or status_words else "unexplained_blank"
    is_number = isinstance(cell, (int, float)) and not isinstance(cell, bool)
    if numbers:
        if not is_number:
            return "retyped" if any(cell == str(number) for number in numbers) else "number_differs"
        return "shown" if any(same_value(cell, number) for number in numbers) else "number_differs"
    if is_number:
        if len(texts) != 1:
            return "not_shown" if texts else "retyped"
        agreement = number_agrees(texts[0], cell, number_format)
        if agreement == "not_a_number":
            return "retyped"
        return {"same": "shown", "decimals_differ": "decimals_differ"}.get(agreement, "number_differs")
    if not isinstance(cell, str):
        return "retyped" if any(str(cell) == text for text in texts) else "not_shown"
    if not all(shows_text(cell, text) for text in texts):
        return "not_shown"
    if status_words and not texts:
        said = cell.strip()
        if said in status_words or any(
            said.startswith(f"{words}{REASON_SEPARATOR}") for words in status_words
        ):
            return "shown"
        return "wrong_words"
    return "shown"


def raw_record(cell: Any) -> bool:
    """Whether a cell shows a piece of the record's JSON (a value object written as data) instead of words."""
    return (
        isinstance(cell, str)
        and re.search(r"[{\[]\s*['\"](status|rule|words|result|note)['\"]\s*:", cell) is not None
    )


# ── the registry's values, field by field, and the record's ─────────────────────────────────────────────


def is_value_object(value: Any) -> bool:
    """A status object: a dict with a status, whose keys are a value object's."""
    return isinstance(value, dict) and "status" in value and set(value) <= set(VALUE_OBJECT_KEYS)


def _segments(field_name: str) -> list[str]:
    """A field's record path below the study ("studies[]." removed)."""
    return field_name.split(".")[1:]


def _element_key(item: Any, index: int, group_key: str) -> Any:
    """A list entry's place: its group ID where it carries one (measurements, counts), else its index."""
    if isinstance(item, dict) and isinstance(item.get(group_key), str):
        return ("group", item[group_key])
    return index


def keyed_values(node: Any, segments: list[str], group_key: str) -> list[tuple[tuple, Any]]:
    """Every value under a node at a path, with its place: one key per list followed."""
    nodes: list[tuple[tuple, Any]] = [((), node)]
    for segment in segments:
        name = segment.removesuffix("[]")
        following = []
        for key, held in nodes:
            if not isinstance(held, dict) or name not in held:
                continue
            value = held[name]
            if segment.endswith("[]"):
                items = value if isinstance(value, list) else []
                following += [
                    (key + (_element_key(item, i, group_key),), item) for i, item in enumerate(items)
                ]
            else:
                following.append((key, value))
        nodes = following
    return nodes


def _record_depth(field: contract.Field) -> int:
    return sum(segment.endswith("[]") for segment in _segments(field.name))


def _which_field(field: contract.Field) -> contract.Field | None:
    """For a field the registry keeps in several lists, the record's field naming which list an entry is
    in."""
    if len(field.source) < 2:
        return None
    segments = _segments(field.name)
    first = next(i for i, segment in enumerate(segments) if segment.endswith("[]"))
    prefix = ".".join(["studies[]", *segments[: first + 1]]) + "."
    return next(f for f in FIELDS if f.form == "which list" and f.name.startswith(prefix))


def registry_field(body: dict[str, Any], field: contract.Field) -> dict[tuple, Any]:
    """The registry's values of a plain field, keyed by place, as the record must hold them (its form)."""
    depth = _record_depth(field)
    gathered: dict[tuple, list[Any]] = {}
    for template in field.source:
        listed = keyed_values(body, template.split("."), "groupId")
        which = None
        if len(field.source) > 1:
            which = WHICH_LIST[next(s for s in template.split(".") if s.endswith("[]")).removesuffix("[]")]
        for key, value in listed:
            place = key[:depth]
            if which is not None:
                place = ((which, place[0]), *place[1:])
            gathered.setdefault(place, []).append(which if field.form == "which list" else value)
    expected: dict[tuple, Any] = {}
    api_depth = field.source[0].count("[]")
    for place, values in gathered.items():
        if field.form == "count":
            expected[place] = len(values)
        elif field.form == "distinct":
            expected[place] = list(dict.fromkeys(v for v in values if contract.holds_value(v)))
        elif api_depth > depth:
            expected[place] = values
        else:
            expected[place] = values[0]
    return {place: value for place, value in expected.items() if contract.holds_value(value)}


def _which_places(study: dict[str, Any], which: contract.Field) -> dict[int, tuple[str, int]]:
    """The record's entries of a several-list field: index → (its list name, its place within that list)."""
    segments = _segments(which.name)
    listing = keyed_values(study, segments[:-1], "group")
    seen: dict[str, int] = {}
    places = {}
    for key, entry in listing:
        name = entry.get(segments[-1]) if isinstance(entry, dict) else None
        name = name if isinstance(name, str) else "unnamed"
        places[key[0]] = (name, seen.get(name, 0))
        seen[name] = seen.get(name, 0) + 1
    return places


def record_field(study: dict[str, Any], field: contract.Field) -> tuple[dict[tuple, Any], set[tuple]]:
    """The record's values of a field, keyed by place as registry_field keys them, and the places of the
    nodes that hold the field (its parents). A status object met on the way stands for every field below
    it."""
    segments = _segments(field.name)
    nodes: list[tuple[tuple, Any]] = [((), study)]
    found: dict[tuple, Any] = {}
    for depth, segment in enumerate(segments):
        name = segment.removesuffix("[]")
        following = []
        for key, held in nodes:
            if is_value_object(held):
                found[key] = held
                continue
            if not isinstance(held, dict) or name not in held:
                continue
            value = held[name]
            if segment.endswith("[]"):
                items = value if isinstance(value, list) else []
                following += [(key + (_element_key(item, i, "group"),), item) for i, item in enumerate(items)]
            elif depth == len(segments) - 1:
                found[key] = value
            else:
                following.append((key, value))
        if depth == len(segments) - 1:
            parents = {key for key, held in nodes if isinstance(held, dict) and not is_value_object(held)}
        nodes = following
    which = _which_field(field)
    if which is not None:
        places = _which_places(study, which)
        found = {_which_key(places, key): value for key, value in found.items()}
        parents = {_which_key(places, key) for key in parents}
    return found, parents


def _which_key(places: dict[int, tuple[str, int]], key: tuple) -> tuple:
    """A record key with its several-list entry's index read as (its list name, its place in that list); a key
    above the list (a status object standing for the whole list) is kept as it is."""
    return (places.get(key[0], key[0]), *key[1:]) if key else key


def _siblings(expected: dict[tuple, Any], place: tuple) -> list[Any]:
    return [value for key, value in expected.items() if key != place and key[:-1] == place[:-1]]


def _where(field: contract.Field, place: tuple) -> str:
    return f"{field.name} at {list(place)}"


def study_findings(body: dict[str, Any], study: dict[str, Any], complete: bool) -> list[Finding]:
    """Every plain field of one study, registry against record (complete: the record must carry every value
    the registry holds; an excerpt, what it carries)."""
    nct = study.get("nct") if isinstance(study.get("nct"), str) else str(study.get("nct"))
    findings = []
    for field in FIELDS:
        if field.kind != "plain" or not field.name.startswith("studies[]."):
            continue
        expected = registry_field(body, field)
        held, parents = record_field(study, field)
        carried = any(not is_value_object(value) for value in held.values())
        for place in list(expected) + [p for p in held if p not in expected]:
            in_record = place in held
            record_value = held.get(place)
            record_holds = (
                "absent" if not in_record else "value_object" if is_value_object(record_value) else "value"
            )
            required = complete or (carried and place in parents)
            code = value_verdict(
                place in expected,
                expected.get(place),
                record_holds,
                record_value,
                _siblings(expected, place),
                required,
            )
            if code not in ("match", "silent", "not_in_excerpt"):
                findings.append(
                    Finding(code, nct, field.name, _where(field, place), expected.get(place), record_value)
                )
    return findings


def record_findings(
    bodies: dict[str, dict[str, Any]], record: dict[str, Any], complete: bool = True
) -> list[Finding]:
    """The registry → record check over a record's studies, each against its registry body by NCT number."""
    findings = []
    studies = [study for study in record.get("studies", []) if isinstance(study, dict)]
    held = set()
    for study in studies:
        nct = study.get("nct")
        held.add(nct)
        if nct not in bodies:
            findings.append(Finding("no_body", str(nct), "studies[].nct", "", None, nct))
            continue
        findings += study_findings(bodies[nct], study, complete)
    if complete:
        findings += [
            Finding("study_missing", nct, "studies[].nct", "", nct, None) for nct in bodies if nct not in held
        ]
    return findings


def project_study(body: dict[str, Any]) -> dict[str, Any]:
    """A study's plain fields laid out as landscape.json schema 3 lays them out, from the registry alone: the
    walker's own record, the substrate the planted-defect tests change and the cell check reads."""
    study: dict[str, Any] = {}
    for field in FIELDS:
        if field.kind != "plain" or not field.name.startswith("studies[]."):
            continue
        segments = _segments(field.name)
        offsets = _list_offsets(body, field)
        for place, value in _positional(body, field).items():
            if offsets:
                place = (offsets[place[0][0]] + place[0][1], *place[1:])
            _put(study, segments, list(place), value)
    return study


def _list_offsets(body: dict[str, Any], field: contract.Field) -> dict[str, int]:
    """For a several-list field: where each registry list's entries start in the record's one list."""
    if len(field.source) < 2:
        return {}
    offsets: dict[str, int] = {}
    start = 0
    for template in field.source:
        segments = template.split(".")
        first = next(i for i, s in enumerate(segments) if s.endswith("[]"))
        name = WHICH_LIST[segments[first].removesuffix("[]")]
        offsets[name] = start
        start += len(keyed_values(body, segments[: first + 1], ""))
    return offsets


def _positional(body: dict[str, Any], field: contract.Field) -> dict[tuple, Any]:
    """registry_field, every list entry placed by its index (the layout, not the comparison)."""
    depth = _record_depth(field)
    gathered: dict[tuple, list[Any]] = {}
    for template in field.source:
        which = None
        if len(field.source) > 1:
            which = WHICH_LIST[next(s for s in template.split(".") if s.endswith("[]")).removesuffix("[]")]
        for key, value in keyed_values(body, template.split("."), ""):
            place = key[:depth]
            if which is not None:
                place = ((which, place[0]), *place[1:])
            gathered.setdefault(place, []).append(which if field.form == "which list" else value)
    laid = {}
    api_depth = field.source[0].count("[]")
    for place, values in gathered.items():
        if field.form == "count":
            laid[place] = len(values)
        elif field.form == "distinct":
            laid[place] = list(dict.fromkeys(v for v in values if contract.holds_value(v)))
        else:
            laid[place] = values if api_depth > depth else values[0]
    return {place: value for place, value in laid.items() if contract.holds_value(value)}


def _put(node: dict[str, Any], segments: list[str], places: list[int], value: Any) -> None:
    """Set a value at a record path, creating the objects and list entries on the way."""
    for depth, segment in enumerate(segments):
        name = segment.removesuffix("[]")
        last = depth == len(segments) - 1
        if not segment.endswith("[]"):
            if last:
                node[name] = value
                return
            node = node.setdefault(name, {})
            continue
        items = node.setdefault(name, [])
        index = places.pop(0)
        items.extend({} for _ in range(index + 1 - len(items)))
        node = items[index]


# ── record → cell ───────────────────────────────────────────────────────────────────────────────────────
# The words, forms and blanks are the contract's declared display policy (contract.STATUS_WORDS, REASON_FORM,
# BASIS_WORDS, WHICH_LIST_WORDS, READING_CODE_WORDS, DATE_FORMS, NUMBER_FORMATS, EMPTY_LISTING_WORDS,
# INDEX_COMPACT, BLANK_BY_CONSTRUCTION, DENOMINATOR); which record values a cell must show, the joins of
# groups and denominators at their scope, the rows a listing must have and the numeric comparison are this
# module's own.

# A criterion the banks typed nothing in reads in words (design §2); the record holds its readings as [].
EMPTY_READING_WORDS = {}
# The statuses a cell shows in their own words where the record holds no value: an absence, a value the
# rules leave unresolved, a reading its universe does not apply.
WORDED_STATUSES = ("not_stated", "not_posted", "unresolved", "not_applicable")
ISO_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:[T ](.+))?")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# Listings the contract gives an empty line but whose rows are readings (no row grain of their own here).
EMPTY_GRAINS = {}
# The units a denominator column implies in its header (contract.DENOMINATOR): a count of these is a number.
IMPLIED_UNITS = "Participants"
# Typed registry date fields; date-shaped free text is not a date field.
DATE_FIELDS = {
    "studies[].start_date.date",
    "studies[].primary_completion_date.date",
    "studies[].completion_date.date",
    "studies[].first_posted",
    "studies[].results_first_posted",
    "studies[].last_update_posted",
    "studies[].documents[].date",
    "studies[].posted_outcomes[].anticipated_posting_date",
}
DENOMINATOR_UNITS = (
    "studies[].posted_outcomes[].denominators[].units",
    "studies[].posted_outcomes[].classes[].denominators[].units",
    "studies[].baseline.denominators[].units",
    "studies[].baseline.measures[].denominators[].units",
    "studies[].baseline.measures[].classes[].denominators[].units",
)
POSTED_GROUPS = "studies[].posted_outcomes[].groups[]"


class Row(NamedTuple):
    """A listing row read back: its sheet, its number in the sheet, and its cells by header."""

    sheet: str
    number: int
    cells: dict[str, Any]


class Number(NamedTuple):
    """A number cell read back from a workbook: its value and its number format."""

    value: Any
    number_format: str


class Linked(NamedTuple):
    """A text cell read back with an internal hyperlink: its text, and the sheet and data row it points to
    (the row's number among the sheet's rows below its header, from 1)."""

    value: Any
    sheet: str
    row: int


def status_words(status: str) -> str:
    """A status in the contract's words (contract.STATUS_WORDS)."""
    return contract.STATUS_WORDS.get(status, status)


def date_words(text: str) -> str:
    """A registry date as contract.DATE_FORMS writes it: a day DD-Mon-YYYY, a month Mon-YYYY, a year YYYY, a
    date with a time the date so written then the time as written; anything else as written."""
    found = ISO_DATE.fullmatch(text)
    if found is None:
        return text
    year, month, day, time = found.groups()
    if month is not None and not 1 <= int(month) <= 12:
        return text
    words = year if month is None else f"{MONTHS[int(month) - 1]}-{year}"
    words = f"{day}-{words}" if day else words
    return f"{words} {time}" if time else words


def decimal_format(text: str) -> str:
    """The number format contract.NUMBER_FORMATS gives a registry decimal: 0, or 0. and one 0 per decimal
    place the registry wrote."""
    places = len(text.partition(".")[2]) if "." in text else 0
    return "0" if not places else "0." + "0" * places


def resolve_pointer(record: Any, tokens: list[str]) -> tuple[bool, Any, str, list[int]]:
    """A pointer's node in the record: whether found, the node, its path template and its list indices."""
    node = record
    template: list[str] = []
    indices: list[int] = []
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
            template.append(token)
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node) and template:
            node = node[int(token)]
            template[-1] += "[]"
            indices.append(int(token))
        else:
            return False, None, "", []
    return True, node, ".".join(template), indices


def _resolve(record: Any, address: Any) -> tuple[bool, Any, str, list[int]]:
    code, tokens = pointer_steps(address) if isinstance(address, str) else ("not_a_pointer", [])
    return resolve_pointer(record, tokens) if code == "ok" else (False, None, "", [])


def _first_list(segments: list[str]) -> int:
    return next((i for i, s in enumerate(segments) if s.endswith("[]") and i > 0), len(segments))


def _applies(field_name: str, row_template: str, grains: tuple[str, ...]) -> bool:
    """Whether a field's values belong to a row: it branches from the row's path no higher than the row's
    first list below the study, and not into another kind of row of the same listing."""
    field = field_name.split(".")
    row = row_template.split(".")
    common = 0
    for a, b in zip(field, row, strict=False):
        if a != b:
            break
        common += 1
    if common < min(_first_list(row), len(row)) and common < len(row):
        return False
    for grain in grains:
        other = grain.split(".")
        if grain == row_template or (row_template + ".").startswith(grain + "."):
            continue
        if common < len(field) and len(other) > common and other[: common + 1] == field[: common + 1]:
            return False
    return True


def _row_values(record: Any, field_name: str, row_template: str, indices: list[int], group: Any):
    """The values of a field for a row: the row's own entries along its path, every entry below it (only the
    row's group's, where entries name a group)."""
    nodes = [record]
    path: list[str] = []
    used = 0
    for segment in field_name.split("."):
        name = segment.removesuffix("[]")
        path.append(segment)
        prefix = ".".join(path)
        along = row_template == prefix or row_template.startswith(prefix + ".")
        following = []
        for node in nodes:
            if is_value_object(node):
                following.append(node)
                continue
            if not isinstance(node, dict) or name not in node:
                continue
            value = node[name]
            if not segment.endswith("[]"):
                following.append(value)
                continue
            if not isinstance(value, list):
                following += [value] if is_value_object(value) else []
            elif along:
                following += [value[indices[used]]] if indices[used] < len(value) else []
            else:
                following += [item for item in value if _in_group(item, group)]
        if segment.endswith("[]") and along:
            used += 1
        nodes = following
    return nodes


def _joins(field_name: str, row_template: str) -> bool:
    """Whether a field is only the group ID that joins another entry to the row (a denominator's group): the
    row's group is shown once, in its Group column, not again beside each joined value."""
    parent = field_name.rpartition(".")[0]
    return field_name.endswith(".group") and not (row_template + ".").startswith(parent + ".")


def _in_group(item: Any, group: Any) -> bool:
    if group is None or not isinstance(item, dict):
        return True
    for key in ("group", "id"):
        if isinstance(item.get(key), str):
            return item[key] == group
    return True


class Expected(NamedTuple):
    """What a cell must show: texts (codes in their words, dates in their form), counts (numbers the
    registry gives as numbers, shown as numbers), and status words (where the record holds no value)."""

    texts: list[str]
    counts: list[Any]
    words: list[str]

    def plus(self, other: Expected) -> Expected:
        return Expected(self.texts + other.texts, self.counts + other.counts, self.words + other.words)


NOTHING = Expected([], [], [])


def expected(field: contract.Field, value: Any) -> Expected:
    """A record value as a cell must show it. A reading the cell shows in its own words (a known reading's
    labels) gives nothing, and the cell must only not be blank."""
    if is_value_object(value):
        status = value.get("status")
        if status == "not_stated" and value.get("note") == "not_applicable":
            return Expected([], [], [status_words("not_applicable")])
        class_rule = contract.FIELD_NAMES["studies[].interventions[].drug_class"].source[0]
        if status == "known" and value.get("rule") == class_rule:
            result = value.get("result")
            classes = (
                result.get("classes")
                if isinstance(result, dict) and result.get("state") == "classified"
                else None
            )
            if isinstance(classes, list) and classes:
                lines = [
                    contract.RXNAV_CLASS_DISPLAY_FORM.format(
                        id=entry[0], name=entry[1], relation=entry[2], source=entry[3]
                    )
                    for entry in classes
                    if isinstance(entry, (list, tuple)) and len(entry) == 4
                ]
                if len(lines) == len(classes):
                    return Expected(["\n".join(lines)], [], [])
            return Expected([], [], [status_words("unresolved")])
        return Expected([], [], [status_words(status)]) if status in WORDED_STATUSES else NOTHING
    if isinstance(value, list):
        if not value and field.name in EMPTY_READING_WORDS:
            return Expected([], [], [EMPTY_READING_WORDS[field.name]])
        total = NOTHING
        for item in value:
            total = total.plus(expected(field, item))
        return total
    if isinstance(value, str) and field.form == "which list":
        return Expected([contract.WHICH_LIST_WORDS.get(value, value)], [], [])
    if isinstance(value, str) and field.display:
        return Expected([contract.display_words(field.display, value)[1]], [], [])
    if isinstance(value, str) and field.kind == "reading" and value in contract.READING_CODE_WORDS:
        return Expected([contract.READING_CODE_WORDS[value]], [], [])
    if isinstance(value, bool):
        return Expected(["Yes" if value else "No"], [], [])
    if isinstance(value, int):
        return Expected([str(value)], [value], [])
    if isinstance(value, str) and contract.holds_value(value):
        return Expected([date_words(value) if field.name in DATE_FIELDS else value], [], [])
    if isinstance(value, float):
        return Expected([repr(value)], [], [])
    return NOTHING


def judge(cell: Any, want: Expected, by_construction: bool) -> str:
    """cell_verdict over a cell as read back, with the contract's number formats: a count shown as a number
    in General, a registry decimal in the format of its own decimal places (format_differs otherwise)."""
    texts = list(dict.fromkeys(want.texts))
    words = list(dict.fromkeys(want.words))
    value = cell.value if isinstance(cell, (Number, Linked)) else cell
    if not isinstance(cell, Number):
        return cell_verdict(value, texts, [], words, by_construction)
    counts = list(dict.fromkeys(want.counts))
    if counts and len(texts) == len(counts):
        return _count_verdict(cell, counts, by_construction)
    else:
        verdict = cell_verdict(value, texts, [], words, by_construction, cell.number_format)
        wanted_format = decimal_format(texts[0]) if len(texts) == 1 else cell.number_format
    if verdict == "shown" and cell.number_format != wanted_format:
        return "format_differs"
    return verdict


def _count_verdict(cell: Any, counts: list[Any], by_construction: bool) -> str:
    """A count (a number the registry gives as a number): the cell holds it as a number, in General."""
    verdict = cell_verdict(_plain(cell), [], counts, [], by_construction)
    general = contract.NUMBER_FORMATS["count"]
    if verdict == "shown" and isinstance(cell, Number) and cell.number_format != general:
        return "format_differs"
    return verdict


def _plain(cell: Any) -> Any:
    return cell.value if isinstance(cell, (Number, Linked)) else cell


def sheet_grains(sheet: contract.Sheet) -> tuple[str, ...]:
    """A listing's row grains: LISTING_GRAINS', or the one top-level list all its fields are under."""
    if sheet.name in LISTING_GRAINS:
        return LISTING_GRAINS[sheet.name]
    tops = {name.split(".")[0] for column in sheet.columns for name in column.fields}
    if len(tops) == 1 and next(iter(tops)).endswith("[]") and tops != {"studies[]"}:
        return (next(iter(tops)),)
    return ()


def _raw_findings(row: Row, nct: str, where: str) -> list[Finding]:
    return [
        Finding("raw_record", nct, f"{row.sheet}: {header}", where, None, _plain(cell))
        for header, cell in row.cells.items()
        if raw_record(_plain(cell))
    ]


def _declared_blank(sheet: str, kind: str) -> tuple[str, ...]:
    """The columns contract.BLANK_BY_CONSTRUCTION declares blank for a sheet's kind of row."""
    return contract.BLANK_BY_CONSTRUCTION.get((sheet, kind), ())


def blank_columns(sheet: str, template: str, node: Any, record: Any, indices: list[int]) -> set[str]:
    """The columns of a row blank by construction: the kinds of row contract.BLANK_BY_CONSTRUCTION names,
    each recognised here from the record."""
    blank: set[str] = set()
    if sheet in (contract.POSTED, contract.BASELINE):
        kind = "a measurement of an untitled class or category"
        found, klass, _t, _i = resolve_pointer(record, _pointer(template, indices, "classes[]"))
        found_c, category, _t, _i = resolve_pointer(record, _pointer(template, indices, "categories[]"))
        if found and isinstance(klass, dict) and not contract.holds_value(klass.get("title")):
            blank |= {"Class"} & set(_declared_blank(sheet, kind))
        if found_c and isinstance(category, dict) and not contract.holds_value(category.get("title")):
            blank |= {"Category"} & set(_declared_blank(sheet, kind))
    if sheet == contract.GROUPS:
        if template != "studies[].adverse_events.groups[]":
            blank |= set(_declared_blank(sheet, "a group of any module but adverse events"))
        if template != POSTED_GROUPS:
            blank |= set(_declared_blank(sheet, "a group of any module but posted results"))
    return blank


def _pointer(template: str, indices: list[int], down_to: str) -> list[str]:
    """The tokens of the pointer to a row's ancestor at a list segment of its template."""
    tokens: list[str] = []
    used = 0
    for segment in template.split("."):
        tokens.append(segment.removesuffix("[]"))
        if segment.endswith("[]"):
            tokens.append(str(indices[used]))
            used += 1
            if segment == down_to:
                return tokens
    return []


def _safety_expected(
    study: dict[str, Any], event: dict[str, Any], n: int, stat: str
) -> tuple[bool, list[Any]]:
    """A Safety cell's expectation: (blank by construction, the number or the words it must show)."""
    groups = (study.get("adverse_events") or {}).get("groups") or []
    if n > len(groups):
        return True, []
    group = groups[n - 1].get("id") if isinstance(groups[n - 1], dict) else None
    counts = [c for c in event.get("counts") or [] if isinstance(c, dict) and c.get("group") == group]
    if counts and stat in counts[0] and not is_value_object(counts[0][stat]):
        return False, [counts[0][stat]]
    return False, []


def _group_of(record: Any, template: str, indices: list[int], node: Any) -> dict[str, Any] | None:
    """A row's group in its own module, for the listings whose Group cell links to it (contract.GROUP_LINKS):
    a measurement's in its own measure's groups, a baseline measurement's or a flow count's in its module's
    groups (the join by group ID within the module)."""
    if not isinstance(node, dict):
        return None
    for sheet, groups_template in contract.GROUP_LINKS.items():
        if template not in LISTING_GRAINS.get(sheet, ()):
            continue
        holder = groups_template.removesuffix(".groups[]").split(".")[-1]
        tokens = (
            _pointer(template, indices, holder)
            if holder.endswith("[]")
            else ["studies", str(indices[0]), holder]
        )
        found, parent, _t, _i = resolve_pointer(record, tokens)
        groups = parent.get("groups") if found and isinstance(parent, dict) else None
        return next(
            (g for g in groups or [] if isinstance(g, dict) and g.get("id") == node.get("group")), None
        )
    return None


def _same_group(left: Any, right: Any) -> bool:
    """Two posted-outcome groups of one trial are the same group where their title and description are."""
    return (
        isinstance(left, dict)
        and isinstance(right, dict)
        and same_value(left.get("title"), right.get("title"))
        and same_value(left.get("description"), right.get("description"))
    )


def _link_findings(
    record, sheets, cell: Linked, group, study_index: int, nct: str, where: str, sheet: str = contract.POSTED
) -> list[Finding]:
    """A Group cell's link must point at the Groups row of the row's own group (contract.GROUP_LINKS): of the
    same trial and module; a posted measure's group by its title and description, any other by its ID."""
    rows = sheets.get(cell.sheet, ([], []))
    headers, cells = rows
    field = f"{sheet}: Group"
    if cell.sheet != contract.GROUPS or not 0 < cell.row <= len(cells):
        return [Finding("wrong_link", nct, field, where, contract.GROUPS, cell)]
    address = dict(zip(headers, cells[cell.row - 1], strict=False)).get(contract.ADDRESS)
    found, target, template, indices = _resolve(record, _plain(address))
    want = contract.GROUP_LINKS.get(sheet)
    if found and template == want and indices[0] == study_index and isinstance(target, dict):
        if want == POSTED_GROUPS and _same_group(target, group):
            return []
        if want != POSTED_GROUPS and target.get("id") == group.get("id") and _same_group(target, group):
            return []
    return [Finding("wrong_link", nct, field, where, group, _plain(address))]


def _outcome_measures(record: Any, study_index: int, node: Any) -> Expected:
    """A posted-outcome group's Outcome measures cell: the title of every measure of its trial that holds the
    same group (title and description)."""
    studies = record.get("studies") or []
    study = studies[study_index] if study_index < len(studies) else {}
    titles = [
        m.get("title")
        for m in study.get("posted_outcomes") or []
        if isinstance(m, dict) and any(_same_group(g, node) for g in m.get("groups") or [])
    ]
    return Expected([t for t in titles if isinstance(t, str)], [], [])


def row_findings(
    record: dict[str, Any], sheet: contract.Sheet, row: Row, sheets: dict | None = None
) -> tuple[list[Finding], str]:
    """One listing row against the record: its address, its trial and every column; and the node it shows."""
    where = f"{sheet.name} row {row.number}"
    address = _plain(row.cells.get(contract.ADDRESS))
    found, node, template, indices = _resolve(record, address)
    if not isinstance(address, str) or pointer_steps(address)[0] != "ok":
        return [Finding("address_unreadable", "", sheet.name, where, None, address)], ""
    if not found:
        return [Finding("address_unresolved", "", sheet.name, where, None, address)], ""
    studies = record.get("studies") or []
    study = studies[indices[0]] if template.startswith("studies[]") and indices else {}
    nct = study.get("nct") if isinstance(study, dict) else None
    findings = _raw_findings(row, str(nct), where)
    trial = _plain(row.cells.get("Trial ID"))
    if "Trial ID" in row.cells and not (isinstance(nct, str) and shows_text(str(trial), nct)):
        findings.append(Finding("trial_differs", str(nct), sheet.name, where, nct, trial))
    if sheet.name in ADDRESSED_ONLY:
        return findings, address
    grains = sheet_grains(sheet)
    placeholder = template in contract.MEASUREMENT_PLACEHOLDER_GRAINS.get(sheet.name, {})
    placeholder = placeholder and address in listing_nodes(record, sheet)
    if template not in grains and not placeholder:
        return [*findings, Finding("wrong_grain", str(nct), sheet.name, where, grains, address)], address
    group = node.get("group") if isinstance(node, dict) else None
    blank = blank_columns(sheet.name, template, node, record, indices)
    joined = _group_of(record, template, indices, node)
    for column in sheet.columns:
        if column.shows == "address" or column.header == "Trial ID":
            continue
        if column.shows == "per group":
            findings += _safety_findings(study, node, row, column, str(nct), where)
            continue
        if column.header not in row.cells:
            findings.append(Finding("column_missing", str(nct), sheet.name, column.header, None, None))
            continue
        cell = row.cells[column.header]
        want, names = _column_expected(record, sheet, column, template, indices, node, group, grains)
        if want is None:
            continue
        if isinstance(cell, Linked) and column.header == "Group" and joined is not None:
            findings += _link_findings(
                record, sheets or {}, cell, joined, indices[0], str(nct), where, sheet.name
            )
            want = Expected([t for t in want.texts if t != group], want.counts, want.words)
        verdict = judge(cell, want, column.header in blank)
        if (
            column.header == "Spread or limits"
            and len(want.texts) == 1
            and want.texts[0].endswith(": " + status_words("not_stated"))
            and not want.counts
            and not want.words
            and _plain(cell) != want.texts[0]
        ):
            verdict = "not_shown"
        findings += _scoped_display_findings(
            record, sheet.name, column.header, cell, template, indices, node, group, str(nct), where
        )
        if verdict not in ("shown", "blank_by_construction"):
            field = f"{sheet.name}: {column.header}"
            findings.append(Finding(verdict, str(nct), field, where, want.texts or want.words, _plain(cell)))
    return findings, address


def _scoped_display_findings(record, sheet, header, cell, template, indices, node, group, nct, where):
    """Check scope attachment independently of the flat field-value comparison.

    Shared constants declare display policy only. This walker selects the row's class, measure and module
    itself, and binds each count or population to its displayed label. Equal values at different scopes do
    not discharge the obligation to retain both labels.
    """
    findings = []
    text = _plain(cell)
    if not isinstance(text, str):
        return findings
    field = f"{sheet}: {header} (scope)"

    def require(words):
        if not shows_text(text, words):
            findings.append(Finding("not_shown", nct, field, where, [words], text))

    if sheet in (contract.POSTED, contract.BASELINE) and header == contract.DENOMINATOR:
        scopes = []
        for segment, scope in (
            ("classes[]", "Class"),
            ("posted_outcomes[]" if sheet == contract.POSTED else "measures[]", "Measure"),
        ):
            found, parent, _t, _i = resolve_pointer(record, _pointer(template, indices, segment))
            if found and isinstance(parent, dict):
                scopes.append((scope, parent))
        if sheet == contract.BASELINE:
            found, parent, _t, _i = resolve_pointer(record, ["studies", str(indices[0]), "baseline"])
            if found and isinstance(parent, dict):
                scopes.append(("Module", parent))
        supplied = []
        for scope, parent in scopes:
            values = []
            for denominator in parent.get("denominators") or []:
                for count in denominator.get("counts") or []:
                    if count.get("group") == group and contract.holds_value(count.get("value")):
                        values.append((count["value"], denominator.get("units")))
            if values:
                supplied.append((scope, values))
        qualifiers = [
            (scope, key, parent[key])
            for scope, parent in scopes
            for key in contract.DENOMINATOR_QUALIFIER_LABELS
            if key in parent and not is_value_object(parent[key]) and contract.holds_value(parent[key])
        ]
        for scope, key, value in qualifiers:
            require(
                contract.DENOMINATOR_QUALIFIER_FORM.format(
                    scope=scope, label=contract.DENOMINATOR_QUALIFIER_LABELS[key], value=value
                )
            )
        if len(supplied) > 1 or qualifiers:
            markers = {
                scope: contract.DENOMINATOR_SCOPE_FORM.format(scope=scope, value="")
                for scope in contract.DENOMINATOR_SCOPE_LABELS
            }
            for scope, values in supplied:
                marker = markers[scope]
                require(marker)
                if marker not in text:
                    continue
                component = text.partition(marker)[2]
                for other in markers.values():
                    if other in component:
                        component = component.partition(other)[0]
                for value, units in values:
                    if not shows_text(component, str(value)):
                        findings.append(Finding("not_shown", nct, field, where, [scope, value], component))
                    if isinstance(units, str) and units != IMPLIED_UNITS and not shows_text(component, units):
                        findings.append(Finding("not_shown", nct, field, where, [scope, units], component))
    if sheet == contract.BASELINE and header == "Population":
        found, measure, _t, _i = resolve_pointer(record, _pointer(template, indices, "measures[]"))
        module_found, module, _t, _i = resolve_pointer(record, ["studies", str(indices[0]), "baseline"])
        if found and module_found and isinstance(measure, dict) and isinstance(module, dict):
            populations = (measure.get("population"), module.get("population"))
            if all(isinstance(value, str) and contract.holds_value(value) for value in populations):
                for label, population in zip(contract.BASELINE_POPULATION_LABELS, populations, strict=True):
                    require(contract.BASELINE_POPULATION_FORM.format(label=label, value=population))
    if sheet == contract.ANALYSES and header == "Confidence interval" and isinstance(node, dict):
        policy = contract.CONFIDENCE_COMPONENT_POLICY
        if any(
            contract.holds_value(node.get(key)) and not is_value_object(node.get(key))
            for key in policy["show_when_any"]
        ):
            missing = sum(
                not contract.holds_value(node.get(key)) or is_value_object(node.get(key))
                for key in ("ci_lower", "ci_upper")
            )
            if text.count(policy["missing_bound"]) < missing:
                findings.append(
                    Finding(
                        "not_shown",
                        nct,
                        field,
                        where,
                        [f"{missing} missing bounds labelled {policy['missing_bound']}"],
                        text,
                    )
                )
    return findings


def _column_expected(record, sheet, column, template, indices, node, group, grains):
    """What a listing cell must show (None where it is not checked): the Groups sheet's own columns by
    their rule, the denominator without the participants its header implies, every other column the values
    of its fields that belong to the row."""
    if sheet.name in (contract.POSTED, contract.BASELINE) and column.header == "Spread or limits":
        parent = "posted_outcomes[]" if sheet.name == contract.POSTED else "measures[]"
        found, measure, _t, _i = resolve_pointer(record, _pointer(template, indices, parent))
        kind = measure.get("dispersion_type") if found and isinstance(measure, dict) else None
        measurement = node if template.endswith("measurements[]") and isinstance(node, dict) else {}
        values = [measurement.get(name) for name in ("spread", "lower_limit", "upper_limit")]
        present = any(contract.holds_value(value) and not is_value_object(value) for value in values)
        if isinstance(kind, str) and kind != "NA" and not present:
            field_name = (
                "studies[].posted_outcomes[].dispersion_type"
                if sheet.name == contract.POSTED
                else "studies[].baseline.measures[].dispersion_type"
            )
            label = expected(contract.FIELD_NAMES[field_name], kind).texts[0]
            return Expected([f"{label}: {status_words('not_stated')}"], [], []), column.fields
    if sheet.name == contract.BASELINE and column.header == "Population":
        found, measure, _t, _i = resolve_pointer(record, _pointer(template, indices, "measures[]"))
        module_found, module, _t, _i = resolve_pointer(record, ["studies", str(indices[0]), "baseline"])
        measure_value = measure.get("population") if found and isinstance(measure, dict) else None
        module_value = module.get("population") if module_found and isinstance(module, dict) else None
        measure_label, module_label = contract.BASELINE_POPULATION_LABELS
        if isinstance(measure_value, str):
            want = Expected(
                [contract.BASELINE_POPULATION_FORM.format(label=measure_label, value=measure_value)], [], []
            )
        else:
            status = (
                measure_value.get("status", "not_stated") if isinstance(measure_value, dict) else "not_stated"
            )
            want = Expected(
                [],
                [],
                [contract.BASELINE_POPULATION_FORM.format(label=measure_label, value=status_words(status))],
            )
        if isinstance(module_value, str):
            want = Expected(
                want.texts
                + want.words
                + [contract.BASELINE_POPULATION_FORM.format(label=module_label, value=module_value)],
                [],
                [],
            )
        return want, column.fields
    placeholders = contract.MEASUREMENT_PLACEHOLDER_GRAINS.get(sheet.name, {})
    if template in placeholders and column.header in ("Value", "Group"):
        key = "value" if column.header == "Value" else "group"
        return Expected([contract.MEASUREMENT_PLACEHOLDER_WORDS[key]], [], []), ()
    if sheet.name == contract.GROUPS and column.header == "Module":
        return NOTHING, ()
    if sheet.name == contract.GROUPS and column.header == "Column":
        if template == "studies[].adverse_events.groups[]":
            return Expected([f"G{indices[-1] + 1}"], [], []), ()
        return NOTHING, ()
    if sheet.name == contract.GROUPS and column.header == "Outcome measures" and template == POSTED_GROUPS:
        return _outcome_measures(record, indices[0], node), ()
    if sheet.name == contract.ANALYSES and column.header == "Compared groups":
        parent_tokens = _pointer(template, indices, "posted_outcomes[]")
        found, measure, _template, _indices = resolve_pointer(record, parent_tokens)
        groups = measure.get("groups") if found and isinstance(measure, dict) else []
        titles = {g.get("id"): g.get("title") for g in groups or [] if isinstance(g, dict)}
        selected = node.get("groups") if isinstance(node, dict) else []
        want = Expected([titles.get(group, group) for group in selected or []], [], [])
        for value in _row_values(
            record, "studies[].posted_outcomes[].analyses[].group_description", template, indices, group
        ):
            want = want.plus(
                expected(
                    contract.FIELD_NAMES["studies[].posted_outcomes[].analyses[].group_description"], value
                )
            )
        return want, column.fields
    names = [
        name
        for name in column.fields
        if name != "studies[].nct" and _applies(name, template, grains) and not _joins(name, template)
    ]
    want = NOTHING
    for name in names:
        for value in _row_values(record, name, template, indices, group):
            if name in DENOMINATOR_UNITS and value == IMPLIED_UNITS:
                continue
            want = want.plus(expected(contract.FIELD_NAMES[name], value))
    return want, names


def _safety_findings(study, event, row: Row, column: contract.Column, nct: str, where: str) -> list[Finding]:
    findings = []
    headers = [header for header in row.cells if SAFETY_CELL.fullmatch(header)]
    for header in headers:
        n, stat = SAFETY_CELL.fullmatch(header).groups()
        if column.header != f"G{{n}} {stat}":
            continue
        by_construction, numbers = _safety_expected(study, event, int(n), SAFETY_STAT[stat])
        words = [] if by_construction or numbers else [NOT_REPORTED]
        cell = row.cells[header]
        if numbers:
            verdict = _count_verdict(cell, numbers, by_construction)
        else:
            verdict = cell_verdict(_plain(cell), [], [], words, by_construction)
        if verdict not in ("shown", "blank_by_construction"):
            field = f"{contract.SAFETY}: {header}"
            findings.append(Finding(verdict, nct, field, where, numbers or words, _plain(cell)))
    return findings


def grain_nodes(record: dict[str, Any], grain: str) -> list[str]:
    """Every node of the record at a row grain, as a JSON pointer."""
    pointers = [("", record)]
    for segment in grain.split("."):
        name = segment.removesuffix("[]")
        following = []
        for pointer, node in pointers:
            if not isinstance(node, dict) or name not in node:
                continue
            value = node[name]
            if segment.endswith("[]"):
                items = value if isinstance(value, list) else []
                following += [(f"{pointer}/{name}/{i}", item) for i, item in enumerate(items)]
            else:
                following.append((f"{pointer}/{name}", value))
        pointers = following
    return [pointer for pointer, _node in pointers]


def listing_nodes(record: dict[str, Any], sheet: contract.Sheet) -> list[str]:
    """Actual measurement rows plus the deepest empty source nodes explicitly allowed as placeholders.

    A parent with child classes/categories never gets an additional placeholder; a node with any descendant
    measurement cannot stand in for one. This is an independent traversal of the record, not the renderer.
    """
    nodes = [pointer for grain in sheet_grains(sheet) for pointer in grain_nodes(record, grain)]
    for grain, descendants in contract.MEASUREMENT_PLACEHOLDER_GRAINS.get(sheet.name, {}).items():
        for pointer in grain_nodes(record, grain):
            found, node, _template, _indices = _resolve(record, pointer)
            if not found or not isinstance(node, dict) or grain_nodes(node, descendants):
                continue
            child = descendants.split(".")[0].removesuffix("[]")
            if child != "measurements" and isinstance(node.get(child), list) and node[child]:
                continue
            nodes.append(pointer)
    return nodes


def _empty_line(record: dict[str, Any], sheet: contract.Sheet, rows: list[Row]) -> list[Finding] | None:
    """A listing no trial has a row in is one row: the contract's words (contract.EMPTY_LISTING_WORDS) in its
    first column, every other cell blank. None where the listing is not such a line."""
    grains = sheet_grains(sheet) or EMPTY_GRAINS.get(sheet.name, ())
    if len(rows) != 1 or _plain(rows[0].cells.get(contract.ADDRESS)) is not None or not grains:
        return None
    if listing_nodes(record, sheet) or any(grain_nodes(record, grain) for grain in grains):
        return None
    cells = list(rows[0].cells.values())
    words = contract.EMPTY_LISTING_WORDS.get(sheet.name)
    where = f"{sheet.name} row 1"
    found = []
    if words is None or _plain(cells[0]) != words:
        found.append(Finding("wrong_words", "", f"{sheet.name}: empty line", where, words, _plain(cells[0])))
    if any(_plain(cell) is not None for cell in cells[1:]):
        found.append(Finding("not_blank", "", f"{sheet.name}: empty line", where, None, cells[1:]))
    return found


def _posted_group_key(record: Any, address: Any) -> tuple | None:
    found, node, template, indices = _resolve(record, address)
    if not found or template != POSTED_GROUPS or not isinstance(node, dict):
        return None
    return (indices[0], json.dumps(node.get("title")), json.dumps(node.get("description")))


def cell_findings(
    record: dict[str, Any],
    sheets: dict[str, tuple[list[str], list[list[Any]]]],
    complete: bool = True,
    whole_workbook: bool = False,
) -> list[Finding]:
    """The record → cell check over a workbook's sheets, each given as (its headers, its rows of cells): the
    listings row by row through their addresses, the Trial index trial by trial and the Trial review fact by
    fact.

    complete: every node of a listing's row grain has exactly one row (a posted-outcome group, one row per
    trial, title and description); whole_workbook: every listing the contract names is present.
    """
    findings = []
    for sheet in SHEETS:
        rows = _rows_of(sheets, sheet.name)
        if sheet.name in (contract.INDEX, contract.REVIEW):
            if rows is not None:
                check = index_findings if sheet.name == contract.INDEX else dossier_findings
                findings += check(record, sheet, rows)
            elif whole_workbook:
                findings.append(Finding("sheet_missing", "", sheet.name, "", sheet.name, None))
            continue
        grains = sheet_grains(sheet)
        if not grains and sheet.name not in ADDRESSED_ONLY:
            continue
        if rows is None:
            if whole_workbook:
                findings.append(Finding("sheet_missing", "", sheet.name, "", sheet.name, None))
            continue
        empty = _empty_line(record, sheet, rows)
        if empty is not None:
            findings += empty
            continue
        addressed: dict[Any, int] = {}
        for row in rows:
            found, address = row_findings(record, sheet, row, sheets)
            findings += found
            if address:
                key = _posted_group_key(record, address) or address
                addressed[key] = addressed.get(key, 0) + 1
        findings += [
            Finding("row_repeated", "", sheet.name, str(key), 1, count)
            for key, count in addressed.items()
            if count > 1
        ]
        if complete:
            findings += [
                Finding("row_missing", "", sheet.name, pointer, pointer, None)
                for pointer in listing_nodes(record, sheet)
                if (_posted_group_key(record, pointer) or pointer) not in addressed
            ]
    return findings


def _rows_of(sheets: dict[str, tuple[list[str], list[list[Any]]]], name: str) -> list[Row] | None:
    if name not in sheets:
        return None
    headers, cells = sheets[name]
    rows = [Row(name, n, dict(zip(headers, c, strict=False))) for n, c in enumerate(cells, 1)]
    return [row for row in rows if any(_plain(cell) is not None for cell in row.cells.values())]


# ── the Trial index and the Trial review ────────────────────────────────────────────────────────────────


def _study_by_nct(record: dict[str, Any]) -> dict[str, tuple[int, dict[str, Any]]]:
    studies = record.get("studies") or []
    return {s.get("nct"): (i, s) for i, s in enumerate(studies) if isinstance(s, dict)}


def _study_values(record: dict[str, Any], i: int, name: str) -> list[Any]:
    return _row_values(record, name, "studies[]", [i], None)


def _field_expected(record: dict[str, Any], i: int, name: str) -> Expected:
    want = NOTHING
    for value in _study_values(record, i, name):
        want = want.plus(expected(contract.FIELD_NAMES[name], value))
    return want


def _as_text(want: Expected) -> Expected:
    """Values shown inside a text cell: counts are then text too."""
    return Expected(want.texts, [], want.words)


def _index_expected(record: dict[str, Any], i: int, study: dict[str, Any], column: contract.Column):
    """What an index cell must show (contract.INDEX_COMPACT), or None where the column is not checked here."""
    header = column.header
    if header == "Trial ID":
        return None
    if header == "Dossier":
        return NOTHING
    if header == "Acronym or short title":
        name = "acronym" if isinstance(study.get("acronym"), str) else "brief_title"
        return _field_expected(record, i, f"studies[].{name}")
    if header == "Status":
        want = _field_expected(record, i, "studies[].overall_status")
        if study.get("overall_status") == "UNKNOWN":
            want = want.plus(_field_expected(record, i, "studies[].last_known_status"))
        return want
    if header == "Primary endpoint":
        primary = [o for o in study.get("registered_outcomes") or [] if isinstance(o, dict)]
        primary = [o for o in primary if o.get("category") == "primary"]
        measure = primary[0].get("measure") if primary else None
        texts = [measure] if isinstance(measure, str) else []
        return Expected(texts + ([str(len(primary) - 1)] if len(primary) > 1 else []), [], [])
    if header == "Results posted":
        state = study.get("results_posted")
        status = state.get("status") if isinstance(state, dict) else "not_stated"
        if status == "known":
            first = study.get("results_first_posted")
            return Expected([date_words(first) if isinstance(first, str) else "Yes"], [], [])
        return Expected([], [], [status_words(status)])
    if header == "Design":
        values = [study.get(name) for name in contract.INDEX_SILENT_DESIGN_FIELDS]
        silent = all(
            value is None
            or value == []
            or value == ""
            or (is_value_object(value) and value.get("status") == "not_stated")
            for value in values
        )
        if silent and study.get("study_type") == "INTERVENTIONAL":
            type_words = contract.display_words("StudyType", study["study_type"])[1]
            return Expected([contract.INDEX_SILENT_DESIGN_FORM.format(study_type=type_words)], [], [])
        direct_fields = ("primary_purpose", "allocation", "intervention_model", "masking")
        inapplicable = all(
            isinstance(study.get(name), dict)
            and study[name].get("status") == "not_stated"
            and study[name].get("note") == "not_applicable"
            for name in direct_fields
        )
        who = study.get("who_masked")
        who_supplied = contract.holds_value(who) and not is_value_object(who)
        if (
            study.get("study_type") in ("OBSERVATIONAL", "EXPANDED_ACCESS")
            and inapplicable
            and not who_supplied
        ):
            kind = contract.display_words("StudyType", study["study_type"])[1]
            return Expected([f"{kind} — interventional design fields not applicable"], [], [])
    if header == "Publications":
        references = [r for r in study.get("references") or [] if isinstance(r, dict)]
        if not references:
            return Expected([], [], [status_words("not_stated")])
        results = sum(1 for r in references if r.get("type") == "RESULT")
        return Expected([str(len(references)), str(results)], [], [])
    want = NOTHING
    for name in column.fields:
        if header == "Design":
            for value in _study_values(record, i, name):
                if (
                    is_value_object(value)
                    and value.get("status") == "not_stated"
                    and value.get("note") == "not_applicable"
                ):
                    continue
                want = want.plus(expected(contract.FIELD_NAMES[name], value))
        else:
            want = want.plus(_field_expected(record, i, name))
    return want if header == "Enrollment" else _as_text(want)


def index_findings(record: dict[str, Any], sheet: contract.Sheet, rows: list[Row]) -> list[Finding]:
    """The Trial index, one row a trial: each column against the record's values of its trial."""
    findings = []
    studies = _study_by_nct(record)
    seen = set()
    for row in rows:
        nct = _plain(row.cells.get("Trial ID"))
        where = f"{sheet.name} row {row.number}"
        findings += _raw_findings(row, str(nct), where)
        if nct not in studies:
            findings.append(Finding("trial_differs", str(nct), sheet.name, where, sorted(studies), nct))
            continue
        seen.add(nct)
        i, study = studies[nct]
        for column in sheet.columns:
            want = _index_expected(record, i, study, column)
            if want is None:
                continue
            if column.header not in row.cells:
                findings.append(Finding("column_missing", nct, sheet.name, column.header, None, None))
                continue
            cell = row.cells[column.header]
            verdict = judge(cell, want, False)
            if column.header == "Design" and isinstance(study.get("study_type"), str):
                type_words = contract.display_words("StudyType", study["study_type"])[1]
                summaries = (
                    contract.INDEX_SILENT_DESIGN_FORM.format(study_type=type_words),
                    f"{type_words} — interventional design fields not applicable",
                )
                if any(want.texts == [summary] and _plain(cell) != summary for summary in summaries):
                    verdict = "wrong_words"
            if column.header == "Enrollment" and want.counts and not isinstance(_plain(cell), (int, float)):
                verdict = "retyped"
            if verdict != "shown":
                field = f"{sheet.name}: {column.header}"
                findings.append(Finding(verdict, nct, field, where, want.texts or want.words, _plain(cell)))
    findings += [
        Finding("row_missing", nct, sheet.name, nct, nct, None) for nct in studies if nct not in seen
    ]
    return findings


DOSSIER_FIELDS = tuple(field for field in FIELDS if contract.DOSSIER in field.consumers)
NUMBERED = re.compile(r"(.+?) (\d+)")
LINE = re.compile(r"([^:\n]+): (.*)")
DOSSIER_PART = re.compile(
    re.escape(contract.DOSSIER_PART_FORM)
    .replace(re.escape("{fact}"), r"(?P<fact>.+)")
    .replace(re.escape("{part}"), r"(?P<part>\d+)")
    .replace(re.escape("{count}"), r"(?P<count>\d+)")
)


def _scalar_fields() -> dict[str, contract.Field]:
    """The dossier's facts of one value a study holds (no list below the study), by label."""
    return {f.label: f for f in DOSSIER_FIELDS if "[]" not in f.name.removeprefix("studies[].")}


def _list_fields(label: str) -> dict[str, contract.Field]:
    """For a line's label, the dossier fields of one list below the study that carry it, by their list."""
    found = {}
    for field in DOSSIER_FIELDS:
        rest = field.name.removeprefix("studies[].")
        if field.label == label and rest.count("[]") == 1:
            found[rest.split("[]")[0]] = field
    return found


def _values_expected(field: contract.Field, values: list[Any]) -> Expected:
    want = NOTHING
    for value in values:
        if field.name == "studies[].enrollment.count" and type(value) is int:
            want = want.plus(Expected([f"{value:,}"], [], []))
        else:
            want = want.plus(expected(field, value))
    return want


def _basis(field: contract.Field, values: list[Any]) -> list[str]:
    """The words the Trial review's Basis must hold for a fact (contract.BASIS_WORDS, else a status's
    words)."""
    objects = [v for v in values if is_value_object(v)]
    worded = [status_words(v.get("status")) for v in objects if v.get("status") in WORDED_STATUSES]
    if worded:
        return worded
    if objects or field.kind == "reading":
        return [contract.BASIS_WORDS["reading"]]
    return [contract.BASIS_WORDS["registry"]] if any(contract.holds_value(v) for v in values) else []


def _numbered_element(study: dict[str, Any], fact: str, labels: list[str]) -> tuple[str, Any] | None:
    """The list entry a numbered dossier fact ("Arm 2", "Primary outcome 3") shows: the list its lines'
    labels name, and its N-th entry (a registered outcome's N-th of its category)."""
    numbered = NUMBERED.fullmatch(fact)
    if numbered is None:
        return None
    prefix, n = numbered.group(1), int(numbered.group(2))
    lists = None
    for label in labels:
        named = set(_list_fields(label))
        lists = named if lists is None else lists & named
    category = next((c for c in contract.WHICH_LIST_WORDS if prefix.lower() == f"{c} outcome"), None)
    if category is not None:
        lists = {"registered_outcomes"}
    if not lists or len(lists) != 1:
        return None
    name = next(iter(lists))
    items = study.get(name)
    if not isinstance(items, list):
        return None
    if category is not None:
        items = [o for o in items if isinstance(o, dict) and o.get("category") == category]
    return (name, items[n - 1]) if 0 < n <= len(items) else (name, None)


def dossier_part_rows(rows: list[Row]) -> tuple[list[Row], list[Finding], set[int]]:
    """Join actual adjacent dossier parts in their written order, validating their declared sequence.

    This reads the workbook's labels and contents, not the writer's splitting algorithm. No whitespace is
    inserted or removed. Broken groups remain findings even if their joined text happens to contain a fact.
    """
    joined, findings, continued = [], [], set()
    seen: set[tuple[str, str, str]] = set()
    position = 0
    while position < len(rows):
        first = rows[position]
        fact = _plain(first.cells.get("Fact"))
        match = DOSSIER_PART.fullmatch(fact) if isinstance(fact, str) else None
        if match is None:
            joined.append(first)
            position += 1
            continue
        base = match["fact"]
        nct = str(_plain(first.cells.get("Trial ID")))
        section = str(_plain(first.cells.get("Section")))
        key = (nct, section, base)
        count = int(match["count"])
        group = []
        while position < len(rows):
            row = rows[position]
            named = _plain(row.cells.get("Fact"))
            part = DOSSIER_PART.fullmatch(named) if isinstance(named, str) else None
            if (
                part is None
                or (
                    str(_plain(row.cells.get("Trial ID"))),
                    str(_plain(row.cells.get("Section"))),
                    part["fact"],
                )
                != key
            ):
                break
            group.append((row, int(part["part"]), int(part["count"])))
            position += 1
        texts = [_plain(row.cells.get("Value")) for row, _, _ in group]
        first_basis = _plain(first.cells.get("Basis"))
        valid = (
            count >= 2
            and len(group) == count
            and key not in seen
            and all(
                part == i and total == count and _plain(row.cells.get("Basis")) == first_basis
                for i, (row, part, total) in enumerate(group, 1)
            )
            and all(isinstance(text, str) for text in texts)
        )
        if not valid:
            findings.append(
                Finding(
                    "continuation_invalid",
                    nct,
                    f"{first.sheet}: {base}",
                    f"{first.sheet} row {first.number}",
                    {"parts": count, "order": "1 through the declared count", "basis": first_basis},
                    [(part, total, _plain(row.cells.get("Basis"))) for row, part, total in group],
                )
            )
        seen.add(key)
        cells = dict(first.cells)
        cells["Fact"] = base
        cells["Value"] = "".join(text for text in texts if isinstance(text, str))
        joined.append(Row(first.sheet, first.number, cells))
        continued.add(first.number)
    return joined, findings, continued


def dossier_findings(record: dict[str, Any], sheet: contract.Sheet, rows: list[Row]) -> list[Finding]:
    """The Trial review, one row a fact: a fact of one value against the record's value of its label, its
    Basis in the contract's words; a numbered fact's every "Label: value" line against its list entry; and
    every fact of one value the registry holds has its row."""
    rows, findings, continued = dossier_part_rows(rows)
    studies = _study_by_nct(record)
    scalars = _scalar_fields()
    shown: dict[str, set[str]] = {}
    for row in rows:
        nct = _plain(row.cells.get("Trial ID"))
        where = f"{sheet.name} row {row.number}"
        findings += _raw_findings(row, str(nct), where)
        if nct not in studies:
            findings.append(Finding("trial_differs", str(nct), sheet.name, where, sorted(studies), nct))
            continue
        i, study = studies[nct]
        fact, value = _plain(row.cells.get("Fact")), row.cells.get("Value")
        shown.setdefault(nct, set()).add(fact)
        basis = _plain(row.cells.get("Basis"))
        if not isinstance(fact, str) or basis == contract.BASIS_WORDS["note"]:
            continue
        if fact in scalars:
            field = scalars[fact]
            values = _study_values(record, i, field.name)
            want = _values_expected(field, values)
            verdict = judge(value, want, False)
            if (
                row.number in continued
                and field.kind == "plain"
                and not field.display
                and field.name not in DATE_FIELDS | {"studies[].lead_sponsor.name"}
                and len(values) == 1
                and isinstance(values[0], str)
            ):
                exact = values[0] + ("\n[End of field]" if "\n\n" in values[0] else "")
                if _plain(value) != exact:
                    verdict = "not_shown"
            if verdict != "shown":
                field_name = f"{sheet.name}: {fact}"
                findings.append(
                    Finding(verdict, nct, field_name, where, want.texts or want.words, _plain(value))
                )
            wanted = _basis(field, values)
            if wanted and basis not in wanted:
                findings.append(
                    Finding("wrong_words", nct, f"{sheet.name}: {fact} (basis)", where, wanted, basis)
                )
            continue
        text = _plain(value)
        if not isinstance(text, str):
            continue
        labelled = []
        for line in text.split("\n"):
            match = LINE.fullmatch(line)
            if match is not None and _list_fields(match.group(1)):
                labelled.append((match.group(1), match.group(2)))
            elif labelled and line != "[End of field]":
                label, previous = labelled.pop()
                labelled.append((label, previous + "\n" + line))
        entry = _numbered_element(study, fact, [label for label, _text in labelled if _list_fields(label)])
        if entry is None:
            continue
        name, element = entry
        for label, line in labelled:
            field = _list_fields(label).get(name)
            if field is None or element is None:
                continue
            rest = field.name.removeprefix(f"studies[].{name}[].")
            values = _row_values(element, rest, "", [], None)
            want = _values_expected(field, values)
            verdict = judge(line, _as_text(want), False)
            if (
                row.number in continued
                and field.kind == "plain"
                and not field.display
                and field.name not in DATE_FIELDS
                and len(values) == 1
                and isinstance(values[0], str)
                and line != values[0]
            ):
                verdict = "not_shown"
            if verdict != "shown":
                field_name = f"{sheet.name}: {fact}: {label}"
                findings.append(Finding(verdict, nct, field_name, where, want.texts or want.words, line))
    for nct, (i, _study) in studies.items():
        composites: set[str] = set()
        for label, field in scalars.items():
            parent = field.name.rpartition(".")[0]
            if parent in composites or field.kind != "plain":
                continue
            if parent != "studies[]":
                composites.add(parent)
            held = [
                v
                for v in _study_values(record, i, field.name)
                if contract.holds_value(v) and not is_value_object(v)
            ]
            if held and label not in shown.get(nct, set()):
                findings.append(Finding("fact_missing", nct, f"{sheet.name}: {label}", nct, held, None))
    return findings


# ── the shells: a workbook read back, a run folder's files ─────────────────────────────────────────────

LOCATION = re.compile(r"#?'?(?P<sheet>[^'!]+)'?!\$?[A-Z]+\$?(?P<row>\d+)")


def workbook_sheets(path: Path) -> dict[str, tuple[list[str], list[list[Any]]]]:
    """A workbook's sheets as (headers, rows): a number cell as a Number with its format, a cell linking
    inside the workbook as a Linked to the sheet and data row it points at. The header row is the first that
    names the address column or begins with the Trial ID; a listing's continuation sheets ("Safety (2)",
    "Safety 2") are read on after it."""
    from openpyxl import load_workbook

    book = load_workbook(path, data_only=True)
    raw: dict[str, list[tuple[str, int, list[Any]]]] = {}
    names = {sheet.name for sheet in SHEETS}
    for worksheet in book.worksheets:
        base = re.sub(r"\s*(\(\d+\)|\d+)$", "", worksheet.title)
        if base not in names:
            continue
        rows = [list(row) for row in worksheet.iter_rows()]
        values = [[cell.value for cell in row] for row in rows]
        start = next(
            (i for i, row in enumerate(values) if contract.ADDRESS in row or (row and row[0] == "Trial ID")),
            None,
        )
        if start is None:
            continue
        raw.setdefault(base, []).append((worksheet.title, start, rows))
    # a sheet's data rows numbered across its continuation sheets, to read each link's target row
    offsets: dict[str, tuple[str, int]] = {}
    for base, parts in raw.items():
        count = 0
        for title, start, rows in parts:
            offsets[title] = (base, count - (start + 1))
            count += len(rows) - start - 1
    sheets: dict[str, tuple[list[str], list[list[Any]]]] = {}
    for base, parts in raw.items():
        for _title, start, rows in parts:
            headers = [str(cell.value) if cell.value is not None else "" for cell in rows[start]]
            held = sheets.setdefault(base, (headers, []))
            held[1].extend([[_read_cell(cell, offsets) for cell in row] for row in rows[start + 1 :]])
    book.close()
    return sheets


def _read_cell(cell: Any, offsets: dict[str, tuple[str, int]]) -> Any:
    value = getattr(cell, "value", None)
    link = getattr(cell, "hyperlink", None)
    location = getattr(link, "location", None) if link is not None else None
    if isinstance(location, str):
        found = LOCATION.fullmatch(location)
        if found is not None and found.group("sheet") in offsets:
            base, offset = offsets[found.group("sheet")]
            return Linked(value, base, int(found.group("row")) + offset)
        return Linked(value, location, 0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Number(value, getattr(cell, "number_format", "General") or "General")
    return value


def bodies_in(paths: list[Path]) -> dict[str, dict[str, Any]]:
    """The registry's study bodies in saved JSON files (an API page `{"studies": [...]}` or one study), by NCT
    number."""
    bodies = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        studies = data.get("studies", [data]) if isinstance(data, dict) else []
        for study in studies:
            if isinstance(study, dict) and "protocolSection" in study:
                nct = study["protocolSection"].get("identificationModule", {}).get("nctId")
                bodies[nct] = study
    return bodies


def check_run(
    bodies: dict[str, dict[str, Any]],
    record_path: Path,
    workbook_path: Path | None = None,
    complete: bool = True,
) -> list[Finding]:
    """Registry → record → cell for a run: landscape.json against the bodies, and landscape.xlsx (when given)
    against landscape.json."""
    record = json.loads(record_path.read_text(encoding="utf-8"))
    findings = record_findings(bodies, record, complete)
    if workbook_path is not None:
        findings += cell_findings(record, workbook_sheets(workbook_path), complete, whole_workbook=True)
    return findings
