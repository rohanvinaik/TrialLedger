"""Preservation (refine-landscape-record 1.7): every contract field's registry value is the record's value.

An independent check, written apart from the assembly code: its own walker reads each contract field's API
paths in the saved registry bodies, with every list position, and its own walker reads the record at the
field's name with the same positions (a field the registry keeps in several lists, the outcomes and the
adverse events, follows those lists one after another). The two must agree everywhere: nested populations,
denominators at every scope, comments and the registry's own precision. Nothing here calls landscape.py but
to build the record under test.

Positive: the record built from the fixture bodies preserves every value. Negative: two planted defects (a
measurement moved to another group; a dropped nested field) each make the check fail.
"""

import copy
import json
from pathlib import Path

from universe_shim import shim_domains

from TrialLedger import landscape
from TrialLedger.contract import FIELDS
from TrialLedger.reading import read_population

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
BODIES = [
    study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
]
WORDS = {
    "primaryOutcomes": "primary",
    "secondaryOutcomes": "secondary",
    "otherOutcomes": "other",
    "seriousEvents": "serious",
    "otherEvents": "other",
}


def held(value):
    return value not in (None, "", [], {})


def registry_walk(body, template):
    """(positions, value) for every value at a dotted template, each "[]" a list followed in order."""
    nodes = [((), body)]
    for segment in template.split("."):
        name = segment.removesuffix("[]")
        following = []
        for positions, node in nodes:
            if not isinstance(node, dict) or name not in node:
                continue
            if segment.endswith("[]"):
                items = node[name] if isinstance(node[name], list) else []
                following += [((*positions, i), item) for i, item in enumerate(items)]
            else:
                following.append((positions, node[name]))
        nodes = following
    return nodes


def registry_values(body, field):
    """The registry's value of a field at each record position."""
    depth = field.name.count("[]") - 1
    found, offset = {}, 0
    for template in field.source:
        first = template.split("[]")[0] + "[]"
        if field.form == "which list":
            word = WORDS[first.removesuffix("[]").rpartition(".")[2]]
            for positions, _item in registry_walk(body, template):
                found[(positions[0] + offset,)] = word
        else:
            grouped = {}
            for positions, value in registry_walk(body, template):
                key = positions[:depth]
                key = (key[0] + offset, *key[1:]) if depth and len(field.source) > 1 else key
                grouped.setdefault(key, []).append(value)
            for key, values in grouped.items():
                if field.form == "count":
                    found[key] = len(values)
                elif field.form == "distinct":
                    found[key] = list(dict.fromkeys(v for v in values if held(v)))
                elif template.count("[]") > depth:
                    found[key] = values
                else:
                    found[key] = values[0]
        if len(field.source) > 1:
            offset += len(registry_walk(body, first))
    return {key: value for key, value in found.items() if held(value)}


def record_values(study, name):
    """The record's plain value of a field at each position; absences ({status, note}) left out."""
    nodes = [((), study)]
    for part in name.split(".")[1:]:
        key = part.removesuffix("[]")
        following = []
        for positions, node in nodes:
            if not isinstance(node, dict) or key not in node:
                continue
            if part.endswith("[]"):
                items = node[key] if isinstance(node[key], list) else []
                following += [((*positions, i), item) for i, item in enumerate(items)]
            else:
                following.append((positions, node[key]))
        nodes = following
    return {
        positions: value
        for positions, value in nodes
        if not (isinstance(value, dict) and set(value) == {"status", "note"})
    }


def preservation_problems(record, bodies):
    """Every (trial, field, position) where the registry's value and the record's differ."""
    problems = []
    for body, study in zip(bodies, record["studies"], strict=True):
        for field in FIELDS:
            if field.kind != "plain" or not field.name.startswith("studies[]."):
                continue
            registry, held_here = registry_values(body, field), record_values(study, field.name)
            for key in sorted(set(registry) | set(held_here)):
                if registry.get(key) != held_here.get(key):
                    problems.append((study.get("nct"), field.name, key))
    return problems


def build():
    reading = read_population(BODIES, {})
    manifest = landscape.landscape_manifest(BODIES, "2", "t", "c", {}, landscape.RULE_VERSIONS)
    record = landscape.landscape_record(reading, BODIES, {}, {}, manifest, None, shim_domains)
    return json.loads(json.dumps(record, ensure_ascii=False))


RECORD = build()


def test_every_contract_value_of_every_body_is_preserved():
    assert preservation_problems(RECORD, BODIES) == []
    compared = sum(
        len(registry_values(body, field)) for body in BODIES for field in FIELDS if field.kind == "plain"
    )
    assert compared > 10_000


def first_measured_category(record):
    for s, study in enumerate(record["studies"]):
        for measure in study["posted_outcomes"] if isinstance(study["posted_outcomes"], list) else []:
            for klass in measure["classes"]:
                for category in klass["categories"]:
                    values = {m.get("value") for m in category["measurements"]}
                    if len(category["measurements"]) >= 2 and len(values) >= 2:
                        return s, category
    raise AssertionError("no category with two different measurements")


def test_a_measurement_moved_to_another_group_is_caught():
    broken = copy.deepcopy(RECORD)
    _s, category = first_measured_category(broken)
    first, second = category["measurements"][:2]
    first["group"], second["group"] = second["group"], first["group"]
    problems = preservation_problems(broken, BODIES)
    assert any(name.endswith("measurements[].group") for _nct, name, _at in problems)


def test_a_dropped_nested_field_is_caught():
    broken = copy.deepcopy(RECORD)
    cll = next(study for study in broken["studies"] if study["nct"] == "NCT01030536")
    measurement = cll["posted_outcomes"][0]["classes"][0]["categories"][0]["measurements"][0]
    del measurement["comment"]
    problems = preservation_problems(broken, BODIES)
    assert (
        "NCT01030536",
        "studies[].posted_outcomes[].classes[].categories[].measurements[].comment",
        (0, 0, 0, 0),
    ) in problems


def test_a_rounded_value_is_caught():
    broken = copy.deepcopy(RECORD)
    cll = next(study for study in broken["studies"] if study["nct"] == "NCT01030536")
    age = next(m for m in cll["baseline"]["measures"] if m["title"] == "Age, Continuous")
    age["classes"][0]["categories"][0]["measurements"][0]["value"] = "63"
    problems = preservation_problems(broken, BODIES)
    assert any(name.endswith("measurements[].value") for _nct, name, _at in problems)
