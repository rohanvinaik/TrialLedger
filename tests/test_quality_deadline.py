"""Independent budget-boundary tests; fake clocks/runners do not establish mutation adequacy.

A census deadline is resource exhaustion, never evidence that a mutant was detected. An unfinished
function contributes no partial result; old evidence may survive only explicitly marked stale.
"""

from __future__ import annotations

import datetime
import subprocess

import pytest

from scripts import quality_metrics as qm
from tests.test_quality_pending_scope import execute, install_doubles, repository

SOURCE = "def decide(value):\n    return value > 1\n"


def target(tmp_path):
    (tmp_path / "TrialLedger").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "TrialLedger/tiny.py").write_text(SOURCE)
    (tmp_path / "tests/test_tiny.py").write_text(
        "from TrialLedger.tiny import decide\ndef test_decide():\n    assert decide(2)\n"
    )
    return qm.functions(tmp_path)[0]


def clock(monkeypatch, initial=100.0):
    value = [initial]
    monkeypatch.setattr(qm.time, "time", lambda: value[0])
    monkeypatch.setattr(qm.time, "monotonic", lambda: value[0])
    return value


def passed():
    return subprocess.CompletedProcess(["pytest"], 0, stdout="", stderr="")


@pytest.mark.parametrize("at", [101.0, 102.0])
def test_selected_suite_at_or_after_deadline_never_starts(at, tmp_path, monkeypatch):
    clock(monkeypatch, at)

    def forbidden(*args, **kwargs):
        pytest.fail("a subprocess must not start once the census deadline is reached")

    monkeypatch.setattr(qm, "pytest", forbidden)
    assert qm.census_test_run(tmp_path, ["tests/test_tiny.py"], 60.0, 101.0) == "deferred"


@pytest.mark.parametrize("mode", ["returns_after_deadline", "budget_timeout"])
def test_baseline_exhaustion_defers_without_a_failing_or_measured_record(mode, tmp_path, monkeypatch):
    item = target(tmp_path)
    now = clock(monkeypatch)
    calls = []

    def baseline(_root, _tests, timeout):
        calls.append(timeout)
        assert timeout <= 1.0
        now[0] = 101.0
        if mode == "budget_timeout":
            raise subprocess.TimeoutExpired(["pytest"], timeout)
        return passed()

    monkeypatch.setattr(qm, "pytest", baseline)
    records = qm.census((str(tmp_path), [item], 101.0))
    assert calls == [1.0]
    assert records == [{**item, "skipped": True}]
    assert (tmp_path / "TrialLedger/tiny.py").read_text() == SOURCE
    reconciled = qm.reconcile_census(records, [])
    assert reconciled["records"] == [] and reconciled["remeasured"] == 0
    assert reconciled["pending_targets"] == [item]
    assert qm.tally(reconciled["records"])["mutants"] == 0


@pytest.mark.parametrize("mode", ["returns_after_deadline", "budget_timeout"])
def test_mutant_budget_expiry_discards_earlier_outcomes_and_restores_source(mode, tmp_path, monkeypatch):
    item = target(tmp_path)
    now = clock(monkeypatch)
    seen = []

    def selected(_root, _tests, timeout):
        seen.append((now[0], timeout, (tmp_path / "TrialLedger/tiny.py").read_text()))
        if len(seen) == 1:
            now[0] += 0.1
            return passed()
        if len(seen) == 2:
            now[0] += 0.1
            return subprocess.CompletedProcess(["pytest"], 1, stdout="", stderr="")
        assert timeout <= 101.0 - now[0]
        now[0] = 101.0
        if mode == "budget_timeout":
            raise subprocess.TimeoutExpired(["pytest"], timeout)
        return passed()

    monkeypatch.setattr(qm, "pytest", selected)
    records = qm.census((str(tmp_path), [item], 101.0))
    assert len(seen) == 3 and seen[1][2] != SOURCE and seen[2][2] != SOURCE
    assert records == [{**item, "skipped": True}], "a partial caught-mutant count is not a completed census"
    assert (tmp_path / "TrialLedger/tiny.py").read_text() == SOURCE
    reconciled = qm.reconcile_census(records, [])
    aggregate = qm.tally(reconciled["records"])
    assert aggregate["mutants"] == aggregate["killed"] == aggregate["timeouts"] == 0
    assert aggregate["kill_rate"] is None


@pytest.mark.parametrize("remaining", [60.0, 60.001])
def test_budget_timeout_tied_with_or_observed_after_intrinsic_timeout_is_not_a_kill(
    remaining, tmp_path, monkeypatch
):
    now = clock(monkeypatch)
    deadline = now[0] + remaining

    def timed_out(_root, _tests, timeout):
        assert timeout == 60.0
        now[0] = deadline
        raise subprocess.TimeoutExpired(["pytest"], timeout)

    monkeypatch.setattr(qm, "pytest", timed_out)
    assert qm.census_test_run(tmp_path, ["tests/test_tiny.py"], 60.0, deadline) == "deferred"


