"""Conservative source binding for landscape derivation, separate from archival workbook warrants.

Every package Python module is included, including modules not reachable through archival workbook.py's
import graph. Registry and semantics resources are included byte for byte. Python comments/docstrings do
not change meaning and use the existing semantic_source normalization. Development conformance inventory,
hidden files, cache directories and generated cache/temporary files do not enter the runtime source root.
"""

from __future__ import annotations

from pathlib import Path

from TrialLedger.warrants import digest, merkle_root, semantic_source

VERSION = "landscape-derivation/1"
DEVELOPMENT_RESOURCES = frozenset({"semantics/conformance-inventory.json"})
CACHE_DIRECTORIES = frozenset({"__pycache__", "cache", "caches"})
GENERATED_SUFFIXES = frozenset({".pyc", ".pyo", ".log", ".tmp", ".partial", ".lock"})


def derivation_files(package: Path) -> list[Path]:
    """All package Python and retained runtime resource files, sorted by their package-relative names."""
    candidates = set(package.rglob("*.py"))
    for directory in ("registry", "semantics"):
        candidates.update((package / directory).rglob("*"))
    files = []
    for path in candidates:
        relative = path.relative_to(package)
        if not path.is_file() or relative.as_posix() in DEVELOPMENT_RESOURCES:
            continue
        if any(part.startswith(".") or part in CACHE_DIRECTORIES for part in relative.parts):
            continue
        if path.suffix in GENERATED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(package).as_posix())


def derivation_root(package: Path) -> str:
    """Bind runtime derivation files by relative path and content; never use the archival import graph."""
    leaves = [
        digest(
            "landscape-file",
            path.relative_to(package).as_posix(),
            semantic_source(path.read_text(encoding="utf-8")) if path.suffix == ".py" else path.read_bytes(),
        )
        for path in derivation_files(package)
    ]
    return digest(VERSION, merkle_root(leaves))
