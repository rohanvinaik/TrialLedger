"""Search coverage: pure decisions (TrialLedger/coverage.py) and their carriers in the request and preview."""

import json
from pathlib import Path

import pytest

from TrialLedger import coverage
from TrialLedger.ingest import check_query
from TrialLedger.preview import scope_words
from TrialLedger.readout import coverage_search_words
from TrialLedger.request import RXNORM_IDS, lookup_url, request_problems, resolve_scope

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
PD1_IN_LUNG = DOC["requests"][0]
CLASS_ONLY = {"condition_class": "Carcinoma, Non-Small-Cell Lung"}
FILTERED = {**CLASS_ONLY, "phase": ["PHASE3"], "status": ["COMPLETED"], "start_from": "2020-01-01"}
POLICY = {"max_studies": 100, "max_registry_requests": 10}


def scope_of(request):
    scope = resolve_scope(request, {})
    assert scope["code"] == "resolved"
    return scope


# ── the alternate query: only the condition route changes ────────────────────────────────────────────────


def test_alternate_query_replaces_only_the_class_clause_and_keeps_every_other_filter():
    scope = scope_of(FILTERED)
    code, alternate = coverage.alternate_query(scope)
    assert code == "ok"
    assert alternate["query.cond"] == "Carcinoma, Non-Small-Cell Lung"
    assert alternate["filter.advanced"] == (
        "AREA[Phase]PHASE3 AND AREA[OverallStatus]COMPLETED AND AREA[StartDate]RANGE[2020-01-01,MAX]"
    )
    assert coverage.unchanged_filters(scope["query"], alternate)
    assert check_query(alternate)[0] == "ok"


def test_alternate_query_must_not_keep_a_mesh_clause_or_drop_a_filter():
    _code, alternate = coverage.alternate_query(scope_of(FILTERED))
    assert "ConditionMeshTerm" not in json.dumps(alternate) and "ConditionAncestorTerm" not in json.dumps(
        alternate
    )
    for clause in (
        "AREA[Phase]PHASE3",
        "AREA[OverallStatus]COMPLETED",
        "AREA[StartDate]RANGE[2020-01-01,MAX]",
    ):
        assert clause in alternate["filter.advanced"]


def test_alternate_query_of_a_class_alone_is_the_text_search_alone():
    assert coverage.alternate_query(scope_of(CLASS_ONLY)) == (
        "ok",
        {"query.cond": "Carcinoma, Non-Small-Cell Lung"},
    )


def test_alternate_query_carries_unrelated_raw_parameters_unchanged():
    request = {**CLASS_ONLY, "params": {"sort": "LastUpdatePostDate"}}
    if request_problems(request)[0] != "ok":
        pytest.skip("this registry parameter is not admitted")
    code, alternate = coverage.alternate_query(scope_of(request))
    assert code == "ok" and alternate["sort"] == "LastUpdatePostDate"


@pytest.mark.parametrize(
    ("request_", "code"),
    [
        ({"phase": ["PHASE3"]}, "no_condition_class"),
        ({**CLASS_ONLY, "condition": "NSCLC"}, "condition_text_also_requested"),
    ],
)
def test_alternate_query_names_why_no_comparison_applies(request_, code):
    assert coverage.alternate_query(scope_of(request_)) == (code, {})


def test_alternate_query_refuses_an_unresolved_scope_and_a_query_it_cannot_reproduce():
    assert coverage.alternate_query(resolve_scope(PD1_IN_LUNG, {})) == ("scope_unresolved", {})
    scope = scope_of(FILTERED)
    scope["query"] = {
        "filter.advanced": scope["query"]["filter.advanced"] + " AND AREA[StudyType]INTERVENTIONAL"
    }
    assert coverage.alternate_query(scope) == ("query_not_reproducible", {})
    assert coverage.alternate_query("nonsense") == ("scope_unresolved", {})


def test_unchanged_filters_is_false_when_another_parameter_differs():
    scope = scope_of(FILTERED)
    _code, alternate = coverage.alternate_query(scope)
    assert not coverage.unchanged_filters(scope["query"], alternate | {"sort": "x"})
    assert not coverage.unchanged_filters(scope["query"], scope["query"])


# ── identifier sets: counts alone establish nothing ──────────────────────────────────────────────────────


