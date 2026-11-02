"""Schema-4 MCP fixture; the historical helper filename is retained for test imports.

The two worked reporting studies are copied from the contract example unchanged. A synthetic copy of the
first adds a third paging item with its own ID/link and explicitly synthetic digest. This fixture tests
transport and paging, not source certification or clinical interpretation. No analysis fields are added.
"""

import copy
import json
from pathlib import Path

from TrialLedger.contract import SCHEMA_VERSION

EXAMPLE = Path(__file__).resolve().parent / "fixtures" / "contract" / "examples" / "record.json"
THIRD = "NCT09000009"


def schema3_record() -> dict:
    """Return three reporting studies for paging; the function name is historical."""
    record = copy.deepcopy(json.loads(EXAMPLE.read_text(encoding="utf-8")))
    assert record["schema_version"] == SCHEMA_VERSION == 4
    third = copy.deepcopy(record["studies"][0])
    third.update(
        nct=THIRD, link=f"https://clinicaltrials.gov/study/{THIRD}", digest="synthetic paging fixture"
    )
    record["studies"].append(third)
    ids = ",".join(study["nct"] for study in record["studies"])
    record["request"] = {"params": {"filter.ids": ids}}
    record["scope"] = {"code": "resolved", "query": {"filter.ids": ids}}
    record["manifest"] = {
        "api_version": "fixture (no run)",
        "data_timestamp": "2026-10-31T09:00:00",
        "retrieval": {"mode": "relay", "matched": 3, "read": 3},
    }
    assert set(record) == {
        "schema_version",
        "request",
        "scope",
        "manifest",
        "statuses",
        "envelope",
        "fields",
        "studies",
    }
    return record
