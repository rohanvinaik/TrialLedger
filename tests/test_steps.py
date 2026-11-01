"""The run folder's shell — a pull through the folder, fetched directly or relayed by an agent, holds the same
records as a direct pull, or is refused by name.

Positive: a relay round trip on the conftest FakeAPI's registry pages (the agent fetching each URL next.json
names and saving its body) ends complete with the very records a direct-mode run and `query_studies` give; the
URLs relayed are exactly the requests the direct path sends, parameters and order included; a re-run after a
partial fetch resumes, asking only for what is missing; a re-run with nothing new changes nothing; next.json
gives the agent its instructions in plain words; the run folder keeps the request and the scope.
An RxNav answer that fails (a 404 in direct mode, an error page or a recorded failure in relay mode) is a
failed lookup that `rxnav_answers` gives in classes.py's shape, status 0 and no body, and the run completes;
a JSON answer is given as status 200 and its body. A hidden file beside the bodies (.DS_Store) is no body.
Negative: a missing, truncated, HTML, foreign or other-snapshot body is refused by name, and no record (and
no RxNav answer) is read until the decision says complete; a body saved before it was named is refused; pages
whose tokens cannot be followed are refused with the advice to start a new run, never to delete and re-fetch;
every refusal has exactly one piece of advice; a refused query writes nothing; a folder holding another scope
is not reused; an unknown mode is refused; the direct path is unchanged (tests/test_pull.py passes
untouched). Opt-in and live: a run fetched directly from the real registry holds what query_studies returns.
"""

import ast
import inspect
import json

import httpx
import pytest
from conftest import DATA_TIMESTAMP, FakeAPI, json_page, version

from TrialLedger import steps
from TrialLedger.classes import rxnorm_ids
from TrialLedger.ingest import API_BASE, PAGE_SIZE, PullError, query_ids, query_studies
from TrialLedger.steps import (
    ADVICE,
    COMPLETE_INSTRUCTIONS,
    FETCH_INSTRUCTIONS,
    NEXT_NAME,
    Step,
    StepError,
    advance,
    open_run,
    records,
    rxnav_answers,
)

# a query with a space, a comma and an Essie area, so the URLs carry every kind of encoding
QUERY = {"query.cond": "lung cancer, stage IV", "filter.advanced": "AREA[Phase](PHASE2 OR PHASE3)"}
A, B, C = "NCT00000001", "NCT00000002", "NCT00000003"


def registry_pages():
    """What the registry answers, in the order the run asks: two ID pages, then two batches of two and one."""
    return [
        json_page([A, B], total=3, token="t1"),
        json_page([C]),
        json_page([B, A], total=2),  # a batch in another order than the IDs: the records follow the IDs
        json_page([C], total=1),
    ]


@pytest.fixture
def small_batches(monkeypatch):
    monkeypatch.setattr(steps, "PAGE_SIZE", 2)


def started(tmp_path, name="run"):
    folder = tmp_path / name
    assert open_run(folder, {"drug": ["testamab"]}, QUERY) == ("ok", [])
    return folder


def relay_round(folder, client):
    """The agent's part: fetch each URL next.json names and save its body, as fetched, where it says."""
    document = json.loads((folder / NEXT_NAME).read_text(encoding="utf-8"))
    for fetch in document["fetches"]:
        (folder / fetch["save_as"]).write_bytes(client.get(fetch["url"]).content)
    return document


def relay_to_the_end(folder, fake):
    client = fake.client()
    statuses = []
    while True:
        step = advance(folder, "relay")
        statuses.append(step.status)
        if step.status != "awaiting_fetch":
            return statuses
        relay_round(folder, client)


def test_a_relay_round_trip_holds_the_direct_pulls_records(tmp_path, small_batches, no_clock):
    relayed = FakeAPI(json_pages=registry_pages())
    folder = started(tmp_path, "relay")
    statuses = relay_to_the_end(folder, relayed)
    assert statuses == ["awaiting_fetch"] * 5 + ["complete"]
    direct = FakeAPI(json_pages=registry_pages())
    other = started(tmp_path, "direct")
    assert advance(other, "direct", http=direct.client(), sleep=direct.sleep, monotonic=no_clock) == Step(
        "complete", "", []
    )
    whole = FakeAPI(json_pages=[json_page([A, B], total=3, token="t1"), json_page([C])])
    expected = query_studies(QUERY, http=whole.client(), sleep=whole.sleep, monotonic=no_clock)
    assert records(folder) == records(other) == expected
    assert [s["protocolSection"]["identificationModule"]["nctId"] for s in expected[0]] == [A, B, C]
    assert expected[1:] == ("2.0.5", DATA_TIMESTAMP)


