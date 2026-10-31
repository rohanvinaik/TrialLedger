"""check_query — a /studies query is sent only when the API will answer it exactly as written.

Positive: an ordinary query, an ID filter, or an ID-only query with no filters to lose is sent ("ok").
Negative: never send an empty query (the whole registry); never let a caller set a parameter this tool owns;
never send a blank value; never send an NCT-ID-only query.* value beside any filter, because the API then
silently ignores every filter. Each refusal names the parameters concerned, sorted.
"""

from TrialLedger.ingest import check_query


def test_ordinary_query_is_sent():
    assert check_query({"query.cond": "lung cancer", "filter.overallStatus": "RECRUITING"}) == (
        "ok",
        [],
    )


def test_id_filter_alone_is_sent():
    assert check_query({"filter.ids": "NCT04852770|NCT01030536"}) == ("ok", [])


def test_id_only_query_with_no_filter_is_sent():
    assert check_query({"query.term": "NCT01030536"}) == ("ok", [])


def test_empty_query_is_refused():
    assert check_query({}) == ("no_parameters", [])


def test_format_is_reserved():
    assert check_query({"query.cond": "asthma", "format": "csv"}) == ("reserved", ["format"])


def test_markup_format_is_reserved():
    assert check_query({"query.cond": "asthma", "markupFormat": "legacy"}) == (
        "reserved",
        ["markupFormat"],
    )


def test_fields_is_reserved():
    assert check_query({"query.cond": "asthma", "fields": "NCTId"}) == ("reserved", ["fields"])


def test_count_total_is_reserved():
    assert check_query({"query.cond": "asthma", "countTotal": "false"}) == (
        "reserved",
        ["countTotal"],
    )


def test_page_size_is_reserved():
    assert check_query({"query.cond": "asthma", "pageSize": "5"}) == ("reserved", ["pageSize"])


def test_page_token_is_reserved():
    assert check_query({"query.cond": "asthma", "pageToken": "abc"}) == ("reserved", ["pageToken"])


def test_every_reserved_name_is_reported_sorted():
    assert check_query({"pageToken": "a", "format": "csv", "query.cond": "x"}) == (
        "reserved",
        ["format", "pageToken"],
    )


def test_blank_value_is_refused():
    assert check_query({"query.cond": "   ", "query.term": "asthma"}) == (
        "empty_value",
        ["query.cond"],
    )


def test_empty_string_value_is_refused():
    assert check_query({"filter.overallStatus": ""}) == ("empty_value", ["filter.overallStatus"])


def test_reserved_is_reported_before_blank():
    assert check_query({"pageSize": "", "query.cond": ""}) == ("reserved", ["pageSize"])


def test_blank_is_reported_before_ignored_filters():
    assert check_query(
        {"query.term": "NCT01030536", "filter.overallStatus": "RECRUITING", "query.cond": " "}
    ) == ("empty_value", ["query.cond"])


def test_id_only_term_beside_status_filter_is_refused():
    assert check_query({"query.term": "NCT01030536", "filter.overallStatus": "RECRUITING"}) == (
        "filters_ignored",
        ["query.term"],
    )


def test_lowercase_id_counts_as_id_only():
    assert check_query({"query.cond": "nct01030536", "filter.advanced": "AREA[Phase]PHASE3"}) == (
        "filters_ignored",
        ["query.cond"],
    )


def test_comma_and_space_separated_ids_count_as_id_only():
    assert check_query({"query.term": "NCT01030536, NCT04852770", "aggFilters": "status:rec"}) == (
        "filters_ignored",
        ["query.term"],
    )


def test_short_form_id_counts_as_id_only():
    assert check_query({"query.term": "NCT1030536", "postFilter.overallStatus": "COMPLETED"}) == (
        "filters_ignored",
        ["query.term"],
    )


def test_every_id_only_query_is_named_sorted():
    assert check_query(
        {
            "query.term": "NCT01030536",
            "query.cond": "NCT04852770",
            "filter.geo": "distance(39.0,-77.1,50mi)",
        }
    ) == ("filters_ignored", ["query.cond", "query.term"])


def test_ids_mixed_with_words_are_not_id_only():
    assert check_query({"query.term": "NCT01030536 lymphoma", "filter.overallStatus": "RECRUITING"}) == (
        "ok",
        [],
    )


def test_pipe_joined_ids_are_not_id_only():
    assert check_query({"query.term": "NCT01030536|NCT04852770", "filter.overallStatus": "RECRUITING"}) == (
        "ok",
        [],
    )


def test_separators_alone_are_not_id_only():
    assert check_query({"query.term": ",", "filter.overallStatus": "RECRUITING"}) == ("ok", [])


def test_all_zero_id_is_not_an_id():
    assert check_query({"query.term": "NCT00000000", "filter.overallStatus": "RECRUITING"}) == (
        "ok",
        [],
    )


def test_ids_in_a_filter_are_not_flagged():
    assert check_query({"filter.ids": "NCT01030536", "filter.overallStatus": "COMPLETED"}) == (
        "ok",
        [],
    )


def test_geo_decay_is_not_a_filter():
    assert check_query(
        {"query.term": "NCT01030536", "geoDecay": "func:exp,scale:300mi,offset:0mi,decay:0.5"}
    ) == ("ok", [])


def test_sort_is_not_a_filter():
    assert check_query({"query.term": "NCT01030536", "sort": "LastUpdatePostDate"}) == ("ok", [])
