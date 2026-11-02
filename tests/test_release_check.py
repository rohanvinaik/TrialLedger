"""scripts/release_check.py — the release check's decisions (the steps themselves run live, by hand).

Positive: a checkout is installed from its path, a pip-ready address as given, a repository's https address
as "git+<address>", an archive as given; a pip address is cloned without its "git+" and fragment, at the
revision after its path's last "@"; captured output reads as text whether it came as text or as bytes; the
usage line lists every subcommand in its order, and the real `trialledger --help` lists the four a first-time
user runs; a traceback and a warning are each found with their line; a step that ends as expected is
as_expected, or warned when it printed a warning; every tracked package file installed leaves nothing
missing; every expected output there leaves nothing missing; a sheet with widths, a filter and frozen panes,
and a read-me with widths, depart from nothing; a written or resized file is listed with its size, a new
folder as a folder; a pull whose accounting (made by the pull's own reconcile_ids) has every number and
prints its alias is accounted; every command the guide names is available; a help text's jargon is found
whole, in JARGON's order; every step passing and every check run without a problem is ready.
Negative: a bare name is not a source; an "@" in the host part names no revision; nothing captured is no
text; a text with no brace group lists no subcommand; an ordinary line is no finding; a step with no exit code
timed out, one with another code is an unexpected exit, and a traceback outranks a warning; a tracked file the
install lacks is missing, an installed file nothing tracks is not; an expected output not there is missing,
an unexpected one is no gap; a listing without widths, filter or frozen panes departs on each, a read-me only
on widths; an unchanged file or a folder already there is not written; a number the record does not hold, an
alias the pull did not print, and no alias where one was expected are each named; a command the CLI lacks is
named once; a word inside a longer word is not jargon; no step, a failing step, a check with a problem or a
check that did not run is not ready.
"""

import pytest

from scripts import release_check
from TrialLedger.cli import main
from TrialLedger.ingest import reconcile_ids


def help_text(capsys, *argv):
    """What the real CLI prints for `trialledger <argv> --help`."""
    with pytest.raises(SystemExit):
        main([*argv, "--help"])
    return capsys.readouterr().out


def study(nct_id, aliases=()):
    identification = {"nctId": nct_id}
    if aliases:
        identification["nctIdAliases"] = list(aliases)
    return {"protocolSection": {"identificationModule": identification}}


# The three studies the live pull returns, as the registry answers PULL_IDS: the alias number answered by the
# study that lists it (NCT01030536, as tests/test_requested_ids.py records).
PULLED = [study("NCT04852770"), study("NCT01827384"), study("NCT01030536", ["NCT01086644"])]
ALIAS_LINE = (
    "trialledger: NCT01086644 is another number of NCT01030536: the registry gave that trial's record\n"
)
# What the pull printed before 2026-11-01: the status's code, which a clinical reader does not know.
OLD_ALIAS_LINE = "trialledger: requested NCT01086644: aliased, answered by NCT01030536\n"


@pytest.mark.parametrize(
    "source, is_dir, expected",
    [
        ("/src/TrialLedger", True, ("path", "/src/TrialLedger")),
        ("git+https://github.com/o/TrialLedger", False, ("vcs_url", "git+https://github.com/o/TrialLedger")),
        (
            "https://github.com/o/TrialLedger",
            False,
            ("repository_url", "git+https://github.com/o/TrialLedger"),
        ),
        (
            "https://x.org/TrialLedger-0.1.0.tar.gz",
            False,
            ("archive_url", "https://x.org/TrialLedger-0.1.0.tar.gz"),
        ),
        ("https://x.org/t.whl", False, ("archive_url", "https://x.org/t.whl")),
        ("TrialLedger", False, ("not_a_source", "")),
        ("http://github.com/o/TrialLedger", False, ("not_a_source", "")),
    ],
)
def test_install_spec(source, is_dir, expected):
    assert release_check.install_spec(source, is_dir) == expected


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("git+https://github.com/o/TrialLedger", ("https://github.com/o/TrialLedger", "")),
        ("git+https://github.com/o/TrialLedger@v0.1", ("https://github.com/o/TrialLedger", "v0.1")),
        (
            "git+https://github.com/o/TrialLedger@refs/pull/1/head#egg=TrialLedger",
            ("https://github.com/o/TrialLedger", "refs/pull/1/head"),
        ),
        ("git+ssh://git@github.com/o/TrialLedger", ("ssh://git@github.com/o/TrialLedger", "")),
        ("git+ssh://git@github.com/o/TrialLedger@main", ("ssh://git@github.com/o/TrialLedger", "main")),
        ("git+file:///src/TrialLedger", ("file:///src/TrialLedger", "")),
        ("https://github.com/o/TrialLedger#subdirectory=x", ("https://github.com/o/TrialLedger", "")),
    ],
)
def test_clone_source(spec, expected):
    assert release_check.clone_source(spec) == expected


