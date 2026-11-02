"""The reviewer's workbook of a schema-3 record (refine-landscape-record unit C), against the fixture records
of tests/schema3_records.py and the contract's hand-checked examples.

Positive: the fixture agrees with the example record; the Safety rows are the example's, cell for cell; every
sheet's headers are contract.SHEETS'; the dossier shows its expected facts always and any other only when
stated; the Basis column names what each value rests on; codes and readings read in clinical words; every
listing row's address leads back to the record value the row shows (an independent check, which planted
defects fail); the same record writes the same bytes; a long listing continues on numbered sheets.
Negative: no raw registry code, no internal term, no cell blank except where its column cannot apply, a
tampered file refused, a stat the registry does not give never read as zero.
"""

import copy
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
    basis,
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
    value_words,
)

SAFETY = json.loads((EXAMPLES / "safety.json").read_text(encoding="utf-8"))
RECORD = record_of()
PLAN = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(RECORD)}


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


def resolve(record, pointer):
    """The node a JSON pointer names in the record, read without the workbook's code."""
    node = record
    for part in pointer.strip("/").split("/"):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def sheet_rows(name):
    headers, rows = PLAN[name]
    return [dict(zip(headers, (held[0] for held in row), strict=True)) for row in rows]


def dossier(study):
    return {fact: (value, label_) for _h, _l, fact, value, label_ in readout.dossier_facts(study)}


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
        ("unresolved", "no_rule_match", "Unresolved — no rule match"),
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


def test_the_basis_names_what_a_value_rests_on():
    known = {"status": "known", "rule": "r", "words": [], "result": "x", "note": ""}
    assert basis("x") == "Registry" and basis(known) == "Reading" and basis(None) == "Not stated"
    assert basis({**known, "status": "interpolated"}) == "Interpolated"
    assert basis({"status": "not_posted", "note": ""}) == "Not posted"
    assert basis({"status": "odd", "note": ""}) == "Unresolved"
    assert least_settled(["Registry", "Interpolated"]) == "Unresolved"
    assert least_settled(["Reading", "Registry"]) == "Registry"
    assert least_settled(["Reading", "Not stated"]) == "Reading"
    assert least_settled(["Not posted", "Not stated"]) == "Not posted"
    assert least_settled(["Not stated"]) == "Not stated"


# ── universes ───────────────────────────────────────────────────────────────────────────────────────────


def test_a_pack_applies_only_where_its_requirements_hold():
    assert pack_applies("setting", ("oncology.solid",), "TREATMENT") == "applies"
    assert pack_applies("setting", ("oncology.solid",), "SUPPORTIVE_CARE") == "other_purpose"
    assert pack_applies("selection", ("oncology.solid",), "SUPPORTIVE_CARE") == "applies"
    assert pack_applies("prior_advanced_lines", ("oncology.heme",), "TREATMENT") == "applies"
    assert pack_applies("setting", ("oncology.heme",), "TREATMENT") == "outside_universe"
    assert pack_applies("setting", ("general",), "TREATMENT") == "outside_universe"


def test_why_a_reading_is_not_made_is_said_in_clinical_words():
    words = readout.not_applicable_words("setting", ("oncology.heme",), "TREATMENT")
    assert words == "Not read for haematologic cancer trials (this reading is defined for solid tumours)"
    words = readout.not_applicable_words("setting", ("oncology.solid",), "SUPPORTIVE_CARE")
    assert words == "Not read for supportive care trials (this reading is defined for treatment trials)"


def test_the_universe_reading_names_its_universes():
    assert assigned(RECORD["studies"][0]) == ("known", ("oncology.heme",))
    assert assigned(RECORD["studies"][1]) == ("missing", ())
    assert assigned({"universe": {"status": "not_stated", "note": "x"}}) == ("unresolved", ())


