"""The search preview (refine-landscape-record 6.1): the resolved search shown before anything is gathered,
over a fake registry and RxNav's own recorded answers (tests/rxnav_request_answers.json); nothing here
touches the network.

Positive: previewing a broad drug class (the FDA's Kinase Inhibitor, eight subclasses) resolves it, writes
the resolved search and fixes its registry query, and says it in plain words (each subclass, each member
with the subclass it is reached through, the exact search); the same command run afterwards gathers exactly
that search, asking RxNav nothing more and leaving resolution.json byte for byte; a relay preview names
only RxNav's addresses and ends previewed once they are saved; a preview run twice says the same;
`landscape --preview` ends 0 and prints the search, and the same command without it then completes; the
words name each filter in the registry's clinical words. Negative: a preview makes no request of the
registry at all, neither a study, an ID page nor its version; a changed request in the same folder is
refused, previewed or run; a request that cannot resolve stops by name, fixing no search; a refused request
writes nothing; a subclass left out is said to be left out, with the members reached only through it; a
member's ingredient that is not searched is shown as not searched.
"""

import json
from pathlib import Path

import httpx
import pytest
from conftest import version
from records import ongoing_study, results_study

from TrialLedger import cli
from TrialLedger.ingest import API_BASE
from TrialLedger.operate import RUN_ADVICE, run, run_exit
from TrialLedger.preview import PREVIEW_ADVICE, PREVIEWED, preview, scope_words
from TrialLedger.request import lookup_url

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
PD1_IN_LUNG = DOC["requests"][0]
KINASE = DOC["requests"][5]
NO_CLASS = DOC["requests"][4]
assert KINASE == {"drug_class": {"name": "Kinase Inhibitor", "source": "EPC"}}


def drug_free(study):
    for item in study["protocolSection"].get("armsInterventionsModule", {}).get("interventions", []):
        item["type"] = "DEVICE"
    return study


STUDIES = [drug_free(results_study()), drug_free(ongoing_study())]


class Registry:
    """The registry, recording every request it is sent."""

    def __init__(self):
        self.studies = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in STUDIES}
        self.requests = []

    def serve(self, request):
        self.requests.append(request)
        if request.url.path == "/api/v2/version":
            return version()
        params = request.url.params
        if params.get("fields") == "NCTId":
            page = [{"protocolSection": {"identificationModule": {"nctId": n}}} for n in self.studies]
            return httpx.Response(200, json={"studies": page, "totalCount": len(page)})
        asked = params["filter.ids"].split(",")
        return httpx.Response(
            200, json={"studies": [self.studies[n] for n in asked], "totalCount": len(asked)}
        )

    def client(self):
        return httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(self.serve))


class RxNav:
    """RxNav as recorded, each request asked kept in order."""

    def __init__(self):
        self.asked = []

    def get(self, url, params):
        key = lookup_url(url, params)
        self.asked.append(key)
        if key in ANSWERS:
            return tuple(ANSWERS[key])
        if url.endswith("/rxclass/allClasses.json"):
            class_type = params["classTypes"]
            return 200, {
                "rxclassMinConceptList": {
                    "rxclassMinConcept": [
                        {"classId": "OTHER", "className": "Unrelated class", "classType": class_type}
                    ]
                }
            }
        return (200, {"idGroup": {}}) if url.endswith("/rxcui.json") else (200, {})


def previewed(folder, request, rxnav, mode="direct"):
    return preview(folder, request, mode, get=rxnav.get, sleep=lambda s: None)


def read(folder, name):
    return json.loads((folder / name).read_text(encoding="utf-8"))


# ── the preview ─────────────────────────────────────────────────────────────────────────────────────────


def test_previewing_a_broad_class_resolves_and_fixes_the_search_and_asks_the_registry_nothing(tmp_path):
    folder, registry, rxnav = tmp_path / "kinase", Registry(), RxNav()
    outcome = previewed(folder, KINASE, rxnav)
    assert outcome.status == PREVIEWED and run_exit(outcome.status) == 0
    assert outcome.advice == PREVIEW_ADVICE
    assert registry.requests == []
    scope = read(folder, "resolution.json")
    assert scope["code"] == "resolved"
    assert read(folder, "scope.json") == {"query": scope["query"], "rxnav": []}
    assert read(folder, "request.json") == KINASE
    # nothing of the registry's: no fetch named, no body saved, no record
    assert not (folder / "fetches.json").exists() and list((folder / "bodies").iterdir()) == []
    assert not (folder / "landscape.json").exists() and not (folder / "next.json").exists()
    words = outcome.detail.splitlines()
    assert words == scope_words(scope)
    assert "  It includes 8 subclass(es):" in words
    assert "    HER2/neu Receptor Antagonist (N0000175661)" in words
    assert any(
        line.startswith("    trastuzumab, through HER2/neu Receptor Antagonist: searched as")
        for line in words
    )
    assert words[words.index("The exact search sent to the registry:") + 1] == (
        f"  filter.advanced={scope['query']['filter.advanced']}"
    )


