"""The clinical registry record: source copies and direct, reproducible transformations.

The field dictionary states each source path once. Results retain the registry's nesting,
groups, populations, denominators, units and exact text. Eligibility sections are split only
by the registry's unambiguous standard headings, with exact offsets into the retained text.
No clinical recognizer, default, proposal or design analysis runs while writing this record.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from TrialLedger import __version__, checks, contract, registry, warrants
from TrialLedger import classes as rx
from TrialLedger.contract import FIELDS as CONTRACT_FIELDS
from TrialLedger.contract import holds_value, template_values
from TrialLedger.eligibility import split_eligibility
from TrialLedger.landscape_warrants import derivation_root
from TrialLedger.ledger import APPLIES_TO, REDACTED_WHEN_WITHHELD, absence_state, get, results_state
from TrialLedger.links import document_link, study_link

SCHEMA_VERSION = contract.SCHEMA_VERSION
JSON_NAME = "landscape.json"
STUDY = "studies[]"
ELIGIBILITY_TEXT = "protocolSection.eligibilityModule.eligibilityCriteria"
READING_KEYS = ("status", "rule", "words", "result", "note")
ABSENT_KEYS = ("status", "note")
ENVELOPE_MEANINGS = {
    "status": "whether the source establishes this value; one of statuses",
    "rule": "the named direct transformation, defined in fields",
    "words": "the exact source words used, if any",
    "result": "the direct transformation's result",
    "note": "the source limitation or reason the value is unresolved",
}
STATUSES = {
    "known": "stated by a retained source or obtained by a checkable direct transformation",
    "not_stated": "no value is supplied at the declared registry field; never zero or none",
    "not_posted": "the registry reports that study results are not posted",
    "unresolved": "the available source does not establish this value; the note says why",
}
CLASS_NOTES = {
    "classified": "Classes supplied by NLM RxClass for the recorded intervention name or alias",
    "unresolved": "RxClass supplied no class for these names; no clinical absence follows",
    "lookup_failed": "The requested lookup did not establish a class",
    "not_looked_up": "Drug classes were not looked up for this run",
}
LIST_WORDS = {
    "primaryOutcomes": "primary",
    "secondaryOutcomes": "secondary",
    "otherOutcomes": "other",
    "seriousEvents": "serious",
    "otherEvents": "other",
}
RESULTS_MODULES = {
    "posted_outcomes": ("resultsSection", "outcomeMeasuresModule"),
    "baseline": ("resultsSection", "baselineCharacteristicsModule"),
    "participant_flow": ("resultsSection", "participantFlowModule"),
    "adverse_events": ("resultsSection", "adverseEventsModule"),
}
RESULTS_TEXT = {"posted": "results posted", "not_posted": "no results posted"}
ITEMIZED = tuple(
    f"studies[].criteria[].{name}" for name in ("heading", "number", "text", "source_start", "source_end")
)
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
    "derivation_code_root": derivation_root(Path(__file__).parent),
    "display": contract.DISPLAY_VERSION,
    "eligibility_sections": "registry-headings-source-passages/1",
    "registry_checks": checks.CHECKS_VERSION,
}
RECORD_KEYS = ("schema_version", "request", "scope", "manifest", "statuses", "envelope", "fields", "studies")


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
PLAIN_FIELDS = tuple(
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


def collection_presence(study: dict[str, Any], templates: list[str]) -> dict[str, str]:
    """Preserve collection reporting shape independently of the assembled listing's empty default.

    Only source paths declared by the plain-field contract are inspected. Each collection has an exact
    source pointer and named state: stated, stated_empty, not_stated or malformed. An empty collection says
    no items were listed; it never establishes zero clinical events or an absent clinical condition.
    """
    prefixes: set[tuple[str, ...]] = set()
    for template in templates:
        tokens = template.split(".")
        prefixes.update(
            tuple(tokens[: index + 1]) for index, token in enumerate(tokens) if token.endswith("[]")
        )
    states: dict[str, str] = {}

    def walk(node: Any, tokens: tuple[str, ...], pointer: str, state: str = "present") -> None:
        token, *rest = tokens
        name = token.removesuffix("[]")
        where = pointer + "/" + name.replace("~", "~0").replace("/", "~1")
        child = None
        if state == "present":
            if not isinstance(node, dict):
                state = "malformed"
            elif name not in node:
                state = "missing"
            else:
                child = node[name]
        if token.endswith("[]"):
            states[where] = (
                "not_stated"
                if state == "missing"
                else "malformed"
                if state != "present" or not isinstance(child, list)
                else "stated"
                if child
                else "stated_empty"
            )
            if rest and isinstance(child, list) and state == "present":
                for index, item in enumerate(child):
                    walk(item, tuple(rest), f"{where}/{index}")
        elif rest:
            walk(child, tuple(rest), where, state)

    for prefix in sorted(prefixes):
        walk(study, prefix, "")
    return states


def criterion_entries(text: str) -> list[dict[str, Any]]:
    """Readable exact source passages, never inferred requirements or clinical categories.

    Section names come only from the original unambiguous registry-heading split.
    Physical lines stay separate; lines exceeding 1,600 characters are continued at a space
    where possible so their text fits a readable workbook row. Every character is retained.
    Offsets slice the full source exactly, and joining passages reproduces it character for character.
    The passage number is a display position, never a numbered clinical requirement.
    """
    if not text:
        return []
    code, before, inclusion, exclusion = split_eligibility(text)
    sections = (("unsectioned", before), ("inclusion", inclusion), ("exclusion", exclusion))
    if code != "split":
        sections = (("unsectioned", text),)
    entries: list[dict[str, Any]] = []
    start = 0
    for heading, words in sections:
        number = 0
        for line in words.splitlines(keepends=True):
            if not line.strip() and entries and entries[-1]["heading"] == heading:
                entries[-1]["text"] += line
                entries[-1]["source_end"] += len(line)
                start += len(line)
                continue
            while line:
                end = min(len(line), 1600)
                if end < len(line):
                    space = line.rfind(" ", 0, end)
                    if space > 0:
                        end = space + 1
                number += 1
                entries.append(
                    {
                        "heading": heading,
                        "number": number,
                        "text": line[:end],
                        "source_start": start,
                        "source_end": start + end,
                    }
                )
                start += end
                line = line[end:]
    return entries


def drug_class_reading(name: str, aliases: list[str], answers: dict[str, Any] | None) -> dict[str, Any]:
    """Attribute classes to an established RxNorm subject; retain every alias answer and disagreement."""
    evidence = rx.class_evidence(aliases, answers)
    return value_object(
        "known" if evidence["state"] == "classified" else "unresolved",
        "classes.class_evidence",
        [name],
        evidence,
        evidence["reason"],
    )


def registry_check_inputs(study: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    """Each distinct declared check input once, retaining absence, null and malformed parents."""
    inputs = {}
    for path in dict.fromkeys(paths):
        node: Any = study
        walked: list[str] = []
        for token in path.split("."):
            if not isinstance(node, dict):
                inputs[path] = {
                    "state": "malformed_parent",
                    "at": ".".join(walked),
                    "value": copy.deepcopy(node),
                }
                break
            if token not in node:
                inputs[path] = {"state": "not_stated"}
                break
            node = node[token]
            walked.append(token)
        else:
            inputs[path] = {"state": "stated", "value": copy.deepcopy(node)}
    return inputs


def registry_check_reading(study: dict[str, Any]) -> dict[str, Any]:
    """Run the existing approved structural checks without changing any source value."""
    definitions = {check.id: check for check in checks.CHECKS}
    rows = [
        {
            "id": result.check_id,
            "label": definitions[result.check_id].relation,
            "outcome": result.outcome,
            "detail": result.detail,
            "source": list(checks.READS[result.check_id]),
            "rule": definitions[result.check_id].rule,
            "basis": definitions[result.check_id].basis,
            **({"information": result.information} if result.information is not None else {}),
        }
        for result in checks.run_checks(study)
    ]
    return value_object(
        "known",
        "checks.run_checks",
        [],
        {
            "inputs": registry_check_inputs(study, [path for row in rows for path in row["source"]]),
            "checks": rows,
        },
        "Approved registry checks; findings do not alter source facts or establish clinical meaning",
    )


def study_extract(study: dict[str, Any], answers: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project the declared source fields and only direct, checkable transformations."""
    extract = assemble(study, list(PLAIN_FIELDS), lambda template: absence_note(study, template))
    nct = get(study, "protocolSection", "identificationModule", "nctId")
    state = results_state(study.get("hasResults"), isinstance(study.get("resultsSection"), dict))
    for name, module in RESULTS_MODULES.items():
        if not isinstance(get(study, *module), dict):
            extract[name] = module_absence(state)
    names = rx.drug_names(study)
    for entry in extract.get("interventions", []):
        name = entry.get("name")
        if isinstance(name, str) and name in names:
            entry["drug_class"] = drug_class_reading(name, names[name], answers)
    documents = template_values(study, "documentSection.largeDocumentModule.largeDocs[]")
    for document, held in zip(extract.get("documents", []), documents, strict=True):
        code, url = document_link(nct, held.get("filename") if isinstance(held, dict) else None)
        if code == "ok":
            document["url"] = url
    eligibility = extract.get("eligibility", {})
    text = eligibility.get("text")
    extract.update(
        {
            "nct": nct,
            "link": study_link(nct)[1],
            "digest": warrants.study_digest(study),
            "criteria": criterion_entries(text) if isinstance(text, str) else [],
            "results_posted": results_reading(state),
            "registry_checks": registry_check_reading(study),
            "collection_presence": value_object(
                "known",
                "landscape.collection_presence",
                [],
                collection_presence(
                    study, [template for _, templates, _ in PLAIN_FIELDS for template in templates]
                ),
                "Source collection states; an empty list does not establish clinical absence",
            ),
        }
    )
    return extract


