"""The run folder and its next step (add-agent-operation Decision 6): a pull that needs no network of its own.

A run folder is the checkpoint of one pull. It holds the request (`request.json`, as the agent gave it), the
scope (`scope.json`: the registry query the request resolved to and the RxNav requests it needs), the ordered
list of every fetch named so far (`fetches.json`: each fetch's URL, its parameters, the file its body is saved
as and why it is needed) and the bodies saved so far (`bodies/`, one file per fetch, as the server sent it).

One pure decision, `next_step`, reads that state and names what is needed next. The plan is the direct path's
own requests, with the same parameters, page sizes and order: /version first; the query's NCT IDs page by
page exactly as `ingest.query_ids` asks for them (fields=NCTId, 1,000 a page), each page's URL fixed by the
previous page's nextPageToken; the studies in batches of `ingest.PAGE_SIZE` by filter.ids, each exactly as
`ingest.query_studies` asks for one; /version last. Every saved registry body is checked with the direct
path's own classifiers (`classify_version`, `classify_json_page`, `classify_progress`, `assess_completeness`,
`compare_snapshots`): each page's form, its totalCount and page tokens, every batch exactly the IDs it asked
for, one snapshot from the first /version to the last. Nothing in a registry page says which request it
answers, so a page saved under another page's name is caught only when its tokens or counts disagree. So a
pull through the folder holds exactly the studies a direct pull of the same query at the same snapshot holds,
in the order the ID pages list them; that this is also `query_studies`' order (the registry listing IDs at
1,000 a page as it lists whole studies at 100) is tested only live and opt-in
(`test_a_live_run_holds_what_query_studies_returns`). The RxNav answers are only checked to be there: one
that is not JSON (an error page, or the failure direct mode records) is a failed lookup, read so by
`rxnav_answers`, never refused and never asked again.

The shell around it is the transport seam. `advance` in direct mode performs the named fetches itself
through `ingest.Session` (its throttle, retries and response checks) and saves each body into the folder; a
registry request that fails raises `ingest.PullError` as the direct pull does, an RxNav request that fails is
saved as a note of its failure. In relay mode it writes `next.json` (each URL, the file to save its body as,
and plain instructions for the agent that fetches them) and returns `awaiting_fetch`. Either way the next call
verifies every saved body and continues; a call with nothing new changes nothing. `records` assembles the
studies, and `rxnav_answers` reads the RxNav answers back, only when the decision says complete.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from TrialLedger.ingest import (
    API_BASE,
    JSON_TYPE,
    PAGE_SIZE,
    TIMEOUT_SECONDS,
    USER_AGENT,
    PullError,
    Session,
    assess_completeness,
    check_query,
    classify_json_page,
    classify_progress,
    classify_version,
    compare_snapshots,
    json_query_params,
)

VERSION_URL = f"{API_BASE}/version"
STUDIES_URL = f"{API_BASE}/studies"
START_NAME = "version-start.json"
END_NAME = "version-end.json"
PAGE_CODES = ("next", "last")
REQUEST_NAME = "request.json"
SCOPE_NAME = "scope.json"
FETCHES_NAME = "fetches.json"
NEXT_NAME = "next.json"
BODIES = "bodies"
MODES = ("direct", "relay")
FETCH_INSTRUCTIONS = (
    "Fetch each URL below with an HTTP GET, exactly as written, and save the response body unchanged (byte "
    "for byte: not reformatted, not summarised, not wrapped) to the file named in save_as, inside the run "
    "folder. Nothing in a registry page says which request it answers, so each body must go to the file "
    "named for its own URL. If a URL whose why is rxnav_answer answers with an HTTP error, or not at all, "
    "save the words 'failed: ' and the status (for example 'failed: HTTP 404') to its save_as instead: it is "
    "then read as a failed lookup, never as no class. Save nothing else into the bodies folder. Then run the "
    "same command again: it checks every registry body as a direct pull checks its pages (each page's form, "
    "its totalCount and page tokens, every batch exactly the IDs it asked for, one snapshot from the first "
    "/version to the last), checks only that each RxNav answer is there, and names the next fetches, until "
    "the status is complete."
)
COMPLETE_INSTRUCTIONS = (
    "Nothing more to fetch. Every registry body is saved and passed a direct pull's checks (each page's "
    "form, its totalCount and page tokens, every batch exactly the IDs it asked for, one snapshot from the "
    "first /version to the last). Every RxNav answer is saved and checked only to be there; one that is not "
    "JSON is read as a failed lookup."
)
FAILED_PREFIX = b"failed: "
# What the agent does about each refusal, in plain words: one remedy a code.
ADVICE = {
    "not_json": "The registry body named is not JSON (a truncated download or an error page). Delete it, "
    "fetch its URL again (fetches.json lists it) and run the same command again. If the URL keeps answering "
    "with an error, the run cannot complete: tell the user, with the error's text.",
    "not_a_registry_page": "The registry body named is JSON but not the API's answer to such a request "
    "(a /version answer saved as a page, an error message). Delete it, fetch its URL again (fetches.json "
    "lists it) and run the same command again. If the URL keeps answering with an error, the run cannot "
    "complete: tell the user, with the error's text.",
    "page_out_of_order": "A file was saved into the bodies folder before the run named it, or the run never "
    "names it. Delete the file named and run the same command again: it names what to fetch next.",
    "incomplete_total": "The registry's pages do not hold exactly the studies it counted, or could not be "
    "followed to them (a page token repeated, too many empty pages, more studies than counted), so the pull "
    "would not be complete. Start a new run folder: the registry may have changed while the pages were "
    "fetched, or a page was saved under another page's name.",
    "snapshot_changed": "The registry published new data during the run, so its pages may mix two snapshots. "
    "Start a new run folder.",
}


def follow_ids(
    query: dict[str, str], bodies: dict[str, Any], unreadable: list[str]
) -> tuple[str, list[dict[str, Any]], list[str], str]:
    """The query's NCT IDs as far as the saved ID pages reach (pure — pinned).

    Page n is saved as `ids-<n>.json`; its request is the one `ingest.query_ids` sends for that page (page
    one without a token, every later page with the token the page before it gave). `bodies` holds each saved
    file's decoded JSON, `unreadable` the saved files that are not JSON. Returns (code, the pages named in
    order, the IDs in page order, detail):
      "complete"            — every page saved and verified; the IDs are exactly totalCount, each once.
      "awaiting_fetch"      — the last page named is not saved yet.
      "not_json"            — a saved page is not JSON (a truncated body, an HTML error page).
      "not_a_registry_page" — a saved page is JSON but not a /studies page (classify_json_page's code).
      "incomplete_total"    — the pages cannot be followed to totalCount (classify_progress's code: a token
                              already followed, more IDs than totalCount, too many empty pages), or they
                              hold fewer, more or repeated IDs than totalCount (assess_completeness's code).
    """
    base = json_query_params(query, "NCTId")
    pages: list[dict[str, Any]] = []
    ids: list[str] = []
    seen: list[str] = []
    total = 0
    token = None
    empty_streak = 0
    while True:
        file = f"ids-{len(pages) + 1:03d}.json"
        params = base if token is None else {**base, "pageToken": token}
        pages.append({"file": file, "url": STUDIES_URL, "params": params, "why": "id_page"})
        if file in unreadable:
            return "not_json", pages, ids, file
        if file not in bodies:
            return "awaiting_fetch", pages, ids, file
        payload = bodies[file]
        code = classify_json_page(payload, token is None)
        if code not in PAGE_CODES:
            return "not_a_registry_page", pages, ids, f"{file}: {code}"
        if token is None:
            total = payload["totalCount"]
        page = payload["studies"]
        ids.extend(study["protocolSection"]["identificationModule"]["nctId"] for study in page)
        empty_streak = 0 if page else empty_streak + 1
        if code == "last":
            break
        token = payload["nextPageToken"]
        progress = classify_progress(token, seen, len(ids), total, empty_streak)
        if progress != "continue":
            return "incomplete_total", pages, ids, f"{file}: {progress}"
        seen.append(token)
    verdict = assess_completeness(total, ids)
    if verdict != "complete":
        return "incomplete_total", pages, ids, f"{verdict}: {len(ids)} IDs for a totalCount of {total}"
    return "complete", pages, ids, ""


def follow_batches(
    ids: list[str], bodies: dict[str, Any], unreadable: list[str]
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], str]:
    """The studies of the verified IDs, batch by batch, as far as the saved batches reach (pure — pinned).

    Batch n holds the next `PAGE_SIZE` IDs in page order and is saved as `studies-<n>.json`; its request is
    the one `ingest.query_studies` sends for filter.ids of those IDs. A batch holding exactly its IDs, each
    once, and exactly its totalCount of them is whole even if it offers a nextPageToken: a further page could
    only hold more studies than totalCount, which `query_studies` would refuse. Returns (code, every batch
    named in order, the batches not saved yet, detail):
      "complete"            — every batch saved, each exactly the IDs it asked for, each once, and its total.
      "awaiting_fetch"      — some batches are not saved yet (all of them can be fetched at once).
      "not_json"            — a saved batch is not JSON.
      "not_a_registry_page" — a saved batch is JSON but not a /studies page (classify_json_page's code).
      "incomplete_total"    — a batch holds other studies than it asked for, a repeat, or not its totalCount.
    """
    batches: list[dict[str, Any]] = []
    awaited: list[dict[str, Any]] = []
    for start in range(0, len(ids), PAGE_SIZE):
        asked = ids[start : start + PAGE_SIZE]
        file = f"studies-{len(batches) + 1:03d}.json"
        params = json_query_params({"filter.ids": ",".join(asked)})
        fetch = {"file": file, "url": STUDIES_URL, "params": params, "why": "studies_batch"}
        batches.append(fetch)
        if file in unreadable:
            return "not_json", batches, [], file
        if file not in bodies:
            awaited.append(fetch)
            continue
        payload = bodies[file]
        code = classify_json_page(payload, True)
        if code not in PAGE_CODES:
            return "not_a_registry_page", batches, [], f"{file}: {code}"
        got = [study["protocolSection"]["identificationModule"]["nctId"] for study in payload["studies"]]
        verdict = assess_completeness(payload["totalCount"], got)
        if verdict != "complete" or sorted(got) != sorted(asked):
            return (
                "incomplete_total",
                batches,
                [],
                f"{file}: {len(got)} studies ({verdict}), {len(asked)} asked",
            )
    return ("awaiting_fetch" if awaited else "complete"), batches, awaited, ""


def next_step(
    query: dict[str, str],
    rxnav: list[Any],
    named: list[str],
    bodies: dict[str, Any],
    unreadable: list[str],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], str]:
    """What a run folder needs next (pure — pinned).

    `query` is the scope's registry query and `rxnav` its RxNav requests, each [url, params]; `named` the
    files of the fetches named so far (fetches.json); `bodies` each saved file's decoded JSON and `unreadable`
    the saved files that are not JSON. Returns (code, plan, awaited, detail): `plan` every fetch named up to
    here, in order (each with its file, url, params and why), `awaited` those whose bodies are not saved yet.
    The last /version is named only once every batch is saved, so it is read after every page. An RxNav
    answer is answered once its file is saved, whatever it holds: one that is not JSON is a failed lookup
    (an error page, or the failure the shell recorded), read by its consumer as such, never refused here and
    never asked again; no RxNav answer is checked further, and no snapshot covers them. Only the registry's
    bodies can refuse the run.
      "complete"            — every fetch of the plan is saved, every registry body verified, /version
                              unchanged from the first to the last: the records may be assembled.
      "awaiting_fetch"      — the awaited fetches are needed next (RxNav's alongside the registry's).
      "not_json"            — a saved registry body is not JSON.
      "not_a_registry_page" — a saved registry body is JSON but not the API's answer to such a request.
      "page_out_of_order"   — a file was saved for a fetch not named yet, or one no plan names.
      "incomplete_total"    — the ID pages cannot be followed to totalCount or do not hold exactly
                              totalCount IDs, or a batch is not exactly the IDs it asked for.
      "snapshot_changed"    — the last /version differs from the first: the pages may mix two snapshots.
    """
    start = {"file": START_NAME, "url": VERSION_URL, "params": {}, "why": "version_start"}
    answers = [
        {"file": f"rxnav-{n:03d}.json", "url": url, "params": dict(params), "why": "rxnav_answer"}
        for n, (url, params) in enumerate(rxnav, 1)
    ]
    plan = [start, *answers]
    if START_NAME in unreadable:
        return "not_json", plan, [], START_NAME
    pending = [] if START_NAME in bodies else [start]
    if not pending:
        before = bodies[START_NAME]
        code = classify_version(before)
        if code != "ok":
            return "not_a_registry_page", plan, [], f"{START_NAME}: {code}"
        code, pages, ids, detail = follow_ids(query, bodies, unreadable)
        plan += pages
        if code == "complete":
            code, batches, pending, detail = follow_batches(ids, bodies, unreadable)
            plan += batches
        elif code == "awaiting_fetch":
            pending = pages[-1:]
        if code not in ("complete", "awaiting_fetch"):
            return code, plan, [], detail
        if code == "complete":
            plan.append({"file": END_NAME, "url": VERSION_URL, "params": {}, "why": "version_end"})
            if END_NAME in unreadable:
                return "not_json", plan, [], END_NAME
            if END_NAME not in bodies:
                pending = plan[-1:]
            else:
                after = bodies[END_NAME]
                code = classify_version(after)
                if code != "ok":
                    return "not_a_registry_page", plan, [], f"{END_NAME}: {code}"
                first = (before["apiVersion"], before["dataTimestamp"])
                last = (after["apiVersion"], after["dataTimestamp"])
                if compare_snapshots(first, last) != "same":
                    return (
                        "snapshot_changed",
                        plan,
                        [],
                        f"API {first[0]}, data {first[1]} → {last[0]}, {last[1]}",
                    )
    planned = {fetch["file"] for fetch in plan}
    saved = [*bodies, *unreadable]
    for file in sorted(saved):
        if file not in planned or file not in named:
            return "page_out_of_order", plan, [], f"{file}: saved before it was named"
    awaited = pending + [fetch for fetch in answers if fetch["file"] not in saved]
    return ("awaiting_fetch" if awaited else "complete"), plan, awaited, ""


# ── the shell: it gathers the folder's state, asks next_step what it means, and fetches or relays ──────────


class StepError(Exception):
    """Why a run folder holds no record yet: its next step's code and detail."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Step:
    """Where a run folder stands: its status (complete, awaiting_fetch or a refusal), the detail, and the
    fetches awaited, each with its full URL, the file to save its body as (save_as, within the run folder)
    and why it is needed."""

    status: str
    detail: str
    awaited: list[dict[str, str]]


def _ignore(_message: str) -> None:
    """Default progress sink: say nothing."""


def request_url(url: str, params: dict[str, str]) -> str:
    """The URL exactly as `ingest.Session` sends it: httpx's own encoding of the parameters, in order."""
    return str(httpx.Request("GET", url, params=params).url)


def _write(folder: Path, target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: staged in the run folder, then renamed into place."""
    staging = folder / f".{target.name}.partial"
    staging.write_bytes(data)
    os.replace(staging, target)


def _json_bytes(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def open_run(
    folder: Path, request: Any, query: dict[str, str], rxnav: Sequence[tuple[str, dict[str, str]]] = ()
) -> tuple[str, list[str]]:
    """Start a run folder for `query`, or confirm the one there: the request as given, and the scope (the
    registry query and the RxNav requests, each (url, params)). Nothing is fetched.

    ("ok", [])                — the folder holds this request and this scope.
    ("query.<code>", names)   — `ingest.check_query` refuses the query; nothing is written.
    ("scope_differs", [file]) — the folder already holds another request or scope; nothing is changed.
    """
    code, names = check_query(query)
    if code != "ok":
        return f"query.{code}", names
    scope = {"query": dict(query), "rxnav": [[url, dict(params)] for url, params in rxnav]}
    documents = ((REQUEST_NAME, request), (SCOPE_NAME, scope))
    for name, document in documents:
        path = folder / name
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != document:
            return "scope_differs", [name]
    (folder / BODIES).mkdir(parents=True, exist_ok=True)
    for name, document in documents:
        if not (folder / name).exists():
            _write(folder, folder / name, _json_bytes(document))
    return "ok", []


def _state(folder: Path) -> tuple[dict[str, Any], list[str], dict[str, Any], list[str]]:
    """The folder's state as next_step reads it: the scope, the files named so far, each saved body decoded
    (UTF-8 JSON, as the direct path decodes a response) and the saved files that are not JSON. A hidden file
    is no body."""
    scope = json.loads((folder / SCOPE_NAME).read_text(encoding="utf-8"))
    listed = folder / FETCHES_NAME
    named = (
        [fetch["file"] for fetch in json.loads(listed.read_text(encoding="utf-8"))] if listed.exists() else []
    )
    bodies: dict[str, Any] = {}
    unreadable: list[str] = []
    for path in sorted((folder / BODIES).iterdir()):
        if path.name.startswith("."):
            continue  # what an OS or a tool drops beside the bodies (.DS_Store); no fetch is named so
        try:
            bodies[path.name] = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            unreadable.append(path.name)
    return scope, named, bodies, unreadable


def _shown(fetch: dict[str, Any]) -> dict[str, str]:
    """A fetch as the agent reads it: the full URL, where to save its body, and why."""
    return {
        "url": request_url(fetch["url"], fetch["params"]),
        "save_as": f"{BODIES}/{fetch['file']}",
        "why": fetch["why"],
    }


def _name(folder: Path, plan: list[dict[str, Any]]) -> None:
    """Add the plan's fetches not listed yet to fetches.json, in order; nothing listed is ever rewritten."""
    path = folder / FETCHES_NAME
    listed = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    known = {fetch["file"] for fetch in listed}
    new = [
        {"file": fetch["file"], **_shown(fetch), "params": fetch["params"]}
        for fetch in plan
        if fetch["file"] not in known
    ]
    if new:
        _write(folder, path, _json_bytes(listed + new))


def _relay(folder: Path, step: Step) -> None:
    """next.json: where the run stands, what the agent does now in plain words, and the fetches to make."""
    words = ADVICE.get(
        step.status, COMPLETE_INSTRUCTIONS if step.status == "complete" else FETCH_INSTRUCTIONS
    )
    document = {
        "status": step.status,
        "detail": step.detail,
        "run_folder": str(folder.resolve()),
        "instructions": words,
        "fetches": step.awaited,
    }
    _write(folder, folder / NEXT_NAME, _json_bytes(document))


def _fetch(session: Session, fetch: dict[str, Any]) -> bytes:
    """One fetch's body through the Session. A registry request that fails raises PullError, as in a direct
    pull; an RxNav request that fails gives a note of the failure (not JSON), as an agent records one, so the
    lookup reads as failed (classes.py's lookup_failed) and the run goes on."""
    try:
        return session.get(fetch["url"], fetch["params"], JSON_TYPE).content
    except PullError as error:
        if fetch["why"] != "rxnav_answer":
            raise
        return FAILED_PREFIX + f"{error.code}: {error.detail}\n".encode()


def advance(
    folder: Path,
    mode: str,
    *,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] = _ignore,
) -> Step:
    """Take a run folder (started by `open_run`) as far as `mode` allows, and say where it stands.

    "direct": fetch what next_step names through `ingest.Session` (throttled, retried, every response judged
    by classify_response), save each body into the folder, and ask again, until complete or refused. A failed
    registry exchange raises `ingest.PullError`; every body saved before it stays, so the next call resumes. A
    failed RxNav exchange is saved as a note of its failure, a failed lookup.
    "relay": fetch nothing; write next.json and return. Either way every saved body is verified first, and
    fetches.json gains the fetches named. A call with nothing new changes nothing.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    client: httpx.Client | None = None
    session: Session | None = None
    try:
        while True:
            scope, named, bodies, unreadable = _state(folder)
            code, plan, awaited, detail = next_step(scope["query"], scope["rxnav"], named, bodies, unreadable)
            _name(folder, plan)
            if code != "awaiting_fetch" or mode == "relay":
                step = Step(code, detail, [_shown(fetch) for fetch in awaited])
                if mode == "relay":
                    _relay(folder, step)
                else:
                    (folder / NEXT_NAME).unlink(missing_ok=True)
                return step
            if session is None:
                client = http or httpx.Client(
                    base_url=API_BASE,
                    timeout=TIMEOUT_SECONDS,
                    follow_redirects=False,
                    headers={"User-Agent": USER_AGENT},
                )
                session = Session(client, sleep=sleep, monotonic=monotonic, progress=progress)
            for fetch in awaited:
                _write(folder, folder / BODIES / fetch["file"], _fetch(session, fetch))
                progress(f"saved {fetch['file']} ({fetch['why']})")
    finally:
        if client is not None and http is None:
            client.close()


def records(folder: Path) -> tuple[list[dict[str, Any]], str, str]:
    """A complete run folder's studies in the order the registry listed their IDs, with the API version and
    the data timestamp: what `ingest.query_studies` returns for the same query at the same snapshot. Raises
    StepError, assembling nothing, unless next_step says the folder is complete."""
    scope, named, bodies, unreadable = _state(folder)
    code, plan, awaited, detail = next_step(scope["query"], scope["rxnav"], named, bodies, unreadable)
    if code != "complete":
        raise StepError(code, detail or ", ".join(fetch["file"] for fetch in awaited))
    order: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for fetch in plan:
        if fetch["why"] not in ("id_page", "studies_batch"):
            continue
        for study in bodies[fetch["file"]]["studies"]:
            nct_id = study["protocolSection"]["identificationModule"]["nctId"]
            if fetch["why"] == "id_page":
                order.append(nct_id)
            else:
                by_id[nct_id] = study
    version = bodies[START_NAME]
    return [by_id[nct_id] for nct_id in order], version["apiVersion"], version["dataTimestamp"]


def rxnav_answers(folder: Path) -> list[tuple[str, dict[str, str], int, Any]]:
    """A complete run folder's RxNav answers, one for each request of the scope in its order, as (url,
    params, status, body) in the shape classes.py's decisions read (`http_get`'s): status 200 and the decoded
    body for a JSON answer, status 0 and None for one that is not JSON (a failure an agent or direct mode
    recorded, an error page), which the decisions read as lookup_failed, never as no class. Raises StepError,
    reading nothing, unless next_step says the folder is complete."""
    scope, named, bodies, unreadable = _state(folder)
    code, plan, awaited, detail = next_step(scope["query"], scope["rxnav"], named, bodies, unreadable)
    if code != "complete":
        raise StepError(code, detail or ", ".join(fetch["file"] for fetch in awaited))
    answers = []
    for fetch in plan:
        if fetch["why"] == "rxnav_answer":
            status, body = (200, bodies[fetch["file"]]) if fetch["file"] in bodies else (0, None)
            answers.append((fetch["url"], fetch["params"], status, body))
    return answers
