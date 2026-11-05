"""Intent tests for protocol delivery (C9, OUT-1, OUT-2) through the public CLI only.

Each test replays a frozen v2 design_session fixture with `trialledger reason`, then reads
`reason-export` output. Assertions come from delivery.md, view.md and verification.md.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest
from openpyxl import load_workbook

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / ".venv" / "bin" / "trialledger"
RESULTS = (
    REPO / "openspec" / "changes" / "connect-protocol-design-workflow" / "interface" / "fixtures" / "results"
)

ALL_FIXTURES = sorted(path.stem for path in RESULTS.glob("*.json"))
SECTION_IDS = [
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
]
FINDING_LABELS = {"conflict_found", "repair_choice_open", "none_found_in_declared_checks", "not_checked"}
# Effective outcomes that are admitted conflicts or repair choices in delivery.md and view.md.
ADMITTED_FAILURES = {
    "violation",
    "gap",
    "competing",
    "not_established",
    "outside_window",
    "not_collected",
    "uncovered",
    "no_feasible_time",
    "no_permitted_time",
}
VIOLATION_TEMPLATE = "{n} declared prohibition violation(s) in reachable declared situations."
REFUSED_PREFIX = "Not applied: the deciding premise is "
BULLET_PATTERN = (
    r"prohibition: 1 declared prohibition violation\(s\) in reachable declared situations\. "
    r"— standing [^;]+; result \S+"
)
FORBIDDEN_WORD = re.compile(r"\b(safe|valid|complete|adequate|approved)\b", re.IGNORECASE)
NEGATION_BEFORE = re.compile(r"\b(not|no)\s*$", re.IGNORECASE)
JSON_CELL = re.compile(r'^\s*(\{|\[\s*")|\{\s*"')
PROTOCOL_SHEET_HEADERS = {
    "Protocol synopsis": [
        "Section",
        "Declared",
        "Coverage",
        "Findings",
        "Findings text",
        "Reasons",
        "Objects",
        "Checks",
    ],
    "Protocol findings": [
        "Kind of finding",
        "Check",
        "Kind",
        "Required",
        "Claim",
        "Outcome",
        "Effective outcome",
        "Admission",
        "Application",
        "Standing",
        "Arithmetic standing",
        "Applicability standing",
        "Wording",
        "Determining references",
        "Result reference",
    ],
    "Schedule of assessments": [
        "Check",
        "Assessment",
        "Collection",
        "Cohort",
        "Arm",
        "Phase",
        "Conditionality",
        "Measurement",
        "Mode",
        "Anchor",
        "Unit",
        "Nominal target",
        "Permitted window",
        "Collection availability",
        "Feasible window",
        "Full-coverage gap",
        "Nominal outcome",
        "Standing",
        "Origin",
        "Result reference",
    ],
    "Plan comparisons": [
        "Decision",
        "Question",
        "Disposition",
        "Alternative",
        "Label",
        "Frame",
        "Compatibility",
        "Conditional checks",
        "Assumptions",
        "Application",
    ],
}
SCHEDULE_TABLE_HEADER = [
    "Check",
    "Cohort",
    "Arm",
    "Phase",
    "Conditionality",
    "Measurement",
    "Mode",
    "Anchor",
    "Unit",
    "Nominal",
    "Permitted",
    "Collection",
    "Feasible",
    "Gap",
    "Nominal outcome",
]
SECTIONS_TABLE_HEADER = ["Section", "Declared", "Coverage", "Findings"]


def load_fixture(name):
    """Return the frozen {request, result} fixture as a dict."""
    return json.loads((RESULTS / f"{name}.json").read_text())


def replay(name, tmp_path):
    """Run the fixture request through `reason --compact` and return (fixture, reply, store)."""
    data = load_fixture(name)
    store = tmp_path / "store"
    request = tmp_path / "request.json"
    request.write_text(json.dumps(data["request"]))
    proc = subprocess.run(
        [str(CLI), "reason", "--request", str(request), "--store", str(store), "--compact"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert proc.returncode == 0, f"reason refused the fixture request: {proc.stderr or proc.stdout}"
    return data, json.loads(proc.stdout), store


def export(store, artifact_id, tmp_path):
    """Run `reason-export` into a new folder and return its review directory."""
    out = tmp_path / "export"
    proc = subprocess.run(
        [str(CLI), "reason-export", "--store", str(store), "--id", artifact_id, "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert proc.returncode == 0, f"reason-export refused: {proc.stderr or proc.stdout}"
    return out / "review"


def admitted_failures(data):
    """Yield (check, claim, outcome) for accepted claims whose effective outcome is a conflict or repair."""
    for check in data["result"]["protocol"]["checks"]:
        for child in check["children"]:
            for signal in child.get("signals") or []:
                for row in signal.get("claim_admission") or []:
                    if row["admission"] == "accepted" and row["effective_outcome"] in ADMITTED_FAILURES:
                        yield check["id"], row["id"], row["effective_outcome"]


def refused_rows(data):
    """Yield (check, claim) for claim rows whose admission is not accepted."""
    for check in data["result"]["protocol"]["checks"]:
        for child in check["children"]:
            for signal in child.get("signals") or []:
                for row in signal.get("claim_admission") or []:
                    if row["admission"] != "accepted":
                        yield check["id"], row["id"]


def claim_value(data, check_id, claim_id):
    """Return the canonical violations_found count for a claim from its child result."""
    for check in data["result"]["protocol"]["checks"]:
        if check["id"] != check_id:
            continue
        for child in check["children"]:
            signals = child["result"]["result"]["signals"]
            for claim in signals[0]["value"]["claims"]:
                if claim["id"] == claim_id:
                    return claim
    raise AssertionError(f"no canonical claim {check_id}/{claim_id} in fixture")


def findings_for(reply, check_id, claim_id):
    """Return compact findings that name the given check and claim."""
    return [f for f in reply["protocol"]["findings"] if f["check"] == check_id and f["claim"] == claim_id]


def forbidden_hits(text):
    """Return forbidden status words that are not negated by a preceding 'not' or 'no'."""
    hits = []
    for match in FORBIDDEN_WORD.finditer(text):
        if NEGATION_BEFORE.search(text[: match.start()]):
            continue
        hits.append(match.group(0))
    return hits


def protocol_section(markdown):
    """Return the lines of the `## Protocol` section of the decision list."""
    lines = markdown.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == "## Protocol"]
    assert len(starts) == 1, "decision list must contain exactly one `## Protocol` section"
    body = []
    for line in lines[starts[0] + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def subsection(lines, title):
    """Return the lines under a `### title` heading inside a section, or fail if absent."""
    starts = [i for i, line in enumerate(lines) if re.fullmatch(rf"#*\s*{re.escape(title)}\s*", line.strip())]
    assert starts, f"decision list `## Protocol` lacks the `### {title}` subsection"
    body = []
    for line in lines[starts[0] + 1 :]:
        if line.startswith("#"):
            break
        body.append(line)
    return body


def table_rows(lines, header):
    """Return markdown table rows that follow the exact header, as dicts keyed by header cell."""
    for i, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and cells == header:
            rows = []
            for row in lines[i + 1 :]:
                if not row.strip().startswith("|"):
                    break
                if re.match(r"^\|\s*-", row.strip()):
                    continue
                values = [cell.strip() for cell in row.strip().strip("|").split("|")]
                rows.append(dict(zip(header, values, strict=False)))
            return rows
    raise AssertionError(f"no markdown table with header {header}")


def sheet_rows(workbook, title):
    """Return the header list and data rows of a sheet as dicts keyed by header."""
    assert title in workbook.sheetnames, f"workbook lacks the `{title}` sheet"
    sheet = workbook[title]
    header = [cell.value for cell in sheet[1]]
    header = [h for h in header if h is not None]
    rows = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in values):
            continue
        rows.append(dict(zip(header, [None if v is None else str(v) for v in values], strict=False)))
    return header, rows


def all_sheet_cells(workbook):
    """Yield every text cell in the protocol sheets of the workbook."""
    for title in PROTOCOL_SHEET_HEADERS:
        if title not in workbook.sheetnames:
            continue
        for row in workbook[title].iter_rows(values_only=True):
            for value in row:
                if value is not None:
                    yield title, str(value)


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_compact_reply_carries_all_eight_sections_with_coverage_and_findings(name, tmp_path):
    """The compact reply's protocol block lists all eight sections, each with coverage and findings."""
    _, reply, _ = replay(name, tmp_path)
    protocol = reply.get("protocol")
    assert protocol, "compact reply lacks a `protocol` key (delivery.md, compact reply)"
    assert [s["id"] for s in protocol["sections"]] == SECTION_IDS, (
        "sections must be all eight, in view order, never paged"
    )
    for section in protocol["sections"]:
        assert section.get("coverage"), f"section {section.get('id')} must carry coverage beside its findings"
        assert section.get("findings") in FINDING_LABELS, (
            f"section {section.get('id')} findings label must be one of the four contract labels"
        )
        assert section.get("findings_text"), f"section {section.get('id')} must carry findings_text"


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_compact_protocol_has_paging_omission_and_check_keys(name, tmp_path):
    """The compact protocol block exposes checks, decisions, pages and omitted counts with their keys."""
    _, reply, _ = replay(name, tmp_path)
    protocol = reply["protocol"]
    for key in ("checks", "decisions", "pages", "omitted", "findings"):
        assert key in protocol, f"compact protocol lacks `{key}` (delivery.md, compact reply)"
    assert set(protocol["omitted"]) >= {"findings", "checks"}, "omitted must count findings and checks"
    assert all(isinstance(protocol["omitted"][k], int) for k in ("findings", "checks")), (
        "omitted counts are integers"
    )
    for check in protocol["checks"]:
        for key in ("id", "kind", "required", "code", "conflicts", "repairs", "conditional"):
            assert key in check, f"check row lacks `{key}` (delivery.md, compact reply)"
    for finding in protocol["findings"]:
        assert finding.get("ref"), "every compact finding must keep a result reference"


