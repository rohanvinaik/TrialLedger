"""Real acquisition owners: early NIH guards, recorded resume policy and unchanged source checks."""

import json

import httpx
import pytest
from conftest import FakeAPI, csv_page, json_page, version

from TrialLedger import operate, steps
from TrialLedger.acquisition import registry_plan_requests
from TrialLedger.ingest import PullError, pull, query_ids, query_studies
from TrialLedger.request import request_problems, resolve_scope

A = "NCT00000001"
QUERY = {"query.cond": "asthma"}


def test_malformed_explicit_request_budget_is_named_before_resolution_or_network(tmp_path):
    assert request_problems({"condition": "asthma", "acquisition": {"max_studies": True}}) == (
        "acquisition_invalid_max_studies",
        ["acquisition"],
    )
    assert request_problems({"condition": "asthma", "acquisition": None}) == (
        "acquisition_not_an_object",
        ["acquisition"],
    )
    assert request_problems({"acquisition": {"max_studies": 1000}}) == ("empty_request", [])
    fake = FakeAPI()
    result = operate.run(
        tmp_path / "bad", {"condition": "asthma", "acquisition": {"extra": 4}}, "direct", http=fake.client()
    )
    assert result.status == "request_refused"
    assert "acquisition_unknown_field" in result.detail
    assert fake.requests == []


def test_policy_does_not_become_a_registry_filter_or_advanced_clause():
    scope = resolve_scope({"condition": "asthma", "acquisition": {"max_studies": 2000}}, {})
    assert scope["code"] == "resolved"
    assert scope["query"] == QUERY


