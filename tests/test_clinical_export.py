"""A clinical handoff preserves source meaning and the complete canonical result.

The managed decisions below are invented renderer fixtures, not clinical evidence
or an authenticated exchange. Tests exercise the actual exported file read-back.
"""

import hashlib
import json
import time
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest
from openpyxl import load_workbook

from TrialLedger import reasoning_artifacts
from TrialLedger.clinical_export import ExportError, export_review, option_wording_code, text_display_code


def retained(store: Path, *, question="Should NYHA IV be allowed?"):
    response = {
        "code": "complete",
        "operation": "design_session",
        "problems": [],
        "result": {
            "session_id": "invented-session",
            "revision": "one",
            "decisions": [
                {
                    "id": "nyha",
                    "question": question,
                    "target": {"kind": "new_trial", "ref": "invented"},
                    "code": "design_choice",
                    "standing": "known",
                    "coverage": "represented_restriction",
                    "coverage_limit": "Only the NYHA restriction is represented.",
                    "selected": None,
                    "origin": {"kind": "computed", "refs": []},
                    "alternatives": [
                        {
                            "id": "iv",
                            "label": "NYHA IV permitted",
                            "analysis": "iv-check",
                            "code": "feasible",
                            "query": {"nyha": "IV"},
                            "warrant": {
                                "result": "UNDETERMINED",
                                "status": None,
                                "proof": ["nyha-premise"],
                                "blockers": ["undecided_by_constraints"],
                            },
                            "origin_refs": ["invented-not-a-real-confirmation"],
                        },
                        {
                            "id": "non-iv",
                            "label": "Everyone must be NYHA I–III",
                            "analysis": "non-iv-check",
                            "code": "feasible",
                            "query": {"not": {"nyha": "IV"}},
                            "warrant": {
                                "result": "UNDETERMINED",
                                "status": None,
                                "proof": ["nyha-premise"],
                                "blockers": ["undecided_by_constraints"],
                            },
                            "origin_refs": [],
                        },
                    ],
                    "distinctions": [],
                }
            ],
            "sources": [],
            "premises": [],
            "effective_premises": [],
        },
    }
    return reasoning_artifacts.save(store, {"operation": "design_session", "session": {}}, response)


def source_record(path: Path):
    baseline = {
        "population": "All randomized participants",
        "groups": [
            {"id": "G1", "title": "Drug"},
            {"id": "G2", "title": "Comparator"},
            {"id": "G3", "title": "Total"},
        ],
        "denominators": [
            {
                "units": "Participants",
                "counts": [
                    {"group": "G1", "value": 2373},
                    {"group": "G2", "value": 2371},
                    {"group": "G3", "value": 4744},
                ],
            }
        ],
        "measures": [
            {
                "title": "NYHA functional class",
                "unit": "Participants",
                "param_type": "Count of Participants",
                "classes": [
                    {
                        "categories": [
                            {
                                "title": "II",
                                "measurements": [
                                    {"group": "G1", "value": 1606},
                                    {"group": "G2", "value": 1597},
                                    {"group": "G3", "value": 3203},
                                ],
                            },
                            {
                                "title": "III",
                                "measurements": [
                                    {"group": "G1", "value": 747},
                                    {"group": "G2", "value": 751},
                                    {"group": "G3", "value": 1498},
                                ],
                            },
                            {
                                "title": "IV",
                                "measurements": [
                                    {"group": "G1", "value": 20},
                                    {"group": "G2", "value": 23},
                                    {"group": "G3", "value": 43},
                                ],
                            },
                        ]
                    }
                ],
            }
        ],
    }
    record = {"studies": [{"nct": "NCT-invented", "baseline": baseline}]}
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


def rows(path: Path, sheet: str):
    book = load_workbook(path, read_only=True, data_only=False)
    try:
        return list(book[sheet].values)
    finally:
        book.close()


def test_text_display_must_not_refuse_exact_cell_boundary_or_crlf():
    assert text_display_code("x" * 32767) == "literal_text"
    assert text_display_code("") == "literal_text"
    assert text_display_code("雪\r\n") == "literal_text"
    assert text_display_code("=1+2") == "literal_text"
    assert text_display_code("😀" * 16383 + "x") == "literal_text"


