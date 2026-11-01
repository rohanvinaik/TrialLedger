"""request against the real RxNav and ClinicalTrials.gov. Opt-in: `uv run pytest -m live`.

Positive: each registry form request.py emits beyond sample.py's (request.NEW_FORMS), asked as recorded in
tests/request_query_forms.json, still returns trials, fewer than the whole registry (the area filters), names
grouped inside an area among them, which the registry still answers as it answers them one by one; a drug
class in a disease, resolved round by round through the URLs request.lookups_needed names, gives a query the
registry answers with trials; a class with subclasses lists each, attributes each member reached through one,
and with its subclasses excluded resolves to a query the registry answers with fewer trials.
Negative: an unknown status value is still refused with HTTP 400 and a name no trial holds returns none, as
an intervention's name, as an other name and grouped (the recorded controls), so an area the registry ignored
would fail; a class RxClass does not hold stops the scope by name; a class whose query would be longer than
the registry answers is named query_too_long, never sent.
"""

import json
import time
from pathlib import Path

import httpx
import pytest

from TrialLedger.ingest import API_BASE
from TrialLedger.request import NEW_FORMS, lookups_needed, resolve_scope

pytestmark = pytest.mark.live
FORMS = json.loads((Path(__file__).parent / "request_query_forms.json").read_text(encoding="utf-8"))
KINASE = {"name": "Kinase Inhibitor", "source": "EPC"}


def count(query: dict[str, str]) -> tuple[int, int | None]:
    """The registry's status and totalCount for one query, one ID a page."""
    params = query | {"countTotal": "true", "pageSize": "1", "fields": "NCTId"}
    response = httpx.get(f"{API_BASE}/studies", params=params, timeout=60)
    time.sleep(1.5)
    body = response.json() if response.status_code == 200 else {}
    return response.status_code, body.get("totalCount")


def answer(url: str) -> list:
    """One RxNav answer as resolution reads it: [status, body], a body that is not JSON None, no response at
    all [0, None] (as classes.http_get)."""
    try:
        response = httpx.get(url, timeout=60)
    except httpx.HTTPError:
        return [0, None]
    try:
        return [response.status_code, response.json()]
    except ValueError:
        return [response.status_code, None]


def resolved(request: dict) -> dict:
    """The request's scope, its RxNav answers fetched round by round as lookups_needed names them."""
    answers: dict[str, list] = {}
    while needed := lookups_needed(request, answers):
        for url in needed:
            answers[url] = answer(url)
            time.sleep(0.3)
    return resolve_scope(request, answers)


def test_every_new_form_still_returns_trials_and_filters():
    status, everything = count({})
    assert status == 200 and everything
    for form in NEW_FORMS:
        status, total = count({"filter.advanced": FORMS["forms"][form]["query"]})
        assert status == 200 and total and 0 < total < everything, form
    for control in (
        "a name no trial holds",
        "a name no trial holds, as an other name",
        "names no trial holds, grouped",
    ):
        assert count({"filter.advanced": FORMS["also"][control]["query"]}) == (200, 0), control
    assert count({"filter.advanced": FORMS["also"]["unknown status value"]["query"]})[0] == 400


def test_names_grouped_in_an_area_are_answered_as_one_by_one():
    pair = FORMS["also"]["two names grouped and one by one"]
    assert count({"filter.advanced": pair["grouped"]["query"]}) == count(
        {"filter.advanced": pair["one by one"]["query"]}
    )
    assert count({"filter.advanced": pair["name or other name, grouped"]["query"]}) == count(
        {"filter.advanced": pair["name or other name, one by one"]["query"]}
    )


def test_a_drug_class_in_a_disease_resolves_to_a_query_the_registry_answers():
    scope = resolved(
        {
            "drug_class": {"name": "Programmed Death Receptor-1 Blocking Antibody", "source": "EPC"},
            "condition_class": "Lung Neoplasms",
            "phase": ["PHASE3"],
            "status": ["RECRUITING"],
            "study_type": "INTERVENTIONAL",
            "start_from": "2015-01-01",
        }
    )
    assert scope["code"] == "resolved" and scope["release"][0] == "found"
    status, total = count(scope["query"])
    assert status == 200 and total and total > 0


def test_a_class_with_subclasses_is_attributed_and_its_subclasses_can_be_excluded():
    scope = resolved({"drug_class": KINASE})
    assert scope["code"] == "resolved"
    attribution = next(e for e in scope["expansions"] if e["kind"] == "subclass_attribution")
    assert "Janus Kinase Inhibitor" in [row[1] for row in attribution["subclasses"]]
    via = {row[1]: [name for _, name in row[4]] for row in attribution["members"]}
    assert via["trastuzumab"] == ["HER2/neu Receptor Antagonist"]
    excluded = resolved({"drug_class": KINASE | {"subclasses": "exclude"}})
    assert excluded["code"] == "resolved"
    status, total = count(scope["query"])
    status_excluded, total_excluded = count(excluded["query"])
    assert status == status_excluded == 200 and 0 < total_excluded < total


def test_an_unknown_class_and_an_overlong_query_stop_by_name():
    assert resolved({"drug_class": {"name": "No Such Class Zzq", "source": "EPC"}})["stops"] == [
        ["drug_class", "class_not_found", []]
    ]
    scope = resolved({"drug_class": {"name": "Kinase Inhibitors", "source": "MoA"}})
    assert scope["code"] == "unresolved" and scope["stops"][0][:2] == ["query", "query_too_long"]
