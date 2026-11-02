"""The contract's worked examples (tests/fixtures/contract/examples) held to the contract and to the registry.

Each example was checked by hand against the saved registry bodies (its README says how); these tests hold it
to contract.FIELDS and contract.SHEETS, and re-read every plain value from the body it came from, so that a
producer and a consumer built against the examples cannot agree on the same mistake.
"""

import json
from pathlib import Path

from TrialLedger import contract, landscape, mcp_server
from TrialLedger.contract import FIELD_NAMES, SHEETS, template_values

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
EXAMPLES = FIXTURES / "examples"
BODIES = {
    study["protocolSection"]["identificationModule"]["nctId"]: study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
}
RECORD = json.loads((EXAMPLES / "record.json").read_text(encoding="utf-8"))
READING_KEYS = ("status", "rule", "words", "result", "note")
ABSENT_KEYS = ("status", "note")


def example(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def leaves(node, path=""):
    """Every field the example holds: (the field's name, its position in each list, the value)."""
    found = []
    queue = [(node, path, ())]
    for held, where, positions in queue:
        if where in FIELD_NAMES:
            found.append((where, positions, held))
        elif isinstance(held, dict):
            assert any(name.startswith(f"{where}.".lstrip(".")) for name in FIELD_NAMES), where
            queue.extend((value, f"{where}.{key}".lstrip("."), positions) for key, value in held.items())
        elif isinstance(held, list):
            queue.extend((value, f"{where}[]", (*positions, i)) for i, value in enumerate(held))
        else:
            raise AssertionError(f"{where} is not a field of the contract")
    return found


def indexed(body, template):
    """Every value at a template with its position in each list, read independently of template_values."""
    nodes = [((), body)]
    for segment in template.split("."):
        name = segment.removesuffix("[]")
        following = []
        for positions, node in nodes:
            if not isinstance(node, dict) or name not in node:
                continue
            if segment.endswith("[]"):
                following += [((*positions, i), item) for i, item in enumerate(node[name] or [])]
            else:
                following.append((positions, node[name]))
        nodes = following
    return nodes


def is_value_object(value, keys):
    return isinstance(value, dict) and tuple(value) == keys


def test_the_example_record_holds_only_contract_fields():
    assert RECORD["schema_version"] == contract.SCHEMA_VERSION
    found = leaves(RECORD)
    assert {name for name, _p, _v in found} >= {
        "studies[].nct",
        "studies[].universe",
        "studies[].posted_outcomes[].classes[].categories[].measurements[].comment",
        "studies[].baseline.measures[].classes[].categories[].measurements[].spread",
        "studies[].participant_flow.periods[].withdrawals[].reason",
        "studies[].adverse_events.events[].counts[].at_risk",
        "studies[].interventions[].drug_class",
    }
    # Neither example trial carries a coordinate: the PTSD trial is general, and what the CLL trial's
    # CAT-8015 treats cannot be read (RxNav gives it no ATC class), so its prior-lines pack is unresolved.
    assert not any(name.startswith("studies[].coordinates.") for name, _p, _v in found)


def test_every_plain_value_is_the_registrys_and_every_absence_is_real():
    checked = 0
    for name, positions, value in leaves(RECORD):
        field = FIELD_NAMES[name]
        if field.kind != "plain" or len(field.source) != 1 or field.form != "as held":
            continue
        study = RECORD["studies"][positions[0]]
        body = BODIES[study["nct"]]
        inner = positions[1:]
        at = [held for where, held in indexed(body, field.source[0]) if where[: len(inner)] == inner]
        listed = field.source[0].count("[]") > len(inner)
        if is_value_object(value, ABSENT_KEYS):
            assert value["status"] == "not_stated", name
            assert not any(contract.holds_value(held) for held in at), name
        else:
            assert value == (at if listed else at[0]), name
        checked += 1
    assert checked > 60


def test_every_reading_is_a_value_object_of_its_rule():
    for name, _positions, value in leaves(RECORD):
        field = FIELD_NAMES[name]
        if field.kind != "reading":
            continue
        assert is_value_object(value, READING_KEYS), name
        assert value["rule"] == field.source[0], name
        assert value["status"] in landscape.STATUSES, name


def test_the_universe_assignments_are_of_the_contracts_sources_and_anchors():
    universes = example("universes.json")
    names = {universe.name for universe in contract.UNIVERSES}
    paths = {name: paths for name, _words, paths in contract.ASSIGNMENT_SOURCES}
    anchors = {anchor for _u, _s, terms in contract.MESH_ANCHORS for anchor in terms}
    anchors |= {term for term, _match in contract.ONCOLOGY_TERMS}
    expected = {
        "NCT04852770": ["general"],
        "NCT01030536": ["oncology.heme"],
        "NCT01827384": ["oncology.solid"],
    }
    for nct, assignment in universes.items():
        assert tuple(assignment) == READING_KEYS
        assert assignment["rule"] == "universes.assign"
        result = assignment["result"]
        assert result["universes"] == expected[nct] and set(result["universes"]) <= names
        assert [source["source"] for source in result["sources"]] == list(paths)
        assert result["decided_by"] in paths
        for source in result["sources"]:
            held = {value for path in paths[source["source"]] for value in template_values(BODIES[nct], path)}
            for finding in source["found"]:
                assert finding["term"] in held and finding["anchor"] in anchors, (nct, finding)
                assert finding["universe"] in names
            assert set(source["non_oncology"]) <= held, nct
    assert RECORD["studies"][0]["universe"] == universes["NCT04852770"]
    assert RECORD["studies"][1]["universe"] == universes["NCT01030536"]


def test_the_safety_example_is_the_sheets_layout_and_the_registrys_counts():
    safety = example("safety.json")
    sheet = next(sheet for sheet in SHEETS if sheet.name == contract.SAFETY)
    n = max(
        len(BODIES[nct]["resultsSection"]["adverseEventsModule"]["eventGroups"]) for nct in safety["trials"]
    )
    assert safety["groups"] == n == 5
    columns = []
    for column in sheet.columns:
        if column.shows == "per group":
            continue
        columns.append(column.header)
        if column.header == "Term":
            columns += [h.format(n=g) for g in range(1, n + 1) for h in contract.SAFETY_GROUP_HEADERS]
    assert safety["columns"] == columns
    first = columns.index("G1 affected")
    for row in safety["rows"]:
        nct = row[0]
        module = BODIES[nct]["resultsSection"]["adverseEventsModule"]
        event = module["seriousEvents"][int(row[1].rsplit("/", 1)[1])]
        assert (
            row[1]
            == f"/studies/{safety['trials'].index(nct)}/adverse_events/events/{row[1].rsplit('/', 1)[1]}"
        )
        assert (row[3], row[4]) == (event["organSystem"], event["term"])
        stats = {s["groupId"]: s for s in event["stats"]}
        for g in range(n):
            cells = row[first + 3 * g : first + 3 * g + 3]
            if g >= len(module["eventGroups"]):
                assert cells == [None, None, None]
                continue
            s = stats[module["eventGroups"][g]["id"]]
            assert cells == [s["numAffected"], s["numAtRisk"], s["numEvents"]]
    for named in safety["group_columns"]:
        groups = BODIES[named["trial"]]["resultsSection"]["adverseEventsModule"]["eventGroups"]
        group = groups[int(named["column"][1:]) - 1]
        assert (named["group"], named["title"]) == (group["id"], group["title"])


def test_the_mcp_page_serves_only_studies_part_fields():
    page = example("mcp_paging.json")
    assert page["part"] in mcp_server.RECORD_PARTS
    for line in page["studies"]:
        for key in line:
            assert ("mcp", "studies") in FIELD_NAMES[f"studies[].{key}"].consumers, key
    window = page["page"]
    assert window["returned"] == len(page["studies"]) <= window["limit"]
    assert window["next_offset"] == window["offset"] + window["returned"] < window["total"]
