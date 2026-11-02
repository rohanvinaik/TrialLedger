"""The contract's worked examples (tests/fixtures/contract/examples) held to the contract and to the registry.

Generated source examples are checked against fixed raw registry bodies, contract fields and sheet columns.
Independent path traversal, source spans and fixed manual anchors provide checks beyond producer agreement.
"""

import json
from pathlib import Path

from TrialLedger import contract, landscape, mcp_server
from TrialLedger.contract import FIELD_NAMES, SHEETS

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
            assert any(
                name.startswith(f"{where}.".lstrip(".")) or name.startswith(f"{where}[].")
                for name in FIELD_NAMES
            ), where
            if is_value_object(held, ABSENT_KEYS):
                # Module-level absence is checked independently against its raw source below.
                continue
            queue.extend((value, f"{where}.{key}".lstrip("."), positions) for key, value in held.items())
        elif isinstance(held, list):
            assert any(name.startswith(f"{where}[].") for name in FIELD_NAMES), where
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
        "studies[].posted_outcomes[].classes[].categories[].measurements[].comment",
        "studies[].baseline.measures[].classes[].categories[].measurements[].spread",
        "studies[].participant_flow.periods[].withdrawals[].reason",
        "studies[].adverse_events.events[].counts[].at_risk",
        "studies[].interventions[].drug_class",
    }
    assert not any(
        name.startswith(("studies[].coordinates.", "studies[].universe", "cohort.")) for name, _p, _v in found
    )


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
        if name.startswith("studies[].criteria[]."):
            continue  # Literal section scalars are proved by their exact source spans below.
        assert is_value_object(value, READING_KEYS), name
        assert value["rule"] == field.source[0], name
        assert value["status"] in landscape.STATUSES, name


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
    for name, _positions, _value in leaves({"studies": page["studies"]}):
        assert ("mcp", "studies") in FIELD_NAMES[name].consumers, name
    window = page["page"]
    assert window["returned"] == len(page["studies"]) <= window["limit"]
    assert window["next_offset"] == window["offset"] + window["returned"] < window["total"]


def test_literal_sections_are_exact_source_slices_without_clinical_assertions():
    for study in RECORD["studies"]:
        source = BODIES[study["nct"]]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
        assert study["eligibility"]["text"] == source
        assert "".join(section["text"] for section in study["criteria"]) == source
        for section in study["criteria"]:
            assert set(section) == {"heading", "number", "text", "source_start", "source_end"}
            assert source[section["source_start"] : section["source_end"]] == section["text"]
            assert len(section["text"]) <= 1600


def test_independent_manual_anchors_and_module_absences_stay_tied_to_raw_sources():
    absent, posted = RECORD["studies"]
    assert absent["nct"] == "NCT04852770" and posted["nct"] == "NCT01030536"
    assert absent["conditions"] == ["Posttraumatic Stress Disorder", "Covid19"]
    assert BODIES[absent["nct"]]["protocolSection"]["conditionsModule"]["conditions"] == absent["conditions"]
    assert "resultsSection" not in BODIES[absent["nct"]]
    for module in ("posted_outcomes", "baseline", "participant_flow", "adverse_events"):
        assert absent[module]["status"] == "not_posted"
    raw = BODIES[posted["nct"]]["resultsSection"]["baselineCharacteristicsModule"]["measures"][0]
    source_values = raw["classes"][0]["categories"][0]["measurements"]
    shown = posted["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"]
    assert [(value["value"], value["spread"]) for value in source_values[:2]] == [
        ("63.4", "8.7"),
        ("53.7", "16.9"),
    ]
    assert [(value["value"], value["spread"]) for value in shown[:2]] == [("63.4", "8.7"), ("53.7", "16.9")]
    assert source_values[4]["spread"] == shown[4]["spread"] == "NA"
    assert source_values[4]["comment"] == shown[4]["comment"] == "Data was not calculated"
