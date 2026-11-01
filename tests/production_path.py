"""The production path, driven end to end with every function call recorded. Run as a script, it prints, as
one JSON line after "WIRING ", the exit codes of its commands and every function of the package that none of
them reached; tests/test_wiring.py holds that set to the declared one.

The profiler starts before TrialLedger is imported, so the tables built at import are reached. The path is
what production does: `trialledger pull` over two pages, with a retry and a value a cell cannot hold;
`trialledger verify` of the folder written; `trialledger profile` of it, with RxClass answering for one source
and failing for the other, and RxNav resolving an ingredient, a brand and a combination and answering ATC and
structure classes (asked only for the experimental drugs' names); `profile` of a folder that is no record; a
live `resolve` with a near-miss pair, an aligned pair, a shared structure class, an own name RxNorm does not
hold beside a combination alias, a target the drug's own entry states and a genetic CAR-T entry, rendered as
the JSON and design.xlsx with its Drug Axes sheet; `sample`, `audit` and `pilot`; `verify` of a folder whose
workbook is unreadable; and a pull the server keeps failing.
"""

import ast
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "TrialLedger"
CALLED: set[tuple[str, str]] = set()


def record_call(frame, event, _arg):
    if event == "call" and frame.f_code.co_filename.startswith(str(PACKAGE)):
        CALLED.add((Path(frame.f_code.co_filename).name, frame.f_code.co_qualname))


def defined() -> set[tuple[str, str]]:
    """Every function, method and lambda the package defines, by file and qualified name."""
    found: set[tuple[str, str]] = set()
    for path in sorted(PACKAGE.glob("*.py")):

        def walk(node: ast.AST, prefix: str, file: str = path.name) -> None:
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
        f"* ECOG performance status {ecog}\n\nKey Exclusion Criteria:\n\n* Active autoimmune disease\n"
    )
    protocol["armsInterventionsModule"] = {
        "armGroups": [{"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: Placebo"]}],
        "interventions": [{"type": "DRUG", "name": "Placebo"}],
    }
    return study


def audited_study() -> dict:
    """A trial with every kind of audit unit: a criterion no bank types (NCT04382755's), outcomes with an
    endpoint class, a window ("up to") and an unmarked time point (NCT04693377's), an experimental drug only
    its own entry classifies (anti-PD-1) beside one RxClass classifies."""
    from records import ongoing_study

    study = ongoing_study()
    protocol = study["protocolSection"]
    protocol["identificationModule"]["nctId"] = "NCT09000004"
    protocol["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* ECOG performance status 0-1\n\n"
        "Exclusion Criteria:\n\n* History of active or past meningococcal disease\n"
    )
    protocol["outcomesModule"] = {
        "primaryOutcomes": [
            {"measure": "Duration of response", "timeFrame": "Up to 24 weeks post-treatment"}
        ],
        "secondaryOutcomes": [{"measure": "Pain response", "timeFrame": "At 12 weeks post-treatment"}],
    }
    protocol["armsInterventionsModule"] = {
        "armGroups": [
            {"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: XB-1", "Drug: Placebo"]}
        ],
        "interventions": [
            {"type": "DRUG", "name": "XB-1", "description": "XB-1 is an anti-PD-1 antibody"},
            {"type": "DRUG", "name": "Placebo"},
        ],
    }
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


def axis(params: dict) -> tuple[int, dict]:
    """RxClass's ATC and structure answers: PD-1/PD-L1 inhibitors (ATC) and platinum-containing compounds
    (structure) for the names RxNorm resolves, each about the ingredient, as RxClass answers a brand."""
    subject = SUBJECTS.get(params["drugName"])
    if subject is None:
        return 200, {}
    if params["relaSource"] == "ATC":
        item = {"classId": "L01FF", "className": "PD-1/PD-L1 inhibitors", "classType": "ATC1-4"}
    else:
        item = {"classId": "N0000175073", "className": "Platinum-containing Compounds", "classType": "CHEM"}
    entry = {
        "minConcept": {"rxcui": subject[0], "name": subject[1], "tty": "IN"},
        "rxclassMinConceptItem": item,
        "rela": params.get("relas", ""),
        "relaSource": params["relaSource"],
    }
    return 200, {"rxclassDrugInfoList": {"rxclassDrugInfo": [entry]}}


