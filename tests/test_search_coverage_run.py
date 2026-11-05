"""The coverage comparison against a mocked registry (the transport seam every acquisition test uses)."""

import json

import httpx
import pytest
from conftest import DATA_TIMESTAMP, version

from TrialLedger import coverage, coverage_run
from TrialLedger.request import resolve_scope

REQUEST = {"condition_class": "Carcinoma, Non-Small-Cell Lung", "phase": ["PHASE3"]}
CLASS_IDS = ["NCT00000001", "NCT00000002"]
TEXT_IDS = ["NCT00000002", "NCT00000003"]  # equal counts, different trials


def nct(nct_id, derived=None, conditions=("NSCLC",)):
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": f"T {nct_id}"},
            "conditionsModule": {"conditions": list(conditions)},
        },
        "derivedSection": derived if derived is not None else {},
    }
    return record


class Registry:
    """/version, the text search's id pages and the diagnosis batches; every request recorded."""

    def __init__(self, text_ids=TEXT_IDS, total=None, stamps=None, fail_search=0, pages=None):
        self.text_ids, self.total = list(text_ids), total
        self.stamps = list(stamps or [DATA_TIMESTAMP, DATA_TIMESTAMP])
        self.fail_search, self.pages = fail_search, pages
        self.requests = []

    def serve(self, request):
        self.requests.append(request)
        params = request.url.params
        if request.url.path == "/api/v2/version":
            return version(self.stamps.pop(0) if len(self.stamps) > 1 else self.stamps[0])
        if "filter.ids" in params:
            asked = params["filter.ids"].split(",")
            return httpx.Response(200, json={"studies": [nct(n) for n in asked], "totalCount": len(asked)})
        if self.fail_search:
            self.fail_search -= 1
            raise httpx.ConnectError("down", request=request)
        total = len(self.text_ids) if self.total is None else self.total
        page = [{"protocolSection": {"identificationModule": {"nctId": n}}} for n in self.text_ids]
        return httpx.Response(200, json={"studies": page, "totalCount": total})

    def client(self):
        return httpx.Client(base_url=coverage_run.API_BASE, transport=httpx.MockTransport(self.serve))

    def searches(self):
        return [
            r for r in self.requests if r.url.path == "/api/v2/studies" and "filter.ids" not in r.url.params
        ]

    def diagnoses(self):
        return [r for r in self.requests if "filter.ids" in r.url.params]


def make_run(
    tmp_path, *, request=REQUEST, class_ids=CLASS_IDS, policy=None, complete=True, stamp=DATA_TIMESTAMP
):
    folder = tmp_path / "run"
    (folder / "bodies").mkdir(parents=True)
    scope = resolve_scope(request, {})
    assert scope["code"] == "resolved"
    documents = {
        "request.json": request,
        "resolution.json": scope,
        "scope.json": {
            "query": scope["query"],
            "rxnav": [],
            "acquisition": policy or {"max_studies": 1000, "max_registry_requests": 100},
        },
        "bodies/version-start.json": {"apiVersion": "2.0.5", "dataTimestamp": stamp},
        "bodies/version-end.json": {"apiVersion": "2.0.5", "dataTimestamp": stamp},
    }
    if complete:
        page = [{"protocolSection": {"identificationModule": {"nctId": n}}} for n in class_ids]
        documents["bodies/ids-001.json"] = {"studies": page, "totalCount": len(class_ids)}
    for name, document in documents.items():
        (folder / name).write_text(json.dumps(document), encoding="utf-8")
    return folder


def compare(folder, registry):
    return coverage_run.run_coverage(folder, http=registry.client(), sleep=lambda s: None)


def saved(folder):
    return json.loads((folder / "coverage.json").read_text(encoding="utf-8"))


# ── a complete comparison ───────────────────────────────────────────────────────────────────────────────


def test_equal_counts_with_different_trials_are_compared_by_identifier_and_kept_complete(tmp_path):
    folder, registry = make_run(tmp_path), Registry()
    state, words = compare(folder, registry)
    document = saved(folder)
    assert state == "complete" and document["state"] == "complete"
    assert document["class_search"]["total"] == document["text_search"]["total"] == 2
    assert document["comparison"]["class_only"] == ["NCT00000001"]
    assert document["comparison"]["text_only"] == ["NCT00000003"]
    assert document["comparison"]["intersection"] == ["NCT00000002"]
    assert "1 trial(s)" in words and "candidates for clinical review" in words
    assert document["routes"] == {
        "NCT00000001": ["class"],
        "NCT00000002": ["class", "text"],
        "NCT00000003": ["text"],
    }


def test_the_complete_record_keeps_queries_times_states_and_sources_of_both_sides(tmp_path):
    folder = make_run(tmp_path)
    compare(folder, Registry())
    document = saved(folder)
    klass, text = document["class_search"], document["text_search"]
    assert (
        klass["query"] != text["query"]
        and "query.cond" in text["query"]
        and "query.cond" not in klass["query"]
    )
    assert klass["ids"] == CLASS_IDS and text["ids"] == TEXT_IDS
    assert klass["sources"] == ["bodies/ids-001.json"] and text["sources"] == ["coverage/bodies/ids-001.json"]
    assert klass["retrieved_at"] and text["retrieved_at"] and text["retrieved_at_basis"]
    assert klass["snapshot"] == text["snapshot"] == {"api_version": "2.0.5", "data_timestamp": DATA_TIMESTAMP}
    assert document["other_filters_unchanged"] is True
    assert (folder / "coverage" / "bodies" / "ids-001.json").is_file() and (folder / "coverage.md").is_file()


