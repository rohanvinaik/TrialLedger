"""The contract of landscape.json schema 3 (TrialLedger/contract.py), held to the registry and its consumers.

The founder's two principles, as gates (refine-landscape-record design §0):
- no false silence: every API path the contract copies or reads exists in the API's field metadata and holds
  a value in at least one saved baseline body, except the paths UNEXERCISED names (exactly those); and every
  field of the metadata is carried or named in NOT_WANTED with its reason, so nothing is dropped silently;
- nothing nobody uses: every field names a consumer, and every consumer it names exists (a sheet and column of
  SHEETS, which names the same fields back; a part the MCP record tool serves, or one declared to be built;
  a layer-two function, by import).
Beside them: every rule resolves by import or names the task that builds it; the display dictionaries cover
every value the API defines for each code the workbook shows; the universe table names the coherence
coordinates and relations that exist; and the helpers, both signs.
"""

import importlib
import json
import re
from pathlib import Path

import pytest

from TrialLedger import coherence, contract, mcp_server
from TrialLedger.contract import (
    DISPLAY,
    DISPLAY_NOT_API_ENUMS,
    FIELDS,
    NOT_WANTED,
    SHEETS,
    UNEXERCISED,
    display_words,
    holds_value,
    resolves,
    template_values,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "contract"
TASKS = ROOT / "openspec" / "changes" / "refine-landscape-record" / "tasks.md"
METADATA = json.loads((FIXTURES / "metadata.json").read_text(encoding="utf-8"))
ENUMS = {entry["type"]: entry for entry in json.loads((FIXTURES / "enums.json").read_text(encoding="utf-8"))}
BODIES = [
    study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
]


def metadata_nodes():
    """Every node of the field metadata by its path template (lists as "[]"), with whether it is a leaf."""
    nodes = {}
    queue = [("", node) for node in METADATA]
    for prefix, node in queue:
        path = f"{prefix}.{node['name']}" if prefix else node["name"]
        path += "[]" if node.get("type", "").endswith("[]") else ""
        children = node.get("children") or []
        nodes[path] = (node, not children)
        queue.extend((path, child) for child in children)
    return nodes


NODES = metadata_nodes()


def carried():
    """Every API path template the contract copies or reads."""
    found = set()
    for field in FIELDS:
        found.update(field.source if field.kind == "plain" else field.reads)
    for _name, _words, paths in contract.ASSIGNMENT_SOURCES:
        found.update(paths)
    return found


def covers(key, path):
    return path == key or path.startswith(key + ".")


def resolve_name(dotted):
    module, _, name = dotted.rpartition(".")
    return getattr(importlib.import_module(f"TrialLedger.{module}"), name)


# ── the fixtures are the registry's own tables ──────────────────────────────────────────────────────────


def test_the_fixture_tables_are_the_vendored_registry_tables():
    registry = ROOT / "TrialLedger" / "registry"
    vendored_metadata = json.loads((registry / "ctg-metadata.json").read_text(encoding="utf-8"))
    assert vendored_metadata == METADATA
    vendored = json.loads((registry / "ctg-enums.json").read_text(encoding="utf-8"))
    assert list(ENUMS.values()) == vendored


def test_the_bodies_are_the_baseline_trials():
    ncts = [study["protocolSection"]["identificationModule"]["nctId"] for study in BODIES]
    assert ncts[:3] == ["NCT01030536", "NCT01827384", "NCT04852770"]
    assert {"NCT02959749", "NCT02151981"} <= set(ncts)
    assert len(ncts) == len(set(ncts)) == 10


# ── the table's own form ────────────────────────────────────────────────────────────────────────────────


def test_every_field_is_well_formed():
    names = [field.name for field in FIELDS]
    assert len(names) == len(set(names))
    for field in FIELDS:
        assert field.kind in contract.KINDS, field.name
        assert field.form in contract.FORMS, field.name
        assert field.label, field.name
        if field.kind == "plain":
            assert field.source and not field.reads and not field.built_by, field.name
        else:
            assert len(field.source) == 1 and field.form == "as held", field.name
        assert field.kind == "reading" or not field.reads, field.name


# ── no false silence ────────────────────────────────────────────────────────────────────────────────────


def test_every_path_the_contract_reads_is_in_the_api_metadata():
    for template in carried():
        assert template in NODES, template


def test_every_plain_path_holds_a_value_in_a_saved_body_but_the_unexercised():
    unheld = {template for template in carried() if not any(resolves(body, template) for body in BODIES)}
    assert unheld == set(UNEXERCISED)
    for reason in UNEXERCISED.values():
        assert reason.strip()


def test_every_metadata_field_is_carried_or_named_not_wanted():
    paths = carried()
    for key, reason in NOT_WANTED.items():
        assert key in NODES, key
        assert reason.strip(), key
        assert not any(covers(key, path) for path in paths), key
    leaves = [path for path, (_node, leaf) in NODES.items() if leaf]
    silent = [
        path
        for path in leaves
        if path not in paths and not any(covers(key, path) for key in NOT_WANTED)
        # a list or structure the contract counts or names as a whole carries its leaves' place, not them
    ]
    assert silent == []


def test_what_is_not_wanted_is_listed_for_information(capsys):
    named = sorted(
        path for path, (_n, leaf) in NODES.items() if leaf and any(covers(k, path) for k in NOT_WANTED)
    )
    print("metadata fields not carried, each under a NOT_WANTED reason:", len(named))
    for path in named:
        print("  ", path)
    assert named


# ── nothing nobody uses ─────────────────────────────────────────────────────────────────────────────────


def test_every_field_has_a_consumer_and_every_consumer_exists():
    sheets = {sheet.name: {column.header for column in sheet.columns} for sheet in SHEETS}
    parts = set(mcp_server.RECORD_PARTS)
    assert not parts & set(contract.MCP_PARTS_TO_BUILD)
    for field in FIELDS:
        assert field.consumers, field.name
        for consumer in field.consumers:
            kind, *rest = consumer
            if kind == "sheet":
                sheet, column = rest
                assert column in sheets.get(sheet, ()), (field.name, consumer)
            elif kind == "mcp":
                assert rest[0] in parts or rest[0] in contract.MCP_PARTS_TO_BUILD, (field.name, consumer)
            else:
                assert kind == "design" and callable(resolve_name(rest[0])), (field.name, consumer)


def test_every_column_shows_the_fields_that_name_it():
    names = {field.name for field in FIELDS}
    assert len({sheet.name for sheet in SHEETS}) == len(SHEETS)
    for sheet in SHEETS:
        headers = [column.header for column in sheet.columns]
        assert len(headers) == len(set(headers)), sheet.name
        assert sheet.row, sheet.name
        for column in sheet.columns:
            assert column.shows in contract.SHOWS, (sheet.name, column.header)
            naming = tuple(f.name for f in FIELDS if ("sheet", sheet.name, column.header) in f.consumers)
            assert column.fields == naming, (sheet.name, column.header)
            assert set(column.fields) <= names
            if column.shows == "address":
                assert not column.fields and column.header == contract.ADDRESS, sheet.name
            else:
                assert column.fields, (sheet.name, column.header)


def test_every_listing_carries_its_rows_address():
    summaries = {contract.READ_ME, contract.INDEX, contract.REVIEW, contract.DICTIONARY}
    for sheet in SHEETS:
        addresses = [column for column in sheet.columns if column.shows == "address"]
        assert len(addresses) == (0 if sheet.name in summaries else 1), sheet.name


def test_safety_repeats_three_numeric_cells_for_each_group():
    safety = next(sheet for sheet in SHEETS if sheet.name == contract.SAFETY)
    repeated = [column.header for column in safety.columns if column.shows == "per group"]
    assert tuple(repeated) == contract.SAFETY_GROUP_HEADERS


def test_fields_served_only_through_the_study_part_are_listed_for_information(capsys):
    only = [field.name for field in FIELDS if set(field.consumers) == {contract.STUDY}]
    print("fields whose only consumer is the MCP study part:", only)
    assert all(name.startswith("studies[].") for name in only)


# ── the rules ───────────────────────────────────────────────────────────────────────────────────────────


def test_every_rule_exists_or_names_the_task_that_builds_it():
    tasks = TASKS.read_text(encoding="utf-8")
    open_tasks = set(re.findall(r"^- \[[ x]\] (\d+\.\d+[a-z]?)", tasks, flags=re.MULTILINE))
    for field in FIELDS:
        if field.kind == "plain":
            continue
        if field.built_by:
            assert field.built_by in open_tasks, field.name
        else:
            resolve_name(field.source[0])


# ── the dossier and the Read me ─────────────────────────────────────────────────────────────────────────


def test_every_dossier_field_is_in_one_band():
    dossier = [field.name for field in FIELDS if contract.DOSSIER in field.consumers]
    sheets = {sheet.name for sheet in SHEETS}
    for _heading, listing, _prefixes in contract.DOSSIER_SECTIONS:
        assert listing == "" or listing in sheets
    for name in dossier:
        bands = [
            heading
            for heading, _listing, prefixes in contract.DOSSIER_SECTIONS
            if any(
                name == prefix or (prefix.endswith((".", "[].")) and name.startswith(prefix))
                for prefix in prefixes
            )
        ]
        assert len(bands) == 1, (name, bands)
    for heading, _listing, prefixes in contract.DOSSIER_SECTIONS:
        for prefix in prefixes:
            assert any(name == prefix or name.startswith(prefix) for name in dossier), (heading, prefix)
    assert "studies[].brief_summary" in dossier


def test_the_read_me_names_every_field_it_shows_and_ends_in_provenance():
    shown = {field.name for field in FIELDS if ("sheet", contract.READ_ME, "Content") in field.consumers}
    topics = {name for _topic, names in contract.READ_ME_TOPICS for name in names}
    assert topics == shown
    assert contract.READ_ME_TOPICS[0][0].startswith("The search")
    assert contract.READ_ME_TOPICS[-1][0] == "Technical provenance"


# ── the display dictionaries ────────────────────────────────────────────────────────────────────────────


def test_every_code_the_workbook_shows_has_its_words():
    used = set()
    for field in FIELDS:
        sheets = [c for c in field.consumers if c[0] == "sheet"]
        enums = {
            NODES[t][0].get("type", "").removesuffix("[]")
            for t in field.source
            if NODES.get(t, ({}, 0))[0].get("isEnum")
        }
        if field.kind == "plain" and sheets and enums:
            assert enums == {field.display}, field.name
        if field.display:
            assert field.display in DISPLAY, field.name
            used.add(field.display)
    assert used == set(DISPLAY)


def test_every_value_the_api_defines_has_words():
    for name, words in DISPLAY.items():
        assert all(text.strip() and text != "N/A" for text in words.values()), name
        if name in DISPLAY_NOT_API_ENUMS:
            continue
        assert set(words) == {value["value"] for value in ENUMS[name]["values"]}, name


def test_the_registry_text_codes_shown_have_words():
    for field in FIELDS:
        if field.display not in DISPLAY_NOT_API_ENUMS:
            continue
        for body in BODIES:
            for template in field.source:
                for value in template_values(body, template):
                    if field.display == "LargeDocType" or value.isupper():
                        assert display_words(field.display, value)[0] == "ok", (field.name, value)


# ── the universes ───────────────────────────────────────────────────────────────────────────────────────


def test_the_universes_name_what_coherence_holds():
    names = [universe.name for universe in contract.UNIVERSES]
    assert names == ["oncology.solid", "oncology.heme", "general"]
    relations = {relation.id for relation in coherence.RELATIONS}
    assert set(contract.NSCLC_RELATIONS) == relations
    assert contract.SELECTED_GENES == coherence.SELECTED_GENES
    purposes = set(DISPLAY["PrimaryPurpose"])
    for universe in contract.UNIVERSES:
        assert universe.version and universe.label
        for pack in universe.packs:
            for coordinate in pack.coordinates:
                assert coordinate in coherence.COORDINATES or coordinate in contract.NEW_COORDINATES
            assert set(pack.relations) <= relations
            assert pack.requires
            for requirement in pack.requires:
                assert requirement.kind in contract.REQUIREMENT_KINDS
                allowed = {
                    "universe": set(names),
                    "primary_purpose": purposes,
                    "treated_target": {"cancer"},
                }[requirement.kind]
                assert set(requirement.values) <= allowed, (pack.name, requirement)
    assert set(contract.TREATED_TARGETS) == {"cancer", "not_cancer", "unresolved"}
    assert contract.UNIVERSES[-1].packs == ()


def test_reporting_fields_do_not_authorize_inferred_clinical_categories():
    assert "studies[].universe" not in contract.FIELD_NAMES
    assert not any(name.startswith("studies[].coordinates.") for name in contract.FIELD_NAMES)
    assert not any(name.startswith("cohort.") for name in contract.FIELD_NAMES)
    assert "studies[].scoped_assertions" not in contract.FIELD_NAMES


def test_assignment_preserves_registry_sources_without_lookups_or_category_guessing():
    from TrialLedger.universes import assign, reading

    for body in BODIES:
        result = reading(assign(body))
        assert result["status"] == "unresolved"
        assert result["result"]["universes"] == []
        assert result["result"]["indications"] == []
        assert all(row["status"] == "scope_unresolved" for row in result["result"]["applicability"])
        sources = {row["source"]: row for row in result["result"]["sources"] if "source" in row}
        conditions = body["protocolSection"].get("conditionsModule", {})
        browse = body.get("derivedSection", {}).get("conditionBrowseModule", {})
        assert sources["registry_conditions"]["conditions"] == conditions.get("conditions", [])
        assert sources["registry_conditions"]["keywords"] == conditions.get("keywords", [])
        assert sources["registry_mesh"]["meshes"] == browse.get("meshes", [])
        assert sources["registry_mesh"]["ancestors"] == browse.get("ancestors", [])
        assert sources["registry_mesh"]["browse_leaves"] == browse.get("browseLeaves", [])
        assert sources["mesh_lookups"]["lookups"] == []
        assert sources["titles"]["code"] == "not_looked_up"


# ── the helpers ─────────────────────────────────────────────────────────────────────────────────────────


def test_template_values_follows_lists_in_order():
    body = {"a": {"b": [{"c": 1}, {"c": None}, {"d": 2}, {"c": [3]}]}}
    assert template_values(body, "a.b[].c") == [1, None, [3]]
    assert template_values(body, "a.b[]") == body["a"]["b"]
    assert template_values(body, "a.b") == [body["a"]["b"]]


def test_template_values_finds_nothing_where_the_body_holds_nothing():
    assert template_values({"a": {"b": "text"}}, "a.b[].c") == []
    assert template_values({"a": "text"}, "a.b") == []
    assert template_values({}, "a") == []
    assert template_values([], "a") == []
    assert template_values({"a": {"b": {"c": 1}}}, "a.b[]") == []


def test_holds_value_counts_zero_and_false():
    assert (
        holds_value(0)
        and holds_value(False)
        and holds_value("x")
        and holds_value([0])
        and holds_value({"k": None})
    )


def test_holds_value_refuses_none_and_empty():
    assert not holds_value(None)
    assert not holds_value("")
    assert not holds_value([])
    assert not holds_value({})


def test_resolves_both_signs():
    body = {"a": [{"b": ""}, {"b": 0}]}
    assert resolves(body, "a[].b")
    assert not resolves({"a": [{"b": ""}, {"b": None}]}, "a[].b")
    assert not resolves(body, "a[].c")


@pytest.mark.parametrize(
    ("dictionary", "code", "expected"),
    [
        ("Phase", "PHASE1", ("ok", "Phase 1")),
        ("MeasureParam", "COUNT_OF_PARTICIPANTS", ("ok", "Count of participants")),
        ("EventAssessment", "SYSTEMATIC_ASSESSMENT", ("ok", "Systematic assessment")),
        ("Phase", "PHASE9", ("not_in_dictionary", "PHASE9")),
        ("Phase", ["PHASE1"], ("not_in_dictionary", "['PHASE1']")),
        ("Phase", None, ("not_in_dictionary", "None")),
        ("NoSuchEnum", "PHASE1", ("no_dictionary", "PHASE1")),
    ],
)
def test_display_words(dictionary, code, expected):
    assert display_words(dictionary, code) == expected