def test_captured_text():
    assert release_check.captured_text("partial\n") == "partial\n"
    assert release_check.captured_text(b"partial\n") == "partial\n"
    assert release_check.captured_text("é".encode()) == "é"
    assert release_check.captured_text(b"a\xffb") == "a\ufffdb"
    assert release_check.captured_text(None) == ""


def test_captured_text_of_no_bytes_is_text():
    assert release_check.captured_text(b"") == ""


# The current two-layer public command surface, including a wrapped argparse usage line.
USAGE = """usage: trialledger [-h]
                   {doctor,landscape,pull,verify,mcp,reason} ...

positional arguments:
  {doctor,landscape,pull,verify,mcp,reason}
    doctor              check what this sandbox can do before a run
"""


def test_subcommand_names_reads_the_usage_line():
    names = release_check.subcommand_names(USAGE)
    assert names == ("doctor", "landscape", "pull", "verify", "mcp", "reason")
    assert release_check.subcommand_names("usage: x {a-b,c2} y {d}") == ("a-b", "c2")


def test_subcommand_names_reads_the_real_help(capsys):
    names = release_check.subcommand_names(help_text(capsys))
    assert {"doctor", "pull", "verify", "reason", "landscape", "mcp"} <= set(names)


def test_subcommand_names_of_a_text_with_none():
    assert release_check.subcommand_names("usage: trialledger verify [-h] folder") == ()
    assert release_check.subcommand_names("") == ()


def test_output_findings():
    text = (
        "studies written\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1\n'
        "/x/openpyxl/reader.py:3: UserWarning: Data Validation extension is not supported\n"
        "WARNING: pip is out of date\n"
    )
    assert release_check.output_findings(text) == (
        ("traceback", "Traceback (most recent call last):"),
        ("warning", "/x/openpyxl/reader.py:3: UserWarning: Data Validation extension is not supported"),
        ("warning", "WARNING: pip is out of date"),
    )
    assert release_check.output_findings("3 studies written to pulled/ (certified)\n") == ()


@pytest.mark.parametrize(
    "expected, actual, kinds, verdict",
    [
        (0, 0, (), "as_expected"),
        (0, 0, ("warning",), "warned"),
        (0, 0, ("warning", "traceback"), "traceback"),
        (0, 1, (), "unexpected_exit"),
        (2, 0, (), "unexpected_exit"),
        (0, None, ("traceback",), "timed_out"),
    ],
)
def test_step_verdict(expected, actual, kinds, verdict):
    assert release_check.step_verdict(expected, actual, kinds) == verdict


def test_missing_package_files():
    tracked = (
        "TrialLedger/cli.py",
        "TrialLedger/registry/ctg-enums.json",
        "TrialLedger/layer2/semantics/x.py",
    )
    installed = (*tracked, "TrialLedger/__pycache__/cli.cpython-312.pyc")
    assert release_check.missing_package_files(tracked, installed) == ()
    assert release_check.missing_package_files(tracked, installed[:1]) == (
        "TrialLedger/layer2/semantics/x.py",
        "TrialLedger/registry/ctg-enums.json",
    )