def test_the_same_command_then_gathers_exactly_the_previewed_search(tmp_path):
    folder, rxnav = tmp_path / "pd1", RxNav()
    previewed(folder, PD1_IN_LUNG, rxnav)
    resolved = (folder / "resolution.json").read_bytes()
    registry, later = Registry(), RxNav()
    outcome = run(folder, PD1_IN_LUNG, "direct", get=later.get, http=registry.client(), sleep=lambda s: None)
    assert outcome.status == "complete"
    assert later.asked == []  # no study has a drug, and the search is never resolved again
    assert (folder / "resolution.json").read_bytes() == resolved
    record = read(folder, "landscape.json")
    assert record["scope"] == json.loads(resolved)
    id_pages = [r for r in registry.requests if r.url.params.get("fields") == "NCTId"]
    assert id_pages and all(
        r.url.params["filter.advanced"] == record["scope"]["query"]["filter.advanced"] for r in id_pages
    )


def test_a_preview_run_again_says_the_same_and_asks_nothing(tmp_path):
    folder = tmp_path / "pd1"
    first = previewed(folder, PD1_IN_LUNG, RxNav())
    again = RxNav()
    second = previewed(folder, PD1_IN_LUNG, again)
    assert second == first and again.asked == []


def test_a_changed_request_in_the_same_folder_is_refused_previewed_or_run(tmp_path):
    folder = tmp_path / "pd1"
    previewed(folder, PD1_IN_LUNG, RxNav())
    changed = {**PD1_IN_LUNG, "phase": ["PHASE2"]}
    outcome = previewed(folder, changed, RxNav())
    assert outcome.status == "request_differs" and run_exit(outcome.status) == 2
    assert outcome.advice == RUN_ADVICE["request_differs"]
    registry = Registry()
    ran = run(folder, changed, "direct", get=RxNav().get, http=registry.client(), sleep=lambda s: None)
    assert ran.status == "request_differs" and registry.requests == []
    assert read(folder, "request.json") == PD1_IN_LUNG


def test_a_relay_preview_names_only_rxnavs_addresses_and_ends_previewed(tmp_path):
    folder, rxnav = tmp_path / "relay", RxNav()
    statuses = []
    for _round in range(20):
        outcome = previewed(folder, PD1_IN_LUNG, rxnav, mode="relay")
        statuses.append(outcome.status)
        if outcome.status != "awaiting_fetch":
            break
        assert run_exit(outcome.status) == 3
        for fetch in read(folder, "next.json")["fetches"]:
            url = httpx.URL(fetch["url"])
            assert url.host == "rxnav.nlm.nih.gov" and fetch["save_as"].startswith("lookups/")
            status, body = rxnav.get(str(url.copy_with(query=None)), dict(url.params))
            (folder / fetch["save_as"]).write_text(json.dumps(body), encoding="utf-8")
    assert statuses[-1] == PREVIEWED and set(statuses[:-1]) == {"awaiting_fetch"}
    waiting = read(folder, "next.json")
    assert waiting["status"] == PREVIEWED and waiting["fetches"] == []
    assert waiting["detail"] == outcome.detail and waiting["instructions"] == PREVIEW_ADVICE
    direct = tmp_path / "direct"
    assert previewed(direct, PD1_IN_LUNG, RxNav()).detail == outcome.detail


def test_a_request_that_cannot_resolve_stops_by_name_fixing_no_search(tmp_path):
    folder = tmp_path / "none"
    outcome = previewed(folder, NO_CLASS, RxNav())
    assert outcome.status == "scope_stopped" and run_exit(outcome.status) == 2
    assert "RxClass holds no class of that name" in outcome.advice
    assert read(folder, "resolution.json")["code"] == "unresolved"
    assert not (folder / "scope.json").exists()


def test_a_refused_request_writes_nothing(tmp_path):
    outcome = previewed(tmp_path / "empty", {}, RxNav())
    assert outcome.status == "request_refused" and outcome.detail.startswith("empty_request")
    assert not (tmp_path / "empty").exists()


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match="mode must be one of"):
        preview(Path("unused"), PD1_IN_LUNG, "carrier pigeon")


