"""Source location proves exact retained values and quotation, never a clinical interpretation."""

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from TrialLedger.layer2 import source_evidence as evidence
from TrialLedger.warrants import study_digest


@pytest.fixture
def study():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00322452"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2013-11-07", "type": "ESTIMATED"}},
            "eligibilityModule": {"minimumAge": "18 Years", "healthyVolunteers": False},
        },
        "data": {"a/b": {"~1": [None, True, 1, "001", "é🧬18\n"]}, "": "empty-key"},
    }


def declare(study, address, expected, **extra):
    return {
        "id": "selected",
        "address": address,
        "digest": evidence.snapshot(study)["digest"],
        "expected": expected,
        **extra,
    }


def located(study, address, expected, **extra):
    return evidence.anchors(study, evidence.snapshot(study), [declare(study, address, expected, **extra)])


def test_snapshot_binds_complete_content_and_returns_an_independent_exact_update_object(study):
    before = copy.deepcopy(study)
    result = evidence.snapshot(study)
    digest = study_digest(study)
    assert result == {
        "nct": "NCT00322452",
        "digest": digest,
        "study_ref": f"ctg:NCT00322452:{digest}",
        "version": digest,
        "last_update": {"date": "2013-11-07", "type": "ESTIMATED"},
    }
    result["last_update"]["date"] = "changed"
    assert study == before
    study["data"]["added"] = 0
    assert evidence.snapshot(study)["digest"] != digest


def test_absent_and_explicit_null_update_have_no_invented_edition(study):
    del study["protocolSection"]["statusModule"]
    assert evidence.snapshot(study)["last_update"] is None
    study["protocolSection"]["statusModule"] = {"lastUpdatePostDateStruct": None}
    assert evidence.snapshot(study)["last_update"] is None


@pytest.mark.parametrize(
    "value", [None, [], {}, {"protocolSection": None}, {"protocolSection": {"identificationModule": []}}]
)
def test_snapshot_requires_raw_study_object_identity(value):
    with pytest.raises(evidence.BridgeError, match="not_an_object"):
        evidence.snapshot(value)


@pytest.mark.parametrize(
    "nct",
    ["NCT1234567", "NCT123456789", "nct00322452", "NCT00322452\n", "NCT００３２２４５２", 322452, True, None],
)
def test_snapshot_requires_complete_ascii_nct_identity(study, nct):
    study["protocolSection"]["identificationModule"]["nctId"] = nct
    with pytest.raises(evidence.BridgeError, match="invalid_nct"):
        evidence.snapshot(study)


@pytest.mark.parametrize("status", [None, [], "date"])
def test_malformed_status_module_is_not_an_absent_update(study, status):
    study["protocolSection"]["statusModule"] = status
    with pytest.raises(evidence.BridgeError, match="not_an_object:study.statusModule"):
        evidence.snapshot(study)


def test_scalar_update_does_not_become_a_version(study):
    study["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"] = "2013-11-07"
    with pytest.raises(evidence.BridgeError, match="not_an_object:study.last_update"):
        evidence.snapshot(study)


def test_pointer_escapes_are_decoded_once_and_empty_object_keys_are_valid(study):
    assert evidence.pointer_tokens("/data/a~1b/~01/0") == ("data", "a/b", "~1", "0")
    result = located(study, "/data/a~1b/~01/0", None)[0]
    assert result["value"] is None and result["code"] == "located"
    assert located(study, "/data/", "empty-key")[0]["value"] == "empty-key"
    source = evidence.snapshot(study)
    assert result["source"] == {
        "ref": source["study_ref"],
        "version": source["digest"],
        "address": "/data/a~1b/~01/0",
        "digest": source["digest"],
    }
    assert result["ref"] == source["study_ref"] + "#/data/a~1b/~01/0"


@pytest.mark.parametrize(
    "address", ["", "data", "#/data", "/data/~", "/data/~2", "/data/~10~9", None, False, 0, []]
)
def test_invalid_pointer_admission_is_named(address):
    assert evidence.pointer_state(address) == "invalid_pointer"
    with pytest.raises(evidence.BridgeError, match="invalid_pointer"):
        evidence.pointer_tokens(address)


@pytest.mark.parametrize("index", ["01", "-1", "+1", "-", "1.0", " 1", "１", "1e0"])
def test_list_indexes_must_be_canonical_unsigned_decimal(study, index):
    with pytest.raises(evidence.BridgeError, match="invalid_list_index"):
        located(study, "/data/a~1b/~01/" + index, None)


@pytest.mark.parametrize(
    "address",
    [
        "/missing",
        "/data/a~1b/~01/5",
        "/data/a~1b/~01/999999999999",
        "/data/a~1b/~01/0/child",
        "/data/a%2Fb/~01/0",
    ],
)
def test_missing_selected_location_is_a_translation_refusal(study, address):
    with pytest.raises(evidence.BridgeError, match="missing_location"):
        located(study, address, None)


