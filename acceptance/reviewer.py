"""Independent checks of registry reporting tasks over record, workbook and MCP data.

Four tasks preserve the evidence boundaries: exact eligibility source sections; registered population,
enrollment and baseline denominators kept separate; posted-result populations and scoped denominators;
and adverse-event periods with group-specific counts. Workbook row addresses are checked against the
record tool. These checks do not supply clinical interpretations, recommendations or an inferred population.
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
# The title the registry gives the baseline's group of all participants.
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


def _safety_listed(run: Run, nct: str, base: str, events: dict[str, Any]) -> list[Item]:
    """Check every source count row and each event-level safety placeholder against its workbook row."""
    if run.sheets is None:
        return []
    rows = _rows(run, contract.SAFETY)
    expected: list[tuple[str, str | None]] = []
    groups = events.get("groups") or []
    for event_index, event in enumerate(events.get("events") or []):
        address = f"{base}/events/{event_index}"
        counts = event.get("counts") or []
        expected.extend(
            (f"{address}/counts/{count_index}", None) for count_index, _count in enumerate(counts)
        )
        count_ids = [count.get("group") if isinstance(count, dict) else None for count in counts]
        missing_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_id = group.get("id")
            if group_id in count_ids or group_id in missing_groups:
                continue
            missing_groups.append(group_id)
            expected.append((address, "Not stated" if group_id is None else str(group_id)))
        if not groups and not counts:
            expected.append((address, "Not stated"))
    missing = []
    for address, group_id in expected:
        if any(
            row.get(contract.ADDRESS) == address and (group_id is None or row.get("Group ID") == group_id)
            for row in rows
        ):
            continue
        missing.append(Item(nct, address, FINDING_WORDS["not_in_destination"], contract.SAFETY))
    return missing


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
    """Compare exact source eligibility sections, without assigning a clinical role or reading."""
    destination = (contract.ELIGIBILITY,)
    evidence, unresolved, findings = [], _no_workbook(run, destination), []
    for i, study in _studies(run, ncts):
        nct = str(study.get("nct"))
        criteria = study.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            unresolved.append(Item(nct, f"/studies/{i}/criteria", "no eligibility sections stated"))
            continue
        original = (
            run.bodies.get(nct, {})
            .get("protocolSection", {})
            .get("eligibilityModule", {})
            .get("eligibilityCriteria")
        )
        addresses = []
        source_end = 0
        for j, section in enumerate(criteria):
            address = f"/studies/{i}/criteria/{j}"
            addresses.append(address)
            if not isinstance(section, dict):
                findings.append(Item(nct, address, "eligibility section is not an object"))
                continue
            start, end, text = section.get("source_start"), section.get("source_end"), section.get("text")
            evidence.append(
                Item(nct, address, "source eligibility section", [section.get("heading"), text, start, end])
            )
            if original is None:
                unresolved.append(Item(nct, address, "registry body not given: source section not checked"))
            elif not (
                type(start) is int
                and type(end) is int
                and 0 <= start <= end <= len(original)
                and original[start:end] == text
            ):
                findings.append(
                    Item(nct, address, "eligibility section differs from its exact source span", text)
                )
            if isinstance(original, str):
                if start != source_end:
                    findings.append(Item(nct, address, "source eligibility passages are not contiguous"))
                if type(end) is int:
                    source_end = end
        if isinstance(original, str) and source_end != len(original):
            findings.append(
                Item(
                    nct,
                    f"/studies/{i}/criteria",
                    "source eligibility passages do not cover the original text",
                )
            )
        findings += _listed(run, contract.ELIGIBILITY, nct, addresses)
    return TaskResult(
        "compare source eligibility across selected trials", destination, evidence, unresolved, findings
    )


def eligible_vs_enrolled(run: Run, ncts: list[str] | None = None) -> TaskResult:
    """Keep the registered eligible population, enrollment and baseline populations separate.

    Every denominator retains its stated group and scope. No group counts are summed to infer a unique
    enrolled or analysed population; overlapping groups cannot establish such a total."""
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
                isinstance(row.get("Value"), (str, int))
                and (
                    shows_text(str(row.get("Value")), str(count))
                    or (type(count) is int and shows_text(str(row.get("Value")), f"{count:,}"))
                )
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
        for d, denominator in enumerate(baseline.get("denominators") or []):
            for c, entry in enumerate(denominator.get("counts") or []):
                address = f"/studies/{i}/baseline/denominators/{d}/counts/{c}"
                evidence.append(
                    Item(
                        nct,
                        address,
                        f"baseline denominator, {entry.get('group')}",
                        [entry.get("value"), denominator.get("units")],
                    )
                )
        for m, measure in enumerate(baseline.get("measures") or []):
            measure_base = f"/studies/{i}/baseline/measures/{m}"
            if _plain(measure.get("population")):
                evidence.append(
                    Item(
                        nct,
                        f"{measure_base}/population",
                        "baseline measure population",
                        measure["population"],
                    )
                )
            holders = [("measure", measure, measure_base)]
            holders += [
                ("class", klass, f"{measure_base}/classes/{c}")
                for c, klass in enumerate(measure.get("classes") or [])
            ]
            for scope, holder, location in holders:
                for d, denominator in enumerate(holder.get("denominators") or []):
                    for count_index, count_entry in enumerate(denominator.get("counts") or []):
                        evidence.append(
                            Item(
                                nct,
                                f"{location}/denominators/{d}/counts/{count_index}",
                                f"baseline {scope} denominator, {count_entry.get('group')}",
                                [count_entry.get("value"), denominator.get("units")],
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
                        for scope, holder, location in (
                            ("measure", measure, base),
                            ("class", klass, f"{base}/classes/{c}"),
                        ):
                            for d, stated in enumerate(holder.get("denominators") or []):
                                for count_index, count_entry in enumerate(stated.get("counts") or []):
                                    if count_entry.get("group") == group:
                                        evidence.append(
                                            Item(
                                                nct,
                                                f"{location}/denominators/{d}/counts/{count_index}",
                                                f"{scope} denominator, {group}",
                                                [count_entry.get("value"), stated.get("units")],
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
                    str(group.get("title") or "Unresolved — group title not stated"),
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
        for e, event in enumerate(events.get("events") or []):
            address = f"{base}/events/{e}"
            counts = event.get("counts") or []
            for c, held in enumerate(counts):
                count_address = f"{address}/counts/{c}"
                count = held if isinstance(held, dict) else {}
                group_id = count.get("group")
                matches = [
                    group for group in groups if isinstance(group, dict) and group.get("id") == group_id
                ]
                title = (
                    str(matches[0].get("title") or "Unresolved — group title not stated")
                    if len(matches) == 1
                    else "Unresolved — no unique adverse-event source group is available"
                )
                what = f"{title}: {event.get('term') or 'Unresolved — event term not stated'}"
                evidence.append(
                    Item(
                        nct,
                        count_address,
                        what,
                        [count.get("affected"), count.get("at_risk"), count.get("events")],
                    )
                )
                for stat in ("affected", "at_risk", "events"):
                    if not isinstance(count.get(stat), int):
                        unresolved.append(
                            Item(nct, count_address, f"{what} — {stat}: {preserve.NOT_REPORTED}")
                        )
                findings += _exceeds(nct, count_address, count.get("affected"), count.get("at_risk"))
            count_ids = [count.get("group") if isinstance(count, dict) else None for count in counts]
            missing_group_ids = []
            for group in groups:
                if not isinstance(group, dict):
                    continue
                group_id = group.get("id")
                if group_id in count_ids or group_id in missing_group_ids:
                    continue
                missing_group_ids.append(group_id)
                title = str(group.get("title") or "Unresolved — group title not stated")
                for stat in ("affected", "at_risk", "events"):
                    unresolved.append(Item(nct, address, f"{title} — {stat}: {preserve.NOT_REPORTED}"))
        findings += _safety_listed(run, nct, base, events)
        findings += _listed(run, contract.GROUPS, nct, [f"{base}/groups/{g}" for g in range(len(groups))])
    return TaskResult("read safety within its reporting period", destination, evidence, unresolved, findings)


def _exceeds(nct: str, address: str, affected: Any, at_risk: Any) -> list[Item]:
    if isinstance(affected, int) and isinstance(at_risk, int) and affected > at_risk:
        return [Item(nct, address, FINDING_WORDS["affected_exceeds_at_risk"], [affected, at_risk])]
    return []


# The kind of warrant each reading's field rests on; a field not named rests on quotation.


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


TASKS = (eligibility_across, eligible_vs_enrolled, result_population, safety_in_period)


def review(run: Run, ask: Callable[[str], tuple[str, Any]] | None = None) -> list[TaskResult]:
    """Every reviewer's task over a run, the record tool's when an `ask` is given."""
    results = [task(run) for task in TASKS]
    if ask is not None:
        results.append(address_answered(run, ask))
    return results
