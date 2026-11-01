"""The live stratified sample.

Positive: a draw is seeded, depends only on the set of IDs, the seed and the label, and takes n from the
discovery pool; a trial in two strata is kept once with both memberships and its union inclusion probability;
the whole sample records queries, pool sizes, the seed and the snapshot, and declares its balance check; a
declared cell no drawn trial holds is asked of the registry within the frame, exactly, and a seeded supplement
is drawn from its discovery pool with its own inclusion probability, and a trial drawn for two cells carries
its union probability; every form a cell query is built from was tried live and is declared with its date.
The confirmation pool is three batches (add-bank-coverage B8): `pool` names NCT04852770 confirmation batch 0
(its SHA-256 mod 10 is 0) and NCT01030536 discovery (5); the three batches partition exactly the reserved IDs;
a confirmation draw takes from its one named batch, seeded, and the sample records the batch it was drawn
from; a declared batch with a code version git names is allowed. A confirmation draw (Decision 9, B4) takes
no trial of a declared inspected list (a sample's, an audit's or a record's IDs) and counts those it excluded;
it is allowed for clean code at a commit, whose state names the commit and a digest of TrialLedger/ and
tests/, and for a batch the ledger leaves unused or gives to this same commit.
Negative: no confirmation-pool ID is ever drawn; a smaller pool gives fewer, never repeats; a sample whose
strata come from different snapshots fails; a present or undeclared cell is never asked or supplemented; a
supplement never repeats a sampled trial; supplements read across snapshots fail with SnapshotChanged, never
a bare RuntimeError; no form is declared verified without a live count above zero on that date. The batches
change nothing in discovery (the same draw as before B8); a confirmation draw never takes a discovery ID or
another batch's; a confirmation sample declares no supplement (a supplement comes from discovery); a batch
outside 0, 1, 2, or a code version git cannot name, is refused; so is code with uncommitted changes, a draw
with no inspected list or an empty one, an unreadable ledger, and a batch the ledger gives another commit."""

import json
from pathlib import Path

import pytest

from TrialLedger.sample import (
    BASE_FROM,
    CATEGORIES,
    LEGACY_PRESENT,
    NO_MESH,
    NONE,
    VERIFIED_FORMS,
    SnapshotChanged,
    base_query,
    batch_request,
    cell_query,
    code_state,
    declared_cells,
    draw,
    draw_batch,
    draw_sample,
    draw_supplements,
    holds_cell,
    inclusion,
    inspected_ids,
    ledger_batches,
    pool,
    query_forms,
    reserved,
    screen_inspected,
    stratum_query,
)

IDS = [f"NCT{n:08d}" for n in range(1, 201)]
P = "2026-11-01"  # the present a test sample is drawn on


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
    assert stratum_query(NO_MESH, "2026-11-01").endswith("AREA[ConditionMeshTerm]MISSING")
    query = stratum_query("Eye Diseases", "2026-11-01")
    assert 'AREA[ConditionMeshTerm]"Eye Diseases" OR AREA[ConditionAncestorTerm]"Eye Diseases"' in query
    assert query.startswith("AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2026-11-01]")


def test_the_frame_runs_to_the_present_the_sample_records():
    """Positive (B1, 2010 to the present): every stratum's query ends start dates at the present passed in,
    and the sample records that present and its base filter. Negative: no query keeps the old end, 2025-12-31,
    which only a sample drawn before the present was recorded is read with (LEGACY_PRESENT)."""
    asked = []

    def fake(query, progress):
        asked.append(query["filter.advanced"])
        return [], "2.0.5", "T"

    sample = draw_sample(2, "s", fake, present="2026-11-01")
    assert sample["present"] == "2026-11-01" and sample["base"] == base_query("2026-11-01")
    assert base_query("2026-11-01").endswith("AREA[StartDate]RANGE[2010-01-01,2026-11-01]")
    assert len(asked) == len(CATEGORIES) + 1
    assert all(q.startswith(base_query("2026-11-01") + " AND ") for q in asked)
    assert not any("2025-12-31" in q for q in asked)
    assert LEGACY_PRESENT == "2025-12-31" and BASE_FROM == "2010-01-01"


