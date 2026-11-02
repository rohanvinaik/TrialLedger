"""`trialledger profile` and `trialledger resolve` end to end, through the CLI.

Positive: a written folder gets design.xlsx and classes.json, with every sheet the About sheet describes; the
pull's own four files are byte for byte unchanged and the folder still verifies; a profile asks EPC and MoA
and marks the axes it has not cached not_looked_up; `--fill-axes` asks them once, then they are read from the
cache; resolve asks the axes its outputs read; resolve's JSON and design.xlsx give each coordinate its known,
interpolated and proposed levels with their statuses, each relation its kind, and each RxClass answer its
requests and release (add-scoped-reasoning 1.1 and 1.2).
Negative: a record that no longer matches its digests gets no design.xlsx (exit 1); a folder with no record
gets nothing (exit 2); a profile without `--fill-axes` asks RxNav nothing about the axes, and with it, a
record that does not verify is asked nothing; a default's narrowing is never known and a proposal's never
interpolated; an answer cached before answers carried a warrant is never asked again and its release is never
invented.
"""

import json

import httpx
import openpyxl
import pytest
from conftest import FakeAPI, csv_page
from records import ongoing_study, results_study

from TrialLedger import classes as rx
from TrialLedger import cli, warrants
from TrialLedger.coherence import RELATIONS, SETTINGS, Relation, resolve
from TrialLedger.symbolic import _coordinate

PULL_FILES = ("studies.json", "studies.csv", "review.xlsx", "record.xlsx")


def rxclass(url, params):
    # RxNorm holds every name as its own ingredient ("rx-<name>"), the RxNav release is not stated, and
    # RxClass, asked by concept, answers only DailyMed's EPC.
    if url.endswith("/rxcui.json"):
        return 200, {"idGroup": {"rxnormId": [f"rx-{params['name']}"]}}
    if url.endswith("/properties.json"):
        rxcui = url.rsplit("/", 2)[-2]
        return 200, {"properties": {"rxcui": rxcui, "name": rxcui.removeprefix("rx-"), "tty": "IN"}}
    if not url.endswith("/byRxcui.json"):
        return 200, {}
    concept = {"rxcui": params["rxcui"], "name": params["rxcui"].removeprefix("rx-"), "tty": "IN"}
    item = {"classId": "N0000191260", "className": "Programmed Death Receptor-1 Blocking Antibody"}
    entry = {
        "minConcept": concept,
        "rxclassMinConceptItem": item,
        "rela": "has_epc",
        "relaSource": "DAILYMED",
    }
    return 200, {"rxclassDrugInfoList": {"rxclassDrugInfo": [entry]}}


@pytest.fixture
def folder(tmp_path):
    first, second = results_study(), ongoing_study()
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in (first, second)]
    api = FakeAPI(
        json_pages=[httpx.Response(200, json={"studies": [first, second], "totalCount": 2})],
        csv_pages=[csv_page(ids, total=2, header=True)],
    )
    out = tmp_path / "run"
    assert (
        cli.main(
            ["pull", f"filter.ids={','.join(ids)}", "--out", str(out)], http=api.client(), sleep=api.sleep
        )
        == 0
    )
    return out


def test_profile_writes_beside_the_pull_and_changes_none_of_it(folder):
    before = {name: (folder / name).read_bytes() for name in PULL_FILES}
    assert cli.main(["profile", str(folder)], rxclass_get=rxclass) == 0
    assert {name: (folder / name).read_bytes() for name in PULL_FILES} == before
    assert cli.main(["verify", str(folder)]) == 0
    book = openpyxl.load_workbook(folder / "design.xlsx", read_only=True)
    assert book.sheetnames == [
        "About",
        "Trials",
        "Criteria",
        "Residual",
        "Audit",
        "Coordinates",
        "Outcomes",
        "Results",
        "Expectations",
        "Review Queue",
        "Near Misses",
        "Drug Axes",
        "Rules",
        "Relations",
        "Classes",
        "Profile",
        "Mechanism Signals",
        "Occupancy",
    ]
    cache = json.loads((folder / "classes.json").read_text())
    assert cache["endpoint"].startswith("https://rxnav.nlm.nih.gov/")