def test_every_other_filter_is_identical_in_the_request_actually_sent(tmp_path):
    folder, registry = make_run(tmp_path), Registry()
    compare(folder, registry)
    sent = registry.searches()[0].url.params
    assert sent["filter.advanced"] == "AREA[Phase]PHASE3" and sent["query.cond"] == REQUEST["condition_class"]
    assert "ConditionMeshTerm" not in sent["filter.advanced"]
    assert sent["fields"] == "NCTId" and sent["pageSize"] == "1000"


def test_the_comparison_never_rewrites_the_record_or_hydrates_a_trial(tmp_path):
    folder, registry = make_run(tmp_path), Registry()
    (folder / "landscape.json").write_text("{}", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
    compare(folder, registry)
    assert (folder / "landscape.json").read_bytes() == before["landscape.json"]
    assert (folder / "scope.json").read_bytes() == before["scope.json"]
    assert not (folder / "landscape.xlsx").exists()
    fields = {r.url.params.get("fields") for r in registry.requests if r.url.path.endswith("/studies")}
    assert fields == {"NCTId", coverage.DIAGNOSIS_FIELDS}


def test_differing_records_are_read_only_for_their_condition_annotations(tmp_path):
    folder, registry = make_run(tmp_path), Registry()
    compare(folder, registry)
    trials = saved(folder)["diagnosis"]["trials"]
    assert sorted(trials) == ["NCT00000001", "NCT00000003"]
    assert trials["NCT00000003"]["annotation"] == "none" and trials["NCT00000003"]["route"] == ["text"]
    assert len(registry.diagnoses()) == 1


def test_a_union_is_only_offered_as_a_request_for_a_new_run_and_nothing_gathers_it(tmp_path):
    folder, registry = make_run(tmp_path), Registry()
    compare(folder, registry)
    union = saved(folder)["union"]
    assert union["offered"] is True and union["unique_trials"] == 3 and "NEW run" in union["words"]
    request = json.loads((folder / "coverage_union_request.json").read_text(encoding="utf-8"))
    assert request == {"params": {"filter.ids": "NCT00000001,NCT00000002,NCT00000003"}}
    assert json.loads((folder / "request.json").read_text(encoding="utf-8")) == REQUEST
    assert not (folder / "landscape.json").exists()


def test_a_comparison_with_no_text_only_trial_is_scoped_not_universal(tmp_path):
    folder = make_run(tmp_path)
    _state, words = compare(folder, Registry(text_ids=CLASS_IDS))
    assert saved(folder)["comparison"]["text_only"] == []
    assert (
        "Under these two declared searches" in words and "does not show that no other trial exists" in words
    )
    assert not saved(folder)["diagnosis"]["trials"] and saved(folder)["diagnosis"]["state"] == "not_run"


# ── empty is not failed, failed is not empty ───────────────────────────────────────────────────────────


def test_an_empty_complete_alternate_search_is_a_complete_comparison_with_every_class_trial_class_only(
    tmp_path,
):
    folder = make_run(tmp_path)
    state, _words = compare(folder, Registry(text_ids=[]))
    assert state == "complete" and saved(folder)["comparison"]["class_only"] == CLASS_IDS
    assert saved(folder)["comparison"]["text_only"] == []


def test_a_failed_alternate_search_says_failed_and_never_no_additional_trials(tmp_path):
    folder = make_run(tmp_path)
    state, words = compare(folder, Registry(fail_search=99))
    document = saved(folder)
    assert state == "failed" and document["comparison"] is None and document["routes"] == {}
    assert document["text_search"]["state"] == "failed" and document["text_search"]["ids"] == []
    assert "no statement is made" in words and "found no trial" not in words
    assert document["class_search"]["state"] == "complete" and document["class_search"]["ids"] == CLASS_IDS
    assert not (folder / "coverage_union_request.json").exists()


def test_a_failed_comparison_resumes_without_asking_what_it_already_saved(tmp_path):
    folder = make_run(tmp_path)
    first = Registry(fail_search=99)
    compare(folder, first)
    assert (folder / "coverage" / "bodies" / "version-start.json").is_file()
    second = Registry()
    state, _words = compare(folder, second)
    assert state == "complete"
    assert [r.url.path for r in second.requests].count("/api/v2/version") == 1  # only the closing /version


def test_an_alternate_search_that_stops_short_of_its_total_is_incomplete_not_a_difference(tmp_path):
    folder = make_run(tmp_path)
    state, words = compare(folder, Registry(text_ids=["NCT00000003"], total=5))
    assert state in ("incomplete", "failed") and saved(folder)["comparison"] is None
    assert "no statement is made" in words


def test_a_class_search_that_is_not_complete_asks_the_registry_nothing(tmp_path):
    folder, registry = make_run(tmp_path, complete=False), Registry()
    state, _words = compare(folder, registry)
    assert state == "incomplete" and registry.requests == []
    assert saved(folder)["text_search"]["state"] == "not_run" and saved(folder)["comparison"] is None


def test_different_registry_snapshots_make_no_comparison(tmp_path):
    folder = make_run(tmp_path)
    state, words = compare(folder, Registry(stamps=["2026-10-31T09:00:04"]))
    assert state == "snapshot_differs" and saved(folder)["comparison"] is None
    assert "different registry snapshots" in words
    assert not (folder / "coverage_union_request.json").exists()


def test_a_request_with_no_condition_class_is_not_applicable_and_asks_nothing(tmp_path):
    folder, registry = make_run(tmp_path, request={"phase": ["PHASE3"]}), Registry()
    state, detail = compare(folder, registry)
    assert (state, detail) == ("not_applicable", "no_condition_class") and registry.requests == []
    assert saved(folder)["state"] == "not_applicable"


# ── the acquisition budget, before anything is read ─────────────────────────────────────────────────────


def test_a_text_search_larger_than_the_study_budget_stops_after_its_first_page(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 2, "max_registry_requests": 100})
    registry = Registry(text_ids=TEXT_IDS, total=3)
    state, _words = compare(folder, registry)
    document = saved(folder)
    assert state == "failed" and "acquisition.study_expansion" in document["text_search"]["detail"]
    assert len(registry.searches()) == 1 and registry.diagnoses() == []
    assert document["comparison"] is None