def test_text_display_must_not_silently_accept_overflow_or_xml_controls():
    assert text_display_code("x" * 32768) == "reference_required"
    assert text_display_code("a\x01b") == "reference_required"
    assert text_display_code("\x00") == "reference_required"
    assert text_display_code(False) == "invalid_text"
    assert text_display_code(None) == "invalid_text"
    assert text_display_code(32767) == "invalid_text"
    assert text_display_code("😀" * 16384) == "reference_required"
    assert text_display_code("\ufffe") == "reference_required"
    assert text_display_code("\uffff") == "reference_required"


def test_validation_must_not_delete_a_carriage_return_to_make_an_overflow_fit():
    """Validation may substitute CR for counting, but must never erase its UTF-16 unit."""
    assert text_display_code("x" * 32767 + "\r") == "reference_required"
    assert text_display_code("x" * 32766 + "\r") == "literal_text"


def test_permission_wording_requires_the_complete_existing_feasibility_outcome():
    assert (
        option_wording_code("feasible", "UNDETERMINED", ["undecided_by_constraints"])
        == "allowed_not_required"
    )
    assert option_wording_code("feasible", "ENTAILED", []) == "use_logical_code"
    assert option_wording_code("infeasible", "REFUTED", []) == "use_logical_code"


def test_permission_wording_must_not_fill_proposal_scope_conflict_or_unknown_gaps():
    assert option_wording_code("feasible", "UNDETERMINED", ["proposed_refused:A"]) == "use_logical_code"
    assert option_wording_code("feasible", "UNDETERMINED", ["open_scope:cohort:A"]) == "use_logical_code"
    assert option_wording_code("conflict", "INCONSISTENT", []) == "use_logical_code"
    assert option_wording_code("future", "UNDETERMINED", ["undecided_by_constraints"]) == "use_logical_code"
    assert option_wording_code("feasible", "UNDETERMINED", []) == "use_logical_code"
    assert option_wording_code("feasible", "REFUTED", ["undecided_by_constraints"]) == "use_logical_code"
    assert option_wording_code("feasible", "INCONSISTENT", ["undecided_by_constraints"]) == "use_logical_code"
    assert option_wording_code("feasible", "ENTAILED", ["undecided_by_constraints"]) == "use_logical_code"
    assert (
        option_wording_code("feasible", "UNDETERMINED", ["undecided_by_constraints", "resource_bound"])
        == "use_logical_code"
    )


