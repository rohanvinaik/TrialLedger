"""`trialledger landscape` end to end (add-agent-operation 4.2): operate.run and the command over a fake
registry and RxNav's own recorded answers (tests/rxnav_request_answers.json, fetched 2026-11-01); nothing here
touches the network.

Positive: a relay run, the agent fetching every URL next.json names and saving each body where it says, writes
the record a direct run writes, apart from the retrieval's mode and its statement that the drugs' classes
were not looked up, when no study read has an experimental arm's drug (with one, the drug's classes, axes,
review flags and what follows from them read not_looked_up in relay mode, by design); the resolved scope is
written before any study is read and is the record's scope, with RxNav's release asked again after the last
round and found unchanged; a relay run reads every experimental
drug's classes and axes not_looked_up and asks RxNav nothing after the pull; a re-run with nothing new
changes nothing, a run interrupted resumes, and a finished run re-run, in either mode, asks nothing and leaves
its record byte for byte; failed lookups are set aside and asked again on the next run; a query by number
accounts for every number asked; the command ends 0 complete, 3 awaiting fetch, 2 refused or stopped and 1
failed, each with its words, its mode the doctor's when none is given; the workbook's call site writes
landscape.xlsx, the record's readout, certified by reading it back, staged then renamed, and kept on a re-run.
Negative: a request that cannot resolve (an empty request, an unknown class, a query too long) stops by name
with its advice and no registry query is written or sent, and a failed lookup beside such a stop is never
promised again in that folder; a release changed between the rounds is refused; a registry that keeps
failing writes no record; a folder holding another request, or a record that differs, is never overwritten;
a record the schema refuses is not written; a request given both as a file and as flags is refused.
"""

import json
import re
from pathlib import Path

import httpx
import pytest
from conftest import version
from records import ongoing_study, results_study

from TrialLedger import cli, operate, readout
from TrialLedger.ingest import API_BASE
from TrialLedger.operate import (
    CLASSES_NOT_LOOKED_UP,
    RUN_ADVICE,
    STOP_ADVICE,
    run,
    run_exit,
)
from TrialLedger.request import lookup_url
from TrialLedger.steps import FETCH_INSTRUCTIONS

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
PD1_IN_LUNG, _BY_NAME, _ALK_ATC, _ALK_AS_EPC, NO_CLASS, _KINASE_EPC, KINASE_MOA = DOC["requests"]
VERSION = "https://rxnav.nlm.nih.gov/REST/version.json"
PD1_CLAUSE_START = '(AREA[InterventionName]("pembrolizumab" OR '


def drug_free(study):
    """A study none of whose interventions is a drug, biological or genetic one: RxNav is asked nothing."""
    module = study["protocolSection"].get("armsInterventionsModule") or {}
    for item in module.get("interventions", []):
        item["type"] = "DEVICE"
    return study


def ids_of(studies):
    return [s["protocolSection"]["identificationModule"]["nctId"] for s in studies]


