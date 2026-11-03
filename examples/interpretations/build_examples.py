"""Rebuild invented request files and execute them through the installed public CLI."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

from TrialLedger.layer2 import dependency_evidence
from TrialLedger.layer2.interpretations_guide import example, frame, premise, quantity

HERE = Path(__file__).resolve().parent
STUDY = "invented:adult-NSCLC-draft:v1"


def supported_signal(identity: str, kind: str, data: dict, status: str = "known") -> dict:
    return {
        "id": identity,
        "kind": kind,
        "data": data,
        "support": [
            {
                "id": identity + "-premise",
                "status": status,
                "resolution": "resolved",
                "basis": ["invented:explicit-demonstration-premise-not-trial-evidence"],
            }
        ],
    }


def interval(before: str, after: str, lower: int, upper: int) -> dict:
    return {
        "before": before,
        "after": after,
        "lower": lower,
        "upper": upper,
        "lower_inclusive": True,
        "upper_inclusive": True,
    }


def assessment_roles() -> dict:
    request = example()
    request["fixed"]["signals"] = [
        supported_signal(
            "planned-schedule",
            "temporal",
            {
                "scope": "invented:planned-routine-assessments:v1",
                "unit": "day",
                "origin": "randomization",
                "resolution": "resolved",
                "events": ["randomization", "first_scheduled_assessment"],
                "constraints": [interval("randomization", "first_scheduled_assessment", 35, 49)],
            },
        ),
        supported_signal(
            "observed-scan",
            "temporal",
            {
                "scope": "invented:observed-unscheduled-scan-log:v1",
                "unit": "day",
                "origin": "randomization",
                "resolution": "resolved",
                "events": ["randomization", "actual_unscheduled_scan"],
                "constraints": [interval("randomization", "actual_unscheduled_scan", 28, 28)],
            },
        ),
    ]
    readings = []
    for identity, label, signal, event, day, maximum in (
        (
            "scheduled-42",
            "Routine first assessment on day 42, ECOG 0–2",
            "planned-schedule",
            "first_scheduled_assessment",
            42,
            2,
        ),
        (
            "scheduled-49",
            "Routine first assessment at the day-49 boundary, ECOG 0–3",
            "planned-schedule",
            "first_scheduled_assessment",
            49,
            3,
        ),
        (
            "scheduled-28",
            "Treat day 28 as the routine scheduled first assessment",
            "planned-schedule",
            "first_scheduled_assessment",
            28,
            2,
        ),
        (
            "unscheduled-28",
            "Keep day 28 as a separate actual unscheduled scan, ECOG 0–3",
            "observed-scan",
            "actual_unscheduled_scan",
            28,
            3,
        ),
    ):
        item = frame(identity, label, [premise(identity + "-PS", quantity("ECOG", "le", maximum, "ECOG"))])
        item["signal_claims"] = [{"signal": signal, "claim": interval("randomization", event, day, day)}]
        readings.append(item)
    request["interpretations"] = readings
    return request


def scope(population: str, version: str = "invented:definition-v1") -> dict:
    return {
        "study": STUDY,
        "population": population,
        "arm": "all",
        "time": "baseline-to-week12",
        "version": version,
    }


def binding(identity: str, kind: str, relation: str, subjects: list[str], bound_scope: dict) -> dict:
    return {
        "id": identity,
        "kind": kind,
        "relation": relation,
        "subjects": subjects,
        "scope": copy.deepcopy(bound_scope),
        "sources": [
            {"ref": "invented:comparator-protocol", "version": "1", "address": "/invented/definitions"}
        ],
        "status": "proposed",
        "resolution": "resolved",
        "basis": ["invented:explicit-reading-for-hypothetical-computation"],
    }


def population_binding(*, resolved: bool) -> dict:
    request = example()
    universe = "invented:comparator:ITT:cohort-A:v1"
    bound_scope = scope(universe, "invented:population-v1")
    item = binding("EFQ-subset-binding", "population", "subset_of", ["ITT", "EFQ"], bound_scope)
    item["resolution"] = "resolved" if resolved else "unresolved"
    request["bindings"] = [item]
    request["fixed"]["signals"] = [
        supported_signal(
            "EFQ-coverage",
            "population",
            {
                "universe": universe,
                "alignment": "confirmed",
                "total": 200,
                "parent_ref": "ITT",
                "subset_relation": "confirmed",
                "subset": {"ref": "EFQ", "universe": universe, "lower": 160, "upper": 160},
            },
        )
    ]
    readings = []
    for identity, label, claimed_outside in (
        ("aligned-EFQ", "Interpret EFQ as the declared 160-person subset of ITT 200", None),
        ("everyone-in-EFQ", "Assume every ITT participant was in EFQ", 0),
    ):
        row = frame(identity, label, [premise(identity + "-PS", quantity("ECOG", "le", 2, "ECOG"))])
        row["binding_uses"] = [
            {"binding": item["id"], "signal": "EFQ-coverage", "scope": copy.deepcopy(bound_scope)}
        ]
        if claimed_outside is not None:
            row["signal_claims"] = [
                {
                    "signal": "EFQ-coverage",
                    "claim": {"count": "outside", "lower": claimed_outside, "upper": claimed_outside},
                }
            ]
        readings.append(row)
    request["interpretations"] = readings
    return request


def endpoint_inputs() -> dict:
    request = example()
    definition = copy.deepcopy(dependency_evidence.EXAMPLES["dependencies"])
    definition["scope"] = "invented:cohort-A:observed-change-definition"
    definition["rules"][0]["version"] = "invented:definition-v1"
    target = supported_signal("observed-change", "dependencies", definition)
    request["fixed"]["signals"] = [target]
    bound_scope = scope(definition["scope"])
    declared = binding("adopt-change", "definition", "adopts", ["change"], bound_scope)
    declared["status"] = "known"
    request["bindings"] = [declared]
    readings = []
    for identity, label, claim in (
        (
            "observed-week12",
            "Plan to supply an observed week-12 assessment",
            {"available": [{"id": "week12", "mode": "observed"}]},
        ),
        (
            "imputed-week12",
            "Supply an imputed value; observed availability still unknown",
            {"available": [{"id": "week12", "mode": "imputed"}]},
        ),
        (
            "no-observed-week12",
            "Observed week 12 is explicitly unavailable",
            {"unavailable": [{"id": "week12", "mode": "observed"}]},
        ),
    ):
        row = frame(identity, label, [premise(identity + "-PS", quantity("ECOG", "le", 2, "ECOG"))])
        row["signal_claims"] = [{"signal": "observed-change", "claim": claim}]
        row["binding_uses"] = [
            {"binding": declared["id"], "signal": "observed-change", "scope": copy.deepcopy(bound_scope)}
        ]
        readings.append(row)
    request["interpretations"] = readings
    return request


def requests() -> dict[str, dict]:
    choices = example()
    selected = copy.deepcopy(choices)
    selected["selected"] = "PS0-2"
    revised = copy.deepcopy(choices)
    revised["selected"] = "PS0-3"
    return {
        "draft-choices": choices,
        "draft-selected-PS0-2": selected,
        "draft-revised-PS0-3": revised,
        "assessment-roles": assessment_roles(),
        "population-unresolved": population_binding(resolved=False),
        "population-resolved": population_binding(resolved=True),
        "endpoint-inputs": endpoint_inputs(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests-only", action="store_true")
    args = parser.parse_args()
    for name, request in requests().items():
        path = HERE / (name + "-request.json")
        path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.requests_only:
            continue
        response = subprocess.run(
            [sys.executable, "-m", "TrialLedger", "reason", "--request", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(response.stdout)
        if result["code"] != "complete":
            raise RuntimeError(f"{name}: {result['problems']}")
        path.with_name(name + "-result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(name + ": complete")


if __name__ == "__main__":
    main()