def sample_and_audit(scratch: Path, studies: list[dict], rxclass) -> dict[str, int]:
    """`trialledger sample` over every stratum (id-only pages from one snapshot) and `trialledger audit` of
    the draw, one trial at a time, with a local model that answers each question in its own kind's schema
    (every kind: atom claims, an untyped criterion, outcome endpoints and time points, a stated target; the
    RxClass answers used kept in the audit folder and an assignment checked against that kept copy, not asked)
    and is released at the end; its balance table asks the registry about every empty cell and audits the one
    supplement drawn.
    """
    import httpx
    from conftest import version

    from TrialLedger import cli
    from TrialLedger.ingest import API_BASE

    by_id = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in [*studies, audited_study()]}
    # the Neoplasms stratum holds every one of these trials; the discovery draw takes only the unreserved,
    # and a confirmation draw of batch 1 (add-bank-coverage B8) takes NCT09000002, the one in that batch
    frame = list(by_id)
    # a screening trial outside the strata's draw: the registry holds it for the one empty cell it fills, so
    # the balance check asks every empty cell, finds one gap in the registry and audits its supplement
    screening = near_miss_study("NCT09000003", "0-1")
    screening["protocolSection"]["designModule"] = {
        "studyType": "INTERVENTIONAL",
        "phases": ["PHASE2", "PHASE3"],
        "designInfo": {"primaryPurpose": "SCREENING"},
    }
    by_id["NCT09000003"] = screening

    def route(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/version":
            return version()
        params = request.url.params
        if params.get("fields") == "NCTId":
            where = params.get("filter.advanced", "")
            if "AREA[DesignPrimaryPurpose]SCREENING" in where:
                ids = ["NCT09000003"]
            elif "AREA[Phase]" in where or "AREA[InterventionType]" in where or "AREA[Design" in where:
                ids = []
            else:
                ids = frame if "Neoplasms" in where else []
            page = [{"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in ids]
            return httpx.Response(200, json={"studies": page, "totalCount": len(ids)})
        nct = params.get("filter.ids", "")
        return httpx.Response(200, json={"studies": [by_id[nct]], "totalCount": 1})

    registry = httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(route), follow_redirects=False)

    def ollama(method, url, body, timeout):
        if url.endswith("/api/ps"):
            return {"models": []}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b", "digest": "a" * 64}]}
        operation = json.loads(json.loads(body).get("prompt", "{}")).get("operation") if body else None
        if operation == "untyped_criterion":
            instance = {"option": "out_of_taxonomy", "quote": "meningococcal disease"}
            return {"response": json.dumps({"instances": [instance]}), "done_reason": "stop"}
        if operation == "intervention_target":
            return {
                "response": json.dumps({"verdict": "supported", "quote": "anti-PD-1"}),
                "done_reason": "stop",
            }
        return {
            "response": json.dumps({"verdict": "insufficient_context", "quote": ""}),
            "done_reason": "stop",
        }

    sample = scratch / "sample.json"
    codes = {
        "sample": cli.main(
            ["sample", "--seed", "s", "--per-stratum", "3", "--out", str(sample)],
            http=registry,
            sleep=lambda s: None,
        )
    }
    # a confirmation draw (Decision 9, B4; B8) excludes the discovery sample just drawn, needs clean code at a
    # commit (a fake git answers for this run, whose tree is being edited; the refused draw asks the real git)
    # and records its batch in the ledger of used batches
    ledger = scratch / "ledger.json"
    ledger.write_text(json.dumps({"batches": {}}), encoding="utf-8")
    confirmation = ["sample", "--seed", "s", "--per-stratum", "1", "--inspected", str(sample)]
    confirmation += ["--batch-ledger", str(ledger), "--confirmation-batch"]
    answers = {"rev-parse": "c" * 40 + "\n", "status": "", "ls-files": "TrialLedger/sample.py\0"}
    codes["sample_confirmation"] = cli.main(
        [*confirmation, "1", "--out", str(scratch / "confirmation.json")],
        http=registry,
        sleep=lambda s: None,
        git=lambda root, *args: answers[args[0]],
    )
    codes["sample_confirmation_refused"] = cli.main(
        [*confirmation, "3", "--out", str(scratch / "refused.json")], http=registry, sleep=lambda s: None
    )
    codes["audit"] = cli.main(
        ["audit", str(sample), "--out", str(scratch / "audit"), "--model", "qwen3:8b", "--budget", "50"],
        http=registry,
        sleep=lambda s: None,
        rxclass_get=rxclass,
        model_http=ollama,
    )
    codes["pilot"] = cli.main(
        [
            "pilot",
            str(scratch / "audit"),
            "--label",
            "2",
            "--mutate",
            "2",
            "--model",
            "qwen3:8b",
            "--budget",
            "50",
        ],
        model_http=ollama,
    )
    codes["audit_no_budget"] = cli.main(
        ["audit", str(sample), "--out", str(scratch / "nobudget"), "--model", "qwen3:8b"], model_http=ollama
    )
    codes["audit_refused"] = cli.main(
        ["audit", str(sample), "--out", str(scratch / "refused"), "--model", "absent:1b", "--budget", "5"],
        model_http=ollama,
    )
    return codes


def main() -> None:
    sys.setprofile(record_call)
    sys.path.insert(0, str(HERE))
    import httpx
    from conftest import FakeAPI, csv_page
    from records import ongoing_study, results_study

    from TrialLedger import cli

    first, second = results_study(), ongoing_study()
    first["protocolSection"]["descriptionModule"]["detailedDescription"] = "a bell\x07 no cell can hold"
    first["protocolSection"]["descriptionModule"]["a key with a bell\x07"] = "and a value with one\x07"
    # an experimental drug only its own description classifies (anti-PD-1), so the stated-target fallback
    # and the checkpoint-blocker expectation are both on the path
    # and a genetic intervention whose own entry states a CAR-T product, so the modality facets and the cell
    # properties are read
    second["protocolSection"]["armsInterventionsModule"] = {
        "armGroups": [
            {"label": "XB-1", "type": "EXPERIMENTAL", "interventionNames": ["Drug: XB-1", "Genetic: XB-2"]}
        ],
        "interventions": [
            {
                "type": "DRUG",
                "name": "XB-1",
                "otherNames": ["XB-1 + carboplatin"],
                "description": "XB-1 is an anti-PD-1 antibody",
            },
            {"type": "GENETIC", "name": "XB-2", "description": "Autologous CAR-T cells, ex vivo expanded"},
        ],
    }
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in (first, second)]
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
    query = f"filter.ids={','.join(ids)}"
    codes = {"pull": cli.main(["pull", query, "--out", str(out)], http=api.client(), sleep=api.sleep)}
    codes["verify"] = cli.main(["verify", str(out)])

    def rxclass(url, params):
        # RxNav: RxNorm resolves Testamab and Placebo as ingredients, TM-1 as Testamab's brand (an alias that
        # confirms its own name) and "XB-1 + carboplatin" as a combination (an alias that cannot resolve XB-1,
        # which RxNorm does not hold); ATC and structure classes come back for the first three, so a known
        # class, a shared structure class and an aligned pair are all reached.
        if not url.endswith("/byDrugName.json"):
            return rxnav(url, params)
        if params.get("relas") == "has_chemical_structure" or params["relaSource"] == "ATC":
            return axis(params)
        # DailyMed knows only "Placebo" (one class), so the experimental drug falls back to what its record
        # states; MED-RT fails: an answer, an unknown name and a failure are all reached.
        if params["relaSource"] == "DAILYMED" and params["drugName"] == "Placebo":
            item = {"classId": "N0000191260", "className": "Programmed Death Receptor-1 Blocking Antibody"}
            body = {
                "rxclassDrugInfoList": {
                    "rxclassDrugInfo": [
                        {"rxclassMinConceptItem": item, "rela": "has_epc", "relaSource": "DAILYMED"}
                    ]
                }
            }
            return 200, body
        return (200, {}) if params["relaSource"] == "DAILYMED" else (503, None)

    codes["profile"] = cli.main(["profile", str(out)], rxclass_get=rxclass)
    codes["profile_not_a_record"] = cli.main(["profile", str(scratch / "nothing here")], rxclass_get=rxclass)
    os.environ["TRIALLEDGER_CACHE"] = str(scratch / "cache" / "classes.json")
    # two first-line trials of the one drug RxClass classifies, differing only in the ECOG they admit: a
    # near-miss pair, so the pairing and its ordering are on the path
    pair = [near_miss_study(nct, ecog) for nct, ecog in (("NCT09000001", "0-1"), ("NCT09000002", "0-2"))]
    live = FakeAPI(
        json_pages=[httpx.Response(200, json={"studies": [first, second, *pair], "totalCount": 4})]
    )
    codes["resolve"] = cli.main(
        [
            "resolve",
            query + ",NCT09000001,NCT09000002",
            "--json",
            str(scratch / "reading.json"),
            "--out",
            str(scratch / "design.xlsx"),
        ],
        http=live.client(),
        sleep=live.sleep,
        rxclass_get=rxclass,
    )
    codes |= sample_and_audit(scratch, pair, rxclass)
    broken = scratch / "broken"
    shutil.copytree(out, broken)
    (broken / "review.xlsx").write_bytes(b"not a workbook")
    codes["verify_unreadable"] = cli.main(["verify", str(broken)])
    failing = FakeAPI(json_pages=[httpx.Response(503)] * 4)
    never = scratch / "never"
    codes["failed_pull"] = cli.main(
        ["pull", "filter.ids=NCT01234567", "--out", str(never)], http=failing.client(), sleep=failing.sleep
    )
    sys.setprofile(None)
    shutil.rmtree(scratch)
    unreached = sorted(f"{file}: {name}" for file, name in defined() - CALLED)
    print("WIRING " + json.dumps({"codes": codes, "unreached": unreached}))


if __name__ == "__main__":
    main()
