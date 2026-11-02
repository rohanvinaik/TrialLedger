"""Compare the drug classes and axes two run folders read for the same trials (refine-landscape-record 4).

    .venv/bin/python scripts/compare_lookups.py <baseline run folder> <new run folder>

Each folder is a `trialledger landscape` run in direct mode: its saved registry bodies and its classes.json.
Both are read by the same reading (reading.read_population), so a difference is a difference in what RxNav
answered, never in the code that reads it. For every distinct experimental drug (by its own name) the script
compares what the record carries of it: its EPC class reading (state, classes, the name that resolved it) and
its axes (identity code and reason, each name's identity and role, each ATC and structure class row as the
record carries it: the name it was asked by, its standing and the concept it is asserted of; its aligned ATC
classes). Requests, retrieval times and releases
are warrants and are not compared; the releases are printed.

Each drug that differs is put in one category, the first that applies:
  dose_rule      — a name of the drug is asked without a dose or schedule (classes.lookup_name);
  rxnorm_synonym — a name of the drug that RxClass's name search did not match (the baseline holds no class
                   for it) is held by RxNorm as a concept, whose classes it now carries;
  other          — anything else, printed whole for its explanation.
Exit 0 when the folders agree on every drug, 1 when any differs (each difference printed), 2 on misuse.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from TrialLedger import classes as rx
from TrialLedger.reading import read_population
from TrialLedger.steps import records


def drugs_read(folder: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any], set[str]]:
    """Each experimental drug's reading, by its own name and the other names its entry gives it: (readings,
    the folder's answers, the releases)."""
    studies, _, _ = records(folder)
    answers = json.loads((folder / rx.CACHE_NAME).read_text(encoding="utf-8"))["answers"]
    reading = read_population(studies, answers)
    out: dict[str, dict[str, Any]] = {}
    for study, view in zip(studies, reading["views"], strict=True):
        axes = {a["drug"]: a for a in view["drug_axes"]}
        names = rx.drug_names(study)
        for drug, state, classes, resolved_by in view["drugs"]:
            held = axes[drug]
            out[" | ".join(names[drug])] = {
                "class": (state, sorted(classes), resolved_by),
                "identity": (held["identity"], held["reason"]),
                "names": sorted((i[0], i[1], i[2], tuple(i[3]), i[4]) for i in held["identities"]),
                "axes": sorted({(a[0], a[1], a[2], a[3], a[4], a[5], a[6]) for a in held["assertions"]}),
                "atc": (held["atc"][0], sorted(held["atc"][1])),
            }
    held = [answer for answer in answers.values() if isinstance(answer, dict)]
    held += [(answer.get("axes") or {}).get("identity") or {} for answer in held]
    releases = {str(answer["release"][1]) for answer in held if isinstance(answer.get("release"), list)}
    return out, answers, releases


def category(names: list[str], before: dict[str, Any], after: dict[str, Any]) -> str:
    """The category of one drug's difference (module docstring)."""
    if any(rx.lookup_name(name)[0] == "dose_stripped" for name in names):
        return "dose_rule"
    for name in names:
        old, new = before.get(name) or {}, after.get(name) or {}
        if not old.get("classes") and new.get("classes"):
            return "rxnorm_synonym"
    return "other"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    baseline, new = Path(argv[0]), Path(argv[1])
    (old, old_answers, old_releases), (fresh, new_answers, new_releases) = (
        drugs_read(baseline),
        drugs_read(new),
    )
    print(
        f"baseline {baseline}: {len(old)} distinct experimental drugs; RxNav releases {sorted(old_releases)}"
    )
    print(f"new      {new}: {len(fresh)} distinct experimental drugs; RxNav releases {sorted(new_releases)}")
    if set(old) != set(fresh):
        print(f"drugs only in the baseline: {sorted(set(old) - set(fresh))}")
        print(f"drugs only in the new run: {sorted(set(fresh) - set(old))}")
    counts: dict[str, int] = {}
    for drug in sorted(set(old) & set(fresh)):
        if old[drug] == fresh[drug]:
            counts["same"] = counts.get("same", 0) + 1
            continue
        kind = category(drug.split(" | "), old_answers, new_answers)
        counts[kind] = counts.get(kind, 0) + 1
        print(f"\n[{kind}] {drug}")
        for part in ("class", "identity", "names", "axes", "atc"):
            if old[drug][part] != fresh[drug][part]:
                print(f"  {part}:\n    baseline {old[drug][part]}\n    new      {fresh[drug][part]}")
    print("\n" + ", ".join(f"{kind} {count}" for kind, count in sorted(counts.items())))
    return 0 if set(counts) <= {"same"} and set(old) == set(fresh) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