@pytest.mark.parametrize("expected", [False, 1, 1.0, "true", None])
def test_boolean_cannot_match_integer_or_other_expected_json_types(study, expected):
    with pytest.raises(evidence.BridgeError, match="stale_value"):
        located(study, "/data/a~1b/~01/1", expected)


def test_exact_type_equality_is_recursive_and_null_is_a_located_value(study):
    assert evidence.exact_json_equal({"x": [None, True, 1]}, {"x": [None, True, 1]})
    assert not evidence.exact_json_equal({"x": [True]}, {"x": [1]})
    assert not evidence.exact_json_equal([1], [1.0])
    assert not evidence.exact_json_equal({}, {"missing": None})
    assert located(study, "/data/a~1b/~01/0", None)[0]["value"] is None


def test_stale_digest_snapshot_and_expected_are_distinct_refusals(study):
    raw = declare(study, "/data/a~1b/~01/2", 1)
    raw["digest"] = "0" * 64
    with pytest.raises(evidence.BridgeError, match="stale_digest"):
        evidence.anchors(study, evidence.snapshot(study), [raw])
    old = evidence.snapshot(study)
    study["unselected"] = True
    with pytest.raises(evidence.BridgeError, match="stale_snapshot"):
        evidence.anchors(study, old, [])
    with pytest.raises(evidence.BridgeError, match="stale_value"):
        located(study, "/data/a~1b/~01/2", 2)


@pytest.mark.parametrize("change,code", [({"extra": 1}, "unknown_field"), ({"id": ""}, "not_text")])
def test_anchor_schema_is_closed_and_ids_are_nonempty(study, change, code):
    raw = declare(study, "/data/a~1b/~01/0", None)
    raw.update(change)
    with pytest.raises(evidence.BridgeError, match=code):
        evidence.anchors(study, evidence.snapshot(study), [raw])


@pytest.mark.parametrize("missing", ["id", "address", "digest", "expected"])
def test_every_anchor_field_is_required_even_for_a_null_selection(study, missing):
    raw = declare(study, "/data/a~1b/~01/0", None)
    del raw[missing]
    with pytest.raises(evidence.BridgeError, match="missing_field"):
        evidence.anchors(study, evidence.snapshot(study), [raw])


def test_anchor_identity_and_item_limit_are_enforced(study):
    raw = declare(study, "/data/a~1b/~01/0", None)
    with pytest.raises(evidence.BridgeError, match="duplicate_id"):
        evidence.anchors(study, evidence.snapshot(study), [raw, raw])
    with pytest.raises(evidence.BridgeError, match="resource_bound:anchors"):
        evidence.anchors(study, evidence.snapshot(study), [raw] * (evidence.MAX_ANCHORS + 1))
    with pytest.raises(evidence.BridgeError, match="not_a_list"):
        evidence.anchors(study, evidence.snapshot(study), cast(Any, {}))


def test_unicode_span_uses_code_point_offsets_and_hydrates_only_the_quotation(study):
    text = study["data"]["a/b"]["~1"][4]
    result = located(study, "/data/a~1b/~01/4", text, span={"start": 2, "end": 4, "text": "18"})
    assert result[0]["value"] == "é🧬18\n"
    assert result[0]["ref"].endswith(":chars:2:4")
    assert evidence.hydrate({"age": {"$source": "selected", "as": "integer"}}, result) == {"age": 18}
    empty = located(study, "/data/a~1b/~01/4", text, span={"start": 1, "end": 1, "text": ""})
    assert evidence.hydrate({"$source": "selected", "as": "text"}, empty) == ""


@pytest.mark.parametrize(
    "span,code",
    [
        ({"start": 0, "end": 2, "text": "é"}, "stale_span"),
        ({"start": -1, "end": 1, "text": ""}, "invalid_span"),
        ({"start": 3, "end": 2, "text": ""}, "invalid_span"),
        ({"start": 0, "end": 100, "text": ""}, "invalid_span"),
        ({"start": False, "end": 1, "text": "é"}, "invalid_span"),
        ({"start": 0, "end": 1.0, "text": "é"}, "invalid_span"),
        ({"start": 0, "end": 1}, "missing_field"),
        ({"start": 0, "end": 1, "text": "é", "unit": "bytes"}, "unknown_field"),
    ],
)
def test_spans_refuse_wrong_text_types_bounds_or_open_schema(study, span, code):
    text = study["data"]["a/b"]["~1"][4]
    with pytest.raises(evidence.BridgeError, match=code):
        located(study, "/data/a~1b/~01/4", text, span=span)