def test_a_tampered_record_gets_no_design(folder):
    record = json.loads((folder / "studies.json").read_text())
    record["studies"][0]["protocolSection"]["identificationModule"]["briefTitle"] = "changed"
    (folder / "studies.json").write_text(json.dumps(record))
    assert cli.main(["profile", str(folder)], rxclass_get=rxclass) == 1
    assert not (folder / "design.xlsx").exists()


def test_a_folder_without_a_record_gets_nothing(tmp_path):
    assert cli.main(["profile", str(tmp_path)], rxclass_get=rxclass) == 2
    assert list(tmp_path.iterdir()) == []


def test_resolve_reads_live_and_saves_no_record(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    first, second = results_study(), ongoing_study()
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in (first, second)]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": [first, second], "totalCount": 2})])
    out = tmp_path / "reading.json"
    book = tmp_path / "design.xlsx"
    kept = tmp_path / "snapshot.json"
    code = cli.main(
        [
            "resolve",
            f"filter.ids={','.join(ids)}",
            "--json",
            str(out),
            "--out",
            str(book),
            "--keep",
            str(kept),
        ],
        http=api.client(),
        sleep=api.sleep,
        rxclass_get=rxclass,
    )
    assert code == 0
    reading = json.loads(out.read_text())
    assert [s["nct"] for s in reading["studies"]] == ids
    assert {
        "eligibility_coverage",
        "criteria",
        "coordinates",
        "experimental_drugs",
        "outcomes",
        "expectations",
    } <= set(reading["studies"][0])
    coverage = reading["studies"][0]["eligibility_coverage"]
    assert set(coverage) == {"content", "sectioning", "evidence", "markers"}
    assert set(coverage["evidence"]) == {"inclusion", "exclusion"}
    assert book.is_file() and (tmp_path / "cache" / "classes.json").is_file()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["cache", "design.xlsx", "reading.json", "snapshot.json"]
    snapshot = json.loads(kept.read_text())
    assert snapshot["study_digests"] == reading["study_digests"] and len(snapshot["studies"]) == 2
    assert reading["merkle_root"] == warrants.merkle_root(reading["study_digests"])
    assert reading["data_timestamp"] and "code_commit" in reading


def test_resolve_refuses_an_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "classes.json"))
    assert cli.main(["resolve"], rxclass_get=rxclass) == 2


def near_miss_study(nct, ecog):
    study = ongoing_study()
    protocol = study["protocolSection"]
    protocol["identificationModule"]["nctId"] = nct
    protocol["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n"
        "* No prior systemic therapy for advanced or metastatic disease\n"
        f"* ECOG performance status {ecog}\n\nExclusion Criteria:\n\n* Active autoimmune disease\n"
    )
    protocol["armsInterventionsModule"] = {
        "armGroups": [{"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: Pembrolizumab"]}],
        "interventions": [{"type": "DRUG", "name": "Pembrolizumab"}],
    }
    return study


