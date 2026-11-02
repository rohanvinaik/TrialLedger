"""The reviewer's workbook of a schema-3 record (refine-landscape-record unit C), against records made by
the record's own assembly (tests/schema3_records.py) from the contract's saved bodies, and the contract's
hand-checked examples.

Positive: the Safety rows are the example's, cell for cell; every sheet's headers are contract.SHEETS'; the
dossier shows its expected facts always and any other only when stated; the Basis column names what each value
rests on; codes and readings read in clinical words; every listing row's address leads back to the record
value the row shows (an independent check, which planted defects fail); the same record writes the same bytes;
a long listing continues on numbered sheets.
Negative: no raw registry code, no internal term, no cell blank except where its column cannot apply, a
tampered file refused, a stat the registry does not give never read as zero.
"""

import copy
import io
import json
import re
import zipfile

import pytest
from openpyxl import load_workbook
from schema3_records import EXAMPLES, NOT_STATED, record_of

from TrialLedger import contract, readout
from TrialLedger.readout import (
    absence_words,
    basis,
    held_kind,
    item_words,
    least_settled,
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
# RxNav's ATC answer for osimertinib, as the baseline's classes.json holds it, in that file's shape.
OSIMERTINIB = {"Osimertinib": {"axes": {"ATC": {"code": "found", "assertions": [["L01EB"]]}}}}
PLAN = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(RECORD)}


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


def test_the_records_are_the_assemblys_own():
    assert RECORD["schema_version"] == contract.SCHEMA_VERSION
    ptsd = RECORD["studies"][2]
    assert ptsd["acronym"] == NOT_STATED
    assert ptsd["results_posted"]["status"] == "not_posted"
    assert not isinstance(ptsd["adverse_events"], dict) or "events" not in ptsd["adverse_events"]


# ── the value dispatch ──────────────────────────────────────────────────────────────────────────────────


def test_a_value_is_plain_absent_a_reading_or_missing():
    assert held_kind(None) == "missing"
    assert held_kind({"status": "not_stated", "note": "not_reported"}) == "absent"
    reading = {"status": "known", "rule": "r", "words": [], "result": "x", "note": ""}
    assert held_kind(reading) == "reading"
    assert held_kind({"date": "2020", "type": "ACTUAL"}) == "plain"
    # recognised by their fields and shape, never by the order of their keys
    assert held_kind({"note": "x", "status": "not_stated"}) == "absent"
    assert held_kind({"note": "", "result": 1, "words": [], "rule": "r", "status": "known"}) == "reading"
    assert held_kind({"status": "not_stated", "note": None}) == "plain"
    assert held_kind({"status": "known", "rule": "r", "words": "w", "result": 1, "note": ""}) == "plain"
    assert held_kind({"status": "known", "rule": None, "words": [], "result": 1, "note": ""}) == "plain"
    assert held_kind({"status": "x", "note": "y", "extra": 1}) == "plain"
    assert held_kind("text") == "plain" and held_kind(0) == "plain"


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
    assert reading_words({**known, "status": "interpolated"}, "x").startswith("Unresolved")
    assert reading_words({**known, "status": "proposed"}, "x").startswith("Unresolved")
    assert reading_words({**known, "status": "unresolved", "note": "why"}, "x") == "Unresolved — why"
    assert result_words(["0", "1"]) == "0 or 1" and result_words(None) == "nothing"
    assert result_words({"a": "b_c"}) == "a: b c"


def test_the_basis_names_what_a_value_rests_on():
    known = {"status": "known", "rule": "r", "words": [], "result": "x", "note": ""}
    assert basis("x") == "Registry" and basis(known) == "Direct rule" and basis(None) == "Not stated"
    assert basis({**known, "status": "interpolated"}) == "Unresolved"
    assert basis({"status": "not_posted", "note": ""}) == "Not posted"
    assert basis({"status": "odd", "note": ""}) == "Unresolved"
    assert least_settled(["Registry", "Interpolated"]) == "Unresolved"
    assert least_settled(["Direct rule", "Registry"]) == "Registry"
    assert least_settled(["Direct rule", "Not stated"]) == "Direct rule"
    assert least_settled(["Not posted", "Not stated"]) == "Not posted"
    assert least_settled(["Not stated"]) == "Not stated"


# ── universes ───────────────────────────────────────────────────────────────────────────────────────────


# ── the dossier ─────────────────────────────────────────────────────────────────────────────────────────


def test_the_dossier_shows_expected_facts_always_and_others_only_when_stated():
    heme, ptsd = dossier(RECORD["studies"][0]), dossier(RECORD["studies"][2])
    assert ptsd["Results posted"] == ("Not posted", "Not posted")
    assert heme["Results posted"] == ("Yes, first posted 09-Apr-2018", "Direct rule")
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


