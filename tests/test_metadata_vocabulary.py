"""Public examples must remain legible without weakening epistemic boundaries.

These are authored acceptance obligations, not generated characterization tests.
Exact comparison-set counts describe that set; only the deciding elimination
evidence determines the standing of a removed candidate.
"""

import copy
import json
from pathlib import Path

import pytest

from TrialLedger.layer2 import result_semantics, run

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
OPERATIONS = (
    "entailment",
    "coordinates",
    "corpus",
    "design_bounds",
    "signals",
    "interpretations",
    "source_assertions",
)


def _assert_classified(response, label, expected_code="complete"):
    assert response["code"] == expected_code, (label, response["problems"])
    for finding in response["metadata"]["findings"]:
        assert finding["completion"] != "unclassified", (label, finding)
        assert finding["disposition"] != "unclassified", (label, finding)
        assert all(cause["kind"] != "unclassified" for cause in finding["causes"]), (label, finding)


def _guide_requests():
    """Enumerate documented request slots explicitly, never guess from nested keys."""
    description = run({"operation": "describe", "view": "full"})
    assert description["code"] == "complete"
    full = description["result"]
    cases = [("examples/" + name, request) for name, request in full["examples"].items()]
    cases.extend((name, full[name]) for name in ("exception_example", "binding_example"))
    cases.extend(
        ("capability_examples/" + name, example["request"])
        for name, example in full["capability_examples"].items()
    )
    cases.extend(("signal_examples/" + name, request) for name, request in full["signal_examples"].items())
    cases.extend(
        ("worked_session/steps/" + str(index), step["request"])
        for index, step in enumerate(full["worked_session"]["steps"])
    )
    for operation in OPERATIONS:
        focused = run({"operation": "describe", "view": operation})
        assert focused["code"] == "complete"
        cases.append(("focused/" + operation, focused["result"]["example"]))
        for name in ("exception_example", "binding_example"):
            if name in focused["result"]:
                cases.append(("focused/" + operation + "/" + name, focused["result"][name]))
    return [pytest.param(label, request, id=label) for label, request in cases]


@pytest.mark.parametrize(
    "request_path", sorted(EXAMPLES.rglob("*-request.json")), ids=lambda path: str(path.relative_to(EXAMPLES))
)
def test_every_retained_example_executes_with_classified_metadata(request_path):
    request = json.loads(request_path.read_text())
    retained_path = request_path.with_name(request_path.name.removesuffix("-request.json") + "-result.json")
    expected_code = json.loads(retained_path.read_text())["code"] if retained_path.exists() else "complete"
    response = run(request)
    _assert_classified(response, str(request_path.relative_to(ROOT)), expected_code)


@pytest.mark.parametrize(("label", "payload"), _guide_requests())
def test_every_declared_guide_request_executes_with_classified_metadata(label, payload):
    _assert_classified(run(payload), label)


@pytest.mark.parametrize(
    ("signal_status", "state", "elimination_status", "disposition"),
    [
        ("known", "ruled_out", "known", "settled"),
        ("interpolated", "ruled_out", "interpolated", "conditional"),
        ("proposed", "unresolved", None, "open"),
    ],
)
def test_candidate_elimination_uses_its_deciding_signal_not_known_query_or_unrelated_signal(
    signal_status, state, elimination_status, disposition
):
    request = json.loads((EXAMPLES / "source-workflows/ipass-joint-request.json").read_text())
    # This known candidate entails its own restriction, independently of whether
    # the observed joint population is admitted as evidence against that design.
    request["query"] = {
        "class": "Not",
        "part": copy.deepcopy(request["candidates"][0]["assertions"][0]["body"]),
    }
    request["observations"][0]["bridge"]["status"] = "known"
    request["signals"][0]["support"][1]["status"] = signal_status
    unrelated = copy.deepcopy(
        run({"operation": "describe", "view": "signals"})["result"]["signal_examples"]["overlap"]["signals"][
            0
        ]
    )
    unrelated["id"] = "unrelated-known-signal"
    request["signals"].append(unrelated)

    response = run(request)
    assert response["code"] == "complete"
    candidate = response["result"]["candidates"][0]
    assert candidate["query_decision"]["result"] == "ENTAILED"
    assert candidate["query_decision"]["status"] == "known"
    assert candidate["state"] == state
    assert candidate.get("elimination_status") == elimination_status
    finding = next(row for row in response["metadata"]["findings"] if row["path"] == "/result/candidates/0")
    assert finding["standing"] == elimination_status
    assert finding["logical_result"] == state
    assert finding["disposition"] == disposition
    if signal_status == "proposed":
        assert "no_joint" in response["result"]["remaining"]
        assert {cause["code"] for cause in finding["causes"]} == {
            "binding_unresolved",
            "proposed_refused:joint-count",
        }


