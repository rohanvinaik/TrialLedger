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
ACCOUNTING_CODES = ("acquisition.invalid_cost", "acquisition.unverifiable_cost")
CLASS_TIME_BASIS = (
    "modification time of the saved page file (the class search ran in the run's own pull); "
    "it changes if the folder is copied"
)
TEXT_TIME_BASIS = (
    "clock time when this program saved the response; in relay mode the saved file's modification time"
)


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
    stamps, stamp_state = _retrieval_stamps(base)
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
        "retrieved_at": sorted(
            {stamps.get(name) or _iso((base / BODIES / name).stat().st_mtime) for name in saved}
        ),
        "retrieved_at_basis": TEXT_TIME_BASIS,
        "retrieval_metadata_state": stamp_state,
        "snapshot": _snapshot(bodies.get(TEXT_START)),
        "snapshot_end": _snapshot(bodies.get(TEXT_END)),
    }
    return side, bodies


def _retrieval_stamps(base: Path) -> tuple[dict[str, str], str]:
    """Read timestamp metadata independently of the retained response bodies it describes."""
    path = base / RETRIEVED_NAME
    if not path.is_file():
        return {}, "missing"
    try:
        document = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, "malformed"
    if not isinstance(document, dict) or any(not isinstance(value, str) for value in document.values()):
        return {}, "malformed"
    return document, "present"


def same_snapshot(class_side_: dict[str, Any], text_side_: dict[str, Any]) -> bool | None:
    """Whether the registry data was one snapshot across both searches (None when any end is unread)."""
    held = [class_side_.get("snapshot"), class_side_.get("snapshot_end"), text_side_.get("snapshot")]
    held.append(text_side_.get("snapshot_end"))
    known = [snapshot for snapshot in held if isinstance(snapshot, dict)]
    if len(known) != len(held):
        return None
    first = known[0]
    return all(compare_snapshots(tuple(first.values()), tuple(s.values())) == "same" for s in known[1:])


