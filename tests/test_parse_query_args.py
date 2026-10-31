"""parse_query_args — command-line words become API parameters only when each is unambiguous.

Positive: `name=value` words become parameters in the order given; only the first "=" splits, so values
such as Essie expressions keep their own "="; an empty value is passed on for check_query to judge.
Negative: never guess a word without "=" or with an empty name; never pick one of two values given for the
same name. Each refusal names the offending words or names and returns no parameters.
"""

from TrialLedger.cli import parse_query_args


def test_single_parameter():
    assert parse_query_args(["filter.ids=NCT04852770"]) == (
        "ok",
        {"filter.ids": "NCT04852770"},
        [],
    )


def test_several_parameters_keep_their_order():
    code, params, bad = parse_query_args(["query.cond=lung cancer", "filter.overallStatus=RECRUITING"])
    assert (code, list(params.items()), bad) == (
        "ok",
        [("query.cond", "lung cancer"), ("filter.overallStatus", "RECRUITING")],
        [],
    )


def test_only_the_first_equals_sign_splits():
    assert parse_query_args(["filter.advanced=AREA[Phase]=PHASE3"]) == (
        "ok",
        {"filter.advanced": "AREA[Phase]=PHASE3"},
        [],
    )


def test_empty_value_is_passed_on():
    assert parse_query_args(["query.cond="]) == ("ok", {"query.cond": ""}, [])


def test_no_words_is_an_empty_query():
    assert parse_query_args([]) == ("ok", {}, [])


def test_word_without_equals_is_refused():
    assert parse_query_args(["filter.ids=NCT04852770", "lung"]) == ("not_name_value", {}, ["lung"])


def test_word_with_empty_name_is_refused():
    assert parse_query_args(["=RECRUITING"]) == ("not_name_value", {}, ["=RECRUITING"])


def test_every_malformed_word_is_named():
    assert parse_query_args(["a", "query.cond=x", "=b"]) == ("not_name_value", {}, ["a", "=b"])


def test_repeated_name_is_refused():
    assert parse_query_args(["query.cond=asthma", "query.cond=copd"]) == (
        "duplicate",
        {},
        ["query.cond"],
    )


def test_repeated_name_is_named_once():
    assert parse_query_args(["query.cond=a", "query.cond=b", "query.cond=c"]) == (
        "duplicate",
        {},
        ["query.cond"],
    )


def test_malformed_is_reported_before_duplicate():
    assert parse_query_args(["query.cond=a", "query.cond=b", "x"]) == ("not_name_value", {}, ["x"])
