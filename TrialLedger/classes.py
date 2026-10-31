"""Intervention classes from a cited source: NLM RxClass, FDA Established Pharmacologic Class and MED-RT.

The registry states no mechanism for an intervention (its MeSH ancestors are chemical-structure classes), so
TrialLedger asks the U.S. National Library of Medicine's RxClass service, by each drug or biological
intervention's name and then each other name the record gives it: `has_epc` from DailyMed (the FDA's
Established Pharmacologic Class) and `has_moa` from MED-RT (mechanism of action). Every class keeps its
RxClass id and relation source. A name RxClass does not know is `not_found`; a failed request is
`lookup_failed`; neither is ever read as "no class". The answers are cached beside the pull in classes.json,
with the request and the retrieval time, so a profile can be re-derived without the network.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

RXCLASS = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json"
QUERIES = (("DAILYMED", "has_epc"), ("MEDRT", "has_moa"))
CACHE_NAME = "classes.json"
DRUG_TYPES = ("DRUG", "BIOLOGICAL")

Class = tuple[str, str, str, str]  # (class id, class name, relation, relation source)


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
    """Each drug or biological intervention's name, mapped to its name then its other names, in record
    order."""
    module = study.get("protocolSection", {}).get("armsInterventionsModule", {})
    names: dict[str, list[str]] = {}
    for item in module.get("interventions", []) or []:
        if isinstance(item, dict) and item.get("type") in DRUG_TYPES and isinstance(item.get("name"), str):
            others = [n for n in item.get("otherNames", []) or [] if isinstance(n, str)]
            names[item["name"]] = list(dict.fromkeys([item["name"], *others]))
    return names


def experimental_drugs(study: dict[str, Any]) -> list[str]:
    """The drug and biological names an EXPERIMENTAL arm names, by the registry's `<type label>: <name>`
    cross-reference."""
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


def lookup(
    names: list[str],
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]],
    sleep: Callable[[float], None] = time.sleep,
    spacing: float = 0.2,
) -> dict[str, dict[str, Any]]:
    """Ask RxClass for each name, both queries, spaced; each name's code per query and its classes."""
    answers: dict[str, dict[str, Any]] = {}
    for name in dict.fromkeys(names):
        per_query = {}
        for source, rela in QUERIES:
            status, body = get(RXCLASS, {"drugName": name, "relaSource": source, "relas": rela})
            per_query[f"{source}:{rela}"] = rxclass_classes(status, body)
            sleep(spacing)
        answers[name] = {
            "codes": {key: code for key, (code, _) in per_query.items()},
            "classes": sorted({c for _, classes in per_query.values() for c in classes}),
        }
    return answers


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


def load_or_lookup(folder: Path, names: list[str], *, get=http_get, sleep=time.sleep) -> dict[str, Any]:
    """The folder's cached RxClass answers, extended by a lookup of any name not yet cached, and saved."""
    path = folder / CACHE_NAME
    cache = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    answers = cache.get("answers", {})
    missing = [n for n in dict.fromkeys(names) if n not in answers]
    if missing:
        answers.update(lookup(missing, get=get, sleep=sleep))
        cache = {
            "source": "NLM RxClass REST API, byDrugName; DAILYMED has_epc and MEDRT has_moa",
            "endpoint": RXCLASS,
            "retrieved": datetime.now(UTC).isoformat(timespec="seconds"),
            "answers": answers,
        }
        path.write_text(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return answers


def drug_class(answers: dict[str, Any], aliases: list[str]) -> tuple[str, list[Class], str]:
    """A drug's classes by the first of its names RxClass classifies: (code, classes, the name that resolved).

    classified — some name has classes; unresolved — every name was not_found or malformed; lookup_failed —
    no name has classes and at least one lookup failed, so absence is not established.
    """
    failed = False
    for alias in aliases:
        answer = answers.get(alias)
        if answer is None:
            failed = True
            continue
        if answer["classes"]:
            return "classified", [tuple(c) for c in answer["classes"]], alias
        failed = failed or "lookup_failed" in answer["codes"].values()
    return ("lookup_failed" if failed else "unresolved"), [], ""
