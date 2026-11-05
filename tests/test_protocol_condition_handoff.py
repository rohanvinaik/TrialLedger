"""Independent delivery contract: show the actual declared assessment condition, never infer it.

Invented ophthalmology choices exercise proposition structure, inherited conditions and proposed support.
The compact summary, readable check paragraph and schedule cell must preserve the same compositional
meaning. Delivery may consolidate repeated tasks; the retained canonical view must not lose their remedy,
check, claim or exact reference. No source interpretation or clinical-suitability claim is tested here.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
from openpyxl import load_workbook

from tests.test_protocol_golden_outputs import GOLDEN, generate
from tests.test_protocol_mcp_lifecycle import CLI, ROOT, McpClient, cli, fetch
from tests.test_protocol_session_replay import _adult_body, _session, adopt
from tests.test_protocol_walkthrough_repairs import _estimand_with_linked_collection
from TrialLedger import clinical_delivery, clinical_display
from TrialLedger.layer2 import run

OWNED_RUN = Path.home() / "Projects/SquishOS/ops/agents/bin/owned-run"


def _atom(name: str, number: float = 15.0) -> dict:
    atom = _adult_body(_session("84"))
    atom["predicate"]["key"] = name
    atom["value"].update(number=number, unit="letters")
    return atom


def _condition(kind: str) -> dict:
    responder = _atom("invented visual-acuity improvement")
    stable = _atom("invented stable visual-acuity score", 5.0)
    rescue = _atom("invented rescue-treatment count", 1.0)
    if kind == "literal":
        return responder
    if kind == "branches":
        return {
            "class": "AllOf",
            "parts": [responder, {"class": "AnyOf", "parts": [stable, {"class": "Not", "part": rescue}]}],
        }
    if kind == "qualified":
        responder["qualifiers"] = {"class": "AnyOf", "parts": [stable, {"class": "Not", "part": rescue}]}
        return responder
    if kind == "timed":
        responder["time"] = {
            "class": "TemporalScope",
            "orientation": "after",
            "anchor": "randomization",
            "anchor_ref": "",
            "lower": 28.0,
            "upper": 28.0,
            "unit": "day",
            "inclusivity": "inclusive",
            "certainty": "explicit",
            "evidence": [],
        }
        return responder
    if kind == "bounded":
        responder["predicate"]["key"] = "invented long responder definition " + "x" * 8300
        return responder
    raise AssertionError(kind)


def _request(kind: str = "literal", *, inherited: bool = False, proposed: bool = False) -> dict:
    request = _estimand_with_linked_collection("collect") if inherited else _session("84", "known")
    adopt(request, "collection")
    protocol = request["session"]["protocol"]
    assessment = next(item for item in protocol["objects"] if item["id"] == "week12")
    assessment["data"]["condition"] = _condition(kind)
    if inherited:
        protocol["checks"].insert(0, copy.deepcopy(_session("84")["session"]["protocol"]["checks"][0]))
    if proposed:
        collection = next(item for item in protocol["objects"] if item["id"] == "collection")
        collection["standing"] = {
            "status": "proposed",
            "resolution": "unresolved",
            "basis": ["user:invented unaccepted collection"],
        }
    return request


def _text(value: object) -> str:
    if isinstance(value, dict):
        return "\n".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value)
    return value if isinstance(value, str) else ""


def _display(kind: str) -> str:
    display = clinical_display.proposition(_condition(kind), "/exact/condition")
    assert display["code"] == ("display_resource_bound" if kind == "bounded" else "displayed"), display
    return display["text"]


def _compact(tmp_path: Path, request: dict) -> tuple[dict, Path]:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    store = tmp_path / "store"
    reply = cli("reason", "--request", str(path), "--store", str(store), "--compact")
    assert reply["code"] == "complete", reply
    return reply, store


def _rows(workbook: str | Path, sheet: str) -> list[dict]:
    book = load_workbook(workbook)
    values = list(book[sheet].values)
    return [dict(zip(values[0], row, strict=True)) for row in values[1:]]


def _paragraph(text: str, check: str) -> str:
    return text.split(f"Check {check} ", 1)[1].split("###", 1)[0]


@pytest.mark.parametrize("kind", ["literal", "branches", "qualified", "timed", "bounded"])
def test_compact_check_names_the_actual_condition_composition_and_bounded_fallback(kind, tmp_path):
    reply, store = _compact(tmp_path, _request(kind))
    row = next(c for c in reply["protocol"]["checks"] if c["id"] == "week12-schedule")
    assert _display(kind) in _text(row), row
    if kind == "bounded":
        reference = row.get("condition_ref")
        assert reference and reference.startswith("/response/result/protocol/checks/")
        retained = cli(
            "reason-result",
            "--store",
            str(store),
            "--id",
            reply["artifact"]["id"],
            "--part",
            "address",
            "--address",
            reference,
            "--max-bytes",
            "65536",
        )
        assert retained.get("page", {}).get("next_offset") is None, retained
        exact_check = retained["value"]
        assert any(
            condition["condition"] == _condition(kind)
            for child in exact_check["children"]
            for condition in child["receipt"]["conditions"]
        ), exact_check


@pytest.mark.parametrize("kind", ["branches", "qualified", "timed", "bounded"])
def test_readable_check_and_schedule_cell_preserve_the_actual_condition(kind, tmp_path):
    reply, store = _compact(tmp_path, _request(kind))
    exported = cli(
        "reason-export",
        "--store",
        str(store),
        "--id",
        reply["artifact"]["id"],
        "--out",
        str(tmp_path / "export"),
    )
    expected = _display(kind)
    assert expected in _paragraph(Path(exported["decision_list"]).read_text(), "week12-schedule")
    schedule = _rows(exported["workbook"], "Schedule of assessments")
    assert expected in str(schedule[0]["Conditionality"])


def test_linked_assessment_condition_reaches_the_estimand_compact_summary(tmp_path):
    reply, _ = _compact(tmp_path, _request("branches", inherited=True))
    row = next(c for c in reply["protocol"]["checks"] if c["id"] == "estimand-check")
    assert _display("branches") in _text(row), row


def test_proposed_collection_display_never_promotes_its_arithmetic_or_admission(tmp_path):
    request = _request("branches", proposed=True)
    canonical_reply = run(request)
    assert canonical_reply["code"] == "complete", canonical_reply
    claims = canonical_reply["result"]["protocol"]["checks"][0]["children"][0]["signals"][0][
        "claim_admission"
    ]
    assert any(row["admission"] == "proposed_refused" for row in claims), claims
    reply, store = _compact(tmp_path, request)
    row = next(c for c in reply["protocol"]["checks"] if c["id"] == "week12-schedule")
    assert _display("branches") in _text(row), row
    exported = cli(
        "reason-export",
        "--store",
        str(store),
        "--id",
        reply["artifact"]["id"],
        "--out",
        str(tmp_path / "export"),
    )
    retained = json.loads(
        (Path(exported["decision_list"]).parent / "artifacts" / f"{reply['artifact']['id']}.json").read_text()
    )
    assert retained["response"]["result"]["protocol"] == canonical_reply["result"]["protocol"]
    findings = _rows(exported["workbook"], "Protocol findings")
    assert any(
        r["Admission"] == "proposed_refused" and r["Kind of finding"] == "Not applied" for r in findings
    )


class _OwnedMcp(McpClient):
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [
                str(OWNED_RUN),
                "--label",
                "protocol-condition-handoff-test",
                "--",
                CLI,
                "mcp",
                "--root",
                str(root),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            cwd=ROOT,
        )
        self.ident = 0
        reply = self.send(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "condition-handoff", "version": "1"},
            },
        )
        assert reply["result"]["serverInfo"]
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()


def test_initialized_mcp_and_cli_export_inherited_conditions_and_keep_exact_open_tasks(tmp_path):
    request = _request("branches", inherited=True)
    cli_reply, store = _compact(tmp_path, request)
    client = _OwnedMcp(tmp_path / "served")
    try:
        reply = client.call("reason", request=request, response_view="compact")
        assert reply["result_digest"] == cli_reply["result_digest"]
        assert reply["protocol"] == cli_reply["protocol"]
        exported = client.call("reason_export", id=reply["artifact"]["id"])
        cli_export = cli(
            "reason-export",
            "--store",
            str(store),
            "--id",
            cli_reply["artifact"]["id"],
            "--out",
            str(tmp_path / "export"),
        )
        assert Path(exported["decision_list"]).read_bytes() == Path(cli_export["decision_list"]).read_bytes()
        text = Path(exported["decision_list"]).read_text()
        assert _display("branches") in _paragraph(text, "estimand-check")
        canonical_view = fetch(client, reply["artifact"]["id"], "/response/protocol_view")
        direct_view = clinical_delivery.protocol_delivery_view(run(request)["result"])
        assert canonical_view["open_items"] == direct_view["open_items"]
        for task in canonical_view["open_items"]:
            assert task["check"] and task["text"] and task["ref"].startswith("/protocol/checks/")
        assert any(item.get("claim") for item in canonical_view["open_items"])
        assert ".json" in text, "the handoff must retain links to exact stored results"
    finally:
        client.close()


def test_unconditional_existing_delivery_is_byte_identical_to_its_frozen_outputs(tmp_path):
    name = "policy-violation-known"
    produced = generate("fixture", name, tmp_path)
    for filename, value in produced.items():
        assert value == (GOLDEN / f"fixture-{name}" / filename).read_text(), filename


def _task(
    claim: str,
    *,
    check: str = "visit-check",
    ref: str = "/result/one",
    kind: str = "claim_conditional",
    text: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "check": check,
        "claim": claim,
        "text": text or f"Invented remedy for {claim}.",
        "ref": ref,
    }


def _delivery_check(identity: str, claims: dict[str, str]) -> dict:
    return {
        "id": identity,
        "claims": [
            {"id": claim, "outcome": "satisfied", "effective_outcome": effective}
            for claim, effective in claims.items()
        ],
        "conditions": [{"object": "week12", "condition": _condition("branches")}],
    }


def _members(items: list[dict]) -> list[dict]:
    return [member for item in items for member in item.get("members", [item])]


def test_delivery_group_retains_every_original_kind_check_claim_remedy_and_reference():
    from collections import Counter

    items = [
        _task("visit"),
        _task("window"),
        _task("visit"),
        _task("target", kind="claim_failure"),
        _task("target", kind="claim_conditional"),
    ]
    untouched = copy.deepcopy(items)
    checks = [
        _delivery_check(
            "visit-check", {"visit": "satisfied", "window": "satisfied", "target": "not_collected"}
        )
    ]
    delivered = clinical_delivery._protocol_delivery_items(items, checks)
    keys = ("kind", "check", "claim", "text", "ref")
    assert Counter(tuple(item[key] for key in keys) for item in _members(delivered)) == Counter(
        tuple(item[key] for key in keys) for item in items
    )
    satisfied = [item for item in delivered if item.get("claims")]
    assert len(satisfied) == 1
    assert {member["claim"] for member in satisfied[0]["members"]} == {"visit", "window"}
    assert items == untouched, "delivery must never rewrite the canonical open tasks"


def test_delivery_never_groups_claims_across_distinct_checks_or_result_references():
    items = [
        _task("visit", check="visit-check", ref="/result/one"),
        _task("window", check="visit-check", ref="/result/two"),
        _task("visit", check="second-check", ref="/result/one"),
    ]
    checks = [
        _delivery_check("visit-check", {"visit": "satisfied", "window": "satisfied"}),
        _delivery_check("second-check", {"visit": "satisfied"}),
    ]
    delivered = clinical_delivery._protocol_delivery_items(items, checks)
    assert len(delivered) == 3
    for item in delivered:
        assert len({member["check"] for member in item["members"]}) == 1
        assert len({member["ref"] for member in item["members"]}) == 1


def test_proposed_undetermined_and_failed_claims_never_join_a_satisfied_conditional_group():
    items = [
        _task("visit"),
        _task("window"),
        _task("proposed"),
        _task("unknown"),
        _task("failure", kind="claim_failure"),
        _task("context", kind="context_note"),
    ]
    checks = [
        _delivery_check(
            "visit-check",
            {
                "visit": "satisfied",
                "window": "satisfied",
                "proposed": "proposed_refused",
                "unknown": "undetermined",
                "failure": "not_collected",
                "context": "satisfied",
            },
        )
    ]
    delivered = clinical_delivery._protocol_delivery_items(items, checks)
    grouped = [item for item in delivered if item.get("claims")]
    assert len(grouped) == 1
    assert grouped[0]["claims"] == ["visit", "window"]
    assert all(member["kind"] == "claim_conditional" for member in grouped[0]["members"])
    assert {item["claim"] for item in delivered if not item.get("claims")} == {
        "proposed",
        "unknown",
        "failure",
        "context",
    }


def test_markdown_labels_repeated_remedy_wording_with_its_check_and_claim(tmp_path):
    request = _request("literal")
    checks = request["session"]["protocol"]["checks"]
    repeated = copy.deepcopy(checks[0])
    repeated["id"] = "week12-recheck"
    checks.append(repeated)
    reply, store = _compact(tmp_path, request)
    exported = cli(
        "reason-export",
        "--store",
        str(store),
        "--id",
        reply["artifact"]["id"],
        "--out",
        str(tmp_path / "export"),
    )
    text = Path(exported["decision_list"]).read_text()
    open_items = text.split("### Open items", 1)[1]
    for check in ("week12-schedule", "week12-recheck"):
        for claim in ("target", "window"):
            assert f"Check {check}, claim {claim}: " in open_items
