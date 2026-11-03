"""Warrants — every value's hash commits to its basis.

Positive: canonical JSON ignores key order and nothing else; a digest commits to its kind and its parts, each
length-prefixed; the Merkle root pairs digests upward and carries an unpaired last one unchanged; a rule's
warrant changes with its code and with the code root; the code root commits to the workbook's derivation
code (what workbook.py imports, followed through the package) as syntax trees and the registry tables as
bytes, and is blind to caches, editor files, code the derivation does not import, and docstrings and comments;
equal bases give equal warrants.
Negative: no two different bases give the same warrant: joining parts differently, changing the kind, the
location, the value, the study, the rule or an input all change it; changing a derivation module or a
registry table, or wiring a module into the derivation, changes the code root; an empty pull still has a
root.
"""

import hashlib
from pathlib import Path

from TrialLedger import warrants


def expected_digest(kind, *parts):
    hasher = hashlib.sha256()
    for part in (kind, *parts):
        data = part.encode("utf-8") if isinstance(part, str) else part
        hasher.update(len(data).to_bytes(8, "big"))
        hasher.update(data)
    return hasher.hexdigest()


def test_canonical_json_ignores_key_order_only():
    assert warrants.canonical({"b": 1, "a": [2, "é"]}) == warrants.canonical({"a": [2, "é"], "b": 1})
    assert warrants.canonical({"a": 1}) != warrants.canonical({"a": "1"})
    assert warrants.canonical("é") == '"é"'.encode()


def test_a_digest_is_sha256_over_length_prefixed_parts():
    assert warrants.digest("stated", "abc", b"\x00") == expected_digest("stated", "abc", b"\x00")
    assert len(warrants.digest("x")) == 64


def test_joining_parts_differently_never_collides():
    assert warrants.digest("k", "ab", "c") != warrants.digest("k", "a", "bc")
    assert warrants.digest("k", "a") != warrants.digest("ka")


def test_the_merkle_root_pairs_upward():
    a, b, c = (warrants.digest("study", name) for name in ("a", "b", "c"))
    ab = expected_digest("node", a, b)
    assert warrants.merkle_root([a]) == a
    assert warrants.merkle_root([a, b]) == ab
    assert warrants.merkle_root([a, b, c]) == expected_digest("node", ab, c)
    assert warrants.merkle_root([a, b, c]) != warrants.merkle_root([b, a, c])
    assert warrants.merkle_root([]) == expected_digest("empty")


def test_a_study_digest_commits_to_the_whole_record():
    study = {"protocolSection": {"identificationModule": {"nctId": "NCT01234567"}}}
    changed = {"protocolSection": {"identificationModule": {"nctId": "NCT01234568"}}}
    assert warrants.study_digest(study) == expected_digest("study", warrants.canonical(study))
    assert warrants.study_digest(study) != warrants.study_digest(changed)


def test_each_basis_has_its_own_warrant():
    study = warrants.digest("study", "s")
    stated = warrants.stated(study, "a.b", "x")
    assert stated == expected_digest("stated", study, "a.b", warrants.canonical("x"))
    assert stated != warrants.stated(study, "a.c", "x")
    assert stated != warrants.stated(study, "a.b", "y")
    assert stated != warrants.stated(warrants.digest("study", "t"), "a.b", "x")
    assert warrants.absent(study, "a.b", "not_reported") != warrants.absent(study, "a.b", "redacted")
    rule = warrants.rule("r", "0.1.0", "root", warrants.code_digest(expected_digest))
    assert warrants.computed(rule, stated) != warrants.computed(rule, warrants.stated(study, "a.b", "y"))
    assert warrants.review("needs review", stated) != warrants.literal("needs review")
    assert warrants.row("Sheet", [stated]) != warrants.row("Other", [stated])