def test_supplements_query_the_frame_of_their_sample():
    rows = [{"axis": "phase", "value": "PHASE4", "status": "not_checked"}]
    asked = []

    def fake(query, progress):
        asked.append(query["filter.advanced"])
        return [], "2.0.5", "T"

    draw_supplements(rows, "s", 1, set(), fake, lambda m: None, LEGACY_PRESENT)
    draw_supplements(rows, "s", 1, set(), fake, lambda m: None, "2026-11-01")
    assert asked[0].startswith(base_query(LEGACY_PRESENT)) and asked[1].startswith(base_query("2026-11-01"))


def test_the_whole_sample_keeps_memberships_and_its_snapshot():
    shared = [nct for nct in IDS if not reserved(nct)][:3]

    def fake(query, progress):
        if "Neoplasms" in query["filter.advanced"] or "MISSING" in query["filter.advanced"]:
            return shared, "2.0.5", "T"
        return [], "2.0.5", "T"

    sample = draw_sample(2, "s", fake, present=P)
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

    with pytest.raises(SnapshotChanged, match="changed while sampling"):
        draw_sample(2, "s", fake, present=P)


def test_the_sample_declares_its_balance_check_before_any_draw():
    sample = draw_sample(2, "s", lambda query, progress: ([], "2.0.5", "T"), present=P)
    declared = sample["balance"]
    assert declared["cells"] == declared_cells() and declared["supplement_per_cell"] == 1
    assert declared["axes"] == {
        "phase": "Phase",
        "intervention_type": "InterventionType",
        "primary_purpose": "DesignPrimaryPurpose",
    }


def test_a_cell_query_is_exact_and_within_the_frame():
    query = cell_query("phase", "PHASE2", P)
    assert query.startswith(
        "AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2026-11-01] AND ("
    )
    assert "AREA[ConditionMeshTerm]MISSING" in query and 'AREA[ConditionAncestorTerm]"Eye Diseases"' in query
    assert "AREA[Phase]PHASE2" in query and "NOT AREA[Phase]PHASE1" in query
    assert "NOT AREA[Phase]PHASE2" not in query
    both = cell_query("phase", "PHASE1|PHASE2", P)
    assert "AREA[Phase]PHASE1 AND AREA[Phase]PHASE2 AND NOT AREA[Phase]NA" in both
    assert "NOT AREA[Phase]PHASE1" not in both and "NOT AREA[Phase]PHASE3" in both
    assert cell_query("primary_purpose", "SCREENING", P).endswith("AREA[DesignPrimaryPurpose]SCREENING")
    assert cell_query("intervention_type", "GENETIC", P).endswith("AREA[InterventionType]GENETIC")


def test_supplements_fill_only_empty_registry_cells_from_one_snapshot():
    rows = [
        {"axis": "phase", "value": "PHASE2", "status": "present"},
        {"axis": "phase", "value": "PHASE4", "status": "not_checked"},
        {"axis": "primary_purpose", "value": "SCREENING", "status": "not_checked"},
        {"axis": "phase", "value": NONE, "status": "undeclared"},
    ]
    drawable = [nct for nct in IDS if not reserved(nct)]
    asked = []

    def fake(query, progress):
        asked.append(query["filter.advanced"])
        if "PHASE4" in query["filter.advanced"]:
            return [*drawable[:3], *[n for n in IDS if reserved(n)][:2]], "2.0.5", "T"
        return [], "2.0.5", "T"

    registry, supplements, snapshot = draw_supplements(rows, "s", 1, {drawable[0]}, fake, lambda m: None, P)
    assert len(asked) == 2 and registry == {"phase=PHASE4": 5, "primary_purpose=SCREENING": 0}
    assert snapshot == {"api_version": "2.0.5", "data_timestamp": "T"}
    [item] = supplements
    assert item["nct"] in drawable[1:3] and item["label"] == "supplement phase=PHASE4"
    assert item["pool"] == 2 and item["inclusion_probability"] == pytest.approx(0.5)
    again = draw_supplements(rows, "s", 1, {drawable[0]}, fake, lambda m: None, P)[1]
    assert again == supplements
    nothing = draw_supplements(rows[:1], "s", 1, set(), fake, lambda m: None, P)
    assert nothing == ({}, [], {"api_version": "", "data_timestamp": ""})


