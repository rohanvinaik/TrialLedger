"""The search preview (refine-landscape-record 6.1, design §5a): the resolved search shown before anything is
gathered.

`preview` takes a run exactly as far as `operate.run` takes it before the registry is read (both begin
with `operate.fix_scope`): the request
checked and kept (`request.json`; a folder holding another request is refused), the request resolved
through RxNav and written (`resolution.json`, the record's scope) and its registry query fixed (`scope.json`),
and then it stops. No registry request is made, not even for the registry's version. Running the same
request in the same folder afterwards gathers against that fixed scope: `operate.run` reads a scope.json
already written and never resolves the request again.

`scope_words` says the resolved search in plain words for the person: each drug class with every subclass it
includes and the members searched (each with the subclass it is reached through), each drug with the names it
is searched by, each disease class with what the registry includes under it, the other filters in the
registry's own words for its codes, and the exact search sent; or why the search cannot be resolved. A
disease class is searched through the registry's MeSH tree (a trial whose condition MeSH term is the class or
has it as an ancestor), so the diseases under it are the registry's to include: no source the run reads lists
them, and the words say so rather than list them.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from TrialLedger import classes as rx
from TrialLedger import coverage
from TrialLedger.contract import DISPLAY
from TrialLedger.operate import RESOLUTION_NAME, Outcome, fix_scope, stop_advice
from TrialLedger.steps import NEXT_NAME

PREVIEWED = "previewed"
PREVIEW_ADVICE = (
    "Nothing has been gathered yet. Show the person this search: each drug class with its subclasses and "
    "members, each drug with its names, each disease class, and the exact search. To gather it, run the "
    "same command again without --preview (with the tools: call landscape with the same run and request): it "
    "reads the trials of exactly this search. To change the search, start a new run folder (--run) with the "
    "changed request."
)
# How each name a drug is searched by came to be, in words.
NAME_ORIGINS = {
    "request": "as asked",
    coverage.ADDITION_ORIGIN: coverage.ADDITION_WORDS,
    "rxclass_member": "as the class lists it",
    "rxnorm_concept": "RxNorm's name for it",
    "rxnorm_ingredient": "its ingredient, the same molecule",
}
FILTER_WORDS = {
    "phase": ("Phase", "Phase"),
    "status": ("Status", "Status"),
    "study_type": ("Study type", "StudyType"),
}


def _name_words(names: list[list[str]]) -> str:
    """A drug's searched names, each with how it came to be."""
    return "; ".join(f"{name} ({NAME_ORIGINS.get(origin, origin)})" for name, origin in names)


def _class_lines(slot: str, expansions: list[dict[str, Any]]) -> list[str]:
    """The lines of one drug class slot (or a mechanism's classes): the class, its subclasses, its members."""
    lines: list[str] = []
    names = {e["drug"]: e for e in expansions if e["slot"] == slot and e["kind"] == "drug_names"}
    for expansion in expansions:
        if expansion["slot"] != slot:
            continue
        if expansion["kind"] == "crosswalk":
            for target, class_id, label, relation, member, *_ in expansion["rows"]:
                kept = (
                    "expanded into its members" if member else "not expanded (it does not entail membership)"
                )
                lines.append(f"  {target}: ATC class {label} ({class_id}), {relation}; {kept}")
        elif expansion["kind"] == "class" and expansion["code"] == "found":
            class_id, label, _kind = expansion["classes"][0]
            lines.append(f"  Class: {label} ({expansion['source']}, {class_id})")
        elif expansion["kind"] == "class" and expansion["code"] == "class_candidates":
            lines.append("  Source-catalog candidates (navigation only; none selected):")
            for class_id, label, class_type in expansion["candidates"]:
                lines.append(
                    f"    {label} — ID {class_id}, source {expansion['source']} (RxClass type {class_type})"
                )
        elif expansion["kind"] == "subclass_attribution" and expansion["code"] == "found":
            subclasses = expansion["subclasses"]
            if subclasses:
                lines.append(f"  It includes {len(subclasses)} subclass(es):")
            for sub_id, label, _parent, excluded in subclasses:
                lines.append(f"    {label} ({sub_id}){', left out as asked' if excluded else ''}")
            searched = [row for row in expansion["members"] if row[5]]
            dropped = [row for row in expansion["members"] if not row[5]]
            lines.append(f"  Members searched ({len(searched)}):")
            for _rxcui, name, _tty, _relations, via, _kept in searched:
                through = f", through {', '.join(pair[1] for pair in via)}" if via else ""
                found = names.get(name)
                words = _name_words(found["names"]) if found else name
                lines.append(f"    {name}{through}: searched as {words}")
                for candidate, _origin, relation in found["candidates"] if found else []:
                    lines.append(f"      shown, not searched: {candidate} ({relation})")
            if dropped:
                left = ", ".join(row[1] for row in dropped)
                lines.append(f"  Members left out (reached only through a subclass left out): {left}")
    for added in (
        e for e in expansions if e["slot"] == slot and e.get("source_origin") == coverage.ADDITION_ORIGIN
    ):
        note = " (RxNorm does not hold it)" if added["code"] == "not_in_rxnorm" else ""
        lines.append(
            f"  Added by the person, not supplied by RxNav: {added['drug']}{note}: searched as "
            f"{_name_words(added['names']) or 'no name yet'}"
        )
    return lines


