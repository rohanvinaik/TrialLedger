"""The reviewer's tasks, each a check over a run folder (refine-landscape-record design §6 and task 5.2).

A clinical reviewer opens a run's workbook to do six things; each is checked here as that reviewer would do
it, from the record (landscape.json), the workbook read back (landscape.xlsx) and the assistant's record
tool, all read as data or called as black boxes (acceptance/preserve.py reads the files; `mcp_ask` speaks
the Model Context Protocol to `trialledger mcp`'s answer function). Each task names its expected destination
(the sheets a reviewer turns to), the evidence it found there (each item with its address in the record) and
its unresolved cases (what the reviewer cannot settle from the run, in words), beside its findings (what the
run gets wrong, by name):

- `eligibility_across`: compare eligibility across selected trials (Eligibility);
- `eligible_vs_enrolled`: tell the eligible from the enrolled population (Trial review, Baseline);
- `result_population`: a result's analysis population and denominator (Posted results);
- `safety_in_period`: safety within its reporting period (Safety, Groups);
- `biomarker_trace`: a biomarker, and every reading, traced to its source words (Biomarkers, Readings);
- `address_answered`: a workbook row's address asked of the record tool returns the row's value (MCP).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from acceptance import preserve
from acceptance.preserve import is_value_object, same_value, shows_text
from TrialLedger import contract

RECORD_NAME = "landscape.json"
BOOK_NAME = "landscape.xlsx"
# The record tool's part that answers an address, and its argument (unit F's interface, 2026-11-01).
ADDRESS_PART = "address"
# A criterion the banks typed nothing in (design §2).
NO_READING = preserve.EMPTY_READING_WORDS["studies[].criteria[].readings"]
# The title the registry gives the baseline's group of all participants.
BASELINE_TOTAL = "Total"
# A paged answer is read page by page up to this many pages.
PAGE_BOUND = 1000

FINDING_WORDS = {
    "not_in_destination": "the reviewer's destination sheet has no row for what the record holds",
    "affected_exceeds_at_risk": "more participants affected than at risk, as the record holds them",
    "untraced": "a reading's words are not in the registry text it read",
    "unwarranted": "a reading's warrant does not hold (its words, its heading or flag, or its derivation)",
    "key_criterion_differs": "a key criterion's text or role is not that of the criterion its reading names",
    "not_answered": "the record tool did not answer the address",
    "answered_differently": "the record tool's answer is not the record's value at the address",
}


class Item(NamedTuple):
    """One piece of evidence or one unresolved case: the trial, its address in the record, and what it is."""

    nct: str
    address: str
    what: str
    value: Any = None


class TaskResult(NamedTuple):
    """A reviewer's task as checked: what it asks, where a reviewer looks, what was found there, what stays
    unresolved, and what the run gets wrong."""

    task: str
    destination: tuple[str, ...]
    evidence: list[Item]
    unresolved: list[Item]
    findings: list[Item]


class Run(NamedTuple):
    """A run folder as read: its record, its workbook's listings (None when there is no workbook) and the
    registry bodies its studies were read from, by NCT number (empty when not given)."""

    record: dict[str, Any]
    sheets: dict[str, tuple[list[str], list[list[Any]]]] | None
    bodies: dict[str, dict[str, Any]]


def load_run(folder: Path, bodies: dict[str, dict[str, Any]] | None = None) -> Run:
    """A run folder's record and workbook."""
    record = json.loads((folder / RECORD_NAME).read_text(encoding="utf-8"))
    book = folder / BOOK_NAME
    sheets = preserve.workbook_sheets(book) if book.is_file() else None
    return Run(record, sheets, bodies or {})


# ── the pure decision ───────────────────────────────────────────────────────────────────────────────────


def words_traced(words: list[str], texts: list[str]) -> tuple[str, list[str]]:
    """Whether a reading's words are the registry's own (pure — pinned).

    `words` are the words a reading names; `texts` the registry text at the paths it read. Codes: traced
    (every word appears, exactly, in some text); no_words (the reading names none); untraced (with the words
    no text holds).
    """
    if not words:
        return "no_words", []
    missing = [word for word in words if not any(word in text for text in texts)]
    return ("untraced", missing) if missing else ("traced", [])


