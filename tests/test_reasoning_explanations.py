"""Intent: expose real consumers and scope alternatives without changing clinical conclusions."""

from __future__ import annotations

import copy
import itertools

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import coherence, coordinate_admission, entail, interpretations, result_semantics
from TrialLedger.layer2.reasoning_explanations import (
    coordinate_effect_code,
    interpretation_contrast_code,
    relation_application_code,
)


def evidence(concept, values, *, scope="", status="known", ref="person:choice", section="inclusion"):
    return {
        "section": section,
        "concept": concept,
        "values": list(values),
        "scope": scope,
        "ref": ref,
        "standing": {"status": status, "resolution": "resolved", "basis": [ref]},
    }


def coordinates(given):
    typed = [(r["section"], r["concept"], tuple(r["values"]), r["scope"], r["ref"]) for r in given]
    return coordinate_admission.resolve(given, typed)


def test_relation_application_code_direct_intent_all_guard_combinations():
    for missing, alternative, lines, forbidden in itertools.product((False, True), repeat=4):
        actual = relation_application_code(missing, alternative, lines, forbidden)
        expected = (
            "missing_required"
            if missing
            else "missing_alternative"
            if alternative
            else "lines_outside"
            if not lines
            else "guarded"
            if forbidden
            else "applicable"
        )
        assert actual == expected
    assert relation_application_code(False, False, True, False) == "applicable"
    assert relation_application_code(False, False, True, True) == "guarded"
    assert relation_application_code(True, False, True, True) == "missing_required"
    assert relation_application_code(False, False, False, True) == "lines_outside"


def test_coordinate_effect_code_direct_intent_all_combinations():
    for accepted, consumer, active, narrowed, guarded in itertools.product((False, True), repeat=5):
        actual = coordinate_effect_code(accepted, consumer, active, narrowed, guarded)
        expected = (
            "withheld"
            if not accepted
            else "no_consumer"
            if not consumer
            else "narrowed"
            if active and narrowed
            else "guarded"
            if guarded
            else "redundant"
            if active
            else "inactive"
        )
        assert actual == expected
    assert coordinate_effect_code(True, True, True, True, True) == "narrowed"
    assert coordinate_effect_code(True, True, False, False, True) == "guarded"
    assert coordinate_effect_code(True, True, True, False, False) == "redundant"
    assert coordinate_effect_code(True, True, False, False, False) == "inactive"


@pytest.mark.parametrize(
    "answers,selected,expected",
    [
        ((), False, "none"),
        (("OUT_OF_SCOPE",), True, "selected_out_of_scope"),
        (("OUT_OF_SCOPE",), False, "interpretation_out_of_scope"),
        (("OUT_OF_SCOPE", "OUT_OF_SCOPE"), False, "interpretation_out_of_scope"),
        (("OUT_OF_SCOPE", "REFUTED"), False, "interpretation_scope_contrast"),
        (("OUT_OF_SCOPE", "UNDETERMINED"), False, "interpretation_scope_contrast"),
        (("ENTAILED", "REFUTED"), False, "interpretation_answer_contrast"),
        (("REFUTED", "REFUTED"), False, "none"),
    ],
)
def test_interpretation_contrast_code_direct_intent(answers, selected, expected):
    assert interpretation_contrast_code(answers, selected) == expected


def test_literal_setting_word_has_no_consumer_and_does_not_invent_progression_rule():
    given = [
        evidence("setting_word", ["advanced_previously_treated"]),
        evidence("prior_lines", ["1", "2", "3+"], scope="advanced"),
        evidence("biomarker:KRAS", ["positive"]),
    ]
    result = coordinates(given)
    assert result["admission"][0]["code"] == "accepted"
    assert result["effects"][0]["code"] == "no_consumer"
    assert result["effects"][0]["consumers"] == result["effects"][0]["domain_deltas"] == []
    assert result["coordinates"]["setting"]["interpolated"]["domain"] == (
        "advanced_previously_treated",
        "maintenance",
    )
    assert result["coordinates"]["setting"]["domain"] == coherence.SETTINGS


