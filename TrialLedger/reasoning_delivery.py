"""Public reasoning/artifact workflow shared by CLI and MCP delivery shells."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from TrialLedger import clinical_delivery, reasoning_artifacts
from TrialLedger.evidence_access import pointer_value

MAX_EDITS = 64
EDIT_ROOTS = ("premises", "analyses", "decisions", "limits", "target")
EDIT_CODES = (
    "unsupported_edit_operation",
    "invalid_edit_path",
    "immutable_session_field",
    "replace_design_field",
)


def edit_path_code(path: object, operation: object) -> str:
    """Only explicit replacements of declared design fields are shortcuts (pure — pinned).

    post: __return__ in EDIT_CODES
    """
    if operation != "replace":
        return "unsupported_edit_operation"
    if not isinstance(path, str) or not path.startswith("/") or "~" in path:
        return "invalid_edit_path"
    if path[1:].split("/", 1)[0] not in EDIT_ROOTS:
        return "immutable_session_field"
    return "replace_design_field"


def _replace(session: dict, patch: dict) -> None:
    path = patch["path"]
    code, _old = pointer_value(session, path)
    if code != "ok":
        raise ValueError(code)
    parent_path, _, key = path.rpartition("/")
    if parent_path:
        code, parent = pointer_value(session, parent_path)
        if code != "ok":
            raise ValueError(code)
    else:
        parent = session
    parent[int(key) if isinstance(parent, list) else key] = deepcopy(patch["value"])


def edited_session(previous: dict, revision: str, edits: list) -> tuple[dict, list]:
    """Apply bounded explicit edits; changed premises need an explicitly supplied attribution."""
    from TrialLedger.layer2 import source_evidence

    if type(previous) is not dict or not isinstance(revision, str) or not revision or len(revision) > 256:
        raise ValueError("invalid_revision_input")
    if type(edits) is not list or not 1 <= len(edits) <= MAX_EDITS:
        raise ValueError("invalid_revision_edits")
    session = deepcopy(previous)
    reviewed, attributed = [], set()
    whole_premises = False
    for patch in edits:
        if type(patch) is not dict or set(patch) - {"op", "path", "value", "origin"}:
            raise ValueError("invalid_revision_edit_fields")
        if not {"op", "path", "value"} <= set(patch):
            raise ValueError("missing_revision_edit_fields")
        code = edit_path_code(patch["path"], patch["op"])
        if code != "replace_design_field":
            raise ValueError(code)
        code, before = pointer_value(session, patch["path"])
        if code != "ok":
            raise ValueError(code)
        _replace(session, patch)
        steps = patch["path"][1:].split("/")
        if steps[0] == "premises":
            if len(steps) == 1:
                whole_premises = True
            elif steps[1].isdecimal():
                index = int(steps[1])
                if len(steps) == 2 or steps[2] == "origin":
                    attributed.add(index)
                if "origin" in patch:
                    if type(session["premises"][index]) is not dict:
                        raise ValueError("edited_premise_not_an_object")
                    session["premises"][index]["origin"] = deepcopy(patch["origin"])
                    attributed.add(index)
        elif "origin" in patch:
            raise ValueError("edit_origin_requires_premise")
        reviewed.append(
            {"path": patch["path"], "before": deepcopy(before), "after": deepcopy(patch["value"])}
        )
    old = {item["id"]: item for item in previous.get("premises", [])}
    for index, item in enumerate(session.get("premises", [])):
        if type(item) is not dict or "id" not in item or "payload" not in item:
            raise ValueError("edited_premise_invalid")
        before = old.get(item["id"])
        changed = before is None or not source_evidence.exact_json_equal(before["payload"], item["payload"])
        if changed and not (whole_premises or index in attributed):
            raise ValueError("changed_premise_origin_required")
        if changed and "origin" not in item:
            raise ValueError("changed_premise_origin_required")
        if before is not None and before.get("kind") == "source_assertion" and changed:
            raise ValueError("source_premise_requires_new_binding")
    session["revision"] = revision
    session["parent_digest"] = None
    return session, reviewed


def execute(
    request: dict,
    *,
    store: Path | None = None,
    response_view: str = "full",
    intent: str = "unspecified",
    question: str = "",
    max_bytes: int = clinical_delivery.DEFAULT_BYTES,
    _delivery: dict | None = None,
) -> dict:
    """Compute once, retain when requested, and return a full or referenced compact reply."""
    from TrialLedger.layer2 import run

    if response_view not in ("full", "compact"):
        raise ValueError("unsupported_response_view")
    code = clinical_delivery.compact_budget_code(max_bytes)
    if code != "valid_compact_budget":
        raise ValueError(code)
    if response_view == "compact" and store is None:
        raise ValueError("compact_requires_artifact_store")
    # Validate presentation before invoking a potentially expensive computation.
    clinical_delivery.present({}, intent=intent, question=question)
    response = clinical_delivery.present(run(request), intent=intent, question=question)
    if _delivery is not None:
        response["delivery"] = deepcopy(_delivery)
    if store is None:
        return response
    artifact = reasoning_artifacts.save(store, request, response)
    return (
        clinical_delivery.compact(response, artifact, max_bytes=max_bytes)
        if response_view == "compact"
        else {
            **response,
            "artifact": artifact,
        }
    )


def revise(
    store: Path,
    identity: str,
    *,
    session: dict | None = None,
    revision: str | None = None,
    edits: list | None = None,
    response_view: str = "compact",
    intent: str = "unspecified",
    question: str = "",
    max_bytes: int = clinical_delivery.DEFAULT_BYTES,
    prepare_only: bool = False,
) -> dict:
    """Prepare or run a fresh revision through public retained state, with explicit edits."""
    code = clinical_delivery.compact_budget_code(max_bytes)
    if code != "valid_compact_budget":
        raise ValueError(code)
    if (session is None) == (edits is None):
        raise ValueError("revision_requires_session_or_edits")
    prior = reasoning_artifacts.load(store, identity)
    if (
        type(prior["request"]) is not dict
        or prior["request"].get("operation") != "design_session"
        or prior["response"].get("code") != "complete"
    ):
        raise ValueError("revision_requires_complete_session")
    review = []
    if edits is not None:
        if not isinstance(revision, str):
            raise ValueError("revision_label_required_for_edits")
        session, review = edited_session(prior["request"]["session"], revision, edits)
    elif revision is not None:
        raise ValueError("revision_label_is_in_explicit_session")
    if type(session) is not dict:
        raise ValueError("revision_session_not_an_object")
    request = reasoning_artifacts.revision(store, identity, session)
    if type(prepare_only) is not bool:
        raise ValueError("prepare_only_not_boolean")
    if prepare_only:
        return {"code": "prepared", "request": request, "previous_artifact": identity, "edits": review}
    return execute(
        request,
        store=store,
        response_view=response_view,
        intent=intent,
        question=question,
        max_bytes=max_bytes,
        _delivery={"previous_artifact": identity, "edits": review},
    )