def test_unknown_field_is_a_translation_question_with_its_original_refusal_code():
    response = run({"operation": "entailment", "unexpected": True})
    assert response["code"] == "refused"
    assert response["problems"] == ["unknown_field:request"]
    finding = response["metadata"]["findings"][0]
    assert finding["completion"] == "invalid"
    assert finding["disposition"] == "translation_question"
    assert finding["causes"] == [{"code": "unknown_field:request", "kind": "translation"}]


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "future_operation"},
        {"operation": "coordinates", "domain": "future_domain", "evidence": []},
    ],
)
def test_unsupported_public_requests_are_distinct_from_malformed_requests(payload):
    response = run(payload)
    assert response["code"] == "refused"
    finding = response["metadata"]["findings"][0]
    assert finding["completion"] == finding["disposition"] == "unsupported"
    assert finding["causes"][0]["kind"] == "unsupported"


def test_refusal_context_does_not_reclassify_unknown_reasoning_causes():
    refused = result_semantics.metadata("entailment", None, ["future_validation_error:request"])
    assert refused["findings"][0]["completion"] == "invalid"
    assert refused["findings"][0]["disposition"] == "translation_question"
    assert refused["findings"][0]["causes"] == [
        {"code": "future_validation_error:request", "kind": "translation"}
    ]
    assert result_semantics.cause_kind("future_validation_error:request") == "unclassified"
    assert (
        result_semantics.completion_code("UNDETERMINED", ["future_validation_error:request"])
        == "unclassified"
    )
    assert result_semantics.completion_code("FUTURE_RESULT", []) == "unclassified"


def test_refused_resource_work_remains_uncomputed_rather_than_a_translation_question():
    metadata = result_semantics.metadata("design_bounds", None, ["resource_bound:design_bounds"])
    finding = metadata["findings"][0]
    assert finding["completion"] == "limited"
    assert finding["disposition"] == "not_computed"
    assert finding["causes"] == [{"code": "resource_bound:design_bounds", "kind": "computation"}]


@pytest.mark.parametrize(
    ("standing", "expected"),
    [
        ("known", "settled"),
        ("interpolated", "conditional"),
        ("proposed", "conditional"),
        ("", "unclassified"),
    ],
)
def test_removed_candidate_disposition_preserves_its_declared_support(standing, expected):
    assert result_semantics.disposition_code("ruled_out", standing, "complete") == expected


def test_exact_corpus_counts_are_descriptions_and_never_clinically_settled_obligations():
    request = run({"operation": "describe", "view": "corpus"})["result"]["example"]
    response = run(request)
    assert response["code"] == "complete"
    assert response["result"]["frequency"]
    finding = next(row for row in response["metadata"]["findings"] if row["path"] == "/result/frequency/0")
    assert finding["logical_result"] == "computed"
    assert finding["standing"] == "known"
    assert finding["completion"] == "complete"
    assert finding["disposition"] == "descriptive"
    assert not any(
        row["disposition"] in ("settled", "design_choice") for row in response["metadata"]["findings"]
    )
