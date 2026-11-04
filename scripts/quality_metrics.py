"""Reproducible quality metrics for the README badges and QUALITY.md.

Run from the repository root (coverage tools are an overlay, not a project dependency):

    uv run --with coverage --with pytest-cov python scripts/quality_metrics.py --workers 8

Every measurement runs on throwaway `git archive` copies of one commit (default HEAD); the live checkout
is never mutated. The mutation census plants simple bugs (comparison flips, and/or swaps, boolean flips,
integer +1, string-constant changes) one at a time in every pinned decision and in a seeded random sample of
the other functions, then runs the test files that name the function (falling back to files that import its
module). A mutant is killed when those tests fail or time out. Indirect kills by other test files are not
counted, and equivalent mutants are not removed, so the raw kill rate is a lower bound. Writes
quality/metrics.json, quality/survivors.md, .github/badges/*.json and QUALITY.md.
"""

from __future__ import annotations

import argparse
import ast
import copy
import datetime
import hashlib
import html
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PIN = "(pure — pinned)"
SWAP = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}


def copy_env(root: Path, **extra: str) -> dict[str, str]:
    """An environment whose every Python process, subprocesses included, imports the copy's package."""
    return {**os.environ, "PYTHONPATH": str(root), **extra}


def run(argv: list[str], cwd: Path, timeout: float | None = None, env: dict | None = None):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def archive(repo: Path, commit: str, dest: Path) -> None:
    dest.mkdir(parents=True)
    tar = subprocess.Popen(["git", "archive", commit], cwd=repo, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=tar.stdout, check=True)
    if tar.wait() != 0:
        raise SystemExit(f"git archive {commit} failed")


def check_isolated(copy_root: Path) -> None:
    """The copy's own package is what every process imports, even one started outside the copy root."""
    probe = [sys.executable, "-c", "import TrialLedger; print(TrialLedger.__file__)"]
    found = run(probe, Path(tempfile.gettempdir()), env=copy_env(copy_root))
    if not Path(found.stdout.strip()).resolve().is_relative_to(copy_root.resolve()):
        raise SystemExit(f"tests in {copy_root} would import {found.stdout.strip()}; refusing to measure")


def mutants(fn: ast.FunctionDef) -> list[tuple[int, int, int, str, str]]:
    """Single-line mutants of a function body: (line, start col, end col, replacement, kind) (pure)."""
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]
    inside_fstring: set[int] = set()
    for statement in body:
        for node in ast.walk(statement):
            if isinstance(node, ast.JoinedStr):
                inside_fstring.update(id(part) for part in ast.walk(node))
    found = []
    for statement in body:
        for node in ast.walk(statement):
            if id(node) in inside_fstring or getattr(node, "lineno", None) != getattr(node, "end_lineno", -1):
                continue
            new, kind = None, ""
            if isinstance(node, ast.Compare) and type(node.ops[0]) in SWAP:
                new, kind = copy.deepcopy(node), "compare"
                new.ops[0] = SWAP[type(node.ops[0])]()
            elif isinstance(node, ast.BoolOp):
                new, kind = copy.deepcopy(node), "boolop"
                new.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
                new, kind = ast.Constant(not node.value), "bool"
            elif isinstance(node, ast.Constant) and isinstance(node.value, int):
                new, kind = ast.Constant(node.value + 1), "int"
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
                new, kind = ast.Constant(node.value + "_x"), "str"
            if new is not None and isinstance(node, ast.expr) and node.end_col_offset is not None:
                found.append((node.lineno, node.col_offset, node.end_col_offset, ast.unparse(new), kind))
    return found


def functions(root: Path) -> list[dict]:
    out = []
    for path in sorted((root / "TrialLedger").glob("**/*.py")):
        text = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                rel = str(path.relative_to(root))
                out.append(
                    {
                        "file": rel,
                        "name": node.name,
                        "pinned": PIN in docstring,
                        "mutants": len(mutants(node)),
                        "digest": hashlib.sha256(ast.dump(node).encode()).hexdigest()[:16],
                    }
                )
    return out


