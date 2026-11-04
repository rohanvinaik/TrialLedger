"""Bind reporting to its derivation dependencies, independently of the trial-design layer."""

from __future__ import annotations

from pathlib import Path

from TrialLedger.warrants import _imported_modules, digest, merkle_root, semantic_source

VERSION = "landscape-derivation/3"
LEGACY_SOURCE_PASSAGES_VERSIONS = {
    "landscape_schema": 4,
    "contract": "4.1",
    "trialledger": "0.1.0",
    "derivation_code_root": "bdbe6253f6db6c7a9798911734f519edf556af1ce1afa51c89d04e8895caa0ef",
    "display": "display-1",
    "eligibility_sections": "registry-headings-source-passages/1",
    "registry_checks": 3,
}


def retained_format(versions: object) -> str:
    """Identify the one explicitly supported old writing format, never unknown historical code."""
    if (
        isinstance(versions, dict)
        and versions.keys() == LEGACY_SOURCE_PASSAGES_VERSIONS.keys()
        and all(
            type(versions[key]) is type(value) and versions[key] == value
            for key, value in LEGACY_SOURCE_PASSAGES_VERSIONS.items()
        )
    ):
        return "legacy_source_passages_v1"
    return "current"


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
