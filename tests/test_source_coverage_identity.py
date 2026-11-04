"""Object-key order must not change retained coverage or manufacture source revisions."""

import json

from TrialLedger.layer2 import source_evidence
from TrialLedger.layer2.service import run


def test_coverage_is_invariant_under_canonical_object_key_round_trip():
    study = {
        "z/section": {},
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "statusModule": {},
            "descriptionModule": {},
            "eligibilityModule": {"minimumAge": "18 Years", "maximumAge": "N/A"},
            "armsInterventionsModule": {},
        },
        "a~section": {},
    }
    request = {
        "operation": "source_assertions",
        "study": study,
        "expected_digest": source_evidence.snapshot(study)["digest"],
        "anchors": [],
        "interpretations": [],
        "queries": [],
    }
    first = run(request)
    canonical = json.loads(json.dumps(request, sort_keys=True))
    assert run(canonical) == first
    assert first["code"] == "complete", first["problems"]
    # Every unresolved region remains present, including escaped pointer keys.
    coverage = first["result"]["coverage"]
    addresses = [row["address"] for row in coverage if row["code"] == "unresolved_retained"]
    assert addresses == sorted(
        [
            "/z~1section",
            "/a~0section",
            "/protocolSection/identificationModule",
            "/protocolSection/statusModule",
            "/protocolSection/descriptionModule",
            "/protocolSection/armsInterventionsModule",
        ]
    )
