"""The production path, driven end to end with every function call recorded. Run as a script, it prints, as
one JSON line after "WIRING ", the exit codes of its commands and every function of the package that none of
them reached; tests/test_wiring.py holds that set to the declared one.

The profiler starts before TrialLedger is imported, so the tables built at import are reached. The path is
what production does: `trialledger pull` over two pages, with a retry and a value a cell cannot hold;
`trialledger verify` of the folder written; `trialledger profile` of it, with RxClass answering for one source
and failing for the other; `profile` of a folder that is no record; `verify` of a folder whose workbook is
unreadable; and a pull the server keeps failing.
"""

import ast
import json
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