def test_supplements_across_snapshots_fail():
    rows = [{"axis": "phase", "value": v, "status": "not_checked"} for v in ("NA", "PHASE4")]
    stamps = iter(["T1", "T2"])

    def fake(query, progress):
        return [], "2.0.5", next(stamps)

    with pytest.raises(SnapshotChanged, match="changed while supplementing"):
        draw_supplements(rows, "s", 1, set(), fake, lambda m: None, P)


def test_an_empty_stratum_draws_nothing_and_says_its_pool_is_empty():
    """Positive: an empty stratum returns an empty draw and a pool of zero, as a pair. Negative: never None, a
    bare list or a bare count."""
    result = draw([], 6, "s", "x")
    assert result == ([], 0)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], list) and result[1] == 0


def test_a_trial_supplementing_two_cells_carries_its_union_probability():
    drawable = [nct for nct in IDS if not reserved(nct)]
    rows = [
        {"axis": "phase", "value": "PHASE4", "status": "not_checked"},
        {"axis": "primary_purpose", "value": "SCREENING", "status": "not_checked"},
        {"axis": "intervention_type", "value": "GENETIC", "status": "not_checked"},
    ]

    def fake(query, progress):
        where = query["filter.advanced"]
        if "PHASE4" in where or "SCREENING" in where:
            return drawable[:2], "2.0.5", "T"
        return drawable[5:9], "2.0.5", "T"

    _registry, supplements, _snapshot = draw_supplements(rows, "s", 1, set(), fake, lambda m: None, P)
    assert len(supplements) == 3
    for item in supplements[:2]:
        assert item["inclusion_probability"] == pytest.approx(0.5)
        assert item["memberships"] == ["supplement phase=PHASE4", "supplement primary_purpose=SCREENING"]
        assert item["union_inclusion_probability"] == pytest.approx(1 - 0.5 * 0.5)
    genetic = supplements[2]
    assert genetic["memberships"] == ["supplement intervention_type=GENETIC"]
    assert genetic["union_inclusion_probability"] == genetic["inclusion_probability"] == pytest.approx(0.25)


def test_holds_cell_matches_a_combination_in_any_order_and_nothing_else():
    assert holds_cell(["PHASE2|PHASE1"], "PHASE1|PHASE2")
    assert holds_cell(["PHASE1|PHASE2"], "PHASE1|PHASE2")
    assert holds_cell(["DRUG", "DEVICE"], "DEVICE")
    assert not holds_cell(["PHASE1|PHASE2"], "PHASE2")
    assert not holds_cell(["PHASE2"], "PHASE1|PHASE2")
    assert not holds_cell([], "PHASE2") and not holds_cell(["PHASE2|PHASE3"], "PHASE1|PHASE2")


def test_the_query_forms_of_a_cell():
    assert query_forms("phase", "PHASE2") == ["AREA[Phase]", "NOT AREA[Phase]"]
    assert query_forms("phase", "PHASE1|PHASE2") == ["AREA[Phase]", "NOT AREA[Phase]"]
    assert query_forms("primary_purpose", "SCREENING") == ["AREA[DesignPrimaryPurpose]"]
    assert query_forms("intervention_type", "DRUG") == ["AREA[InterventionType]"]
    for axis in ("phase", "primary_purpose", "intervention_type"):
        assert all(form in cell_query(axis, "PHASE2", P) for form in query_forms(axis, "PHASE2"))