@pytest.mark.parametrize(
    "name",
    [n for n in ALL_FIXTURES if list(admitted_failures(load_fixture(n)))],
)
def test_every_admitted_conflict_or_repair_survives_compact_reply(name, tmp_path):
    """Each admitted conflict or repair choice in the canonical protocol is listed or counted as omitted."""
    data, reply, _ = replay(name, tmp_path)
    omitted = reply["protocol"]["omitted"]["findings"]
    for check_id, claim_id, outcome in admitted_failures(data):
        matches = findings_for(reply, check_id, claim_id)
        assert matches or omitted > 0, (
            f"admitted {outcome} for {check_id}/{claim_id} disappeared from the compact reply (OUT-1)"
        )


@pytest.mark.parametrize(
    "name",
    [n for n in ALL_FIXTURES if list(admitted_failures(load_fixture(n)))],
)
def test_admitted_conflicts_and_repairs_are_ordered_before_refused_and_section_findings(name, tmp_path):
    """Admitted conflicts and repairs come before refused claims and section findings in compact findings."""
    data, reply, _ = replay(name, tmp_path)
    findings = reply["protocol"]["findings"]
    expected = {(c, cl) for c, cl, _ in admitted_failures(data)}
    indices = [i for i, f in enumerate(findings) if (f["check"], f["claim"]) in expected]
    if not indices:
        pytest.skip("admitted failures were all counted as omitted; ordering is not visible")
    later = [i for i, f in enumerate(findings) if f["check"] is None or f["text"].startswith(REFUSED_PREFIX)]
    if later:
        assert max(indices) < min(later), (
            "admitted conflicts and repairs must precede refused and section findings"
        )