_TEXTS: dict[Path, dict[str, str]] = {}


def select_tests(root: Path, file: str, name: str) -> tuple[list[str], str]:
    if root not in _TEXTS:
        paths = sorted(str(p.relative_to(root)) for p in (root / "tests").glob("**/*.py"))
        _TEXTS[root] = {t: (root / t).read_text(encoding="utf-8") for t in paths}
    texts = _TEXTS[root]
    tests = sorted(texts)
    named = [t for t in tests if re.search(rf"\b{re.escape(name)}\b", texts[t])]
    if named:
        return named, "name"
    module = file.removesuffix(".py").replace("/", ".")
    leaf = module.rsplit(".", 1)[1]
    imported = [
        t
        for t in tests
        if re.search(rf"\b{re.escape(module)}\b", texts[t])
        or re.search(rf"from {re.escape(module.rsplit('.', 1)[0])} import [^\n]*\b{leaf}\b", texts[t])
    ]
    return imported, "module" if imported else "none"


def pytest(root: Path, tests: list[str], timeout: float):
    argv = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-p", "no:randomly", *tests]
    return run(argv, root, timeout=timeout, env=copy_env(root))


def census(job: tuple[str, list[dict], float]) -> list[dict]:
    """Mutate each function in one private copy, serially; every file is restored after each mutant.

    A function not started before the deadline (epoch seconds; 0 means none) is returned marked skipped."""
    root, targets, deadline = Path(job[0]), job[1], job[2]
    results = []
    for target in targets:
        if deadline and time.time() > deadline:
            results.append({**target, "skipped": True})
            continue
        path = root / target["file"]
        original = path.read_text(encoding="utf-8")
        tree = ast.parse(original)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == target["name"])
        tests, selected_by = select_tests(root, target["file"], target["name"])
        record = {**target, "selected_by": selected_by, "test_files": tests, "outcomes": [], "baseline": ""}
        if not tests:
            record["baseline"] = "no_tests_selected"
            results.append(record)
            continue
        started = time.monotonic()
        baseline = pytest(root, tests, timeout=900)
        elapsed = time.monotonic() - started
        if baseline.returncode != 0:
            record["baseline"] = "failing"
            results.append(record)
            continue
        record["baseline"] = "passing"
        lines = original.splitlines(keepends=True)
        for lineno, start, end, replacement, kind in mutants(fn):
            line = lines[lineno - 1]
            changed = line[:start] + "(" + replacement + ")" + line[end:]
            text = "".join([*lines[: lineno - 1], changed, *lines[lineno:]])
            try:
                ast.parse(text)
            except SyntaxError:
                continue
            path.write_text(text, encoding="utf-8")
            try:
                outcome = (
                    "killed"
                    if pytest(root, tests, timeout=max(60, 5 * elapsed + 30)).returncode
                    else "survived"
                )
            except subprocess.TimeoutExpired:
                outcome = "timeout"
            finally:
                path.write_text(original, encoding="utf-8")
            record["outcomes"].append(
                {
                    "line": lineno,
                    "kind": kind,
                    "outcome": outcome,
                    "before": line.strip(),
                    "after": changed.strip(),
                }
            )
        results.append(record)
    return results


def coverage(root: Path) -> dict:
    env = copy_env(root, COVERAGE_CORE="ctrace", COVERAGE_FILE=str(root / ".coverage"))
    report = root / "coverage.json"
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--cov=TrialLedger",
        "--cov-branch",
    ]
    done = run([*argv, f"--cov-report=json:{report}"], root, env=env)
    if done.returncode != 0:
        raise SystemExit("the suite failed under coverage:\n" + done.stdout + done.stderr)
    totals = json.loads(report.read_text())["totals"]
    summary = re.search(r"(\d+) passed(?:, (\d+) deselected)?", done.stdout)
    if summary is None:
        raise SystemExit("no pytest summary line under coverage")
    return {
        "tests_passed": int(summary.group(1)),
        "tests_deselected": int(summary.group(2) or 0),
        "statements": totals["num_statements"],
        "line_coverage": round(100 * totals["covered_lines"] / totals["num_statements"], 1),
        "branches": totals["num_branches"],
        "branch_coverage": round(100 * totals["covered_branches"] / totals["num_branches"], 1),
    }


