"""landscape.json schema 3: the record an assistant answers from (refine-landscape-record, design §1 and §2).

One record per run, laid out by the contract (`contract.FIELDS`): the request; the resolved scope; the
manifest (the registry snapshot read, each study's digest and their Merkle root, the code commit, the rule
versions, the retrieval coverage); the universes and their rule packs as run; per study, every contract field
the registry record holds, its key criteria among them; across the cohort, the findings the evidence supports
and the standard protocol language of each universe's trials; and the record's own
description: `statuses`, `envelope` (what each key of a value object means) and `fields`, the field dictionary
that states each field's label, kind and API path or rule once.

How a value is held:
- a registry value is held plain, exactly as the registry holds it (its precision, units and wording; a
  registry "NA" stays "NA", with its comment beside it); its API path is stated once, in `fields`;
- a study's or a results module's own field the registry does not hold is a value object
  {"status": "not_stated", "note": <the ledger's absence state>}; a results module of a study that posted no
  results is {"status": "not_posted", "note": ...};
- inside an element of a registry list (an arm, a posted measurement, an adverse event's count), a key the
  registry does not hold is left out, as the registry leaves it out (an untitled class is the registry's one
  class of a measure, not a missing value);
- a rule's reading is a value object {"status", "rule", "words", "result", "note"}: the contract's rule for
  the field, the words it read, what it found, its status and why;
- a domain reading (a treatment setting, prior lines, gene selection) is present only where the study's
  universe assignment (`universes.assign`) admits its pack; elsewhere it is absent and the universe reading
  says why.

Results, baseline, participant flow and adverse events keep the registry's own nesting, each module's groups
keyed within the module by the registry's group IDs, denominators at the scope the registry gives them, its
listed zeros kept. Every element sits at a stable place (the registry's order), so a JSON pointer into
landscape.json names any value exactly. A registered outcome is planned, never efficacy: registered outcomes
and posted measures are different fields.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from typing import Any

from TrialLedger import __version__, coherence, contract, universes, warrants
from TrialLedger.banks import endpoint_classes, time_points
from TrialLedger.coherence import RELATIONS, SETTINGS, STATES, level_status
from TrialLedger.contract import FIELDS as CONTRACT_FIELDS
from TrialLedger.contract import holds_value, template_values
from TrialLedger.criteria import criterion_role
from TrialLedger.design import VERSION as DESIGN_VERSION
from TrialLedger.design import _profile_trials
from TrialLedger.ledger import APPLIES_TO, REDACTED_WHEN_WITHHELD, absence_state, get, results_state
from TrialLedger.links import document_link, study_link
from TrialLedger.profile import (
    SIGNAL_MIN_SPONSORS,
    SIGNAL_MIN_TRIALS,
    STANDARD_SHARE,
    element_key,
    frequency_rows,
    mechanism_rows,
    occupancy_rows,
)
from TrialLedger.reading import effective_section
from TrialLedger.symbolic import _axes
from TrialLedger.typematrix import UNIVERSE
from TrialLedger.workbook import CODE_ROOT, RESULTS_TEXT

SCHEMA_VERSION = contract.SCHEMA_VERSION
JSON_NAME = "landscape.json"
STUDY = "studies[]"
# The eligibility text's API path: what every criterion, its role and its readings were read from.
ELIGIBILITY_TEXT = "protocolSection.eligibilityModule.eligibilityCriteria"
READING_KEYS = ("status", "rule", "words", "result", "note")
ABSENT_KEYS = ("status", "note")
# What each key of a value object means; the record carries it as `envelope`.
ENVELOPE_MEANINGS = {
    "status": "how far the value can be relied on: one of `statuses`",
    "rule": "the named rule that read it (the contract's rule for its field, as `fields` names it)",
    "words": "the words the rule read, as the registry holds them (empty when it read no words)",
    "result": "what the rule found",
    "note": "why: for a value not stated, the ledger's absence state (not_reported, not_applicable, "
    "redacted); for one unresolved or proposed, why; otherwise empty",
}
STATUSES = {
    "known": "read from the record as it holds it, or derived from it by a named rule that reads what it "
    "states (a typed criterion, a class the record or RxClass states, a strict relation's conclusion); never "
    "a default's",
    "interpolated": "assumed until overruled: a default relation's conclusion, or a guess from a rule over "
    "the record's wording (a name's stem); never a reading, and built on only where a consumer says so",
    "proposed": "a proposal's narrowing, each on its own: shown, never built on and never reported as known",
    "not_stated": "the registry record holds no value; the note gives the ledger's absence state; never zero "
    "or no",
    "not_posted": "no results are posted for the study (the registry's own flag): nothing is reported",
    "unresolved": "the rules cannot settle it from the record; the note says why; it is not an absence",
}
# The words a drug class's state is explained in (design §2): why a class is or is not known.
CLASS_NOTES = {
    "classified": "",
    "stated_by_record": "the intervention's own entry states the class; RxClass gives none",
    "unresolved": "RxClass holds no class for this name (the name is not in RxNorm, or RxNorm gives it none)",
    "lookup_failed": "the lookup failed; it is asked again on the next run",
    "not_looked_up": "not looked up (in relay mode the gathered trials' drug classes are not looked up)",
}
OUTCOME_KINDS = (
    ("primary", "primaryOutcomes"),
    ("secondary", "secondaryOutcomes"),
    ("other", "otherOutcomes"),
)
# The words of a "which list" field: the list that holds the entry.
LIST_WORDS = {
    "primaryOutcomes": "primary",
    "secondaryOutcomes": "secondary",
    "otherOutcomes": "other",
    "seriousEvents": "serious",
    "otherEvents": "other",
}
# The results modules a study holds as sections or lists, each with the registry's module it reads.
RESULTS_MODULES = {
    "posted_outcomes": ("resultsSection", "outcomeMeasuresModule"),
    "baseline": ("resultsSection", "baselineCharacteristicsModule"),
    "participant_flow": ("resultsSection", "participantFlowModule"),
    "adverse_events": ("resultsSection", "adverseEventsModule"),
}
# Reading fields held plain: a criterion's heading, number and text (the registry's text as itemized) and a
# key criterion's text, role, reading and rule (the parts of one reading, each its own field).
ITEMIZED = (
    "studies[].criteria[].heading",
    "studies[].criteria[].number",
    "studies[].criteria[].text",
    "studies[].key_criteria[].text",
    "studies[].key_criteria[].role",
    "studies[].key_criteria[].reading",
    "studies[].key_criteria[].rule",
)
ALL_TRIALS = "all trials"  # the stratum design.xlsx's profile names the whole cohort by
ENDPOINT_ELEMENT = "primary:endpoint:"  # an element the cohort's endpoints hold, never a criterion's
# The columns of each cohort table, in the order of its rows' values.
FREQUENCY_COLUMNS = (
    "stratum",
    "element",
    "stating",
    "absent",
    "unresolved_empty",
    "unresolved_no_rule_match",
    "unresolved_abbreviated",
    "unresolved_unspecified",
    "unresolved",
    "trials",
    "statement_rate",
    "lower_bound",
    "upper_bound",
    "surprisal_bits",
    "sponsors",
    "standard_tier",
    "estimand",
)
MECHANISM_COLUMNS = (
    "stratum",
    "class",
    "element",
    "in_class_stating",
    "in_class",
    "others_stating",
    "others",
    "rate_in_class",
    "rate_in_others",
    "difference",
    "least_favourable_difference",
    "sponsors",
    "unresolved_class_trials",
    "abbreviated_in_class",
    "abbreviated_in_others",
    "status",
)
OCCUPANCY_COLUMNS = ("setting", "class", "occupying", "could_fall_here", "state")
PAIR_COLUMNS = (
    "a",
    "b",
    "difference",
    "value_a",
    "value_b",
    "sponsor_a",
    "sponsor_b",
    "start_year_a",
    "start_year_b",
    "predicates_agreeing",
)
NEAR_MISS_COLUMNS = (*PAIR_COLUMNS, "rests_on")
ALIGNED_COLUMNS = (*PAIR_COLUMNS, "basis_a", "basis_b", "rests_on")
ENDPOINT_COLUMNS = ("outcome_type", "endpoint_class", "trials", "ncts", "outcomes", "time_points")
STRUCTURE_COLUMNS = ("rxcui_a", "name_a", "rxcui_b", "name_b", "taxonomy", "class", "release")
QUESTION_KEYS = ("kind", "element", "why", "priority", "question", "options")
MANIFEST_KEYS = (
    "api_version",
    "data_timestamp",
    "study_digests",
    "merkle_root",
    "code_commit",
    "rule_versions",
    "retrieval",
)
RULE_VERSIONS = {
    "landscape_schema": SCHEMA_VERSION,
    "contract": contract.CONTRACT_VERSION,
    "trialledger": __version__,
    "design": DESIGN_VERSION,
    "derivation_code_root": CODE_ROOT,
    "relations": {relation.id: relation.approval for relation in RELATIONS},
    # each relation's kind (add-scoped-reasoning, Decision 2): what its conclusion is, apart from its approval
    "relation_kinds": {relation.id: relation.kind for relation in RELATIONS},
    "universes": {
        "table": contract.UNIVERSE_TABLE_VERSION,
        **{universe.name: universe.version for universe in contract.UNIVERSES},
    },
    "display": contract.DISPLAY_VERSION,
}
# The record's sections, in order; `cohort` omits a table that holds no row.
RECORD_KEYS = (
    "schema_version",
    "request",
    "scope",
    "manifest",
    "universes",
    "coverage",
    "cohort",
    "standard_language",
    "statuses",
    "envelope",
    "fields",
    "studies",
)

# ── the field dictionary and the shape the contract gives a study ─────────────────────────────────────


def field_dictionary() -> dict[str, dict[str, Any]]:
    """Every contract field once: its label, kind, API paths or rule, form, display dictionary and the paths
    a reading reads. The record carries it as `fields`."""
    return {
        field.name: {
            "label": field.label,
            "kind": field.kind,
            "source": list(field.source),
            "form": field.form,
            "display": field.display,
            "reads": list(field.reads),
        }
        for field in CONTRACT_FIELDS
    }


FIELD_DICTIONARY = field_dictionary()
KINDS = {field.name: field.kind for field in CONTRACT_FIELDS}
# A study's plain fields, each as (its path below the study, its API path templates, its form).
PLAIN_FIELDS: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = tuple(
    (tuple(field.name.removeprefix(f"{STUDY}.").split(".")), field.source, field.form)
    for field in CONTRACT_FIELDS
    if field.kind == "plain" and field.name.startswith(f"{STUDY}.")
)


def list_prefix(template: str) -> str:
    """The API path of the list a template's first "[]" segment names, "" when it names none (pure).

    "a.b[].c" gives "a.b[]"; "a.b[].c[].d" gives "a.b[]"; "a.b" gives "".
    """
    head, mark, _rest = template.partition("[]")
    return f"{head}[]" if mark else ""


def below(template: str, prefix: str) -> str:
    """A template relative to the list prefix that holds it: "" for the list's own entries (pure).

    `prefix` is list_prefix's for `template`, or "" for a template not in a list. "a.b[].c" below "a.b[]" is
    "c"; "a.b[]" below "a.b[]" is ""; any template below "" is itself.
    """
    if not prefix:
        return template
    return template.removeprefix(prefix).removeprefix(".")


def leaf_value(node: Any, template: str, form: str, list_word: str) -> tuple[str, Any]:
    """One plain field's value at a template of a registry node, by the field's form (pure — pinned).

    Returns (held, value) or (absent, None):
      which list — the word of the list that holds the entry (`list_word`), held when there is one;
      count      — how many entries the template lists, held when it lists one or more;
      distinct   — the distinct values, in the registry's order, held when there is one;
      as held    — a template through a list ("[]"): every value, in order; otherwise the one value;
                   held when contract.holds_value says so (zero and false are values; None, "" and empty
                   lists and objects are not).
    """
    if form == "which list":
        return ("held", list_word) if list_word else ("absent", None)
    values = template_values(node, template) if template else []
    if form == "count":
        return ("held", len(values)) if values else ("absent", None)
    if form == "distinct":
        distinct = list(dict.fromkeys(value for value in values if holds_value(value)))
        return ("held", distinct) if distinct else ("absent", None)
    value = values if "[]" in template else (values[0] if values else None)
    return ("held", value) if holds_value(value) else ("absent", None)


def absent(status: str, note: str) -> dict[str, str]:
    """A value the registry does not hold: its status and why."""
    return {"status": status, "note": note}


def value_object(status: str, rule: str, words: list[str], result: Any, note: str) -> dict[str, Any]:
    """A rule's reading: its status, rule, the words it read, what it found and why."""
    return {"status": status, "rule": rule, "words": words, "result": result, "note": note}