def test_policy_violation_known_is_first_compact_finding_with_exact_wording(tmp_path):
    """A known prohibition violation is the first compact finding, worded from the canonical count."""
    data, reply, _ = replay("policy-violation-known", tmp_path)
    count = claim_value(data, "interim-safety", "prohibition")["violations_found"]
    assert count >= 1, "fixture must carry a known violation for this test to mean anything"
    first = reply["protocol"]["findings"][0]
    assert (first["check"], first["claim"]) == ("interim-safety", "prohibition"), (
        "the admitted violation must be the first compact finding (admitted conflicts first)"
    )
    assert first["text"] == VIOLATION_TEMPLATE.format(n=count), (
        "violation wording must come from the wording table"
    )


def test_policy_violation_known_check_counts_one_conflict_and_no_repairs(tmp_path):
    """The check row counts the admitted violation as a conflict and no repair choice."""
    _, reply, _ = replay("policy-violation-known", tmp_path)
    check = next(c for c in reply["protocol"]["checks"] if c["id"] == "interim-safety")
    assert check["conflicts"] == 1, "one admitted violation must count as one conflict"
    assert check["repairs"] == 0, "a violation is not a repair choice"


def test_policy_violation_known_section_is_specified_with_conflict_found(tmp_path):
    """A requested safety section with a known violation reads specified, and conflict_found beside it."""
    _, reply, _ = replay("policy-violation-known", tmp_path)
    safety = next(s for s in reply["protocol"]["sections"] if s["id"] == "safety")
    assert safety["coverage"] == "specified", "a violated requested section is specified, not open (view.md)"
    assert safety["findings"] == "conflict_found", (
        "a known violation must read conflict_found beside coverage"
    )