class Registry:
    """The registry: /version, the query's ID pages and its batches by filter.ids, recording every request."""

    def __init__(self, studies, failures=0):
        self.studies = {nct: study for nct, study in zip(ids_of(studies), studies, strict=True)}
        self.failures = failures
        self.requests = []

    def serve(self, request):
        self.requests.append(request)
        if self.failures:
            self.failures -= 1
            return httpx.Response(503)
        if request.url.path == "/api/v2/version":
            return version()
        params = request.url.params
        if params.get("fields") == "NCTId":
            page = [{"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in self.studies]
            return httpx.Response(200, json={"studies": page, "totalCount": len(page)})
        asked = params["filter.ids"].split(",")
        return httpx.Response(
            200, json={"studies": [self.studies[n] for n in asked], "totalCount": len(asked)}
        )

    def client(self):
        return httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(self.serve), follow_redirects=False
        )


class RxNav:
    """RxNav as recorded: each request line's [status, body]; RxNorm holds no other name, and RxClass knows
    no class of any concept. `override` answers chosen lines otherwise, once each (a failure, another
    release)."""

    def __init__(self, override=None):
        self.override = {key: list(answers) for key, answers in (override or {}).items()}
        self.asked = []

    def get(self, url, params):
        key = lookup_url(url, params)
        self.asked.append(key)
        if self.override.get(key):
            return tuple(self.override[key].pop(0))
        if key in ANSWERS:
            return tuple(ANSWERS[key])
        if url.endswith("/rxcui.json"):
            return 200, {"idGroup": {}}  # RxNorm's answer for a name it does not hold
        assert url.endswith(("/byRxcui.json", "/properties.json", "/related.json")), key
        return 200, {}

    def body(self, url):
        """What an agent saves for one URL next.json names: the body, or the note of a failure."""
        parsed = httpx.URL(url)
        status, body = self.get(str(parsed.copy_with(query=None)), dict(parsed.params))
        return json.dumps(body).encode() if status == 200 else f"failed: HTTP {status}".encode()


def direct(folder, request, registry, rxnav, **kwargs):
    return run(
        folder,
        request,
        "direct",
        get=rxnav.get,
        http=registry.client(),
        sleep=lambda seconds: None,
        monotonic=lambda: 0.0,
        **kwargs,
    )


def fetch_round(folder, registry, rxnav):
    """The agent's part: every URL next.json names, fetched and saved, as fetched, where it says."""
    document = json.loads((folder / "next.json").read_text(encoding="utf-8"))
    client = registry.client()
    for fetch in document["fetches"]:
        host = httpx.URL(fetch["url"]).host
        body = rxnav.body(fetch["url"]) if host == "rxnav.nlm.nih.gov" else client.get(fetch["url"]).content
        (folder / fetch["save_as"]).write_bytes(body)
    return document


def relay_to_the_end(folder, request, registry, rxnav):
    statuses = []
    while True:
        outcome = run(folder, request, "relay")
        statuses.append(outcome.status)
        if outcome.status != "awaiting_fetch":
            return statuses, outcome
        fetch_round(folder, registry, rxnav)


def record(folder):
    return json.loads((folder / "landscape.json").read_text(encoding="utf-8"))


def files(folder):
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()
    }


# ── the round trip ──────────────────────────────────────────────────────────────────────────────────────


def test_a_relay_run_writes_the_record_a_direct_run_writes(tmp_path):
    studies = [drug_free(results_study()), ongoing_study()]
    outcome = direct(tmp_path / "direct", PD1_IN_LUNG, Registry(studies), RxNav())
    assert outcome.status == "complete"
    statuses, last = relay_to_the_end(tmp_path / "relay", PD1_IN_LUNG, Registry(studies), RxNav())
    assert statuses[-1] == "complete" and set(statuses[:-1]) == {"awaiting_fetch"}
    assert last.advice == outcome.advice
    held, relayed = record(tmp_path / "direct"), record(tmp_path / "relay")
    retrieval = held["manifest"]["retrieval"]
    assert retrieval == {
        "mode": "direct",
        "matched": 2,
        "read": 2,
        "drug_classes": operate.CLASSES_LOOKED_UP,
    }
    assert relayed["manifest"]["retrieval"] == retrieval | {
        "mode": "relay",
        "drug_classes": CLASSES_NOT_LOOKED_UP,
    }
    relayed["manifest"]["retrieval"] = retrieval
    assert relayed == held
    assert ids_of(studies) == [study["nct"]["value"] for study in held["studies"]]
    # the scope: written before any study was read, and the record's
    scope = json.loads((tmp_path / "relay" / "resolution.json").read_text(encoding="utf-8"))
    assert held["scope"] == scope and scope["code"] == "resolved"
    assert scope["query"]["filter.advanced"].startswith(PD1_CLAUSE_START)
    assert scope["release_check"] == ["unchanged", "05-Oct-2026", "05-Oct-2026"]
    assert scope["release_basis"] == operate.RELEASE_REREAD
    assert json.loads((tmp_path / "relay" / "scope.json").read_text(encoding="utf-8")) == {
        "query": scope["query"],
        "rxnav": [],
    }
    assert (tmp_path / "direct" / "manifest.json").read_bytes() == (
        json.dumps(held["manifest"], ensure_ascii=False, indent=1) + "\n"
    ).encode()


