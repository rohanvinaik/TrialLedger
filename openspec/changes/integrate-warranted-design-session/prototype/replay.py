"""Exercise a session-input prototype using existing public operations, never a new runtime API.

This finite exemplar adapter is planning evidence. It is not imported by TrialLedger and does not define
the eventual session schema. Run with the repository environment from any working directory.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "runs"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def identity(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_children(prototype: dict) -> dict[str, dict]:
    """Restore only the source/queries slots owned by this finite prototype adapter."""
    children = {}
    for analysis in prototype["source_analyses"]:
        source_id = analysis["source"]
        source = prototype["sources"][source_id]
        request = copy.deepcopy(analysis["request"])
        request["study"] = copy.deepcopy(source["snapshot"])
        request["expected_digest"] = source["digest"]
        request["queries"] = []
        for reference in analysis["question_refs"]:
            question = prototype["questions"][reference]
            if question["source"] != source_id:
                raise ValueError("prototype_question_source_mismatch")
            request["queries"].append(copy.deepcopy(question["query"]))
        children[analysis["id"]] = request
    return children


def sensitivity_child(prototype: dict) -> tuple[str, dict]:
    """Restore only the existing max-exceptions and bridge-basis slots of the selected hypothesis."""
    request = copy.deepcopy(prototype["sensitivity"]["base_request"])
    selected = prototype["active_exception_variant"]
    variant = prototype["sensitivity"]["variants"][selected]
    bridge = request["observations"][0]["bridge"]
    bridge["max_exceptions"] = variant["maximum"]
    bridge["basis"] = copy.deepcopy(variant["basis"])
    return variant["reference_name"], request


def source_age_trial(source: dict, response: dict) -> dict:
    """Project this exemplar's registered minimum-age fact; refuse every other origin/rule/shape."""
    assertions = response["result"]["fixed"]["assertions"]
    by_id = {item["id"]: item for item in assertions}
    item = by_id["registry-age-minimumAge"]
    rule = item["rule"]
    value = item["body"]["value"]
    raw = source["snapshot"]
    nct = raw["protocolSection"]["identificationModule"]["nctId"]
    expected_ref = "ctg:" + nct + ":" + source["digest"] + "#/protocolSection/eligibilityModule/minimumAge"
    if (
        item["status"] != "known"
        or item["resolution"] != "resolved"
        or item["modality"] != "required"
        or rule["id"] != "ctg-structured-general-eligibility-age"
        or rule["version"] != "1"
        or value["kind"] != "quantity"
        or value["comparison"] != "ge"
        or value["number"] != 18
        or value["unit"] != "Years"
        or item["criterion_ref"] != expected_ref
        or rule["premises"] != [expected_ref]
    ):
        raise ValueError("prototype_age_projection_not_warranted")
    if raw["protocolSection"]["eligibilityModule"]["minimumAge"] != "18 Years":
        raise ValueError("prototype_age_field_mismatch")
    element = "inclusion:minimum_age=18_Years"
    elements = [element]
    return {
        "id": raw["protocolSection"]["identificationModule"]["nctId"],
        "sponsor": raw["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"],
        "stratum": "explicit-two-record-structured-age-comparison-not-full-clinical-comparability",
        "elements": elements,
        "typed": bool(elements),
        "basis": ["prototype:direct-structured-age-only-no-complete-eligibility-encoding"],
        "standing": {
            "status": "proposed",
            "resolution": "unresolved",
            "basis": ["prototype:other-source-content-and-comparability-not-encoded"],
        },
        "feature_standings": {
            "elements": {
                element: {
                    "status": item["status"],
                    "resolution": item["resolution"],
                    "basis": [item["criterion_ref"], rule["id"] + ":" + rule["version"]],
                }
            }
        },
        "class_unresolved": True,
    }


def age_corpus(prototype: dict, responses: dict) -> dict:
    projection = prototype["projections"][0]
    if projection["kind"] != "registered_minimum_age_18_Years":
        raise ValueError("unsupported_prototype_projection")
    return {
        "operation": "corpus",
        "trials": [
            source_age_trial(prototype["sources"][member["source"]], responses[member["analysis"]])
            for member in projection["members"]
        ],
    }