def test_export_has_decisions_options_canonical_artifact_and_verified_manifest(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    result = export_review(store, identity, tmp_path / "out")
    assert result["code"] == "complete"
    folder = Path(result["folder"])
    assert folder == tmp_path / "out" / "review"
    assert (folder / "artifacts" / f"{identity}.json").read_bytes() == (
        store / f"{identity}.json"
    ).read_bytes()
    assert rows(Path(result["workbook"]), "Decision list")[1][0] == "Should NYHA IV be allowed?"
    options = rows(Path(result["workbook"]), "Options")
    assert all("allowed but not required" in row[3] and "UNDETERMINED" in row[3] for row in options[1:])
    assert all(row[2] == "Compatible with the represented restrictions (feasible)" for row in options[1:])
    assert "nyha-premise" in options[1][5]
    manifest = json.loads(Path(result["manifest"]).read_text())
    for filename, receipt in manifest["files"].items():
        body = (folder / filename).read_bytes()
        assert hashlib.sha256(body).hexdigest() == receipt["sha256"]
        assert len(body) == receipt["bytes"]
    text = Path(result["decision_list"]).read_text()
    assert "Should NYHA IV be allowed?" in text
    assert "undecided_by_constraints" in text
    assert "not authenticated confirmation" in text


def test_baseline_preserves_all_nine_cells_and_matching_denominators_without_summing(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    source_record(source)
    source.with_suffix(".xlsx").write_bytes(b"source-workbook-copy-is-not-rewritten")
    original = source.read_bytes()
    result = export_review(store, identity, tmp_path / "out", source_record=source)
    values = rows(Path(result["workbook"]), "Baseline values")
    assert len(values) == 10
    assert [row[6] for row in values[1:]] == [1606, 1597, 3203, 747, 751, 1498, 20, 23, 43]
    assert [row[4] for row in values[1:]] == ["G1", "G2", "G3"] * 3
    matrix = rows(Path(result["workbook"]), "Baseline tables")
    assert matrix[4][2:5] == ("Drug [G1]", "Comparator [G2]", "Total [G3]")
    assert [row[2:5] for row in matrix[5:8]] == [(1606, 1597, 3203), (747, 751, 1498), (20, 23, 43)]
    assert json.loads(values[-1][11])[0]["value"] == 4744
    assert json.loads(values[-1][10])["module"]["value"] == "All randomized participants"
    book = load_workbook(result["workbook"], data_only=False)
    try:
        target = book["Baseline values"]["N10"].hyperlink.target
        assert target.endswith("/classes/0/categories/2/measurements/2")
        assert book.sheetnames[0] == "Read me"
        assert book["Decision list"]["H2"].value == "Open exact result"
        assert book["Decision list"]["H2"].hyperlink.target.startswith("artifacts/")
    finally:
        book.close()
    assert source.read_bytes() == original
    folder = Path(result["folder"])
    assert (folder / "landscape.json").read_bytes() == original
    assert (folder / "landscape.xlsx").read_bytes() == b"source-workbook-copy-is-not-rewritten"


def test_unknown_group_is_retained_in_values_and_never_guessed_into_comparative_table(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    record = source_record(source)
    record["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"][0][
        "group"
    ] = "Drug"
    source.write_text(json.dumps(record))
    result = export_review(store, identity, tmp_path / "out", source_record=source)
    assert rows(Path(result["workbook"]), "Baseline values")[1][5] == "unknown_group"
    matrix = rows(Path(result["workbook"]), "Baseline tables")
    assert matrix[5][2] == "Not listed for this category"
    assert json.loads(matrix[5][5])[0]["measurement"]["value"] == 1606


@pytest.mark.parametrize("question", ["=2+3", "+1", "-1", "@SUM(A1:A2)", "", "雪\r\nNew line"])
def test_formula_like_and_unicode_text_never_become_formulas_or_disappear(tmp_path, question):
    store = tmp_path / "store"
    identity = retained(store, question=question)["id"]
    result = export_review(store, identity, tmp_path / "out")
    book = load_workbook(result["workbook"], data_only=False)
    try:
        cell = book["Decision list"]["A2"]
        assert cell.data_type == "s"
        assert cell.value == (question if question else '""')
        assert all(cell.data_type != "f" for sheet in book for row in sheet for cell in row)
    finally:
        book.close()


@pytest.mark.parametrize("question", ["x" * 32768, "source\x01text", "😀" * 16384, "\ufffe", "\uffff"])
def test_excel_unrepresentable_text_has_explicit_reference_and_exact_canonical_copy(tmp_path, question):
    store = tmp_path / "store"
    identity = retained(store, question=question)["id"]
    result = export_review(store, identity, tmp_path / "out")
    assert rows(Path(result["workbook"]), "Decision list")[1][0].startswith(
        "Full value retained at artifacts/"
    )
    payload = json.loads((Path(result["folder"]) / "artifacts" / f"{identity}.json").read_text())
    assert payload["response"]["result"]["decisions"][0]["question"] == question


def test_existing_output_and_symlink_are_never_replaced(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    out = tmp_path / "out"
    out.mkdir()
    protected = out / "important.txt"
    protected.write_text("caller content")
    with pytest.raises(ExportError, match="export_output_exists"):
        export_review(store, identity, out)
    assert protected.read_text() == "caller content"
    link = tmp_path / "link"
    link.symlink_to(out)
    with pytest.raises(ExportError, match="export_output_exists"):
        export_review(store, identity, link)


def test_staging_failure_creates_no_published_output(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    source.write_text('{"studies": null}')
    with pytest.raises(ValueError, match="malformed_collection"):
        export_review(store, identity, tmp_path / "out", source_record=source)
    assert not (tmp_path / "out").exists()
    assert list(tmp_path.glob(".clinical-review-*")) == []


def test_included_result_remains_separate_and_is_not_assigned_to_a_decision(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    related = reasoning_artifacts.save(
        store,
        {"operation": "future_operation"},
        {"operation": "future_operation", "code": "complete", "result": {"future": "opaque"}, "problems": []},
    )["id"]
    result = export_review(store, identity, tmp_path / "out", include=[related])
    assert (Path(result["folder"]) / "artifacts" / f"{related}.json").is_file()
    assert len(rows(Path(result["workbook"]), "Decision list")) == 2
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert manifest["included"] == [related]


def test_refused_main_result_never_becomes_a_successful_review(tmp_path):
    store = tmp_path / "store"
    identity = reasoning_artifacts.save(
        store,
        {"operation": "entailment"},
        {"code": "refused", "operation": "entailment", "result": None, "problems": ["invalid"]},
    )["id"]
    with pytest.raises(ExportError, match="export_requires_complete_result"):
        export_review(store, identity, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_unknown_standing_is_not_promoted_by_the_renderer(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    payload = reasoning_artifacts.load(store, identity)
    altered = deepcopy(payload["response"])
    altered["result"]["decisions"][0]["code"] = "future_unknown_code"
    new_id = reasoning_artifacts.save(store, payload["request"], altered)["id"]
    result = export_review(store, new_id, tmp_path / "out")
    assert rows(Path(result["workbook"]), "Decision list")[1][1] == "Unclassified (future_unknown_code)"
    assert "unclassified" in json.dumps(rows(Path(result["workbook"]), "Findings"))


def test_repeated_measurement_is_not_selected_or_added_in_group_matrix(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    record = source_record(source)
    category = record["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0]
    category["measurements"].append({"group": "G1", "value": 0, "comment": "second posted measurement"})
    source.write_text(json.dumps(record))
    result = export_review(store, identity, tmp_path / "out", source_record=source)
    copied = json.loads(rows(Path(result["workbook"]), "Baseline tables")[5][2])
    assert [value["measurement"]["value"] for value in copied] == [1606, 0]
    assert len(rows(Path(result["workbook"]), "Baseline values")) == 11


def test_every_matching_denominator_scope_remains_visible(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    record = source_record(source)
    measure = record["studies"][0]["baseline"]["measures"][0]
    measure["denominators"] = [
        {"units": "Evaluated participants", "counts": [{"group": "G1", "value": 2000}]}
    ]
    measure["classes"][0]["denominators"] = [
        {"units": "Reported participants", "counts": [{"group": "G1", "value": 1900}]}
    ]
    source.write_text(json.dumps(record))
    result = export_review(store, identity, tmp_path / "out", source_record=source)
    denominators = json.loads(rows(Path(result["workbook"]), "Baseline values")[1][11])
    assert [(row["scope"], row["value"]) for row in denominators] == [
        ("class", 1900),
        ("measure", 2000),
        ("module", 2373),
    ]


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (False, False),
        (None, "null"),
        ("", '""'),
        (1234567890123456789, "1234567890123456789"),
        (0.12345678901234568, "0.12345678901234568"),
    ],
)
def test_scalar_values_keep_zero_false_null_empty_and_precision_distinct(tmp_path, value, expected):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    source = tmp_path / "landscape.json"
    record = source_record(source)
    record["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"][0][
        "value"
    ] = value
    source.write_text(json.dumps(record))
    result = export_review(store, identity, tmp_path / "out", source_record=source)
    copied = rows(Path(result["workbook"]), "Baseline values")[1][6]
    assert copied == expected
    assert type(copied) is type(expected)


def test_refused_related_analysis_retains_its_translation_problem(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    related = reasoning_artifacts.save(
        store,
        {"operation": "entailment"},
        {
            "operation": "entailment",
            "code": "refused",
            "result": None,
            "problems": ["unknown_field:invented"],
        },
    )["id"]
    result = export_review(store, identity, tmp_path / "out", include=[related])
    findings = rows(Path(result["workbook"]), "Findings")
    failures = [row for row in findings[1:] if row[0] == "Related analysis"]
    assert failures
    assert all(row[4] == "translation_question" and row[5] == "invalid" for row in failures)
    assert "unknown_field:invented" in json.dumps(failures)


@pytest.mark.parametrize("include", [[{}], [None], [False], ["../outside"], "not-a-list"])
def test_malformed_include_never_selects_an_unverified_path(tmp_path, include):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    with pytest.raises(ExportError, match="invalid_.*artifact"):
        export_review(store, identity, tmp_path / "out", include=include)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("operation", ["design_bounds", "signals"])
def test_standalone_public_results_do_not_assume_the_session_premise_shape(tmp_path, operation):
    from TrialLedger.layer2 import run

    store = tmp_path / "store"
    main_id = retained(store)["id"]
    request = run({"operation": "describe", "view": operation})["result"]["example"]
    response = run(request)
    assert response["code"] == "complete"
    extra = reasoning_artifacts.save(store, request, response)["id"]
    result = export_review(store, main_id, tmp_path / "out", include=[extra])
    payload = json.loads((Path(result["folder"]) / "artifacts" / f"{extra}.json").read_text())
    assert payload["response"]["result"]["premises"] == response["result"]["premises"]
    sources = rows(Path(result["workbook"]), "Sources and origins")
    assert any(row[0] == extra for row in sources[1:])
    findings = rows(Path(result["workbook"]), "Findings")
    assert any(row[0] == "Related analysis" and row[1] == operation for row in findings[1:])


def test_same_canonical_inputs_produce_the_same_workbook_across_writing_times(tmp_path):
    store = tmp_path / "store"
    identity = retained(store, question="CR\r\nLF")["id"]
    first = export_review(store, identity, tmp_path / "first")
    time.sleep(1.1)
    second = export_review(store, identity, tmp_path / "second")
    assert Path(first["workbook"]).read_bytes() == Path(second["workbook"]).read_bytes()
    assert Path(first["manifest"]).read_bytes() == Path(second["manifest"]).read_bytes()
    with zipfile.ZipFile(first["workbook"]) as archive:
        assert all(item.date_time == (2000, 1, 1, 0, 0, 0) for item in archive.infolist())


def test_readable_wording_keeps_open_choice_simulated_origin_and_codes(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    payload = reasoning_artifacts.load(store, identity)
    payload["response"]["result"]["decisions"][0]["origin"] = {
        "kind": "user_choice",
        "basis": ["simulated exchange: not a real confirmation"],
    }
    altered = reasoning_artifacts.save(store, payload["request"], payload["response"])["id"]
    result = export_review(store, altered, tmp_path / "out")
    text = Path(result["decision_list"]).read_text()
    assert "Open design choice (design_choice)" in text
    assert (
        "The represented proposition is allowed but not required under these restrictions (UNDETERMINED)"
        in text
    )
    assert "Caller-declared clinical choice: simulated exchange: not a real confirmation" in text
    assert "not authenticated confirmation" in text


def test_undetermined_with_unsettled_reading_is_never_worded_as_allowed(tmp_path):
    store = tmp_path / "store"
    identity = retained(store)["id"]
    payload = reasoning_artifacts.load(store, identity)
    for option in payload["response"]["result"]["decisions"][0]["alternatives"]:
        option["code"] = "evidence_question"
        option["warrant"]["blockers"] = ["proposed_refused:unconfirmed"]
    altered = reasoning_artifacts.save(store, payload["request"], payload["response"])["id"]
    result = export_review(store, altered, tmp_path / "out")
    text = Path(result["decision_list"]).read_text()
    assert "allowed but not required" not in text.casefold()
    assert "Not determined by the represented criteria (UNDETERMINED)" in text
    assert "This reading has not been confirmed (proposed_refused:unconfirmed)" in text
