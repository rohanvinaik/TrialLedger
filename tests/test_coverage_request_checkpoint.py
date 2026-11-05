"""Coverage retries share the acquisition checkpoint; annotation damage is not absence."""

import json

import httpx
import pytest
from test_search_coverage_run import CLASS_IDS, REQUEST, Registry, compare, make_run, nct, saved

from TrialLedger import coverage, coverage_run, operate


class IdentifierFailure(Registry):
    def serve(self, request):
        if "query.cond" in request.url.params:
            self.requests.append(request)
            return httpx.Response(400, json={})
        return super().serve(request)


def finish_coverage_relay(folder, registry):
    while True:
        state, _detail = coverage_run.run_coverage(folder, relay=True)
        if state != "awaiting_fetch":
            return state
        with registry.client() as client:
            for fetch in saved(folder)["fetches"]:
                (folder / fetch["save_as"]).write_bytes(client.get(fetch["url"]).content)


@pytest.mark.parametrize("limit", [7, 8])
def test_failed_direct_attempt_remains_additive_when_relay_saves_new_responses(tmp_path, limit):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": limit})
    direct = IdentifierFailure()
    assert compare(folder, direct)[0] == "failed" and len(direct.requests) == 2
    relay = Registry()
    assert finish_coverage_relay(folder, relay) == "complete"
    assert 3 + len(direct.requests) + len(relay.requests) == limit
    assert coverage_run.spent_requests(folder) == limit
    assert saved(folder)["diagnosis"]["state"] == ("not_run" if limit == 7 else "complete")
    assert coverage_run.comparison_plan(folder)["spent_requests"] == limit
    again = Registry()
    assert finish_coverage_relay(folder, again) == "complete" and again.requests == []
    assert coverage_run.spent_requests(folder) == limit


def test_legacy_direct_checkpoint_migrates_before_new_relay_responses(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    assert compare(folder, IdentifierFailure())[0] == "failed"
    path = folder / coverage_run.ACQUISITION_NAME
    document = json.loads(path.read_text())
    document.pop("accounted_response_paths", None)
    path.write_text(json.dumps(document))
    relay = Registry()
    assert finish_coverage_relay(folder, relay) == "complete"
    assert len(relay.requests) == 2 and coverage_run.spent_requests(folder) == 7
    assert saved(folder)["diagnosis"]["state"] == "not_run"
    assert "accounted_response_paths" in json.loads(path.read_text())


def test_relay_then_direct_failure_then_relay_keeps_each_attempt_once(tmp_path):
    class VersionFailure(Registry):
        def serve(self, request):
            if request.url.path == "/api/v2/version":
                self.requests.append(request)
                return httpx.Response(400, json={})
            return super().serve(request)

    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    first = Registry()
    assert coverage_run.run_coverage(folder, relay=True)[0] == "awaiting_fetch"
    with first.client() as client:
        for fetch in saved(folder)["fetches"]:
            (folder / fetch["save_as"]).write_bytes(client.get(fetch["url"]).content)
    direct = VersionFailure()
    assert compare(folder, direct)[0] == "snapshot_differs"  # IDs complete, closing snapshot unread
    assert len(first.requests) == 2 and len(direct.requests) == 1
    assert coverage_run.spent_requests(folder) == 6
    last = Registry()
    assert finish_coverage_relay(folder, last) == "complete"
    assert len(last.requests) == 1 and coverage_run.spent_requests(folder) == 7
    assert saved(folder)["diagnosis"]["state"] == "not_run"


def test_legacy_main_checkpoint_preserves_recorded_retries_during_migration(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 8})
    path = folder / coverage_run.ACQUISITION_NAME
    path.write_text(json.dumps({"registry_requests": 5, "policy": {"retained": "metadata"}}))
    assert coverage_run.spent_requests(folder) == 5
    relay = Registry(text_ids=CLASS_IDS)
    assert finish_coverage_relay(folder, relay) == "complete"
    assert len(relay.requests) == 3 and coverage_run.spent_requests(folder) == 8
    assert json.loads(path.read_text())["policy"] == {"retained": "metadata"}