def test_every_verified_form_was_tried_live_on_its_date():
    """The declared list holds the forms the live check of tests/live_query_forms.json returned trials for,
    each with that check's date; a form it did not try, or that returned none, is never declared."""
    fixture = json.loads((Path(__file__).parent / "live_query_forms.json").read_text(encoding="utf-8"))
    assert set(VERIFIED_FORMS) == set(fixture["forms"])
    for form, asked in fixture["forms"].items():
        assert VERIFIED_FORMS[form] == fixture["asked"]
        assert asked["status"] == 200 and 0 < asked["totalCount"] < fixture["base"]["totalCount"]
        assert asked["query"].startswith(fixture["base"]["query"]) and form in asked["query"]
    exact = fixture["forms"]["NOT AREA[Phase]"]["totalCount"]
    assert exact < fixture["forms"]["AREA[Phase]"]["totalCount"]  # the NOT form excludes combinations
    forms_used = {
        form for axis, values in declared_cells().items() for v in values for form in query_forms(axis, v)
    }
    assert forms_used == set(VERIFIED_FORMS)


# ── add-bank-coverage B8: the confirmation pool as three sequential batches ─────────────────────────────────


def test_pool_names_real_trials_by_their_hash():
    assert pool("NCT04852770") == "confirmation_0"
    assert pool("NCT09000002") == "confirmation_1"
    assert pool("NCT01030536") == "discovery"
    assert reserved("NCT04852770") and not reserved("NCT01030536")


def test_the_three_batches_partition_exactly_the_reserved_ids():
    names = {nct: pool(nct) for nct in IDS}
    assert set(names.values()) == {"discovery", "confirmation_0", "confirmation_1", "confirmation_2"}
    for nct, name in names.items():
        assert reserved(nct) == (name != "discovery"), nct


def test_the_batches_change_nothing_in_discovery():
    """The discovery draw pinned before B8 (seed s, Neoplasms, the 200 IDs) is unchanged."""
    expected = ["NCT00000184", "NCT00000068", "NCT00000109", "NCT00000002", "NCT00000001", "NCT00000130"]
    assert draw(IDS, 6, "s", "Neoplasms") == (expected, 139)


def test_a_confirmation_draw_takes_only_its_own_batch():
    for batch in (0, 1, 2):
        members = {nct for nct in IDS if pool(nct) == f"confirmation_{batch}"}
        drawn, size = draw_batch(IDS, 500, "s", "Neoplasms", batch)
        assert size == len(members) and set(drawn) == members
    first, size = draw_batch(IDS, 3, "s", "Neoplasms", 1)
    assert size == 16 and len(set(first)) == 3
    assert all(pool(nct) == "confirmation_1" for nct in first)
    assert first == draw_batch(list(reversed(IDS)) + IDS[:5], 3, "s", "Neoplasms", 1)[0]
    assert first != draw_batch(IDS, 3, "t", "Neoplasms", 1)[0]
    assert not set(first) & set(draw(IDS, 500, "s", "Neoplasms")[0])
    assert draw_batch(IDS, -1, "s", "x", 2)[0] == [] and draw_batch([], 3, "s", "x", 0) == ([], 0)
    assert draw_batch(IDS, 5, "s", "x", 3) == ([], 0)


def test_a_confirmation_request_is_refused_unless_its_batch_and_code_version_are_named():
    a, d = "a" * 40, "d" * 64
    assert batch_request(0, a, d, [], [3], {}) == "ok" and batch_request(2, a, d, [], [3, 1], {}) == "ok"
    assert batch_request(3, a, d, [], [3], {}) == "unknown_batch"
    assert batch_request(-1, a, d, [], [3], {}) == "unknown_batch"
    assert batch_request(1, "not a git checkout", d, [], [3], {}) == "no_code_version"
    assert batch_request(1, "", d, [], [3], {}) == "no_code_version"
    assert batch_request(1, a, "", [], [3], {}) == "no_code_version"  # the source could not be digested
    assert batch_request(7, "not a git checkout", "", ["x"], [], None) == "unknown_batch"


