"""The bridge locates quotations without promoting clinical interpretations to facts."""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, interpretation_bindings, interpretations, signals
from TrialLedger.layer2 import source_assertions as bridge
from TrialLedger.layer2 import source_evidence as source


def study():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "maximumAge": "N/A",
                "eligibilityCriteria": "A or B, if C.",
                "sex": "ALL",
                "healthyVolunteers": False,
            },
        }
    }


def plain(item):
    return json.loads(a.canonical(item))


def assertion_model(value) -> a.ScopedAssertion:
    item = a.from_canonical(json.dumps(value))
    assert isinstance(item, a.ScopedAssertion)
    return item


def literal(key="A", **kwargs):
    return a.Literal(
        a.Subject("participant"), a.Predicate("condition_status", key), a.Value("boolean"), **kwargs
    )


def premise(body=None, **kwargs):
    values: dict[str, Any] = {
        "rule": a.Rule("caller-claims-known", "1"),
        "status": "known",
        "resolution": "resolved",
    }
    values.update(kwargs)
    return plain(
        a.ScopedAssertion(
            "reading", "unverified:caller-location", "required", literal() if body is None else body, **values
        )
    )


def request():
    raw = study()
    return {
        "operation": "source_assertions",
        "study": raw,
        "anchors": [
            {
                "id": "text",
                "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
                "digest": source.snapshot(raw)["digest"],
                "expected": "A or B, if C.",
            }
        ],
    }


def frame(assumptions=None):
    return {
        "id": "possible",
        "label": "One possible reading",
        "origin": "source",
        "basis": ["caller-asserts-truth"],
        "anchors": ["text"],
        "assumptions": [premise()] if assumptions is None else assumptions,
    }


@pytest.mark.parametrize(
    "present,value,code",
    [
        (False, "18 Years", "missing"),
        (True, None, "null"),
        (True, "", "empty"),
        (True, "N/A", "not_applicable"),
        (True, 18, "malformed"),
        (True, False, "malformed"),
        (True, "18.0 Years", "unsupported"),
        (True, "+18 Years", "unsupported"),
        (True, "-1 Years", "unsupported"),
        (True, "018 Years", "unsupported"),
        (True, "18 years", "unsupported"),
        (True, "18 Year", "unsupported"),
        (True, " 18 Years", "unsupported"),
        (True, "18 Years\n", "unsupported"),
        (True, "0 Days", "compiled"),
        (True, "18 Years", "compiled"),
    ],
)
def test_complete_age_field_admission_has_named_states(present, value, code):
    assert bridge.age_state(present, value) == code


def test_real_ipass_snapshot_age_is_only_registered_general_eligibility_fact():
    raw = json.loads(Path("tests/fixtures/ipass-registry.json").read_text())
    original = copy.deepcopy(raw)
    result = bridge.prepare({"operation": "source_assertions", "study": raw})
    assert result["source"]["nct"] == "NCT00322452"
    assert result["requests"] == [] and result["fixed"]["signals"] == []
    fixed = [assertion_model(row) for row in result["fixed"]["assertions"]]
    assert len(fixed) == 1 and fixed[0].status == "known"
    assert isinstance(fixed[0].body, a.Literal)
    assert fixed[0].body.value == a.Value("quantity", "ge", number=18, unit="Years")
    assert fixed[0].criterion_ref.endswith("#/protocolSection/eligibilityModule/minimumAge")
    assert fixed[0].rule is not None and fixed[0].rule.version == bridge.RULE_VERSION
    assert result["source"]["digest"] in fixed[0].criterion_ref
    rows = {row["address"].rsplit("/", 1)[-1]: row for row in result["coverage"]}
    assert rows["maximumAge"]["code"] == "missing"
    assert rows["eligibilityCriteria"]["code"] == "unresolved_retained"
    assert rows["healthyVolunteers"]["value"] is False
    assert raw == original
    result["coverage"][-1]["value"] = "changed output"
    assert raw == original