def test_outputs_missing():
    expected = release_check.EXPECTED_OUTPUTS
    assert release_check.outputs_missing(expected, (*expected, "pulled/extra.txt")) == ()
    assert release_check.outputs_missing(expected, ("unexpected.xlsx", "pulled/studies.json")) == (
        "pulled/studies.csv",
        "pulled/review.xlsx",
        "pulled/record.xlsx",
        "landscape-run/landscape.json",
        "landscape-run/landscape.xlsx",
    )
    assert release_check.outputs_missing((), ()) == ()


def test_reason_problems_accepts_the_population_consequence_with_its_premise():
    answer = {
        "code": "complete",
        "operation": "entailment",
        "result": {"decision": {"result": "REFUTED", "proof": ["population"]}},
    }
    assert release_check.reason_problems(answer) == ()


@pytest.mark.parametrize(
    "answer,expected",
    [
        (None, ("reason_response_not_an_object",)),
        ({"code": "refused"}, ("reason_operation_incomplete",)),
        ({"code": "complete", "operation": "corpus"}, ("reason_operation_incomplete",)),
        ({"code": "complete", "operation": "entailment", "result": None}, ("reason_decision_missing",)),
        (
            {"code": "complete", "operation": "entailment", "result": {"decision": {"result": "ENTAILED"}}},
            ("reason_wrong_decision",),
        ),
        (
            {
                "code": "complete",
                "operation": "entailment",
                "result": {"decision": {"result": "REFUTED", "proof": []}},
            },
            ("reason_premise_missing",),
        ),
        (
            {
                "code": "complete",
                "operation": "entailment",
                "result": {"decision": {"result": "REFUTED", "proof": "population"}},
            },
            ("reason_premise_missing",),
        ),
    ],
)
def test_reason_problems_never_passes_refusal_wrong_consequence_or_missing_proof(answer, expected):
    assert release_check.reason_problems(answer) == expected


@pytest.mark.parametrize(
    "first, widths, filtered, frozen, expected",
    [
        (False, True, True, True, ()),
        (True, True, False, False, ()),
        (True, False, True, True, ("no_widths:w.xlsx/S",)),
        (False, False, False, False, ("no_widths:w.xlsx/S", "no_filter:w.xlsx/S", "not_frozen:w.xlsx/S")),
        (False, True, False, True, ("no_filter:w.xlsx/S",)),
        (False, True, True, False, ("not_frozen:w.xlsx/S",)),
    ],
)
def test_sheet_departures(first, widths, filtered, frozen, expected):
    assert release_check.sheet_departures("w.xlsx/S", first, widths, filtered, frozen) == expected


def test_new_files():
    before = {"/w/a": 3, "/w/b": 5}
    after = {"/w/a": 3, "/w/b": 7, "/w/pulled/studies.json": 900}
    assert release_check.new_files(before, after) == (("/w/b", 7), ("/w/pulled/studies.json", 900))
    assert release_check.new_files(after, after) == ()
    assert release_check.new_files(after, {}) == ()
    folder = release_check.FOLDER
    assert release_check.new_files({"/w/run": folder}, {"/w/run": folder, "/w/new": folder}) == (
        ("/w/new", folder),
    )


def test_accounting_of_the_real_pull_is_complete():
    entries = reconcile_ids(",".join(release_check.PULL_IDS), PULLED)
    assert release_check.accounting_problems(release_check.PULL_IDS, entries, ALIAS_LINE, True) == ()


def test_accounting_problems_are_named():
    entries = reconcile_ids(",".join(release_check.PULL_IDS), PULLED)
    asked = (*release_check.PULL_IDS, "NCT09999999")
    assert release_check.accounting_problems(asked, entries, "", True) == (
        "not_printed:NCT01086644",
        "not_accounted:NCT09999999",
    )
    found_only = reconcile_ids("NCT04852770", PULLED[:1])
    assert release_check.accounting_problems(("NCT04852770",), found_only, "", True) == ("no_alias_named",)
    assert release_check.accounting_problems(("NCT04852770",), found_only, "", False) == ()
    assert release_check.accounting_problems(("NCT04852770",), None, "", False) == (
        "not_accounted:NCT04852770",
    )


