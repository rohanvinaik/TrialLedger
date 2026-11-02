"""The build stamp: an installed copy of TrialLedger records the commit it was built from.

A record names the commit of the code that wrote it (record.code_commit), so that `trialledger verify` can say
which commit to check a folder against. A git checkout asks git; an installed copy has no git, so this hook
writes the commit into the package as TrialLedger/build_commit.txt (record.BUILD_COMMIT_NAME) when a wheel or
an sdist is built from a checkout ("<commit> with uncommitted changes" when anything under TrialLedger/ is not
committed). The source tree is never written: the stamp is made in a temporary folder and included from
there. A wheel built from an sdist, where git cannot say, packages the stamp the sdist carries. An editable
install runs from the checkout and is stamped nothing. hatchling alone; no runtime dependency.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

STAMP = "TrialLedger/build_commit.txt"


def built_from(root: str) -> str | None:
    """The commit a build from `root` is made from, marked when the package has uncommitted changes; None
    when git cannot say (not a checkout, or no git), or when git does not track the package there: an
    unpacked sdist inside some other repository keeps the stamp it carries, never that repository's commit
    (as record.code_commit asks git only about a package it tracks)."""
    git = ["git", "-C", root]
    try:
        subprocess.run(
            [*git, "ls-files", "--error-unmatch", "TrialLedger/__init__.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        head = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        changes = subprocess.run(
            [*git, "status", "--porcelain", "--", "TrialLedger"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = head.stdout.strip()
    return f"{commit} with uncommitted changes" if changes.stdout.strip() else commit


class CommitStamp(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        self._folder: str | None = None
        if version == "editable":
            return
        commit = built_from(self.root)
        if commit is None:
            return
        self._folder = tempfile.mkdtemp(prefix="trialledger-stamp-")
        stamp = Path(self._folder) / "build_commit.txt"
        stamp.write_text(commit + "\n", encoding="utf-8")
        build_data["force_include"][str(stamp)] = STAMP

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        if self._folder is not None:
            shutil.rmtree(self._folder, ignore_errors=True)
