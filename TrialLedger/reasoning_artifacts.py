"""Immutable reasoning delivery, separate from source reports and symbolic computation."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

from TrialLedger.evidence_access import page_window, pointer_value
from TrialLedger.record_access import DEFAULT_BYTES, MAX_BYTES, MIN_BYTES, bounded_view, response_bytes

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
PARTS = {
    "request": "/request",
    "response": "/response",
    "result": "/response/result",
    "clinical": "/response/clinical",
    "summary": "/response/summary",
    "session": "/request/session",
    "decisions": "/response/result/decisions",
    "decision_view": "/response/decision_view",
    "changes": "/response/answer_diff",
}


class ArtifactError(ValueError):
    """A named storage/access refusal; no source or reasoning result is rewritten."""


def artifact_id_code(value: object) -> str:
    """Only a complete lowercase SHA256 selects an artifact (pure — pinned).

    post: __return__ in ('valid_artifact_id', 'invalid_artifact_id')
    """
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        return "invalid_artifact_id"
    return "valid_artifact_id"


def artifact_size_code(size: int, maximum: int) -> str:
    """Empty/malformed and oversized bodies require different remedies (pure — pinned).

    post: __return__ in ('invalid_artifact_size', 'artifact_too_large', 'within_artifact_limit')
    """
    if type(size) is not int or type(maximum) is not int or size < 1 or maximum < 1:
        return "invalid_artifact_size"
    return "artifact_too_large" if size > maximum else "within_artifact_limit"


def _path(root: Path, identity: object) -> Path:
    code = artifact_id_code(identity)
    if code != "valid_artifact_id":
        raise ArtifactError(code)
    return Path(root) / f"{identity}.json"


def load(root: Path, identity: object) -> dict[str, Any]:
    """Read and verify the exact canonical payload, refusing symlinks and changed bytes."""
    from TrialLedger.landscape_verify import strict_json

    path = _path(root, identity)
    if path.is_symlink():
        raise ArtifactError("artifact_symlink_refused")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            information = os.fstat(stream.fileno())
            if not stat.S_ISREG(information.st_mode):
                raise ArtifactError("artifact_not_regular_file")
            code = artifact_size_code(information.st_size, MAX_ARTIFACT_BYTES)
            if code != "within_artifact_limit":
                raise ArtifactError(code)
            body = stream.read(MAX_ARTIFACT_BYTES + 1)
            if artifact_size_code(len(body), MAX_ARTIFACT_BYTES) != "within_artifact_limit":
                raise ArtifactError("artifact_too_large")
    except FileNotFoundError as error:
        raise ArtifactError("artifact_missing") from error
    except OSError as error:
        raise ArtifactError("artifact_unreadable") from error
    if hashlib.sha256(body).hexdigest() != identity:
        raise ArtifactError("artifact_changed")
    try:
        payload = strict_json(body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ArtifactError("artifact_malformed") from error
    if (
        type(payload) is not dict
        or set(payload) != {"schema_version", "request", "response"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or type(payload["response"]) is not dict
    ):
        raise ArtifactError("artifact_schema_invalid")
    return payload


def save(root: Path, request: object, response: dict) -> dict[str, Any]:
    """Atomically retain a complete request/response; a collision never overwrites bytes."""
    from TrialLedger.layer2.session_state import canonical

    if type(response) is not dict:
        raise ArtifactError("artifact_response_not_an_object")
    payload = {"schema_version": 1, "request": request, "response": response}
    try:
        body = canonical(payload).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
        raise ArtifactError("artifact_payload_invalid") from error
    code = artifact_size_code(len(body), MAX_ARTIFACT_BYTES)
    if code != "within_artifact_limit":
        raise ArtifactError(code)
    identity = hashlib.sha256(body).hexdigest()
    path = _path(root, identity)
    temporary = None
    try:
        Path(root).mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(dir=root, prefix=".artifact-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if canonical(load(root, identity)).encode("utf-8") != body:
                raise ArtifactError("artifact_collision") from None
    except OSError as error:
        raise ArtifactError("artifact_store_unwritable") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "id": identity,
        "bytes": len(body),
        "schema_version": 1,
        "identity_scope": "SHA256 of complete canonical request/response payload bytes",
        "parts": ["manifest", *PARTS, "address"],
    }


def manifest(payload: dict, identity: str) -> dict:
    """The artifact's public navigation and scoped fingerprints, without echoed inputs."""
    response = payload["response"]
    return {
        "id": identity,
        "schema_version": payload["schema_version"],
        "operation": response.get("operation"),
        "code": response.get("code"),
        "result_digest": response.get("result_digest"),
        "result_digest_scope": "response.result, distinct from the complete artifact identity",
        "parts": ["manifest", *PARTS, "address"],
    }


def read(root: Path, identity: object, arguments: dict | None = None) -> dict:
    """Bounded exact access reuses the source-record paging and pointer owners."""
    if arguments is not None and type(arguments) is not dict:
        raise ArtifactError("artifact_access_not_an_object")
    args = dict(arguments or {})
    allowed = {"part", "address", "offset", "limit", "max_bytes", "text_offset", "text_limit"}
    if set(args) - allowed:
        raise ArtifactError("unknown_artifact_access_field")
    payload = load(root, identity)
    part = args.get("part", "manifest")
    if "address" in args and part != "address":
        raise ArtifactError("artifact_address_requires_address_part")
    if part == "manifest":
        whole, address = manifest(payload, str(identity)), ""
    elif part == "address":
        address = args.get("address")
        if not isinstance(address, str):
            raise ArtifactError("not_a_pointer")
        code, whole = pointer_value(payload, address)
        if code != "ok":
            raise ArtifactError(code)
    elif isinstance(part, str) and part in PARTS:
        address = PARTS[part]
        code, whole = pointer_value(payload, address)
        if code != "ok":
            raise ArtifactError("artifact_part_unavailable")
    else:
        raise ArtifactError("unsupported_artifact_part")
    offset, limit = args.get("offset", 0), args.get("limit", 50)
    budget = args.get("max_bytes", DEFAULT_BYTES)
    if type(offset) is not int or type(limit) is not int:
        raise ArtifactError("artifact_page_not_integers")
    if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:
        raise ArtifactError("max_bytes_out_of_range")
    container = isinstance(whole, (dict, list))
    code, page = page_window(len(whole) if container else 0, offset, limit)
    if code != "ok":
        raise ArtifactError(code)
    if not container:
        page = None
    args["part"] = "address"
    while True:
        code, view = bounded_view(whole, address, "value", page, args)
        if code != "ok":
            raise ArtifactError(code)
        reply = {"code": "complete", "artifact": identity, "part": part, **view}
        if response_bytes(reply) <= budget:
            return reply
        if page is not None and page["returned"] > 1:
            _, page = page_window(len(whole), offset, max(1, page["returned"] // 2))
        elif isinstance(whole, str) and "text_offset" not in args:
            args["text_offset"] = 0
        else:
            raise ArtifactError("value_too_large")


def revision(root: Path, identity: object, next_session: dict) -> dict:
    """Public revision preparation over verified retained state, without clinical interpretation."""
    from TrialLedger.layer2.design_session import prepare_revision

    payload = load(root, identity)
    return prepare_revision(payload["request"], payload["response"], next_session)
