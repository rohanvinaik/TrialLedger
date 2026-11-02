"""`trialledger mcp`: reference reporting and separate typed reasoning over the Model Context Protocol.

An assistant that speaks MCP (Claude Desktop, Claude Code, and the ChatGPT and Gemini clients that launch a
local server) runs TrialLedger through tools instead of a shell. The server is a thin adapter over the same
functions the command line calls (`doctor.report`, `operate.run`, the run folder's own files); it adds no
clinical reading of its own. The chatbot operates the tools and answers from the saved evidence;
TrialLedger does not use a model to invent or extract trial facts.

The protocol is MCP revision 2025-11-25 (https://modelcontextprotocol.io/specification/2025-11-25), the last
revision opened by an `initialize` handshake, over its stdio transport, with no dependency beyond the standard
library: JSON-RPC 2.0 messages, one a line, UTF-8, no embedded newline; nothing but protocol messages on
standard output (anything else the process writes goes to standard error). The lifecycle: `initialize`
negotiates the version (the client's when it is one of PROTOCOL_VERSIONS, else the latest here), then the
client's `notifications/initialized`; before `initialize` is answered only `ping` is served. Methods served:
`initialize`, `ping`, `tools/list` and `tools/call`. Revision 2026-07-28 drops the handshake; a dual-era
client of it probes a stdio server with `server/discover` and falls back to `initialize` on any error that is
not one of that revision's own (its versioning page, "Backward Compatibility with Initialization-Based
Versions"). This server answers the probe "not initialized" before `initialize` and "method not found" after,
both JSON-RPC errors of the handshake era, so such a client falls back. Batches are refused (removed in
2025-06-18). One line never ends the session: a line that cannot be decoded (not UTF-8, not JSON, nested
past the parser's depth) is a parse error, any other defect an internal error, and an answer echoing text that
cannot be written as UTF-8 (a lone surrogate the client sent) is written with JSON's \\u escapes. A
protocol problem is a JSON-RPC error (parse error, invalid request, method not found, invalid params: an
unknown tool or a call not of the protocol's shape); a tool that cannot do what it was asked returns a result
with `isError: true` and plain words, as the specification asks for input the tool refuses.

The tools: `doctor` (the capability report), `landscape` (start or continue a run), `save_fetch` (write one
body the assistant fetched, in relay mode, only where the run's next.json names it), `scope` (the resolved
search; given the request, the search previewed: resolved and fixed, no trial read, `preview.preview`) and
`record` (the finished schema-4 record, part by part, every value as the record holds it, a list or object
paged, a workbook row's address resolved to its value), and `reason` (separate typed symbolic operations;
operation `describe` returns accepted input shapes and executable examples, without reading a report).
Each reporting run folder
is a name inside one root folder (`--root`), and the server reads and writes only inside the run folders it is
given.

The decisions are pure functions returning named codes: `route` (what a message is), `negotiate` (the
version), `call_target` (which tool a call names), `argument_problems` (a call's arguments against the tool's
schema), `save_target` (the save_fetch path check), `record_view` (a part of the record), `page_window`
(a page of a part), `pointer_value` (the value at a row's address) and `study_line` (a study's line in part
studies).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from TrialLedger import __version__
from TrialLedger import classes as rx
from TrialLedger.classes import CLASS_SOURCES
from TrialLedger.contract import FIELDS, SCHEMA_VERSION
from TrialLedger.doctor import NEXT_STEP, report
from TrialLedger.landscape import JSON_NAME
from TrialLedger.operate import BOOK_NAME, RESOLUTION_NAME, Outcome, run, run_exit
from TrialLedger.preview import PREVIEWED, preview, scope_words
from TrialLedger.request import PHASES, STATUSES, STUDY_TYPES
from TrialLedger.steps import MODES, NEXT_NAME

# The revision followed, first, then the earlier ones a client may ask for: every message shape used here
# (the handshake, ping, tools/list, tools/call, a tool's text content and isError) is the same in all four.
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "trialledger", "version": __version__}
DEFAULT_ROOT = Path.home() / "trialledger-runs"
RUN_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
NCT_PATTERN = "^NCT[0-9]{8}$"
# Each JSON-RPC error a route code or a call's refusal answers with: (code, message).
ERRORS = {
    "parse_error": (-32700, "Parse error: the line is not JSON"),
    "invalid_request": (-32600, "Invalid Request: not a JSON-RPC 2.0 request of MCP's shape"),
    "not_initialized": (-32600, "Not initialized: send initialize first (only ping is served before it)"),
    "already_initialized": (-32600, "Already initialized: initialize is sent once per connection"),
    "method_not_found": (-32601, "Method not found"),
    "invalid_params": (-32602, "Invalid params"),
    "unknown_tool": (-32602, "Unknown tool"),
    "internal_error": (-32603, "Internal error"),
}
# The methods served once initialized, by their route code.
METHODS = {"tools/list": "tools_list", "tools/call": "tools_call"}
INSTRUCTIONS = (
    "TrialLedger has two layers. Layer one is available: the user names specific trial numbers or requests "
    "a subset by drug/class, condition, phase, status, study type or date. Return landscape.xlsx, a clean "
    "clinical reference spreadsheet with a dossier per study and shared listings, and landscape.json, "
    "the matching evidence record you answer from. Layer one contains registry facts and strictly warranted "
    "direct derivations only; no language model supplies source facts. The assistant answers from the saved "
    "record. Layer two is symbolic reasoning about trial design that you operate in conversation. You "
    "translate; the reason tool reasons. Restate the person's criteria and questions as typed premises, "
    "show them back in plain words, ask about each ambiguity and encode only what they confirm. Every answer "
    "is computed and lands in one of four categories, with the premise that decided it: settled (required "
    "or ruled out, or settled by default), something wrong (a contradiction), your call (allowed but not "
    "required, a proposal, comparable trials that chose differently, which cohort is meant) or not "
    "knowable from this evidence (silence, too little support). The tool abstains exactly where the "
    "premises do not settle a question: 'must everyone be at least 65?' against a brief requiring 18 or "
    "older is allowed but not required. Offer, in clinical terms: whether a patient type is in or out "
    "under draft criteria and which criterion decides it; whether criteria contradict each other; which "
    "NSCLC setting criteria imply; and, across trials the person chooses, how common a criterion is, class "
    "patterns, unusual or notable features, gaps and trials differing in one feature. First call reason "
    'with {"request":{"operation":"describe"}} and read its answer_guide, question_vocabulary and '
    "worked_session. Label every statement as from the record, computed, or your own reading; a question "
    "no operation computes is answered as your reading of the record. The complete automated trial writer "
    "is designed and partly built; do not present these answers as a generated protocol. "
    "Call doctor first; then scope with a run name and "
    "the person's request, in the mode doctor reports; show the person the resolved search before gathering. "
    "If a class name has catalogue choices, confirm the intended class, then preview its ID and source in a "
    "new run. No candidate is automatically selected. Then call landscape with the fixed request. "
    "In relay mode, fetch what scope or landscape lists, save each body with save_fetch, and "
    "call landscape again until it reports complete (use relay only when doctor reports it: each body then "
    "passes through you, so save it exactly as received, never retyped, shortened or corrected); then answer "
    "only from record, keeping its sources and any stated status. A fetch tool must provide the complete "
    "unchanged response; excerpts or reconstructed JSON are not a relay transport. Search terminology "
    "lookups work through relay, but drug enrichment after gathering is not performed in relay mode. "
    "Not stated is never none; not posted is never no effect; a registered outcome is a "
    "plan, not a result."
)
# What each exit code of a run means, in plain words (operate.run_exit).
EXIT_MEANINGS = {
    0: "complete: the record is written; read it with the record tool",
    3: "waiting for you: fetch each URL in fetches, save each body with save_fetch, then call landscape "
    "again",
    2: "refused or stopped by name: the advice says what to change",
    1: "failed: nothing was written as the record; the advice says whether calling again resumes or a new "
    "run folder is needed",
}
# What a preview that ends resolved means (operate.run_exit's words are for a run).
PREVIEW_MEANING = (
    "previewed: the search is resolved and fixed in the run folder, and nothing is gathered; show the person "
    "in_words, then call landscape with the same run and request to gather exactly this search"
)
RELAY_STEPS = (
    "For each entry of fetches: GET its url with your web fetch tool, exactly as written, and call "
    "save_fetch with this run, its save_as and the body exactly as received (for an HTTP error or no answer "
    "at an rxnav_answer, the words 'failed: HTTP <status>'). Fetch nothing else. Then call landscape again "
    "with the same run, request and mode."
)
# The doctor's next step as these tools take it (doctor.NEXT_STEP words it for the command line).
TOOL_NEXT = {
    "direct": "Call landscape with a run name and the person's request, mode direct: TrialLedger fetches "
    "from the registry and RxNav itself.",
    "relay": "Call landscape with a run name and the person's request, mode relay: it lists the URLs to "
    "fetch; save each body with save_fetch and call landscape again, until it reports complete.",
}
# What the run's advice, written for the command line, means with these tools: every status but complete,
# awaiting_fetch and the refused bodies.
TOOL_TERMS = (
    "The advice is worded for the command line. With these tools, 'run the same command again' means call "
    "landscape again with the same run, request and mode; 'a new run folder' (--run) means call landscape "
    "with a new run name and the request; each slot's form is in the request's description in landscape's "
    "input schema (there is no --help to run)."
)
# The doctor's next step for a run folder it cannot write, as these tools take it.
NOT_WRITABLE_WORDS = (
    "The server cannot write that run folder. Every run folder is a name inside the root folder the "
    "client's configuration gives `trialledger mcp` (--root): try another run name, and if none can be "
    "written, ask the person to give a root folder this computer can write to, in that configuration."
)
# The step protocol's refusals of a saved body (steps.ADVICE): its advice is to delete the body and fetch
# it again, which these tools cannot do (save_fetch writes only what next.json awaits).
REFUSED_BODIES = ("not_json", "not_a_registry_page", "page_out_of_order")
REFUSED_BODY_WORDS = (
    "These tools cannot delete or replace a body already saved. Call landscape again with a new run name "
    "and the same request: the search starts afresh in its own folder. Save only what each fetch returned, "
    "and never an error page for a registry URL."
)
SAVE_REFUSALS = {
    "run_outside_root": "That run folder is a link reaching out of the server's root folder, so these "
    "tools do not read or write it. Use another run name.",
    "outside_run": "save_as must be a path inside the run folder, as next.json writes it (for example "
    "bodies/ids-001.json): not absolute, without '..' or a backslash, and not reaching out of the folder "
    "through a link. Nothing was written.",
    "not_named": "The run's next.json does not name that save_as among the fetches it awaits. Save only "
    "what landscape listed, under the save_as it gave; call landscape for the current list. Nothing was "
    "written.",
}
ARGUMENT_WORDS = {
    "not_an_object": "The arguments must be a JSON object.",
    "unknown_argument": "The tool takes no argument of that name.",
    "missing_argument": "A required argument is missing.",
    "wrong_type": "An argument is not of its type (the tool's input schema gives each).",
    "not_allowed": "An argument is not one of the values its schema allows, or not of its form (a run "
    "name: letters, digits, '.', '_' or '-', starting with a letter or digit; an NCT number: NCT and eight "
    "digits).",
}
RECORD_PARTS = ("manifest", "studies", "study", "statuses", "fields", "address")
# The most entries one call returns of a part that is a list or an object (studies, fields, findings,
# questions, and a list or object an address names): the rest is read page by page, with offset.
RECORD_PAGE_LIMIT = 50
RECORD_WORDS = {
    "not_a_record": "landscape.json in this run folder is not a record of TrialLedger's form; do not answer "
    "from it.",
    "schema_not_4": "landscape.json in this run folder was written under another form of the record (its "
    "schema_version is not 4), which these tools do not read. Call landscape with a new run name and the "
    "same request to gather it again.",
    "nct_needed": "part study needs nct, the study's NCT number (part studies lists them).",
    "no_such_study": "The record holds no study of that NCT number (held lists those it does).",
    "address_needed": "part address needs address, a row's address in the record as the workbook gives it "
    "(a JSON pointer such as /studies/0/adverse_events/events/3).",
    "not_a_pointer": "address must be a JSON pointer starting with '/', each step a key or a list position "
    "written without leading zeros (for example /studies/1/posted_outcomes/0), as the workbook's 'Address in "
    "the record' column gives it.",
    "outside_record": "The record holds nothing at that address (a step names a key it does not have, a list "
    "position past its end, or steps into a single value). Check the address against the workbook's 'Address "
    "in the record' column.",
    "offset_out_of_range": "offset must be 0, or a position before the end of the part (page.total gives "
    "its length).",
    "limit_out_of_range": f"limit must be between 1 and {RECORD_PAGE_LIMIT}.",
    "unknown_part": "part must be one of " + ", ".join(RECORD_PARTS) + ".",
}


def _served(part: str) -> tuple[str, ...]:
    """The names of the contract fields the record tool serves in `part` (contract.FIELDS' consumers)."""
    return tuple(field.name for field in FIELDS if ("mcp", part) in field.consumers)


# What each part serves, from the contract: the study fields of a line of part studies (each a top-level key
# of the study, or a key within one); the record's top-level sections of parts manifest and statuses; the
# sections of part findings, each as its path in the record (a list of rows, such as cohort.frequency or
# recurring_criteria, or one value, such as cohort.reason); and the study field of part questions.
STUDY_LINE = tuple(name.removeprefix("studies[].") for name in _served("studies"))
MANIFEST_KEYS = tuple(dict.fromkeys(name.split(".")[0] for name in _served("manifest")))
STATUS_KEYS = tuple(dict.fromkeys(name.split(".")[0] for name in _served("statuses")))

# ── the tools: each one's name, description and input schema ──────────────────────────────────────────────

RUN = {
    "type": "string",
    "pattern": RUN_PATTERN,
    "description": "The run folder's name (letters, digits, '.', '_' or '-'; for example egfr-nsclc). One "
    "folder holds one request and everything gathered for it; a new request needs a new name.",
}
REQUEST = {
    "type": "object",
    "description": "The person's request, as slots (each optional; give at least one). The names of one slot "
    "are joined by OR, the slots by AND.",
    "properties": {
        "drug": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "Drug names; canonical RxNorm names and source-backed product relationships "
            "are shown in the preview.",
        },
        "drug_class": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "the class's name, RxClass's own spelling"},
                "id": {"type": "string", "description": "or the class's id (for example L01EB)"},
                "source": {
                    "type": "string",
                    "enum": list(CLASS_SOURCES),
                    "description": "EPC (FDA Established Pharmacologic Class), MoA (MED-RT mechanism of "
                    "action) or ATC (WHO ATC class)",
                },
                "subclasses": {
                    "anyOf": [
                        {"type": "string", "enum": ["include", "exclude"]},
                        {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                    ],
                    "description": "include (the default): the class with every subclass under it; exclude: "
                    "the members reached only through a subclass are left out; or the ids of the "
                    "subclasses to leave out, each with everything under it (scope lists them). A member "
                    "the class lists itself is always searched.",
                },
            },
            "required": ["source"],
            "additionalProperties": False,
            "description": "A drug class, by name or id (one of them) with its source; it is expanded into "
            "its member drugs, with every subclass named and each member attributed to the subclasses it is "
            "reached through. A broad class may bring in subclasses the person does not expect: show them "
            "the scope, and exclude a subclass when they ask.",
        },
        "mechanism": {"type": "string", "description": "A drug target of TrialLedger's sourced crosswalk."},
        "condition": {"type": "string", "description": "A condition, searched as the registry searches it."},
        "condition_class": {
            "type": "string",
            "description": "A MeSH descriptor (for example Lung Neoplasms), read with everything under it.",
        },
        "phase": {"type": "array", "items": {"type": "string", "enum": list(PHASES)}, "minItems": 1},
        "status": {"type": "array", "items": {"type": "string", "enum": list(STATUSES)}, "minItems": 1},
        "study_type": {"type": "string", "enum": list(STUDY_TYPES)},
        "start_from": {"type": "string", "format": "date", "description": "earliest start date, YYYY-MM-DD"},
        "start_to": {"type": "string", "format": "date", "description": "latest start date, YYYY-MM-DD"},
        "params": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Raw ClinicalTrials.gov API parameters for anything else (for example "
            '{"filter.ids": "NCT04852770,NCT01030536"} for trials by number).',
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}
TOOLS: dict[str, dict[str, Any]] = {
    "doctor": {
        "description": "Check what this computer can do before a search: whether it reaches "
        "ClinicalTrials.gov and RxNav (the US National Library of Medicine's drug vocabulary), and whether "
        "the run folder can be written. Returns the mode a search will use: direct (TrialLedger fetches for "
        "itself) or relay (you fetch the web addresses it names and save each with save_fetch), or why no "
        "search can start. Call it once, first, and pass its mode to landscape: direct whenever it reports "
        "direct, since in relay every registry page passes through you. Per-host connection_advice explains "
        "blocked access, rate limits, service failures and unexpected HTTP responses. Its temporary "
        "write check leaves no new run folder behind.",
        "inputSchema": {
            "type": "object",
            "properties": {"run": RUN},
            "required": ["run"],
            "additionalProperties": False,
        },
    },
    "landscape": {
        "description": "Run, or continue, one search of ClinicalTrials.gov for the person's request: every "
        "matching study is gathered, checked for completeness and read into a record by fixed rules; no "
        "language model supplies the trial facts. The request's terms are resolved first (a drug class "
        "into its member "
        "drugs, each drug into its names, a disease class through the registry's MeSH tree): show the person "
        "that resolved search (the scope tool) before relying on the results. Returns a status. complete: "
        "the record is ready (read it with the record tool; landscape.xlsx, when written, is the workbook to "
        "hand over). awaiting_fetch (relay mode): fetch each URL in fetches, save each body with save_fetch, "
        "then call landscape again with the same run, request and mode, until complete. Any other status is "
        "a refusal or a failure, with advice saying what to change or whether calling again resumes. "
        "Calling again with the same run and request is always safe, and a call that timed out can simply be "
        "repeated: the run folder keeps everything gathered. Without mode, doctor decides it at every call; "
        "pass the mode returned.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": RUN,
                "request": REQUEST,
                "mode": {
                    "type": "string",
                    "enum": list(MODES),
                    "description": "direct or relay, as doctor reported (default: doctor decides)",
                },
            },
            "required": ["run", "request"],
            "additionalProperties": False,
        },
    },
    "save_fetch": {
        "description": "Save one body you fetched for a relay-mode search into its run folder, exactly as "
        "given (written byte for byte as UTF-8, never reformatted, summarised or wrapped). Only a save_as "
        "the run's current fetch list names is accepted, inside the run folder; anything else is refused and "
        "nothing is written. Only for a fetch whose why is rxnav_answer, when the URL answered with an HTTP "
        "error or not at all, save the words 'failed: HTTP <status>' as its body. A registry URL (why "
        "version_start, id_page, studies_batch or version_end) that answers with an error is fetched again; "
        "never save an error page for it. The body is checked for form, counts, page order and the exact "
        "trials asked, not value by value, so pass it through exactly as your fetch tool returned it: never "
        "retype, shorten, reformat or correct it. When every listed body is saved, call landscape again.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": RUN,
                "save_as": {"type": "string", "description": "the save_as landscape listed for the URL"},
                "body": {"type": "string", "description": "the response body, exactly as received"},
            },
            "required": ["run", "save_as", "body"],
            "additionalProperties": False,
        },
    },
    "scope": {
        "description": "The search of a run as resolved, to show the person before anything is gathered: "
        "each drug class expanded into its member drugs (every subclass named, each member with the subclass "
        "it is reached through), each drug's names as searched, each disease class through MeSH, the other "
        "filters, and the exact registry query; or, when the request cannot be resolved, the named reason "
        "(its code and stops). Given the request (and the mode doctor reports), it previews: the request is "
        "resolved and the search fixed in the run folder, and no trial is read (in relay mode it may first "
        "list RxNav addresses to fetch and save with save_fetch, as landscape does; then call scope again). "
        "Show the person in_words; then landscape with the same run and request gathers exactly this search. "
        "Without the request it reads the search already resolved.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": RUN,
                "request": REQUEST,
                "mode": {
                    "type": "string",
                    "enum": list(MODES),
                    "description": "direct or relay, as doctor reported (default: doctor decides)",
                },
            },
            "required": ["run"],
            "additionalProperties": False,
        },
    },
    "record": {
        "description": "Read landscape.json exactly as written. Registry values are plain; their API paths "
        "are defined once in fields. Direct derivations and missing values retain their status and source. "
        "Parts: manifest (request, snapshot, code and requested-ID accounting), studies (study index), study "
        "(one NCT record), fields (source dictionary), statuses, and address (the exact JSON pointer from a "
        "workbook row). Lists and objects are paged at most 50 entries per call; use page.next_offset. "
        "Use it to explain a study's source eligibility, planned outcomes, group-specific results and "
        "safety, canonical drug identity/class evidence and registry consistency checks. Those checks "
        "describe source consistency, not clinical suitability. "
        "Not stated is never none; not posted is never no effect; planned outcomes are not observed results. "
        "Layer one supplies no inferred setting, clinical recommendation or trial-design proposal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": RUN,
                "part": {"type": "string", "enum": list(RECORD_PARTS)},
                "nct": {
                    "type": "string",
                    "pattern": NCT_PATTERN,
                    "description": "the study's NCT number, for part study",
                },
                "address": {
                    "type": "string",
                    "description": "a workbook row's address in the record, a JSON pointer such as "
                    "/studies/0/posted_outcomes/1, for part address",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "the first entry of the page (default 0)",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": RECORD_PAGE_LIMIT,
                    "description": f"the most entries returned (default and at most {RECORD_PAGE_LIMIT})",
                },
            },
            "required": ["run", "part"],
            "additionalProperties": False,
        },
    },
    "reason": {
        "description": "Layer two: symbolic reasoning about a trial design. Check whether a patient type "
        "is in or out under a person's criteria and which criterion decides it, find contradictions, narrow "
        "NSCLC settings, or compute criterion frequencies with silence bounds, class associations, rarity, "
        "occupancy and pairs differing in one declared feature across trials the person chooses. Answers are "
        "entailed, refuted, inconsistent or undetermined with named reasons; undetermined is exact "
        "abstention, not failure. You translate: prepare the structured premises from what the person "
        "confirms; they need not know the format. First call with "
        '{"request":{"operation":"describe"}} for input formats, the answer guide and a runnable worked '
        "session. Reasoning requests name operation entailment, coordinates or corpus. Premises retain their "
        "source/user status; an assistant's interpretation is never a registry fact. No trial text is "
        "interpreted, no source is fetched and no report is changed. The complete trial writer is designed "
        "and partly built; these results are not a generated protocol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["describe", "entailment", "coordinates", "corpus"],
                        }
                    },
                    "required": ["operation"],
                    "description": "Start with operation describe for exact request formats and runnable "
                    "examples; other operations require the typed premises it describes.",
                }
            },
            "required": ["request"],
            "additionalProperties": False,
        },
    },
}