def test_equal_counts_with_different_sets_are_a_difference():
    both = coverage.compare_id_sets(["NCT1", "NCT2"], ["NCT2", "NCT3"])
    assert both["class_unique"] == both["text_unique"] == 2
    assert both["class_only"] == ["NCT1"] and both["text_only"] == ["NCT3"]
    assert both["intersection"] == ["NCT2"]


def test_equal_sets_have_no_difference_and_no_class_only():
    same = coverage.compare_id_sets(["NCT2", "NCT1"], ["NCT1", "NCT2"])
    assert same["class_only"] == [] and same["text_only"] == []
    assert same["intersection"] == ["NCT1", "NCT2"]


def test_a_repeated_identifier_is_one_trial_and_the_repeat_is_counted():
    result = coverage.compare_id_sets(["NCT1", "NCT1", "NCT2"], ["NCT2", "NCT2"])
    assert result["class_unique"] == 2 and result["class_repeats_dropped"] == 1
    assert result["text_unique"] == 1 and result["text_repeats_dropped"] == 1
    assert result["class_only"] == ["NCT1"]


def test_routes_keep_query_specific_membership_when_the_sets_are_merged():
    held = coverage.routes(["NCT1", "NCT2", "NCT2"], ["NCT2", "NCT3", "NCT3"])
    assert held == {"NCT1": ["class"], "NCT2": ["class", "text"], "NCT3": ["text"]}
    assert list(held) == ["NCT1", "NCT2", "NCT3"]


# ── states: an incomplete comparison is never "no additional trials" ─────────────────────────────────────

DONE = {"state": "complete"}


@pytest.mark.parametrize(
    ("klass", "text", "same", "state"),
    [
        (DONE, DONE, True, "complete"),
        (DONE, {"state": "not_run"}, True, "not_run"),
        (DONE, {"state": "failed"}, True, "failed"),
        (DONE, {"state": "incomplete"}, True, "incomplete"),
        ({"state": "incomplete"}, DONE, True, "incomplete"),
        ({"state": "incomplete"}, {"state": "not_run"}, True, "incomplete"),
        (DONE, DONE, False, "snapshot_differs"),
        (DONE, DONE, None, "snapshot_differs"),
    ],
)
def test_comparison_state_is_complete_only_when_both_sides_are_complete_from_one_snapshot(
    klass, text, same, state
):
    assert coverage.comparison_state(klass, text, same) == state


def test_a_failed_alternate_search_with_no_ids_is_not_an_empty_difference():
    state = coverage.comparison_state(DONE, {"state": "failed", "ids": []}, True)
    words = coverage.difference_words(state, None)
    assert state == "failed" and "no statement is made" in words
    assert "found no trial" not in words and "no additional" not in words.lower()


@pytest.mark.parametrize("state", ["not_run", "failed", "incomplete", "snapshot_differs"])
def test_no_state_but_complete_says_anything_about_missed_trials(state):
    words = coverage.difference_words(state, coverage.compare_id_sets(["NCT1"], ["NCT1"]))
    assert words.startswith("Comparison incomplete") and "no statement is made" in words
    assert "found no trial" not in words


def test_a_complete_empty_difference_is_scoped_to_the_two_declared_searches():
    words = coverage.difference_words("complete", coverage.compare_id_sets(["NCT1"], ["NCT1"]))
    assert (
        "Under these two declared searches" in words and "does not show that no other trial exists" in words
    )


def test_a_complete_difference_calls_the_extra_trials_candidates_not_members():
    words = coverage.difference_words("complete", coverage.compare_id_sets(["NCT1"], ["NCT1", "NCT2"]))
    assert "1 trial(s)" in words and "candidates for clinical review" in words
    assert "not established disease membership or comparator suitability" in words


def test_not_applicable_is_its_own_statement():
    assert "no condition class" in coverage.difference_words("not_applicable", None)


# ── the budget: the boundaries are admissible, one past is a named stop ──────────────────────────────────


def budget(**kw):
    values = {"policy": POLICY, "class_total": 10, "text_total": 10, "spent_requests": 4} | kw
    return coverage.comparison_budget(
        values["policy"],
        values["class_total"],
        values["text_total"],
        values["spent_requests"],
        diagnosed=values.get("diagnosed", 0),
    )


def test_budget_adds_two_versions_and_the_id_pages_to_the_requests_spent():
    plan = budget()
    assert (plan["added_requests"], plan["planned_requests"], plan["verdict"]) == (3, 7, "within_budget")


