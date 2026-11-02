"""Source-backed drug identities and classes from the National Library of Medicine.

Each recorded name is looked up exactly in RxNorm. Its canonical concept, term type and related ingredients
remain separate from the classes RxClass asserts about a named subject. Reporting keeps the requests,
release and every source assertion; aliases cannot supply a missing identity or transfer a component's class
to a brand, precise ingredient, biosimilar or combination. Related entities are not silently made identical.
The same source parsers support search resolution and the separate symbolic design layer.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

RXCLASS = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json"
QUERIES = (("DAILYMED", "has_epc"), ("MEDRT", "has_moa"))
CACHE_NAME = "classes.json"
DRUG_TYPES = ("DRUG", "BIOLOGICAL", "GENETIC")

Class = tuple[str, str, str, str]  # (class id, class name, relation, relation source)

RXNAV = "https://rxnav.nlm.nih.gov/REST"
RXNAV_VERSION = f"{RXNAV}/version.json"
RXNORM_IDS = f"{RXNAV}/rxcui.json"
RXNORM_PROPERTIES = RXNAV + "/rxcui/{rxcui}/properties.json"
RXNORM_RELATED = RXNAV + "/rxcui/{rxcui}/related.json"
# Every class RxClass holds of one RxNorm concept, every source and relation in one answer; each query of
# QUERIES and each axis of AXES is read from it by relation_body.
RXCLASS_BY_RXCUI = f"{RXNAV}/rxclass/class/byRxcui.json"
# The axes, each its own coordinate: (relation source, relation); ATC has no relation name in RxClass.
AXES = (("ATC", ""), ("DAILYMED", "has_chemical_structure"), ("FDASPL", "has_chemical_structure"))
# The bound on RxNav requests: at most IN_FLIGHT awaiting their answers at once, and at most RATE begun in any
# second (each begun at least 1/RATE s after the one before), under NLM's published 20 a second per address.
IN_FLIGHT = 8
RATE = 15
# (class id, class name, class type, relation, relation source, subject rxcui, subject name, subject tty)
Assertion = tuple[str, str, str, str, str, str, str, str]
Concept = tuple[str, str, str]  # (rxcui, name, term type)
RESOLVED = ("ingredient", "precise_ingredient", "brand", "combination", "other_form")


def rxclass_classes(status: int, body: Any) -> tuple[str, list[Class]]:
    """The classes in one RxClass byDrugName response, or why there are none (pure — pinned).

    found        — HTTP 200 with at least one class; each (classId, className, rela, relaSource), once,
                   sorted.
    not_found    — HTTP 200 and an object without rxclassDrugInfoList (RxClass's answer for an unknown name).
    malformed    — HTTP 200 but the body is not an object, or a listed entry lacks a string id or name.
    lookup_failed — any other HTTP status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    listing = body.get("rxclassDrugInfoList")
    if listing is None:
        return "not_found", []
    entries = listing.get("rxclassDrugInfo") if isinstance(listing, dict) else None
    if not isinstance(entries, list) or not entries:
        return "malformed", []
    found: set[Class] = set()
    for entry in entries:
        item = entry.get("rxclassMinConceptItem") if isinstance(entry, dict) else None
        if not isinstance(item, dict):
            return "malformed", []
        class_id, name = item.get("classId"), item.get("className")
        if not isinstance(class_id, str) or not isinstance(name, str):
            return "malformed", []
        found.add((class_id, name, str(entry.get("rela", "")), str(entry.get("relaSource", ""))))
    return "found", sorted(found)


def drug_names(study: dict[str, Any]) -> dict[str, list[str]]:
    """Each drug, biological or genetic intervention's name, mapped to its name then its other names, in
    record order."""
    module = study.get("protocolSection", {}).get("armsInterventionsModule", {})
    names: dict[str, list[str]] = {}
    for item in module.get("interventions", []) or []:
        if isinstance(item, dict) and item.get("type") in DRUG_TYPES and isinstance(item.get("name"), str):
            others = [n for n in item.get("otherNames", []) or [] if isinstance(n, str)]
            names[item["name"]] = list(dict.fromkeys([item["name"], *others]))
    return names


def experimental_drugs(study: dict[str, Any]) -> list[str]:
    """The drug, biological and genetic names an EXPERIMENTAL arm names, by the registry's `<type label>:
    <name>` cross-reference."""
    module = study.get("protocolSection", {}).get("armsInterventionsModule", {})
    declared = drug_names(study)
    found: dict[str, None] = {}
    for arm in module.get("armGroups", []) or []:
        if not isinstance(arm, dict) or arm.get("type") != "EXPERIMENTAL":
            continue
        for reference in arm.get("interventionNames", []) or []:
            name = reference.split(": ", 1)[1] if isinstance(reference, str) and ": " in reference else None
            if name in declared:
                found.setdefault(name, None)
    return list(found)


# A lookup of many names says how far it has got every PROGRESS_EVERY names, so a long one is never silent.
PROGRESS_EVERY = 5


def progress_due(done: int, total: int) -> bool:
    """Whether a lookup says how far it has got after its `done`-th name of `total` (pure — pinned).

    True after every PROGRESS_EVERY-th name and after the last; never before the first name or past the
    total.
    """
    if done < 1 or done > total:
        return False
    return done == total or done % PROGRESS_EVERY == 0


def _quiet(_message: str) -> None:
    """Default progress sink: say nothing."""


# The rule that strips a dose or a schedule written after a drug's name before RxNav is asked about it
# (lookup_name). The registry's own intervention names carry them ("CAT-8015 20 mcg/kg", one intervention per
# dose level; "AZD9291 80 mg/40 mg"), and RxNorm holds no concept of such a name. A dose is an amount with its
# unit; a schedule word ("oral", "once daily", "QD") is stripped only after a dose. A bare number is never a
# dose ("MEDI 4736", "VP 16"), a dose form ("tablet", "injection") is never stripped, and a dose followed by
# anything else stays as written ("AZD9291 80 mg/40 mg + placebo").


def pace(now: float, free: float, interval: float) -> tuple[float, float]:
    """How long one RxNav request waits before it begins, and when the next may begin (pure — pinned).

    `now` is the clock, `free` the earliest moment the next request may begin (0.0 before the first), and
    `interval` the least time between two beginnings (1/RATE). The request begins at the later of `now` and
    `free`: returns (that moment less `now`, never negative; that moment plus `interval`).
    """
    begin = max(now, free)
    return begin - now, begin + interval


def relation_body(body: Any, source: str, rela: str) -> Any:
    """One query's share of an RxClass byRxcui answer: the answer as RxClass gives it asked with that relation
    source, and with that relation when `rela` is not "" (pure — pinned).

    Each entry of rxclassDrugInfoList.rxclassDrugInfo stated under `source` (and `rela`) is kept, in order; an
    entry that is not an object, or states no string relaSource, is kept too, so that the reading of the share
    (rxclass_classes, rxclass_assertions) names the answer malformed rather than the class absent. A share
    keeping no entry is {} (RxClass's answer when it holds no class: not_found). A body that is not an object,
    or holds no non-empty list of entries, is its own share, read as it is.
    """
    listing = body.get("rxclassDrugInfoList") if isinstance(body, dict) else None
    entries = listing.get("rxclassDrugInfo") if isinstance(listing, dict) else None
    if not isinstance(entries, list) or not entries:
        return body
    kept = [
        entry
        for entry in entries
        if not isinstance(entry, dict)
        or not isinstance(entry.get("relaSource"), str)
        or (entry["relaSource"] == source and (not rela or str(entry.get("rela", "")) == rela))
    ]
    return {"rxclassDrugInfoList": {"rxclassDrugInfo": kept}} if kept else {}


def class_route(ids_code: str, count: int) -> str:
    """Whether RxClass is asked about a name's concept, from its RxNorm identity answer (pure — pinned).

    `ids_code` is rxnorm_ids' code for the name and `count` the number of concepts it found.
    ask                 — exactly one concept: RxClass is asked for its classes (byRxcui).
    not_in_rxnorm       — RxNorm holds no concept of exactly that name.
    ambiguous_in_rxnorm — the name is exactly the name of several concepts.
    lookup_failed       — the identity request failed, so whether a class exists is not established.
    malformed           — anything else (an answer not of RxNorm's form).
    Every code but `ask` is the name's code for each class query, so a failed lookup is never "no class".
    """
    if ids_code == "found" and count == 1:
        return "ask"
    if ids_code == "found" and count > 1:
        return "ambiguous_in_rxnorm"
    return {"not_found": "not_in_rxnorm", "lookup_failed": "lookup_failed"}.get(ids_code, "malformed")


def batch_releases(answers: dict[str, Any]) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """The RxNav releases each lookup batch held in `answers` was read under, before its first request and
    after its last (pure — pinned).

    Each answer, and each answer's axes identity, that carries both `release` and `release_end` gives one
    pair ((code, release) before, (code, release) after), as rxnav_release reads version.json; each pair once,
    sorted. An answer cached before releases were asked after the last request gives none.
    """
    pairs = set()
    for answer in answers.values():
        identity = ((answer.get("axes") or {}).get("identity") or {}) if isinstance(answer, dict) else {}
        for held in (answer, identity):
            if isinstance(held, dict) and "release" in held and "release_end" in held:
                first, last = held["release"], held["release_end"]
                pairs.add(((str(first[0]), str(first[1])), (str(last[0]), str(last[1]))))
    return sorted(pairs)


def _now() -> str:
    """A retrieval time: now, in UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def ask_all(
    requests: list[tuple[str, dict[str, str]]],
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    progress: Callable[[int, int], None],
) -> list[tuple[dict[str, Any], int, Any]]:
    """Each request (URL, parameters) asked of RxNav: at most IN_FLIGHT at once (a pool of that many threads)
    and each begun at least 1/RATE s after the one before (pace), so never more than RATE in a second.
    Returns each request's warrant (URL, parameters, retrieval time), status and body in the order the
    requests are given, whatever order the answers arrive in; `progress` hears (answers in hand, requests) as
    each arrives in that order, from the caller's thread."""
    lock = threading.Lock()
    free = [0.0]

    def one(request: tuple[str, dict[str, str]]) -> tuple[dict[str, Any], int, Any]:
        url, params = request
        with lock:
            wait, free[0] = pace(monotonic(), free[0], 1 / RATE)
        sleep(wait)
        status, body = get(url, params)
        return {"url": url, "params": params, "retrieved": _now()}, status, body

    out: list[tuple[dict[str, Any], int, Any]] = []
    with ThreadPoolExecutor(max_workers=IN_FLIGHT) as pool:
        for answer in pool.map(one, requests):
            out.append(answer)
            progress(len(out), len(requests))
    return out


def _said(progress: Callable[[str], None], words: str, unit: str) -> Callable[[int, int], None]:
    """A round's progress: "<words> for <done> of <total> <unit>" when progress_due; nothing for a round
    without words (the release's single request)."""

    def heard(done: int, total: int) -> None:
        if words and progress_due(done, total):
            progress(f"{words} for {done} of {total} {unit}")

    return heard


def _share(route: str, status: int, body: Any, source: str, rela: str, reader: Callable) -> tuple[str, list]:
    """One query's reading of a name's classes: `reader` (rxclass_classes or rxclass_assertions) over the
    query's share of its concept's RxClass answer (relation_body) when RxClass was asked (class_route "ask"),
    else the route's code and nothing."""
    return reader(status, relation_body(body, source, rela)) if route == "ask" else (route, [])


def _ask_rxnav(
    names: list[str],
    with_axes: set[str],
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    progress: Callable[[str], None],
) -> dict[str, dict[str, Any]]:
    """Each recorded name's RxNorm and RxClass answers, fetched once per distinct request.

    Exact RxNorm identity is asked for every complete recorded name, without normalization or word stripping.
    Names of with_axes also retain concept properties and related ingredients. The same RxClass byRxcui
    response supplies EPC, MoA, ATC and chemical-structure assertions with their source subjects. Requests,
    retrieval times and the releases before and after the batch remain with their evidence.
    """

    def ask(
        keys: list[str], requests: list, words: str, unit: str
    ) -> dict[str, tuple[dict[str, Any], int, Any]]:
        heard = _said(progress, words, unit)
        answered = ask_all(requests, get=get, sleep=sleep, monotonic=monotonic, progress=heard)
        return dict(zip(keys, answered, strict=True))

    def release_of(asked: tuple[dict[str, Any], int, Any]) -> list[Any]:
        return [*rxnav_release(asked[1], asked[2]), asked[0]]

    release = release_of(ask(["release"], [(RXNAV_VERSION, {})], "", "")["release"])
    asked_as = {name: ("as_given", name) for name in names}
    stems = sorted({stem for _rule, stem in asked_as.values()})
    found = ask(
        stems,
        [(RXNORM_IDS, {"name": stem, "search": "0"}) for stem in stems],
        "RxNorm identity asked of RxNav",
        "drug names",
    )
    ids = {stem: (warrant, rxnorm_ids(status, body)) for stem, (warrant, status, body) in found.items()}
    single = {
        stem: held[1][0] for stem, (_, held) in ids.items() if class_route(held[0], len(held[1])) == "ask"
    }
    axes_stems = {asked_as[name][1] for name in with_axes}
    described = sorted({rxcui for stem, rxcui in single.items() if stem in axes_stems})
    properties = ask(
        described,
        [(RXNORM_PROPERTIES.format(rxcui=rxcui), {}) for rxcui in described],
        "RxNorm term types asked of RxNav",
        "concepts",
    )
    concepts = {rxcui: (w, rxnorm_concepts(status, body)) for rxcui, (w, status, body) in properties.items()}
    combined = sorted(
        rxcui
        for rxcui, (_, (code, held)) in concepts.items()
        if code == "found" and len(held) == 1 and held[0][2] != "IN"
    )
    related = ask(
        combined,
        [(RXNORM_RELATED.format(rxcui=rxcui), {"tty": "IN"}) for rxcui in combined],
        "ingredients asked of RxNav",
        "concepts",
    )
    parts = {rxcui: (w, rxnorm_concepts(status, body)) for rxcui, (w, status, body) in related.items()}
    classed = sorted(set(single.values()))
    classes = ask(
        classed,
        [(RXCLASS_BY_RXCUI, {"rxcui": rxcui}) for rxcui in classed],
        "drug classes asked of RxNav",
        "RxNorm concepts",
    )
    release_end = release_of(ask(["release"], [(RXNAV_VERSION, {})], "", "")["release"])
    progress(
        f"RxNav answered {2 + len(stems) + len(described) + len(combined) + len(classed)} requests about "
        f"{len(names)} drug names ({len(stems)} names asked, {len(classed)} RxNorm concepts classed)"
    )
    out = {}
    for name in names:
        rule, stem = asked_as[name]
        identity_warrant, held = ids[stem]
        route = class_route(held[0], len(held[1]))
        rxcui = single.get(stem, "")
        class_warrant, status, body = classes[rxcui] if rxcui else (identity_warrant, 0, None)
        per_query = {
            f"{source}:{rela}": _share(route, status, body, source, rela, rxclass_classes)
            for source, rela in QUERIES
        }
        answer: dict[str, Any] = {
            "asked_as": stem,
            "rule": rule,
            "codes": {key: code for key, (code, _) in per_query.items()},
            "classes": sorted({c for _, found_classes in per_query.values() for c in found_classes}),
            "retrieved": _now(),
            "requests": [identity_warrant, *([class_warrant] if rxcui else [])],
            "release": list(release),
            "release_end": list(release_end),
        }
        if name in with_axes:
            concept = concepts.get(rxcui, (None, ("not_asked", [])))
            ingredients = parts.get(rxcui, (None, ("not_asked", [])))
            asked = [identity_warrant, *(w for w, _ in (concept, ingredients) if w is not None)]
            axes: dict[str, Any] = {
                "identity": {
                    "ids": list(held),
                    "concept": list(concept[1]),
                    "ingredients": list(ingredients[1]),
                    "requests": asked,
                    "release": list(release),
                    "release_end": list(release_end),
                }
            }
            for source, rela in (*QUERIES, *AXES):
                code, assertions = _share(route, status, body, source, rela, rxclass_assertions)
                axes[axis_key(source, rela)] = {
                    "code": code,
                    "assertions": assertions,
                    "request": class_warrant,
                    "release": list(release),
                }
            answer["axes"] = axes
        out[name] = answer
    return out


def http_get(url: str, params: dict[str, str]) -> tuple[int, Any]:
    """One GET; a transport error is status 0, never an exception or an empty answer."""
    try:
        response = httpx.get(url, params=params, timeout=30.0)
    except httpx.HTTPError:
        return 0, None
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


# A live query (`trialledger resolve`) holds no folder: its RxClass answers persist in the user's cache.
USER_CACHE = Path.home() / ".cache" / "trialledger" / CACHE_NAME
CACHE_SETTING = "TRIALLEDGER_CACHE"  # the environment variable that names another cache


def cache_location(setting: str | None, is_folder: bool) -> tuple[str, str]:
    """Where a live run keeps its RxClass and RxNav answers, from TRIALLEDGER_CACHE (pure — pinned).

    `setting` is the variable's value (None when it is not set), `is_folder` whether it names a folder that
    exists. Returns a code and the cache file's path:
      default — not set, or blank: USER_CACHE;
      folder  — a folder that exists, or a path written with a trailing "/": classes.json inside it;
      file    — anything else: that file, as named (created with its folders when first written).
    The cache's contents are the same wherever it is kept.
    """
    if setting is None or not setting.strip():
        return "default", str(USER_CACHE)
    if is_folder or setting.endswith("/"):
        return "folder", str(Path(setting) / CACHE_NAME)
    return "file", setting


def cache_path() -> Path:
    """The cache file a live run reads and extends: cache_location over TRIALLEDGER_CACHE as this
    environment sets it, "~" expanded."""
    setting = os.environ.get(CACHE_SETTING)
    expanded = os.path.expanduser(setting) if setting is not None else None
    return Path(cache_location(expanded, expanded is not None and Path(expanded).is_dir())[1])


def load_or_lookup(
    folder: Path,
    names: list[str],
    axes_names: Sequence[str] = (),
    *,
    fill_axes: bool = False,
    get=http_get,
    sleep=time.sleep,
) -> dict[str, Any]:
    """The folder's cached RxNav answers, extended by a lookup of any name not yet cached, and saved; the
    axes of `axes_names` are kept only with `fill_axes` (load_or_lookup_at)."""
    return load_or_lookup_at(
        folder / CACHE_NAME, names, axes_names, fill_axes=fill_axes, get=get, sleep=sleep
    )


def load_or_lookup_at(
    path: Path,
    names: list[str],
    axes_names: Sequence[str] = (),
    *,
    fill_axes: bool = False,
    get=http_get,
    sleep=time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[str], None] = _quiet,
) -> dict[str, Any]:
    """Retain RxNav answers at path, extending missing names and explicitly requested identity evidence.

    Every name is resolved by exact RxNorm lookup, then its single concept is queried in RxClass. fill_axes
    requests properties, related ingredients and subject-bearing class assertions for axes_names. Cached older
    answers retain their original flattened class values; missing identity/subject evidence is fetched
    separately and retained under axes, never invented from an alias. Failed and negative responses
    stay distinct. Newly saved answers are read back from the retained file, so first use and reuse have
    the same JSON representation, including nested source request objects.
    A changed release prevents extending the on-disk cache; the caller receives both releases to refuse it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    answers = cache.get("answers", {})
    missing = [n for n in dict.fromkeys([*names, *axes_names]) if n not in answers]
    held = [
        n
        for n in dict.fromkeys(axes_names)
        if n in answers
        and any(axis_key(source, rela) not in (answers[n].get("axes") or {}) for source, rela in QUERIES)
    ]
    without_axes = held if fill_axes else []
    asked = [*missing, *without_axes]
    if not asked:
        return answers
    progress(
        f"asking RxNav, the National Library of Medicine's drug vocabulary, about {len(asked)} drug names "
        f"not yet cached: each name's RxNorm identity, then the drug classes of each RxNorm concept once "
        f"(at most {IN_FLIGHT} requests at once and {RATE} a second)"
    )
    with_axes = set(axes_names) & set(asked) if fill_axes else set()
    fresh = _ask_rxnav(asked, with_axes, get=get, sleep=sleep, monotonic=monotonic, progress=progress)
    answers.update({name: fresh[name] for name in missing})
    answers.update({name: {**answers[name], "axes": fresh[name]["axes"]} for name in without_axes})
    if all(first == last for first, last in batch_releases(fresh)):
        cache = {
            "source": "NLM RxNav REST API: each name's RxNorm identity (rxcui by exact name, the name "
            "asked exactly as recorded), then RxClass byRxcui for the one concept it names, read as "
            'DAILYMED has_epc and MEDRT has_moa; each answer with its "requests" (URL, parameters, '
            'retrieval time) and the RxNav "release" it was read under, asked before the batch and again '
            'after it ("release_end"; an answer cached before 2026-11-01 holds neither, one cached before '
            '2026-11-02 no release_end and was asked by byDrugName); per name under "axes": the identity '
            "with its concept's properties and related ingredients, ATC, and has_chemical_structure from "
            "DAILYMED and FDASPL, each with its request, retrieval time and release",
            "endpoint": RXCLASS_BY_RXCUI,
            "retrieved": _now(),
            "answers": answers,
        }
        path.write_text(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        return json.loads(path.read_text(encoding="utf-8"))["answers"]
    return answers


def rxclass_assertions(status: int, body: Any) -> tuple[str, list[Assertion]]:
    """The class assertions in one RxClass byDrugName response, each with its concept (pure — pinned).

    As `rxclass_classes`, but each class keeps the concept RxClass asserts it of (`minConcept`: rxcui, name,
    term type) and its class type, because RxClass answers a brand or a salt as its ingredient: the concept is
    not always the name asked.
    found        — HTTP 200 with at least one entry; each (classId, className, classType, rela, relaSource,
                   rxcui, name, tty), once, sorted.
    not_found    — HTTP 200 and an object without rxclassDrugInfoList.
    malformed    — HTTP 200 but the body is not an object, or an entry lacks a string class id or name or a
                   concept with a string rxcui, name and term type.
    lookup_failed — any other HTTP status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    listing = body.get("rxclassDrugInfoList")
    if listing is None:
        return "not_found", []
    entries = listing.get("rxclassDrugInfo") if isinstance(listing, dict) else None
    if not isinstance(entries, list) or not entries:
        return "malformed", []
    found: set[Assertion] = set()
    for entry in entries:
        item = entry.get("rxclassMinConceptItem") if isinstance(entry, dict) else None
        subject = entry.get("minConcept") if isinstance(entry, dict) else None
        if not isinstance(item, dict) or not isinstance(subject, dict):
            return "malformed", []
        fields = [item.get("classId"), item.get("className")]
        fields += [subject.get("rxcui"), subject.get("name"), subject.get("tty")]
        if not all(isinstance(field, str) for field in fields):
            return "malformed", []
        class_id, name, rxcui, subject_name, tty = fields
        kind = str(item.get("classType", ""))
        rela, source = str(entry.get("rela", "")), str(entry.get("relaSource", ""))
        found.add((class_id, name, kind, rela, source, rxcui, subject_name, tty))
    return "found", sorted(found)