@pytest.mark.parametrize("invalid", [None, "not-an-array", [17], ["same", "same"]])
def test_malformed_response_anchor_never_authorizes_acquisition(tmp_path, invalid):
    folder = make_run(tmp_path)
    path = folder / coverage_run.ACQUISITION_NAME
    path.write_text(json.dumps({"registry_requests": 5, "accounted_response_paths": invalid}))
    with pytest.raises(coverage_run.PullError) as error:
        coverage_run.spent_requests(folder)
    assert error.value.code == "acquisition.invalid_cost"


def test_legacy_mixed_checkpoint_without_an_anchor_refuses_to_invent_total(tmp_path):
    folder = make_run(tmp_path)
    assert compare(folder, IdentifierFailure())[0] == "failed"
    path = folder / coverage_run.ACQUISITION_NAME
    document = json.loads(path.read_text())
    document.pop("accounted_response_paths", None)
    path.write_text(json.dumps(document))
    assert coverage_run.run_coverage(folder, relay=True)[0] == "awaiting_fetch"
    fetch = saved(folder)["fetches"][0]
    with Registry().client() as client:
        (folder / fetch["save_as"]).write_bytes(client.get(fetch["url"]).content)
    # Reconstruct an older mixed checkpoint: it has neither response identities nor which relay
    # successes were incorporated into its recorded attempts. This must remain an accounting question.
    document = json.loads(path.read_text())
    document.pop("accounted_response_paths", None)
    path.write_text(json.dumps(document))
    before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    with pytest.raises(coverage_run.PullError) as error:
        coverage_run.spent_requests(folder)
    assert error.value.code == "acquisition.unverifiable_cost"
    assert {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()} == before


def test_cumulative_request_count_adds_new_responses_beside_recorded_failures():
    assert coverage.cumulative_request_count(5, ["main", "start", "ids"], ["main", "start"]) == 6


def test_cumulative_request_count_never_recharges_retained_or_deleted_responses():
    assert coverage.cumulative_request_count(7, ["a", "a"], ["a", "deleted"]) == 7


@pytest.mark.parametrize("relay", [False, True])
@pytest.mark.parametrize(
    "damage",
    ["count", "anchor", "array", "null", "invalid_json", "legacy_stamps", "legacy_stamp_values"],
)
def test_malformed_accounting_is_a_public_result_not_a_crash_or_a_request(tmp_path, relay, damage):
    from test_search_coverage_run import FullRegistry

    folder = tmp_path / "malformed"
    registry = FullRegistry()
    assert (
        operate.run(folder, REQUEST, "direct", http=registry.client(), sleep=lambda _s: None).status
        == "complete"
    )
    checkpoint = folder / coverage_run.ACQUISITION_NAME
    document = json.loads(checkpoint.read_text())
    if damage == "count":
        document["registry_requests"] = "eight"
    elif damage == "anchor":
        document["accounted_response_paths"] = [17]
    elif damage == "array":
        document = []
    elif damage == "null":
        document = None
    elif damage.startswith("legacy_stamp"):
        document.pop("accounted_response_paths")
        stamps = folder / coverage_run.COVERAGE_DIR / coverage_run.RETRIEVED_NAME
        stamps.write_text(json.dumps(17 if damage == "legacy_stamps" else {"ids-001.json": 17}))
    checkpoint.write_text("not-json" if damage == "invalid_json" else json.dumps(document))
    before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file() and "bodies" in p.parts}
    plan = coverage_run.comparison_plan(folder)
    assert plan["verdict"] == "acquisition.invalid_cost"
    assert plan["spent_requests"] is None and plan["planned_requests"] is None
    again = FullRegistry()
    result = operate.run(
        folder, REQUEST, "relay" if relay else "direct", http=again.client(), sleep=lambda _s: None
    )
    assert result.status == "complete" and "acquisition.invalid_cost" in result.detail
    assert again.requests == []
    assert saved(folder)["state"] == "incomplete" and saved(folder)["reason"] == "acquisition.invalid_cost"
    assert saved(folder)["class_search"]["state"] == saved(folder)["text_search"]["state"] == "complete"
    assert saved(folder)["budget"]["verdict"] == "acquisition.invalid_cost"
    assert "no statement is made" in saved(folder)["difference_words"]
    assert {
        str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file() and "bodies" in p.parts
    } == before