def spent_requests(folder: Path) -> int:
    """All recorded attempts, with retained main and coverage responses as a lower bound.

    The checkpoint's response identities say which successes its attempt count already includes. Newly
    retained relay responses add to that count; failures are never replaced by a response-count maximum.
    Relay attempts without a saved response cannot be measured here.
    """
    checkpoint = folder / ACQUISITION_NAME
    count = 0
    document: dict[str, Any] = {}
    if checkpoint.is_file():
        try:
            document = json.loads(checkpoint.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PullError("acquisition.invalid_cost", "Unreadable acquisition checkpoint JSON") from error
        if not isinstance(document, dict):
            raise PullError("acquisition.invalid_cost", "Acquisition checkpoint must be an object")
        count = document.get("registry_requests")
        if type(count) is not int or count < 0:
            raise PullError("acquisition.invalid_cost", "Malformed recorded registry request count")
    paths = _response_paths(folder)
    if not document:
        return len(paths)
    accounted = document.get("accounted_response_paths")
    if "accounted_response_paths" not in document:
        accounted = _legacy_accounted_paths(folder, paths)
        count = max(count, len(accounted))
    elif (
        not isinstance(accounted, list)
        or any(not isinstance(path, str) for path in accounted)
        or len(set(accounted)) != len(accounted)
        or count < len(accounted)
    ):
        raise PullError("acquisition.invalid_cost", "Malformed accounted registry response identities")
    return coverage.cumulative_request_count(count, paths, accounted)


def _response_paths(folder: Path) -> list[str]:
    """Stable local identities for retained registry responses in this run and comparison."""
    _scope, _named, bodies, unreadable = run_state(folder)
    main = [
        f"{BODIES}/{name}"
        for name in (*bodies, *unreadable)
        if name in (START_NAME, END_NAME) or name.startswith(("ids-", "studies-"))
    ]
    return sorted([*main, *(f"{COVERAGE_DIR}/{BODIES}/{n}" for n in _response_names(folder / COVERAGE_DIR))])


def _legacy_accounted_paths(folder: Path, paths: list[str]) -> list[str]:
    """Migrate old direct-only counts; an unanchored mixed history cannot establish a total."""
    stamps, stamp_state = _retrieval_stamps(folder / COVERAGE_DIR)
    if stamp_state == "malformed":
        raise PullError("acquisition.invalid_cost", "Malformed legacy registry retrieval timestamps")
    unknown = [
        path for path in paths if path.startswith(f"{COVERAGE_DIR}/") and Path(path).name not in stamps
    ]
    if unknown:
        raise PullError(
            "acquisition.unverifiable_cost",
            "Older acquisition checkpoint does not identify which relay responses its attempt count "
            "already includes; request accounting must be resolved before further acquisition. "
            "Retained search evidence is unchanged.",
        )
    return paths


def _response_names(base: Path) -> list[str]:
    """Saved coverage response names, not derived metadata or partially written bodies."""
    return [
        path.name
        for path in (base / BODIES).glob("*.json")
        if path.is_file()
        and (path.name in (TEXT_START, TEXT_END) or path.name.startswith(("ids-", "diagnosis-")))
    ]


def _retained_requests(base: Path, diagnosed: int = 0) -> int:
    """Responses reused by this plan; unrelated saved diagnosis batches do not reduce identifier work."""
    names = _response_names(base)
    text = sum(name in (TEXT_START, TEXT_END) or name.startswith("ids-") for name in names)
    diagnosis = sum(
        f"diagnosis-{number:03d}.json" in names
        for number in range(1, -(-diagnosed // coverage.DIAGNOSIS_BATCH) + 1)
    )
    return text + diagnosis


def _record_attempt(folder: Path, count: int) -> None:
    """Persist the attempt before Session sends it, preserving the main acquisition checkpoint."""
    path = folder / ACQUISITION_NAME
    document = json.loads(path.read_text()) if path.is_file() else {}
    document.update(
        registry_requests=count,
        accounted_response_paths=_response_paths(folder),
        request_count_basis="direct attempts plus retained relay response lower bound",
    )
    _write(path, _json(document))


def _budget(folder: Path, policy: dict, klass: dict, total: int | None, diagnosed: int = 0) -> dict:
    return coverage.comparison_budget(
        policy,
        klass["total"],
        total,
        spent_requests(folder),
        diagnosed=diagnosed,
        retained_requests=_retained_requests(folder / COVERAGE_DIR, diagnosed),
    )


def comparison_plan(folder: Path) -> dict[str, Any]:
    """Preview execution's remaining-work budget from retained evidence, without requests or writes.

    Saved totals determine paging cost. Only a complete, same-snapshot comparison identifies differing
    trials whose annotation batches can be reserved; before then their cost remains unknown.
    """
    resolution = json.loads((folder / "resolution.json").read_text(encoding="utf-8"))
    scope = json.loads((folder / "scope.json").read_text(encoding="utf-8"))
    policy = scope.get("acquisition") or acquisition.effective_policy()
    klass = class_side(folder, resolution["query"])
    _code, alternate = coverage.alternate_query(resolution)
    text, _bodies = text_side_state(folder / COVERAGE_DIR, alternate)
    state = coverage.comparison_state(klass, text, same_snapshot(klass, text))
    differing = 0
    if state == "complete":
        comparison = coverage.compare_id_sets(klass["ids"], text["ids"])
        differing = len(comparison["text_only"]) + len(comparison["class_only"])
    try:
        return _budget(folder, policy, klass, text["total"], differing)
    except PullError as error:
        if error.code not in ACCOUNTING_CODES:
            raise
        return _unverifiable_plan(policy, error.code)


def _unverifiable_plan(policy: dict[str, int], code: str = "acquisition.unverifiable_cost") -> dict[str, Any]:
    """Unknown historical accounting has no computable total or admissible acquisition reservation."""
    return {
        "added_requests": None,
        "retained_requests": None,
        "remaining_requests": None,
        "spent_requests": None,
        "planned_requests": None,
        "unique_studies": None,
        "max_studies": policy["max_studies"],
        "max_registry_requests": policy["max_registry_requests"],
        "verdict": code,
    }


def _accounting_failure(
    folder: Path, policy: dict[str, int], klass: dict[str, Any], alternate: dict[str, str], error: PullError
) -> tuple[str, str]:
    """Keep independently retained searches while exposing an accounting task, without requesting more."""
    text, _bodies = text_side_state(folder / COVERAGE_DIR, alternate)
    words = f"{error.code}: {error.detail} {coverage.difference_words('incomplete', None)}"
    document = {
        "schema": SCHEMA,
        "state": "incomplete",
        "reason": error.code,
        "difference_words": words,
        "boundary": coverage.BOUNDARY,
        "class_search": klass | {"unique_ids": len(set(klass["ids"]))},
        "text_search": text | {"unique_ids": len(set(text["ids"]))},
        "other_filters_unchanged": coverage.unchanged_filters(klass["query"], alternate),
        "comparison": None,
        "routes": {},
        "diagnosis": {"state": "not_run", "detail": error.code, "trials": {}},
        "budget": _unverifiable_plan(policy, error.code),
        "union": {"offered": False},
    }
    _write(folder / COVERAGE_NAME, _json(document))
    _write(folder / COVERAGE_TEXT, render(document).encode("utf-8"))
    return "incomplete", words


class Awaiting(Exception):
    """Relay mode: these exact registry requests must be fetched and saved (save_fetch) before going on."""

    def __init__(self, fetches: list[dict[str, str]]) -> None:
        super().__init__(f"{len(fetches)} fetch(es) awaited")
        self.fetches = fetches


def relay_fetch(url: str, params: dict[str, str], name: str, why: str) -> dict[str, str]:
    """One awaited request as the relay protocol names it: the full URL, where to save the body, why."""
    return {"url": request_url(url, params), "save_as": f"{COVERAGE_DIR}/{BODIES}/{name}", "why": why}


def _fetch(
    session: Session | None, url: str, params: dict[str, str], base: Path, name: str, why: str = "coverage"
) -> None:
    """One response, saved whole and stamped with its retrieval time (relay: named, never fetched here)."""
    if session is None:
        raise Awaiting([relay_fetch(url, params, name, why)])
    content = session.get(url, params, JSON_TYPE).content
    (base / BODIES).mkdir(parents=True, exist_ok=True)
    _write(base / BODIES / name, content)
    path = base / RETRIEVED_NAME
    stamps = json.loads(path.read_text()) if path.is_file() else {}
    stamps[name] = datetime.now(UTC).isoformat(timespec="seconds")
    _write(path, _json(stamps))
    _record_attempt(base.parent, session.registry_requests)


def diagnosis_batches(ids: list[str]) -> list[list[str]]:
    return [
        ids[start : start + coverage.DIAGNOSIS_BATCH]
        for start in range(0, len(ids), coverage.DIAGNOSIS_BATCH)
    ]


def diagnosis_params(batch: list[str]) -> dict[str, str]:
    """The request that reads exactly these trials' condition annotations."""
    return {
        "filter.ids": ",".join(batch),
        "format": "json",
        "markupFormat": "markdown",
        "countTotal": "true",
        "pageSize": str(PAGE_SIZE),
        "fields": coverage.DIAGNOSIS_FIELDS,
    }


def diagnose(
    session: Session | None, base: Path, ids: list[str], term: str, route_of: dict[str, list[str]]
) -> dict[str, Any]:
    """Read the differing trials' condition annotations (identifiers asked, exactly those answered)."""
    readings: dict[str, Any] = {}
    if session is None:  # relay: every missing batch is named at once
        missing = [
            relay_fetch(
                STUDIES_URL, diagnosis_params(batch), f"diagnosis-{number:03d}.json", "coverage_annotations"
            )
            for number, batch in enumerate(diagnosis_batches(ids), 1)
            if not (base / BODIES / f"diagnosis-{number:03d}.json").is_file()
        ]
        if missing:
            raise Awaiting(missing)
    for number, batch in enumerate(diagnosis_batches(ids), 1):
        name = f"diagnosis-{number:03d}.json"
        path = base / BODIES / name
        if not path.is_file():
            _fetch(session, STUDIES_URL, diagnosis_params(batch), base, name, "coverage_annotations")
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
    malformed = [key for key, value in readings.items() if value.get("annotation_state") == "malformed"]
    return {
        "state": "incomplete" if malformed else "complete",
        "detail": "malformed condition annotations: " + ", ".join(malformed) if malformed else "",
        "trials": readings,
    }


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
    relay: bool = False,
) -> tuple[str, str]:
    """Compare the run's class search with its condition-text search; returns (state, detail).

    The state is coverage.COMPARISON_STATES. Every outcome writes coverage.json and coverage.md; a stop
    (budget, failed request) keeps every saved body so the same command resumes. In `relay` mode nothing
    is fetched here: the awaited requests are written to next.json (the relay protocol's own shape) and
    coverage.json, the state is "awaiting_fetch", and nothing is claimed until they are saved and the
    command is repeated; the saved bytes are then read exactly as direct mode's.
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
    klass = class_side(folder, query)
    try:
        spent = spent_requests(folder)
    except PullError as error:
        if error.code not in ACCOUNTING_CODES:
            raise
        return _accounting_failure(folder, policy, klass, alternate, error)
    _record_attempt(folder, spent)
    client = (
        None
        if relay
        else http
        or httpx.Client(
            base_url=API_BASE,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        )
    )
    session = (
        None
        if client is None
        else Session(
            client,
            sleep=sleep,
            monotonic=monotonic,
            progress=progress,
            acquisition=policy,
            registry_requests=spent,
            on_registry_request=lambda count: _record_attempt(folder, count),
        )
    )
    failure = ""
    diagnosis: dict[str, Any] = {"state": "not_run", "detail": "no differing trial to read", "trials": {}}
    try:
        first = _budget(folder, policy, klass, None)
        if klass["state"] != "complete":
            pass  # nothing to compare with: the alternate search is not asked
        elif first["verdict"] != "within_budget":
            failure = f"acquisition_{first['verdict']}: the comparison's first requests exceed the budget"
        else:
            try:
                failure = _retrieve_text(session, base, alternate, policy, klass, progress)
            except PullError as error:
                failure = f"{error.code}: {error.detail}"
            except Awaiting as wait:
                return _awaiting(folder, alternate, wait.fetches)
        text, _bodies = text_side_state(base, alternate, failure)
        if klass["state"] != "complete":
            text["state"], text["detail"] = "not_run", "not asked: the class search itself is not complete"
        state = coverage.comparison_state(klass, text, same_snapshot(klass, text))
        comparison = coverage.compare_id_sets(klass["ids"], text["ids"]) if state == "complete" else None
        routes = coverage.routes(klass["ids"], text["ids"]) if state == "complete" else {}
        differing = [*comparison["text_only"], *comparison["class_only"]] if comparison else []
        budget = _budget(folder, policy, klass, text["total"], len(differing))
        if differing and budget["verdict"] == "within_budget":
            try:
                diagnosis = diagnose(session, base, differing, request["condition_class"], routes)
            except PullError as error:
                diagnosis = {"state": "failed", "detail": f"{error.code}: {error.detail}", "trials": {}}
            except Awaiting as wait:
                return _awaiting(folder, alternate, wait.fetches)
        elif differing:
            diagnosis = {"state": "not_run", "detail": f"budget: {budget['verdict']}", "trials": {}}
    finally:
        if http is None and client is not None:
            client.close()
    budget["requests_this_invocation"] = 0 if session is None else session.registry_requests - spent
    budget["actual_registry_requests"] = spent_requests(folder)
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
    session: Session | None,
    base: Path,
    alternate: dict[str, str],
    policy: dict[str, int],
    klass: dict[str, Any],
    progress: Callable[[str], None],
) -> str:
    """Fetch what the alternate search still needs: /version, its identifier pages, /version again.

    The budget is decided on observed scope as soon as the first page is saved (study total) and before every
    further page; a stop raises PullError('acquisition.…') and keeps what is saved. With no session (relay)
    the awaited requests are raised as Awaiting instead of fetched. Returns "" when nothing failed.
    """
    while True:
        bodies, unreadable = _read_bodies(base / BODIES)
        first = bodies.get("ids-001.json")
        if isinstance(first, dict) and classify_json_page(first, True) in ("next", "last"):
            plan = _budget(base.parent, policy, klass, first["totalCount"])
            if plan["verdict"] != "within_budget":
                raise PullError(
                    "acquisition." + plan["verdict"],
                    acquisition.refusal_detail(
                        policy, plan["unique_studies"], plan["spent_requests"], plan["planned_requests"]
                    ),
                )
        if session is None and TEXT_START not in bodies and "ids-001.json" not in bodies:
            _code, pages, _ids, _detail = follow_ids(alternate, bodies, unreadable)
            raise Awaiting(
                [
                    relay_fetch(VERSION_URL, {}, TEXT_START, "coverage_version_start"),
                    relay_fetch(pages[0]["url"], pages[0]["params"], pages[0]["file"], "coverage_id_page"),
                ]
            )
        if TEXT_START not in bodies:
            _fetch(session, VERSION_URL, {}, base, TEXT_START, "coverage_version_start")
            continue
        code, pages, _ids, _detail = follow_ids(alternate, bodies, unreadable)
        if code == "awaiting_fetch":
            page = pages[-1]
            _fetch(session, page["url"], page["params"], base, page["file"], "coverage_id_page")
            progress(f"saved {page['file']} (alternate id page)")
            continue
        if code == "complete" and TEXT_END not in bodies:
            _fetch(session, VERSION_URL, {}, base, TEXT_END, "coverage_version_end")
            continue
        return "" if code == "complete" else f"{code}: {_detail}"


def _awaiting(folder: Path, alternate: dict[str, str], fetches: list[dict[str, str]]) -> tuple[str, str]:
    """Relay: name the awaited requests in next.json and coverage.json; claim nothing until they run."""
    words = (
        "Comparison not yet run: the registry's condition-text search for the same term, every other filter "
        "unchanged, must be fetched. Fetch each URL in `fetches`, save its body unchanged with save_fetch "
        "under the save_as given, then run the same command again. Nothing is claimed about trials the "
        "class search misses until it has run."
    )
    document = {
        "schema": SCHEMA,
        "state": "awaiting_fetch",
        "alternate_query": alternate,
        "fetches": fetches,
        "difference_words": words,
    }
    _write(folder / COVERAGE_NAME, _json(document))
    _write(folder / COVERAGE_TEXT, render(document).encode("utf-8"))
    # Every save_as directory exists before the relay asks for it, as for the main retrieval's bodies.
    for fetch in fetches:
        (folder / fetch["save_as"]).parent.mkdir(parents=True, exist_ok=True)
    waiting: dict[str, Any] = {
        "status": "awaiting_fetch",
        "detail": f"{len(fetches)} coverage request(s) to fetch",
    }
    waiting |= {"run_folder": str(folder.resolve()), "instructions": words, "fetches": fetches}
    _write(folder / "next.json", _json(waiting))
    return "awaiting_fetch", words


def render(document: dict[str, Any]) -> str:
    """coverage.json as readable text (pure): the state and what may be said first, then the facts."""
    lines = ["# Search coverage: condition class (MeSH) versus condition text", ""]
    lines += [f"State: {document['state']}", document["difference_words"], ""]
    if "class_search" not in document:
        lines.append(f"Reason: {document.get('reason')}")
        for fetch in document.get("fetches", []):
            lines.append(f"- fetch {fetch['url']} and save it as {fetch['save_as']} ({fetch['why']})")
        if document.get("alternate_query"):
            lines.append(f"Alternate query: {json.dumps(document['alternate_query'], ensure_ascii=False)}")
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
    if budget["verdict"] in ACCOUNTING_CODES:
        lines.append("Acquisition budget: not computed; historical request accounting must be resolved.")
    else:
        lines.append(
            f"Acquisition budget: {budget['planned_requests']} of {budget['max_registry_requests']} registry "
            f"requests, {budget['unique_studies']} of {budget['max_studies']} unique studies: "
            f"{budget['verdict']}"
        )
    lines += ["", document["union"].get("words", "No union is offered.")]
    return "\n".join(lines) + "\n"


NOT_RUN_WORDS = {
    "opted_out": "the person opted out of the default comparison",
    "budget": "the acquisition budget would be exceeded",
}


def default_comparison(*args: Any, **kwargs: Any) -> str:
    """default_comparison_state's plain lines alone."""
    return default_comparison_state(*args, **kwargs)[1]


def default_comparison_state(
    folder: Path,
    *,
    enabled: bool = True,
    mode: str = "direct",
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] = lambda _m: None,
) -> tuple[str, str]:
    """The default coverage comparison of a finished class-search run, as plain lines for the run's detail.

    Runs only for a resolved scope that searched a condition class (coverage.alternate_query is ok). Never
    changes the run's outcome. When not run (opted out, relay mode, budget) it says so and saves that in
    coverage.json; it never claims "no additional trials" for a comparison that did not complete.
    """
    resolution = json.loads((folder / "resolution.json").read_text(encoding="utf-8"))
    if coverage.alternate_query(resolution)[0] != "ok":
        return "not_applicable", ""
    reason = "" if enabled else "opted_out"
    if not reason:
        state, words = run_coverage(
            folder, http=http, sleep=sleep, monotonic=monotonic, progress=progress, relay=mode == "relay"
        )
        detail = saved_detail(folder)
        if state == "failed" and detail.startswith("acquisition"):
            reason = "budget"
        else:
            return state, f"Coverage comparison ({state}): {words} See coverage.md."
    words = f"coverage comparison not run: {reason.replace('_', ' ') if reason != 'budget' else 'budget'}"
    document = {
        "schema": SCHEMA,
        "state": "not_run",
        "reason": reason,
        "difference_words": f"Comparison not run ({NOT_RUN_WORDS[reason]}); no statement is made about "
        "trials the class search misses.",
    }
    if reason == "budget" and (folder / COVERAGE_NAME).is_file():
        # The comparison's limit does not erase the independently completed class search or retained costs.
        previous = json.loads((folder / COVERAGE_NAME).read_text())
        document = previous | document
    if reason == "budget" or not (folder / COVERAGE_NAME).is_file():
        _write(folder / COVERAGE_NAME, _json(document))
        _write(folder / COVERAGE_TEXT, render(document).encode("utf-8"))
    line = (
        "" if reason == "opted_out" else f"{words}: {NOT_RUN_WORDS[reason]}. {document['difference_words']}"
    )
    return "not_run", line


def saved_detail(folder: Path) -> str:
    """The alternate search's saved detail (why it stopped), or empty."""
    try:
        return json.loads((folder / COVERAGE_NAME).read_text(encoding="utf-8"))["text_search"].get(
            "detail", ""
        )
    except (OSError, ValueError, KeyError):
        return ""
