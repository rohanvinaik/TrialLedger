"""operate — the decisions of `trialledger landscape` (add-agent-operation 4.2): each RxNav request named
and saved, the release held across the rounds, how a stop ends the run and what it advises, the exit codes,
the record never overwritten, and what the manifest says of the retrieval.

The RxNav answers are RxNav's own (tests/rxnav_request_answers.json, fetched 2026-11-01 through the URLs
request.lookups_needed names); the studies are tests/records.py's.

Positive: every request line of the recorded answers splits into the URL and parameters it names and back; a
saved JSON answer reads as status 200 and its body, exactly as direct mode saves it; one release from the
first round to the last is unchanged; a stop of failed lookups only is asked again; each stop code has its
advice, query_too_long's narrowing the request; a scope stop tells each code's advice in order, failed lookups
alone keeping their "running again asks again"; complete is 0, awaiting_fetch 3; a re-run's identical record
is unchanged; a record written is re-read in the mode it names; the retrieval states the mode, the counts,
whether the classes were looked up (in direct mode, which service was asked about which drugs) and every
number a filter.ids query asked for.
Negative: a recorded failure, an error page, a truncated or non-UTF-8 body reads as status 0 and no body,
never as an answer; direct mode saves a failure as such a note; a changed release is refused, a failed one
asked again, one not stated cannot be compared and refuses nothing; any other stop beside failed lookups
stops the run, and its advice never says running the same command again asks the failed lookup again (the
new run folder does); every failure is 1 and every other status 2; a different record is never overwritten; no
record, or one that is not JSON or names no mode of a run, names none; relay mode says the classes were not
looked up; a query without filter.ids has no requested-ID accounting.
"""

import json
from pathlib import Path

import pytest
from records import ongoing_study, results_study

from TrialLedger import operate
from TrialLedger.classes import rxnav_release
from TrialLedger.operate import (
    CLASSES_LOOKED_UP,
    CLASSES_NOT_LOOKED_UP,
    LOOKUPS_IN_NEW_FOLDER,
    QUERY_ADVICE,
    STOP_ADVICE,
    UNKNOWN_STOP,
    answer_bytes,
    lookup_request,
    record_mode,
    record_state,
    release_check,
    retrieval_coverage,
    run_exit,
    saved_answer,
    scope_advice,
    stop_advice,
    stop_status,
)
from TrialLedger.request import lookup_url

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
VERSION = "https://rxnav.nlm.nih.gov/REST/version.json"
PD1 = (
    "https://rxnav.nlm.nih.gov/REST/rxclass/class/byName.json?className=Programmed+Death+Receptor-1+Blocking"
    "+Antibody&classTypes=EPC"
)


# ── lookup_request ──────────────────────────────────────────────────────────────────────────────────────


def test_every_recorded_request_line_splits_into_its_url_and_parameters_and_back():
    assert len(ANSWERS) == 97
    for line in ANSWERS:
        url, params = lookup_request(line)
        assert "?" not in url and lookup_url(url, params) == line


def test_a_line_names_its_parameters_decoded_in_order():
    assert lookup_request(PD1) == (
        "https://rxnav.nlm.nih.gov/REST/rxclass/class/byName.json",
        {"className": "Programmed Death Receptor-1 Blocking Antibody", "classTypes": "EPC"},
    )
    assert lookup_request(VERSION) == (VERSION, {})
    assert lookup_request("https://x/a.json?name=A%2BB&tty=") == (
        "https://x/a.json",
        {"name": "A+B", "tty": ""},
    )


# ── saved_answer and answer_bytes ───────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("line", [VERSION, PD1])
def test_a_saved_json_answer_is_status_200_and_its_body(line):
    status, body = ANSWERS[line]
    assert status == 200
    assert saved_answer(json.dumps(body).encode()) == (200, body)
    assert saved_answer(answer_bytes(status, body)) == (200, body)


def test_a_saved_answer_keeps_text_beyond_ascii():
    body = {"idGroup": {"name": "ß-lapachone", "rxnormId": ["1"]}}
    assert answer_bytes(200, body) == '{"idGroup": {"name": "ß-lapachone", "rxnormId": ["1"]}}'.encode()
    assert saved_answer(answer_bytes(200, body)) == (200, body)


@pytest.mark.parametrize(
    "raw",
    [
        b"failed: HTTP 503",
        b"failed: http.not_found: GET https://rxnav.nlm.nih.gov/REST/rxcui.json?name=zz",
        b"<html><body>Service Unavailable</body></html>",
        b'{"idGroup": {"rxnormId": ["1"',
        b"\xff\xfe{}",
        b"",
    ],
)
def test_anything_but_a_json_body_is_a_failed_lookup(raw):
    assert saved_answer(raw) == (0, None)