def test_a_confirmation_request_needs_clean_code_the_inspected_lists_and_an_unused_batch():
    """Positive: clean code at a commit, every inspected list holding IDs, and a batch the ledger has not
    given to other code (unused, or used for this same source digest, whatever the commit now is, so
    committing the ledger never refuses a re-draw of the same code). Negative: a changed path, no inspected
    list, an empty one, an unreadable ledger, a batch used for other code are each refused by name."""
    a, b, d, e = "a" * 40, "b" * 40, "d" * 64, "e" * 64
    assert batch_request(1, a, d, [], [5], {"1": d}) == "ok"
    assert batch_request(1, b, d, [], [5], {"1": d}) == "ok"  # HEAD moved (the ledger committed), same code
    assert batch_request(1, a, d, [], [5], {"0": e, "2": e}) == "ok"
    assert batch_request(1, a, d, ["TrialLedger/banks.py"], [5], {}) == "uncommitted_changes"
    assert batch_request(1, a, d, [], [], {}) == "no_inspected"
    assert batch_request(1, a, d, [], [5, 0], {}) == "inspected_empty"
    assert batch_request(1, a, d, [], [5], None) == "ledger_unreadable"
    assert batch_request(1, a, d, [], [5], {"1": e}) == "batch_used"


def test_the_ledger_declares_each_used_batch_with_its_code():
    """Positive: each declared batch maps to the source digest of the code it confirmed (its entry naming the
    digest and the commit); an empty ledger has none used; the repository's ledger has none used. Negative: a
    ledger of another shape, an undeclared batch, an entry that is not an object, or one with an empty or
    missing digest or commit is None, never read as no batch used."""
    entry = {"source_digest": "d", "commit": "a"}
    other = {"source_digest": "e", "commit": "b"}
    assert ledger_batches({"rule": "r", "batches": {"0": entry, "2": other}}) == {"0": "d", "2": "e"}
    assert ledger_batches({"batches": {}}) == {}
    assert ledger_batches(None) is None and ledger_batches([]) is None and ledger_batches({}) is None
    assert ledger_batches({"batches": []}) is None
    assert ledger_batches({"batches": {"3": entry}}) is None
    assert ledger_batches({"batches": {"1": "a"}}) is None  # the earlier commit-only form is not read
    assert ledger_batches({"batches": {"1": {"source_digest": "", "commit": "a"}}}) is None
    assert ledger_batches({"batches": {"1": {"source_digest": "d", "commit": ""}}}) is None
    assert ledger_batches({"batches": {"1": {"source_digest": "d"}}}) is None
    assert ledger_batches({"batches": {"1": {"source_digest": 7, "commit": "a"}}}) is None
    repo = json.loads((Path(__file__).parent.parent / "confirmation_ledger.json").read_text(encoding="utf-8"))
    assert ledger_batches(repo) == {}


def test_the_inspected_ids_are_read_from_a_sample_an_audit_and_a_record():
    """Positive: a sample's trials, an audit's supplements and a record's studies, each once, sorted.
    Negative: any other shape, or an item without a string ID, gives nothing."""
    sample = {"trials": [{"nct": "NCT2"}, {"nct": "NCT1"}, {"nct": "NCT2"}], "supplements": [{"nct": "NCT3"}]}
    assert inspected_ids(sample) == ["NCT1", "NCT2", "NCT3"]
    record = {"provenance": {}, "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT9"}}}]}
    assert inspected_ids(record) == ["NCT9"]
    assert (
        inspected_ids(None) == [] and inspected_ids(["NCT1"]) == [] and inspected_ids({"ncts": ["x"]}) == []
    )
    broken = {"trials": [{"nct": 5}, "NCT1", {}], "studies": [{"protocolSection": {}}, 3], "supplements": 1}
    assert inspected_ids(broken) == []


def test_screening_removes_every_inspected_trial_and_counts_those_of_the_batch():
    """Positive: an inspected ID is never in what is kept; the count names the batch's IDs removed, once.
    Negative: an inspected ID of another pool is removed but not counted; with none inspected, nothing is."""
    batch1 = [nct for nct in IDS if pool(nct) == "confirmation_1"]
    others = [nct for nct in IDS if pool(nct) != "confirmation_1"][:3]
    inspected = frozenset(batch1[:4] + others)
    kept, excluded = screen_inspected(IDS + batch1[:1], inspected, 1)
    assert not set(kept) & inspected and len(kept) == len(IDS) - 7
    assert excluded == sorted(batch1[:4])
    assert screen_inspected(IDS, frozenset(), 1) == (IDS, [])
    assert screen_inspected(IDS, frozenset(others), 1)[1] == []