def test_the_groups_sheet_names_the_adverse_event_groups_g1_to_gn():
    record = record_of(tuple(SAFETY["trials"]))
    named = []
    for i, study in enumerate(record["studies"]):
        for row in readout.group_rows(study, i):
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
    assert first[contract.DENOMINATOR] == 7 and first["Value"] == "NA"
    assert first["Class"] is None and first["Category"] is None
    assert first["Comment"].startswith("Data was not reported")
    outcome = {"denominators": [{"units": "Participants", "counts": [{"group": "OG000", "value": "7"}]}]}
    klass = {"denominators": [{"units": "Eyes", "counts": [{"group": "OG000", "value": "12"}]}]}
    assert (
        readout.denominator_words([klass, outcome], "OG000")
        == "Class denominator: 12 Eyes; Measure denominator: 7 Participants"
    )
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
    source = next(study for study in RECORD["studies"] if study["nct"] == "NCT02151981")
    assert [row["Source passage"] for row in criteria] == [piece["text"] for piece in source["criteria"]]
    assert all("Role" not in row and "Readings" not in row for row in criteria)
    registered = sheet_rows(contract.REGISTERED)[0]
    assert registered["Category"] == "Primary" and "Time-point reading" not in registered
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
        # a float that underflows to zero, or overflows, is never written as a number
        ("0." + "0" * 399 + "1", ("text", "0." + "0" * 399 + "1", "")),
        ("1" + "0" * 400 + ".5", ("text", "1" + "0" * 400 + ".5", "")),
        # more decimal places than a number format shows
        ("0." + "0" * 30 + "1", ("text", "0." + "0" * 30 + "1", "")),
        ("0." + "0" * 29 + "1", ("number", 1e-30, "0." + "0" * 30)),
        # many decimal places the float gives back exactly at its own places
        ("0.300000000000000", ("number", 0.3, "0." + "0" * 15)),
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


def test_the_column_dictionary_names_each_columns_source_once():
    rows = sheet_rows(contract.DICTIONARY)
    pairs = [(row["Sheet"], row["Column"]) for row in rows]
    columns = sum(len(sheet.columns) for sheet in contract.SHEETS if sheet.name != contract.READ_ME)
    assert len(pairs) == len(set(pairs)) == columns
    assert not any(sheet == contract.READ_ME for sheet, _column in pairs)
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
            denominator = cells[contract.DENOMINATOR]
            if isinstance(denominator, int):
                denominator = f"{denominator} Participants"
            first_denominator = denominator.split(";")[0]
            for scope_name in contract.DENOMINATOR_SCOPE_LABELS:
                first_denominator = first_denominator.removeprefix(f"{scope_name} denominator: ")
            if first_denominator != expected:
                problems.append((pointer, "denominator", cells[contract.DENOMINATOR], expected))
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
    assert [row[0][0] for row in rows] == [
        topic
        for topic, _ in contract.READ_ME_TOPICS
        if topic != "Treatment setting and line" or readout.conditional_index_columns(RECORD)
    ]
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
        assert next(book[name].iter_rows(values_only=True)) == readout.sheet_headers(name, n, RECORD)
        declared = [c.header for c in next(s for s in contract.SHEETS if s.name == name).columns]
        fixed = [h for h in readout.sheet_headers(name, n, RECORD) if not re.fullmatch(r"G\d+ .*", h)]
        expected = [h for h in declared if "{n}" not in h]
        assert fixed == expected, name


INTERNAL = re.compile(r"\b(atoms?|packs?|rule pack|unnarrowed|coordinates?|interpolated_|not_stated)\b", re.I)
# The contract's blank-by-construction columns, by sheet (the Safety G columns and the empty listing's line
# are checked apart).
BLANK_ALLOWED: dict[str, set[str]] = {}
for (_sheet, _kind), _columns in contract.BLANK_BY_CONSTRUCTION.items():
    BLANK_ALLOWED.setdefault(_sheet, set()).update(_columns)


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
                if name != contract.DICTIONARY:
                    assert not INTERNAL.search(str(value)), (name, header, value)
                if value is None and not one_line:
                    allowed = BLANK_ALLOWED.get(name, set())
                    assert header in allowed or (name == contract.SAFETY and header.startswith("G")), (
                        name,
                        header,
                    )


def test_the_index_wraps_full_text_and_the_dossier_link_lands_on_the_trial(written):
    book = load_workbook(written)
    index = book[contract.INDEX]
    review = book[contract.REVIEW]
    widths = [index.column_dimensions[column.column_letter].width for column in index[1]]
    for row in index.iter_rows(min_row=2):
        link = row[-1].hyperlink.location
        target = link.split("!")[1]
        assert review[target].value == row[0].value
        needed = row_lines(tuple((held.value,) for held in row), widths)
        assert index.row_dimensions[row[0].row].height == min(
            contract.MAX_ROW_HEIGHT_POINTS, round(needed * readout.LINE_POINTS, 2)
        )
        assert all(held.alignment.wrap_text for held in row if isinstance(held.value, str))