def execute(name: str, request: dict, folder: Path) -> dict:
    request_path = folder / (name + "-request.json")
    write_json(request_path, request)
    completed = subprocess.run(
        [sys.executable, "-m", "TrialLedger", "reason", "--request", str(request_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    result = json.loads(completed.stdout)
    write_json(folder / (name + "-result.json"), result)
    if completed.returncode or result["code"] != "complete":
        raise ValueError("prototype_child_refused:" + name + ":" + completed.stdout)
    return result


def original_fields_preserved(expected: object, actual: object) -> bool:
    """Allow additive result metadata while checking every retained pre-change value recursively."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and original_fields_preserved(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(expected) == len(actual)
            and all(
                original_fields_preserved(left, right) for left, right in zip(expected, actual, strict=True)
            )
        )
    return type(expected) is type(actual) and expected == actual


def replay_revision(prototype: dict, folder: Path) -> dict:
    before = identity(prototype)
    responses = {}
    comparisons = []
    children = source_children(prototype)
    name, child = sensitivity_child(prototype)
    children[name] = child
    for name, request in children.items():
        reference_folder = REFERENCE / (
            "revision-2" if name == "ipass-hypothetical-exceptions-49" else "revision-1"
        )
        expected = read_json(reference_folder / (name + "-request.json"))
        if request != expected:
            raise ValueError("prototype_child_request_changed:" + name)
        response = execute(name, request, folder)
        responses[name] = response
        reference_result = read_json(reference_folder / (name + "-result.json"))
        comparisons.append(
            {
                "child": name,
                "request_exactly_equal_to_reference": True,
                "original_result_fields_preserved": original_fields_preserved(reference_result, response),
            }
        )
    projected = age_corpus(prototype, responses)
    response = execute("registered-age-corpus", projected, folder)
    reference = read_json(HERE / "reference" / "registered-age-corpus-request.json")
    if projected != reference:
        raise ValueError("prototype_corpus_projection_changed")
    row = response["result"]["frequency"][0]
    if row["stating"] != 2 or row["trials"] != 2:
        raise ValueError("prototype_corpus_count_changed")
    if identity(prototype) != before:
        raise ValueError("prototype_mutated")
    return {
        "children": comparisons,
        "corpus_projection_matches_explicit_reference": True,
        "corpus_count": {"stating": row["stating"], "trials": row["trials"]},
        "snapshot_unchanged": True,
        "responses": responses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New replay directory outside this prototype"
    )
    output = parser.parse_args().output.resolve()
    if output == HERE or HERE in output.parents:
        raise ValueError("prototype_output_overwrites_reference")
    output.mkdir(parents=True, exist_ok=False)
    initial = read_json(HERE / "session-input.json")
    revision = read_json(HERE / "revision.json")
    if identity(initial) != revision["parent_digest"]:
        raise ValueError("prototype_parent_digest_mismatch")
    revised = copy.deepcopy(initial)
    revised["revision"] = 2
    revised["active_exception_variant"] = revision["active_exception_variant"]
    initial_result = replay_revision(initial, output / "revision-1")
    revised_result = replay_revision(revised, output / "revision-2")
    old = initial_result["responses"]["ipass-hypothetical-exceptions-48"]["result"]
    new = revised_result["responses"]["ipass-hypothetical-exceptions-49"]["result"]
    receipt = {
        "prototype_not_public_session_api": True,
        "public_child_cli_executions": 12,
        "source_files": {"session-input.json": identity(initial), "revision.json": identity(revision)},
        "revision_1": {key: value for key, value in initial_result.items() if key != "responses"},
        "revision_2": {key: value for key, value in revised_result.items() if key != "responses"},
        "revision_consequence": {
            "changed_assumption": "hypothetical maximum exceptions: 48 -> 49, not a clinician's choice",
            "before_remaining": old["remaining"],
            "after_remaining": new["remaining"],
            "before_common_consequence": old["consequence"],
            "after_common_consequence": new["consequence"],
        },
        "clinical_choices_recorded": initial["clinical_choices"],
    }
    write_json(output / "replay-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
