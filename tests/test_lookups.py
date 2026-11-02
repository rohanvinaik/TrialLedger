"""Exact RxNorm names, source identities, bounded transport and reproducible lookup evidence.

A name containing a dose, schedule, placebo or combination remains the literal query.
A matched shortened stem is never evidence of the recorded product identity.
"""

import json
import threading
import time

import pytest
from rxnav_fake import FakeRxNav

from TrialLedger import classes as rx
from TrialLedger.classes import (
    IN_FLIGHT,
    RATE,
    ask_all,
    batch_releases,
    class_route,
    load_or_lookup_at,
    pace,
    relation_body,
)

CAT = {"names": {"CAT-8015": ["999001"]}, "concepts": {"999001": ("moxetumomab", "IN")}}


def run(tmp_path, asked, axes=(), **fake):
    get = FakeRxNav(**({"names": {}, "concepts": {}} | fake))
    answers = load_or_lookup_at(
        tmp_path / "classes.json", asked, axes, fill_axes=bool(axes), get=get, sleep=lambda s: None
    )
    return answers, get


CARBOPLATIN = {
    "names": {"Carboplatin": ["40048"], "CBDCA": ["40048"], "Paraplatin": ["152200"], "JM-8": []},
    "concepts": {"40048": ("carboplatin", "IN"), "152200": ("Paraplatin", "BN")},
    "ingredients": {"152200": ["40048"]},
    "classes": {
        rxcui: [
            ("N0000175413", "Platinum-based Drug", "EPC", "has_epc", "DAILYMED", "40048"),
            ("N0000175413", "Platinum-based Drug", "EPC", "has_epc", "FDASPL", "40048"),
            ("N0000000233", "Cross-Linking Activity", "MOA", "has_moa", "MEDRT", "40048"),
            ("L01XA", "Platinum compounds", "ATC1-4", "", "ATC", "40048"),
            ("L01XA", "Platinum compounds", "ATC1-4", "", "ATCPROD", "40048"),
            (
                "N0000175073",
                "Platinum-containing Compounds",
                "CHEM",
                "has_chemical_structure",
                "FDASPL",
                "40048",
            ),
            ("D016190", "Carboplatin", "CHEM", "has_ingredient", "MEDRT", "40048"),
        ]
        for rxcui in ("40048", "152200")
    },
}


def test_each_concept_is_classed_once_and_read_for_every_query_and_axis(tmp_path):
    names = ["Carboplatin", "CBDCA", "Paraplatin", "JM-8"]
    answers, get = run(tmp_path, names, names, **CARBOPLATIN)
    assert sorted(p["rxcui"] for url, p in get.asked if url == rx.RXCLASS_BY_RXCUI) == ["152200", "40048"]
    # one request about carboplatin's concept, read for CBDCA too
    assert answers["CBDCA"]["requests"][1] == answers["Carboplatin"]["requests"][1]
    assert answers["CBDCA"]["classes"] == [
        ["N0000000233", "Cross-Linking Activity", "has_moa", "MEDRT"],
        ["N0000175413", "Platinum-based Drug", "has_epc", "DAILYMED"],
    ]
    axes = answers["Paraplatin"]["axes"]
    assert [a[0] for a in axes["ATC"]["assertions"]] == ["L01XA"]  # ATCPROD is not ATC
    assert axes["DAILYMED:has_chemical_structure"]["code"] == "not_found"
    assert [a[4] for a in axes["FDASPL:has_chemical_structure"]["assertions"]] == ["FDASPL"]
    assert axes["identity"]["ingredients"] == ["found", [["40048", "carboplatin", "IN"]]]
    # a name RxNorm does not hold is never asked of RxClass, and says so for every query and axis
    assert answers["JM-8"]["codes"] == {"DAILYMED:has_epc": "not_in_rxnorm", "MEDRT:has_moa": "not_in_rxnorm"}
    assert answers["JM-8"]["axes"]["ATC"] == {
        "code": "not_in_rxnorm",
        "assertions": [],
        "request": answers["JM-8"]["requests"][0],
        "release": answers["JM-8"]["release"],
    }
    evidence = rx.class_evidence(["JM-8"], answers)
    assert evidence["state"] == "unresolved" and evidence["classes"] == []
    assert evidence["reason"] == "own_identity_not_in_rxnorm"


