"""The reviewer's workbook of a schema-3 record (refine-landscape-record unit C), against the fixture records
of tests/schema3_records.py and the contract's hand-checked examples.

Positive: the fixture agrees with the example record; the Safety rows are the example's, cell for cell; every
sheet's headers are contract.SHEETS'; the same record writes the same bytes; codes read in clinical words; a
domain coordinate outside the trial's universe is blank on the index and "Does not apply" in the dossier.
Negative: no raw registry code, no cell blank except where its column cannot apply, a tampered file refused,
a stat the registry does not give never read as zero.
"""

import json
import re
import zipfile

import pytest
from openpyxl import load_workbook
from schema3_records import EXAMPLE_RECORD, EXAMPLES, NOT_STATED, indexed, record_of

from TrialLedger import contract, readout
from TrialLedger.readout import (
    absence_words,
    assigned,
    held_kind,
    item_words,
    least_settled,
    pack_applies,
    reading_words,
    result_words,
    row_lines,
    search_plain_words,
    spread_words,
    stat_cell,
    status_label,
    value_words,
)

SAFETY = json.loads((EXAMPLES / "safety.json").read_text(encoding="utf-8"))
RECORD = record_of()


def example_leaves(node, path="", positions=()):
    """Every leaf of the example record: (dotted path with list markers, positions, value)."""
    if path in contract.FIELD_NAMES or not isinstance(node, (dict, list)):
        yield path, positions, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from example_leaves(value, f"{path}.{key}".lstrip("."), positions)
    else:
        for i, value in enumerate(node):
            yield from example_leaves(value, f"{path}[]", (*positions, i))


def at_position(record, name, positions):
    node, remaining = record, list(positions)
    for segment in name.split("."):
        node = node[segment.removesuffix("[]")]
        if segment.endswith("[]"):
            node = node[remaining.pop(0)]
    return node


# ── the fixture is the contract's example ───────────────────────────────────────────────────────────────


def test_the_fixture_holds_every_value_of_the_example_record_at_its_place():
    built = record_of(tuple(study["nct"] for study in EXAMPLE_RECORD["studies"]))
    checked = 0
    for name, positions, value in example_leaves(EXAMPLE_RECORD):
        if name == "schema_version":
            continue
        assert at_position(built, name, positions) == value, name
        checked += 1
    assert checked > 60


def test_the_fixture_marks_a_value_the_registry_does_not_hold():
    ptsd = RECORD["studies"][2]
    assert ptsd["acronym"] == NOT_STATED
    assert "adverse_events" not in ptsd and "posted_outcomes" not in ptsd
    assert indexed({"a": [{"b": 1}]}, "a[].b") == [((0,), 1)]


# ── the value dispatch ──────────────────────────────────────────────────────────────────────────────────


def test_a_value_is_plain_absent_a_reading_or_missing():
    assert held_kind(None) == "missing"
    assert held_kind({"status": "not_stated", "note": "not_reported"}) == "absent"
    reading = {"status": "known", "rule": "r", "words": [], "result": "x", "note": ""}
    assert held_kind(reading) == "reading"
    assert held_kind({"date": "2020", "type": "ACTUAL"}) == "plain"
    assert held_kind({"note": "x", "status": "not_stated"}) == "plain"  # the key order is the shape's


@pytest.mark.parametrize(
    ("status", "note", "words"),
    [
        ("not_stated", "not_reported", "Not stated"),
        ("not_stated", "not_applicable", "Not applicable"),
        ("not_stated", "redacted", readout.REDACTED),
        ("not_posted", "", "Not posted"),
        ("unresolved", "no_typed_atom", "Unresolved — no typed atom"),
        ("unresolved", "", "Unresolved — the rules cannot settle it from the record"),
        ("guessed", "", "Unresolved — status guessed is not one the record defines"),
    ],
)
def test_an_absence_is_said_in_words(status, note, words):
    assert absence_words(status, note) == words


def test_codes_read_in_clinical_words_and_an_unknown_code_says_so():
    assert item_words("PHASE1", "Phase") == "Phase 1"
    assert item_words("PHASE9", "Phase") == "PHASE9 (a registry code without clinical words)"
    assert item_words(False, "") == "No" and item_words(None, "") == "Not stated"
    assert value_words(["PHASE1", "PHASE2"], "Phase", " / ") == "Phase 1 / Phase 2"
    assert value_words([]) == "Not stated" and value_words(None) == "Not stated"
    assert value_words(0) == 0 and value_words(True) == "Yes"


def test_a_reading_is_labelled_and_never_reads_as_the_registrys():
    known = {"status": "known", "rule": "r", "words": [], "result": "first_line", "note": ""}
    assert value_words(known) == "Reading: first line"
    assert reading_words({**known, "status": "interpolated"}, "x") == "Interpolated: x"
    assert reading_words({**known, "status": "unresolved", "note": "why"}, "x") == "Unresolved — why"
    assert result_words(["0", "1"]) == "0 or 1" and result_words(None) == "nothing"
    assert result_words({"a": "b_c"}) == "a: b c"


