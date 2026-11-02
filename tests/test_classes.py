"""NLM source parsing, exact lookup requests, cache preservation and source warrants.

A failed or absent source answer never becomes a negative clinical finding. Identity and alias
interpretation are covered independently in test_identity_evidence.py.
"""

import json
from datetime import datetime, timedelta

import pytest
from rxnav_fake import FakeRxNav

from TrialLedger.classes import (
    RXCLASS_BY_RXCUI,
    RXNAV_VERSION,
    RXNORM_IDS,
    _ask_rxnav,
    drug_names,
    experimental_drugs,
    load_or_lookup_at,
    rxclass_classes,
)

PEMBRO = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "rxclassMinConceptItem": {
                    "classId": "N0000191260",
                    "className": "Programmed Death Receptor-1 Blocking Antibody",
                },
                "rela": "has_epc",
                "relaSource": "DAILYMED",
            }
        ]
        * 2
    }
}
PEMBRO_CLASS = ("N0000191260", "Programmed Death Receptor-1 Blocking Antibody", "has_epc", "DAILYMED")


def test_a_classified_name_gives_its_classes_once():
    assert rxclass_classes(200, PEMBRO) == ("found", [PEMBRO_CLASS])


@pytest.mark.parametrize(
    "status, body, code",
    [
        (200, {}, "not_found"),
        (200, [], "malformed"),
        (200, {"rxclassDrugInfoList": {"rxclassDrugInfo": []}}, "malformed"),
        (
            200,
            {"rxclassDrugInfoList": {"rxclassDrugInfo": [{"rxclassMinConceptItem": {"classId": 1}}]}},
            "malformed",
        ),
        (200, {"rxclassDrugInfoList": {"rxclassDrugInfo": ["x"]}}, "malformed"),
        (503, PEMBRO, "lookup_failed"),
        (0, None, "lookup_failed"),
    ],
)
def test_no_class_has_a_named_reason(status, body, code):
    assert rxclass_classes(status, body) == (code, [])


# RxNav's own answer to version.json (read live 2026-11-01)
VERSION = {"version": "05-Oct-2026", "apiVersion": "3.1.356"}
PEMBRO_RXCUI = "1547545"
# RxNorm holds pembrolizumab and its brand Keytruda; RxClass answers either about pembrolizumab (2026-11-01)
RXNAV = {
    "names": {"Pembrolizumab": [PEMBRO_RXCUI], "Keytruda": ["1547550"]},
    "concepts": {PEMBRO_RXCUI: ("pembrolizumab", "IN"), "1547550": ("Keytruda", "BN")},
    "classes": {
        rxcui: [(*PEMBRO_CLASS[:2], "EPC", "has_epc", "DAILYMED", PEMBRO_RXCUI)]
        for rxcui in (PEMBRO_RXCUI, "1547550")
    },
}


def lookup(names, **fake):
    get = FakeRxNav(**(RXNAV | fake))
    answers = _ask_rxnav(
        list(dict.fromkeys(names)),
        set(),
        get=get,
        sleep=lambda _: None,
        monotonic=lambda: 0.0,
        progress=lambda _: None,
    )
    return answers, get


def test_lookup_asks_identity_then_classes_once_per_concept():
    answers, get = lookup(["Pembrolizumab", "SCT-I10A", "Pembrolizumab"])
    asked = [(url, params.get("name") or params.get("rxcui", "")) for url, params in get.asked]
    assert asked == [
        (RXNAV_VERSION, ""),
        (RXNORM_IDS, "Pembrolizumab"),
        (RXNORM_IDS, "SCT-I10A"),
        (RXCLASS_BY_RXCUI, PEMBRO_RXCUI),
        (RXNAV_VERSION, ""),
    ]
    assert answers["Pembrolizumab"]["classes"] == [PEMBRO_CLASS]
    assert answers["Pembrolizumab"]["codes"] == {"DAILYMED:has_epc": "found", "MEDRT:has_moa": "not_found"}
    # a name RxNorm does not hold is never asked of RxClass, and says why: never "no class" from RxClass
    assert answers["SCT-I10A"]["codes"] == {
        "DAILYMED:has_epc": "not_in_rxnorm",
        "MEDRT:has_moa": "not_in_rxnorm",
    }
    # each answer carries its own retrieval time, an ISO timestamp in UTC, whatever its code
    for answer in answers.values():
        assert datetime.fromisoformat(answer["retrieved"]).utcoffset() == timedelta(0)


