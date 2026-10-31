"""scripts/push_checks.py — the pre-push gate's decisions.

Positive: a deletion needs nothing; a tree the gate passed on needs nothing; the clean checkout is gated now;
an exact Detective function digest in the certificates file is recognized; a readable report with no flaw is
no_known_flaws; added lines are read from a diff without headers or prefixes.
Negative: any other pushed tree is refused; a digest elsewhere, or not in that commit's certificates, is
unexplained; a missing, unreadable or empty audit report is never a clean audit.
"""

import importlib.util
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


def test_finding_verdict():
    recognized = frozenset({"h1"})
    assert (
        push_checks.finding_verdict(push_checks.CERTIFICATES, push_checks.HEX, "h1", recognized)
        == "function_digest"
    )
    assert push_checks.finding_verdict("tests/other.json", push_checks.HEX, "h1", recognized) == "unexplained"
    assert (
        push_checks.finding_verdict(push_checks.CERTIFICATES, push_checks.HEX, "h2", recognized)
        == "unexplained"
    )
    assert (
        push_checks.finding_verdict(push_checks.CERTIFICATES, "Secret Keyword", "h1", recognized)
        == "unexplained"
    )


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