def test_explicit_setting_is_a_distinct_person_restriction_not_a_setting_word_equivalence():
    given = [evidence("setting", ["advanced_previously_treated"])]
    result = coordinates(given)
    assert result["coordinates"]["setting"]["domain"] == ("advanced_previously_treated",)
    assert result["coordinates"]["prior_advanced_lines"]["domain"] == coherence.PRIOR_LINES
    assert result["effects"][0]["code"] == "narrowed"
    assert result["effects"][0]["consumers"][0]["rule"] == "coherence.narrow_by_evidence"
    assert coherence.direct_coordinate("setting_word", "") == ""
    assert coherence.direct_coordinate("setting", "") == "setting"
    assert coherence.direct_coordinate("prior_lines", "") == ""
    assert coherence.direct_coordinate("prior_lines", "advanced") == "prior_advanced_lines"
    assert coherence.direct_coordinate("biomarker:KRAS", "") == "selection:KRAS"
    assert coherence.direct_coordinate("biomarker:unknown", "") == ""


def test_effect_standing_is_preserved_and_pending_setting_does_not_narrow():
    given = [
        evidence("setting", ["maintenance"], status="interpolated"),
        evidence("setting", ["adjuvant"], status="proposed"),
    ]
    original = copy.deepcopy(given)
    result = coordinates(given)
    assert result["coordinates"]["setting"]["domain"] == coherence.SETTINGS
    assert result["coordinates"]["setting"]["interpolated"]["domain"] == ("maintenance",)
    assert [row["code"] for row in result["effects"]] == ["narrowed", "withheld"]
    assert [row["standing"]["status"] for row in result["effects"]] == ["interpolated", "proposed"]
    assert result["effects"][1]["domain_deltas"] == []
    result["effects"][0]["standing"]["basis"].append("output-only")
    assert given == original


def test_duplicate_support_is_redundant_without_losing_distinct_provenance():
    given = [
        evidence("biomarker:KRAS", ["positive"], ref="source:A"),
        evidence("biomarker:KRAS", ["positive"], ref="source:B"),
    ]
    result = coordinates(given)
    assert [row["code"] for row in result["effects"]] == ["redundant", "redundant"]
    assert [row["ref"] for row in result["effects"]] == ["source:A", "source:B"]
    assert all(row["domain_deltas"] == [] for row in result["effects"])
    assert result["coordinates"]["selection:KRAS"]["domain"] == ("positive",)


def test_active_veto_is_a_consumer_even_when_it_removes_no_coordinate_value():
    given = [evidence("extent", ["metastatic"]), evidence("setting_word", ["adjuvant"])]
    result = coordinates(given)
    guard = result["effects"][1]
    assert guard["code"] == "guarded"
    advanced = next(
        row
        for row in guard["consumers"]
        if row.get("relation") == "advanced_when_metastatic_disease_required"
    )
    assert advanced["applicability"] == "guarded"
    assert advanced["details"]["matched_required"] == ["inclusion:extent:metastatic"]
    assert advanced["matched_fact_roles"] == {"forbidden": ["inclusion:setting_word:adjuvant"]}
    assert advanced["details"]["matched_forbidden"] == ["inclusion:setting_word:adjuvant"]
    assert any(row["preserved_by_input"] for row in guard["domain_deltas"])
    assert result["coordinates"]["setting"]["interpolated"]["domain"] == coherence.SETTINGS
    # With no positive antecedent, the same veto is recorded but is not decisive guarding.
    inactive = coordinates([given[1]])["effects"][0]
    assert inactive["code"] == "inactive"
    assert all(row["applicability"] != "guarded" for row in inactive["consumers"])