def test_the_relayed_urls_are_the_requests_the_direct_path_sends(tmp_path, small_batches, no_clock):
    relayed = FakeAPI(json_pages=registry_pages())
    folder = started(tmp_path, "relay")
    relay_to_the_end(folder, relayed)
    direct = FakeAPI(json_pages=registry_pages())
    advance(
        started(tmp_path, "direct"), "direct", http=direct.client(), sleep=direct.sleep, monotonic=no_clock
    )
    listed = json.loads((folder / "fetches.json").read_text(encoding="utf-8"))
    sent = [str(request.url) for request in direct.requests]
    assert [fetch["url"] for fetch in listed] == sent == [str(request.url) for request in relayed.requests]
    assert [fetch["why"] for fetch in listed] == [
        "version_start",
        "id_page",
        "id_page",
        "studies_batch",
        "studies_batch",
        "version_end",
    ]
    # the ID pages are query_ids' requests, the batches query_studies' for filter.ids
    ids_api = FakeAPI(json_pages=[json_page([A, B], total=3, token="t1"), json_page([C])])
    query_ids(QUERY, http=ids_api.client(), sleep=ids_api.sleep, monotonic=no_clock)
    assert sent[:3] == [str(request.url) for request in ids_api.requests[:3]]
    batch_api = FakeAPI(json_pages=[json_page([B, A], total=2)])
    query_studies(
        {"filter.ids": f"{A},{B}"}, http=batch_api.client(), sleep=batch_api.sleep, monotonic=no_clock
    )
    assert sent[3] == str(batch_api.requests[1].url)


def test_next_json_tells_the_agent_what_to_fetch_and_where(tmp_path):
    folder = started(tmp_path)
    step = advance(folder, "relay")
    document = json.loads((folder / NEXT_NAME).read_text(encoding="utf-8"))
    assert document == {
        "status": "awaiting_fetch",
        "detail": "",
        "run_folder": str(folder.resolve()),
        "instructions": FETCH_INSTRUCTIONS,
        "fetches": [
            {
                "url": "https://clinicaltrials.gov/api/v2/version",
                "save_as": "bodies/version-start.json",
                "why": "version_start",
            }
        ],
    }
    assert step.awaited == document["fetches"]


def test_a_rerun_with_nothing_new_changes_nothing(tmp_path):
    folder = started(tmp_path)
    advance(folder, "relay")
    before = {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}
    assert advance(folder, "relay").status == "awaiting_fetch"
    assert {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()} == before


def test_a_complete_folder_stays_complete_and_fetches_nothing(tmp_path, small_batches, no_clock):
    folder = started(tmp_path)
    relay_to_the_end(folder, FakeAPI(json_pages=registry_pages()))
    idle = FakeAPI(versions=[])
    assert (
        advance(folder, "direct", http=idle.client(), sleep=idle.sleep, monotonic=no_clock).status
        == "complete"
    )
    assert idle.requests == []
    assert not (folder / NEXT_NAME).exists()


def test_a_rerun_after_a_partial_direct_fetch_resumes(tmp_path, small_batches, no_clock):
    folder = started(tmp_path)
    failing = FakeAPI(json_pages=[*registry_pages()[:3], *[httpx.Response(503)] * 4])
    with pytest.raises(PullError) as raised:
        advance(folder, "direct", http=failing.client(), sleep=failing.sleep, monotonic=no_clock)
    assert raised.value.code == "http.server_error"
    saved = sorted(path.name for path in (folder / "bodies").iterdir())
    assert saved == ["ids-001.json", "ids-002.json", "studies-001.json", "version-start.json"]
    with pytest.raises(StepError) as unfinished:
        records(folder)
    assert (unfinished.value.code, unfinished.value.detail) == ("awaiting_fetch", "studies-002.json")
    rest = FakeAPI(versions=[version()], json_pages=registry_pages()[3:])
    assert (
        advance(folder, "direct", http=rest.client(), sleep=rest.sleep, monotonic=no_clock).status
        == "complete"
    )
    assert [request.url.params.get("filter.ids") for request in rest.requests] == [C, None]
    assert [s["protocolSection"]["identificationModule"]["nctId"] for s in records(folder)[0]] == [A, B, C]