def test_resolve_reports_a_near_miss_in_the_sheet_and_the_json(tmp_path, monkeypatch):
    """Positive: two first-line PD-1 trials differing only in the ECOG they admit are one near-miss row, and
    each study's JSON names the other. Negative: the studies of the other tests, with nothing comparable,
    carry no near miss."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    studies = [near_miss_study("NCT09000001", "0-1"), near_miss_study("NCT09000002", "0-2"), results_study()]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": studies, "totalCount": 3})])
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    query = "filter.ids=NCT09000001,NCT09000002"
    argv = ["resolve", query, "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=rxclass) == 0
    header, *rows = openpyxl.load_workbook(book, read_only=True)["Near Misses"].iter_rows(values_only=True)
    # the first-line setting is a default's conclusion: interpolated, never known (add-scoped-reasoning 1.1)
    assert header[10].startswith("Representation (known for 0 and interpolated for 2 of 3 trials")
    assert [row[:5] for row in rows] == [("NCT09000001", "NCT09000002", "ecog_ps", "0|1", "0|1|2")]
    assert header[11].startswith("Rests On") and [row[11] for row in rows] == ["interpolated"]
    header, *trials = openpyxl.load_workbook(book, read_only=True)["Trials"].iter_rows(values_only=True)
    columns = [
        header.index(name) for name in ("Eligibility Content", "Inclusion Coverage", "Exclusion Coverage")
    ]
    assert {tuple(row[i] for i in columns) for row in trials[:2]} == {
        ("present", "unspecified", "unspecified")
    }
    reading = {s["nct"]: s["near_misses"] for s in json.loads(out.read_text())["studies"]}
    assert [(m["other"], m["value"], m["other_value"], m["rests_on"]) for m in reading["NCT09000002"]] == [
        ("NCT09000001", "0|1|2", "0|1", "interpolated")
    ]
    assert reading[results_study()["protocolSection"]["identificationModule"]["nctId"]] == []


ABBREVIATED = (
    "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n* ECOG performance status 0-1\n\n"
    "Key Exclusion Criteria:\n\n* Active autoimmune disease\n"
)


def test_resolve_carries_an_abbreviated_record_to_the_sheets_and_the_json(tmp_path, monkeypatch):
    """Positive: a record whose exclusions are "Key Exclusion Criteria" shows its sectioning, its coverage per
    section and its marker with the marker's exact offsets on the Trials sheet and in the JSON, and its
    eligibility_abbreviated question on the Review Queue sheet and in the JSON. Negative: a record with no
    marker has no marker, reads unspecified in both sections (never complete) and gets no such question."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    abbreviated = near_miss_study("NCT09000003", "0-1")
    abbreviated["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = ABBREVIATED
    plain = near_miss_study("NCT09000004", "0-1")
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": [abbreviated, plain], "totalCount": 2})])
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    argv = ["resolve", "filter.ids=NCT09000003,NCT09000004", "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=rxclass) == 0
    start = ABBREVIATED.index("Key Exclusion")
    end = start + len("Key Exclusion")

    studies = {s["nct"]: s for s in json.loads(out.read_text())["studies"]}
    coverage = studies["NCT09000003"]["eligibility_coverage"]
    assert (coverage["content"], coverage["sectioning"]) == ("present", "sectioned")
    assert coverage["evidence"] == {"inclusion": "unspecified", "exclusion": "abbreviation_stated"}
    ((marker,),) = [coverage["markers"]]
    assert (marker["kind"], marker["scope"], marker["start"], marker["end"]) == (
        "abbreviation_stated",
        "exclusion",
        start,
        end,
    )
    assert ABBREVIATED[marker["start"] : marker["end"]] == marker["text"] == "Key Exclusion"
    (flag,) = [f for f in studies["NCT09000003"]["review"] if f["kind"] == "eligibility_abbreviated"]
    assert flag["evidence"] == [
        f"[exclusion] piece {marker['piece']}, characters {start}-{end}: Key Exclusion"
    ]
    assert flag["answer"] is None
    assert studies["NCT09000004"]["eligibility_coverage"]["markers"] == []
    assert studies["NCT09000004"]["eligibility_coverage"]["evidence"] == {
        "inclusion": "unspecified",
        "exclusion": "unspecified",
    }
    assert not [f for f in studies["NCT09000004"]["review"] if f["kind"] == "eligibility_abbreviated"]

    workbook = openpyxl.load_workbook(book, read_only=True)
    header, *rows = workbook["Trials"].iter_rows(values_only=True)
    trials = {row[0]: dict(zip(header, row, strict=True)) for row in rows}
    row = trials["NCT09000003"]
    assert (row["Eligibility Content"], row["Sectioning"]) == ("present", "sectioned")
    assert (row["Inclusion Coverage"], row["Exclusion Coverage"]) == ("unspecified", "abbreviation_stated")
    assert row["Coverage Markers"] == (
        f"abbreviation_stated [exclusion] piece {marker['piece']}, characters {start}-{end}: Key Exclusion"
    )
    assert (trials["NCT09000004"]["Exclusion Coverage"], trials["NCT09000004"]["Coverage Markers"]) in {
        ("unspecified", None),
        ("unspecified", ""),
    }
    header, *rows = workbook["Review Queue"].iter_rows(values_only=True)
    queue = [dict(zip(header, row, strict=True)) for row in rows]
    flagged = [(q["NCT Number"], q["Evidence"]) for q in queue if q["Kind"] == "eligibility_abbreviated"]
    assert flagged == [("NCT09000003", flag["evidence"][0])]


def recording(asked):
    """The `rxclass` fake, recording each request as a name's RxNorm identity ("identity"), a concept's
    classes ("classes"), the RxNav release ("release", asked before and after each lookup batch) or a request
    the axes alone need ("axes": a concept's properties or ingredients), each with the name it is about."""

    def get(url, params):
        page = url.rsplit("/", 1)[-1]
        kinds = {"rxcui.json": "identity", "byRxcui.json": "classes", "version.json": "release"}
        name = params.get("name") or params.get("rxcui") or url.rsplit("/", 2)[-2]
        about = "" if page == "version.json" else name.removeprefix("rx-")
        asked.append((kinds.get(page, "axes"), page, about))
        return rxclass(url, params)

    return get


def axes_identities(folder):
    sheet = openpyxl.load_workbook(folder / "design.xlsx", read_only=True)["Drug Axes"]
    _header, *rows = sheet.iter_rows(values_only=True)
    return {(row[1], row[2], row[3]) for row in rows}


def test_a_profile_asks_no_axes_and_marks_them_not_looked_up(folder, capsys):
    """Positive: a profile asks RxClass for EPC and MoA as before and renders every experimental drug whose
    axes were never asked as not_looked_up. Negative: it asks RxNav nothing about the axes."""
    asked = []
    assert cli.main(["profile", str(folder)], rxclass_get=recording(asked)) == 0
    # each name's identity and its concept's classes, with the release their batch was read under asked
    # before and after it (its warrant), and nothing the axes alone need
    assert asked and {kind for kind, *_ in asked} == {"identity", "classes", "release"}
    assert [kind for kind, *_ in asked].count("release") == 2
    assert asked[0][0] == "release" and asked[-1][0] == "release"
    assert sorted({name for kind, _, name in asked if kind == "classes"}) == ["Placebo", "TM-1", "Testamab"]
    assert axes_identities(folder) == {("Testamab", "not_looked_up", "own_name_not_looked_up")}
    assert "--fill-axes" in capsys.readouterr().err
    cache = json.loads((folder / "classes.json").read_text())["answers"]
    assert not any("axes" in answer for answer in cache.values())


def test_fill_axes_asks_once_then_a_profile_reads_the_cache(folder):
    """Positive: --fill-axes asks RxNav for the experimental drugs' names, after which the sheet shows their
    identity; a later profile reads them from the cache. Negative: the placebo outside the experimental arm is
    never asked for axes, and the later profile asks nothing at all."""
    asked = []
    assert cli.main(["profile", str(folder), "--fill-axes"], rxclass_get=recording(asked)) == 0
    axes = [name for kind, _, name in asked if kind == "axes" and name]
    assert set(axes) == {"Testamab", "TM-1"}
    filled = axes_identities(folder)
    assert filled and not any(code == "not_looked_up" for _, code, _ in filled)
    asked.clear()
    assert cli.main(["profile", str(folder)], rxclass_get=recording(asked)) == 0
    assert asked == [] and axes_identities(folder) == filled


def test_fill_axes_asks_nothing_for_a_record_that_does_not_verify(folder, tmp_path):
    """Positive: a tampered record with --fill-axes ends 1 and a missing one 2, as without it. Negative:
    neither asks RxNav anything, and the folder's classes.json is not written."""
    record = json.loads((folder / "studies.json").read_text())
    record["studies"][0]["protocolSection"]["identificationModule"]["briefTitle"] = "changed"
    (folder / "studies.json").write_text(json.dumps(record))
    asked = []
    assert cli.main(["profile", str(folder), "--fill-axes"], rxclass_get=recording(asked)) == 1
    assert asked == [] and not (folder / "classes.json").exists()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli.main(["profile", str(empty), "--fill-axes"], rxclass_get=recording(asked)) == 2
    assert asked == [] and list(empty.iterdir()) == []


def test_resolve_asks_the_axes_its_outputs_read(tmp_path, monkeypatch):
    """Positive: resolve, whose JSON reads the axes, asks RxNav for them. Negative: its drug is never left
    not_looked_up."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    study = results_study()
    nct = study["protocolSection"]["identificationModule"]["nctId"]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": [study], "totalCount": 1})])
    out = tmp_path / "reading.json"
    asked = []
    argv = ["resolve", f"filter.ids={nct}", "--json", str(out)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=recording(asked)) == 0
    assert {name for kind, _, name in asked if kind == "axes" and name} == {"Testamab", "TM-1"}
    [axes] = json.loads(out.read_text())["studies"][0]["drug_axes"]
    assert axes["drug"] == "Testamab" and axes["identity"] != "not_looked_up"


# RxNav's own answer to version.json (read live 2026-11-01; tests/test_classes.py)
RXNAV_VERSION = {"version": "05-Oct-2026", "apiVersion": "3.1.356"}
IDENTITY_REQUEST = f"{rx.RXNORM_IDS}?name=Pembrolizumab&search=0"
CLASS_REQUEST = f"{rx.RXCLASS_BY_RXCUI}?rxcui=rx-Pembrolizumab"
PD1 = "Programmed Death Receptor-1 Blocking Antibody"
ALL_SETTINGS = list(SETTINGS)


def released(asked):
    """The `rxclass` fake with RxNav's release answered, recording every request."""

    def get(url, params):
        asked.append((url, dict(params)))
        return (200, RXNAV_VERSION) if url.endswith("/version.json") else rxclass(url, params)

    return get


def resected_study(nct):
    """A trial requiring a completed resection: only a proposal narrows its setting."""
    study = near_miss_study(nct, "0-1")
    study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Completely resected stage IB-IIIA non-small cell lung cancer\n"
        "* ECOG performance status 0-1\n"
    )
    return study


def sheet_rows(book, name):
    header, *rows = openpyxl.load_workbook(book, read_only=True)[name].iter_rows(values_only=True)
    return [dict(zip(header, row, strict=True)) for row in rows]


def test_resolve_shows_each_status_each_kind_and_each_warrant(tmp_path, monkeypatch):
    """Positive (add-scoped-reasoning 1.1 and 1.2, end to end): a first-line trial's setting is interpolated
    by the default, with the default named, its prior lines known by its criterion; a resected trial's setting
    is narrowed by the resection proposal alone, proposed; the Trials and Coordinates sheets show each level,
    the Relations sheet each relation's kind beside its approval, and each RxClass answer its two requests and
    the RxNav release, in the JSON and on the Classes sheet. Negative: the known setting never holds the
    default's narrowing (all nine values, unresolved), a proposal never enters the interpolated level, and no
    relation is strict."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    studies = [near_miss_study("NCT09000001", "0-1"), resected_study("NCT09000005")]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": studies, "totalCount": 2})])
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    argv = ["resolve", "filter.ids=NCT09000001,NCT09000005", "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=released([])) == 0
    reading = {s["nct"]: s for s in json.loads(out.read_text())["studies"]}
    wide = {"domain": ALL_SETTINGS, "state": "unnarrowed", "status": "unresolved", "removed_by": []}
    first_line = [s for s in ALL_SETTINGS if s != "advanced_first_line"]
    default = "first_line_when_no_prior_advanced_therapy"
    assert reading["NCT09000001"]["coordinates"]["setting"] == {
        "known": wide,
        "interpolated": {
            "domain": ["advanced_first_line"],
            "state": "resolved",
            "status": "interpolated",
            "removed_by": [["setting", first_line, default]],
        },
        "proposed": [],
    }
    lines = {"domain": ["0"], "state": "resolved"}
    assert reading["NCT09000001"]["coordinates"]["prior_advanced_lines"] == {
        "known": {
            **lines,
            "status": "known",
            "removed_by": [["prior_advanced_lines", ["1", "2", "3+"], "criterion 2"]],
        },
        "interpolated": {**lines, "status": "known", "removed_by": []},
        "proposed": [],
    }
    proposal = "adjuvant_or_perioperative_when_resection_required"
    kept = ["adjuvant", "perioperative"]
    assert reading["NCT09000005"]["coordinates"]["setting"] == {
        "known": wide,
        "interpolated": wide,
        "proposed": [
            {
                "relation": proposal,
                "domain": kept,
                "state": "unresolved",
                "status": "proposed",
                "removed_by": [["setting", [s for s in ALL_SETTINGS if s not in kept], proposal]],
            }
        ],
    }
    cache = json.loads((tmp_path / "cache" / "classes.json").read_text())["answers"]["Pembrolizumab"]
    asked = [{"request": rx.request_text(w), "retrieved": w["retrieved"]} for w in cache["requests"]]
    assert [a["request"] for a in asked] == [IDENTITY_REQUEST, CLASS_REQUEST]
    for nct in ("NCT09000001", "NCT09000005"):
        assert reading[nct]["experimental_drugs"] == [
            {
                "name": "Pembrolizumab",
                "state": "classified",
                "classes": [PD1],
                "resolved_by": "Pembrolizumab",
                "rxclass": [
                    {
                        "name": "Pembrolizumab",
                        "release_state": "found",
                        "release": "05-Oct-2026",
                        "requests": asked,
                    }
                ],
            }
        ]

    joined = " | ".join(ALL_SETTINGS)
    trials = {row["NCT Number"]: row for row in sheet_rows(book, "Trials")}
    levels = (
        "Setting (known)",
        "Setting (interpolated: default relations added)",
        "Setting (each proposal alone)",
    )
    assert [trials["NCT09000001"][c] for c in (*levels, "Prior Advanced Lines (known)")] == [
        joined,
        "advanced_first_line",
        None,
        "0",
    ]
    assert [trials["NCT09000005"][c] for c in levels] == [
        joined,
        joined,
        f"{proposal}: adjuvant | perioperative",
    ]
    coordinates = {(row["NCT Number"], row["Coordinate"]): row for row in sheet_rows(book, "Coordinates")}
    columns = (
        "Known Domain",
        "Known State",
        "Interpolated Domain (default relations added)",
        "Interpolated State",
        "Each Proposal Alone (never built on)",
        "Removed By (status: values by criterion or relation)",
    )
    assert [coordinates["NCT09000001", "setting"][c] for c in columns] == [
        joined,
        "unnarrowed",
        "advanced_first_line",
        "resolved",
        None,
        f"interpolated: {'|'.join(first_line)} by {default}",
    ]
    assert [coordinates["NCT09000001", "prior_advanced_lines"][c] for c in columns] == [
        "0",
        "resolved",
        "0",
        "resolved",
        None,
        "known: 1|2|3+ by criterion 2",
    ]
    assert [coordinates["NCT09000005", "setting"][c] for c in columns] == [
        joined,
        "unnarrowed",
        joined,
        "unnarrowed",
        f"{proposal}: adjuvant | perioperative",
        f"proposed: {'|'.join(s for s in ALL_SETTINGS if s not in kept)} by {proposal}",
    ]
    kind = "Kind (strict: known; default: interpolated; proposal: shown alone, never built on)"
    assert {row["Relation"]: (row[kind], row["Approval"]) for row in sheet_rows(book, "Relations")} == {
        relation.id: (relation.kind, relation.approval) for relation in RELATIONS
    }
    assert {(relation.kind, relation.approval) for relation in RELATIONS} == {
        ("default", "approved"),
        ("proposal", "proposed"),
    }
    [classes] = sheet_rows(book, "Classes")
    assert [classes[c] for c in ("Name Asked", "Class", CLASSES_REQUESTS, CLASSES_RELEASE)] == [
        "Pembrolizumab",
        PD1,
        " | ".join(f"{a['request']} at {a['retrieved']}" for a in asked),
        "05-Oct-2026",
    ]


CLASSES_REQUESTS = "Requests (each with its retrieval time)"
CLASSES_RELEASE = "RxNav Release (not_recorded: cached before answers carried it)"


def test_an_answer_cached_before_warrants_keeps_its_classes_and_records_no_release(tmp_path, monkeypatch):
    """Positive: an EPC answer cached before answers carried their warrant still classes its drug, and says
    its release was not recorded, in the JSON and on the Classes sheet. Negative: its EPC and MoA are never
    asked again, no request is listed for it and no release is invented."""
    cache = tmp_path / "cache" / "classes.json"
    cache.parent.mkdir()
    old = {
        "codes": {"DAILYMED:has_epc": "found", "MEDRT:has_moa": "not_found"},
        "classes": [["N0000191260", PD1, "has_epc", "DAILYMED"]],
        "retrieved": "2026-10-31T00:00:00+00:00",
    }
    cache.write_text(json.dumps({"answers": {"Pembrolizumab": old}}))
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(cache))
    api = FakeAPI(
        json_pages=[
            httpx.Response(200, json={"studies": [near_miss_study("NCT09000001", "0-1")], "totalCount": 1})
        ]
    )
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    asked = []
    argv = ["resolve", "filter.ids=NCT09000001", "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=released(asked)) == 0
    # the axes are asked (resolve reads them): the name's identity and its concept's classes, read for the
    # axes alone; its EPC and MoA are kept as they were answered
    assert [url.rsplit("/", 1)[-1] for url, _ in asked] == [
        "version.json",
        "rxcui.json",
        "properties.json",
        "byRxcui.json",
        "version.json",
    ]
    [drug] = json.loads(out.read_text())["studies"][0]["experimental_drugs"]
    assert (drug["state"], drug["classes"]) == ("classified", [PD1])
    assert drug["rxclass"] == [
        {"name": "Pembrolizumab", "release_state": "not_recorded", "release": "", "requests": []}
    ]
    [classes] = sheet_rows(book, "Classes")
    assert [classes[c] for c in ("Name Asked", "Class", CLASSES_REQUESTS, CLASSES_RELEASE)] == [
        "Pembrolizumab",
        PD1,
        None,
        "(not_recorded)",
    ]


def test_a_level_the_defaults_empty_is_unresolved_in_the_json():
    """Positive: a declared default contradicting a stated prior line leaves the known level known (one value)
    and empties the interpolated one, which the JSON calls unresolved with the default named. Negative: an
    emptied interpolated level is never called interpolated, and the known value is never changed by it."""
    default = Relation(
        "no_prior_lines_when_named", "a test default", "a test basis", "proposed", "default",
        ("inclusion:setting_word:x",), (), "prior_advanced_lines", ("0",),
    )  # fmt: skip
    evidence = [
        ("inclusion", "prior_lines", ("1",), "advanced", "criterion 1"),
        ("inclusion", "setting_word", ("x",), "", "criterion 2"),
    ]
    assert _coordinate(resolve(evidence, relations=(default,))["prior_advanced_lines"]) == {
        "known": {
            "domain": ["1"],
            "state": "resolved",
            "status": "known",
            "removed_by": [["prior_advanced_lines", ["0", "2", "3+"], "criterion 1"]],
        },
        "interpolated": {
            "domain": [],
            "state": "conflict",
            "status": "unresolved",
            "removed_by": [["prior_advanced_lines", ["1"], "no_prior_lines_when_named"]],
        },
        "proposed": [],
    }