def test_a_name_of_several_concepts_is_never_classed_and_a_failure_is_never_no_class(tmp_path):
    fake = {
        "names": {"Ambiguous": ["1", "2"], "Flaky": ["3"]},
        "concepts": {"1": ("a", "IN"), "2": ("b", "IN"), "3": ("c", "IN")},
        "failing": {"3"},
    }
    answers, get = run(tmp_path, ["Ambiguous", "Flaky"], ["Ambiguous", "Flaky"], **fake)
    assert set(answers["Ambiguous"]["codes"].values()) == {"ambiguous_in_rxnorm"}
    assert [p["rxcui"] for url, p in get.asked if url == rx.RXCLASS_BY_RXCUI] == ["3"]
    evidence = rx.class_evidence(["Flaky"], answers)
    assert evidence["state"] == "lookup_failed" and evidence["classes"] == []
    assert evidence["reason"] == "own_identity_lookup_failed"
    kept = json.loads((tmp_path / "classes.json").read_text())["answers"]
    # both are kept as answered, the failure as a failure, so the same run read again reads the same
    assert set(kept["Ambiguous"]["codes"].values()) == {"ambiguous_in_rxnorm"}
    assert set(kept["Flaky"]["codes"].values()) == {"lookup_failed"}


def test_a_negative_answer_is_cached_and_never_asked_again(tmp_path):
    answers, _ = run(
        tmp_path,
        ["Almonertinib", "Placebo"],
        names={"Placebo": ["8375"]},
        concepts={"8375": ("placebo", "IN")},
    )
    assert set(answers["Almonertinib"]["codes"].values()) == {"not_in_rxnorm"}
    assert set(answers["Placebo"]["codes"].values()) == {"not_found"}
    again = FakeRxNav(names={}, concepts={})
    load_or_lookup_at(tmp_path / "classes.json", ["Almonertinib", "Placebo"], get=again, sleep=lambda s: None)
    assert again.asked == []


def test_a_batch_whose_release_changed_is_never_cached(tmp_path):
    releases = [{"version": "05-Oct-2026"}, {"version": "02-Nov-2026"}]
    answers, get = run(tmp_path, ["Carboplatin"], release=releases, **CARBOPLATIN)
    assert get.asked[0][0] == rx.RXNAV_VERSION and get.asked[-1][0] == rx.RXNAV_VERSION
    assert batch_releases(answers) == [(("found", "05-Oct-2026"), ("found", "02-Nov-2026"))]
    assert answers["Carboplatin"]["classes"]  # the run's answers, for its caller to refuse
    assert not (tmp_path / "classes.json").exists()


def test_the_answers_do_not_depend_on_the_order_replies_arrive(tmp_path, monkeypatch):
    """Positive: replies arriving in reverse order give the same answers, and the same classes.json bytes,
    as replies arriving in order. Negative: no reply is matched to another request."""
    monkeypatch.setattr(rx, "_now", lambda: "2026-11-02T00:00:00+00:00")
    names = ["Carboplatin", "CBDCA", "Paraplatin", "JM-8", *[f"X-{n}" for n in range(12)]]

    def cached(folder, delay):
        fake = FakeRxNav(**CARBOPLATIN)

        def get(url, params):
            # a later request answers sooner: the replies arrive in reverse order
            time.sleep(delay(len(fake.asked)))
            return fake(url, params)

        folder.mkdir()
        answers = load_or_lookup_at(
            folder / "classes.json", names, names, fill_axes=True, get=get, sleep=lambda s: None
        )
        return answers, (folder / "classes.json").read_bytes()

    ordered, ordered_bytes = cached(tmp_path / "a", lambda n: 0.0)
    reversed_, reversed_bytes = cached(tmp_path / "b", lambda n: max(0.0, 0.02 - n * 0.001))
    assert reversed_ == ordered and reversed_bytes == ordered_bytes
    assert ordered["Paraplatin"]["axes"]["identity"]["concept"] == ["found", [["152200", "Paraplatin", "BN"]]]


def test_at_most_in_flight_requests_are_awaited_at_once():
    assert IN_FLIGHT <= 8 and RATE <= 15
    lock, state = threading.Lock(), {"now": 0, "most": 0}

    def get(url, params):
        with lock:
            state["now"] += 1
            state["most"] = max(state["most"], state["now"])
        time.sleep(0.01)
        with lock:
            state["now"] -= 1
        return 200, {"n": params["n"]}

    requests = [("u", {"n": str(n)}) for n in range(40)]
    out = ask_all(requests, get=get, sleep=lambda s: None, monotonic=lambda: 0.0, progress=lambda d, t: None)
    assert 1 < state["most"] <= IN_FLIGHT
    assert [body["n"] for _, _, body in out] == [str(n) for n in range(40)]


def test_no_more_than_rate_requests_begin_in_a_second():
    waits = []
    ask_all(
        [("u", {"n": str(n)}) for n in range(30)],
        get=lambda url, params: (200, {}),
        sleep=waits.append,
        monotonic=lambda: 0.0,
        progress=lambda d, t: None,
    )
    # the clock stands still, so the n-th request to begin waits n/RATE s
    assert sorted(waits) == pytest.approx([n / RATE for n in range(30)])


def test_progress_is_heard_in_order_from_the_callers_thread():
    heard, threads = [], set()

    def progress(done, total):
        heard.append((done, total))
        threads.add(threading.get_ident())

    ask_all(
        [("u", {})] * 7,
        get=lambda u, p: (200, {}),
        sleep=lambda s: None,
        monotonic=lambda: 0.0,
        progress=progress,
    )
    assert heard == [(n, 7) for n in range(1, 8)] and threads == {threading.get_ident()}


