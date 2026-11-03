"""Intent cases for explicit standing and public admission; invented premises only."""

from itertools import product

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.admission import admission_code, read_standing


def test_admission_code_follows_the_exact_consumer_contract():
    for status, resolution, interpolated in product(
        ("known", "interpolated", "proposed", "invalid"),
        ("resolved", "unresolved", "partially_resolved", "conflicting", "invalid"),
        (False, True),
    ):
        expected = (
            "proposed_refused"
            if status == "proposed"
            else "resolution_unresolved"
            if resolution != "resolved"
            else "accepted"
            if status == "known" or (interpolated and status == "interpolated")
            else "standing_not_accepted"
        )
        assert admission_code(status, resolution, interpolated) == expected


def test_missing_standing_is_detached_pending_and_explicit_support_needs_provenance():
    assert read_standing(None, "example") == {"status": "proposed", "resolution": "unresolved", "basis": []}
    raw = {"status": "known", "resolution": "resolved", "basis": ["invented:choice"]}
    result = read_standing(raw, "example")
    result["basis"].append("output")
    assert raw["basis"] == ["invented:choice"]
    for malformed in ({}, [], False, {**raw, "basis": []}, {**raw, "extra": 1}):
        with pytest.raises((ValueError, TypeError)):
            read_standing(malformed, "example")


def known():
    return {"status": "known", "resolution": "resolved", "basis": ["invented:accepted-premise"]}


def trial(identity="invented-A"):
    return {
        "id": identity,
        "sponsor": identity,
        "stratum": "invented-set",
        "typed": True,
        "elements": ["inclusion:age=adult", "exclusion:brain_metastases=present"],
        "basis": ["invented:unconfirmed-reading"],
        "classes": ["invented-A"],
        "class_unresolved": False,
        "setting_domain": ["invented-X"],
        "representation": {"setting": "invented-X"},
        "predicates": {"PS": "0-1"},
    }


def test_unmarked_readings_do_not_become_counts_coordinates_occupants_or_near_misses():
    a, b = trial(), trial("invented-B")
    b["predicates"]["PS"] = "0-2"
    reply = run({"operation": "corpus", "trials": [a, b], "cells": [["invented-X", "invented-A"]]})
    assert reply["code"] == "complete", reply
    result = reply["result"]
    assert all(r["stating"] == 0 and r["lower"] == 0 and r["upper"] == 1 for r in result["frequency"])
    assert result["near_misses"] == result["associations"] == []
    assert result["occupancy"][0]["state"] == "unknown"
    assert result["pending"] and result["association_abstentions"] and result["near_miss_abstentions"]
    evidence = {
        "section": "inclusion",
        "concept": "prior_lines",
        "values": ["0"],
        "scope": "advanced",
        "ref": "invented:unconfirmed",
    }
    coord = run({"operation": "coordinates", "domain": "nsclc", "evidence": [evidence]})
    assert coord["result"]["coordinates"]["prior_advanced_lines"]["state"] == "unnarrowed"
    assert coord["result"]["admission"][0]["level"] == "pending"


def test_known_feature_is_preserved_alongside_pending_rival_feature():
    item = trial()
    item["feature_standings"] = {"elements": {"inclusion:age=adult": known()}}
    result = run({"operation": "corpus", "trials": [item]})["result"]
    rows = {r["element"]: r for r in result["frequency"]}
    assert rows["inclusion:age=adult"]["stating"] == 1
    pending = rows["exclusion:brain_metastases=present"]
    assert pending["stating"] == 0 and pending["pending_stating"] == 1
    assert pending["surprisal_bits"] is None


@pytest.mark.parametrize("operation", ["coordinates", "corpus"])
def test_explicit_null_standing_refuses_at_public_boundary(operation):
    if operation == "corpus":
        item = trial()
        item["standing"] = None
        request = {"operation": operation, "trials": [item]}
    else:
        request = {
            "operation": operation,
            "domain": "nsclc",
            "evidence": [
                {
                    "section": "inclusion",
                    "concept": "prior_lines",
                    "values": ["0"],
                    "scope": "advanced",
                    "ref": "invented:ref",
                    "standing": None,
                }
            ],
        }
    assert run(request)["code"] == "refused"