def tally(records: list[dict]) -> dict:
    outcomes = [o["outcome"] for r in records for o in r["outcomes"]]
    killed = sum(o in ("killed", "timeout") for o in outcomes)
    return {
        "functions": len(records),
        "functions_measured": sum(r["baseline"] == "passing" for r in records),
        "functions_without_selected_tests": sum(r["baseline"] == "no_tests_selected" for r in records),
        "functions_with_failing_baseline": sum(r["baseline"] == "failing" for r in records),
        "functions_selected_by_module_import": sum(r["selected_by"] == "module" for r in records),
        "mutants": len(outcomes),
        "killed": outcomes.count("killed"),
        "timeouts": outcomes.count("timeout"),
        "survived": outcomes.count("survived"),
        "kill_rate": round(100 * killed / len(outcomes), 1) if outcomes else None,
    }


def color(percent: float) -> str:
    """The shields colour for a percentage (pure)."""
    for floor, name in ((95, "brightgreen"), (90, "green"), (80, "yellowgreen"), (70, "yellow")):
        if percent >= floor:
            return name
    return "orange"


def badge(label: str, message: str, colour: str) -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": colour}


def rate(tallied: dict) -> str:
    return "not measured" if tallied["kill_rate"] is None else f"{tallied['kill_rate']}%"


def mutation_basis(metrics: dict) -> dict:
    """Describe the census basis, never treating carried results as a new measurement (pure).

    Legacy snapshots use their original commit/date. Explicit null means no census exists.
    Even a measured snapshot is a bounded census, not a fresh Detective audit.
    """
    commit = metrics.get("mutation_commit", metrics["commit"])
    stale = metrics.get("functions_stale", 0)
    pending = metrics.get("functions_not_yet_measured", 0)
    pin = metrics["mutation_pinned"]
    unavailable = pin.get("functions_without_selected_tests", 0) + pin.get(
        "functions_with_failing_baseline", 0
    )
    if commit is None or pin["kill_rate"] is None:
        status = "unmeasured"
    elif commit != metrics["commit"]:
        status = "historical"
    elif stale or pending or unavailable:
        status = "partial"
    else:
        status = "measured"
    return {
        "status": status,
        "commit": commit,
        "measured": metrics.get("mutation_measured", metrics["measured"]),
        "stale_functions": stale,
        "unmeasured_functions": pending,
        "unavailable_pinned_functions": unavailable,
    }


def mutation_message(metrics: dict) -> str:
    """Keep the census score, commit and incomplete scope together in the visible badge (pure)."""
    basis = mutation_basis(metrics)
    if basis["status"] == "unmeasured":
        return "Not measured"
    message = f"{rate(metrics['mutation_pinned'])} · {basis['commit'][:7]} · {basis['status'].capitalize()}"
    for key, label in (
        ("stale_functions", "stale"),
        ("unmeasured_functions", "unmeasured"),
        ("unavailable_pinned_functions", "without passing baseline"),
    ):
        if basis[key]:
            message += f" · {basis[key]} {label}"
    return message