def test_the_relayed_resolution_is_the_step_protocols_shape(tmp_path):
    folder = tmp_path / "relay"
    outcome = run(folder, PD1_IN_LUNG, "relay")
    assert (outcome.status, run_exit(outcome.status)) == ("awaiting_fetch", 3)
    document = json.loads((folder / "next.json").read_text(encoding="utf-8"))
    assert document == {
        "status": "awaiting_fetch",
        "detail": "2 RxNav request(s) to fetch, named in next.json",
        "run_folder": str(folder.resolve()),
        "instructions": FETCH_INSTRUCTIONS,
        "fetches": [
            {"url": VERSION, "save_as": "lookups/lookup-001.json", "why": "rxnav_answer"},
            {
                "url": "https://rxnav.nlm.nih.gov/REST/rxclass/class/byName.json?className=Programmed+Death"
                "+Receptor-1+Blocking+Antibody&classTypes=EPC",
                "save_as": "lookups/lookup-002.json",
                "why": "rxnav_answer",
            },
        ],
    }
    assert not (folder / "scope.json").exists() and not (folder / "bodies").exists()


def test_a_relay_run_reads_every_experimental_drug_not_looked_up(tmp_path):
    rxnav = RxNav()
    statuses, _ = relay_to_the_end(tmp_path / "relay", PD1_IN_LUNG, Registry([results_study()]), rxnav)
    assert statuses[-1] == "complete"
    assert not any("byDrugName" in key for key in rxnav.asked)
    testamab = record(tmp_path / "relay")["studies"][0]["interventions"][0]
    assert testamab["drug_class"]["value"] == {"state": "not_looked_up", "classes": [], "resolved_by": ""}
    assert (testamab["drug_class"]["status"], testamab["drug_class"]["note"]) == (
        "unresolved",
        "not_looked_up",
    )
    assert testamab["axes"]["note"] == "not_looked_up: own_name_not_looked_up"
    assert not (tmp_path / "relay" / "classes.json").exists()


def test_a_direct_run_asks_rxclass_about_the_studies_drugs(tmp_path):
    rxnav = RxNav()
    assert direct(tmp_path / "direct", PD1_IN_LUNG, Registry([results_study()]), rxnav).status == "complete"
    asked = [key for key in rxnav.asked if "rxcui.json?name=Testamab" in key]
    assert asked and (tmp_path / "direct" / "classes.json").is_file()
    testamab = record(tmp_path / "direct")["studies"][0]["interventions"][0]
    assert testamab["drug_class"]["value"]["state"] == "unresolved"


def test_a_query_by_number_accounts_for_every_number_asked(tmp_path):
    request = {"params": {"filter.ids": "NCT01234567,NCT07654321,NCT99999999"}}
    rxnav = RxNav()
    outcome = direct(
        tmp_path / "ids", request, Registry([drug_free(results_study()), ongoing_study()]), rxnav
    )
    assert outcome.status == "complete" and rxnav.asked == []
    retrieval = record(tmp_path / "ids")["manifest"]["retrieval"]
    assert [entry["status"] for entry in retrieval["requested_ids"]] == ["found", "found", "missing"]
    assert record(tmp_path / "ids")["scope"]["release_check"] == ["not_asked", "", ""]
    # the run says so in plain words (the release check, 2026-11-01), as pull does
    assert outcome.detail.split("\n")[1:] == [
        "3 trials asked for by number, 2 found under their own number",
        "NCT99999999: no trial in the registry has this number, or lists it as another number",
    ]


def test_an_alias_is_said_as_another_number_of_its_trial(tmp_path):
    aliased = ongoing_study()
    aliased["protocolSection"]["identificationModule"]["nctIdAliases"] = ["NCT01086644"]
    own = aliased["protocolSection"]["identificationModule"]["nctId"]
    request = {"params": {"filter.ids": f"NCT01086644,{own}"}}
    outcome = direct(tmp_path / "ids", request, Registry([aliased]), RxNav())
    assert outcome.status == "complete"
    said = outcome.detail.split("\n")[1:]
    assert said == [
        "2 trials asked for by number, 1 found under their own number",
        f"NCT01086644 is another number of {own}: the registry gave that trial's record",
    ]
    assert "aliased" not in outcome.detail
    statuses = [e["status"] for e in record(tmp_path / "ids")["manifest"]["retrieval"]["requested_ids"]]
    assert statuses == ["aliased", "found"]