def landscape_record(
    studies: list[dict[str, Any]],
    request: Any,
    scope: Any,
    manifest: dict[str, Any],
    answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One source-bound clinical report. No second reading or inference engine is an input."""
    if manifest.get("study_digests") != [warrants.study_digest(study) for study in studies]:
        raise ValueError("the manifest is not of these studies, in this order")
    return {
        "schema_version": SCHEMA_VERSION,
        "request": request,
        "scope": scope,
        "manifest": copy.deepcopy(manifest),
        "statuses": dict(STATUSES),
        "envelope": dict(ENVELOPE_MEANINGS),
        "fields": copy.deepcopy(FIELD_DICTIONARY),
        "studies": [study_extract(study, answers) for study in studies],
    }


def landscape_manifest(
    studies: list[dict[str, Any]],
    api_version: str,
    data_timestamp: str,
    code_commit: str,
    retrieval: dict[str, Any],
    rule_versions: dict[str, Any],
) -> dict[str, Any]:
    """Bind a report to its registry snapshot, ordered study digests and direct-rule versions.

    Retrieval accounting is copied from the verified fetch operation. The manifest records
    provenance; it does not supply an inferred clinical value (pure — pinned).
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
PLAIN_TYPES = {
    field.name: (
        "integer"
        if field.form == "count"
        else "text"
        if field.form == "which list"
        else registry.FIELDS.get(field.source[0].replace("[]", ""), {}).get("type", "").removesuffix("[]"),
        1
        if field.form == "distinct"
        else 0
        if field.form in ("count", "which list")
        else max(0, field.source[0].count("[]") - field.name.count("[]") + 1),
    )
    for field in CONTRACT_FIELDS
    if field.kind == "plain"
}
REQUIRED = tuple(name.removeprefix(f"{STUDY}.").removesuffix("[]") for name in PLACES if name.count(".") == 1)
WALK_DEPTH = max(name.count(".") for name in PLACES) + 2


def scalar_problem(value: Any, source_type: str, list_depth: int = 0) -> str:
    """Check the registry's declared primitive shape without conversion (pure).

    A malformed value is retained in the raw response and refuses a typed report by name. It is never
    coerced, rounded or passed as a clinical number. A boolean is not an integer. Registry numeric strings
    (outcome values, confidence limits) are text by the source schema and remain exact strings.
    """
    if list_depth:
        if not isinstance(value, list):
            return "wrong_type"
        return next(
            (
                problem
                for item in value
                if (problem := scalar_problem(item, source_type, list_depth - 1)) != "ok"
            ),
            "ok",
        )
    if source_type in ("integer", "long"):
        return "ok" if type(value) is int else "wrong_type"
    if source_type == "boolean":
        return "ok" if type(value) is bool else "wrong_type"
    return "ok" if isinstance(value, str) else "wrong_type"


def study_problems(study: Any, where: str) -> list[tuple[str, str]]:
    """Every way one study departs from schema 4, by code and where.

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
                    if code == "ok" and kind == "plain" and not isinstance(held, dict):
                        code = scalar_problem(held, *PLAIN_TYPES.get(child, ("text", 0)))
                    if code != "ok":
                        found.append((code, here))
        frontier = following
    return found


def schema_problems(record: Any) -> tuple[tuple[str, str], ...]:
    """Every way a record departs from schema 4 that the record itself shows, each by its code and where.

    unknown_schema_version, statuses_differ, envelope_differ, fields_differ, (the record's
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
