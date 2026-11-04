"""A raw-source handle preserves evidence, never authenticates a reading or adoption.

All study values and clinical choices here are explicitly invented transport fixtures.
"""

import json
from copy import deepcopy

import pytest
from test_session_revision_delivery import request as session_request

from TrialLedger import reasoning_artifacts, retained_sources
from TrialLedger.cli import main
from TrialLedger.evidence_access import read_record
from TrialLedger.layer2 import source_evidence
from TrialLedger.mcp_server import Context, call_tool
from TrialLedger.retained_sources import source_marker_code
from TrialLedger.warrants import study_digest

NCT = "NCT00000001"
ADDRESS = "/protocolSection/eligibilityModule/eligibilityCriteria"


def saved(root, text="Invented eligibility: α\r\nDo not normalize."):
    folder = root / "source-run"
    (folder / "bodies").mkdir(parents=True)
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT},
            "statusModule": {},
            "eligibilityModule": {"minimumAge": "18 Years", "eligibilityCriteria": text},
        },
        "retained_values": {"false": False, "zero": 0, "empty": [], "null": None},
    }
    digest = study_digest(study)
    manifest = {"study_digests": [digest]}
    record = {
        "schema_version": 4,
        "manifest": manifest,
        "studies": [{"nct": NCT, "digest": digest}],
    }
    fetches = [{"why": "studies_batch", "file": "studies-001.json", "save_as": "bodies/studies-001.json"}]
    for name, value in (
        ("manifest.json", manifest),
        ("landscape.json", record),
        ("fetches.json", fetches),
        ("bodies/studies-001.json", {"studies": [study]}),
    ):
        (folder / name).write_text(json.dumps(value, ensure_ascii=False))
    marker = {"$retained_study": {"run": folder.name, "nct": NCT, "digest": digest}}
    return folder, study, marker


def with_evidence(marker, text):
    request = session_request()
    session = request["session"]
    session["sources"] = [
        {"id": "source", "study": marker, "expected_digest": marker["$retained_study"]["digest"]}
    ]
    other = deepcopy(session["analyses"][0])
    other["id"] = "not-A-check"
    other["parameters"]["query"] = {"class": "Not", "part": deepcopy(other["parameters"]["query"])}
    session["analyses"].append(other)
    session["decisions"] = [
        {
            "id": "invented-choice",
            "question": "Invented A or not A?",
            "target": deepcopy(session["target"]),
            "coverage": "represented_restriction",
            "selected": None,
            "alternatives": [
                {
                    "id": "A",
                    "label": "Caller label A",
                    "analysis": "A-check",
                    "query": deepcopy(session["analyses"][0]["parameters"]["query"]),
                },
                {
                    "id": "not-A",
                    "label": "Caller label not A",
                    "analysis": "not-A-check",
                    "query": deepcopy(other["parameters"]["query"]),
                },
            ],
            "evidence": [
                {
                    "id": "quoted",
                    "source": "source",
                    "role": "quote",
                    "anchor": {
                        "id": "quoted",
                        "address": ADDRESS,
                        "digest": marker["$retained_study"]["digest"],
                        "expected": text,
                    },
                }
            ],
        }
    ]
    return request


def mcp(root, name, arguments):
    code, reply = call_tool(Context(root), {"name": name, "arguments": arguments})
    assert code == "ok"
    payload = json.loads(reply["content"][0]["text"])
    payload.pop("tool")
    return payload, reply["isError"]


@pytest.mark.parametrize("run", ["", ".", "..", "../other", "/absolute", "a/b", "a\\b", "a" * 101])
def test_source_reference_never_accepts_a_path_as_a_run(run):
    assert source_marker_code(run, NCT, "a" * 64) == "invalid_source_run"


@pytest.mark.parametrize("nct", ["", "NCT1", "nct00000001", NCT + "\n", "NCT000000010"])
def test_source_reference_requires_whole_canonical_nct(nct):
    assert source_marker_code("run", nct, "a" * 64) == "invalid_source_nct"