def test_status_labels_and_the_least_settled_of_several():
    assert status_label("x") == "Known" and status_label(None) == "Not stated"
    assert status_label({"status": "odd", "note": ""}) == "Unresolved"
    assert least_settled(["Known", "Interpolated"]) == "Unresolved"
    assert least_settled(["Known", "Not posted"]) == "Not posted"
    assert least_settled(["Known", "Not stated"]) == "Known"
    assert least_settled(["Not stated"]) == "Not stated"


# ── universes ───────────────────────────────────────────────────────────────────────────────────────────


def test_a_pack_applies_only_where_its_requirements_hold():
    assert pack_applies("setting", ("oncology.solid",), "TREATMENT")
    assert not pack_applies("setting", ("oncology.solid",), "SUPPORTIVE_CARE")
    assert pack_applies("selection", ("oncology.solid",), "SUPPORTIVE_CARE")
    assert pack_applies("prior_advanced_lines", ("oncology.heme",), "TREATMENT")
    assert not pack_applies("setting", ("oncology.heme",), "TREATMENT")
    assert not pack_applies("setting", ("general",), "TREATMENT")


def test_the_universe_reading_names_its_universes():
    assert assigned(RECORD["studies"][0]) == ("known", ("oncology.heme",))
    assert assigned(RECORD["studies"][1]) == ("missing", ())
    assert assigned({"universe": {"status": "not_stated", "note": "x"}}) == ("unresolved", ())


def test_outside_its_universe_a_coordinate_is_blank_on_the_index_and_said_in_the_dossier():
    plan = {name: rows for name, _headers, rows, _starts in readout.book_plan(RECORD)}
    headers = readout.sheet_headers(contract.INDEX, 5)
    ptsd = plan[contract.INDEX][2]
    for column in ("Treatment setting", "Prior lines for advanced disease", "Gene selection"):
        assert ptsd[headers.index(column)][0] is None
    heme = plan[contract.INDEX][0]
    assert heme[headers.index("Treatment setting")][0] is None
    assert heme[headers.index("Prior lines for advanced disease")][0] == "Unresolved"
    facts = {fact: value for _h, _l, fact, value, _s in readout.dossier_facts(RECORD["studies"][2])}
    assert facts["Treatment setting"].startswith("Does not apply")


# ── the listings ────────────────────────────────────────────────────────────────────────────────────────


def test_the_safety_rows_are_the_contract_examples_cell_for_cell():
    record = record_of(tuple(SAFETY["trials"]))
    n = readout.safety_groups(record)
    assert n == SAFETY["groups"]
    assert list(readout.sheet_headers(contract.SAFETY, n)) == SAFETY["columns"]
    rows = [
        tuple(held[0] for held in row)
        for i, study in enumerate(record["studies"])
        for row in readout.safety_rows(study, i, n)
    ]
    for expected in SAFETY["rows"]:
        assert tuple(expected) in rows, expected


def test_the_groups_sheet_names_each_trials_adverse_event_groups_g1_to_gn():
    record = record_of(tuple(SAFETY["trials"]))
    named = []
    for i, study in enumerate(record["studies"]):
        for row in readout.group_rows(study, i):
            if row[2][0] == "Adverse events":
                named.append(
                    {
                        "trial": row[0][0],
                        "module": "adverse_events",
                        "column": row[4][0],
                        "group": row[3][0],
                        "title": row[5][0],
                    }
                )
    assert named == SAFETY["group_columns"]


def test_a_count_the_registry_does_not_give_is_not_reported_and_a_listed_zero_stays_zero():
    assert stat_cell({"affected": 0}, "affected") == 0
    assert stat_cell({"affected": NOT_STATED}, "affected") == "Not reported"
    assert stat_cell(None, "events") == "Not reported"
    study = {
        "nct": "NCT00000001",
        "adverse_events": {
            "groups": [{"id": "EG000"}, {"id": "EG001"}],
            "events": [
                {
                    "table": "other",
                    "term": "Nausea",
                    "counts": [{"group": "EG000", "affected": 0, "at_risk": 10, "events": NOT_STATED}],
                }
            ],
        },
    }
    (row,) = readout.safety_rows(study, 0, 3)
    values = [held[0] for held in row]
    assert values[5:14] == [
        0,
        10,
        "Not reported",
        "Not reported",
        "Not reported",
        "Not reported",
        None,
        None,
        None,
    ]


def test_a_measurement_names_its_group_within_its_measure_and_its_denominator_at_its_scope():
    rows = readout.posted_rows(RECORD["studies"][0], 0)
    first = [held[0] for held in rows[0]]
    headers = readout.sheet_headers(contract.POSTED, 0)
    assert first[headers.index("Group")] == "CAT-8015 20 Microgram Per Kilogram (mcg/kg)"
    assert first[headers.index("Denominator")] == "7 Participants"
    assert first[headers.index("Value")] == "NA"
    assert first[headers.index("Comment")].startswith("Data was not reported")
    assert first[1] == "/studies/0/posted_outcomes/0/classes/0/categories/0/measurements/0"
    outcome = {"denominators": [{"units": "Participants", "counts": [{"group": "OG000", "value": "7"}]}]}
    klass = {"denominators": [{"units": "Eyes", "counts": [{"group": "OG000", "value": "12"}]}]}
    assert readout.denominator_words(outcome, klass, "OG000") == "12 Eyes"
    assert readout.denominator_words(outcome, {}, "OG000") == "7 Participants"
    assert readout.denominator_words(outcome, {}, "OG009") == "Not stated"


