"""Rebuild source-bound IPASS examples through the public CLI without network access."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

from TrialLedger import warrants
from TrialLedger.layer2.interpretations_guide import frame, quantity

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parents[1] / "tests" / "fixtures" / "ipass-registry.json"
BASELINE = "/resultsSection/baselineCharacteristicsModule"
PS2 = BASELINE + "/measures/5/classes/2/categories/0/measurements/2/value"
NEVER = BASELINE + "/measures/4/classes/0/categories/0/measurements/2/value"
TOTAL = BASELINE + "/denoms/0/counts/2/value"
SCHEDULE = "/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame"
ELIGIBILITY = "/protocolSection/eligibilityModule/eligibilityCriteria"


def source_request() -> dict:
    study = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "operation": "source_assertions",
        "study": study,
        "expected_digest": warrants.study_digest(study),
        "queries": [{"id": "registered-adult-age", "body": quantity("age", "ge", 18, "Years")}],
    }


def anchor(request: dict, identity: str, address: str, *, whole_text: bool = False) -> dict:
    """Declare one exact known address; this performs no label search or clinical inference."""
    value = request["study"]
    for token in address.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    row = {
        "id": identity,
        "address": address,
        "digest": request["expected_digest"],
        "expected": copy.deepcopy(value),
    }
    if whole_text:
        row["span"] = {"start": 0, "end": len(value), "text": value}
    return row


def source_frame(identity: str, label: str, anchors: list[str]) -> dict:
    reading = frame(identity, label, [])
    reading["anchors"] = anchors
    reading["basis"] = ["assistant:exploration-reading-not-confirmed-by-a-clinical-user"]
    return reading


def count(identity: str) -> dict:
    return {"$source": identity, "as": "integer"}


def overlap() -> dict:
    request = source_request()
    request["anchors"] = [
        anchor(request, "PS2-count", PS2),
        anchor(request, "never-count", NEVER),
        anchor(request, "total-count", TOTAL),
        anchor(request, "PS-table", BASELINE + "/measures/5"),
        anchor(request, "smoking-table", BASELINE + "/measures/4"),
        anchor(request, "denominator-table", BASELINE + "/denoms/0"),
    ]
    anchor_ids = [row["id"] for row in request["anchors"]]
    digest = request["expected_digest"]
    study_ref = "ctg:NCT00322452:" + digest
    universe = study_ref + ":baseline:BG002"
    scope = {
        "study": study_ref,
        "population": universe,
        "arm": "baseline-module:BG002-total",
        "time": "baseline-assessment-not-eligibility-time",
        "version": digest,
    }
    request["bindings"] = [
        {
            "id": "same-baseline-universe",
            "kind": "population",
            "relation": "same_universe",
            "subjects": ["WHO_PS2", "never_smoker"],
            "scope": scope,
            "sources": [{"ref": study_ref, "version": digest, "address": BASELINE, "digest": digest}],
            "status": "proposed",
            "resolution": "resolved",
            "basis": [
                "assistant:assume-these-are-exact-participant-counts-in-the-same-BG002-baseline-universe",
                "assistant:baseline-population-description-is-not-stated",
                "assistant:no-eligibility-time-alignment-is-asserted",
            ],
            "anchors": anchor_ids,
        }
    ]
    reading = source_frame(
        "aligned-baseline-counts",
        "If WHO PS 2 and never-smoking counts describe one exact BG002 baseline population",
        anchor_ids,
    )
    reading["signals"] = [
        {
            "id": "PS2-and-never-smoking",
            "kind": "overlap",
            "data": {
                "universe": universe,
                "alignment": "confirmed",
                "total": count("total-count"),
                "marginals": [
                    {
                        "ref": "WHO_PS2",
                        "universe": universe,
                        "lower": count("PS2-count"),
                        "upper": count("PS2-count"),
                    },
                    {
                        "ref": "never_smoker",
                        "universe": universe,
                        "lower": count("never-count"),
                        "upper": count("never-count"),
                    },
                ],
            },
            "support": [
                {
                    "id": "counts-plus-common-universe-reading",
                    "status": "proposed",
                    "resolution": "resolved",
                    "basis": [
                        "assistant:exact-values-do-not-establish-their-joint-population-or-clinical-meaning"
                    ],
                }
            ],
        }
    ]
    reading["binding_uses"] = [
        {
            "binding": "same-baseline-universe",
            "signal": "PS2-and-never-smoking",
            "scope": copy.deepcopy(scope),
        }
    ]
    request["interpretations"] = [reading]
    request["queries"].append(
        {"id": "registered-PS-at-most-two", "body": quantity("WHO_PS", "le", 2, "WHO_PS")}
    )
    return request


def interval(before: str, after: str, lower: int, upper: int) -> dict:
    return {
        "before": before,
        "after": after,
        "lower": lower,
        "upper": upper,
        "lower_inclusive": True,
        "upper_inclusive": True,
    }


def schedule() -> dict:
    request = source_request()
    request["anchors"] = [anchor(request, "whole-schedule-passage", SCHEDULE, whole_text=True)]
    readings = []
    for identity, label, later_interval in (
        (
            "randomization-anchored",
            "Apply each 42-day assessment tolerance around nominal days measured from randomization",
            interval("randomization", "second_permitted_assessment", 77, 91),
        ),
        (
            "successive-gaps",
            "Apply each 42-day assessment tolerance as a gap after the preceding assessment",
            interval("first_permitted_assessment", "second_permitted_assessment", 35, 49),
        ),
    ):
        reading = source_frame(identity, label, ["whole-schedule-passage"])
        reading["basis"].append({"$source": "whole-schedule-passage", "as": "text"})
        reading["signals"] = [
            {
                "id": "scheduled-assessments",
                "kind": "temporal",
                "data": {
                    "scope": "NCT00322452:registered-PFS:proposed-first-two-postbaseline",
                    "unit": "day",
                    "origin": "randomization",
                    "resolution": "resolved",
                    "events": [
                        "randomization",
                        "first_nominal_target",
                        "second_nominal_target",
                        "first_permitted_assessment",
                        "second_permitted_assessment",
                    ],
                    "constraints": [
                        interval("randomization", "first_nominal_target", 42, 42),
                        interval("first_nominal_target", "second_nominal_target", 42, 42),
                        interval("randomization", "first_permitted_assessment", 35, 49),
                        later_interval,
                    ],
                },
                "support": [
                    {
                        "id": identity + "-schedule-reading",
                        "status": "proposed",
                        "resolution": "resolved",
                        "basis": [
                            "assistant:proposed-inclusive-first-and-subsequent-tolerance-reading",
                            "assistant:nominal-targets-and-permitted-windows-are-distinct-information-channels",
                            "assistant:not-actual-attendance-or-endpoint-confirmation",
                        ],
                    }
                ],
            }
        ]
        readings.append(reading)
    request["interpretations"] = readings
    return request


def requests() -> dict[str, dict]:
    adults = source_request()
    adults["queries"].append({"id": "under-18", "body": quantity("age", "lt", 18, "Years")})
    return {
        "ipass-registered-age": adults,
        "ipass-baseline-overlap": overlap(),
        "ipass-schedule-readings": schedule(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests-only", action="store_true")
    options = parser.parse_args()
    original = FIXTURE.read_bytes()
    for name, request in requests().items():
        path = HERE / (name + "-request.json")
        path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if options.requests_only:
            continue
        completed = subprocess.run(
            [sys.executable, "-m", "TrialLedger", "reason", "--request", str(path)],
            check=True,
            text=True,
            capture_output=True,
        )
        response = json.loads(completed.stdout)
        if response["code"] != "complete":
            raise RuntimeError(f"{name}: {response['problems']}")
        path.with_name(name + "-result.json").write_text(
            json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(name + ": complete")
    if FIXTURE.read_bytes() != original:
        raise RuntimeError("The retained source changed during example generation")


if __name__ == "__main__":
    main()