@pytest.mark.parametrize("relay", [False, True])
def test_unverifiable_legacy_accounting_has_a_public_result_without_new_requests(tmp_path, relay):
    from test_search_coverage_run import FullRegistry

    folder = tmp_path / "public"
    registry = FullRegistry()
    assert (
        operate.run(folder, REQUEST, "direct", http=registry.client(), sleep=lambda _s: None).status
        == "complete"
    )
    checkpoint = folder / coverage_run.ACQUISITION_NAME
    document = json.loads(checkpoint.read_text())
    document.pop("accounted_response_paths")
    checkpoint.write_text(json.dumps(document))
    stamps = folder / coverage_run.COVERAGE_DIR / coverage_run.RETRIEVED_NAME
    direct = json.loads(stamps.read_text())
    direct.pop("ids-001.json")
    stamps.write_text(json.dumps(direct))
    before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file() and "bodies" in p.parts}
    again = FullRegistry()
    outcome = operate.run(
        folder, REQUEST, "relay" if relay else "direct", http=again.client(), sleep=lambda _s: None
    )
    assert outcome.status == "complete" and "acquisition.unverifiable_cost" in outcome.detail
    assert again.requests == []
    assert saved(folder)["state"] == "incomplete"
    assert saved(folder)["class_search"]["state"] == "complete"
    assert saved(folder)["text_search"]["state"] == "complete"
    assert "no statement is made" in saved(folder)["difference_words"]
    plan = coverage_run.comparison_plan(folder)
    assert plan["verdict"] == "acquisition.unverifiable_cost"
    assert plan["spent_requests"] is None and plan["planned_requests"] is None
    assert {
        str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file() and "bodies" in p.parts
    } == before


def test_comparison_preview_reuses_a_complete_comparison_without_writes_or_network(tmp_path, monkeypatch):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    assert compare(folder, Registry())[0] == "complete"
    before = {str(path): path.read_bytes() for path in folder.rglob("*") if path.is_file()}

    def no_client(*args, **kwargs):
        pytest.fail("A retained comparison preview must never create a registry client")

    monkeypatch.setattr(coverage_run.httpx, "Client", no_client)
    plan = coverage_run.comparison_plan(folder)
    assert plan["spent_requests"] == plan["planned_requests"] == 7
    assert plan["retained_requests"] == 4 and plan["remaining_requests"] == 0
    assert plan["unique_studies"] == 2 and plan["verdict"] == "within_budget"
    assert {str(path): path.read_bytes() for path in folder.rglob("*") if path.is_file()} == before


def test_comparison_preview_keeps_failed_attempt_costs_and_updates_after_resume(tmp_path):
    class NonRetryFailure(Registry):
        def serve(self, request):
            if "query.cond" in request.url.params:
                self.requests.append(request)
                return httpx.Response(400, json={})
            return super().serve(request)

    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    assert compare(folder, NonRetryFailure(text_ids=CLASS_IDS))[0] == "failed"
    plan = coverage_run.comparison_plan(folder)
    assert plan["spent_requests"] == 5 and plan["retained_requests"] == 1
    assert plan["remaining_requests"] == 2 and plan["planned_requests"] == 7
    assert plan["verdict"] == "within_budget"
    assert compare(folder, Registry(text_ids=CLASS_IDS))[0] == "complete"
    resumed = coverage_run.comparison_plan(folder)
    assert resumed["spent_requests"] == resumed["planned_requests"] == 7
    assert resumed["remaining_requests"] == 0 and resumed["verdict"] == "within_budget"


def test_comparison_preview_cannot_hide_exhausted_attempts_behind_one_retained_response(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 6})
    assert compare(folder, Registry(text_ids=CLASS_IDS, fail_search=99))[0] == "failed"
    plan = coverage_run.comparison_plan(folder)
    assert plan["spent_requests"] == 6 and plan["remaining_requests"] == 2
    assert plan["planned_requests"] == 8 and plan["verdict"] == "request_expansion"


