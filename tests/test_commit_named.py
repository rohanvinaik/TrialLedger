"""record.commit_named and the build stamp — an installed copy names the commit it was built from.

The release check (2026-11-01): a folder written by a copy installed from the repository recorded its
code_commit as "not a git checkout", so `verify` could not say which commit to check it against.
Positive: an installed copy's stamp is its commit, as stamped, whatever git would say; a clean checkout is its
head; a checkout with changed derivation code is marked; a package holding a stamp file is read through it,
never through git.
Negative: no stamp and no commit is "not a git checkout", never a guess; a blank stamp is no stamp; a copy
inside a repository that does not track it is not named by that repository's commit.
"""

import subprocess

import pytest

from TrialLedger import record as record_module
from TrialLedger.record import BUILD_COMMIT_NAME, NOT_A_CHECKOUT, code_commit, commit_named

HEAD = "a" * 40


@pytest.mark.parametrize(
    ("stamp", "head", "dirty", "expected"),
    [
        (f"{HEAD}\n", "", False, HEAD),
        (f"{HEAD} with uncommitted changes\n", "", False, f"{HEAD} with uncommitted changes"),
        (HEAD, "b" * 40, True, HEAD),
        (None, HEAD, False, HEAD),
        (None, HEAD, True, f"{HEAD} with uncommitted changes to the derivation code"),
        (None, "", False, NOT_A_CHECKOUT),
        (None, "", True, NOT_A_CHECKOUT),
        ("", "", False, NOT_A_CHECKOUT),
        (" \n", HEAD, False, HEAD),
    ],
)
def test_the_commit_a_record_names(stamp, head, dirty, expected):
    assert commit_named(stamp, head, dirty) == expected


def git(repository, *args):
    command = ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    command += ["-c", "commit.gpgsign=false", *args]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def installed(tmp_path):
    package = tmp_path / "site-packages" / "TrialLedger"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "workbook.py").write_text("X = 1\n")
    return package


def test_an_installed_copy_names_its_stamped_commit(tmp_path):
    package = installed(tmp_path)
    assert code_commit(package) == NOT_A_CHECKOUT
    (package / BUILD_COMMIT_NAME).write_text(f"{HEAD}\n", encoding="utf-8")
    assert code_commit(package) == HEAD


def test_a_stamp_wins_over_the_repository_around_it(tmp_path):
    package = installed(tmp_path)
    git(tmp_path, "init")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "x")
    (package / BUILD_COMMIT_NAME).write_text(f"{HEAD}\n", encoding="utf-8")
    assert code_commit(package) == HEAD


def test_a_copy_its_surrounding_repository_does_not_track_is_not_named_by_it(tmp_path):
    package = installed(tmp_path)
    (tmp_path / "README").write_text("another project\n")
    git(tmp_path, "init")
    git(tmp_path, "add", "README")
    git(tmp_path, "commit", "-m", "another project")
    assert code_commit(package) == NOT_A_CHECKOUT


def test_an_unreadable_stamp_is_no_stamp(tmp_path):
    package = installed(tmp_path)
    (package / BUILD_COMMIT_NAME).write_bytes(b"\xff\xfe")
    assert record_module._stamp(package) is None
    assert code_commit(package) == NOT_A_CHECKOUT