# ── the command ─────────────────────────────────────────────────────────────────────────────────────────


def test_landscape_preview_ends_0_with_the_search_and_the_same_command_then_completes(tmp_path, capsys):
    folder = tmp_path / "pd1"
    registry, rxnav = Registry(), RxNav()
    flags = [
        "landscape",
        "--run",
        str(folder),
        "--request",
        str(tmp_path / "request.json"),
        "--mode",
        "direct",
    ]
    (tmp_path / "request.json").write_text(json.dumps(PD1_IN_LUNG), encoding="utf-8")
    code = cli.main(
        [*flags, "--preview"], http=registry.client(), sleep=lambda s: None, rxclass_get=rxnav.get
    )
    out = capsys.readouterr().out
    assert code == 0 and registry.requests == []
    assert f"trialledger landscape: previewed (exit 0) — run folder {folder}" in out
    assert "Phase: Phase 3" in out and "Status: Recruiting" in out and PREVIEW_ADVICE in out
    code = cli.main(flags, http=registry.client(), sleep=lambda s: None, rxclass_get=rxnav.get)
    assert code == 0 and (folder / "landscape.json").is_file()


def test_landscape_preview_of_a_class_not_found_ends_2(tmp_path, capsys):
    flags = ["landscape", "--run", str(tmp_path / "x"), "--drug-class", "No Such Class Zzq"]
    code = cli.main(
        [*flags, "--class-source", "EPC", "--mode", "direct", "--preview"], rxclass_get=RxNav().get
    )
    assert code == 2 and "scope_stopped" in capsys.readouterr().err


def test_preview_of_a_missed_class_name_shows_explicit_catalog_choices(tmp_path):
    class CatalogRxNav(RxNav):
        def get(self, url, params):
            if url.endswith("/rxclass/allClasses.json"):
                return 200, {
                    "rxclassMinConceptList": {
                        "rxclassMinConcept": [
                            {
                                "classId": "L01EB",
                                "className": (
                                    "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors"
                                ),
                                "classType": "ATC1-4",
                            },
                        ]
                    }
                }
            return super().get(url, params)

    asked = {"drug_class": {"name": "EGFR tyrosine kinase inhibitors", "source": "ATC"}}
    outcome = previewed(tmp_path / "candidate", asked, CatalogRxNav())
    scope = read(tmp_path / "candidate", "resolution.json")
    assert outcome.status == "scope_stopped"
    assert scope["code"] == "unresolved" and scope["query"] == {}
    assert "L01EB" in outcome.detail and "source ATC" in outcome.detail
    assert scope["stops"] == [
        [
            "drug_class",
            "class_candidates",
            [["L01EB", "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors", "ATC1-4"]],
        ]
    ]
    assert "--drug-class-id <ID>" in outcome.detail and "--class-source" in outcome.detail
    assert "No candidate was selected." in outcome.detail
    assert "The exact search sent to the registry:" not in outcome.detail


# ── the words, directly ─────────────────────────────────────────────────────────────────────────────────


def resolved(request):
    from TrialLedger.request import class_catalog_request, resolve_scope

    answers = dict(ANSWERS)
    drug_class = request.get("drug_class") if isinstance(request, dict) else None
    if isinstance(drug_class, dict) and "name" in drug_class:
        answers.setdefault(
            class_catalog_request(drug_class["source"]),
            [
                200,
                {
                    "rxclassMinConceptList": {
                        "rxclassMinConcept": [
                            {"classId": "N1", "className": "Other class", "classType": "EPC"}
                        ]
                    }
                },
            ],
        )
    return resolve_scope(request, answers)


def test_scope_words_name_each_filter_in_clinical_words_and_the_exact_search():
    words = scope_words(resolved(PD1_IN_LUNG))
    assert words[0].startswith("Drug class asked for: Programmed Death Receptor-1 Blocking Antibody (EPC)")
    assert "  Class: Programmed Death Receptor-1 Blocking Antibody (EPC, N0000191260)" in words
    assert "    pembrolizumab: searched as pembrolizumab (as the class lists it)" in words
    assert (
        "Phase: Phase 3" in words and "Status: Recruiting" in words and "Study type: Interventional" in words
    )
    assert "Started on or after 2015-01-01" in words
    assert words[-3] == "Drug names and classes as RxNav's release 05-Oct-2026 gives them"
    assert words[-2] == "The exact search sent to the registry:"
    disease = next(line for line in words if line.startswith("Disease class: Lung Neoplasms"))
    assert "no source this run reads lists them" in disease
    # a code is never shown but in the exact search itself
    assert not [line for line in words[:-1] if "PHASE3" in line or "RECRUITING" in line]