@pytest.mark.parametrize(
    ("now", "free", "wait", "following"),
    [
        (10.0, 0.0, 0.0, 10.0 + 1 / 15),  # the first request begins at once
        (10.0, 10.5, 0.5, 10.5 + 1 / 15),  # an early one waits for its slot
        (11.0, 10.5, 0.0, 11.0 + 1 / 15),  # a late one begins at once, never "catching up" past the rate
    ],
)
def test_a_request_begins_at_its_slot_and_holds_the_next(now, free, wait, following):
    assert pace(now, free, 1 / 15) == pytest.approx((wait, following))


ENTRY = {
    "rxclassMinConceptItem": {"classId": "A", "className": "a"},
    "rela": "has_epc",
    "relaSource": "DAILYMED",
}


def test_a_share_keeps_its_relations_entries_and_every_unreadable_one():
    other = ENTRY | {"rela": "has_moa", "relaSource": "MEDRT"}
    body = {"rxclassDrugInfoList": {"rxclassDrugInfo": [ENTRY, other, "x", {"rela": "has_epc"}]}}
    assert relation_body(body, "DAILYMED", "has_epc") == {
        "rxclassDrugInfoList": {"rxclassDrugInfo": [ENTRY, "x", {"rela": "has_epc"}]}
    }
    assert rx.rxclass_classes(200, relation_body(body, "DAILYMED", "has_epc"))[0] == "malformed"
    clean = {"rxclassDrugInfoList": {"rxclassDrugInfo": [ENTRY, other]}}
    assert relation_body(clean, "ATC", "") == {}
    assert rx.rxclass_classes(200, relation_body(clean, "ATC", "")) == ("not_found", [])
    atc = ENTRY | {"rela": "", "relaSource": "ATC"}
    assert relation_body({"rxclassDrugInfoList": {"rxclassDrugInfo": [atc]}}, "ATC", "") == {
        "rxclassDrugInfoList": {"rxclassDrugInfo": [atc]}
    }
    for odd in ({}, [], None, {"rxclassDrugInfoList": []}, {"rxclassDrugInfoList": {"rxclassDrugInfo": []}}):
        assert relation_body(odd, "DAILYMED", "has_epc") == odd


@pytest.mark.parametrize(
    ("code", "count", "route"),
    [
        ("found", 1, "ask"),
        ("found", 2, "ambiguous_in_rxnorm"),
        ("found", 0, "malformed"),
        ("not_found", 0, "not_in_rxnorm"),
        ("lookup_failed", 0, "lookup_failed"),
        ("malformed", 0, "malformed"),
    ],
)
def test_only_a_name_of_one_concept_is_asked_of_rxclass(code, count, route):
    assert class_route(code, count) == route


def test_each_batchs_releases_are_read_once():
    first, last = ["found", "05-Oct-2026", {}], ["found", "02-Nov-2026", {}]
    answers = {
        "a": {"release": first, "release_end": first},
        "b": {"release": first, "release_end": first},
        "c": {"release": first},  # cached before the release was asked after a batch
        "d": {"axes": {"identity": {"release": first, "release_end": last}}},
        "e": "not an answer",
    }
    assert batch_releases(answers) == [
        (("found", "05-Oct-2026"), ("found", "02-Nov-2026")),
        (("found", "05-Oct-2026"), ("found", "05-Oct-2026")),
    ]
    assert batch_releases({}) == []


@pytest.mark.parametrize(
    "name",
    [
        "CAT-8015 20 mcg/kg",
        "CAT-8015 60 mcg/kg",
        "Osimertinib 80mg/40mg",
        "AZD9291 80 mg/40 mg",
        "Placebo AZD9291 80 mg/ 40 mg",
        "Erlotinib 150/100 mg",
        "Iressa 250mg",
        "AZD9291 80mg oral each day",
        "Drug X 2.5 mg/kg, once daily",
        "MEDI 4736",
        "VP 16-213",
        "Osimertinib tablet",
        "Carboplatin Injection",
        "AZD9291 80 mg/40 mg + placebo",
        "AZD9291, 80mg, QD, p.o. (2nd line or later)",
        "80 mg",
        "Osimertinib oral",
        "osimertinib oral and bevazizumab intravenously",
    ],
)
def test_recorded_name_is_queried_exactly_without_a_clinical_name_heuristic(tmp_path, name):
    answers, get = run(tmp_path, [name], [name], **CAT)
    assert [params["name"] for url, params in get.asked if url == rx.RXNORM_IDS] == [name]
    assert not [params for url, params in get.asked if url == rx.RXCLASS_BY_RXCUI]
    assert answers[name]["asked_as"] == name
    assert answers[name]["axes"]["identity"]["ids"][0] == "not_found"
    assert rx.class_evidence([name], answers)["classes"] == []
