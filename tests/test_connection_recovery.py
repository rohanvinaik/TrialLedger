"""Positive: HTTP success enables direct use. Negative: blocked/throttled/error replies cannot.

These cases pin transport status only; gathering still validates source response bodies.
"""

import json
from types import SimpleNamespace

import pytest

from TrialLedger.cli import main
from TrialLedger.doctor import http_probe_status, probe, report


@pytest.mark.parametrize("status", [200, 201, 204, 299])
def test_success_is_reachable(status):
    assert http_probe_status(status) == "reachable"


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (199, "unexpected_response"),
        (300, "unexpected_response"),
        (401, "access_blocked"),
        (403, "access_blocked"),
        (404, "unexpected_response"),
        (429, "rate_limited"),
        (500, "service_unavailable"),
        (503, "service_unavailable"),
        (599, "service_unavailable"),
        (600, "unexpected_response"),
        (0, "unexpected_response"),
        (-1, "unexpected_response"),
    ],
)
def test_failures_have_distinct_recovery_and_never_mean_success(status, code):
    assert http_probe_status(status) == code
    assert (
        probe("https://test.invalid", lambda *a, **k: SimpleNamespace(status_code=status))
        == f"{code}: HTTP {status}"
    )


@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
def test_real_doctor_entry_point_does_not_select_direct_for_failed_gets(status, tmp_path, capsys):
    def get(*args, **kwargs):
        return SimpleNamespace(status_code=status)

    assert main(["doctor", "--run", str(tmp_path / "run")], probe_get=get) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "relay"
    assert all(value != "reachable" for value in result["reachable"].values())
    assert not (tmp_path / "run").exists()


def test_one_failed_service_is_enough_and_report_keeps_its_reason(tmp_path):
    def get(url, **kwargs):
        return SimpleNamespace(status_code=429 if "rxnav" in url else 200)

    result = report(tmp_path / "run", get)
    assert result["mode"] == "relay"
    assert result["reachable"]["rxnav.nlm.nih.gov"] == "rate_limited: HTTP 429"
