"""Intervention classes from a cited source: NLM RxClass, FDA Established Pharmacologic Class and MED-RT, and
the drug-class axes beside them (ATC, chemical structure), each about an entity RxNorm resolves.

The registry states no mechanism for an intervention (its MeSH ancestors are chemical-structure classes), so
TrialLedger asks the U.S. National Library of Medicine's RxClass service, by each drug, biological or genetic
intervention's name and then each other name the record gives it: `has_epc` from DailyMed (the FDA's
Established Pharmacologic Class) and `has_moa` from MED-RT (mechanism of action). Every class keeps its
RxClass id and relation source. A name RxClass does not know is `not_found`; a failed request is
`lookup_failed`; neither is ever read as "no class". The answers are cached beside the pull in classes.json,
with the request and the retrieval time (of the cache's last extension, and of each answer since 2026-11-01;
an answer cached before then has none), so a profile can be re-derived without the network.

The axes (add-scoped-reasoning, Decision 11) are separate coordinates, never merged with the classes above or
with each other: the ATC class (RxClass relaSource ATC) and the chemical-structure class
(`has_chemical_structure` from DAILYMED and from FDASPL). RxClass answers a brand or a salt as its ingredient
(asked "Keytruda" or "osimertinib mesylate", it answers about pembrolizumab or osimertinib, measured
2026-10-31), so a class is read as a source assertion about the concept RxClass names, and each name is first
resolved by RxNorm (its exact-name concept, the concept's term type, a non-ingredient's ingredients). The
intervention's own name decides what it is; another name the record gives it may confirm that concept but
never supplies one. A class counts as the intervention's own (`known`) only when it is asserted of the very
concept its own name resolves to; a salt, brand or combination never inherits its ingredient's class by an API
answer alone. Every axis answer keeps its warrant: the request, the retrieval time, the RxNav release and the
ids, and the axes are asked only for the experimental drugs' names, the only ones read, and only when a
consumer of them or the explicit fill asks (load_or_lookup_at's `fill_axes`). A target the drug's
own entry states (anti-PD-1, EGFR inhibitor) aligns to ATC through a sourced crosswalk with named relations,
membership only where the relation entails it; a word naming another drug (carboplatin, paclitaxel) is no
target of this one. Registry intervention MeSH stays at trial level unless the record's own name of one
intervention is the term.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from TrialLedger.modality import history_clause

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
# The axes, each its own coordinate: (relation source, relation); ATC has no relation name in RxClass.
AXES = (("ATC", ""), ("DAILYMED", "has_chemical_structure"), ("FDASPL", "has_chemical_structure"))
# (class id, class name, class type, relation, relation source, subject rxcui, subject name, subject tty)
Assertion = tuple[str, str, str, str, str, str, str, str]
Concept = tuple[str, str, str]  # (rxcui, name, term type)
RESOLVED = ("ingredient", "salt", "brand", "combination", "other_form")


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


def lookup(
    names: list[str],
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]],
    sleep: Callable[[float], None] = time.sleep,
    spacing: float = 0.2,
) -> dict[str, dict[str, Any]]:
    """Ask RxClass for each name, both queries, spaced; each name's code per query, its classes and when it
    was retrieved."""
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
            "retrieved": datetime.now(UTC).isoformat(timespec="seconds"),
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


# A live query (`trialledger resolve`) holds no folder: its RxClass answers persist in the user's cache.
USER_CACHE = Path.home() / ".cache" / "trialledger" / CACHE_NAME


def load_or_lookup(
    folder: Path,
    names: list[str],
    axes_names: Sequence[str] = (),
    *,
    fill_axes: bool = False,
    get=http_get,
    sleep=time.sleep,
) -> dict[str, Any]:
    """The folder's cached RxClass answers, extended by a lookup of any name not yet cached, and saved; the
    axes of `axes_names` are asked only with `fill_axes` (load_or_lookup_at)."""
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
) -> dict[str, Any]:
    """The RxClass answers cached at `path`, extended by a lookup of any name not yet cached, and saved.

    EPC and MoA are asked for every name of `names` and `axes_names` not yet cached. The axes (RxNorm
    identity, ATC, structure: four to six spaced requests a name) are asked only when `fill_axes` is given,
    and only for `axes_names` (the experimental drugs' names, the only ones the reading reads) not yet holding
    them: a consumer that reads them (the `resolve` JSON and its design.xlsx) or the explicit fill
    (`trialledger profile --fill-axes`) asks; any other run reads the axes already cached, and the reading
    names the rest not_looked_up (reading.axes_as_looked_up), never "no class". Asked on every profile, they
    took a stored 487-trial folder from seconds to over an hour (2026-11-01), which a profile must not need.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    answers = cache.get("answers", {})
    missing = [n for n in dict.fromkeys([*names, *axes_names]) if n not in answers]
    if missing:
        answers.update(lookup(missing, get=get, sleep=sleep))
    # A name cached before the axes existed is asked for them alone; its classes stay as they were answered.
    unasked = [n for n in dict.fromkeys(axes_names) if "axes" not in answers[n]] if fill_axes else []
    if unasked:
        for name, axes in lookup_axes(unasked, get=get, sleep=sleep).items():
            answers[name]["axes"] = axes
    if missing or unasked:
        cache = {
            "source": "NLM RxClass REST API, byDrugName; DAILYMED has_epc and MEDRT has_moa; per name under "
            '"axes": RxNorm identity (rxcui by exact name, properties, related ingredients), ATC, and '
            "has_chemical_structure from DAILYMED and FDASPL, each with its request, retrieval time and "
            "release",
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


def _warranted(
    get, url: str, params: dict[str, str], sleep, spacing: float
) -> tuple[dict[str, Any], int, Any]:
    """One request with its warrant (url, parameters, retrieval time), spaced; the status and body beside
    it."""
    status, body = get(url, params)
    sleep(spacing)
    warrant = {"url": url, "params": params, "retrieved": datetime.now(UTC).isoformat(timespec="seconds")}
    return warrant, status, body


def lookup_axes(
    names: list[str],
    *,
    get: Callable[[str, dict[str, str]], tuple[int, Any]],
    sleep: Callable[[float], None] = time.sleep,
    spacing: float = 0.2,
) -> dict[str, dict[str, Any]]:
    """Each name's RxNorm identity and its ATC and structure answers, spaced, each with its warrant.

    The RxNav release is asked once for the batch. Identity: the exact-name concepts; when there is exactly
    one, its properties; when that is not an ingredient (IN), its related ingredients. Then each axis of AXES.
    """
    warrant, status, body = _warranted(get, RXNAV_VERSION, {}, sleep, spacing)
    release = [*rxnav_release(status, body), warrant]
    out: dict[str, dict[str, Any]] = {}
    for name in dict.fromkeys(names):
        requests = []
        warrant, status, body = _warranted(get, RXNORM_IDS, {"name": name, "search": "0"}, sleep, spacing)
        requests.append(warrant)
        ids = rxnorm_ids(status, body)
        concept: tuple[str, list[Concept]] = ("not_asked", [])
        ingredients: tuple[str, list[Concept]] = ("not_asked", [])
        if ids[0] == "found" and len(ids[1]) == 1:
            url = RXNORM_PROPERTIES.format(rxcui=ids[1][0])
            warrant, status, body = _warranted(get, url, {}, sleep, spacing)
            requests.append(warrant)
            concept = rxnorm_concepts(status, body)
            if concept[0] == "found" and len(concept[1]) == 1 and concept[1][0][2] != "IN":
                url = RXNORM_RELATED.format(rxcui=ids[1][0])
                warrant, status, body = _warranted(get, url, {"tty": "IN"}, sleep, spacing)
                requests.append(warrant)
                ingredients = rxnorm_concepts(status, body)
        answer: dict[str, Any] = {
            "identity": {
                "ids": list(ids),
                "concept": list(concept),
                "ingredients": list(ingredients),
                "requests": requests,
                "release": release,
            }
        }
        for source, rela in AXES:
            params = {"drugName": name, "relaSource": source} | ({"relas": rela} if rela else {})
            warrant, status, body = _warranted(get, RXCLASS, params, sleep, spacing)
            code, assertions = rxclass_assertions(status, body)
            answer[axis_key(source, rela)] = {
                "code": code,
                "assertions": assertions,
                "request": warrant,
                "release": release,
            }
        out[name] = answer
    return out


# A drug class's members (add-agent-operation, Decision 5): RxClass classMembers, asked by class id under the
# relation source and relation of the class's own source. Observed 2026-11-01 (RxNav release 05-Oct-2026):
# each member is an RxNorm concept (an ingredient, IN, or a precise ingredient, PIN) with a "Relation" node
# attribute, DIRECT or INDIRECT (a member of a narrower class); an unknown class id answers {}.
RXCLASS_MEMBERS = f"{RXNAV}/rxclass/classMembers.json"
# Each class source a request may name: (RxClass class type, relation source, relation).
CLASS_SOURCES = {
    "EPC": ("EPC", "DAILYMED", "has_epc"),
    "MoA": ("MOA", "MEDRT", "has_moa"),
    "ATC": ("ATC1-4", "ATC", ""),
}
Member = tuple[str, str, str, str]  # (rxcui, name, term type, relation: DIRECT or INDIRECT, "" when unstated)


def class_members_request(class_id: str, source: str) -> tuple[str, dict[str, str]]:
    """The RxClass classMembers request for one class of a source of CLASS_SOURCES: (URL, parameters)."""
    _kind, rela_source, rela = CLASS_SOURCES[source]
    return RXCLASS_MEMBERS, {"classId": class_id, "relaSource": rela_source} | (
        {"rela": rela} if rela else {}
    )


def rxclass_members(status: int, body: Any) -> tuple[str, list[Member]]:
    """The member drugs in one RxClass classMembers response, or why there are none (pure — pinned).

    found        — HTTP 200 with at least one member; each (rxcui, name, tty, relation), once, sorted; the
                   relation is the member's "Relation" node attribute, "" when it states none.
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
        relation = next(
            (
                str(attribute.get("attrValue", ""))
                for attribute in (attributes if isinstance(attributes, list) else [])
                if isinstance(attribute, dict) and attribute.get("attrName") == "Relation"
            ),
            "",
        )
        found.add((fields[0], fields[1], fields[2], relation))
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
    salt          — one PIN (a precise ingredient: a salt or an ester) with one ingredient.
    brand         — one BN with one ingredient.
    other_form    — one concept of any other type (a clinical drug, a dose form group) with one ingredient.
    """
    (ids_code, id_list), (concept_code, concepts), (ingredients_code, parts) = ids, concept, ingredients
    if "lookup_failed" in (ids_code, concept_code, ingredients_code):
        return "lookup_failed", "", []
    if ids_code == "not_found":
        return "not_in_rxnorm", "", []
    if ids_code != "found" or len(id_list) > 1:
        return ("ambiguous" if ids_code == "found" else "unresolved"), "", []
    if concept_code != "found" or len(concepts) != 1:
        return "unresolved", "", []
    rxcui, _name, tty = concepts[0]
    if tty == "IN":
        return "ingredient", rxcui, [rxcui]
    rxcuis = sorted({part[0] for part in parts}) if ingredients_code == "found" else []
    if tty == "MIN" or len(rxcuis) > 1:
        return "combination", rxcui, rxcuis
    if not rxcuis:
        return "unresolved", "", []
    return {"PIN": "salt", "BN": "brand"}.get(tty, "other_form"), rxcui, rxcuis


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
_COMBINATION_WORDING = re.compile(r"/|\+|,|\band\b|\bplus\b", re.IGNORECASE)


def alias_role(own_name: str, own: tuple[str, str, list[str]], alias: tuple[str, str, list[str]]) -> str:
    """What another name the record gives an intervention says beside its own name (pure — pinned).

    `own` and `alias` are name_identity's (code, rxcui, ingredients). An alias never supplies a concept:
    alias_not_resolved   — RxNorm does not resolve the alias to one concept: it says nothing.
    confirms             — the own name resolves and the alias is that concept, or names the same ingredients
                           (a brand or a salt of the same single ingredient).
    alias_is_combination — the alias is a combination and the own name is not that combination (or does not
                           resolve).
    alias_is_one_ingredient — the alias is a single ingredient of the own name: of its resolved combination,
                           or, when RxNorm does not hold the own name, of the combination its own wording
                           names ("Carboplatin/Pemetrexed", "X + Y", "X, Y", "X and Y", "X plus Y").
    alias_other_concept  — any other concept.
    """
    own_code, own_rxcui, own_parts = own
    code, rxcui, parts = alias
    if code not in RESOLVED:
        return "alias_not_resolved"
    if own_code in RESOLVED and (rxcui == own_rxcui or sorted(parts) == sorted(own_parts)):
        return "confirms"
    if len(parts) > 1:
        return "alias_is_combination"
    combination = len(own_parts) > 1 if own_code in RESOLVED else bool(_COMBINATION_WORDING.search(own_name))
    if combination and (own_code not in RESOLVED or set(parts) <= set(own_parts)):
        return "alias_is_one_ingredient"
    return "alias_other_concept"


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
        identity = name_identity(held["ids"], held["concept"], held["ingredients"])
        if not identities:
            own = identity
        role = "own" if not identities else alias_role(aliases[0], own, identity)
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
TARGET_WORDS = {
    "PD-1": r"anti[- ]?PD[- ]?1\b|\bPD[- ]?1 (?:inhibitor|antibod|blockade|blocking)",
    "PD-L1": r"anti[- ]?PD[- ]?L1\b|\bPD[- ]?L1 (?:inhibitor|antibod|blockade|blocking)",
    "CTLA-4": r"anti[- ]?CTLA[- ]?4\b|\bCTLA[- ]?4 (?:inhibitor|antibod|blockade|blocking)",
    "immune checkpoint": r"immune[- ]checkpoint inhibitor|\bcheckpoint inhibitor",
    "EGFR inhibitor": r"\bEGFR[- ](?:TKI|tyrosine kinase inhibitor|inhibitor|directed|targeted)",
    "ALK inhibitor": r"\bALK[- ](?:TKI|tyrosine kinase inhibitor|inhibitor|directed|targeted)",
    "MET inhibitor": r"\bc?-?MET[- ](?:TKI|inhibitor|targeted|directed)",
    "VEGF inhibitor": r"anti[- ]?VEGF\b|\bVEGFR? (?:inhibitor|antibod)",
}


_OTHER_DRUG = re.compile(
    r"\b[A-Za-z][\w-]*(?:mab|nib|ciclib|parib|platin|taxel|mustine|rubicin|trexed|citabine)\b"
    r"|\b(?:cisplatin|carboplatin|oxaliplatin|paclitaxel|docetaxel|pemetrexed|gemcitabine|etoposide)\b",
    re.IGNORECASE,
)


def own_targets(entry: str, own_name: str = "") -> list[str]:
    """The targets a drug's own entry states of the drug itself (pure — pinned).

    Each TARGET_WORDS target named in `entry` (the intervention's own name and description), each once, in the
    order first named, except a mention whose clause states the patient's history or eligibility
    (modality.history_clause: "patients previously treated with an anti-PD-1"), which is about the patient,
    and a mention whose clause names another drug before it ("XB-1 given with pembrolizumab, an anti-PD-1
    antibody"), which may be that drug's: a drug-name stem other than `own_name` makes the reading abstain,
    never assert. A word naming another drug is no target ("XB-1 given after carboplatin and paclitaxel"
    states none). None stated: an empty list."""
    own = own_name.strip().lower()
    found: dict[str, int] = {}
    for target, pattern in TARGET_WORDS.items():
        for match in re.finditer(pattern, entry, re.IGNORECASE):
            clause_start = max(entry.rfind(mark, 0, match.start()) for mark in (". ", ";", "\n")) + 1
            others = [
                m
                for m in _OTHER_DRUG.finditer(entry, clause_start, match.start())
                if m.group(0).lower() != own
            ]
            if not history_clause(entry[: match.start()]) and not others:
                found[target] = min(found.get(target, match.start()), match.start())
    return sorted(found, key=lambda target: found[target])


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