def test_a_text_search_exactly_at_the_study_budget_is_admitted(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 2, "max_registry_requests": 100})
    state, _words = compare(folder, Registry(text_ids=TEXT_IDS))
    assert state == "complete"


def test_the_request_budget_is_decided_before_the_first_request(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 5})  # 3 spent + 3 > 5
    registry = Registry()
    state, words = compare(folder, registry)
    assert state == "failed" and registry.requests == []
    assert "acquisition_request_expansion" in saved(folder)["text_search"]["detail"]
    assert "no statement is made" in words


def test_the_request_budget_boundary_is_inclusive(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 6})
    state, _words = compare(folder, Registry(text_ids=CLASS_IDS))  # 3 spent + 3 == 6, no diagnosis needed
    assert state == "complete"


def test_a_diagnosis_beyond_the_budget_is_skipped_while_the_comparison_stays_complete(tmp_path):
    folder = make_run(tmp_path, policy={"max_studies": 1000, "max_registry_requests": 6})
    registry = Registry()
    state, _words = compare(folder, registry)
    document = saved(folder)
    assert state == "complete" and document["comparison"]["text_only"] == ["NCT00000003"]
    assert (
        document["diagnosis"]["state"] == "not_run" and "request_expansion" in document["diagnosis"]["detail"]
    )
    assert registry.diagnoses() == []


def test_the_actual_requests_added_are_recorded_against_the_plan(tmp_path):
    folder = make_run(tmp_path)
    compare(folder, Registry())
    budget = saved(folder)["budget"]
    # 2 versions, 1 page, 1 diagnosis: asked, planned and saved agree; a resume asks nothing more
    assert budget["requests_this_invocation"] == budget["added_requests"] == budget["saved_responses"] == 4
    compare(folder, Registry())
    assert (
        saved(folder)["budget"]["requests_this_invocation"] == 0
        and saved(folder)["budget"]["saved_responses"] == 4
    )
    assert budget["verdict"] == "within_budget"


# ── pure helpers of the shell ───────────────────────────────────────────────────────────────────────────


def test_a_union_too_long_for_one_request_is_not_offered_as_a_request():
    ids = [f"NCT{n:08d}" for n in range(700)]
    assert coverage_run.union_request(ids) == ("union_ids_too_long_for_one_request", None)
    assert coverage_run.union_request(ids[:3])[0] == "ok"


def test_diagnosis_batches_are_at_most_the_registry_page_and_cover_every_trial():
    ids = [f"NCT{n:08d}" for n in range(250)]
    batches = coverage_run.diagnosis_batches(ids)
    assert [len(b) for b in batches] == [100, 100, 50]
    assert [n for b in batches for n in b] == ids


@pytest.mark.parametrize(
    ("end", "expected"),
    [(DATA_TIMESTAMP, True), ("2026-10-31T00:00:00", False)],
)
def test_same_snapshot_needs_every_end_to_agree(end, expected):
    snap = {"api_version": "2.0.5", "data_timestamp": DATA_TIMESTAMP}
    other = {"api_version": "2.0.5", "data_timestamp": end}
    assert (
        coverage_run.same_snapshot(
            {"snapshot": snap, "snapshot_end": snap}, {"snapshot": snap, "snapshot_end": other}
        )
        is expected
    )
    assert (
        coverage_run.same_snapshot(
            {"snapshot": snap, "snapshot_end": None}, {"snapshot": snap, "snapshot_end": snap}
        )
        is None
    )