@pytest.mark.parametrize("digest", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n"])
def test_source_reference_never_accepts_partial_or_noncanonical_digest(digest):
    assert source_marker_code("run", NCT, digest) == "invalid_source_digest"


def test_valid_source_reference_is_a_named_code():
    assert source_marker_code("run.1-x_y", NCT, "a1" * 32) == "source_reference"


def test_source_record_cli_mcp_share_exact_raw_value_and_snapshot(tmp_path, capsys):
    folder, study, _ = saved(tmp_path)
    expected = study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    assert main(["record", str(folder), "--part", "source", "--nct", NCT, "--address", ADDRESS]) == 0
    cli = json.loads(capsys.readouterr().out)
    remote, error = mcp(
        tmp_path, "record", {"run": folder.name, "part": "source", "nct": NCT, "address": ADDRESS}
    )
    assert not error
    assert cli == {"tool": "record", **remote}
    assert remote["value"] == expected
    snapshot = source_evidence.snapshot(study)
    assert remote["snapshot"] == {key: snapshot[key] for key in ("nct", "digest", "study_ref")}


def test_raw_source_text_continuation_is_lossless_and_evidence_unchanged(tmp_path):
    text = "α\r\n\tFalse is not zero. " * 1000
    folder, study, _ = saved(tmp_path, text)
    before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    offset, parts = 0, []
    while offset is not None:
        reply, error = read_record(
            folder,
            {"part": "source", "nct": NCT, "address": ADDRESS, "text_offset": offset, "max_bytes": 2048},
        )
        assert not error
        assert reply["snapshot"]["digest"] == study_digest(study)
        parts.append(reply["text"])
        offset = reply["text_page"]["next_offset"]
    assert len(parts) > 1
    assert "".join(parts) == text
    assert before == {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


@pytest.mark.parametrize("name,expected", [("false", False), ("zero", 0), ("empty", []), ("null", None)])
def test_source_values_keep_false_zero_empty_and_null_distinct(tmp_path, name, expected):
    folder, _, _ = saved(tmp_path)
    reply, error = read_record(folder, {"part": "source", "nct": NCT, "address": "/retained_values/" + name})
    assert not error and reply["value"] == expected
    assert type(reply["value"]) is type(expected)


def test_study_marker_hydration_is_exact_and_does_not_mutate_caller(tmp_path):
    _, study, marker = saved(tmp_path)
    request = {"operation": "source_assertions", "study": marker, "expected_digest": study_digest(study)}
    before = deepcopy(request)
    hydrated = retained_sources.hydrate_request(request, tmp_path)
    assert hydrated == {**request, "study": study}
    assert request == before
    assert hydrated["study"] is not study


def test_marker_like_literal_data_outside_typed_slots_is_never_resolved(tmp_path):
    _, _, marker = saved(tmp_path)
    for request in (
        {"operation": "entailment", "query": marker},
        {"operation": "signals", "signals": [marker]},
        {"operation": "design_session", "session": {"premises": [{"payload": marker}]}},
    ):
        assert retained_sources.hydrate_request(request, tmp_path) == request


@pytest.mark.parametrize(
    "marker",
    [
        {"$retained_study": None},
        {"$retained_study": {}},
        {"$retained_study": {"run": "r", "nct": NCT, "digest": 1}},
        {"$retained_study": {"run": "r", "nct": NCT, "digest": "a" * 64}, "extra": 1},
    ],
)
def test_malformed_source_markers_refuse_named_without_filling_any_study(tmp_path, marker):
    with pytest.raises(ValueError, match="invalid_source_marker"):
        retained_sources.hydrate_request({"operation": "source_assertions", "study": marker}, tmp_path)


def test_source_reference_needs_explicit_cli_root(tmp_path):
    _, _, marker = saved(tmp_path)
    with pytest.raises(ValueError, match="source_root_required"):
        retained_sources.hydrate_request({"operation": "source_assertions", "study": marker}, None)


def test_stale_source_reference_does_not_take_current_snapshot_silently(tmp_path):
    _, _, marker = saved(tmp_path)
    marker["$retained_study"]["digest"] = "0" * 64
    with pytest.raises(ValueError, match="stale_source_digest"):
        retained_sources.hydrate_request({"operation": "source_assertions", "study": marker}, tmp_path)


def test_valid_handle_does_not_replace_a_conflicting_expected_digest(tmp_path):
    _, _, marker = saved(tmp_path)
    reply, error = mcp(
        tmp_path,
        "reason",
        {"request": {"operation": "source_assertions", "study": marker, "expected_digest": "0" * 64}},
    )
    assert error and reply["code"] == "refused"
    assert reply["problems"] == ["source_digest_mismatch"]


def test_source_body_changes_are_detected_against_recorded_digest(tmp_path):
    folder, _, _ = saved(tmp_path)
    (folder / "bodies/studies-001.json").write_text(
        json.dumps({"studies": [{"protocolSection": {"identificationModule": {"nctId": NCT}}}]})
    )
    reply, error = read_record(folder, {"part": "source", "nct": NCT})
    assert error and reply["error"] == "source_body_digest_mismatch"


def test_duplicate_raw_identity_and_duplicate_json_keys_are_refused(tmp_path):
    folder, study, _ = saved(tmp_path)
    body = folder / "bodies/studies-001.json"
    body.write_text(json.dumps({"studies": [study, study]}))
    reply, error = read_record(folder, {"part": "source", "nct": NCT})
    assert error and reply["error"] == "source_study_not_unique"
    body.write_text('{"studies": [], "studies": []}')
    reply, error = read_record(folder, {"part": "source", "nct": NCT})
    assert error and "duplicate" in reply["error"].lower()


def test_record_manifest_and_index_digest_must_agree(tmp_path):
    folder, _, _ = saved(tmp_path)
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps({"study_digests": ["0" * 64]}))
    reply, error = read_record(folder, {"part": "source", "nct": NCT})
    assert error and reply["error"] == "source_manifest_mismatch"
    record = json.loads((folder / "landscape.json").read_text())
    record["manifest"]["study_digests"] = ["0" * 64]
    (folder / "landscape.json").write_text(json.dumps(record))
    reply, error = read_record(folder, {"part": "source", "nct": NCT})
    assert error and reply["error"] == "source_record_digest_mismatch"


def test_quoted_source_marker_property_is_not_recursively_executed(tmp_path):
    folder, study, marker = saved(tmp_path)
    study["retained_values"]["nested"] = {"$retained_study": {"run": "../outside"}}
    digest = study_digest(study)
    marker["$retained_study"]["digest"] = digest
    manifest = {"study_digests": [digest]}
    (folder / "manifest.json").write_text(json.dumps(manifest))
    (folder / "landscape.json").write_text(
        json.dumps({"schema_version": 4, "manifest": manifest, "studies": [{"nct": NCT, "digest": digest}]})
    )
    (folder / "bodies/studies-001.json").write_text(json.dumps({"studies": [study]}))
    hydrated = retained_sources.hydrate_request({"operation": "source_assertions", "study": marker}, tmp_path)
    assert hydrated["study"] == study
    assert hydrated["study"]["retained_values"]["nested"] == {"$retained_study": {"run": "../outside"}}


@pytest.mark.parametrize(
    "arguments,code",
    [
        ({}, "invalid_source_nct"),
        ({"nct": NCT, "address": None}, "not_a_pointer"),
        ({"nct": NCT, "max_bytes": 0}, "max_bytes_out_of_range"),
        ({"nct": NCT, "limit": 0}, "limit_out_of_range"),
        ({"nct": NCT, "address": "/missing"}, "outside_record"),
    ],
)
def test_source_access_malformed_and_boundary_inputs_remain_named(tmp_path, arguments, code):
    folder, _, _ = saved(tmp_path)
    reply, error = read_record(folder, {"part": "source", **arguments})
    assert error and reply["error"] == code


def test_source_handle_cannot_follow_run_or_body_link_outside_root(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    folder, _, marker = saved(outside)
    root.mkdir()
    (root / folder.name).symlink_to(folder)
    with pytest.raises(ValueError, match="source_run_outside_root"):
        retained_sources.hydrate_request({"operation": "source_assertions", "study": marker}, root)
    local, _, _ = saved(root / "local")
    body = local / "bodies/studies-001.json"
    body.unlink()
    body.symlink_to(folder / "bodies/studies-001.json")
    reply, error = read_record(local, {"part": "source", "nct": NCT})
    assert error and reply["error"] == "source_file_outside_run"


def test_canonical_retention_revision_export_keep_mcp_source_quote(tmp_path, capsys):
    folder, study, marker = saved(tmp_path)
    text = study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    request = with_evidence(marker, text)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    store = tmp_path / ".reasoning"
    assert (
        main(
            [
                "reason",
                "--request",
                str(path),
                "--source-root",
                str(tmp_path),
                "--store",
                str(store),
                "--compact",
            ]
        )
        == 0
    )
    cli = json.loads(capsys.readouterr().out)
    remote, error = mcp(tmp_path, "reason", {"request": request, "response_view": "compact"})
    assert not error and remote == cli
    retained = reasoning_artifacts.load(store, remote["artifact"]["id"])
    assert retained["request"]["session"]["sources"][0]["study"] == study
    assert "$retained_study" not in retained["request"]["session"]["sources"][0]["study"]
    revised, error = mcp(
        tmp_path,
        "reason_revise",
        {
            "id": remote["artifact"]["id"],
            "revision": "two",
            "edits": [
                {"op": "replace", "path": "/decisions/0/question", "value": "Reworded invented question"}
            ],
        },
    )
    assert not error
    new = reasoning_artifacts.load(store, revised["artifact"]["id"])
    assert new["request"]["session"]["sources"][0]["study"] == study
    exported, error = mcp(tmp_path, "reason_export", {"id": revised["artifact"]["id"]})
    assert not error and exported["code"] == "complete"
    review = tmp_path / "reasoning-exports" / revised["artifact"]["id"] / "review"
    assert "Invented eligibility: α" in (review / "decision-list.md").read_text()
    assert "Do not normalize." in (review / "decision-list.md").read_text()
    assert new["request"]["session"]["decisions"][0]["evidence"][0]["anchor"]["expected"] == text
    assert study_digest(study) in (review / "decision-list.md").read_text()
    assert (
        retained["response"]["result"]["analyses"][0]["result"]["result"]["decision"]["result"] == "ENTAILED"
    )
    assert (folder / "bodies/studies-001.json").is_file()


def test_explicit_revision_session_can_reuse_digest_bound_source_handle(tmp_path):
    _, study, marker = saved(tmp_path)
    request = with_evidence(marker, study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"])
    held, error = mcp(tmp_path, "reason", {"request": request, "retain": True})
    assert not error
    session = deepcopy(request["session"])
    session["revision"] = "two"
    prepared, error = mcp(
        tmp_path, "reason_revise", {"id": held["artifact"]["id"], "session": session, "prepare_only": True}
    )
    assert not error
    assert prepared["request"]["session"]["sources"][0]["study"] == study
    assert request["session"]["sources"][0]["study"] == marker


def test_later_revisions_use_immutable_artifact_not_live_source_folder(tmp_path, monkeypatch):
    _, study, marker = saved(tmp_path)
    request = with_evidence(marker, study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"])
    held, error = mcp(tmp_path, "reason", {"request": request, "retain": True})
    assert not error

    def unavailable(*args, **kwargs):
        raise AssertionError("A retained complete snapshot must not reread the original source folder")

    monkeypatch.setattr(retained_sources, "load_study", unavailable)
    for revision in ("two", "three"):
        held, error = mcp(
            tmp_path,
            "reason_revise",
            {
                "id": held["artifact"]["id"],
                "revision": revision,
                "edits": [
                    {
                        "op": "replace",
                        "path": "/decisions/0/question",
                        "value": "Wording revision " + revision,
                    }
                ],
            },
        )
        assert not error and held["code"] == "complete"
        retained = reasoning_artifacts.load(tmp_path / ".reasoning", held["artifact"]["id"])
        assert retained["request"]["session"]["sources"][0]["study"] == study