def test_a_confirmation_sample_never_draws_an_inspected_trial_and_counts_the_exclusion():
    """Positive: with the whole batch but two inspected, only those two can be drawn, and the sample counts
    the excluded trials once across strata. Negative: with nothing inspected, the B8 draw is unchanged."""
    batch2 = sorted(nct for nct in IDS if pool(nct) == "confirmation_2")
    inspected = frozenset(batch2[2:])
    sample = draw_sample(
        4, "s", lambda query, progress: (IDS, "2.0.5", "T"), batch=2, inspected=inspected, present=P
    )
    assert {t["nct"] for t in sample["trials"]} == set(batch2[:2])
    assert all(s["pool"] == 2 and s["inspected_excluded"] == 20 for s in sample["strata"])
    assert sample["inspected_excluded"] == 20
    plain = draw_sample(4, "s", lambda query, progress: (IDS, "2.0.5", "T"), batch=2, present=P)
    assert plain["inspected_excluded"] == 0 and all(s["pool"] == 22 for s in plain["strata"])
    assert plain["strata"][0]["drawn"] == draw_batch(IDS, 4, "s", CATEGORIES[0], 2)[0]
    assert (
        draw_sample(4, "s", lambda query, progress: (IDS, "2.0.5", "T"), present=P)["inspected_excluded"]
        is None
    )


def _fake_git(answers):
    def git(root, *args):
        answer = answers[args[0]]
        if isinstance(answer, Exception):
            raise answer
        return answer

    return git


def test_the_code_state_names_the_commit_the_changes_and_a_digest_of_the_source(tmp_path):
    """Positive: the commit, each changed path, and a digest of the tracked files' bytes that changes when one
    byte does. Negative: git unable to answer names no commit; an unreadable tracked file gives no digest."""
    (tmp_path / "TrialLedger").mkdir()
    (tmp_path / "TrialLedger" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("y = 2\n", encoding="utf-8")
    answers = {"rev-parse": "c" * 40 + "\n", "status": "", "ls-files": "tests/t.py\0TrialLedger/a.py\0"}
    state = code_state(tmp_path, git=_fake_git(answers))
    assert state["commit"] == "c" * 40 and state["dirty"] == []
    assert state["watched"] == ["TrialLedger", "tests"] and len(state["source_digest"]) == 64
    (tmp_path / "TrialLedger" / "a.py").write_text("x = 2\n", encoding="utf-8")
    changed = code_state(
        tmp_path, git=_fake_git(answers | {"status": " M TrialLedger/a.py\n?? tests/n.py\n"})
    )
    assert changed["dirty"] == ["TrialLedger/a.py", "tests/n.py"]
    assert changed["source_digest"] != state["source_digest"]
    gone = code_state(tmp_path, git=_fake_git(answers | {"ls-files": "TrialLedger/missing.py\0"}))
    assert gone["source_digest"] == "" and gone["commit"] == "c" * 40
    failed = code_state(tmp_path, git=_fake_git(answers | {"rev-parse": OSError("no git")}))
    assert failed["commit"] == "" and failed["source_digest"] == ""


def test_a_confirmation_sample_records_its_batch_and_declares_no_supplement():
    sample = draw_sample(4, "s", lambda query, progress: (IDS, "2.0.5", "T"), batch=2, present=P)
    assert sample["drawn_from"] == "confirmation_2" and sample["confirmation_batch"] == 2
    assert sample["confirmation_batches"]["confirmation_1"] == "sha256(NCT ID) mod 10 == 1"
    assert sample["balance"]["supplement_per_cell"] == 0
    assert sample["trials"] and all(pool(t["nct"]) == "confirmation_2" for t in sample["trials"])
    assert all(s["pool"] == 22 for s in sample["strata"])
    discovery = draw_sample(4, "s", lambda query, progress: (IDS, "2.0.5", "T"), present=P)
    assert discovery["drawn_from"] == "discovery" and discovery["confirmation_batch"] is None
    assert discovery["balance"]["supplement_per_cell"] == 1
    assert all(pool(t["nct"]) == "discovery" for t in discovery["trials"])