# ── the decisions ─────────────────────────────────────────────────────────────────────────────────────────


def route(message: Any, initialized: bool) -> tuple[str, Any]:
    """What one decoded message is, and the id an answer to it carries (pure — pinned).

    `initialized` is whether `initialize` has been answered on this connection. Returns (code, id); the id is
    the message's when it is a string or an integer (never a boolean), else None.
      invalid_request     — not an object of jsonrpc "2.0"; a method that is not a string; a request whose
                            id is not a string or an integer; an object with neither a method nor a
                            result or error (a JSON array, a batch, is not an object);
      response            — a client's answer (an id and a result or error, no method): nothing to answer;
      notification        — a method and no id: never answered (notifications/initialized among them);
      invalid_params      — a request whose params are not an object;
      initialize          — the handshake's request, the first time;
      already_initialized — the handshake's request again;
      ping                — answered whenever it comes;
      not_initialized     — any other request before initialize is answered;
      tools_list, tools_call — the methods served (METHODS);
      method_not_found    — any other method (server/discover among them).
    """
    ident = message.get("id") if isinstance(message, dict) else None
    valid_id = isinstance(ident, str | int) and not isinstance(ident, bool)
    ident = ident if valid_id else None
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return "invalid_request", ident
    if "method" not in message:
        answered = valid_id and ("result" in message or "error" in message)
        return ("response" if answered else "invalid_request"), ident
    method = message["method"]
    if not isinstance(method, str):
        return "invalid_request", ident
    if "id" not in message:
        return "notification", None
    if not valid_id:
        return "invalid_request", None
    if "params" in message and not isinstance(message["params"], dict):
        return "invalid_params", ident
    if method == "initialize":
        return ("already_initialized" if initialized else "initialize"), ident
    if method == "ping":
        return "ping", ident
    if not initialized:
        return "not_initialized", ident
    return METHODS.get(method, "method_not_found"), ident


