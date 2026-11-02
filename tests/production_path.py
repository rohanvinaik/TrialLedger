"""Real reporting, archival verification, MCP and typed reasoning entry points.

Unreached functions are diagnostic, not proof that an unfinished pipeline is complete.
"""

import ast
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "TrialLedger"
CALLED: set[tuple[str, str]] = set()


def record_call(frame, event, _arg):
    if event == "call" and frame.f_code.co_filename.startswith(str(PACKAGE)):
        # keyed by the path within the package, so a subpackage's module never shares a top-level one's key
        where = Path(frame.f_code.co_filename).relative_to(PACKAGE).as_posix()
        CALLED.add((where, frame.f_code.co_qualname))


def defined() -> set[tuple[str, str]]:
    """Every function, method and lambda the package and its subpackages define, by the file's path within
    the package ("record.py", "semantics/loader.py") and qualified name."""
    found: set[tuple[str, str]] = set()
    for path in sorted(PACKAGE.rglob("*.py")):

        def walk(node: ast.AST, prefix: str, file: str = path.relative_to(PACKAGE).as_posix()) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.add((file, prefix + child.name))
                    walk(child, f"{prefix}{child.name}.<locals>.")
                elif isinstance(child, ast.Lambda):
                    found.add((file, prefix + "<lambda>"))
                    walk(child, f"{prefix}<lambda>.<locals>.")
                elif isinstance(child, ast.ClassDef):
                    walk(child, f"{prefix}{child.name}.")
                else:
                    walk(child, prefix)

        walk(ast.parse(path.read_text(encoding="utf-8")), "")
    return found


def near_miss_study(nct: str, ecog: str) -> dict:
    from records import ongoing_study

    study = ongoing_study()
    protocol = study["protocolSection"]
    protocol["identificationModule"]["nctId"] = nct
    protocol["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n"
        "* No prior systemic therapy for advanced or metastatic disease\n"
        # a record that says its exclusions are abbreviated: the coverage markers and their flag are reached
        f"* Participants must have ECOG performance status {ecog}\n"
        "* Participants must have hemoglobin >= 9 g/dL\n"
        "\nCohort A only:\n\n* Participants must have ECOG performance status 0-1 "
        "or ECOG performance status 0-2\n\n"
        "All participants:\n\n"
        "Key Exclusion Criteria:\n\n* Active autoimmune disease\n"
    )
    protocol["armsInterventionsModule"] = {
        "armGroups": [{"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: Placebo"]}],
        "interventions": [{"type": "DRUG", "name": "Placebo"}],
    }
    # An explicit synthetic canonical condition resolves only through its recorded MeSH response.
    # This changes no other registry fixture and authorizes no title-fragment or category inference.
    protocol["conditionsModule"] = {"conditions": ["Carcinoma, Non-Small-Cell Lung"]}
    study.setdefault("derivedSection", {})["conditionBrowseModule"] = {
        "meshes": [{"id": "D002289", "term": "Carcinoma, Non-Small-Cell Lung"}],
        "ancestors": [],
    }
    protocol.setdefault("designModule", {}).setdefault("designInfo", {})["primaryPurpose"] = "TREATMENT"
    return study


RXNORM = {"Testamab": ("9001", "IN"), "Placebo": ("9002", "IN"), "TM-1": ("9003", "BN")}
RXNORM["XB-1 + carboplatin"] = ("9004", "MIN")
INGREDIENTS = {"9003": [("9001", "testamab")], "9004": [("9005", "xb-1"), ("9006", "carboplatin")]}
SUBJECTS = {"Testamab": ("9001", "testamab"), "TM-1": ("9001", "testamab"), "Placebo": ("9002", "placebo")}


def rxnav(url: str, params: dict) -> tuple[int, dict]:
    """RxNav's release and RxNorm's identity answers, as the live service gives them."""
    if url.endswith("/version.json"):
        return 200, {"version": "05-Oct-2026", "apiVersion": "3.1.356"}
    if url.endswith("/rxcui.json"):
        known = RXNORM.get(params["name"])
        return 200, {"idGroup": {"rxnormId": [known[0]]} if known else {"name": params["name"]}}
    rxcui = url.rsplit("/", 2)[-2]
    if url.endswith("/properties.json"):
        name, (_, tty) = next((n, v) for n, v in RXNORM.items() if v[0] == rxcui)
        return 200, {"properties": {"rxcui": rxcui, "name": name, "tty": tty}}
    parts = [{"rxcui": r, "name": n, "tty": "IN"} for r, n in INGREDIENTS[rxcui]]
    return 200, {"relatedGroup": {"conceptGroup": [{"tty": "IN", "conceptProperties": parts}]}}


