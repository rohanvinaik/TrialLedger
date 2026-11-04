"""Structural headings, identity access and optional annotations retain source distinctions."""

from __future__ import annotations

from TrialLedger import readout
from TrialLedger.evidence_access import study_line


def test_study_index_copies_titles_and_acronym_without_replacing_identity():
    absent = {"status": "not_stated", "note": "not_reported"}
    study = {
        "nct": "NCT00000001",
        "brief_title": "Trial",
        "official_title": "Complete title",
        "acronym": absent,
    }
    line = study_line(study)
    assert line["nct"] == "NCT00000001"
    assert line["brief_title"] == "Trial" and line["official_title"] == "Complete title"
    assert line["acronym"] == absent
    study["acronym"] = ""
    assert study_line(study)["acronym"] == ""


def test_absent_optional_notes_are_blank_but_source_and_derivation_notes_survive():
    study = {
        "nct": "N",
        "adverse_events": {
            "groups": [{"id": "G", "title": "Drug", "other_at_risk": 10}],
            "events": [
                {"table": "other", "term": "A", "counts": [{"group": "G", "at_risk": 10, "affected": 0}]},
                {
                    "table": "other",
                    "term": "B",
                    "notes": "Source note",
                    "counts": [{"group": "G", "at_risk": 10}],
                },
                {"table": "other", "term": "C", "counts": [{"group": "G", "affected": 1}]},
            ],
        },
    }
    rows = readout.safety_rows(study, 0, 1)
    assert rows[0][-1][0] is None
    assert rows[1][-1][0] == "Source note"
    assert "checks.at_risk" in rows[2][-1][0]
    assert "/studies/0/adverse_events/groups/0/other_at_risk" in rows[2][-1][0]
    assert rows[0][5][0] == 0
    assert readout.safety_rows(study, 0, 1, legacy_notes=True)[0][-1][0] == "Not stated"
