"""follow_batches — the studies of the verified IDs, each batch what query_studies sends for filter.ids.

Positive: the IDs are cut into batches of PAGE_SIZE in page order, each named exactly as query_studies asks
for filter.ids of its IDs (100 a page, no projection) and all of them awaited at once; saved batches that hold
exactly their IDs, in any order, are complete; a full batch holding exactly its IDs and its totalCount is
whole even with a nextPageToken (a further page could only exceed totalCount); no IDs need no batch.
Negative: a batch that is not JSON, one that is not a /studies page, one holding a study it did not ask for, a
repeat, or fewer studies than its totalCount (with or without a nextPageToken) is refused by name.
"""

from conftest import json_page

from TrialLedger.ingest import PAGE_SIZE, json_query_params
from TrialLedger.steps import STUDIES_URL, follow_batches

A, B, C = "NCT00000001", "NCT00000002", "NCT00000003"


def batch(file, ids):
    params = {
        "filter.ids": ",".join(ids),
        "format": "json",
        "markupFormat": "markdown",
        "countTotal": "true",
        "pageSize": "100",
    }
    return {"file": file, "url": STUDIES_URL, "params": params, "why": "studies_batch"}


def body(nct_ids, total=None, token=None):
    return json_page(nct_ids, total=total, token=token).json()


def test_no_ids_need_no_batch():
    assert follow_batches([], {}, []) == ("complete", [], [], "")


def test_every_batch_is_awaited_at_once_as_query_studies_asks():
    ids = [f"NCT{n:08d}" for n in range(1, PAGE_SIZE + 3)]
    assert (
        json_query_params({"filter.ids": ",".join(ids[:PAGE_SIZE])}) == batch("x", ids[:PAGE_SIZE])["params"]
    )
    first, second = batch("studies-001.json", ids[:PAGE_SIZE]), batch("studies-002.json", ids[PAGE_SIZE:])
    assert follow_batches(ids, {}, []) == ("awaiting_fetch", [first, second], [first, second], "")


def test_only_the_unsaved_batches_are_awaited():
    ids = [f"NCT{n:08d}" for n in range(1, PAGE_SIZE + 2)]
    bodies = {"studies-001.json": body(ids[:PAGE_SIZE], total=PAGE_SIZE)}
    code, batches, awaited, detail = follow_batches(ids, bodies, [])
    assert (code, [b["file"] for b in batches], awaited, detail) == (
        "awaiting_fetch",
        ["studies-001.json", "studies-002.json"],
        [batch("studies-002.json", ids[PAGE_SIZE:])],
        "",
    )


def test_saved_batches_holding_their_ids_in_any_order_are_complete():
    bodies = {"studies-001.json": body([C, A, B], total=3)}
    assert follow_batches([A, B, C], bodies, []) == (
        "complete",
        [batch("studies-001.json", [A, B, C])],
        [],
        "",
    )


def test_a_batch_that_is_not_json_is_refused():
    assert follow_batches([A], {}, ["studies-001.json"]) == (
        "not_json",
        [batch("studies-001.json", [A])],
        [],
        "studies-001.json",
    )


def test_a_batch_that_is_not_a_studies_page_is_refused():
    assert follow_batches([A], {"studies-001.json": {"message": "busy"}}, []) == (
        "not_a_registry_page",
        [batch("studies-001.json", [A])],
        [],
        "studies-001.json: no_studies",
    )


def test_a_batch_without_its_total_is_refused():
    assert follow_batches([A], {"studies-001.json": body([A])}, [])[0::3] == (
        "not_a_registry_page",
        "studies-001.json: no_total",
    )


def test_a_batch_holding_a_study_it_did_not_ask_for_is_refused():
    assert follow_batches([A, B], {"studies-001.json": body([A, C], total=2)}, []) == (
        "incomplete_total",
        [batch("studies-001.json", [A, B])],
        [],
        "studies-001.json: 2 studies (complete), 2 asked",
    )


def test_a_batch_repeating_a_study_is_refused():
    assert follow_batches([A, B], {"studies-001.json": body([A, A], total=2)}, [])[0::3] == (
        "incomplete_total",
        "studies-001.json: 2 studies (duplicates), 2 asked",
    )


def test_a_batch_short_of_its_total_is_refused():
    assert follow_batches([A], {"studies-001.json": body([A], total=2)}, [])[0::3] == (
        "incomplete_total",
        "studies-001.json: 1 studies (short), 1 asked",
    )


def test_a_whole_batch_offering_a_further_page_is_complete():
    ids = [f"NCT{n:08d}" for n in range(1, PAGE_SIZE + 1)]
    bodies = {"studies-001.json": body(ids, total=PAGE_SIZE, token="t")}
    assert follow_batches(ids, bodies, []) == ("complete", [batch("studies-001.json", ids)], [], "")


def test_a_short_batch_offering_a_further_page_is_refused():
    assert follow_batches([A, B], {"studies-001.json": body([A], total=2, token="t")}, [])[0::3] == (
        "incomplete_total",
        "studies-001.json: 1 studies (short), 2 asked",
    )


def test_a_refused_batch_stops_before_the_later_ones():
    ids = [f"NCT{n:08d}" for n in range(1, PAGE_SIZE + 2)]
    code, batches, awaited, detail = follow_batches(ids, {}, ["studies-001.json"])
    assert (code, len(batches), awaited, detail) == ("not_json", 1, [], "studies-001.json")