def test_one_trial_asked_for_by_number_is_said_in_the_singular(tmp_path):
    study = ongoing_study()
    own = study["protocolSection"]["identificationModule"]["nctId"]
    outcome = direct(tmp_path / "one", {"params": {"filter.ids": own}}, Registry([study]), RxNav())
    assert outcome.status == "complete"
    assert outcome.detail.split("\n")[1:] == ["1 trial asked for by number, 1 found under their own number"]
    assert "1 trials" not in outcome.detail


# ── re-runs ─────────────────────────────────────────────────────────────────────────────────────────────


def test_a_rerun_with_nothing_new_changes_nothing(tmp_path):
    folder = tmp_path / "relay"
    run(folder, PD1_IN_LUNG, "relay")
    before = files(folder)
    assert run(folder, PD1_IN_LUNG, "relay").status == "awaiting_fetch"
    assert files(folder) == before


def test_a_finished_run_rerun_asks_nothing_and_leaves_its_record(tmp_path):
    studies = [drug_free(results_study()), ongoing_study()]
    registry, rxnav = Registry(studies), RxNav()
    relay_to_the_end(tmp_path / "relay", PD1_IN_LUNG, registry, rxnav)
    assert direct(tmp_path / "direct", PD1_IN_LUNG, registry, rxnav).status == "complete"
    for name in ("relay", "direct"):
        folder = tmp_path / name
        before = files(folder)
        idle_registry, idle_rxnav = Registry(studies), RxNav()
        for mode in ("relay", "direct"):
            outcome = run(
                folder,
                PD1_IN_LUNG,
                mode,
                get=idle_rxnav.get,
                http=idle_registry.client(),
                sleep=lambda seconds: None,
            )
            assert outcome.status == "complete" and outcome.detail.endswith("landscape.json unchanged")
        assert idle_registry.requests == [] and idle_rxnav.asked == []
        after = files(folder)
        after.pop("next.json", None), before.pop("next.json", None)
        assert after == before


def test_a_run_interrupted_resumes(tmp_path):
    folder = tmp_path / "direct"
    studies = [drug_free(results_study()), ongoing_study()]
    answering = Registry(studies)

    def fail_after_version(request):
        # /version answers, then the first ID page fails every retry
        if request.url.path == "/api/v2/studies":
            return httpx.Response(503)
        return answering.serve(request)

    client = httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(fail_after_version))
    outcome = run(folder, PD1_IN_LUNG, "direct", get=RxNav().get, http=client, sleep=lambda s: None)
    assert (outcome.status, run_exit(outcome.status)) == ("pull_failed", 1)
    assert "http.server_error" in outcome.detail and outcome.advice == RUN_ADVICE["pull_failed"]
    assert not (folder / "landscape.json").exists() and (folder / "bodies" / "version-start.json").is_file()
    rxnav, registry = RxNav(), Registry(studies)
    assert direct(folder, PD1_IN_LUNG, registry, rxnav).status == "complete"
    assert rxnav.asked == []  # the resolution was kept, never asked again
    assert [r.url.path for r in registry.requests].count("/api/v2/version") == 1  # the end's /version only


def test_failed_lookups_are_set_aside_and_asked_again(tmp_path):
    folder = tmp_path / "direct"
    members = (
        "https://rxnav.nlm.nih.gov/REST/rxclass/classMembers.json?classId=N0000191260&relaSource=DAILYMED"
    )
    members += "&rela=has_epc"
    rxnav = RxNav({members: [(503, None)]})
    studies = [drug_free(results_study())]
    outcome = direct(folder, PD1_IN_LUNG, Registry(studies), rxnav)
    assert (outcome.status, run_exit(outcome.status)) == ("lookup_failed", 1)
    assert outcome.detail.startswith('drug_class: members_lookup_failed ["N0000191260"]')
    assert outcome.detail.endswith("(set aside: lookup-003.json)")
    assert "running the same command again asks them again" in outcome.advice
    assert (folder / "lookups" / "dropped" / "lookup-003.json.1").read_bytes() == b"failed: HTTP 503\n"
    assert not (folder / "scope.json").exists() and not (folder / "bodies").exists()
    assert direct(folder, PD1_IN_LUNG, Registry(studies), rxnav).status == "complete"
    assert rxnav.asked.count(members) == 2


