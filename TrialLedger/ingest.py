"""Talk to the ClinicalTrials.gov API (v2, spec/ctg-oas-v2.yaml) and return a pull that is complete, or raise.

Every decision the network code makes is a pure function beside the code that consumes it, returning a
named code. Nothing here interprets study content: records and spreadsheet rows are kept as the API sent them.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from TrialLedger import __version__

API_BASE = "https://clinicaltrials.gov/api/v2"  # spec: servers[0].url
SPEC_API_VERSION = "2.0.5"  # spec: info.version
PAGE_SIZE = 100  # spec: pageSize is coerced down to 1,000 if greater
MAX_EMPTY_PAGES = 2  # consecutive empty pages tolerated while a nextPageToken is still offered
RETRY_BASE_SECONDS = 2.0  # first wait after a failed attempt; doubles with each further failure
RETRY_CAP_SECONDS = 60.0  # no single wait is longer than this
CSV_HEADER_START = "NCT Number,"  # first column of the API's CSV header row (observed 2026-10-31)
JSON_TYPE = "application/json"
CSV_TYPE = "text/csv"
MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 60.0
# At most ~48 requests a minute. The API publishes no limit; third-party write-ups cite ~50 per minute
# per IP (unverified). The real guard is the HTTP 429 handling in classify_response and retry_delay.
MIN_INTERVAL_SECONDS = 1.25
USER_AGENT = f"TrialLedger/{__version__}"

# Parameters this tool sets on every /studies request itself, so a caller can never override them.
RESERVED_PARAMETERS = ("format", "markupFormat", "fields", "countTotal", "pageSize", "pageToken")

_CANONICAL_NCT_ID = re.compile(r"NCT[0-9]{8}")
_SPEC_NCT_ID = re.compile(r"[Nn][Cc][Tt]0*[1-9][0-9]{0,7}")  # spec: ^[Nn][Cc][Tt]0*[1-9]\d{0,7}$
_ID_LIST_SEPARATORS = re.compile(r"[,\s]+")  # spec: "comma- and/or space-separated"


def check_query(params: dict[str, str]) -> tuple[str, list[str]]:
    """Whether a /studies query can be sent as written (pure — pinned).

    Returns a code and the parameter names it concerns:
      "ok"              — send it.
      "no_parameters"   — an empty query asks the API for every registered study; refused.
      "reserved"        — the caller set a parameter this tool owns (format, paging, fields).
      "empty_value"     — a parameter with a blank value.
      "filters_ignored" — a query.* value is nothing but NCT IDs while a filter is present. The API then
                          ignores every filter (spec, listStudies; observed 2026-10-31), so the result would
                          silently be unfiltered.
    """
    if not params:
        return "no_parameters", []
    reserved = sorted(name for name in params if name in RESERVED_PARAMETERS)
    if reserved:
        return "reserved", reserved
    blank = sorted(name for name, value in params.items() if not value.strip())
    if blank:
        return "empty_value", blank
    has_filter = any(name.startswith(("filter.", "postFilter.")) or name == "aggFilters" for name in params)
    if has_filter:
        id_only = []
        for name, value in params.items():
            tokens = [token for token in _ID_LIST_SEPARATORS.split(value) if token]
            if (
                name.startswith("query.")
                and tokens
                and all(_SPEC_NCT_ID.fullmatch(token) for token in tokens)
            ):
                id_only.append(name)
        if id_only:
            return "filters_ignored", sorted(id_only)
    return "ok", []


def classify_response(
    status_code: int | None,
    content_type: str | None,
    expected_type: str,
    attempt: int,
    max_attempts: int,
) -> str:
    """What one HTTP exchange means (pure — pinned).

    `status_code` is None when no response arrived at all (connection, timeout or protocol failure).
      "ok"                 — 2xx and the body's media type is `expected_type`.
      "retry"              — no response, 429, or 500/502/503/504, with attempts left.
      "no_response", "rate_limited", "server_error" — the same three, with no attempts left.
      "bad_request" (400), "not_found" (404) — never retried; the server's text is the explanation.
      "redirect"           — any 3xx. Never followed: the API's 301 for an alias drops the query string.
      "wrong_content_type" — 2xx carrying some other media type, such as an HTML page from a front end.
      "unexpected_status"  — anything else.
    """
    attempts_left = attempt < max_attempts
    if status_code is None:
        return "retry" if attempts_left else "no_response"
    if 200 <= status_code <= 299:
        media_type = (content_type or "").split(";")[0].strip().lower()
        return "ok" if media_type == expected_type else "wrong_content_type"
    if 300 <= status_code <= 399:
        return "redirect"
    if status_code == 429:
        return "retry" if attempts_left else "rate_limited"
    if status_code in (500, 502, 503, 504):
        return "retry" if attempts_left else "server_error"
    if status_code == 400:
        return "bad_request"
    if status_code == 404:
        return "not_found"
    return "unexpected_status"


def retry_delay(attempt: int, retry_after: str | None) -> float:
    """Seconds to wait after failed attempt number `attempt` (1-based) before the next one (pure — pinned).

    A Retry-After header in delta-seconds form is honoured; otherwise the wait is
    RETRY_BASE_SECONDS·2^(attempt−1). The result never exceeds RETRY_CAP_SECONDS. An HTTP-date Retry-After
    falls back to the exponential wait, since reading one would need a clock.
    """
    if retry_after is not None:
        text = retry_after.strip()
        if text.isascii() and text.isdigit():
            return min(float(text), RETRY_CAP_SECONDS)
    return min(RETRY_BASE_SECONDS * 2 ** (attempt - 1), RETRY_CAP_SECONDS)


def classify_version(payload: dict | list | str | int | float | bool | None) -> str:
    """Whether a decoded /version body can stamp a pull's provenance (pure — pinned).

    "ok"                — apiVersion and dataTimestamp are both non-empty strings.
    "not_an_object"     — the body is not a JSON object.
    "no_api_version"    — apiVersion is missing or not a non-empty string.
    "no_data_timestamp" — dataTimestamp is missing or not a non-empty string. Without it a pull cannot
                          say which snapshot of the registry it holds, so it is refused.
    """
    if not isinstance(payload, dict):
        return "not_an_object"
    api_version = payload.get("apiVersion")
    if not isinstance(api_version, str) or not api_version:
        return "no_api_version"
    data_timestamp = payload.get("dataTimestamp")
    if not isinstance(data_timestamp, str) or not data_timestamp:
        return "no_data_timestamp"
    return "ok"


def classify_json_page(payload: dict | list | str | int | float | bool | None, first_page: bool) -> str:
    """What one decoded JSON page of /studies means for pagination (pure — pinned).

    "next"          — well-formed and carries a nextPageToken: fetch the next page, even when
                      this one is empty.
    "last"          — well-formed and carries no nextPageToken.
    "not_an_object" — the body is not a JSON object.
    "no_studies"    — there is no `studies` list.
    "bad_study"     — a study lacks a canonical protocolSection.identificationModule.nctId.
    "no_total"      — the first page lacks a non-negative integer totalCount (countTotal=true is
                      always sent).
    "bad_token"     — nextPageToken is present but is not a non-empty string.
    """
    if not isinstance(payload, dict):
        return "not_an_object"
    studies = payload.get("studies")
    if not isinstance(studies, list):
        return "no_studies"
    for study in studies:
        section = study.get("protocolSection") if isinstance(study, dict) else None
        module = section.get("identificationModule") if isinstance(section, dict) else None
        nct_id = module.get("nctId") if isinstance(module, dict) else None
        if not isinstance(nct_id, str) or _CANONICAL_NCT_ID.fullmatch(nct_id) is None:
            return "bad_study"
    if first_page:
        total = payload.get("totalCount")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            return "no_total"
    if "nextPageToken" not in payload:
        return "last"
    token = payload["nextPageToken"]
    if not isinstance(token, str) or not token:
        return "bad_token"
    return "next"


def classify_progress(
    token: str, seen_tokens: list[str], received: int, total: int, empty_streak: int
) -> str:
    """Whether pagination may follow `token` to another page (pure — pinned).

    "continue"       — follow it.
    "repeated_token" — the API handed back a token already followed: the pages would loop.
    "overrun"        — more studies have arrived than the API's totalCount.
    "stalled"        — more than MAX_EMPTY_PAGES empty pages in a row, each still offering a token.
    """
    if token in seen_tokens:
        return "repeated_token"
    if received > total:
        return "overrun"
    if empty_streak > MAX_EMPTY_PAGES:
        return "stalled"
    return "continue"


def classify_csv_page(body: str, first_page: bool, total_header: str | None, token_header: str | None) -> str:
    """What one CSV page of /studies means for pagination (pure — pinned).

    Pages are concatenated into one file, so each must fit: only the first carries the header row, and every
    non-empty page ends in a line break.
      "next"         — well-formed, with an x-next-page-token: fetch the next page.
      "last"         — well-formed, with no x-next-page-token.
      "no_header"    — the first page does not begin with the API's header row.
      "extra_header" — a later page begins with the header row, which would become a data row.
      "unterminated" — a non-empty page does not end in a line break; concatenation would fuse two rows.
      "no_total"     — the first page lacks an integer x-total-count header.
      "bad_token"    — x-next-page-token is present but empty.
    """
    starts_with_header = body.startswith(CSV_HEADER_START)
    if first_page and not starts_with_header:
        return "no_header"
    if not first_page and starts_with_header:
        return "extra_header"
    if body and not body.endswith("\n"):
        return "unterminated"
    if first_page and (total_header is None or not (total_header.isascii() and total_header.isdigit())):
        return "no_total"
    if token_header is None:
        return "last"
    if not token_header:
        return "bad_token"
    return "next"


def assess_completeness(total: int, nct_ids: list[str]) -> str:
    """Whether a finished pagination holds exactly the studies the API said matched (pure — pinned).

    "complete"   — every match arrived, exactly once.
    "duplicates" — some study arrived more than once: the result set moved under the pagination.
    "short"      — fewer studies than totalCount: something was lost.
    "excess"     — more studies than totalCount.
    """
    if len(set(nct_ids)) != len(nct_ids):
        return "duplicates"
    if len(nct_ids) < total:
        return "short"
    if len(nct_ids) > total:
        return "excess"
    return "complete"


def compare_formats(json_ids: list[str], csv_ids: list[str]) -> str:
    """Whether the JSON record and the spreadsheet hold the same studies (pure — pinned).

    "same"      — the same NCT IDs, the same number of times.
    "different" — anything else: the two files would disagree about what was pulled.
    """
    return "same" if sorted(json_ids) == sorted(csv_ids) else "different"


# ── the network shell: it gathers facts and asks the decisions above what they mean ──────────────


class PullError(Exception):
    """Why a pull could not be completed exactly. When this is raised, nothing has been written."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Pull:
    """Every study one query matched: the JSON records and the API's CSV, from one registry snapshot."""

    query: dict[str, str]
    api_version: str
    data_timestamp: str
    retrieved_at: str
    total_count: int
    studies: list[dict[str, Any]]
    csv_text: str


