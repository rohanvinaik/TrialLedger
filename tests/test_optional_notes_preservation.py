"""Optional annotation blanks never license dropping an actual source note."""

from acceptance import preserve
from TrialLedger import contract, readout


def test_independent_preservation_accepts_only_a_genuinely_optional_note_blank():
    event = {"table": "other", "term": "A", "counts": [{"group": "G", "at_risk": 10, "affected": 0}]}
    study = {"nct": "N", "adverse_events": {"groups": [{"id": "G", "title": "Drug"}], "events": [event]}}
    record = {"studies": [study]}
    sheet = next(s for s in contract.SHEETS if s.name == contract.SAFETY)
    cells = dict(
        zip(
            readout.sheet_headers(contract.SAFETY, 1),
            [c[0] for c in readout.safety_rows(study, 0, 1)[0]],
            strict=True,
        )
    )
    row = preserve.Row(contract.SAFETY, 1, cells)
    findings, _ = preserve.row_findings(record, sheet, row)
    assert not [f for f in findings if f.field == "Safety: Notes"]
    event["notes"] = "Source definition limits reporting to the treatment period."
    findings, _ = preserve.row_findings(record, sheet, row)
    assert any(f.field == "Safety: Notes" and f.code == "blank" for f in findings)