def test_comparison_preview_uses_saved_text_total_when_more_pages_are_required(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 2000, "max_registry_requests": 6})
    assert compare(folder, Registry(text_ids=CLASS_IDS, total=1100))[0] == "failed"
    plan = coverage_run.comparison_plan(folder)
    assert plan["spent_requests"] == 5 and plan["retained_requests"] == 2
    assert plan["unique_studies"] == 1100 and plan["remaining_requests"] == 2
    assert plan["planned_requests"] == 7 and plan["verdict"] == "request_expansion"


def test_failed_comparison_attempts_are_persisted_before_a_resume(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 6})
    first = Registry(text_ids=CLASS_IDS, fail_search=99)
    assert compare(folder, first)[0] == "failed"
    assert len(first.requests) == 3
    assert coverage_run.spent_requests(folder) == 6
    second = Registry(text_ids=CLASS_IDS)
    state, words = compare(folder, second)
    assert state == "failed" and "no statement is made" in words
    assert second.requests == []
    assert "acquisition_request_expansion" in saved(folder)["text_search"]["detail"]
    assert saved(folder)["class_search"]["state"] == "complete"


def test_a_retry_and_resume_with_sufficient_budget_charge_only_missing_work(tmp_path):
    class NonRetryFailure(Registry):
        def serve(self, request):
            if "query.cond" in request.url.params:
                self.requests.append(request)
                return httpx.Response(400, json={})
            return super().serve(request)

    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    first = NonRetryFailure(text_ids=CLASS_IDS)
    assert compare(folder, first)[0] == "failed"
    assert coverage_run.spent_requests(folder) == 5  # main 3, start version, failed identifier request
    second = Registry(text_ids=CLASS_IDS)
    assert compare(folder, second)[0] == "complete"  # identifier page and closing version fit exactly
    assert len(second.requests) == 2 and coverage_run.spent_requests(folder) == 7


def test_retained_complete_comparison_at_the_limit_needs_no_new_reservation(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 6})
    assert compare(folder, Registry(text_ids=CLASS_IDS))[0] == "complete"
    assert coverage_run.spent_requests(folder) == 6
    again = Registry(text_ids=CLASS_IDS)
    assert compare(folder, again)[0] == "complete"
    assert again.requests == []
    assert saved(folder)["budget"]["planned_requests"] == 6


def test_a_successful_retry_uses_the_remaining_budget_exactly(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 7})
    registry = Registry(text_ids=CLASS_IDS, fail_search=1)
    assert compare(folder, registry)[0] == "complete"
    assert len(registry.requests) == 4 and coverage_run.spent_requests(folder) == 7
    assert saved(folder)["budget"]["planned_requests"] == 7


def test_coverage_attempt_is_checkpointed_before_transport_runs(tmp_path):
    folder = make_run(tmp_path)
    registry = Registry(text_ids=CLASS_IDS)

    def serve(request):
        checkpoint = json.loads((folder / coverage_run.ACQUISITION_NAME).read_text())
        assert checkpoint["registry_requests"] == 3 + len(registry.requests) + 1
        return registry.serve(request)

    with httpx.Client(base_url=coverage_run.API_BASE, transport=httpx.MockTransport(serve)) as client:
        assert coverage_run.run_coverage(folder, http=client, sleep=lambda _s: None)[0] == "complete"


def test_malformed_annotations_do_not_erase_a_valid_comparison(tmp_path):
    class BrokenAnnotations(Registry):
        def serve(self, request):
            if "filter.ids" in request.url.params:
                self.requests.append(request)
                ids = request.url.params["filter.ids"].split(",")
                damaged = {"conditionBrowseModule": {"meshes": "not-an-array", "ancestors": [{"term": 17}]}}
                return httpx.Response(
                    200,
                    json={
                        "studies": [nct(identity, derived=damaged) for identity in ids],
                        "totalCount": len(ids),
                    },
                )
            return super().serve(request)

    folder = make_run(tmp_path)
    assert compare(folder, BrokenAnnotations())[0] == "complete"
    document = saved(folder)
    assert document["comparison"]["text_only"] == ["NCT00000003"]
    assert document["diagnosis"]["state"] == "incomplete"
    for reading in document["diagnosis"]["trials"].values():
        assert reading["annotation"] == "unreadable"
        assert reading["annotation_state"] == "malformed"