def test_raw_full_study_query_must_not_fetch_any_full_body_after_broad_id_count(no_clock):
    fake = FakeAPI(json_pages=[json_page([A], total=1001, token="more-ids")])
    with pytest.raises(PullError) as caught:
        query_studies(QUERY, http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert caught.value.code == "acquisition.study_expansion"
    assert "observed studies=1001" in caught.value.detail
    assert len(fake.requests) == 2
    assert fake.requests[-1].url.params["fields"] == "NCTId"


def test_raw_json_csv_pull_must_not_fetch_full_body_or_csv_after_broad_id_count(no_clock):
    fake = FakeAPI(json_pages=[json_page([A], total=1001, token="more-ids")])
    with pytest.raises(PullError) as caught:
        pull(QUERY, http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert caught.value.code == "acquisition.study_expansion"
    assert fake.studies_requests("csv") == []
    assert len(fake.studies_requests("json")) == 1
    assert fake.studies_requests("json")[0].url.params["fields"] == "NCTId"


def test_id_query_must_stop_before_second_identifier_page(no_clock):
    fake = FakeAPI(json_pages=[json_page([A], total=1001, token="next")])
    with pytest.raises(PullError) as caught:
        query_ids(QUERY, http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert caught.value.code == "acquisition.study_expansion"
    assert len(fake.requests) == 2


def test_known_complete_raw_plan_must_fit_before_full_data_acquisition(no_clock):
    fake = FakeAPI(json_pages=[json_page([A], total=1)])
    with pytest.raises(PullError) as caught:
        pull(
            QUERY,
            acquisition={"max_registry_requests": 4},
            http=fake.client(),
            sleep=fake.sleep,
            monotonic=no_clock,
        )
    assert caught.value.code == "acquisition.request_expansion"
    assert fake.requests[-1].url.params["fields"] == "NCTId"
    assert fake.studies_requests("csv") == []


def test_retried_preflight_cost_must_not_be_lost_from_remaining_raw_plan(no_clock):
    fake = FakeAPI(json_pages=[httpx.Response(503), json_page([A], total=1)])
    with pytest.raises(PullError) as caught:
        pull(
            QUERY,
            acquisition={"max_registry_requests": 5},
            http=fake.client(),
            sleep=fake.sleep,
            monotonic=no_clock,
        )
    assert caught.value.code == "acquisition.request_expansion"
    assert len(fake.requests) == 3  # version, failed preflight, successful preflight; no full study
    assert all(r.url.params.get("fields") == "NCTId" for r in fake.studies_requests("json"))


def test_deliberate_large_raw_pull_keeps_json_csv_paging_and_both_snapshots(no_clock):
    ids = [f"NCT{i:08}" for i in range(1, 1101)]
    jsons = [json_page(ids[:1000], total=len(ids), token="metadata-only")]
    csvs = []
    for start in range(0, len(ids), 100):
        token = str(start + 100) if start + 100 < len(ids) else None
        jsons.append(json_page(ids[start : start + 100], total=len(ids) if start == 0 else None, token=token))
        csvs.append(
            csv_page(
                ids[start : start + 100],
                total=len(ids) if start == 0 else None,
                token=token,
                header=start == 0,
            )
        )
    fake = FakeAPI(json_pages=jsons, csv_pages=csvs)
    result = pull(
        QUERY,
        acquisition={"max_studies": 1100, "max_registry_requests": 25},
        http=fake.client(),
        sleep=fake.sleep,
        monotonic=no_clock,
    )
    assert result.total_count == 1100
    assert [s["protocolSection"]["identificationModule"]["nctId"] for s in result.studies] == ids
    assert len(fake.requests) == registry_plan_requests(1100, "json_csv") == 25
    assert fake.requests[0].url.path.endswith("/version")
    assert fake.requests[-1].url.path.endswith("/version")


def test_first_full_count_must_not_silently_disagree_with_id_preflight(no_clock):
    fake = FakeAPI(json_pages=[json_page([A], total=2, token="more"), json_page([A], total=1)])
    with pytest.raises(PullError) as caught:
        query_studies(QUERY, http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert caught.value.code == "json.total_changed"


def test_direct_run_stops_after_first_id_count_and_keeps_complete_response(tmp_path, no_clock):
    folder = tmp_path / "direct"
    assert steps.open_run(folder, {"condition": "asthma"}, QUERY) == ("ok", [])
    page = json_page([A], total=1001, token="next")
    fake = FakeAPI(json_pages=[page])
    result = steps.advance(folder, "direct", http=fake.client(), sleep=fake.sleep, monotonic=no_clock)
    assert result.status == "acquisition_study_expansion"
    assert len(fake.requests) == 2
    assert (folder / "bodies/ids-001.json").read_bytes() == page.content
    assert not (folder / "bodies/ids-002.json").exists()
    assert not (folder / "bodies/studies-001.json").exists()
    receipt = json.loads((folder / "acquisition.json").read_text())
    assert receipt["observed_total"] == 1001
    assert receipt["registry_requests"] == 2
    assert receipt["policy"] == {"max_studies": 1000, "max_registry_requests": 100}
    idle = FakeAPI(versions=[])
    assert steps.advance(folder, "direct", http=idle.client()).status == "acquisition_study_expansion"
    assert idle.requests == []


def test_relay_names_no_second_id_page_or_batches_after_broad_first_count(tmp_path):
    folder = tmp_path / "relay"
    assert steps.open_run(folder, {"condition": "asthma"}, QUERY) == ("ok", [])
    steps.advance(folder, "relay")
    (folder / "bodies/version-start.json").write_bytes(version().content)
    steps.advance(folder, "relay")
    page = json_page([A], total=1001, token="next")
    (folder / "bodies/ids-001.json").write_bytes(page.content)
    result = steps.advance(folder, "relay")
    assert result.status == "acquisition_study_expansion"
    assert result.awaited == []
    document = json.loads((folder / "next.json").read_text())
    assert document["fetches"] == []
    assert "1001" in document["detail"]
    assert [f["file"] for f in json.loads((folder / "fetches.json").read_text())] == [
        "version-start.json",
        "ids-001.json",
    ]


def test_explicit_id_scope_records_expectation_instead_of_search_default(tmp_path):
    ids = [f"NCT{i:08}" for i in range(1, 10001)]
    folder = tmp_path / "ids"
    query = {"filter.ids": ",".join(ids)}
    assert steps.open_run(folder, {"params": query}, query) == ("ok", [])
    policy = json.loads((folder / "scope.json").read_text())["acquisition"]
    assert policy == {"max_studies": 10000, "max_registry_requests": 112}
    assert steps.open_run(folder, {"params": query}, query) == ("ok", [])


def test_legacy_fully_retained_large_report_is_local_validation_not_new_acquisition(tmp_path):
    ids = [f"NCT{i:08}" for i in range(1, 1002)]
    folder = tmp_path / "old"
    (folder / "bodies").mkdir(parents=True)
    scope = {"query": QUERY, "rxnav": []}
    (folder / "scope.json").write_text(json.dumps(scope))
    bodies = {
        "version-start.json": version().json(),
        "ids-001.json": json_page(ids, total=len(ids)).json(),
        "version-end.json": version().json(),
    }
    for start in range(0, len(ids), 100):
        bodies[f"studies-{start // 100 + 1:03}.json"] = json_page(
            ids[start : start + 100], total=len(ids[start : start + 100])
        ).json()
    for name, body in bodies.items():
        (folder / "bodies" / name).write_text(json.dumps(body))
    (folder / "fetches.json").write_text(json.dumps([{"file": name} for name in bodies]))
    before = (folder / "scope.json").read_bytes()
    assert len(steps.records(folder)[0]) == 1001
    idle = FakeAPI(versions=[])
    assert steps.advance(folder, "direct", http=idle.client()).status == "complete"
    assert idle.requests == []
    assert (folder / "scope.json").read_bytes() == before
    assert not (folder / "acquisition.json").exists()


def test_legacy_incomplete_run_must_apply_guard_before_new_network_requests(tmp_path):
    folder = tmp_path / "old"
    (folder / "bodies").mkdir(parents=True)
    (folder / "scope.json").write_text(json.dumps({"query": QUERY, "rxnav": []}))
    (folder / "bodies/version-start.json").write_bytes(version().content)
    (folder / "bodies/ids-001.json").write_bytes(json_page([A], total=1001, token="next").content)
    (folder / "fetches.json").write_text(
        json.dumps([{"file": "version-start.json"}, {"file": "ids-001.json"}])
    )
    idle = FakeAPI(versions=[])
    assert steps.advance(folder, "direct", http=idle.client()).status == "acquisition_study_expansion"
    assert idle.requests == []
    assert "acquisition" not in json.loads((folder / "scope.json").read_text())


@pytest.mark.parametrize("budget,expected", [(7, "acquisition_request_expansion"), (8, "complete")])
def test_retry_cost_survives_interrupted_direct_run_and_resume(tmp_path, no_clock, budget, expected):
    folder = tmp_path / str(budget)
    request = {"condition": "asthma", "acquisition": {"max_registry_requests": budget}}
    assert steps.open_run(folder, request, QUERY) == ("ok", [])
    failing = FakeAPI(json_pages=[json_page([A], total=1), *[httpx.Response(503)] * 4])
    with pytest.raises(PullError) as caught:
        steps.advance(folder, "direct", http=failing.client(), sleep=failing.sleep, monotonic=no_clock)
    assert caught.value.code == "http.server_error"
    assert json.loads((folder / "acquisition.json").read_text())["registry_requests"] == 6
    rest = FakeAPI(versions=[version()], json_pages=[json_page([A], total=1)])
    assert (
        steps.advance(folder, "direct", http=rest.client(), sleep=rest.sleep, monotonic=no_clock).status
        == expected
    )
    if budget == 7:
        assert rest.requests == []
        assert json.loads((folder / "acquisition.json").read_text())["registry_requests"] == 6
    else:
        assert len(steps.records(folder)[0]) == 1
        assert json.loads((folder / "acquisition.json").read_text())["registry_requests"] == 8
