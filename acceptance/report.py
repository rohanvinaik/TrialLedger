"""Layer one's acceptance test, step 4: the report, written from the run's result files.

`.venv/bin/python -m acceptance.compare report --date D` (or `-m acceptance.report --date D`) writes
`acceptance/report-<D>.md` from `acceptance/selection.json`, `runs/<D>/fetch.json`, `runs/<D>/results.json`,
`runs/<D>/defects.json` (and `runs/<D>/defects-first-version.json` when kept) and the reader's authored causes
in `acceptance/causes-<D>.json`. Every number in the report is read from those files; the causes are the only
prose written after the results were seen, and each is keyed to the kind of result it explains.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = ("agree", "differ", "not_comparable", "omitted", "duplicated")
# How a column that is not compared as a field is nevertheless read by the comparison, where it is.
READ_AS = {
    "NCT Number": "the row's study; its link is compared (c-links)",
    "Location": "the row's element; the rows are compared with the records' elements (c-rows)",
    "Whole Text": "compared with eligibilityCriteria when the text is not split (c)",
    "Before the Inclusion Heading": "the three parts joined are compared with eligibilityCriteria (c)",
    "Inclusion Criteria": "the three parts joined are compared with eligibilityCriteria (c)",
    "Exclusion Criteria": "the three parts joined are compared with eligibilityCriteria (c)",
    "Eligibility › Split": "decides which of the two eligibility checks applies (c)",
}
NAMES = {
    "a": "(a) record.xlsx Record rows: Value against the raw JSON at the row's Location",
    "a-leaves": "(a) every leaf of the raw JSON against record.xlsx's rows (omitted, duplicated)",
    "a-title": "(a) record.xlsx Field against the registry's title for the field (/studies/metadata)",
    "a-role": "(a) record.xlsx Role: each facet it states against the record's enclosing elements",
    "b-json": "(b) the API's CSV against the raw JSON, by the documented columns",
    "b-workbook": "(b) the API's CSV single-field columns against record.xlsx",
    "c": "(c) review.xlsx columns declared stated from one registry field, against that field",
    "c-form": "(c) review.xlsx stated columns giving the row's place or a declared form of one field",
    "c-rule": "(c) review.xlsx computed Participants at Risk and At Risk Source, against their declared rule",
    "c-declared": "(c) each column compared, against the status and source review.xlsx's About declares",
    "c-rows": "(c) review.xlsx rows against the records' elements of each sheet's kind",
    "c-links": "(c) review.xlsx links against the registry's own forms (study page, PubMed, document copy)",
    "d": "(d) studies.csv against the API's CSV, byte for byte, then line by line",
    "e": "(e) trialledger verify on the pulled folder",
    "f": "(f) studies.json's records against the records fetched independently",
    "g": "(g) the workbooks' About provenance against the registry's /version, the selection and the records",
}
# How record.xlsx's Record columns are read by the comparison.
RECORD_READ_AS = {
    "Record › NCT Number": "the row's study; a row naming a study not fetched differs (a)",
    "Record › Category": "not compared",
    "Record › Field": "against the registry's title for the field (a-title)",
    "Record › Location": "the place the Value is compared at; every leaf is held once (a, a-leaves)",
    "Record › Value": "against the raw JSON at the Location (a)",
    "Record › Role": "each facet against the record's enclosing elements (a-role); see below",
}


def read_as(column: str) -> str:
    """How the comparison reads a review.xlsx column it does not compare as a field, if it reads it at all."""
    sheet, _, name = column.partition(" › ")
    if sheet in ("Checks", "Check Rules"):
        return "TrialLedger's edit checks, not registry fields; not read"
    return READ_AS.get(name, READ_AS.get(column, "not compared"))


def short(value: object, width: int = 90) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text.replace("\n", "⏎").replace("|", "\\|")
    return text if len(text) <= width else text[: width - 1] + "…"


def totals(fields: dict) -> dict:
    out: dict[str, int] = {}
    for cell in fields.values():
        for key, value in cell.items():
            if key != "studies":
                out[key] = out.get(key, 0) + value
    return out


def cause_for(causes: dict, comparison: str, field: str, result: str) -> str:
    return (
        causes.get(f"{comparison}|{field}|{result}")
        or causes.get(f"{comparison}|*|{result}")
        or ("Not established from the data.")
    )


def write_report(date: str) -> Path:
    run = HERE / "runs" / date
    selection = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
    fetch = json.loads((run / "fetch.json").read_text(encoding="utf-8"))
    results = json.loads((run / "results.json").read_text(encoding="utf-8"))
    defects = json.loads((run / "defects.json").read_text(encoding="utf-8"))
    first_path = run / "defects-first-version.json"
    first = json.loads(first_path.read_text(encoding="utf-8")) if first_path.exists() else None
    causes = json.loads((HERE / f"causes-{date}.json").read_text(encoding="utf-8"))
    summary, issues, provenance = results["summary"], results["issues"], results["provenance"]
    w: list[str] = []
    add = w.append

    grand = {
        key: sum(totals(summary[c]).get(key, 0) for c in summary) for key in (*RESULTS, "of which absent")
    }
    differences = [i for i in issues if i["result"] in ("differ", "omitted", "duplicated")]
    caught = sum(1 for d in defects["defects"] if d["caught"])

    add(f"# Layer one acceptance test, {date}")
    add("")
    add(
        "TrialLedger `add-agent-operation` task 7.1: twenty trials chosen and written down before any "
        "comparison,"
    )
    add(
        "each compared field by field by an independent reader against the registry's own records. "
        "Generated by"
    )
    add(
        f"`acceptance/report.py` from the files of `acceptance/runs/{date}/`; the causes are the reader's, in"
    )
    add(f"`acceptance/causes-{date}.json`.")
    add("")
    add("## In brief")
    add("")
    add(
        f"- {sum(grand[k] for k in RESULTS):,} results over the twenty trials: {grand['agree']:,} agree, "
        f"{grand['differ']:,} differ, {grand['omitted']:,} omitted, {grand['duplicated']:,} duplicated, "
        f"{grand['not_comparable']:,} not comparable."
    )
    a = totals(summary["a"])
    leaves = totals(summary["a-leaves"])
    add(
        f"- record.xlsx: all {a.get('agree', 0):,} values of its Record sheet agree with the raw JSON at "
        "the location "
        f"each names, and every one of the records' {results['leaves']:,} leaves is held by exactly one row "
        f"({leaves.get('agree', 0):,} agree, {leaves.get('omitted', 0)} omitted, "
        f"{leaves.get('duplicated', 0)} "
        "duplicated)."
    )
    c = totals(summary["c"])
    rows = totals(summary["c-rows"])
    add(
        f"- review.xlsx: {c.get('agree', 0):,} cells of columns declared stated from one registry field "
        "agree with it "
        f"({c.get('of which absent', 0):,} of them where the record holds no value and the cell says so), "
        f"{c.get('differ', 0)} differ; {rows.get('omitted', 0)} record elements have no row (see "
        "Differences); "
        f"{totals(summary['c-links']).get('agree', 0):,} links agree."
    )
    form, rule = totals(summary["c-form"]), totals(summary["c-rule"])
    declared = totals(summary["c-declared"])
    add(
        f"- review.xlsx, further: {form.get('agree', 0):,} cells of the stated columns that give a row's "
        f"place or a declared form agree, {form.get('differ', 0)} differ; {rule.get('agree', 0):,} computed "
        f"at-risk counts follow their declared rule, {rule.get('differ', 0)} do not; of the "
        f"{sum(declared.values())} columns compared, {declared.get('agree', 0)} are declared stated from the "
        f"field the reader pairs them with, {declared.get('differ', 0)} are not."
    )
    role, prov = totals(summary["a-role"]), totals(summary["g"])
    add(
        f"- record.xlsx's Role: {role.get('agree', 0):,} roles hold of the record, {role.get('differ', 0)} "
        f"do not, {role.get('not_comparable', 0)} not comparable (see Role, under 'Not comparable, and not "
        "compared'). "
        f"Provenance in the two About sheets: {prov.get('agree', 0)} agree, {prov.get('differ', 0)} differ, "
        f"{prov.get('omitted', 0)} omitted, {prov.get('not_comparable', 0)} not comparable (TrialLedger's "
        "own record of its run)."
    )
    d = summary["d"]
    if "studies.csv byte-order mark" in d and not totals(
        {k: v for k, v in d.items() if k.endswith("line")}
    ).get("differ"):
        add(
            "- studies.csv is the API's CSV with a UTF-8 byte-order mark put before it; otherwise "
            "identical, line "
            "for line."
        )
    else:
        add(f"- studies.csv against the API's CSV: {json.dumps(d)}.")
    verified = summary["e"]["verify"].get("agree") == 1
    add(
        f"- `trialledger verify` {'certifies' if verified else 'does not certify'} the pulled folder "
        f"(`acceptance/runs/{date}/verify-pull.txt`); {summary['f']['record'].get('agree', 0)} of "
        "studies.json's "
        f"{summary['f']['record']['studies']} records equal the records fetched independently."
    )
    add(
        f"- Seeded defects: {caught} of {len(defects['defects'])} caught by the comparisons"
        + ("; the first version of comparison (d) missed one (see Seeded defects)." if first else ".")
    )
    add("")

    add("## What was selected, and how")
    add("")
    add(
        f"Selected {selection['created_at']} (written {selection['written_at']}) by `acceptance/select.py` "
        f"(SHA-256 `{selection['code']['sha256']}`), seed {selection['seed']}, from the live registry (data "
        f"{selection['registry']['version_before']['dataTimestamp']}, API "
        f"{selection['registry']['version_before']['apiVersion']}; the same before and after the draw: "
        f"{selection['registry']['version_before'] == selection['registry']['version_after']}), before "
        "anything "
        "was pulled or compared. Criteria, as written before the draw:"
    )
    add("")
    add("> " + selection["criteria"])
    add("")
    method = selection["method"]
    add(
        f"Each stratum is an Essie expression in `filter.advanced`. A stratum of at most "
        f"{method['whole_stratum_at_most']} studies is read whole; a larger one is narrowed to a seeded "
        "month of first "
        f"posting ({method['months']}; to its year when the month holds none; up to {method['max_windows']} "
        f"windows), and one ID is chosen by `{method['choice']}`. Two strata keep the largest or the "
        "smallest "
        f"record (bytes of its JSON) of {method['size_draws']} draws. Every expression, count, window and "
        "candidate "
        "is in `acceptance/selection.json`."
    )
    add("")
    add(
        "| # | Stratum | NCT | Phases | Overall status | Study type | Results | Lead sponsor class | "
        "Bytes | Aliases |"
    )
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for n, fact in enumerate(selection["facts"], start=1):
        add(
            f"| {n} | {fact['stratum']} | {fact['nctId']} | {', '.join(fact['phases']) or '(none)'} | "
            f"{fact['overallStatus']} | {fact['studyType']} | {'posted' if fact['hasResults'] else 'none'} | "
            f"{fact['leadSponsorClass']} | {fact['recordBytes']:,} | "
            f"{', '.join(fact['nctIdAliases']) or ''} |"
        )
    add("")
    cov = selection["coverage"]
    add("Coverage: " + "; ".join(f"{k} {json.dumps(v)}" for k, v in cov.items()) + ".")
    add("")

    add("## The run")
    add("")
    pull = fetch["pull"]
    add(
        f"- Pull: `{' '.join(pull['command'][:2])} filter.ids=<the twenty> --out "
        f"acceptance/runs/{date}/pull`, "
        f"exit {pull['exit']}, {pull['started_at']} to {pull['finished_at']}; "
        f"{provenance.get('tool')}, code commit `{provenance.get('code_commit')}`, code root "
        f"`{provenance.get('code_root')}`; registry data {provenance.get('data_timestamp')}, API "
        f"{provenance.get('api_version')}; every requested ID `found` "
        f"({sum(1 for r in provenance.get('requested_ids', []) if r['status'] == 'found')} of 20)."
    )
    for key, label in (("json", "JSON"), ("csv", "CSV")):
        f = fetch[key]
        add(
            f"- Independent {label}: `{f['url']}`, HTTP {f['status']}, requested {f['requested_at']}, "
            "received "
            f"{f['received_at']}, {f['bytes']:,} bytes, SHA-256 `{f['sha256']}` "
            f"(`acceptance/runs/{date}/{f['file']}`)."
        )
    before = json.loads((run / "independent" / "version-before.json").read_text())
    after = json.loads((run / "independent" / "version-after.json").read_text())
    add(f"- Registry /version before the pull {json.dumps(before)}, after the fetches {json.dumps(after)}.")
    add(
        f"- Compared {results['compared_at']} by `acceptance/compare.py` (SHA-256 "
        f"`{results['code']['sha256']}`): "
        f"{results['record_rows']:,} Record rows, {results['leaves']:,} JSON leaves, review.xlsx rows "
        + ", ".join(f"{k} {v}" for k, v in results["review_rows"].items())
        + "."
    )
    add("")

    add("## Results by comparison")
    add("")
    add(
        "Each comparison names a result per field per study; the per-field counts over the twenty trials "
        "are in "
        "the appendix. *Absent* counts agreements where the record holds no value and the cell says so "
        "(blank, "
        '"not reported", "not applicable to this study type").'
    )
    add("")
    add("| Comparison | Fields | Agree | of which absent | Differ | Omitted | Duplicated | Not comparable |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for comparison, fields in summary.items():
        t = totals(fields)
        add(
            f"| {NAMES.get(comparison, comparison)} | {len(fields)} | {t.get('agree', 0):,} | "
            f"{t.get('of which absent', 0):,} | {t.get('differ', 0):,} | {t.get('omitted', 0):,} | "
            f"{t.get('duplicated', 0):,} | {t.get('not_comparable', 0):,} |"
        )
    add("")

    add("## Differences, each with its cause")
    add("")
    groups: dict[tuple, list] = {}
    for item in differences:
        groups.setdefault((item["comparison"], item["field"], item["result"]), []).append(item)
    for (comparison, field, result), items in sorted(groups.items()):
        studies = sorted({i["nct"] for i in items})
        add(f"### {NAMES.get(comparison, comparison).split(' ', 1)[0]} {field}: {result} ({len(items)})")
        add("")
        add(f"Studies: {', '.join(studies)}.")
        add("")
        add("| Study | Where | Why | Expected (registry) | Found |")
        add("| --- | --- | --- | --- | --- |")
        for item in items:
            add(
                f"| {item['nct']} | {short(item['where'], 70)} | {short(item['why'], 80)} | "
                f"{short(item['expected'])} | {short(item['found'])} |"
            )
        add("")
        add("Cause: " + cause_for(causes, comparison, field, result))
        add("")

    add("## Not comparable, and not compared")
    add("")
    nc: dict[tuple, int] = {}
    for item in issues:
        if item["result"] == "not_comparable":
            nc[(item["comparison"], item["why"])] = nc.get((item["comparison"], item["why"]), 0) + 1
    for (comparison, why), count in sorted(nc.items()):
        fields = sorted({i["field"] for i in issues if i["comparison"] == comparison and i["why"] == why})
        add(
            f"- {NAMES.get(comparison, comparison)}: {count:,} results, {len(fields)} fields: {why}. "
            + cause_for(causes, comparison, "*", "not_comparable")
        )
        add(f"  Fields: {', '.join(f'`{f}`' for f in fields)}.")
    add(
        "- record.xlsx's columns, each with the status and source its About sheet declares, and how the "
        "comparison reads it:"
    )
    add("")
    add("| Column | Declared status | Declared source | Read here as |")
    add("| --- | --- | --- | --- |")
    for row in results["record_columns"]:
        add(
            f"| {row['column']} | {row['status']} | {short(row['declared_source'], 140)} | "
            f"{RECORD_READ_AS.get(row['column'], 'not compared')} |"
        )
    add("")
    add("  " + causes["record_role"])
    add("")
    add(
        "- review.xlsx columns not compared as values, each with the status and source the workbook declares "
        "for it and how the comparison reads it, if at all (a column whose declared status is computed, "
        "needs review or warrant is TrialLedger's rule or its warrant, not a field of the record; a stated "
        "column here is the row's study, its place, or TrialLedger's edit checks):"
    )
    add("")
    add("| Column | Declared status | Declared source | Read here as |")
    add("| --- | --- | --- | --- |")
    for row in results["not_compared_columns"]:
        add(
            f"| {row['column']} | {row['status']} | {short(row['declared_source'], 140)} | "
            f"{read_as(row['column'])} |"
        )
    add("")

    add("## Seeded defects")
    add("")
    add(
        f"A copy of the pulled folder (`acceptance/runs/{date}/defects-copy/`, regenerated by "
        f"`python -m acceptance.compare defects --date {date}` and not kept) was given the defects below, "
        "then "
        "compared exactly as the original. A defect is caught when a result the clean run does not have "
        "names its "
        "study and its place. Every comparison of the copy is against the same registry records."
    )
    add("")
    add("| # | Kind | File | Planted | Caught | By |")
    add("| --- | --- | --- | --- | --- | --- |")
    for d in defects["defects"]:
        by = "; ".join(
            f"{h['comparison']} {h['nct']} {short(h['where'], 60)}: {h['result']}" for h in d["caught_by"]
        )
        add(
            f"| {d['id']} | {d['kind']} | {d['file']} | {short(d['what'], 100)} | "
            f"{'yes' if d['caught'] else '**no**'} | {short(by, 200)} |"
        )
    add("")
    add(f"New results not attributed to a planted defect: {len(defects['unattributed'])}.")
    verify_copy = defects["verify_on_copy"][0] if defects["verify_on_copy"] else None
    if verify_copy:
        add(
            "`trialledger verify` on the defective copy (TrialLedger's own check, not this reader's): "
            f"{'certified' if verify_copy['result'] == 'agree' else 'not certified'}; "
            f"{short(verify_copy['why'], 200)}."
        )
    if first:
        missed = [d for d in first["defects"] if not d["caught"]]
        add("")
        add(
            f"The first version of the comparison caught {len(first['defects']) - len(missed)} of "
            f"{len(first['defects'])} (`acceptance/runs/{date}/defects-first-version.json`). It missed: "
            + "; ".join(f"#{d['id']} {d['kind']} in {d['file']} ({d['what']})" for d in missed)
            + ". Comparison (d) then compared studies.csv with the API's CSV only as a whole file; since "
            "the clean "
            "file already differs (the byte-order mark), a further change could not show as a new result. "
            "(d) now "
            "names the byte-order mark on its own and compares the rest line by line, and the same defect is "
            "caught at its line. That a whole-file check already failing hides every later change in that "
            "file is "
            "itself a finding about how such checks must be read."
        )
    add("")

    add("## Changes to the reader after the first comparison")
    add("")
    add(
        "Reported because the test is reported as it falls: every change made to the reader (compare.py) "
        "after it first compared the twenty, each the reader's own error or gap; none changed a TrialLedger "
        "output, and the results above are the revised reader's."
    )
    add("")
    for change in causes.get("reader_changes", []):
        add("- " + change)
    add("")

    add("## What this establishes, and what it cannot")
    add("")
    add(
        "Establishes, for these twenty trials, on the registry's data of "
        f"{provenance.get('data_timestamp')} and TrialLedger at commit `{provenance.get('code_commit')}`:"
    )
    add("")
    add(
        "- record.xlsx transcribes the registry's JSON faithfully: every value at the location it names, "
        "as the "
        "same value of the same kind, and every value of the record exactly once."
    )
    add(
        "- review.xlsx's columns that declare one registry field as their source hold that field's value "
        "(or say it is absent where the record holds none); the stated columns that give a row's place hold "
        "it; its computed at-risk counts follow their declared rule; its rows stand for the records' "
        "elements of each kind once each; and its study, publication and document links are the registry's "
        "own forms of them; each with the exceptions named under Differences."
    )
    add(
        "- record.xlsx's Role states nothing the record does not hold: every facet it names is a value of an "
        "element enclosing the row's location. The workbooks' About sheets state the registry's API version, "
        "data date, the query and the study count as the registry and the selection give them, and account "
        "for every requested ID once."
    )
    add(
        "- studies.json holds the records exactly as the registry sends them; studies.csv holds the "
        "registry's "
        "CSV, with a byte-order mark added."
    )
    add(
        "- The comparisons find each kind of defect planted here (a changed text, number or date, a "
        "truncated "
        "text, a dropped or duplicated row, a swapped pair, a changed link), so a defect of these kinds "
        "in the "
        "outputs compared would have been seen."
    )
    add("")
    add("Cannot establish:")
    add("")
    add(
        "- Anything about clinical meaning: whether a value is clinically right, whether a trial is "
        "relevant to a "
        "question, or anything the readings of `trialledger resolve` compute (criteria, settings, the "
        "profile); "
        "they were not compared."
    )
    add(
        "- The registry's own correctness: the reference is the registry's record as the API sent it. "
        "Where the "
        "registry's CSV departs from its documentation (the Age column), that is recorded, not judged."
    )
    add(
        "- How TrialLedger compares with human transcribers: no person transcribed these trials here; the "
        "reader is a program written from the registry's documentation, and its own errors would show as "
        "differences or, worse, as agreements it should not have given (the seeded defects bound that "
        "risk for "
        "the kinds planted, not for every kind)."
    )
    add(
        "- Other trials, other data dates or other code: twenty trials across the strata above are a test of "
        "the mapping's breadth, not a measured error rate. Columns computed by TrialLedger's rules (other "
        "than the at-risk count), record.xlsx's Category, and the fields named under Not comparable were not "
        "checked against the registry."
    )
    add(
        "- That the reader chose its pairings independently: which registry field each review.xlsx column "
        "holds, the text forms of the c-form columns and the facet names of record.xlsx's Role were "
        "transcribed from the workbooks' own About sheets and values. What is independent is resolving each "
        "named field in the registry's JSON and comparing; c-declared shows the pairings match the "
        "declarations, so a column paired with the wrong field by both would not be seen."
    )
    add(
        "- That a Role names every facet it should: a-role checks that what a Role states holds, not that a "
        "row without a facet should have had one."
    )
    add(
        "- Fine order inside the API's CSV columns that join several fields (Age, Study Design, Other IDs, "
        "Locations, Study Documents and the outcome columns): (b) checks each documented piece appears "
        "somewhere in the cell, so a swap of pieces between two sites or two outcomes in the same cell would "
        'not be seen there. The list join ("|") and the Interventions form ("type: name") were read from '
        "the CSV itself and are then compared exactly."
    )
    add(
        "- The registry's own page: the comparison is with the API's JSON and CSV, the sources TrialLedger "
        "reads, not with the HTML study page."
    )
    add("")

    add("## Reproducing it")
    add("")
    add(
        "From the repository's root: `.venv/bin/python -m acceptance.select` (refuses to overwrite the "
        "frozen "
        f"selection), `.venv/bin/python -m acceptance.compare run --date {date}` (live; refuses an "
        "existing run), "
        f"then `compare`, `defects` and `report` with the same date (offline), and `.venv/bin/python -m "
        f"acceptance.probe_bom --date {date}` (live) for the byte-order-mark probe. The comparison logic "
        "is tested "
        "without the network in `tests/test_acceptance.py`."
    )
    add("")

    add("## Appendix: results per field over the twenty trials")
    add("")
    for comparison, fields in summary.items():
        add(f"### {NAMES.get(comparison, comparison)}")
        add("")
        add("| Field | Studies | Agree | of which absent | Differ | Omitted | Duplicated | Not comparable |")
        add("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for field, cell in fields.items():
            add(
                f"| `{short(field, 120)}` | {cell.get('studies', 0)} | {cell.get('agree', 0)} | "
                f"{cell.get('of which absent', 0)} | {cell.get('differ', 0)} | {cell.get('omitted', 0)} | "
                f"{cell.get('duplicated', 0)} | {cell.get('not_comparable', 0)} |"
            )
        add("")
    path = HERE / f"report-{date}.md"
    path.write_text("\n".join(w).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    print(write_report(args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
