"""write_record and verify_folder — a complete pull lands on disk as three files, or not at all, and a written
folder can be certified later from its own record.

Positive: studies.json holds the provenance, the studies exactly as pulled and their content digests;
studies.csv holds the API's CSV byte for byte (CRLF kept) after a UTF-8 byte-order mark; review.xlsx
certifies; verify_folder certifies the untouched folder.
Negative: an existing directory is never overwritten; a write that fails part-way, the workbook included,
leaves neither the record nor its staging directory behind; a changed record, spreadsheet or workbook, a
missing or unreadable workbook, a repeated key, a changed provenance entry, a mislabelled study, a link
changed in the file, and a folder written by other code or another writer are never certified; a folder
without a readable record is not a record.
"""

import hashlib
import json
import subprocess
import zipfile

import pytest
from records import ongoing_study, results_study

from TrialLedger import record as record_module
from TrialLedger import warrants
from TrialLedger.ingest import Pull
from TrialLedger.record import verify_folder, write_record
from TrialLedger.workbook import WorkbookError

CSV_TEXT = 'NCT Number,Study Title\r\nNCT01234567,"Fundação, line one\nline two"\r\n'


def make_pull(csv_text=CSV_TEXT, studies=None):
    studies = studies if studies is not None else [results_study(), ongoing_study()]
    return Pull(
        query={"filter.ids": "NCT01234567,NCT07654321"},
        api_version="2.0.5",
        data_timestamp="2026-10-30T09:00:04",
        retrieved_at="2026-10-31T16:00:00Z",
        total_count=len(studies),
        studies=studies,
        csv_text=csv_text,
    )


def test_record_holds_the_pull_verbatim_with_its_digests(tmp_path):
    out = tmp_path / "run"
    written = write_record(make_pull(), out)
    assert [p.name for p in written] == ["studies.json", "studies.csv", "review.xlsx", "record.xlsx"]
    saved = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    assert saved["studies"] == [results_study(), ongoing_study()]
    provenance = saved["provenance"]
    assert provenance["query"] == {"filter.ids": "NCT01234567,NCT07654321"}
    assert provenance["data_timestamp"] == "2026-10-30T09:00:04"
    assert provenance["study_count"] == 2
    digests = [warrants.study_digest(s) for s in saved["studies"]]
    assert [d["digest"] for d in provenance["study_digests"]] == digests
    assert [d["nctId"] for d in provenance["study_digests"]] == ["NCT01234567", "NCT07654321"]
    assert provenance["merkle_root"] == warrants.merkle_root(digests)
    csv_bytes = (out / "studies.csv").read_bytes()
    assert csv_bytes == b"\xef\xbb\xbf" + CSV_TEXT.encode("utf-8")
    assert provenance["spreadsheet_sha256"] == hashlib.sha256(csv_bytes).hexdigest()


def test_a_written_folder_certifies(tmp_path):
    out = tmp_path / "run"
    write_record(make_pull(), out)
    assert verify_folder(out) == ("certified", [])


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


def test_a_failed_workbook_leaves_nothing(tmp_path, monkeypatch):
    def refuse(record, path, book):
        path.write_bytes(b"partial")
        raise WorkbookError("workbook.readback_mismatch", "simulated")

    monkeypatch.setattr(record_module, "write_workbook", refuse)
    with pytest.raises(WorkbookError):
        write_record(make_pull(), tmp_path / "run")
    assert list(tmp_path.iterdir()) == []


def test_a_changed_record_is_not_certified(tmp_path):
    out = tmp_path / "run"
    write_record(make_pull(), out)
    saved = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    saved["studies"][0]["protocolSection"]["statusModule"]["overallStatus"] = "TERMINATED"
    (out / "studies.json").write_text(json.dumps(saved), encoding="utf-8")
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems[0].startswith("record.study_digest: study 0 (NCT01234567)")


def test_a_changed_spreadsheet_or_missing_workbook_is_not_certified(tmp_path):
    out = tmp_path / "run"
    write_record(make_pull(), out)
    (out / "studies.csv").write_bytes(b"changed")
    assert verify_folder(out)[1] == ["record.spreadsheet_digest: studies.csv no longer matches its digest"]
    (out / "review.xlsx").unlink()
    assert "workbook.missing: review.xlsx is not in the folder" in verify_folder(out)[1]


def test_a_folder_without_a_record_is_not_a_record(tmp_path):
    code, problems = verify_folder(tmp_path)
    assert code == "not_a_record"
    assert "studies.json" in problems[0]


def written_folder(tmp_path, name="run"):
    out = tmp_path / name
    write_record(make_pull(), out)
    return out


def saved(out):
    return json.loads((out / "studies.json").read_text(encoding="utf-8"))