def test_an_alias_printed_as_its_code_is_not_said():
    entries = reconcile_ids(",".join(release_check.PULL_IDS), PULLED)
    assert release_check.accounting_problems(release_check.PULL_IDS, entries, OLD_ALIAS_LINE, True) == (
        "not_printed:NCT01086644",
    )
    wrong_trial = ALIAS_LINE.replace("NCT01030536", "NCT01030537")
    assert release_check.accounting_problems(release_check.PULL_IDS, entries, wrong_trial, True) == (
        "not_printed:NCT01086644",
    )


def test_a_number_not_found_is_said_by_number():
    entries = reconcile_ids("NCT04852770,NCT09999999,NCT12x", PULLED[:1])
    asked = ("NCT04852770", "NCT09999999", "NCT12x")
    printed = (
        "trialledger: NCT09999999: no trial in the registry has this number\nNCT12x: not a trial number\n"
    )
    assert release_check.accounting_problems(asked, entries, printed, False) == ()
    assert release_check.accounting_problems(asked, entries, printed.split("\n")[0], False) == (
        "not_printed:NCT12x",
    )
    assert release_check.accounting_problems(asked, entries, "NCT09999999 NCT12x", False) == (
        "not_printed:NCT09999999",
        "not_printed:NCT12x",
    )
    assert release_check.accounting_problems(asked, [*entries, "not an entry"], printed, False) == ()


def test_unknown_commands():
    available = ("doctor", "reason", "pull", "verify")
    guide = (
        "Run `trialledger doctor`, then `trialledger landscape`, `trialledger <command> --help` and again "
    )
    guide += "`trialledger landscape --run x`; `trialledger pull` saves."
    assert release_check.unknown_commands(guide, available) == ("landscape",)
    assert release_check.unknown_commands("`trialledger doctor` and `trialledger pull`", available) == ()


# A passage of `trialledger pull --help` as it stood on 2026-11-01.
PULL_HELP = """usage: trialledger pull [-h] [--out OUT] [NAME=VALUE ...]

Pull every ClinicalTrials.gov study a query matches, through the official API (spec/ctg-oas-v2.yaml),
into a new directory holding studies.json (the records exactly as the API sent them, plus provenance and
content digests), studies.csv (the API's own spreadsheet for the same query).

NAME is any /studies query parameter from the spec, sent exactly as given; the API rejects unknown names.
query.* parameters search the API's search areas and rank by relevance; filter.* parameters restrict the
set.
"""


def test_jargon_found_in_the_pull_help():
    found = release_check.jargon_found(PULL_HELP)
    assert found == ("API", "NAME=VALUE", "query.*", "filter.*", "digests", "spec/ctg-oas-v2.yaml")


def test_jargon_found_in_workbook_headings():
    found = release_check.jargon_found("NCT Number Piece Criterion Atoms Founder: correct? (yes/no) Warrant")
    assert found == ("Warrant", "Atoms", "Founder")


def test_jargon_is_found_only_whole():
    assert release_check.jargon_found("rapid APIs; digestion; JSONs; a re-derived copy; studies.json") == ()
    assert release_check.jargon_found("the API and its digest") == ("API", "digest")


@pytest.mark.parametrize(
    "verdicts, checks, expected",
    [
        (("as_expected", "warned"), ((), (), (), (), ()), "ready"),
        (("as_expected",), (), "ready"),
        ((), ((), ()), "not_ready"),
        (("as_expected", "unexpected_exit"), ((), ()), "not_ready"),
        (("as_expected", "skipped"), ((), ()), "not_ready"),
        (("as_expected",), (("TrialLedger/registry/ctg-enums.json",), ()), "not_ready"),
        (("as_expected",), ((), ("no_alias_named",)), "not_ready"),
        (("as_expected",), ((), ("no_filter:pulled/review.xlsx/Studies",)), "not_ready"),
        (("as_expected",), ((), None), "not_ready"),
        (("as_expected",), (None,), "not_ready"),
    ],
)
def test_overall_verdict(verdicts, checks, expected):
    assert release_check.overall_verdict(verdicts, checks) == expected
