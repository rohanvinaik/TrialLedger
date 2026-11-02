"""landscape.json schema-3 records for the workbook's tests, made by the record's own assembly.

Each record is landscape.landscape_record over the contract's saved registry bodies
(tests/fixtures/contract/studies-*.json), read as a relay-mode run reads them (no RxNav answers: every drug
class "not looked up"), with the retrieval coverage operate.retrieval_coverage gives a run asking for the
trials by number. Only what a run records about itself and no body holds is labelled fixture: the API
version and the code commit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from TrialLedger import landscape, operate
from TrialLedger.reading import read_population

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
EXAMPLES = FIXTURES / "examples"
BODIES: dict[str, dict[str, Any]] = {
    study["protocolSection"]["identificationModule"]["nctId"]: study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
}
NOT_STATED = {"status": "not_stated", "note": "not_reported"}
# The trials of the mixed-group safety example (examples/safety.json), in its order, then the PTSD trial.
SAMPLE = ("NCT01030536", "NCT02151981", "NCT04852770")


def record_of(
    ncts: tuple[str, ...] = SAMPLE,
    bodies: dict[str, Any] | None = None,
    answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The schema-3 record of the given trials, in that order (module docstring); with `answers`, RxNav's
    answers in classes.json's shape, read as a direct run reads them."""
    held = bodies if bodies is not None else BODIES
    studies = [held[nct] for nct in ncts]
    ids = ",".join(ncts)
    retrieval = operate.retrieval_coverage("relay", len(ncts), {"filter.ids": ids}, studies)
    manifest = landscape.landscape_manifest(
        studies,
        "fixture (no run)",
        "2026-11-01T00:00:00",
        "fixture (no run)",
        retrieval,
        landscape.RULE_VERSIONS,
    )
    reading = read_population(studies, {})
    request, scope = {"params": {"filter.ids": ids}}, {"query": {"filter.ids": ids}}
    record = landscape.landscape_record(reading, studies, request, scope, manifest, answers)
    return json.loads(json.dumps(record, ensure_ascii=False))