@pytest.mark.parametrize("value,code", [(None, "null"), ([], "malformed"), ("", "malformed")])
def test_missing_and_malformed_eligibility_parent_are_separate(value, code):
    raw = study()
    raw["protocolSection"]["eligibilityModule"] = value
    result = bridge.prepare({"operation": "source_assertions", "study": raw})
    assert result["fixed"]["assertions"] == []
    assert result["coverage"][0] == {
        "address": "/protocolSection/eligibilityModule",
        "code": code,
        "value": value,
    }
    del raw["protocolSection"]["eligibilityModule"]
    assert (
        bridge.prepare({"operation": "source_assertions", "study": raw})["coverage"][0]["code"] == "missing"
    )


def test_zero_age_unit_preservation_and_unsupported_upper_create_no_hidden_bound():
    raw = study()
    raw["protocolSection"]["eligibilityModule"].update(minimumAge="0 Days", maximumAge="99.5 Years")
    result = bridge.prepare({"operation": "source_assertions", "study": raw})
    assert len(result["fixed"]["assertions"]) == 1
    body = result["fixed"]["assertions"][0]["body"]
    assert body["value"]["number"] == 0 and body["value"]["unit"] == "Days"
    assert result["coverage"][1]["code"] == "unsupported"


def test_proposed_reading_retains_or_and_scope_time_actor_and_conditional_obligation():
    raw = request()
    time = a.TemporalScope(
        "before",
        "named_event",
        "dose",
        lower=0,
        upper=7,
        unit="Days",
        inclusivity="inclusive",
        certainty="explicit",
    )
    partner = a.Literal(
        a.Subject("partner"),
        a.Predicate("condition_status", "B"),
        a.Value("boolean"),
        polarity="negative",
        time=time,
        qualifiers=literal("Q"),
        evidence=(a.Evidence("record_field", "caller-invented"),),
    )
    body = a.AnyOf((literal(), a.AllOf((partner, literal("D")))))
    item = premise(
        body,
        applicability=literal("C"),
        cohort=a.Scope("cohort_ref", "cohort-A"),
        branch=a.Branch("any_of", (1,)),
    )
    raw["interpretations"] = [frame([item])]
    before = copy.deepcopy(raw)
    result = bridge.prepare(raw)
    prepared = assertion_model(result["interpretations"][0]["assumptions"][0])
    assert prepared.status == "proposed" and prepared.resolution == "resolved"
    assert prepared.rule is not None and prepared.rule.version == bridge.RULE_VERSION
    assert isinstance(prepared.body, a.AnyOf) and isinstance(prepared.body.parts[1], a.AllOf)
    prepared_partner = prepared.body.parts[1].parts[0]
    assert isinstance(prepared_partner, a.Literal)
    assert prepared_partner.subject.kind == "partner"
    assert prepared_partner.time is not None
    assert dataclasses.replace(prepared_partner.time, evidence=()) == time
    assert prepared.branch == a.Branch("any_of", (1,))
    assert prepared.cohort == a.Scope("cohort_ref", "cohort-A")
    assert isinstance(prepared.applicability, a.Literal)
    assert prepared.applicability.predicate.key == "C"
    assert "caller-invented" not in a.canonical(prepared)
    assert result["submitted"]["interpretations"] == before["interpretations"] and raw == before
    assert entail.decide((prepared,), literal()).result == "UNDETERMINED"
    assert "proposed_refused:reading" in entail.decide((prepared,), literal()).blockers


def test_located_text_does_not_admit_known_label_but_conditional_frame_can_compute():
    raw = request()
    raw["interpretations"] = [frame()]
    raw["queries"] = [{"id": "A", "body": plain(literal())}]
    result = bridge.prepare(raw)
    prepared = assertion_model(result["interpretations"][0]["assumptions"][0])
    ordinary = entail.decide((prepared,), literal())
    assert ordinary.result == "UNDETERMINED"
    resolved = interpretations.resolve(
        result["source"]["study_ref"],
        (),
        (),
        (interpretations.Interpretation("possible", "reading", "source", ("source-location",), (prepared,)),),
        (interpretations.Query("A", literal()),),
    )
    assert resolved["interpretations"][0]["queries"][0]["result"] == "ENTAILED"
    assert resolved["interpretations"][0]["queries"][0]["warrant"]["status"] == "proposed"
    assert result["requests"][0]["operation"] == "interpretations"