@pytest.mark.parametrize(
    ("status", "body", "note"),
    [
        (503, None, b"failed: HTTP 503\n"),
        (404, {"error": "not found"}, b"failed: HTTP 404\n"),
        (0, None, b"failed: no response\n"),
        (200, None, b"failed: HTTP 200 (not JSON)\n"),
    ],
)
def test_direct_mode_saves_a_failure_as_its_note(status, body, note):
    assert answer_bytes(status, body) == note
    assert saved_answer(note) == (0, None)


def test_an_empty_json_answer_is_an_answer():
    assert answer_bytes(200, {}) == b"{}"
    assert saved_answer(b"{}") == (200, {})


# ── release_check ───────────────────────────────────────────────────────────────────────────────────────


def test_one_release_from_the_first_round_to_the_last_is_unchanged():
    held = rxnav_release(*ANSWERS[VERSION])
    assert held == ("found", "05-Oct-2026")
    assert release_check(held, held) == "unchanged"


def test_a_changed_release_is_refused():
    assert release_check(("found", "05-Oct-2026"), ("found", "02-Nov-2026")) == "release_changed"


@pytest.mark.parametrize(
    ("first", "last"),
    [
        (("found", "05-Oct-2026"), ("lookup_failed", "")),
        (("lookup_failed", ""), ("found", "05-Oct-2026")),
        (("malformed", ""), ("lookup_failed", "")),
        (("lookup_failed", ""), ("malformed", "")),
    ],
)
def test_a_failed_release_is_asked_again(first, last):
    assert release_check(first, last) == "release_lookup_failed"


@pytest.mark.parametrize(
    ("first", "last"),
    [
        (("found", "05-Oct-2026"), ("malformed", "")),
        (("malformed", ""), ("found", "05-Oct-2026")),
        (("malformed", ""), ("malformed", "")),
    ],
)
def test_a_release_not_stated_cannot_be_compared_and_refuses_nothing(first, last):
    assert release_check(first, last) == "release_not_stated"


# ── stop_status and stop_advice ─────────────────────────────────────────────────────────────────────────


def test_failed_lookups_alone_are_asked_again():
    stops = [["drug", "name_lookup_failed", ["Keytruda"]], ["drug_class", "class_lookup_failed", []]]
    stops.append(["drug", "name_lookup_failed", ["osimertinib"]])
    assert stop_status(stops) == ("lookup_failed", ["name_lookup_failed", "class_lookup_failed"])
    assert stop_status([["drug_class", "members_lookup_failed", ["N0000191260"]]]) == (
        "lookup_failed",
        ["members_lookup_failed"],
    )


def test_any_other_stop_stops_the_run():
    stops = [["drug", "name_lookup_failed", ["Keytruda"]], ["drug_class", "class_not_found", []]]
    assert stop_status(stops) == ("scope_stopped", ["name_lookup_failed", "class_not_found"])
    too_long = [["query", "query_too_long", [7210, 7000]]]
    assert stop_status(too_long) == ("scope_stopped", ["query_too_long"])
    assert stop_status([]) == ("scope_stopped", [])


def test_query_too_long_advises_narrowing_the_request():
    assert stop_advice("query_too_long") == STOP_ADVICE["query_too_long"]
    assert "EPC class instead of a MoA class" in stop_advice("query_too_long")


@pytest.mark.parametrize("code", sorted(STOP_ADVICE))
def test_each_named_stop_has_its_own_advice(code):
    assert stop_advice(code) == STOP_ADVICE[code]


def test_a_failed_lookups_advice_says_running_again_asks_again():
    for code in operate.FAILED_LOOKUPS:
        assert "Running the same command again asks it again" in stop_advice(code)


@pytest.mark.parametrize("code", ["query_reserved", "query_empty_value", "query_filters_ignored"])
def test_any_other_query_refusal_advises_changing_the_params(code):
    assert stop_advice(code) == QUERY_ADVICE


def test_an_unknown_stop_is_told_as_such():
    assert stop_advice("galaxy_brain") == UNKNOWN_STOP
    assert stop_advice("") == UNKNOWN_STOP


# ── scope_advice ────────────────────────────────────────────────────────────────────────────────────────


def test_a_scope_stop_tells_each_codes_advice_in_order():
    assert scope_advice(["class_not_found"]) == STOP_ADVICE["class_not_found"]
    assert scope_advice(["no_members", "query_reserved"]) == f"{STOP_ADVICE['no_members']} {QUERY_ADVICE}"


def test_failed_lookups_alone_keep_their_running_again_words():
    codes = ["name_lookup_failed", "class_lookup_failed"]
    assert scope_advice(codes) == f"{STOP_ADVICE['name_lookup_failed']} {STOP_ADVICE['class_lookup_failed']}"
    assert scope_advice([]) == ""


