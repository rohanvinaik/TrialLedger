"""write_record — a complete pull lands on disk as both files, or not at all.

Positive: studies.json holds the provenance and the studies exactly as pulled; studies.csv holds the API's
CSV byte for byte (CRLF line ends kept) after a UTF-8 byte-order mark.
Negative: an existing directory is never overwritten; a write that fails part-way leaves neither the record
nor its staging directory behind.
"""

import json

import pytest

from TrialLedger.ingest import Pull
from TrialLedger.record import write_record

STUDY = {"protocolSection": {"identificationModule": {"nctId": "NCT04852770", "briefTitle": "Fundação"}}}
CSV_TEXT = 'NCT Number,Study Title\r\nNCT04852770,"Fundação, line one\nline two"\r\n'


def make_pull(csv_text=CSV_TEXT):
    return Pull(
        query={"filter.ids": "NCT04852770"},
        api_version="2.0.5",
        data_timestamp="2026-10-30T09:00:04",
        retrieved_at="2026-10-31T16:00:00Z",
        total_count=1,
        studies=[STUDY],
        csv_text=csv_text,
    )


def test_record_holds_the_pull_verbatim(tmp_path):
    out = tmp_path / "run"
    write_record(make_pull(), out)
    record = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    assert record["studies"] == [STUDY]
    assert record["provenance"]["query"] == {"filter.ids": "NCT04852770"}
    assert record["provenance"]["data_timestamp"] == "2026-10-30T09:00:04"
    assert record["provenance"]["retrieved_at"] == "2026-10-31T16:00:00Z"
    assert record["provenance"]["study_count"] == 1
    assert (out / "studies.csv").read_bytes() == b"\xef\xbb\xbf" + CSV_TEXT.encode("utf-8")


def test_existing_directory_is_never_overwritten(tmp_path):
    out = tmp_path / "run"
    out.mkdir()
    (out / "keep.txt").write_text("mine")
    with pytest.raises(FileExistsError):
        write_record(make_pull(), out)
    assert [p.name for p in out.iterdir()] == ["keep.txt"]


def test_failed_write_leaves_nothing(tmp_path):
    out = tmp_path / "run"
    with pytest.raises(UnicodeEncodeError):
        write_record(make_pull(csv_text="NCT Number\r\n\ud800\r\n"), out)
    assert list(tmp_path.iterdir()) == []
