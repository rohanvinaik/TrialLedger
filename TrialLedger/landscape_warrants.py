"""Bind reporting to its derivation dependencies, independently of the trial-design layer."""

from __future__ import annotations

from pathlib import Path

from TrialLedger.warrants import _imported_modules, digest, merkle_root, semantic_source

VERSION = "landscape-derivation/2"


def derivation_files(package: Path) -> list[Path]:
    """The record/workbook's transitive imports and registry tables, in stable path order.

    Command routing, retrieval orchestration and layer-two code cannot change a projection of retained
    inputs. They therefore do not invalidate that projection's warrant.
    """
    seen: set[Path] = set()
    queue = [package / name for name in ("landscape.py", "readout.py", "__init__.py")]
    while queue:
        module = queue.pop()
        if module.is_file() and module not in seen:
            seen.add(module)
            queue.extend(_imported_modules(module, package))
    return sorted(
        seen | set(package.glob("registry/*.json")), key=lambda path: path.relative_to(package).as_posix()
    )


def derivation_root(package: Path) -> str:
    """Bind only files that can change the source record or its workbook projection."""
    leaves = [
        digest(
            "landscape-file",
            path.relative_to(package).as_posix(),
            semantic_source(path.read_text(encoding="utf-8")) if path.suffix == ".py" else path.read_bytes(),
        )
        for path in derivation_files(package)
    ]
    return digest(VERSION, merkle_root(leaves))