def test_a_relay_run_finished_directly_is_the_same_run(tmp_path, small_batches, no_clock):
    folder = started(tmp_path)
    relayed = FakeAPI(json_pages=registry_pages()[:1])
    client = relayed.client()
    for _ in range(2):
        advance(folder, "relay")
        relay_round(folder, client)
    rest = FakeAPI(versions=[version()], json_pages=registry_pages()[1:])
    assert (
        advance(folder, "direct", http=rest.client(), sleep=rest.sleep, monotonic=no_clock).status
        == "complete"
    )
    assert not (folder / NEXT_NAME).exists()
    assert len(records(folder)[0]) == 3


def saved_through_ids(tmp_path):
    """A run whose /version and only ID page are saved, awaiting its one batch."""
    folder = started(tmp_path)
    advance(folder, "relay")
    (folder / "bodies" / "version-start.json").write_bytes(version().content)
    advance(folder, "relay")
    (folder / "bodies" / "ids-001.json").write_bytes(json_page([A], total=1).content)
    assert advance(folder, "relay").awaited[0]["save_as"] == "bodies/studies-001.json"
    return folder


def refused(folder, code):
    step = advance(folder, "relay")
    document = json.loads((folder / NEXT_NAME).read_text(encoding="utf-8"))
    assert (step.status, document["status"], document["instructions"]) == (code, code, ADVICE[code])
    with pytest.raises(StepError) as raised:
        records(folder)
    assert raised.value.code == code
    return step.detail


def test_a_missing_body_is_awaited_and_no_record_is_assembled(tmp_path):
    folder = saved_through_ids(tmp_path)
    with pytest.raises(StepError) as raised:
        records(folder)
    assert (raised.value.code, raised.value.detail) == ("awaiting_fetch", "studies-001.json")


def test_a_truncated_body_is_refused_by_name(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "studies-001.json").write_bytes(json_page([A], total=1).content[:-5])
    assert refused(folder, "not_json") == "studies-001.json"


def test_an_html_error_page_is_refused_by_name(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "studies-001.json").write_bytes(b"<html><body>Service Unavailable</body></html>")
    assert refused(folder, "not_json") == "studies-001.json"


def test_a_foreign_body_is_refused_by_name(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "studies-001.json").write_bytes(version().content)
    assert refused(folder, "not_a_registry_page") == "studies-001.json: no_studies"


def test_another_snapshot_is_refused_by_name(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "studies-001.json").write_bytes(json_page([A], total=1).content)
    assert advance(folder, "relay").awaited[0]["why"] == "version_end"
    (folder / "bodies" / "version-end.json").write_bytes(
        version(data_timestamp="2026-10-31T09:00:02").content
    )
    assert (
        refused(folder, "snapshot_changed")
        == "API 2.0.5, data 2026-10-30T09:00:04 → 2.0.5, 2026-10-31T09:00:02"
    )


def test_a_body_saved_before_it_was_named_is_refused(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "version-end.json").write_bytes(version().content)
    assert refused(folder, "page_out_of_order") == "version-end.json: saved before it was named"


def test_a_batch_missing_a_study_is_refused(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / "studies-001.json").write_bytes(json_page([], total=0).content)
    assert refused(folder, "incomplete_total") == "studies-001.json: 0 studies (complete), 1 asked"


def test_the_rxnav_answers_are_relayed_with_the_first_version(tmp_path):
    folder = tmp_path / "run"
    rxnav = [("https://rxnav.nlm.nih.gov/REST/rxcui.json", {"name": "testamab", "search": "0"})]
    assert open_run(folder, {}, QUERY, rxnav) == ("ok", [])
    step = advance(folder, "relay")
    assert step.awaited[1] == {
        "url": "https://rxnav.nlm.nih.gov/REST/rxcui.json?name=testamab&search=0",
        "save_as": "bodies/rxnav-001.json",
        "why": "rxnav_answer",
    }


