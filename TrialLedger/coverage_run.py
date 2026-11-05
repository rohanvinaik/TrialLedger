"""`landscape --compare-condition-text`: a run's MeSH condition-class search against condition text.

The run folder already holds the class search's complete identifier pages (`bodies/ids-*.json`, the pull
that wrote the record). This asks, in `coverage/` inside that folder, the SAME query with the condition class
replaced by `query.cond` (coverage.alternate_query: every other filter unchanged), identifiers only, through
the existing machinery: steps.follow_ids pages it, ingest.Session throttles, retries and counts every
registry request against the run's own acquisition budget, and every saved body is kept so a re-run resumes.
The comparison hydrates nothing; trials that differ are read once for their condition annotations only
(coverage.DIAGNOSIS_FIELDS) when the budget allows.

Outputs, all in the run folder: `coverage.json` (every query, retrieval time, completion state, source
bodies, the sets, routes, diagnosis and what may be said) and `coverage.md` (the same, readable), plus
`coverage/bodies/` (the alternate search's complete responses). landscape.json and landscape.xlsx are
never rewritten. An explicit union (class ∪ text) is only ever offered as a request for a NEW run
(`coverage_union_request.json`); nothing gathers it silently.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from TrialLedger import acquisition, coverage
from TrialLedger.ingest import (
    API_BASE,
    JSON_TYPE,
    PAGE_SIZE,
    TIMEOUT_SECONDS,
    USER_AGENT,
    PullError,
    Session,
    classify_json_page,
    classify_version,
    compare_snapshots,
)
from TrialLedger.request import QUERY_LIMIT
from TrialLedger.steps import (
    ACQUISITION_NAME,
    BODIES,
    END_NAME,
    START_NAME,
    STUDIES_URL,
    VERSION_URL,
    follow_ids,
    request_url,
)
from TrialLedger.steps import _state as run_state

COVERAGE_NAME = "coverage.json"
COVERAGE_TEXT = "coverage.md"
UNION_NAME = "coverage_union_request.json"
COVERAGE_DIR = "coverage"
RETRIEVED_NAME = "retrieved.json"  # within COVERAGE_DIR: when each saved body was fetched (UTC)
SCHEMA = "coverage-1"
TEXT_START, TEXT_END = "version-start.json", "version-end.json"
CLASS_TIME_BASIS = (
    "modification time of the saved page file (the class search ran in the run's own pull); "
    "it changes if the folder is copied"
)
TEXT_TIME_BASIS = "clock time when this program saved the response"


def _json(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _write(path: Path, data: bytes) -> None:
    staging = path.with_name(f".{path.name}.partial")
    staging.write_bytes(data)
    os.replace(staging, path)


def _read_bodies(folder: Path) -> tuple[dict[str, Any], list[str]]:
    bodies: dict[str, Any] = {}
    unreadable: list[str] = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.name.startswith("."):
                continue
            try:
                bodies[path.name] = json.loads(path.read_bytes().decode("utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
                unreadable.append(path.name)
    return bodies, unreadable


def _snapshot(version: Any) -> dict[str, str] | None:
    if isinstance(version, dict) and classify_version(version) == "ok":
        return {"api_version": version["apiVersion"], "data_timestamp": version["dataTimestamp"]}
    return None


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat(timespec="seconds")


def class_side(folder: Path, query: dict[str, str]) -> dict[str, Any]:
    """The class search as the run's own retained pages hold it: complete only when follow_ids says so."""
    _scope, _named, bodies, unreadable = run_state(folder)
    code, pages, ids, detail = follow_ids(query, bodies, unreadable)
    files = [folder / BODIES / page["file"] for page in pages if page["file"] in bodies]
    side: dict[str, Any] = {
        "query": query,
        "state": "complete" if code == "complete" else "incomplete",
        "retrieval_code": code,
        "detail": detail,
        "total": bodies["ids-001.json"].get("totalCount") if "ids-001.json" in bodies else None,
        "ids": ids if code == "complete" else [],
        "sources": [f"{BODIES}/{path.name}" for path in files],
        "retrieved_at": sorted({_iso(path.stat().st_mtime) for path in files}),
        "retrieved_at_basis": CLASS_TIME_BASIS,
        "snapshot": _snapshot(bodies.get(START_NAME)),
        "snapshot_end": _snapshot(bodies.get(END_NAME)),
    }
    return side