def test_outside_its_universe_a_reading_is_not_applicable_on_the_index_with_its_reason_in_the_dossier():
    index = sheet_rows(contract.INDEX)
    for column in ("Treatment setting", "Prior lines for advanced disease", "Gene selection"):
        assert index[2][column] == "Not applicable"
    assert index[0]["Treatment setting"] == "Not applicable"
    assert index[0]["Prior lines for advanced disease"] == "Unresolved"
    facts = dossier(RECORD["studies"][0])
    assert facts["Prior lines for advanced disease"] == (
        "Not settled: the eligibility criteria do not state the prior lines of therapy for advanced disease",
        "Unresolved",
    )
    assert facts["Treatment setting"][0].startswith("Not read for haematologic cancer trials")
    assert "Treatment setting and line: what they are" in facts
    assert "Treatment setting and line: what they are" not in dossier(RECORD["studies"][2])


# ── the dossier ─────────────────────────────────────────────────────────────────────────────────────────


def test_the_dossier_shows_expected_facts_always_and_others_only_when_stated():
    heme, ptsd = dossier(RECORD["studies"][0]), dossier(RECORD["studies"][2])
    assert ptsd["Results posted"] == ("Not posted", "Not posted")
    assert heme["Results posted"] == ("Yes, first posted 09-Apr-2018", "Reading")
    assert "Acronym" not in heme and "Collaborators" not in heme and "Why stopped" not in heme
    assert ptsd["Why stopped"][0].startswith("The study was interrupted")
    assert "Who is masked" not in heme and ptsd["Who is masked"] == (
        "Investigator; Outcomes assessor",
        "Registry",
    )
    assert "Last known status (for a trial whose status is unknown)" not in heme
    assert "Publications" in heme and heme["Publications"] == ("Not stated", "Not stated")
    for internal in ("How the criteria were itemized", "Adverse-event reporting period"):
        assert internal not in ptsd
    assert heme["Adverse-event reporting period"][0].startswith("From Screening")
    assert not any(fact.startswith(("How the criteria", "Whether the record says")) for fact in heme)


def test_the_dossier_has_key_criteria_and_each_band_links_to_its_listing():
    rows = sheet_rows(contract.REVIEW)
    key = [row for row in rows if row["Section"] == "Key criteria" and row["Trial ID"] == "NCT02151981"]
    assert key[0]["Fact"] == "Detail" and key[0]["Value"].endswith("rows in Eligibility")
    assert any(row["Fact"].startswith("Key criterion") and row["Basis"] == "Reading" for row in key)
    assert {row["Basis"] for row in rows} <= {
        "Registry",
        "Reading",
        "Note",
        "Not stated",
        "Not posted",
        "Unresolved",
        "Interpolated",
        "Proposed",
    }


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


