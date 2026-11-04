"""pull — the network shell returns every study a query matched, from one snapshot, or raises.

Positive: pages are followed to the end (including empty pages that still carry a token); transient 503s,
429s and connection failures are retried; every page repeats the first page's parameters; the tool's own
parameters are always sent; requests are throttled.
Negative: a failure that outlasts the retries never yields a partial pull — no silent dropout of a page,
a chunk or the spreadsheet; 400s are never retried and keep the server's words; redirects are never
followed; an HTML or malformed body is never data; a short, duplicated or looping pagination, a CSV that
disagrees with the JSON, or a registry refresh mid-pull all fail; a refused query sends nothing.
"""

import httpx
import pytest
from conftest import CSV_HEADER_ROW, FakeAPI, csv_page, csv_row, json_page, version

from TrialLedger.ingest import MAX_ATTEMPTS, MIN_INTERVAL_SECONDS, PullError, pull

A, B, C = "NCT00000001", "NCT00000002", "NCT00000003"


def run(fake, no_clock, query=None):
    return pull(
        query or {"query.cond": "asthma"},
        http=fake.client(),
        sleep=fake.sleep,
        monotonic=no_clock,
        clock=lambda: "2026-10-31T16:00:00Z",
    )


def two_page_api(**overrides):
    script = {
        "json_pages": [json_page([A, B], total=3, token="j1"), json_page([C])],
        "csv_pages": [csv_page([A, B], total=3, token="c1", header=True), csv_page([C])],
    }
    script.update(overrides)
    # Raw full-body acquisition now asks a single ID-only preflight before these exact
    # full JSON/CSV response scripts. Keep that extra request visible in assertions.
    total = 3
    for response in script["json_pages"]:
        if isinstance(response, httpx.Response) and response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                continue
            if isinstance(payload, dict) and type(payload.get("totalCount")) is int:
                total = payload["totalCount"]
                break
    script["json_pages"] = [json_page([A], total=total, token="preflight"), *script["json_pages"]]
    return FakeAPI(**script)


def test_complete_pull_across_pages(no_clock):
    result = run(two_page_api(), no_clock)
    ids = [s["protocolSection"]["identificationModule"]["nctId"] for s in result.studies]
    assert (result.total_count, ids) == (3, [A, B, C])
    assert result.csv_text == CSV_HEADER_ROW + csv_row(A) + csv_row(B) + csv_row(C)
    assert (result.api_version, result.data_timestamp, result.retrieved_at) == (
        "2.0.5",
        "2026-10-30T09:00:04",
        "2026-10-31T16:00:00Z",
    )


def test_query_and_tool_parameters_are_sent(no_clock):
    fake = two_page_api()
    run(fake, no_clock, {"query.cond": "asthma", "filter.overallStatus": "RECRUITING"})
    preflight, *full_json = fake.studies_requests("json")
    assert preflight.url.params["fields"] == "NCTId"
    assert preflight.url.params["pageSize"] == "1000"
    first_json = dict(full_json[0].url.params)
    first_csv = dict(fake.studies_requests("csv")[0].url.params)
    assert first_json == {
        "query.cond": "asthma",
        "filter.overallStatus": "RECRUITING",
        "format": "json",
        "markupFormat": "markdown",
        "countTotal": "true",
        "pageSize": "100",
    }
    assert first_csv == {
        "query.cond": "asthma",
        "filter.overallStatus": "RECRUITING",
        "format": "csv",
        "countTotal": "true",
        "pageSize": "100",
    }


def test_later_pages_repeat_the_first_page_parameters(no_clock):
    fake = two_page_api()
    run(fake, no_clock)
    for fmt, token in (("json", "j1"), ("csv", "c1")):
        requests = fake.studies_requests(fmt)
        if fmt == "json":
            assert requests[0].url.params["fields"] == "NCTId"
            requests = requests[1:]
        first, second = (dict(r.url.params) for r in requests)
        assert second.pop("pageToken") == token
        assert second == first


def test_empty_page_with_a_token_keeps_paginating(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=3, token="j1"), json_page([], token="j2"), json_page([C])]
    )
    assert run(fake, no_clock).total_count == 3


def test_transient_503_is_retried(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=3, token="j1"), httpx.Response(503), json_page([C])]
    )
    assert run(fake, no_clock).total_count == 3
    assert 2.0 in fake.sleeps


def test_persistent_503_fails_the_pull_and_stops(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=3, token="j1")] + [httpx.Response(503)] * MAX_ATTEMPTS
    )
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.server_error"
    assert fake.studies_requests("csv") == []