def classes_of(rxcui: str) -> tuple[int, dict]:
    """RxClass's answer by concept (byRxcui), every source in one answer: PD-1/PD-L1 inhibitors (ATC) and
    platinum-containing compounds (structure, DailyMed's and FDASPL's) about testamab for Testamab and its
    brand TM-1 (RxClass answers a brand about its ingredient) and about placebo for Placebo, beside Placebo's
    one DailyMed class; the combination's concept fails (503)."""
    if rxcui == "9004":
        return 503, {}
    subject = {"9001": ("9001", "testamab"), "9003": ("9001", "testamab"), "9002": ("9002", "placebo")}[rxcui]
    atc = {"classId": "L01FF", "className": "PD-1/PD-L1 inhibitors", "classType": "ATC1-4"}
    platinum = {"classId": "N0000175073", "className": "Platinum-containing Compounds", "classType": "CHEM"}
    pd1 = {
        "classId": "N0000191260",
        "className": "Programmed Death Receptor-1 Blocking Antibody",
        "classType": "EPC",
    }
    stated = [(atc, "", "ATC"), (platinum, "has_chemical_structure", "DAILYMED")]
    stated += [(platinum, "has_chemical_structure", "FDASPL")]
    stated += [(pd1, "has_epc", "DAILYMED")] if rxcui == "9002" else []
    concept = {"rxcui": subject[0], "name": subject[1], "tty": "IN"}
    entries = [
        {"minConcept": concept, "rxclassMinConceptItem": item, "rela": rela, "relaSource": source}
        for item, rela, source in stated
    ]
    return 200, {"rxclassDrugInfoList": {"rxclassDrugInfo": entries}}