def test_policy_violation_proposed_refused_claim_is_not_an_admitted_conflict(tmp_path):
    """A proposed (refused) violation is not counted as a conflict and reads as not applied."""
    data, reply, _ = replay("policy-violation-proposed", tmp_path)
    check = next(c for c in reply["protocol"]["checks"] if c["id"] == "interim-safety")
    assert check["conflicts"] == 0, "a refused proposed violation must not be an admitted conflict"
    safety = next(s for s in reply["protocol"]["sections"] if s["id"] == "safety")
    assert safety["findings"] != "conflict_found", "refused support must not produce conflict_found"
    assert safety["coverage"] == "open", "an unresolved prohibition claim keeps the requested section open"
    for check_id, claim_id in refused_rows(data):
        for finding in findings_for(reply, check_id, claim_id):
            assert finding["text"].startswith(REFUSED_PREFIX), (
                f"refused {check_id}/{claim_id} must read as not applied, not as its raw outcome"
            )
            assert "violation(s)" not in finding["text"], (
                "a refused violation must not show the violation wording"
            )


def test_schedule_refuted_outside_window_is_repair_and_refused_window_is_not(tmp_path):
    """The admitted outside-window target is the repair; the refused visit and window claims are not."""
    data, reply, _ = replay("schedule-refuted-and-conditional", tmp_path)
    check = next(c for c in reply["protocol"]["checks"] if c["id"] == "week12-schedule")
    assert check["repairs"] == 1, "one admitted outside-window nominal target is one repair choice"
    assert check["conflicts"] == 0, "no admitted conflicts in the schedule fixture"
    target = findings_for(reply, "week12-schedule", "target")
    assert target and target[0]["text"] == "The nominal target is outside the permitted window.", (
        "the nominal target must carry the outside_window wording"
    )
    for claim_id in ("visit", "window"):
        for finding in findings_for(reply, "week12-schedule", claim_id):
            assert finding["text"].startswith(REFUSED_PREFIX), (
                f"refused claim {claim_id} must read not applied, not a repair"
            )


def test_schedule_refuted_compact_check_is_not_conditional(tmp_path):
    """The refuted schedule check has no declared condition, so it is not marked conditional."""
    _, reply, _ = replay("schedule-refuted-and-conditional", tmp_path)
    check = next(c for c in reply["protocol"]["checks"] if c["id"] == "week12-schedule")
    assert check["conditional"] is False, "no declared condition means the check is unconditional"


def test_conditional_admitted_repair_keeps_its_prefix_in_compact_reply(tmp_path):
    """A conditional admitted repair keeps its 'If the declared condition applies:' prefix."""
    _, reply, _ = replay("schedule-conditional-assessment", tmp_path)
    targets = findings_for(reply, "week12-schedule", "target")
    assert targets, "the conditional nominal target must remain visible in compact findings"
    assert targets[0]["text"].startswith("If the declared condition applies: "), (
        "conditional claims keep the wording prefix (view.md wording table)"
    )
    assert "outside planned collection" in targets[0]["text"], "the not-collected wording must remain"


def test_policy_work_limit_claim_reads_not_computed_not_satisfied(tmp_path):
    """A work-limited claim reads not computed, and its safety section reads not_computed."""
    _, reply, _ = replay("policy-work-limit", tmp_path)
    coverage = findings_for(reply, "big-safety", "coverage")
    assert coverage and coverage[0]["text"] == "Not computed within the declared work limit.", (
        "a work-limited claim is not computed, never satisfied"
    )
    safety = next(s for s in reply["protocol"]["sections"] if s["id"] == "safety")
    assert safety["coverage"] == "not_computed", (
        "a work-limited consuming check makes the section not_computed"
    )


