"""Task-sized discovery and lossless evidence navigation through the public assistant surface.

The limits must never turn a directory/chunk into a source value, skip requested entries, normalize
text, or change a saved report. The worked brief must enforce the range it tells the clinician.
"""

from __future__ import annotations

import copy
import json

import pytest

from TrialLedger.layer2 import run
from TrialLedger.mcp_server import Context, call_tool, record_view
from TrialLedger.record_access import MAX_BYTES, MIN_BYTES, bounded_view, response_bytes, text_window


def test_default_discovery_is_small_and_points_to_every_focused_guide():
    reply = run({"operation": "describe"})
    assert reply["code"] == "complete" and response_bytes(reply) < 8_192
    overview = reply["result"]
    assert "worked_session" not in overview and "tagged_model" not in overview
    assert set(overview["discovery"]) == {
        "overview",
        "entailment",
        "coordinates",
        "corpus",
        "design_bounds",
        "worked_session",
        "full",
    }
    assert len(overview["availability"]["built"]) == 4
    for operation in ("entailment", "coordinates", "corpus", "design_bounds"):
        focused = run(overview["discovery"][operation])["result"]
        assert run(focused["example"])["code"] == "complete"
        assert operation in focused["input_shapes"]
        assert focused["result_guide"] and focused["answer_guide"][operation]
        assert "worked_session" not in focused and "developer_building_blocks" not in focused
        other_operations = {"entailment", "coordinates", "corpus", "design_bounds"} - {operation}
        assert not other_operations.intersection(focused["input_shapes"])
    assert "tagged_model" in run(overview["discovery"]["entailment"])["result"]
    assert "worked_session" in run(overview["discovery"]["worked_session"])["result"]
    assert "developer_building_blocks" in run(overview["discovery"]["full"])["result"]


@pytest.mark.parametrize("view", [None, [], {}, 0, True, "", "unknown"])
def test_discovery_refuses_unknown_or_malformed_views(view):
    reply = run({"operation": "describe", "view": view})
    assert reply["code"] == "refused" and reply["result"] is None
    assert reply["problems"] == ["request.view:unsupported_view"]


@pytest.mark.parametrize(
    "score,expected", [(-1, "REFUTED"), (0, "UNDETERMINED"), (1, "UNDETERMINED"), (2, "REFUTED")]
)
def test_worked_ecog_range_matches_both_inclusive_bounds(score, expected):
    session = run({"operation": "describe", "view": "worked_session"})["result"]["worked_session"]
    request = copy.deepcopy(session["steps"][2]["request"])
    request["query"]["value"]["number"] = score
    reply = run(request)
    assert reply["code"] == "complete"
    assert reply["result"]["decision"]["result"] == expected
    assert reply["result"]["decision"]["proof"] == ("ecog",)


def test_revising_a_premise_recomputes_the_answer_without_changing_the_original():
    session = run({"operation": "describe", "view": "worked_session"})["result"]["worked_session"]
    original = session["steps"][2]["request"]
    request = copy.deepcopy(original)
    assert run(request)["result"]["decision"]["result"] == "REFUTED"
    request["assertions"][1]["body"]["parts"][1]["value"]["number"] = 2
    assert run(request)["result"]["decision"]["result"] == "UNDETERMINED"
    assert run(original)["result"]["decision"]["result"] == "REFUTED"


def test_text_window_is_lossless_and_progresses_with_escaped_and_multibyte_text():
    original = 'é\n"\\\x00\U0001f9ec e\u0301\ud800' * 1_000
    offset, chunks = 0, []
    while True:
        code, reply = text_window(original, offset, 8_192, MIN_BYTES)
        assert code == "ok" and response_bytes(reply) <= MIN_BYTES
        assert reply["text_page"]["offset"] == offset
        assert reply["text_page"]["returned"] == len(reply["text"]) > 0
        chunks.append(reply["text"])
        following = reply["text_page"]["next_offset"]
        if following is None:
            break
        assert following > offset
        offset = following
    assert "".join(chunks) == original
    assert len(chunks) > 1


def test_text_window_keeps_empty_text_and_exact_limit_boundaries():
    assert text_window("", 0, 1, MIN_BYTES) == (
        "ok",
        {"text": "", "text_page": {"offset": 0, "returned": 0, "total": 0, "next_offset": None}},
    )
    assert text_window("abc", 0, 3, MAX_BYTES)[1]["text_page"]["next_offset"] is None
    assert text_window("abc", 0, 2, MIN_BYTES)[1]["text_page"]["next_offset"] == 2
    assert text_window("abc", 2, 1, MIN_BYTES)[1]["text"] == "c"


@pytest.mark.parametrize("offset", [-1, 3, None, True, "0"])
def test_text_window_must_not_accept_an_invalid_character_offset(offset):
    assert text_window("abc", offset, 1, MIN_BYTES) == ("text_offset_out_of_range", {})


@pytest.mark.parametrize("limit", [0, -1, 8_193, None, True])
def test_text_window_must_not_accept_an_invalid_character_limit(limit):
    assert text_window("abc", 0, limit, MIN_BYTES) == ("text_limit_out_of_range", {})