def test_a_rule_warrant_changes_with_its_code_root_and_data():
    first = warrants.code_digest(expected_digest)
    second = warrants.code_digest(test_canonical_json_ignores_key_order_only)
    assert first != second
    assert warrants.rule("r", "1", "root", first) != warrants.rule("r", "1", "root", second)
    assert warrants.rule("r", "1", "root", first, "a") != warrants.rule("r", "1", "root", first, "b")
    assert warrants.rule("r", "1", "root", first) != warrants.rule("r", "2", "root", first)
    assert warrants.rule("r", "1", "root", first) != warrants.rule("r", "1", "other root", first)


def package(tmp_path):
    root = tmp_path / "pkg"
    (root / "registry").mkdir(parents=True)
    (root / "__init__.py").write_text('__version__ = "0"\n')
    (root / "workbook.py").write_text(
        "from TrialLedger import checks\n"
        "from TrialLedger.ledger import get\n\n\n"
        "def f():\n"
        "    from . import links\n"
    )
    (root / "checks.py").write_text("from TrialLedger.ledger import get\nCLOSED = ('COMPLETED',)\n")
    (root / "ledger.py").write_text("def get(): ...\n")
    (root / "links.py").write_text("LINK = 'https://example.org/'\n")
    (root / "cli.py").write_text("from TrialLedger import workbook\nHELP = 'help'\n")
    (root / "registry" / "enums.json").write_text("{}")
    return root


DERIVATION = ["__init__.py", "checks.py", "ledger.py", "links.py", "registry/enums.json", "workbook.py"]


def names(root):
    return [path.relative_to(root).as_posix() for path in warrants.derivation_files(root)]


def test_the_code_root_commits_to_the_derivation_code_and_tables(tmp_path):
    root = package(tmp_path)
    assert names(root) == DERIVATION
    leaves = [
        expected_digest(
            "file",
            name,
            warrants.semantic_source((root / name).read_text())
            if name.endswith(".py")
            else (root / name).read_bytes(),
        )
        for name in DERIVATION
    ]
    assert warrants.code_root(root) == warrants.merkle_root(leaves)


def test_a_docstring_or_comment_edit_leaves_the_root_unchanged(tmp_path):
    root = package(tmp_path)
    first = warrants.code_root(root)
    (root / "ledger.py").write_text('"""The ledger."""\n\n\ndef get():  # read a value\n    ...\n')
    assert warrants.code_root(root) == first
    (root / "registry" / "enums.json").write_text("{ }")  # a table is committed byte for byte
    assert warrants.code_root(root) != first


def test_code_that_cannot_change_a_derived_value_is_not_in_the_root(tmp_path):
    root = package(tmp_path)
    first = warrants.code_root(root)
    (root / "cli.py").write_text("from TrialLedger import workbook\nHELP = 'other help'\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "checks.cpython-314.pyc").write_bytes(b"compiled")
    (root / ".DS_Store").write_bytes(b"finder")
    (root / "notes.txt").write_text("not code")
    assert warrants.code_root(root) == first


def test_any_change_to_the_derivation_code_or_tables_changes_the_root(tmp_path):
    root = package(tmp_path)
    first = warrants.code_root(root)
    for name, changed in (
        ("checks.py", "from TrialLedger.ledger import get\nCLOSED = ()\n"),
        ("ledger.py", "def get(): return 1\n"),
        ("links.py", "LINK = 'https://example.org/other'\n"),
        ("registry/enums.json", '{"a": 1}'),
        ("__init__.py", '__version__ = "1"\n'),
    ):
        before = (root / name).read_text()
        (root / name).write_text(changed)
        assert warrants.code_root(root) != first, name
        (root / name).write_text(before)
    assert warrants.code_root(root) == first
    (root / "checks.py").write_text("import TrialLedger.cli\nfrom TrialLedger.ledger import get\n")
    assert "cli.py" in names(root)  # a module wired into the derivation joins the root


def test_the_real_derivation_is_the_workbook_and_what_it_imports():
    package_dir = Path(warrants.__file__).parent
    assert names(package_dir) == [
        "__init__.py",
        "cells.py",
        "checks.py",
        "date_possibilities.py",
        "eligibility.py",
        "ledger.py",
        "links.py",
        "registry.py",
        "registry/ctg-enums.json",
        "registry/ctg-metadata.json",
        "warrants.py",
        "workbook.py",
    ]
