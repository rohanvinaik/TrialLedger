"""Universes: which domain readings a trial's record may carry (refine-landscape-record design §3).

A universe (contract.UNIVERSES) names the rule packs it owns; a rule outside every universe a trial is in is
never applied. Membership is not permission: each pack states what it requires (the trial's universe and,
for the setting and line-of-therapy pack, a treatment purpose) before its coordinates are computed.

`assign` reads three named sources of the registry's study record, each recorded with what it found:
1. condition_mesh: the condition MeSH terms and their ancestors, matched whole against the MeSH anchors
   (contract.MESH_ANCHORS);
2. free_text: the free-text conditions, matched word by word against the declared vocabulary
   (contract.ONCOLOGY_TERMS); a condition that names no disease (contract.NOT_DISEASE_CONDITIONS, such as
   "Progression Free Survival") is no evidence of any domain. The titles are read where no condition names a
   cancer, only as a signal of oncology, never as evidence of another domain; a condition the vocabulary
   misses counts as outside oncology only where neither the conditions nor the titles name a cancer;
3. drug_class: for a treatment trial, each intervention's ATC class as RxNav gives it for the intervention's
   name or one of its other names (antineoplastic agents, L01; endocrine therapy for cancer, L02). The classes
   are an input, never looked up here; in relay mode they are not looked up at all and the source reads "not
   looked up", never "no class".

How they decide (scope_case):
- oncology: a condition source (the MeSH terms or the free-text conditions) finds an oncology anchor; or only
  the titles or a drug's class do and no condition is positively outside oncology. The trial is in each
  oncology universe its findings name (several: the union). An anchor that names no kind of tumour
  (UNSPECIFIC_ANCHORS: "Neoplasms", "cancer", an ATC class) counts as haematologic where any source finds a
  haematologic anchor (rituximab is L01, and a lymphoma's MeSH ancestors include Neoplasms); within one
  source, such an anchor is not listed beside a specific one.
- general: the conditions are positively outside oncology (a condition MeSH term, or a free-text condition
  that names a disease) and no source signals oncology.
- unresolved, sources disagree: the conditions are positively outside oncology while the titles or a drug's
  class signal it (methotrexate, L01, in a rheumatoid arthritis trial).
- unresolved, no domain: no usable condition and no oncology signal; never general.

The decisions are pure and pinned (term_hits, drug_anchor, counted_universe, scope_case, permitted_packs);
`assign` gathers their inputs from the study record and assembles the Assignment and its words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from TrialLedger import contract

RULE = "universes.assign"
SOLID = "oncology.solid"
HEME = "oncology.heme"
GENERAL = "general"
TREATMENT = "TREATMENT"
# Anchors that name no kind of tumour: each counts as haematologic where a haematologic anchor holds.
UNSPECIFIC_ANCHORS = ("Neoplasms", "neoplasm", "cancer", "tumour", "tumor", "malignan", "L01", "L02")
# The ATC classes the drug source reads, each with its words.
DRUG_ANCHORS = {
    "L01": "antineoplastic agents (ATC L01)",
    "L02": "endocrine therapy for cancer (ATC L02)",
}
SOURCE_WORDS = {
    "condition_mesh": "condition MeSH",
    "free_text": "conditions",
    "titles": "title",
    "drug_class": "drug class",
}
# What each source did, in words.
SOURCE_STATUSES = {
    "read": "read",
    "no_terms": "the registry gives no condition MeSH term",
    "titles": "no condition names a disease; the titles were read",
    "conditions_and_titles": "no condition names a cancer; the titles were read too",
    "no_text": "no condition names a disease and the record has no title",
    "does_not_apply": "not a treatment trial: a drug's class is not read",
    "not_looked_up": "the drugs' classes were not looked up (relay mode, or a name never asked of RxNav)",
}
# The outcomes scope_case names, each with its words.
CASE_CODES = {
    "oncology": "an oncology universe",
    "general": "General: no domain readings apply",
    "unresolved_disagreement": "Scope unresolved — the sources disagree",
    "unresolved_no_domain": "Scope unresolved — no source identifies a domain",
}
_WORD = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class Assignment:
    """A trial's universe assignment.

    case            — "oncology", "general" or "unresolved" (contract.ASSIGNMENT_CASES);
    code            — the decision (CASE_CODES);
    universes       — the universes, in contract.UNIVERSES order; ("general",) for general, () unresolved;
    decided_by      — the first source whose finding decided, "" when unresolved;
    primary_purpose — the registry's primary purpose code, "" when the record states none;
    sources         — one dict per contract.ASSIGNMENT_SOURCES entry, in order: {"source", "status",
                      "found": [{"term", "anchor", "universe"}], "non_oncology": [terms]};
    packs           — "universe/pack" for every pack whose requirements hold (permitted_packs);
    words           — the Trial index words;
    conditions      — the free-text conditions as the registry gives them.
    """

    case: str
    code: str
    universes: tuple[str, ...]
    decided_by: str
    primary_purpose: str
    sources: tuple[dict[str, Any], ...]
    packs: tuple[str, ...]
    words: str
    conditions: tuple[str, ...] = ()


def term_hits(text: str, terms: list[tuple[str, str]]) -> list[str]:
    """The vocabulary terms a text names, in the order the text names them (pure — pinned).

    `terms` holds (term, match), match one of contract.TERM_MATCHES: "word" (a whole word), "prefix" (a word
    beginning with it) or "within" (anywhere within a word); words are runs of letters and digits, compared
    case-insensitively. Each term is listed once, at the first word it matches; terms matching the same word
    keep the table's order. No term matches: an empty list.
    """
    words = [word.lower() for word in _WORD.findall(text)]
    found: list[tuple[int, int, str]] = []
    for order, (term, match) in enumerate(terms):
        key = term.lower()
        for position, word in enumerate(words):
            if (
                (match == "word" and word == key)
                or (match == "prefix" and word.startswith(key))
                or (match == "within" and key in word)
            ):
                found.append((position, order, term))
                break
    return [term for _position, _order, term in sorted(found)]


def drug_anchor(codes: list[str]) -> str:
    """The ATC class among DRUG_ANCHORS that a drug's ATC codes fall under, or "" (pure — pinned).

    A code falls under an anchor when it begins with it ("L01EB" under "L01"); the first code that falls
    under one decides, in the order given. No code under an anchor (a placebo, a supportive drug): "".
    """
    for code in codes:
        for anchor in DRUG_ANCHORS:
            if code.startswith(anchor):
                return anchor
    return ""


def counted_universe(anchor: str, universe: str, haematologic: bool) -> str:
    """The universe a finding counts for (pure — pinned).

    A solid-tumour finding whose anchor names no kind of tumour (UNSPECIFIC_ANCHORS) counts as haematologic
    oncology where `haematologic` (some source finds a haematologic anchor); every other finding counts for
    its own universe.
    """
    if universe == SOLID and anchor in UNSPECIFIC_ANCHORS and haematologic:
        return HEME
    return universe


def scope_case(condition_oncology: bool, other_oncology: bool, non_oncology: bool) -> str:
    """How the sources decide (pure — pinned).

    `condition_oncology`: a condition source (the MeSH terms or the free-text conditions) finds an oncology
    anchor; `other_oncology`: the titles or a drug's class do; `non_oncology`: a condition is positively
    outside oncology (a condition MeSH term, or a free-text condition naming a disease, with no anchor).
      "oncology"                — the conditions signal oncology; or only the titles or a drug's class do and
                                  no condition is positively outside it;
      "unresolved_disagreement" — the conditions are outside oncology; only the titles or a drug signal it;
      "general"                 — the conditions are outside oncology, and nothing signals it;
      "unresolved_no_domain"    — nothing identifies a domain.
    """
    if condition_oncology:
        return "oncology"
    if other_oncology:
        return "unresolved_disagreement" if non_oncology else "oncology"
    return "general" if non_oncology else "unresolved_no_domain"


def permitted_packs(universes: list[str], primary_purpose: str) -> list[str]:
    """Every pack whose requirements hold, as "universe/pack", in contract.UNIVERSES order (pure — pinned).

    A pack of a universe the trial is in is permitted when each of its requirements holds: a "universe"
    requirement when one of `universes` is among its values, a "primary_purpose" requirement when
    `primary_purpose` is. A requirement of another kind never holds. Membership alone permits nothing.
    """
    permitted = []
    for universe in contract.UNIVERSES:
        if universe.name not in universes:
            continue
        for pack in universe.packs:
            held = [
                (requirement.kind == "universe" and any(name in requirement.values for name in universes))
                or (requirement.kind == "primary_purpose" and primary_purpose in requirement.values)
                for requirement in pack.requires
            ]
            if all(held):
                permitted.append(f"{universe.name}/{pack.name}")
    return permitted


def pack_scope(packs: tuple[str, ...]) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """The coherence coordinates the named packs compute, each with the packs that own it, and the relation
    ids they own, in contract.UNIVERSES order."""
    coordinates: dict[str, list[str]] = {}
    relations: dict[str, None] = {}
    for universe in contract.UNIVERSES:
        for pack in universe.packs:
            name = f"{universe.name}/{pack.name}"
            if name not in packs:
                continue
            for coordinate in pack.coordinates:
                coordinates.setdefault(coordinate, []).append(name)
            for relation in pack.relations:
                relations.setdefault(relation, None)
    return coordinates, tuple(relations)


def atc_classes(answers: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Each name's ATC codes from the run's RxNav answers (classes.json's "answers"): a name whose ATC was
    asked and answered (found, or found to have none) maps to its codes, () for none. A name whose ATC was
    never asked, or whose lookup failed, is left out, so it reads "not looked up", never "no class"."""
    codes = {}
    for name, answer in answers.items():
        atc = answer.get("axes", {}).get("ATC", {})
        if atc.get("code") in ("found", "not_found"):
            codes[name] = tuple(str(assertion[0]) for assertion in atc.get("assertions", []))
    return codes