# ── helpers over the record and the workbook ────────────────────────────────────────────────────────────


def _studies(run: Run, ncts: list[str] | None) -> list[tuple[int, dict[str, Any]]]:
    studies = [(i, s) for i, s in enumerate(run.record.get("studies") or []) if isinstance(s, dict)]
    return [(i, s) for i, s in studies if ncts is None or s.get("nct") in ncts]


def _rows(run: Run, sheet: str) -> list[dict[str, Any]]:
    if run.sheets is None or sheet not in run.sheets:
        return []
    headers, rows = run.sheets[sheet]
    return [dict(zip(headers, row, strict=False)) for row in rows]


def _addressed(run: Run, sheet: str) -> set[str]:
    return {row.get(contract.ADDRESS) for row in _rows(run, sheet)}


def _no_workbook(run: Run, destination: tuple[str, ...]) -> list[Item]:
    if run.sheets is not None:
        return []
    return [Item("", "", f"no workbook in the run folder: {', '.join(destination)} not checked")]


def _listed(run: Run, sheet: str, nct: str, addresses: list[str]) -> list[Item]:
    """A finding for each address the destination listing has no row for (with a workbook only)."""
    if run.sheets is None:
        return []
    held = _addressed(run, sheet)
    return [Item(nct, a, FINDING_WORDS["not_in_destination"], sheet) for a in addresses if a not in held]


def _nodes(i: int, study: dict[str, Any], sheet: str) -> list[str]:
    """The addresses of a study's nodes a listing shows a row for."""
    prefix = len("/studies/0")
    return [
        f"/studies/{i}{pointer[prefix:]}"
        for grain in preserve.LISTING_GRAINS[sheet]
        for pointer in preserve.grain_nodes({"studies": [study]}, grain)
    ]


def _plain(value: Any) -> bool:
    return value is not None and not is_value_object(value)


def _words(value: Any) -> str:
    if is_value_object(value):
        return f"{value.get('status')}: {value.get('note')}"
    return str(value)


# ── the tasks ───────────────────────────────────────────────────────────────────────────────────────────