def save(out, record):
    (out / "studies.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_a_repeated_key_is_never_certified(tmp_path):
    out = written_folder(tmp_path)
    text = (out / "studies.json").read_text(encoding="utf-8")
    at = text.index('"briefTitle": ')
    altered = text[:at] + '"briefTitle": "ALTERED TITLE",\n        ' + text[at:]
    (out / "studies.json").write_text(altered, encoding="utf-8")
    assert verify_folder(out) == (
        "not_certified",
        ["record.duplicate_key: an object in studies.json repeats the key briefTitle"],
    )


def test_a_changed_provenance_entry_is_never_certified(tmp_path):
    for key, value in (("data_timestamp", "2027-01-01T00:00:00"), ("query", {"filter.ids": "NCT99999999"})):
        out = written_folder(tmp_path, key)
        record = saved(out)
        record["provenance"][key] = value
        save(out, record)
        code, problems = verify_folder(out)
        assert code == "not_certified"
        assert problems[0] == "record.record_root: the provenance no longer matches the recorded root", key


def test_a_mislabelled_study_is_never_certified(tmp_path):
    out = written_folder(tmp_path)
    record = saved(out)
    record["provenance"]["study_digests"][0]["nctId"] = "NCT99999999"
    save(out, record)
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems[0] == "record.study_label: study 0 is recorded as NCT99999999, its record is NCT01234567"


def test_an_unreadable_workbook_is_never_certified(tmp_path):
    out = written_folder(tmp_path)
    (out / "review.xlsx").write_bytes(b"not a workbook")
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems[0].startswith("workbook.unreadable: review.xlsx")


def test_a_link_changed_in_the_file_is_never_certified(tmp_path):
    out = written_folder(tmp_path)
    workbook = out / "review.xlsx"
    with zipfile.ZipFile(workbook) as source:
        parts = [(info, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(workbook, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in parts:
            if info.filename == "xl/worksheets/_rels/sheet2.xml.rels":
                data = data.replace(b"https://clinicaltrials.gov/study/NCT01234567", b"https://example.org/x")
            target.writestr(info, data)
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems[0].startswith("workbook.file_differs: review.xlsx: xl/worksheets/_rels/sheet2.xml.rels")


def test_another_code_or_writer_is_never_certified(tmp_path, monkeypatch):
    out = written_folder(tmp_path)
    provenance = saved(out)["provenance"]
    monkeypatch.setattr(record_module, "CODE_ROOT", "another code root")
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems == [
        f"record.code_root: written by TrialLedger code {provenance['code_root']} (commit "
        f"{provenance['code_commit']}), and this TrialLedger is another code root; a folder is checked only "
        "by the code that wrote it, so verify it with TrialLedger at that commit"
    ]
    words = problems[0].split("), and this TrialLedger", 1)[1]  # the message's own words, not the commit's
    assert "derivation code" not in words and "re-derives" not in words
    monkeypatch.undo()
    monkeypatch.setattr(record_module, "WRITER", "openpyxl 9.9 (etree serializer)")
    code, problems = verify_folder(out)
    assert code == "not_certified"
    assert problems[0].startswith("record.writer: the workbooks were written with openpyxl")


def test_the_provenance_names_the_commit_that_wrote_it(tmp_path):
    out = written_folder(tmp_path)
    assert saved(out)["provenance"]["code_commit"] == record_module.code_commit()


def git(repository, *args):
    command = ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    command += ["-c", "commit.gpgsign=false", *args]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def test_the_commit_marks_uncommitted_derivation_code_only(tmp_path):
    package = tmp_path / "TrialLedger"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "workbook.py").write_text("X = 1\n")
    (package / "cli.py").write_text("HELP = 'help'\n")
    assert record_module.code_commit(package) == "not a git checkout"
    git(tmp_path, "init")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "the derivation")
    head = git(tmp_path, "rev-parse", "HEAD")
    assert record_module.code_commit(package) == head
    (package / "cli.py").write_text("HELP = 'other help'\n")
    assert record_module.code_commit(package) == head
    (package / "workbook.py").write_text("X = 2\n")
    assert record_module.code_commit(package) == f"{head} with uncommitted changes to the derivation code"


def test_a_missing_record_workbook_is_never_certified(tmp_path):
    out = written_folder(tmp_path)
    (out / "record.xlsx").unlink()
    assert verify_folder(out) == ("not_certified", ["workbook.missing: record.xlsx is not in the folder"])


def test_a_workbook_over_google_sheets_cap_is_named(tmp_path, monkeypatch):
    monkeypatch.setattr(record_module, "book_size_state", lambda cells: "over_google_sheets")
    said = []
    write_record(make_pull(), tmp_path / "run", progress=said.append)
    notes = [line for line in said if line.startswith("note: ")]
    assert [note.split(" holds ")[0] for note in notes] == ["note: review.xlsx", "note: record.xlsx"]
    assert all(
        note.endswith("more than the 10,000,000 that Google Sheets opens in one spreadsheet")
        for note in notes
    )


def test_a_record_with_a_lone_surrogate_is_named_never_raised(tmp_path):
    out = written_folder(tmp_path)
    text = (out / "studies.json").read_text(encoding="utf-8")
    (out / "studies.json").write_text(
        text.replace('"briefTitle": "', '"briefTitle": "\\ud800', 1), encoding="utf-8"
    )
    code, problems = verify_folder(out)
    assert code == "not_certified" and problems[0].startswith("record.invalid_text")


def test_a_number_python_cannot_read_is_not_a_record(tmp_path):
    (tmp_path / "studies.json").write_text('{"x": ' + "9" * 5000 + "}", encoding="utf-8")
    code, problems = verify_folder(tmp_path)
    assert code == "not_a_record" and "studies.json" in problems[0]