def absence_note(study: dict[str, Any], template: str) -> str:
    """The ledger's absence state for a study's field at an API path template."""
    path = template.replace("[]", "")
    return absence_state(
        False,
        path in REDACTED_WHEN_WITHHELD,
        APPLIES_TO.get(path),
        get(study, "protocolSection", "designModule", "studyType"),
        get(study, "protocolSection", "statusModule", "overallStatus"),
    )


def assemble(
    node: Any,
    fields: Sequence[tuple[tuple[str, ...], tuple[str, ...], str]],
    note: Callable[[str], str] | None,
    list_word: str = "",
) -> dict[str, Any]:
    """The record's object for one registry node, every plain field the contract gives it.

    `fields` are (the path below this object, the API templates relative to `node`, the form). A path of one
    segment is a field: its value (leaf_value), or, where the registry holds none, `note`'s absence object
    for a study's or a module's own field, nothing for an element of a list (`note` None). A segment ending
    "[]" is a list: its elements, for each of the field's alternative registry lists in turn (the primary,
    secondary and other outcomes; the serious and other events), each element assembled from its own node.
    Any other segment is an object of this node.
    """
    held: dict[str, Any] = {}
    grouped: dict[str, list[tuple[tuple[str, ...], tuple[str, ...], str]]] = {}
    for path, templates, form in fields:
        grouped.setdefault(path[0], []).append((path, templates, form))
    for head, members in grouped.items():
        path, templates, form = members[0]
        if len(path) == 1:
            outcome, value = leaf_value(node, templates[0], form, list_word)
            if outcome == "held":
                held[head] = value
            elif note is not None:
                held[head] = absent("not_stated", note(templates[0]))
            continue
        below_path = [(p[1:], t, f) for p, t, f in members]
        if not head.endswith("[]"):
            held[head] = assemble(node, below_path, note, list_word)
            continue
        prefixes = [list_prefix(template) for template in templates]
        items = []
        for index, prefix in enumerate(prefixes):
            word = LIST_WORDS.get(prefix.removesuffix("[]").rpartition(".")[2], "")
            for element in template_values(node, prefix):
                inner = [(p, (below(t[index], prefix),), f) for p, t, f in below_path]
                items.append(assemble(element, inner, None, word))
        held[head.removesuffix("[]")] = items
    return held


