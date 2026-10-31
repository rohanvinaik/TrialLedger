"""Warrants: every value TrialLedger shows carries a hash that commits to the basis that produced it.

A study's digest commits to its record exactly as written (canonical JSON). A pull's root is the Merkle root
of its studies' digests, in pull order. The code root is the Merkle root of the files the workbook's
derivation reads: workbook.py, every package module it imports (followed through their own imports), the
package's __init__.py and the registry tables; so it commits to all the code and tables any rule can read,
and to nothing that cannot change a derived value (the command line, the network layer, the writer and
verifier of the folder). A value's warrant commits to its basis:
  stated   — the study digest, the value's location and the value;
  absent   — the study digest, the location and the absence state the registry's terms give it;
  computed — the rule (its id, the tool version, the code root and the digest of the functions that apply
             it) and its inputs' warrants;
  review   — the reason it needs review and its sources' warrants;
  literal  — text TrialLedger itself writes (headings, explanations), committed as such.
So every cell chains back to the registry's bytes and to the exact code that rendered it; recomputing a
warrant from studies.json under the same code either reproduces it or names the cell that does not follow.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    """The canonical JSON bytes of a value: sorted keys, no insignificant space, UTF-8."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(kind: str, *parts: str | bytes) -> str:
    """SHA-256 over a kind tag and length-prefixed parts, so different part lists never collide by joining."""
    hasher = hashlib.sha256()
    for part in (kind, *parts):
        data = part.encode("utf-8") if isinstance(part, str) else part
        hasher.update(len(data).to_bytes(8, "big"))
        hasher.update(data)
    return hasher.hexdigest()


def study_digest(study: dict[str, Any]) -> str:
    return digest("study", canonical(study))


def merkle_root(leaves: list[str]) -> str:
    """The Merkle root of digests in order: pairs hash upward; an unpaired last digest rises unchanged."""
    if not leaves:
        return digest("empty")
    level = list(leaves)
    while len(level) > 1:
        nxt = [digest("node", level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def stated(study: str, location: str, value: Any) -> str:
    return digest("stated", study, location, canonical(value))


def absent(study: str, location: str, state: str) -> str:
    return digest("absent", study, location, state)


def code_digest(*functions: Callable[..., Any]) -> str:
    """The digest of the source code of the functions that apply a rule."""
    return digest("code", *(inspect.getsource(function) for function in functions))


PACKAGE_NAME = "TrialLedger"
DERIVATION_ENTRY = "workbook.py"


def _imported_modules(module: Path, package: Path) -> set[Path]:
    """The package modules `module` imports, absolutely or relatively, wherever an import stands."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            prefix = f"{PACKAGE_NAME}."
            names.update(alias.name.split(".")[1] for alias in node.names if alias.name.startswith(prefix))
        elif isinstance(node, ast.ImportFrom):
            source = node.module or ""
            if (node.level == 0 and source == PACKAGE_NAME) or (node.level == 1 and not source):
                names.update(alias.name for alias in node.names)
            elif node.level == 0 and source.startswith(f"{PACKAGE_NAME}."):
                names.add(source.split(".")[1])
            elif node.level == 1:
                names.add(source.split(".")[0])
    return {package / f"{name}.py" for name in names if (package / f"{name}.py").is_file()}


def derivation_files(package: Path) -> list[Path]:
    """The files the workbook's derivation reads, in path order: workbook.py, every package module it imports,
    followed through their own imports, the package's __init__.py and the registry tables."""
    seen: set[Path] = set()
    queue = [package / DERIVATION_ENTRY, package / "__init__.py"]
    while queue:
        module = queue.pop()
        if module not in seen and module.is_file():
            seen.add(module)
            queue.extend(_imported_modules(module, package))
    files = seen | set(package.glob("registry/*.json"))
    return sorted(files, key=lambda path: path.relative_to(package).as_posix())


def code_root(package: Path) -> str:
    """The Merkle root of derivation_files: each leaf commits to a file's path within the package and its
    bytes. Caches, editor files and code that cannot change a derived value are not part of it."""
    leaves = [
        digest("file", path.relative_to(package).as_posix(), path.read_bytes())
        for path in derivation_files(package)
    ]
    return merkle_root(leaves)


def rule(rule_id: str, version: str, root: str, code: str, *data: str) -> str:
    """A rule's warrant: its id, the tool version, the code root, the digest of the functions that apply it
    and the digests of the data it reads."""
    return digest("rule", rule_id, version, root, code, *data)


def computed(rule_warrant: str, *inputs: str) -> str:
    return digest("computed", rule_warrant, *inputs)


def review(reason: str, *sources: str) -> str:
    return digest("review", reason, *sources)


def literal(text: str) -> str:
    return digest("literal", text)


def row(sheet: str, cells: list[str]) -> str:
    return digest("row", sheet, *cells)