@pytest.mark.parametrize(
    ("header", "text"),
    (
        (
            "Acronym or short title",
            "A Randomized Multicenter Study of Treatment in Participants With Previously Treated Disease "
            "With Long Term Assessment of Safety, Clinical Outcomes, and Patient Reported Function " * 2,
        ),
        (
            "Sponsor",
            "Department of Clinical Research, University Medical Center and Affiliated Research Hospitals "
            * 3,
        ),
        (
            "Design",
            "Treatment; Randomized; Parallel assignment; masking Quadruple "
            "(Participant, Care provider, Investigator, Outcomes assessor)",
        ),
    ),
)
def test_long_index_fields_get_wrapped_height_and_short_rows_stay_compact(header, text):
    headers = readout.sheet_headers(contract.INDEX, 0)
    column = headers.index(header)
    short = tuple(readout.cell("Short", "known") for _ in headers)
    long = list(short)
    long[column] = readout.cell(text, "known")
    data, _ = readout._write_book([(contract.INDEX, headers, [short, tuple(long)], [])], ("", "", ""))
    book = load_workbook(io.BytesIO(data))
    index = book[contract.INDEX]
    expected_widths = readout.LAYOUT[contract.INDEX][1]
    for held in index[1]:
        assert index.column_dimensions[held.column_letter].width == expected_widths[held.value]
    assert index.row_dimensions[2].height == readout.LINE_POINTS
    width = index.column_dimensions[index.cell(1, column + 1).column_letter].width
    needed = -(-len(text) // width)
    assert needed > 1
    assert index.row_dimensions[3].height >= needed * readout.LINE_POINTS
    assert index.cell(3, column + 1).value == text
    assert index.cell(3, column + 1).alignment.wrap_text is True


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


# ── the contract's display data (negative tests) ─────────────────────────────────────────────────────────


def test_every_cell_uses_the_contracts_words_and_never_another_word_for_unresolved(written):
    book = load_workbook(written, read_only=True)
    basis_words = set(contract.BASIS_WORDS.values()) | set(contract.STATUS_WORDS.values())
    for name in book.sheetnames:
        rows = list(book[name].iter_rows(values_only=True))
        headers = rows[0]
        for row in rows[1:]:
            cells = dict(zip(headers, row, strict=True))
            assert not any("Not settled" in str(value) for value in row), name
            if name == contract.REVIEW:
                assert cells["Basis"] in basis_words, cells
            if name == contract.SAFETY:
                assert cells["Table"] in contract.WHICH_LIST_WORDS.values(), cells["Table"]
            if name == contract.REGISTERED:
                assert cells["Category"] in contract.WHICH_LIST_WORDS.values(), cells["Category"]
            if name == contract.ELIGIBILITY:
                assert cells["Source section"] in contract.READING_CODE_WORDS.values(), cells


def test_a_count_is_in_the_general_format_and_a_registry_decimal_in_its_own(written):
    book = load_workbook(written, read_only=True)
    safety = list(book[contract.SAFETY].iter_rows(min_row=2, max_row=2))[0]
    counts = [cell for cell in safety if isinstance(cell.value, int)]
    assert counts and all(cell.number_format == contract.NUMBER_FORMATS["count"] for cell in counts)
    assert readout.registry_number("63.40")[2] == "0.00" and readout.registry_number("7")[2] == "0"


def test_an_empty_listing_is_one_line_without_an_address():
    record = copy.deepcopy(RECORD)
    for study in record["studies"]:
        study["posted_outcomes"] = []
    plan = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(record)}
    headers, rows = plan[contract.POSTED]
    (row,) = rows
    values = dict(zip(headers, (held[0] for held in row), strict=True))
    assert values["Trial ID"] == contract.EMPTY_LISTING_WORDS[contract.POSTED]
    assert values[contract.ADDRESS] is None
    assert all(value is None for header, value in values.items() if header != "Trial ID")


def test_the_contracts_display_tables_are_whole():
    assert set(contract.ROW_GRAINS) == {sheet.name for sheet in contract.SHEETS}
    index = {column.header for column in contract.SHEETS[1].columns}
    assert set(contract.INDEX_COMPACT) <= index
    for (sheet, _kind), columns in contract.BLANK_BY_CONSTRUCTION.items():
        if sheet == "every listing":
            continue
        headers = {column.header for column in next(s for s in contract.SHEETS if s.name == sheet).columns}
        assert all(column in headers or column.startswith("G{n}") for column in columns), sheet
    assert set(contract.EMPTY_LISTING_WORDS) <= {sheet.name for sheet in contract.SHEETS}


