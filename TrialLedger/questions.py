"""Targeted questions: one specific question, closed options, a bounded source envelope.

Specified in openspec/changes/add-targeted-questions. The symbolic system decides which questions exist and
what each may see; a model only answers. A question's envelope is deterministic: the target piece of
eligibility text with its offsets, the section heading it sits under, the scoping lines between that heading
and it (a cohort line such as "Cohort B only:"), the stem it continues (a previous piece ending in a colon),
and its neighbours when an explicit "and"/"or" joins them. It never resolves those relationships; it hands
over the text that bears on them. An envelope over its budget is refused, never truncated. An answer is
validated deterministically: its verdict is one of the closed options and its quote lies verbatim in the
envelope (a location check, not entailment).

The kinds (design.md Decision 6), each one thing asked: `atom_claim` (one typed atom of one criterion);
`untyped_criterion` (a criterion no bank typed: which of the banks' concept instances it states, each with a
span, or none, or out_of_taxonomy with a span); `outcome_endpoint` (an endpoint class claimed of an outcome's
own measure text); `outcome_time_point` (a time point of an outcome's own time frame: "up to N" is claimed
as the end of an observation window, the founder's rule; any other time point is claimed only as "a time
point at N", never given a role the text does not mark);
`intervention_target` (a target an intervention's own registry entry states). An outcome's or intervention's
envelope is its own field's text, verbatim, with the one field that names it (the measure of a time frame, the
name of an entry) as context; never the rest of the record. RxClass assignments are never asked: audit.py
checks them against the kept RxClass answer.
"""

from __future__ import annotations

import hashlib
import json
import re

from TrialLedger.banks import (
    AGENT_WORDS,
    ANALYTES,
    CONDITIONS,
    EXTENT_WORDS,
    GENES,
    HISTOLOGY,
    SETTING_WORDS,
)

ENVELOPE_BUDGET = 4000  # bytes of envelope text; a larger envelope is refused, never cut
ATOM_CLAIM_OPTIONS = (
    "supported",
    "wrong_value",
    "wrong_polarity_or_modality",
    "unsupported",
    "insufficient_context",
)
# An endpoint class of an outcome, or a target an intervention's entry states: no section, so no polarity.
FIELD_CLAIM_OPTIONS = ("supported", "wrong_value", "unsupported", "insufficient_context")
TIME_POINT_OPTIONS = ("supported", "wrong_value", "wrong_role", "unsupported", "insufficient_context")
# The concept instances the banks can type, named as their atoms name them: a concept whose values are a
# closed vocabulary is one instance per value ("condition:hiv", "lab:platelets"), any other concept is one
# instance ("ecog_ps", "age"); each biomarker is its own concept ("biomarker:EGFR").
_PER_VALUE = {
    "prior_agent": AGENT_WORDS,
    "extent": EXTENT_WORDS,
    "setting_word": SETTING_WORDS,
    "resection": {"resected": "", "resectable": ""},
    "lab": ANALYTES,
    "condition": CONDITIONS,
    "histology": HISTOLOGY,
}
CONCEPT_OPTIONS = (
    "ecog_ps",
    *(f"biomarker:{gene}" for gene in GENES),
    "prior_lines",
    "stage",
    "organ_function_unspecified",
    "age",
    *(f"{concept}:{value}" for concept, table in _PER_VALUE.items() for value in table),
)
UNTYPED_ALONE = ("none", "insufficient_context")  # each only as the one instance of an answer
UNTYPED_OPTIONS = (*CONCEPT_OPTIONS, "out_of_taxonomy", *UNTYPED_ALONE)
# "up to N", "up to approximately N": the end of a window over which events are counted (the founder's rule).
_WINDOW_BEFORE = re.compile(r"\bup\s+to\s+(?:(?:approximately|approx\.?|about|around|~)\s*)?$", re.IGNORECASE)
_JOIN_AT_END = re.compile(r"(?:\bor|\band|\band/or|;\s*or|;\s*and)\s*$", re.IGNORECASE)
_JOIN_AT_START = re.compile(r"^\W*(?:or|and|and/or)\b", re.IGNORECASE)

Piece = tuple[str, str, int, int]  # kind, section, start, end (criteria.itemize)