def text_side_state(
    base: Path, query: dict[str, str], failure: str = ""
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The text search as its saved bodies hold it, and the retrieval times kept beside them."""
    bodies, unreadable = _read_bodies(base / BODIES)
    code, pages, ids, detail = follow_ids(query, bodies, unreadable)
    stamps = json.loads((base / RETRIEVED_NAME).read_text()) if (base / RETRIEVED_NAME).is_file() else {}
    saved = [page["file"] for page in pages if page["file"] in bodies]
    first = bodies.get("ids-001.json")
    state = "complete" if code == "complete" else ("failed" if failure else "incomplete")
    side = {
        "query": query,
        "state": state,
        "retrieval_code": code,
        "detail": failure or detail,
        "total": first.get("totalCount") if isinstance(first, dict) and "totalCount" in first else None,
        "ids": ids if code == "complete" else [],
        "sources": [f"{COVERAGE_DIR}/{BODIES}/{name}" for name in saved],
        "retrieved_at": sorted({stamps[name] for name in saved if name in stamps}),
        "retrieved_at_basis": TEXT_TIME_BASIS,
        "snapshot": _snapshot(bodies.get(TEXT_START)),
        "snapshot_end": _snapshot(bodies.get(TEXT_END)),
    }
    return side, bodies


def same_snapshot(class_side_: dict[str, Any], text_side_: dict[str, Any]) -> bool | None:
    """Whether the registry data was one snapshot across both searches (None when any end is unread)."""
    held = [class_side_.get("snapshot"), class_side_.get("snapshot_end"), text_side_.get("snapshot")]
    held.append(text_side_.get("snapshot_end"))
    if any(snapshot is None for snapshot in held):
        return None
    first = held[0]
    return all(compare_snapshots(tuple(first.values()), tuple(s.values())) == "same" for s in held[1:])


def spent_requests(folder: Path) -> int:
    """Registry requests the run has already made (its acquisition checkpoint, else its saved bodies)."""
    checkpoint = folder / ACQUISITION_NAME
    if checkpoint.is_file():
        count = json.loads(checkpoint.read_text()).get("registry_requests")
        if type(count) is int and count >= 0:
            return count
    _scope, _named, bodies, unreadable = run_state(folder)
    return sum(
        name in (START_NAME, END_NAME) or name.startswith(("ids-", "studies-"))
        for name in (*bodies, *unreadable)
    )


def _fetch(session: Session, url: str, params: dict[str, str], base: Path, name: str) -> None:
    """One response, saved whole and stamped with its retrieval time."""
    content = session.get(url, params, JSON_TYPE).content
    (base / BODIES).mkdir(parents=True, exist_ok=True)
    _write(base / BODIES / name, content)
    path = base / RETRIEVED_NAME
    stamps = json.loads(path.read_text()) if path.is_file() else {}
    stamps[name] = datetime.now(UTC).isoformat(timespec="seconds")
    _write(path, _json(stamps))


def diagnosis_batches(ids: list[str]) -> list[list[str]]:
    return [
        ids[start : start + coverage.DIAGNOSIS_BATCH]
        for start in range(0, len(ids), coverage.DIAGNOSIS_BATCH)
    ]


def diagnose(
    session: Session, base: Path, ids: list[str], term: str, route_of: dict[str, list[str]]
) -> dict[str, Any]:
    """Read the differing trials' condition annotations (identifiers asked, exactly those answered)."""
    readings: dict[str, Any] = {}
    for number, batch in enumerate(diagnosis_batches(ids), 1):
        name = f"diagnosis-{number:03d}.json"
        path = base / BODIES / name
        if not path.is_file():
            params = {
                "filter.ids": ",".join(batch),
                "format": "json",
                "markupFormat": "markdown",
                "countTotal": "true",
                "pageSize": str(PAGE_SIZE),
                "fields": coverage.DIAGNOSIS_FIELDS,
            }
            _fetch(session, STUDIES_URL, params, base, name)
        payload = json.loads(path.read_bytes().decode("utf-8"))
        if classify_json_page(payload, True) not in ("next", "last"):
            return {"state": "incomplete", "detail": f"{name}: not a registry page", "trials": readings}
        got = [study["protocolSection"]["identificationModule"]["nctId"] for study in payload["studies"]]
        if sorted(got) != sorted(batch):
            return {
                "state": "incomplete",
                "detail": f"{name}: not exactly the trials asked",
                "trials": readings,
            }
        for study in payload["studies"]:
            reading = coverage.annotation_reading(study, term)
            reading["route"] = route_of[reading["nct_id"]]
            readings[reading["nct_id"]] = reading
    return {"state": "complete", "detail": "", "trials": readings}


def union_request(ids: list[str]) -> tuple[str, dict[str, Any] | None]:
    """The explicit union as a request for a NEW run by identifier, or why it cannot be one request."""
    query = {"filter.ids": ",".join(ids)}
    if len(urlencode(query, quote_via=quote)) > QUERY_LIMIT:
        return "union_ids_too_long_for_one_request", None
    return "ok", {"params": query}


def run_coverage(
    folder: Path,
    *,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] = lambda _m: None,
) -> tuple[str, str]:
    """Compare the run's class search with its condition-text search; returns (state, detail).

    The state is coverage.COMPARISON_STATES. Every outcome writes coverage.json and coverage.md; a stop
    (budget, failed request) keeps every saved body so the same command resumes.
    """
    request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
    resolution = json.loads((folder / "resolution.json").read_text(encoding="utf-8"))
    code, alternate = coverage.alternate_query(resolution)
    if code != "ok":
        document = {"schema": SCHEMA, "state": "not_applicable", "reason": code}
        document["difference_words"] = coverage.difference_words("not_applicable", None)
        _write(folder / COVERAGE_NAME, _json(document))
        _write(folder / COVERAGE_TEXT, render(document).encode("utf-8"))
        return "not_applicable", code
    query = resolution["query"]
    scope_file = json.loads((folder / "scope.json").read_text(encoding="utf-8"))
    policy = scope_file.get("acquisition") or acquisition.effective_policy()
    base = folder / COVERAGE_DIR
    spent = spent_requests(folder)
    klass = class_side(folder, query)
    client = http or httpx.Client(
        base_url=API_BASE, timeout=TIMEOUT_SECONDS, follow_redirects=False, headers={"User-Agent": USER_AGENT}
    )
    session = Session(
        client,
        sleep=sleep,
        monotonic=monotonic,
        progress=progress,
        acquisition=policy,
        registry_requests=spent,
    )
    failure = ""
    diagnosis: dict[str, Any] = {"state": "not_run", "detail": "no differing trial to read", "trials": {}}
    try:
        first = coverage.comparison_budget(policy, klass["total"], None, spent)
        if klass["state"] != "complete":
            pass  # nothing to compare with: the alternate search is not asked
        elif first["verdict"] != "within_budget":
            failure = f"acquisition_{first['verdict']}: the comparison's first requests exceed the budget"
        else:
            try:
                failure = _retrieve_text(session, base, alternate, policy, spent, klass, progress)
            except PullError as error:
                failure = f"{error.code}: {error.detail}"
        text, _bodies = text_side_state(base, alternate, failure)
        if klass["state"] != "complete":
            text["state"], text["detail"] = "not_run", "not asked: the class search itself is not complete"
        state = coverage.comparison_state(klass, text, same_snapshot(klass, text))
        comparison = coverage.compare_id_sets(klass["ids"], text["ids"]) if state == "complete" else None
        routes = coverage.routes(klass["ids"], text["ids"]) if state == "complete" else {}
        differing = [*comparison["text_only"], *comparison["class_only"]] if comparison else []
        budget = coverage.comparison_budget(
            policy, klass["total"], text["total"], spent, diagnosed=len(differing)
        )
        if differing and budget["verdict"] == "within_budget":
            try:
                diagnosis = diagnose(session, base, differing, request["condition_class"], routes)
            except PullError as error:
                diagnosis = {"state": "failed", "detail": f"{error.code}: {error.detail}", "trials": {}}
        elif differing:
            diagnosis = {"state": "not_run", "detail": f"budget: {budget['verdict']}", "trials": {}}
    finally:
        if http is None:
            client.close()
    budget["requests_this_invocation"] = session.registry_requests - spent
    budget["saved_responses"] = len([p for p in (base / BODIES).glob("*") if not p.name.startswith(".")])
    union: dict[str, Any] = {"policy": "explicit_expansion_offered_not_gathered", "offered": False}
    if comparison is not None:
        merged = sorted({*klass["ids"], *text["ids"]})
        union_code, union_body = (
            union_request(merged)
            if len(merged) <= policy["max_studies"]
            else ("acquisition_study_expansion", None)
        )
        union |= {"offered": union_body is not None, "code": union_code, "unique_trials": len(merged)}
        union["words"] = (
            "An expanded search (class OR condition text) is offered only as an explicit choice: gather it "
            "in "
            f"a NEW run from {UNION_NAME}. Each trial's retrieval route is in `routes`; a trial reached only "
            "by the text search is a candidate for clinical review, not established disease membership."
        )
        if union_body is not None:
            _write(folder / UNION_NAME, _json(union_body))
    document = {
        "schema": SCHEMA,
        "state": state,
        "clinical_term": request["condition_class"],
        "boundary": coverage.BOUNDARY,
        "class_search": klass | {"unique_ids": len(set(klass["ids"]))},
        "text_search": text | {"unique_ids": len(set(text["ids"]))},
        "other_filters_unchanged": coverage.unchanged_filters(query, alternate),
        "comparison": comparison,
        "difference_words": coverage.difference_words(state, comparison),
        "routes": routes,
        "diagnosis": diagnosis,
        "budget": budget,
        "union": union,
        "request_urls": {
            "class": request_url(STUDIES_URL, {**query, "format": "json", "fields": "NCTId"}),
            "text": request_url(STUDIES_URL, {**alternate, "format": "json", "fields": "NCTId"}),
        },
        "sources_note": "class_search sources are the run's own bodies/; text_search sources are "
        "coverage/bodies/.",
    }
    _write(folder / COVERAGE_NAME, _json(document))
    _write(folder / COVERAGE_TEXT, render(document).encode("utf-8"))
    return state, document["difference_words"]