def test_budget_study_boundary_is_inclusive_and_one_past_is_a_study_expansion():
    assert budget(text_total=100)["verdict"] == "within_budget"
    assert budget(text_total=101)["verdict"] == "study_expansion"
    assert budget(class_total=101, text_total=3)["verdict"] == "study_expansion"


def test_budget_request_boundary_is_inclusive_and_one_past_is_a_request_expansion():
    assert budget(spent_requests=7)["verdict"] == "within_budget"  # 7 + 3 == 10
    assert budget(spent_requests=8)["verdict"] == "request_expansion"


def test_budget_counts_id_pages_of_a_large_text_total_and_the_diagnosis_batches():
    big = {"max_studies": 5000, "max_registry_requests": 100}
    assert budget(policy=big, class_total=10, text_total=2500)["added_requests"] == 2 + 3
    assert budget(diagnosed=100)["added_requests"] == 3 + 1
    assert budget(diagnosed=101)["added_requests"] == 3 + 2
    assert budget(spent_requests=6, diagnosed=101)["verdict"] == "request_expansion"  # 6 + 5 > 10


def test_budget_before_the_first_page_checks_requests_only():
    plan = coverage.comparison_budget(POLICY, 10, None, 8)
    assert plan["verdict"] == "request_expansion"
    assert coverage.comparison_budget(POLICY, 10_000, None, 4)["verdict"] == "within_budget"


# ── a record's own annotations, never a guess ───────────────────────────────────────────────────────────


def study(meshes=(), ancestors=(), derived=True):
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT1", "briefTitle": "T"},
            "conditionsModule": {"conditions": ["NSCLC"], "keywords": ["k"]},
        }
    }
    if derived:
        record["derivedSection"] = {
            "conditionBrowseModule": {
                "meshes": [{"term": t} for t in meshes],
                "ancestors": [{"term": t} for t in ancestors],
            }
        }
    else:
        record["derivedSection"] = {}
    return record


def test_a_record_without_condition_annotations_reads_none_not_absent_disease():
    for record in (study(derived=False), study()):
        reading = coverage.annotation_reading(record, "Carcinoma, Non-Small-Cell Lung")
        assert reading["annotation"] == "none" and reading["conditions"] == ["NSCLC"]


def test_annotations_under_the_class_or_other_are_distinguished_case_insensitively():
    term = "Carcinoma, Non-Small-Cell Lung"
    assert (
        coverage.annotation_reading(study(meshes=["Lung Neoplasms"], ancestors=[term.lower()]), term)[
            "annotation"
        ]
        == "under_class"
    )
    assert coverage.annotation_reading(study(meshes=["Lung Neoplasms"]), term)["annotation"] == "other"


def test_an_unreadable_record_is_unreadable():
    assert coverage.annotation_reading(None, "x") == {"annotation": "unreadable"}


# ── the statements the scope carries ────────────────────────────────────────────────────────────────────


def test_a_class_search_scope_states_the_boundary_and_that_mesh_less_records_cannot_match():
    held = scope_of(CLASS_ONLY)["coverage"]
    assert held["boundary"] == coverage.BOUNDARY
    assert (
        held["condition"]["slot"] == "condition_class"
        and "no condition MeSH annotation" in held["condition"]["limit"]
    )
    assert "drug_catalogue" not in held


def test_a_condition_text_search_scope_names_its_own_route_and_no_mesh_limit():
    held = scope_of({"condition": "asthma"})["coverage"]
    assert held["condition"]["slot"] == "condition" and "limit" not in held["condition"]


def test_a_scope_with_no_condition_still_states_the_boundary_only():
    assert set(scope_of({"phase": ["PHASE3"]})["coverage"]) == {"boundary"}


def test_catalogue_statement_keeps_members_release_and_the_limit():
    scope = resolve_scope(PD1_IN_LUNG, ANSWERS)
    held = scope["coverage"]["drug_catalogue"]
    assert scope["code"] == "resolved" and held["release"] == scope["release"][1] != ""
    assert "pembrolizumab" in held["members_returned"] and held["additions"] == []
    assert "does not establish that every clinically relevant drug is included" in held["limit"]


# ── a person's additions: searched, attributed, never RxNav's ───────────────────────────────────────────