def envelope(text: str, pieces: list[Piece], index: int, budget: int = ENVELOPE_BUDGET) -> tuple[str, dict]:
    """The envelope of piece `index` of an itemized eligibility text (pure — pinned).

    Returns ("ok", envelope) or ("envelope_over_budget", {}) or ("not_a_criterion", {}). The envelope holds
    the target (text, start, end, section), the nearest heading before it, the scoping lines (prose pieces
    ending in a colon) between that heading and it, the stem (the piece just before it, when that piece ends
    in a colon), and the siblings (the criteria just before and after it, when an explicit "and"/"or" joins
    them).
    """
    kind, section, start, end = pieces[index]
    if kind != "criterion":
        return "not_a_criterion", {}
    target = text[start:end]
    heading_at = next((i for i in range(index - 1, -1, -1) if pieces[i][0] == "heading"), -1)
    headings = [text[pieces[heading_at][2] : pieces[heading_at][3]]] if heading_at >= 0 else []
    scoping = [
        text[s:e]
        for k, _sec, s, e in pieces[heading_at + 1 : index]
        if k == "prose" and text[s:e].rstrip().endswith(":")
    ]
    previous = pieces[index - 1] if index > 0 else None
    following = pieces[index + 1] if index + 1 < len(pieces) else None
    stem = ""
    if previous and previous[0] == "criterion" and text[previous[2] : previous[3]].rstrip().endswith(":"):
        stem = text[previous[2] : previous[3]]
    siblings = []
    if previous and previous[0] == "criterion" and not stem:
        before = text[previous[2] : previous[3]]
        if _JOIN_AT_END.search(before) or _JOIN_AT_START.search(target):
            siblings.append(before)
    if following and following[0] == "criterion":
        after = text[following[2] : following[3]]
        if _JOIN_AT_END.search(target) or _JOIN_AT_START.search(after):
            siblings.append(after)
    held = {
        "target": {"text": target, "start": start, "end": end, "section": section},
        "headings": headings,
        "scoping": scoping,
        "stem": stem,
        "siblings": siblings,
    }
    size = sum(len(part.encode("utf-8")) for part in [target, *headings, *scoping, stem, *siblings])
    if size > budget:
        return "envelope_over_budget", {}
    return "ok", held


def atom_claim(atom: tuple, section: str) -> str:
    """The claim one typed atom makes about its criterion, in words a reader checks against the text."""
    _bank, concept, values, params, _s, _e = atom
    detail = "; ".join(
        f"{name} {value}" for name, value in params if name not in ("text_polarity", "modality")
    )
    if concept == "condition":
        # a mention-type atom names a condition, not a value: say it in words, so no reader grades the
        # concept's name as if it were a value the text should state (the auditor pilot, 2026-11-01)
        stated = " or ".join(value.replace("_", " ") for value in values) + (f" ({detail})" if detail else "")
        if section == "permitted":
            return f"This criterion permits, without requiring, participants who have: {stated}"
        if section == "exclusion":
            return f"This exclusion criterion excludes participants who have: {stated}"
        if section == "inclusion":
            return f"This inclusion criterion requires participants to have: {stated}"
        return f"This criterion (no inclusion or exclusion heading) names: {stated}"
    stated = f"{concept} = {' | '.join(values)}" + (f" ({detail})" if detail else "")
    if section == "permitted":
        return f"This criterion permits, without requiring, participants to have: {stated}"
    if section == "exclusion":
        return f"This exclusion criterion excludes participants with: {stated}"
    if section == "inclusion":
        return f"This inclusion criterion requires participants to have: {stated}"
    return f"This criterion (no inclusion or exclusion heading) states: {stated}"


def field_envelope(
    field: str, text: str, context: list[tuple[str, str]], budget: int = ENVELOPE_BUDGET
) -> tuple[str, dict]:
    """The envelope of one record field's own text (pure — pinned).

    Returns ("ok", envelope), ("empty_field", {}) when the field holds no text, or
    ("envelope_over_budget", {}) when the field and its context together exceed `budget` bytes (refused, never
    cut). The envelope has the eligibility envelope's keys, so one validation reads both: the target is the
    field's text verbatim (start 0, end its length, and its field path), headings, scoping, stem and siblings
    are empty, and `context` holds the named fields given, each verbatim (the measure a time frame belongs to,
    the name of an intervention entry).
    """
    if not text.strip():
        return "empty_field", {}
    held = {
        "target": {"text": text, "start": 0, "end": len(text), "field": field},
        "headings": [],
        "scoping": [],
        "stem": "",
        "siblings": [],
        "context": [{"field": name, "text": value} for name, value in context],
    }
    size = sum(len(part.encode("utf-8")) for part in [text, *(value for _name, value in context)])
    if size > budget:
        return "envelope_over_budget", {}
    return "ok", held