def _retrieve_text(
    session: Session,
    base: Path,
    alternate: dict[str, str],
    policy: dict[str, int],
    spent: int,
    klass: dict[str, Any],
    progress: Callable[[str], None],
) -> str:
    """Fetch what the alternate search still needs: /version, its identifier pages, /version again.

    The budget is decided on observed scope after the first page (study total) and before every further
    page; a stop raises PullError('acquisition.…') and keeps what is saved. Returns "" when nothing failed.
    """
    while True:
        bodies, unreadable = _read_bodies(base / BODIES)
        if TEXT_START not in bodies:
            _fetch(session, VERSION_URL, {}, base, TEXT_START)
            continue
        code, pages, _ids, _detail = follow_ids(alternate, bodies, unreadable)
        if code == "awaiting_fetch":
            page = pages[-1]
            _fetch(session, page["url"], page["params"], base, page["file"])
            progress(f"saved {page['file']} (alternate id page)")
            if page["file"] == "ids-001.json":
                first = json.loads((base / BODIES / "ids-001.json").read_bytes().decode("utf-8"))
                if classify_json_page(first, True) in ("next", "last"):
                    plan = coverage.comparison_budget(policy, klass["total"], first["totalCount"], spent)
                    if plan["verdict"] != "within_budget":
                        raise PullError(
                            "acquisition." + plan["verdict"],
                            acquisition.refusal_detail(
                                policy, plan["unique_studies"], spent, plan["planned_requests"]
                            ),
                        )
            continue
        if code == "complete" and TEXT_END not in bodies:
            _fetch(session, VERSION_URL, {}, base, TEXT_END)
            continue
        return "" if code == "complete" else f"{code}: {_detail}"


