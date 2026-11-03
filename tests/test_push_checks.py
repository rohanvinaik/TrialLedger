"""scripts/push_checks.py — the pre-push gate's decisions.

Positive: a deletion needs nothing; a tree the gate passed on needs nothing; the clean checkout is gated now;
a readable report with no flaw is no_known_flaws; added lines are read from a diff without headers or
prefixes; the secret scan runs detect-secrets with its hex-entropy detector disabled and every other one on.
Negative: any other pushed tree is refused; every finding of the secret scan refuses the push, and a scan that
fails or cannot be read is never a pass; a missing, unreadable or empty audit report is never a clean audit.
"""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "push_checks", Path(__file__).resolve().parents[1] / "scripts" / "push_checks.py"
)
push_checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(push_checks)

SHA = "a" * 40
TREE = "b" * 40


@pytest.mark.parametrize(
    "local_sha, tree, passed, head, clean, expected",
    [
        (push_checks.ZERO, "", frozenset(), SHA, True, "deletion"),
        (SHA, TREE, frozenset({TREE}), "c" * 40, False, "gate_passed_on_this_tree"),
        (SHA, TREE, frozenset(), SHA, True, "gate_runs_now"),
        (SHA, TREE, frozenset(), SHA, False, "gate_not_run_on_this_tree"),
        (SHA, TREE, frozenset(), "c" * 40, True, "gate_not_run_on_this_tree"),
    ],
)
def test_ref_check(local_sha, tree, passed, head, clean, expected):
    assert push_checks.ref_check(local_sha, tree, passed, head, clean) == expected


@pytest.mark.parametrize(
    "report, expected",
    [
        ({"dependencies": [{"name": "a", "version": "1", "vulns": []}]}, "no_known_flaws"),
        (
            {"dependencies": [{"name": "a", "vulns": []}, {"name": "b", "skip_reason": "not on PyPI"}]},
            "no_known_flaws",
        ),
        (
            {"dependencies": [{"name": "a", "vulns": [{"id": "PYSEC-1", "fix_versions": ["2"]}]}]},
            "flaws_found",
        ),
        ({"dependencies": []}, "audit_did_not_run"),
        ({"dependencies": [{"name": "b", "skip_reason": "not on PyPI"}]}, "audit_did_not_run"),
        ({"dependencies": [{"name": "a", "vulns": []}, "garbage"]}, "audit_did_not_run"),
        (None, "audit_did_not_run"),
        ({"no": "dependencies"}, "audit_did_not_run"),
    ],
)
def test_audit_result(report, expected):
    assert push_checks.audit_result(report) == expected


def test_added_lines_drop_headers_and_prefixes():
    diff = "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1,0 +1,2 @@\n+first\n+second\n@@ -5 +6,0 @@\n-gone\n"
    assert push_checks.added_lines(diff) == ["first", "second"]


def _fake_scan(monkeypatch, stdout, returncode=0):
    """Stand in for git and detect-secrets: one commit adding one file; every command run is recorded."""
    commands = []

    def fake_run(command, cwd=None, env=None):
        commands.append(command)
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="boom")

    monkeypatch.setattr(push_checks, "commit_additions", lambda sha: {"runs/a.json": ['"k": "v"']})
    monkeypatch.setattr(push_checks, "run", fake_run)
    return commands


def test_the_scan_disables_hex_entropy_and_refuses_every_other_finding(monkeypatch):
    """Positive: detect-secrets runs with HexHighEntropyString disabled and nothing else disabled, and each
    finding it reports refuses the push. Negative: a scan with no finding refuses nothing."""
    report = {
        "results": {
            f"./{SHA}/runs/a.json": [
                {"type": "AWS Access Key", "line_number": 3},
                {"type": "Secret Keyword", "line_number": 7},
            ]
        }
    }
    commands = _fake_scan(monkeypatch, json.dumps(report))
    refusals = push_checks.scan([SHA])
    assert commands == [
        [
            "uvx",
            push_checks.DETECT_SECRETS,
            "scan",
            "--no-verify",
            "--disable-plugin",
            "HexHighEntropyString",
            "--all-files",
            ".",
        ]
    ]
    assert refusals == [
        f"a possible secret in {SHA[:7]} runs/a.json, added line 3: AWS Access Key",
        f"a possible secret in {SHA[:7]} runs/a.json, added line 7: Secret Keyword",
    ]
    _fake_scan(monkeypatch, json.dumps({"results": {}}))
    assert push_checks.scan([SHA]) == []


@pytest.mark.parametrize(
    "stdout, returncode",
    [("", 1), ("not json", 0), (json.dumps({"no": "results"}), 0), (json.dumps({"results": []}), 0)],
)
def test_a_scan_that_did_not_run_is_never_a_pass(monkeypatch, stdout, returncode):
    _fake_scan(monkeypatch, stdout, returncode)
    with pytest.raises(push_checks.Unchecked):
        push_checks.scan([SHA])