def test_a_relayed_failure_is_reported_then_asked_again(tmp_path):
    folder = tmp_path / "relay"
    by_name = lookup_url(
        "https://rxnav.nlm.nih.gov/REST/rxclass/class/byName.json",
        {"className": "Programmed Death Receptor-1 Blocking Antibody", "classTypes": "EPC"},
    )
    rxnav = RxNav({by_name: [(500, None)]})
    run(folder, PD1_IN_LUNG, "relay")
    fetch_round(folder, Registry([]), rxnav)
    outcome = run(folder, PD1_IN_LUNG, "relay")
    assert outcome.status == "lookup_failed"
    assert json.loads((folder / "next.json").read_text(encoding="utf-8"))["status"] == "lookup_failed"
    again = run(folder, PD1_IN_LUNG, "relay")
    assert again.status == "awaiting_fetch"
    document = json.loads((folder / "next.json").read_text(encoding="utf-8"))
    assert [fetch["save_as"] for fetch in document["fetches"]] == ["lookups/lookup-002.json"]


# ── refusals and stops ──────────────────────────────────────────────────────────────────────────────────


def test_a_release_changed_between_the_rounds_is_refused(tmp_path):
    folder = tmp_path / "direct"
    later = (200, {"version": "02-Nov-2026", "apiVersion": "3.1.357"})
    rxnav = RxNav({VERSION: [tuple(ANSWERS[VERSION]), later]})
    registry = Registry([drug_free(results_study())])
    outcome = direct(folder, PD1_IN_LUNG, registry, rxnav)
    assert (outcome.status, run_exit(outcome.status)) == ("rxnav_release_changed", 1)
    assert outcome.detail == (
        "RxNav's release: found '05-Oct-2026' in the first round, found '02-Nov-2026' after the last"
    )
    assert outcome.advice == RUN_ADVICE["rxnav_release_changed"]
    assert registry.requests == [] and not (folder / "scope.json").exists()
    assert direct(folder, PD1_IN_LUNG, registry, RxNav()).status == "rxnav_release_changed"


def test_a_failed_release_reread_is_asked_again(tmp_path):
    folder = tmp_path / "direct"
    rxnav = RxNav({VERSION: [tuple(ANSWERS[VERSION]), (503, None)]})
    outcome = direct(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), rxnav)
    assert outcome.status == "lookup_failed" and outcome.detail.endswith("(set aside: release-end.json)")
    assert direct(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), rxnav).status == "complete"


@pytest.mark.parametrize(
    ("request_", "code"), [(KINASE_MOA, "query_too_long"), (NO_CLASS, "class_not_found")]
)
def test_a_stop_names_its_advice_and_sends_no_query(tmp_path, request_, code):
    for mode in ("direct", "relay"):
        folder = tmp_path / mode
        registry = Registry([])
        outcome = direct(folder, request_, registry, RxNav()) if mode == "direct" else None
        if mode == "relay":
            statuses, outcome = relay_to_the_end(folder, request_, registry, RxNav())
        assert (outcome.status, run_exit(outcome.status)) == ("scope_stopped", 2)
        assert outcome.detail.startswith(("drug_class: " if code == "class_not_found" else "query: ") + code)
        assert outcome.advice == STOP_ADVICE[code]
        scope = json.loads((folder / "resolution.json").read_text(encoding="utf-8"))
        assert scope["code"] == "unresolved" and scope["stops"][0][1] == code
        assert registry.requests == [] and not (folder / "scope.json").exists()
    document = json.loads((tmp_path / "relay" / "next.json").read_text(encoding="utf-8"))
    assert (document["status"], document["instructions"], document["fetches"]) == (
        "scope_stopped",
        outcome.advice,
        [],
    )


def test_a_failed_lookup_beside_another_stop_is_not_promised_again_here(tmp_path):
    # An unknown class beside a drug whose RxNorm lookup fails: the request must change, so a new folder.
    request = {"drug_class": {"name": "No Such Class Zzq", "source": "EPC"}, "drug": ["Keytruda"]}
    keytruda = "https://rxnav.nlm.nih.gov/REST/rxcui.json?name=Keytruda&search=0"
    folder = tmp_path / "direct"
    rxnav = RxNav({keytruda: [(503, None)]})
    outcome = direct(folder, request, Registry([]), rxnav)
    assert (outcome.status, run_exit(outcome.status)) == ("scope_stopped", 2)
    assert outcome.detail == 'drug_class: class_not_found []; drug: name_lookup_failed ["Keytruda"]'
    assert outcome.advice == f"{STOP_ADVICE['class_not_found']} {operate.LOOKUPS_IN_NEW_FOLDER}"
    assert "Running the same command again" not in outcome.advice
    before = files(folder)
    assert not (folder / "lookups" / "dropped").exists()
    assert direct(folder, request, Registry([]), rxnav) == outcome
    assert files(folder) == before and rxnav.asked.count(keytruda) == 1