def render(document: dict[str, Any]) -> str:
    """coverage.json as readable text (pure): the state and what may be said first, then the facts."""
    lines = ["# Search coverage: condition class (MeSH) versus condition text", ""]
    lines += [f"State: {document['state']}", document["difference_words"], ""]
    if document["state"] == "not_applicable":
        lines.append(f"Reason: {document.get('reason')}")
        return "\n".join(lines) + "\n"
    lines += [document["boundary"], ""]
    for key, title in (("class_search", "Class search (MeSH)"), ("text_search", "Condition-text search")):
        side = document[key]
        lines += [f"## {title}", f"- state: {side['state']} ({side['detail'] or 'no detail'})"]
        lines += [f"- query: {json.dumps(side['query'], ensure_ascii=False)}"]
        lines += [f"- registry total: {side['total']}; unique identifiers read: {side['unique_ids']}"]
        lines += [
            f"- retrieved: {', '.join(side['retrieved_at']) or 'not stated'} ({side['retrieved_at_basis']})"
        ]
        lines += [
            f"- registry data snapshot: {side['snapshot']}; sources: {len(side['sources'])} saved page(s)",
            "",
        ]
    lines.append(f"Every other filter unchanged: {document['other_filters_unchanged']}")
    comparison = document["comparison"]
    if comparison:
        lines += [
            "",
            f"In both: {len(comparison['intersection'])}; class only: {len(comparison['class_only'])}; "
            f"text only: {len(comparison['text_only'])}",
        ]
        for label, key in (("Class only", "class_only"), ("Text only", "text_only")):
            lines.append(f"- {label}: {', '.join(comparison[key]) or 'none'}")
        for nct_id, reading in document["diagnosis"]["trials"].items():
            lines.append(
                f"  - {nct_id} [{'+'.join(reading['route'])}] condition MeSH annotation: "
                f"{reading['annotation']}; "
                f"conditions: {'; '.join(reading['conditions']) or 'none stated'}"
            )
    lines += [
        "",
        f"Diagnosis of differing records: {document['diagnosis']['state']} {document['diagnosis']['detail']}",
    ]
    budget = document["budget"]
    lines += [
        f"Acquisition budget: {budget['planned_requests']} of {budget['max_registry_requests']} registry "
        f"requests, {budget['unique_studies']} of {budget['max_studies']} unique studies: "
        f"{budget['verdict']}",
        "",
        document["union"].get("words", "No union is offered."),
    ]
    return "\n".join(lines) + "\n"
