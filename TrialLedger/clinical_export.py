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
from TrialLedger.analysis_review import summaries as analysis_summaries
from TrialLedger.baseline_view import baseline_tables, group_code
from TrialLedger.cells import cell_number_state, cell_text_state
from TrialLedger.landscape_verify import strict_json
from TrialLedger.layer2.clinical_answers import project
from TrialLedger.layer2.session_state import canonical

DECISION_WORDS = {
    "unrepresented_design_question": "Draft does not address this choice",
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
    "question_changed": "Represented question changed",
    "wording_changed": "Caller wording changed",
    "context_changed": "Linked evidence context changed",
    "support_changed": "Supporting warrant changed",
    "requirements_changed": "Remaining requirements changed; verdict unchanged",
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
    if sheet.title in ("Decision list", "Options"):
        sheet.freeze_panes = "C2" if sheet.title == "Options" else "B2"
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
            "Findings": 132,
            "Changes": 56,
            "Sources and origins": 64,
            "Baseline values": 56,
            "Decision list": 96,
            "Decision evidence": 180,
            "Analysis details": 180,
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
        elif code == "undecided_by_constraints":
            words = "This exact query is allowed but not required; its negation also fits"
        elif code == "table_uncovered_case":
            words = "A feasible declared situation has no action"
        elif code == "table_conflicting_actions":
            words = "A feasible declared situation selects different actions"
        elif code == "table_forbidden_action":
            words = "The table can select an explicitly prohibited action"
        elif isinstance(code, str) and code.startswith("estimand_collection_plan_mismatch:"):
            words = "The collection plan does not meet a declared requirement"
        elif isinstance(code, str) and code.startswith("estimand_unresolved:"):
            words = "Actual data availability remains unresolved"
        elif isinstance(code, str) and code.startswith("dependency_blocked:"):
            words = "An adopted derivation has no available input alternative"
        elif isinstance(code, str) and code.startswith("dependency_unresolved:"):
            words = "Input availability or applicability remains unresolved"
        elif code in (
            "definition_missing_support",
            "definition_proposed_refused",
            "definition_binding_unresolved",
        ):
            words = "The declared relationship between meanings remains unresolved"
        elif code == "definition_computation_refused":
            words = "The declared relationship could not be computed from this request"
        elif isinstance(code, str) and code.startswith("definition_analysis_refused:"):
            words = "A linked analysis was refused; its definition cannot be certified"
        elif isinstance(code, str) and code.startswith("definition_empty_antecedent:"):
            words = "A declared antecedent is inconsistent; the relationship is not certified"
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


def _origins_text(origins: object) -> str:
    if isinstance(origins, dict):
        return _origin_text(origins)
    if isinstance(origins, list):
        return (
            "; ".join(_origin_text(row.get("origin", row)) for row in origins if isinstance(row, dict))
            or "Origin not stated"
        )
    return "Origin not stated"


def _premise_text(premises: list[dict]) -> str:
    return (
        "\n".join(
            f"{row.get('id')}: {row.get('text', 'Open the exact premise.')} "
            f"[standing: {row.get('standing', row.get('support'))}; {_origins_text(row.get('origin'))}]"
            for row in premises
        )
        or "No deciding premise returned; inspect open items and exact result."
    )


def _condition_text(conditions: list[dict]) -> str:
    if not conditions:
        return "No additional proved requirement displayed; this is not complete screening."
    return (
        "The supplied profile does not establish the following; actual absence is not asserted.\n"
        + "\n".join(
            f"{row.get('relation')}: {row.get('requirement', {}).get('text', 'Open exact requirement')} "
            f"[standing: {row.get('standing')}; proof: {', '.join(row.get('proof', []))}]."
            for row in conditions
        )
    )


def _permission_text(permissions: list[dict]) -> str:
    """Render existing permission mentions, never infer permission from silence."""
    return "\n".join(
        f"{p['id']}: {p['statement']['text']}; applies when {p['applicability']['text']}; "
        f"scope: {_json(p.get('scope'))}; standing: {p.get('standing')}; "
        f"basis: {p.get('criterion_ref')}; {_blocker_text(p.get('blockers', []))}. "
        "Permission mention only: neither a requirement nor complete entry eligibility."
        for p in permissions
    )


def _context_text(evidence: list[dict]) -> str:
    if not evidence:
        return "No comparator context linked to this decision; source absence is not asserted."
    rows = []
    for item in evidence:
        anchor = item.get("anchor", {})
        value = anchor.get("span", {}).get("text", anchor.get("value"))
        copied = value if isinstance(value, str) else _json(value)
        source = item.get("source", {})
        rows.append(
            f"{source.get('study_ref', item.get('source_id'))} {anchor.get('address')}: {copied} "
            f"[https://clinicaltrials.gov/study/{source.get('nct')}]. "
            f"[exact source copy; digest {source.get('digest')}]. "
            f"Caller role: {item.get('role')}; caller-declared scope: {item.get('declared_scope')}. "
            f"Caller note (proposed): {item.get('note') or 'None supplied'}. Context only."
        )
    return "\n".join(rows)


def _held_scalar(value: object) -> object:
    """Unwrap only an exact source field-state object; never coerce its value."""
    if not isinstance(value, dict) or set(value) != {"present", "value", "source"}:
        return value
    if value["present"] is False:
        return "Not stated"
    return value["value"] if value["present"] is True else value


def _display_parts(text: str) -> list[str]:
    """Preserve every character while bounding both width and explicit line breaks."""
    parts, start, breaks = [], 0, 0
    for index, char in enumerate(text):
        breaks += char == "\n"
        if index - start + 1 >= 320 or breaks >= 5:
            parts.append(text[start : index + 1])
            start, breaks = index + 1, 0
    if start < len(text):
        parts.append(text[start:])
    return parts


def _evidence_rows(book: Workbook, views: list[dict], identity: str) -> dict[str, int]:
    """Flow complete context across labelled display parts; never shorten a source value."""
    sheet = _sheet(
        book,
        "Decision evidence",
        [
            "Your question (caller wording)",
            "Evidence id",
            "Trial",
            "Channel",
            "Part",
            "Value",
            "Standing",
            "Source address",
            "Exact result",
        ],
    )
    starts = {}
    for i, view in enumerate(views):
        starts[view["id"]] = sheet.max_row + 1
        for j, item in enumerate(view["evidence"]):
            anchor, source = item["anchor"], item["source"]
            value = anchor.get("span", {}).get("text", anchor["value"])
            channels = [
                ("Caller note (" + item["role"] + ")", item["note"], "proposed"),
                ("Caller-declared scope", item["declared_scope"], "proposed"),
                ("Exact source copy", value if isinstance(value, str) else _json(value), "known as copied"),
            ]
            for kind, text, standing in channels:
                parts = _display_parts(text) or (
                    [""] if kind == "Exact source copy" else ["No annotation supplied"]
                )
                ref = _reference(identity, f"/response/decision_view/{i}/evidence/{j}")
                for number, part in enumerate(parts, 1):
                    _write(
                        sheet,
                        [
                            view["caller_question"]["text"],
                            item["id"],
                            source["nct"],
                            kind,
                            f"{number}/{len(parts)}",
                            part,
                            standing,
                            anchor["address"],
                            ref,
                        ],
                        ref,
                    )
                    sheet.cell(
                        sheet.max_row, 3
                    ).hyperlink = f"https://clinicaltrials.gov/study/{source['nct']}"
    return starts


def _decision_rows(book: Workbook, payload: dict, identity: str) -> list[str]:
    from TrialLedger.clinical_view import build

    response = payload["response"]
    result = response.get("result") or {}
    views = build(response)
    sheet = _sheet(
        book,
        "Decision list",
        [
            "Your question (caller wording)",
            "Current result",
            "Selected option (caller wording)",
            "Deciding criteria",
            "Open items",
            "Origin",
            "Coverage",
            "Exact result",
            "Comparator evidence and context",
            "Permission mentions",
        ],
    )
    options = _sheet(
        book,
        "Options",
        [
            "Your question (caller wording)",
            "Your option label (caller wording)",
            "Computed feasibility",
            "Logical answer",
            "Standing",
            "Deciding criteria",
            "Open items",
            "Represented profile",
            "Origin",
            "Exact result",
            "Remaining requirements",
            "Comparator evidence and context",
            "Actual analysis context",
            "Permission mentions",
        ],
    )
    lines = [
        "# Clinical design decision list",
        "",
        f"Session: {result.get('session_id', 'Not a managed session')}",
        f"Revision: {result.get('revision', 'Not stated')}",
        "",
        "Questions and option labels are caller wording, not computed assertions. "
        "Only the represented restrictions are checked. "
        "Caller origin labels are not authenticated confirmation.",
        "",
    ]
    requirements = _sheet(
        book,
        "Requirements",
        [
            "Your question (caller wording)",
            "Option (caller wording)",
            "Represented profile",
            "Relation",
            "Proved requirement",
            "Standing",
            "Deciding premises",
            "Scope",
            "Coverage",
            "Exact result",
        ],
    )
    context_starts = _evidence_rows(book, views, identity)
    permissions = _sheet(
        book,
        "Permissions",
        [
            "Your question (caller wording)",
            "Option (caller wording)",
            "Represented profile",
            "Permission",
            "Applies when",
            "Scope",
            "Standing",
            "Criterion reference",
            "Rule and warrants",
            "Open items",
            "Exact result",
        ],
    )
    raw = result.get("decisions", [])
    for i, view in enumerate(views):
        decision = raw[i]
        question = view["caller_question"]["text"]
        ref = _reference(identity, "/response" + view["canonical_ref"])
        selected = view["selected"]
        key = selected.get("alternative") if isinstance(selected, dict) else None
        label = next((o["caller_label"]["text"] for o in view["options"] if o["id"] == key), key or "Open")
        outcome = _word(view["decision_code"], DECISION_WORDS)
        origin = _origin_text(view["origin"])
        premises = {row["id"]: row for option in view["options"] for row in option["deciding_premises"]}
        deciding = _premise_text(list(premises.values()))
        open_items = "\n".join(
            f"Caller-labelled option {o['caller_label']['text']}: {_blocker_text(o['open_items'])}"
            for o in view["options"]
        )
        permission_count = sum(len(o["permissions"]) for o in view["options"])
        permission_summary = (
            f"{permission_count} permission mentions: open Permissions for statements, applicability, "
            "scope, standing and basis. Mentions neither require action nor certify entry eligibility."
            if permission_count
            else "No related permission returned"
        )
        if permission_count:
            outcome += "; permission mentions and their conditions are shown separately"
        context = _context_text(view["evidence"])
        context_summary = (
            (
                f"{len(view['evidence'])} linked entries; open Decision evidence for full passages "
                "and separately attributed notes."
            )
            if view["evidence"]
            else context
        )
        _write(
            sheet,
            [
                question,
                outcome,
                label,
                deciding,
                open_items,
                origin,
                view["coverage"],
                ref,
                context_summary,
                permission_summary,
            ],
            ref,
        )
        if view["evidence"]:
            sheet.cell(sheet.max_row, 9).hyperlink = f"#'Decision evidence'!A{context_starts[view['id']]}"
        if permission_count:
            sheet.cell(sheet.max_row, 10).hyperlink = f"#'Permissions'!A{permissions.max_row + 1}"
        lines.extend(
            [
                f"## {question}",
                "",
                "Question above is caller wording.",
                f"Current result: {outcome}. Selected caller-labelled option: {label}.",
                "",
                "Comparator evidence and context:",
                context,
                "",
            ]
        )
        for j, option in enumerate(view["options"]):
            original = decision["alternatives"][j]
            option_ref = _reference(identity, "/response" + option["canonical_ref"])
            logical = _logical_text(original)
            premise_text = _premise_text(option["deciding_premises"])
            conditions = _condition_text(option["conditions"])
            permission_text = _permission_text(option["permissions"])
            profile = option["profile"]["text"]
            for permission in option["permissions"]:
                permission_ref = _reference(identity, "/response" + permission["canonical_ref"])
                _write(
                    permissions,
                    [
                        question,
                        option["caller_label"]["text"],
                        profile,
                        permission["statement"]["text"],
                        permission["applicability"]["text"],
                        _json(permission.get("scope")),
                        permission.get("standing"),
                        permission.get("criterion_ref"),
                        _json(permission.get("rule")),
                        _blocker_text(permission.get("blockers", [])),
                        permission_ref,
                    ],
                    permission_ref,
                )
            for condition in option["conditions"]:
                condition_ref = _reference(identity, "/response" + condition["canonical_ref"])
                _write(
                    requirements,
                    [
                        question,
                        option["caller_label"]["text"],
                        profile,
                        condition["relation"],
                        condition["requirement"]["text"],
                        condition["standing"],
                        ", ".join(condition["proof"]),
                        _detail_text(condition.get("scope"), condition_ref),
                        option.get("condition_coverage") or "Bounded discovery, not complete screening",
                        condition_ref,
                    ],
                    condition_ref,
                )
            _write(
                options,
                [
                    question,
                    option["caller_label"]["text"],
                    _word(option["feasibility"], OPTION_WORDS),
                    logical,
                    option["standing"],
                    premise_text,
                    _blocker_text(option["open_items"]),
                    profile,
                    _origins_text(option["origin"]),
                    option_ref,
                    conditions,
                    context_summary,
                    _detail_text(option["context"], option_ref)
                    if option["context"]
                    else "No context supplied; cohort/phase/arm remain open",
                    permission_text,
                ],
                option_ref,
            )
            if view["evidence"]:
                options.cell(
                    options.max_row, 12
                ).hyperlink = f"#'Decision evidence'!A{context_starts[view['id']]}"
            lines.extend(
                [
                    f"### Caller-labelled option: {option['caller_label']['text']}",
                    "",
                    f"Represented profile: {profile}",
                    f"Actual analysis context: {_detail_text(option['context'], option_ref)}",
                    f"Computed answer: {logical}",
                    f"Feasibility: {_word(option['feasibility'], OPTION_WORDS)}. "
                    f"Standing: {option['standing']}.",
                    "Deciding criteria:",
                    premise_text,
                    "Remaining requirements:",
                    conditions,
                    *(["Permission mentions:", permission_text] if permission_text else []),
                    "Open items: " + _blocker_text(option["open_items"]),
                    f"Exact result: `{option_ref}`",
                    "",
                ]
            )
        lines.extend([f"Origin: {origin}", f"Coverage: {view['coverage']}", f"Exact result: `{ref}`", ""])
    if not views:
        lines.extend(
            [
                "No decision entries were declared. See the workbook's Findings "
                "and complete retained result.",
                "",
            ]
        )
    return lines


def finding_owner_code(operation: str, address: str, count: int) -> str:
    """Discriminate identically named paths by their owning schema (pure — pinned)."""
    if operation != "design_session":
        return "operation_result"
    parts = address.split("/")
    if len(parts) < 4 or parts[:3] != ["", "result", "analyses"] or not parts[3].isdecimal():
        return "operation_result"
    return "managed_analysis" if int(parts[3]) < count else "operation_result"


def _finding_name(response: dict, address: str, index: int) -> str:
    """Name a managed analysis only from its exact structural result path."""
    parts = address.split("/")
    analyses = (response.get("result") or {}).get("analyses", [])
    if finding_owner_code(response.get("operation") or "", address, len(analyses)) == "managed_analysis":
        position = int(parts[3])
        return str(analyses[position]["id"])
    return "Main" if index == 0 else "Related analysis"


def _detail_text(value: object, reference: str, depth: int = 0) -> str:
    """Mechanical labels and typed statements; full canonical objects remain linked."""
    from TrialLedger import clinical_display

    if depth > 12:
        return f"Full nested value retained at {reference}"
    if isinstance(value, dict):
        if value.get("class") == "ScopedAssertion":
            return clinical_display.assertion(value, reference)["text"]
        if "class" in value:
            return clinical_display.proposition(value, reference)["text"]
        return (
            "\n".join(f"{key}: {_detail_text(item, reference, depth + 1)}" for key, item in value.items())
            or "None listed"
        )
    if isinstance(value, list | tuple):
        return "; ".join(_detail_text(item, reference, depth + 1) for item in value) or "None listed"
    if isinstance(value, str):
        if value.startswith('{"class":'):
            return clinical_display.proposition(value, reference)["text"]
        return value
    return str(value) if value is not None else "Not stated"


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
            address = finding["canonical_ref"]
            ref = _reference(identity, "/response" + address)
            _write(
                sheet,
                [
                    _finding_name(response, address, index),
                    response.get("operation"),
                    finding["outcome"],
                    finding["standing"] if finding["standing"] is not None else "Not stated",
                    finding["disposition"],
                    finding["completion"],
                    _detail_text(
                        {
                            key: finding["scope"][key]
                            for key in ("query", "context")
                            if key in finding["scope"]
                        }
                        | {
                            key: value
                            for key, value in finding["scope"].items()
                            if key not in ("query", "context")
                        },
                        ref,
                    ),
                    _detail_text(finding["values"], ref),
                    _detail_text(finding["conditions"], ref),
                    _detail_text(finding["support"], ref),
                    _detail_text(finding["origins"], ref),
                    _blocker_text(finding["blockers"]),
                    ref,
                ],
                ref,
            )


def _changes(book: Workbook, payload: dict, identity: str) -> list[str]:
    sheet = _sheet(
        book,
        "Changes",
        [
            "Type",
            "Item",
            "Change",
            "Answer",
            "Support",
            "Origin",
            "Before",
            "After",
            "Exact comparison",
            "Question",
            "Caller wording",
            "Evidence context",
            "Remaining requirements",
        ],
    )
    difference = payload["response"].get("answer_diff")
    if not isinstance(difference, dict):
        return []
    lines = ["## Changes from the previous revision", ""]
    rows = [
        (kind, index, item)
        for kind in ("decisions", "analyses", "definition_checks")
        for index, item in enumerate(difference.get(kind, []))
    ]
    rows.sort(key=lambda row: (row[2].get("code") in ("unchanged", "input_only"), row[0] != "decisions"))
    for kind, index, item in rows:
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
                axes.get("question"),
                axes.get("wording"),
                axes.get("context"),
                axes.get("requirements", "Not recorded in this artifact"),
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
            f"- {item.get('id')}: {_word(item.get('code'), CHANGE_WORDS)}. "
            + "; ".join(
                f"{axis}: {axes.get(axis, 'Not recorded in this artifact')}"
                for axis in ("question", "answer", "requirements", "support", "origin", "wording", "context")
            )
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


def _analysis_rows(book: Workbook, payloads: list[tuple[str, dict]]) -> list[str]:
    """Carry returned analyses into the main handoff without assigning them to choices."""
    sheet = _sheet(
        book,
        "Analysis review",
        [
            "Analysis",
            "Kind",
            "Applied result / conditional calculation",
            "Standing",
            "Declared scope and version",
            "Computed summary",
            "Open items",
            "Basis and rule",
            "Exact result",
            "Details",
        ],
    )
    detail_sheet = _sheet(
        book, "Analysis details", ["Analysis", "Returned detail", "Standing", "Exact result", "Part"]
    )
    lines = [
        "## Supporting analyses",
        "",
        "These are separate computations, not additional clinical choices. Inclusion alone does not "
        "bind populations or adopt a comparator's result. Applied results and conditional calculations "
        "remain distinct; open the exact result for all support and admission details.",
        "",
    ]
    for row in analysis_summaries(payloads):
        identity = row["artifact"]
        ref = _reference(identity, row["canonical_ref"])
        scope = f"{_detail_text(row['scope'], ref)}; version/snapshot: {row['version']}"
        result = f"Applied: {row['code']}; calculation: {row['calculation_code']}"
        basis = "; ".join(str(value) for value in row["basis"]) or "Not stated"
        basis += f"; rule: {row['rule']}"
        details = list(row["details"])
        if row["basis"]:
            details.append(
                {
                    "text": "Declared basis references: " + basis,
                    "standing": row["standing"],
                    "canonical_ref": row["canonical_ref"],
                    "sheet_only": True,
                }
            )
        if row["blockers"]:
            details.append(
                {
                    "text": "Reported open items: " + _blocker_text(row["blockers"]),
                    "standing": row["standing"],
                    "canonical_ref": row["canonical_ref"],
                    "sheet_only": True,
                }
            )
        _write(
            sheet,
            [
                row["analysis"],
                row["kind"],
                result,
                row["standing"] if row["standing"] is not None else "Not stated",
                scope,
                row["summary"],
                f"{len(row['blockers'])} reported open items; open Analysis details"
                if row["blockers"]
                else "No blocker reported",
                f"{len(row['basis'])} declared basis references; rule: {row['rule']}; open Analysis details"
                if row["basis"]
                else basis,
                ref,
                f"{len(details)} returned detail entries" if details else "Open exact result",
            ],
            ref,
        )
        if details:
            sheet.cell(sheet.max_row, 10).hyperlink = f"#'Analysis details'!A{detail_sheet.max_row + 1}"
        else:
            sheet.cell(sheet.max_row, 10).hyperlink = ref
        lines.extend(
            [
                f"### {row['analysis']} ({row['kind']})",
                "",
                f"{result}. Standing: {row['standing'] if row['standing'] is not None else 'Not stated'}.",
                f"Declared scope: {scope}",
                row["summary"],
                f"Basis: {basis}",
                "Open items: " + _blocker_text(row["blockers"]),
                f"Exact result: [{row['kind']} result]({ref})",
                "",
            ]
        )
        for detail in details:
            detail_ref = _reference(identity, detail["canonical_ref"])
            parts = _display_parts(detail["text"]) or [""]
            for part, text in enumerate(parts, 1):
                _write(
                    detail_sheet,
                    [row["analysis"], text, detail["standing"], detail_ref, f"{part}/{len(parts)}"],
                    detail_ref,
                )
            if not detail.get("sheet_only"):
                lines.extend(
                    [
                        f"- {detail['text']} Standing: {detail['standing']}. [Exact detail]({detail_ref})",
                        "",
                    ]
                )
    return lines


def _comparative_table(sheet, table: dict) -> None:
    """Lay out exact local groups beside each other without joining or aggregating."""
    ref = f"landscape.json#{table['source']}"
    identities = [group["id"] for group in table["groups"]]
    groups = [group for group in table["groups"] if group_code(group["id"], identities) == "unique"]
    _write(
        sheet,
        [
            "Trial",
            table["trial"],
            "Measure",
            table["title"] if table["title"] is not None else "No listed measure",
            "Exact source",
            ref,
        ],
        ref,
    )
    populations = {
        key: {"present": field["present"], "value": field["value"]}
        for key, field in table["population"].items()
    }
    statistic = {
        key: table["measure"][key]
        for key in ("unit", "param_type", "dispersion_type")
        if key in table["measure"]
    }
    _write(
        sheet,
        [
            "Source populations",
            "\n".join(
                f"{key}: {_detail_text(_held_scalar(table['population'][key]), ref)}" for key in populations
            ),
            "Unit and statistic",
            _detail_text(statistic, ref) if statistic else "Not stated",
        ],
        ref,
    )
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
    _write(
        sheet,
        [
            "Group denominators",
            _detail_text(denominators, ref) if denominators else "No matching denominators listed",
        ],
        ref,
    )
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
        _write(
            sheet,
            [
                "Availability",
                _detail_text(_held_scalar(table.get("availability", {"rows": "not listed"})), ref),
            ],
            ref,
        )
    _write(
        sheet, ["End of measure", table["title"] if table["title"] is not None else "No listed measure"], ref
    )


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
            "Unit source",
            "Parameter source",
            "Dispersion source",
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
                        _held_scalar(value["unit"]),
                        _held_scalar(value["parameter"]),
                        _held_scalar(value["dispersion"]),
                        table["population"],
                        value["denominators"],
                        measurement,
                        ref,
                        "landscape.json#" + value["unit"]["source"],
                        "landscape.json#" + value["parameter"]["source"],
                        "landscape.json#" + value["dispersion"]["source"],
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
            "Analysis review and the readable list summarize included and managed analyses once each; "
            "Analysis details and Findings retain their details. Inclusion does not bind their populations "
            "or assign them to a decision. Table completeness covers only the declared variables and "
            "constraints; it is not clinical safety or statistical validity.",
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
    lines.extend(_analysis_rows(book, pairs))
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
