"""hatch_build.built_from — the commit a wheel or sdist is stamped with when it is built.

Positive: a build from a checkout that tracks the package is stamped with its head, marked when TrialLedger/
has uncommitted changes.
Negative: a build from a folder git does not track the package in (an unpacked sdist inside some other
repository, such as a home folder kept under git) is stamped nothing new, never that repository's commit; a
folder outside any repository is stamped nothing.
"""

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hatch_build(monkeypatch):
    """hatch_build.py, loaded with a stand-in for hatchling (a build-time dependency, not a test one)."""
    names = ("hatchling", "hatchling.builders", "hatchling.builders.hooks", "hatchling.builders.hooks.plugin")
    for name in names:
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")
    interface.BuildHookInterface = object
    monkeypatch.setitem(sys.modules, interface.__name__, interface)
    spec = importlib.util.spec_from_file_location("hatch_build_under_test", ROOT / "hatch_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repository, *args):
    command = ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    command += ["-c", "commit.gpgsign=false", *args]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def source(folder):
    package = folder / "TrialLedger"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    return folder


def test_a_checkout_is_stamped_with_its_head(tmp_path, hatch_build):
    root = source(tmp_path)
    git(root, "init")
    git(root, "add", ".")
    git(root, "commit", "-m", "x")
    head = git(root, "rev-parse", "HEAD")
    assert hatch_build.built_from(str(root)) == head
    (root / "TrialLedger" / "__init__.py").write_text("X = 1\n")
    assert hatch_build.built_from(str(root)) == f"{head} with uncommitted changes"


def test_an_unpacked_sdist_inside_another_repository_is_not_stamped_with_its_commit(tmp_path, hatch_build):
    (tmp_path / "notes.txt").write_text("another project\n")
    git(tmp_path, "init")
    git(tmp_path, "add", "notes.txt")
    git(tmp_path, "commit", "-m", "another project")
    unpacked = source(tmp_path / "Downloads" / "trialledger-0.1.0")
    assert hatch_build.built_from(str(unpacked)) is None


def test_a_folder_outside_any_repository_is_not_stamped(tmp_path, hatch_build, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert hatch_build.built_from(str(source(tmp_path / "unpacked"))) is None