def test_scope_words_name_each_drug_with_its_names_and_a_date_range():
    words = scope_words(resolved(DOC["requests"][1]))
    assert (
        "  Keytruda: searched as Keytruda (as asked); pembrolizumab (its ingredient, the same molecule)"
        in words
    )
    assert "  XB-1 zzq (RxNorm does not hold it): searched as XB-1 zzq (as asked)" in words
    assert "Started on or before 2024-12-31" in words


def test_scope_words_say_a_subclass_left_out_and_the_members_reached_only_through_it():
    words = scope_words(resolved({"drug_class": {**KINASE["drug_class"], "subclasses": ["N0000175661"]}}))
    assert "    HER2/neu Receptor Antagonist (N0000175661), left out as asked" in words
    left = next(line for line in words if line.startswith("  Members left out"))
    assert left.endswith(": pertuzumab, trastuzumab, margetuximab")  # each reached only through HER2/neu
    assert not any(line.startswith("    trastuzumab,") for line in words)


def test_scope_words_say_why_a_search_cannot_resolve():
    words = scope_words(resolved(NO_CLASS))
    assert words[-2] == "The search cannot be resolved, so nothing is searched:"
    assert words[-1].startswith("  drug_class: class_not_found — RxClass holds no class")
    mechanism = scope_words(resolved({"mechanism": "PD-1"}))
    assert mechanism[0] == "Mechanism: PD-1, through the sourced crosswalk"
    assert "overlaps; not expanded (it does not entail membership)" in mechanism[1]
    assert mechanism[-1].startswith('  mechanism: mechanism_not_entailed ([["PD-1", "L01FF"')


def test_scope_words_show_a_candidate_not_searched_and_other_settings():
    scope = {
        "code": "awaiting_lookups",
        "slots": [
            {"slot": "drug_class", "value": {"id": "X1", "source": "MoA"}},
            {"slot": "condition", "value": "asthma"},
            {"slot": "params", "value": {"query.term": "biomarker"}},
        ],
        "expansions": [
            {
                "slot": "drug_class",
                "kind": "class",
                "code": "found",
                "source": "MoA",
                "classes": [["X1", "Xs", "MOA"]],
            },
            {
                "slot": "drug_class",
                "kind": "subclass_attribution",
                "code": "found",
                "subclasses": [],
                "members": [["1", "bevacizumab-awwb", "PIN", ["DIRECT"], [], True]],
            },
            {
                "slot": "drug_class",
                "kind": "drug_names",
                "drug": "bevacizumab-awwb",
                "code": "other_form",
                "names": [["bevacizumab-awwb", "rxclass_member"]],
                "candidates": [
                    ["bevacizumab", "rxnorm_ingredient", "the ingredient of bevacizumab-awwb (PIN)"]
                ],
            },
        ],
        "pending": ["a", "b"],
        "release": ["pending", "", "x"],
    }
    assert scope_words(scope) == [
        "Drug class asked for: X1 (MoA), with every subclass it includes unless left out",
        "  Class: Xs (MoA, X1)",
        "  Members searched (1):",
        "    bevacizumab-awwb: searched as bevacizumab-awwb (as the class lists it)",
        "      shown, not searched: bevacizumab (the ingredient of bevacizumab-awwb (PIN))",
        "Condition: asthma, as the registry's own condition search reads it",
        "Other registry search settings, sent as given: query.term=biomarker",
        "Not resolved yet: 2 RxNav answer(s) still awaited.",
    ]


@pytest.mark.parametrize("scope", [None, [], "resolved", {}, {"query": {}}])
def test_scope_words_say_there_is_no_resolved_search_for_anything_else(scope):
    assert scope_words(scope) == ["No resolved search: the scope holds no resolution."]


def test_scope_words_say_a_request_refused():
    scope = {"code": "refused", "check": ["unknown_slot", ["drugs"]]}
    assert scope_words(scope) == ["The request is refused as written (unknown_slot: drugs)."]


@pytest.mark.parametrize(
    ("status", "code"),
    [(PREVIEWED, 0), ("awaiting_fetch", 3), ("lookup_failed", 1), ("scope_stopped", 2), ("complete", 0)],
)
def test_run_exit_reads_a_preview_as_a_run(status, code):
    assert run_exit(status) == code