@pytest.mark.parametrize(
    "kwargs,blocker",
    [
        ({"rule": a.UNRESOLVED_RULE}, "unresolved_rule:reading"),
        ({"resolution": "unresolved"}, "unresolved_assertion:reading"),
    ],
)
def test_unresolved_derivation_or_resolution_never_becomes_usable_by_anchoring(kwargs, blocker):
    raw = request()
    raw["interpretations"] = [frame([premise(**kwargs)])]
    result = bridge.prepare(raw)
    item = assertion_model(result["interpretations"][0]["assumptions"][0])
    assumed = dataclasses.replace(item, status="interpolated")
    assert blocker in entail.decide((assumed,), literal()).blockers


def test_hydrated_queries_and_distinct_rival_namespaces_are_reusable_without_frames():
    raw = request()
    raw["anchors"].append(
        {
            "id": "age",
            "address": "/protocolSection/eligibilityModule/minimumAge",
            "digest": source.snapshot(raw["study"])["digest"],
            "expected": "18 Years",
        }
    )
    age = a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", "age"),
        a.Value("quantity", "ge", number=18, unit="Years"),
    )
    raw["queries"] = [{"id": "adult", "body": plain(age)}]
    result = bridge.prepare(raw)
    downstream = result["requests"][0]
    fixed = tuple(assertion_model(item) for item in downstream["assertions"])
    assert entail.decide(fixed, a.from_canonical(json.dumps(downstream["query"]))).result == "ENTAILED"
    raw["interpretations"] = [frame(), {**frame(), "id": "rival"}]
    assert len(bridge.prepare(raw)["interpretations"]) == 2


@pytest.mark.parametrize(
    "mutation,problem",
    [
        (lambda r: r.update(fixed={}), "unknown_fields"),
        (lambda r: r.update(expected_digest="wrong"), "source_digest_mismatch"),
        (lambda r: r.update(selected="possible"), "selected_without_interpretations"),
        (lambda r: r.update(interpretations=[{**frame(), "extra": True}]), "unknown_fields"),
        (lambda r: r.update(interpretations=[{**frame(), "anchors": []}]), "nonempty_list"),
        (lambda r: r.update(interpretations=[{**frame(), "anchors": ["text", "text"]}]), "duplicate_anchor"),
        (lambda r: r.update(interpretations=[{**frame(), "anchors": ["other"]}]), "unknown_anchor"),
        (lambda r: r.update(interpretations=[frame(), frame()]), "duplicate_id"),
        (lambda r: r.update(interpretations=[frame([premise(), premise()])]), "duplicate_id"),
        (lambda r: r.update(queries=[{"id": "x", "body": plain(literal())}] * 2), "duplicate_id"),
        (lambda r: r.update(bound=True), "invalid_resource_bound"),
        (lambda r: r.update(context={"arm": ""}), "nonempty_text"),
    ],
)
def test_inspection_alone_still_refuses_malformed_frames_and_queries(mutation, problem):
    raw = request()
    mutation(raw)
    with pytest.raises(source.BridgeError, match=problem):
        bridge.prepare(raw)


def test_local_signal_support_is_proposed_and_exact_hydration_never_establishes_alignment():
    raw = request()
    raw["study"]["count"] = "7"
    digest = source.snapshot(raw["study"])["digest"]
    raw["anchors"][0]["digest"] = digest
    raw["anchors"].append({"id": "count", "address": "/count", "digest": digest, "expected": "7"})
    reading = frame([])
    reading["anchors"].append("count")
    reading["signals"] = [
        {
            "id": "overlap",
            "kind": "overlap",
            "data": {
                "universe": "explicit-hypothesis",
                "alignment": "unresolved",
                "total": 10,
                "marginals": [
                    {
                        "ref": "A",
                        "universe": "explicit-hypothesis",
                        "lower": {"$source": "count", "as": "integer"},
                        "upper": 7,
                    },
                    {"ref": "B", "universe": "explicit-hypothesis", "lower": 6, "upper": 6},
                ],
            },
            "support": [{"id": "caller", "status": "known", "resolution": "resolved", "basis": ["fake"]}],
        }
    ]
    raw["interpretations"] = [reading]
    result = bridge.prepare(raw)
    item = result["interpretations"][0]["signals"][0]
    assert item["data"]["marginals"][0]["lower"] == 7
    assert item["data"]["alignment"] == "unresolved"
    assert item["support"][0]["status"] == "proposed"
    assert "fake" not in item["support"][0]["basis"]
    direct = signals.Signal(
        item["id"],
        item["kind"],
        item["data"],
        (signals.Support("caller", "proposed", "resolved", ("real-anchor",)),),
        {},
    )
    assert signals.evaluate(direct)["code"] == "unresolved"


