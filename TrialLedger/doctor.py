"""The capability check an agent runs first (add-agent-operation task 4.1, design Decision 3).

An agent pointed at this repository runs `trialledger doctor` before anything else. It reports, as JSON, what
this sandbox can do: the Python version and whether it is supported, each dependency, whether the registry,
RxNav and GitHub answer from this process, and whether the run folder is writable. From those facts one pure
decision names the mode a run will use: `direct` (TrialLedger fetches for itself), `relay` (the agent fetches
the URLs TrialLedger names, because this process cannot reach the registry or RxNav), or the reason no run can
start. It changes nothing that stays: a probe is one small GET with a short timeout, and the folder test
writes and removes one file, in a run folder it creates for the test and removes again when it did not
exist.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

MINIMUM_PYTHON = (3, 12)
DEPENDENCIES = ("httpx", "openpyxl")
# What each probe asks. GitHub is reported for the agent (it fetched, or will fetch, the repository from
# there); a run never needs it.
PROBES = {
    "clinicaltrials.gov": "https://clinicaltrials.gov/api/v2/version",
    "rxnav.nlm.nih.gov": "https://rxnav.nlm.nih.gov/REST/version.json",
    "github.com": "https://github.com",
}
PROBE_TIMEOUT_S = 8.0
MODES = ("direct", "relay", "unsupported_python", "missing_dependency", "folder_not_writable")
CONNECTION_RECOVERY = {
    "reachable": "Connection check succeeded; gathering will validate the source response.",
    "access_blocked": (
        "Access was refused. Use an authorised connection or a permitted exact-response fetch route."
    ),
    "rate_limited": "The service is limiting requests. Wait as the service directs, then retry the check.",
    "service_unavailable": "The service is unavailable. Retry later; this is not a missing clinical record.",
    "unexpected_response": (
        "The endpoint returned an unexpected status. Check the address and connection before retrying."
    ),
    "unreachable": (
        "This process could not connect. Use another permitted connection or an exact-response fetch route."
    ),
}
# Each step names only commands that exist today (add-agent-operation 4.2: `trialledger landscape` and its
# relay through next.json).
NEXT_STEP = {
    "direct": (
        "Run `trialledger landscape --run <folder>` with the person's request (--request FILE, or the "
        "request's flags: see `trialledger landscape --help`; trials by number: --ids "
        "NCT01234567,NCT07654321); TrialLedger fetches from the registry and RxNav itself and writes the "
        "record, landscape.json, into the folder. Answer from that record."
    ),
    "relay": (
        "This process cannot reach the registry or RxNav, so you fetch for TrialLedger. Run `trialledger "
        "landscape --run <folder> --mode relay` with the person's request (--request FILE, or the "
        "request's flags: see `trialledger landscape --help`; trials by number: --ids "
        "NCT01234567,NCT07654321). It writes next.json in the folder: fetch each URL next.json names into "
        "the file it names (save_as, inside the folder), exactly as fetched, then run the same command "
        "again; repeat until it reports complete, then answer from landscape.json. Fetch only the URLs "
        "next.json names: do not fetch registry records yourself in place of TrialLedger."
    ),
    "unsupported_python": "Install Python 3.12 or later (with uv, for example), then TrialLedger again.",
    "missing_dependency": "Install TrialLedger with its dependencies: pip install the repository.",
    "folder_not_writable": "Choose a run folder this sandbox can write to, and pass it with --run.",
}


def run_mode(python_ok: bool, missing: list[str], registry: str, rxnav: str, writable: bool) -> str:
    """The mode a run starts in, from the sandbox's facts (pure — pinned).

    `registry` and `rxnav` are probe results ("reachable", or the reason they were not). A run needs a
    supported Python, every dependency and a writable run folder, in that order of report; given those, it
    fetches for itself only when both the registry and RxNav answer, and relays through the agent otherwise
    (one unreachable host is enough: a run needs both, and a relay serves either). Codes:
      direct              — every fact holds and both hosts answer;
      relay               — every fact holds and at least one host does not answer;
      unsupported_python  — the Python is older than MINIMUM_PYTHON;
      missing_dependency  — a dependency is not installed;
      folder_not_writable — the run folder cannot be written.
    """
    if not python_ok:
        return "unsupported_python"
    if missing:
        return "missing_dependency"
    if not writable:
        return "folder_not_writable"
    if registry == "reachable" and rxnav == "reachable":
        return "direct"
    return "relay"


def http_probe_status(status: int) -> str:
    """Classify a connection check's HTTP response (pure — pinned).

    Only a successful HTTP response permits direct mode. Access restrictions, throttling,
    service failures and unexpected responses require different recovery; none means success.
    Source consumers still validate the actual response bodies when gathering evidence.
    """
    if 200 <= status < 300:
        return "reachable"
    if status in (401, 403):
        return "access_blocked"
    if status == 429:
        return "rate_limited"
    if 500 <= status < 600:
        return "service_unavailable"
    return "unexpected_response"


def probe(url: str, get: Callable[..., Any] | None = None) -> str:
    """Report a successful HTTP response, or the named failure and HTTP status/exception.

    A response from a blocked or throttled service must never select direct mode.
    """
    try:
        response = (get or httpx.get)(url, timeout=PROBE_TIMEOUT_S, follow_redirects=True)
    except Exception as error:  # every failure is reported by name, never raised past the check
        return f"unreachable: {type(error).__name__}"
    status = getattr(response, "status_code", 0)
    code = http_probe_status(status)
    return code if code == "reachable" else f"{code}: HTTP {status}"


def folder_writable(folder: Path) -> bool:
    """Whether `folder` accepts a file: one temporary file written and removed. A folder that did not exist is
    created for the test and removed after it, with every folder above it the test created, so the check
    leaves nothing behind."""
    created = [path for path in (folder, *folder.parents) if not path.exists()]
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".doctor-", delete=True) as handle:
            handle.write(b"ok")
        return True
    except OSError:
        return False
    finally:
        # deepest first, each only if it is there and empty: a folder holding anything is never removed
        for path in created:
            if not path.exists():
                continue
            try:
                path.rmdir()
            except OSError:
                break


def dependency_versions() -> dict[str, str | None]:
    """Each dependency's installed version, or None when it is not installed."""
    found: dict[str, str | None] = {}
    for name in DEPENDENCIES:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def report(folder: Path, get: Callable[..., Any] | None = None) -> dict[str, Any]:
    """The capability report: the facts, the mode `run_mode` names from them, and the agent's next step."""
    version = sys.version_info[:3]
    python_ok = tuple(version[:2]) >= MINIMUM_PYTHON
    dependencies = dependency_versions()
    missing = sorted(name for name, found in dependencies.items() if found is None)
    reach = {host: probe(url, get) for host, url in PROBES.items()}
    writable = folder_writable(folder)
    mode = run_mode(python_ok, missing, reach["clinicaltrials.gov"], reach["rxnav.nlm.nih.gov"], writable)
    return {
        "python": {"version": ".".join(map(str, version)), "supported": python_ok},
        "dependencies": dependencies,
        "reachable": reach,
        "connection_advice": {
            host: CONNECTION_RECOVERY[result.split(":", 1)[0]] for host, result in reach.items()
        },
        "run_folder": {"path": str(folder), "writable": writable},
        "platform": {"os": os.name, "executable": sys.executable},
        "mode": mode,
        "next": NEXT_STEP[mode],
    }
