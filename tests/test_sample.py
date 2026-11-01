"""The live stratified sample.

Positive: a draw is seeded, depends only on the set of IDs, the seed and the label, and takes n from the
discovery pool; a trial in two strata is kept once with both memberships and its union inclusion probability;
the whole sample records queries, pool sizes, the seed and the snapshot.
Negative: no confirmation-pool ID is ever drawn; a smaller pool gives fewer, never repeats; a sample whose
strata come from different snapshots fails."""

import pytest

from TrialLedger.sample import (
    CATEGORIES,
    NO_MESH,
    draw,
    draw_sample,
    inclusion,
    reserved,
    stratum_query,
)

IDS = [f"NCT{n:08d}" for n in range(1, 201)]


def test_the_confirmation_pool_is_fixed_and_never_drawn():
    held = [nct for nct in IDS if reserved(nct)]
    assert 30 < len(held) < 90
    drawn, pool = draw(IDS, 500, "s", "Neoplasms")
    assert pool == len(IDS) - len(held) and len(drawn) == pool
    assert not set(drawn) & set(held)


def test_a_draw_is_seeded_and_order_free():
    first, _ = draw(IDS, 6, "s", "Neoplasms")
    assert first == draw(list(reversed(IDS)) + IDS[:10], 6, "s", "Neoplasms")[0]
    assert len(first) == 6 == len(set(first))
    assert first != draw(IDS, 6, "t", "Neoplasms")[0]
    assert first != draw(IDS, 6, "s", "Eye Diseases")[0]
    assert draw(IDS, 0, "s", "x") == ([], draw(IDS, 0, "s", "x")[1])
    assert draw(IDS, -1, "s", "x")[0] == []
    assert draw([], 6, "s", "x") == ([], 0)


def test_union_inclusion_probability():
    sizes = {"a": (6, 60), "b": (6, 12), "c": (0, 0)}
    assert inclusion(["a"], sizes) == pytest.approx(0.1)
    assert inclusion(["a", "b"], sizes) == pytest.approx(1 - 0.9 * 0.5)
    assert inclusion(["c"], sizes) == 0
    assert inclusion([], sizes) == 0
    assert inclusion(["b"], {"b": (20, 12)}) == pytest.approx(1)


def test_stratum_queries():
    assert stratum_query(NO_MESH).endswith("AREA[ConditionMeshTerm]MISSING")
    query = stratum_query("Eye Diseases")
    assert 'AREA[ConditionMeshTerm]"Eye Diseases" OR AREA[ConditionAncestorTerm]"Eye Diseases"' in query
    assert query.startswith("AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2025-12-31]")


def test_the_whole_sample_keeps_memberships_and_its_snapshot():
    shared = [nct for nct in IDS if not reserved(nct)][:3]

    def fake(query, progress):
        if "Neoplasms" in query["filter.advanced"] or "MISSING" in query["filter.advanced"]:
            return shared, "2.0.5", "T"
        return [], "2.0.5", "T"

    sample = draw_sample(2, "s", fake)
    assert sample["data_timestamp"] == "T" and len(sample["strata"]) == len(CATEGORIES) + 1
    trials = {t["nct"]: t for t in sample["trials"]}
    assert set(trials) <= set(shared) and 2 <= len(trials) <= 3
    for trial in trials.values():
        assert trial["strata"] == ["Neoplasms", NO_MESH]
        assert trial["inclusion_probability"] == pytest.approx(1 - (1 - 2 / 3) ** 2)


def test_a_sample_across_snapshots_fails():
    stamps = iter(["T1"] + ["T2"] * 40)

    def fake(query, progress):
        return [], "2.0.5", next(stamps)

    with pytest.raises(RuntimeError, match="changed while sampling"):
        draw_sample(2, "s", fake)


def test_an_empty_stratum_draws_nothing_and_says_its_pool_is_empty():
    """Positive: an empty stratum returns an empty draw and a pool of zero, as a pair. Negative: never None, a
    bare list or a bare count."""
    result = draw([], 6, "s", "x")
    assert result == ([], 0)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], list) and result[1] == 0