def test_exact_span_hydrates_query_operand_without_certifying_the_query_meaning():
    raw = request()
    raw["anchors"].append(
        {
            "id": "age-number",
            "address": "/protocolSection/eligibilityModule/minimumAge",
            "digest": source.snapshot(raw["study"])["digest"],
            "expected": "18 Years",
            "span": {"start": 0, "end": 2, "text": "18"},
        }
    )
    body = plain(
        a.Literal(
            a.Subject("participant"),
            a.Predicate("measurement", "age"),
            a.Value("quantity", "ge", number=0, unit="Years"),
        )
    )
    body["value"]["number"] = {"$source": "age-number", "as": "integer"}
    raw["queries"] = [{"id": "age", "body": body}]
    result = bridge.prepare(raw)
    assert result["requests"][0]["query"]["value"]["number"] == 18
    assert raw["queries"][0]["body"]["value"]["number"] == {"$source": "age-number", "as": "integer"}


def test_prepared_binding_replaces_caller_truth_and_wrong_scope_remains_unresolved():
    raw = request()
    study_ref = source.snapshot(raw["study"])["study_ref"]
    scope = {"study": study_ref, "population": "ITT", "arm": "A", "time": "baseline", "version": "v1"}
    signal = {
        "id": "coverage",
        "kind": "population",
        "data": {
            "universe": "ITT",
            "alignment": "confirmed",
            "total": 100,
            "parent_ref": "ITT",
            "subset_relation": "confirmed",
            "subset": {"ref": "EFQ", "universe": "ITT", "lower": 70, "upper": 70},
        },
        "support": [{"id": "count", "status": "known", "resolution": "resolved", "basis": ["fake"]}],
    }
    reading = frame([])
    reading["signals"] = [signal]
    reading["binding_uses"] = [
        {"binding": "subset", "signal": "coverage", "scope": {**scope, "time": "week12"}}
    ]
    raw["interpretations"] = [reading]
    raw["bindings"] = [
        {
            "id": "subset",
            "kind": "population",
            "relation": "subset_of",
            "subjects": ["ITT", "EFQ"],
            "scope": scope,
            "sources": [{"ref": "fake", "version": "fake", "address": "/fake"}],
            "status": "known",
            "resolution": "resolved",
            "basis": ["fake"],
            "anchors": ["text"],
        }
    ]
    before = copy.deepcopy(raw)
    result = bridge.prepare(raw)
    prepared = result["bindings"][0]
    assert prepared["status"] == "proposed"
    assert prepared["sources"] == [result["anchors"][0]["source"]]
    assert prepared["scope"] == scope and prepared["resolution"] == "resolved"
    parsed = interpretation_bindings.parse_bindings(result["bindings"], study_ref)
    uses = interpretation_bindings.parse_uses(reading["binding_uses"], parsed, {"coverage"}, study_ref)
    evidence = signals.Signal(
        "coverage",
        "population",
        signal["data"],
        (signals.Support("count", "proposed", "resolved", ("anchor",)),),
        {},
    )
    checks = interpretation_bindings.check_uses(parsed, uses, (evidence,), study_ref)
    assert checks[0]["code"] == "unresolved" and checks[0]["status"] == "proposed"
    assert checks[0]["blockers"] == ["scope_mismatch:subset"]
    assert result["submitted"]["bindings"] == before["bindings"] and raw == before