def time_point_role(frame: str, point: str) -> str:
    """The role a time frame gives one of its time points, as `banks.time_points` names it ("24 week")
    (pure — pinned).

    "window" when the first statement of that number and unit follows "up to" (optionally "approximately",
    "about", "around" or "~"): the end of an observation window, not a scheduled measurement (the founder's
    rule); "unmarked" when it is stated otherwise (no role is read: "at 12 weeks", "within 6 months" and a
    listed time are not told apart here); "not_stated" when the frame does not state it as number then unit.
    """
    amount, _, unit = point.partition(" ")
    if not amount or not unit:
        return "not_stated"
    found = re.search(rf"(?<![\d.]){re.escape(amount)}\s*{re.escape(unit)}s?\b", frame, re.IGNORECASE)
    if not found:
        return "not_stated"
    return "window" if _WINDOW_BEFORE.search(frame[: found.start()]) else "unmarked"


def concept_instances(concept: str, values: tuple[str, ...]) -> list[str]:
    """The concept instances one typed atom states, named as the untyped-criterion options name them
    (pure — pinned): one per value ("condition:hiv") for a concept whose values are a closed vocabulary
    (prior_agent, extent, setting_word, resection, lab, condition, histology), else the concept alone, once,
    whatever its values ("ecog_ps", "age", "biomarker:EGFR")."""
    if concept in _PER_VALUE:
        return [f"{concept}:{value}" for value in values]
    return [concept]


def endpoint_claim(endpoint: str) -> str:
    """The claim an endpoint class makes of an outcome's measure."""
    return f"This outcome measure is an endpoint of the class: {endpoint.replace('_', ' ')}"


def time_point_claim(point: str, role: str) -> str:
    """The claim a time point in its role makes of an outcome's time frame: a window ("up to N") is claimed as
    one; an unmarked or not-stated point is claimed only as a time point, with no role."""
    if role == "window":
        return f"This time frame states {point}(s) as the end of an observation window (up to that time)"
    return f"This time frame states a time point at {point}(s)"


def target_claim(drug: str, target: str) -> str:
    """The claim a record-stated target makes of an intervention's own entry."""
    return (
        f"This intervention's own entry states that {drug} itself is a drug of the class named by: {target}"
    )


def untyped_claim() -> str:
    """The one question an untyped criterion is asked."""
    return (
        "Which of the option concepts does this criterion state? One instance per concept stated, each with "
        "its verbatim span of the criterion; out_of_taxonomy with its span for a requirement no option "
        "names; none if it states no requirement."
    )


def question(kind: str, target: dict, held: dict, options: tuple[str, ...]) -> dict:
    """A question object with its id: a hash of everything the model will see."""
    body = {"kind": kind, "target": target, "envelope": held, "options": list(options)}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"id": digest[:16], **body}


def answer_schema(options: tuple[str, ...]) -> dict:
    """The JSON schema an answer must satisfy: one closed verdict and the verbatim quote it rests on."""
    return {
        "type": "object",
        "properties": {"verdict": {"type": "string", "enum": list(options)}, "quote": {"type": "string"}},
        "required": ["verdict", "quote"],
        "additionalProperties": False,
    }


def validate_answer(raw: str, options: tuple[str, ...], held: dict) -> tuple[str, str, str]:
    """A model's raw answer, checked (pure — pinned).

    Returns (code, verdict, quote): ("ok", verdict, quote) when the answer is a JSON object with exactly a
    verdict among `options` and a quote; the quote must lie verbatim in the envelope's text unless the verdict
    is "insufficient_context" or "unsupported" (which may quote nothing). Otherwise a named audit error with
    empty verdict and quote: "malformed", "unknown_verdict", "quote_not_in_envelope".
    """
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return "malformed", "", ""
    if not isinstance(answer, dict) or set(answer) != {"verdict", "quote"}:
        return "malformed", "", ""
    verdict, quote = answer["verdict"], answer["quote"]
    if not isinstance(verdict, str) or not isinstance(quote, str):
        return "malformed", "", ""
    if verdict not in options:
        return "unknown_verdict", "", ""
    if quote.strip() and not quote_in(quote, envelope_texts(held)):
        return "quote_not_in_envelope", "", ""
    if not quote.strip() and verdict not in ("insufficient_context", "unsupported"):
        return "quote_not_in_envelope", "", ""
    return "ok", verdict, quote


