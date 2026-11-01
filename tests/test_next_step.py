"""next_step — what a run folder needs next: the direct path's own requests, in its order, or complete, or a
refusal by name.

Positive: an empty folder names /version first, with the scope's RxNav answers alongside; then ID page one;
then every batch at once; then /version again, only once every batch is saved; a folder holding every body,
both /version answers the same snapshot, is complete, and its plan is every fetch in order; an RxNav answer
not yet saved is still awaited after the registry's last body; an RxNav answer that is not JSON (an error
page, a recorded failure) is answered, read later as a failed lookup, and never asked again.
Negative: a registry body that is not JSON (the first or last /version), a /version that is not one, a
refused ID page or batch (a repeated page token among them), a last /version from another snapshot, and a
body saved before its fetch was named (the last /version fetched early, a page named by no plan, a body the
folder's list of fetches never named, an RxNav answer the scope does not hold) are each refused by name,
never complete.
"""

from conftest import json_page, version

from TrialLedger.steps import END_NAME, START_NAME, STUDIES_URL, VERSION_URL, next_step

QUERY = {"query.cond": "asthma"}
A, B = "NCT00000001", "NCT00000002"
RXNAV = [["https://rxnav.nlm.nih.gov/REST/rxcui.json", {"name": "aspirin", "search": "0"}]]
START = {"file": START_NAME, "url": VERSION_URL, "params": {}, "why": "version_start"}
END = {"file": END_NAME, "url": VERSION_URL, "params": {}, "why": "version_end"}
ANSWER = {"file": "rxnav-001.json", "url": RXNAV[0][0], "params": RXNAV[0][1], "why": "rxnav_answer"}


def every_body(end=None):
    """Every body of a two-study pull: both /version answers, one ID page, one batch."""
    return {
        START_NAME: version().json(),
        "ids-001.json": json_page([A, B], total=2).json(),
        "studies-001.json": json_page([A, B], total=2).json(),
        END_NAME: end or version().json(),
    }


def files(fetches):
    return [fetch["file"] for fetch in fetches]


def test_an_empty_folder_names_version_first():
    assert next_step(QUERY, [], [], {}, []) == ("awaiting_fetch", [START], [START], "")


def test_the_rxnav_answers_are_named_alongside_the_first_version():
    assert next_step(QUERY, RXNAV, [], {}, []) == ("awaiting_fetch", [START, ANSWER], [START, ANSWER], "")


def test_after_version_the_first_id_page_is_named():
    code, plan, awaited, detail = next_step(QUERY, [], [START_NAME], {START_NAME: version().json()}, [])
    assert (code, files(plan), files(awaited), detail) == (
        "awaiting_fetch",
        [START_NAME, "ids-001.json"],
        ["ids-001.json"],
        "",
    )
    assert awaited[0]["url"] == STUDIES_URL
    assert awaited[0]["params"]["fields"] == "NCTId"


def test_after_the_id_pages_every_batch_is_named():
    bodies = {key: value for key, value in every_body().items() if key in (START_NAME, "ids-001.json")}
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), files(awaited), detail) == (
        "awaiting_fetch",
        [START_NAME, "ids-001.json", "studies-001.json"],
        ["studies-001.json"],
        "",
    )
    assert awaited[0]["params"]["filter.ids"] == f"{A},{B}"


def test_the_last_version_is_named_once_every_batch_is_saved():
    bodies = every_body()
    del bodies[END_NAME]
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, plan[-1], awaited, detail) == ("awaiting_fetch", END, [END], "")


def test_a_folder_holding_every_body_of_one_snapshot_is_complete():
    bodies = every_body()
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), awaited, detail) == (
        "complete",
        [START_NAME, "ids-001.json", "studies-001.json", END_NAME],
        [],
        "",
    )


def test_an_rxnav_answer_not_saved_is_still_awaited():
    bodies = every_body()
    code, plan, awaited, detail = next_step(QUERY, RXNAV, [*bodies, "rxnav-001.json"], bodies, [])
    assert (code, files(plan), awaited, detail) == (
        "awaiting_fetch",
        [START_NAME, "rxnav-001.json", "ids-001.json", "studies-001.json", END_NAME],
        [ANSWER],
        "",
    )


def test_every_rxnav_answer_saved_completes_the_run():
    bodies = {**every_body(), "rxnav-001.json": {"idGroup": {"name": "aspirin"}}}
    assert next_step(QUERY, RXNAV, list(bodies), bodies, [])[0] == "complete"


def test_an_rxnav_answer_that_is_not_json_is_answered_not_refused():
    assert next_step(QUERY, RXNAV, [START_NAME, "rxnav-001.json"], {}, ["rxnav-001.json"]) == (
        "awaiting_fetch",
        [START, ANSWER],
        [START],
        "",
    )
    bodies = every_body()
    assert next_step(QUERY, RXNAV, [*bodies, "rxnav-001.json"], bodies, ["rxnav-001.json"]) == (
        "complete",
        [START, ANSWER, *next_step(QUERY, [], list(bodies), bodies, [])[1][1:]],
        [],
        "",
    )