def test_unspecified_line_scope_has_a_named_inactive_direct_consumer():
    result = coordinates([evidence("prior_lines", ["0"], scope="unspecified")])
    effect = result["effects"][0]
    assert effect["code"] == "inactive"
    assert effect["consumers"][0]["reason"] == "advanced_scope_required"
    assert result["coordinates"]["prior_advanced_lines"]["domain"] == coherence.PRIOR_LINES


def literal(comparison, value, key="ECOG", unit="ECOG"):
    return a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", key),
        a.Value("quantity", comparison, number=value, unit=unit),
    )


def premise(identity, body, *, cohort=None, status="proposed"):
    return a.ScopedAssertion(
        identity,
        "source:" + identity,
        "required",
        body,
        cohort=cohort or a.Scope("all_participants"),
        status=status,
        resolution="resolved",
        rule=a.Rule("person-or-reading", "1", warrants=("source:" + identity,)),
    )


def scope_case(*, selected=None, fixed=(), queries=None):
    crossover = premise("ecog-crossover", literal("le", 2), cohort=a.Scope("cohort_ref", "crossover"))
    entry = premise("ecog-entry", literal("le", 2))
    frames = tuple(
        interpretations.Interpretation(identity, identity, "assistant", ("source:eligibility",), (item,))
        for identity, item in (("crossover-only", crossover), ("entry", entry))
    )
    return interpretations.resolve(
        "study:example",
        fixed,
        (),
        frames,
        queries or (interpretations.Query("ecog3-at-entry", literal("eq", 3)),),
        context=entail.Context(cohort="randomized-entry"),
        selected=selected,
    )


def pointer(document, path):
    value = document
    for key in path.removeprefix("/").split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def test_scope_contrast_has_distinct_answers_real_scope_links_and_no_false_refutation():
    result = scope_case()
    common = result["consequences"][0]
    assert common["result"] == "UNDETERMINED"
    assert common["warrant"]["status"] == "proposed"
    assert common["warrant"]["blockers"] == ["interpretation_scope_contrast"]
    contrast = common["contrast"]
    assert contrast["code"] == "interpretation_scope_contrast"
    assert contrast["context"]["cohort"] == "randomized-entry"
    assert [row["result"] for row in contrast["answers"]] == ["OUT_OF_SCOPE", "REFUTED"]
    assert result["refuted"] == result["incoherent"] == []
    for answer in contrast["answers"]:
        actual = pointer({"result": result}, answer["query_path"])
        assert actual["result"] == answer["result"]
        assert pointer({"result": result}, answer["warrant_path"])["status"] == "proposed"
        for deciding in answer["deciding_premises"]:
            assert pointer({"result": result}, deciding["path"])["cohort"] == deciding["cohort"]
    assert contrast["answers"][0]["deciding_premises"][0]["cohort"]["ref"] == "crossover"


def test_selected_out_of_scope_remains_unresolved_with_a_specific_next_scope_question():
    result = scope_case(selected="crossover-only")
    common = result["consequences"][0]
    assert common["result"] == "UNDETERMINED"
    assert common["warrant"]["blockers"] == ["selected_out_of_scope"]
    assert common["contrast"]["code"] == "selected_out_of_scope"
    assert [answer["frame"] for answer in common["contrast"]["answers"]] == ["crossover-only"]
    assert common["contrast"]["answers"][0]["result"] == "OUT_OF_SCOPE"


def test_rival_scope_answers_cannot_dilute_an_independently_settled_fixed_floor():
    adult = premise("adult", literal("ge", 18, "age", "years"), status="known")
    query = interpretations.Query("adult", literal("ge", 18, "age", "years"))
    result = scope_case(selected="crossover-only", fixed=(adult,), queries=(query,))
    common = result["consequences"][0]
    assert common["result"] == "ENTAILED" and common["warrant"]["status"] == "known"
    assert common["basis"] == "fixed_floor" and common["frames"] == []
    assert "contrast" not in common


