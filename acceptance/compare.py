"""Layer one's acceptance test, step 2: an independent reader compares TrialLedger's pull with the registry.

Run from the repository's root, as a module (`.venv/bin/python -m acceptance.compare <step> --date D`):

- `run` (live): runs `trialledger pull filter.ids=<the twenty of acceptance/selection.json>` into
  `acceptance/runs/<D>/pull/`, then fetches the same twenty records independently from the registry's API, as
  JSON (`format=json`) and as the API's own CSV (`format=csv`), each body saved exactly as received with its
  retrieval time and SHA-256, and the registry's /version before and after.
- `compare` (offline, over the saved files): every comparison below, written to `runs/<D>/results.json`.
- `defects` (offline): copies the pulled folder, plants defects of different kinds, compares the copy the
  same way and names, for each defect, whether a comparison caught it (`runs/<D>/defects.json`).
- `report`: writes `acceptance/report-<D>.md` from the two result files and the authored causes in
  `acceptance/causes-<D>.json`.

The comparisons, each naming its result per field (agree; differ, with both values; not comparable, with why;
omitted; duplicated):

- (a) record.xlsx's Record sheet against the raw JSON: every row's Value against the value at the Location the
  row names (transcription fidelity), its Field against the registry's own title for that field
  (`TrialLedger/registry/ctg-metadata.json`, the API's /studies/metadata); every leaf of the raw JSON
  against the rows (nothing omitted, nothing duplicated); and every facet a row's Role states (`arm=`,
  `group=`, ...) against the record's elements enclosing the row's Location (a-role).
- (b) the API's CSV against the raw JSON, by the registry's documented columns (`acceptance/csv-columns.md`),
  an independent flattening; and its single-field columns against record.xlsx.
- (c) review.xlsx: each column declared `stated` from one registry field against that field; the stated
  columns whose value is the row's place in the record or a declared form of one field (c-form); the computed
  Participants at Risk and At Risk Source against the rule the workbook declares for them (c-rule); the rows
  of each sheet against the records' elements of that kind (nothing omitted, nothing duplicated); each link
  against the registry's own form of it; and every column this reader compares against the status and
  source review.xlsx's About sheet declares for it (c-declared).
- (d) studies.csv byte for byte against the API's CSV fetched independently.
- (e) `trialledger verify` on the pulled folder.
- (f) studies.json's records against the independently fetched JSON, record by record.
- (g) the provenance both workbooks' About sheets state (API version, data date, query, study count, each
  requested ID's status) against the registry's /version, the selection and the records fetched here.

Independence: nothing here imports or reads TrialLedger's code or tests. The pull is run as a black box (the
installed `trialledger` command), and its outputs are read as files. What the reader took from those outputs:
review.xlsx's sheet and column names, and which registry field each column declares as its source, were
transcribed into `REVIEW_SHEETS` from review.xlsx's own About sheet. The pairing of a column with a field is
therefore TrialLedger's declaration, not this reader's; what is independent is resolving the field in the
registry's raw JSON and comparing the cell with it. Comparison c-declared compares every pairing with the
About sheet's declaration, so a pairing here that departs from it shows as a difference. The text forms of the
c-form columns ("milestone", "name (class)", ...) and the facet names of record.xlsx's Role were likewise
read from the workbooks; the reader checks that what they state holds in the record.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

API = "https://clinicaltrials.gov/api/v2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SELECTION = HERE / "selection.json"
METADATA = ROOT / "TrialLedger" / "registry" / "ctg-metadata.json"
STUDY_URL = "https://clinicaltrials.gov/study/"
ABSENT = "<absent>"
# What the workbooks' About sheet says a cell holds when the record holds no value ("how to read"); a blank
# cell counts as absent too.
ABSENCE_MARKERS = ("not reported", "not applicable to this study type", "redacted (withheld study)")

LOCATION_TOKEN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)((?:\[\d+\])*)")

# ----------------------------------------------------------------------------------------------------------
# Pure decisions: locations and the JSON record
# ----------------------------------------------------------------------------------------------------------


def parse_location(location: object) -> tuple | None:
    """(pure — pinned)

    A location written as the workbooks write it (`a.b[0].c`) as its path of keys and indices; None when it is
    not one.
    """
    if not isinstance(location, str) or not location:
        return None
    tokens: list = []
    for part in location.split("."):
        match = LOCATION_TOKEN.fullmatch(part)
        if not match:
            return None
        tokens.append(match.group(1))
        tokens.extend(int(index) for index in re.findall(r"\[(\d+)\]", match.group(2)))
    return tuple(tokens)


def format_location(tokens: tuple) -> str:
    """(pure — pinned)

    A path of keys and indices written as a location (`a.b[0].c`).
    """
    out = ""
    for token in tokens:
        if isinstance(token, int):
            out += f"[{token}]"
        else:
            out += f".{token}" if out else token
    return out


def field_pattern(tokens: tuple) -> str:
    """(pure — pinned)

    A location's field, its indices dropped (`a.b[].c`), the unit results are counted by.
    """
    return format_location(tuple(-1 if isinstance(t, int) else t for t in tokens)).replace("[-1]", "[]")


def resolve(record: object, tokens: tuple) -> tuple[bool, object]:
    """(pure — pinned)

    The value at a path in a JSON record: (True, value) when every step exists, else (False, None).
    """
    node = record
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(node, list) or token >= len(node):
                return False, None
        elif not isinstance(node, dict) or token not in node:
            return False, None
        node = node[token]
    return True, node


def json_leaves(record: object, prefix: tuple = ()) -> list[tuple[tuple, object]]:
    """(pure — pinned)

    Every leaf of a JSON record with its path, in the record's order; an empty list or object is a leaf too.
    """
    if isinstance(record, dict) and record:
        return [leaf for key, value in record.items() for leaf in json_leaves(value, (*prefix, key))]
    if isinstance(record, list) and record:
        return [leaf for index, value in enumerate(record) for leaf in json_leaves(value, (*prefix, index))]
    return [(prefix, record)]


def value_result(expected: object, cell: object) -> tuple[str, str]:
    """(pure — pinned)

    A cell against the record's value: agree when the same value of the same kind (text, number,
    true/false; a number of either JSON form); differ otherwise, saying how; not comparable when the cell says
    it could not hold the value (the workbooks' "not written" reason, which names studies.json).
    """

    def kind(value: object) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int | float):
            return "number"
        if isinstance(value, str):
            return "text"
        return "empty" if value is None else type(value).__name__

    if kind(expected) == kind(cell) and expected == cell:
        return "agree", ""
    if isinstance(cell, str) and "studies.json" in cell and cell != expected:
        return "not_comparable", "the cell states it could not hold the value: " + cell
    if kind(expected) != kind(cell):
        if str(expected) == str(cell):
            return (
                "differ",
                f"same text, different kind: {kind(expected)} in the record, {kind(cell)} in the cell",
            )
        return "differ", f"{kind(expected)} in the record, {kind(cell)} in the cell"
    if kind(expected) == "text":
        if expected.startswith(cell) and len(cell) < len(expected):
            return "differ", f"the cell holds the first {len(cell)} of {len(expected)} characters"
        return "differ", "different text"
    return "differ", "different value"


def absence_result(cell: object) -> tuple[str, str]:
    """(pure — pinned)

    A cell where the record holds no value: agree when it says so (a blank or one of the workbooks' absence
    words, named); differ when it holds a value.
    """
    if cell is None or cell == "":
        return "agree", "absent: blank"
    if cell in ABSENCE_MARKERS:
        return "agree", f"absent: {cell}"
    return "differ", "the record holds no value here, the cell holds one"


def role_result(record: object, tokens: tuple, role: object) -> tuple[str, str]:
    """(pure — pinned)

    A Record row's Role against the record: agree when every facet it states (`key=value`, joined by "; ")
    holds of an element enclosing the row's location (arm: an armGroups element's label; intervention: an
    interventions element's name; reference_type: a references element's type; outcome_type: an
    outcomeMeasures element's type, or the protocol section the outcome sits in; event_table: serious or other
    by the events list; group: an enclosing element's groupId, or a groups or eventGroups element's id);
    differ naming each facet that does not; not comparable for a facet this reader has no rule for.
    """
    enclosing = [
        (tokens[i - 1], resolve(record, tokens[: i + 1])[1])
        for i in range(1, len(tokens))
        if isinstance(tokens[i], int) and isinstance(tokens[i - 1], str)
    ]

    def holds(key: str, value: str) -> bool | None:
        if key == "event_table":
            return {"serious": "seriousEvents", "other": "otherEvents"}.get(value) in tokens
        if key == "group":
            ids = [e.get("groupId") for _, e in enclosing if isinstance(e, dict)]
            ids += [
                e.get("id") for n, e in enclosing if n in ("groups", "eventGroups") and isinstance(e, dict)
            ]
            return value in ids
        if key == "outcome_type":
            sections = [n.removesuffix("Outcomes").upper() for n, _ in enclosing if n.endswith("Outcomes")]
            types = [e.get("type") for n, e in enclosing if n == "outcomeMeasures" and isinstance(e, dict)]
            return value in sections + types
        fields = {"arm": ("armGroups", "label"), "intervention": ("interventions", "name")}
        fields["reference_type"] = ("references", "type")
        if key not in fields:
            return None
        name, field = fields[key]
        return any(n == name and isinstance(e, dict) and e.get(field) == value for n, e in enclosing)

    if not isinstance(role, str) or not role:
        return "not_comparable", "the row states no role"
    failed, unknown = [], []
    for facet in role.split("; "):
        key, _, value = facet.partition("=")
        verdict = holds(key, value)
        if verdict is None:
            unknown.append(facet)
        elif not verdict:
            failed.append(facet)
    if failed:
        return "differ", "no enclosing element of the record holds " + "; ".join(failed)
    if unknown:
        return "not_comparable", "a facet this reader has no rule for: " + "; ".join(unknown)
    return "agree", "every facet holds of an element enclosing the row's location"


def metadata_titles(metadata: list) -> dict[str, str]:
    """(pure — pinned)

    The registry's title of every field in /studies/metadata, by its path of names (`a.b.c`); a field without
    a title is not listed.
    """
    titles: dict[str, str] = {}

    def walk(nodes: list, prefix: str) -> None:
        for node in nodes:
            path = f"{prefix}.{node['name']}" if prefix else node["name"]
            if node.get("title"):
                titles[path] = node["title"]
            walk(node.get("children", []), path)

    walk(metadata, "")
    return titles


def title_result(titles: dict[str, str], tokens: tuple, cell: object) -> tuple[str, str]:
    """(pure — pinned)

    A Record row's Field against the registry's title for its location's field; not comparable when the
    metadata gives that field no title.
    """
    path = ".".join(t for t in tokens if isinstance(t, str))
    if path not in titles:
        return "not_comparable", "the registry's metadata gives this field no title"
    return value_result(titles[path], cell)


# ----------------------------------------------------------------------------------------------------------
# Pure decisions: comparison (a), record.xlsx against the raw JSON
# ----------------------------------------------------------------------------------------------------------


def finding(
    comparison: str, nct: str, where: str, field: str, result: str, why: str, expected=None, found=None
):
    """(pure — pinned)

    One result of one comparison, in the shape every result is kept in.
    """
    return {
        "comparison": comparison,
        "nct": nct,
        "where": where,
        "field": field,
        "result": result,
        "why": why,
        "expected": expected,
        "found": found,
    }


def compare_record_rows(studies: dict[str, dict], rows: list[dict], titles: dict[str, str]) -> list[dict]:
    """(pure — pinned)

    Comparison (a): every Record row against the raw JSON at the location it names (value, field title, and
    the facets of its Role when it states one), then every leaf of the raw JSON against the rows; one result
    per row and per leaf.
    """
    out = []
    seen: dict[tuple[str, str], int] = {}
    for row in rows:
        nct, location, where = row["nct"], row["location"], f"Record!row {row['row']}"
        tokens = parse_location(location)
        if tokens is None:
            out.append(
                finding(
                    "a",
                    nct,
                    where,
                    str(location),
                    "differ",
                    "the row's Location is not a location",
                    None,
                    location,
                )
            )
            continue
        field = field_pattern(tokens)
        if nct not in studies:
            out.append(
                finding(
                    "a",
                    nct,
                    where,
                    field,
                    "differ",
                    "the row names a study the registry did not return for the selection",
                    None,
                    row["value"],
                )
            )
            continue
        found, value = resolve(studies[nct], tokens)
        key = (nct, format_location(tokens))
        seen[key] = seen.get(key, 0) + 1
        if not found:
            out.append(
                finding(
                    "a",
                    nct,
                    location,
                    field,
                    "differ",
                    "the record holds nothing at this location",
                    ABSENT,
                    row["value"],
                )
            )
        elif isinstance(value, dict | list) and value:
            out.append(
                finding(
                    "a",
                    nct,
                    location,
                    field,
                    "differ",
                    "the location holds a list or object, not a value",
                    "<container>",
                    row["value"],
                )
            )
        else:
            result, why = value_result(value, row["value"])
            out.append(finding("a", nct, location, field, result, why, value, row["value"]))
        if row.get("role") not in (None, ""):
            result, why = role_result(studies[nct], tokens, row["role"])
            out.append(finding("a-role", nct, location, field, result, why, None, row["role"]))
        result, why = title_result(titles, tokens, row["title"])
        out.append(
            finding(
                "a-title",
                nct,
                location,
                field,
                result,
                why,
                titles.get(".".join(t for t in tokens if isinstance(t, str))),
                row["title"],
            )
        )
    for nct, study in studies.items():
        for tokens, value in json_leaves(study):
            location = format_location(tokens)
            count = seen.get((nct, location), 0)
            if count == 0:
                out.append(
                    finding(
                        "a-leaves",
                        nct,
                        location,
                        field_pattern(tokens),
                        "omitted",
                        "a value of the record no Record row holds",
                        value,
                        None,
                    )
                )
            elif count > 1:
                out.append(
                    finding(
                        "a-leaves",
                        nct,
                        location,
                        field_pattern(tokens),
                        "duplicated",
                        f"{count} Record rows hold this location",
                        value,
                        count,
                    )
                )
            else:
                out.append(finding("a-leaves", nct, location, field_pattern(tokens), "agree", "", None, None))
    return out


# ----------------------------------------------------------------------------------------------------------
# Pure decisions: comparison (b), the API's CSV
# ----------------------------------------------------------------------------------------------------------

P = "protocolSection."


def _get(study: dict, path: str) -> object:
    found, value = resolve(study, parse_location(path) or ())
    return value if found else None


# The documented CSV columns (acceptance/csv-columns.md) by how each is built from a record: one field; one
# list, its items (or each item's named key) joined by "|"; or several fields of each item of a list, each a
# component that must appear in the cell.
CSV_SINGLE = {
    "NCT Number": P + "identificationModule.nctId",
    "Study Title": P + "identificationModule.briefTitle",
    "Acronym": P + "identificationModule.acronym",
    "Study Status": P + "statusModule.overallStatus",
    "Brief Summary": P + "descriptionModule.briefSummary",
    "Sponsor": P + "sponsorCollaboratorsModule.leadSponsor.name",
    "Sex": P + "eligibilityModule.sex",
    "Enrollment": P + "designModule.enrollmentInfo.count",
    "Funder Type": P + "sponsorCollaboratorsModule.leadSponsor.class",
    "Study Type": P + "designModule.studyType",
    "Start Date": P + "statusModule.startDateStruct.date",
    "Primary Completion Date": P + "statusModule.primaryCompletionDateStruct.date",
    "Completion Date": P + "statusModule.completionDateStruct.date",
    "First Posted": P + "statusModule.studyFirstPostDateStruct.date",
    "Results First Posted": P + "statusModule.resultsFirstPostDateStruct.date",
    "Last Update Posted": P + "statusModule.lastUpdatePostDateStruct.date",
}
CSV_LISTS = {
    "Conditions": (P + "conditionsModule.conditions", None),
    "Phases": (P + "designModule.phases", None),
    "Collaborators": (P + "sponsorCollaboratorsModule.collaborators", "name"),
}
CSV_ITEM_PARTS = {
    "Primary Outcome Measures": (
        P + "outcomesModule.primaryOutcomes",
        ("measure", "description", "timeFrame"),
    ),
    "Secondary Outcome Measures": (
        P + "outcomesModule.secondaryOutcomes",
        ("measure", "description", "timeFrame"),
    ),
    "Other Outcome Measures": (P + "outcomesModule.otherOutcomes", ("measure", "description", "timeFrame")),
    "Locations": (P + "contactsLocationsModule.locations", ("facility", "city", "state", "zip", "country")),
    "Study Documents": ("documentSection.largeDocumentModule.largeDocs", ("label", "filename")),
}
DESIGN_PARTS = ("allocation", "interventionModel", "primaryPurpose", "observationalModel", "timePerspective")


def csv_expected(column: str, study: dict) -> tuple[str, object]:
    """(pure — pinned)

    What the registry's documentation says a CSV column holds for a study, built from its JSON record:
    ("exact", text) for a column of one field or one list (list items joined by "|", as the CSV joins them),
    ("components", [values]) for a column joining several fields, each of which must appear in the cell, or
    ("unknown", column) for a column the documentation does not list.
    """
    if column in CSV_SINGLE:
        value = _get(study, CSV_SINGLE[column])
        return "exact", "" if value is None else str(value)
    if column == "Study URL":
        return "exact", STUDY_URL + str(_get(study, CSV_SINGLE["NCT Number"]))
    if column == "Study Results":
        return "exact", "YES" if study.get("hasResults") else "NO"
    if column in CSV_LISTS:
        path, key = CSV_LISTS[column]
        return "exact", "|".join(str(item[key] if key else item) for item in _get(study, path) or [])
    if column == "Interventions":
        items = _get(study, P + "armsInterventionsModule.interventions") or []
        return "exact", "|".join(f"{item.get('type')}: {item.get('name')}" for item in items)
    if column in CSV_ITEM_PARTS:
        path, keys = CSV_ITEM_PARTS[column]
        return "components", [
            str(item[key]) for item in _get(study, path) or [] for key in keys if key in item
        ]
    if column == "Age":
        eligibility = _get(study, P + "eligibilityModule") or {}
        parts = [eligibility[key] for key in ("minimumAge", "maximumAge") if key in eligibility]
        return "components", parts + list(eligibility.get("stdAges", []))
    if column == "Study Design":
        info = _get(study, P + "designModule.designInfo") or {}
        masking = info.get("maskingInfo", {})
        parts = [info[key] for key in DESIGN_PARTS if key in info]
        parts += [masking["masking"]] if "masking" in masking else []
        return "components", parts + list(masking.get("whoMasked", []))
    if column == "Other IDs":
        ident = P + "identificationModule."
        parts = [_get(study, ident + "orgStudyIdInfo.id")]
        parts += [item.get("id") for item in _get(study, ident + "secondaryIdInfos") or []]
        return "components", [str(part) for part in parts if part is not None]
    return "unknown", column


def csv_cell_result(expected: tuple[str, object], cell: str) -> tuple[str, str]:
    """(pure — pinned)

    A CSV cell against what its column should hold: exact text equality, or every component present in the
    cell (each missing one named); not comparable for a column the documentation does not list.
    """
    how, value = expected
    if how == "exact":
        if cell == value:
            return "agree", ""
        return "differ", "different text"
    if how == "components":
        missing = [part for part in value if part not in cell]
        if not missing:
            return "agree", "every documented component appears in the cell"
        return "differ", "missing from the cell: " + " | ".join(missing)
    return "not_comparable", "a column the registry's documentation does not list"


# The CSV columns of one field (or one list), and where that field sits in a record, for comparing the CSV
# with record.xlsx; the CSV joins a list's items with "|".
CSV_RECORD_FIELDS = {
    "NCT Number": P + "identificationModule.nctId",
    "Study Title": P + "identificationModule.briefTitle",
    "Acronym": P + "identificationModule.acronym",
    "Study Status": P + "statusModule.overallStatus",
    "Brief Summary": P + "descriptionModule.briefSummary",
    "Conditions": P + "conditionsModule.conditions[]",
    "Sponsor": P + "sponsorCollaboratorsModule.leadSponsor.name",
    "Collaborators": P + "sponsorCollaboratorsModule.collaborators[].name",
    "Sex": P + "eligibilityModule.sex",
    "Phases": P + "designModule.phases[]",
    "Enrollment": P + "designModule.enrollmentInfo.count",
    "Funder Type": P + "sponsorCollaboratorsModule.leadSponsor.class",
    "Study Type": P + "designModule.studyType",
    "Start Date": P + "statusModule.startDateStruct.date",
    "Primary Completion Date": P + "statusModule.primaryCompletionDateStruct.date",
    "Completion Date": P + "statusModule.completionDateStruct.date",
    "First Posted": P + "statusModule.studyFirstPostDateStruct.date",
    "Results First Posted": P + "statusModule.resultsFirstPostDateStruct.date",
    "Last Update Posted": P + "statusModule.lastUpdatePostDateStruct.date",
}


def workbook_text(cells: dict[str, object], pattern: str) -> str:
    """(pure — pinned)

    What record.xlsx holds for one field pattern of one study, written as the CSV writes it: the value as
    text, a list's items in order joined by "|", "" when it holds nothing there or an empty cell.
    """

    def text(value: object) -> str:
        return "" if value is None else str(value)

    if "[]" not in pattern:
        return text(cells[pattern]) if pattern in cells else ""
    head, tail = pattern.split("[]", 1)
    items = []
    for index in range(len(cells)):
        if f"{head}[{index}]{tail}" not in cells:
            break
        items.append(text(cells[f"{head}[{index}]{tail}"]))
    return "|".join(items)


def compare_csv(
    studies: dict[str, dict],
    csv_rows: list[dict],
    header: list[str],
    documented: list[str],
    record_cells: dict[str, dict[str, object]],
) -> list[dict]:
    """(pure — pinned)

    Comparison (b): the header against the documented columns, every CSV cell against the raw JSON by the
    documented column, and every single-field column against record.xlsx.
    """
    out = []
    if header != documented:
        out.append(
            finding(
                "b-json",
                "*",
                "header",
                "header",
                "differ",
                "the CSV's columns are not the documented columns, in order",
                documented,
                header,
            )
        )
    else:
        out.append(finding("b-json", "*", "header", "header", "agree", "", None, None))
    by_nct: dict[str, list[dict]] = {}
    for row in csv_rows:
        by_nct.setdefault(row.get("NCT Number", ""), []).append(row)
    for nct, study in studies.items():
        rows = by_nct.get(nct, [])
        if len(rows) != 1:
            out.append(
                finding(
                    "b-json",
                    nct,
                    "row",
                    "row",
                    "omitted" if not rows else "duplicated",
                    f"{len(rows)} CSV rows for the study",
                    1,
                    len(rows),
                )
            )
            continue
        row = rows[0]
        for column in header:
            cell = row.get(column, "")
            expected = csv_expected(column, study)
            result, why = csv_cell_result(expected, cell)
            out.append(finding("b-json", nct, column, column, result, why, expected[1], cell))
            if column in CSV_RECORD_FIELDS:
                held = workbook_text(record_cells.get(nct, {}), CSV_RECORD_FIELDS[column])
                result, why = ("agree", "") if held == cell else ("differ", "different text")
                out.append(
                    finding("b-workbook", nct, column, CSV_RECORD_FIELDS[column], result, why, cell, held)
                )
    for nct in by_nct:
        if nct not in studies:
            out.append(
                finding(
                    "b-json", nct, "row", "row", "differ", "a CSV row for a study not returned", None, nct
                )
            )
    return out


# ----------------------------------------------------------------------------------------------------------
# Pure decisions: comparison (c), review.xlsx
# ----------------------------------------------------------------------------------------------------------

AE = "resultsSection.adverseEventsModule."
OM = "resultsSection.outcomeMeasuresModule.outcomeMeasures[*]"
BL = "resultsSection.baselineCharacteristicsModule.measures[*]"
MEASUREMENTS = ".classes[*].categories[*].measurements[*]"
STUDIES_COLUMNS = {
    "NCT Number": P + "identificationModule.nctId",
    "Brief Title": P + "identificationModule.briefTitle",
    "Acronym": P + "identificationModule.acronym",
    "Overall Status": P + "statusModule.overallStatus",
    "Why Stopped": P + "statusModule.whyStopped",
    "Study Type": P + "designModule.studyType",
    "Phases": P + "designModule.phases[*]",
    "Primary Purpose": P + "designModule.designInfo.primaryPurpose",
    "Allocation": P + "designModule.designInfo.allocation",
    "Intervention Model": P + "designModule.designInfo.interventionModel",
    "Masking": P + "designModule.designInfo.maskingInfo.masking",
    "Who Masked": P + "designModule.designInfo.maskingInfo.whoMasked[*]",
    "Observational Model": P + "designModule.designInfo.observationalModel",
    "Time Perspective": P + "designModule.designInfo.timePerspective",
    "Enrollment": P + "designModule.enrollmentInfo.count",
    "Enrollment Type": P + "designModule.enrollmentInfo.type",
    "Start Date": P + "statusModule.startDateStruct.date",
    "Start Date Type": P + "statusModule.startDateStruct.type",
    "Primary Completion Date": P + "statusModule.primaryCompletionDateStruct.date",
    "Primary Completion Date Type": P + "statusModule.primaryCompletionDateStruct.type",
    "Completion Date": P + "statusModule.completionDateStruct.date",
    "Completion Date Type": P + "statusModule.completionDateStruct.type",
    "Conditions": P + "conditionsModule.conditions[*]",
    "Condition MeSH Terms": "derivedSection.conditionBrowseModule.meshes[*].term",
    "Condition MeSH Ancestors": "derivedSection.conditionBrowseModule.ancestors[*].term",
    "Intervention MeSH Terms": "derivedSection.interventionBrowseModule.meshes[*].term",
    "Intervention MeSH Ancestors": "derivedSection.interventionBrowseModule.ancestors[*].term",
    "Lead Sponsor": P + "sponsorCollaboratorsModule.leadSponsor.name",
    "Lead Sponsor Class": P + "sponsorCollaboratorsModule.leadSponsor.class",
    "Collaborators": {"form": "collaborators"},
    "Sex": P + "eligibilityModule.sex",
    "Gender Based": P + "eligibilityModule.genderBased",
    "Minimum Age": P + "eligibilityModule.minimumAge",
    "Maximum Age": P + "eligibilityModule.maximumAge",
    "Age Groups": P + "eligibilityModule.stdAges[*]",
    "Healthy Volunteers": P + "eligibilityModule.healthyVolunteers",
    "Results First Posted": P + "statusModule.resultsFirstPostDateStruct.date",
    "Results Submitted, Not Yet Posted": "derivedSection.miscInfoModule.submissionTracking"
    ".estimatedResultsFirstSubmitDate",
    "Results Delay Requested": P + "statusModule.dispFirstSubmitDate",
    "Results Waived": P + "statusModule.resultsWaived",
}

# Each sheet of review.xlsx: how its rows are keyed (one per study, or by the Location they name), the record
# elements a row stands for (`[*]` any index; `base + suffix` means the suffix's elements, or the base element
# itself when it has none), and the columns compared, each a path: absolute, `@.f` (the row's own element),
# `@^.f` (that element's parent element), `@seg.f` (the row's enclosing `seg[i]` element), a join, or a form
# (`{"form": ...}`, a stated column whose value is the row's place in the record or a declared text form of
# one field; structure_value). The sheets, their columns and the field each column is paired with were
# transcribed from review.xlsx's About sheet; compare_declared checks every pairing against it.
REVIEW_SHEETS: dict[str, dict] = {
    "Studies": {"key": "nct", "columns": STUDIES_COLUMNS},
    "Eligibility": {
        "key": "nct",
        "columns": {
            "NCT Number": P + "identificationModule.nctId",
            "Sex": P + "eligibilityModule.sex",
            "Gender Based": P + "eligibilityModule.genderBased",
            "Gender Description": P + "eligibilityModule.genderDescription",
            "Minimum Age": P + "eligibilityModule.minimumAge",
            "Maximum Age": P + "eligibilityModule.maximumAge",
            "Age Groups": P + "eligibilityModule.stdAges[*]",
            "Healthy Volunteers": P + "eligibilityModule.healthyVolunteers",
            "Study Population": P + "eligibilityModule.studyPopulation",
            "Sampling Method": P + "eligibilityModule.samplingMethod",
        },
    },
    "Outcomes": {
        "key": "location",
        "rows": [
            (P + "outcomesModule.primaryOutcomes[*]", ""),
            (P + "outcomesModule.secondaryOutcomes[*]", ""),
            (P + "outcomesModule.otherOutcomes[*]", ""),
        ],
        "columns": {
            "Outcome Type": {"form": "outcome section"},
            "Order": {"form": "position"},
            "Measure": "@.measure",
            "Description": "@.description",
            "Time Frame": "@.timeFrame",
        },
    },
    "Arms": {
        "key": "location",
        "rows": [(P + "armsInterventionsModule.armGroups[*]", "")],
        "columns": {
            "Arm Label": "@.label",
            "Arm Type": "@.type",
            "Description": "@.description",
            "Interventions Named": "@.interventionNames[*]",
        },
    },
    "Interventions": {
        "key": "location",
        "rows": [(P + "armsInterventionsModule.interventions[*]", "")],
        "columns": {
            "Type": "@.type",
            "Name": "@.name",
            "Other Names": "@.otherNames[*]",
            "Description": "@.description",
            "Arms Named": "@.armGroupLabels[*]",
        },
    },
    "Sites": {
        "key": "location",
        "rows": [(P + "contactsLocationsModule.locations[*]", "")],
        "columns": {
            "Facility": "@.facility",
            "Site Status": "@.status",
            "City": "@.city",
            "State": "@.state",
            "ZIP": "@.zip",
            "Country": "@.country",
        },
    },
    "Outcome Results": {
        "key": "location",
        "rows": [(OM, MEASUREMENTS)],
        "columns": {
            "Outcome Type": "@outcomeMeasures.type",
            "Title": "@outcomeMeasures.title",
            "Description": "@outcomeMeasures.description",
            "Time Frame": "@outcomeMeasures.timeFrame",
            "Population Description": "@outcomeMeasures.populationDescription",
            "Reporting Status": "@outcomeMeasures.reportingStatus",
            "Measure Type": "@outcomeMeasures.paramType",
            "Dispersion Type": "@outcomeMeasures.dispersionType",
            "Unit of Measure": "@outcomeMeasures.unitOfMeasure",
            "Class": "@classes.title",
            "Category": "@categories.title",
            "Group ID": "@measurements.groupId",
            "Value": "@measurements.value",
            "Spread": "@measurements.spread",
            "Lower Limit": "@measurements.lowerLimit",
            "Upper Limit": "@measurements.upperLimit",
            "Comment": "@measurements.comment",
        },
    },
    "Analyses": {
        "key": "location",
        "rows": [(OM + ".analyses[*]", "")],
        "columns": {
            "Outcome Title": "@outcomeMeasures.title",
            "Group Description": "@.groupDescription",
            "Estimation Parameter": "@.paramType",
            "Estimated Value": "@.paramValue",
            "CI Level (%)": "@.ciPctValue",
            "CI Sides": "@.ciNumSides",
            "CI Lower": "@.ciLowerLimit",
            "CI Upper": "@.ciUpperLimit",
            "P-Value": "@.pValue",
            "P-Value Comment": "@.pValueComment",
            "Statistical Method": "@.statisticalMethod",
            "Test Type": "@.nonInferiorityType",
            "Dispersion Type": "@.dispersionType",
            "Dispersion Value": "@.dispersionValue",
            "Estimation Comment": "@.estimateComment",
        },
    },
    "Adverse Events": {
        "key": "location",
        "rows": [(AE + "seriousEvents[*].stats[*]", ""), (AE + "otherEvents[*].stats[*]", "")],
        "columns": {
            "Term": "@^.term",
            "Organ System": "@^.organSystem",
            "Source Vocabulary": "@^.sourceVocabulary",
            "Assessment Type": "@^.assessmentType",
            "Notes": "@^.notes",
            "Group ID": "@.groupId",
            "Participants Affected": "@.numAffected",
            "Events": "@.numEvents",
            "Group Title": {"join": AE + "eventGroups", "on": "id", "key": "@.groupId", "take": "title"},
            "Table": {"form": "event table"},
        },
    },
    "Event Groups": {
        "key": "location",
        "rows": [(AE + "eventGroups[*]", "")],
        "columns": {
            "Group ID": "@.id",
            "Title": "@.title",
            "Description": "@.description",
            "Deaths Affected": "@.deathsNumAffected",
            "Deaths at Risk": "@.deathsNumAtRisk",
            "Serious Affected": "@.seriousNumAffected",
            "Serious at Risk": "@.seriousNumAtRisk",
            "Other Affected": "@.otherNumAffected",
            "Other at Risk": "@.otherNumAtRisk",
            "Frequency Threshold (%)": AE + "frequencyThreshold",
            "Time Frame": AE + "timeFrame",
            "Reporting Description": AE + "description",
            "All-Cause Mortality Comment": AE + "allCauseMortalityComment",
        },
    },
    "Participant Flow": {
        "key": "location",
        "rows": [
            ("resultsSection.participantFlowModule.periods[*].milestones[*].achievements[*]", ""),
            ("resultsSection.participantFlowModule.periods[*].dropWithdraws[*].reasons[*]", ""),
        ],
        "columns": {
            "Period": "@periods.title",
            "Kind": {"form": "flow kind"},
            "Type": "@^.type",
            "Group ID": "@.groupId",
            "Participants": "@.numSubjects",
            "Comment": "@.comment",
        },
    },
    "Baseline": {
        "key": "location",
        "rows": [(BL, MEASUREMENTS)],
        "columns": {
            "Measure": "@measures.title",
            "Measure Type": "@measures.paramType",
            "Dispersion Type": "@measures.dispersionType",
            "Unit of Measure": "@measures.unitOfMeasure",
            "Class": "@classes.title",
            "Category": "@categories.title",
            "Group ID": "@measurements.groupId",
            "Value": "@measurements.value",
            "Spread": "@measurements.spread",
            "Lower Limit": "@measurements.lowerLimit",
            "Upper Limit": "@measurements.upperLimit",
        },
    },
    "Publications": {
        "key": "location",
        "rows": [(P + "referencesModule.references[*]", "")],
        "columns": {
            "PMID": "@.pmid",
            "Type": "@.type",
            "Citation": "@.citation",
            "Retractions": {"form": "retractions"},
        },
    },
    "Documents": {
        "key": "location",
        "rows": [("documentSection.largeDocumentModule.largeDocs[*]", "")],
        "columns": {
            "Document Type": "@.typeAbbrev",
            "Label": "@.label",
            "Includes Protocol": "@.hasProtocol",
            "Includes SAP": "@.hasSap",
            "Includes ICF": "@.hasIcf",
            "Document Date": "@.date",
            "Uploaded": "@.uploadDate",
            "File": "@.filename",
        },
    },
}


def expand(record: object, pattern: str) -> list[tuple]:
    """(pure — pinned)

    Every path of a record a pattern names (`a.b[0].c[*]`), `[*]` standing for each index of a list, in the
    record's order; none when the pattern is not one.
    """
    steps: list = []
    for part in pattern.split("."):
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)((?:\[(?:\d+|\*)\])*)", part)
        if not match:
            return []
        steps.append(match.group(1))
        steps += ["*" if i == "*" else int(i) for i in re.findall(r"\[(\d+|\*)\]", match.group(2))]
    paths: list[tuple] = [()]
    for step in steps:
        grown = []
        for path in paths:
            node = resolve(record, path)[1]
            if step == "*":
                grown += [(*path, i) for i in range(len(node))] if isinstance(node, list) else []
            elif resolve(record, (*path, step))[0]:
                grown.append((*path, step))
        paths = grown
    return paths


def row_elements(record: object, rows: list[tuple[str, str]]) -> list[tuple]:
    """(pure — pinned)

    The record elements a sheet has one row for: each base element's suffix elements, or the base element
    itself when the suffix names none.
    """
    out = []
    for base, suffix in rows:
        for path in expand(record, base):
            deeper = expand(resolve(record, path)[1], suffix.lstrip(".")) if suffix else []
            out += [(*path, *tail) for tail in deeper] if deeper else [path]
    return out


def column_path(spec: str, row: tuple | None) -> tuple[str, tuple | None]:
    """(pure — pinned)

    A column's path for one row: ("path", pattern) with the row's element substituted for `@`, `@^` or
    `@seg`; ("outside", None) when the row's element does not reach the anchor the column names.
    """
    if not spec.startswith("@"):
        return "path", spec
    anchor, _, rest = spec[1:].partition(".")
    if row is None:
        return "outside", None
    if anchor == "":
        base = row
    elif anchor == "^":
        cut = [i for i, token in enumerate(row) if isinstance(token, int)]
        if len(cut) < 2:
            return "outside", None
        base = row[: cut[-2] + 1]
    else:
        at = [i for i, token in enumerate(row[:-1]) if token == anchor and isinstance(row[i + 1], int)]
        if not at:
            return "outside", None
        base = row[: at[-1] + 2]
    return "path", format_location(base) + ("." + rest if rest else "")


def project(record: object, pattern: str) -> tuple[bool, object]:
    """(pure — pinned)

    A column's value in a record: one value for a plain path, the list of values for a path with `[*]`
    (absent when there are none); (False, None) when the record holds nothing there.
    """
    if "[*]" not in pattern:
        return resolve(record, parse_location(pattern) or ("<unparseable>",))
    values = [resolve(record, path)[1] for path in expand(record, pattern)]
    return (True, values) if values else (False, None)


def review_cell_result(found: bool, value: object, cell: object) -> tuple[str, str]:
    """(pure — pinned)

    A review.xlsx cell against its declared field: absence as absence; a list as its items one per line, each
    as the record holds it; otherwise the value itself (value_result).
    """
    if not found:
        return absence_result(cell)
    if isinstance(value, list):
        if any(isinstance(item, dict | list) for item in value):
            return "not_comparable", "the field holds objects, not values"
        return value_result("\n".join(str(item) for item in value), cell)
    if isinstance(value, dict):
        return "not_comparable", "the field holds an object, not a value"
    return value_result(value, cell)


def structure_value(form: str, study: dict, row: tuple | None) -> tuple[bool, object] | None:
    """(pure — pinned)

    What a stated column that gives the row's place in the record, or a declared text form of one field,
    holds for the row, as review.xlsx's About sheet declares the form: the outcome section (primaryOutcomes as
    PRIMARY), the position in its list from 1, the adverse-event table (serious or other), the flow kind
    (milestone, or reason not completed), a reference's retractions as "PMID (source)" and the collaborators
    as "name (class)", one per line; (False, None) when the record holds none; None for a form it has no rule
    for.
    """
    if form in ("retractions", "collaborators"):
        if form == "collaborators":
            items = project(study, P + "sponsorCollaboratorsModule.collaborators")[1]
            keys = ("name", "class")
        else:
            element = resolve(study, row)[1] if row is not None else None
            items = element.get("retractions") if isinstance(element, dict) else None
            keys = ("pmid", "source")
        lines = [f"{i.get(keys[0])} ({i.get(keys[1])})" for i in items or [] if isinstance(i, dict)]
        return (True, "\n".join(lines)) if lines else (False, None)
    if form not in ("outcome section", "position", "event table", "flow kind"):
        return None
    if not row or not isinstance(row[-1], int):
        return False, None
    if form == "position":
        return True, row[-1] + 1
    if form == "outcome section":
        section = row[-2] if isinstance(row[-2], str) and row[-2].endswith("Outcomes") else None
        return (True, section.removesuffix("Outcomes").upper()) if section else (False, None)
    names = {"event table": {"seriousEvents": "serious", "otherEvents": "other"}}
    names["flow kind"] = {"milestones": "milestone", "dropWithdraws": "reason not completed"}
    found = [names[form][token] for token in row if token in names[form]]
    return (True, found[-1]) if found else (False, None)


def at_risk_result(study: dict, element: tuple | None, cells: dict) -> tuple[str, str, object]:
    """(pure — pinned)

    review.xlsx's computed Participants at Risk and At Risk Source for one adverse-event count, against the
    rule review.xlsx declares for them: the event's own numAtRisk, labelled "stated"; when the event leaves it
    blank, its group's total for the table (eventGroups' seriousNumAtRisk or otherNumAtRisk), labelled "group
    total". Returns the result, why, and what the rule gives.
    """
    stat = resolve(study, element)[1] if element is not None else None
    if not isinstance(stat, dict) or not ({"seriousEvents", "otherEvents"} & set(element or ())):
        return "not_comparable", "the row's Location is not an adverse event's count", None
    if "numAtRisk" in stat:
        source, value = "stated", stat["numAtRisk"]
    else:
        events = resolve(study, ("resultsSection", "adverseEventsModule", "eventGroups"))[1]
        groups = [g for g in events or [] if isinstance(g, dict) and g.get("id") == stat.get("groupId")]
        if len(groups) != 1:
            return "not_comparable", f"{len(groups)} event groups have the count's group id", None
        table = "serious" if "seriousEvents" in element else "other"
        source, value = "group total", groups[0].get(f"{table}NumAtRisk")
    expected = {"At Risk Source": source, "Participants at Risk": value}
    if cells.get("At Risk Source") != source:
        return "differ", f"the rule gives At Risk Source {source!r}", expected
    result, why = value_result(value, cells.get("Participants at Risk"))
    return result, why or f"{source}: the count the rule names", expected


def column_value(spec: object, study: dict, row: tuple | None) -> tuple[str, object]:
    """(pure — pinned)

    What one column of one row should hold: ("value", (found, value)) from the record, or ("skip", why) when
    a join finds no single element or the column's path lies outside the row's element.
    """
    if isinstance(spec, dict) and "form" in spec:
        held = structure_value(spec["form"], study, row)
        return ("value", held) if held is not None else ("skip", f"no rule for the form {spec['form']!r}")
    if isinstance(spec, dict) and "join" in spec:
        kind, key_path = column_path(spec["key"], row)
        if kind != "path":
            return "skip", "the row's element does not reach the join key"
        found, key = project(study, key_path)
        groups = resolve(study, parse_location(spec["join"]) or ())[1] or []
        matches = [g for g in groups if isinstance(g, dict) and found and g.get(spec["on"]) == key]
        if len(matches) != 1:
            return "skip", f"{len(matches)} elements of {spec['join']} have {spec['on']} {key!r}"
        return "value", (spec["take"] in matches[0], matches[0].get(spec["take"]))
    kind, path = column_path(spec, row)
    if kind != "path":
        return "skip", "the row's element does not reach this column's field"
    return "value", project(study, path)


def compare_review(studies: dict[str, dict], sheets: dict[str, list[dict]]) -> list[dict]:
    """(pure — pinned)

    Comparison (c): each declared single-field column of each review.xlsx sheet against its field, each
    sheet's rows against the records' elements of that kind, and each study link against the registry's form.
    """
    out = []
    for name, spec in REVIEW_SHEETS.items():
        rows = sheets.get(name, [])
        expected: dict[tuple[str, str], int] = {}
        if spec["key"] == "nct":
            expected = {(nct, ""): 1 for nct in studies}
        else:
            for nct, study in studies.items():
                for element in row_elements(study, spec["rows"]):
                    expected[(nct, format_location(element))] = 1
        seen: dict[tuple[str, str], int] = {}
        for row in rows:
            nct = row["cells"].get("NCT Number")
            where = f"{name}!row {row['row']}"
            link = row["links"].get("NCT Number")
            link_ok = link == STUDY_URL + str(nct)
            out.append(
                finding(
                    "c-links",
                    str(nct),
                    where,
                    f"{name} › NCT Number link",
                    "agree" if link_ok else "differ",
                    "" if link_ok else "not the study's registry page",
                    STUDY_URL + str(nct),
                    link,
                )
            )
            if nct not in studies:
                out.append(
                    finding(
                        "c-rows", str(nct), where, name, "differ", "a row for a study not returned", None, nct
                    )
                )
                continue
            study = studies[nct]
            if spec["key"] == "nct":
                element: tuple | None = ()
                key = (nct, "")
            else:
                element = parse_location(row["cells"].get("Location"))
                key = (
                    nct,
                    format_location(element) if element is not None else str(row["cells"].get("Location")),
                )
            seen[key] = seen.get(key, 0) + 1
            if key not in expected:
                if any(k[0] == nct for k in expected):
                    out.append(
                        finding(
                            "c-rows",
                            nct,
                            where,
                            name,
                            "differ",
                            "the row's Location is not an element of this kind in the record",
                            None,
                            key[1],
                        )
                    )
                else:
                    out.append(placeholder_result(name, nct, where, row["cells"], spec["columns"]))
                continue
            for column, column_spec in spec["columns"].items():
                if column not in row["cells"]:
                    out.append(
                        finding(
                            "c",
                            nct,
                            where,
                            f"{name} › {column}",
                            "not_comparable",
                            "the sheet has no such column",
                            None,
                            None,
                        )
                    )
                    continue
                cell = row["cells"][column]
                kind, value = column_value(column_spec, study, element)
                which = "c-form" if isinstance(column_spec, dict) and "form" in column_spec else "c"
                if kind == "skip":
                    out.append(
                        finding(
                            which, nct, where, f"{name} › {column}", "not_comparable", str(value), None, cell
                        )
                    )
                    continue
                found, held = value
                result, why = review_cell_result(found, held, cell)
                out.append(
                    finding(
                        which, nct, where, f"{name} › {column}", result, why, held if found else ABSENT, cell
                    )
                )
            out += special_checks(name, nct, study, row, where)
        for key in expected:
            got = seen.get(key, 0)
            if got == 0:
                out.append(
                    finding(
                        "c-rows",
                        key[0],
                        key[1] or name,
                        name,
                        "omitted",
                        "an element of the record no row of the sheet stands for",
                        None,
                        None,
                    )
                )
            elif got > 1:
                out.append(
                    finding(
                        "c-rows",
                        key[0],
                        key[1] or name,
                        name,
                        "duplicated",
                        f"{got} rows of the sheet stand for this element",
                        1,
                        got,
                    )
                )
            else:
                out.append(finding("c-rows", key[0], key[1] or name, name, "agree", "", None, None))
    return out


def placeholder_result(name: str, nct: str, where: str, cells: dict, columns: dict) -> dict:
    """(pure — pinned)

    A row that stands for no element, in a sheet whose kind of element the study's record does not hold: it
    agrees when every column declared from a field is empty or says absence, and it names what the row states.
    """
    holding = sorted(c for c in columns if c in cells and absence_result(cells[c])[0] != "agree")
    states = "; ".join(
        f"{c}: {v}"
        for c, v in cells.items()
        if v is not None and c not in ("NCT Number", "Warrant", "Location") and c not in columns
    )
    if holding:
        return finding(
            "c-rows",
            nct,
            where,
            name,
            "differ",
            "a row standing for no element holds values in " + ", ".join(holding),
            None,
            {c: cells[c] for c in holding},
        )
    return finding(
        "c-rows",
        nct,
        where,
        name,
        "agree",
        "absent: the record holds no element of this kind; the row says so (" + states + ")",
        None,
        cells.get("Location"),
    )


def special_checks(name: str, nct: str, study: dict, row: dict, where: str) -> list[dict]:
    """(pure — pinned)

    The checks a sheet needs beyond its columns: an adverse event's computed at-risk count follows its
    declared rule (at_risk_result), the eligibility text's split parts put back together are the registry's
    text (or its Whole Text is), a PMID's link names that PMID on PubMed, and a document's link ends in its
    study and file name.
    """
    cells, links, out = row["cells"], row["links"], []
    if name == "Adverse Events":
        result, why, expected = at_risk_result(study, parse_location(cells.get("Location")), cells)
        held = {key: cells.get(key) for key in ("At Risk Source", "Participants at Risk")}
        field = "Adverse Events › Participants at Risk, At Risk Source"
        out.append(finding("c-rule", nct, where, field, result, why, expected, held))
    if name == "Eligibility":
        found, text = resolve(study, ("protocolSection", "eligibilityModule", "eligibilityCriteria"))
        if cells.get("Split") == "split":
            parts = [
                cells.get(c) or ""
                for c in ("Before the Inclusion Heading", "Inclusion Criteria", "Exclusion Criteria")
            ]
            held = "".join(str(part) for part in parts)
            result, why = value_result(text, held) if found else absence_result(held)
            out.append(
                finding(
                    "c",
                    nct,
                    where,
                    "Eligibility › split parts, joined",
                    result,
                    why or "the three parts joined are the registry's text",
                    text,
                    held,
                )
            )
        else:
            result, why = review_cell_result(found, text, cells.get("Whole Text"))
            out.append(
                finding(
                    "c",
                    nct,
                    where,
                    "Eligibility › Whole Text",
                    result,
                    why,
                    text if found else ABSENT,
                    cells.get("Whole Text"),
                )
            )
    if name == "Publications":
        pmid, link = cells.get("PMID"), links.get("PMID")
        ok = (
            isinstance(link, str)
            and link.startswith("https://pubmed.ncbi.nlm.nih.gov/")
            and f"/{pmid}" in link
        )
        if pmid not in (None, "", *ABSENCE_MARKERS) or link:
            out.append(
                finding(
                    "c-links",
                    nct,
                    where,
                    "Publications › PMID link",
                    "agree" if ok else "differ",
                    "" if ok else "not the PMID's PubMed page",
                    pmid,
                    link,
                )
            )
    if name == "Documents":
        filename, link = cells.get("File"), links.get("File")
        ok = isinstance(link, str) and link.endswith(f"/{nct}/{filename}")
        out.append(
            finding(
                "c-links",
                nct,
                where,
                "Documents › File link",
                "agree" if ok else "differ",
                "" if ok else "not the study's copy of the file",
                filename,
                link,
            )
        )
    return out


def declared_source_result(spec: object, declared: tuple | None) -> tuple[str, str]:
    """(pure — pinned)

    One column this reader compares against what review.xlsx's About sheet declares for it, (status,
    source): agree when it is declared stated and its source names the field the reader pairs it with (the
    last two keys of the reader's path, indices dropped, end one of the dotted paths the source names; one key
    when either has only one), or, for a form, when it is declared stated; differ otherwise, or when the About
    sheet declares no such column.
    """
    if declared is None:
        return "differ", "review.xlsx's About sheet declares no such column"
    status, source = declared
    if status not in ("stated", "stated (link)"):
        return "differ", f"declared {status}, not stated"
    if isinstance(spec, dict) and "form" in spec:
        return "agree", "declared stated; the reader reads its form from this declaration"
    path = f"{spec['join']}.{spec['take']}" if isinstance(spec, dict) else str(spec)
    if path.startswith("@"):
        anchor, _, rest = path[1:].partition(".")
        path = rest if anchor in ("", "^") else f"{anchor}.{rest}"
    mine = [re.sub(r"\[[^\]]*\]", "", key) for key in path.split(".")]
    theirs = [
        [re.sub(r"\[[^\]]*\]", "", key) for key in candidate.split(".") if key]
        for candidate in re.findall(r"[A-Za-z_<>.\[\]]+", str(source))
    ]
    for keys in theirs:
        k = min(2, len(mine), len(keys))
        if k and mine[-k:] == keys[-k:]:
            return "agree", "declared stated from the field the reader pairs it with"
    return "differ", "the declared source does not name the field the reader pairs this column with"


def compare_declared(sheets: dict[str, dict], about: list[tuple]) -> list[dict]:
    """(pure — pinned)

    Comparison c-declared: every column of every sheet the reader compares (`REVIEW_SHEETS`) against the
    status and source review.xlsx's About sheet declares for it (`('column', 'Sheet › Column', status,
    source)` rows), one result per column.
    """
    declared = {row[1]: (row[2], row[3]) for row in about if len(row) >= 4 and row[0] == "column"}
    out = []
    for sheet, spec in sheets.items():
        for column, column_spec in spec["columns"].items():
            name = f"{sheet} › {column}"
            result, why = declared_source_result(column_spec, declared.get(name))
            out.append(finding("c-declared", "*", name, name, result, why, column_spec, declared.get(name)))
    return out


def provenance_results(
    about: list[tuple], where: str, version: dict, ids: list[str], fetched: dict[str, dict]
) -> list[dict]:
    """(pure — pinned)

    Comparison (g): the provenance a workbook's About sheet states against what this reader holds: the API's
    address, the query (the selection's IDs in order), the registry's API version and data date (its
    /version), the study count and each requested ID's status (found, for an ID that is the NCT number of a
    fetched record; one row per ID). The rest of the provenance is TrialLedger's record of its own run, not
    comparable with the registry.
    """
    stated = {row[1]: row[2] for row in about if len(row) >= 3 and row[0] == "provenance"}
    expected = {
        "source": API + "/studies",
        "query": "filter.ids=" + ",".join(ids),
        "api_version": version.get("apiVersion"),
        "data_timestamp": version.get("dataTimestamp"),
        "study_count": len(fetched),
    }
    out = []
    for key, value in expected.items():
        if key not in stated:
            out.append(finding("g", "*", where, key, "omitted", "the About sheet does not state it", value))
            continue
        result, why = value_result(value, stated[key])
        out.append(finding("g", "*", where, key, result, why, value, stated[key]))
    for key in sorted(set(stated) - set(expected)):
        why = "TrialLedger's record of its own run; the registry holds nothing to compare it with"
        out.append(finding("g", "*", where, key, "not_comparable", why, None, stated[key]))
    requested: dict[str, list] = {}
    for row in about:
        if len(row) >= 3 and row[0] == "requested id":
            requested.setdefault(row[1], []).append(row[2])
    for nct in ids:
        statuses = requested.get(nct, [])
        if len(statuses) != 1:
            result = "omitted" if not statuses else "duplicated"
            why = f"{len(statuses)} rows account for the requested ID"
            out.append(finding("g", nct, where, "requested id", result, why, 1, len(statuses)))
        elif nct not in fetched:
            why = "not the NCT number of a record fetched here; how it was answered is not checked"
            out.append(finding("g", nct, where, "requested id", "not_comparable", why, None, statuses[0]))
        else:
            result, why = value_result("found", statuses[0])
            out.append(finding("g", nct, where, "requested id", result, why, "found", statuses[0]))
    for nct in sorted(set(requested) - set(ids)):
        why = "an ID the selection did not request"
        out.append(finding("g", nct, where, "requested id", "differ", why, None, requested[nct]))
    return out


# ----------------------------------------------------------------------------------------------------------
# Pure decisions: (d), (f), the summary and the defects
# ----------------------------------------------------------------------------------------------------------


BOM = b"\xef\xbb\xbf"


def csv_bytes_results(pulled: bytes, fetched: bytes) -> list[dict]:
    """(pure — pinned)

    Comparison (d): the pulled studies.csv against the API's CSV byte for byte. When they differ: a leading
    UTF-8 byte-order mark on one side only is named on its own, and the rest is compared line by line (each
    line kept with its own line ending), each line named by its study, so that a change in one line is seen
    as that line's difference.
    """
    whole = (hashlib.sha256(fetched).hexdigest(), hashlib.sha256(pulled).hexdigest())
    if pulled == fetched:
        return [finding("d", "*", "studies.csv", "studies.csv", "agree", "byte for byte identical", *whole)]
    out = [finding("d", "*", "studies.csv", "studies.csv", "differ", "not byte for byte identical", *whole)]
    if pulled.startswith(BOM) != fetched.startswith(BOM):
        side = "studies.csv" if pulled.startswith(BOM) else "the API's CSV"
        out.append(
            finding(
                "d",
                "*",
                "byte-order mark",
                "studies.csv byte-order mark",
                "differ",
                f"a UTF-8 byte-order mark (EF BB BF) begins {side} only",
                fetched[:3].hex(),
                pulled[:3].hex(),
            )
        )
        pulled, fetched = pulled.removeprefix(BOM), fetched.removeprefix(BOM)
    ours, theirs = pulled.splitlines(keepends=True), fetched.splitlines(keepends=True)
    for index in range(max(len(ours), len(theirs))):
        mine = ours[index] if index < len(ours) else None
        sent = theirs[index] if index < len(theirs) else None
        line = sent if sent is not None else mine
        named = re.match(rb"NCT\d{8}", line)
        nct = named.group().decode() if named else "*"
        where = "header" if index == 0 else f"line {index + 1}"
        if mine == sent:
            out.append(finding("d", nct, where, "studies.csv line", "agree", ""))
        elif mine is None:
            out.append(
                finding("d", nct, where, "studies.csv line", "omitted", "a line of the API's CSV missing")
            )
        elif sent is None:
            out.append(
                finding("d", nct, where, "studies.csv line", "differ", "a line the API's CSV does not have")
            )
        else:
            at = next(
                i
                for i in range(min(len(mine), len(sent)) + 1)
                if i >= min(len(mine), len(sent)) or mine[i] != sent[i]
            )
            out.append(
                finding(
                    "d",
                    nct,
                    where,
                    "studies.csv line",
                    "differ",
                    f"the bytes differ from byte {at}",
                    sent[max(0, at - 20) : at + 20].decode("utf-8", "replace"),
                    mine[max(0, at - 20) : at + 20].decode("utf-8", "replace"),
                )
            )
    return out


def compare_records(pulled: dict[str, dict], fetched: dict[str, dict]) -> list[dict]:
    """(pure — pinned)

    Comparison (f): each record of studies.json against the same record fetched independently, as parsed JSON.
    """
    out = []
    for nct in sorted(set(pulled) | set(fetched)):
        if nct not in pulled:
            out.append(finding("f", nct, "studies.json", "record", "omitted", "fetched, not in studies.json"))
        elif nct not in fetched:
            out.append(finding("f", nct, "studies.json", "record", "differ", "in studies.json, not fetched"))
        elif pulled[nct] == fetched[nct]:
            out.append(finding("f", nct, "studies.json", "record", "agree", ""))
        else:
            differing = sorted(
                {
                    field_pattern(t)
                    for t, v in json_leaves(pulled[nct])
                    if resolve(fetched[nct], t) != (True, v)
                }
                | {
                    field_pattern(t)
                    for t, v in json_leaves(fetched[nct])
                    if resolve(pulled[nct], t) != (True, v)
                }
            )
            out.append(
                finding(
                    "f",
                    nct,
                    "studies.json",
                    "record",
                    "differ",
                    "fields differ: " + ", ".join(differing[:20]),
                    None,
                    None,
                )
            )
    return out


def summarize(findings: list[dict]) -> dict:
    """(pure — pinned)

    The results counted per comparison and per field, over all studies: how many agree, differ, are not
    comparable, omitted or duplicated, and in how many studies the field occurs.
    """
    out: dict[str, dict[str, dict]] = {}
    for item in findings:
        cell = out.setdefault(item["comparison"], {}).setdefault(item["field"], {"studies": set()})
        cell[item["result"]] = cell.get(item["result"], 0) + 1
        if item["why"].startswith("absent: "):
            cell["of which absent"] = cell.get("of which absent", 0) + 1
        cell["studies"].add(item["nct"])
    return {
        comparison: {
            field: {**{k: v for k, v in cell.items() if k != "studies"}, "studies": len(cell["studies"])}
            for field, cell in sorted(fields.items())
        }
        for comparison, fields in sorted(out.items())
    }


def issue_key(item: dict) -> tuple:
    """(pure — pinned)

    What identifies a result that is not agreement, for telling a planted defect's results from the clean
    run's: its comparison, study, place and field, and its result.
    """
    return (item["comparison"], item["nct"], item["where"], item["field"], item["result"])


def defect_caught(defect: dict, new_issues: list[dict]) -> list[dict]:
    """(pure — pinned)

    The results, among those the clean run does not have, that name the planted defect's study and file
    part: one of the comparisons that read that file, and the defect's place (its sheet and row, location,
    column or line).
    """
    hits = []
    for item in new_issues:
        if not item["comparison"].startswith(tuple(defect["comparisons"])):
            continue
        if defect["nct"] not in ("*", item["nct"]):
            continue
        if any(mark in (item["where"], item["field"]) for mark in defect["marks"]):
            hits.append(item)
    return hits


# ----------------------------------------------------------------------------------------------------------
# The shell: reading the files, the live run, the defects, the report
# ----------------------------------------------------------------------------------------------------------


def run_dir(date: str) -> Path:
    return HERE / "runs" / date


def now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def live_run(date: str) -> None:
    import httpx

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    ids = selection["nct_ids"]
    out = run_dir(date)
    if out.exists():
        raise SystemExit(f"{out} exists: a run is never overwritten")
    (out / "independent").mkdir(parents=True)
    client = httpx.Client(timeout=180, follow_redirects=False)
    log: dict = {"selection_sha256": hashlib.sha256(SELECTION.read_bytes()).hexdigest(), "nct_ids": ids}

    def fetch(name: str, path: str, params: dict | None) -> dict:
        time.sleep(1.0)
        started = now()
        response = client.get(API + path, params=params)
        body = response.content
        (out / "independent" / name).write_bytes(body)
        return {
            "file": f"independent/{name}",
            "url": str(response.url),
            "status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "requested_at": started,
            "received_at": now(),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "x_total_count": response.headers.get("x-total-count"),
            "x_next_page_token": response.headers.get("x-next-page-token"),
        }

    log["version_before"] = fetch("version-before.json", "/version", None)
    trialledger = Path(sys.executable).parent / "trialledger"
    command = [str(trialledger), "pull", "filter.ids=" + ",".join(ids), "--out", str(out / "pull")]
    started = now()
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    log["pull"] = {
        "command": ["trialledger", *command[1:4], f"acceptance/runs/{date}/pull"],
        "exit": done.returncode,
        "started_at": started,
        "finished_at": now(),
    }
    (out / "pull.log").write_text(done.stdout + done.stderr, encoding="utf-8")
    query = {"filter.ids": ",".join(ids), "pageSize": 100, "countTotal": "true"}
    log["json"] = fetch("studies.page1.json", "/studies", {**query, "format": "json"})
    log["csv"] = fetch("studies.page1.csv", "/studies", {**query, "format": "csv"})
    log["version_after"] = fetch("version-after.json", "/version", None)
    (out / "fetch.json").write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: log[k] for k in ("pull", "json", "csv")}, indent=1))


def read_record_rows(path: Path) -> list[dict]:
    import openpyxl

    sheet = openpyxl.load_workbook(path)["Record"]
    header = [c.value for c in sheet[1]]
    column = {name: header.index(name) for name in ("NCT Number", "Field", "Location", "Value", "Role")}
    rows = []
    for number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        rows.append(
            {
                "row": number,
                "nct": row[column["NCT Number"]],
                "title": row[column["Field"]],
                "location": row[column["Location"]],
                "value": row[column["Value"]],
                "role": row[column["Role"]],
            }
        )
    return rows


def read_about(path: Path) -> list[tuple]:
    import openpyxl

    return [tuple(row) for row in openpyxl.load_workbook(path)["About"].iter_rows(values_only=True)]


def read_review(path: Path) -> tuple[dict[str, list[dict]], list[tuple]]:
    import openpyxl

    book = openpyxl.load_workbook(path)
    sheets: dict[str, list[dict]] = {}
    for sheet in book.worksheets:
        if sheet.title == "About":
            continue
        header = [c.value for c in sheet[1]]
        rows = []
        for number, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            if all(c.value is None for c in row):
                continue
            cells = {header[i]: c.value for i, c in enumerate(row) if i < len(header)}
            links = {
                header[i]: c.hyperlink.target
                for i, c in enumerate(row)
                if i < len(header) and c.hyperlink is not None
            }
            rows.append({"row": number, "cells": cells, "links": links})
        sheets[sheet.title] = rows
    about = [tuple(row) for row in book["About"].iter_rows(values_only=True)]
    return sheets, about


def load_inputs(date: str, folder: Path) -> dict:
    out = run_dir(date)
    fetched_doc = json.loads((out / "independent" / "studies.page1.json").read_text(encoding="utf-8"))
    fetched = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in fetched_doc["studies"]}
    csv_bytes = (out / "independent" / "studies.page1.csv").read_bytes()
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"), newline=""))
    csv_rows = list(reader)
    documented = [
        line.split("|")[1].strip()
        for line in (HERE / "csv-columns.md").read_text().splitlines()
        if line.startswith("| ") and not line.startswith("| Column") and not line.startswith("| ---")
    ]
    pulled_doc = json.loads((folder / "studies.json").read_text(encoding="utf-8"))
    pulled = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in pulled_doc["studies"]}
    return {
        "fetched": fetched,
        "fetched_doc": fetched_doc,
        "csv_bytes": csv_bytes,
        "csv_rows": csv_rows,
        "csv_header": list(reader.fieldnames or []),
        "documented": documented,
        "pulled": pulled,
        "pulled_provenance": pulled_doc.get("provenance", {}),
    }


def compare_folder(date: str, folder: Path) -> dict:
    inputs = load_inputs(date, folder)
    studies = inputs["fetched"]
    titles = metadata_titles(json.loads(METADATA.read_text(encoding="utf-8")))
    record_rows = read_record_rows(folder / "record.xlsx")
    record_cells: dict[str, dict[str, object]] = {}
    for row in record_rows:
        tokens = parse_location(row["location"])
        if tokens is not None:
            record_cells.setdefault(row["nct"], {})[format_location(tokens)] = row["value"]
    review, about = read_review(folder / "review.xlsx")
    record_about = read_about(folder / "record.xlsx")
    findings = compare_record_rows(studies, record_rows, titles)
    findings += compare_csv(
        studies, inputs["csv_rows"], inputs["csv_header"], inputs["documented"], record_cells
    )
    findings += compare_review(studies, review)
    findings += compare_declared(REVIEW_SHEETS, about)
    version = json.loads((run_dir(date) / "independent" / "version-before.json").read_text(encoding="utf-8"))
    ids = json.loads(SELECTION.read_text(encoding="utf-8"))["nct_ids"]
    findings += provenance_results(record_about, "record.xlsx About", version, ids, studies)
    findings += provenance_results(about, "review.xlsx About", version, ids, studies)
    findings += csv_bytes_results((folder / "studies.csv").read_bytes(), inputs["csv_bytes"])
    findings += compare_records(inputs["pulled"], studies)
    verify = subprocess.run(
        [str(Path(sys.executable).parent / "trialledger"), "verify", str(folder)],
        capture_output=True,
        text=True,
        check=False,
    )
    said = (verify.stdout + verify.stderr).strip()
    (folder.parent / f"verify-{folder.name}.txt").write_text(said.replace(str(ROOT) + "/", "") + "\n")
    lines = said.splitlines()
    findings.append(
        finding(
            "e",
            "*",
            "trialledger verify",
            "verify",
            "agree" if verify.returncode == 0 else "differ",
            f"exit {verify.returncode}; {len(lines)} lines of output (verify-{folder.name}.txt); last: "
            + (lines[-1].replace(str(ROOT) + "/", "")[:300] if lines else ""),
        )
    )
    declared = [row for row in about if row and row[0] == "column"]
    compared = {f"{sheet} › {column}" for sheet, spec in REVIEW_SHEETS.items() for column in spec["columns"]}
    compared |= {"Adverse Events › Participants at Risk", "Adverse Events › At Risk Source"}
    not_compared = [
        {"column": row[1], "status": row[2], "declared_source": row[3]}
        for row in declared
        if row[1] not in compared
    ]
    record_columns = [
        {"column": row[1], "status": row[2], "declared_source": row[3]}
        for row in record_about
        if row and row[0] == "column"
    ]
    return {
        "findings": findings,
        "not_compared_columns": not_compared,
        "record_columns": record_columns,
        "provenance": inputs["pulled_provenance"],
        "record_rows": len(record_rows),
        "leaves": sum(len(json_leaves(s)) for s in studies.values()),
        "review_rows": {name: len(rows) for name, rows in review.items()},
    }


def code_digest() -> dict:
    return {
        "file": "acceptance/compare.py",
        "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def keep_superseded(path: Path) -> None:
    """Before a result file is rewritten, keep what it said: the whole of a small one, and of results.json
    its digest, the reader's digest, its summary and every result that is not agreement or not comparable."""
    if not path.exists():
        return
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    kept = path.with_name(f"{path.stem}-superseded-{digest[:12]}.json")
    if path.name != "results.json":
        kept.write_bytes(data)
        return
    old = json.loads(data)
    summary = {
        "what": "results.json before a later reader rewrote it; not-comparable results left out",
        "sha256": digest,
        "code": old.get("code"),
        "compared_at": old.get("compared_at"),
        "summary": old.get("summary"),
        "issues": [i for i in old.get("issues", []) if i["result"] != "not_comparable"],
    }
    kept.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def compare_step(date: str) -> None:
    out = run_dir(date)
    keep_superseded(out / "results.json")
    result = compare_folder(date, out / "pull")
    findings = result.pop("findings")
    fetch = json.loads((out / "fetch.json").read_text(encoding="utf-8"))
    payload = {
        "date": date,
        "compared_at": now(),
        "code": code_digest(),
        "selection_sha256": hashlib.sha256(SELECTION.read_bytes()).hexdigest(),
        "fetch": fetch,
        **result,
        "summary": summarize(findings),
        "issues": [item for item in findings if item["result"] != "agree"],
    }
    (out / "results.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    print(len(findings), "results,", len(payload["issues"]), "not agreement")


# ----- the defects -----


def _shift_up(sheet, row: int) -> None:
    """Delete a row by moving every later row's values and links up one, links staying with their cells."""
    last = sheet.max_row
    for r in range(row, last):
        for c in range(1, sheet.max_column + 1):
            below = sheet.cell(r + 1, c)
            cell = sheet.cell(r, c)
            cell.value = below.value
            cell.hyperlink = below.hyperlink.target if below.hyperlink is not None else None
    sheet.delete_rows(last)


def _insert_copy(sheet, row: int) -> None:
    """Duplicate a row just below itself, moving every later row down one, links with their cells."""
    last = sheet.max_row
    for r in range(last, row - 1, -1):
        for c in range(1, sheet.max_column + 1):
            above = sheet.cell(r, c)
            cell = sheet.cell(r + 1, c)
            cell.value = above.value
            cell.hyperlink = above.hyperlink.target if above.hyperlink is not None else None


def plant_defects(folder: Path, studies: dict[str, dict]) -> list[dict]:
    """Plant the defects in a copied folder; each named with where it is and what should catch it."""
    import openpyxl

    defects: list[dict] = []
    record_path, review_path = folder / "record.xlsx", folder / "review.xlsx"
    record = openpyxl.load_workbook(record_path)
    sheet = record["Record"]

    def find_row(nct: str, location: str) -> int:
        for r in range(2, sheet.max_row + 1):
            if sheet.cell(r, 1).value == nct and sheet.cell(r, 4).value == location:
                return r
        raise LookupError((nct, location))

    ids = sorted(studies)
    ident, status = P + "identificationModule.", P + "statusModule."
    # 1. A changed text value: one letter of a brief title.
    nct = ids[0]
    r = find_row(nct, ident + "briefTitle")
    old = sheet.cell(r, 5).value
    sheet.cell(r, 5).value = old.replace("a", "e", 1) if "a" in old else old + "."
    defects.append(
        {
            "id": 1,
            "kind": "changed text value",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a", "b-workbook"],
            "marks": [ident + "briefTitle"],
            "what": f"briefTitle {old!r} → {sheet.cell(r, 5).value!r}",
        }
    )
    # 2. A changed number: an enrollment count plus one.
    nct = next(n for n in ids[1:] if "count" in studies[n][P[:-1]]["designModule"].get("enrollmentInfo", {}))
    r = find_row(nct, P + "designModule.enrollmentInfo.count")
    old = sheet.cell(r, 5).value
    sheet.cell(r, 5).value = old + 1
    defects.append(
        {
            "id": 2,
            "kind": "changed number",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a", "b-workbook"],
            "marks": [P + "designModule.enrollmentInfo.count"],
            "what": f"enrollment {old} → {old + 1}",
        }
    )
    # 3. A truncated text: the eligibility criteria cut to half their length.
    nct = next(n for n in ids[2:] if "eligibilityCriteria" in studies[n][P[:-1]].get("eligibilityModule", {}))
    loc = P + "eligibilityModule.eligibilityCriteria"
    r = find_row(nct, loc)
    old = sheet.cell(r, 5).value
    sheet.cell(r, 5).value = old[: len(old) // 2]
    defects.append(
        {
            "id": 3,
            "kind": "truncated text",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a", "b-workbook"],
            "marks": [loc],
            "what": f"eligibilityCriteria cut from {len(old)} to {len(old) // 2} characters",
        }
    )
    # 4. A swapped pair of values between studies: two overall statuses that differ.
    pair = [
        n
        for n in ids
        if studies[n][P[:-1]]["statusModule"]["overallStatus"]
        != studies[ids[0]][P[:-1]]["statusModule"]["overallStatus"]
    ][:1] + [ids[0]]
    loc = status + "overallStatus"
    r1, r2 = find_row(pair[0], loc), find_row(pair[1], loc)
    v1, v2 = sheet.cell(r1, 5).value, sheet.cell(r2, 5).value
    sheet.cell(r1, 5).value, sheet.cell(r2, 5).value = v2, v1
    defects.append(
        {
            "id": 4,
            "kind": "swapped pair between studies",
            "file": "record.xlsx",
            "nct": "*",
            "comparisons": ["a", "b-workbook"],
            "marks": [loc],
            "what": f"overallStatus of {pair[0]} ({v1}) and {pair[1]} ({v2})",
        }
    )
    # 5. A duplicated row: a condition's row repeated just below itself.
    nct = ids[3]
    loc = P + "conditionsModule.conditions[0]"
    r = find_row(nct, loc)
    _insert_copy(sheet, r)
    defects.append(
        {
            "id": 5,
            "kind": "duplicated row",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a", "b-workbook"],
            "marks": [loc],
            "what": f"the Record row of {loc} twice",
        }
    )
    # 6. A dropped row: a location's facility, gone.
    nct = next(n for n in ids[4:] if studies[n][P[:-1]].get("contactsLocationsModule", {}).get("locations"))
    loc = P + "contactsLocationsModule.locations[0].city"
    r = find_row(nct, loc)
    _shift_up(sheet, r)
    defects.append(
        {
            "id": 6,
            "kind": "dropped row",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a", "b-workbook"],
            "marks": [loc],
            "what": f"the Record row of {loc} removed",
        }
    )
    # 14. A changed role: an arm's Role names an arm the record does not have.
    r = next(r for r in range(2, sheet.max_row + 1) if str(sheet.cell(r, 6).value or "").startswith("arm="))
    nct, loc, old = sheet.cell(r, 1).value, sheet.cell(r, 4).value, sheet.cell(r, 6).value
    sheet.cell(r, 6).value = "arm=An arm the record does not name"
    defects.append(
        {
            "id": 14,
            "kind": "changed text value",
            "file": "record.xlsx",
            "nct": nct,
            "comparisons": ["a-role"],
            "marks": [loc],
            "what": f"the Role of {loc}: {old!r} → {sheet.cell(r, 6).value!r}",
        }
    )
    # 15. A changed provenance value: the registry's data date in record.xlsx's About sheet.
    about = record["About"]
    r = next(r for r in range(1, about.max_row + 1) if about.cell(r, 2).value == "data_timestamp")
    old = about.cell(r, 3).value
    about.cell(r, 3).value = "2026-10-29T09:00:04"
    defects.append(
        {
            "id": 15,
            "kind": "altered date",
            "file": "record.xlsx",
            "nct": "*",
            "comparisons": ["g"],
            "marks": ["data_timestamp"],
            "what": f"About › data_timestamp {old} → {about.cell(r, 3).value}",
        }
    )
    record.save(record_path)

    review = openpyxl.load_workbook(review_path)
    studies_sheet = review["Studies"]
    header = [c.value for c in studies_sheet[1]]

    def study_row(nct: str) -> int:
        return next(r for r in range(2, studies_sheet.max_row + 1) if studies_sheet.cell(r, 1).value == nct)

    # 7. A changed link: one study's registry link pointing at another study's page.
    nct, other = ids[5], ids[6]
    r = study_row(nct)
    studies_sheet.cell(r, 1).hyperlink = STUDY_URL + other
    defects.append(
        {
            "id": 7,
            "kind": "changed link",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c-links"],
            "marks": [f"Studies!row {r}"],
            "what": f"Studies › NCT Number link of {nct} → {STUDY_URL + other}",
        }
    )
    # 8. An altered date: a start date a year later.
    nct = next(n for n in ids[7:] if "date" in studies[n][P[:-1]]["statusModule"].get("startDateStruct", {}))
    r = study_row(nct)
    column = header.index("Start Date") + 1
    old = studies_sheet.cell(r, column).value
    new = str(int(old[:4]) + 1) + old[4:]
    studies_sheet.cell(r, column).value = new
    defects.append(
        {
            "id": 8,
            "kind": "altered date",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c"],
            "marks": [f"Studies!row {r}"],
            "what": f"Studies › Start Date {old} → {new}",
        }
    )
    # 9. A dropped row in a review sheet: one registered outcome gone.
    outcomes = review["Outcomes"]
    r = 2
    nct = outcomes.cell(r, 1).value
    location = outcomes.cell(r, [c.value for c in outcomes[1]].index("Location") + 1).value
    _shift_up(outcomes, r)
    defects.append(
        {
            "id": 9,
            "kind": "dropped row",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c-rows"],
            "marks": [location],
            "what": f"the Outcomes row of {location} removed",
        }
    )
    # 10. A duplicated row in a review sheet: one site twice.
    sites = review["Sites"]
    r = 2
    nct = sites.cell(r, 1).value
    location = sites.cell(r, [c.value for c in sites[1]].index("Location") + 1).value
    _insert_copy(sites, r)
    defects.append(
        {
            "id": 10,
            "kind": "duplicated row",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c-rows"],
            "marks": [location],
            "what": f"the Sites row of {location} twice",
        }
    )
    # 11. A changed number in posted results: one adverse event's participants affected plus one.
    events = review["Adverse Events"]
    head = [c.value for c in events[1]]
    column = head.index("Participants Affected") + 1
    r = next(r for r in range(2, events.max_row + 1) if isinstance(events.cell(r, column).value, int))
    nct = events.cell(r, 1).value
    old = events.cell(r, column).value
    events.cell(r, column).value = old + 1
    defects.append(
        {
            "id": 11,
            "kind": "changed number",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c"],
            "marks": [f"Adverse Events!row {r}"],
            "what": f"Adverse Events › Participants Affected {old} → {old + 1}",
        }
    )
    # 16. A changed computed count: one adverse event's Participants at Risk plus one.
    column = head.index("Participants at Risk") + 1
    r = next(r for r in range(r + 1, events.max_row + 1) if isinstance(events.cell(r, column).value, int))
    nct = events.cell(r, 1).value
    old = events.cell(r, column).value
    events.cell(r, column).value = old + 1
    defects.append(
        {
            "id": 16,
            "kind": "changed number",
            "file": "review.xlsx",
            "nct": nct,
            "comparisons": ["c-rule"],
            "marks": [f"Adverse Events!row {r}"],
            "what": f"Adverse Events › Participants at Risk {old} → {old + 1}",
        }
    )
    # 12. A swapped pair between studies in review.xlsx: two lead sponsors exchanged.
    a, b = ids[8], ids[9]
    column = header.index("Lead Sponsor") + 1
    ra, rb = study_row(a), study_row(b)
    va, vb = studies_sheet.cell(ra, column).value, studies_sheet.cell(rb, column).value
    studies_sheet.cell(ra, column).value, studies_sheet.cell(rb, column).value = vb, va
    defects.append(
        {
            "id": 12,
            "kind": "swapped pair between studies",
            "file": "review.xlsx",
            "nct": "*",
            "comparisons": ["c"],
            "marks": [f"Studies!row {ra}", f"Studies!row {rb}"],
            "what": f"Lead Sponsor of {a} ({va!r}) and {b} ({vb!r})",
        }
    )
    review.save(review_path)

    # 13. A changed character in studies.csv.
    path = folder / "studies.csv"
    data = bytearray(path.read_bytes())
    at = data.index(b"COMPLETED")
    data[at : at + 9] = b"COMPLETEX"
    path.write_bytes(bytes(data))
    lines = bytes(data).removeprefix(BOM).splitlines(keepends=True)
    line = next(i for i, text in enumerate(lines) if b"COMPLETEX" in text)
    defects.append(
        {
            "id": 13,
            "kind": "changed text value",
            "file": "studies.csv",
            "nct": "*",
            "comparisons": ["d"],
            "marks": ["header" if line == 0 else f"line {line + 1}"],
            "what": f"the first 'COMPLETED' in studies.csv (line {line + 1}) → 'COMPLETEX'",
        }
    )
    return defects


def defects_step(date: str) -> None:
    out = run_dir(date)
    keep_superseded(out / "defects.json")
    clean = json.loads((out / "results.json").read_text(encoding="utf-8"))
    copy = out / "defects-copy"
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(out / "pull", copy)
    inputs = load_inputs(date, copy)
    defects = plant_defects(copy, inputs["fetched"])
    result = compare_folder(date, copy)
    clean_keys = {issue_key(item) for item in clean["issues"]}
    new = [
        item for item in result["findings"] if item["result"] != "agree" and issue_key(item) not in clean_keys
    ]
    for defect in defects:
        hits = defect_caught(defect, new)
        defect["caught"] = bool(hits)
        defect["caught_by"] = hits
    attributed = {issue_key(hit) for defect in defects for hit in defect["caught_by"]}
    payload = {
        "date": date,
        "compared_at": now(),
        "code": code_digest(),
        "clean_results_sha256": hashlib.sha256((out / "results.json").read_bytes()).hexdigest(),
        "defects": defects,
        "new_issues": len(new),
        "unattributed": [
            item for item in new if issue_key(item) not in attributed and item["comparison"] != "e"
        ],
        "verify_on_copy": [item for item in result["findings"] if item["comparison"] == "e"],
    }
    (out / "defects.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    print(
        sum(d["caught"] for d in defects),
        "of",
        len(defects),
        "defects caught;",
        len(payload["unattributed"]),
        "unattributed",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["run", "compare", "defects", "report"])
    parser.add_argument("--date", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    if args.step == "run":
        live_run(args.date)
    elif args.step == "compare":
        compare_step(args.date)
    elif args.step == "defects":
        defects_step(args.date)
    else:
        from acceptance.report import write_report

        write_report(args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
