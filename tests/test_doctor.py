"""The capability check (openspec/changes/add-agent-operation task 4.1, design Decision 3).

Positive: a supported Python, every dependency and a writable run folder give `direct` when the registry and
RxNav both answer, and `relay` when either does not; the report carries the facts, the mode and the agent's
next step; a probe that gets any HTTP answer below 500 is reachable.
Negative: an old Python, a missing dependency and an unwritable folder each stop a run by name, reported in
that order whatever else holds; one unreachable host is enough for `relay`, never `direct`; a probe that
raises or gets a server error is unreachable with its reason, never raised past the check.
"""

import pytest

from TrialLedger.doctor import MODES, NEXT_STEP, PROBES, folder_writable, probe, report, run_mode


def test_a_sandbox_that_reaches_both_hosts_runs_direct():
    assert run_mode(True, [], "reachable", "reachable", True) == "direct"


@pytest.mark.parametrize(
    ("registry", "rxnav"),
    [
        ("unreachable: ConnectError", "reachable"),
        ("reachable", "unreachable: ConnectError"),
        ("unreachable: HTTP 503", "unreachable: ProxyError"),
    ],
)
def test_one_unreachable_host_is_enough_to_relay(registry, rxnav):
    assert run_mode(True, [], registry, rxnav, True) == "relay"


def test_what_stops_a_run_is_named_in_order():
    assert run_mode(False, ["httpx"], "reachable", "reachable", False) == "unsupported_python"
    assert run_mode(True, ["httpx"], "reachable", "reachable", False) == "missing_dependency"
    assert run_mode(True, [], "reachable", "reachable", False) == "folder_not_writable"
    assert run_mode(True, [], "unreachable: ConnectError", "reachable", False) == "folder_not_writable"
    assert set(NEXT_STEP) == set(MODES)


class _Answer:
    def __init__(self, status):
        self.status_code = status


def test_a_probe_reports_an_answer_or_the_reason():
    assert probe("https://x", lambda url, **kwargs: _Answer(200)) == "reachable"
    assert probe("https://x", lambda url, **kwargs: _Answer(404)) == "reachable"
    assert probe("https://x", lambda url, **kwargs: _Answer(503)) == "unreachable: HTTP 503"

    def blocked(url, **kwargs):
        raise ConnectionRefusedError("egress blocked")

    assert probe("https://x", blocked) == "unreachable: ConnectionRefusedError"


def test_the_report_carries_the_facts_the_mode_and_the_next_step(tmp_path):
    def sandbox(url, **kwargs):
        if "rxnav" in url:
            raise ConnectionRefusedError("egress blocked")
        return _Answer(200)

    found = report(tmp_path / "run", sandbox)
    assert found["mode"] == "relay" and found["next"] == NEXT_STEP["relay"]
    assert found["reachable"] == {
        "clinicaltrials.gov": "reachable",
        "rxnav.nlm.nih.gov": "unreachable: ConnectionRefusedError",
        "github.com": "reachable",
    }
    assert set(found["reachable"]) == set(PROBES)
    assert found["run_folder"] == {"path": str(tmp_path / "run"), "writable": True}
    assert found["python"]["supported"] is True and found["dependencies"]["httpx"]


def test_an_unwritable_folder_is_reported_not_raised(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert folder_writable(blocker / "run") is False
    assert folder_writable(tmp_path / "run") is True


def test_the_folder_test_leaves_nothing_behind(tmp_path):
    """The release check (2026-11-01): `doctor` created its run folder although its help said it changes
    nothing. Positive: a run folder that did not exist, with the folders above it, is created for the test and
    removed after it. Negative: a folder that existed stays, with what it holds, and nothing is added to it;
    a folder that is not writable is not created and nothing above it is removed."""
    assert folder_writable(tmp_path / "a" / "b" / "run") is True
    assert list(tmp_path.iterdir()) == []
    existing = tmp_path / "kept"
    existing.mkdir()
    (existing / "notes.txt").write_text("the person's", encoding="utf-8")
    assert folder_writable(existing) is True
    assert [p.name for p in existing.iterdir()] == ["notes.txt"]
    assert folder_writable(existing / "new") is True
    assert [p.name for p in existing.iterdir()] == ["notes.txt"]
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert folder_writable(blocker / "run") is False
    assert sorted(p.name for p in tmp_path.iterdir()) == ["file", "kept"]


def test_the_report_leaves_no_run_folder_behind(tmp_path):
    found = report(tmp_path / "run", lambda url, **kwargs: _Answer(200))
    assert found["run_folder"]["writable"] is True and found["mode"] == "direct"
    assert list(tmp_path.iterdir()) == []