def extra_age_anchor(raw):
    raw["anchors"].append(
        {
            "id": "other",
            "address": "/protocolSection/eligibilityModule/minimumAge",
            "digest": source.snapshot(raw["study"])["digest"],
            "expected": "18 Years",
        }
    )


def binding_declaration(raw):
    return {
        "id": "subset",
        "kind": "population",
        "relation": "subset_of",
        "subjects": ["ITT", "EFQ"],
        "scope": {
            "study": source.snapshot(raw["study"])["study_ref"],
            "population": "ITT",
            "arm": "A",
            "time": {"$source": "other", "as": "text"},
            "version": "v1",
        },
        "sources": [{"ref": "submitted", "version": "v1", "address": "/submitted"}],
        "status": "known",
        "resolution": "resolved",
        "basis": ["submitted"],
        "anchors": ["text"],
    }


def test_frame_hydration_cannot_use_undeclared_source_dependency():
    raw = request()
    extra_age_anchor(raw)
    reading = frame()
    reading["label"] = {"$source": "other", "as": "text"}
    raw["interpretations"] = [reading]
    before = copy.deepcopy(raw)
    with pytest.raises(source.BridgeError, match="unknown_ref:source_marker"):
        bridge.prepare(raw)
    assert raw == before
    reading["anchors"].append("other")
    result = bridge.prepare(raw)
    assert result["interpretations"][0]["label"] == "18 Years"
    assert result["anchors"][1]["ref"] in result["interpretations"][0]["basis"]
    assert result["submitted"]["interpretations"] == raw["interpretations"]


def test_binding_hydration_cannot_use_undeclared_source_dependency():
    raw = request()
    extra_age_anchor(raw)
    raw["bindings"] = [binding_declaration(raw)]
    before = copy.deepcopy(raw)
    with pytest.raises(source.BridgeError, match="unknown_ref:source_marker"):
        bridge.prepare(raw)
    assert raw == before
    raw["bindings"][0]["anchors"].append("other")
    result = bridge.prepare(raw)
    assert result["bindings"][0]["scope"]["time"] == "18 Years"
    assert result["anchors"][1]["ref"] in result["bindings"][0]["basis"]
    assert result["submitted"]["bindings"] == raw["bindings"]


def test_other_nih_sections_have_content_bound_uncompiled_root_references_not_duplicated_values():
    raw = json.loads(Path("tests/fixtures/ipass-registry.json").read_text())
    result = bridge.prepare({"operation": "source_assertions", "study": raw})
    rows = {row["address"]: row for row in result["coverage"]}
    for address in (
        "/resultsSection",
        "/derivedSection",
        "/hasResults",
        "/protocolSection/identificationModule",
        "/protocolSection/designModule",
    ):
        assert rows[address] == {
            "address": address,
            "ref": result["source"]["study_ref"] + "#" + address,
            "code": "unresolved_retained",
            "reason": "outside_structured_age_direct_rules",
        }
        assert "value" not in rows[address]


def test_inspection_total_budget_counts_frames_and_assumptions_together():
    raw = request()
    raw["interpretations"] = [{**frame(), "id": f"frame-{index}"} for index in range(500)]
    with pytest.raises(source.BridgeError, match="resource_bound:source_assertions"):
        bridge.prepare(raw)


def test_inspection_total_budget_counts_frame_and_binding_lists_before_parsing_them():
    raw = request()
    raw["interpretations"] = [{**frame([]), "id": f"frame-{index}"} for index in range(600)]
    raw["bindings"] = [None] * 400
    with pytest.raises(source.BridgeError, match="resource_bound:source_assertions"):
        bridge.prepare(raw)


def test_query_work_budget_counts_each_frame_and_fixed_floor_evaluation():
    raw = request()
    raw["interpretations"] = [{**frame([]), "id": f"frame-{index}"} for index in range(50)]
    raw["queries"] = [{"id": f"query-{index}", "body": plain(literal())} for index in range(20)]
    with pytest.raises(source.BridgeError, match="resource_bound:source_assertions"):
        bridge.prepare(raw)