def test_query_too_long_advises_narrowing_the_request(tmp_path):
    outcome = direct(tmp_path / "moa", KINASE_MOA, Registry([]), RxNav())
    assert "EPC class instead of a MoA class" in outcome.advice


def test_a_refused_request_writes_nothing(tmp_path):
    outcome = run(tmp_path / "run", {}, "relay")
    assert (outcome.status, outcome.detail, run_exit(outcome.status)) == (
        "request_refused",
        "empty_request: ",
        2,
    )
    assert not (tmp_path / "run").exists()


def test_a_folder_holding_another_request_is_not_reused(tmp_path):
    folder = tmp_path / "run"
    run(folder, PD1_IN_LUNG, "relay")
    before = files(folder)
    outcome = run(folder, NO_CLASS, "relay")
    assert (outcome.status, run_exit(outcome.status)) == ("request_differs", 2)
    assert files(folder) == before


def test_a_record_that_differs_is_never_overwritten(tmp_path):
    folder = tmp_path / "direct"
    studies = [drug_free(results_study())]
    direct(folder, PD1_IN_LUNG, Registry(studies), RxNav())
    tampered = record(folder)
    tampered["studies"][0]["sponsor"]["value"] = "Someone Else"
    (folder / "landscape.json").write_text(json.dumps(tampered), encoding="utf-8")
    held = (folder / "landscape.json").read_bytes()
    outcome = direct(folder, PD1_IN_LUNG, Registry(studies), RxNav())
    assert (outcome.status, run_exit(outcome.status)) == ("record_differs", 2)
    assert (folder / "landscape.json").read_bytes() == held


def test_a_record_the_schema_refuses_is_not_written(tmp_path, monkeypatch):
    monkeypatch.setattr(operate, "schema_problems", lambda record: (("missing_field", "studies[0].nct"),))
    folder = tmp_path / "relay"
    statuses, outcome = relay_to_the_end(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), RxNav())
    assert (outcome.status, outcome.detail, run_exit(outcome.status)) == (
        "schema_problem",
        "missing_field at studies[0].nct",
        2,
    )
    assert not (folder / "landscape.json").exists() and not (folder / "manifest.json").exists()
    assert json.loads((folder / "next.json").read_text(encoding="utf-8"))["status"] == "schema_problem"


def test_an_unknown_mode_is_refused(tmp_path):
    with pytest.raises(ValueError) as raised:
        run(tmp_path / "run", PD1_IN_LUNG, "hosted")
    assert (type(raised.value).__name__, raised.value.args) == (
        "ValueError",
        ("mode must be one of ('direct', 'relay'), not 'hosted'",),
    )


# ── the workbook's call site ────────────────────────────────────────────────────────────────────────────


def test_the_workbook_is_the_readout_of_the_record_and_certified(tmp_path):
    folder = tmp_path / "direct"
    outcome = direct(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), RxNav())
    assert outcome.advice.endswith(operate.BOOK_WORDS["written"])
    assert readout.readout_problems(record(folder), folder / "landscape.xlsx") == []
    assert not (folder / ".landscape.partial.xlsx").exists()


def test_the_workbook_is_staged_then_renamed_and_kept_on_a_rerun(tmp_path, monkeypatch):
    written = []

    def write_readout(held, path):
        written.append((held, path))
        assert not (path.parent / "landscape.xlsx").exists()  # staged: never in place until whole
        path.write_bytes(b"xlsx")
        return 1

    monkeypatch.setattr(readout, "write_readout", write_readout)
    folder = tmp_path / "direct"
    outcome = direct(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), RxNav())
    assert outcome.advice.endswith(operate.BOOK_WORDS["written"])
    assert written == [(record(folder), folder / ".landscape.partial.xlsx")]
    assert (folder / "landscape.xlsx").read_bytes() == b"xlsx"
    assert not (folder / ".landscape.partial.xlsx").exists()
    again = direct(folder, PD1_IN_LUNG, Registry([drug_free(results_study())]), RxNav())
    assert again.advice.endswith(operate.BOOK_WORDS["kept"]) and len(written) == 1


