"""Plain reporting help and an accurately separate symbolic operation.

The ordinary reference-sheet commands explain their work, example and exit codes in clinical terms.
The separate reason command may explain typed symbolic premises; it must not promise a complete protocol.
Retired raw-reader commands are not part of this public interface.
"""

import re

import pytest

from scripts import release_check
from TrialLedger.cli import USER_COMMANDS, main

INTERNAL = ("digest", "re-derive", "merkle", "code root", "spec/ctg-oas-v2.yaml")
REPORTING_COMMANDS = ("doctor", "landscape", "record", "pull", "verify", "mcp")
NAMED_MODE = {"relay"}


def help_text(capsys, *argv):
    with pytest.raises(SystemExit) as ended:
        main([*argv, "--help"])
    assert ended.value.code == 0
    return capsys.readouterr().out


def test_the_public_commands_are_the_two_layer_guide_interface():
    assert (*REPORTING_COMMANDS, "reason") == USER_COMMANDS


def test_the_top_level_help_lists_actual_commands(capsys):
    text = help_text(capsys)
    assert "ClinicalTrials.gov" in text
    assert "Layer one" in text and "Layer two" in text
    assert release_check.subcommand_names(text) == USER_COMMANDS
    assert not [word for word in INTERNAL if word in text.lower()]
    assert not {"resolve", "profile", "sample", "audit", "pilot"} & set(release_check.subcommand_names(text))


@pytest.mark.parametrize("command", USER_COMMANDS)
def test_each_command_explains_use_example_and_exit_codes(capsys, command):
    text = help_text(capsys, command)
    assert "example" in text and f"trialledger {command}" in text.split("example", 1)[1]
    exits = text.split("exit status", 1)[1]
    assert re.search(r"\b0\b", exits) and re.search(r"\b2\b", exits)
    assert not [word for word in INTERNAL if word in text.lower()]
    if command != "reason":
        assert set(release_check.jargon_found(text)) <= NAMED_MODE


def test_reason_help_names_working_logic_and_incomplete_integration(capsys):
    text = " ".join(help_text(capsys, "reason").split())
    assert "premises" in text or "assertions" in text
    assert "No trial text is interpreted" in text
    assert "working symbolic logic" in text
    assert "complete trial writer is designed" in text and "unfinished" in text


@pytest.mark.parametrize("command", ["doctor", "landscape"])
def test_a_help_that_names_relay_explains_it(capsys, command):
    text = help_text(capsys, command)
    assert "relay" in text and "cannot reach" in text


def test_the_default_folder_names_share_one_form(capsys):
    assert "default: ./trialledger_run" in " ".join(help_text(capsys, "doctor").split())
    assert "default: ./trialledger_<UTC time>" in " ".join(help_text(capsys, "pull").split())


def test_landscape_writes_a_record_and_workbook(capsys):
    from TrialLedger.operate import BOOK_WORDS

    text = " ".join(help_text(capsys).split())
    assert "a record an AI assistant answers from and a spreadsheet" in text
    assert "a record and a spreadsheet" in text.split("landscape ", 1)[1].split("pull ", 1)[0]
    assert set(BOOK_WORDS) == {"written", "kept"}
    assert not [words for words in BOOK_WORDS.values() if "add-agent-operation" in words or "4.3" in words]


def test_the_printed_next_steps_use_no_internal_slot_words():
    from TrialLedger.doctor import NEXT_STEP

    assert not [mode for mode, words in NEXT_STEP.items() if "slot" in words]


def test_verify_explains_writing_version_and_uncertified_output(capsys):
    text = " ".join(help_text(capsys, "verify").split())
    assert "only by that version, under any Python TrialLedger supports" in text
    assert "is not certified (exit 1)" in text and "is refused" not in text


def test_landscape_exit_two_names_first_time_stops(capsys):
    exits = " ".join(help_text(capsys, "landscape").split("exit status", 1)[1].split())
    assert "already holds another request" in exits and "no run can start" in exits


def test_landscape_help_describes_plain_source_values(capsys):
    text = " ".join(help_text(capsys, "landscape").split())
    assert "sources defined once in the field dictionary" in text
    assert "rule readings and missing values carry their status" in text
    assert "Registry conditions and MeSH are copied as given" in text
    assert "every value with its status" not in text
