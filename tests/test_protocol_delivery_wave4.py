"""Wave-4 walkthrough fixes: effective outcomes in comparisons, statistics, changes, models, relations."""

import json
from copy import deepcopy
from pathlib import Path

from openpyxl import Workbook, load_workbook

from TrialLedger import clinical_delivery, reasoning_artifacts
from TrialLedger.clinical_export import _relation_section, export_review
from TrialLedger.layer2 import protocol_view, run

RESULTS = Path(__file__).resolve().parents[1] / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results"
)


def fixture(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text())


def exported(tmp_path: Path, name: str, mutate) -> tuple[Path, str]:
    """Run a fixture request, let `mutate` edit the retained response, then store and export it."""
    request = fixture(name)["request"]
    response = run(request)
    assert response["code"] == "complete", response
    mutate(response)
    # The view is a pure function of the result; drop the one rendered before the edit so it is re-rendered.
    response.pop("protocol_view", None)
    stored = reasoning_artifacts.save(tmp_path / "store", request, response)
    review = Path(export_review(tmp_path / "store", stored["id"], tmp_path / "out")["folder"])
    return review, (review / "decision-list.md").read_text()


def rows(review: Path, sheet: str) -> list[dict]:
    values = list(load_workbook(review / "design-review.xlsx")[sheet].values)
    return [dict(zip(values[0], row, strict=False)) for row in values[1:]]


def refuse_alternative_claims(response: dict) -> None:
    alternative = response["result"]["protocol"]["decisions"][0]["alternatives"][0]
    for check in alternative["checks"]:
        for claim in check["claims"]:
            claim["admission"] = "binding_unresolved"
            claim["effective_outcome"] = "unresolved"
        check["check_code"] = "undetermined"


def test_alternative_claims_show_effective_outcome_and_admission_not_the_raw_outcome(tmp_path):
    review, text = exported(tmp_path, "decision-plan-comparison", refuse_alternative_claims)
    drafted = next(r for r in rows(review, "Plan comparisons") if r["Alternative"] == "as-drafted")
    cell = drafted["Claim outcomes under this alternative"]
    assert "not applied" in cell and "binding_unresolved" in cell
    assert "holds under the declared inputs" not in cell.split("extend")[0]
    assert "calculated; its claims are not applied" in drafted["Full-coverage gap"]
    assert "not applied" in text.split("- as-drafted:")[1].split("- extend:")[0]


def test_an_undetermined_alternative_names_the_check_that_decides_it(tmp_path):
    result = deepcopy(fixture("decision-plan-comparison")["result"])
    alternative = result["protocol"]["decisions"][0]["alternatives"][0]
    refuse_alternative_claims({"result": result})
    view = clinical_delivery.protocol_delivery_view(result)
    deciding = view["decisions"][0]["alternatives"][0]["deciding_checks"]
    assert deciding[0]["check"] == alternative["checks"][0]["id"]
    assert deciding[0]["required"] is True and deciding[0]["check_code"] == "undetermined"
    assert "not applied" in deciding[0]["reason"]


def test_retained_binomial_statistics_show_exact_values_with_decimals(tmp_path):
    stat = {
        "n": 36,
        "critical_count": 33,
        "p0": "4/5",
        "p1": "19/20",
        "null_rejection_probability": "1/20",
        "power": "9/10",
    }

    def add(response: dict) -> None:
        extend = response["result"]["protocol"]["decisions"][0]["alternatives"][1]
        extend["checks"][0]["children"][0]["statistics"] = [stat]

    review, text = exported(tmp_path, "decision-plan-comparison", add)
    cell = next(r for r in rows(review, "Plan comparisons") if r["Alternative"] == "extend")[
        "Retained binomial plan (exact, with rounded decimal)"
    ]
    assert "sample size n 36" in cell and "critical count (reject at or above) 33" in cell
    assert "null rejection probability 1/20 (0.0500)" in cell and "power 9/10 (0.9000)" in cell
    assert "Retained binomial plan: " in text


