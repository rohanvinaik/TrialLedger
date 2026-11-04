from __future__ import annotations

import hashlib

import pytest

from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger.record_access import response_bytes


@pytest.mark.parametrize("value", [None, False, "", "0" * 63, "A" * 64, "../" + "0" * 64])
def test_artifact_identity_cannot_select_a_path_or_partial_fingerprint(value):
    assert artifacts.artifact_id_code(value) == "invalid_artifact_id"


def test_complete_lowercase_identity_is_valid():
    assert artifacts.artifact_id_code("a1" * 32) == "valid_artifact_id"


@pytest.mark.parametrize(
    ("size", "maximum", "code"),
    [
        (0, 10, "invalid_artifact_size"),
        (True, 10, "invalid_artifact_size"),
        (1, False, "invalid_artifact_size"),
        (9, 10, "within_artifact_limit"),
        (10, 10, "within_artifact_limit"),
        (11, 10, "artifact_too_large"),
    ],
)
def test_artifact_size_has_exact_boundary_and_named_remedies(size, maximum, code):
    assert artifacts.artifact_size_code(size, maximum) == code


def test_storage_preserves_complete_inputs_and_is_immutable_idempotent(tmp_path):
    request = {"operation": "entailment", "source": "完整\r\n" * 1000, "zero": 0, "false": False}
    response = {"code": "complete", "operation": "entailment", "result": {"answer": None}}
    first = artifacts.save(tmp_path, request, response)
    before = (tmp_path / f"{first['id']}.json").read_bytes()
    assert artifacts.save(tmp_path, request, response) == first
    assert (tmp_path / f"{first['id']}.json").read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == first["id"]
    assert artifacts.load(tmp_path, first["id"]) == {
        "schema_version": 1,
        "request": request,
        "response": response,
    }
    assert list(tmp_path.iterdir()) == [tmp_path / f"{first['id']}.json"]


def test_changed_existing_artifact_is_never_replaced(tmp_path):
    held = artifacts.save(tmp_path, {}, {})
    path = tmp_path / f"{held['id']}.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(artifacts.ArtifactError, match="artifact_changed"):
        artifacts.save(tmp_path, {}, {})
    assert path.read_bytes().endswith(b" ")


def test_missing_and_symlink_artifacts_are_distinct_refusals(tmp_path):
    with pytest.raises(artifacts.ArtifactError, match="artifact_missing"):
        artifacts.load(tmp_path, "0" * 64)
    held = artifacts.save(tmp_path, {}, {})
    (tmp_path / ("0" * 64 + ".json")).symlink_to(tmp_path / f"{held['id']}.json")
    with pytest.raises(artifacts.ArtifactError, match="artifact_symlink_refused"):
        artifacts.load(tmp_path, "0" * 64)


def test_matching_hash_does_not_admit_an_unknown_artifact_schema(tmp_path):
    body = b'{"schema_version":true,"request":{},"response":{}}'
    identity = hashlib.sha256(body).hexdigest()
    (tmp_path / f"{identity}.json").write_bytes(body)
    with pytest.raises(artifacts.ArtifactError, match="artifact_schema_invalid"):
        artifacts.load(tmp_path, identity)


def test_store_limit_refuses_before_creating_files(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "MAX_ARTIFACT_BYTES", 16)
    with pytest.raises(artifacts.ArtifactError, match="artifact_too_large"):
        artifacts.save(tmp_path, {}, {})
    assert not list(tmp_path.iterdir())


def test_address_pages_reconstruct_complete_long_text(tmp_path):
    text = "α\r\n\t末 " * 3000
    held = artifacts.save(tmp_path, {}, {"result": {"text": text}})
    offset, chunks = 0, []
    while offset is not None:
        reply = artifacts.read(
            tmp_path,
            held["id"],
            {
                "part": "address",
                "address": "/response/result/text",
                "text_offset": offset,
                "max_bytes": 2048,
            },
        )
        assert response_bytes(reply) <= 2048
        chunks.append(reply["text"])
        offset = reply["text_page"]["next_offset"]
    assert "".join(chunks) == text


def test_large_values_return_exact_navigation_not_shortened_values(tmp_path):
    value = {"a/b": {"text": "z" * 10000}}
    held = artifacts.save(tmp_path, {}, {"result": value})
    reply = artifacts.read(tmp_path, held["id"], {"part": "result", "max_bytes": 2048})
    assert reply["navigation"] == "addresses"
    assert reply["entries"][0]["address"] == "/response/result/a~1b"
    full = artifacts.load(tmp_path, held["id"])
    assert full["response"]["result"] == value


@pytest.mark.parametrize(
    "arguments",
    [
        True,
        {"part": "made-up"},
        {"limit": True},
        {"offset": False},
        {"limit": 0},
        {"max_bytes": False},
        {"unrecognized": 1},
        {"part": "result", "address": "/request"},
    ],
)
def test_malformed_access_cannot_be_accepted_as_inert_input(tmp_path, arguments):
    held = artifacts.save(tmp_path, {}, {"result": 0})
    with pytest.raises(artifacts.ArtifactError):
        artifacts.read(tmp_path, held["id"], arguments)


def test_canonical_store_refuses_nonfinite_values(tmp_path):
    with pytest.raises(artifacts.ArtifactError, match="artifact_payload_invalid"):
        artifacts.save(tmp_path, {"value": float("nan")}, {})
    assert not list(tmp_path.iterdir())
