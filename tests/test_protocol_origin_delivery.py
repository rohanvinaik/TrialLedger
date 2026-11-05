"""Caller-attributed source readings remain visible beside exactly their affected protocol checks.

The source fixture supplies an addressable record, not a warrant for the invented protocol reading. Origin
display is context: it never promotes standing, confirms a person, or changes a logical consequence.
"""

import copy
import json
import subprocess

import openpyxl

from tests.test_protocol_composition_matrix import ESTIMAND, SCHEDULE, _base, mutate, obj, with_alternative
from tests.test_protocol_mcp_lifecycle import CLI, ROOT, McpClient
from TrialLedger import clinical_delivery
from TrialLedger.layer2 import protocol_view, run


def source_plan(identity: str = "week12") -> dict:
    return mutate(_base(), identity, "origin_src")


def row_of(rows: list[dict], identity: str) -> dict:
    return next(row for row in rows if row["id"] == identity)


def checked(request: dict) -> dict:
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def readings(row: dict) -> list[dict]:
    return row.get("source_readings", [])


def expected_reading(request: dict, identity: str = "week12") -> dict:
    return {"object": identity, "origin": copy.deepcopy(obj(request, identity)["origin"])}


def logical_signature(reply: dict) -> dict:
    checks = []
    fields = ("code", "calculation_code", "status", "admission", "blockers", "application", "finding_status")
    for check in reply["result"]["protocol"]["checks"]:
        checks.append(
            {
                "id": check["id"],
                "scope": check["scope"],
                "signals": [
                    {key: copy.deepcopy(signal.get(key)) for key in fields}
                    for child in check["children"]
                    for signal in child["signals"]
                ],
            }
        )
    metadata_fields = ("kind", "logical_result", "standing", "completion", "disposition")
    return {
        "checks": checks,
        "metadata": [
            {key: copy.deepcopy(finding.get(key)) for key in metadata_fields}
            for finding in reply["metadata"]["findings"]
        ],
    }


def test_view_and_check_summaries_keep_the_exact_attributed_origin_of_each_gating_source_input():
    request = source_plan()
    reply = checked(request)
    view = protocol_view.view(reply["result"])
    delivery = clinical_delivery.protocol_delivery_view(reply["result"])
    expected = expected_reading(request)

    for check_id in (SCHEDULE, ESTIMAND):
        assert readings(row_of(view["checks"], check_id)) == [expected]
        assert readings(row_of(delivery["check_summaries"], check_id)) == [expected]
    assert logical_signature(reply) == logical_signature(checked(copy.deepcopy(_base())))


def test_a_nested_baseline_source_reading_reaches_the_estimand_but_not_independent_schedule_timing():
    request = source_plan("base-score")
    view = protocol_view.view(checked(request)["result"])

    assert readings(row_of(view["checks"], ESTIMAND)) == [expected_reading(request, "base-score")]
    assert readings(row_of(view["checks"], SCHEDULE)) == []


def test_an_unrelated_source_reading_never_appears_as_check_input_provenance():
    request = source_plan("base-score")
    item = obj(request, "base-score")
    unrelated = copy.deepcopy(item)
    unrelated.update(id="unrelated-source-reading", support=[])
    item["origin"] = copy.deepcopy(obj(_base(), "base-score")["origin"])
    request["session"]["protocol"]["objects"].append(unrelated)

    reply = checked(request)
    view = protocol_view.view(reply["result"])

    assert all(readings(row) == [] for row in view["checks"])
    assert logical_signature(reply) == logical_signature(checked(copy.deepcopy(_base())))


def test_showing_a_proposed_reading_never_admits_it_as_a_known_fact():
    request = source_plan()
    obj(request, "week12")["standing"]["status"] = "proposed"
    reply = checked(request)
    view = protocol_view.view(reply["result"])

    assert readings(row_of(view["checks"], ESTIMAND)) == [expected_reading(request)]
    assert row_of(view["checks"], ESTIMAND)["standing"] == "proposed"
    check = row_of(reply["result"]["protocol"]["checks"], ESTIMAND)
    assert check["children"][0]["signals"][0]["admission"]["code"] == "proposed_refused"
    findings = [f for f in reply["metadata"]["findings"] if f["kind"].startswith("estimand")]
    assert findings
    assert not any(finding["disposition"] == "settled" for finding in findings)


def test_hypothetical_replacements_display_their_own_origins_instead_of_the_baseline_reading():
    request = source_plan()
    replacement = copy.deepcopy(obj(request, "week12"))
    replacement["origin"] = copy.deepcopy(obj(_base(), "week12")["origin"])
    reply = checked(with_alternative(request, replacement))
    decision = reply["result"]["protocol"]["decisions"][0]
    baseline = row_of(decision["alternatives"], "as-is")
    candidate = row_of(decision["alternatives"], "var")
    expected = [{"check": check_id, **expected_reading(request)} for check_id in (SCHEDULE, ESTIMAND)]

    assert readings(baseline) == expected
    assert readings(candidate) == []
    assert candidate["frame"] == "hypothetical"
    displayed = clinical_delivery.protocol_delivery_view(reply["result"])["decisions"][0]
    assert readings(row_of(displayed["alternatives"], "as-is")) == expected
    assert readings(row_of(displayed["alternatives"], "var")) == []
    assert candidate["unconditional_application"] == "withheld"


