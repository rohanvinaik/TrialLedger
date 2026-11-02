"""First use and cached reuse derive from the same retained source representation."""

import copy
import json

import httpx
import pytest
from records import results_study
from rxnav_fake import FakeRxNav
from test_landscape_run import Registry

from TrialLedger import classes as rx
from TrialLedger import cli

NAME = "Recorded source name"


def source_for(case):
    names = {NAME: ["100"]}
    if case == "negative":
        names = {}
    elif case == "ambiguous":
        names = {NAME: ["100", "200"]}
    return FakeRxNav(
        names=names,
        concepts={"100": ("Canonical source name", "IN"), "200": ("Distinct source name", "IN")},
        classes={"100": [("C", "Declared class", "EPC", "has_epc", "DAILYMED", "100")]},
        failing={NAME} if case == "failed" else set(),
    )


def forbidden(*_args, **_kwargs):
    raise AssertionError("A completed run must not make a fresh service request")


@pytest.mark.parametrize(
    "case, identity",
    (
        ("positive", "ingredient"),
        ("negative", "not_in_rxnorm"),
        ("ambiguous", "ambiguous"),
        ("failed", "lookup_failed"),
    ),
)
def test_first_identity_cache_answer_is_the_exact_retained_representation_and_reused(
    tmp_path, case, identity
):
    path = tmp_path / "classes.json"
    source = source_for(case)
    first = rx.load_or_lookup_at(path, [NAME], [NAME], fill_axes=True, get=source, sleep=lambda _: None)
    saved = path.read_bytes()
    retained = json.loads(saved)["answers"]
    assert json.dumps(first) == json.dumps(retained)
    assert rx.identity_evidence(NAME, first[NAME])["code"] == identity
    before = json.dumps(rx.class_evidence([NAME], first))
    second = rx.load_or_lookup_at(path, [NAME], [NAME], fill_axes=True, get=forbidden, sleep=forbidden)
    assert path.read_bytes() == saved
    assert json.dumps(second) == json.dumps(first)
    assert json.dumps(rx.class_evidence([NAME], second)) == before
    assert first[NAME]["release"][:2] == ["found", "05-Oct-2026"]
    assert first[NAME]["release_end"][:2] == ["found", "05-Oct-2026"]
    if case in ("negative", "ambiguous", "failed"):
        assert source.count(rx.RXCLASS_BY_RXCUI) == 0
        assert all(not first[NAME]["axes"][rx.axis_key(*query)]["assertions"] for query in rx.QUERIES)


@pytest.mark.parametrize("case", ("positive", "negative", "ambiguous", "failed"))
def test_completed_cli_run_reuses_identity_evidence_and_keeps_all_artifact_bytes(tmp_path, case):
    study = copy.deepcopy(results_study())
    study["protocolSection"]["armsInterventionsModule"]["interventions"] = [{"type": "DRUG", "name": NAME}]
    nct = study["protocolSection"]["identificationModule"]["nctId"]
    registry = Registry([study])
    source = source_for(case)
    flags = ["landscape", "--run", str(tmp_path), "--ids", nct, "--mode", "direct"]
    assert cli.main(flags, http=registry.client(), rxclass_get=source, sleep=lambda _: None) == 0
    paths = [tmp_path / name for name in ("classes.json", "landscape.json", "landscape.xlsx")]
    before = {path.name: path.read_bytes() for path in paths}
    assert registry.requests and source.asked
    idle_registry = httpx.Client(transport=httpx.MockTransport(forbidden))
    assert cli.main(flags, http=idle_registry, rxclass_get=forbidden, sleep=forbidden) == 0
    assert {path.name: path.read_bytes() for path in paths} == before


def test_a_class_query_absent_from_an_established_identity_is_still_fetched(tmp_path):
    path = tmp_path / "classes.json"
    first_source = source_for("positive")
    rx.load_or_lookup_at(path, [NAME], [NAME], fill_axes=True, get=first_source, sleep=lambda _: None)
    cache = json.loads(path.read_text())
    missing = rx.axis_key("MEDRT", "has_moa")
    del cache["answers"][NAME]["axes"][missing]
    path.write_text(json.dumps(cache, sort_keys=True))
    source = source_for("positive")
    answers = rx.load_or_lookup_at(path, [NAME], [NAME], fill_axes=True, get=source, sleep=lambda _: None)
    assert source.count(rx.RXCLASS_BY_RXCUI) == 1
    assert answers[NAME]["axes"][missing]["code"] == "not_found"
    assert json.dumps(answers) == json.dumps(json.loads(path.read_text())["answers"])