def negotiate(params: Any) -> tuple[str, str]:
    """The protocol version an initialize request is answered with (pure — pinned).

    `params` is the request's params. ("ok", the version asked) when it is one of PROTOCOL_VERSIONS; ("ok",
    PROTOCOL_VERSIONS[0], the latest here) for any other version string, as the lifecycle asks (the client
    then decides whether to go on); ("invalid_params", "") when params are not an object or name no version
    as a string.
    """
    requested = params.get("protocolVersion") if isinstance(params, dict) else None
    if not isinstance(requested, str):
        return "invalid_params", ""
    return "ok", requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]


def call_target(params: Any) -> tuple[str, str, dict[str, Any]]:
    """Which tool a tools/call request names, and its arguments (pure — pinned).

    Returns (code, the tool's name, the arguments):
      ok             — a tool of TOOLS, with its arguments (an object; none given is {});
      invalid_params — params not an object, a name that is not a string, or arguments not an object;
      unknown_tool   — a name no tool here has (its name returned, to be told).
    """
    if not isinstance(params, dict) or not isinstance(params.get("name"), str):
        return "invalid_params", "", {}
    name = params["name"]
    if name not in TOOLS:
        return "unknown_tool", name, {}
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return "invalid_params", name, {}
    return "ok", name, arguments