METHOD = """## How it is measured

[`scripts/quality_metrics.py`](scripts/quality_metrics.py) measures one commit in throwaway `git archive`
copies; the working checkout is never modified. Reproduce from the repository root:

```bash
uv run --with coverage --with pytest-cov python scripts/quality_metrics.py --workers 8
```

- **Coverage** runs the whole suite under coverage.py with the classic tracer, counting statements and
  branches in the `TrialLedger` package.
- **Mutation score** plants one simple bug at a time inside a function body (comparison flipped, `and`/`or`
  swapped, boolean flipped, integer incremented, string constant changed), runs the test files that name
  the function (or, failing that, import its module) and counts the bug caught if a test fails or times
  out. Every pinned decision is measured; the other functions are a seeded random sample. The score is a
  lower bound: tests elsewhere that catch a bug indirectly are not run, and equivalent mutants (changes
  that cannot alter behavior) are not removed. Every survivor is listed in
  [`quality/survivors.md`](quality/survivors.md).
- **On each push** the quality workflow publishes tests and coverage before starting mutation work, then
  publishes the completed census if that run finishes. The first publication preserves the prior census's
  own commit and date; it never relabels it as a measurement of the new code. A newer push can cancel the
  slow run without withholding already-published tests. The separate Actions badge reports suite status.
  The census re-measures mutants
  only for functions whose code, or whose selected test files, changed since the last published measurement
  (or this committed baseline). A 30-minute budget bounds each run; a function not reached keeps its previous
  result, marked stale, and is re-measured on the next run. Stale results remain in the historical aggregate;
  the badge names their count and says Partial (or Historical when its commit differs from coverage).
  Unmeasured targets and pinned functions without a passing selected-test baseline also remain visible.
  Reuse checks function bodies and selected tests, not the entire transitive dependency graph; Measured
  describes that census basis, not proof of every path at the current commit. See the published
  [snapshot report](https://rohanvinaik.github.io/TrialLedger/quality.md) for its exact basis and date.
- **Detective certificates** are read from `tests/detective/certificates.json`, as recorded by Detective's
  two-sign audit; this report does not re-run that audit or certify that its recorded basis is still current.

These numbers describe how thoroughly the code is specified and tested. They are not a clinical validation
of any trial interpretation.
"""


def quality_md(m: dict) -> str:
    pin, sample, cert = m["mutation_pinned"], m["mutation_unpinned_sample"], m["detective_certificates"]
    basis = mutation_basis(m)
    deps = ", ".join(re.split(r"[<>=!~ ]", d)[0] for d in m["runtime_dependencies"])
    rows = [
        (
            "Tests",
            f"{m['tests_passed']:,} passing ({m['tests_deselected']} opt-in live-registry tests deselected)",
        ),
        ("Line coverage", f"{m['line_coverage']}% of {m['statements']:,} statements"),
        ("Branch coverage", f"{m['branch_coverage']}% of {m['branches']:,} branches"),
        (
            "Mutation score, pinned decisions",
            f"{rate(pin)} of {pin['mutants']:,} planted bugs caught, "
            f"across {pin['functions']} recorded functions "
            f'marked "pure — pinned" ({pin["killed"]:,} failed a test, {pin["timeouts"]} timed out, '
            f"{pin['survived']} survived)",
        ),
        (
            "Mutation measurement basis",
            f"{mutation_message(m)}; census date: {basis['measured'] or 'not measured'}. "
            "Scope counts include the pinned decisions and the separate sampled functions; "
            "unavailable-baseline count refers to pinned decisions only.",
        ),
        (
            "Mutation score, other functions",
            f"{rate(sample)} of {sample['mutants']:,} planted bugs caught, across a seeded random sample of "
            f"{sample['functions']} of the remaining functions; "
            f"{sample['functions_selected_by_module_import']} of them have no test that names them, so tests "
            "that catch bugs indirectly were not run and this bound is looser",
        ),
        (
            "Detective certificates",
            f"{cert['complete']} of {cert['pinned_decisions']} pinned decisions recorded complete at "
            f"`{m.get('detective_certificates_commit', m['commit'])[:7]}`; "
            "audit not rerun or freshness-validated",
        ),
        ("Runtime dependencies", f"{len(m['runtime_dependencies'])} ({deps})"),
        ("Package", f"{m['package_functions']} functions, {m['package_nonblank_lines']:,} non-blank lines"),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in rows)
    intro = (
        f"Tests and coverage measured at commit `{m['commit'][:7]}` on {m['measured']} "
        f"with Python {m['python']}.\n"
        "Mutation results have the separate basis below. This file is a retained snapshot; live README\n"
        "badges show the latest successful publication, which may lag main. They are published by the\n"
        f"[quality workflow](.github/workflows/quality.yml) and published to {PAGES}."
    )
    return f"# Quality\n\n{intro}\n\n| Measure | Value |\n|---|---|\n{table}\n\n{METHOD}"