def test_binomial_value_and_decision_changes_read_before_to_after():
    before, after = protocol_view.change_lines(
        [
            {"signal": "design", "field": "n", "before": 30, "after": 36},
            {"signal": "design", "field": "critical_count", "before": 28, "after": 33},
            {"signal": "design", "field": "null_rejection_probability", "before": "1/25", "after": "1/20"},
            {"field": "selected", "before": "as-drafted", "after": None},
            {"field": "disposition", "before": "repair_choice", "after": "design_choice"},
            {
                "alternative": "extend",
                "field": "compatibility",
                "before": "undetermined",
                "after": "compatible_under_declared_checks",
            },
        ]
    )
    assert "Check finding design, sample size n: 30" in before[0]
    assert after[0].endswith(": 36") and after[1].endswith(": 33")
    assert after[2].endswith("1/20 (0.0500)") and before[2].endswith("1/25 (0.0400)")
    assert before[3].endswith("as-drafted") and after[3].endswith("none selected")
    assert "design_choice (" in after[4]
    assert "Alternative extend, compatibility: compatible_under_declared_checks (" in after[5]


def test_changes_sheet_and_list_carry_the_readable_value_changes(tmp_path):
    def add(response: dict) -> None:
        response["answer_diff"] = {
            "decisions": [],
            "analyses": [],
            "protocol_checks": [
                {
                    "id": "week12-schedule",
                    "code": "changed",
                    "axes": ["verdict"],
                    "changes": [{"signal": "s", "field": "n", "before": 30, "after": 36}],
                }
            ],
            "protocol_decisions": [
                {
                    "id": "collection-plan",
                    "code": "changed",
                    "axes": ["verdict"],
                    "changes": [{"field": "selected", "before": "as-drafted", "after": "extend"}],
                }
            ],
        }

    review, text = exported(tmp_path, "decision-plan-comparison", add)
    assert "sample size n: 30 → 36" in text and "selected alternative: as-drafted → extend" in text
    changes = {r["Item"]: r for r in rows(review, "Changes")}
    assert "30" in changes["week12-schedule"]["Before"] and "36" in changes["week12-schedule"]["After"]
    assert "extend" in changes["collection-plan"]["After"]


def test_model_assumptions_are_stated_in_words_with_role_status_and_guarantee(tmp_path):
    def keep(response: dict) -> None:
        pass

    review, text = exported(tmp_path, "efficacy-binomial-and-external", keep)
    section = text.split("### Model assumptions")[1].split("###")[0]
    assert "fixed sample size with independent, identically distributed binary responses" in section
    assert "alignment" in section and "missing" in section
    assert "fixed_n" in section and "declared, known" in section
    assert "exact, conditional on the declared model" in section
    sheet = rows(review, "Model assumptions")
    assert (
        sheet and "Withheld" not in str(sheet[0]["Why withheld"]) and "alignment" in sheet[0]["Why withheld"]
    )


def test_withheld_binomial_claim_names_the_role_and_keeps_values_visible():
    view = protocol_view.view(fixture("efficacy-binomial-and-external")["result"])
    claim = next(
        c for ch in view["checks"] for c in ch["claims"] if c["claim"] == "null_rejection_probability"
    )
    assert "assumption_missing:alignment" in claim["wording"]
    assert "stay visible; they are not applied" in claim["wording"]


def test_relation_rows_warn_when_a_reading_differs_and_word_a_conflict_plainly():
    result = {
        "definition_checks": [
            {
                "id": "rel",
                "relation": "equivalent",
                "code": "conflict",
                "status": "known",
                "blockers": [],
                "declaration": {
                    "left": {"protocol_check": "a", "address": "/x", "status": "known"},
                    "right": {"protocol_check": "b", "address": "/y", "status": "known"},
                },
                "observed_match": {"left": "exact_copy", "right": "differs"},
                "checks": [
                    {
                        "direction": "left_implies_right",
                        "result": {"result": {"decision": {"result": "ENTAILED", "blockers": []}}},
                    },
                    {
                        "direction": "right_implies_left",
                        "result": {"result": {"decision": {"result": "UNDETERMINED", "blockers": []}}},
                    },
                ],
            },
            {"id": "ordinary", "relation": "implies", "declaration": {"left": {"analysis": "x"}}},
        ]
    }
    rows_ = protocol_view.relation_rows(result)
    assert [r["id"] for r in rows_] == ["rel"]
    assert [d["result"] for d in rows_[0]["directions"]] == ["ENTAILED", "UNDETERMINED"]
    book = Workbook()
    lines = _relation_section(book, rows_, "artifact")
    text = "\n".join(lines)
    assert "this reading differs from the value at its address" in text
    assert "refuted by a counterexample" in text and "not a contradiction inside the protocol" in text
    assert "right implies left: UNDETERMINED" in text