def test_metadata_consumes_effects_and_contrasts_and_prefixes_every_child_link():
    coordinate_result = coordinates([evidence("setting_word", ["advanced_previously_treated"])])
    metadata = result_semantics.metadata("coordinates", coordinate_result)
    effect = next(row for row in metadata["findings"] if row["kind"] == "coordinate_effect")
    assert effect["effect"] == "no_consumer" and effect["disposition"] == "translation_question"
    assert effect["causes"] == [{"code": "coordinate_effect_no_consumer", "kind": "translation"}]
    child = {"operation": "interpretations", "result": scope_case()}
    child["metadata"] = result_semantics.metadata("interpretations", child["result"])
    analysis = {"analyses": [{"result": child}], "decisions": []}
    findings = result_semantics.metadata("design_session", analysis)["findings"]
    common = next(row for row in findings if row.get("contrast_code") == "interpretation_scope_contrast")
    assert common["causes"] == [{"code": "interpretation_scope_contrast", "kind": "translation"}]
    for path in [common["contrast_path"], *common["answer_paths"]]:
        assert pointer({"result": analysis}, path) is not None
    source = {"analyses": [child]}
    common = next(
        row
        for row in result_semantics.metadata("source_assertions", source)["findings"]
        if row.get("contrast_code") == "interpretation_scope_contrast"
    )
    for path in [common["contrast_path"], *common["answer_paths"]]:
        assert pointer({"result": source}, path) is not None


def test_neutral_coordinate_restriction_has_no_retraction_solve_and_preserves_full_choice(monkeypatch):
    calls = []
    original = coordinate_admission._coordinates

    def counted(known, interpolated):
        calls.append((len(known), len(interpolated)))
        return original(known, interpolated)

    monkeypatch.setattr(coordinate_admission, "_coordinates", counted)
    given = [
        evidence("setting", coherence.SETTINGS[index:] + coherence.SETTINGS[:index], ref=f"person:{index}")
        for index in range(len(coherence.SETTINGS))
    ]
    result = coordinates(given)
    assert calls == [(len(given), 0)]
    assert result["coordinates"]["setting"]["domain"] == coherence.SETTINGS
    assert all(effect["code"] == "redundant" and not effect["domain_deltas"] for effect in result["effects"])


def test_effects_are_invariant_to_input_order_without_assigning_unique_proofs():
    given = [
        evidence("extent", ["metastatic"], ref="source:extent"),
        evidence("setting_word", ["adjuvant"], ref="person:veto"),
        evidence("biomarker:KRAS", ["positive"], ref="source:KRAS"),
    ]
    expected = None
    for ordered in itertools.permutations(given):
        result = coordinates(list(ordered))
        by_ref = {
            row["ref"]: {key: value for key, value in row.items() if key not in ("index", "input_path")}
            for row in result["effects"]
        }
        if expected is None:
            expected = by_ref
        assert by_ref == expected
        assert all(
            row["comparison"] == "marginal_retraction_not_unique_proof_or_clinical_causality"
            for row in result["effects"]
        )


def test_scope_contrast_disappears_when_the_requested_cohort_matches_both_actual_restrictions():
    crossover = premise("crossover", literal("le", 2), cohort=a.Scope("cohort_ref", "crossover"))
    entry = premise("entry", literal("le", 2))
    frames = tuple(
        interpretations.Interpretation(item.id, item.id, "assistant", ("source:eligibility",), (item,))
        for item in (crossover, entry)
    )
    result = interpretations.resolve(
        "study:example",
        (),
        (),
        frames,
        (interpretations.Query("ECOG3", literal("eq", 3)),),
        context=entail.Context(cohort="crossover"),
    )
    common = result["consequences"][0]
    assert common["result"] == "REFUTED"
    assert common["warrant"]["status"] == "proposed"
    assert common["contrast"]["code"] == "none"
    assert common["warrant"]["blockers"] == []