def test_the_groups_sheet_names_the_adverse_event_groups_and_holds_no_posted_measure_groups():
    record = record_of(tuple(SAFETY["trials"]))
    named = []
    for i, study in enumerate(record["studies"]):
        for row in readout.group_rows(study, i):
            assert "posted_outcomes" not in row[1][0]
            if row[2][0] == "Adverse events":
                values = [held[0] for held in row]
                named.append(
                    {
                        "trial": values[0],
                        "module": "adverse_events",
                        "column": values[4],
                        "group": values[3],
                        "title": values[5],
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
    first = sheet_rows(contract.POSTED)[0]
    assert first["Group"] == "CAT-8015 20 Microgram Per Kilogram (mcg/kg)"
    assert first["Denominator"] == 7 and first["Value"] == "NA"
    assert first["Class"] is None and first["Category"] is None
    assert first["Comment"].startswith("Data was not reported")
    outcome = {"denominators": [{"units": "Participants", "counts": [{"group": "OG000", "value": "7"}]}]}
    klass = {"denominators": [{"units": "Eyes", "counts": [{"group": "OG000", "value": "12"}]}]}
    assert readout.denominator_words([klass, outcome], "OG000") == "12 Eyes"
    assert readout.denominator_words([{}, outcome], "OG000") == "7"
    assert readout.denominator_words([{}, outcome], "OG009") == "Not stated"


def test_spread_reads_its_dispersion_or_says_why_it_has_none():
    assert spread_words("Standard Deviation", {"spread": "8.7"}) == "Standard Deviation: 8.7"
    assert spread_words("95% CI", {"lower_limit": "1", "upper_limit": "2"}) == "95% CI: 1 to 2"
    assert (
        spread_words("STANDARD_DEVIATION", {"spread": "1"}, "MeasureDispersionType")
        == "Standard deviation: 1"
    )
    assert spread_words("NA", {}) == "Not applicable"
    assert spread_words(NOT_STATED, {}) == "Not stated"


def test_an_analysis_names_its_compared_groups_interval_and_hypothesis():
    first = sheet_rows(contract.ANALYSES)[0]
    assert first["Compared groups"] == "Osimertinib 80mg; Chemotherapy"
    assert first["Confidence interval"] == "95% 2-sided interval: 0.23 to 0.41"
    assert first["Hypothesis"] == "Superiority or other (legacy)" and first["P-value"] == "<0.001"


def test_eligibility_registered_outcomes_and_flow_read_in_clinical_words():
    criteria = [row for row in sheet_rows(contract.ELIGIBILITY) if row["Trial ID"] == "NCT02151981"]
    assert criteria[5]["Readings"] == "Reading: Performance status (ECOG/WHO): 0 or 1"
    assert criteria[3]["Readings"] == "No reading produced"
    registered = sheet_rows(contract.REGISTERED)[0]
    assert registered["Category"] == "Primary" and registered["Time-point reading"] == "Reading: 28 day"
    flow = sheet_rows(contract.FLOW)[0]
    assert (flow["Milestone or reason"], flow["Participants"]) == ("Started", 7)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("63.4", ("number", 63.4, "0.0")),
        ("63.40", ("number", 63.4, "0.00")),
        ("7", ("number", 7, "0")),
        ("-0.5", ("number", -0.5, "0.0")),
        ("0", ("number", 0, "0")),
        ("NA", ("text", "NA", "")),
        ("<0.001", ("text", "<0.001", "")),
        ("1,500", ("text", "1,500", "")),
        ("007", ("text", "007", "")),
        ("-0", ("text", "-0", "")),
        ("1234567890123456", ("text", "1234567890123456", "")),
        (7, ("text", 7, "")),
    ],
)
def test_a_plain_decimal_is_a_number_in_its_own_format_and_anything_else_text(text, expected):
    assert readout.registry_number(text) == expected


def test_a_number_cell_keeps_the_registrys_decimal_places_in_the_file(written):
    book = load_workbook(written, read_only=True)
    rows = list(book[contract.BASELINE].iter_rows(min_row=2))
    headers = [c.value for c in next(book[contract.BASELINE].iter_rows(max_row=1))]
    value = rows[0][headers.index("Value")]
    assert (value.value, value.number_format) == (63.4, "0.0")


def test_an_empty_listing_and_the_across_trial_sheets_say_so_on_one_line():
    (biomarkers,) = sheet_rows(contract.BIOMARKERS)
    assert biomarkers["Trial ID"].startswith("No biomarker is named")
    (findings,) = sheet_rows(contract.FINDINGS)
    assert findings["Type"].startswith("Too few comparable trials to assess: 3 trials here")
    (standard,) = sheet_rows(contract.STANDARD)
    assert standard["Criterion"].startswith("Too few comparable trials to assess")


def test_standard_protocol_language_shows_each_criterion_with_its_counts_and_wording():
    record = copy.deepcopy(RECORD)
    record["standard_language"] = [
        {
            "criterion": "Performance status 0 or 1",
            "role": "inclusion",
            "trials": 6,
            "of_trials": 7,
            "wording": "ECOG performance status 0-1",
            "wording_from": "NCT02151981",
            "other_trials": ["NCT01", "NCT02"],
        }
    ]
    (row,) = readout.standard_rows(record)
    values = [held[0] for held in row]
    assert values == [
        "Performance status 0 or 1",
        "Inclusion",
        6,
        7,
        "“ECOG performance status 0-1”",
        "NCT02151981",
        "NCT01, NCT02",
        "/standard_language/0",
    ]