def test_a_reading_introduced_only_by_a_hypothetical_plan_stays_with_that_plan():
    request = source_plan()
    replacement = copy.deepcopy(obj(request, "week12"))
    obj(request, "week12")["origin"] = copy.deepcopy(obj(_base(), "week12")["origin"])
    reply = checked(with_alternative(request, replacement))
    decision = reply["result"]["protocol"]["decisions"][0]
    baseline = row_of(decision["alternatives"], "as-is")
    candidate = row_of(decision["alternatives"], "var")
    expected = [
        {"check": check_id, "object": "week12", "origin": replacement["origin"]}
        for check_id in (SCHEDULE, ESTIMAND)
    ]

    assert readings(baseline) == []
    assert readings(candidate) == expected
    assert candidate["frame"] == "hypothetical"
    assert candidate["unconditional_application"] == "withheld"
    displayed = clinical_delivery.protocol_delivery_view(reply["result"])["decisions"][0]
    assert readings(row_of(displayed["alternatives"], "var")) == expected


def test_user_choice_only_checks_keep_source_reading_context_absent_or_empty():
    reply = checked(copy.deepcopy(_base()))
    view = protocol_view.view(reply["result"])
    delivery = clinical_delivery.protocol_delivery_view(reply["result"])

    assert all(readings(row) == [] for row in view["checks"])
    assert all(readings(row) == [] for row in delivery["check_summaries"])


def cli(*arguments: str) -> dict:
    completed = subprocess.run([CLI, *arguments], capture_output=True, text=True, cwd=ROOT, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


def markdown_check_blocks(text: str) -> dict[str, str]:
    """The check paragraphs under Findings, excluding later headings such as Adoption."""
    blocks: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("Check "):
            current = line.removeprefix("Check ").split(" ", 1)[0]
            blocks[current] = []
        elif line.startswith("#"):
            current = None
        if current is not None:
            blocks[current].append(line)
    return {key: "\n".join(lines) for key, lines in blocks.items()}


def test_real_cli_and_initialized_mcp_keep_source_readings_in_compact_replies_and_export(tmp_path):
    request = source_plan()
    submitted = tmp_path / "request.json"
    submitted.write_text(json.dumps(request))
    store = tmp_path / "store"
    cli_reply = cli("reason", "--request", str(submitted), "--store", str(store), "--compact")
    client = McpClient(tmp_path / "served")
    try:
        mcp_reply = client.call("reason", request=request, response_view="compact")
        exported = client.call("reason_export", id=mcp_reply["artifact"]["id"])
    finally:
        client.close()

    assert cli_reply["result_digest"] == mcp_reply["result_digest"]
    expected = expected_reading(request)
    for check_id in (SCHEDULE, ESTIMAND):
        assert readings(row_of(cli_reply["protocol"]["checks"], check_id)) == [expected]
        assert readings(row_of(mcp_reply["protocol"]["checks"], check_id)) == [expected]

    origin = expected["origin"]
    text = ROOT.joinpath(exported["decision_list"]).read_text(encoding="utf-8")
    blocks = markdown_check_blocks(text)
    for check_id in (SCHEDULE, ESTIMAND):
        assert origin["ref"] in blocks[check_id]
        assert origin["source"] in blocks[check_id]
        assert "caller-attributed" in blocks[check_id].casefold()

    book = openpyxl.load_workbook(exported["workbook"])
    sheet = list(book["Protocol findings"].iter_rows(values_only=True))
    assert any("caller-attributed" in str(value).casefold() for row in sheet for value in row)
    for check_id in (SCHEDULE, ESTIMAND):
        rows = [row for row in sheet if check_id in row]
        assert rows, check_id
        assert any(origin["ref"] in str(row) and origin["source"] in str(row) for row in rows)


def test_the_source_reading_projection_is_detached_and_uses_the_actual_check_closure():
    from TrialLedger.layer2.protocol_origins import source_readings

    request = source_plan("base-score")
    reply = checked(request)
    objects = request["session"]["protocol"]["objects"]
    check = row_of(reply["result"]["protocol"]["checks"], ESTIMAND)
    objects_before, check_before = copy.deepcopy(objects), copy.deepcopy(check)

    result = source_readings(objects, check)

    assert result == [expected_reading(request, "base-score")]
    result[0]["origin"]["ref"] = "caller:changed detached display"
    assert objects == objects_before and check == check_before


def test_the_source_reading_projection_never_selects_a_source_outside_the_checks_gating_closure():
    from TrialLedger.layer2.protocol_origins import source_readings

    request = source_plan("base-score")
    reply = checked(request)
    check = row_of(reply["result"]["protocol"]["checks"], SCHEDULE)

    assert source_readings(request["session"]["protocol"]["objects"], check) == []


def test_the_source_reading_projection_never_relabels_a_user_choice_as_a_source_reading():
    from TrialLedger.layer2.protocol_origins import source_readings

    request = copy.deepcopy(_base())
    reply = checked(request)
    check = row_of(reply["result"]["protocol"]["checks"], ESTIMAND)

    assert source_readings(request["session"]["protocol"]["objects"], check) == []