def test_extensional_duplicates_share_only_domain_identity_not_ref_order_or_standing(monkeypatch):
    calls = []
    original = coordinate_admission._coordinates

    def counted(known, interpolated):
        calls.append((len(known), len(interpolated)))
        return original(known, interpolated)

    monkeypatch.setattr(coordinate_admission, "_coordinates", counted)
    given = [
        evidence("setting", ["advanced_previously_treated", "maintenance"], ref="source:A"),
        evidence("setting", ["maintenance", "advanced_previously_treated"], ref="source:B"),
    ]
    result = coordinates(given)
    assert calls == [(2, 0)]
    assert result["coordinates"]["setting"]["domain"] == ("advanced_previously_treated", "maintenance")
    assert [effect["code"] for effect in result["effects"]] == ["redundant", "redundant"]
    assert [row["evidence"]["values"] for row in result["admission"]] == [row["values"] for row in given]
    assert [row["ref"] for row in result["effects"]] == ["source:A", "source:B"]
    # Standing layers are not interchangeable: the known input independently narrows the known level.
    given[1]["standing"]["status"] = "interpolated"
    result = coordinates(given)
    assert result["effects"][0]["code"] == "narrowed"
    assert result["effects"][1]["code"] == "redundant"


def test_direct_coordinate_consumer_is_an_exact_finite_codebook_not_a_name_similarity_rule():
    for gene in ("EGFR", "ALK", "ROS1", "KRAS", "BRAF", "MET", "RET", "NTRK", "HER2"):
        assert coherence.direct_coordinate("biomarker:" + gene, "") == "selection:" + gene
        assert coherence.direct_coordinate("biomarker:" + gene.lower(), "") == ""
    assert coherence.direct_coordinate("setting_word", "advanced") == ""
    assert coherence.direct_coordinate("setting:maintenance", "") == ""
    assert coherence.direct_coordinate("prior_lines", "any_treatment") == ""


def test_inactive_proposal_fallbacks_do_not_appear_as_consumed_levels():
    result = coordinates([evidence("setting", ["advanced_previously_treated"])])
    assert result["coordinates"]["setting"]["proposals"] == []
    effect = result["effects"][0]
    assert effect["code"] == "narrowed"
    assert {delta["level"] for delta in effect["domain_deltas"]} == {"known", "interpolated"}
    assert all(consumer["kind"] == "direct_coordinate" for consumer in effect["consumers"])


def test_proposal_comparison_keeps_parent_fallback_when_only_full_snapshot_reports_it():
    result = coordinates([evidence("resection", ["resected"])])
    relation = "adjuvant_or_perioperative_when_resection_required"
    assert [row["relation"] for row in result["coordinates"]["setting"]["proposals"]] == [relation]
    assert coordinates([])["coordinates"]["setting"]["proposals"] == []
    deltas = result["effects"][0]["domain_deltas"]
    assert len(deltas) == 1 and deltas[0]["level"] == "proposal:" + relation
    assert deltas[0]["excluded_by_input"] == [
        value for value in coherence.SETTINGS if value not in ("adjuvant", "perioperative")
    ]
    assert deltas[0]["preserved_by_input"] == []


def test_proposal_comparison_keeps_parent_fallback_when_only_retracted_snapshot_reports_it():
    resection = evidence("resection", ["resected"], ref="source:resection")
    explicit = evidence("setting", ["adjuvant"], ref="person:setting")
    result = coordinates([resection, explicit])
    assert result["coordinates"]["setting"]["proposals"] == []
    assert len(coordinates([resection])["coordinates"]["setting"]["proposals"]) == 1
    deltas = result["effects"][1]["domain_deltas"]
    proposals = [row for row in deltas if row["level"] not in ("known", "interpolated")]
    assert proposals == [
        {
            "coordinate": "setting",
            "level": "proposal:adjuvant_or_perioperative_when_resection_required",
            "excluded_by_input": ["perioperative"],
            "preserved_by_input": [],
        }
    ]