# ── the command ─────────────────────────────────────────────────────────────────────────────────────────

PD1_FLAGS = [
    "--drug-class",
    "Programmed Death Receptor-1 Blocking Antibody",
    "--class-source",
    "EPC",
    "--condition-class",
    "Lung Neoplasms",
    "--phase",
    "PHASE3",
    "--status",
    "RECRUITING",
    "--study-type",
    "INTERVENTIONAL",
    "--start-from",
    "2015-01-01",
]


def command(folder, *words, registry=None, rxnav=None, probe_get=None):
    return cli.main(
        ["landscape", "--run", str(folder), *words],
        http=(registry or Registry([])).client(),
        sleep=lambda seconds: None,
        rxclass_get=(rxnav or RxNav()).get,
        probe_get=probe_get,
    )


def test_the_command_ends_0_when_complete(tmp_path, capsys):
    studies = [drug_free(results_study())]
    assert command(tmp_path / "run", *PD1_FLAGS, "--mode", "direct", registry=Registry(studies)) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"trialledger landscape: complete (exit 0) — run folder {tmp_path / 'run'}\n")
    assert RUN_ADVICE["complete"] in out
    assert json.loads((tmp_path / "run" / "request.json").read_text(encoding="utf-8")) == PD1_IN_LUNG


def test_the_command_ends_3_awaiting_fetch_its_mode_the_doctors(tmp_path, capsys):
    def sandbox(url, **kwargs):
        if "rxnav" in url:
            raise ConnectionRefusedError("egress blocked")
        return httpx.Response(200)

    assert command(tmp_path / "run", *PD1_FLAGS, probe_get=sandbox) == 3
    out = capsys.readouterr().out
    assert out.startswith("trialledger landscape: awaiting_fetch (exit 3)")
    assert RUN_ADVICE["awaiting_fetch"] in out
    assert (tmp_path / "run" / "next.json").is_file()


def test_the_command_reads_a_request_file(tmp_path):
    held = tmp_path / "request.json"
    held.write_text(json.dumps(PD1_IN_LUNG), encoding="utf-8")
    assert command(tmp_path / "run", "--request", str(held), "--mode", "relay") == 3


def test_a_finished_run_given_its_request_otherwise_writes_the_same_record(tmp_path):
    held = tmp_path / "request.json"
    held.write_text(json.dumps(dict(reversed(PD1_IN_LUNG.items()))), encoding="utf-8")
    studies = [drug_free(results_study())]
    folder = tmp_path / "run"
    assert command(folder, "--request", str(held), "--mode", "direct", registry=Registry(studies)) == 0
    before = (folder / "landscape.json").read_bytes()
    assert command(folder, *PD1_FLAGS, "--mode", "direct", registry=Registry(studies)) == 0
    assert (folder / "landscape.json").read_bytes() == before


@pytest.mark.parametrize(
    ("words", "detail"),
    [
        ([], "empty_request: "),
        (["--phase", "PHASE9"], "malformed_value: phase"),
        (["--drug", "x", "--param", "query.term"], "params_not_name_value: query.term"),
        (["--drug-class", "No Such Class Zzq", "--class-source", "EPC"], "drug_class: class_not_found []"),
    ],
)
def test_the_command_ends_2_refused_or_stopped_by_name(tmp_path, capsys, words, detail):
    assert command(tmp_path / "run", *words, "--mode", "direct") == 2
    err = capsys.readouterr().err.splitlines()
    ended = next(n for n, line in enumerate(err) if line.startswith("trialledger landscape: "))
    assert err[ended + 1] == detail
    # what came before the end is only the resolution saying how far its RxNav requests have got
    assert all(line.startswith("resolving the request: ") for line in err[:ended])