def slim(records: list[dict]) -> list[dict]:
    """Keep planted-bug text only for survivors; a caught bug keeps its line, kind and outcome (pure)."""
    keep = ("line", "kind", "outcome")
    return [
        {
            **r,
            "outcomes": [o if o["outcome"] == "survived" else {k: o[k] for k in keep} for o in r["outcomes"]],
        }
        for r in records
    ]


def render(metrics: dict, out: Path, quality: Path | None = None) -> None:
    """Write metrics.json, survivors.md and the badge files to `out`, and QUALITY.md when asked."""
    out.mkdir(parents=True, exist_ok=True)
    metrics = {**metrics, "records": slim(metrics["records"])}
    metrics["mutation_basis"] = mutation_basis(metrics)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    survivors = [
        f"| `{r['file']}::{r['name']}` | {o['kind']} | `{o['before']}` | `{o['after']}` |"
        for r in metrics["records"]
        for o in r["outcomes"]
        if o["outcome"] == "survived"
    ]
    (out / "survivors.md").write_text(
        f"# Surviving mutants\n\nCensus basis: {mutation_message(metrics)}.\n\n"
        "Each row is a planted bug the selected tests "
        "did not catch. Some are equivalent (they cannot change behavior) and some are real gaps; none has "
        "been classified here.\n\n| Function | Kind | Original | Mutant |\n|---|---|---|---|\n"
        + "\n".join(survivors)
        + "\n",
        encoding="utf-8",
    )
    badges = out / "badges"
    badges.mkdir(exist_ok=True)
    pin = metrics["mutation_pinned"]
    basis = metrics["mutation_basis"]
    commit = metrics["commit"][:7]
    for name, data in {
        "tests": badge("Test Suite", f"{metrics['tests_passed']:,} passed · {commit}", "blue"),
        "coverage": badge(
            "Line Coverage", f"{metrics['line_coverage']}% · {commit}", color(metrics["line_coverage"])
        ),
        "branches": badge(
            "Branch Coverage", f"{metrics['branch_coverage']}% · {commit}", color(metrics["branch_coverage"])
        ),
        "mutation": badge(
            "Mutation Census (Decision Logic)",
            mutation_message(metrics),
            color(pin["kill_rate"]) if basis["status"] == "measured" else "lightgrey",
        ),
        "dependencies": badge(
            "Runtime Dependencies", str(len(metrics["runtime_dependencies"])), "brightgreen"
        ),
    }.items():
        (badges / f"{name}.json").write_text(json.dumps(data) + "\n", encoding="utf-8")
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>TrialLedger Quality</title><h1>TrialLedger Quality</h1>'
        f"<p>Tests and coverage: <code>{commit}</code>, measured {html.escape(metrics['measured'])}.</p>"
        f"<p>Mutation census: {html.escape(mutation_message(metrics))}. "
        f"Census date: {html.escape(str(basis['measured'] or 'not measured'))}.</p>"
        "<p>Latest successful publication; it may lag main. "
        '<a href="quality.md">Measurement report</a>, <a href="metrics.json">metrics.json</a>, '
        f'<a href="survivors.md">survivors.md</a>, '
        f'<a href="https://github.com/rohanvinaik/TrialLedger">repository</a>. '
        "Detective certificates are recorded statuses, not a rerun or freshness validation.</p>\n",
        encoding="utf-8",
    )
    report = quality_md(metrics)
    (out / "quality.md").write_text(report, encoding="utf-8")
    if quality is not None:
        quality.write_text(report, encoding="utf-8")