def test_every_reading_has_its_row_in_the_readings_sheet():
    readings = sheet_rows(contract.READINGS)
    pointers = {row["Address in the record"] for row in readings}
    for i, study in enumerate(RECORD["studies"]):
        for pointer, _value in readout.readings_of(study, f"/studies/{i}"):
            assert pointer in pointers
    role = next(row for row in readings if row["Address in the record"] == "/studies/0/criteria/0/role")
    assert role["Words read"] == "Its heading" and role["Result"] == "Inclusion"


def test_the_column_dictionary_names_each_columns_source_once():
    rows = sheet_rows(contract.DICTIONARY)
    pairs = [(row["Sheet"], row["Column"]) for row in rows]
    assert len(pairs) == len(set(pairs)) == sum(len(sheet.columns) for sheet in contract.SHEETS)
    phase = next(row for row in rows if (row["Sheet"], row["Column"]) == (contract.INDEX, "Phase"))
    assert phase["Registry field or rule"] == "protocolSection.designModule.phases[]"


# ── the independent record → cell check (task 3.6) ──────────────────────────────────────────────────────


def shown(value):
    """A registry value or a cell as the reader sees it: a plain decimal as its number, text as text."""
    if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value):
        return float(value)
    return float(value) if isinstance(value, (int, float)) else value


def preservation_problems(record):
    """Every Posted results, Baseline and Safety row whose cells differ from the record value its address
    names: group titles looked up in the row's own module, denominators at the innermost scope, counts per
    group in the module's order; written without the workbook's helpers."""
    plan = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(record)}
    problems = []
    for name in (contract.POSTED, contract.BASELINE):
        headers, rows = plan[name]
        for row in rows:
            cells = dict(zip(headers, (held[0] for held in row), strict=True))
            pointer = cells[contract.ADDRESS]
            if "/measurements/" not in pointer:
                continue
            # .../<measure>/classes/k/categories/c/measurements/m; a baseline measure sits in its module
            parts = pointer.strip("/").split("/")
            measure = resolve(record, "/".join(parts[:-6]))
            module = resolve(record, "/".join(parts[:-8])) if name == contract.BASELINE else measure
            klass = resolve(record, "/".join(parts[:-4]))
            measurement = resolve(record, pointer)
            group = measurement["group"]
            title = next(g["title"] for g in module["groups"] if g["id"] == group)
            if cells["Group"] != title:
                problems.append((pointer, "group", cells["Group"], title))
            if shown(cells["Value"]) != shown(measurement["value"]):
                problems.append((pointer, "value", cells["Value"], measurement["value"]))
            if isinstance(measurement.get("comment"), str) and cells["Comment"] != measurement["comment"]:
                problems.append((pointer, "comment", cells["Comment"], measurement["comment"]))
            scopes = [klass, measure] + ([module] if name == contract.BASELINE else [])
            expected = next(
                (
                    f"{c['value']} {d['units']}"
                    for scope in scopes
                    for d in scope.get("denominators") or []
                    for c in d.get("counts") or []
                    if c.get("group") == group
                ),
                "Not stated",
            )
            denominator = cells["Denominator"]
            if isinstance(denominator, int):
                denominator = f"{denominator} Participants"
            if denominator.split(";")[0] != expected:
                problems.append((pointer, "denominator", cells["Denominator"], expected))
    headers, rows = plan[contract.SAFETY]
    for row in rows:
        cells = dict(zip(headers, (held[0] for held in row), strict=True))
        pointer = cells[contract.ADDRESS]
        study = resolve(record, "/".join(pointer.strip("/").split("/")[:2]))
        event = resolve(record, pointer)
        for g, group in enumerate(study["adverse_events"]["groups"], 1):
            count = next((c for c in event["counts"] if c["group"] == group["id"]), {})
            for key, column in (("affected", "affected"), ("at_risk", "at risk"), ("events", "events")):
                held = count.get(key)
                expected = held if isinstance(held, int) else "Not reported"
                if cells[f"G{g} {column}"] != expected:
                    problems.append((pointer, f"G{g} {column}", cells[f"G{g} {column}"], expected))
    return problems


