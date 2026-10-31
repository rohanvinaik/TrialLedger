"""record_problems — whatever in a written record no longer matches its own content digests.

Positive: a record whose provenance, studies and spreadsheet are as written has no problems, whatever the key
order of its studies.
Negative: a changed value, a swapped pair of studies, a dropped study, a mislabelled study, a changed
provenance entry, a changed or missing spreadsheet, and a record that never had digests or a record root are
each named, never passed; a provenance that is not an object is never read, even when it names every digest;
a recorded digest that is not text is named, never hashed; an empty spreadsheet digest is judged like any
other.
"""

import copy

from records import ongoing_study, results_study

from TrialLedger.record import DIGEST_KEYS, digests, record_problems, record_root

SPREADSHEET = "﻿NCT Number\r\nNCT01234567\r\n".encode()
PROVENANCE = {"query": {"filter.ids": "NCT01234567,NCT07654321"}, "data_timestamp": "2026-10-30T09:00:04"}


def written():
    studies = [results_study(), ongoing_study()]
    provenance = dict(PROVENANCE)
    provenance.update(digests(provenance, studies, SPREADSHEET))
    return {"provenance": provenance, "studies": studies}


def test_an_unchanged_record_has_no_problems():
    assert record_problems(written(), SPREADSHEET) == []


def test_key_order_is_not_a_change():
    record = written()
    record["studies"][0] = dict(reversed(list(record["studies"][0].items())))
    record["provenance"] = dict(reversed(list(record["provenance"].items())))
    assert record_problems(record, SPREADSHEET) == []


def test_a_changed_value_is_named():
    record = written()
    record["studies"][1]["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
    problems = record_problems(record, SPREADSHEET)
    assert problems[0].startswith("record.study_digest: study 1 (NCT07654321)")
    assert problems[1].startswith("record.merkle_root")
    assert len(problems) == 2


def test_swapped_studies_are_named():
    record = written()
    record["studies"].reverse()
    problems = record_problems(record, SPREADSHEET)
    assert [p.split(":")[0] for p in problems] == [
        "record.study_digest",
        "record.study_label",
        "record.study_digest",
        "record.study_label",
        "record.merkle_root",
    ]
    assert problems[1] == "record.study_label: study 0 is recorded as NCT01234567, its record is NCT07654321"


def test_a_mislabelled_study_is_named():
    record = written()
    record["provenance"]["study_digests"][0]["nctId"] = "NCT99999999"
    assert record_problems(record, SPREADSHEET) == [
        "record.study_label: study 0 is recorded as NCT99999999, its record is NCT01234567",
        "record.record_root: the provenance no longer matches the recorded root",
    ]


def test_a_changed_provenance_entry_is_named():
    record = written()
    record["provenance"]["data_timestamp"] = "2027-01-01T00:00:00"
    assert record_problems(record, SPREADSHEET) == [
        "record.record_root: the provenance no longer matches the recorded root"
    ]
    record = written()
    record["provenance"]["merkle_root"] = 7
    assert record_problems(record, SPREADSHEET)[-1].startswith("record.record_root")


def test_a_dropped_study_is_named():
    record = written()
    record["studies"].pop()
    problems = record_problems(record, SPREADSHEET)
    assert problems[0] == "record.study_count: 2 digests recorded for 1 studies"
    assert "record.merkle_root: the studies no longer match the recorded root" in problems


def test_a_changed_or_missing_spreadsheet_is_named():
    assert record_problems(written(), SPREADSHEET + b"x") == [
        "record.spreadsheet_digest: studies.csv no longer matches its digest"
    ]
    assert record_problems(written(), None) == ["record.no_spreadsheet: studies.csv is missing"]


def test_a_record_without_digests_is_never_certified():
    for missing in ("merkle_root", "record_root", "study_digests", "spreadsheet_sha256"):
        record = written()
        del record["provenance"][missing]
        assert record_problems(record, SPREADSHEET)[0].startswith("record.no_digests"), missing
    assert record_problems({"studies": []}, SPREADSHEET)[0].startswith("record.no_digests")
    assert record_problems("not a record", SPREADSHEET)[0].startswith("record.no_digests")


def test_a_single_study_record_has_no_problems():
    studies = [ongoing_study()]
    record = {"provenance": digests({}, studies, SPREADSHEET), "studies": studies}
    assert record_problems(record, SPREADSHEET) == []


def test_studies_that_are_not_a_list_are_no_studies():
    record = written()
    record["studies"] = "ab"
    assert record_problems(record, SPREADSHEET)[0] == "record.study_count: 2 digests recorded for 0 studies"


def test_recorded_digests_that_are_not_a_list_are_none():
    record = written()
    record["provenance"]["study_digests"] = "ab"
    assert record_problems(record, SPREADSHEET)[0] == "record.study_count: 0 digests recorded for 2 studies"


def test_a_recorded_digest_that_is_not_a_digest_is_named():
    record = written()
    broken = copy.deepcopy(record)
    broken["provenance"]["study_digests"][0] = "garbage"
    problems = record_problems(broken, SPREADSHEET)
    assert problems[0].startswith("record.study_digest: study 0 (None)")
    assert problems[1] == "record.study_label: study 0 is recorded as None, its record is NCT01234567"


def test_a_provenance_that_is_not_an_object_is_never_read():
    for provenance in (list(DIGEST_KEYS), " ".join(DIGEST_KEYS)):
        record = {"provenance": provenance, "studies": []}
        assert record_problems(record, SPREADSHEET) == [
            "record.no_digests: the record carries no content digests (written before warrants)"
        ]


def test_a_recorded_spreadsheet_digest_that_is_not_text_is_named_never_hashed():
    for value in (7, None, ["digest"]):
        record = written()
        record["provenance"]["spreadsheet_sha256"] = value
        assert record_problems(record, SPREADSHEET) == [
            "record.spreadsheet_digest: studies.csv no longer matches its digest",
            "record.record_root: the provenance no longer matches the recorded root",
        ]


def test_an_empty_spreadsheet_digest_is_judged_like_any_other():
    record = written()
    provenance = record["provenance"]
    provenance["spreadsheet_sha256"] = ""
    provenance["record_root"] = record_root(provenance)
    assert record_problems(record, SPREADSHEET) == [
        "record.spreadsheet_digest: studies.csv no longer matches its digest"
    ]


def test_anything_added_to_the_provenance_is_named():
    record = written()
    record["provenance"]["study_digests"][0]["extra"] = "changed provenance"
    assert record_problems(record, SPREADSHEET) == [
        "record.record_root: the provenance no longer matches the recorded root"
    ]