def _slot_lines(slot: dict[str, Any], expansions: list[dict[str, Any]]) -> list[str]:
    """The lines of one slot of the request, as resolved."""
    name, value = slot["slot"], slot["value"]
    if name in ("drug_class", "mechanism"):
        if name == "mechanism":
            head = f"Mechanism: {value}, through the sourced crosswalk"
        else:
            asked = value.get("name", value.get("id")) if isinstance(value, dict) else value
            source = value.get("source") if isinstance(value, dict) else ""
            head = (
                f"Drug class asked for: {asked} ({source}), with every subclass it includes unless left out"
            )
        return [head, *_class_lines(name, expansions)]
    if name == "class_drug_additions":
        return []  # said with the class it extends (_class_lines)
    if name == "drug":
        lines = ["Drugs, each searched by every name RxNorm gives it:"]
        for expansion in expansions:
            if expansion["slot"] == "drug" and expansion["kind"] == "drug_names":
                words = _name_words(expansion["names"]) or "no name yet"
                note = " (RxNorm does not hold it)" if expansion["code"] == "not_in_rxnorm" else ""
                lines.append(f"  {expansion['drug']}{note}: searched as {words}")
        return lines
    if name == "condition_class":
        return [
            f"Disease class: {value}, with every disease the registry's MeSH tree files under it (a trial "
            f"whose condition MeSH term is {value} or has it as an ancestor); the registry decides which "
            "diseases those are, and no source this run reads lists them"
        ]
    if name == "condition":
        return [f"Condition: {value}, as the registry's own condition search reads it"]
    if name in FILTER_WORDS:
        label, dictionary = FILTER_WORDS[name]
        values = value if isinstance(value, list) else [value]
        words = ", ".join(DISPLAY[dictionary].get(item, str(item)) for item in values)
        return [f"{label}: {words}"]
    if name == "start_from":
        return [f"Started on or after {value}"]
    if name == "start_to":
        return [f"Started on or before {value}"]
    pairs = "; ".join(f"{key}={text}" for key, text in value.items()) if isinstance(value, dict) else value
    return [f"Other registry search settings, sent as given: {pairs}"]


