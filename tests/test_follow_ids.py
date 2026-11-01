"""follow_ids — a run folder's ID pages are the pages query_ids asks for, followed only while they are honest.

Positive: an empty folder names page one, exactly as query_ids sends it (fields=NCTId, 1,000 a page); a saved
page with a nextPageToken names the next page with that token and nothing else changed; pages followed to the
last give every ID in page order, empty pages with a token included; a query matching nothing is complete.
Negative: a body that is not JSON, a JSON body that is not a /studies page (a /version body, a first page
without totalCount, a study without a canonical NCT ID) is refused by name; pages that cannot be followed to
totalCount (a token already followed, more IDs than totalCount before the last page, too many empty pages) and
pages holding fewer, more or repeated IDs than totalCount are refused as incomplete_total, the classifier's
code in the detail, never followed.
"""

from conftest import json_page, version

from TrialLedger.ingest import json_query_params
from TrialLedger.steps import STUDIES_URL, follow_ids

QUERY = {"query.cond": "lung cancer", "filter.advanced": "AREA[Phase]PHASE3"}
A, B, C = "NCT00000001", "NCT00000002", "NCT00000003"
FIRST = {
    "query.cond": "lung cancer",
    "filter.advanced": "AREA[Phase]PHASE3",
    "format": "json",
    "markupFormat": "markdown",
    "countTotal": "true",
    "pageSize": "1000",
    "fields": "NCTId",
}


def page(file, params):
    return {"file": file, "url": STUDIES_URL, "params": params, "why": "id_page"}


def body(nct_ids, total=None, token=None):
    return json_page(nct_ids, total=total, token=token).json()


def test_an_empty_folder_names_page_one_as_query_ids_sends_it():
    assert json_query_params(QUERY, "NCTId") == FIRST
    assert follow_ids(QUERY, {}, []) == ("awaiting_fetch", [page("ids-001.json", FIRST)], [], "ids-001.json")


def test_a_saved_page_with_a_token_names_the_next_page_with_it():
    bodies = {"ids-001.json": body([A, B], total=3, token="t1")}
    second = {**FIRST, "pageToken": "t1"}
    assert follow_ids(QUERY, bodies, []) == (
        "awaiting_fetch",
        [page("ids-001.json", FIRST), page("ids-002.json", second)],
        [A, B],
        "ids-002.json",
    )


def test_pages_followed_to_the_last_give_every_id_in_page_order():
    bodies = {
        "ids-001.json": body([A], total=3, token="t1"),
        "ids-002.json": body([], token="t2"),
        "ids-003.json": body([B, C]),
    }
    code, pages, ids, detail = follow_ids(QUERY, bodies, [])
    assert (code, ids, detail) == ("complete", [A, B, C], "")
    assert [p["params"].get("pageToken") for p in pages] == [None, "t1", "t2"]


def test_a_query_matching_nothing_is_complete():
    assert follow_ids(QUERY, {"ids-001.json": body([], total=0)}, []) == (
        "complete",
        [page("ids-001.json", FIRST)],
        [],
        "",
    )


def test_a_body_that_is_not_json_is_refused():
    assert follow_ids(QUERY, {}, ["ids-001.json"]) == (
        "not_json",
        [page("ids-001.json", FIRST)],
        [],
        "ids-001.json",
    )


def test_a_version_body_saved_as_a_page_is_not_a_registry_page():
    assert follow_ids(QUERY, {"ids-001.json": version().json()}, [])[0::3] == (
        "not_a_registry_page",
        "ids-001.json: no_studies",
    )


def test_a_first_page_without_a_total_is_not_a_registry_page():
    assert follow_ids(QUERY, {"ids-001.json": body([A])}, [])[0::3] == (
        "not_a_registry_page",
        "ids-001.json: no_total",
    )


def test_a_later_page_needs_no_total_but_a_valid_study():
    bodies = {"ids-001.json": body([A], total=2, token="t1"), "ids-002.json": {"studies": [{"x": 1}]}}
    assert follow_ids(QUERY, bodies, [])[0::3] == ("not_a_registry_page", "ids-002.json: bad_study")


def test_a_token_already_followed_is_refused():
    bodies = {
        "ids-001.json": body([A], total=3, token="t1"),
        "ids-002.json": body([B], token="t1"),
    }
    assert follow_ids(QUERY, bodies, [])[0::3] == ("incomplete_total", "ids-002.json: repeated_token")


def test_more_ids_than_the_total_before_the_last_page_are_refused():
    bodies = {"ids-001.json": body([A, B], total=1, token="t1")}
    assert follow_ids(QUERY, bodies, [])[0::3] == ("incomplete_total", "ids-001.json: overrun")


def test_too_many_empty_pages_are_refused():
    bodies = {
        "ids-001.json": body([], total=1, token="t1"),
        "ids-002.json": body([], token="t2"),
        "ids-003.json": body([], token="t3"),
    }
    assert follow_ids(QUERY, bodies, [])[0::3] == ("incomplete_total", "ids-003.json: stalled")


def test_fewer_ids_than_the_total_are_refused():
    assert follow_ids(QUERY, {"ids-001.json": body([A, B], total=3)}, []) == (
        "incomplete_total",
        [page("ids-001.json", FIRST)],
        [A, B],
        "short: 2 IDs for a totalCount of 3",
    )


def test_a_repeated_id_is_refused():
    bodies = {"ids-001.json": body([A, B], total=3, token="t1"), "ids-002.json": body([B])}
    assert follow_ids(QUERY, bodies, [])[0::3] == (
        "incomplete_total",
        "duplicates: 3 IDs for a totalCount of 3",
    )


def test_more_ids_than_the_total_are_refused():
    bodies = {"ids-001.json": body([A, B], total=1)}
    assert follow_ids(QUERY, bodies, [])[0::3] == ("incomplete_total", "excess: 2 IDs for a totalCount of 1")
