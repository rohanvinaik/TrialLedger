"""Separate, reproducible clinical handoffs over immutable reasoning artifacts.

This is an I/O renderer, not another admission, inference or recommendation path.
The shared clinical projection owns finding semantics. Original request/response
bytes and an optional source workbook remain alongside the human-readable views.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from TrialLedger import reasoning_artifacts
from TrialLedger.baseline_view import baseline_tables, group_code
from TrialLedger.cells import cell_number_state, cell_text_state
from TrialLedger.landscape_verify import strict_json
from TrialLedger.layer2.clinical_answers import project
from TrialLedger.layer2.session_state import canonical

DECISION_WORDS = {
    "design_choice": "Open design choice",
    "evidence_question": "More evidence is needed",
    "translation_question": "Clarify the represented wording or scope",
    "computation_task": "Calculation remains open",
    "blocker": "A conflict needs resolving",
    "chosen_by_person": "Recorded clinical choice",
    "chosen_with_open_checks": "Recorded choice with open checks",
    "settled_within_declared_alternatives": "Settled within the declared alternatives",
    "options_not_distinguished": "The declared options are not distinguished",
}
LOGICAL_WORDS = {
    "ENTAILED": "Follows from the represented criteria",
    "REFUTED": "Ruled out by the represented criteria",
    "INCONSISTENT": "The represented criteria contradict each other",
    "UNDETERMINED": "Not determined by the represented criteria",
    "OUT_OF_SCOPE": "The represented criteria address another scope",
    "UNSUPPORTED_QUERY": "The question needs a supported representation",
}
OPTION_WORDS = {
    "feasible": "Compatible with the represented restrictions",
    "infeasible": "Ruled out under the represented restrictions",
    "conflict": "The represented criteria conflict",
    "target_mismatch": "This check concerns a different target",
    "translation_question": "Clarify the represented wording or scope",
    "computation_task": "Calculation remains open",
    "evidence_question": "More evidence is needed",
}
BLOCKER_WORDS = {
    "undecided_by_constraints": "Both sides remain possible under the represented restrictions",
    "no_constraint_mentions_query": "No represented restriction addresses this question",
    "resource_bound": "Not resolved within the computation limit",
    "unresolved_rule": "The deciding rule is not fully stated",
    "unresolved_assertion": "A premise is not fully stated",
    "unresolved_scope": "The applicable population, arm or time is not settled",
    "unresolved_literal": "The proposition is not fully stated",
    "unspecified_boundary": "The limit's inclusivity is not stated",
    "opaque": "A premise needs a supported representation",
}
CHANGE_WORDS = {
    "answer_changed": "Clinical answer changed",
    "support_changed": "Supporting warrant changed",
    "origin_changed": "Attributed origin changed",
    "input_only": "Inputs changed; clinical answer, support and origin stayed the same",
    "unchanged": "No change",
    "new": "New item",
    "withdrawn": "Withdrawn item",
    "projection_unknown": "Comparison not available",
}


class ExportError(ValueError):
    """A named delivery refusal, never a clinical finding."""


def text_display_code(text: object) -> str:
    """A cell either holds the exact text or names its complete retained value.

    post: __return__ in ('invalid_text', 'reference_required', 'literal_text')
    """
    if not isinstance(text, str):
        return "invalid_text"
    if cell_text_state(text.replace("\r", "\n")) != "ok":
        return "reference_required"
    return "literal_text"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _cell(value: object, reference: str) -> object:
    """Prepare a literal cell without silently losing precision or long source text."""
    if isinstance(value, str):
        text = value if value else '""'
    elif value is None:
        text = "null"
    elif isinstance(value, int | float) and cell_number_state(value) == "ok":
        return value
    else:
        text = _json(value)
    if text_display_code(text) == "reference_required":
        return f"Full value retained at {reference}"
    return text


def _write(sheet, values: Sequence[object], reference: str) -> None:
    """Formula-like source strings are always strings, including leading equals."""
    if sheet.max_row >= 1048576 or len(values) > 16384:
        raise ExportError("export_exceeds_workbook_dimensions")
    sheet.append([_cell(value, reference) for value in values])
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"
            if reference and (cell.value == reference or cell.value.startswith("Full value retained at ")):
                cell.hyperlink = reference
        cell.alignment = Alignment(vertical="top", wrap_text=True)


def _sheet(book: Workbook, name: str, headers: list[str]):
    sheet = book.create_sheet(name)
    _write(sheet, headers, "")
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="17384A")
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    return sheet


def _finish(sheet) -> None:
    if sheet.title != "Baseline tables":
        sheet.auto_filter.ref = sheet.dimensions
    sheet.print_title_rows = "1:1"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if cell.hyperlink and cell.value == cell.hyperlink.target:
                cell.value = (
                    "Open exact source"
                    if cell.hyperlink.target.startswith("landscape.json#")
                    else "Open exact result"
                )
    for column in sheet.columns:
        size = max(len(str(cell.value or "").split("\n")[0]) for cell in column)
        sheet.column_dimensions[get_column_letter(column[0].column)].width = min(65, max(16, size + 2))
    for row in sheet.iter_rows(min_row=2):
        lines = 1
        for cell in row:
            cell.font = Font(
                name="Calibri",
                size=11,
                color="0563C1" if cell.hyperlink else "17384A",
                underline="single" if cell.hyperlink else None,
            )
            width = sheet.column_dimensions[cell.column_letter].width
            lines = max(
                lines,
                sum(max(1, math.ceil(len(part) / max(1, width - 2))) for part in str(cell.value).split("\n")),
            )
        ceiling = {
            "Options": 64,
            "Findings": 64,
            "Changes": 56,
            "Sources and origins": 64,
            "Baseline values": 56,
            "Decision list": 96,
        }.get(sheet.title, 120)
        sheet.row_dimensions[row[0].row].height = min(ceiling, max(28, lines * 14))


def _artifact(store: Path, identity: str) -> tuple[dict, bytes]:
    payload = reasoning_artifacts.load(store, identity)
    body = (store / f"{identity}.json").read_bytes()
    if _sha(body) != identity:
        raise ExportError("artifact_changed_during_export")
    return payload, body


def _reference(identity: str, address: str = "") -> str:
    return f"artifacts/{identity}.json#{address}"


def _projection(response: dict) -> dict:
    """Use the existing semantic owner, including for older retained envelopes."""
    return project(response.get("operation", ""), response.get("result"), response.get("problems", ()))


def _word(code: object, glossary: dict[str, str]) -> str:
    """Translate an existing code; unknown codes remain explicitly unclassified."""
    return f"{glossary.get(str(code), 'Unclassified')} ({code})"


def option_wording_code(feasibility: str, result: str, blockers: list[str]) -> str:
    """Only the existing complete feasibility outcome warrants the permission wording.

    post: __return__ in ('allowed_not_required', 'use_logical_code')
    post: __return__ != 'allowed_not_required' or feasibility == 'feasible'
    post: __return__ != 'allowed_not_required' or result == 'UNDETERMINED'
    post: __return__ != 'allowed_not_required' or blockers == ['undecided_by_constraints']
    """
    if feasibility == "feasible" and result == "UNDETERMINED" and blockers == ["undecided_by_constraints"]:
        return "allowed_not_required"
    return "use_logical_code"


def _logical_text(option: dict) -> str:
    warrant = option.get("warrant") or {}
    code = option_wording_code(option.get("code", ""), warrant.get("result", ""), warrant.get("blockers", []))
    if code == "allowed_not_required":
        return (
            "The represented proposition is allowed but not required under these restrictions (UNDETERMINED)"
        )
    return _word(warrant.get("result"), LOGICAL_WORDS)


def _blocker_text(codes: list) -> str:
    parts = []
    for code in codes:
        if isinstance(code, str) and code.startswith("proposed_refused:"):
            words = "This reading has not been confirmed"
        elif isinstance(code, str) and code.startswith("open_scope:"):
            words = "Which cohort, arm or phase applies remains open"
        elif isinstance(code, str) and code.startswith("conflicting:"):
            words = "The criterion has conflicting readings"
        else:
            words = BLOCKER_WORDS.get(str(code), "Unclassified open item")
        parts.append(f"{words} ({code})")
    return "; ".join(parts) if parts else "No blocker reported"


def _origin_text(origin: object) -> str:
    """Describe caller provenance without certifying an exchange or source truth."""
    if not isinstance(origin, dict):
        return "Origin not stated"
    kind = origin.get("kind")
    label = {
        "user_choice": "Caller-declared clinical choice",
        "computed": "Computed from declared premises",
        "source": "Retained source",
        "hypothetical": "Hypothetical premise",
    }.get(kind, f"Declared origin ({kind})")
    refs = [origin["ref"]] if isinstance(origin.get("ref"), str) else []
    refs.extend(value for value in origin.get("basis", []) if isinstance(value, str))
    for value in origin.get("refs", []):
        if isinstance(value, dict):
            nested = value.get("origin", {})
            if isinstance(nested, dict) and isinstance(nested.get("ref"), str):
                refs.append(nested["ref"])
    return label + (": " + "; ".join(dict.fromkeys(refs)) if refs else "")


def _decision_rows(book: Workbook, payload: dict, identity: str) -> list[str]:
    result = payload["response"].get("result")
    result = result if isinstance(result, dict) else {}
    decisions = result.get("decisions", [])
    decisions = decisions if isinstance(decisions, list) else []
    findings = {row["path"]: row for row in _projection(payload["response"])["findings"]}
    sheet = _sheet(
        book,
        "Decision list",
        [
            "Decision",
            "Current result",
            "Selected option",
            "What decides it",
            "Open items",
            "Origin",
            "Coverage",
            "Exact result",
        ],
    )
    options = _sheet(
        book,
        "Options",
        [
            "Decision",
            "Option",
            "Computed feasibility",
            "Logical answer",
            "Standing",
            "Deciding premises",
            "Open items",
            "Query",
            "Origin",
            "Exact result",
        ],
    )
    lines = [
        "# Clinical design decision list",
        "",
        f"Session: {result.get('session_id', 'Not a managed session')}",
        f"Revision: {result.get('revision', 'Not stated')}",
        "",
        "Only the represented restrictions are checked. Caller origin labels record declarations, "
        "not authenticated confirmation.",
        "",
    ]
    for i, decision in enumerate(decisions):
        path = f"/result/decisions/{i}"
        ref = _reference(identity, "/response" + path)
        finding = findings.get(path, {})
        selected = decision.get("selected")
        selected_label = selected.get("alternative") if isinstance(selected, dict) else "Open"
        selected_label = next(
            (
                option["label"]
                for option in decision.get("alternatives", [])
                if option.get("id") == selected_label
            ),
            selected_label,
        )
        outcome = _word(finding.get("outcome", decision.get("code")), DECISION_WORDS)
        origin = _origin_text(decision.get("origin"))
        _write(
            sheet,
            [
                decision.get("question"),
                outcome,
                selected_label,
                {
                    key: value
                    for key, value in finding.get("support", {}).items()
                    if key in ("determining_alternatives", "determining_distinctions")
                },
                _blocker_text(finding.get("blockers", [])),
                origin,
                decision.get("coverage_limit", decision.get("coverage")),
                ref,
            ],
            ref,
        )
        lines.extend(
            [
                f"## {decision.get('question', decision.get('id', 'Decision'))}",
                "",
                f"Current result: {outcome}. Selected option: {selected_label}.",
                "",
            ]
        )
        for j, option in enumerate(decision.get("alternatives", [])):
            warrant = option.get("warrant") or {}
            option_ref = f"{ref}/alternatives/{j}"
            _write(
                options,
                [
                    decision.get("question"),
                    option.get("label"),
                    _word(option.get("code"), OPTION_WORDS),
                    _logical_text(option),
                    warrant.get("status"),
                    warrant.get("proof", []),
                    _blocker_text(warrant.get("blockers", [])),
                    option.get("query"),
                    option.get("origin_refs", []),
                    option_ref,
                ],
                option_ref,
            )
            lines.extend(
                [
                    f"- {option.get('label', option.get('id'))}: {_logical_text(option)}. "
                    f"Feasibility: {_word(option.get('code'), OPTION_WORDS)}. "
                    f"Deciding premises: {_json(warrant.get('proof', []))}. "
                    f"Open items: {_blocker_text(warrant.get('blockers', []))}."
                ]
            )
        lines.extend(
            [
                "",
                f"Origin: {origin}",
                f"Coverage: {decision.get('coverage_limit', decision.get('coverage', 'Not stated'))}",
                f"Exact result: `{ref}`",
                "",
            ]
        )
    if not decisions:
        lines.extend(
            [
                "No decision entries were declared. See the workbook's Findings "
                "and the retained complete result.",
                "",
            ]
        )
    return lines


def _findings(book: Workbook, payloads: list[tuple[str, dict]]) -> None:
    sheet = _sheet(
        book,
        "Findings",
        [
            "Analysis",
            "Operation",
            "Result",
            "Standing",
            "Disposition",
            "Completion",
            "Scope and question",
            "Reported values",
            "Necessary conditions",
            "What decides it",
            "Origin",
            "Open items",
            "Exact result",
        ],
    )
    for index, (identity, payload) in enumerate(payloads):
        response = payload["response"]
        for finding in _projection(response)["findings"]:
            ref = _reference(identity, "/response" + finding["canonical_ref"])
            _write(
                sheet,
                [
                    "Main" if index == 0 else "Related analysis",
                    response.get("operation"),
                    finding["outcome"],
                    finding["standing"],
                    finding["disposition"],
                    finding["completion"],
                    finding["scope"],
                    finding["values"],
                    finding["conditions"],
                    finding["support"],
                    finding["origins"],
                    finding["blockers"],
                    ref,
                ],
                ref,
            )


def _changes(book: Workbook, payload: dict, identity: str) -> list[str]:
    sheet = _sheet(
        book,
        "Changes",
        ["Type", "Item", "Change", "Answer", "Support", "Origin", "Before", "After", "Exact comparison"],
    )
    difference = payload["response"].get("answer_diff")
    if not isinstance(difference, dict):
        return []
    lines = ["## Changes from the previous revision", ""]
    for kind in ("analyses", "decisions"):
        for index, item in enumerate(difference.get(kind, [])):
            axes = item.get("axes", {})
            ref = _reference(identity, f"/response/answer_diff/{kind}/{index}")
            _write(
                sheet,
                [
                    kind,
                    item.get("id"),
                    _word(item.get("code"), CHANGE_WORDS),
                    axes.get("answer"),
                    axes.get("support"),
                    axes.get("origin"),
                    "Open previous answer",
                    "Open current answer",
                    ref,
                ],
                ref,
            )
            for column, field in ((7, "before_path"), (8, "after_path")):
                address = item.get(field)
                if isinstance(address, str) and address.startswith("/"):
                    sheet.cell(sheet.max_row, column).hyperlink = _reference(identity, "/response" + address)
                else:
                    sheet.cell(sheet.max_row, column).value = "See exact comparison"
            lines.append(
                f"- {item.get('id')}: {_word(item.get('code'), CHANGE_WORDS)}. Answer: {axes.get('answer')}. "
                f"Support: {axes.get('support')}. Origin: {axes.get('origin')}."
            )
    return [*lines, ""]


def _sources(book: Workbook, payloads: list[tuple[str, dict]]) -> None:
    sheet = _sheet(
        book,
        "Sources and origins",
        ["Analysis", "Type", "Identity", "Origin or source snapshot", "Payload", "Exact reference"],
    )
    for identity, payload in payloads:
        result = payload["response"].get("result")
        if not isinstance(result, dict):
            continue
        for collection, kind in (
            ("sources", "Source snapshot"),
            ("premises", "Declared premise"),
            ("effective_premises", "Effective premise"),
        ):
            if collection not in result:
                continue
            container = result[collection]
            items = list(enumerate(container)) if isinstance(container, list) else [(None, container)]
            for index, item in items:
                address = f"/response/result/{collection}" + (f"/{index}" if index is not None else "")
                ref = _reference(identity, address)
                label = item.get("id") if isinstance(item, dict) else "No declared id"
                origin = item.get("origin", item.get("snapshot")) if isinstance(item, dict) else None
                _write(
                    sheet,
                    [identity, kind if index is not None else f"{kind} container", label, origin, item, ref],
                    ref,
                )


def _comparative_table(sheet, table: dict) -> None:
    """Lay out exact local groups beside each other without joining or aggregating."""
    ref = f"landscape.json#{table['source']}"
    identities = [group["id"] for group in table["groups"]]
    groups = [group for group in table["groups"] if group_code(group["id"], identities) == "unique"]
    _write(sheet, ["Trial", table["trial"], "Measure", table["title"], "Exact source", ref], ref)
    populations = {
        key: {"present": field["present"], "value": field["value"]}
        for key, field in table["population"].items()
    }
    statistic = {
        key: table["measure"][key]
        for key in ("unit", "param_type", "dispersion_type")
        if key in table["measure"]
    }
    _write(sheet, ["Source populations", populations, "Unit and statistic", statistic], ref)
    denominators = [
        {
            "id": group["id"],
            "title": group["title"],
            "denominators": [
                {key: count[key] for key in ("scope", "value", "units")} for count in group["denominators"]
            ],
        }
        for group in table["groups"]
    ]
    _write(sheet, ["Group denominators", denominators], ref)
    _write(
        sheet,
        [
            "Class",
            "Category",
            *[f"{group['title']} [{group['id']}]" for group in groups],
            "Values without a unique group",
            "Exact source",
        ],
        ref,
    )
    for cell in sheet[sheet.max_row]:
        cell.fill = PatternFill("solid", fgColor="E1EBF0")
        cell.font = Font(name="Calibri", size=11, bold=True, color="17384A")
    for row in table["rows"]:
        copied = []
        for group in groups:
            matching = [
                value
                for value in row["values"]
                if value["group_code"] == "unique" and value["group"] == group["id"]
            ]
            if len(matching) == 1:
                copied.append(matching[0]["measurement"].get("value", "Not stated"))
            elif matching:
                copied.append(matching)
            else:
                copied.append("Not listed for this category")
        unresolved = [value for value in row["values"] if value["group_code"] != "unique"]
        row_ref = f"landscape.json#{row['source']}"
        _write(
            sheet,
            [
                row["class"].get("title", "Not stated"),
                row["category"].get("title", "Not stated"),
                *copied,
                unresolved,
                row_ref,
            ],
            row_ref,
        )
    if not table["rows"]:
        _write(sheet, ["Availability", table.get("availability", {"rows": "not listed"})], ref)
    _write(sheet, ["End of measure", table["title"]], ref)


def _baseline(book: Workbook, record: dict) -> None:
    values = _sheet(
        book,
        "Baseline values",
        [
            "Trial",
            "Measure",
            "Class",
            "Category",
            "Group id",
            "Group resolution",
            "Value",
            "Unit",
            "Parameter",
            "Dispersion",
            "Population",
            "All matching denominators",
            "Measurement metadata",
            "Exact source",
        ],
    )
    comparative = _sheet(
        book,
        "Baseline tables",
        ["Baseline comparison", "Source groups stay separate. Every value is also in Baseline values."],
    )
    for table in baseline_tables(record):
        _comparative_table(comparative, table)
        if not table["rows"]:
            _write(
                values,
                [
                    table["trial"],
                    table["title"],
                    "No listed measures",
                    "",
                    "",
                    "",
                    "Not stated",
                    table.get("measure", {}).get("unit"),
                    "",
                    "",
                    table["population"],
                    [],
                    table.get("availability"),
                    f"landscape.json#{table['source']}",
                ],
                f"landscape.json#{table['source']}",
            )
        for row in table["rows"]:
            for value in row["values"]:
                ref = f"landscape.json#{value['source']}"
                measurement = value["measurement"]
                number = measurement.get("value", "Not stated")
                _write(
                    values,
                    [
                        table["trial"],
                        table["title"],
                        row["class"],
                        row["category"],
                        value["group"],
                        value["group_code"],
                        number,
                        value["unit"],
                        value["parameter"],
                        value["dispersion"],
                        table["population"],
                        value["denominators"],
                        measurement,
                        ref,
                    ],
                    ref,
                )


def _notes(book: Workbook, payloads: list[tuple[str, dict]], source: bool) -> None:
    sheet = _sheet(book, "Read me", ["Item", "Meaning"])
    notes = [
        (
            "Scope",
            "Only declared and represented restrictions are checked. "
            "A compatible restriction is not full clinical eligibility.",
        ),
        (
            "Source and choices",
            "Registry values, accepted premises, proposed readings and clinical choices retain their "
            "separate origins. A caller-written confirmation label is not authenticated confirmation.",
        ),
        (
            "Standing",
            "Known is conditional on its premises. Interpolated means an overridable working assumption. "
            "Proposed means an unconfirmed reading, usable only within its explicit hypothetical frame.",
        ),
        ("Counts", "Counts describe the declared comparison set and never decide the clinical choice."),
        (
            "Source coverage",
            "A registry's eligibility excerpt can be partial. A linked publication is not evidence that "
            "its findings were read. Missing, not posted and zero remain different.",
        ),
        (
            "Related analyses",
            "Included artifacts are shown separately. Inclusion does not bind their populations "
            "or assign them to a decision.",
        ),
        (
            "Exact content",
            "Artifact JSON copies retain every request and response field. Any value not representable "
            "in a cell is replaced with its explicit canonical reference, without shortening the original.",
        ),
        (
            "Baseline",
            "Every measurement remains in Baseline values. Baseline tables resolves columns only from "
            "exact, unique local group identifiers. Unplaced values remain explicit. It never sums total "
            "and treatment arms or selects an effective population or denominator.",
        ),
        (
            "Source association",
            "The optional source report is supplied by the caller. Sharing an export does not establish "
            "population identity or comparability."
            if source
            else "No source report was supplied with this export.",
        ),
    ]
    for label, meaning in notes:
        _write(sheet, [label, meaning], "")
    for identity, payload in payloads:
        _write(sheet, ["Complete artifact", _reference(identity)], _reference(identity))
        _write(
            sheet,
            [
                "Question as supplied",
                payload["response"].get("presentation", {}).get("question", "Not stated"),
            ],
            _reference(identity, "/response/presentation"),
        )


def _verify_book(path: Path, book: Workbook) -> None:
    """Read-back checks values and types, including literal formula-like strings."""
    loaded = load_workbook(path, read_only=False, data_only=False)
    try:
        if loaded.sheetnames != book.sheetnames:
            raise ExportError("export_sheet_readback_mismatch")
        for sheet in book:
            other = loaded[sheet.title]
            for expected, actual in zip(sheet.iter_rows(), other.iter_rows(), strict=True):
                for left, right in zip(expected, actual, strict=True):
                    expected_link = left.hyperlink.target if left.hyperlink else None
                    actual_link = right.hyperlink.target if right.hyperlink else None
                    if left.value != right.value or right.data_type == "f" or expected_link != actual_link:
                        raise ExportError("export_cell_readback_mismatch")
    finally:
        loaded.close()


def _protect_line_endings(path: Path) -> None:
    """Preserve CR and normalize writing timestamps in this newly rendered workbook."""
    temporary = path.with_suffix(".line-endings.xlsx")
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(temporary, "w") as destination:
        for item in source.infolist():
            body = source.read(item.filename)
            if item.filename == "docProps/core.xml":
                core = ElementTree.fromstring(body)
                for name in ("created", "modified"):
                    stamp = core.find(f"{{http://purl.org/dc/terms/}}{name}")
                    if stamp is not None:
                        stamp.text = "2000-01-01T00:00:00Z"
                body = ElementTree.tostring(core, encoding="utf-8")
            if item.filename.endswith(".xml"):
                body = body.replace(b"\r", b"&#13;")
            item.date_time = (2000, 1, 1, 0, 0, 0)
            destination.writestr(item, body)
    os.replace(temporary, path)


def _stage(folder: Path, payloads: list[tuple[str, dict, bytes]], source_record: Path | None) -> dict:
    artifacts = folder / "artifacts"
    artifacts.mkdir()
    for identity, _payload, body in payloads:
        (artifacts / f"{identity}.json").write_bytes(body)
    source = None
    if source_record is not None:
        if source_record.is_symlink() or not source_record.is_file():
            raise ExportError("source_record_not_regular_file")
        body = source_record.read_bytes()
        source = strict_json(body.decode("utf-8"))
        (folder / "landscape.json").write_bytes(body)
        workbook = source_record.with_suffix(".xlsx")
        if workbook.exists():
            if workbook.is_symlink() or not workbook.is_file():
                raise ExportError("source_workbook_not_regular_file")
            shutil.copyfile(workbook, folder / "landscape.xlsx")
    pairs = [(identity, payload) for identity, payload, _ in payloads]
    identity, payload = pairs[0]
    book = Workbook()
    book.remove(book.active)
    lines = _decision_rows(book, payload, identity)
    _findings(book, pairs)
    lines.extend(_changes(book, payload, identity))
    _sources(book, pairs)
    if source is not None:
        _baseline(book, source)
    _notes(book, pairs, source is not None)
    book.move_sheet("Read me", offset=-(len(book.sheetnames) - 1))
    for sheet in book:
        _finish(sheet)
    path = folder / "design-review.xlsx"
    book.save(path)
    _protect_line_endings(path)
    _verify_book(path, book)
    book.close()
    (folder / "decision-list.md").write_text("\n".join(lines), encoding="utf-8")
    files = {
        str(p.relative_to(folder)): {"sha256": _sha(p.read_bytes()), "bytes": p.stat().st_size}
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }
    manifest = {
        "schema_version": 1,
        "artifact": identity,
        "included": [value[0] for value in pairs[1:]],
        "source_association": "caller_supplied_not_population_binding"
        if source is not None
        else "not_supplied",
        "files": files,
        "verification": "Every exported workbook cell read back with equal value; no formula cells.",
    }
    (folder / "export-manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return manifest


def export_review(
    store: Path, identity: str, out: Path, source_record: Path | None = None, include: list[str] | None = None
) -> dict[str, Any]:
    """Publish a new review atomically inside an exclusively created output folder.

    The outer folder is reserved only after staging and read-back succeed. A single
    directory rename publishes `review`; no caller file or source record is replaced.
    """
    if include is not None and (not isinstance(include, list) or len(include) > 64):
        raise ExportError("invalid_included_artifacts")
    identities = [identity, *(include or [])]
    if any(reasoning_artifacts.artifact_id_code(key) != "valid_artifact_id" for key in identities):
        raise ExportError("invalid_artifact_id")
    if len(set(identities)) != len(identities):
        raise ExportError("duplicate_included_artifact")
    payloads = [(key, *_artifact(Path(store), key)) for key in identities]
    if payloads[0][1]["response"].get("code") != "complete":
        raise ExportError("export_requires_complete_result")
    out = Path(out).absolute()
    if out.exists() or out.is_symlink():
        raise ExportError("export_output_exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    reserved = False
    with tempfile.TemporaryDirectory(prefix=".clinical-review-", dir=out.parent) as temporary:
        staged = Path(temporary) / "review"
        staged.mkdir()
        manifest = _stage(staged, payloads, Path(source_record) if source_record is not None else None)
        try:
            out.mkdir()
            reserved = True
            os.rename(staged, out / "review")
        except FileExistsError as error:
            raise ExportError("export_output_exists") from error
        except OSError:
            if reserved:
                with suppress(OSError):
                    out.rmdir()
            raise
    review = out / "review"
    return {
        "code": "complete",
        "artifact": identity,
        "folder": str(review),
        "workbook": str(review / "design-review.xlsx"),
        "decision_list": str(review / "decision-list.md"),
        "manifest": str(review / "export-manifest.json"),
        "files": manifest["files"],
        "problems": [],
    }
