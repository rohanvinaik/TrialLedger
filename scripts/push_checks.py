"""The pre-push gate, which git runs before every push (`.githooks/pre-push`, set up once per clone with
`.venv/bin/python scripts/push_checks.py install`), patterned on the process contract's worked example
(RSNA_Knee's scripts/push_checks.py; PROFESSIONAL_CODING_PERFORMANCE_ENGINEERING.md §9).

The founder asked (2026-10-31, paraphrased) for a proper CI gate to run before anything is pushed to GitHub,
using Detective and Wesker at his local checkouts; so the gate runs here, before anything leaves this machine
(scripts/ci_local.sh). Git hands the hook each ref being pushed, and the hook:

- runs the declared gate (scripts/ci_local.sh) unless it has already passed on exactly the tree being pushed:
  the gate stamps the tree it ran on when it passes and the tree did not change during the run. A tree the
  gate has not passed on is gated now when it is the clean checkout being pushed; any other is refused, since
  the gate checks the working tree;
- scans every line the pushed commits add, file by file, for secrets (detect-secrets), with its "Hex High
  Entropy String" detector disabled: this project's lowercase hex values (function digests, SHA-256 study
  digests, Merkle roots, the file digests of run artifacts) are fingerprints, never credentials, and that
  detector refused them and nothing else (the founder, 2026-11-01: fix the scan or remove it). Every other
  detector still runs (AWS, GitHub, private keys, keywords, Base64 entropy and the rest). Findings refuse
  unless scripts/secret_scan_reviews.json records an exact reviewed path, detector and complete added-line
  fingerprint. A changed line or another detector is not covered. A line carrying
  `# pragma: allowlist secret`, detect-secrets' own mark for a reviewed non-secret, is not a finding;
- audits the lockfile with all extras and groups (pip-audit) and names its result: no_known_flaws;
  flaws_found, each flaw printed with its package and the versions that fix it; or audit_did_not_run, with
  pip-audit's messages. The audit refuses nothing: its findings are leads, not verdicts.

A check that did not run is never a pass: the gate and the secret scan refuse the push when they fail or
cannot run.

    .venv/bin/python scripts/push_checks.py install           # once per clone: git runs .githooks/pre-push
    .venv/bin/python scripts/push_checks.py audit             # the lockfile audit alone
    .venv/bin/python scripts/push_checks.py scan <revs>     # the secret scan alone, of `git rev-list <revs>`
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 40
# Pinned, so every push is checked with the same versions.
DETECT_SECRETS = "detect-secrets@1.5.0"  # pragma: allowlist secret
PIP_AUDIT = "pip-audit@2.10.1"


class Unchecked(Exception):
    """A check that could not run, with the reason: the push is refused for it (the audit only reports it)."""


def run(
    command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """`command` run to its end with its output kept; a command that cannot start is Unchecked."""
    try:
        return subprocess.run(
            command,
            cwd=cwd or ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise Unchecked(f"{command[0]} could not be run: {error}") from error


def git(*arguments: str) -> str:
    """What `git <arguments>` prints; a git command that fails is Unchecked."""
    done = run(["git", *arguments])
    if done.returncode != 0:
        raise Unchecked(f"git {' '.join(arguments)} failed: {done.stderr.strip()}")
    return done.stdout


def ref_check(local_sha: str, local_tree: str, passed: frozenset[str], head: str, clean: bool) -> str:
    """What one pushed ref needs from the gate, as a named code: "deletion" (nothing);
    "gate_passed_on_this_tree" (nothing); "gate_runs_now" (it is the clean checkout, so the gate runs on
    it); otherwise "gate_not_run_on_this_tree", which refuses the push, since the gate checks only the
    working tree."""
    if local_sha == ZERO:
        return "deletion"
    if local_tree in passed:
        return "gate_passed_on_this_tree"
    if local_sha == head and clean:
        return "gate_runs_now"
    return "gate_not_run_on_this_tree"


def added_lines(diff: str) -> list[str]:
    """The lines a `--unified=0` diff of one file adds, without headers or the '+' prefix columns."""
    lines: list[str] = []
    columns = 0
    for line in diff.splitlines():
        if line.startswith("diff "):
            columns = 0
        elif line.startswith("@@"):
            columns = len(line) - len(line.lstrip("@")) - 1
        elif columns and line[:columns] == "+" * columns:
            lines.append(line[columns:])
    return lines


def pushed_commits(local_sha: str, remote_sha: str, remote: str) -> list[str]:
    """The commits a push of `local_sha` over `remote_sha` sends, oldest first."""
    known = run(["git", "cat-file", "-e", f"{remote_sha}^{{commit}}"])
    if remote_sha != ZERO and known.returncode == 0:
        span = [f"{remote_sha}..{local_sha}"]
    else:
        span = [local_sha, "--not", f"--remotes={remote}"]
    return git("rev-list", "--reverse", *span).split()


def commit_additions(sha: str) -> dict[str, list[str]]:
    """The lines one commit adds, by file (a merge read as its combined diff)."""
    additions: dict[str, list[str]] = {}
    for path in git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "--cc", sha).splitlines():
        diff = git("show", "--format=", "--unified=0", "--no-color", "--no-ext-diff", "--cc", sha, "--", path)
        lines = added_lines(diff)
        if lines:
            additions[path] = lines
    return additions


def secret_review_state(path: str, detector: str, digest: str, reviewed: list[tuple[str, str, str]]) -> str:
    """Only an exact reviewed file/detector/whole-line fingerprint is admitted (pure — pinned).

    post: (__return__ == 'reviewed_non_secret') == ((path, detector, digest) in reviewed)
    post: (__return__ == 'unreviewed') == ((path, detector, digest) not in reviewed)
    """
    if (path, detector, digest) in reviewed:
        return "reviewed_non_secret"
    return "unreviewed"


def secret_reviews() -> list[tuple[str, str, str]]:
    """Load narrowly reviewed findings; malformed reviews refuse rather than disable a detector."""
    path = ROOT / "scripts" / "secret_scan_reviews.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if set(data) != {"version", "reviews"} or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("unsupported review schema")
        if not isinstance(data["reviews"], list) or len(data["reviews"]) > 1024:
            raise ValueError("invalid review list")
        result = []
        for row in data["reviews"]:
            if not isinstance(row, dict) or set(row) != {"path", "detector", "added_line_sha256", "reason"}:
                raise ValueError("invalid review fields")
            if any(not isinstance(value, str) or not value for value in row.values()):
                raise ValueError("empty review field")
            digest = row["added_line_sha256"]
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("invalid review fingerprint")
            key = (row["path"], row["detector"], digest)
            if key in result:
                raise ValueError("duplicate review")
            result.append(key)
        return result
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise Unchecked(f"secret reviews could not be read: {error}") from error


def scan(commits: list[str]) -> list[str]:
    """Scan the lines the commits add for secrets, every detector but hex entropy (the project's lowercase hex
    digests are fingerprints, never credentials); refuse each finding without an exact reviewed identity."""
    if not commits:
        return []
    reviewed = secret_reviews()
    added_by_file = {}
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        written = 0
        for sha in commits:
            for path, lines in commit_additions(sha).items():
                added_by_file[sha + "/" + path] = lines
                target = base / sha / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
                written += 1
        done = run(
            [
                "uvx",
                DETECT_SECRETS,
                "scan",
                "--no-verify",
                "--disable-plugin",
                "HexHighEntropyString",
                "--all-files",
                ".",
            ],
            cwd=base,
        )
        if done.returncode != 0:
            raise Unchecked(f"detect-secrets failed: {done.stderr.strip()}")
        try:
            results = json.loads(done.stdout)["results"]
        except (ValueError, KeyError, TypeError) as error:
            raise Unchecked(f"detect-secrets' report could not be read: {error!r}") from error
        if not isinstance(results, dict):
            raise Unchecked("detect-secrets' report holds no results object")
    print(
        f"secret scan ({DETECT_SECRETS}, hex entropy disabled): the added lines of {written} files, "
        f"over {len(commits)} commit(s)"
    )
    refusals: list[str] = []
    accepted_reviews = 0
    for name, findings in sorted(results.items()):
        sha, _, path = name.removeprefix("./").partition("/")
        for finding in findings:
            lines = added_by_file.get(sha + "/" + path, [])
            number = finding["line_number"]
            if type(number) is int and 1 <= number <= len(lines):
                digest = hashlib.sha256(lines[number - 1].encode("utf-8")).hexdigest()
                if secret_review_state(path, finding["type"], digest, reviewed) == "reviewed_non_secret":
                    accepted_reviews += 1
                    continue
            refusals.append(
                f"a possible secret in {sha[:7]} {path}, "
                f"added line {finding['line_number']}: {finding['type']}"
            )
    print(f"secret scan: {len(refusals)} findings")
    print(f"secret scan: {accepted_reviews} exact reviewed non-secret findings")
    return refusals


def audit_result(report: object) -> str:
    """The lockfile audit's result as a named code: "flaws_found", "no_known_flaws" (at least one package
    audited, no flaw, every entry readable), or "audit_did_not_run" (no report, an unreadable one, or nothing
    audited): an audit that did not run is never a clean one."""
    entries = report.get("dependencies") if isinstance(report, dict) else None
    if not isinstance(entries, list):
        return "audit_did_not_run"
    audited = [e for e in entries if isinstance(e, dict) and isinstance(e.get("vulns"), list)]
    skipped = [e for e in entries if isinstance(e, dict) and "vulns" not in e and "skip_reason" in e]
    if any(entry["vulns"] for entry in audited):
        return "flaws_found"
    if audited and len(audited) + len(skipped) == len(entries):
        return "no_known_flaws"
    return "audit_did_not_run"


def audit_lines(report: object) -> list[str]:
    """What pip-audit's report says, one line each: every known flaw, with the versions that fix it, and every
    package it could not audit, with its reason."""
    entries = report.get("dependencies") if isinstance(report, dict) else None
    lines: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            lines.append(f"an entry that cannot be read: {entry!r}")
            continue
        package = f"{entry.get('name', '?')} {entry.get('version', '')}".strip()
        if "vulns" not in entry and "skip_reason" in entry:
            lines.append(f"{package}: not audited: {entry['skip_reason']}")
            continue
        for flaw in entry.get("vulns") or []:
            fixes = flaw.get("fix_versions") if isinstance(flaw, dict) else None
            fixed = (
                ", ".join(map(str, fixes)) if isinstance(fixes, list) and fixes else "no fixed version yet"
            )
            lines.append(
                f"{package}: {flaw.get('id', '?') if isinstance(flaw, dict) else flaw!r}; fixed in {fixed}"
            )
    return lines


def audit() -> str:
    """The lockfile audit with all extras and groups, as a named result, printed with pip-audit's report."""
    report: object = None
    messages = ""
    with tempfile.TemporaryDirectory() as folder:
        requirements = Path(folder) / "requirements.txt"
        written = Path(folder) / "pip-audit.json"
        try:
            exported = run(
                [
                    "uv",
                    "export",
                    "--frozen",
                    "--no-hashes",
                    "--no-emit-project",
                    "--all-extras",
                    "--all-groups",
                    "--format",
                    "requirements-txt",
                    "--output-file",
                    str(requirements),
                ]
            )
            if exported.returncode != 0:
                raise Unchecked(f"uv export failed: {exported.stderr.strip()}")
            done = run(
                [
                    "uvx",
                    PIP_AUDIT,
                    "-r",
                    str(requirements),
                    "--no-deps",
                    "--disable-pip",
                    "--format",
                    "json",
                    "--output",
                    str(written),
                ]
            )
            messages = done.stdout + done.stderr
            if written.is_file():
                report = json.loads(written.read_text(encoding="utf-8"))
        except Unchecked as error:
            messages = str(error)
        except (OSError, ValueError) as error:
            messages = f"{messages.rstrip()}\nits report could not be read: {error}"
    result = audit_result(report)
    print(f"lockfile audit ({PIP_AUDIT}, all extras and groups): {result}")
    for line in audit_lines(report):
        print(f"  {line}")
    print(messages.rstrip())
    print("lockfile audit: a lead, not a verdict; it refuses no push")
    return result


