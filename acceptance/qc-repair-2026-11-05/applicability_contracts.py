"""Bounded source-identity gate: scope, pending work and matching evidence remain conjunctive."""

from scripts.quality_metrics import mutation_applicability


def applicability_requires_all_three(verified: bool, complete: bool, pending: bool) -> str:
    """No missing prerequisite may be replaced by the other two.

    post: (__return__ == 'applicable') == (verified and complete and not pending)
    """
    target = {"file": "TrialLedger/x.py", "name": "f", "digest": "body", "pinned": True, "mutants": 1}
    record = {**target, "baseline": "passing", "input_digest": "inputs" if verified else "other"}
    prior = {
        "mutation_commit": "old",
        "scope_complete": complete,
        "records": [record],
        "functions_not_yet_measured": 1 if pending else 0,
    }
    return mutation_applicability(prior, "inputs", [target])