def argument_problems(schema: dict[str, Any], arguments: Any) -> tuple[str, list[str]]:
    """Whether a call's arguments hold to its tool's input schema, at the top level (pure — pinned).

    The schemas here use, at the top level, `properties` (each with a `type` of string, object, integer or
    boolean, and optionally an `enum` or a `pattern`; an integer's `minimum` and `maximum` tell the client its
    range and are not read here: record_view refuses an offset or a limit outside it through page_window),
    `required` and `additionalProperties: false`; each pattern is anchored at both ends and matched against
    the whole value. What lies inside an object argument (the landscape request) is not read here:
    `request.request_problems` names its problems. Returns the first code that applies, in this order, and the
    arguments it concerns, sorted:
      not_an_object    — the arguments are not an object;
      unknown_argument — names the schema does not describe;
      missing_argument — required names not given;
      wrong_type       — values not of their type (a boolean is not an integer);
      not_allowed      — values outside their enum, or not matching their pattern;
      ok               — none of these.
    """
    if not isinstance(arguments, dict):
        return "not_an_object", []
    described = schema["properties"]
    unknown = sorted(str(name) for name in arguments if name not in described)
    if unknown:
        return "unknown_argument", unknown
    missing = sorted(name for name in schema.get("required", ()) if name not in arguments)
    if missing:
        return "missing_argument", missing
    kinds = {"string": str, "object": dict, "integer": int, "boolean": bool}
    wrong = sorted(
        name
        for name, value in arguments.items()
        if not isinstance(value, kinds[described[name]["type"]])
        or (described[name]["type"] == "integer" and isinstance(value, bool))
    )
    if wrong:
        return "wrong_type", wrong
    refused = sorted(
        name
        for name, value in arguments.items()
        if ("enum" in described[name] and value not in described[name]["enum"])
        or (
            "pattern" in described[name]
            and re.fullmatch(described[name]["pattern"].removeprefix("^").removesuffix("$"), value) is None
        )
    )
    if refused:
        return "not_allowed", refused
    return "ok", []


