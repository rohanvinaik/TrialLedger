"""CrossHair contracts over fixed target shapes, not a proof of every possible census record.

The four skip/history states and two pending-sample states exercise the real pure owners. File access,
subprocess deadlines and publication have separate entry-point tests and receipts.
"""

from scripts.quality_metrics import census_scope, reconcile_census


def deferred_never_counts_as_measured(skipped: bool, had_previous: bool) -> int:
    """Budget deferral never contributes a newly measured function.

    post: __return__ == (0 if skipped else 1)
    """
    row = {"file": "TrialLedger/x.py", "name": "f", "digest": "d"}
    result = reconcile_census([{**row, "skipped": skipped}], [row] if had_previous else [])
    return result["remeasured"]


def deferred_identity_is_retained(had_previous: bool) -> bool:
    """A target remains either pending or stale, never silently absent.

    post: __return__
    """
    row = {"file": "TrialLedger/x.py", "name": "f", "digest": "d"}
    result = reconcile_census([{**row, "skipped": True}], [row] if had_previous else [])
    return (
        result["records"] == [{**row, "stale": True}] and not result["pending_targets"]
        if had_previous
        else result["pending_targets"] == [row] and not result["records"]
    )


def pending_sample_keeps_current_target(pending: bool) -> bool:
    """Current selected identities survive while unrelated unselected functions stay outside the sample.

    post: __return__
    """
    row = {"file": "TrialLedger/x.py", "name": "f", "pinned": False, "mutants": 1, "digest": "now"}
    unrelated = {**row, "name": "unselected"}
    baseline = {
        "commit": "old",
        "records": [],
        "pending_targets": [{**row, "digest": "old"}] if pending else [],
    }
    return census_scope([row, unrelated], baseline, 0, 7) == ([row] if pending else [])