# ── the readings of one study ─────────────────────────────────────────────────────────────────────────


def results_reading(state: str) -> dict[str, Any]:
    """Whether a study's results are posted, from ledger.results_state's code (pure — pinned).

    posted            — known, "results posted";
    not_posted        — not_posted, "no results posted": nothing posted is reported, and a registered outcome
                        is never put in its place;
    flag_not_reported — not_stated (the registry's flag is absent), the code as its note;
    any other code    — unresolved (the flag and the results section disagree), the code as its note.
    """
    rule = "ledger.results_state"
    if state == "posted":
        return value_object("known", rule, [], RESULTS_TEXT[state], "")
    if state == "not_posted":
        return value_object("not_posted", rule, [], RESULTS_TEXT[state], "")
    status = "not_stated" if state == "flag_not_reported" else "unresolved"
    return value_object(status, rule, [], RESULTS_TEXT.get(state, state), state)


def module_absence(state: str) -> dict[str, str]:
    """A results module the registry does not hold, from the study's results state (pure — pinned).

    not_posted — the study posted no results: not_posted;
    otherwise  — results are posted (or the flag and the section disagree) but this module is not among
                 them: not_stated, not_reported.
    """
    if state == "not_posted":
        return absent("not_posted", "no results are posted for the study")
    return absent("not_stated", "not_reported")


