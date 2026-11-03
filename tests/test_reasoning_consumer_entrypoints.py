"""Actual public handoffs preserve pending information and independent accepted consequences."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2 import run

DEMO = Path(__file__).resolve().parents[1] / "examples" / "reasoning-admission"


@pytest.mark.parametrize("mode", ["cli", "mcp"])
@pytest.mark.parametrize(
    "name", ["mixed-comparison", "coordinate-standing", "unbound-scale", "declared-proposition-bridge"]
)
def test_complete_demo_reaches_real_consumer_without_changing_inputs(mode, name, tmp_path):
    request = json.loads((DEMO / (name + "-request.json")).read_text())
    original = copy.deepcopy(request)
    actual = invoke(request, mode, tmp_path)
    assert actual == json.loads((DEMO / (name + "-result.json")).read_text())
    assert request == original
    result = actual["result"]
    if name == "mixed-comparison":
        rows = {r["element"]: r for r in result["frequency"]}
        assert rows["inclusion:age=adult"]["stating"] == 2
        ps = rows["exclusion:brain_metastases=present"]
        assert (ps["stating"], ps["pending_stating"], ps["lower"], ps["upper"]) == (1, 1, 0.5, 1)
        assert result["associations"] == result["near_misses"] == []
        assert result["association_abstentions"] and result["near_miss_abstentions"]
        assert [(r["occupants"], r["possible"], r["state"]) for r in result["occupancy"]] == [
            (1, 1, "occupied"),
            (0, 0, "empty"),
        ]
        assert result["expectations"][0]["rarity"][0] == "abstain"
        assert result["expectations"][0]["admitted_count"] == 1
    elif name == "coordinate-standing":
        coordinates = result["coordinates"]
        assert coordinates["selection:EGFR"]["domain"] == ["positive"]
        assert len(coordinates["prior_advanced_lines"]["domain"]) == 4
        assert coordinates["prior_advanced_lines"]["interpolated"]["domain"] == ["0"]
        assert coordinates["setting"]["interpolated"]["domain"] == ["advanced_first_line"]
    elif name == "unbound-scale":
        assert result["decision"]["result"] == "UNDETERMINED"
        assert result["translation_diagnostics"][0]["dimensions"] == ["unit"]
    else:
        assert result["decision"]["result"] == "ENTAILED"
        assert result["decision"]["status"] == "interpolated"
        assert "invented-declared-equivalence" in result["decision"]["proof"]


def minimal():
    return {
        "id": "invented",
        "sponsor": "invented",
        "stratum": "invented",
        "elements": [],
        "basis": ["invented:premise"],
    }


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_omitted_pending_setting_is_possible_instead_of_translation_refusal(mode, tmp_path):
    result = invoke({"operation": "corpus", "trials": [minimal()], "cells": [["X", "C"]]}, mode, tmp_path)
    assert result["code"] == "complete"
    assert result["result"]["occupancy"] == [
        {"setting": "X", "class": "C", "occupants": 0, "possible": 1, "state": "unknown"}
    ]


@pytest.mark.parametrize("field", ["typed", "classes", "setting_domain", "eligibility_content", "coverage"])
def test_default_insertion_cannot_invent_a_standing_override_target(field):
    trial = minimal()
    trial["feature_standings"] = {
        field: {"status": "known", "resolution": "resolved", "basis": ["invented:unsupported-override"]}
    }
    result = run({"operation": "corpus", "trials": [trial]})
    assert result["code"] == "refused"
    assert result["problems"] == ["missing_override_target:trial:invented:" + field]
