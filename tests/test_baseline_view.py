"""A compact baseline table preserves source cells and cannot fabricate group bindings."""

from __future__ import annotations

import copy
import json

import pytest

from TrialLedger.baseline_view import BaselineViewError, baseline_tables, group_code


def record():
    return {
        "studies": [
            {
                "nct": "NCT00000001",
                "baseline": {
                    "population": {"status": "not_stated", "note": "not_reported"},
                    "groups": [
                        {"id": "G1", "title": "Drug"},
                        {"id": "G2", "title": "Placebo"},
                        {"id": "G3", "title": "Total"},
                    ],
                    "denominators": [
                        {
                            "units": "Participants",
                            "counts": [
                                {"group": "G1", "value": "2373"},
                                {"group": "G2", "value": "2371"},
                                {"group": "G3", "value": "4744"},
                            ],
                        }
                    ],
                    "measures": [
                        {
                            "title": "NYHA class at enrollment",
                            "param_type": "COUNT_OF_PARTICIPANTS",
                            "unit": "Participants",
                            "classes": [
                                {
                                    "categories": [
                                        {
                                            "title": title,
                                            "measurements": [
                                                {"group": g, "value": v}
                                                for g, v in zip(("G1", "G2", "G3"), values, strict=True)
                                            ],
                                        }
                                        for title, values in [
                                            ("II", ("1606", "1597", "3203")),
                                            ("III", ("747", "751", "1498")),
                                            ("IV", ("20", "23", "43")),
                                        ]
                                    ]
                                }
                            ],
                        }
                    ],
                },
            }
        ]
    }


@pytest.mark.parametrize(
    ("group", "identities", "expected"),
    [
        (None, [None], "missing_group"),
        ("", [""], "missing_group"),
        (False, [False], "invalid_group"),
        (0, [0], "invalid_group"),
        ([], [], "invalid_group"),
        ("G", [], "unknown_group"),
        ("G", ["G", "G"], "ambiguous_group"),
        ("G", ["G", "other"], "unique"),
        ("Drug", ["G"], "unknown_group"),
    ],
)
def test_group_binding_has_named_outcomes(group, identities, expected):
    assert group_code(group, identities) == expected


def test_matrix_preserves_nine_cells_all_denominators_and_input():
    source = record()
    before = copy.deepcopy(source)
    [table] = baseline_tables(source)
    assert source == before
    assert [row["category"]["title"] for row in table["rows"]] == ["II", "III", "IV"]
    assert [[v["measurement"]["value"] for v in row["values"]] for row in table["rows"]] == [
        ["1606", "1597", "3203"],
        ["747", "751", "1498"],
        ["20", "23", "43"],
    ]
    assert [g["denominators"][0]["value"] for g in table["groups"]] == ["2373", "2371", "4744"]
    assert table["population"]["measure"]["present"] is False
    assert table["population"]["module"]["value"] == source["studies"][0]["baseline"]["population"]
    for row in table["rows"]:
        for cell in row["values"]:
            raw = source
            for token in cell["source"].removeprefix("/").split("/"):
                raw = raw[int(token)] if isinstance(raw, list) else raw[token]
            assert json.dumps(raw, sort_keys=True) == json.dumps(cell["measurement"], sort_keys=True)
            assert cell["group_code"] == "unique"
            assert cell["denominators"][0]["scope"] == "module"
            assert cell["unit"]["value"] == "Participants"


def test_class_measure_and_module_denominators_are_not_collapsed():
    source = record()
    measure = source["studies"][0]["baseline"]["measures"][0]
    measure["population"] = "Measure population"
    measure["denominators"] = [{"units": "Samples", "counts": [{"group": "G1", "value": "2000"}]}]
    measure["classes"][0].update(
        units_analyzed="Lesions",
        denominators=[{"units": "Lesions", "counts": [{"group": "G1", "value": "3000"}]}],
    )
    [table] = baseline_tables(source)
    cell = table["rows"][0]["values"][0]
    assert [(d["scope"], d["units"], d["value"]) for d in cell["denominators"]] == [
        ("class", "Lesions", "3000"),
        ("measure", "Samples", "2000"),
        ("module", "Participants", "2373"),
    ]
    assert table["rows"][0]["class"]["units_analyzed"] == "Lesions"
    assert table["population"]["measure"]["value"] == "Measure population"