def coordinate_readings(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """One design coordinate as coherence.resolve gives it, at its three levels (pure — pinned).

    `row` is resolve's row for the coordinate. Returns ("", known), ("_interpolated",
    interpolated) and, when a proposal narrows it, ("_proposed", proposed), each a reading of
    coherence.resolve whose result is the domain left at that level:
      known        — known when one value remains, unresolved when several or none (a conflict); the note
                     names the domain's state, each removal and the packs that own the coordinate;
      interpolated — the known value's status when the default relations leave it as it is (noted so);
                     interpolated when they narrow it to one or more values, unresolved when to none;
      proposed     — each proposal's narrowing alone ({relation, domain}), proposed when every one leaves a
                     value, unresolved when one leaves none; never built on.
    """
    rule = "coherence.resolve"
    known = list(row["domain"])
    removals = [f"{'|'.join(removed)} removed by {cause}" for _, removed, cause in row["causes"]]
    packs = [f"pack {pack}" for pack in row.get("packs", [])]
    note = "; ".join([row["state"], *removals, *packs])
    found = [("", value_object(level_status("known", tuple(known), tuple(known)), rule, [], known, note))]
    interpolated = list(row["interpolated"]["domain"])
    if interpolated == known:
        held = "no default relation narrows it"
    else:
        added = [f"{'|'.join(r)} removed by {cause}" for _, r, cause in row["interpolated"]["causes"]]
        held = "; ".join([row["interpolated"]["state"], *added])
    status = level_status("interpolated", tuple(interpolated), tuple(known))
    found.append(("_interpolated", value_object(status, rule, [], interpolated, held)))
    proposals = [
        {"relation": proposal["relation"], "domain": list(proposal["domain"])}
        for proposal in row["proposals"]
    ]
    if proposals:
        status = "proposed" if all(p["domain"] for p in proposals) else "unresolved"
        words = "each proposal alone, never built on"
        found.append(("_proposed", value_object(status, rule, [], proposals, words)))
    return found


def selection_readings(rows: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Gene selection, per gene, at its three levels (pure).

    `rows` map each gene to coherence.resolve's row for its "selection:<gene>" coordinate. A level's result
    names each gene whose domain that level narrows below every state (negative, positive, unknown):
      known        — known when it names one or more genes each with one state, unresolved otherwise (no
                     gene's state stated, several states left, or none: a conflict);
      interpolated — the known value's status when no default narrows any gene further; else interpolated
                     when every gene it names keeps a state, unresolved when one keeps none;
      proposed     — present only when a proposal narrows a gene: each gene's narrowings, proposed when each
                     leaves a state, unresolved when one leaves none.
    """
    rule = "coherence.resolve"
    full = list(STATES)
    known = {gene: list(row["domain"]) for gene, row in rows.items() if list(row["domain"]) != full}
    single = bool(known) and all(len(domain) == 1 for domain in known.values())
    note = "" if known else "no gene's state is stated"
    found = [("", value_object("known" if single else "unresolved", rule, [], known, note))]
    interpolated = {
        gene: list(row["interpolated"]["domain"])
        for gene, row in rows.items()
        if list(row["interpolated"]["domain"]) != full
    }
    if interpolated == known:
        found.append(
            (
                "_interpolated",
                value_object(found[0][1]["status"], rule, [], known, "no default relation narrows it"),
            )
        )
    else:
        kept = all(interpolated.values())
        status = "interpolated" if kept else "unresolved"
        found.append(("_interpolated", value_object(status, rule, [], interpolated, "")))
    proposals = {
        gene: [{"relation": p["relation"], "domain": list(p["domain"])} for p in row["proposals"]]
        for gene, row in rows.items()
        if row["proposals"]
    }
    if proposals:
        kept = all(p["domain"] for held in proposals.values() for p in held)
        status = "proposed" if kept else "unresolved"
        found.append(
            ("_proposed", value_object(status, rule, [], proposals, "each proposal alone, never built on"))
        )
    return found


def coordinate_section(resolved: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The study's domain readings: each coordinate resolve gives (only those the study's universe admits),
    at its three levels; gene selection gathered into one reading per level."""
    held: dict[str, dict[str, Any]] = {}
    for name in ("setting", "prior_advanced_lines"):
        if name in resolved:
            for suffix, value in coordinate_readings(resolved[name]):
                held[f"{name}{suffix}"] = value
    genes = {name.partition(":")[2]: row for name, row in resolved.items() if name.startswith("selection:")}
    if genes:
        for suffix, value in selection_readings(genes):
            held[f"selection{suffix}"] = value
    return held


def drug_class_reading(found: list[Any]) -> dict[str, Any]:
    """An experimental drug's class as the reading found it (pure).

    `found` is the reading's [drug, state, classes, resolved by]. classified (NLM RxClass's FDA established
    pharmacologic class) and stated_by_record (the class its own entry states, known by the founder's decision
    of 2026-10-31) are known; any other state is unresolved, its note saying why in words (CLASS_NOTES; a
    state without words names itself).
    """
    drug, state, classes, resolved_by = found
    status = "known" if state in ("classified", "stated_by_record") else "unresolved"
    result = {"state": state, "classes": list(classes), "resolved_by": resolved_by}
    return value_object(status, "classes.drug_class", [drug], result, CLASS_NOTES.get(state, state))


def axes_reading(axes: dict[str, Any]) -> dict[str, Any]:
    """An experimental drug's axes as the reading gives them: known when its own name's RxNorm identity is
    resolved, else unresolved with the identity code and its reason."""
    status = "known" if axes["identity"] == "resolved" else "unresolved"
    note = "" if status == "known" else f"{axes['identity']}: {axes['reason']}"
    return value_object(status, "classes.drug_axes", [axes["drug"]], _axes(axes), note)


def modality_reading(extractions: list[tuple]) -> dict[str, Any]:
    """The modality facets and cell properties one intervention entry states, each with its own status and
    where it was read: known when every extraction is, interpolated when one rests on a name's stem."""
    result = [
        {"property": e[1], "value": e[2], "polarity": e[3], "scope": e[4], "where": e[5], "status": e[7]}
        for e in extractions
    ]
    status = "known" if all(e[7] == "known" for e in extractions) else "interpolated"
    words = list(dict.fromkeys(e[5] for e in extractions))
    return value_object(status, "modality.entry_properties", words, result, "")


def criterion_entries(criteria: list[tuple]) -> list[dict[str, Any]]:
    """A study's criteria as itemized, each with its role and its readings (pure).

    `criteria` are the reading's (piece, section, text, atoms), in the text's order. Each criterion: its
    heading (the section it sits under), its number within that section, its text as written, its role
    (criteria.criterion_role: known when the wording and the heading settle it, unresolved otherwise, the
    role words as its words) and one reading per atom a bank typed (banks.type_criterion: the span it rests on
    as its words; the bank, concept, values, params, effective section and element key as its result). A
    criterion no bank typed has no reading; that does not mean it carries no clinical information.
    """
    counts: dict[str, int] = {}
    entries = []
    for _piece, section, text, atoms in criteria:
        counts[section] = counts.get(section, 0) + 1
        role, words = criterion_role(text, section)
        readings = []
        for bank, concept, values, params, start, end in atoms:
            effective = effective_section(section, params)
            result = {
                "bank": bank,
                "concept": concept,
                "values": list(values),
                "params": dict(params),
                "section": effective,
                "element": element_key(effective, concept, values, params),
            }
            readings.append(value_object("known", "banks.type_criterion", [text[start:end]], result, ""))
        entries.append(
            {
                "heading": section,
                "number": counts[section],
                "text": text,
                "role": value_object(
                    "unresolved" if role == "unresolved" else "known",
                    "criteria.criterion_role",
                    list(words),
                    role,
                    "the wording and the heading do not settle it" if role == "unresolved" else "",
                ),
                "readings": readings,
            }
        )
    return entries


def biomarker_mentions(
    criteria: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Each biomarker a criterion's reading names and each registered outcome whose measure names a biomarker
    endpoint, as a mention: its words, role and the rule that read it (pure).

    `criteria` are criterion_entries's, `outcomes` the study's registered outcomes, each with its category,
    measure and endpoint-class reading. A criterion's mention: the biomarker, the states it allows, its role
    (the atom's effective section) and the criterion's place among the study's criteria; an outcome's: no
    biomarker named, its role "<category> outcome" and the outcome's place. Every mention known.
    """
    rule = "banks.biomarker_status"
    found = []
    for index, criterion in enumerate(criteria):
        for reading in criterion["readings"]:
            concept = reading["result"]["concept"]
            if not concept.startswith("biomarker:"):
                continue
            result = {
                "biomarker": concept.removeprefix("biomarker:"),
                "states": list(reading["result"]["values"]),
                "role": reading["result"]["section"],
                "at": f"criteria/{index}",
            }
            found.append(value_object("known", rule, list(reading["words"]), result, ""))
    for index, outcome in enumerate(outcomes):
        classes = outcome.get("endpoint_classes", {}).get("result", [])
        if "biomarker_endpoint" not in classes:
            continue
        result = {
            "biomarker": None,
            "states": [],
            "role": f"{outcome.get('category')} outcome",
            "at": f"registered_outcomes/{index}",
        }
        words = [outcome["measure"]] if isinstance(outcome.get("measure"), str) else []
        found.append(
            value_object("known", rule, words, result, "a biomarker endpoint (banks.endpoint_classes)")
        )
    return found


def key_category(concept: str, values: list[str]) -> str:
    """The key-criterion category a typed reading falls in, "" for none (pure — pinned).

    The first of contract.KEY_CRITERION_CATEGORIES with a matcher (concept, values) whose concept is the
    reading's (or, ending ":", begins it) and whose values are empty or share a value with the reading's.
    """
    for name, _label, matchers in contract.KEY_CRITERION_CATEGORIES:
        for wanted, accepted in matchers:
            same = concept.startswith(wanted) if wanted.endswith(":") else concept == wanted
            if same and (not accepted or set(accepted) & set(values)):
                return name
    return ""


def key_criteria(criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The study's key criteria: each criterion with a reading in a key category, once (pure).

    `criteria` are criterion_entries's. For each criterion, in order, with one or more readings in a key
    category (key_category): its text as written, its role (its role reading's result), the reading (the
    labels of the categories it falls in, in the order first met; the criterion's place among the study's
    criteria; and each reading in a category: the category's label, the concept and the values) and the rule,
    landscape.key_criteria. A criterion falling in several categories is one entry naming them all.
    """
    labels = {name: label for name, label, _matchers in contract.KEY_CRITERION_CATEGORIES}
    found = []
    for index, criterion in enumerate(criteria):
        readings = []
        for reading in criterion["readings"]:
            category = key_category(reading["result"]["concept"], reading["result"]["values"])
            if category:
                readings.append(
                    {
                        "category": labels[category],
                        "concept": reading["result"]["concept"],
                        "values": reading["result"]["values"],
                    }
                )
        if not readings:
            continue
        categories = list(dict.fromkeys(held["category"] for held in readings))
        found.append(
            {
                "text": criterion["text"],
                "role": criterion["role"]["result"],
                "reading": {"categories": categories, "at": f"criteria/{index}", "readings": readings},
                "rule": "landscape.key_criteria",
            }
        )
    return found


def standard_language(studies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Standard protocol language: each criterion reading most trials of one universe state (pure — pinned).

    `studies` are the record's studies (their nct, universe reading and criteria). A trial counts in each
    universe its universe reading names ("unresolved scope" when it names none). Within a universe of at least
    contract.STANDARD_LANGUAGE_MIN_TRIALS trials, a reading (its element key) is standard when the trials
    stating it are at least that many and at least contract.STANDARD_LANGUAGE_SHARE of the universe's trials.
    Each row: the criterion (the universe, the element, its concept and values), its role (the effective
    section), the trials stating it of the universe's trials, the representative wording (the shortest
    statement and the longest other one) with where each is from (trial, heading, number, address) and the
    other trials stating it; rows by universe, then most trials, then element. A universe with too few trials
    is one row: its criterion names the universe and why, and it states no wording.
    """
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for position, study in enumerate(studies):
        for name in study["universe"]["result"]["universes"] or ["unresolved scope"]:
            groups.setdefault(name, []).append((position, study))
    least = contract.STANDARD_LANGUAGE_MIN_TRIALS
    rows = []
    for universe in sorted(groups):
        members = groups[universe]
        if len(members) < least:
            reason = too_few(len(members), least)
            criterion = {"universe": universe, "element": None, "reason": reason}
            rows.append(
                {
                    "criterion": criterion,
                    "role": "",
                    "trials": 0,
                    "of_trials": len(members),
                    "wording": [],
                    "wording_from": [],
                    "other_trials": [],
                }
            )
            continue
        stated: dict[str, dict[str, Any]] = {}
        for position, study in members:
            for index, criterion in enumerate(study["criteria"]):
                for reading in criterion["readings"]:
                    result = reading["result"]
                    entry = stated.setdefault(
                        result["element"],
                        {"concept": result["concept"], "values": result["values"], "role": result["section"]},
                    )
                    entry.setdefault("wording", []).append(
                        {
                            "text": criterion["text"],
                            "nct": study["nct"],
                            "heading": criterion["heading"],
                            "number": criterion["number"],
                            "at": f"/studies/{position}/criteria/{index}",
                        }
                    )
        found = []
        for element, entry in stated.items():
            trials = sorted({wording["nct"] for wording in entry["wording"]})
            if len(trials) < least or len(trials) < contract.STANDARD_LANGUAGE_SHARE * len(members):
                continue
            ordered = sorted(entry["wording"], key=lambda w: (len(w["text"]), w["nct"], w["number"], w["at"]))
            shown = [ordered[0]] + ([ordered[-1]] if ordered[-1]["text"] != ordered[0]["text"] else [])
            sources = {wording["nct"] for wording in shown}
            criterion = {
                "universe": universe,
                "element": element,
                "concept": entry["concept"],
                "values": entry["values"],
            }
            found.append(
                {
                    "criterion": criterion,
                    "role": entry["role"],
                    "trials": len(trials),
                    "of_trials": len(members),
                    "wording": [wording["text"] for wording in shown],
                    "wording_from": [{k: w[k] for k in ("nct", "heading", "number", "at")} for w in shown],
                    "other_trials": [nct for nct in trials if nct not in sources],
                }
            )
        found.sort(key=lambda row: (-row["trials"], row["criterion"]["element"]))
        rows += found
    return rows


def open_questions(flags: list[tuple], admitted: set[str]) -> list[dict[str, Any]]:
    """The study's review flags as closed questions for an expert, never answered here (pure).

    `flags` are review.flags_for's (kind, element, why, priority, evidence, question, options); `admitted` the
    coordinates the study's universe admits. A coordinate conflict on a coordinate the universe does not admit
    is no question for this study and is left out. Each question: unresolved, its evidence as its words.
    """
    found = []
    for kind, element, why, priority, evidence, question, options in flags:
        if kind == "coordinate_conflict" and element not in admitted:
            continue
        result = dict(
            zip(QUESTION_KEYS, (kind, element, why, int(priority), question, list(options)), strict=True)
        )
        found.append(value_object("unresolved", "review.flags_for", list(evidence), result, why))
    return found


def criteria_evidence(criteria: list[tuple]) -> list[tuple[str, str, tuple[str, ...], str, str]]:
    """The evidence coherence.resolve narrows a study's coordinates by, from its criteria (pure).

    For each atom, in order: its effective section (reading.effective_section), concept, values, its scope
    param ("" when it has none) and "criterion <piece>", exactly as reading.study_view gathers it.
    """
    return [
        (
            effective_section(section, params),
            concept,
            tuple(values),
            dict(params).get("scope", ""),
            f"criterion {piece}",
        )
        for piece, section, _text, atoms in criteria
        for _bank, concept, values, params, _start, _end in atoms
    ]


def domain_readings(
    study: dict[str, Any], view: dict[str, Any], answers: dict[str, Any] | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A study's universe reading and the coordinates its universe admits (unit B's interface).

    universes.assign over the study and its drugs' ATC classes (universes.atc_classes of the RxNav
    `answers`; None in relay mode, where nothing was looked up), its reading (universes.reading), then
    coherence.resolve over the study's criteria evidence under that assignment: a coordinate no permitted
    pack owns is absent, and each row names the packs that own it."""
    classes = None if answers is None else universes.atc_classes(answers)
    assignment = universes.assign(study, classes)
    resolved = coherence.resolve(criteria_evidence(view["criteria"]), assignment)
    return universes.reading(assignment), resolved


# ── the per-study extract ─────────────────────────────────────────────────────────────────────────────


def study_extract(
    study: dict[str, Any],
    view: dict[str, Any],
    flags: list[tuple],
    universe: dict[str, Any],
    resolved: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """One study as schema 3 holds it: every contract field the registry record holds, and the readings.

    `view` is reading.study_view's for `study`; `flags` its review flags; `universe` its universe reading and
    `resolved` the coordinates its universe admits (domain_readings). Plain fields by the contract's API
    paths (assemble); the run's own fields (link, digest, a document's link); and the readings: the universe,
    the domain coordinates, whether results are posted, the criteria, the biomarker mentions, each registered
    and posted outcome's endpoint classes and time points, each experimental drug's class, axes and
    modality, eligibility coverage where the criteria could not be itemized, and the open questions.
    """
    nct = view["nct"]
    state = results_state(study.get("hasResults"), isinstance(study.get("resultsSection"), dict))
    extract = assemble(study, list(PLAIN_FIELDS), lambda template: absence_note(study, template))
    for name, module in RESULTS_MODULES.items():
        if not isinstance(get(study, *module), dict):
            extract[name] = module_absence(state)
    for outcome in extract["registered_outcomes"]:
        measure = outcome.get("measure") if isinstance(outcome.get("measure"), str) else ""
        frame = outcome.get("time_frame") if isinstance(outcome.get("time_frame"), str) else ""
        outcome["endpoint_classes"] = value_object(
            "known", "banks.endpoint_classes", [measure], endpoint_classes(measure), ""
        )
        outcome["time_points"] = value_object("known", "banks.time_points", [frame], time_points(frame), "")
    if isinstance(extract["posted_outcomes"], list):
        for measure in extract["posted_outcomes"]:
            title = measure.get("title") if isinstance(measure.get("title"), str) else ""
            measure["endpoint_classes"] = value_object(
                "known", "banks.endpoint_classes", [title], endpoint_classes(title), ""
            )
    names = [
        item.get("name") if isinstance(item, dict) else None
        for item in template_values(study, "protocolSection.armsInterventionsModule.interventions[]")
    ]
    drugs = {found[0]: found for found in view["drugs"]}
    axes = {held["drug"]: held for held in view["drug_axes"]}
    base = "protocolSection.armsInterventionsModule.interventions"
    for index, (entry, name) in enumerate(zip(extract["interventions"], names, strict=True)):
        if name in drugs:
            entry["drug_class"] = drug_class_reading(list(drugs[name]))
        if name in axes:
            entry["axes"] = axes_reading(axes[name])
        extractions = [e for e in view["properties"] if e[5].startswith(f"{base}[{index}].")]
        if extractions:
            entry["modality"] = modality_reading(extractions)
    documents = template_values(study, "documentSection.largeDocumentModule.largeDocs[]")
    for document, held in zip(extract["documents"], documents, strict=True):
        code, url = document_link(nct, held.get("filename") if isinstance(held, dict) else None)
        if code == "ok":
            document["url"] = url
    criteria = criterion_entries(view["criteria"])
    eligibility = extract.pop("eligibility")
    if view["itemize"] != "itemized":
        result = {
            "itemized": view["itemize"],
            "content": view["coverage"]["content"],
            "sectioning": view["coverage"]["sectioning"],
        }
        note = f"the criteria could not be itemized ({view['itemize']})"
        eligibility["coverage"] = value_object(
            "unresolved", "criteria.eligibility_coverage", [], result, note
        )
    coordinates = coordinate_section(resolved)
    admitted = {name for name in resolved}
    return {
        "nct": extract.pop("nct"),
        "link": study_link(nct)[1],
        "digest": view["digest"],
        **extract,
        "eligibility": eligibility,
        "criteria": criteria,
        "key_criteria": key_criteria(criteria),
        "biomarker_mentions": biomarker_mentions(criteria, extract["registered_outcomes"]),
        "universe": universe,
        **({"coordinates": coordinates} if coordinates else {}),
        "results_posted": results_reading(state),
        "open_questions": open_questions(flags, admitted),
    }


# ── the cohort, the record and its manifest ───────────────────────────────────────────────────────────


def endpoint_profile(trials: list[tuple[str, list[tuple]]]) -> list[tuple]:
    """Each planned outcome type and endpoint class across the cohort, with its time points (pure — pinned).

    `trials` are (nct, the reading's outcomes: (type, measure, time frame, endpoint classes, time points)). An
    outcome counts under each class its measure names, or under "(no endpoint class)" when it names none. Rows
    (outcome type, endpoint class, trials naming it, their NCT numbers sorted, outcomes naming it, each time
    point with how many of those outcomes state it, sorted by point), ordered primary, secondary, other, then
    by descending trials, then by class.
    """
    held: dict[tuple[str, str], tuple[set[str], list[int], dict[str, int]]] = {}
    for nct, outcomes in trials:
        for kind, _measure, _frame, classes, points in outcomes:
            for klass in classes or ["(no endpoint class)"]:
                ncts, count, times = held.setdefault((kind, klass), (set(), [0], {}))
                ncts.add(nct)
                count[0] += 1
                for point in dict.fromkeys(points):
                    times[point] = times.get(point, 0) + 1
    order = [kind for kind, _ in OUTCOME_KINDS]
    # each (type, class) is one row, so the keys never tie and the rows are never compared
    keyed = sorted(
        (
            (order.index(kind), -len(ncts), klass),
            (kind, klass, len(ncts), sorted(ncts), count[0], sorted(times.items())),
        )
        for (kind, klass), (ncts, count, times) in held.items()
    )
    return [row for _, row in keyed]


def too_few(trials: int, least: int) -> str:
    """Why a set of comparable trials is not assessed, "" when it is (pure — pinned).

    Fewer than `least` trials (the signal minimum): "too few comparable trials to assess (<trials>; at least
    <least> needed)"; otherwise "".
    """
    return (
        f"too few comparable trials to assess ({trials}; at least {least} needed)" if trials < least else ""
    )


def kept_strata(members: dict[str, list[str]], everyone: list[str], least: int) -> list[str]:
    """The by-setting strata the cohort keeps (pure — pinned).

    `members` map each stratum to its trials' NCT numbers; `everyone` the NCT numbers of all trials; `least`
    the signal minimum. A stratum holding every trial and no other repeats "all trials" and is dropped, and so
    is one of fewer than `least` trials (too_few); the rest are kept, in the order of `members`.
    """
    whole = sorted(everyone)
    return [
        stratum
        for stratum, ncts in members.items()
        if sorted(ncts) != whole and not too_few(len(set(ncts)), least)
    ]


def cohort_section(reading: dict[str, Any], admitted: list[set[str]]) -> dict[str, Any]:
    """The across-trial findings the evidence supports, as named rows; a table with no row is left out.

    `reading` is reading.read_population's; `admitted` each view's coordinates its universe admits, in the
    order of the views. Below the signal minimum (profile.SIGNAL_MIN_TRIALS trials) the cohort holds its
    thresholds and why it is not assessed (too_few), and no row. Otherwise: the frequency and mechanism rows
    over every trial ("all trials"), then by known setting over the trials whose universe admits a setting,
    each stratum kept only where it is not all trials and holds the signal minimum (kept_strata); a primary
    endpoint's element is the endpoints' table's, never a criterion's frequency. The occupancy of each setting
    and observed class cell and the near-miss pairs, over the trials whose universe admits a setting; the
    planned endpoints and time points by class; the structure relations; and the thresholds the tiers and
    signals were read at.
    """
    views = reading["views"]
    thresholds = {
        "standard_share": STANDARD_SHARE,
        "signal_min_trials": SIGNAL_MIN_TRIALS,
        "signal_min_sponsors": SIGNAL_MIN_SPONSORS,
    }
    reason = too_few(len(views), SIGNAL_MIN_TRIALS)
    if reason:
        return {"thresholds": thresholds, "reason": reason}
    setting = [view for view, held in zip(views, admitted, strict=True) if "setting" in held]
    everyone = [view["nct"] for view in views]
    rows = _profile_trials(setting, True)
    members: dict[str, list[str]] = {}
    for row in rows:
        members.setdefault(row[2], []).append(row[0])
    kept = set(kept_strata(members, everyone, SIGNAL_MIN_TRIALS))
    by_setting = [row for row in rows if row[2] in kept]
    frequency, mechanism = [], []
    for trials in (_profile_trials(views, False), by_setting):
        if trials:
            frequency += frequency_rows(trials)
            mechanism += mechanism_rows(trials)
    frequency = [row for row in frequency if not row[1].startswith(ENDPOINT_ELEMENT)]
    mechanism = [row for row in mechanism if not row[2].startswith(ENDPOINT_ELEMENT)]
    occupancy_trials = [
        (
            v["nct"],
            v["coordinates"]["setting"]["domain"],
            tuple(sorted({c for _, s, e, _ in v["drugs"] if s == "classified" for c in e}))
            if v["drugs"] and all(s == "classified" for _, s, _, _ in v["drugs"])
            else (),
        )
        for v in setting
    ]
    observed = sorted({c for _, _, classes in occupancy_trials for c in classes})
    cells = [(name, klass) for name in SETTINGS for klass in observed]
    placed = {view["nct"] for view in setting}
    tables = {
        "frequency": [dict(zip(FREQUENCY_COLUMNS, row, strict=True)) for row in frequency],
        "mechanism_signals": [dict(zip(MECHANISM_COLUMNS, row, strict=True)) for row in mechanism],
        "occupancy": [
            dict(zip(OCCUPANCY_COLUMNS, row, strict=True)) for row in occupancy_rows(cells, occupancy_trials)
        ]
        if occupancy_trials
        else [],
        "near_misses": [
            dict(zip(NEAR_MISS_COLUMNS, (*pair, rests_on), strict=True))
            for pair, rests_on in zip(reading["pairs"], reading["pair_status"], strict=True)
            if pair[0] in placed and pair[1] in placed
        ],
        "aligned_near_misses": [
            dict(zip(ALIGNED_COLUMNS, (*pair, rests_on), strict=True))
            for pair, rests_on in zip(reading["aligned_pairs"], reading["aligned_pair_status"], strict=True)
            if pair[0] in placed and pair[1] in placed
        ],
        "endpoints": [
            dict(zip(ENDPOINT_COLUMNS, (*row[:5], dict(row[5])), strict=True))
            for row in endpoint_profile([(v["nct"], v["outcomes"]) for v in views])
        ],
        "structure_relations": [
            dict(zip(STRUCTURE_COLUMNS, row, strict=True)) for row in reading["structure_relations"]
        ],
    }
    return {"thresholds": thresholds, **{name: rows for name, rows in tables.items() if rows}}


def landscape_manifest(
    studies: list[dict[str, Any]],
    api_version: str,
    data_timestamp: str,
    code_commit: str,
    retrieval: dict[str, Any],
    rule_versions: dict[str, Any],
) -> dict[str, Any]:
    """The manifest of a record: what it was read from and by (pure — pinned).

    The API version and data timestamp of the registry snapshot read, each study's digest in order and their
    Merkle root (as `trialledger resolve` names them), the code commit, the rule versions (the command passes
    RULE_VERSIONS: the schema, the tool, the design rules, the derivation code root and every relation's
    approval; a copy, so the record never shares them) and the retrieval coverage as the pull gives it
    (`retrieval`, carried as given).
    """
    digests = [warrants.study_digest(study) for study in studies]
    return {
        "api_version": api_version,
        "data_timestamp": data_timestamp,
        "study_digests": digests,
        "merkle_root": warrants.merkle_root(digests),
        "code_commit": code_commit,
        "rule_versions": copy.deepcopy(rule_versions),
        "retrieval": retrieval,
    }


def universes_table() -> list[dict[str, Any]]:
    """The universes and their rule packs as run (contract.UNIVERSES), as JSON."""
    return [
        {
            "name": universe.name,
            "label": universe.label,
            "version": universe.version,
            "packs": [
                {
                    "name": pack.name,
                    "label": pack.label,
                    "coordinates": list(pack.coordinates),
                    "relations": list(pack.relations),
                    "requires": [{"kind": r.kind, "values": list(r.values)} for r in pack.requires],
                }
                for pack in universe.packs
            ],
        }
        for universe in contract.UNIVERSES
    ]


def landscape_record(
    reading: dict[str, Any],
    studies: list[dict[str, Any]],
    request: Any,
    scope: Any,
    manifest: dict[str, Any],
    answers: dict[str, Any] | None,
) -> dict[str, Any]:
    """landscape.json: the record of truth for one run, schema 3.

    `reading` is reading.read_population's over `studies`, in the same order: a reading whose views' digests
    are not the studies' digests, in order, raises ValueError and pairs nothing. `request` and `scope` are
    carried as given; `manifest` is landscape_manifest's; `answers` the RxNav answers the reading was made
    with (None in relay mode, where nothing was looked up), from which domain_readings gives each study's
    universe reading and the coordinates its universe admits (universes.assign, then coherence.resolve). The
    record: RECORD_KEYS in order, each study's extract (study_extract), the cohort (cohort_section), the
    standard protocol language across the studies (standard_language) and the record's self-description.
    """
    views = reading["views"]
    if [view["digest"] for view in views] != [warrants.study_digest(study) for study in studies]:
        raise ValueError("the reading is not of these studies, in this order")
    found = [domain_readings(study, view, answers) for study, view in zip(studies, views, strict=True)]
    admitted = [set(resolved) for _universe, resolved in found]
    extracts = [
        study_extract(study, view, flags, universe, resolved)
        for study, view, flags, (universe, resolved) in zip(
            studies, views, reading["flags"], found, strict=True
        )
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "request": request,
        "scope": scope,
        "manifest": manifest,
        "universes": universes_table(),
        "coverage": {"universe": copy.deepcopy(UNIVERSE)},
        "cohort": cohort_section(reading, admitted),
        "standard_language": standard_language(extracts),
        "statuses": dict(STATUSES),
        "envelope": dict(ENVELOPE_MEANINGS),
        "fields": copy.deepcopy(FIELD_DICTIONARY),
        "studies": extracts,
    }


# ── the validator ─────────────────────────────────────────────────────────────────────────────────────


def value_problem(node: Any, kind: str, rule: str) -> str:
    """Whether one node is a well-formed value of a field of its kind (pure — pinned).

    `kind` is the field's contract kind ("plain", "reading", "run", or "itemized" for a reading's part held
    plain: ITEMIZED), `rule` a reading field's rule. Codes:
      ok              — an itemized value (a reading's part held plain), whatever it holds; a plain or run
                        value that is not an object, or a well-formed absence object
                        (status not_stated or not_posted, and a note); a reading: a value object whose status
                        is one of STATUSES and whose rule is its field's, or a list of such objects;
      malformed_value — an object that is neither an absence object nor, for a reading, a value object; a
                        reading that is not a value object or a list of them;
      unknown_status  — a value object or absence object whose status is not one of STATUSES (an absence
                        object's, not not_stated or not_posted);
      wrong_rule      — a reading's value object whose rule is not its field's.
    """
    if kind == "reading":
        held = node if isinstance(node, list) else [node]
        for item in held:
            if not isinstance(item, dict) or tuple(item) != READING_KEYS:
                return "malformed_value"
            if item["status"] not in STATUSES:
                return "unknown_status"
            if item["rule"] != rule:
                return "wrong_rule"
        return "ok"
    if kind == "itemized" or not isinstance(node, dict):
        return "ok"
    if tuple(node) != ABSENT_KEYS or not isinstance(node["note"], str):
        return "malformed_value"
    return "ok" if node["status"] in ("not_stated", "not_posted") else "unknown_status"


# Each described place below a study (its contract name), and what it is: a field's kind, or "object" or
# "list" for a place that holds fields.
PLACES: dict[str, str] = {}
for _field in CONTRACT_FIELDS:
    if not _field.name.startswith(f"{STUDY}."):
        continue
    _parts = _field.name.split(".")
    for _depth in range(2, len(_parts)):
        _place = ".".join(_parts[:_depth])
        PLACES.setdefault(_place, "list" if _place.endswith("[]") else "object")
    PLACES[_field.name] = "itemized" if _field.name in ITEMIZED else _field.kind
RULES = {field.name: field.source[0] for field in CONTRACT_FIELDS if field.kind == "reading"}
# A study's own places a record always holds: every place one step below the study but the readings that
# apply only where their rule does.
OPTIONAL = ("coordinates", "eligibility.coverage")
REQUIRED = tuple(
    name.removeprefix(f"{STUDY}.").removesuffix("[]")
    for name in PLACES
    if name.count(".") == 1 and name.removeprefix(f"{STUDY}.").removesuffix("[]") not in OPTIONAL
)
WALK_DEPTH = max(name.count(".") for name in PLACES) + 2


def study_problems(study: Any, where: str) -> list[tuple[str, str]]:
    """Every way one study departs from schema 3, by code and where.

    Walked level by level from the study (WALK_DEPTH levels reach every described place): a key that is no
    described place (undescribed_field); a required place missing (missing_field); an object or list place
    that is neither (wrong_type) unless a results module's absence object; each field's value (value_problem);
    the study's link not its NCT number's page (wrong_link).
    """
    if not isinstance(study, dict):
        return [("wrong_type", where)]
    found = [("missing_field", f"{where}.{key}") for key in REQUIRED if key not in study]
    nct = study.get("nct")
    if study.get("link") != study_link(nct if isinstance(nct, str) else None)[1]:
        found.append(("wrong_link", f"{where}.link"))
    frontier: list[tuple[str, str, Any]] = [(STUDY, where, study)]
    for _level in range(WALK_DEPTH):
        following: list[tuple[str, str, Any]] = []
        for place, at, node in frontier:
            for key, held in node.items():
                child, here = f"{place}.{key}", f"{at}.{key}"
                kind = PLACES.get(child) or PLACES.get(f"{child}[]")
                if kind is None:
                    found.append(("undescribed_field", here))
                elif kind == "object" or kind == "list":
                    listed = PLACES.get(f"{child}[]") == "list"
                    if listed and isinstance(held, list):
                        following += [
                            (f"{child}[]", f"{here}[{i}]", item)
                            for i, item in enumerate(held)
                            if isinstance(item, dict)
                        ]
                        found += [
                            ("wrong_type", f"{here}[{i}]")
                            for i, item in enumerate(held)
                            if not isinstance(item, dict)
                        ]
                    elif not listed and isinstance(held, dict) and tuple(held) != ABSENT_KEYS:
                        following.append((child, here, held))
                    elif not (
                        key in RESULTS_MODULES
                        and value_problem(held, "plain", "") == "ok"
                        and isinstance(held, dict)
                    ):
                        found.append(("wrong_type", here))
                else:
                    code = value_problem(held, kind, RULES.get(child, ""))
                    if code != "ok":
                        found.append((code, here))
        frontier = following
    return found


def schema_problems(record: Any) -> tuple[tuple[str, str], ...]:
    """Every way a record departs from schema 3 that the record itself shows, each by its code and where.

    unknown_schema_version, statuses_differ, envelope_differ, fields_differ, universes_differ (the record's
    own description is not this schema's); undescribed_field and missing_field at the top (RECORD_KEYS); each
    study's problems (study_problems); digest_mismatch (the manifest's study digests are not the studies',
    in order) and root_mismatch (the Merkle root is not their root). A record that is not an object:
    (("not_an_object", ""),). A record with no problem: (). The record is checked against the schema and
    itself, never against the registry bodies: re-deriving it from the studies its manifest names does that.
    """
    if not isinstance(record, dict):
        return (("not_an_object", ""),)
    found: list[tuple[str, str]] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        found.append(("unknown_schema_version", "schema_version"))
    described = (
        ("statuses", STATUSES),
        ("envelope", ENVELOPE_MEANINGS),
        ("fields", FIELD_DICTIONARY),
        ("universes", universes_table()),
    )
    for name, held in described:
        if record.get(name) != held:
            found.append((f"{name}_differ", name))
    found += [("undescribed_field", key) for key in record if key not in RECORD_KEYS]
    found += [("missing_field", key) for key in RECORD_KEYS if key not in record]
    studies = record.get("studies")
    if not isinstance(studies, list):
        return (*found, ("wrong_type", "studies"))
    for index, study in enumerate(studies):
        found += study_problems(study, f"studies[{index}]")
    manifest = record.get("manifest")
    if isinstance(manifest, dict):
        digests = manifest.get("study_digests")
        if digests != [study.get("digest") if isinstance(study, dict) else None for study in studies]:
            found.append(("digest_mismatch", "manifest.study_digests"))
        if not (
            isinstance(digests, list)
            and all(isinstance(d, str) for d in digests)
            and manifest.get("merkle_root") == warrants.merkle_root(digests)
        ):
            found.append(("root_mismatch", "manifest.merkle_root"))
    else:
        found.append(("wrong_type", "manifest"))
    return tuple(found)