def test_efficacy_external_method_is_not_computed_in_section_coverage(tmp_path):
    """The external survival method makes the efficacy section not_computed in the compact reply."""
    _, reply, _ = replay("efficacy-binomial-and-external", tmp_path)
    efficacy = next(s for s in reply["protocol"]["sections"] if s["id"] == "efficacy")
    assert efficacy["coverage"] == "not_computed", "an external method without inputs is not computed"
    listed = any(f["check"] == "survival-method" for f in reply["protocol"]["findings"])
    assert listed or reply["protocol"]["omitted"]["findings"] > 0, (
        "the not-computed declaration must be listed or counted, not dropped"
    )


def test_compact_findings_never_name_a_caller_label_inside_computed_text(tmp_path):
    """Computed wording never contains the caller's check or object label."""
    _, reply, _ = replay("policy-violation-known", tmp_path)
    for finding in reply["protocol"]["findings"]:
        assert "interim-safety" not in finding["text"], (
            "a caller label must not appear in a computed wording template"
        )


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_decision_list_has_protocol_section_with_sections_table_for_all_eight(name, tmp_path):
    """The decision list's Protocol section lists all eight sections, matching the compact reply."""
    _, reply, store = replay(name, tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    lines = protocol_section((review / "decision-list.md").read_text())
    rows = table_rows(subsection(lines, "Sections"), SECTIONS_TABLE_HEADER)
    assert [row["Section"] for row in rows] == SECTION_IDS, "Sections table must list all eight in order"
    for row, section in zip(rows, reply["protocol"]["sections"], strict=True):
        assert row["Coverage"] == section["coverage"], "table coverage must match the view, not be recomputed"
        assert row["Findings"] in {section["findings"], section["findings_text"]}, (
            "table findings must come from the view beside coverage (label or its readable text)"
        )


def test_decision_list_protocol_order_and_limits_for_schedule_fixture(tmp_path):
    """The Protocol section has its subsections in contract order and states the limits of claim."""
    _, reply, store = replay("schedule-refuted-and-conditional", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    markdown = (review / "decision-list.md").read_text()
    lines = protocol_section(markdown)
    order = ["Sections", "Findings", "Schedule of assessments", "Open items", "Limits"]
    headings = [line.strip().lstrip("#").strip() for line in lines if line.startswith("### ")]
    positions = [headings.index(title) for title in order]
    assert positions == sorted(positions), (
        f"Protocol subsections must appear in contract order, got {headings}"
    )
    limits = subsection(lines, "Limits")
    text = "\n".join(limits)
    assert "Coverage and violations are over the declared variables, objects and claims only." in text, (
        "the view's limits_of_claim must reach the decision list"
    )
    assert "Rendered decimals are rounded displays; exact rationals are canonical." in text, (
        "the decimal-display limit must reach the decision list"
    )


def test_decision_list_schedule_table_keeps_permitted_window_apart_from_feasible(tmp_path):
    """The schedule table keeps permitted [77, 91], gap (80, 91] and feasible [77, 80] apart."""
    _, reply, store = replay("schedule-refuted-and-conditional", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    lines = protocol_section((review / "decision-list.md").read_text())
    rows = table_rows(subsection(lines, "Schedule of assessments"), SCHEDULE_TABLE_HEADER)
    assert len(rows) == 1, "one schedule check must yield exactly one schedule row"
    row = rows[0]
    assert row["Permitted"] == "[77, 91] days from randomization", (
        "the original permitted window must be shown unchanged"
    )
    assert row["Feasible"] == "[77, 80] days from randomization", (
        "feasible is the intersection of permitted and collection availability"
    )
    assert row["Feasible"] != row["Permitted"], (
        "the permitted window must never be replaced by the feasible window"
    )
    assert row["Gap"] == "(80, 91] days from randomization", (
        "the full-coverage gap is the uncollected part of the permitted window"
    )
    assert row["Conditionality"] == "unconditional", "no declared condition means unconditional"


def test_decision_list_open_items_are_numbered_and_include_known_violation(tmp_path):
    """Open items are numbered and include the admitted violation wording."""
    data, reply, store = replay("policy-violation-known", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    lines = protocol_section((review / "decision-list.md").read_text())
    items = [line for line in subsection(lines, "Open items") if re.match(r"^\s*\d+\.\s", line)]
    assert items, "Open items must be a numbered list"
    count = claim_value(data, "interim-safety", "prohibition")["violations_found"]
    wording = VIOLATION_TEMPLATE.format(n=count)
    assert any(wording in item for item in items), (
        "the admitted violation must be listed under Open items (OUT-1)"
    )


def test_decision_list_findings_bullet_names_claim_wording_standing_and_result(tmp_path):
    """Each claim bullet reads `<claim>: <wording> — standing <standing>; result <ref>`."""
    _, reply, store = replay("policy-violation-known", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    lines = protocol_section((review / "decision-list.md").read_text())
    findings = subsection(lines, "Findings")
    heading = [
        line for line in findings if re.search(r"Check interim-safety \(finite_policy, required\)", line)
    ]
    assert heading, "Findings must carry a `Check <id> (<kind>, required|optional)` sub-list"
    bullet = [
        line
        for line in findings
        if re.search(
            BULLET_PATTERN,
            line,
        )
    ]
    assert bullet, "the violation bullet must follow `<claim>: <wording> — standing <standing>; result <ref>`"


def test_decision_list_refused_violation_is_not_reported_as_violation(tmp_path):
    """The decision list names the refused prohibition as not applied, never as a violation."""
    data, reply, store = replay("policy-violation-proposed", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    text = "\n".join(protocol_section((review / "decision-list.md").read_text()))
    assert "declared prohibition violation(s)" not in text, "a refused violation must not read as a violation"
    assert f"{REFUSED_PREFIX}still a proposal." in text, (
        "the refused claim must read not applied with its admission"
    )


def test_decision_list_efficacy_open_items_name_missing_inputs(tmp_path):
    """The external method's missing inputs appear in the decision list's open items."""
    _, reply, store = replay("efficacy-binomial-and-external", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    open_items = "\n".join(
        subsection(protocol_section((review / "decision-list.md").read_text()), "Open items")
    )
    assert "accrual_rate" in open_items and "dropout" in open_items, (
        "the missing inputs of the not-computed method must be visible in open items"
    )


def test_decision_list_conditional_prefix_is_kept_in_open_items(tmp_path):
    """A conditional admitted repair keeps its wording prefix in the decision list."""
    _, reply, store = replay("schedule-conditional-assessment", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    text = "\n".join(protocol_section((review / "decision-list.md").read_text()))
    assert "If the declared condition applies: The nominal target" in text, (
        "the conditional prefix must survive into the decision list"
    )


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_decision_list_protocol_section_has_no_forbidden_status_words_or_json(name, tmp_path):
    """No Protocol line says safe, valid, complete, adequate or approved, and none is raw JSON."""
    _, reply, store = replay(name, tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    for line in protocol_section((review / "decision-list.md").read_text()):
        assert not forbidden_hits(line), f"forbidden status word in Protocol line: {line!r}"
        assert '{"' not in line, f"raw JSON object text in Protocol line: {line!r}"


def test_workbook_has_the_four_protocol_sheets_with_exact_headers(tmp_path):
    """The review workbook gains the four protocol sheets with the exact header rows from delivery.md."""
    _, reply, store = replay("schedule-refuted-and-conditional", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    for title, expected in PROTOCOL_SHEET_HEADERS.items():
        header, _ = sheet_rows(workbook, title)
        assert header[: len(expected)] == expected, f"`{title}` header must match delivery.md exactly"


def test_workbook_schedule_row_keeps_permitted_feasible_and_gap_apart(tmp_path):
    """The workbook schedule row keeps permitted, feasible and gap in separate cells."""
    _, reply, store = replay("schedule-refuted-and-conditional", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    _, rows = sheet_rows(workbook, "Schedule of assessments")
    assert len(rows) == 1, "one schedule check must yield exactly one workbook row"
    row = rows[0]
    assert row["Permitted window"] == "[77, 91] days from randomization", (
        "the permitted window cell must be the original window"
    )
    assert row["Feasible window"] == "[77, 80] days from randomization", (
        "the feasible window must be its own cell"
    )
    assert row["Feasible window"] != row["Permitted window"], (
        "the permitted window must never be replaced by feasible"
    )
    assert row["Full-coverage gap"] == "(80, 91] days from randomization", "the gap must be its own cell"
    assert row["Cohort"] == "not stated (open)", "a null cohort renders as `not stated (open)`"
    assert row["Conditionality"] == "unconditional", "no declared condition means unconditional"
    assert "assessment: known" in row["Standing"] and "collection: proposed" in row["Standing"], (
        "standing must render as a map of object to standing status"
    )
    assert row["Origin"].count("user_choice: ") >= 1, "origin must render as `user_choice: <ref>`"


def test_workbook_schedule_scope_mismatch_reads_not_projected_without_numbers(tmp_path):
    """A scope-mismatched schedule shows its not-projected conditionality and no feasible or gap numbers."""
    _, reply, store = replay("schedule-scope-mismatch-unresolved", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    _, rows = sheet_rows(workbook, "Schedule of assessments")
    assert rows, "the scope-mismatched schedule check must still have a row"
    row = rows[0]
    assert row["Conditionality"] == "not projected: projection_scope_mismatch", (
        "a scope mismatch is named, never projected into numbers"
    )
    assert row["Feasible window"] in {"unknown", "not computed"}, (
        "no feasible window may be shown for a mismatch"
    )
    assert row["Full-coverage gap"] in {"unknown", "not computed"}, "no gap may be shown for a mismatch"


def test_workbook_refused_prohibition_effective_outcome_is_not_the_raw_violation(tmp_path):
    """The refused prohibition row shows its effective outcome as unresolved, not as violation."""
    _, reply, store = replay("policy-violation-proposed", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    _, rows = sheet_rows(workbook, "Protocol findings")
    prohibition = [r for r in rows if r["Claim"] == "prohibition"]
    assert prohibition, "the prohibition claim must have a Protocol findings row"
    row = prohibition[0]
    assert row["Effective outcome"] != "violation", (
        "a refused raw violation must never be the effective outcome"
    )
    assert row["Effective outcome"] == "unresolved", "the refused prohibition is unresolved in the view"
    assert row["Outcome"] == "violation", "the caller's computed outcome stays visible as the raw outcome"
    assert row["Wording"].startswith(REFUSED_PREFIX), "the refused wording must read not applied"


def test_workbook_known_violation_row_carries_exact_violation_wording(tmp_path):
    """The known violation row carries the violation wording beside its result reference."""
    data, reply, store = replay("policy-violation-known", tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    _, rows = sheet_rows(workbook, "Protocol findings")
    prohibition = [r for r in rows if r["Claim"] == "prohibition"]
    assert prohibition, "the known prohibition claim must have a Protocol findings row"
    count = claim_value(data, "interim-safety", "prohibition")["violations_found"]
    assert prohibition[0]["Wording"] == VIOLATION_TEMPLATE.format(n=count), "wording must come from the view"
    assert prohibition[0]["Effective outcome"] == "violation", (
        "the known violation is its own effective outcome"
    )
    assert prohibition[0]["Result reference"], "the row must keep a canonical result reference"


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_workbook_protocol_sheets_have_no_json_cells_or_forbidden_status_words(name, tmp_path):
    """Protocol sheet cells hold clinical text or numbers, with no raw JSON or status words."""
    _, reply, store = replay(name, tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    for title, value in all_sheet_cells(workbook):
        assert not JSON_CELL.search(value), f"raw JSON in `{title}` cell: {value[:120]!r}"
        assert not forbidden_hits(value), f"forbidden status word in `{title}` cell: {value[:120]!r}"


@pytest.mark.parametrize("name", ["schedule-refuted-and-conditional", "schedule-conditional-assessment"])
def test_workbook_permitted_window_is_never_equal_to_feasible_window(name, tmp_path):
    """For schedule fixtures with a permitted interval, the permitted cell differs from the feasible cell."""
    _, reply, store = replay(name, tmp_path)
    review = export(store, reply["artifact"]["id"], tmp_path)
    workbook = load_workbook(review / "design-review.xlsx", read_only=True)
    _, rows = sheet_rows(workbook, "Schedule of assessments")
    for row in rows:
        assert row["Permitted window"] != row["Feasible window"], (
            "the permitted window must not be replaced by the feasible window"
        )
