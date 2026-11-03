"""Invented clinical questions for public consumer admission; never trial evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from TrialLedger.layer2 import run
from TrialLedger.layer2.interpretations_guide import premise, quantity

ROOT = Path(__file__).resolve().parent


def standing(status="known", resolution="resolved"):
    return {"status": status, "resolution": resolution, "basis": ["invented:accepted-teaching-premise"]}


def requests():
    def trial(identity):
        return {
            "id": identity,
            "sponsor": identity,
            "stratum": "invented-comparison-set",
            "elements": ["inclusion:age=adult", "exclusion:brain_metastases=present"],
            "typed": True,
            "basis": ["invented:teaching-only"],
            "standing": standing(),
            "classes": ["invented-class-A"],
            "class_unresolved": False,
            "setting_domain": ["invented-setting-X"],
            "representation": {"setting": "invented-X"},
            "predicates": {"PS": "0-1"},
        }

    a, b = trial("invented-A"), trial("invented-B")
    b["predicates"]["PS"] = "0-2"
    b["feature_standings"] = {
        "elements": {"exclusion:brain_metastases=present": standing("proposed")},
        "predicates": {"PS": standing("proposed")},
        "setting_domain": standing("proposed"),
    }
    corpus = {
        "operation": "corpus",
        "trials": [a, b],
        "cells": [["invented-setting-X", "invented-class-A"], ["invented-setting-X", "invented-class-B"]],
        "expectations": [
            {
                "id": "invented-expectation",
                "cell": "invented-cell",
                "support": 2,
                "basis": ["invented:teaching-only"],
                "standing": standing(),
                "observations": [["invented-cell", "present"], ["invented-cell", "explicitly_negated"]],
                "observation_standings": [standing(), standing("proposed")],
            }
        ],
    }
    evidence = []
    for concept, values, scope, status in (
        ("biomarker:EGFR", ["positive"], "", "known"),
        ("prior_lines", ["0"], "advanced", "interpolated"),
        ("extent", ["advanced"], "", "known"),
        ("biomarker:EGFR", ["negative"], "", "proposed"),
    ):
        evidence.append(
            {
                "section": "inclusion",
                "concept": concept,
                "values": values,
                "scope": scope,
                "ref": "invented:" + concept + status,
                "standing": standing(status),
            }
        )
    ecog = quantity("performance_status", "le", 1, "ECOG")
    who = quantity("performance_status", "le", 1, "WHO")
    given = premise("invented-ECOG-criterion", ecog, status="known")
    mismatch = {"operation": "entailment", "assertions": [given], "query": who}
    # This is an explicitly invented equivalence of these two propositions, not a clinical scale mapping.
    iff = {
        "class": "AllOf",
        "parts": [
            {"class": "AnyOf", "parts": [{"class": "Not", "part": ecog}, who]},
            {"class": "AnyOf", "parts": [{"class": "Not", "part": who}, ecog]},
        ],
    }
    bridge = premise("invented-declared-equivalence", iff, status="interpolated")
    return {
        "mixed-comparison": corpus,
        "coordinate-standing": {"operation": "coordinates", "domain": "nsclc", "evidence": evidence},
        "unbound-scale": mismatch,
        "declared-proposition-bridge": {**copy.deepcopy(mismatch), "assertions": [given, bridge]},
    }


def build():
    for name, request in requests().items():
        result = run(request)
        if result["code"] != "complete":
            raise ValueError(result)
        for suffix, value in (("request", request), ("result", result)):
            (ROOT / f"{name}-{suffix}.json").write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n"
            )


if __name__ == "__main__":
    build()
