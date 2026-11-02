"""`trialledger landscape`: one run, from the request to the record (add-agent-operation 4.2).

A run lives in one folder, the checkpoint of everything it has asked and been answered, so that re-running
the same command resumes it and, once finished, changes nothing. In order:

1. The request (`request.json`): `request.request_problems` must say "ok" before anything is saved; a
   folder holding another request is never reused.
2. Its resolution: `request.lookups_needed` names the RxNav requests the request needs, round by round;
   each is fetched directly (`classes.http_get`, spaced as `classes.lookup` spaces its requests) or relayed
   through the agent (`next.json`, in the step protocol's own shape and words), and its answer saved in
   `lookups/` as the service sent it, a failure as a note of it. After the last round RxNav's release is
   read again and a change since the first round is refused by name. A stop that is only failed lookups
   sets those answers aside, so a re-run asks them again; any other stop ends the run with its advice
   (scope_advice: a failed lookup beside it is asked again in the new run folder, not in this one). The
   resolved scope (`resolution.json`: `request.resolve_scope`'s, with the release check) and its registry
   query (`scope.json`, through `steps.open_run`) are written before any study is read, and are never
   resolved again.
3. The registry pull: `steps.advance` in the run's mode.
4. The reading: direct mode asks RxClass and RxNav about the pulled studies' drugs exactly as
   `trialledger resolve` does, with the run folder's own classes.json; relay mode asks nothing after the
   pull (hundreds to thousands of requests; decided 2026-11-01), so every experimental drug's classes and
   axes are not_looked_up (reading.classes_as_looked_up, reading.axes_as_looked_up), never "no class" and
   never a failed lookup, and the manifest's retrieval says so.
5. The record: `landscape.landscape_record` with `landscape.landscape_manifest`, refused unless
   `landscape.schema_problems` finds nothing in exactly what would be written; `manifest.json` and
   `landscape.json` written whole (staged, then renamed), never overwritten by a different record.
6. The workbook, `landscape.xlsx`, at one call site (`write_book`, staged then renamed), once
   add-agent-operation 4.3 builds it.

Every decision here is a pure function returning a named code; the shell around them gathers the folder's
state and fetches, relays or writes.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import httpx

from TrialLedger import classes as rx
from TrialLedger.classes import RXNAV_VERSION, rxnav_release
from TrialLedger.ingest import PullError, reconcile_ids, requested_id_words
from TrialLedger.landscape import (
    JSON_NAME,
    RULE_VERSIONS,
    landscape_manifest,
    landscape_record,
    schema_problems,
)
from TrialLedger.reading import axes_aliases, drug_aliases, read_population
from TrialLedger.record import code_commit
from TrialLedger.request import lookup_url, lookups_needed, request_problems, resolve_scope
from TrialLedger.steps import (
    ADVICE,
    BODIES,
    FETCH_INSTRUCTIONS,
    FETCHES_NAME,
    MODES,
    NEXT_NAME,
    REQUEST_NAME,
    SCOPE_NAME,
    advance,
    open_run,
    records,
    request_url,
)

LOOKUPS = "lookups"  # the resolution's RxNav answers, one file a request, as the service sent them
LOOKUPS_NAME = "lookups.json"  # every resolution request named so far, in order, never rewritten
DROPPED = "dropped"  # within LOOKUPS: failed answers set aside, so the same command asks them again
RESOLUTION_NAME = "resolution.json"  # the resolved scope, with its release check: the record's scope
RELEASE_END = "release-end.json"  # RxNav's version.json asked again after the last round
MANIFEST_NAME = "manifest.json"
BOOK_NAME = "landscape.xlsx"
BOOK_STAGING = ".landscape.partial.xlsx"  # the workbook as it is written, renamed to BOOK_NAME once whole
SPACING = 0.2  # seconds after each RxNav request, as classes.lookup spaces them
RELEASE_REREAD = (
    "version.json asked in the first round and again after the last; release_check holds the code of the "
    "comparison (operate.release_check) and both releases"
)

# The statuses a run ends with, and the exit code of each: 0 complete, 3 awaiting the agent's fetches, 1
# failed (nothing written as the record; the same command again, or a new run folder where the status's
# words say so, may succeed), 2 refused or stopped by name (the
# request, the folder or a body must change first).
FAILED = ("lookup_failed", "rxnav_release_changed", "pull_failed", "snapshot_changed", "incomplete_total")
# The stops of request.resolve_scope that are a lookup that failed: set aside and asked again on a re-run.
FAILED_LOOKUPS = ("class_lookup_failed", "members_lookup_failed", "name_lookup_failed")
_AGAIN = "Running the same command again asks it again"
_NEW_FOLDER = "Start a new run folder (--run) with the changed request"
_REFETCH = (
    "If you fetched it, check it was saved unchanged under the file next.json named, and start a new run "
    "folder (--run) to fetch it again; otherwise tell the person the request cannot be resolved now."
)
# What the agent does about each stop of request.resolve_scope, in plain words: one remedy a code.
STOP_ADVICE = {
    "class_not_found": "RxClass holds no class of that name or id under that source. Check the class's "
    f"name (RxClass's own spelling) and its source, or name the drugs themselves. {_NEW_FOLDER}.",
    "class_ambiguous": "RxClass holds more than one class of that name under that source (the candidates "
    f"are in the detail). Name one of them by its id (drug_class: id and source). {_NEW_FOLDER}.",
    "class_source_mismatch": "RxClass holds that class, but not under the source named (the classes it "
    f"holds are in the detail). Name the source it is held under, or another class. {_NEW_FOLDER}.",
    "class_lookup_failed": f"RxNav did not answer the class's lookup. {_AGAIN}.",
    "class_malformed": "RxNav's answer to the class's lookup was not of the form RxNav gives, so the class "
    f"is not read from it. {_REFETCH}",
    "mechanism_not_in_crosswalk": "No row of TrialLedger's sourced crosswalk names that mechanism. Name a "
    f"drug class (EPC or MoA) or the drugs themselves instead. {_NEW_FOLDER}.",
    "mechanism_not_entailed": "The crosswalk names that target, but none of its rows makes a drug of the "
    "target a member of the class (each row's relation is in the detail), so no class is expanded from "
    f"it. Name a drug class (EPC or MoA) or the drugs themselves instead. {_NEW_FOLDER}.",
    "no_members": "RxClass lists no member drug of that class under its source. Name a broader class, "
    f"another source's class, or the drugs themselves. {_NEW_FOLDER}.",
    "members_lookup_failed": f"RxNav did not answer the lookup of the class's members. {_AGAIN}.",
    "members_malformed": "RxNav's answer listing the class's members was not of the form RxNav gives, so no "
    f"member is read from it. {_REFETCH}",
    "name_lookup_failed": f"RxNav did not answer a lookup of a drug's names. {_AGAIN}.",
    "name_malformed": "RxNav's answer about a drug's names was not of the form RxNav gives, so the drug is "
    f"not searched by a name alone (the search would be silently short). {_REFETCH}",
    "name_not_quotable": "A drug's name holds a double quote, which the registry's query cannot hold. Name "
    f"the drug without it. {_NEW_FOLDER}.",
    "query_too_long": "The registry query the request resolves to is longer than the registry accepts (its "
    "length and the limit are in the detail). Narrow the request: for instance an EPC class instead of a "
    "MoA class, one of the class's narrower subclasses, the drugs themselves, or a condition or phase "
    f"beside the class. {_NEW_FOLDER}.",
}
# Any other query_<code> stop: ingest.check_query refuses the query the request resolves to.
QUERY_ADVICE = (
    "The registry query the request resolves to would be refused or silently misread by the registry (the "
    f"code says why; the raw parameters are the usual cause). Change the request's params. {_NEW_FOLDER}."
)
UNKNOWN_STOP = "The request cannot be resolved (the code and the detail say why). Tell the person."
# A failed lookup beside a stop that needs a changed request: this folder is not asked it again (its request
# cannot change), the new run folder for the changed request is.
LOOKUPS_IN_NEW_FOLDER = (
    "RxNav also did not answer a lookup (its code is in the detail); this run folder does not ask it again, "
    "the new run folder for the changed request does."
)
CLASSES_LOOKED_UP = {
    "state": "looked_up",
    "source": "NLM RxClass asked for the EPC and MoA classes of every drug, biological and genetic "
    "intervention of the studies read, and RxNav for the RxNorm identity, ATC classes and structure of each "
    "experimental arm's drug, biological or genetic intervention only; cached in the run folder's "
    "classes.json",
}
CLASSES_NOT_LOOKED_UP = {
    "state": "not_looked_up",
    "source": "relay mode: RxClass and RxNav were not asked about the studies read (hundreds to thousands "
    "of requests the agent would fetch), so every experimental drug's EPC and MoA classes and its axes are "
    "not_looked_up: never no class and never a failed lookup. A class an intervention's own entry states "
    "is read as such (stated_by_record).",
}


def lookup_request(line: str) -> tuple[str, dict[str, str]]:
    """The URL and parameters of one RxNav request as `request.lookup_url` writes it (pure — pinned).

    The line is the URL, then "?" and its parameters as urlencode wrote them, or the URL alone; returns the
    URL and the parameters decoded, in order, a blank value kept, so the request fetched is the one the line
    names (the line is `lookup_url(url, params)` again).
    """
    url, _, query = line.partition("?")
    return url, dict(parse_qsl(query, keep_blank_values=True))


def saved_answer(raw: bytes) -> tuple[int, Any]:
    """One saved RxNav answer, as classes.py's decisions read it (`http_get`'s shape) (pure — pinned).

    (200, the body) for a body that is UTF-8 JSON; (0, None) for anything else: the note of a failure that
    direct mode or the agent recorded ("failed: HTTP 503"), an error page or a truncated body, which every
    decision reads as lookup_failed, never as no class. As steps.rxnav_answers reads an RxNav answer.
    """
    try:
        return 200, json.loads(raw.decode("utf-8"))
    except ValueError:
        return 0, None


def answer_bytes(status: int, body: Any) -> bytes:
    """What direct mode saves for one RxNav answer, `classes.http_get`'s (status, body) (pure — pinned).

    The body as UTF-8 JSON when the status is 200 and the body is JSON; otherwise the note of a failure, as
    the agent saves one: "failed: HTTP <status>", "failed: HTTP 200 (not JSON)" or, for no answer at all
    (status 0), "failed: no response". saved_answer reads the first back as (200, the body) and every note
    as (0, None).
    """
    if status == 200 and body is not None:
        return json.dumps(body, ensure_ascii=False).encode("utf-8")
    if status == 0:
        return b"failed: no response\n"
    return f"failed: HTTP {status}{' (not JSON)' if status == 200 else ''}\n".encode()


def release_check(first: tuple[str, str], last: tuple[str, str]) -> str:
    """Whether RxNav's release held from a request's first round of lookups to its last (pure — pinned).

    `first` and `last` are classes.rxnav_release's (code, version) of version.json as asked in the first
    round and again after the last.
      unchanged             — both found, the same release: every answer is of one release.
      release_changed       — both found, different releases: the answers may mix two; refused.
      release_lookup_failed — either request failed: it is asked again on a re-run.
      release_not_stated    — otherwise (an answer that states no release): the releases cannot be
                              compared, which is stated and refuses nothing, as resolution keeps such a
                              release.
    """
    if "lookup_failed" in (first[0], last[0]):
        return "release_lookup_failed"
    if first[0] != "found" or last[0] != "found":
        return "release_not_stated"
    return "unchanged" if first[1] == last[1] else "release_changed"


def stop_status(stops: list[list[Any]]) -> tuple[str, list[str]]:
    """How a run ends when its scope cannot resolve, from request.resolve_scope's stops (pure — pinned).

    `stops` are [slot, code, detail]. Returns the run's status and the stops' codes, each once, in order:
      lookup_failed  — every stop is a lookup that failed (FAILED_LOOKUPS): the failed answers are set aside
                       and asked again when the same command runs again;
      scope_stopped  — any other stop, or none: the request must change (each code has its advice).
    """
    codes = list(dict.fromkeys(str(stop[1]) for stop in stops))
    if codes and all(code in FAILED_LOOKUPS for code in codes):
        return "lookup_failed", codes
    return "scope_stopped", codes


def stop_advice(code: str) -> str:
    """What the agent does about one stop of request.resolve_scope, in plain words (pure — pinned).

    STOP_ADVICE's words for a code it names; QUERY_ADVICE for any other query_<code> (ingest.check_query's
    refusal of the resolved query); UNKNOWN_STOP for anything else.
    """
    if code in STOP_ADVICE:
        return STOP_ADVICE[code]
    return QUERY_ADVICE if code.startswith("query_") else UNKNOWN_STOP


def scope_advice(codes: list[str]) -> str:
    """What the agent does about a scope that stopped, from its stops' codes, in plain words (pure — pinned).

    Each code's stop_advice, in order, joined by a space, but for a lookup that failed (FAILED_LOOKUPS) beside
    any other stop: the other stop needs a changed request, and so a new run folder, where that lookup is
    asked again; this folder never asks it again, so its "running the same command again" words would be
    false. Those codes are told once, by LOOKUPS_IN_NEW_FOLDER, after the other stops' words. When every code
    is a failed lookup (stop_status's lookup_failed: the run sets them aside) each keeps its own words.
    """
    others = [stop_advice(code) for code in codes if code not in FAILED_LOOKUPS]
    if not others:
        return " ".join(stop_advice(code) for code in codes)
    failed = any(code in FAILED_LOOKUPS for code in codes)
    return " ".join([*others, LOOKUPS_IN_NEW_FOLDER] if failed else others)


def run_exit(status: str) -> int:
    """The exit code a run ends with, from its status (pure — pinned).

    0 complete (landscape.json written); 3 awaiting_fetch (relay: the agent fetches what next.json names and
    runs the same command again); 1 a failure (FAILED: a lookup or the registry did not answer, RxNav's
    release or the registry's snapshot changed, the registry's pages cannot be followed to their count;
    nothing written as the record); 2 any other status: refused or stopped by name.
    """
    if status == "complete":
        return 0
    if status == "awaiting_fetch":
        return 3
    return 1 if status in FAILED else 2


def record_state(existing: bytes | None, new: bytes) -> str:
    """What becomes of a record about to be written, beside the one the folder holds (pure — pinned).

    absent    — the folder holds none (`existing` None): write it.
    unchanged — it holds exactly these bytes: a re-run; nothing is written.
    differs   — it holds another record: it is kept, never overwritten.
    """
    if existing is None:
        return "absent"
    return "unchanged" if existing == new else "differs"


def record_mode(existing: bytes | None) -> str:
    """The mode a record already written was read in, so a finished run re-run reads alike (pure — pinned).

    `existing` is landscape.json's bytes, None when the folder holds none. Its manifest's retrieval mode
    when that is "direct" or "relay"; "" otherwise (no record, or one that is not JSON or names no such
    mode): the run's own mode is then used.
    """
    document = saved_answer(existing)[1] if existing is not None else None
    manifest = document.get("manifest") if isinstance(document, dict) else None
    retrieval = manifest.get("retrieval") if isinstance(manifest, dict) else None
    mode = retrieval.get("mode") if isinstance(retrieval, dict) else None
    return mode if mode in ("direct", "relay") else ""


def retrieval_coverage(
    mode: str, matched: int, query: dict[str, str], studies: list[dict[str, Any]]
) -> dict[str, Any]:
    """The manifest's retrieval: what the run fetched and how (pure — pinned).

    The mode the studies were read in, the studies the registry counted for the query (`matched`, its
    totalCount) and those read; whether the drugs' classes were looked up (direct mode, CLASSES_LOOKED_UP)
    or not (relay mode, CLASSES_NOT_LOOKED_UP); and, when the query names studies by number (filter.ids),
    what became of each number asked (ingest.reconcile_ids: found, aliased, missing, duplicate or
    malformed).
    """
    retrieval: dict[str, Any] = {"mode": mode, "matched": matched, "read": len(studies)}
    retrieval["drug_classes"] = dict(CLASSES_LOOKED_UP if mode == "direct" else CLASSES_NOT_LOOKED_UP)
    if "filter.ids" in query:
        retrieval["requested_ids"] = reconcile_ids(query["filter.ids"], studies)
    return retrieval


# ── the shell: it gathers the folder's state, asks the decisions what it means, and fetches, relays or writes


# What the agent does at the end of each run, in plain words, for the statuses whose words are not the step
# protocol's (steps.ADVICE) or a stop's (stop_advice).
RUN_ADVICE = {
    "complete": "The record is landscape.json in the run folder. Answer the person from it, keeping each "
    "value's status, source and registry link, and show them the scope (what was searched and what each "
    "term was expanded to) so they can judge whether it covers their question.",
    "awaiting_fetch": "Fetch each URL that next.json in the run folder lists into the file its save_as "
    "names, inside the run folder, exactly as fetched (next.json's instructions say how), then run the same "
    "command again; repeat until it reports complete. Do not fetch registry records yourself for any other "
    "use, and do not answer from them.",
    "request_refused": "The request cannot be resolved as written (the code and the slots or parameters it "
    "concerns are in the detail; `trialledger landscape --help` gives each slot's form). Correct it and run "
    "again.",
    "request_differs": "This run folder holds another request. Start a new run folder (--run) for this one: "
    "a folder holds one request, so its record never mixes two.",
    "scope_differs": "This run folder holds another request's resolved scope. Start a new run folder (--run) "
    "for this request.",
    "lookup_failed": "RxNav did not answer (the lookups are in the detail). The failed answers were set "
    "aside in lookups/dropped/, so running the same command again asks them again; if RxNav keeps failing, "
    "tell the person the request cannot be resolved now.",
    "rxnav_release_changed": "RxNav published a new data release while the request was being resolved, so "
    "its answers may mix two releases. Start a new run folder (--run) and run the request again.",
    "pull_failed": "The registry did not answer after TrialLedger's retries (its words are in the detail). "
    "Everything fetched so far is kept: run the same command again later to resume; if it keeps failing, "
    "tell the person, with the detail.",
    "schema_problem": "The record TrialLedger assembled does not pass its own schema check (each problem is "
    "in the detail), so nothing was written as the record. This is a defect of TrialLedger: tell the person, "
    "with the detail, and do not answer from anything in the run folder.",
    "record_differs": "landscape.json already holds a different record for this run (written by other code, "
    "or from other answers); it is kept as it is. Start a new run folder (--run) to write a new one.",
}
BOOK_WORDS = {
    "written": "landscape.xlsx, the workbook to hand to the person, is written beside it.",
    "kept": "landscape.xlsx, the workbook to hand to the person, is beside it.",
}


@dataclass(frozen=True)
class Outcome:
    """How a run ended: its status (run_exit gives its exit code), the detail, and what the agent does now."""

    status: str
    detail: str
    advice: str


def _ignore(_message: str) -> None:
    """Default progress sink: say nothing."""


def _write(target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: staged beside it, then renamed into place."""
    staging = target.parent / f".{target.name}.partial"
    staging.write_bytes(data)
    os.replace(staging, target)


def _json_bytes(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _read_json(path: Path) -> Any:
    """A JSON file's content, or None when it is absent or not JSON."""
    raw = _read(path)
    status, document = saved_answer(raw) if raw is not None else (0, None)
    return document if status == 200 else None


def _named(folder: Path) -> list[dict[str, Any]]:
    """The resolution requests named so far (lookups.json), in order."""
    return _read_json(folder / LOOKUPS_NAME) or []


def _answers(folder: Path, named: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Each saved answer of a resolution round, keyed by its request line as request.py reads them."""
    answers: dict[str, list[Any]] = {}
    for entry in named:
        raw = _read(folder / LOOKUPS / entry["file"])
        if entry["why"] == "rxnav_lookup" and raw is not None:
            answers[entry["key"]] = list(saved_answer(raw))
    return answers


def _name(folder: Path, named: list[dict[str, Any]], keys: list[str], why: str) -> list[dict[str, Any]]:
    """The entries of the requests `keys`, naming in lookups.json, in order, those not named yet; an entry
    named is never rewritten, so a request keeps its file across re-runs."""
    known = {entry["key"]: entry for entry in named if entry["why"] == why}
    new = []
    for key in keys:
        if key in known:
            continue
        url, params = lookup_request(key)
        number = len(named) + len(new) + 1
        file = RELEASE_END if why == "rxnav_release_end" else f"lookup-{number:03d}.json"
        known[key] = {"key": key, "file": file, "url": url, "params": params, "why": why}
        new.append(known[key])
    if new:
        _write(folder / LOOKUPS_NAME, _json_bytes(named + new))
    return [known[key] for key in keys]


def _shown(entry: dict[str, Any]) -> dict[str, str]:
    """A resolution request as the agent reads it in next.json: the step protocol's own shape and why."""
    url = request_url(entry["url"], entry["params"])
    return {"url": url, "save_as": f"{LOOKUPS}/{entry['file']}", "why": "rxnav_answer"}


def _note(folder: Path, mode: str, status: str, detail: str, words: str, fetches: list[dict]) -> None:
    """next.json, in relay mode, in the step protocol's shape: where the run stands, what to do and what to
    fetch. Direct mode keeps none."""
    if mode != "relay":
        (folder / NEXT_NAME).unlink(missing_ok=True)
        return
    document: dict[str, Any] = {"status": status, "detail": detail, "run_folder": str(folder.resolve())}
    document |= {"instructions": words, "fetches": fetches}
    _write(folder / NEXT_NAME, _json_bytes(document))


def _stop(folder: Path, mode: str, status: str, detail: str, words: str) -> Outcome:
    _note(folder, mode, status, detail, words, [])
    return Outcome(status, detail, words)


def _await(folder: Path, entries: list[dict[str, Any]]) -> Outcome:
    """Relay: name the requests to fetch in next.json, with the step protocol's instructions."""
    detail = f"{len(entries)} RxNav request(s) to fetch, named in next.json"
    _note(folder, "relay", "awaiting_fetch", detail, FETCH_INSTRUCTIONS, [_shown(e) for e in entries])
    return Outcome("awaiting_fetch", detail, RUN_ADVICE["awaiting_fetch"])


def _fetch(
    folder: Path, entries: list[dict[str, Any]], get: Callable, sleep: Callable, progress: Callable
) -> None:
    """Direct: ask RxNav for each request, spaced, and save its answer (a failure as its note), saying how far
    it has got (classes.progress_due)."""
    for done, entry in enumerate(entries, 1):
        status, body = get(entry["url"], entry["params"])
        sleep(SPACING)
        _write(folder / LOOKUPS / entry["file"], answer_bytes(status, body))
        if rx.progress_due(done, len(entries)):
            progress(f"resolving the request: {done} of {len(entries)} RxNav lookups asked")


def _drop_failed(folder: Path) -> list[str]:
    """Set aside every saved resolution answer that is a failure, so the same command asks it again; each is
    kept in lookups/dropped/, never deleted or overwritten."""
    dropped = []
    for entry in _named(folder):
        path = folder / LOOKUPS / entry["file"]
        raw = _read(path)
        if raw is None or saved_answer(raw)[0] == 200:
            continue
        aside = folder / LOOKUPS / DROPPED
        aside.mkdir(exist_ok=True)
        count = 1
        while (aside / f"{entry['file']}.{count}").exists():
            count += 1
        os.replace(path, aside / f"{entry['file']}.{count}")
        dropped.append(entry["file"])
    return dropped


def _resolve(
    folder: Path, request: Any, mode: str, get: Callable, sleep: Callable, progress: Callable
) -> tuple[Outcome | None, dict[str, Any]]:
    """The request's resolution, round by round, then RxNav's release asked again; the resolved scope, or how
    the run ends meanwhile. The scope is written into resolution.json whether or not it resolves."""
    (folder / LOOKUPS).mkdir(parents=True, exist_ok=True)
    while True:
        named = _named(folder)
        answers = _answers(folder, named)
        needed = lookups_needed(request, answers)
        if not needed:
            break
        entries = _name(folder, named, needed, "rxnav_lookup")
        if mode == "relay":
            return _await(folder, entries), {}
        _fetch(folder, entries, get, sleep, progress)
    scope = resolve_scope(request, answers)
    if scope["code"] != "resolved":
        _write(folder / RESOLUTION_NAME, _json_bytes(scope))
        status, codes = stop_status(scope["stops"])
        detail = "; ".join(f"{slot}: {code} {json.dumps(said)}" for slot, code, said in scope["stops"])
        if status == "scope_stopped":
            return _stop(folder, mode, status, detail, scope_advice(codes)), {}
        dropped = _drop_failed(folder)
        detail += f" (set aside: {', '.join(dropped)})"
        return _stop(folder, mode, status, detail, RUN_ADVICE["lookup_failed"]), {}
    if scope["release"][0] == "not_asked":
        scope["release_check"] = ["not_asked", "", ""]
    else:
        [entry] = _name(folder, _named(folder), [lookup_url(RXNAV_VERSION, {})], "rxnav_release_end")
        path = folder / LOOKUPS / entry["file"]
        if not path.is_file():
            if mode == "relay":
                return _await(folder, [entry]), {}
            _fetch(folder, [entry], get, sleep, progress)
        first = (scope["release"][0], scope["release"][1])
        last = rxnav_release(*saved_answer(path.read_bytes()))
        verdict = release_check(first, last)
        detail = f"RxNav's release: {first[0]} {first[1]!r} in the first round, {last[0]} {last[1]!r} after"
        if verdict == "release_lookup_failed":
            detail += f" the last (set aside: {', '.join(_drop_failed(folder))})"
            return _stop(folder, mode, "lookup_failed", detail, RUN_ADVICE["lookup_failed"]), {}
        if verdict == "release_changed":
            words = RUN_ADVICE["rxnav_release_changed"]
            return _stop(folder, mode, "rxnav_release_changed", detail + " the last", words), {}
        scope["release_basis"] = RELEASE_REREAD
        scope["release_check"] = [verdict, first[1], last[1]]
    _write(folder / RESOLUTION_NAME, _json_bytes(scope))
    return None, scope


def _matched(folder: Path) -> int:
    """The registry's totalCount for the query, from the first ID page the run saved."""
    fetches = _read_json(folder / FETCHES_NAME) or []
    first = next(fetch for fetch in fetches if fetch["why"] == "id_page")
    return _read_json(folder / BODIES / first["file"])["totalCount"]


def write_book(record: dict[str, Any], folder: Path) -> str:
    """The one call site of landscape.xlsx, the reviewer's workbook (`readout.write_book`,
    refine-landscape-record unit C), written from the record alone and certified by reading it back. The
    workbook is written whole or not at all: staged beside it (BOOK_STAGING), then renamed into place, so a
    run cut short never leaves a partial landscape.xlsx that a re-run would report as kept."""
    from TrialLedger.readout import write_book as write_workbook

    staging = folder / BOOK_STAGING
    write_workbook(record, staging)
    os.replace(staging, folder / BOOK_NAME)
    return "written"


def run(
    folder: Path,
    request: Any,
    mode: str,
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]] = rx.http_get,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] = _ignore,
) -> Outcome:
    """Take a run of `request` in `folder` as far as `mode` allows, and say how it stands (module docstring).

    `get` asks RxNav (classes.http_get's shape); `http`, `sleep`, `monotonic` and `progress` reach the
    registry's Session (steps.advance). Re-running resumes; a finished run re-run changes nothing.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    code, concerned = request_problems(request)
    if code != "ok":
        return Outcome("request_refused", f"{code}: {', '.join(concerned)}", RUN_ADVICE["request_refused"])
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / REQUEST_NAME).is_file():
        _write(folder / REQUEST_NAME, _json_bytes(request))
    elif _read_json(folder / REQUEST_NAME) != request:
        return Outcome("request_differs", str(folder / REQUEST_NAME), RUN_ADVICE["request_differs"])
    # The request as the folder keeps it, so a re-run given it otherwise (a file's key order, flags) writes
    # the same record.
    request = _read_json(folder / REQUEST_NAME)
    # Once its registry query is in scope.json the scope is fixed: resolution is never asked again.
    scope = _read_json(folder / RESOLUTION_NAME) if (folder / SCOPE_NAME).is_file() else None
    if scope is None:
        outcome, scope = _resolve(folder, request, mode, get, sleep, progress)
        if outcome is not None:
            return outcome
        code, concerned = open_run(folder, request, scope["query"])
        if code == "scope_differs":
            return Outcome(code, ", ".join(concerned), RUN_ADVICE["scope_differs"])
        if code != "ok":
            stop = "query_" + code.removeprefix("query.")
            return _stop(folder, mode, "scope_stopped", f"query: {stop} {concerned}", stop_advice(stop))
    try:
        step = advance(folder, mode, http=http, sleep=sleep, monotonic=monotonic, progress=progress)
    except PullError as error:
        return _stop(folder, mode, "pull_failed", str(error), RUN_ADVICE["pull_failed"])
    if step.status == "awaiting_fetch":
        detail = f"{len(step.awaited)} registry request(s) to fetch, named in next.json"
        return Outcome(step.status, detail, RUN_ADVICE["awaiting_fetch"])
    if step.status != "complete":
        return Outcome(step.status, step.detail, ADVICE[step.status])
    studies, api_version, data_timestamp = records(folder)
    existing = _read(folder / JSON_NAME)
    reading_mode = record_mode(existing) or mode
    answers: dict[str, Any] = {}
    if reading_mode == "direct":
        answers = rx.load_or_lookup_at(
            folder / rx.CACHE_NAME,
            drug_aliases(studies),
            axes_aliases(studies),
            fill_axes=True,
            get=get,
            sleep=sleep,
            monotonic=monotonic,
            progress=progress,
        )
        # RxNav's release, asked before each batch's first request and after its last: answers read across a
        # release change, or with a release that could not be read, are never made into a record.
        # The same verdicts as the request's resolution (release_check): a changed release is refused, a
        # failed release request is asked again on a re-run, and a release not stated refuses nothing.
        for first, last in rx.batch_releases(answers):
            verdict = release_check(first, last)
            if verdict in ("release_changed", "release_lookup_failed"):
                stop = "rxnav_release_changed" if verdict == "release_changed" else "lookup_failed"
                releases = f"{first[0]} {first[1]!r}, then {last[0]} {last[1]!r}"
                detail = f"RxNav's release for the drug lookups: {releases}"
                return _stop(folder, mode, stop, detail, RUN_ADVICE[stop])
    reading = read_population(studies, answers)
    retrieval = retrieval_coverage(reading_mode, _matched(folder), scope["query"], studies)
    manifest = landscape_manifest(
        studies, api_version, data_timestamp, code_commit(), retrieval, RULE_VERSIONS
    )
    # The RxNav answers decide each drug's ATC class for its universe; in relay mode none was looked up.
    looked_up = answers if reading_mode == "direct" else None
    text = _json_bytes(landscape_record(reading, studies, request, scope, manifest, looked_up))
    problems = schema_problems(json.loads(text))
    if problems:
        detail = "; ".join(f"{problem} at {where}" for problem, where in problems[:20])
        return _stop(folder, mode, "schema_problem", detail, RUN_ADVICE["schema_problem"])
    state = record_state(existing, text)
    if state == "differs":
        return _stop(folder, mode, "record_differs", str(folder / JSON_NAME), RUN_ADVICE["record_differs"])
    if state == "absent":
        _write(folder / MANIFEST_NAME, _json_bytes(manifest))
        _write(folder / JSON_NAME, text)
    book = "kept"
    if state == "absent" or not (folder / BOOK_NAME).is_file():
        # The workbook is written from the record exactly as landscape.json holds it.
        book = write_book(json.loads(text), folder)
    detail = f"{len(studies)} studies; {folder / JSON_NAME} {'written' if state == 'absent' else 'unchanged'}"
    if "requested_ids" in retrieval:
        # Trials asked for by number: how many, how many under their own number, and each other one in plain
        # words (an alias reads "<number> is another number of <trial>"), as pull prints them.
        asked = retrieval["requested_ids"]
        found = sum(entry["status"] == "found" for entry in asked)
        trials = "trial" if len(asked) == 1 else "trials"
        detail += f"\n{len(asked)} {trials} asked for by number, {found} found under their own number"
        detail += "".join(f"\n{requested_id_words(e)}" for e in asked if e["status"] != "found")
    return Outcome("complete", detail, f"{RUN_ADVICE['complete']} {BOOK_WORDS[book]}")