RXCUI = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
NAME = {"name": "zz", "search": "0"}


def with_rxnav(fake, answer):
    """A client that answers RxNav with `answer` and the registry as `fake` does, recording every request."""
    asked = []

    def serve(request):
        if request.url.host == "rxnav.nlm.nih.gov":
            asked.append(request)
            return answer
        return fake._serve(request)

    return httpx.Client(
        base_url=API_BASE, transport=httpx.MockTransport(serve), follow_redirects=False
    ), asked


def started_with_rxnav(tmp_path):
    folder = tmp_path / "run"
    assert open_run(folder, {"drug": ["zz"]}, QUERY, [(RXCUI, NAME)]) == ("ok", [])
    return folder


def test_a_failed_rxnav_answer_in_direct_mode_is_a_failed_lookup_and_the_run_completes(tmp_path, no_clock):
    folder = started_with_rxnav(tmp_path)
    fake = FakeAPI(json_pages=[json_page([A], total=1), json_page([A], total=1)])
    client, asked = with_rxnav(fake, httpx.Response(404, text="Not Found"))
    step = advance(folder, "direct", http=client, sleep=fake.sleep, monotonic=no_clock)
    assert step == Step("complete", "", [])
    assert len(asked) == 1
    saved = (folder / "bodies" / "rxnav-001.json").read_bytes()
    assert saved.startswith(b"failed: http.not_found: GET https://rxnav.nlm.nih.gov/REST/rxcui.json?name=zz")
    assert rxnav_answers(folder) == [(RXCUI, NAME, 0, None)]
    assert rxnorm_ids(*rxnav_answers(folder)[0][2:]) == ("lookup_failed", [])
    again, asked_again = with_rxnav(FakeAPI(versions=[]), httpx.Response(404))
    assert advance(folder, "direct", http=again, sleep=fake.sleep, monotonic=no_clock).status == "complete"
    assert asked_again == []


