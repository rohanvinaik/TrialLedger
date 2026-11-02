"""ingest.requested_id_words — what became of each number asked for, in the words pull and landscape print.

Positive: each status of reconcile_ids reads as plain words naming the number as the person wrote it; an alias
reads "<number> is another number of <trial>", naming the trial the registry answered with.
Negative: no status is printed as its code ("aliased" never appears); a status the words do not know is shown
as given, never dropped; an entry missing its keys still names what it can.
"""

import pytest

from TrialLedger.ingest import reconcile_ids, requested_id_words


def study(nct_id, aliases=()):
    identification = {"nctId": nct_id}
    if aliases:
        identification["nctIdAliases"] = list(aliases)
    return {"protocolSection": {"identificationModule": identification}}


ENTRIES = reconcile_ids(
    "NCT04852770,NCT01086644,NCT09999999,NCT4852770,NCT12x",
    [study("NCT04852770"), study("NCT01030536", ["NCT01086644"])],
)


def test_each_status_reads_as_plain_words():
    assert [requested_id_words(entry) for entry in ENTRIES] == [
        "NCT04852770: found under its own number",
        "NCT01086644 is another number of NCT01030536: the registry gave that trial's record",
        "NCT09999999: no trial in the registry has this number, or lists it as another number",
        "NCT4852770: asked for more than once, counted once",
        "NCT12x: not a trial number (NCT followed by up to eight digits)",
    ]


def test_the_number_is_named_as_written():
    (entry,) = reconcile_ids("nct1086644", [study("NCT01030536", ["NCT01086644"])])
    assert requested_id_words(entry).startswith("nct1086644 is another number of NCT01030536")


@pytest.mark.parametrize("entry", ENTRIES)
def test_no_status_is_printed_as_its_code(entry):
    words = requested_id_words(entry)
    assert "aliased" not in words and "malformed" not in words and "duplicate" not in words


def test_an_unknown_status_is_shown_as_given():
    assert requested_id_words({"requested": "NCT1", "status": "withheld"}) == "NCT1: withheld"


def test_an_entry_without_its_keys_names_what_it_can():
    assert requested_id_words({}) == ": "
    assert requested_id_words({"status": "aliased"}) == (
        " is another number of : the registry gave that trial's record"
    )