def test_a_failed_lookup_beside_another_stop_is_asked_again_in_the_new_folder():
    # stop_status ends this run scope_stopped and sets nothing aside: the same command would stop alike
    advice = scope_advice(["class_not_found", "name_lookup_failed"])
    assert advice == f"{STOP_ADVICE['class_not_found']} {LOOKUPS_IN_NEW_FOLDER}"
    assert "Running the same command again" not in advice
    mixed = ["members_lookup_failed", "name_not_quotable", "name_lookup_failed", "class_malformed"]
    assert scope_advice(mixed) == " ".join(
        [STOP_ADVICE["name_not_quotable"], STOP_ADVICE["class_malformed"], LOOKUPS_IN_NEW_FOLDER]
    )


# ── run_exit and record_state ───────────────────────────────────────────────────────────────────────────


def test_complete_is_0_and_awaiting_fetch_3():
    assert run_exit("complete") == 0
    assert run_exit("awaiting_fetch") == 3


@pytest.mark.parametrize("status", operate.FAILED)
def test_every_failure_is_1(status):
    assert run_exit(status) == 1


@pytest.mark.parametrize(
    "status",
    [
        "request_refused",
        "request_differs",
        "scope_differs",
        "scope_stopped",
        "not_json",
        "not_a_registry_page",
        "page_out_of_order",
        "schema_problem",
        "record_differs",
        "mode_unavailable",
        "",
    ],
)
def test_every_refusal_or_named_stop_is_2(status):
    assert run_exit(status) == 2


def test_a_record_is_written_once_and_never_overwritten():
    assert record_state(None, b"{}") == "absent"
    assert record_state(b'{"a": 1}\n', b'{"a": 1}\n') == "unchanged"
    assert record_state(b'{"a": 1}\n', b'{"a": 2}\n') == "differs"
    assert record_state(b"", b"{}") == "differs"


def written(retrieval):
    """A landscape.json's bytes as a run writes them, its manifest's retrieval as given."""
    record = {"schema_version": "1", "manifest": {"api_version": "2.0.5", "retrieval": retrieval}}
    return (json.dumps(record, ensure_ascii=False, indent=1) + "\n").encode()


@pytest.mark.parametrize("mode", ["direct", "relay"])
def test_a_record_written_is_reread_in_the_mode_it_names(mode):
    retrieval = retrieval_coverage(mode, 2, {"query.cond": "asthma"}, [results_study(), ongoing_study()])
    assert record_mode(written(retrieval)) == mode


@pytest.mark.parametrize(
    "existing",
    [
        None,
        b"",
        b"<html>Service Unavailable</html>",
        b"[]",
        b'{"manifest": []}',
        b'{"manifest": {"retrieval": "relay"}}',
        written({"matched": 2}),
        written({"mode": "hosted"}),
        written({"mode": None}),
        written({"mode": ["relay"]}),
    ],
)
def test_no_record_or_one_naming_no_mode_names_none(existing):
    assert record_mode(existing) == ""


# ── retrieval_coverage ──────────────────────────────────────────────────────────────────────────────────


def test_the_retrieval_of_a_direct_run_by_numbers():
    studies = [results_study(), ongoing_study()]
    query = {"filter.ids": "NCT01234567,nct7654321,NCT01234567,NCT99999999,NOT-AN-ID"}
    retrieval = retrieval_coverage("direct", 2, query, studies)
    assert retrieval == {
        "mode": "direct",
        "matched": 2,
        "read": 2,
        "drug_classes": CLASSES_LOOKED_UP,
        "requested_ids": [
            {"requested": "NCT01234567", "id": "NCT01234567", "status": "found", "study": "NCT01234567"},
            {"requested": "nct7654321", "id": "NCT07654321", "status": "found", "study": "NCT07654321"},
            {"requested": "NCT01234567", "id": "NCT01234567", "status": "duplicate", "study": ""},
            {"requested": "NCT99999999", "id": "NCT99999999", "status": "missing", "study": ""},
            {"requested": "NOT-AN-ID", "id": "", "status": "malformed", "study": ""},
        ],
    }
    # a copy: the record never shares the module's statement
    assert retrieval["drug_classes"] is not CLASSES_LOOKED_UP
    # what was asked of which drugs: RxClass about every one, RxNav about experimental arms' only
    # (load_or_lookup_at's axes names are reading.axes_aliases)
    assert retrieval["drug_classes"]["source"].startswith(
        "NLM RxClass asked for the EPC and MoA classes of every drug, biological and genetic intervention"
    )
    assert (
        "of each experimental arm's drug, biological or genetic intervention only"
        in (retrieval["drug_classes"]["source"])
    )


def test_a_relay_run_says_the_classes_were_not_looked_up():
    retrieval = retrieval_coverage("relay", 1, {"query.cond": "asthma"}, [ongoing_study()])
    assert retrieval == {
        "mode": "relay",
        "matched": 1,
        "read": 1,
        "drug_classes": CLASSES_NOT_LOOKED_UP,
    }
    assert retrieval["drug_classes"] is not CLASSES_NOT_LOOKED_UP
    assert retrieval["drug_classes"]["state"] == "not_looked_up"
    assert "never no class and never a failed lookup" in retrieval["drug_classes"]["source"]