def test_the_command_says_how_far_its_rxnav_requests_have_got(tmp_path, capsys):
    """The release check (2026-11-01): never silence for minutes. Positive: each round of the request's
    resolution says how many of its RxNav requests are asked, and the drug lookups after the pull say how
    many drug names, then how many requests RxNav answered; each line before the end. Negative: a run asking
    RxNav nothing says nothing of it."""
    studies = [results_study()]
    assert command(tmp_path / "run", *PD1_FLAGS, "--mode", "direct", registry=Registry(studies)) == 0
    err = capsys.readouterr().err.splitlines()
    assert any(re.fullmatch(r"resolving the request: \d+ of \d+ RxNav lookups asked", line) for line in err)
    assert not [line for line in err if "round" in line]
    assert any(
        line.startswith("asking RxNav, the National Library of Medicine's drug vocabulary") for line in err
    )
    assert any(
        re.fullmatch(r"RxNorm identity asked of RxNav for \d+ of \d+ drug names", line) for line in err
    )
    assert any(re.fullmatch(r"RxNav answered \d+ requests about \d+ drug names .*", line) for line in err)
    drug_less = Registry([drug_free(results_study())])
    assert command(tmp_path / "ids", "--ids", "NCT01234567", "--mode", "direct", registry=drug_less) == 0
    assert not [line for line in capsys.readouterr().err.splitlines() if "RxNav" in line]


def test_the_command_takes_trials_by_number_and_says_what_became_of_each(tmp_path, capsys):
    """--ids (the release check, 2026-11-01). Positive: the numbers are the request's filter.ids, every one is
    in the record's accounting, and the end says, in plain words, those not found under their own number.
    Negative: --ids beside --param filter.ids is refused before anything is written."""
    studies = [drug_free(results_study()), drug_free(ongoing_study())]
    own = ids_of(studies)
    folder = tmp_path / "ids"
    words = ["--ids", f"{own[0]},NCT09999999", "--ids", own[1], "--mode", "direct"]
    assert command(folder, *words, registry=Registry(studies)) == 0
    out = capsys.readouterr().out
    assert json.loads((folder / "request.json").read_text(encoding="utf-8")) == {
        "params": {"filter.ids": f"{own[0]},NCT09999999,{own[1]}"}
    }
    assert "3 trials asked for by number, 2 found under their own number\n" in out
    assert "NCT09999999: no trial in the registry has this number, or lists it as another number\n" in out
    statuses = [e["status"] for e in record(folder)["manifest"]["retrieval"]["requested_ids"]]
    assert statuses == ["found", "missing", "found"]
    twice = ["--ids", own[0], "--param", f"filter.ids={own[1]}", "--mode", "direct"]
    assert command(tmp_path / "twice", *twice) == 2
    assert "params_duplicate: filter.ids" in capsys.readouterr().err
    assert not (tmp_path / "twice").exists()


def test_a_request_both_as_a_file_and_as_flags_is_refused(tmp_path, capsys):
    held = tmp_path / "request.json"
    held.write_text(json.dumps(PD1_IN_LUNG), encoding="utf-8")
    assert command(tmp_path / "run", "--request", str(held), "--drug", "x", "--mode", "relay") == 2
    assert "request_and_flags" in capsys.readouterr().err
    unreadable = tmp_path / "broken.json"
    unreadable.write_text("{", encoding="utf-8")
    assert command(tmp_path / "run", "--request", str(unreadable), "--mode", "relay") == 2
    assert not (tmp_path / "run").exists()


def test_the_command_ends_2_when_the_doctor_finds_no_run_can_start(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert command(blocker / "run", *PD1_FLAGS, probe_get=lambda url, **kw: httpx.Response(200)) == 2
    assert "mode_unavailable (exit 2)" in capsys.readouterr().err


def test_the_command_ends_1_when_the_registry_keeps_failing(tmp_path, capsys):
    failing = Registry([], failures=4)
    assert (
        command(tmp_path / "run", "--param", "query.cond=asthma", "--mode", "direct", registry=failing) == 1
    )
    err = capsys.readouterr().err.splitlines()
    assert err[0] == "retrying in 2s after HTTP 503 (attempt 1 of 4)"
    assert err[3].startswith("trialledger landscape: pull_failed (exit 1)")
    assert err[4].startswith("http.server_error: GET https://clinicaltrials.gov/api/v2/version")
    assert err[5] == RUN_ADVICE["pull_failed"]
    assert not (tmp_path / "run" / "landscape.json").exists()