def test_a_refused_check_child_is_a_not_computed_finding_and_never_none_found():
    result = deepcopy(fixture("schedule-refuted-and-conditional")["result"])
    check = result["protocol"]["checks"][0]
    check["children"][0]["refusal"] = ["estimand_variable_mismatch"]
    check["children"][0]["signals"] = []
    view = clinical_delivery.protocol_delivery_view(result)
    summary = next(c for c in view["check_summaries"] if c["id"] == check["id"])
    assert summary["code"] == "refused"
    row = next(c for c in view["checks"] if c["id"] == check["id"])
    assert "estimand_variable_mismatch" in row["not_computed_items"][0]["text"]
    assessments = next(s for s in view["sections"] if s["id"] == "assessments")
    assert assessments["coverage"] == "not_computed"
    assert assessments["findings"] != "none_found_in_declared_checks"


def test_a_consistent_plain_signal_is_a_no_finding_row():
    result = deepcopy(fixture("schedule-refuted-and-conditional")["result"])
    check = result["protocol"]["checks"][0]
    check["children"][0]["signals"].append(
        {
            "id": "dep",
            "kind": "dependencies",
            "code": "consistent",
            "calculation_code": "consistent",
            "blockers": [],
            "admission": {"code": "accepted"},
            "claim_admission": [],
        }
    )
    row = clinical_delivery.protocol_delivery_view(result)["checks"][0]
    assert [c["code"] for c in row["clean_signals"]] == ["consistent"]


def test_definition_reference_standing_and_superseded_adoptions_are_named():
    result = deepcopy(fixture("efficacy-binomial-and-external")["result"])
    protocol = result["protocol"]
    target = next(
        o for o in protocol["objects"] if isinstance(o.get("data"), dict) and "definition" in o["data"]
    )
    target["data"]["definition"]["status"] = "proposed"
    adoption = next(r for r in protocol_view.view(result)["adoption"] if r["object"] == target["id"])
    assert adoption["definition_standing"] == "proposed"
    premise = {
        "id": "adopt:gone:v0",
        "kind": "adoption",
        "payload": {"objects": [{"id": target["id"], "version": "an-older-version"}]},
    }
    result["effective_premises"] = [*result.get("effective_premises", []), premise]
    words = protocol_view.superseded_adoptions(result)
    assert "names a superseded version" in words["adopt:gone:v0"] and "not used" in words["adopt:gone:v0"]


def test_compact_findings_carry_the_witness_and_say_when_it_is_cut(monkeypatch):
    result = deepcopy(fixture("policy-violation-known")["result"])
    view = clinical_delivery.protocol_delivery_view(result)
    witnessed = [f for f in view["delivery_findings"] if f.get("witness")]
    assert witnessed and witnessed[0]["witness_truncated"] is False
    long = "x" * (clinical_delivery.WITNESS_CHARACTERS + 50)
    monkeypatch.setattr(protocol_view, "witness_wording", lambda row, child: long)
    cut = [
        f for f in clinical_delivery.protocol_delivery_view(result)["delivery_findings"] if f.get("witness")
    ]
    assert cut and all(f["witness_truncated"] is True for f in cut)
    assert all(len(f["witness"]) == clinical_delivery.WITNESS_CHARACTERS + 1 for f in cut)


def test_an_optional_not_computed_check_is_named_beside_computed_required_checks():
    result = deepcopy(fixture("efficacy-binomial-and-external")["result"])
    for check in result["protocol"]["checks"]:
        if check["id"] == "survival-method":
            check["required"] = False
    efficacy = next(s for s in protocol_view.view(result)["sections"] if s["id"] == "efficacy")
    assert efficacy["coverage"] == "not_computed"
    assert (
        "Required checks computed; optional check survival-method not computed" in efficacy["findings_text"]
    )
    assert "missing inputs" in efficacy["findings_text"]