def test_each_answer_carries_its_requests_and_the_releases_of_its_batch():
    """Positive (add-scoped-reasoning 1.2): each answer keeps the requests that decided it, each URL with its
    parameters and retrieval time, and the RxNav release its batch was read under, asked before its first
    request and again after its last. Negative: a release RxNav did not give (a failure, a malformed body) is
    named, never filled in; no name asks nothing."""
    answers, get = lookup(["Pembrolizumab", "Keytruda"])
    assert get.count(RXNAV_VERSION) == 2
    assert get.asked[0][0] == RXNAV_VERSION and get.asked[-1][0] == RXNAV_VERSION
    answer = answers["Keytruda"]
    assert [(r["url"], r["params"]) for r in answer["requests"]] == [
        (RXNORM_IDS, {"name": "Keytruda", "search": "0"}),
        (RXCLASS_BY_RXCUI, {"rxcui": "1547550"}),
    ]
    for request in answer["requests"]:
        assert datetime.fromisoformat(request["retrieved"]).utcoffset() == timedelta(0)
    code, release, version_request = answer["release"]
    assert (code, release, version_request["url"], version_request["params"]) == (
        "found",
        "05-Oct-2026",
        RXNAV_VERSION,
        {},
    )
    assert answer["release_end"][:2] == ["found", "05-Oct-2026"]
    assert answers["Pembrolizumab"]["release"] == answer["release"]
    failed, _ = lookup(["X"], failing={RXNAV_VERSION})
    assert failed["X"]["release"][:2] == ["lookup_failed", ""]
    odd, _ = lookup(["X"], release={"apiVersion": "3.1.356"})
    assert odd["X"]["release"][:2] == ["malformed", ""]


STUDY = {
    "protocolSection": {
        "armsInterventionsModule": {
            "armGroups": [
                {"type": "EXPERIMENTAL", "interventionNames": ["Biological: SHR-1316", "Drug: Carboplatin"]},
                {"type": "PLACEBO_COMPARATOR", "interventionNames": ["Drug: Placebo", "Drug: Carboplatin"]},
            ],
            "interventions": [
                {"type": "BIOLOGICAL", "name": "SHR-1316", "otherNames": ["adebrelimab"]},
                {"type": "DRUG", "name": "Carboplatin"},
                {"type": "DRUG", "name": "Placebo"},
                {"type": "PROCEDURE", "name": "Surgery"},
            ],
        }
    }
}


def test_drug_names_and_experimental_drugs_follow_the_record():
    assert drug_names(STUDY) == {
        "SHR-1316": ["SHR-1316", "adebrelimab"],
        "Carboplatin": ["Carboplatin"],
        "Placebo": ["Placebo"],
    }
    assert experimental_drugs(STUDY) == ["SHR-1316", "Carboplatin"]


def test_each_answer_keeps_its_own_retrieval_time(tmp_path):
    """Positive: a name looked up now is cached with its own retrieval time. Negative: an answer cached before
    answers carried one keeps none, never back-dated from the cache's last extension."""
    path = tmp_path / "classes.json"
    legacy = {"codes": {"DAILYMED:has_epc": "not_found", "MEDRT:has_moa": "not_found"}, "classes": []}
    path.write_text(json.dumps({"retrieved": "2026-01-01T00:00:00+00:00", "answers": {"Old": legacy}}))
    get = FakeRxNav(names={}, concepts={})
    load_or_lookup_at(path, ["Old", "New"], get=get, sleep=lambda _: None)
    kept = json.loads(path.read_text())["answers"]
    assert "retrieved" not in kept["Old"]
    assert datetime.fromisoformat(kept["New"]["retrieved"]).utcoffset() == timedelta(0)