def test_ambiguous_and_undeclared_groups_keep_cells_without_guessing_titles():
    source = record()
    baseline = source["studies"][0]["baseline"]
    baseline["groups"].append({"id": "G1", "title": "Different definition"})
    category = baseline["measures"][0]["classes"][0]["categories"][0]
    category["measurements"].extend([{"group": "Drug", "value": "5"}, {"value": "0"}])
    [table] = baseline_tables(source)
    cells = table["rows"][0]["values"]
    assert cells[0]["group_code"] == "ambiguous_group"
    assert len(cells[0]["group_sources"]) == 2
    assert cells[3]["group_code"] == "unknown_group" and cells[3]["group_sources"] == []
    assert cells[4]["group_code"] == "missing_group" and cells[4]["measurement"]["value"] == "0"
    assert cells[4]["denominators"] == []
    assert len(table["groups"]) == 4


@pytest.mark.parametrize("value", [0, False, None, "0.000", "=1+1"])
def test_literal_measurement_values_and_comments_are_not_coerced(value):
    source = record()
    measurement = source["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0][
        "measurements"
    ][0]
    measurement.update(value=value, comment="Source comment", spread="1.20", lower="0", upper="2")
    [table] = baseline_tables(source)
    assert json.dumps(table["rows"][0]["values"][0]["measurement"], sort_keys=True) == json.dumps(
        measurement, sort_keys=True
    )


def test_identical_group_ids_in_different_studies_remain_separate():
    source = record()
    second = copy.deepcopy(source["studies"][0])
    second["nct"] = "NCT00000002"
    second["baseline"]["groups"][0]["title"] = "Other study drug"
    source["studies"].append(second)
    first, second = baseline_tables(source)
    assert first["groups"][0]["title"] == "Drug"
    assert second["groups"][0]["title"] == "Other study drug"
    assert first["groups"][0]["source"] != second["groups"][0]["source"]


def test_unlisted_baseline_is_a_source_state_not_zero_observations():
    source = {"studies": [{"nct": "N", "baseline": {"status": "not_posted", "note": "no_results"}}]}
    [table] = baseline_tables(source)
    assert table["rows"] == [] and table["groups"] == []
    assert table["module"] == source["studies"][0]["baseline"]
    assert table["availability"] == {
        "present": False,
        "value": None,
        "source": "/studies/0/baseline/measures",
    }


@pytest.mark.parametrize("path", ["classes", "categories", "measurements"])
def test_explicit_empty_collections_stay_distinct_from_missing(path):
    source = record()
    measure = source["studies"][0]["baseline"]["measures"][0]
    parent = measure if path == "classes" else measure["classes"][0]
    if path == "measurements":
        parent = parent["categories"][0]
    parent[path] = []
    [table] = baseline_tables(source)
    assert table["rows"][0][path]["present"] is True
    assert table["rows"][0][path]["value"] == []
    del parent[path]
    [table] = baseline_tables(source)
    assert table["rows"][0][path]["present"] is False


@pytest.mark.parametrize("source", [None, [], False, {}])
def test_malformed_record_is_refused(source):
    with pytest.raises(BaselineViewError):
        baseline_tables(source)


@pytest.mark.parametrize("value", [None, False, {}, [1]])
def test_malformed_measurements_cannot_look_like_an_empty_table(value):
    source = record()
    source["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"] = value
    with pytest.raises(BaselineViewError, match="malformed_"):
        baseline_tables(source)