def test_a_registry_failure_in_direct_mode_still_raises(tmp_path, no_clock):
    folder = started(tmp_path)
    fake = FakeAPI(json_pages=[httpx.Response(404, text="no such page")])
    with pytest.raises(PullError) as raised:
        advance(folder, "direct", http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert raised.value.code == "http.not_found"
    assert sorted(path.name for path in (folder / "bodies").iterdir()) == ["version-start.json"]


def test_an_rxnav_json_answer_is_given_with_status_200(tmp_path, no_clock):
    folder = started_with_rxnav(tmp_path)
    fake = FakeAPI(json_pages=[json_page([A], total=1), json_page([A], total=1)])
    answer = {"idGroup": {"name": "zz", "rxnormId": ["123"]}}
    client, _ = with_rxnav(fake, httpx.Response(200, json=answer))
    assert advance(folder, "direct", http=client, sleep=fake.sleep, monotonic=no_clock).status == "complete"
    assert rxnav_answers(folder) == [(RXCUI, NAME, 200, answer)]
    assert rxnorm_ids(*rxnav_answers(folder)[0][2:]) == ("found", ["123"])


@pytest.mark.parametrize("saved", [b"<html><body>404 Not Found</body></html>", b"failed: HTTP 404"])
def test_a_relayed_rxnav_error_page_or_failure_is_a_failed_lookup_not_a_loop(tmp_path, saved):
    folder = started_with_rxnav(tmp_path)
    advance(folder, "relay")
    (folder / "bodies" / "version-start.json").write_bytes(version().content)
    (folder / "bodies" / "rxnav-001.json").write_bytes(saved)
    assert [fetch["why"] for fetch in advance(folder, "relay").awaited] == ["id_page"]
    with pytest.raises(StepError) as unfinished:
        rxnav_answers(folder)
    assert (unfinished.value.code, unfinished.value.detail) == ("awaiting_fetch", "ids-001.json")
    (folder / "bodies" / "ids-001.json").write_bytes(json_page([A], total=1).content)
    advance(folder, "relay")
    (folder / "bodies" / "studies-001.json").write_bytes(json_page([A], total=1).content)
    advance(folder, "relay")
    (folder / "bodies" / "version-end.json").write_bytes(version().content)
    step = advance(folder, "relay")
    document = json.loads((folder / NEXT_NAME).read_text(encoding="utf-8"))
    assert (step.status, document["instructions"]) == ("complete", COMPLETE_INSTRUCTIONS)
    assert rxnav_answers(folder) == [(RXCUI, NAME, 0, None)]


def test_a_hidden_file_beside_the_bodies_is_no_body(tmp_path):
    folder = saved_through_ids(tmp_path)
    (folder / "bodies" / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")
    assert advance(folder, "relay").awaited[0]["save_as"] == "bodies/studies-001.json"


def test_pages_whose_tokens_cannot_be_followed_ask_for_a_new_run(tmp_path):
    folder = started(tmp_path)
    advance(folder, "relay")
    (folder / "bodies" / "version-start.json").write_bytes(version().content)
    advance(folder, "relay")
    (folder / "bodies" / "ids-001.json").write_bytes(json_page([A], total=2, token="t").content)
    advance(folder, "relay")
    (folder / "bodies" / "ids-002.json").write_bytes(json_page([B], token="t").content)
    assert refused(folder, "incomplete_total") == "ids-002.json: repeated_token"
    assert "Start a new run folder" in ADVICE["incomplete_total"]


def returned_codes(function):
    """The string constants a function's return statements can give as their code (the tuple's first item)."""
    tree = ast.parse(inspect.getsource(function))
    return {
        value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple)
        for value in ast.walk(node.value.elts[0])
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }


def test_every_refusal_has_exactly_one_piece_of_advice():
    codes = set().union(
        *(returned_codes(f) for f in (steps.next_step, steps.follow_ids, steps.follow_batches))
    )
    assert set(ADVICE) == codes - {"complete", "awaiting_fetch"}


def test_the_folder_keeps_the_request_and_the_scope(tmp_path):
    folder = started(tmp_path)
    assert json.loads((folder / "request.json").read_text(encoding="utf-8")) == {"drug": ["testamab"]}
    assert json.loads((folder / "scope.json").read_text(encoding="utf-8")) == {"query": QUERY, "rxnav": []}
    assert open_run(folder, {"drug": ["testamab"]}, QUERY) == ("ok", [])


def test_a_folder_holding_another_scope_is_not_reused(tmp_path):
    folder = started(tmp_path)
    assert open_run(folder, {"drug": ["testamab"]}, {"query.cond": "asthma"}) == (
        "scope_differs",
        ["scope.json"],
    )
    assert open_run(folder, {"drug": ["other"]}, QUERY) == ("scope_differs", ["request.json"])
    assert json.loads((folder / "scope.json").read_text(encoding="utf-8"))["query"] == QUERY


def test_a_refused_query_writes_nothing(tmp_path):
    folder = tmp_path / "run"
    assert open_run(folder, {}, {}) == ("query.no_parameters", [])
    assert open_run(folder, {}, {"query.term": A, "filter.overallStatus": "RECRUITING"}) == (
        "query.filters_ignored",
        ["query.term"],
    )
    assert not folder.exists()


def test_an_unknown_mode_is_refused(tmp_path):
    with pytest.raises(ValueError) as raised:
        advance(started(tmp_path), "hosted")
    assert (type(raised.value).__name__, raised.value.args) == (
        "ValueError",
        ("mode must be one of ('direct', 'relay'), not 'hosted'",),
    )


@pytest.mark.live
def test_a_live_run_holds_what_query_studies_returns(tmp_path):
    """Against the real registry (opt-in: `uv run pytest -m live`): a run fetched directly, its IDs listed at
    1,000 a page and its studies fetched in batches of 100, holds exactly the studies `query_studies` returns
    for the same query, in the same order, across more than one batch. Two pulls of one snapshot: run it
    again if the registry publishes between them (the data timestamps then differ). Passed 2026-11-01 (269
    studies, batches of 100, 100 and 69); each full batch of 100 carried a nextPageToken, so a whole batch is
    accepted with one (follow_batches), as query_studies' next page would hold nothing more."""
    query = {"query.cond": "mesothelioma", "filter.overallStatus": "COMPLETED"}
    folder = tmp_path / "live"
    assert open_run(folder, {}, query) == ("ok", [])
    assert advance(folder, "direct").status == "complete"
    held = records(folder)
    expected = query_studies(query)
    assert len(held[0]) > PAGE_SIZE
    assert held == expected
