"""Named session projections; exact representations, no clinical equivalence compiler."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import cast

from TrialLedger.layer2 import admission, source_evidence
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import session_state as state

IDENTITY_SLOTS = {
    "assertion": "assertions",
    "derived_assertion": "assertions",
    "source_assertion": "assertions",
    "signal": "signals",
    "binding": "bindings",
    "observation": "observations",
    "candidate": "candidates",
}
META_FIELDS = {
    "sponsor",
    "classes",
    "setting_domain",
    "class_unresolved",
    "eligibility_content",
    "coverage",
    "representation",
    "predicates",
    "start_year",
}


def _model(payload: dict, expected: type) -> object:
    item = a.from_canonical(state.canonical(payload))
    if not isinstance(item, expected):
        raise ValueError("projection_model_mismatch")
    return item


def weakest(values: list[dict], basis: list[str]) -> dict:
    """Combine declared actual support without verifying premise truth."""
    if not values:
        return {"status": "proposed", "resolution": "unresolved", "basis": basis}
    rank = {"known": 0, "interpolated": 1, "proposed": 2}
    status = max((v["status"] for v in values), key=rank.__getitem__)
    resolution = "resolved" if all(v["resolution"] == "resolved" for v in values) else "unresolved"
    if any(v["resolution"] == "conflicting" for v in values):
        resolution = "conflicting"
    return {"status": status, "resolution": resolution, "basis": basis}


def _declared(premise: dict, payload: dict) -> dict:
    kind = premise["kind"]
    basis = [premise["origin"]["ref"]]
    if kind in ("assertion", "derived_assertion", "source_assertion", "binding", "observation", "adoption"):
        return admission.read_standing(
            {
                "status": payload.get("status", "proposed"),
                "resolution": payload.get("resolution", "unresolved"),
                "basis": basis,
            },
            premise["id"],
        )
    if kind == "signal":
        vals = [
            admission.read_standing({k: row[k] for k in ("status", "resolution", "basis")}, premise["id"])
            for row in payload.get("support", [])
        ]
        return weakest(vals, basis)
    if kind == "coordinate_evidence":
        return admission.read_standing(payload["standing"], premise["id"])
    return {"status": "proposed", "resolution": "unresolved", "basis": basis}


def _weaken(node: object, support: dict) -> object:
    """Only an explicitly claimed premise dependency weakens its entire dependent object."""
    if isinstance(node, list):
        return [_weaken(v, support) for v in node]
    if not isinstance(node, dict):
        return node
    out = {key: _weaken(value, support) for key, value in node.items()}
    if "status" in node and "resolution" in node:
        combined = weakest(
            [{"status": node["status"], "resolution": node["resolution"]}, support], support["basis"]
        )
        out["status"] = combined["status"]
        out["resolution"] = combined["resolution"]
    return out


def _context_scope(context: dict) -> a.Scope:
    """A conclusion remains restricted to every fixed producer context dimension."""
    parts = tuple(a.Scope(key + "_ref", ref) for key, ref in context.items() if ref is not None)
    if not parts:
        return a.Scope("all_participants")
    return parts[0] if len(parts) == 1 else a.Scope("all_of", parts=parts)


def effective(premise: dict, prepared: dict, values: dict, analyses: dict) -> dict:
    """Materialize one premise after its support/producer dependencies have completed."""
    payload = deepcopy(premise["payload"])
    kind = premise["kind"]
    if kind == "source_assertion":
        state.obj(payload, {"source", "assertion"}, "source_assertion")
        if payload["source"] != premise["origin"]["source"]:
            raise ValueError("source_assertion_origin_mismatch")
        held = prepared["sources"].get(payload["source"])
        if held is None:
            raise ValueError("unknown_source:source_assertion")
        found = [v for v in held["compiled"]["fixed"]["assertions"] if v["id"] == payload["assertion"]]
        if len(found) != 1:
            raise ValueError("unknown_compiled_assertion")
        payload = deepcopy(found[0])
        if premise["origin"]["ref"] != payload["criterion_ref"]:
            raise ValueError("source_rule_reference_mismatch")
        payload["id"] = premise["id"]
    elif kind == "derived_assertion":
        produced = analyses[payload["analysis"]]
        request, result = produced["request"], produced["result"]
        if request["operation"] != "entailment" or not source_evidence.exact_json_equal(
            payload["query"], request["query"]
        ):
            raise ValueError("derived_query_identity_mismatch")
        if result["code"] != "complete":
            raise ValueError("derived_result_not_complete")
        decision = result["result"]["decision"]
        if (
            decision["result"] not in ("ENTAILED", "REFUTED")
            or admission.admission_code(decision["status"], "resolved", True) != "accepted"
        ):
            raise ValueError("derived_result_not_accepted")
        body = (
            payload["query"]
            if decision["result"] == "ENTAILED"
            else {"class": "Not", "part": payload["query"]}
        )
        payload = json.loads(
            a.canonical(
                a.ScopedAssertion(
                    premise["id"],
                    premise["origin"]["ref"],
                    "required",
                    cast(a.Proposition, a.from_canonical(state.canonical(body))),
                    cohort=_context_scope(request.get("context", {})),
                    rule=a.Rule(
                        "session-derived-entailment",
                        "1",
                        premises=tuple(decision["proof"]),
                        warrants=(produced["result_digest"],),
                    ),
                    status=decision["status"],
                    resolution="resolved",
                )
            )
        )
    elif kind == "assertion":
        _model(payload, a.ScopedAssertion)
        if payload["id"] != premise["id"]:
            raise ValueError("assertion_ledger_id_mismatch")
    elif kind == "coordinate_evidence":
        state.obj(payload, {"evidence", "standing"}, "coordinate_evidence")
        if type(payload["evidence"]) is not dict or "standing" in payload["evidence"]:
            raise ValueError("coordinate_standing_collision")
    own = _declared(premise, payload)
    if premise["origin"]["kind"] == "hypothesis" and kind != "candidate" and own["status"] != "proposed":
        raise ValueError("hypothesis_cannot_supply_fact")
    deps = [values[ref]["standing"] for ref in premise["depends_on"]]
    standing = weakest([own, *deps], [premise["origin"]["ref"], *premise["depends_on"]])
    if deps:
        payload = _weaken(payload, standing)
    return {
        "id": premise["id"],
        "kind": kind,
        "payload": payload,
        "standing": standing,
        "origin": deepcopy(premise["origin"]),
        "depends_on": list(premise["depends_on"]),
        "dependency_support": weakest(deps, list(premise["depends_on"])) if deps else None,
    }


def _without_evidence(node: object) -> object:
    if isinstance(node, dict):
        return {k: _without_evidence(v) for k, v in node.items() if k != "evidence"}
    if isinstance(node, list):
        return [_without_evidence(v) for v in node]
    return node


def feature(value: dict, projection: str, prepared: dict) -> tuple[str, dict]:
    """Project only documented source statements; exact representation, never semantic normalization."""
    payload = value["payload"]
    if projection == "registered_general_age_to_corpus":
        if value["kind"] != "source_assertion":
            raise ValueError("age_projection_requires_compiled_floor")
        criterion = payload["criterion_ref"].split("#", 1)[1]
        field = criterion.rsplit("/", 1)[-1]
        label = {"minimumAge": "minimum_age", "maximumAge": "maximum_age"}.get(field)
        if label is None or payload["rule"]["id"] != "ctg-structured-general-eligibility-age":
            raise ValueError("age_projection_requires_age_rule")
        literal = payload["body"]["value"]
        number = literal["number"]
        number_text = str(int(number)) if number == int(number) else str(number)
        element = f"inclusion:{label}={number_text}_{literal['unit']}"
    elif projection == "documented_assertion_to_corpus":
        if value["kind"] not in ("assertion", "source_assertion") or value["origin"]["kind"] not in (
            "source_rule",
            "source_interpretation",
        ):
            raise ValueError("corpus_statement_requires_documentary_origin")
        _model(payload, a.ScopedAssertion)
        if payload["modality"] not in ("required", "excluded"):
            raise ValueError("corpus_statement_requires_requirement")
        semantic = {
            key: _without_evidence(payload[key]) for key in ("modality", "body", "applicability", "cohort")
        }
        section = "inclusion" if payload["modality"] == "required" else "exclusion"
        element = section + ":assertion=" + state.canonical(semantic)
    else:
        raise ValueError("unsupported_corpus_feature_projection")
    return element, {
        "premise": value["id"],
        "projection": projection,
        "element": element,
        "standing": deepcopy(value["standing"]),
        "origin": deepcopy(value["origin"]),
        "typed_object": deepcopy(payload),
    }


def corpus_trial(value: dict, values: dict, prepared: dict) -> tuple[dict, list[dict]]:
    payload = value["payload"]
    source = prepared["sources"][payload["source"]]
    metadata = payload["metadata"]
    if type(metadata) is not dict or set(metadata) - META_FIELDS:
        raise ValueError("unsupported_corpus_metadata")
    sponsor = metadata.get("sponsor")
    if sponsor is None:
        sponsor = (
            source["study"]
            .get("protocolSection", {})
            .get("sponsorCollaboratorsModule", {})
            .get("leadSponsor", {})
            .get("name")
        )
    state.text(sponsor, "corpus.sponsor")
    features = []
    for use in payload["feature_uses"]:
        value_source = values[use["premise"]]["origin"]["source"]
        if value_source != payload["source"]:
            raise ValueError("corpus_feature_source_mismatch")
        features.append(feature(values[use["premise"]], use["projection"], prepared))
    elements = []
    support = {}
    ledger = []
    for element, record in features:
        if value["dependency_support"] is not None:
            record["standing"] = weakest(
                [record["standing"], value["dependency_support"]],
                [record["origin"]["ref"], *value["depends_on"]],
            )
        if element in support:
            # Multiple witnesses do not require all witnesses: retain strongest exact representation support.
            old = support[element]
            if admission.code(record["standing"]) == "accepted" and admission.code(old) != "accepted":
                support[element] = record["standing"]
        else:
            elements.append(element)
            support[element] = record["standing"]
        ledger.append(record)
    known = {
        "status": "known",
        "resolution": "resolved",
        "basis": [source["snapshot"]["study_ref"], "structural:represented-eligibility-object"],
    }
    item = {
        **deepcopy(metadata),
        "id": source["snapshot"]["nct"],
        "sponsor": sponsor,
        "stratum": payload["stratum"],
        "elements": elements,
        "typed": bool(elements),
        "basis": [source["snapshot"]["study_ref"], value["origin"]["ref"]],
        "standing": {"status": "proposed", "resolution": "unresolved", "basis": [value["origin"]["ref"]]},
        "feature_standings": {"elements": support, "typed": known},
    }
    return item, ledger


def _target_guard(value: dict, analysis: dict, prepared: dict) -> None:
    """All clinical projection channels preserve source target and explicit adoption boundaries."""
    kind = value["kind"]
    if value["origin"]["source"] is not None:
        held_source = prepared["sources"][value["origin"]["source"]]["snapshot"]["study_ref"]
        if analysis["target"]["kind"] == "historical" and analysis["target"]["scope"]["study"] != held_source:
            raise ValueError("historical_source_target_mismatch")
    if kind == "derived_assertion":
        producer = prepared["analyses"][value["origin"]["analysis"]]
        if producer["target"] != analysis["target"]:
            raise ValueError("derived_target_mismatch")
    restrictive = analysis["operation"] in (
        "entailment",
        "design_bounds",
        "interpretations",
        "coordinates",
    )
    if (
        analysis["target"]["kind"] == "new_trial"
        and restrictive
        and kind != "candidate"
        and value["origin"]["kind"] not in ("user_choice", "derived")
    ):
        raise ValueError("new_trial_requires_explicit_adoption")


def project(
    use: dict, analysis: dict, value: dict, prepared: dict, values: dict
) -> tuple[object, list[dict]]:
    """Validate one named channel and return an inspectable detached projection."""
    projection, slot = use["projection"], use["slot"]
    kind = value["kind"]
    if projection in ("identity", "coordinate_evidence_identity"):
        _target_guard(value, analysis, prepared)
    if projection == "identity":
        expected = IDENTITY_SLOTS.get(kind)
        if slot in ("fixed_assertions", "fixed_signals"):
            expected_slot = "assertions" if slot == "fixed_assertions" else "signals"
        else:
            expected_slot = slot
        if expected is None or expected != expected_slot:
            raise ValueError("identity_projection_kind_mismatch")
        return deepcopy(value["payload"]), []
    if projection == "coordinate_evidence_identity" and kind == "coordinate_evidence" and slot == "evidence":
        payload = value["payload"]
        return {**deepcopy(payload["evidence"]), "standing": deepcopy(value["standing"])}, []
    if projection == "corpus_trial" and kind == "corpus_trial" and slot == "trials":
        return corpus_trial(value, values, prepared)
    raise ValueError("unsupported_named_projection")
