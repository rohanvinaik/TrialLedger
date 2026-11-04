"""Literal source structure is preserved without becoming a clinical scope assertion."""

from __future__ import annotations

import copy

import pytest
from openpyxl import load_workbook
from test_landscape_verify import completed_run, document, save

from TrialLedger import landscape, readout
from TrialLedger.landscape_verify import verify_landscape
from TrialLedger.landscape_warrants import LEGACY_SOURCE_PASSAGES_VERSIONS, retained_format


@pytest.mark.parametrize(
    ("line", "isolated", "expected"),
    [
        ("Inclusion Criteria:", False, "registry_heading"),
        ("Exclusion Criteria", False, "registry_heading"),
        ("### Crossover", False, "markdown_heading"),
        ("   # Crossover", False, "markdown_heading"),
        ("Crossover Inclusion Criteria:", True, "colon_label"),
        ("Crossover Inclusion Criteria:", False, "unstated"),
        ("* ECOG 0-2:", True, "unstated"),
        ("1. Crossover:", True, "unstated"),
        ("> Crossover:", True, "unstated"),
        ("    # Crossover", True, "unstated"),
        ("\t# Crossover", True, "unstated"),
        ("####### Not ATX", True, "unstated"),
        ("#No separator", True, "unstated"),
        ("ECOG 0-2", True, "unstated"),
        ("", True, "unstated"),
    ],
)
def test_literal_structure_has_named_outcomes(line, isolated, expected):
    assert landscape.literal_context_kind(line, isolated) == expected


def test_local_crossover_label_survives_filtering_without_becoming_clinical_scope():
    text = (
        "Inclusion Criteria:\n\n* Adults\n\nCrossover Inclusion Criteria:\n\n"
        "* ECOG 0-2\n\nExclusion Criteria:\n* Prior therapy"
    )
    entries = landscape.criterion_entries(text)
    [ecog] = [row for row in entries if "* ECOG" in row["text"]]
    assert ecog["heading"] == "inclusion"
    assert ecog["source_context"] == {
        "text": "Crossover Inclusion Criteria:",
        "kind": "colon_label",
        "source_start": text.index("Crossover"),
        "source_end": 60,
    }
    assert "scope" not in ecog and "population" not in ecog
    [prior] = [row for row in entries if "* Prior" in row["text"]]
    assert prior["source_context"]["text"] == "Exclusion Criteria:"
    assert "".join(row["text"] for row in entries) == text
    for row in entries:
        assert text[row["source_start"] : row["source_end"]] == row["text"]


def test_repeated_sections_keep_literal_context_without_forcing_a_coarse_split():
    text = "Inclusion Criteria:\nA\nInclusion Criteria:\nB"
    entries = landscape.criterion_entries(text)
    assert {row["heading"] for row in entries} == {"unsectioned"}
    assert entries[-1]["source_context"]["source_start"] == text.rindex("Inclusion")


def test_markdown_context_ignores_fenced_or_indented_code_and_bulleted_labels():
    text = "## Entry\n* Adults\n\n```\n# Fake\n```\n\n    # Indented\n\n* Fake label:\n\n* Final"
    entries = landscape.criterion_entries(text)
    assert {row["source_context"]["text"] for row in entries} == {"## Entry"}
    assert entries[-1]["source_context"]["kind"] == "markdown_heading"


def test_long_continuations_keep_same_context_and_crlf_offsets():
    text = "## Crossover\r\n" + "* " + ("long-word " * 600) + "\r\n"
    entries = landscape.criterion_entries(text)
    assert len(entries) > 3
    assert all(row["source_context"] == entries[0]["source_context"] for row in entries)
    assert entries[0]["source_context"]["text"] == "## Crossover"
    assert "".join(row["text"] for row in entries) == text


def test_unstructured_text_does_not_invent_context():
    assert all("source_context" not in row for row in landscape.criterion_entries("Adults\n* ECOG 0-2"))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"kind": "population"}, "context_kind"),
        ({"kind": []}, "context_kind"),
        ({"source_start": True}, "context_offsets"),
        ({"source_end": 300}, "context_offsets"),
        ({"text": "invented"}, "context_source_mismatch"),
    ],
)
def test_context_cannot_claim_an_unmatched_source_slice(mutation, expected):
    context = {"text": "# Entry", "kind": "markdown_heading", "source_start": 0, "source_end": 7}
    context.update(mutation)
    assert landscape.context_problem(context, "# Entry\nAdults", 8) == expected


def test_context_source_slice_is_positive():
    assert (
        landscape.context_problem(
            {"text": "# Entry", "kind": "markdown_heading", "source_start": 0, "source_end": 7},
            "# Entry\nAdults",
            8,
        )
        == "ok"
    )
    assert landscape.context_problem(None, "# Entry", 0) == "context_shape"


def test_new_record_workbook_and_source_context_replay(tmp_path):
    folder = completed_run(tmp_path / "new")
    assert verify_landscape(folder) == ("verified", [])
    record = document(folder / "landscape.json")
    assert landscape.schema_problems(record) == ()
    book = load_workbook(folder / "landscape.xlsx", read_only=True)
    headers = [cell.value for cell in book["Eligibility"][1]]
    assert "Local source context" in headers and "Context structure" in headers
    book.close()
    assert "studies[].criteria[].source_context.text" in record["fields"]


def test_explicit_legacy_projection_replays_old_format_not_new_context(tmp_path):
    folder = completed_run(tmp_path / "old")
    record = document(folder / "landscape.json")
    record["manifest"]["rule_versions"] = copy.deepcopy(LEGACY_SOURCE_PASSAGES_VERSIONS)
    record = landscape.legacy_record_projection(record)
    assert landscape.schema_problems(record) == ()
    save(folder / "landscape.json", record)
    save(folder / "manifest.json", record["manifest"])
    readout.write_book(record, folder / "landscape.xlsx")
    code, details = verify_landscape(folder)
    assert code == "verified" and details[0].startswith("legacy_format:")
    book = load_workbook(folder / "landscape.xlsx", read_only=True)
    assert [cell.value for cell in book["Eligibility"][1]] == [
        "Trial ID",
        "Address in the record",
        "Source section",
        "Passage",
        "Source passage",
    ]
    book.close()
    assert all(
        "source_context" not in passage for study in record["studies"] for passage in study["criteria"]
    )


def test_unknown_legacy_root_is_never_projected_or_verified(tmp_path):
    folder = completed_run(tmp_path / "unknown")
    record = document(folder / "landscape.json")
    record["manifest"]["rule_versions"] = copy.deepcopy(LEGACY_SOURCE_PASSAGES_VERSIONS)
    record["manifest"]["rule_versions"]["derivation_code_root"] = "unknown-old-code"
    save(folder / "landscape.json", record)
    save(folder / "manifest.json", record["manifest"])
    assert retained_format(record["manifest"]["rule_versions"]) == "current"
    assert verify_landscape(folder)[0] == "wrong_code"


@pytest.mark.parametrize("value", [4.0, True, "4"])
def test_legacy_identity_does_not_coerce_version_types(value):
    versions = dict(LEGACY_SOURCE_PASSAGES_VERSIONS)
    versions["landscape_schema"] = value
    assert retained_format(versions) == "current"


@pytest.mark.parametrize("manifest", ["malformed", [1], True])
def test_malformed_manifest_is_a_named_schema_problem_not_a_crash(tmp_path, manifest):
    folder = completed_run(tmp_path / "malformed-manifest")
    record = document(folder / "landscape.json")
    record["manifest"] = manifest
    assert ("wrong_type", "manifest") in landscape.schema_problems(record)