def test_spread_reads_its_dispersion_or_says_why_it_has_none():
    assert spread_words("Standard Deviation", {"spread": "8.7"}) == "Standard Deviation: 8.7"
    assert spread_words("95% CI", {"lower_limit": "1", "upper_limit": "2"}) == "95% CI: 1 to 2"
    assert spread_words("NA", {}) == "Not applicable"
    assert spread_words(NOT_STATED, {}) == "Not stated"


# ── the Read me ─────────────────────────────────────────────────────────────────────────────────────────


def test_the_search_reads_in_words_never_as_json():
    assert search_plain_words(RECORD["request"]).startswith("Trials asked for by number: NCT01030536")
    words = search_plain_words({"phase": ["PHASE3"], "drug": ["osimertinib"]})
    assert words == "Drug: osimertinib\nPhase: Phase 3"
    assert search_plain_words({}) == "Not stated" and search_plain_words(None) == "Not stated"


def test_the_read_me_follows_the_contracts_topics_search_first_provenance_last():
    rows = readout.guide_rows(RECORD)
    assert [row[0][0] for row in rows] == [topic for topic, _ in contract.READ_ME_TOPICS]
    assert all("{" not in str(row[1][0]) for row in rows)


def test_row_lines_counts_wrapped_lines():
    row = ((("a" * 25) + "\nb", "", "", "", "", ""), (7, "", "", "", "", ""))
    assert row_lines(row, [10, 5]) == 4
    assert row_lines(((None, "", "", "", "", ""),), [10]) == 1


# ── the written book ────────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    path = tmp_path_factory.mktemp("book") / "landscape.xlsx"
    readout.write_book(RECORD, path)
    return path


def test_every_sheet_holds_the_contracts_headers(written):
    book = load_workbook(written, read_only=True)
    n = readout.safety_groups(RECORD)
    assert book.sheetnames == list(readout.BUILT)
    for name in book.sheetnames:
        assert next(book[name].iter_rows(values_only=True)) == readout.sheet_headers(name, n)
        declared = [c.header for c in next(s for s in contract.SHEETS if s.name == name).columns]
        fixed = [h for h in readout.sheet_headers(name, n) if not re.fullmatch(r"G\d+ .*", h)]
        assert fixed == [h for h in declared if "{n}" not in h], name


def test_no_raw_code_and_no_blank_but_by_construction(written):
    book = load_workbook(written, read_only=True)
    codes = {code for words in contract.DISPLAY.values() for code in words if code.isupper() and "_" in code}
    blank_allowed = {
        contract.INDEX: {"Treatment setting", "Prior lines for advanced disease", "Gene selection"},
        contract.GROUPS: {"Column", "Totals"},
    }
    for name in book.sheetnames:
        rows = list(book[name].iter_rows(values_only=True))
        headers = rows[0]
        for row in rows[1:]:
            for header, value in zip(headers, row, strict=True):
                assert value not in codes, (name, header, value)
                assert "without clinical words" not in str(value), (name, header)
                if value is None:
                    allowed = blank_allowed.get(name, set())
                    assert header in allowed or (name == contract.SAFETY and header.startswith("G")), (
                        name,
                        header,
                    )


def test_the_index_row_is_one_line_and_the_dossier_link_lands_on_the_trial(written):
    book = load_workbook(written)
    index = book[contract.INDEX]
    review = book[contract.REVIEW]
    for row in index.iter_rows(min_row=2):
        link = row[-1].hyperlink.location
        target = link.split("!")[1]
        assert review[target].value == row[0].value
        assert index.row_dimensions[row[0].row].height == readout.LINE_POINTS


def test_the_same_record_writes_the_same_bytes(tmp_path):
    first, second = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    readout.write_book(RECORD, first)
    readout.write_book(RECORD, second)
    assert first.read_bytes() == second.read_bytes()
    assert all(info.date_time == readout.ZIP_TIME for info in zipfile.ZipFile(first).infolist())


def test_a_tampered_cell_is_refused(written, tmp_path):
    book = load_workbook(written)
    book[contract.SAFETY]["F2"] = 99
    tampered = tmp_path / "tampered.xlsx"
    book.save(tampered)
    problems = readout.book_problems(RECORD, tampered)
    assert problems and "Safety row 2" in problems[0]
    assert readout.book_problems(RECORD, written) == []


def test_a_write_whose_read_back_differs_leaves_no_file(tmp_path, monkeypatch):
    path = tmp_path / "landscape.xlsx"
    monkeypatch.setattr(readout, "book_problems", lambda *_args, **_kw: ["differs"])
    with pytest.raises(readout.ReadoutError):
        readout.write_book(RECORD, path)
    assert not path.exists()