def test_every_listing_row_shows_the_value_its_address_names():
    assert preservation_problems(RECORD) == []


def test_the_check_fails_a_measurement_shown_under_the_wrong_group(monkeypatch):
    real = readout.group_title

    def shifted(groups, group):
        ids = [g.get("id") for g in groups or []]
        moved = ids[(ids.index(group) + 1) % len(ids)] if group in ids else group
        return real(groups, moved)

    monkeypatch.setattr(readout, "group_title", shifted)
    assert any(problem[1] == "group" for problem in preservation_problems(RECORD))


def test_the_check_fails_a_dropped_class_scope_denominator(monkeypatch):
    record = copy.deepcopy(RECORD)
    klass = record["studies"][0]["posted_outcomes"][0]["classes"][0]
    group = klass["categories"][0]["measurements"][0]["group"]
    klass["denominators"] = [{"units": "Eyes", "counts": [{"group": group, "value": "14"}]}]
    assert preservation_problems(record) == []
    real = readout.denominator_words
    monkeypatch.setattr(readout, "denominator_words", lambda scopes, group: real(scopes[1:], group))
    assert any(problem[1] == "denominator" for problem in preservation_problems(record))


def test_the_check_fails_a_dropped_nested_comment(monkeypatch):
    real = readout.measurement_rows

    def dropped(*args):
        return [(*row[:-1], (readout.NOT_STATED, *row[-1][1:])) for row in real(*args)]

    monkeypatch.setattr(readout, "measurement_rows", dropped)
    assert any(problem[1] == "comment" for problem in preservation_problems(RECORD))


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
    assert book.sheetnames == [sheet.name for sheet in contract.SHEETS]
    for name in book.sheetnames:
        assert next(book[name].iter_rows(values_only=True)) == readout.sheet_headers(name, n)
        declared = [c.header for c in next(s for s in contract.SHEETS if s.name == name).columns]
        fixed = [h for h in readout.sheet_headers(name, n) if not re.fullmatch(r"G\d+ .*", h)]
        assert fixed == [h for h in declared if "{n}" not in h], name


INTERNAL = re.compile(r"\b(atoms?|packs?|rule pack|unnarrowed|coordinates?|interpolated_|not_stated)\b", re.I)
BLANK_ALLOWED = {
    contract.POSTED: {"Class", "Category"},
    contract.BASELINE: {"Class", "Category"},
    contract.GROUPS: {"Column", "Totals"},
}


def test_no_raw_code_no_internal_term_and_no_blank_but_by_construction(written):
    book = load_workbook(written, read_only=True)
    codes = {code for words in contract.DISPLAY.values() for code in words if code.isupper() and "_" in code}
    for name in book.sheetnames:
        rows = list(book[name].iter_rows(values_only=True))
        headers = rows[0]
        one_line = len(rows) == 2 and rows[1][1:].count(None) >= len(headers) - 2
        for row in rows[1:]:
            for header, value in zip(headers, row, strict=True):
                assert value not in codes, (name, header, value)
                assert "without clinical words" not in str(value), (name, header)
                if name not in (contract.READINGS, contract.DICTIONARY):
                    assert not INTERNAL.search(str(value)), (name, header, value)
                if value is None and not one_line:
                    allowed = BLANK_ALLOWED.get(name, set())
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


def test_a_long_listing_continues_on_numbered_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr(readout, "CAPACITY", 100)
    path = tmp_path / "long.xlsx"
    readout.write_book(RECORD, path)
    names = load_workbook(path, read_only=True).sheetnames
    assert {"Safety", "Safety 2", "Safety 3", "Posted results 3"} <= set(names)
    assert readout.book_problems(RECORD, path) == []


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