def git_path(name: str) -> Path:
    path = Path(git("rev-parse", "--git-path", name).strip())
    return path if path.is_absolute() else ROOT / path


def worktree_tree() -> str:
    """The tree the working tree would be committed as, written through a copy of the index."""
    with tempfile.TemporaryDirectory() as folder:
        index = Path(folder) / "index"
        current = git_path("index")
        if current.exists():
            index.write_bytes(current.read_bytes())
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        added = run(["git", "add", "-A", "."], env=env)
        if added.returncode != 0:
            raise Unchecked(f"git add -A (to a copy of the index) failed: {added.stderr.strip()}")
        written = run(["git", "write-tree"], env=env)
        if written.returncode != 0:
            raise Unchecked(f"git write-tree failed: {written.stderr.strip()}")
        return written.stdout.strip()


def passed_trees() -> frozenset[str]:
    folder = git_path("gate-passed")
    return frozenset(entry.name for entry in folder.iterdir()) if folder.is_dir() else frozenset()


def stamp(tree: str) -> int:
    """Stamp `tree`, read when the gate began, as passed, if the working tree is still exactly it."""
    if not tree or worktree_tree() != tree:
        print("push gate: the tree changed during the gate (or was not read), so it is not stamped")
        return 0
    folder = git_path("gate-passed")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / tree).write_text(datetime.now(UTC).isoformat(timespec="seconds") + "\n", encoding="utf-8")
    print(f"push gate: stamped tree {tree}; a push of exactly this tree will not run the gate again")
    return 0


