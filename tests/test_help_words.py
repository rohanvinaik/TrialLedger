"""The help a first-time user reads: plain words for a clinical reader (the release check, 2026-11-01).

The people reading TrialLedger's words are an AI assistant and, through it, a clinical development
professional who is not a programmer.
Positive: `trialledger --help` says what TrialLedger does and lists the user commands first, each in plain
words; the developer tools are named under "for developers" and still run; each user command's help says
what it does, gives an example and says what each exit code means; the default folder names share one form;
"30%" reads as written.
Negative: no user command's help uses an internal term ("symbolic", "digest", "warranted", "re-derive",
"Merkle", "code root") or cites a file an install does not have (spec/ctg-oas-v2.yaml); the release check's
list of words a clinical reader would not know finds none in them but "relay", the name of the mode the
guides define; no developer tool is listed among the user commands; "30%%" never appears.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

from TrialLedger.cli import DEVELOPER_COMMANDS, USER_COMMANDS, main

NAME = "scripts.release_check"
release_check = sys.modules.get(NAME)
if release_check is None:
    SPEC = importlib.util.spec_from_file_location(
        NAME, Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
    )
    release_check = importlib.util.module_from_spec(SPEC)
    sys.modules[NAME] = release_check
    SPEC.loader.exec_module(release_check)

INTERNAL = ("symbolic", "digest", "warranted", "re-derive", "merkle", "code root", "spec/ctg-oas-v2.yaml")
# "relay" is the name of the mode AGENTS.md and SKILL.md define for a sandbox that cannot reach the registry
# (`--mode relay`, doctor's "mode": "relay"); each help that names it says what it means.
NAMED_MODE = {"relay"}


def help_text(capsys, *argv):
    with pytest.raises(SystemExit) as ended:
        main([*argv, "--help"])
    assert ended.value.code == 0
    return capsys.readouterr().out


def test_the_user_commands_are_the_ones_the_guides_name():
    assert USER_COMMANDS[:4] == ("doctor", "landscape", "pull", "verify")
    assert set(DEVELOPER_COMMANDS) == {"resolve", "profile", "sample", "audit", "pilot"}
    assert not set(USER_COMMANDS) & set(DEVELOPER_COMMANDS)


def test_the_top_level_help_lists_the_user_commands_first(capsys):
    text = help_text(capsys)
    assert "ClinicalTrials.gov" in text and "no language model reads a trial" in text.lower()
    listed = re.findall(r"^    (\w+) ", text, re.MULTILINE)
    # a user command added later (mcp) joins USER_COMMANDS and is listed after these four
    assert listed[:4] == ["doctor", "landscape", "pull", "verify"]
    assert not set(listed) & set(DEVELOPER_COMMANDS)
    developers = text.lower().index("for developers")
    assert all(text.index(f"  {name} ", developers) > developers for name in DEVELOPER_COMMANDS)
    assert release_check.subcommand_names(text)[:4] == ("doctor", "landscape", "pull", "verify")
    assert set(DEVELOPER_COMMANDS) <= set(release_check.subcommand_names(text))
    assert not [word for word in INTERNAL if word in text.lower()]
    assert release_check.jargon_found(text) == ()


# Every user command, so one added to USER_COMMANDS (mcp, when it lands) is held to the same plain words.
@pytest.mark.parametrize("command", USER_COMMANDS)
def test_each_user_command_says_what_it_does_with_an_example_and_its_exit_codes(capsys, command):
    text = help_text(capsys, command)
    assert "example" in text and f"trialledger {command}" in text.split("example", 1)[1]
    exits = text.split("exit status", 1)[1]
    assert re.search(r"\b0\b", exits) and re.search(r"\b2\b", exits)
    assert not [word for word in INTERNAL if word in text.lower()]
    assert set(release_check.jargon_found(text)) <= NAMED_MODE


@pytest.mark.parametrize("command", ["doctor", "landscape"])
def test_a_help_that_names_relay_says_what_it_means(capsys, command):
    text = help_text(capsys, command)
    assert "relay" in text and "cannot reach" in text


@pytest.mark.parametrize("command", DEVELOPER_COMMANDS)
def test_each_developer_tool_still_runs(capsys, command):
    assert help_text(capsys, command).startswith(f"usage: trialledger {command}")


def test_the_default_folder_names_share_one_form(capsys):
    assert "default: ./trialledger_run" in " ".join(help_text(capsys, "doctor").split())
    assert "default: ./trialledger_<UTC time>" in " ".join(help_text(capsys, "pull").split())


def test_a_percentage_reads_as_written(capsys):
    text = help_text(capsys, "sample")
    assert "30%" in text and "30%%" not in text


def test_the_cache_setting_says_a_folder_or_a_file(capsys):
    """The review of the release check's fixes: a folder that does not exist yet counts as a folder only when
    its path ends in "/", and the help says so."""
    text = " ".join(help_text(capsys, "resolve").split())
    assert "TRIALLEDGER_CACHE" in text and "a folder (classes.json is kept inside it) or a file" in text
    assert 'already exists or the path ends in "/"' in text and "any other path is the cache file" in text


def test_the_help_promises_no_spreadsheet_landscape_does_not_write(capsys):
    """The review: landscape.xlsx is not built yet, so neither the top-level help nor landscape's line says
    landscape writes a spreadsheet, and the words a run ends with say so without the task's number."""
    from TrialLedger.operate import BOOK_WORDS

    text = " ".join(help_text(capsys).split())
    assert "a record and a spreadsheet" not in text and "is not built yet in this version" in text
    assert "spreadsheet" not in text.split("landscape ", 1)[1].split("pull ", 1)[0]
    assert "add-agent-operation" not in BOOK_WORDS["not_built"] and "4.3" not in BOOK_WORDS["not_built"]


def test_the_printed_next_steps_use_no_internal_words():
    from TrialLedger.doctor import NEXT_STEP

    assert not [mode for mode, words in NEXT_STEP.items() if "slot" in words]


def test_verify_needs_the_version_that_wrote_a_folder_under_any_python_and_a_repeated_field_ends_1(capsys):
    """A folder's code fingerprint is the same under every supported Python (warrants.canonical_tree)."""
    text = " ".join(help_text(capsys, "verify").split())
    assert "only by that version, under any Python TrialLedger supports" in text
    assert "is not certified (exit 1)" in text and "is refused" not in text


def test_landscape_exit_2_names_the_cases_a_first_time_user_meets(capsys):
    exits = " ".join(help_text(capsys, "landscape").split("exit status", 1)[1].split())
    assert "already holds another request" in exits and "no run can start" in exits