# ── the shell: the sources gathered from the study record ──────────────────────────────────────────────


def _module(study: dict[str, Any], path: str) -> dict[str, Any]:
    node: Any = study
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, dict) else {}


def _terms(items: Any) -> list[str]:
    return [str(item["term"]) for item in items or [] if isinstance(item, dict) and item.get("term")]


def _distinct(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _anchors(source: str) -> dict[str, str]:
    return {
        anchor: universe
        for universe, name, anchors in contract.MESH_ANCHORS
        if name == source
        for anchor in anchors
    }


def _text_findings(texts: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    """The free-text findings of each text, and the texts with none."""
    haematologic = set(contract.HAEMATOLOGIC_TERMS)
    found, silent = [], []
    for text in texts:
        hits = term_hits(text, list(contract.ONCOLOGY_TERMS))
        found += [
            {"term": text, "anchor": hit, "universe": HEME if hit in haematologic else SOLID} for hit in hits
        ]
        if not hits:
            silent.append(text)
    return found, silent


def _specific_only(found: list[dict[str, str]]) -> list[dict[str, str]]:
    """A source's findings, an unspecific anchor dropped where the source has a specific one."""
    if all(finding["anchor"] in UNSPECIFIC_ANCHORS for finding in found):
        return found
    return [finding for finding in found if finding["anchor"] not in UNSPECIFIC_ANCHORS]


def _drug_findings(
    interventions: list[list[str]], drug_classes: dict[str, tuple[str, ...]] | None, purpose: str
) -> tuple[str, list[dict[str, str]]]:
    """The drug source's status and findings: per intervention, its first name (the name, then its other
    names) whose ATC codes fall under an anchor."""
    if purpose != TREATMENT:
        return "does_not_apply", []
    if drug_classes is None or not any(name in drug_classes for names in interventions for name in names):
        return "not_looked_up", []
    found = []
    for names in interventions:
        for name in names:
            anchor = drug_anchor(list(drug_classes.get(name, ())))
            if anchor:
                found.append({"term": name, "anchor": anchor, "universe": SOLID})
                break
    return "read", found


def _titled(source: dict[str, Any]) -> bool:
    """Whether a source's findings are the titles' (free text, where no condition names a cancer)."""
    return source["status"] in ("titles", "conditions_and_titles")


def _source_words(source: dict[str, Any], terms: list[str], titles: bool = False) -> str:
    name = "titles" if titles else source["source"]
    if source["source"] == "drug_class":
        terms = [f"{f['term']}, {DRUG_ANCHORS[f['anchor']]}" for f in source["found"]]
    return f"{SOURCE_WORDS[name]}: {'; '.join(_distinct(terms))}"


def _words(
    code: str, universes: list[str], sources: list[dict[str, Any]], mesh: list[str], conditions: list[str]
) -> str:
    """The Trial index words for an assignment: the universe and the source that decided it, or why none."""
    labels = {universe.name: universe.label for universe in contract.UNIVERSES}
    mesh_source, text_source, drug_source = sources
    if code == "oncology":
        decided = next(source for source in sources if source["found"])
        terms = mesh if decided is mesh_source and mesh else [f["term"] for f in decided["found"]]
        # A title is long: the first that signals cancer (the brief title, where it does) stands for both.
        terms = terms[:1] if _titled(decided) else terms
        named = [labels[name] for name in universes]
        named = [named[0], *(f"{label[0].lower()}{label[1:]}" for label in named[1:])]
        return f"{' and '.join(named)} ({_source_words(decided, terms, _titled(decided))})"
    outside = [
        _source_words(source, source["non_oncology"])
        for source in (mesh_source, text_source)
        if source["non_oncology"]
    ]
    if code == "general":
        return f"{CASE_CODES[code]} ({outside[0]})"
    if code == "unresolved_disagreement":
        signals = [
            _source_words(source, [f["term"] for f in source["found"]][:1], _titled(source))
            if source is text_source
            else _source_words(source, [])
            for source in (text_source, drug_source)
            if source["found"]
        ]
        return (
            f"{CASE_CODES[code]}: the conditions are outside oncology ({'; '.join(outside)}), "
            f"but {'; '.join(signals)} signals cancer"
        )
    why = {name.lower(): reason for name, reason in contract.NOT_DISEASE_CONDITIONS}
    named = [f"{c} ({why[c.strip().lower()]})" for c in conditions if c.strip().lower() in why]
    drug = drug_source["status"]
    drug_words = "no drug of an antineoplastic class" if drug == "read" else SOURCE_STATUSES[drug]
    return "; ".join(
        (
            f"{CASE_CODES[code]}: no condition MeSH term",
            f"the conditions name no disease ({'; '.join(named)})" if named else "no condition is stated",
            "no title names a cancer" if text_source["status"] == "titles" else "the record has no title",
            f"drug class: {drug_words}",
        )
    )


def assign(study: dict[str, Any], drug_classes: dict[str, tuple[str, ...]] | None = None) -> Assignment:
    """A study's universe assignment from its registry record (API v2 shape) and its drugs' ATC classes.

    `drug_classes` maps an intervention's name or other name to its ATC codes, as RxNav gave them (see
    atc_classes); None in relay mode, where none is looked up. Pure: nothing is fetched."""
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    purpose = str(_module(protocol, "designModule.designInfo").get("primaryPurpose") or "")
    browse = _module(study, "derivedSection.conditionBrowseModule")
    mesh = _distinct(_terms(browse.get("meshes")))
    mesh_anchors = _anchors("condition_mesh")
    mesh_found = _specific_only(
        [
            {"term": term, "anchor": term, "universe": mesh_anchors[term]}
            for term in _distinct(mesh + _terms(browse.get("ancestors")))
            if term in mesh_anchors
        ]
    )
    not_disease = {condition.lower() for condition, _why in contract.NOT_DISEASE_CONDITIONS}
    conditions = [str(c) for c in (protocol.get("conditionsModule") or {}).get("conditions") or []]
    usable = [c for c in conditions if c.strip() and c.strip().lower() not in not_disease]
    titles = [str(identification[key]) for key in ("briefTitle", "officialTitle") if identification.get(key)]
    condition_found, silent = _text_findings(usable)
    # A condition the vocabulary misses is no evidence either way: the titles are read too, and the unmatched
    # conditions count as outside oncology only where neither the conditions nor the titles name a cancer.
    title_found = [] if condition_found else _text_findings(titles)[0]
    if condition_found or not titles:
        text_status = "read" if usable else "no_text"
    else:
        text_status = "conditions_and_titles" if usable else "titles"
    text_found = condition_found or title_found
    interventions = [
        [str(entry["name"]), *(str(other) for other in entry.get("otherNames") or [])]
        for entry in (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
        if entry.get("name")
    ]
    drug_status, drug_found = _drug_findings(interventions, drug_classes, purpose)
    found = [mesh_found, _specific_only(text_found), drug_found]
    haematologic = any(finding["universe"] == HEME for findings in found for finding in findings)
    for findings in found:
        for finding in findings:
            finding["universe"] = counted_universe(finding["anchor"], finding["universe"], haematologic)
    sources: list[dict[str, Any]] = [
        {
            "source": "condition_mesh",
            "status": "read" if mesh else "no_terms",
            "found": mesh_found,
            "non_oncology": [] if mesh_found else mesh,
        },
        {
            "source": "free_text",
            "status": text_status,
            "found": found[1],
            "non_oncology": [] if text_found else silent,
        },
        {"source": "drug_class", "status": drug_status, "found": drug_found, "non_oncology": []},
    ]
    code = scope_case(
        bool(mesh_found or condition_found),
        bool(title_found or drug_found),
        bool(sources[0]["non_oncology"] or sources[1]["non_oncology"]),
    )
    counted = {finding["universe"] for findings in found for finding in findings}
    universes: list[str] = []
    decided_by = ""
    if code == "oncology":
        universes = [u.name for u in contract.UNIVERSES if u.name in counted]
        decided_by = str(next(source["source"] for source in sources if source["found"]))
    elif code == "general":
        universes = [GENERAL]
        decided_by = str(next(source["source"] for source in sources if source["non_oncology"]))
    case = "unresolved" if code.startswith("unresolved") else code
    return Assignment(
        case,
        code,
        tuple(universes),
        decided_by,
        purpose,
        tuple(sources),
        tuple(permitted_packs(universes, purpose)),
        _words(code, universes, sources, mesh, conditions),
        tuple(conditions),
    )


def reading(assignment: Assignment) -> dict[str, Any]:
    """The assignment as the record's value object (studies[].universe): its status, the rule, the words that
    decided (the deciding source's terms; for an unresolved scope, every source's and the conditions as
    written), the result and the Trial index words as its note."""
    decided = [s for s in assignment.sources if s["source"] == assignment.decided_by]
    if assignment.case == "oncology":
        words = [finding["term"] for source in decided for finding in source["found"]]
    elif assignment.case == "general":
        words = [term for source in decided for term in source["non_oncology"]]
    else:
        words = [
            term
            for source in assignment.sources
            for term in [*(f["term"] for f in source["found"]), *source["non_oncology"]]
        ] + list(assignment.conditions)
    return {
        "status": "unresolved" if assignment.case == "unresolved" else "known",
        "rule": RULE,
        "words": _distinct(words),
        "result": {
            "universes": list(assignment.universes),
            "decided_by": assignment.decided_by,
            "sources": [dict(source) for source in assignment.sources],
        },
        "note": assignment.words,
    }