def test_span_requires_an_addressed_string(study):
    with pytest.raises(evidence.BridgeError, match="invalid_span"):
        located(study, "/data/a~1b/~01/2", 1, span={"start": 0, "end": 1, "text": "1"})


def test_repeated_words_keep_the_selected_offsets_without_a_first_match_search(study):
    study["repeated"] = "same; same"
    first = located(study, "/repeated", "same; same", span={"start": 0, "end": 4, "text": "same"})
    second = located(study, "/repeated", "same; same", span={"start": 6, "end": 10, "text": "same"})
    assert first[0]["span"] != second[0]["span"] and first[0]["ref"] != second[0]["ref"]
    assert evidence.hydrate({"$source": "selected", "as": "text"}, second) == "same"


@pytest.mark.parametrize(
    "value,expected,state",
    [
        (0, 0, "integer"),
        (-12, -12, "integer"),
        ("0", 0, "integer_text"),
        ("+12", 12, "integer_text"),
        ("-001", -1, "integer_text"),
        ("001", 1, "integer_text"),
    ],
)
def test_integer_conversion_accepts_only_its_declared_lexical_language(value, expected, state):
    assert evidence.integer_state(value) == state
    assert evidence.strict_integer(value) == expected
    assert type(evidence.strict_integer(value)) is int


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        None,
        1.0,
        float("nan"),
        "",
        " 1",
        "1 ",
        "1\n",
        "1,217",
        "1.0",
        "1e2",
        "١",
        "--1",
        "+",
        [],
        {},
    ],
)
def test_integer_conversion_never_rounds_or_coerces(value):
    assert evidence.integer_state(value) == "invalid_integer"
    with pytest.raises(evidence.BridgeError, match="invalid_integer"):
        evidence.strict_integer(value)


@pytest.mark.parametrize(
    "marker,code",
    [
        ({"$source": "unknown", "as": "json"}, "unknown_ref"),
        ({"$source": "selected", "as": "float"}, "unknown_mode"),
        ({"$source": "selected", "as": []}, "unknown_mode"),
        ({"$source": "selected"}, "missing_field"),
        ({"$source": "selected", "as": "json", "default": 1}, "unknown_field"),
        ({"$source": False, "as": "json"}, "not_text"),
    ],
)
def test_marker_language_is_closed_and_never_guesses_unknown_references(study, marker, code):
    values = located(study, "/data/a~1b/~01/0", None)
    with pytest.raises(evidence.BridgeError, match=code):
        evidence.hydrate(marker, values)


def test_text_mode_requires_string_and_json_mode_preserves_null_and_boolean(study):
    values = located(study, "/data/a~1b/~01/0", None)
    assert evidence.hydrate({"$source": "selected", "as": "json"}, values) is None
    with pytest.raises(evidence.BridgeError, match="not_text"):
        evidence.hydrate({"$source": "selected", "as": "text"}, values)
    values = located(study, "/data/a~1b/~01/1", True)
    assert evidence.hydrate({"$source": "selected", "as": "json"}, values) is True
    with pytest.raises(evidence.BridgeError, match="invalid_integer"):
        evidence.hydrate({"$source": "selected", "as": "integer"}, values)


def test_selected_source_json_is_literal_even_when_it_contains_a_marker_shaped_object(study):
    literal = {"$source": "not-a-template", "as": "json"}
    study["literal"] = literal
    values = located(study, "/literal", literal)
    assert evidence.hydrate({"$source": "selected", "as": "json"}, values) == literal


def test_returned_values_templates_and_sources_are_independent_copies(study):
    before = copy.deepcopy(study)
    raw = [declare(study, "/data/a~1b/~01", study["data"]["a/b"]["~1"])]
    raw_before = copy.deepcopy(raw)
    values = evidence.anchors(study, evidence.snapshot(study), raw)
    template = {"selected": {"$source": "selected", "as": "json"}, "own": [0]}
    original_template = copy.deepcopy(template)
    result = evidence.hydrate(template, values)
    assert isinstance(result, dict)
    result["selected"].append("changed")
    result["own"].append(1)
    assert study == before and raw == raw_before and template == original_template
    assert values[0]["value"] == study["data"]["a/b"]["~1"]
    values[0]["value"].append("independent")
    assert study == before


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), (1,), {1: "bad-key"}, "\ud800", object()]
)
def test_nonfinite_and_nonstrict_json_never_reach_a_snapshot(study, value):
    study["bad"] = value
    with pytest.raises(evidence.BridgeError, match="nonfinite_json|invalid_json"):
        evidence.snapshot(study)


