"""classify_version — a /version body can stamp provenance only if it names both versions.

Positive: apiVersion and dataTimestamp as non-empty strings are "ok".
Negative: a body that is not an object, or lacks either value, or carries one that is empty or not a string,
is never "ok" — a pull that cannot say which registry snapshot it holds is refused.
"""

from TrialLedger.ingest import classify_version


def test_both_versions_present_is_ok():
    assert classify_version({"apiVersion": "2.0.5", "dataTimestamp": "2026-10-30T09:00:04"}) == "ok"


def test_list_body_is_not_an_object():
    assert classify_version([{"apiVersion": "2.0.5"}]) == "not_an_object"


def test_null_body_is_not_an_object():
    assert classify_version(None) == "not_an_object"


def test_string_body_is_not_an_object():
    assert classify_version("2.0.5") == "not_an_object"


def test_missing_api_version():
    assert classify_version({"dataTimestamp": "2026-10-30T09:00:04"}) == "no_api_version"


def test_empty_api_version():
    assert classify_version({"apiVersion": "", "dataTimestamp": "2026-10-30T09:00:04"}) == ("no_api_version")


def test_numeric_api_version():
    assert classify_version({"apiVersion": 2, "dataTimestamp": "2026-10-30T09:00:04"}) == ("no_api_version")


def test_missing_data_timestamp():
    assert classify_version({"apiVersion": "2.0.5"}) == "no_data_timestamp"


def test_empty_data_timestamp():
    assert classify_version({"apiVersion": "2.0.5", "dataTimestamp": ""}) == "no_data_timestamp"


def test_null_data_timestamp():
    assert classify_version({"apiVersion": "2.0.5", "dataTimestamp": None}) == "no_data_timestamp"


def test_numeric_data_timestamp():
    assert classify_version({"apiVersion": "2.0.5", "dataTimestamp": 20261030}) == ("no_data_timestamp")


def test_list_data_timestamp():
    assert classify_version({"apiVersion": "2.0.5", "dataTimestamp": ["2026-10-30"]}) == ("no_data_timestamp")