def test_main_run_budget_still_withholds_default_coverage_after_a_failed_attempt(tmp_path):
    from test_search_coverage_run import FullRegistry

    folder = tmp_path / "full"
    request = {**REQUEST, "acquisition": {"max_studies": 1000, "max_registry_requests": 7}}
    first = FullRegistry(fail_search=99)
    outcome = operate.run(folder, request, "direct", http=first.client(), sleep=lambda _s: None)
    assert outcome.status == "complete"
    before = coverage_run.spent_requests(folder)
    second = FullRegistry()
    outcome = operate.run(folder, request, "direct", http=second.client(), sleep=lambda _s: None)
    assert outcome.status == "complete"
    assert coverage_run.spent_requests(folder) == before
    assert second.requests == []
    assert saved(folder)["class_search"]["state"] == "complete"


def test_relay_saved_responses_are_counted_once_and_completed_replay_asks_nothing(tmp_path):
    from test_search_coverage_run import FullRegistry, relay_to_the_end

    folder = tmp_path / "relay"
    request = {**REQUEST, "acquisition": {"max_studies": 1000, "max_registry_requests": 8}}
    outcome, rounds = relay_to_the_end(folder, request, FullRegistry())
    assert outcome.status == "complete" and rounds
    assert coverage_run.spent_requests(folder) == 8
    again, rounds = relay_to_the_end(folder, request, FullRegistry())
    assert again.status == "complete" and rounds == []
    assert coverage_run.spent_requests(folder) == 8
    assert saved(folder)["budget"]["planned_requests"] == 8


def test_budget_subtracts_only_retained_successes_from_the_remaining_work():
    plan = coverage.comparison_budget(
        {"max_studies": 100, "max_registry_requests": 7}, 2, 2, 6, retained_requests=2
    )
    assert plan["remaining_requests"] == 1
    assert plan["planned_requests"] == 7 and plan["verdict"] == "within_budget"


def test_missing_empty_and_malformed_annotations_keep_distinct_structural_states():
    missing = coverage.annotation_reading({}, "lung")
    empty = coverage.annotation_reading(
        {"derivedSection": {"conditionBrowseModule": {"meshes": [], "ancestors": []}}}, "lung"
    )
    malformed = coverage.annotation_reading(
        {"derivedSection": {"conditionBrowseModule": {"meshes": "not-an-array"}}}, "lung"
    )
    assert missing["annotation_state"] == "missing" and missing["annotation"] == "none"
    assert empty["annotation_state"] == "empty" and empty["annotation"] == "none"
    assert malformed["annotation_state"] == "malformed" and malformed["annotation"] == "unreadable"


def test_known_matching_annotation_survives_an_independently_malformed_array():
    reading = coverage.annotation_reading(
        {"derivedSection": {"conditionBrowseModule": {"meshes": [{"term": "lung"}], "ancestors": False}}},
        "lung",
    )
    assert reading["annotation"] == "under_class"
    assert reading["annotation_state"] == "malformed"
    assert reading["mesh_terms"] == ["lung"]


@pytest.mark.parametrize(
    ("fields", "values", "malformed", "expected"),
    [(False, False, False, "missing"), (True, False, False, "empty"), (True, True, False, "present")],
)
def test_annotation_structure_named_states(fields, values, malformed, expected):
    assert coverage.annotation_state(fields, values, malformed) == expected


@pytest.mark.parametrize(("fields", "values"), [(False, False), (True, False), (True, True)])
def test_malformed_annotation_structure_never_reads_as_missing_or_empty(fields, values):
    assert coverage.annotation_state(fields, values, True) == "malformed"


@pytest.mark.parametrize("invalid", [True, -1, 0.5, None])
def test_retained_work_never_accepts_an_invalid_cost(invalid):
    with pytest.raises(ValueError, match="^coverage_invalid_retained_cost$"):
        coverage.comparison_budget(
            {"max_studies": 100, "max_registry_requests": 7}, 2, 2, 6, retained_requests=invalid
        )
