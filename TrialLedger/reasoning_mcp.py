"""MCP declarations and dispatch for retained clinical reasoning delivery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from TrialLedger import clinical_delivery, reasoning_artifacts, reasoning_delivery

IDENTITY = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
PRESENTATION = {
    "response_view": {"type": "string", "enum": ["full", "compact"]},
    "intent": {"type": "string", "enum": list(clinical_delivery.INTENTS)},
    "question": {"type": "string", "maxLength": 4096},
    "max_bytes": {
        "type": "integer",
        "minimum": clinical_delivery.MIN_BYTES,
        "maximum": clinical_delivery.MAX_BYTES,
        "description": f"Compact pretty-JSON reply budget; default {clinical_delivery.DEFAULT_BYTES}. "
        "Full mode stays full. Omitted detail remains at exact artifact references.",
    },
}
REASON_FIELDS: dict[str, Any] = {**PRESENTATION, "retain": {"type": "boolean"}}
TOOL_SCHEMAS = {
    "reason_result": {
        "name": "reason_result",
        "description": (
            "Read a retained clinical reasoning result, decision list or exact address without loading "
            "the whole response. Follow page/text continuation. The artifact id is returned by reason "
            "with retain true or response_view compact. Source workbooks remain separate."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "id": IDENTITY,
                "part": {"type": "string", "enum": ["manifest", *reasoning_artifacts.PARTS, "address"]},
                "address": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "max_bytes": {"type": "integer", "minimum": 2048, "maximum": 65536},
                "text_offset": {"type": "integer", "minimum": 0},
                "text_limit": {"type": "integer", "minimum": 1, "maximum": 8192},
            },
            "required": ["id"],
        },
    },
    "reason_revise": {
        "name": "reason_revise",
        "description": (
            "What changes if we revise the draft? Supply a retained design_session artifact id and either "
            "an explicit next session or replacement edits plus a new revision label. Changed premises "
            "need explicit origin attribution; copied source snapshots cannot be edited by this shortcut. "
            "Both snapshots are recomputed. Integrity fingerprints are filled by the program. "
            "prepare_only returns the valid request; otherwise a new retained result is returned."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "id": IDENTITY,
                "session": {"type": "object"},
                "revision": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 64,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "op": {"type": "string", "enum": ["replace"]},
                            "path": {"type": "string"},
                            "value": {},
                            "origin": {"type": "object"},
                        },
                        "required": ["op", "path", "value"],
                    },
                },
                "prepare_only": {"type": "boolean"},
                **PRESENTATION,
            },
            "required": ["id"],
            "oneOf": [
                {"required": ["session"], "not": {"required": ["edits"]}},
                {"required": ["edits", "revision"], "not": {"required": ["session"]}},
            ],
        },
    },
    "reason_export": {
        "name": "reason_export",
        "description": (
            "Give the clinician and colleagues a reproducible decision workbook and readable decision list. "
            "Supply a retained session artifact id, optionally a source report run and other retained "
            "analysis ids. Options, consequences, origins, unknowns and revision changes remain visible. "
            "Source reports are never modified; included analyses are not automatically assigned "
            "to a decision."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "id": IDENTITY,
                "source_run": {"type": "string"},
                "include": {"type": "array", "items": IDENTITY, "maxItems": 64},
            },
            "required": ["id"],
        },
    },
}


def store_root(root: Path) -> Path:
    """A separate namespace owns reasoning; no source report is repurposed."""
    folder = root / ".reasoning"
    if folder.is_symlink() or folder.resolve().parent != root.resolve():
        raise ValueError("reasoning_store_outside_root")
    return folder


def reason(root: Path, arguments: dict) -> dict:
    retain = arguments.get("retain", False) or arguments.get("response_view") == "compact"
    return reasoning_delivery.execute(
        arguments["request"],
        store=store_root(root) if retain else None,
        response_view=arguments.get("response_view", "full"),
        intent=arguments.get("intent", "unspecified"),
        question=arguments.get("question", ""),
        max_bytes=arguments.get("max_bytes", clinical_delivery.DEFAULT_BYTES),
    )


def handle(name: str, root: Path, arguments: dict) -> dict:
    """Call the same owners as CLI, with bounded root-relative report selection."""
    try:
        if name == "reason_result":
            return reasoning_artifacts.read(
                store_root(root), arguments["id"], {k: v for k, v in arguments.items() if k != "id"}
            )
        if name == "reason_revise":
            return reasoning_delivery.revise(
                store_root(root), arguments["id"], **{k: v for k, v in arguments.items() if k != "id"}
            )
        if name == "reason_export":
            from TrialLedger.clinical_export import export_review

            source = None
            if "source_run" in arguments:
                run = arguments["source_run"]
                if not isinstance(run, str) or not run or Path(run).name != run or run in (".", ".."):
                    raise ValueError("source_run_outside_root")
                folder = root / run
                if folder.resolve().parent != root.resolve():
                    raise ValueError("source_run_outside_root")
                source = folder / "landscape.json"
            identity = arguments["id"]
            if reasoning_artifacts.artifact_id_code(identity) != "valid_artifact_id":
                raise ValueError("invalid_artifact_id")
            exports = root / "reasoning-exports"
            if exports.is_symlink() or exports.resolve().parent != root.resolve():
                raise ValueError("reasoning_export_outside_root")
            return export_review(
                store_root(root),
                identity,
                exports / identity,
                source_record=source,
                include=arguments.get("include", []),
            )
        raise ValueError("unsupported_reasoning_delivery_tool")
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"code": "refused", "problems": [str(error)]}