@pytest.mark.parametrize("budget", [0, MIN_BYTES - 1, MAX_BYTES + 1, None, True])
def test_text_window_must_not_accept_an_invalid_response_budget(budget):
    assert text_window("abc", 0, 1, budget) == ("max_bytes_out_of_range", {})


def test_small_values_keep_types_and_large_values_become_navigation_not_fake_values():
    record = {"schema_version": 4, "studies": [{"nct": "NCT00000001", "safety": {"huge/~": "x" * 5_000}}]}
    arguments = {"part": "study", "nct": "NCT00000001", "max_bytes": MIN_BYTES}
    before = copy.deepcopy(record)
    code, reply = record_view(record, arguments)
    assert code == "ok" and response_bytes(reply) <= MIN_BYTES
    assert "study" not in reply and reply["navigation"] == "addresses"
    assert {item["address"] for item in reply["entries"]} == {"/studies/0/nct", "/studies/0/safety"}
    _, child = record_view(
        record, {"part": "address", "address": "/studies/0/safety", "max_bytes": MIN_BYTES}
    )
    assert child["entries"][0]["address"] == "/studies/0/safety/huge~1~0"
    assert record == before
    for value in (None, False, 0, "", [], {}):
        record["studies"][0]["value"] = value
        code, result = record_view(record, {"part": "address", "address": "/studies/0/value"})
        assert code == "ok" and result["value"] == value
        assert type(result["value"]) is type(value)


def test_byte_limited_directory_pages_cover_every_entry_once():
    whole = {f"item-{index}-{'x' * 50}": {"large": "z" * 4_000} for index in range(120)}
    record = {"schema_version": 4, "studies": [whole]}
    offset, seen = 0, []
    while True:
        code, reply = record_view(
            record,
            {
                "part": "study",
                "nct": None,
                "offset": offset,
                "max_bytes": MIN_BYTES,
            }
            | {"part": "address", "address": "/studies/0"},
        )
        assert code == "ok" and response_bytes(reply) <= MIN_BYTES
        assert reply["navigation"] == "addresses"
        seen.extend(entry["key"] for entry in reply["entries"])
        assert reply["page"]["returned"] == len(reply["entries"])
        if reply["page"]["next_offset"] is None:
            break
        assert reply["page"]["next_offset"] > offset
        offset = reply["page"]["next_offset"]
    assert seen == list(whole)


def test_record_tool_delivers_exact_long_text_in_chunks_without_changing_files(tmp_path):
    folder = tmp_path / "clinical-review"
    folder.mkdir()
    original = 'Exact eligibility: é\n"\\\U0001f9ec ' * 2_000
    record = {"schema_version": 4, "studies": [{"nct": "NCT00000001", "eligibility": original}]}
    path = folder / "landscape.json"
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    offset, chunks = 0, []
    while True:
        code, response = call_tool(
            Context(tmp_path),
            {
                "name": "record",
                "arguments": {
                    "run": folder.name,
                    "part": "address",
                    "address": "/studies/0/eligibility",
                    "max_bytes": MIN_BYTES,
                    "text_offset": offset,
                },
            },
        )
        assert code == "ok" and not response["isError"]
        reply = json.loads(response["content"][0]["text"])
        assert "value" not in reply
        assert len(response["content"][0]["text"].encode()) <= MIN_BYTES + 1_024
        chunks.append(reply["text"])
        following = reply["text_page"]["next_offset"]
        if following is None:
            break
        offset = following
    assert "".join(chunks) == original and path.read_bytes() == before


def test_record_budget_refusals_are_named_and_do_not_return_partial_source_values():
    record = {"schema_version": 4, "studies": [{"nct": "NCT00000001", "value": 0}]}
    assert record_view(record, {"part": "study", "nct": "NCT00000001", "max_bytes": 0}) == (
        "max_bytes_out_of_range",
        {},
    )
    assert record_view(record, {"part": "address", "address": "/studies/0/value", "text_offset": 0}) == (
        "not_text",
        {},
    )
    assert bounded_view(
        "x",
        "/" + "x" * 3_000,
        "value",
        None,
        {
            "part": "address",
            "max_bytes": MIN_BYTES,
        },
    ) == ("value_too_large", {})


def test_independent_reviewer_follows_directories_and_text_continuations(tmp_path):
    from acceptance.reviewer import mcp_ask

    folder = tmp_path / "nested"
    folder.mkdir()
    study = {"nct": "NCT00000001", "nested": [{"a/~": "exact é\n" * 10_000}, {"zero": 0, "flag": False}]}
    path = folder / "landscape.json"
    path.write_text(json.dumps({"schema_version": 4, "studies": [study]}))
    before = path.read_bytes()
    assert mcp_ask(tmp_path, folder.name)("/studies/0") == ("ok", study)
    assert path.read_bytes() == before


def test_a_missing_id_does_not_dump_a_large_study_index_into_the_error():
    record = {"schema_version": 4, "studies": [{"nct": f"NCT{i:08d}"} for i in range(500)]}
    code, reply = record_view(record, {"part": "study", "nct": "NCT99999999", "max_bytes": MIN_BYTES})
    assert code == "no_such_study" and response_bytes(reply) <= MIN_BYTES
    assert reply == {"held_count": 500, "next": {"part": "studies", "offset": 0}}
