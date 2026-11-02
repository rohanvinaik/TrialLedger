"""Choose the saved baseline bodies the contract's gates read, deterministically.

The three trials named by number (ids-3) are kept whole, as saved. From the 49 osimertinib phase-3 trials the
fewest are kept that, with the three, hold every API path template the contract reads (each plain field's
paths, each reading's inputs and the universe assignment's sources), together with the two trials whose only
condition names no disease ("Progression Free Survival", "Anticancer Treatment"): greedily, the trial adding
the most templates not yet held first, the smaller body first on a tie, then the NCT number. Each study object
is written exactly as the registry sent it, in the page's order.

Run from the repository root:
    .venv/bin/python tests/fixtures/contract/select_bodies.py ~/tools/TrialLedger-runs/baseline-2026-11-01
"""

import json
import sys
from pathlib import Path

from TrialLedger import contract

HERE = Path(__file__).resolve().parent
NAMED = ("NCT02959749", "NCT02151981")


def templates() -> set[str]:
    """Every API path template the contract reads."""
    found: set[str] = set()
    for field in contract.FIELDS:
        found.update(field.source if field.kind == "plain" else field.reads)
    for _name, _words, paths in contract.ASSIGNMENT_SOURCES:
        found.update(paths)
    return found


def held(study: dict, wanted: set[str]) -> set[str]:
    """The templates a study holds a value at."""
    return {template for template in wanted if contract.resolves(study, template)}


def main(baseline: Path) -> None:
    ids_bytes = (baseline / "ids-3" / "bodies" / "studies-001.json").read_bytes()
    page = json.loads((baseline / "osimertinib-phase3-49" / "bodies" / "studies-001.json").read_bytes())
    wanted = templates()
    covered: set[str] = set()
    for study in json.loads(ids_bytes)["studies"]:
        covered |= held(study, wanted)
    pool = {study["protocolSection"]["identificationModule"]["nctId"]: study for study in page["studies"]}
    chosen = set(NAMED)
    for nct in NAMED:
        covered |= held(pool[nct], wanted)
    for _ in range(len(pool)):
        gains = sorted(
            (-len(held(study, wanted) - covered), len(json.dumps(study)), nct)
            for nct, study in pool.items()
            if nct not in chosen
        )
        if not gains or gains[0][0] == 0:
            break
        _gain, _size, nct = gains[0]
        chosen.add(nct)
        covered |= held(pool[nct], wanted)
    kept = [study for nct, study in pool.items() if nct in chosen]
    (HERE / "studies-ids-3.json").write_bytes(ids_bytes)
    subset = {"source": "osimertinib-phase3-49/bodies/studies-001.json", "studies": kept}
    (HERE / "studies-osimertinib-subset.json").write_text(json.dumps(subset, ensure_ascii=False) + "\n")
    print("kept", sorted(chosen), "unheld", sorted(wanted - covered))


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