def test_bytes_are_bounded_in_utf8_and_depth_and_nodes_are_bounded(study, monkeypatch):
    study["too_large"] = "x" * (evidence.MAX_BYTES + 1)
    with pytest.raises(evidence.BridgeError, match="resource_bound:bytes"):
        evidence.snapshot(study)
    del study["too_large"]
    value = 0
    for _ in range(evidence.MAX_DEPTH):
        value = [value]
    study["deep"] = value
    with pytest.raises(evidence.BridgeError, match="resource_bound:depth"):
        evidence.snapshot(study)
    del study["deep"]
    monkeypatch.setattr(evidence, "MAX_NODES", 20)
    study["wide"] = [None] * 21
    with pytest.raises(evidence.BridgeError, match="resource_bound:nodes"):
        evidence.snapshot(study)


def test_unicode_byte_budget_counts_encoded_bytes_and_exact_boundary(study, monkeypatch):
    size = len(json.dumps(study, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    monkeypatch.setattr(evidence, "MAX_BYTES", size)
    assert evidence.snapshot(study)["nct"] == "NCT00322452"
    monkeypatch.setattr(evidence, "MAX_BYTES", size - 1)
    with pytest.raises(evidence.BridgeError, match="resource_bound:bytes"):
        evidence.snapshot(study)


def test_cycles_are_bounded_without_mutating_source(study):
    study["cycle"] = study
    with pytest.raises(evidence.BridgeError, match="resource_bound:depth"):
        evidence.snapshot(study)
    assert study["cycle"] is study


def test_depth_node_and_anchor_limits_admit_their_exact_boundaries(study, monkeypatch):
    value = 0
    for _ in range(evidence.MAX_DEPTH - 1):
        value = [value]
    study["deep"] = value
    assert evidence.snapshot(study)["nct"] == "NCT00322452"
    del study["deep"]
    # Root + protocol + identity + NCT + a four-element list + its four leaves: nine JSON nodes.
    small = {"protocolSection": {"identificationModule": {"nctId": "NCT00322452"}}, "x": [0] * 4}
    monkeypatch.setattr(evidence, "MAX_NODES", 9)
    assert evidence.snapshot(small)["nct"] == "NCT00322452"
    small["x"].append(0)
    with pytest.raises(evidence.BridgeError, match="resource_bound:nodes"):
        evidence.snapshot(small)
    monkeypatch.setattr(evidence, "MAX_NODES", 100_000)
    declarations = [
        {**declare(study, "/data/a~1b/~01/0", None), "id": f"a{index}"}
        for index in range(evidence.MAX_ANCHORS)
    ]
    assert len(evidence.anchors(study, evidence.snapshot(study), declarations)) == evidence.MAX_ANCHORS


def test_hydrated_expansion_is_bounded_while_constructing_output(study, monkeypatch):
    study["payload"] = "x" * 2000
    values = located(study, "/payload", study["payload"])
    template = [{"$source": "selected", "as": "json"}] * 30
    monkeypatch.setattr(evidence, "MAX_BYTES", 20_000)
    with pytest.raises(evidence.BridgeError, match="resource_bound:bytes:hydrated"):
        evidence.hydrate(template, values)


def test_hydration_counts_the_selected_value_depth_at_its_new_template_location(study):
    study["payload"] = [[0]]
    values = located(study, "/payload", [[0]])
    template = {"$source": "selected", "as": "json"}
    for _ in range(evidence.MAX_DEPTH - 1):
        template = [template]
    with pytest.raises(evidence.BridgeError, match="resource_bound:depth:hydrated"):
        evidence.hydrate(template, values)


def test_hydrate_refuses_malformed_or_duplicate_located_records(study):
    values = located(study, "/data/a~1b/~01/0", None)
    marker = {"$source": "selected", "as": "json"}
    with pytest.raises(evidence.BridgeError, match="duplicate_id:located"):
        evidence.hydrate(marker, values * 2)
    values[0]["code"] = "proposed"
    with pytest.raises(evidence.BridgeError, match="not_located"):
        evidence.hydrate(marker, values)
    with pytest.raises(evidence.BridgeError, match="not_a_list:located"):
        evidence.hydrate(marker, cast(Any, {}))


def test_retained_ipass_cell_is_only_located_not_clinically_promoted():
    source = Path(__file__).parent / "fixtures" / "ipass-registry.json"
    study = json.loads(source.read_text())
    address = (
        "/resultsSection/baselineCharacteristicsModule/measures/5/classes/2/categories/0/measurements/2/value"
    )
    values = located(study, address, "126")
    assert values[0]["code"] == "located" and values[0]["value"] == "126"
    assert evidence.hydrate({"count": {"$source": "selected", "as": "integer"}}, values) == {"count": 126}
    assert set(values[0]) == {"id", "address", "digest", "value", "ref", "source", "code"}
