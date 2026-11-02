"""Universes: which domain readings a trial's record may carry (refine-landscape-record design §3).

A universe (contract.UNIVERSES) names the rule packs it owns; a rule outside every universe a trial is in is
never applied. Membership is not permission: each pack states what it requires (the trial's universe and,
for the setting and line-of-therapy packs, a treatment purpose and an intervention that treats the cancer)
before its coordinates are computed. What the interventions treat (treated_target) is read from the drug and
biological interventions' ATC classes and the radiation interventions: an antineoplastic drug or radiation
treats the cancer; drugs all read and of other classes (or placebo) do not; anything unread leaves the pack's
applicability unresolved, stated with its reason in the assignment and its words, never silently absent.

`assign` reads three named sources of the registry's study record, each recorded with what it found:
1. condition_mesh: the condition MeSH terms and their ancestors, matched whole against the MeSH anchors
   (contract.MESH_ANCHORS);
2. free_text: the free-text conditions, matched word by word against the declared vocabulary
   (contract.ONCOLOGY_TERMS); a condition that names no disease (contract.NOT_DISEASE_CONDITIONS, such as
   "Progression Free Survival") is no evidence of any domain. The titles are read where no condition names a
   cancer, only as a signal of oncology, never as evidence of another domain. A condition naming a term of
   the declared non-oncology vocabulary (contract.NON_ONCOLOGY_TERMS) counts as outside oncology only where
   neither the conditions nor the titles name a cancer; a condition naming neither vocabulary is no evidence;
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
  naming a non-oncology term) and no source signals oncology.
- unresolved, sources disagree: the conditions are positively outside oncology while the titles or a drug's
  class signal it (methotrexate, L01, in a rheumatoid arthritis trial).
- unresolved, no domain: no positive evidence of any domain and no oncology signal (no usable condition, or
  conditions naming neither vocabulary: "Unmapped condition ZYX-123"); never general.

The decisions are pure and pinned (term_hits, drug_anchor, counted_universe, scope_case, treated_target,
pack_applicability);
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
    "lookup_failed": "RxNav did not answer for a drug's class, so it cannot be read; the same run asks again",
}
# The outcomes scope_case names, each with its words.
CASE_CODES = {
    "oncology": "an oncology universe",
    "general": "General: no domain readings apply",
    "unresolved_disagreement": "Scope unresolved — the sources disagree",
    "unresolved_no_domain": "Scope unresolved — no source identifies a domain",
}
# The intervention types the drug source reads for what a trial treats, and the one that treats the cancer.
DRUG_TYPES = ("DRUG", "BIOLOGICAL")
RADIATION = "RADIATION"
# What pack_applicability names, each in words.
APPLICABILITY_CODES = {
    "permitted": "applies",
    "not_permitted_universe": "not applicable: the trial is not in the pack's universe",
    "not_permitted_primary_purpose": "not applicable: not a treatment trial",
    "not_permitted_treated_target": "not applicable: no intervention treats the cancer",
    "unresolved_treated_target": "applicability unresolved: what the interventions treat cannot be read",
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
    packs           — "universe/pack" for every pack whose requirements hold (pack_applicability);
    words           — the Trial index words, with every domain pack that does not apply and why;
    conditions      — the free-text conditions as the registry gives them;
    target          — what the interventions treat (treated_target), with its words;
    applicability   — each pack of the trial's universes: {"pack", "status", "words"}.
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
    target: dict[str, str] | None = None
    applicability: tuple[dict[str, str], ...] = ()


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


def treated_target(drugs: list[str], radiation: bool) -> str:
    """What the trial's interventions treat, as contract.TREATED_TARGETS names it (pure — pinned).

    `drugs` holds each drug or biological intervention's state, as the drug source read it: "anchored" (a
    name's ATC class is antineoplastic, L01 or L02), "classed" (an ATC class, none antineoplastic), "placebo"
    (its name says placebo), "unclassed" (RxNav gives no ATC class), "lookup_failed" or "not_looked_up";
    `radiation`: an intervention is of type RADIATION.
      "cancer"     — radiation, or an antineoplastic drug;
      "not_cancer" — a drug of another class, and every drug classed or a placebo;
      "unresolved" — otherwise: a drug unread (not looked up, its lookup failed, no ATC class), or no drug.
    """
    if radiation or "anchored" in drugs:
        return "cancer"
    if "classed" in drugs and all(state in ("classed", "placebo") for state in drugs):
        return "not_cancer"
    return "unresolved"


def pack_applicability(universes: list[str], primary_purpose: str, target: str) -> list[tuple[str, str]]:
    """Each pack of the trial's universes and whether it applies, in UNIVERSES order (pure — pinned).

    Each pack, as ("universe/pack", code): its requirements are read in order; a "universe" requirement holds
    when one of `universes` is among its values, a "primary_purpose" one when `primary_purpose` is, a
    "treated_target" one when `target` (treated_target's) is, and one of another kind never holds.
      "permitted"                     — every requirement holds;
      "not_permitted_<kind>"          — the first requirement that does not hold, by its kind;
      "unresolved_treated_target"     — every other requirement holds and `target` is "unresolved".
    Membership alone permits nothing; a pack of a universe the trial is not in is not listed.
    """
    applicability = []
    for universe in contract.UNIVERSES:
        if universe.name not in universes:
            continue
        for pack in universe.packs:
            failed, open_target = "", False
            for requirement in pack.requires:
                if requirement.kind == "treated_target" and target == "unresolved":
                    open_target = True
                    continue
                holds = (
                    (requirement.kind == "universe" and any(name in requirement.values for name in universes))
                    or (requirement.kind == "primary_purpose" and primary_purpose in requirement.values)
                    or (requirement.kind == "treated_target" and target in requirement.values)
                )
                if not holds and not failed:
                    failed = requirement.kind
            if failed:
                code = f"not_permitted_{failed}"
            else:
                code = "unresolved_treated_target" if open_target else "permitted"
            applicability.append((f"{universe.name}/{pack.name}", code))
    return applicability


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


def atc_classes(answers: dict[str, Any]) -> dict[str, tuple[str, ...] | None]:
    """Each name's ATC codes from the run's RxNav answers (classes.json's "answers"): a name whose ATC was
    asked and answered (found, or found to have none) maps to its codes, () for none; a name whose ATC
    lookup failed maps to None, so it reads "lookup failed", never "no class"; a name whose ATC was never
    asked is left out, so it reads "not looked up"."""
    codes: dict[str, tuple[str, ...] | None] = {}
    for name, answer in answers.items():
        atc = answer.get("axes", {}).get("ATC") if isinstance(answer, dict) else None
        if not isinstance(atc, dict) or "code" not in atc:
            continue
        if atc["code"] in ("found", "not_found"):
            codes[name] = tuple(str(assertion[0]) for assertion in atc.get("assertions", []))
        else:
            codes[name] = None
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


def _text_findings(texts: list[str]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """The free-text findings of each text; the texts naming a non-oncology term and none of oncology; and the
    texts naming a term of neither vocabulary, which are no evidence of any domain."""
    haematologic = set(contract.HAEMATOLOGIC_TERMS)
    found, outside, unmatched = [], [], []
    for text in texts:
        hits = term_hits(text, list(contract.ONCOLOGY_TERMS))
        found += [
            {"term": text, "anchor": hit, "universe": HEME if hit in haematologic else SOLID} for hit in hits
        ]
        if not hits:
            (outside if term_hits(text, list(contract.NON_ONCOLOGY_TERMS)) else unmatched).append(text)
    return found, outside, unmatched


def _specific_only(found: list[dict[str, str]]) -> list[dict[str, str]]:
    """A source's findings, an unspecific anchor dropped where the source has a specific one."""
    if all(finding["anchor"] in UNSPECIFIC_ANCHORS for finding in found):
        return found
    return [finding for finding in found if finding["anchor"] not in UNSPECIFIC_ANCHORS]


def _drug_findings(
    interventions: list[list[str]], drug_classes: dict[str, tuple[str, ...] | None] | None, purpose: str
) -> tuple[str, list[dict[str, str]]]:
    """The drug source's status and findings: per intervention, its first name (the name, then its other
    names) whose ATC codes fall under an anchor. With no anchor found, a failed lookup of any of the
    interventions' names makes the source "lookup_failed": a drug RxNav did not answer for might be one."""
    if purpose != TREATMENT:
        return "does_not_apply", []
    if drug_classes is None or not any(name in drug_classes for names in interventions for name in names):
        return "not_looked_up", []
    found = []
    for names in interventions:
        for name in names:
            anchor = drug_anchor(list(drug_classes.get(name) or ()))
            if anchor:
                found.append({"term": name, "anchor": anchor, "universe": SOLID})
                break
    failed = any(
        name in drug_classes and drug_classes[name] is None for names in interventions for name in names
    )
    if not found and failed:
        return "lookup_failed", []
    return "read", found


def _drug_state(names: list[str], drug_classes: dict[str, tuple[str, ...] | None] | None) -> str:
    """A drug intervention's state for treated_target, from the ATC answers for its name and other names."""
    answers = {
        name: drug_classes[name] for name in names if drug_classes is not None and name in drug_classes
    }
    codes = [code for held in answers.values() for code in held or ()]
    if drug_anchor(codes):
        return "anchored"
    if any(term_hits(name, [("placebo", "word")]) for name in names):
        return "placebo"
    if codes:
        return "classed"
    if any(held is None for held in answers.values()):
        return "lookup_failed"
    return "unclassed" if answers else "not_looked_up"


def _target(
    entries: list[tuple[str, list[str]]], drug_classes: dict[str, tuple[str, ...] | None] | None
) -> dict[str, str]:
    """What the interventions treat (treated_target), with its words: the drugs or radiation it rests on."""
    drugs = [(names[0], _drug_state(names, drug_classes)) for kind, names in entries if kind in DRUG_TYPES]
    radiation = [names[0] for kind, names in entries if kind == RADIATION]
    target = treated_target([state for _name, state in drugs], bool(radiation))

    def named(*states: str) -> str:
        return "; ".join(name for name, state in drugs if state in states)

    if target == "cancer":
        treats = [f"{named('anchored')} (antineoplastic)"] if named("anchored") else []
        words = "; ".join([*treats, *(f"{name} (radiation)" for name in radiation)])
    elif target == "not_cancer":
        words = f"every drug read is of another class ({named('classed', 'placebo')})"
    else:
        reasons = [
            (f"{why} ({named(state)})")
            for state, why in (
                ("not_looked_up", "the drugs' classes were not looked up"),
                ("lookup_failed", "RxNav did not answer for a drug's class"),
                ("unclassed", "RxNav gives no ATC class"),
            )
            if named(state)
        ]
        words = "; ".join(reasons) or "no intervention is a drug or radiation"
    return {"status": target, "words": words}


def _applicability(universes: list[str], purpose: str, target: dict[str, str]) -> list[dict[str, str]]:
    """Each pack of the trial's universes with whether it applies and why, in words."""
    rows = []
    for pack, code in pack_applicability(universes, purpose, target["status"]):
        words = APPLICABILITY_CODES.get(code, f"not applicable: {code}")
        if code.endswith("treated_target"):
            words = f"{words} ({target['words']})"
        rows.append({"pack": pack, "status": code, "words": words})
    return rows


def _titled(source: dict[str, Any]) -> bool:
    """Whether a source's findings are the titles' (free text, where no condition names a cancer)."""
    return source["status"] in ("titles", "conditions_and_titles")


def _source_words(source: dict[str, Any], terms: list[str], titles: bool = False) -> str:
    name = "titles" if titles else source["source"]
    if source["source"] == "drug_class":
        terms = [f"{f['term']}, {DRUG_ANCHORS[f['anchor']]}" for f in source["found"]]
    return f"{SOURCE_WORDS[name]}: {'; '.join(_distinct(terms))}"


def _words(
    code: str,
    universes: list[str],
    sources: list[dict[str, Any]],
    mesh: list[str],
    conditions: list[str],
    unmatched: list[str],
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
    parts = [f"{CASE_CODES[code]}: no condition MeSH term"]
    if named:
        parts.append(f"the conditions name no disease ({'; '.join(named)})")
    if unmatched:
        parts.append(f"no condition names a term of the declared vocabularies ({'; '.join(unmatched)})")
    if not conditions:
        parts.append("no condition is stated")
    parts.append("no title names a cancer" if _titled(text_source) else "the record has no title")
    parts.append(f"drug class: {drug_words}")
    return "; ".join(parts)


def assign(
    study: dict[str, Any], drug_classes: dict[str, tuple[str, ...] | None] | None = None
) -> Assignment:
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
    condition_found, outside, unmatched = _text_findings(usable)
    # A condition naming no cancer leaves the titles to read; a condition naming a non-oncology term counts
    # as outside oncology only where neither the conditions nor the titles name a cancer, and a condition
    # naming neither vocabulary is no evidence at all.
    title_found = [] if condition_found else _text_findings(titles)[0]
    if condition_found or not titles:
        text_status = "read" if usable else "no_text"
    else:
        text_status = "conditions_and_titles" if usable else "titles"
    text_found = condition_found or title_found
    entries = [
        (str(entry.get("type") or ""), [str(entry["name"]), *(str(o) for o in entry.get("otherNames") or [])])
        for entry in (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
        if isinstance(entry, dict) and entry.get("name")
    ]
    interventions = [names for _kind, names in entries]
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
            "non_oncology": [] if text_found else outside,
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
    target = _target(entries, drug_classes)
    applicability = _applicability(universes, purpose, target)
    # A domain pack that computes coordinates and does not apply for what the trial treats says so where the
    # universe is shown: its absence is never silent.
    labels = {f"{u.name}/{p.name}": p.label for u in contract.UNIVERSES for p in u.packs if p.coordinates}
    withheld = [
        f"{labels[row['pack']]}: {row['words']}"
        for row in applicability
        if row["status"].endswith("treated_target") and row["pack"] in labels
    ]
    return Assignment(
        case,
        code,
        tuple(universes),
        decided_by,
        purpose,
        tuple(sources),
        tuple(row["pack"] for row in applicability if row["status"] == "permitted"),
        "; ".join([_words(code, universes, sources, mesh, conditions, unmatched), *withheld]),
        tuple(conditions),
        target,
        tuple(applicability),
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
            "treated_target": dict(assignment.target or {}),
            "applicability": [dict(row) for row in assignment.applicability],
        },
        "note": assignment.words,
    }