ADDED = {**PD1_IN_LUNG, "class_drug_additions": ["zzznovel"]}
UNHELD = {
    lookup_url(RXNORM_IDS, {"name": "zzznovel", "search": "0"}): [200, {"idGroup": {"name": "zzznovel"}}]
}


def test_additions_need_a_class_to_extend():
    assert request_problems({"class_drug_additions": ["x"], "phase": ["PHASE3"]}) == (
        "malformed_value",
        ["class_drug_additions"],
    )
    assert request_problems({"class_drug_additions": [], **PD1_IN_LUNG})[0] == "malformed_value"
    assert request_problems({"class_drug_additions": ['a"b'], **PD1_IN_LUNG})[0] == "malformed_value"
    assert request_problems(ADDED) == ("ok", [])


def test_an_addition_is_searched_beside_the_members_and_attributed_to_the_person():
    scope = resolve_scope(ADDED, ANSWERS | UNHELD)
    assert scope["code"] == "resolved"
    assert (
        '"zzznovel"' in scope["query"]["filter.advanced"]
        and '"pembrolizumab"' in scope["query"]["filter.advanced"]
    )
    added = [e for e in scope["expansions"] if e.get("source_origin") == coverage.ADDITION_ORIGIN]
    assert [e["drug"] for e in added] == ["zzznovel"] and added[0]["code"] == "not_in_rxnorm"
    held = scope["coverage"]["drug_catalogue"]
    assert (
        held["additions"][0]["name"] == "zzznovel" and held["additions"][0]["also_listed_by_rxnav"] is False
    )
    assert "zzznovel" not in held["members_returned"]


def test_an_addition_must_not_be_reported_as_an_rxnav_member_in_words():
    words = scope_words(resolve_scope(ADDED, ANSWERS | UNHELD))
    assert any(line.startswith("  Added by the person, not supplied by RxNav: zzznovel") for line in words)
    assert not any("zzznovel" in line and "as the class lists it" in line for line in words)
    members = [line for line in words if line.startswith("    ") and "as the class lists it" in line]
    assert members and all("zzznovel" not in line for line in members)


def test_an_addition_awaits_its_own_lookup_before_the_scope_resolves():
    scope = resolve_scope(ADDED, ANSWERS)
    assert scope["code"] == "awaiting_lookups"
    assert any("zzznovel" in url for url in scope["pending"])


def test_an_addition_rxnav_also_lists_is_marked_and_searched_once():
    held = {
        lookup_url(RXNORM_IDS, {"name": "pembrolizumab", "search": "0"}): [200, {"idGroup": {"name": "x"}}]
    }
    scope = resolve_scope({**PD1_IN_LUNG, "class_drug_additions": ["pembrolizumab"]}, ANSWERS | held)
    assert scope["code"] == "resolved"
    assert scope["coverage"]["drug_catalogue"]["additions"][0]["also_listed_by_rxnav"] is True
    assert scope["query"]["filter.advanced"].count('"pembrolizumab"') == 2  # name and other name, once each


# ── words in the preview and the workbook ───────────────────────────────────────────────────────────────


def test_preview_states_the_boundary_the_mesh_limit_and_the_unrun_alternate_without_codes():
    words = scope_words(scope_of(FILTERED))
    text = "\n".join(words)
    assert "Coverage boundary: A completed retrieval means the declared search finished" in text
    assert "cannot match this search whatever its condition text says" in text
    assert "Not run: the same search with the disease class replaced" in text
    assert not [line for line in words[:-1] if "PHASE3" in line]
    assert words[-2] == "The exact search sent to the registry:"


def test_preview_of_a_search_with_no_condition_class_offers_no_comparison():
    text = "\n".join(scope_words(scope_of({"phase": ["PHASE3"]})))
    assert "Coverage boundary" in text and "Not run: the same search" not in text


def test_workbook_words_add_the_boundary_only_when_the_scope_carries_it():
    request = FILTERED
    old = {"request": request, "scope": {"code": "resolved"}}
    new = {"request": request, "scope": scope_of(request)}
    assert "Coverage boundary" not in coverage_search_words(old)
    words = coverage_search_words(new)
    assert words.startswith(coverage_search_words(old)) and "Coverage boundary" in words
    assert "different search" in words


def test_coverage_words_of_nothing_are_nothing():
    assert coverage.coverage_words(None) == [] and coverage.coverage_words({}) == []