def test_a_posted_group_is_one_groups_row_per_title_and_description_and_each_measurement_links_to_it():
    groups = sheet_rows(contract.GROUPS)
    posted = [row for row in groups if row["Module"] == "Posted results"]
    keys = [(row["Trial ID"], row["Title"], row["Description"]) for row in posted]
    assert posted and len(keys) == len(set(keys))
    first = posted[0]
    assert first[contract.ADDRESS] == "/studies/0/posted_outcomes/0/groups/0"
    assert first["Outcome measures"].startswith("Maximum Tolerated Dose (MTD) (/studies/0/posted_outcomes/0/")
    assert first["Column"] is None and first["Totals"] is None
    others = [row for row in groups if row["Module"] != "Posted results"]
    assert all(row["Outcome measures"] is None for row in others)
    headers, rows = PLAN[contract.POSTED]
    at = headers.index("Group")
    link = rows[0][at][1]
    target = int(link.rsplit("A", 1)[1]) - 2
    group_row = dict(
        zip(PLAN[contract.GROUPS][0], (held[0] for held in PLAN[contract.GROUPS][1][target]), strict=True)
    )
    assert group_row["Title"] == rows[0][at][0] and group_row["Module"] == "Posted results"
    assert not any("OG0" in str(row[at][0]) for row in rows)


def test_a_denominator_names_any_unit_but_participants_and_never_drops_one():
    other = {"denominators": [{"units": "Eyes", "counts": [{"group": "OG000", "value": "12"}]}]}
    missing = {"denominators": [{"counts": [{"group": "OG000", "value": "9"}]}]}
    assert readout.denominator_words([other], "OG000") == "12 Eyes"
    assert readout.denominator_words([missing], "OG000") == "9 (units not stated)"
    assert "participants unless otherwise specified" in contract.DENOMINATOR


RECORD_JSON = re.compile(r"[{\[]\s*['\"]")


def test_no_cell_ever_holds_the_records_json(written):
    book = load_workbook(written, read_only=True)
    for name in book.sheetnames:
        for row in book[name].iter_rows(min_row=2, values_only=True):
            for value in row:
                assert not RECORD_JSON.search(str(value)), (name, value)
    assert not RECORD_JSON.search(str(readout.value_words([{"a": 1}, {"b": "c"}])))
    assert readout.value_words({"kind": "x_y"}) == "kind: x y"


def group_link_problems(record, plan):
    """Every Baseline and Participant flow row whose Group cell does not link to the Groups row of the
    measurement's own group (the group of its ID in its module), checked through the addresses alone."""
    groups_headers, groups_rows = plan[contract.GROUPS]
    problems = []
    for sheet in (contract.BASELINE, contract.FLOW):
        headers, rows = plan[sheet]
        at = headers.index("Group")
        for row in rows:
            pointer = row[1][0]
            if not isinstance(pointer, str):
                continue
            parts = pointer.strip("/").split("/")
            group_id = resolve(record, pointer).get("group")
            module = record["studies"][int(parts[1])][parts[2]]
            link = row[at][1]
            if not link.startswith(f"#'{contract.GROUPS}'!A"):
                problems.append((sheet, pointer, "no link"))
                continue
            target = dict(
                zip(
                    groups_headers,
                    (held[0] for held in groups_rows[int(link.rsplit("A", 1)[1]) - 2]),
                    strict=True,
                )
            )
            group = resolve(record, target[contract.ADDRESS])
            same_module = target[contract.ADDRESS].startswith(f"/studies/{parts[1]}/{parts[2]}/groups/")
            if not same_module or group not in module["groups"] or group.get("id") != group_id:
                problems.append((sheet, pointer, target[contract.ADDRESS]))
            if row[at][0] != group.get("title") or str(group_id) in str(row[at][0]):
                problems.append((sheet, pointer, "title"))
    return problems


def test_a_baseline_or_flow_group_cell_shows_the_title_and_links_to_its_group():
    assert set(contract.GROUP_LINKS) == {contract.POSTED, contract.BASELINE, contract.FLOW}
    assert group_link_problems(RECORD, PLAN) == []


def test_a_link_to_the_wrong_group_is_caught(monkeypatch):
    real = readout.group_target

    def shifted(record, sheet, address):
        target = real(record, sheet, address)
        if sheet == contract.BASELINE and target.endswith("/groups/0"):
            return target.removesuffix("0") + "1"
        return target

    monkeypatch.setattr(readout, "group_target", shifted)
    plan = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(RECORD)}
    assert any(problem[0] == contract.BASELINE for problem in group_link_problems(RECORD, plan))
