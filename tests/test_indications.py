"""Intent checks: identity evidence never turns missing/unrelated MeSH into clinical scope."""

import base64
import json
from dataclasses import asdict

import pytest

from TrialLedger.layer2.indications import (
    LookupResult,
    MeshIdentity,
    MeshLookup,
    is_disease,
    lookup_url,
    parse_response,
    relation,
    resolve_indication,
)


def body(descriptor="D002289", label="Carcinoma, Non-Small-Cell Lung", trees=("C04.100",)):
    return json.dumps(
        {
            "results": {
                "bindings": [
                    {
                        "descriptor": {
                            "type": "uri",
                            "value": f"http://id.nlm.nih.gov/mesh/2026/{descriptor}",
                        },
                        "label": {"type": "literal", "value": label},
                        "tree": {"type": "uri", "value": f"http://id.nlm.nih.gov/mesh/2026/{tree}"},
                    }
                    for tree in trees
                ]
            }
        }
    ).encode()


NSCLC = MeshIdentity("D002289", "Carcinoma, Non-Small-Cell Lung", ("C04.100.200",), "2026")
LUNG = MeshIdentity("D008175", "Lung Neoplasms", ("C04.100",), "2026")
OTHER = MeshIdentity("D000544", "Alzheimer Disease", ("C10.228",), "2026")


@pytest.mark.parametrize(
    "payload", [b"null", b"{}", b"[]", b"bad", b'{"results":null}', b'{"results":{"bindings":[{}]}}']
)
def test_malformed_source_never_resolves(payload):
    assert parse_response(payload, "2026").code == "malformed"


def test_whole_response_trees_preserved_and_deduplicated():
    answer = parse_response(body(trees=("C04.100", "C08.200", "C04.100")), "2026")
    assert answer.code == "resolved"
    assert answer.identities[0].trees == ("C04.100", "C08.200")
    assert parse_response(body().replace(b"2026", b"2025"), "2026").code == "malformed"
    assert parse_response(b'{"results":{"bindings":[]}}', "2026").code == "not_found"


def test_distinct_descriptors_are_ambiguous_and_truncated_answer_refused():
    first = json.loads(body())
    second = json.loads(body("D000544", "Alzheimer Disease", ("C10.228",)))
    first["results"]["bindings"] += second["results"]["bindings"]
    assert parse_response(json.dumps(first).encode(), "2026").code == "ambiguous"
    first["results"]["bindings"] *= 500
    assert parse_response(json.dumps(first).encode(), "2026").code == "result_limit"


def test_typed_relations_never_call_extra_descriptor_contradiction():
    assert relation(NSCLC, NSCLC) == "equivalent"
    assert relation(LUNG, NSCLC) == "compatible_broader"
    assert relation(NSCLC, LUNG) == "compatible_narrower"
    assert relation(NSCLC, OTHER) == "unexplained_discrepancy"
    assert (
        relation(NSCLC, MeshIdentity(NSCLC.descriptor, NSCLC.label, NSCLC.trees, "2025"))
        == "scope_unresolved"
    )
    assert relation(NSCLC, MeshIdentity("D123", "Unknown", (), "2026")) == "scope_unresolved"


def test_process_is_not_disease_but_mental_disorder_is():
    assert is_disease(NSCLC)
    assert not is_disease(MeshIdentity("D123", "Process", ("C23.100",), "2026"))
    assert is_disease(MeshIdentity("D456", "Disorder", ("F03.100",), "2026"))
    assert not is_disease(MeshIdentity("D789", "Procedure", ("E01.100",), "2026"))


def test_literal_condition_controls_scope_not_unrelated_derived_mesh():
    lookups = {"Alzheimer": LookupResult("resolved", (OTHER,)), "NSCLC": LookupResult("resolved", (NSCLC,))}
    answer = resolve_indication(["Alzheimer"], lookups, (NSCLC.descriptor,), (NSCLC,))
    assert answer["code"] == "inapplicable"
    assert answer["decided_by"] == "conditions"
    assert answer["indications"] == [asdict(OTHER)]
    assert answer["relationships"][0]["relation"] == "unexplained_discrepancy"


def test_broader_condition_never_authorizes_or_denies_narrower_pack():
    lookups = {"Lung": LookupResult("resolved", (LUNG,)), "NSCLC": LookupResult("resolved", (NSCLC,))}
    assert resolve_indication(["Lung"], lookups, (NSCLC.descriptor,))["code"] == "scope_unresolved"
    assert resolve_indication(["NSCLC"], lookups, (LUNG.descriptor,))["code"] == "inapplicable"
    assert resolve_indication(["NSCLC"], lookups, (LUNG.descriptor, NSCLC.descriptor))["code"] == "applicable"


