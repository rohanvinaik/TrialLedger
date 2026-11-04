"""Views preserve separately computed feasibility support and logical warrant support."""

from TrialLedger.layer2.service import run


def test_feasibility_standing_is_consumed_without_relabelling_the_logical_warrant():
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    response = run(request)
    for decision, view in zip(response["result"]["decisions"], response["decision_view"], strict=True):
        for option, shown in zip(decision["alternatives"], view["options"], strict=True):
            assert option["code"] == "feasible"
            assert shown["standing"] == option["feasibility_status"] == "known"
            assert shown["logical_standing"] == option["warrant"]["status"] is None


def test_decision_view_retains_actual_computation_context_independent_of_caller_labels():
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    for analysis in request["session"]["analyses"]:
        analysis["parameters"]["context"] = {"cohort": "renal"}
    for alternative in request["session"]["decisions"][0]["alternatives"]:
        alternative["label"] = "A label that does not name a cohort"
    response = run(request)
    assert response["code"] == "complete"
    assert all(option["context"] == {"cohort": "renal"} for option in response["decision_view"][0]["options"])


def test_evidence_display_parts_reconstruct_long_exact_source_and_proposed_note(tmp_path):
    from openpyxl import load_workbook

    from TrialLedger import reasoning_artifacts
    from TrialLedger.clinical_export import export_review
    from TrialLedger.layer2 import source_evidence

    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    text = ("α\r\nExact long source with a cohort qualifier. " * 100) + "\n"
    note = "Caller reading; proposed. " * 100
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": text},
        }
    }
    snapshot = source_evidence.snapshot(study)
    request["session"]["sources"].append(
        {"id": "source", "study": study, "expected_digest": snapshot["digest"]}
    )
    request["session"]["decisions"][0]["evidence"] = [
        {
            "id": "long",
            "source": "source",
            "role": "reading",
            "note": note,
            "scope": "Caller scope only",
            "anchor": {
                "id": "long",
                "digest": snapshot["digest"],
                "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
                "expected": text,
            },
        }
    ]
    response = run(request)
    saved = reasoning_artifacts.save(tmp_path / "store", request, response)
    exported = export_review(tmp_path / "store", saved["id"], tmp_path / "out")
    book = load_workbook(exported["workbook"])
    try:
        rows = list(book["Decision evidence"].iter_rows(min_row=2, values_only=True))
        copied = [row for row in rows if row[3] == "Exact source copy"]
        notes = [row for row in rows if row[3] == "Caller note (reading)"]
        assert "".join(row[5] for row in copied) == text
        assert "".join(row[5] for row in notes) == note
        assert all(row[6] == "proposed" for row in notes)
        assert len(copied) > 1 and copied[0][4] == "1/" + str(len(copied))
        assert all(len(row[5]) <= 320 for row in copied + notes)
        assert book["Decision list"]["I2"].hyperlink.target.startswith("#'Decision evidence'!A")
    finally:
        book.close()


def test_display_parts_bound_newlines_as_well_as_width_without_dropping_any_character():
    from TrialLedger.clinical_export import _display_parts

    for text in ["", "\n" * 1000, "\r\n" * 500, "α" * 4096, "line\r\n" * 100]:
        parts = _display_parts(text)
        assert "".join(parts) == text
        assert all(0 < len(part) <= 320 and part.count("\n") <= 5 for part in parts)


def test_exact_empty_source_is_not_displayed_as_an_absent_annotation():
    from openpyxl import Workbook

    from TrialLedger.clinical_export import _evidence_rows

    book = Workbook()
    _evidence_rows(
        book,
        [
            {
                "id": "d",
                "caller_question": {"text": "Question"},
                "evidence": [
                    {
                        "id": "empty",
                        "role": "quote",
                        "note": "",
                        "declared_scope": "",
                        "source": {"nct": "NCT00000001"},
                        "anchor": {"address": "/text", "value": ""},
                    }
                ],
            }
        ],
        "a" * 64,
    )
    try:
        assert book["Decision evidence"]["D4"].value == "Exact source copy"
        assert book["Decision evidence"]["F4"].value == '""'
        assert book["Decision evidence"]["F4"].value != book["Decision evidence"]["F2"].value
    finally:
        book.close()