_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>^|~=])")
_ELLIPSIS = re.compile(r"(?:\.\.\.|…)\s*$")


def normal_text(text: str) -> str:
    """Text as a quote is compared (pure — pinned): markdown backslash escapes removed ("\\>" is ">"),
    surrounding quotation marks dropped, runs of whitespace one space, ends trimmed."""
    return " ".join(_ESCAPE.sub(r"\1", text).strip().strip("\"'“”‘’").split())


def quote_in(quote: str, texts: list[str]) -> bool:
    """Whether a model's quote lies in the envelope (pure — pinned): verbatim after `normal_text` on both
    sides; a quote ending in "..." or "…" is a prefix (what precedes the marks must lie in a text). An empty
    quote, or one that is only the marks, lies nowhere."""
    prefix = bool(_ELLIPSIS.search(quote))
    wanted = normal_text(_ELLIPSIS.sub("", quote) if prefix else quote)
    return bool(wanted) and any(wanted in normal_text(text) for text in texts)


def envelope_texts(held: dict) -> list[str]:
    """Every text an envelope holds: its target, headings, scoping lines, stem, siblings and named context."""
    context = [part["text"] for part in held.get("context", [])]
    return [
        held["target"]["text"],
        *held["headings"],
        *held["scoping"],
        held["stem"],
        *held["siblings"],
        *context,
    ]


def instances_schema(options: tuple[str, ...]) -> dict:
    """The JSON schema an untyped-criterion answer must satisfy: one or more instances, each a closed option
    and the verbatim span it rests on."""
    instance = {
        "type": "object",
        "properties": {"option": {"type": "string", "enum": list(options)}, "quote": {"type": "string"}},
        "required": ["option", "quote"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"instances": {"type": "array", "items": instance, "minItems": 1}},
        "required": ["instances"],
        "additionalProperties": False,
    }


def validate_instances(raw: str, options: tuple[str, ...], held: dict) -> tuple[str, list[tuple[str, str]]]:
    """A model's raw answer to an untyped-criterion question, checked (pure — pinned).

    Returns ("ok", [(option, quote), ...]) when the answer is a JSON object with exactly a non-empty list of
    instances, each exactly an option among `options` and a quote, no instance repeated; a concept or
    out_of_taxonomy instance quotes a span of the target criterion itself, verbatim; "none" and
    "insufficient_context" stand alone, and may quote nothing (a quote they give must lie in the envelope).
    Otherwise a named audit error with no instances: "malformed", "unknown_verdict", "duplicate_instance",
    "exclusive_option_combined", "quote_not_in_target", "quote_not_in_envelope".
    """
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return "malformed", []
    if not isinstance(answer, dict) or set(answer) != {"instances"}:
        return "malformed", []
    listed = answer["instances"]
    if not isinstance(listed, list) or not listed:
        return "malformed", []
    found: list[tuple[str, str]] = []
    for item in listed:
        if not isinstance(item, dict) or set(item) != {"option", "quote"}:
            return "malformed", []
        option, quote = item["option"], item["quote"]
        if not isinstance(option, str) or not isinstance(quote, str):
            return "malformed", []
        if option not in options:
            return "unknown_verdict", []
        found.append((option, quote.strip()))
    if len(set(found)) != len(found):
        return "duplicate_instance", []
    alone = [option for option, _quote in found if option in UNTYPED_ALONE]
    if alone and len(found) > 1:
        return "exclusive_option_combined", []
    for option, quote in found:
        if option in UNTYPED_ALONE:
            if quote and not any(quote in part for part in envelope_texts(held)):
                return "quote_not_in_envelope", []
        elif not quote or quote not in held["target"]["text"]:
            return "quote_not_in_target", []
    return "ok", found


def untyped_reading(found: list[tuple[str, str]]) -> str:
    """What a validated untyped-criterion answer says of the criterion (pure — pinned).

    "insufficient_context" or "no_requirement" (none) when that is the answer; "concept_stated" when any
    instance names a concept of the banks (a candidate miss: whether a bank declined it or silently missed it
    is the adjudicator's call); otherwise "out_of_taxonomy" (only requirements no option names: counted apart,
    never an engine error in this wave).
    """
    options = {option for option, _quote in found}
    if "insufficient_context" in options:
        return "insufficient_context"
    if "none" in options:
        return "no_requirement"
    if options - {"out_of_taxonomy"}:
        return "concept_stated"
    return "out_of_taxonomy"