def hook(remote: str, pushed: list[list[str]]) -> int:
    """The pre-push gate over the refs git is pushing; 1 refuses the push."""
    refusals: list[str] = []
    audited = ""
    try:
        head = git("rev-parse", "HEAD").strip()
        clean = git("status", "--porcelain") == ""
        passed = passed_trees()
        gated = False
        sending: list[str] = []
        for local_ref, local_sha, remote_ref, remote_sha in pushed:
            tree = git("rev-parse", f"{local_sha}^{{tree}}").strip() if local_sha != ZERO else ""
            code = ref_check(local_sha, tree, passed, head, clean)
            print(f"push gate: {local_ref} -> {remote_ref}: {code}")
            if code == "deletion":
                continue
            if code == "gate_runs_now" and not gated:
                gated = True
                if subprocess.run(["bash", "scripts/ci_local.sh"], cwd=ROOT, check=False).returncode:
                    refusals.append(f"the gate failed on {local_ref} ({local_sha[:7]})")
            elif code == "gate_not_run_on_this_tree":
                refusals.append(
                    f"the gate has not passed on the tree of {local_ref} ({local_sha[:7]}), "
                    "and it can check only the clean checkout being pushed: commit or stash the changes, "
                    "or check that commit out"
                )
            for sha in pushed_commits(local_sha, remote_sha, remote):
                if sha not in sending:
                    sending.append(sha)
        if sending:
            refusals.extend(scan(sending))
            audited = audit()
    except (Unchecked, OSError, ValueError, KeyError) as error:
        refusals.append(f"the push gate could not finish: {error}")
    for refusal in refusals:
        print(f"push gate: REFUSED: {refusal}")
    if audited and audited != "no_known_flaws":
        print(
            f"push gate: the lockfile audit's result is {audited}: a lead to look into, which refuses nothing"
        )
    if refusals:
        return 1
    print("push gate: PASSED")
    return 0


def install() -> int:
    """Have git run `.githooks/pre-push` before every push from this clone."""
    hook_file = ROOT / ".githooks" / "pre-push"
    if not hook_file.is_file() or not os.access(hook_file, os.X_OK):
        print(f"{hook_file} is missing or not executable")
        return 1
    git("config", "core.hooksPath", ".githooks")
    print("git now runs .githooks/pre-push before every push from this clone")
    return 0


def main(arguments: list[str]) -> int:
    command, rest = (arguments[0], arguments[1:]) if arguments else ("", [])
    try:
        if command == "hook" and rest:
            pushed = [line.split() for line in sys.stdin.read().splitlines() if line.strip()]
            return hook(rest[0], pushed)
        if command == "audit":
            return 0 if audit() == "no_known_flaws" else 1
        if command == "tree":
            print(worktree_tree())
            return 0
        if command == "stamp":
            return stamp(rest[0] if rest else "")
        if command == "install":
            return install()
        if command == "scan" and rest:
            refusals = scan(git("rev-list", "--reverse", *rest).split())
        else:
            print(__doc__)
            return 2
    except Unchecked as error:
        refusals = [str(error)]
    for refusal in refusals:
        print(f"REFUSED: {refusal}")
    return 1 if refusals else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
