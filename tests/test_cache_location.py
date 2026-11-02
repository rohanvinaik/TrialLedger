"""classes.cache_location — where a live run keeps its RxNav answers, from TRIALLEDGER_CACHE.

The release check (2026-11-01) set TRIALLEDGER_CACHE to a folder, as `resolve --help` read, and the resolve
failed with a traceback after all its lookups: the variable named only the cache file.
Positive: not set, or blank, is the user's cache; a folder that exists, or a path written with a trailing "/",
holds classes.json; anything else is the file itself, as named; through the environment, a folder and a file
both work end to end and keep the same contents.
Negative: a file path is never read as a folder (classes.json is not appended to it); a folder is never
written over as a file.
"""

import json
from pathlib import Path

import pytest

from TrialLedger import classes
from TrialLedger.classes import CACHE_NAME, USER_CACHE, cache_location, cache_path, load_or_lookup_at


@pytest.mark.parametrize(
    ("setting", "is_folder", "expected"),
    [
        (None, False, ("default", str(USER_CACHE))),
        ("", False, ("default", str(USER_CACHE))),
        ("  ", True, ("default", str(USER_CACHE))),
        ("/tmp/tl", True, ("folder", "/tmp/tl/classes.json")),
        ("/tmp/tl/", False, ("folder", "/tmp/tl/classes.json")),
        ("/tmp/tl/cache.json", False, ("file", "/tmp/tl/cache.json")),
        ("/tmp/tl/classes.json", False, ("file", "/tmp/tl/classes.json")),
        ("relative/answers", False, ("file", "relative/answers")),
    ],
)
def test_the_setting_names_the_cache_file(setting, is_folder, expected):
    assert cache_location(setting, is_folder) == expected


def test_a_file_path_is_never_read_as_a_folder():
    code, path = cache_location("/tmp/tl/cache.json", False)
    assert code == "file" and not path.endswith(CACHE_NAME)


def answering(url, params):
    return 200, {}


@pytest.mark.parametrize("as_folder", [True, False])
def test_a_folder_and_a_file_each_work_through_the_environment(tmp_path, monkeypatch, as_folder):
    folder = tmp_path / "cache"
    folder.mkdir()
    setting = folder if as_folder else folder / "answers.json"
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(setting))
    path = cache_path()
    assert path == (folder / CACHE_NAME if as_folder else folder / "answers.json")
    load_or_lookup_at(path, ["Testamab"], get=answering, sleep=lambda s: None)
    assert json.loads(path.read_text(encoding="utf-8"))["answers"]["Testamab"]["codes"]
    assert folder.is_dir()


def test_unset_is_the_users_cache(monkeypatch):
    monkeypatch.delenv("TRIALLEDGER_CACHE", raising=False)
    assert cache_path() == Path(str(classes.USER_CACHE))


def test_a_tilde_is_the_home_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TRIALLEDGER_CACHE", "~/answers.json")
    assert cache_path() == tmp_path / "answers.json"