def test_intrinsic_mutant_timeout_before_budget_expiry_can_count_separately(tmp_path, monkeypatch):
    item = target(tmp_path)
    now = clock(monkeypatch)
    calls = []

    def selected(_root, _tests, timeout):
        calls.append(timeout)
        if len(calls) == 2:
            now[0] += timeout
            raise subprocess.TimeoutExpired(["pytest"], timeout)
        now[0] += 0.1
        return passed()

    monkeypatch.setattr(qm, "pytest", selected)
    records = qm.census((str(tmp_path), [item], 10000.0))
    assert records[0]["baseline"] == "passing" and not records[0].get("skipped")
    assert [row["outcome"] for row in records[0]["outcomes"]] == ["timeout", "survived"]
    assert qm.tally(records)["timeouts"] == 1
    assert (tmp_path / "TrialLedger/tiny.py").read_text() == SOURCE


def test_all_normal_outcomes_before_deadline_remain_a_complete_measurement(tmp_path, monkeypatch):
    item = target(tmp_path)
    now = clock(monkeypatch)
    calls = []

    def selected(_root, _tests, timeout):
        calls.append(timeout)
        now[0] += 0.1
        return subprocess.CompletedProcess(["pytest"], int(len(calls) == 2), stdout="", stderr="")

    monkeypatch.setattr(qm, "pytest", selected)
    records = qm.census((str(tmp_path), [item], 110.0))
    assert [row["outcome"] for row in records[0]["outcomes"]] == ["killed", "survived"]
    assert qm.tally(records)["kill_rate"] == 50.0
    assert (tmp_path / "TrialLedger/tiny.py").read_text() == SOURCE
    assert qm.reconcile_census(records, [])["remeasured"] == 1


def test_a_deferred_function_keeps_old_evidence_stale_without_merging_new_partial_outcomes(
    tmp_path, monkeypatch
):
    item = target(tmp_path)
    now = clock(monkeypatch)
    original = {
        **item,
        "selected_by": "name",
        "test_files": ["tests/test_tiny.py"],
        "baseline": "passing",
        "outcomes": [
            {
                "line": 2,
                "kind": "compare",
                "outcome": "survived",
                "before": "value > 1",
                "after": "value >= 1",
            }
        ],
    }

    def selected(_root, _tests, timeout):
        now[0] = 101.0
        raise subprocess.TimeoutExpired(["pytest"], timeout)

    monkeypatch.setattr(qm, "pytest", selected)
    attempts = qm.census((str(tmp_path), [item], 101.0))
    result = qm.reconcile_census(attempts, [original])
    assert result["records"] == [{**original, "stale": True}]
    assert result["remeasured"] == 0 and result["pending_targets"] == []
    assert qm.tally(result["records"])["killed"] == 0
    assert (tmp_path / "TrialLedger/tiny.py").read_text() == SOURCE


def test_next_function_at_exact_deadline_does_not_start(tmp_path, monkeypatch):
    item = target(tmp_path)
    source = "def first():\n    pass\ndef second():\n    return True\n"
    (tmp_path / item["file"]).write_text(source)
    first, second = qm.functions(tmp_path)
    now = clock(monkeypatch)
    calls = []
    monkeypatch.setattr(qm, "select_tests", lambda *_: (["tests/test_tiny.py"], "name"))

    def completed_first(*args, **kwargs):
        calls.append(args)
        now[0] = 101.0
        return "passed"

    monkeypatch.setattr(qm, "census_test_run", completed_first)
    records = qm.census((str(tmp_path), [first, second], 101.0))
    assert len(calls) == 1
    assert records[0]["baseline"] == "passing"
    assert records[1] == {**second, "skipped": True}
    assert (tmp_path / item["file"]).read_text() == source


def test_zero_remeasurement_preserves_census_date_and_records_a_separate_check_date(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    scheduled, _ = install_doubles(monkeypatch, repo)
    real_date = datetime.date

    class MeasuredDate(real_date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 2)

    class CheckedDate(real_date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 5)

    monkeypatch.setattr(qm.datetime, "date", MeasuredDate)
    first = execute(tmp_path / "first")
    assert first["mutation_measured"] == "2026-11-02"
    scheduled.clear()
    monkeypatch.setattr(qm.datetime, "date", CheckedDate)
    reused = execute(tmp_path / "reused", "--incremental", str(tmp_path / "first/metrics.json"))
    assert not scheduled
    assert reused["functions_remeasured"] == 0
    assert reused["mutation_measured"] == "2026-11-02"
    assert reused["census_checked"] == "2026-11-05"
