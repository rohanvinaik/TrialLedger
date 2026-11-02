"""A TEST FIXTURE: a schema-3 landscape.json for the MCP record tool, built from the contract's worked
example.

The study extracts are `tests/fixtures/contract/examples/record.json`'s two studies (hand-checked against
the registry bodies), unchanged, and a third study made from the first by changing its NCT number, so that
part studies has a page past its first. The record-level sections are made here in the shapes the record
unit gives them (refine-landscape-record unit A, 2026-11-01): `cohort` holds each kind of across-trial
finding as a list of row objects (a kind with no rows absent) and `thresholds` as an object, and
`standard_language` the criteria a universe's trials share; each study's
`open_questions` is a list of reading value objects ({status, rule, words, result, note}, the result the
review flag); `fields` is an object keyed by contract field name. Every value here is a test value; none is
read from the registry.
"""

import copy
import json
from pathlib import Path

from TrialLedger.contract import FIELDS, SCHEMA_VERSION

EXAMPLE = Path(__file__).resolve().parent / "fixtures" / "contract" / "examples" / "record.json"
THIRD = "NCT09000009"


def question(element: str) -> dict:
    """One open question as the record holds it: a reading value object of review.flags_for."""
    return {
        "status": "unresolved",
        "rule": "review.flags_for",
        "words": [f"words about {element}"],
        "result": {
            "kind": "coverage",
            "element": element,
            "why": "the criteria say they are abbreviated",
            "priority": 2,
            "question": f"Does the trial require {element}?",
            "options": ["yes", "no", "cannot tell"],
        },
        "note": "the criteria say they are abbreviated",
    }


def schema3_record() -> dict:
    """The fixture record: three studies, the cohort's findings, open questions, fields and the manifest."""
    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    studies = example["studies"]
    third = copy.deepcopy(studies[0])
    third["nct"] = THIRD
    third["link"] = f"https://clinicaltrials.gov/study/{THIRD}"
    studies.append(third)
    studies[0]["open_questions"] = []
    studies[1]["open_questions"] = [question("prior therapy"), question("brain metastases")]
    third["open_questions"] = [question("organ function")]
    return {
        "schema_version": SCHEMA_VERSION,
        "request": {"params": {"filter.ids": f"NCT04852770,NCT01030536,{THIRD}"}},
        "scope": {"code": "resolved", "query": {"filter.ids": f"NCT04852770,NCT01030536,{THIRD}"}},
        "manifest": {
            "api_version": "2.0.5",
            "data_timestamp": "2026-10-31T09:00:00",
            "retrieval": {"mode": "direct", "matched": 3, "read": 3},
        },
        "universes": [{"name": "general", "label": "General: no domain readings apply", "version": "1"}],
        "studies": studies,
        "cohort": {
            "thresholds": {"standard_share": 0.8, "signal_min_trials": 3, "signal_min_sponsors": 2},
            "frequency": [
                {"stratum": "all trials", "element": "age", "statement_rate": "3/3"},
                {"stratum": "all trials", "element": "ecog", "statement_rate": "1/3"},
            ],
            "near_misses": [{"first": "NCT04852770", "second": THIRD, "differs_in": "ecog"}],
        },
        "standard_language": [{"criterion": "age", "role": "inclusion", "trials": 3, "of_trials": 3}],
        "statuses": {"known": "the record states it", "not_stated": "the record says nothing"},
        "envelope": {"status": "what is known of the value"},
        "fields": {field.name: {"label": field.label, "kind": field.kind} for field in FIELDS},
    }
