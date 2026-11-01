"""Coherence — design coordinates as domains narrowed by evidence and relations, to a fixed point.

Positive: an inclusion atom keeps the values it states and an exclusion atom removes them, each removal named
with its criterion; relations narrow when their facts hold and their prior-lines condition is met; closure
reaches the same fixed point in any order; a trial requiring no prior advanced therapy resolves, under the
proposed relations, to first line; contradictory evidence empties a domain and names every cause.
Negative: silence never narrows (no evidence leaves every domain full); an unsectioned atom, an atom of
unspecified scope and an atom without values never narrow; a proposed relation never changes the reported
domain; a relation whose facts are absent never applies; an unknown relation id is never silently skipped;
an empty domain is never resolved.
"""

import itertools

import pytest

from TrialLedger.coherence import (
    COORDINATES,
    RELATIONS,
    SETTINGS,
    close,
    domain_state,
    narrow_by_evidence,
    resolve,
)

RELATION_IDS = tuple(relation.id for relation in RELATIONS)

FIRST_LINE = [
    ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
    ("inclusion", "stage", ("IV",), "", "c2"),
    ("inclusion", "extent", ("metastatic",), "", "c2"),
]


def test_silence_never_narrows():
    domains, causes = narrow_by_evidence([])
    assert domains == dict(COORDINATES)
    assert causes == []


def test_inclusion_keeps_and_exclusion_removes_with_causes():
    domains, causes = narrow_by_evidence(
        [
            ("inclusion", "biomarker:EGFR", ("negative", "unknown"), "", "c1"),
            ("exclusion", "biomarker:ALK", ("positive",), "", "c9"),
        ]
    )
    assert domains["selection:EGFR"] == ("negative", "unknown")
    assert domains["selection:ALK"] == ("negative", "unknown")
    assert causes == [("selection:EGFR", ("positive",), "c1"), ("selection:ALK", ("positive",), "c9")]


@pytest.mark.parametrize(
    "atom",
    [
        ("unsectioned", "prior_lines", ("0",), "advanced", "c1"),
        ("inclusion", "prior_lines", ("0",), "unspecified", "c1"),
        ("inclusion", "biomarker:PD-L1", ("positive",), "", "c1"),
        ("inclusion", "biomarker:EGFR", (), "", "c1"),
        ("inclusion", "stage", ("IV",), "", "c1"),
    ],
)
def test_atoms_that_state_no_coordinate_never_narrow(atom):
    assert narrow_by_evidence([atom]) == (dict(COORDINATES), [])


def test_contradictory_evidence_is_a_named_conflict():
    domains, causes = narrow_by_evidence(
        [
            ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
            ("inclusion", "prior_lines", ("1",), "advanced", "c4"),
        ]
    )
    assert domains["prior_advanced_lines"] == ()
    assert domain_state(domains["prior_advanced_lines"], COORDINATES["prior_advanced_lines"]) == "conflict"
    assert [ref for _, _, ref in causes] == ["c3", "c4"]


def test_first_line_resolves_under_the_approved_relation():
    result = resolve(FIRST_LINE)
    assert result["prior_advanced_lines"]["domain"] == ("0",)
    assert result["setting"]["domain"] == ("advanced_first_line",)
    assert result["setting"]["state"] == "resolved"
    assert {cause[2] for cause in result["setting"]["causes"]} >= {
        "first_line_when_no_prior_advanced_therapy"
    }


def setting_after(facts, lines=None):
    evidence = [("inclusion", "prior_lines", lines, "advanced", "c1")] if lines else []
    domains, _ = narrow_by_evidence(evidence)
    approved = [r.id for r in RELATIONS if r.approval == "approved"]
    return close(domains, facts, approved)[0]["setting"]


@pytest.mark.parametrize(
    "facts, lines",
    [
        # neoadjuvant stage III requiring no prior therapy for "locally advanced" disease (Codex, 2026-10-31)
        (["inclusion:extent:locally advanced", "inclusion:resection:resectable"], ("0",)),
        # resected oligometastatic disease, adjuvant
        (["inclusion:extent:metastatic", "inclusion:stage:IV", "inclusion:resection:resected"], None),
        # consolidation after definitive chemoradiation, one prior platinum regimen given with radiation
        (["inclusion:prior_agent:radiotherapy", "inclusion:setting_word:consolidation"], ("1",)),
        # "stage III or IV" admits stage III chemoradiation
        (["inclusion:stage:III", "inclusion:stage:IV"], None),
    ],
)
def test_approved_relations_never_fire_on_the_counterexamples(facts, lines):
    assert setting_after(facts, lines) == SETTINGS


def test_maintenance_survives_a_prior_line_requirement():
    assert "maintenance" in setting_after(["inclusion:extent:metastatic"], ("1",))


def test_closure_is_order_independent():
    domains, _ = narrow_by_evidence(FIRST_LINE)
    facts = ["inclusion:stage:IV", "inclusion:extent:metastatic", "inclusion:resection:resected"]
    results = {
        tuple(close(domains, facts, list(order))[0].items()) for order in itertools.permutations(RELATION_IDS)
    }
    assert len(results) == 1


def test_a_relation_without_its_facts_never_applies():
    domains, _ = narrow_by_evidence([])
    closed, causes = close(domains, [], list(RELATION_IDS))
    assert closed == dict(COORDINATES)
    assert causes == []


def test_relations_that_disagree_empty_the_domain_with_both_named():
    domains, _ = narrow_by_evidence([("inclusion", "prior_lines", ("0",), "advanced", "c1")])
    facts = ["inclusion:extent:metastatic", "inclusion:setting_word:consolidation"]
    closed, causes = close(domains, facts, list(RELATION_IDS))
    assert closed["setting"] == ()
    assert {relation for _, _, relation in causes} >= {
        "first_line_when_no_prior_advanced_therapy",
        "consolidation_when_named",
    }


def test_an_unknown_relation_is_never_skipped():
    with pytest.raises(KeyError):
        close(dict(COORDINATES), [], ["no_such_relation"])


@pytest.mark.parametrize(
    "domain, state",
    [
        ((), "conflict"),
        (("0",), "resolved"),
        (("0", "1"), "unresolved"),
        (("0", "1", "2", "3+"), "unnarrowed"),
    ],
)
def test_domain_states(domain, state):
    assert domain_state(domain, COORDINATES["prior_advanced_lines"]) == state