def scope_words(scope: Any) -> list[str]:
    """The resolved search in plain words, line by line, for the person (pure — pinned).

    `scope` is request.resolve_scope's (resolution.json). A scope that is not an object, or names no code,
    is said to be no resolved search. Otherwise each slot of the request in order (_slot_lines), then by its
    code:
      resolved         — the exact search sent to the registry, each parameter as name=value;
      awaiting_lookups — how many RxNav answers are still awaited before it resolves;
      unresolved       — that nothing is searched, and each stop's slot, code and advice;
      refused          — that the request is refused, with request_problems' code and what it concerns.
    The RxNav release the expansions rest on is named when one was read.
    """
    if not isinstance(scope, dict) or "code" not in scope:
        return ["No resolved search: the scope holds no resolution."]
    code = scope["code"]
    if code == "refused":
        check, concerned = scope.get("check", ["", []])
        return [f"The request is refused as written ({check}: {', '.join(map(str, concerned))})."]
    expansions = scope.get("expansions", [])
    lines: list[str] = []
    for slot in scope.get("slots", []):
        lines += _slot_lines(slot, expansions)
    lines += coverage.coverage_words(scope.get("coverage"))
    alternate_code, alternate = coverage.alternate_query(scope)
    if alternate_code == "ok":
        lines.append(
            "Not run: the same search with the disease class replaced by the registry's condition-text "
            f"search for {alternate['query.cond']}, every other filter unchanged, can be "
            "compared with this one: `trialledger landscape --run <this run folder> "
            "--compare-condition-text` (add --compare-plan to see its exact query and budget first); it "
            "reads "
            "identifiers only, within this run's acquisition budget."
        )
    release = scope.get("release", ["", "", ""])
    if release[0] == "found":
        lines.append(f"Drug names and classes as RxNav's release {release[1]} gives them")
    if code == "resolved":
        lines.append("The exact search sent to the registry:")
        lines += [f"  {name}={value}" for name, value in scope["query"].items()]
    elif code == "awaiting_lookups":
        lines.append(f"Not resolved yet: {len(scope.get('pending', []))} RxNav answer(s) still awaited.")
    else:
        lines.append("The search cannot be resolved, so nothing is searched:")
        for slot, stop, detail in scope.get("stops", []):
            said = f" ({json.dumps(detail, ensure_ascii=False)})" if detail else ""
            lines.append(f"  {slot}: {stop}{said} — {stop_advice(stop)}")
        if any(stop == "class_candidates" for _slot, stop, _detail in scope.get("stops", [])):
            lines.append(
                "To search a candidate, start a new run and pass its ID with "
                "--drug-class-id <ID> and the same --class-source. No candidate was selected."
            )
    return lines


def _note(folder: Path, mode: str, detail: str) -> None:
    """next.json at a preview's end: in relay mode it says the search is previewed and names no fetch (so
    save_fetch writes nothing more); direct mode keeps none."""
    target = folder / NEXT_NAME
    if mode != "relay":
        target.unlink(missing_ok=True)
        return
    document: dict[str, Any] = {"status": PREVIEWED, "detail": detail, "run_folder": str(folder.resolve())}
    document |= {"instructions": PREVIEW_ADVICE, "fetches": []}
    staging = folder / f".{NEXT_NAME}.partial"
    staging.write_bytes((json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    os.replace(staging, target)


def preview(
    folder: Path,
    request: Any,
    mode: str,
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]] = rx.http_get,
    sleep: Callable[[float], None] = time.sleep,
    progress: Callable[[str], None] | None = None,
) -> Outcome:
    """Resolve `request` in `folder`, fix its scope and say it in words, reading no study (module docstring).

    The run's own opening, operate.fix_scope (the request refused, or kept in request.json, a folder holding
    another request refused; the scope read when scope.json already fixes it, else resolved round by round, in
    relay mode the RxNav requests named in next.json for the agent to fetch, and its registry query fixed).
    Ends `previewed`, with scope_words as its detail (operate.run_exit reads it 0), or as the run would end at
    that step. `progress` is operate.fix_scope's (it says nothing when none is given).
    """
    given = {} if progress is None else {"progress": progress}
    outcome, _request, scope = fix_scope(folder, request, mode, get=get, sleep=sleep, **given)
    if outcome is not None:
        resolution = folder / RESOLUTION_NAME
        if outcome.status == "scope_stopped" and resolution.is_file():
            saved_scope = json.loads(resolution.read_text(encoding="utf-8"))
            if any(stop == "class_candidates" for _slot, stop, _detail in saved_scope.get("stops", [])):
                return Outcome(outcome.status, "\n".join(scope_words(saved_scope)), outcome.advice)
        return outcome
    detail = "\n".join(scope_words(scope))
    _note(folder, mode, detail)
    return Outcome(PREVIEWED, detail, PREVIEW_ADVICE)
