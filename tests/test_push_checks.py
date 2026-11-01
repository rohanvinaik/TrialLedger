"""scripts/push_checks.py — the pre-push gate's decisions.

Positive: a deletion needs nothing; a tree the gate passed on needs nothing; the clean checkout is gated now;
an exact Detective function digest in the certificates file is recognized, and a golden digest Detective pins
in a test file it generated; a readable report with no flaw is
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


# Two atom content digests from Detective's generated atom_digest test: test data, reviewed as no secret.
GOLDEN_VALUE = "de62bd6f4154f381"  # pragma: allowlist secret
OTHER_VALUE = "0136a6da21b97e5e"  # pragma: allowlist secret


def test_a_generated_golden_digest_is_recognized_only_where_detective_pins_it():
    """Positive: a 16-hex value on an exact `assert result == "..."` line of a Detective-generated test file
    is a golden digest, recognized for that file. Negative: the same value in a hand-written test, on any
    other line, of another length or case, or a finding of another type, stays unexplained."""
    import hashlib

    generated = "tests/detective/test_TrialLedger_semantics_contracts_atom_digest_687ff1ce81_synth.py"
    lines = [
        f'    assert result == "{GOLDEN_VALUE}"',
        f'TOKEN = "{OTHER_VALUE}"',
        f'assert result == "{GOLDEN_VALUE.upper()}"',
    ]
    hashed = hashlib.sha1(GOLDEN_VALUE.encode(), usedforsecurity=False).hexdigest()
    other = hashlib.sha1(OTHER_VALUE.encode(), usedforsecurity=False).hexdigest()
    goldens = push_checks.golden_hashes(generated, lines)
    assert goldens == frozenset({hashed})
    assert (
        push_checks.finding_verdict(generated, push_checks.HEX, hashed, frozenset(), goldens)
        == "detective_golden"
    )
    assert (
        push_checks.finding_verdict(generated, push_checks.HEX, other, frozenset(), goldens) == "unexplained"
    )
    assert (
        push_checks.finding_verdict(generated, "Secret Keyword", hashed, frozenset(), goldens)
        == "unexplained"
    )
    assert push_checks.golden_hashes("tests/test_evaluation.py", lines) == frozenset()
    assert push_checks.finding_verdict(
        "tests/test_evaluation.py", push_checks.HEX, hashed, frozenset(), goldens
    ) == ("unexplained")
    assert push_checks.golden_hashes(generated, [f'assert result == "{GOLDEN_VALUE[:-1]}"']) == frozenset()


# A study digest of Detective's landscape_manifest golden (SHA-256 of a test record): reviewed as no secret.
STUDY_DIGEST = "183f6dc518ee38946bae08096097d1c5a9e50ef95b7a5c039d0ef05d1723dab6"  # pragma: allowlist secret


def test_a_whole_expected_object_pins_its_digests_and_nothing_else():
    """Positive: in a Detective-generated file that parses, every 16- or 64-hex string constant inside a
    witness's inputs (`result = f(...)`) or its golden (`assert result == ...`) is pinned, however deeply
    nested. Negative: the same kind of value assigned to another name, compared with another name, cut
    short, in capitals, or in a hand-written file, is not; a file that does not parse falls back to the
    one-line form."""
    import hashlib

    generated = "tests/detective/test_TrialLedger_landscape_landscape_manifest_3f52b6b51f_synth.py"
    file_lines = [
        "def test_value():",
        f'    result = f(view={{"digest": "{GOLDEN_VALUE}"}})',
        f'    unrelated = f(view={{"digest": "{OTHER_VALUE}"}})',
        "    assert result == {",
        f'        "study_digests": ["{STUDY_DIGEST}"],',
        f'        "short": "{STUDY_DIGEST[:-1]}",',
        f'        "upper": "{STUDY_DIGEST.upper()}",',
        "    }",
        f'TOKEN = "{OTHER_VALUE}"',
        f'assert other == "{GOLDEN_VALUE}"',
    ]

    def hashed(value):
        return hashlib.sha1(value.encode(), usedforsecurity=False).hexdigest()

    assert push_checks.pinned_digests("\n".join(file_lines)) == {STUDY_DIGEST, GOLDEN_VALUE}
    assert push_checks.golden_hashes(generated, file_lines) == frozenset(
        {hashed(STUDY_DIGEST), hashed(GOLDEN_VALUE)}
    )
    assert push_checks.golden_hashes("tests/test_landscape.py", file_lines) == frozenset()
    assert push_checks.pinned_digests("    assert result == {") is None
