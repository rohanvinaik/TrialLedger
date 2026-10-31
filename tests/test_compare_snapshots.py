"""compare_snapshots — a pull is accepted only if the registry did not change while it ran.

Positive: the same API version and data timestamp before and after is "same".
Negative: a different data timestamp, a different API version, or both is never "same".
"""

from TrialLedger.ingest import compare_snapshots


def test_unchanged_registry_is_same():
    assert compare_snapshots(("2.0.5", "2026-10-30T09:00:04"), ("2.0.5", "2026-10-30T09:00:04")) == "same"


def test_new_data_timestamp_is_changed():
    assert compare_snapshots(("2.0.5", "2026-10-30T09:00:04"), ("2.0.5", "2026-10-31T09:00:02")) == "changed"


def test_new_api_version_is_changed():
    assert compare_snapshots(("2.0.5", "2026-10-30T09:00:04"), ("2.0.6", "2026-10-30T09:00:04")) == "changed"


def test_both_changed_is_changed():
    assert compare_snapshots(("2.0.5", "2026-10-30T09:00:04"), ("2.0.6", "2026-10-31T09:00:02")) == "changed"