def landscape_runs(scratch: Path, studies: list[dict], rxclass, sandbox) -> dict[str, int]:
    """`trialledger landscape`, as an assistant runs it (add-agent-operation 4.2), over the registry's pages
    for `studies` and RxNav's recorded answers (tests/rxnav_request_answers.json) beside `rxclass`'s for the
    studies' drugs: in direct mode, a drug class in a condition class with a named drug, every slot of the
    request resolved (its first members lookup failing once, so the failed answer is set aside and asked
    again on the next run), then run again, finished; a mechanism no crosswalk row expands, stopped by name;
    and in relay mode, as the doctor decides for a sandbox that cannot reach RxNav, a request file relayed
    through next.json until complete, every fetch made by the agent and saved where it says."""
    import httpx
    from conftest import version

    from TrialLedger import cli
    from TrialLedger.ingest import API_BASE
    from TrialLedger.request import lookup_url

    recorded = json.loads((HERE / "rxnav_request_answers.json").read_text(encoding="utf-8"))
    by_id = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in studies}
    members = f"{RXNAV}/rxclass/classMembers.json?classId=N0000191260&relaSource=DAILYMED&rela=has_epc"
    failing = [members]

    def rxnav_answer(url, params):
        key = lookup_url(url, params)
        if key in failing:
            failing.remove(key)
            return 503, None
        if key in recorded["answers"]:
            return tuple(recorded["answers"][key])
        return rxclass(url, params)

    def route(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/version":
            return version()
        params = request.url.params
        if params.get("fields") == "NCTId":
            page = [{"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in by_id]
            return httpx.Response(200, json={"studies": page, "totalCount": len(page)})
        asked = params["filter.ids"].split(",")
        return httpx.Response(200, json={"studies": [by_id[nct] for nct in asked], "totalCount": len(asked)})

    def registry():
        return httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(route), follow_redirects=False)

    pd1 = recorded["requests"][0]["drug_class"]["name"]
    flags = ["--drug-class", pd1, "--class-source", "EPC", "--drug", "Keytruda"]
    flags += ["--condition-class", "Lung Neoplasms", "--phase", "PHASE3", "--status", "RECRUITING"]
    flags += ["--study-type", "INTERVENTIONAL", "--start-from", "2015-01-01", "--mode", "direct"]

    def direct(name, *words):
        return cli.main(
            ["landscape", "--run", str(scratch / name), *words],
            http=registry(),
            sleep=lambda s: None,
            rxclass_get=rxnav_answer,
            probe_get=sandbox,
        )

    codes = {"landscape_lookup_failed": direct("landscape-direct", *flags)}
    codes["landscape"] = direct("landscape-direct", *flags)
    codes["landscape_again"] = direct("landscape-direct", *flags)
    codes["verify_landscape"] = cli.main(["verify", str(scratch / "landscape-direct")])
    invalid_json = scratch / "landscape-nonfinite"
    shutil.copytree(scratch / "landscape-direct", invalid_json)
    (invalid_json / "landscape.json").write_text('{"value":NaN}')
    codes["verify_landscape_nonfinite"] = cli.main(["verify", str(invalid_json)])
    completed = json.loads((scratch / "landscape-direct" / "landscape.json").read_text())
    sources = {study["protocolSection"]["identificationModule"]["nctId"]: study for study in studies}
    for reported in completed["studies"]:
        original = sources[reported["nct"]]
        assert (
            reported["eligibility"]["text"]
            == original["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
        )
        assert not {"universe", "coordinates", "scoped_assertions", "assertion_compilation"}.intersection(
            reported
        )
    codes["landscape_stopped"] = direct("landscape-mechanism", "--mechanism", "PD-1", "--mode", "direct")
    # A class with subclasses (the FDA's Kinase Inhibitor: HER2, EGFR, JAK ... below it), so each subclass's
    # own members are asked and every member attributed to the subclass it comes through.
    codes["landscape_subclasses"] = direct(
        "landscape-kinase", "--drug-class", "Kinase Inhibitor", "--class-source", "EPC", "--mode", "direct"
    )
    # Trials by number (--ids), one of them no trial holds, so each number is accounted for and the one not
    # found is said in plain words.
    codes["landscape_ids"] = direct("landscape-ids", "--ids", "NCT09000001,NCT09999999", "--mode", "direct")
    # The search previewed: resolved and fixed, no trial read; the same command without --preview gathers it.
    kinase = ["--drug-class", "Kinase Inhibitor", "--class-source", "EPC", "--mode", "direct"]
    codes["landscape_preview"] = direct("landscape-preview", *kinase, "--preview")
    held = scratch / "request.json"
    held.write_text(json.dumps(recorded["requests"][0]), encoding="utf-8")
    relayed = scratch / "landscape-relay"
    client = registry()
    while True:
        codes["landscape_relay"] = cli.main(
            ["landscape", "--run", str(relayed), "--request", str(held)], probe_get=sandbox
        )
        if codes["landscape_relay"] != 3:
            break
        for fetch in json.loads((relayed / "next.json").read_text(encoding="utf-8"))["fetches"]:
            url = httpx.URL(fetch["url"])
            if url.host == "rxnav.nlm.nih.gov":
                status, body = rxnav_answer(str(url.copy_with(query=None)), dict(url.params))
                (relayed / fetch["save_as"]).write_text(
                    json.dumps(body) if status == 200 else f"failed: {status}"
                )
            else:
                (relayed / fetch["save_as"]).write_bytes(client.get(fetch["url"]).content)
    return codes | mcp_session(scratch / "mcp", recorded["requests"][0], rxnav_answer, registry, sandbox)


MCP_ROUNDS = 20  # the relay through the tools ends within this many landscape calls, or the path fails
# The record tool's calls on the relayed run's record, beside its first study by NCT number.
RECORD_CALLS = (
    {"part": "manifest"},
    {"part": "statuses"},
    {"part": "fields", "offset": 50},
    {"part": "studies", "offset": 1},
    {"part": "study", "nct": "NCT99999999"},
    {"part": "findings"},
    {"part": "questions"},
    {"part": "address", "address": "/studies/0"},
    {"part": "address", "address": "/studies/99"},
    {"part": "studies", "offset": 99},
)


def mcp_session(root: Path, request: dict, rxnav_answer, registry, sandbox) -> dict[str, int]:
    """`trialledger mcp` as an assistant's MCP client drives it (add-agent-operation 6.2): a ping before the
    handshake, initialize and its notification, tools/list, a line that is not JSON, server/discover (not
    found), doctor in a sandbox RxNav is blocked from (relay), a scope not there yet, a save_fetch outside the
    run refused, a request refused; then the request in relay mode, the mode doctor's: landscape, every fetch
    it lists saved through save_fetch as fetched, landscape again, until complete; the record's every part,
    paged, and the scope read back, a study it does not hold, an address outside the record, a page past the
    end and an unknown tool refused; and the request previewed through scope in another run folder, then
    gathered there in direct mode. Each line is written after the answer to the one before it, so the client
    reads what the server answered, as a client does."""
    import httpx

    from TrialLedger import cli

    written: list[str] = []
    finished: dict[str, int] = {}

    def line(ident, method, params=None):
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        return json.dumps(message | ({"params": params} if params is not None else {})).encode()

    def tool(ident, name, **arguments):
        return line(ident, "tools/call", {"name": name, "arguments": arguments})

    def document():
        return json.loads(json.loads(written[-1])["result"]["content"][0]["text"])

    def body(fetch):
        url = httpx.URL(fetch["url"])
        if url.host == "rxnav.nlm.nih.gov":
            status, answer = rxnav_answer(str(url.copy_with(query=None)), dict(url.params))
            return json.dumps(answer) if status == 200 else f"failed: HTTP {status}"
        return client.get(fetch["url"]).content.decode("utf-8")

    def session():
        yield line(0, "ping")
        hello = {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "path", "version": "1"},
        }
        yield line(1, "initialize", hello)
        yield json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode()
        yield line(2, "tools/list")
        yield b"not json\n"
        yield line(3, "server/discover")
        yield tool(4, "doctor", run="relayed")
        yield tool(5, "scope", run="relayed")
        yield tool(6, "save_fetch", run="relayed", save_as="../outside.json", body="{}")
        yield tool(7, "landscape", run="refused", request={}, mode="relay")
        ident = 10
        for _round in range(MCP_ROUNDS):
            ident += 1
            yield tool(ident, "landscape", run="relayed", request=request)
            reply = document()
            if reply["status"] != "awaiting_fetch":
                finished["mcp_relay"] = reply["exit"]
                break
            for fetch in reply["fetches"]:
                ident += 1
                yield tool(ident, "save_fetch", run="relayed", save_as=fetch["save_as"], body=body(fetch))
        ident += 1
        yield tool(ident, "record", run="relayed", part="studies", limit=1)
        nct = document()["studies"][0]["nct"]
        # the relayed run's record: every part read, paged, and refused by name
        for arguments in (*RECORD_CALLS, {"part": "study", "nct": nct}):
            ident += 1
            yield tool(ident, "record", run="relayed", **arguments)
        yield tool(ident + 1, "scope", run="relayed")
        yield tool(ident + 2, "design", run="relayed")
        # the search previewed through scope, then gathered through landscape
        yield tool(ident + 3, "scope", run="direct", request=request, mode="direct")
        finished["mcp_preview"] = document()["exit"]
        yield tool(ident + 4, "landscape", run="direct", request=request, mode="direct")
        finished["mcp_direct"] = document()["exit"]

    client = registry()
    finished["mcp"] = cli.main(
        ["mcp", "--root", str(root)],
        http=registry(),
        sleep=lambda s: None,
        rxclass_get=rxnav_answer,
        probe_get=sandbox,
        mcp_streams=(session(), written.append),
    )
    return finished


RXNAV = "https://rxnav.nlm.nih.gov/REST"


def main() -> None:
    sys.setprofile(record_call)
    threading.setprofile(record_call)
    sys.path.insert(0, str(HERE))
    import httpx
    from conftest import FakeAPI, csv_page
    from records import ongoing_study, results_study

    from TrialLedger import cli

    first, second = (results_study(), ongoing_study())
    first["protocolSection"]["descriptionModule"]["detailedDescription"] = "a bell\x07 no cell can hold"
    ids = [s["protocolSection"]["identificationModule"]["nctId"] for s in (first, second)]
    api = FakeAPI(
        json_pages=[
            httpx.Response(503),
            httpx.Response(200, json={"studies": [first], "totalCount": 2, "nextPageToken": "page-2"}),
            httpx.Response(200, json={"studies": [second]}),
        ],
        csv_pages=[csv_page(ids[:1], total=2, token="page-2", header=True), csv_page(ids[1:])],
    )
    scratch = Path(tempfile.mkdtemp())
    out = scratch / "run"

    def sandbox(url, **kwargs):
        if "rxnav" in url:
            raise ConnectionRefusedError("egress blocked")
        return httpx.Response(200)

    def rxclass(url, params):
        return classes_of(params["rxcui"]) if url.endswith("/byRxcui.json") else rxnav(url, params)

    try:
        codes = {"doctor": cli.main(["doctor", "--run", str(scratch / "doctor")], probe_get=sandbox)}
        codes["pull"] = cli.main(
            ["pull", f"filter.ids={','.join(ids)}", "--out", str(out)], http=api.client(), sleep=api.sleep
        )
        codes["verify"] = cli.main(["verify", str(out)])
        pair = [near_miss_study(nct, ecog) for nct, ecog in (("NCT09000001", "0-1"), ("NCT09000002", "0-2"))]
        codes |= landscape_runs(scratch, [first, second, *pair], rxclass, sandbox)
        premise = scratch / "premises.json"
        premise.write_text(json.dumps({"operation": "coordinates", "domain": "nsclc", "evidence": []}))
        codes["reason"] = cli.main(["reason", "--request", str(premise)])
        broken = scratch / "broken"
        shutil.copytree(out, broken)
        (broken / "review.xlsx").write_bytes(b"not a workbook")
        codes["verify_unreadable"] = cli.main(["verify", str(broken)])
        failing = FakeAPI(json_pages=[httpx.Response(503)] * 4)
        codes["failed_pull"] = cli.main(
            ["pull", "filter.ids=NCT01234567", "--out", str(scratch / "never")],
            http=failing.client(),
            sleep=failing.sleep,
        )
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
        shutil.rmtree(scratch)
    unreached = sorted((f"{file}: {name}" for file, name in defined() - CALLED))
    print(
        "WIRING "
        + json.dumps(
            {
                "codes": codes,
                "called": sorted((f"{file}: {name}" for file, name in CALLED)),
                "unreached": unreached,
            }
        )
    )


if __name__ == "__main__":
    main()