def rxnorm_ids(status: int, body: Any) -> tuple[str, list[str]]:
    """The RxNorm concepts whose name is exactly the name asked, from one rxcui.json?search=0 (pure — pinned).

    found — HTTP 200 and an idGroup listing at least one rxcui string, each once, sorted; not_found — an
            idGroup
    without rxnormId (RxNorm's answer for a name it does not hold); malformed — a body that is not an object,
    an idGroup that is not one, or a listing that is empty or holds a non-string; lookup_failed — any other
    status.
    """
    if status != 200:
        return "lookup_failed", []
    group = body.get("idGroup") if isinstance(body, dict) else None
    if not isinstance(group, dict):
        return "malformed", []
    ids = group.get("rxnormId")
    if ids is None:
        return "not_found", []
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
        return "malformed", []
    return "found", sorted(set(ids))


def rxnorm_concepts(status: int, body: Any) -> tuple[str, list[Concept]]:
    """The concepts of one RxNorm properties.json or related.json answer, as (rxcui, name, tty)
    (pure — pinned).

    found — HTTP 200 and at least one concept, each once, sorted; not_found — HTTP 200 and an object holding
    neither properties nor a relatedGroup, or a relatedGroup with no concept; malformed — a body that is not
    an object, groups that are not a list of objects, or a concept without a string rxcui, name and term type;
    lookup_failed — any other status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    if "properties" in body:
        raw = [body["properties"]]
    elif isinstance(body.get("relatedGroup"), dict):
        groups = body["relatedGroup"].get("conceptGroup") or []
        if not isinstance(groups, list) or not all(isinstance(g, dict) for g in groups):
            return "malformed", []
        if not all(isinstance(g.get("conceptProperties") or [], list) for g in groups):
            return "malformed", []
        raw = [c for g in groups for c in g.get("conceptProperties") or []]
    else:
        return "not_found", []
    concepts: set[Concept] = set()
    for concept in raw:
        if not isinstance(concept, dict) or not all(
            isinstance(concept.get(k), str) for k in ("rxcui", "name", "tty")
        ):
            return "malformed", []
        concepts.add((concept["rxcui"], concept["name"], concept["tty"]))
    return ("found" if concepts else "not_found"), sorted(concepts)


def rxnav_release(status: int, body: Any) -> tuple[str, str]:
    """The RxNav data release an answer was read under, from version.json (pure — pinned).

    found — HTTP 200 and an object with a non-empty string version (RxNav's release date, "05-Oct-2026");
    malformed — HTTP 200 and anything else; lookup_failed — any other status. Without a release the axes are
    still asked, but no structure relation is drawn from them.
    """
    if status != 200:
        return "lookup_failed", ""
    version = body.get("version") if isinstance(body, dict) else None
    if not isinstance(version, str) or not version:
        return "malformed", ""
    return "found", version


# A drug class's members (add-agent-operation, Decision 5): RxClass classMembers, asked by class id under the
# relation source and relation of the class's own source. Observed 2026-11-01 (RxNav release 05-Oct-2026):
# each member is an RxNorm concept (an ingredient, IN, or a precise ingredient, PIN) with "Relation" node
# attributes, DIRECT or INDIRECT (a direct member of one of the class's subclasses in the source's own
# hierarchy), one member sometimes carrying both in one list (ruxolitinib, everolimus and sirolimus in the EPC
# Kinase Inhibitor); an unknown class id answers {}. Asked with trans=1 the answer held the DIRECT entries
# only (the class's own members, without its subclasses'); without it, both.
RXCLASS_MEMBERS = f"{RXNAV}/rxclass/classMembers.json"
# The class's subclasses: RxClass classTree, the class as its root and each subclass under its parent, at any
# depth (the EPC Kinase Inhibitor's Janus Kinase Inhibitor holds Tyrosine Kinase 2 Inhibitor, 2026-11-01); a
# class id RxClass does not hold answers {}.
RXCLASS_TREE = f"{RXNAV}/rxclass/classTree.json"
# Each class source a request may name: (RxClass class type, relation source, relation).
CLASS_SOURCES = {
    "EPC": ("EPC", "DAILYMED", "has_epc"),
    "MoA": ("MOA", "MEDRT", "has_moa"),
    "ATC": ("ATC1-4", "ATC", ""),
}
# (rxcui, name, term type, relations: each "Relation" the member states, once, sorted; () when it states none)
Member = tuple[str, str, str, tuple[str, ...]]
# (class id, class name, class type, parent class id: "" for the root)
TreeClass = tuple[str, str, str, str]


def class_members_request(class_id: str, source: str) -> tuple[str, dict[str, str]]:
    """The RxClass classMembers request for one class of a source of CLASS_SOURCES: (URL, parameters)."""
    _kind, rela_source, rela = CLASS_SOURCES[source]
    return RXCLASS_MEMBERS, {"classId": class_id, "relaSource": rela_source} | (
        {"rela": rela} if rela else {}
    )


def direct_members_request(class_id: str, source: str) -> tuple[str, dict[str, str]]:
    """The classMembers request for one class's own (DIRECT) members, without its subclasses': the class's
    request with trans=1 (URL, parameters)."""
    url, params = class_members_request(class_id, source)
    return url, params | {"trans": "1"}


def class_tree_request(class_id: str) -> tuple[str, dict[str, str]]:
    """The RxClass classTree request for one class: (URL, parameters)."""
    return RXCLASS_TREE, {"classId": class_id}


def rxclass_tree(status: int, body: Any) -> tuple[str, list[TreeClass]]:
    """The classes in one RxClass classTree response, each under its parent (pure — pinned).

    found        — HTTP 200 and a tree: each class as (classId, className, classType, parent classId), the
                   top classes with parent "", in the tree's own order, each class before its subclasses; a
                   class listed under the same parent again is listed once (a class under two parents is
                   listed under each).
    not_found    — HTTP 200 and an object without rxclassTree (RxClass's answer for a class id it does not
                   hold, observed 2026-11-01).
    malformed    — HTTP 200 but the body is not an object, its rxclassTree is not a non-empty list, a node is
                   not an object, a node's rxclassTree is not a list, or a node lacks a string classId,
                   className and classType.
    lookup_failed — any other HTTP status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    top = body.get("rxclassTree")
    if top is None:
        return "not_found", []
    if not isinstance(top, list) or not top:
        return "malformed", []
    found: list[TreeClass] = []
    stack: list[tuple[Any, str]] = [(node, "") for node in reversed(top)]
    while stack:
        node, parent = stack.pop()
        item = node.get("rxclassMinConceptItem") if isinstance(node, dict) else None
        fields = (
            [item.get(key) for key in ("classId", "className", "classType")] if isinstance(item, dict) else []
        )
        children = node.get("rxclassTree", []) if isinstance(node, dict) else None
        if (
            not fields
            or not all(isinstance(field, str) for field in fields)
            or not isinstance(children, list)
        ):
            return "malformed", []
        entry = (fields[0], fields[1], fields[2], parent)
        if entry not in found:
            found.append(entry)
        stack += [(child, fields[0]) for child in reversed(children)]
    return "found", found


def rxclass_members(status: int, body: Any) -> tuple[str, list[Member]]:
    """The member drugs in one RxClass classMembers response, or why there are none (pure — pinned).

    found        — HTTP 200 with at least one member; each (rxcui, name, tty, relations), once, sorted; the
                   relations are every "Relation" node attribute the member states (DIRECT, INDIRECT or both,
                   as RxClass lists them in one member's attributes), each as text, once, sorted; () when it
                   states none.
    not_found    — HTTP 200 and an object without drugMemberGroup, or a group without drugMember (RxClass's
                   answer for a class id it does not hold, or a class with no member under that source).
    malformed    — HTTP 200 but the body is not an object, the group is not one, the listing is empty or not a
                   list, or a member lacks a concept with a string rxcui, name and term type.
    lookup_failed — any other HTTP status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    group = body.get("drugMemberGroup")
    if group is None:
        return "not_found", []
    listing = group.get("drugMember") if isinstance(group, dict) else []
    if listing is None:
        return "not_found", []
    if not isinstance(listing, list) or not listing:
        return "malformed", []
    found: set[Member] = set()
    for entry in listing:
        concept = entry.get("minConcept") if isinstance(entry, dict) else None
        fields = [concept.get(key) for key in ("rxcui", "name", "tty")] if isinstance(concept, dict) else []
        if not fields or not all(isinstance(field, str) for field in fields):
            return "malformed", []
        attributes = entry.get("nodeAttr")
        relations = {
            str(attribute["attrValue"])
            for attribute in (attributes if isinstance(attributes, list) else [])
            if isinstance(attribute, dict)
            and attribute.get("attrName") == "Relation"
            and "attrValue" in attribute
        }
        found.add((fields[0], fields[1], fields[2], tuple(sorted(relations))))
    return "found", sorted(found)


def axis_key(source: str, rela: str) -> str:
    """The name of an axis in the cache and the reading: its source, then its relation when it has one."""
    return f"{source}:{rela}" if rela else source


def name_identity(ids: list, concept: list, ingredients: list) -> tuple[str, str, list[str]]:
    """What RxNorm says one intervention name is: (code, its concept's rxcui, its ingredients)
    (pure — pinned).

    `ids`, `concept` and `ingredients` are the (code, values) of rxnorm_ids and rxnorm_concepts, a request not
    made being ("not_asked", []); the ingredients are rxcuis, sorted.
    lookup_failed — any of the requests failed.
    not_in_rxnorm — RxNorm holds no concept of exactly that name.
    ambiguous     — the name is exactly the name of more than one concept.
    unresolved    — an answer was malformed, or the one concept's type or ingredients could not be read.
    ingredient    — one concept, of term type IN: its own ingredient.
    combination   — one MIN, or a concept of another type with more than one ingredient.
    precise_ingredient — one PIN with one ingredient; PIN alone does not distinguish a salt, ester or
                         biologic variant, and never establishes equivalence to its related ingredient.
    brand         — one BN with one ingredient.
    other_form    — one concept of any other type (a clinical drug, a dose form group) with one ingredient.
    """
    (ids_code, id_list), (concept_code, concepts), (ingredients_code, parts) = ids, concept, ingredients
    if "lookup_failed" in (ids_code, concept_code, ingredients_code):
        return "lookup_failed", "", []
    if ids_code == "not_found":
        return "not_in_rxnorm", "", []
    if ids_code != "found" or len(id_list) != 1:
        return ("ambiguous" if ids_code == "found" and len(id_list) > 1 else "unresolved"), "", []
    if concept_code != "found" or len(concepts) != 1 or concepts[0][0] != id_list[0]:
        return "unresolved", "", []
    rxcui, _name, tty = concepts[0]
    if tty == "IN":
        return "ingredient", rxcui, [rxcui]
    rxcuis = sorted({part[0] for part in parts}) if ingredients_code == "found" else []
    if tty == "MIN" or len(rxcuis) > 1:
        return "combination", rxcui, rxcuis
    if not rxcuis:
        return "unresolved", "", []
    return {"PIN": "precise_ingredient", "BN": "brand"}.get(tty, "other_form"), rxcui, rxcuis


def class_standing(identity: str, entity: str, ingredients: list[str], subject: str) -> str:
    """Whether a class RxClass asserted of concept `subject` is the asked name's own (pure — pinned).

    known                  — the name resolved (name_identity) and the class is asserted of that very concept.
    not_inherited          — the name is a salt, brand, combination or other form and the class is asserted of
                             one of its ingredients: the ingredient's class, which no rule here carries over.
    other_entity           — asserted of a concept that is neither the name's nor one of its ingredients.
    identity_lookup_failed — the name's identity could not be asked, so nothing is attributed.
    identity_unresolved    — RxNorm does not resolve the name to one concept, so nothing is attributed.
    """
    if identity in RESOLVED:
        if subject == entity:
            return "known"
        return "not_inherited" if subject in ingredients else "other_entity"
    return "identity_lookup_failed" if identity == "lookup_failed" else "identity_unresolved"


def request_text(warrant: dict[str, Any]) -> str:
    """A request's warrant as one line: the URL with its parameters, as asked."""
    params = warrant.get("params") or {}
    return warrant["url"] + (f"?{urlencode(params)}" if params else "")


# An alias resolving to a concept other than the own name's; the own name still decides.
ALIAS_CONFLICTS = ("alias_is_combination", "alias_is_one_ingredient", "alias_other_concept")


def alias_role(own: tuple[str, str, list[str]], alias: tuple[str, str, list[str]]) -> str:
    """What another name the record gives an intervention says beside its own name (pure — pinned).

    `own` and `alias` are name_identity's (code, rxcui, ingredients). An alias never supplies a concept:
    alias_not_resolved   — RxNorm does not resolve the alias to one concept: it says nothing.
    confirms             — the own name resolves and the alias is that exact RxNorm concept.
    related_form         — distinct concepts whose source-listed ingredient sets agree; related is not
                           identical, so this never carries a class from one entity to another.
    alias_is_combination — the alias is a combination and the own name is not that combination (or does not
                           resolve).
    alias_is_one_ingredient — the alias names a source-listed component of the own resolved combination.
    alias_other_concept  — any other concept.
    """
    own_code, own_rxcui, own_parts = own
    code, rxcui, parts = alias
    if code not in RESOLVED:
        return "alias_not_resolved"
    if own_code in RESOLVED and rxcui == own_rxcui:
        return "confirms"
    if own_code in RESOLVED and parts and sorted(parts) == sorted(own_parts):
        return "related_form"
    if len(parts) > 1:
        return "alias_is_combination"
    if own_code in RESOLVED and len(own_parts) > 1 and set(parts) <= set(own_parts):
        return "alias_is_one_ingredient"
    return "alias_other_concept"


def identity_evidence(name: str, answer: Any) -> dict[str, Any]:
    """One recorded name's retained RxNorm evidence, with no substitution from another name.

    The concept and ingredient rows are the parsed source response, not names interpreted locally.
    An absent answer is not_looked_up; evidence missing from an existing answer is not_recorded;
    an invalid response shape is malformed. A PIN is a precise
    ingredient; its term type alone never establishes salt versus biosimilar or identity with a base.
    """
    evidence: dict[str, Any] = {
        "name": name,
        "asked_as": "",
        "name_rule": "",
        "code": "not_looked_up",
        "rxcui": "",
        "canonical_name": "",
        "term_type": "",
        "ingredients": [],
        "ingredient_concepts": [],
        "role": "",
        "requests": [],
        "release": [],
        "release_end": [],
    }
    if answer is None:
        return evidence
    if not isinstance(answer, dict):
        return {**evidence, "code": "malformed"}
    evidence.update(asked_as=answer.get("asked_as", ""), name_rule=answer.get("rule", ""))
    axes = answer.get("axes")
    held = axes.get("identity") if isinstance(axes, dict) else None
    if held is None:
        return {**evidence, "code": "not_recorded"}
    if not isinstance(held, dict):
        return {**evidence, "code": "malformed"}
    evidence.update({key: held.get(key, []) for key in ("requests", "release", "release_end")})
    parsed = []
    for key, width in (("ids", 1), ("concept", 3), ("ingredients", 3)):
        part = held.get(key)
        if not isinstance(part, (tuple, list)) or len(part) != 2:
            return {**evidence, "code": "malformed"}
        code, rows = part
        if not isinstance(code, str) or not isinstance(rows, (tuple, list)):
            return {**evidence, "code": "malformed"}
        if width == 1:
            valid = all(isinstance(row, str) and row for row in rows)
        else:
            valid = all(
                isinstance(row, (tuple, list))
                and len(row) == width
                and all(isinstance(value, str) and value for value in row)
                for row in rows
            )
        if not valid:
            return {**evidence, "code": "malformed"}
        parsed.append([code, list(rows)])
    code, rxcui, ingredients = name_identity(*parsed)
    evidence.update(code=code, rxcui=rxcui, ingredients=ingredients, ingredient_concepts=list(parsed[2][1]))
    if code in RESOLVED:
        _rxcui, canonical, tty = parsed[1][1][0]
        evidence.update(canonical_name=canonical, term_type=tty)
    requests = held.get("requests")
    queries = (
        [
            request.get("params", {}).get("name")
            for request in requests
            if isinstance(request, dict)
            and request.get("url") == RXNORM_IDS
            and isinstance(request.get("params"), dict)
            and str(request["params"].get("search")) == "0"
        ]
        if isinstance(requests, list)
        else []
    )
    if name not in queries:
        evidence.update(identity_kind=code, code="lookup_candidate" if queries else "not_recorded")
        evidence["asked_as"] = queries[0] if queries else ""
    return evidence


def class_evidence(aliases: list[str], answers: dict[str, Any] | None) -> dict[str, Any]:
    """Source identities and EPC/MoA assertions for one recorded intervention (pure).

    Only an assertion whose subject is the own name's exact established RxCUI can be known. An alias
    never supplies a missing own identity; related ingredients/forms remain distinct entities. Every
    source assertion is retained with its subject and standing. An unrelated alias identity makes the
    intervention unresolved, never whichever name happened to be visited first. Class sets from different
    sources/relations are not competing identities and are retained separately.
    """
    out: dict[str, Any] = {
        "state": "unresolved",
        "reason": "no_recorded_name",
        "classes": [],
        "resolved_by": "",
        "identities": [],
        "assertions": [],
        "queries": [],
    }
    if not isinstance(aliases, list) or any(not isinstance(name, str) or not name for name in aliases):
        return {**out, "reason": "malformed_recorded_names"}
    if not aliases:
        return out
    if answers is not None and not isinstance(answers, dict):
        return {**out, "reason": "malformed_answers"}
    names = [aliases[0], *sorted(set(aliases[1:]) - {aliases[0]})]
    supplied = answers if isinstance(answers, dict) else {}
    identities = [identity_evidence(name, supplied.get(name)) for name in names]
    own = (identities[0]["code"], identities[0]["rxcui"], identities[0]["ingredients"])
    for index, identity in enumerate(identities):
        identity["role"] = (
            "own"
            if index == 0
            else alias_role(own, (identity["code"], identity["rxcui"], identity["ingredients"]))
        )
    conflict = any(identity["role"] in ALIAS_CONFLICTS for identity in identities[1:])
    out["identities"] = identities
    for name in names:
        answer = supplied.get(name)
        axes = answer.get("axes", {}) if isinstance(answer, dict) else {}
        for source, relation in QUERIES:
            axis = axes.get(axis_key(source, relation)) if isinstance(axes, dict) else None
            query = {
                "queried_name": name,
                "source": source,
                "relation": relation,
                "code": "not_recorded" if isinstance(answer, dict) else "not_looked_up",
                "request": None,
                "release": [],
            }
            if axis is None and isinstance(answer, dict):
                recorded = answer.get("codes")
                if isinstance(recorded, dict) and axis_key(source, relation) in recorded:
                    query.update(
                        code=recorded[axis_key(source, relation)],
                        requests=answer.get("requests", []),
                        release=answer.get("release", []),
                    )
            if isinstance(axis, dict):
                query.update({key: axis.get(key, query[key]) for key in ("code", "request", "release")})
                rows = axis.get("assertions")
                if (
                    query["code"]
                    not in (
                        "found",
                        "not_found",
                        "lookup_failed",
                        "malformed",
                        "not_in_rxnorm",
                        "ambiguous_in_rxnorm",
                    )
                    or not isinstance(rows, list)
                    or bool(rows) != (query["code"] == "found")
                    or any(
                        not isinstance(row, (tuple, list))
                        or len(row) != 8
                        or not all(isinstance(value, str) for value in row)
                        or not all(row[index] for index in (0, 1, 5, 6, 7))
                        or row[3:5] not in ((relation, source), [relation, source])
                        for row in rows
                    )
                ):
                    query["code"] = "malformed"
                    rows = []
                for cid, label, kind, rela, origin, subject, subject_name, tty in rows:
                    standing = class_standing(*own, subject)
                    if conflict and standing == "known":
                        standing = "identity_conflict"
                    out["assertions"].append(
                        {
                            "queried_name": name,
                            "class_id": cid,
                            "class_name": label,
                            "class_type": kind,
                            "relation": rela,
                            "source": origin,
                            "subject_rxcui": subject,
                            "subject_name": subject_name,
                            "subject_type": tty,
                            "standing": standing,
                            "request": query["request"],
                            "release": query["release"],
                        }
                    )
            elif axis is not None:
                query["code"] = "malformed"
            out["queries"].append(query)
    classes = sorted(
        {
            (a["class_id"], a["class_name"], a["relation"], a["source"])
            for a in out["assertions"]
            if a["standing"] == "known"
        }
    )
    out["classes"] = [list(row) for row in classes]
    if answers is None or own[0] == "not_looked_up":
        out.update(state="not_looked_up", reason="own_identity_not_looked_up")
    elif own[0] == "lookup_failed":
        out.update(state="lookup_failed", reason="own_identity_lookup_failed")
    elif own[0] not in RESOLVED:
        out["reason"] = f"own_identity_{own[0]}"
    elif conflict:
        out.update(state="conflict", reason="alias_identity_conflict")
    elif classes:
        out.update(state="classified", reason="exact_source_subject", resolved_by=names[0])
    elif any(query["code"] == "lookup_failed" for query in out["queries"]):
        out.update(state="lookup_failed", reason="class_lookup_failed")
    elif any(query["code"] == "malformed" for query in out["queries"]):
        out["reason"] = "class_response_malformed"
    else:
        out["reason"] = "no_direct_class_assertion"
    return out


def drug_axes(aliases: list[str], answers: dict[str, Any]) -> tuple[str, str, list[tuple], list[tuple]]:
    """One intervention's ATC and structure classes, decided by its own name (pure — pinned).

    `aliases` are its names in record order, its own name first. The own name is resolved (name_identity) and
    decides what the intervention is; every other name is resolved only to say whether it confirms that
    (alias_role), and every class RxClass gave for any of the names keeps its standing against the own name's
    concept (class_standing), so an alias can never make a class known.
    Returns (code, reason, identities, assertions):
    resolved      — reason own_name: the own name resolves and no alias names another concept.
    conflict      — the own name resolves and an alias names another concept (reason: that alias_role); a
                    class that would be known is `identity_conflict`.
    unresolved    — the own name does not resolve to one concept, whatever its aliases resolve to: reason the
                    first resolving alias's role (alias_is_one_ingredient, alias_is_combination,
                    alias_other_concept), else own_name_<its identity code>; own_name_not_asked when the
                    answers hold no axes for it.
    lookup_failed — reason own_name_lookup_failed: the own name's identity could not be asked.
    Identities are (name, code, rxcui, ingredients, role — "own" or alias_role's, requests as (request,
    retrieved) pairs, release); assertions are (name, axis, class id, class name, class type, standing,
    subject rxcui, subject name, release, request, retrieved), sorted; the release is "" when RxNav's could
    not be read.
    """
    own_axes = (answers.get(aliases[0]) or {}).get("axes") if aliases else None
    if not own_axes:
        return "unresolved", "own_name_not_asked", [], []
    own: tuple[str, str, list[str]] = ("", "", [])
    identities, assertions = [], []
    for alias in aliases:
        axes = (answers.get(alias) or {}).get("axes")
        if not axes:
            continue
        held = axes["identity"]
        evidence = identity_evidence(alias, answers.get(alias))
        identity = (evidence["code"], evidence["rxcui"], evidence["ingredients"])
        if not identities:
            own = identity
        role = "own" if not identities else alias_role(own, identity)
        requests = tuple((request_text(w), w["retrieved"]) for w in held.get("requests", []))
        release = held["release"][1] if held["release"][0] == "found" else ""
        identities.append((alias, *identity, role, requests, release))
        for source, rela in AXES:
            axis = axis_key(source, rela)
            answer = axes[axis]
            release = answer["release"][1] if answer["release"][0] == "found" else ""
            request, retrieved = request_text(answer["request"]), answer["request"]["retrieved"]
            for class_id, name, kind, _rela, _source, rxcui, subject_name, _tty in answer["assertions"]:
                standing = class_standing(own[0], own[1], own[2], rxcui)
                assertions.append(
                    (
                        alias,
                        axis,
                        class_id,
                        name,
                        kind,
                        standing,
                        rxcui,
                        subject_name,
                        release,
                        request,
                        retrieved,
                    )
                )
    roles = [identity[4] for identity in identities[1:]]
    conflict = next((role for role in roles if role in ALIAS_CONFLICTS), "")
    if own[0] == "lookup_failed":
        return "lookup_failed", "own_name_lookup_failed", identities, sorted(assertions)
    if own[0] not in RESOLVED:
        return "unresolved", conflict or f"own_name_{own[0]}", identities, sorted(assertions)
    if conflict:
        assertions = [(*a[:5], "identity_conflict" if a[5] == "known" else a[5], *a[6:]) for a in assertions]
        return "conflict", conflict, identities, sorted(assertions)
    return "resolved", "own_name", identities, sorted(assertions)


def shares_structure_class(
    a: tuple[str, list[tuple[str, str, str, str]]], b: tuple[str, list[tuple[str, str, str, str]]]
) -> list[tuple[str, str, str, str, str]]:
    """The structure classes two distinct drugs share (pure — pinned).

    Each drug is (name, its known structure classes as (taxonomy, class id, class name, release)). The
    relation shares_structure_class(a, b, taxonomy, class, release) holds for each class both drugs hold under
    the same taxonomy (relation source and relation; DAILYMED and FDASPL are never merged) and the same known
    release. It states a shared class, never homology. A drug is never related to itself (the same name), and
    a class under an unknown release ("") relates nothing. Returns (a, b, taxonomy, "<id> <name>", release),
    sorted.
    """
    if a[0] == b[0]:
        return []
    held = {(taxonomy, class_id, release) for taxonomy, class_id, _name, release in b[1] if release}
    return sorted(
        {
            (a[0], b[0], taxonomy, f"{class_id} {name}", release)
            for taxonomy, class_id, name, release in a[1]
            if release and (taxonomy, class_id, release) in held
        }
    )


# The target-to-ATC crosswalk (Decision 11): a target a drug's own entry states (TARGET_WORDS) against the ATC
# class names RxClass returns. The relation is the stated target's concept against the ATC class's:
# equivalent_to (the same), narrower_than (the target lies within the class), broader_than (the class lies
# within the target), overlaps (each has members the other lacks), unresolved (the names cannot decide). Only
# targets: a word naming a drug (platinum, cisplatin, carboplatin, taxane, paclitaxel, docetaxel, pemetrexed,
# bevacizumab) names another drug an entry mentions, never this drug's target, so no row is keyed by one.
# Rows: (stated target, ATC id, ATC name as RxClass returns it, relation, citation, RxClass request,
# retrieved); each name read by that request on 2026-11-01 under RxNav release 05-Oct-2026.
RXCLASS_BY_ID = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byId.json?classId="
CROSSWALK_READ = "2026-11-01"
_L01FF = "PD-1/PD-L1 (Programmed cell death protein 1/death ligand 1) inhibitors"
CROSSWALK = (
    (
        "PD-1",
        "L01FF",
        _L01FF,
        "overlaps",
        "L01FF also holds PD-L1 inhibitors and lies under L01F, MONOCLONAL ANTIBODIES AND ANTIBODY DRUG "
        "CONJUGATES; a stated PD-1 target does not state an antibody",
        RXCLASS_BY_ID + "L01FF",
        CROSSWALK_READ,
    ),
    (
        "PD-L1",
        "L01FF",
        _L01FF,
        "overlaps",
        "L01FF also holds PD-1 inhibitors and lies under L01F, MONOCLONAL ANTIBODIES AND ANTIBODY DRUG "
        "CONJUGATES; a stated PD-L1 target does not state an antibody",
        RXCLASS_BY_ID + "L01FF",
        CROSSWALK_READ,
    ),
    (
        "CTLA-4",
        "L01FX",
        "Other monoclonal antibodies and antibody drug conjugates",
        "unresolved",
        "no fourth-level ATC class names CTLA-4; RxClass places ipilimumab in the residual L01FX "
        "(byDrugName.json?drugName=ipilimumab&relaSource=ATC, 2026-11-01)",
        RXCLASS_BY_ID + "L01FX",
        CROSSWALK_READ,
    ),
    (
        "immune checkpoint",
        "L01FF",
        _L01FF,
        "unresolved",
        "the class name names PD-1 and PD-L1, not immune checkpoints",
        RXCLASS_BY_ID + "L01FF",
        CROSSWALK_READ,
    ),
    (
        "EGFR inhibitor",
        "L01EB",
        "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors",
        "broader_than",
        "every member inhibits EGFR; the stated words also cover EGFR antibodies (L01FE) and EGFR-directed "
        "agents",
        RXCLASS_BY_ID + "L01EB",
        CROSSWALK_READ,
    ),
    (
        "EGFR inhibitor",
        "L01FE",
        "EGFR (Epidermal Growth Factor Receptor) inhibitors",
        "broader_than",
        "L01FE lies under L01F, MONOCLONAL ANTIBODIES AND ANTIBODY DRUG CONJUGATES; the stated words also "
        "cover EGFR tyrosine kinase inhibitors (L01EB)",
        RXCLASS_BY_ID + "L01FE",
        CROSSWALK_READ,
    ),
    (
        "ALK inhibitor",
        "L01ED",
        "Anaplastic lymphoma kinase (ALK) inhibitors",
        "broader_than",
        "every member inhibits ALK; the stated words also match ALK-directed and ALK-targeted agents",
        RXCLASS_BY_ID + "L01ED",
        CROSSWALK_READ,
    ),
    (
        "MET inhibitor",
        "L01EP",
        "Cellular-mesenchymal-epithelial transition factor (c-MET) kinase inhibitors",
        "broader_than",
        "every member inhibits the c-MET kinase; the stated words also match MET-directed and MET-targeted "
        "agents",
        RXCLASS_BY_ID + "L01EP",
        CROSSWALK_READ,
    ),
    (
        "VEGF inhibitor",
        "L01FG",
        "VEGF/VEGFR (Vascular Endothelial Growth Factor / -Receptor) inhibitors",
        "overlaps",
        "L01FG lies under L01F, MONOCLONAL ANTIBODIES AND ANTIBODY DRUG CONJUGATES; VEGFR tyrosine kinase "
        "inhibitors are L01EK, and the stated words also name them",
        RXCLASS_BY_ID + "L01FG",
        CROSSWALK_READ,
    ),
)

# The words that name a drug's own target, never another drug: each a target of the crosswalk.


def entails_membership(relation: str) -> bool:
    """Whether a crosswalk relation makes a drug of the stated target an ATC class member (pure — pinned).

    Only equivalent_to and narrower_than (the target lies within the class) entail membership; broader_than,
    overlaps, unresolved, and any name not a relation, never do.
    """
    return relation in ("equivalent_to", "narrower_than")


def target_alignment(targets: list[str]) -> list[tuple[str, str, str, str, bool, str, str]]:
    """Each stated target's ATC alignment by the crosswalk (pure — pinned).

    Returns (target, ATC id, ATC name, relation, member, RxClass request, retrieved) for every crosswalk row
    of each target, in the order the targets are given; a target no row names is (target, "", "",
    "unresolved", False, "", ""). `member` is entails_membership(relation).
    """
    out = []
    for target in targets:
        rows = [row for row in CROSSWALK if row[0] == target]
        if not rows:
            out.append((target, "", "", "unresolved", False, "", ""))
        out += [
            (target, atc, name, relation, entails_membership(relation), request, read)
            for _, atc, name, relation, _, request, read in rows
        ]
    return out


def drug_atc(known: list[str], targets: list[str], alignment: list[tuple]) -> tuple[str, list[str]]:
    """A drug's ATC classes for the aligned near-miss representation, and their basis (pure — pinned).

    rxclass   — RxClass gave classes `known` (asserted of the drug's own resolved concept): those, once,
                sorted.
    crosswalk — none known, and every target the drug's own entry states (own_targets) has a crosswalk row
                (`alignment`, target_alignment's) entailing membership: the classes those rows entail, once,
                sorted. No row of the present crosswalk entails membership, so none does yet.
    ""        — otherwise (no target, or a target whose rows do not entail membership): no classes.
    """
    if known:
        return "rxclass", sorted(set(known))
    members = {target: [row[1] for row in alignment if row[0] == target and row[4]] for target in targets}
    if targets and all(members.values()):
        return "crosswalk", sorted({atc for atcs in members.values() for atc in atcs})
    return "", []


def mesh_scope(meshes: Any, names: dict[str, list[str]]) -> list[tuple[str, str, str, str]]:
    """Where each registry-derived intervention MeSH term belongs (pure — pinned).

    The registry derives derivedSection.interventionBrowseModule.meshes for the trial, not for an
    intervention, so a term stays at trial level ("trial", "") unless it is, letter for letter apart from
    case, a name or other name the record gives exactly one intervention: then ("intervention", that
    intervention's name). `names` maps each intervention's name to its names. Returns (mesh id, term, scope,
    intervention) in the registry's order; an entry without a string id and term is skipped.
    """
    out = []
    for mesh in meshes if isinstance(meshes, list) else []:
        if (
            not isinstance(mesh, dict)
            or not isinstance(mesh.get("id"), str)
            or not isinstance(mesh.get("term"), str)
        ):
            continue
        term = mesh["term"]
        linked = [
            name for name, aliases in names.items() if term.casefold() in {a.casefold() for a in aliases}
        ]
        scope, linked_name = ("intervention", linked[0]) if len(linked) == 1 else ("trial", "")
        out.append((mesh["id"], term, scope, linked_name))
    return out