def save_target(save_as: Any, named: list[Any]) -> str:
    """Whether save_fetch may write a body to `save_as` within a run folder (pure — pinned).

    `named` is every save_as the run's next.json lists. The path is read as next.json writes it, relative
    to the run folder with "/" between its parts:
      outside_run — empty, not a string, absolute, holding a ".." part, a backslash, a NUL or a drive
                    letter ("C:"): it could name a file outside the run folder, so it is refused even when
                    next.json names it (a next.json edited by hand);
      not_named   — next.json does not list it;
      ok          — it is listed, and stays inside the run folder as written (the shell also refuses one a
                    link would carry outside).
    """
    if not isinstance(save_as, str) or not save_as:
        return "outside_run"
    path = PurePosixPath(save_as)
    if path.is_absolute() or ".." in path.parts or "\\" in save_as or "\x00" in save_as:
        return "outside_run"
    if ":" in path.parts[0]:
        return "outside_run"
    return "ok" if save_as in named else "not_named"


def page_window(total: int, offset: int, limit: int) -> tuple[str, dict[str, Any]]:
    """The page of a part `total` entries long that an offset and a limit name (pure — pinned).

    ("ok", page) with page = {offset, limit, returned, total, next_offset}: the entries from offset, at most
    limit of them; next_offset the position the next page starts at, None on the last page.
      offset_out_of_range — offset below 0, or not before the end (0 is always a page, the only one of an
                            empty part);
      limit_out_of_range  — limit below 1 or above RECORD_PAGE_LIMIT.
    The refusals carry an empty page.
    """
    if limit < 1 or limit > RECORD_PAGE_LIMIT:
        return "limit_out_of_range", {}
    if offset < 0 or (offset >= total and offset != 0):
        return "offset_out_of_range", {}
    returned = min(limit, total - offset)
    following = offset + returned
    page = {"offset": offset, "limit": limit, "returned": returned, "total": total}
    return "ok", page | {"next_offset": following if following < total else None}


