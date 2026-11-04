"""Common readable delivery over canonical reasoning; no new clinical premises."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from copy import deepcopy

from TrialLedger.record_access import DEFAULT_BYTES, MAX_BYTES, MIN_BYTES, response_bytes

INTENTS = ("unspecified", "compatibility", "necessity", "consistency", "description", "decision")


def augment(response: dict) -> dict:
    """Add one shared clinical projection and summary, retaining every original result field."""
    from TrialLedger.layer2 import clinical_answers
    from TrialLedger.layer2.session_state import digest

    operation = response["operation"]
    if operation == "describe":
        return {
            "summary": {"kind": "discovery", "code": response["code"], "operation": operation},
            **response,
        }
    clinical = clinical_answers.project(operation, response["result"], response["problems"])
    dispositions = Counter(row["disposition"] for row in clinical["findings"])
    summary = {
        "kind": ("inspection" if operation == "prepare" else "reasoning")
        if response["code"] == "complete"
        else "refusal",
        "code": response["code"],
        "operation": operation,
        "findings": len(clinical["findings"]),
        "dispositions": dict(sorted(dispositions.items())),
        "problems": deepcopy(response["problems"]),
    }
    if "answer_diff" in response:
        changes = response["answer_diff"]
        summary["changes"] = (
            {kind: dict(Counter(row["code"] for row in changes.get(kind, []))) for kind in changes}
            if isinstance(changes, dict)
            else None
        )
    reply = {"summary": summary, "clinical": clinical, **response}
    if operation == "design_session" and response["code"] == "complete":
        from TrialLedger.clinical_view import build

        reply["decision_view"] = build(response)
    if response["code"] == "complete":
        reply["result_digest"] = digest(response["result"])
        reply["result_digest_scope"] = "result only; excludes summary, presentation and artifact metadata"
    return reply


def present(response: dict, *, intent: str = "unspecified", question: str = "") -> dict:
    """A declared clinical question guides wording; it never changes a logical outcome."""
    if not isinstance(intent, str) or intent not in INTENTS:
        raise ValueError("unsupported_question_intent")
    if not isinstance(question, str) or len(question) > 4096:
        raise ValueError("invalid_clinical_question")
    if intent == "unspecified" and not question:
        return dict(response)
    return {
        **response,
        "presentation": {
            "intent": intent,
            "question": question,
            "origin": "caller_declared_question; not authenticated confirmation",
        },
    }


def compact_budget_code(value: object) -> str:
    """Only integer reply budgets in the supported inclusive range are admitted.

    post: __return__ in ('valid_compact_budget', 'max_bytes_out_of_range')
    """
    if type(value) is not int or not MIN_BYTES <= value <= MAX_BYTES:
        return "max_bytes_out_of_range"
    return "valid_compact_budget"


def _compact_finding(row: dict, address: str) -> dict:
    """Keep decision channels; the exact scope and full support remain at their source address."""
    fields = ("path", "kind", "outcome", "status", "standing", "disposition", "completion", "blockers")
    return {
        **{key: deepcopy(row[key]) for key in fields if key in row},
        "scope_ref": address + "/scope",
        "canonical_ref": address,
    }


def _compact_change(row: dict, address: str) -> dict:
    """Preserve every change axis without echoing before/after projections."""
    fields = ("id", "code", "changes", "axes")
    return {**{key: deepcopy(row[key]) for key in fields if key in row}, "canonical_ref": address}


def _compact_decision(row: dict, address: str) -> dict:
    """Overview of a coherent stored view, with no shortened source excerpts."""
    fields = ("id", "caller_question", "decision_code", "selected", "coverage")
    return {
        **{key: deepcopy(row[key]) for key in fields if key in row},
        "options_count": len(row.get("options", [])),
        "evidence_count": len(row.get("evidence", [])),
        "canonical_ref": address,
    }


def _compact_edit(row: dict, address: str) -> dict:
    from TrialLedger.layer2.session_state import digest

    return {
        "path": row["path"],
        "before_digest": digest(row["before"]),
        "after_digest": digest(row["after"]),
        "canonical_ref": address,
    }


def _compact_page(total: int, returned: int = 0) -> dict:
    return {
        "offset": 0,
        "returned": returned,
        "total": total,
        "next_offset": returned if returned < total else None,
    }


def compact(response: dict, artifact: dict, *, max_bytes: int = DEFAULT_BYTES) -> dict:
    """Bound a retained reply and expose exact navigation for every omitted field and row.

    The conservative counter includes pretty whitespace and escaped Unicode. The reserved 128 bytes
    cover the MCP tool-name field and CLI trailing newline. No source value is shortened.
    """
    from TrialLedger.reasoning_artifacts import artifact_id_code

    code = compact_budget_code(max_bytes)
    if code != "valid_compact_budget":
        raise ValueError(code)
    if type(artifact) is not dict or artifact_id_code(artifact.get("id")) != "valid_artifact_id":
        raise ValueError("compact_requires_canonical_artifact")
    reply = {
        "code": response["code"],
        "operation": response["operation"],
        "artifact": {key: artifact[key] for key in ("id", "bytes", "schema_version") if key in artifact},
        "view": "compact",
        "max_bytes": max_bytes,
        "canonical_ref": "/response",
        "canonical_result": "Full request/response retained unchanged. Read canonical_ref with "
        "reason_result part address; follow page.next_offset.",
    }
    if "preparation" in response:
        preparation = response["preparation"]
        reply["preparation"] = {
            "artifact": preparation["artifact"],
            "meaning": preparation["meaning"],
            "defaults": len(preparation["defaults"]),
            "origins": len(preparation["origins"]),
            "canonical_ref": "/response/preparation",
        }
        if "applies_to" in preparation:
            reply["preparation"]["applies_to"] = preparation["applies_to"]
    # A group admits a contiguous prefix. If a summary cannot fit, next_offset still names that row.
    # Each channel gets a turn; a long finding list cannot crowd out every revision or decision row.
    groups: list[tuple[list, dict, list, str, Callable[[dict, str], dict]]] = []
    if "decision_view" in response:
        rows = response["decision_view"]
        section = {
            "decisions": [],
            "page": _compact_page(len(rows)),
            "canonical_ref": "/response/decision_view",
        }
        reply["decision_view"] = section
        groups.append(
            (section["decisions"], section["page"], rows, section["canonical_ref"], _compact_decision)
        )
    if isinstance(response.get("answer_diff"), dict):
        changes = response["answer_diff"]
        section = {"canonical_ref": "/response/answer_diff", "pages": {}}
        reply["answer_diff"] = section
        for kind in changes:
            rows = changes.get(kind, [])
            shown_changes: list = []
            change_page = _compact_page(len(rows))
            section[kind] = shown_changes
            section["pages"][kind] = change_page
            groups.append(
                (
                    shown_changes,
                    change_page,
                    rows,
                    f"/response/answer_diff/{kind}",
                    _compact_change,
                )
            )
    elif "answer_diff" in response:
        reply["answer_diff"] = (
            None
            if response["answer_diff"] is None
            else {"navigation": "exact_artifact", "canonical_ref": "/response/answer_diff"}
        )
    if "clinical" in response:
        clinical = response["clinical"]
        rows = clinical["findings"]
        section = {
            "version": clinical["version"],
            "operation": clinical["operation"],
            "findings": [],
            "page": _compact_page(len(rows)),
            "canonical_ref": "/response/clinical/findings",
        }
        reply["clinical"] = section
        groups.append(
            (section["findings"], section["page"], rows, section["canonical_ref"], _compact_finding)
        )
    if "delivery" in response:
        delivery = response["delivery"]
        rows = delivery["edits"]
        section = {
            "previous_artifact": delivery["previous_artifact"],
            "edits": [],
            "page": _compact_page(len(rows)),
            "canonical_ref": "/response/delivery/edits",
        }
        reply["delivery"] = section
        groups.append((section["edits"], section["page"], rows, section["canonical_ref"], _compact_edit))
    fields = ("summary", "problems", "result_digest", "result_digest_scope", "presentation", "diagnostics")
    reply["omitted_fields"] = [key for key in fields if key in response]
    if response_bytes(reply) > max_bytes - 128:
        return {
            "code": response["code"],
            "operation": response["operation"],
            "artifact": {"id": artifact["id"]},
            "view": "compact",
            "max_bytes": max_bytes,
            "navigation": "exact_artifact",
            "canonical_ref": "/response",
            "pages": {address: _compact_page(len(rows)) for _shown, _page, rows, address, _project in groups},
            "omitted_fields": reply["omitted_fields"],
        }
    for key in tuple(reply["omitted_fields"]):
        if key == "diagnostics":
            continue
        reply[key] = deepcopy(response[key])
        if response_bytes(reply) <= max_bytes - 128:
            reply["omitted_fields"].remove(key)
        else:
            del reply[key]
    active = list(groups)
    while active:
        following = []
        for shown, page, rows, address, project in active:
            index = len(shown)
            if index == len(rows):
                continue
            shown.append(project(rows[index], f"{address}/{index}"))
            page.update(_compact_page(len(rows), len(shown)))
            if response_bytes(reply) <= max_bytes - 128:
                following.append((shown, page, rows, address, project))
            else:
                shown.pop()
                page.update(_compact_page(len(rows), len(shown)))
        active = following
    return reply