def test_an_rxnav_answer_the_scope_does_not_hold_is_out_of_order():
    bodies = {START_NAME: version().json()}
    assert next_step(QUERY, RXNAV, [START_NAME, "rxnav-001.json"], bodies, ["rxnav-002.json"])[0::3] == (
        "page_out_of_order",
        "rxnav-002.json: saved before it was named",
    )


def test_a_repeated_page_token_is_an_incomplete_total():
    bodies = {
        START_NAME: version().json(),
        "ids-001.json": json_page([A], total=2, token="t").json(),
        "ids-002.json": json_page([B], token="t").json(),
    }
    assert next_step(QUERY, [], list(bodies), bodies, [])[0::3] == (
        "incomplete_total",
        "ids-002.json: repeated_token",
    )


def test_a_first_version_that_is_not_json_is_refused():
    assert next_step(QUERY, [], [START_NAME], {}, [START_NAME]) == ("not_json", [START], [], START_NAME)


def test_a_first_version_that_is_not_one_is_refused():
    page = json_page([A], total=1).json()
    assert next_step(QUERY, [], [START_NAME], {START_NAME: page}, []) == (
        "not_a_registry_page",
        [START],
        [],
        "version-start.json: no_api_version",
    )


def test_a_refused_id_page_is_refused_by_its_name():
    bodies = {START_NAME: version().json(), "ids-001.json": json_page([A], total=2).json()}
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), awaited, detail) == (
        "incomplete_total",
        [START_NAME, "ids-001.json"],
        [],
        "short: 1 IDs for a totalCount of 2",
    )


def test_a_refused_batch_is_refused_by_its_name():
    bodies = every_body()
    bodies["studies-001.json"] = json_page([A], total=1).json()
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), awaited, detail) == (
        "incomplete_total",
        [START_NAME, "ids-001.json", "studies-001.json"],
        [],
        "studies-001.json: 1 studies (complete), 2 asked",
    )


def test_a_last_version_that_is_not_json_is_refused():
    bodies = every_body()
    del bodies[END_NAME]
    code, plan, awaited, detail = next_step(QUERY, [], [*bodies, END_NAME], bodies, [END_NAME])
    assert (code, plan[-1], awaited, detail) == ("not_json", END, [], END_NAME)


def test_a_last_version_that_is_not_one_is_refused():
    bodies = every_body(end={"apiVersion": "2.0.5"})
    assert next_step(QUERY, [], list(bodies), bodies, [])[0::3] == (
        "not_a_registry_page",
        "version-end.json: no_data_timestamp",
    )


def test_a_last_version_of_another_snapshot_is_refused():
    bodies = every_body(end=version(data_timestamp="2026-10-31T09:00:02").json())
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, plan[-1], awaited, detail) == (
        "snapshot_changed",
        END,
        [],
        "API 2.0.5, data 2026-10-30T09:00:04 → 2.0.5, 2026-10-31T09:00:02",
    )


def test_another_api_version_is_another_snapshot():
    bodies = every_body(end=version(api_version="2.0.6").json())
    assert next_step(QUERY, [], list(bodies), bodies, [])[0] == "snapshot_changed"


def test_a_last_version_fetched_before_the_batches_is_out_of_order():
    bodies = every_body()
    del bodies["studies-001.json"]
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), awaited, detail) == (
        "page_out_of_order",
        [START_NAME, "ids-001.json", "studies-001.json"],
        [],
        "version-end.json: saved before it was named",
    )


def test_a_body_its_fetch_list_never_named_is_out_of_order():
    bodies = every_body()
    named = [name for name in bodies if name != END_NAME]
    assert next_step(QUERY, [], named, bodies, [])[0::3] == (
        "page_out_of_order",
        "version-end.json: saved before it was named",
    )


def test_an_unreadable_file_no_plan_names_is_out_of_order():
    assert next_step(QUERY, [], [START_NAME], {START_NAME: version().json()}, ["notes.json"])[0::3] == (
        "page_out_of_order",
        "notes.json: saved before it was named",
    )


def test_only_the_id_page_the_last_token_fixes_is_awaited():
    bodies = {START_NAME: version().json(), "ids-001.json": json_page([A], total=2, token="t1").json()}
    code, plan, awaited, detail = next_step(QUERY, [], list(bodies), bodies, [])
    assert (code, files(plan), files(awaited), detail) == (
        "awaiting_fetch",
        [START_NAME, "ids-001.json", "ids-002.json"],
        ["ids-002.json"],
        "",
    )
    assert awaited[0]["params"]["pageToken"] == "t1"


def test_the_first_stray_file_in_name_order_is_named():
    bodies = {START_NAME: version().json(), "z-notes.json": {}}
    assert next_step(QUERY, [], [START_NAME], bodies, ["a-notes.json"])[0::3] == (
        "page_out_of_order",
        "a-notes.json: saved before it was named",
    )
