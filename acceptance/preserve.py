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
  are blank only past the trial's last group.

Two depths. A complete record (a run's output) must carry every value the registry holds. An excerpt (the
contract's worked examples, cut from the bodies by hand) is held to what it carries: every value it holds must
be the registry's, and a field it carries somewhere must be carried at every node it holds.

Each disagreement is a named finding (FINDING_WORDS). The decisions are pure, over literal values, beside the
shells that walk the JSON and read the workbook.
"""

from __future__ import annotations

import json
import re
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
ADDRESSED_ONLY = (contract.BIOMARKERS, contract.READINGS, contract.FINDINGS)
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
    "not_shown": "the cell does not show the record's value exactly",
}


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


def cell_verdict(cell: Any, texts: list[str], numbers: list[Any], worded: bool, by_construction: bool) -> str:
    """What a displayed cell shows of the record's values (pure — pinned).

    cell            — the cell as read back: None (blank), text, or a number;
    texts           — the record's values the cell must show as text (codes already in their words);
    numbers         — the record's numbers the cell must hold exactly (the Safety counts);
    worded          — whether the record states an absence or a reading here (a status object), which the
                      cell shows in words;
    by_construction — whether the column cannot apply to the row (a group past the trial's last).
    Codes: shown; blank_by_construction; not_blank; blank (a value to show, none shown); unexplained_blank
    (nothing to show, yet an absence must be worded); retyped; number_differs; not_shown.
    """
    blank = cell is None or (isinstance(cell, str) and not cell.strip())
    if by_construction:
        return "blank_by_construction" if blank else "not_blank"
    if blank:
        return "blank" if texts or numbers else "unexplained_blank"
    is_number = isinstance(cell, (int, float)) and not isinstance(cell, bool)
    if numbers:
        if not is_number:
            return "retyped" if any(cell == str(number) for number in numbers) else "number_differs"
        return "shown" if any(same_value(cell, number) for number in numbers) else "number_differs"
    if not isinstance(cell, str):
        return "retyped" if any(str(cell) == text for text in texts) else "not_shown"
    if all(shows_text(cell, text) for text in texts):
        return "shown"
    return "not_shown"


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
        found = {(places.get(key[0], key[0]), *key[1:]): value for key, value in found.items()}
        parents = {(places.get(key[0], key[0]), *key[1:]) for key in parents}
    return found, parents


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


class Row(NamedTuple):
    """A listing row read back: its sheet, its number in the sheet, and its cells by header."""

    sheet: str
    number: int
    cells: dict[str, Any]


def resolve_pointer(record: Any, tokens: list[str]) -> tuple[bool, Any, str, list[int]]:
    """A pointer's node in the record: whether found, the node, its path template and its list indices."""
    node = record
    template: list[str] = []
    indices: list[int] = []
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
            template.append(token)
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
            template[-1] += "[]"
            indices.append(int(token))
        else:
            return False, None, "", []
    return True, node, ".".join(template), indices


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
        if grain == row_template:
            continue
        branch = ".".join(field[: len(grain.split("."))])
        if branch == grain and not row_template.startswith(grain):
            return False
    return True


def _row_values(record: dict[str, Any], field_name: str, row_template: str, indices: list[int], group: Any):
    """The values of a field for a row: the row's own entries along its path, every entry below it (only the
    row's group's, where entries name a group)."""
    nodes = [record]
    path: list[str] = []
    used = 0
    for segment in field_name.split("."):
        name = segment.removesuffix("[]")
        path.append(segment)
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
            items = value if isinstance(value, list) else []
            prefix = ".".join(path)
            if row_template == prefix or row_template.startswith(prefix + "."):
                following += [items[indices[used]]] if indices[used] < len(items) else []
            else:
                following += [item for item in items if _in_group(item, group)]
        if segment.endswith("[]") and (
            row_template == ".".join(path) or row_template.startswith(".".join(path) + ".")
        ):
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


def _texts(field: contract.Field, value: Any) -> list[str]:
    """A record value as the text a cell shows: codes in their words, a list's every entry."""
    if isinstance(value, list):
        return [text for item in value for text in _texts(field, item)]
    if field.form == "which list" and isinstance(value, str):
        return [WHICH_LIST_WORDS.get(value, value)]
    if field.display and isinstance(value, str):
        return [contract.display_words(field.display, value)[1]]
    if isinstance(value, bool):
        return ["Yes" if value else "No"]
    if isinstance(value, (str, int, float)):
        return [str(value)]
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


def row_findings(record: dict[str, Any], sheet: contract.Sheet, row: Row) -> tuple[list[Finding], str]:
    """One listing row against the record: its address, its trial and every column; and the node it shows."""
    where = f"{sheet.name} row {row.number}"
    address = row.cells.get(contract.ADDRESS)
    code, tokens = pointer_steps(address) if isinstance(address, str) else ("not_a_pointer", [])
    if code != "ok":
        return [Finding("address_unreadable", "", sheet.name, where, None, address)], ""
    found, node, template, indices = resolve_pointer(record, tokens)
    if not found:
        return [Finding("address_unresolved", "", sheet.name, where, None, address)], ""
    studies = record.get("studies") or []
    study = studies[indices[0]] if template.startswith("studies[]") and indices else {}
    nct = study.get("nct") if isinstance(study, dict) else None
    findings = []
    if "Trial ID" in row.cells and not (isinstance(nct, str) and shows_text(str(row.cells["Trial ID"]), nct)):
        findings.append(Finding("trial_differs", str(nct), sheet.name, where, nct, row.cells.get("Trial ID")))
    if sheet.name in ADDRESSED_ONLY:
        return findings, address
    grains = LISTING_GRAINS[sheet.name]
    if template not in grains:
        return [*findings, Finding("wrong_grain", str(nct), sheet.name, where, grains, address)], address
    group = node.get("group") if isinstance(node, dict) else None
    for column in sheet.columns:
        if column.shows == "address" or column.header == "Trial ID":
            continue
        if column.shows == "per group":
            findings += _safety_findings(study, node, row, column, str(nct), where)
            continue
        if column.header not in row.cells:
            findings.append(Finding("column_missing", str(nct), sheet.name, column.header, None, None))
            continue
        texts, worded = (
            _groups_column(column.header, template, indices) if sheet.name == contract.GROUPS else ([], False)
        )
        if texts is None:
            continue
        for name in column.fields if sheet.name != contract.GROUPS or column.header not in GROUPS_OWN else ():
            if name == "studies[].nct" or not _applies(name, template, grains) or _joins(name, template):
                continue
            for value in _row_values(record, name, template, indices, group):
                worded = worded or is_value_object(value)
                texts += _texts(contract.FIELD_NAMES[name], value)
        verdict = cell_verdict(row.cells[column.header], list(dict.fromkeys(texts)), [], worded, False)
        if verdict != "shown":
            findings.append(
                Finding(
                    verdict,
                    str(nct),
                    f"{sheet.name}: {column.header}",
                    where,
                    texts,
                    row.cells[column.header],
                )
            )
    return findings, address


def _groups_column(header: str, template: str, indices: list[int]) -> tuple[list[str] | None, bool]:
    """The Groups sheet's own columns: Module shows the module in words the contract does not fix (any words);
    Column names an adverse-event group's Safety columns, G1 ... Gn by its place, and is not fixed for the
    other modules (not checked: None). Other columns: their fields, as for any listing."""
    if header == "Module":
        return [], True
    if header == "Column":
        if template == "studies[].adverse_events.groups[]":
            return [f"G{indices[-1] + 1}"], False
        return None, False
    return [], False


def _safety_findings(study, event, row: Row, column: contract.Column, nct: str, where: str) -> list[Finding]:
    findings = []
    headers = [header for header in row.cells if SAFETY_CELL.fullmatch(header)]
    for header in headers:
        n, stat = SAFETY_CELL.fullmatch(header).groups()
        if column.header != f"G{{n}} {stat}":
            continue
        by_construction, numbers = _safety_expected(study, event, int(n), SAFETY_STAT[stat])
        texts = [] if by_construction or numbers else [NOT_REPORTED]
        verdict = cell_verdict(row.cells[header], texts, numbers, False, by_construction)
        if verdict not in ("shown", "blank_by_construction"):
            findings.append(
                Finding(
                    verdict, nct, f"{contract.SAFETY}: {header}", where, numbers or texts, row.cells[header]
                )
            )
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


def cell_findings(
    record: dict[str, Any],
    sheets: dict[str, tuple[list[str], list[list[Any]]]],
    complete: bool = True,
    whole_workbook: bool = False,
) -> list[Finding]:
    """The record → cell check over a workbook's listings, each given as (its headers, its rows of cells).

    complete: every node of a listing's row grain has exactly one row; whole_workbook: every listing the
    contract names is present (a workbook read back, not listings given one by one).
    """
    findings = []
    for sheet in SHEETS:
        if sheet.name not in LISTING_GRAINS and sheet.name not in ADDRESSED_ONLY:
            continue
        if sheet.name not in sheets:
            if whole_workbook:
                findings.append(Finding("sheet_missing", "", sheet.name, "", sheet.name, None))
            continue
        headers, rows = sheets[sheet.name]
        addressed: dict[str, int] = {}
        for number, cells in enumerate(rows, start=1):
            row = Row(sheet.name, number, dict(zip(headers, cells, strict=False)))
            found, address = row_findings(record, sheet, row)
            findings += found
            if address:
                addressed[address] = addressed.get(address, 0) + 1
        findings += [
            Finding("row_repeated", "", sheet.name, address, 1, count)
            for address, count in addressed.items()
            if count > 1
        ]
        if complete and sheet.name in LISTING_GRAINS:
            for grain in LISTING_GRAINS[sheet.name]:
                findings += [
                    Finding("row_missing", "", sheet.name, pointer, pointer, None)
                    for pointer in grain_nodes(record, grain)
                    if pointer not in addressed
                ]
    return findings


# ── the shells: a workbook read back, a run folder's files ─────────────────────────────────────────────


def workbook_sheets(path: Path) -> dict[str, tuple[list[str], list[list[Any]]]]:
    """A workbook's listings as (headers, rows): the header row is the first that names the address column
    (or the Trial ID, for a sheet without one), and a listing's continuation sheets ("Safety (2)", "Safety 2")
    are read on after it."""
    from openpyxl import load_workbook

    book = load_workbook(path, read_only=True, data_only=True)
    sheets: dict[str, tuple[list[str], list[list[Any]]]] = {}
    names = {sheet.name for sheet in SHEETS}
    for worksheet in book.worksheets:
        title = worksheet.title
        base = re.sub(r"\s*(\(\d+\)|\d+)$", "", title)
        if base not in names:
            continue
        rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
        start = next(
            (i for i, row in enumerate(rows) if contract.ADDRESS in row or "Trial ID" in row),
            None,
        )
        if start is None:
            continue
        headers = [str(cell) if cell is not None else "" for cell in rows[start]]
        held = sheets.setdefault(base, (headers, []))
        held[1].extend(rows[start + 1 :])
    book.close()
    return sheets


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