def eligibility_across(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """Compare eligibility across the selected trials: each criterion, its role and its labelled readings.

    Unresolved: a trial whose criteria were not itemized (with the coverage reading's reason); a criterion
    with no reading, its readings empty ("No reading produced", which does not mean it carries no clinical
    information), named with its address and its text. Findings: a key criterion whose text or role is not
    that of the criterion its reading names (`reading.at`)."""
    destination = (contract.ELIGIBILITY,)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        criteria = study.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            eligibility = study.get("eligibility") if isinstance(study.get("eligibility"), dict) else {}
            coverage = eligibility.get("coverage")
            why = _words(coverage) if coverage is not None else "the record holds no itemized criteria"
            unresolved.append(Item(nct, f"/studies/{i}/criteria", f"criteria not itemized ({why})"))
            continue
        addresses = []
        for j, criterion in enumerate(criteria):
            address = f"/studies/{i}/criteria/{j}"
            addresses.append(address)
            if not isinstance(criterion, dict):
                continue
            role = criterion.get("role")
            text = criterion.get("text")
            evidence.append(Item(nct, address, "criterion", [criterion.get("heading"), _words(role), text]))
            readings = criterion.get("readings")
            if readings in (None, []) or (is_value_object(readings) and not readings.get("result")):
                unresolved.append(Item(nct, address, NO_READING, text))
        findings += _listed(run, contract.ELIGIBILITY, nct, addresses)
        findings += _key_criteria_findings(nct, i, study, criteria)
    return TaskResult(
        "compare eligibility across the selected trials", destination, evidence, unresolved, findings
    )


def _key_criteria_findings(nct: str, i: int, study: dict[str, Any], criteria: list[Any]) -> list[Item]:
    """Each key criterion against the criterion its reading names: the same text and the same role."""
    findings = []
    for k, key in enumerate(study.get("key_criteria") or []):
        if not isinstance(key, dict):
            continue
        reading = key.get("reading") if isinstance(key.get("reading"), dict) else {}
        at = reading.get("at")
        place = at.split("/")[-1] if isinstance(at, str) else ""
        source = criteria[int(place)] if place.isdigit() and int(place) < len(criteria) else None
        address = f"/studies/{i}/key_criteria/{k}"
        if not isinstance(source, dict):
            findings.append(Item(nct, address, FINDING_WORDS["key_criterion_differs"], ["no criterion", at]))
            continue
        role = source.get("role")
        role = role.get("result") if is_value_object(role) else role
        if key.get("text") != source.get("text") or key.get("role") != role:
            held = [key.get("text"), key.get("role")]
            findings.append(Item(nct, address, FINDING_WORDS["key_criterion_differs"], held))
    return findings


def eligible_vs_enrolled(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """Tell the eligible population (the registry's eligibility: ages, sex, healthy volunteers) from the
    enrolled one (the enrollment) and the analysed one (the baseline's population and denominators).

    Unresolved: an anticipated enrollment; no baseline posted; a baseline denominator total that differs from
    the enrollment (the reviewer reads why in the baseline's population description). The total is the
    registry's own "Total" group's count at the module's first denominator where the baseline lists one, else
    the groups' counts summed."""
    destination = (contract.REVIEW, contract.BASELINE)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    review = _rows(run, contract.REVIEW)
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        population = study.get("population") if isinstance(study.get("population"), dict) else {}
        for key in ("minimum_age", "maximum_age", "sex", "healthy_volunteers"):
            if key in population:
                evidence.append(
                    Item(nct, f"/studies/{i}/population/{key}", f"eligible: {key}", population[key])
                )
        enrollment = study.get("enrollment") if isinstance(study.get("enrollment"), dict) else {}
        count = enrollment.get("count")
        evidence.append(Item(nct, f"/studies/{i}/enrollment", "enrolled", [count, enrollment.get("type")]))
        if enrollment.get("type") != "ACTUAL":
            unresolved.append(
                Item(
                    nct,
                    f"/studies/{i}/enrollment/type",
                    "the enrollment is not actual",
                    enrollment.get("type"),
                )
            )
        if run.sheets is not None and _plain(count):
            mine = [row for row in review if row.get("Trial ID") == nct]
            if not any(
                isinstance(row.get("Value"), (str, int)) and shows_text(str(row.get("Value")), str(count))
                for row in mine
            ):
                findings.append(
                    Item(
                        nct,
                        f"/studies/{i}/enrollment/count",
                        "no Trial review row shows the enrollment",
                        count,
                    )
                )
        baseline = study.get("baseline")
        if not isinstance(baseline, dict) or is_value_object(baseline):
            why = (
                f"no baseline characteristics posted ({_words(baseline)})"
                if baseline
                else "no baseline characteristics posted"
            )
            unresolved.append(Item(nct, f"/studies/{i}/baseline", why))
            continue
        evidence.append(
            Item(
                nct,
                f"/studies/{i}/baseline/population",
                "analysed (baseline population)",
                _words(baseline.get("population")),
            )
        )
        totals = {g.get("id") for g in baseline.get("groups") or [] if g.get("title") == BASELINE_TOTAL}
        counts: dict[str, int] = {}
        whole = True
        for d, denominator in enumerate(baseline.get("denominators") or []):
            for c, entry in enumerate(denominator.get("counts") or []):
                address = f"/studies/{i}/baseline/denominators/{d}/counts/{c}"
                evidence.append(Item(nct, address, f"analysed, {entry.get('group')}", entry.get("value")))
                value = entry.get("value")
                whole = whole and isinstance(value, str) and value.isdigit()
                if d == 0 and isinstance(value, str) and value.isdigit():
                    counts[entry.get("group")] = int(value)
        held_totals = [counts[group] for group in totals if group in counts]
        total = held_totals[0] if held_totals else sum(counts.values())
        if whole and isinstance(count, int) and total != count:
            unresolved.append(
                Item(
                    nct,
                    f"/studies/{i}/baseline/denominators",
                    f"the baseline analysed {total} of {count} enrolled",
                )
            )
        findings += _listed(run, contract.BASELINE, nct, _nodes(i, study, contract.BASELINE))
    return TaskResult(
        "tell the eligible from the enrolled population", destination, evidence, unresolved, findings
    )


def result_population(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """For each posted result: its analysis population and the denominator of each group's value.

    Unresolved: a measure whose population is not stated; a value whose group has no denominator at the
    measure's or its class's scope; a value the registry gives as "NA" without a comment."""
    destination = (contract.POSTED,)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        outcomes = study.get("posted_outcomes")
        if not isinstance(outcomes, list):
            unresolved.append(
                Item(
                    nct,
                    f"/studies/{i}/posted_outcomes",
                    "no results posted",
                    _words(study.get("results_posted")),
                )
            )
            continue
        addresses = []
        for m, measure in enumerate(outcomes):
            base = f"/studies/{i}/posted_outcomes/{m}"
            population = measure.get("population")
            if _plain(population):
                evidence.append(Item(nct, f"{base}/population", "analysis population", population))
            else:
                unresolved.append(
                    Item(nct, f"{base}/population", "analysis population not stated", _words(population))
                )
            measure_denoms = _denominators(measure)
            for c, klass in enumerate(measure.get("classes") or []):
                class_denoms = _denominators(klass)
                for k, category in enumerate(klass.get("categories") or []):
                    for v, value in enumerate(category.get("measurements") or []):
                        address = f"{base}/classes/{c}/categories/{k}/measurements/{v}"
                        addresses.append(address)
                        group = value.get("group")
                        denominator = class_denoms.get(group) or measure_denoms.get(group)
                        if denominator is None:
                            unresolved.append(Item(nct, address, f"no denominator for group {group}"))
                        else:
                            evidence.append(
                                Item(
                                    nct,
                                    address,
                                    f"{group}: value over denominator",
                                    [value.get("value"), denominator],
                                )
                            )
                        if value.get("value") == "NA" and not _plain(value.get("comment")):
                            unresolved.append(Item(nct, address, "NA without the registry's reason"))
        findings += _listed(run, contract.POSTED, nct, addresses)
    return TaskResult(
        "find a result's analysis population and denominator", destination, evidence, unresolved, findings
    )


def _denominators(node: dict[str, Any]) -> dict[str, list[Any]]:
    """A measure's or class's denominators by group: each its count and units."""
    found: dict[str, list[Any]] = {}
    for denominator in node.get("denominators") or []:
        for entry in denominator.get("counts") or []:
            found.setdefault(entry.get("group"), [entry.get("value"), denominator.get("units")])
    return found


def safety_in_period(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """Read safety within its reporting period: the period, the threshold, each group's totals at risk, and
    each event's counts per group.

    Unresolved: no reporting period stated; a group's count the registry does not give ("Not reported").
    Findings: more affected than at risk."""
    destination = (contract.SAFETY, contract.GROUPS)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        events = study.get("adverse_events")
        base = f"/studies/{i}/adverse_events"
        if not isinstance(events, dict) or is_value_object(events):
            why = f"no adverse events posted ({_words(events)})" if events else "no adverse events posted"
            unresolved.append(Item(nct, base, why))
            continue
        period = events.get("time_frame")
        if _plain(period):
            evidence.append(Item(nct, f"{base}/time_frame", "reporting period", period))
        else:
            unresolved.append(
                Item(
                    nct,
                    f"{base}/time_frame",
                    "reporting period not stated: the counts cannot be placed in time",
                )
            )
        evidence.append(
            Item(
                nct,
                f"{base}/frequency_threshold",
                "threshold for other events (%)",
                _words(events.get("frequency_threshold")),
            )
        )
        groups = events.get("groups") or []
        for g, group in enumerate(groups):
            address = f"{base}/groups/{g}"
            evidence.append(
                Item(
                    nct,
                    address,
                    f"G{g + 1}: {group.get('title')}",
                    [
                        group.get(k)
                        for k in ("serious_affected", "serious_at_risk", "other_affected", "other_at_risk")
                    ],
                )
            )
            for kind in ("deaths", "serious", "other"):
                findings += _exceeds(
                    nct, address, group.get(f"{kind}_affected"), group.get(f"{kind}_at_risk")
                )
        ids = [group.get("id") for group in groups]
        for e, event in enumerate(events.get("events") or []):
            address = f"{base}/events/{e}"
            counts = {c.get("group"): c for c in event.get("counts") or [] if isinstance(c, dict)}
            for n, group_id in enumerate(ids, start=1):
                held = counts.get(group_id, {})
                for stat in ("affected", "at_risk", "events"):
                    if not isinstance(held.get(stat), int):
                        unresolved.append(Item(nct, address, f"G{n} {stat}: {preserve.NOT_REPORTED}"))
                findings += _exceeds(nct, address, held.get("affected"), held.get("at_risk"))
        findings += _listed(run, contract.SAFETY, nct, _nodes(i, study, contract.SAFETY))
        findings += _listed(run, contract.GROUPS, nct, [f"{base}/groups/{g}" for g in range(len(groups))])
    return TaskResult("read safety within its reporting period", destination, evidence, unresolved, findings)


def _exceeds(nct: str, address: str, affected: Any, at_risk: Any) -> list[Item]:
    if isinstance(affected, int) and isinstance(at_risk, int) and affected > at_risk:
        return [Item(nct, address, FINDING_WORDS["affected_exceeds_at_risk"], [affected, at_risk])]
    return []


def _readings(study: dict[str, Any], i: int) -> list[tuple[str, str, dict[str, Any]]]:
    """Every reading of a study: (its field, its address, its value object), lists followed."""
    found = []
    for field in contract.FIELDS:
        if field.kind != "reading" or not field.name.startswith("studies[]."):
            continue
        nodes = [(f"/studies/{i}", study)]
        for segment in field.name.split(".")[1:]:
            name = segment.removesuffix("[]")
            following = []
            for pointer, node in nodes:
                if not isinstance(node, dict) or name not in node:
                    continue
                value = node[name]
                if segment.endswith("[]"):
                    following += [
                        (f"{pointer}/{name}/{k}", item)
                        for k, item in enumerate(value if isinstance(value, list) else [])
                    ]
                else:
                    following.append((f"{pointer}/{name}", value))
            nodes = following
        for pointer, value in nodes:
            items = value if isinstance(value, list) else [value]
            for k, item in enumerate(items):
                if is_value_object(item):
                    found.append((field.name, pointer if item is value else f"{pointer}/{k}", item))
    return found


def biomarker_trace(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """Trace each biomarker mention, and every other reading, to what warrants it, by the kind of warrant its
    field rests on (WARRANT_KINDS):

    - quotation: the words a reading cites must occur, exactly, in the registry text at the paths its field
      reads (contract.FIELDS' `reads`). "Traced" means only that the cited words occur there, never that the
      clinical interpretation of them is right;
    - structural: a criterion's role rests on its heading, or on its own words where they overrule it (each
      in the criterion's text); results posted rests on the registry's hasResults flag;
    - derivation: a coordinate's known level is derived from typed readings (their cited words in the
      eligibility text; none, and it is unnarrowed), its interpolated level within its known level; an open
      question is derived from an unresolved reading it names (an intervention of the trial).

    Unresolved: a trial with no biomarker mention; a quotation reading that cites no words; a coordinate no
    typed reading narrows; a trial whose registry body was not given. Findings: each warrant that does not
    hold, and (with a workbook) a reading with no row in its destination. Evidence names its warrant kind and
    what holds it."""
    destination = (contract.BIOMARKERS, contract.READINGS)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    readings_listed = _addressed(run, contract.READINGS)
    biomarkers_listed = _addressed(run, contract.BIOMARKERS)
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        body = run.bodies.get(nct)
        readings = _readings(study, i)
        if not any(name == "studies[].biomarker_mentions" for name, _a, _v in readings):
            unresolved.append(
                Item(nct, f"/studies/{i}/biomarker_mentions", "no biomarker mention in the record")
            )
        if body is None:
            unresolved.append(Item(nct, f"/studies/{i}", "registry body not given: readings not traced"))
            continue
        for name, address, value in readings:
            kind = warrant_kind(name)
            code, detail = _warrant(kind, name, address, value, study, body)
            what = f"{kind}: {name}: {code}"
            if code in WARRANTED:
                evidence.append(Item(nct, address, what, detail))
            elif code in ("no_words", "unnarrowed"):
                unresolved.append(Item(nct, address, what, _words(value)))
            else:
                findings.append(Item(nct, address, FINDING_WORDS["unwarranted"], [kind, code, detail]))
            if run.sheets is not None:
                sheet = contract.BIOMARKERS if name == "studies[].biomarker_mentions" else contract.READINGS
                listed = biomarkers_listed if sheet == contract.BIOMARKERS else readings_listed
                if address not in listed and not any(str(a).startswith(address + "/") for a in listed):
                    findings.append(Item(nct, address, FINDING_WORDS["not_in_destination"], sheet))
    return TaskResult("trace a biomarker to its source words", destination, evidence, unresolved, findings)


# The kind of warrant each reading's field rests on; a field not named rests on quotation.
WARRANT_KINDS = {
    "studies[].criteria[].role": "structural",
    "studies[].results_posted": "structural",
    "studies[].open_questions": "derivation",
}
WARRANTED = ("traced", "heading", "own_words", "flag_agrees", "narrows", "derived")


def warrant_kind(field_name: str) -> str:
    """quotation, structural or derivation (a coordinate is derived from typed readings)."""
    if field_name.startswith("studies[].coordinates."):
        return "derivation"
    return WARRANT_KINDS.get(field_name, "quotation")


def role_warrant(heading: str, result: str, words: list[str], text: str) -> str:
    """A criterion's role against what warrants it (pure — pinned): heading (no words cited, the role is
    its heading's); own_words (its own cited words, each in the criterion's text, overrule the heading or
    leave it unresolved); untraced (a cited word not in the text); unwarranted (no words cited, yet the role
    is not its heading's)."""
    if words:
        return "own_words" if all(word.lower() in text.lower() for word in words) else "untraced"
    return "heading" if result == heading else "unwarranted"


def results_warrant(has_results: object, status: str) -> str:
    """Results posted against the registry's own flag (pure — pinned): flag_agrees (hasResults true and the
    reading known, or false and not posted); flag_disagrees; no_flag (the body holds no boolean flag)."""
    if not isinstance(has_results, bool):
        return "no_flag"
    return "flag_agrees" if (status == "known") == has_results else "flag_disagrees"


def narrowing_warrant(known: object, interpolated: object) -> str:
    """A coordinate's interpolated level against its known level (pure — pinned): narrows (every value the
    interpolated level leaves is one the known level leaves: a default relation only removes values);
    widens (it leaves a value the known level had removed); not_comparable (the levels are not lists of
    values, or not maps of genes to values)."""
    if isinstance(known, list) and isinstance(interpolated, list):
        return "narrows" if set(map(str, interpolated)) <= set(map(str, known)) else "widens"
    if isinstance(known, dict) and isinstance(interpolated, dict):
        return "narrows" if set(interpolated) <= set(known) else "widens"
    return "not_comparable"


def _warrant(kind: str, name: str, address: str, value: dict, study: dict, body: dict) -> tuple[str, Any]:
    """A reading's warrant checked by its kind: (its code, what holds it)."""
    words = [w for w in value.get("words") or [] if isinstance(w, str)]
    if kind == "quotation":
        texts = [
            t
            for path in contract.FIELD_NAMES[name].reads
            for t in _strings(contract.template_values(body, path))
        ]
        code, missing = words_traced(words, texts)
        return code, missing or words
    if name == "studies[].criteria[].role":
        place = address.rsplit("/", 2)[-2]
        criterion = (study.get("criteria") or [])[int(place)] if place.isdigit() else {}
        heading, text = criterion.get("heading"), criterion.get("text")
        code = role_warrant(str(heading), str(value.get("result")), words, str(text))
        return code, [heading, value.get("result"), words]
    if name == "studies[].results_posted":
        return results_warrant(body.get("hasResults"), str(value.get("status"))), body.get("hasResults")
    if name == "studies[].open_questions":
        element = (
            (value.get("result") or {}).get("element") if isinstance(value.get("result"), dict) else None
        )
        names = _strings(contract.template_values(body, f"{contract.AI}.interventions[].name"))
        return ("derived" if element in names else "underived"), element
    coordinate = name.removeprefix("studies[].coordinates.")
    base = coordinate.removesuffix("_interpolated").removesuffix("_proposed")
    if coordinate == base:
        if not words:
            return "unnarrowed", value.get("note")
        texts = _strings(contract.template_values(body, f"{contract.EL}.eligibilityCriteria"))
        code, missing = words_traced(words, texts)
        return ("derived" if code == "traced" else code), missing or words
    known = (study.get("coordinates") or {}).get(base)
    known_result = known.get("result") if is_value_object(known) else None
    return narrowing_warrant(known_result, value.get("result")), [known_result, value.get("result")]


def _strings(values: list[Any]) -> list[str]:
    return [value for value in values if isinstance(value, str)]


def address_answered(run: Run, ask: Callable[[str], tuple[str, Any]], bound: int = 200) -> TaskResult:
    """Ask the assistant's record tool about workbook rows by their addresses: each answer must be the
    record's value at the address. The rows asked are the workbook's listing rows (without a workbook, the
    record's listing nodes), at most `bound` of them, in order.

    `ask(address)` returns ("ok", the value) or (an error code, its detail)."""
    destination = ("the assistant's record tool",)
    evidence, unresolved, findings = [], [], []
    if run.sheets is not None:
        addresses = [
            a for name in preserve.LISTING_GRAINS for a in sorted(_addressed(run, name)) if isinstance(a, str)
        ]
    else:
        addresses = [
            p
            for grains in preserve.LISTING_GRAINS.values()
            for g in grains
            for p in preserve.grain_nodes(run.record, g)
        ]
        unresolved.append(
            Item("", "", "no workbook in the run folder: the record's listing nodes asked instead")
        )
    for address in addresses[:bound]:
        code, tokens = preserve.pointer_steps(address)
        found, node, _template, indices = (
            preserve.resolve_pointer(run.record, tokens) if code == "ok" else (False, None, "", [])
        )
        nct = str(run.record["studies"][indices[0]].get("nct")) if found and indices else ""
        if not found:
            continue
        verdict, answer = ask(address)
        if verdict != "ok":
            findings.append(Item(nct, address, FINDING_WORDS["not_answered"], [verdict, answer]))
        elif not same_value(answer, node):
            findings.append(Item(nct, address, FINDING_WORDS["answered_differently"], answer))
        else:
            evidence.append(Item(nct, address, "answered with the record's value"))
    return TaskResult(
        "ask the assistant about a workbook row by its address", destination, evidence, unresolved, findings
    )


def mcp_ask(root: Path, run_name: str) -> Callable[[str], tuple[str, Any]]:
    """The record tool of `trialledger mcp`, asked through its protocol answer function, as an `ask` for
    address_answered: part "address" with the pointer, every page read (a list's pages joined, an object's
    merged), up to PAGE_BOUND pages."""
    from TrialLedger import mcp_server

    context = mcp_server.Context(root=root)

    def ask(address: str) -> tuple[str, Any]:
        value: Any = None
        offset: Any = 0
        for page_number in range(PAGE_BOUND):
            arguments = {"run": run_name, "part": ADDRESS_PART, "address": address}
            if page_number:
                arguments["offset"] = offset
            call = {
                "jsonrpc": "2.0",
                "id": page_number + 1,
                "method": "tools/call",
                "params": {"name": "record", "arguments": arguments},
            }
            reply, _initialized = mcp_server.answer(context, json.dumps(call).encode("utf-8"), True)
            result = (reply or {}).get("result")
            if not isinstance(result, dict):
                return "protocol_error", reply
            document = json.loads(result["content"][0]["text"])
            if result.get("isError"):
                return "refused", document
            piece = document.get("value")
            if isinstance(piece, list) and isinstance(value, list):
                value = value + piece
            elif isinstance(piece, dict) and isinstance(value, dict):
                value = value | piece
            else:
                value = piece
            page = document.get("page")
            offset = page.get("next_offset") if isinstance(page, dict) else None
            if offset is None:
                return "ok", value
        return "too_many_pages", address

    return ask


TASKS = (eligibility_across, eligible_vs_enrolled, result_population, safety_in_period, biomarker_trace)


def review(run: Run, ask: Callable[[str], tuple[str, Any]] | None = None) -> list[TaskResult]:
    """Every reviewer's task over a run, the record tool's when an `ask` is given."""
    results = [task(run) for task in TASKS]
    if ask is not None:
        results.append(address_answered(run, ask))
    return results
