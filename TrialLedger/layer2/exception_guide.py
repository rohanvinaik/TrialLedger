"""Closed exception-evidence shapes and a runnable, explicitly invented demonstration."""

from TrialLedger.layer2 import bounds_guide, source_evidence


def _shape(fields: dict) -> dict:
    return {"required": tuple(fields), "fields": fields}


INPUTS = {
    "exception_evidence": _shape(
        {
            "sources": "array of exception_source objects; complete retained snapshots, aggregate bounded",
            "observations": "array of exception_observation objects; exact source quantities and context",
            "bindings": "array of exception_binding objects; meaning is a separate supplied premise",
        }
    ),
    "exception_source": _shape(
        {
            "id": "unique nonempty source id",
            "study": "complete supplied ClinicalTrials.gov study object",
            "digest": "canonical SHA256 from source_assertions inspection snapshot",
        }
    ),
    "exception_observation": _shape(
        {
            "id": "unique observation id",
            "source": "existing exception_source id",
            "scope": "exception_scope object; exact application identities, not matching group titles",
            "count": "exception_selection of nonnegative participant integer/string; never events",
            "category": "exception_selection preserving the complete reported category",
            "denominator": "exception_selection of nonnegative population integer/string",
            "context": "nonempty exact anchors {id,address,expected}; group and period context",
        }
    ),
    "exception_selection": _shape({"address": "exact JSON pointer", "expected": "exact typed source value"}),
    "exception_scope": _shape(
        {
            "study": "canonical snapshot study_ref",
            "version": "canonical snapshot digest",
            "population": "declared population identity",
            "arm": "declared arm identity",
            "time": "declared assessment/entry identity; recording period does not establish failed target",
        }
    ),
    "exception_binding": _shape(
        {
            "id": "unique attribution id",
            "observation": "existing exception_observation id",
            "scope": "exception_scope",
            "possible_targets": (
                "nonempty unique subset of entry_eligibility, treatment_adherence, "
                "assessment_adherence, other_protocol_requirement"
            ),
            "extent": "population or profile",
            "profile": "null for population; tagged proposition for profile",
            "status": "known/interpolated/proposed; accepted reading never becomes a registry fact",
            "resolution": "resolved/partially_resolved/unresolved/conflicting",
            "basis": "nonempty warrant references",
            "rule": "{id: nonempty string, version: nonempty string}",
        }
    ),
    "exception_reference": _shape(
        {
            "bindings": "nonempty unique existing exception_binding ids",
            "scope": "exception_scope",
            "extent": "population or profile",
            "profile": "null for population; exact witness body for profile",
        }
    ),
}


def example() -> dict:
    """Invented one-person entry violation contradicts an assumed global zero-exception ceiling."""
    request = bounds_guide.example()
    study = {
        "protocolSection": {"identificationModule": {"nctId": "NCT00000001"}},
        "invented": {
            "count": 1,
            "denominator": 100,
            "category": "Protocol violation",
            "group": "example-total",
            "period": "follow-up",
        },
    }
    snapshot = source_evidence.snapshot(study)
    scope = {
        "study": snapshot["study_ref"],
        "version": snapshot["digest"],
        "population": "invented:baseline-total",
        "arm": "all",
        "time": "entry",
    }
    request["study_ref"] = snapshot["study_ref"]
    request["exception_evidence"] = {
        "sources": [{"id": "invented", "study": study, "digest": snapshot["digest"]}],
        "observations": [
            {
                "id": "reported",
                "source": "invented",
                "scope": scope.copy(),
                **{
                    key: {"address": "/invented/" + key, "expected": study["invented"][key]}
                    for key in ("count", "category", "denominator")
                },
                "context": [
                    {"id": key, "address": "/invented/" + key, "expected": study["invented"][key]}
                    for key in ("group", "period")
                ],
            }
        ],
        "bindings": [
            {
                "id": "entry-reading",
                "observation": "reported",
                "scope": scope.copy(),
                "possible_targets": ["entry_eligibility"],
                "extent": "population",
                "profile": None,
                "status": "interpolated",
                "resolution": "resolved",
                "basis": ["invented:assume-distinct-enrolled-person-with-entry-violation-discovered-late"],
                "rule": {"id": "supplied-reading-not-registry-definition", "version": "1"},
            }
        ],
    }
    request["observations"][0]["bridge"]["exception_evidence"] = {
        "bindings": ["entry-reading"],
        "scope": scope.copy(),
        "extent": "population",
        "profile": None,
    }
    return request