def test_persistent_503_on_the_spreadsheet_fails_the_pull(no_clock):
    fake = two_page_api(
        csv_pages=[csv_page([A, B], total=3, token="c1", header=True)] + [httpx.Response(503)] * 4
    )
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.server_error"


def test_connection_failure_is_retried(no_clock):
    fake = two_page_api(
        json_pages=[httpx.ConnectError, json_page([A, B], total=3, token="j1"), json_page([C])]
    )
    assert run(fake, no_clock).total_count == 3


def test_persistent_connection_failure_fails_the_pull(no_clock):
    fake = two_page_api(json_pages=[httpx.ReadTimeout] * MAX_ATTEMPTS)
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.no_response"


def test_429_waits_as_long_as_retry_after_says(no_clock):
    limited = httpx.Response(429, headers={"retry-after": "7"})
    fake = two_page_api(json_pages=[limited, json_page([A, B], total=3, token="j1"), json_page([C])])
    assert run(fake, no_clock).total_count == 3
    assert 7.0 in fake.sleeps


def test_400_is_not_retried_and_keeps_the_server_text(no_clock):
    refusal = httpx.Response(400, text="`query.condition` is unknown parameter")
    fake = two_page_api(json_pages=[refusal])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.bad_request"
    assert "`query.condition` is unknown parameter" in raised.value.detail
    assert len(fake.studies_requests("json")) == 2


def test_html_200_is_not_data(no_clock):
    page = httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>busy</html>")
    fake = two_page_api(json_pages=[page])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.wrong_content_type"


def test_redirect_is_never_followed(no_clock):
    moved = httpx.Response(301, headers={"location": f"https://clinicaltrials.gov/api/v2/studies/{A}"})
    fake = two_page_api(json_pages=[moved])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "http.redirect"
    assert [r.url.path for r in fake.requests] == ["/api/v2/version", "/api/v2/studies", "/api/v2/studies"]


def test_malformed_json_body_fails(no_clock):
    broken = httpx.Response(200, headers={"content-type": "application/json"}, content=b'{"studies": [')
    fake = two_page_api(json_pages=[broken])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "json.bad_json"


def test_fewer_studies_than_the_total_fails(no_clock):
    fake = two_page_api(json_pages=[json_page([A, B], total=3)])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "json.short"


def test_a_study_repeated_across_pages_fails(no_clock):
    fake = two_page_api(json_pages=[json_page([A, B], total=3, token="j1"), json_page([B])])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "json.duplicates"


def test_a_repeated_page_token_fails(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A], total=3, token="j1"), json_page([B], token="j1"), json_page([C])]
    )
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "json.repeated_token"


def test_csv_page_repeating_the_header_fails(no_clock):
    fake = two_page_api(
        csv_pages=[csv_page([A, B], total=3, token="c1", header=True), csv_page([C], header=True)]
    )
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "csv.extra_header"


def test_csv_with_fewer_rows_than_its_total_fails(no_clock):
    fake = two_page_api(csv_pages=[csv_page([A, B], total=3, header=True)])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "csv.short"


def test_unparseable_csv_fails(no_clock):
    body = (CSV_HEADER_ROW + f'{A},"unterminated\r\n').encode()
    broken = httpx.Response(200, headers={"content-type": "text/csv", "x-total-count": "1"}, content=body)
    fake = two_page_api(json_pages=[json_page([A], total=1)], csv_pages=[broken])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "csv.unparseable"


def test_csv_disagreeing_with_json_fails(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=2)], csv_pages=[csv_page([A, C], total=2, header=True)]
    )
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "formats.different"


def test_registry_refresh_during_the_pull_fails(no_clock):
    fake = two_page_api(versions=[version(), version(data_timestamp="2026-10-31T09:00:02")])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "snapshot.changed"


def test_version_without_a_data_timestamp_sends_no_query(no_clock):
    fake = FakeAPI(versions=[httpx.Response(200, json={"apiVersion": "2.0.5"})])
    with pytest.raises(PullError) as raised:
        run(fake, no_clock)
    assert raised.value.code == "version.no_data_timestamp"
    assert fake.studies_requests("json") == []


def test_refused_query_sends_nothing(no_clock):
    fake = FakeAPI()
    with pytest.raises(PullError) as raised:
        run(fake, no_clock, {"query.term": A, "filter.overallStatus": "RECRUITING"})
    assert raised.value.code == "query.filters_ignored"
    assert fake.requests == []


def test_requests_are_throttled(no_clock):
    fake = two_page_api()
    run(fake, no_clock)
    assert fake.sleeps.count(MIN_INTERVAL_SECONDS) == len(fake.requests) - 1