def pointer_value(document: Any, pointer: Any) -> tuple[str, Any]:
    """The value at a JSON pointer (RFC 6901) in a document (pure — pinned).

    A workbook row's address in the record: "/" then each step, "~1" written for "/" and "~0" for "~" within
    a step. ("ok", the value) when every step is held: a key of an object, or a list position written in
    decimal without leading zeros. Codes:
      not_a_pointer  — not a string starting with "/", or a "~" not followed by 0 or 1;
      outside_record — a step the document does not hold: a key an object lacks, a list position that is
                       not a number or is past the list's end ("-", the position after the end, among them),
                       or any step into a value that is neither an object nor a list.
    """
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return "not_a_pointer", None
    node = document
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            return "not_a_pointer", None
        step = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and step in node:
            node = node[step]
        elif isinstance(node, list) and re.fullmatch(r"0|[1-9][0-9]*", step) and int(step) < len(node):
            node = node[int(step)]
        else:
            return "outside_record", None
    return "ok", node


def study_line(study: dict[str, Any]) -> dict[str, Any]:
    """The contract's source fields for one index line, preserving missing-value objects whole.

    Nested source fields retain their parent object. No derived clinical category is substituted.
    """
    line: dict[str, Any] = {}
    for name in STUDY_LINE:
        top, _, inner = name.partition(".")
        top = top.removesuffix("[]")
        held = study.get(top)
        if inner and isinstance(held, dict) and "status" not in held:
            line.setdefault(top, {})[inner] = held.get(inner)
        else:
            line[top] = held
    return line