def _ignore(_message: str) -> None:
    """Default progress sink: say nothing."""


class Session:
    """Throttled, retrying GETs. Each exchange is judged by classify_response; nothing is retried blindly."""

    def __init__(
        self,
        http: httpx.Client,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        progress: Callable[[str], None] = _ignore,
    ) -> None:
        self._http = http
        self._sleep = sleep
        self._monotonic = monotonic
        self.progress = progress
        self._last_request: float | None = None

    def get(self, path: str, params: dict[str, str], expected_type: str) -> httpx.Response:
        request = self._http.build_request("GET", path, params=params)
        attempt = 0
        while True:
            attempt += 1
            self._throttle()
            response: httpx.Response | None = None
            failure = ""
            try:
                response = self._http.send(request)
            except httpx.RequestError as error:
                failure = f"{type(error).__name__}: {error}"
            status = None if response is None else response.status_code
            content_type = None if response is None else response.headers.get("content-type")
            code = classify_response(status, content_type, expected_type, attempt, MAX_ATTEMPTS)
            if code == "ok" and response is not None:
                return response
            if code == "retry":
                retry_after = None if response is None else response.headers.get("retry-after")
                wait = retry_delay(attempt, retry_after)
                cause = failure or f"HTTP {status}"
                self.progress(f"retrying in {wait:g}s after {cause} (attempt {attempt} of {MAX_ATTEMPTS})")
                self._sleep(wait)
                continue
            raise PullError(f"http.{code}", _describe(request, response, failure, attempt))

    def _throttle(self) -> None:
        if self._last_request is not None:
            wait = MIN_INTERVAL_SECONDS - (self._monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._monotonic()


def _describe(request: httpx.Request, response: httpx.Response | None, failure: str, attempt: int) -> str:
    """The failing exchange in words, with the server's own text."""
    where = f"GET {request.url}"
    if response is None:
        return f"{where}: no response after {attempt} attempt(s) ({failure})"
    text = response.content.decode("utf-8", errors="replace").strip()
    if len(text) > 500:
        text = text[:500] + " …"
    content_type = response.headers.get("content-type")
    return f"{where}: HTTP {response.status_code} ({content_type}) after {attempt} attempt(s): {text}"


def _decode_json(response: httpx.Response, label: str) -> Any:
    try:
        return json.loads(response.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PullError(f"{label}.bad_json", f"{response.request.url}: {error}") from error


def fetch_version(session: Session) -> tuple[str, str]:
    """The API version and the registry's data timestamp, from /version."""
    response = session.get("/version", {}, JSON_TYPE)
    payload = _decode_json(response, "version")
    code = classify_version(payload)
    if code != "ok":
        raise PullError(f"version.{code}", f"{response.request.url}: {payload!r}"[:500])
    return payload["apiVersion"], payload["dataTimestamp"]


def fetch_json_pages(session: Session, query: dict[str, str]) -> tuple[int, list[dict[str, Any]], list[str]]:
    """Every JSON study for `query`: (totalCount, studies in API order, their NCT IDs). Complete, or raise."""
    params = {
        **query,
        "format": "json",
        "markupFormat": "markdown",
        "countTotal": "true",
        "pageSize": str(PAGE_SIZE),
    }
    studies: list[dict[str, Any]] = []
    seen_tokens: list[str] = []
    total = 0
    token: str | None = None
    empty_streak = 0
    page_number = 0
    while True:
        page_number += 1
        page_params = params if token is None else {**params, "pageToken": token}
        response = session.get("/studies", page_params, JSON_TYPE)
        payload = _decode_json(response, "json")
        code = classify_json_page(payload, token is None)
        if code not in ("next", "last"):
            raise PullError(f"json.{code}", f"page {page_number}: {response.request.url}")
        if token is None:
            total = payload["totalCount"]
        page = payload["studies"]
        studies.extend(page)
        empty_streak = 0 if page else empty_streak + 1
        session.progress(f"JSON page {page_number}: {len(studies)} of {total} studies")
        if code == "last":
            break
        token = cast(str, payload["nextPageToken"])  # classify_json_page says "next" only for a non-empty str
        progress = classify_progress(token, seen_tokens, len(studies), total, empty_streak)
        if progress != "continue":
            raise PullError(
                f"json.{progress}", f"after page {page_number}: {len(studies)} of {total} studies"
            )
        seen_tokens.append(token)
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in studies]
    verdict = assess_completeness(total, ids)
    if verdict != "complete":
        raise PullError(
            f"json.{verdict}",
            f"{len(ids)} studies received ({len(set(ids))} distinct); the API reported {total}",
        )
    return total, studies, ids


def fetch_csv_pages(session: Session, query: dict[str, str]) -> tuple[int, str, list[str]]:
    """The API's CSV for `query`: (x-total-count, the pages joined, each row's NCT ID). Complete, or raise."""
    params = {**query, "format": "csv", "countTotal": "true", "pageSize": str(PAGE_SIZE)}
    bodies: list[str] = []
    ids: list[str] = []
    seen_tokens: list[str] = []
    total = 0
    token: str | None = None
    empty_streak = 0
    page_number = 0
    while True:
        page_number += 1
        first_page = token is None
        page_params = params if first_page else {**params, "pageToken": token}
        response = session.get("/studies", page_params, CSV_TYPE)
        try:
            body = response.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PullError("csv.bad_encoding", f"page {page_number}: {error}") from error
        next_token = response.headers.get("x-next-page-token")
        code = classify_csv_page(body, first_page, response.headers.get("x-total-count"), next_token)
        if code not in ("next", "last"):
            raise PullError(f"csv.{code}", f"page {page_number}: {response.request.url}")
        if first_page:
            total = int(response.headers["x-total-count"])
        try:
            rows = list(csv.reader(io.StringIO(body, newline=""), strict=True))
        except csv.Error as error:
            raise PullError("csv.unparseable", f"page {page_number}: {error}") from error
        data_rows = rows[1:] if first_page else rows
        ids.extend(row[0] if row else "" for row in data_rows)
        bodies.append(body)
        empty_streak = 0 if data_rows else empty_streak + 1
        session.progress(f"CSV page {page_number}: {len(ids)} of {total} rows")
        if code == "last":
            break
        token = cast(str, next_token)  # classify_csv_page says "next" only for a non-empty token
        progress = classify_progress(token, seen_tokens, len(ids), total, empty_streak)
        if progress != "continue":
            raise PullError(f"csv.{progress}", f"after page {page_number}: {len(ids)} of {total} rows")
        seen_tokens.append(token)
    verdict = assess_completeness(total, ids)
    if verdict != "complete":
        raise PullError(
            f"csv.{verdict}",
            f"{len(ids)} rows received ({len(set(ids))} distinct); the API reported {total}",
        )
    return total, "".join(bodies), ids


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compare_snapshots(before: tuple[str, str], after: tuple[str, str]) -> str:
    """Whether a pull came from one registry snapshot (pure — pinned).

    `before` and `after` are (apiVersion, dataTimestamp) read from /version at the start and the end.
      "same"    — the same API version and the same data timestamp: one snapshot throughout.
      "changed" — either differs: pages may mix two versions of the registry, so the pull is refused.
    """
    return "same" if before == after else "changed"


def pull(
    query: dict[str, str],
    *,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    clock: Callable[[], str] = _utc_now,
    progress: Callable[[str], None] = _ignore,
) -> Pull:
    """Every study `query` matches, as JSON records and as the API's CSV, from one snapshot — or raise.

    `query` holds ClinicalTrials.gov /studies parameters, sent exactly as given. Nothing is written here.
    """
    code, names = check_query(query)
    if code != "ok":
        raise PullError(f"query.{code}", ", ".join(names) or "no query parameters were given")
    client = http or httpx.Client(
        base_url=API_BASE,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
    session = Session(client, sleep=sleep, monotonic=monotonic, progress=progress)
    try:
        before = fetch_version(session)
        total, studies, json_ids = fetch_json_pages(session, query)
        _, csv_text, csv_ids = fetch_csv_pages(session, query)
        after = fetch_version(session)
    finally:
        if http is None:
            client.close()
    if compare_snapshots(before, after) != "same":
        raise PullError(
            "snapshot.changed",
            f"the registry changed during the pull (API {before[0]}, data {before[1]} → "
            f"API {after[0]}, data {after[1]}); run it again",
        )
    if compare_formats(json_ids, csv_ids) != "same":
        only_json = sorted(set(json_ids) - set(csv_ids))
        only_csv = sorted(set(csv_ids) - set(json_ids))
        raise PullError(
            "formats.different",
            f"{len(json_ids)} JSON studies vs {len(csv_ids)} CSV rows; "
            f"only in JSON: {only_json[:10]}; only in CSV: {only_csv[:10]}",
        )
    return Pull(
        query=dict(query),
        api_version=before[0],
        data_timestamp=before[1],
        retrieved_at=clock(),
        total_count=total,
        studies=studies,
        csv_text=csv_text,
    )