PAGES = "https://rohanvinaik.github.io/TrialLedger/"


def inventory(root: Path, everything: list[dict]) -> dict:
    """Read package size, dependencies and recorded certificates from the same archived commit."""
    pinned = {f"{f['file']}::{f['name']}" for f in everything if f["pinned"]}
    certificates = json.loads((root / "tests/detective/certificates.json").read_text())
    return {
        "package_functions": len(everything),
        "package_nonblank_lines": sum(
            1
            for p in (root / "TrialLedger").glob("**/*.py")
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ),
        "runtime_dependencies": tomllib.loads((root / "pyproject.toml").read_text())["project"][
            "dependencies"
        ],
        "detective_certificates": {
            "pinned_decisions": len(pinned),
            "complete": sum(
                key in pinned and c.get("standing") == "complete" for key, c in certificates.items()
            ),
        },
    }


def publish_coverage(repo: Path, commit: str, baseline: dict | None, out: Path, quality: Path | None):
    """Publish passing coverage without doing or redating any mutation work."""
    with tempfile.TemporaryDirectory(prefix="trialledger-coverage-") as temporary:
        root = Path(temporary).resolve() / "base"
        archive(repo, commit, root)
        check_isolated(root)
        covered = coverage(root)
        package = inventory(root, functions(root))
    prior = baseline or {}
    metrics = {
        **prior,
        **package,
        **covered,
        "commit": commit,
        "measured": datetime.date.today().isoformat(),
        "python": sys.version.split()[0],
        "mutation_commit": prior.get("mutation_commit", prior.get("commit")),
        "mutation_measured": prior.get("mutation_measured", prior.get("measured")),
        "functions_remeasured": 0,
        "functions_stale": prior.get("functions_stale", 0),
        "functions_not_yet_measured": prior.get("functions_not_yet_measured", 0),
        "mutation_pinned": prior.get("mutation_pinned", tally([])),
        "mutation_unpinned_sample": prior.get("mutation_unpinned_sample", tally([])),
        "detective_certificates_commit": commit,
        "records": prior.get("records", []),
    }
    render(metrics, out, quality)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--unpinned-sample", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument(
        "--out", type=Path, default=Path("quality"), help="where metrics and badges are written"
    )
    parser.add_argument(
        "--incremental", type=Path, help="a baseline metrics.json: re-measure only what changed"
    )
    parser.add_argument("--render", type=Path, help="render an existing metrics.json without measuring")
    parser.add_argument("--quality-md", type=Path, help="also write the QUALITY.md report here")
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="publish tests and coverage now, preserving the prior mutation census and its own basis",
    )
    parser.add_argument(
        "--budget-minutes",
        type=float,
        default=0,
        help="stop starting functions after this long; unfinished ones keep their prior result, marked stale",
    )
    parser.add_argument("--count-only", action="store_true", help="print the census size and stop")
    parser.add_argument("--limit", type=int, default=0, help="census only the first N targets (smoke test)")
    args = parser.parse_args(argv)
    if args.render:
        render(json.loads(args.render.read_text()), args.out, args.quality_md)
        return 0
    repo = Path.cwd()
    if not (repo / ".git").exists() or not (repo / "TrialLedger").is_dir():
        raise SystemExit("run from the TrialLedger repository root")
    commit = run(["git", "rev-parse", args.commit], repo).stdout.strip()
    baseline = json.loads(args.incremental.read_text()) if args.incremental else None
    if args.coverage_only:
        publish_coverage(repo, commit, baseline, args.out, args.quality_md)
        return 0
    with tempfile.TemporaryDirectory(prefix="trialledger-quality-") as temporary:
        scratch = Path(temporary).resolve()  # macOS temp paths are symlinks; tests compare resolved paths
        base = scratch / "base"
        archive(repo, commit, base)
        check_isolated(base)
        everything = functions(base)
        pinned = [f for f in everything if f["pinned"]]
        reused: list[dict] = []
        mutation_commit = baseline.get("mutation_commit", baseline["commit"]) if baseline else None
        if baseline is None or mutation_commit is None:
            others = [f for f in everything if not f["pinned"] and f["mutants"]]
            sample = random.Random(args.seed).sample(others, min(args.unpinned_sample, len(others)))
            targets = pinned + sample
        else:
            old = {(r["file"], r["name"]): r for r in baseline["records"]}
            kept = {key for key, r in old.items() if not r["pinned"]}
            targets, sample = (
                [],
                [f for f in everything if (f["file"], f["name"]) in kept and not f["pinned"]],
            )
            diff = run(["git", "diff", "--name-only", mutation_commit, commit], repo).stdout.split()
            for f in pinned + sample:
                record = old.get((f["file"], f["name"]))
                tests, _ = select_tests(base, f["file"], f["name"])
                unchanged = (
                    record is not None
                    and not record.get("stale")
                    and record.get("digest") == f["digest"]
                    and record["pinned"] == f["pinned"]
                    and record.get("test_files", tests) == tests
                    and not set(tests) & set(diff)
                )
                (reused.append(record) if unchanged else targets.append(f))
        print(
            f"{commit[:7]}: {len(everything)} functions, {len(pinned)} pinned decisions; measuring "
            f"{len(targets)} functions ({sum(f['mutants'] for f in targets)} mutants), reusing {len(reused)}",
            flush=True,
        )
        if args.count_only:
            return 0
        print("measuring coverage", flush=True)
        covered = coverage(base)
        targets = sorted(targets, key=lambda f: -f["mutants"])
        omitted = max(0, len(targets) - args.limit) if args.limit else 0
        if args.limit:
            targets = targets[-args.limit :]
        records = list(reused)
        workers = max(1, min(args.workers, len(targets)))
        deadline = time.time() + 60 * args.budget_minutes if args.budget_minutes else 0.0
        if targets:
            copies = []
            for index in range(workers):
                copies.append(scratch / f"worker-{index}")
                archive(repo, commit, copies[-1])
                check_isolated(copies[-1])
            shares = [targets[index::workers] for index in range(workers)]
            with ProcessPoolExecutor(max_workers=workers) as pool:
                jobs = zip(map(str, copies), shares, [deadline] * workers, strict=True)
                for share in pool.map(census, jobs):
                    records.extend(share)
        previous = {(r["file"], r["name"]): r for r in (baseline or {}).get("records", [])}
        stale, unmeasured = 0, omitted
        for index, record in enumerate(records):
            if record.get("skipped"):
                old = previous.get((record["file"], record["name"]))
                if old is not None:
                    records[index], stale = {**old, "stale": True}, stale + 1
                else:
                    unmeasured += 1
        records = [r for r in records if not r.get("skipped")]
        print("mutation census done", flush=True)
        package = inventory(base, everything)
    metrics = {
        "commit": commit,
        "measured": datetime.date.today().isoformat(),
        "python": sys.version.split()[0],
        "baseline_commit": mutation_commit or commit,
        "mutation_commit": commit,
        "mutation_measured": datetime.date.today().isoformat(),
        "functions_remeasured": len(targets) - stale - (unmeasured - omitted),
        "functions_stale": stale,
        "functions_not_yet_measured": unmeasured,
        **package,
        **covered,
        "mutation_pinned": tally([r for r in records if r["pinned"]]),
        "mutation_unpinned_sample": {**tally([r for r in records if not r["pinned"]]), "seed": args.seed},
        "detective_certificates_commit": commit,
        "records": sorted(records, key=lambda r: (r["file"], r["name"])),
    }
    render(metrics, args.out, args.quality_md)
    print(json.dumps({k: v for k, v in metrics.items() if k != "records"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