@pytest.mark.parametrize("code", ["not_found", "not_looked_up", "unavailable", "malformed", "ambiguous"])
def test_unresolved_condition_cannot_be_overridden_by_derived_mesh(code):
    assert (
        resolve_indication(["unresolved"], {"unresolved": LookupResult(code)}, (NSCLC.descriptor,), (NSCLC,))[
            "code"
        ]
        == "scope_unresolved"
    )


def test_missing_condition_and_scoped_own_assertions_have_explicit_provenance():
    assert resolve_indication([], {}, (NSCLC.descriptor,), (NSCLC,))["decided_by"] == "registry_mesh"
    assert resolve_indication([], {}, (NSCLC.descriptor,), (), (NSCLC,))["decided_by"] == "own_assertions"
    assert resolve_indication([], {}, (NSCLC.descriptor,))["code"] == "scope_unresolved"


def test_cache_replay_retains_exact_body_url_and_digest(tmp_path):
    calls = []
    raw = body()

    def fetch(url):
        calls.append(url)
        return raw

    adapter = MeshLookup(tmp_path, fetch=fetch)
    first = adapter.lookup("Carcinoma, Non-Small-Cell Lung")
    second = adapter.lookup("Carcinoma, Non-Small-Cell Lung")
    assert first == second
    assert len(calls) == 1
    assert first.code == "resolved"
    assert base64.b64decode(first.sources[0].body_b64) == raw
    assert first.sources[0].url == calls[0]
    saved_path = next(tmp_path.iterdir())
    saved = json.loads(saved_path.read_text())
    saved["digest"] = "corrupted"
    saved_path.write_text(json.dumps(saved))
    assert adapter.lookup("Carcinoma, Non-Small-Cell Lung").code == "cache_invalid"


def test_unavailable_source_is_retryable_and_negative_answer_cached(tmp_path):
    def fail(_url):
        raise OSError("offline")

    assert MeshLookup(tmp_path, fetch=fail).lookup("missing").code == "unavailable"
    assert list(tmp_path.iterdir()) == []
    adapter = MeshLookup(tmp_path, fetch=lambda _url: b'{"results":{"bindings":[]}}')
    assert adapter.lookup("missing").code == "not_found"
    assert MeshLookup(tmp_path, fetch=fail).lookup("missing").code == "not_found"


def test_query_is_fixed_version_and_label_injection_is_literal(tmp_path):
    url = lookup_url('x" } UNION { ?s ?p ?o } #', "2026")
    from urllib.parse import parse_qs, urlparse

    params = parse_qs(urlparse(url).query)
    assert params["year"] == ["2026"]
    assert 'x\\" } UNION' in params["query"][0]
    with pytest.raises(ValueError, match="fixed_mesh_year_required"):
        MeshLookup(tmp_path, year="current")
    assert MeshLookup(tmp_path).lookup("").code == "malformed_request"


def test_entry_term_query_uses_measured_mesh_predicates_and_preferred_concept():
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(lookup_url("Non-Small-Cell Lung Carcinoma", "2026")).query)["query"][0]
    assert "meshv:preferredConcept ?concept" in query
    assert "meshv:prefLabel|meshv:altLabel|rdfs:label" in query


@pytest.mark.parametrize("bad", [b"not json", b'{"results":{"bindings":' + b"[{}]" + b"}}"])
def test_malformed_response_is_preserved_but_retry_is_not_poisoned(tmp_path, bad):
    replies = iter([bad, body()])
    adapter = MeshLookup(tmp_path, fetch=lambda _url: next(replies))
    first = adapter.lookup("Carcinoma, Non-Small-Cell Lung")
    assert first.code == "malformed"
    assert base64.b64decode(first.sources[0].body_b64) == bad
    assert len(list((tmp_path / "failures").iterdir())) == 1
    second = adapter.lookup("Carcinoma, Non-Small-Cell Lung")
    assert second.code == "resolved"
    assert adapter.lookup("Carcinoma, Non-Small-Cell Lung") == second


def test_polyhierarchy_with_both_ancestry_directions_remains_scope_unresolved():
    """Authored tree-shape intent: mixed ancestry cannot choose one scope direction."""
    left = MeshIdentity("D1", "Left", ("C01", "C02.001"), "2026")
    right = MeshIdentity("D2", "Right", ("C01.001", "C02"), "2026")
    assert relation(left, right) == "scope_unresolved"
    assert relation(right, left) == "scope_unresolved"
    broad = MeshIdentity("D3", "Broad", ("C01",), "2026")
    narrow = MeshIdentity("D4", "Narrow", ("C01.001",), "2026")
    assert relation(broad, narrow) == "compatible_broader"
    assert relation(narrow, broad) == "compatible_narrower"