def record_view(record: Any, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Read a part of the direct source record, with bounded paging and exact JSON addresses.

    Parts: manifest, statuses, fields, studies, study and address. No clinical inference or
    proposed design findings are part of a layer-one record. A different schema is refused.
    """
    if not isinstance(record, dict) or not isinstance(record.get("studies"), list):
        return "not_a_record", {}
    studies = record["studies"]
    if not all(isinstance(study, dict) for study in studies):
        return "not_a_record", {}
    if record.get("schema_version") != SCHEMA_VERSION:
        return "schema_not_4", {}
    part = arguments.get("part")
    if part == "manifest":
        return "ok", {part: {key: record.get(key) for key in MANIFEST_KEYS}}
    if part == "statuses":
        return "ok", {part: {key: record.get(key) for key in STATUS_KEYS}}
    if part == "study":
        nct = arguments.get("nct")
        if nct is None:
            return "nct_needed", {}
        held = [study.get("nct") for study in studies]
        if nct not in held:
            return "no_such_study", {"held": held}
    whole: Any
    if part == "study":
        whole = studies[held.index(nct)]
    elif part == "studies":
        whole = [study_line(study) for study in studies]
    elif part == "fields":
        whole = record.get("fields")
    elif part == "address":
        if "address" not in arguments:
            return "address_needed", {}
        code, whole = pointer_value(record, arguments["address"])
        if code != "ok":
            return code, {}
    else:
        return "unknown_part", {}
    reply: dict[str, Any] = {"address": arguments["address"]} if part == "address" else {}
    if not isinstance(whole, list | dict):
        return "ok", reply | {"value" if part == "address" else part: whole}
    code, page = page_window(
        len(whole), arguments.get("offset", 0), arguments.get("limit", RECORD_PAGE_LIMIT)
    )
    if code != "ok":
        return code, {}
    window = list(whole)[page["offset"] : page["offset"] + page["returned"]]
    shown = {key: whole[key] for key in window} if isinstance(whole, dict) else window
    return "ok", reply | {"value" if part == "address" else part: shown, "page": page}


# ── the shell: it reads messages, asks the decisions what they mean, runs the tools and answers ────────────


@dataclass(frozen=True)
class Context:
    """What the tools reach: the root folder of the run folders, and the transports `operate.run` and
    `doctor.report` take (injected by tests and the production path)."""

    root: Path
    get: Callable[[str, dict[str, str]], tuple[int, Any]] = rx.http_get
    http: httpx.Client | None = None
    sleep: Callable[[float], None] = time.sleep
    probe_get: Callable[..., Any] | None = None


def _progress(message: str) -> None:
    """A run's progress, to standard error: standard output carries protocol messages only."""
    print(message, file=sys.stderr)


def _read_json(path: Path) -> Any:
    """A JSON file's content, or None when it is absent or not JSON."""
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None


def _doctor(context: Context, folder: Path, _arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    found = report(folder, context.probe_get)
    usable = found["mode"] in MODES
    reply = {"mode": found["mode"], "report": found}
    words = NOT_WRITABLE_WORDS if found["mode"] == "folder_not_writable" else found["next"]
    return reply | {"with_these_tools": TOOL_NEXT.get(found["mode"], words)}, not usable


def _outcome_reply(folder: Path, mode: str, outcome: Outcome, code: int) -> dict[str, Any]:
    """A run's or a preview's end as these tools tell it: the status, its exit code and meaning, the detail
    and advice, what the advice means with these tools, and the fetches awaited in relay mode."""
    reply: dict[str, Any] = {"mode": mode, "status": outcome.status, "exit": code}
    meaning = PREVIEW_MEANING if outcome.status == PREVIEWED else EXIT_MEANINGS[code]
    reply |= {"meaning": meaning, "detail": outcome.detail, "advice": outcome.advice}
    if outcome.status in REFUSED_BODIES:
        reply["with_these_tools"] = REFUSED_BODY_WORDS
    elif outcome.status == "mode_unavailable" and mode == "folder_not_writable":
        reply["with_these_tools"] = NOT_WRITABLE_WORDS
    elif outcome.status not in ("complete", "awaiting_fetch", PREVIEWED):
        reply["with_these_tools"] = TOOL_TERMS
    if outcome.status == "awaiting_fetch":
        waiting = _read_json(folder / NEXT_NAME) or {}
        reply |= {"then": RELAY_STEPS, "instructions": waiting.get("instructions")}
        reply["fetches"] = waiting.get("fetches", [])
    return reply


def _landscape(context: Context, folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    mode = arguments.get("mode") or report(folder, context.probe_get)["mode"]
    if mode in MODES:
        outcome = run(
            folder,
            arguments["request"],
            mode,
            get=context.get,
            http=context.http,
            sleep=context.sleep,
            progress=_progress,
        )
    else:
        outcome = Outcome("mode_unavailable", mode, NEXT_STEP[mode])
    code = run_exit(outcome.status)
    reply = _outcome_reply(folder, mode, outcome, code)
    for key, name in (("record", JSON_NAME), ("workbook", BOOK_NAME)):
        if code == 0 and (folder / name).is_file():
            reply[key] = str((folder / name).resolve())
    return reply, code in (1, 2)


def _save_fetch(_context: Context, folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    waiting = _read_json(folder / NEXT_NAME)
    fetches = waiting.get("fetches") if isinstance(waiting, dict) else None
    named = [fetch.get("save_as") for fetch in fetches if isinstance(fetch, dict)] if fetches else []
    save_as = arguments["save_as"]
    code = save_target(save_as, named)
    target = folder / save_as
    if code == "ok" and folder.resolve() not in target.resolve().parents:
        code = "outside_run"  # a link inside the folder would carry the write out of it
    if code != "ok":
        return {"save_as": save_as, "refused": code, "why": SAVE_REFUSALS[code]}, True
    try:
        data = arguments["body"].encode("utf-8")
    except UnicodeEncodeError:
        words = "The body holds text that cannot be written as UTF-8 (a lone surrogate): nothing was written."
        return {"save_as": save_as, "refused": "not_utf8", "why": words}, True
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.partial"
    staging.unlink(missing_ok=True)  # a link or a leftover at the staging name is removed, never followed
    handle = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(handle, "wb") as staged:
        staged.write(data)
    os.replace(staging, target)
    # only the names save_fetch would write are looked at, so nothing outside the run folder is read
    remaining = [n for n in named if save_target(n, named) == "ok" and not (folder / n).is_file()]
    then = "Call landscape again." if not remaining else "Save the others still listed, then call landscape."
    return {"saved": save_as, "bytes": len(data), "still_to_save": remaining, "then": then}, False


def _scope(context: Context, folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if "request" in arguments:
        mode = arguments.get("mode") or report(folder, context.probe_get)["mode"]
        if mode in MODES:
            outcome = preview(
                folder, arguments["request"], mode, get=context.get, sleep=context.sleep, progress=_progress
            )
        else:
            outcome = Outcome("mode_unavailable", mode, NEXT_STEP[mode])
        code = run_exit(outcome.status)
        reply = _outcome_reply(folder, mode, outcome, code)
        scope = _read_json(folder / RESOLUTION_NAME)
        if scope is not None and outcome.status in (PREVIEWED, "scope_stopped"):
            reply |= {"scope": scope, "in_words": scope_words(scope)}
        return reply, code in (1, 2)
    scope = _read_json(folder / RESOLUTION_NAME)
    if scope is None:
        words = (
            "No search has been resolved in this run folder yet: call scope with the run and the request to "
        )
        words += "preview it (nothing is gathered), then landscape with the same run and request."
        return {"error": "no_scope", "why": words}, True
    return {"scope": scope, "in_words": scope_words(scope)}, False


def _record(_context: Context, folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if not (folder / JSON_NAME).is_file():
        words = "This run has no record yet: call landscape until it reports complete."
        return {"error": "no_record", "why": words}, True
    code, view = record_view(_read_json(folder / JSON_NAME), arguments)
    if code != "ok":
        return {"error": code, "why": RECORD_WORDS[code], **view}, True
    return {"part": arguments["part"], **view}, False


def _reason(_context: Context, _folder: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """A separate symbolic operation; no report, network or file mutation."""
    from TrialLedger.layer2 import run

    reply = run(arguments["request"])
    return reply, reply["code"] != "complete"


HANDLERS: dict[str, Callable[[Context, Path, dict[str, Any]], tuple[dict[str, Any], bool]]] = {
    "reason": _reason,
    "doctor": _doctor,
    "landscape": _landscape,
    "save_fetch": _save_fetch,
    "scope": _scope,
    "record": _record,
}


def _text(document: Any, is_error: bool) -> dict[str, Any]:
    """A tool's result: its document as one text content block of JSON, and whether it is an error."""
    text = json.dumps(document, ensure_ascii=False, indent=1)
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(context: Context, params: Any) -> tuple[str, Any]:
    """Run one tools/call: ("ok", the result) or (the JSON-RPC error's code name, its data)."""
    code, name, arguments = call_target(params)
    if code != "ok":
        return code, {"tool": name} if name else None
    verdict, concerned = argument_problems(TOOLS[name]["inputSchema"], arguments)
    if verdict != "ok":
        refusal = {"tool": name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}
        return "ok", _text(refusal, True)
    folder = context.root if name == "reason" else context.root / arguments["run"]
    if name != "reason" and folder.resolve().parent != context.root.resolve():
        refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}
        return "ok", _text(refusal, True)
    reply, is_error = HANDLERS[name](context, folder, arguments)
    result = {"tool": name, **reply}
    if name != "reason":
        result["run_folder"] = str(folder.resolve())
    return "ok", _text(result, is_error)


def _error(ident: Any, code: str, data: Any = None) -> dict[str, Any]:
    number, message = ERRORS[code]
    error: dict[str, Any] = {"code": number, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": ident, "error": error}


def answer(context: Context, line: bytes, initialized: bool) -> tuple[dict[str, Any] | None, bool]:
    """The answer to one line (None for a notification, a response or a blank line), and whether the
    connection is initialized after it."""
    if not line.strip():
        return None, initialized
    try:
        message = json.loads(line.decode("utf-8"))
    except (ValueError, RecursionError):  # not UTF-8 (a ValueError), not JSON, or nested past the parser
        return _error(None, "parse_error"), initialized
    code, ident = route(message, initialized)
    if code in ("notification", "response"):
        return None, initialized
    if code in ERRORS:
        return _error(ident, code), initialized
    params = message.get("params", {})
    if code == "initialize":
        verdict, version = negotiate(params)
        if verdict != "ok":
            return _error(ident, verdict, {"supported": list(PROTOCOL_VERSIONS)}), initialized
        result = {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        }
        return {"jsonrpc": "2.0", "id": ident, "result": result}, True
    if code == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}, initialized
    if code == "tools_list":
        tools = [{"name": name, **tool} for name, tool in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": tools}}, initialized
    try:
        verdict, result = call_tool(context, params)
    except Exception as error:  # a defect of TrialLedger: told by name, and the connection kept
        return _error(ident, "internal_error", {"detail": f"{type(error).__name__}: {error}"}), initialized
    if verdict != "ok":
        return _error(ident, verdict, result), initialized
    return {"jsonrpc": "2.0", "id": ident, "result": result}, initialized


def wire(reply: dict[str, Any]) -> str:
    """One answer as the line written: JSON with its text as UTF-8, no embedded newline; an answer that
    echoes text UTF-8 cannot hold (a lone surrogate the client sent, in an id or an argument) is written with
    JSON's \\u escapes instead, which every JSON reader decodes."""
    text = json.dumps(reply, ensure_ascii=False)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(reply)
    return text


def serve(lines: Iterable[bytes], write: Callable[[str], None], context: Context) -> None:
    """Answer every line until the input ends: each answer one line of JSON, no embedded newline. No line
    ends the session: a defect in answering one is an internal error, and the next line is read."""
    context.root.mkdir(parents=True, exist_ok=True)
    initialized = False
    for line in lines:
        try:
            reply, initialized = answer(context, line, initialized)
        except Exception as error:  # a defect of TrialLedger outside a tool: told, and the connection kept
            reply = _error(None, "internal_error", {"detail": f"{type(error).__name__}: {error}"})
        if reply is not None:
            write(wire(reply))


def stdio_streams() -> tuple[Iterator[bytes], Callable[[str], None]]:
    """The process's standard input lines and a writer of protocol lines. Standard output is kept for the
    protocol alone: its descriptor is duplicated for the writer, and descriptor 1 then points at standard
    error, so anything else the process writes (a print, a child process) cannot corrupt the stream."""
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "wb")
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

    def write(text: str) -> None:
        protocol.write(text.encode("utf-8") + b"\n")
        protocol.flush()

    return iter(sys.stdin.buffer.readline, b""), write
