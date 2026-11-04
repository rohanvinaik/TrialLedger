"""Explicit public-example inventory and semantic views for invariant tests.

Only declared unordered collections are permuted. The views omit copied inputs,
proof selection and presentation order; interval endpoints and temporal paths are
never sorted. They do not certify factual correctness of supplied premises.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from TrialLedger.layer2 import run, service

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = tuple(operation for operation in service.OPERATIONS if operation != "describe")
ORDER_FIELDS = {
    "entailment": ("assertions",),
    "coordinates": ("evidence",),
    "corpus": ("trials",),
    "design_bounds": ("candidates", "observations", "signals", "bindings", "binding_uses"),
    "signals": ("signals", "bindings", "binding_uses"),
    "interpretations": ("interpretations", "bindings", "queries"),
    "source_assertions": ("interpretations", "anchors", "bindings", "queries"),
    # Session array order participates in immutable canonical revision identity.
    "design_session": (),
    # Variable order and tied witness enumeration are explicitly ordered inputs.
    "evidence_requests": (),
}
REQUEST_FIELDS = {
    "entailment": {"assertions", "query"},
    "coordinates": {"evidence"},
    "corpus": {"trials"},
    "design_bounds": {"candidates", "observations", "query"},
    "signals": {"signals"},
    "interpretations": {"fixed", "interpretations", "queries"},
    "source_assertions": {"study", "anchors", "interpretations", "queries"},
    "design_session": {"session", "previous"},
    "evidence_requests": {"candidates", "survivors", "variables", "survival_basis"},
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def json_value(value):
    return json.loads(encoded(value))


def runnable_objects(value):
    """Locate whole request objects in discovery, not strings or schema fragments."""
    found = []
    if isinstance(value, dict):
        if (
            isinstance(value.get("operation"), str)
            and value["operation"] in REQUEST_FIELDS
            and REQUEST_FIELDS[value["operation"]] <= value.keys()
            and (value["operation"] != "design_session" or isinstance(value["session"], dict))
            and "code" not in value
            and value["operation"] != "describe"
            and "discovery" not in value
            and set(value) != {"question", "operation", "read", "meaning"}
        ):
            # A whole public request is atomic. Its analysis declarations and
            # previous child requests are not separately advertised examples.
            return [value]
        for nested in value.values():
            found.extend(runnable_objects(nested))
    elif isinstance(value, (list, tuple)):
        for nested in value:
            found.extend(runnable_objects(nested))
    return found


def example_cases():
    """Cover saved request documents and every explicitly documented request slot."""
    cases = []
    assert set(OPERATIONS) <= ORDER_FIELDS.keys()
    assert set(OPERATIONS) <= REQUEST_FIELDS.keys()
    for path in sorted((ROOT / "examples").rglob("*.json")):
        value = json.loads(path.read_text())
        if isinstance(value, dict) and isinstance(value.get("operation"), str) and "code" not in value:
            cases.append((str(path.relative_to(ROOT)), value))
    full = run({"operation": "describe", "view": "full"})["result"]
    declared = list(full["examples"].items())
    declared += [("signal/" + key, value) for key, value in full["signal_examples"].items()]
    declared += [
        ("capability/" + key, value["request"]) for key, value in full["capability_examples"].items()
    ]
    declared += [
        ("worked/" + str(index), step["request"])
        for index, step in enumerate(full["worked_session"]["steps"])
    ]
    declared += [(key, full[key]) for key in ("exception_example", "binding_example")]
    represented = {encoded(request) for _, request in declared}
    located = {encoded(request) for request in runnable_objects(full)}
    assert located == represented, "A discovery request slot has no invariant-inventory policy"
    cases.extend(("describe/full/" + label, request) for label, request in declared)
    for operation in OPERATIONS:
        focus = run({"operation": "describe", "view": operation, "detail": "full"})["result"]
        requests = [("example", focus["example"])]
        requests += [
            (key, focus[key])
            for key in ("exception_example", "binding_example", "revision_example")
            if key in focus
        ]
        # Focused signals discovery also publishes all per-kind examples.
        requests += [("signal/" + key, value) for key, value in focus.get("signal_examples", {}).items()]
        requests += [
            ("capability/" + key, value["request"])
            for key, value in focus.get("capability_examples", {}).items()
        ]
        assert {encoded(request) for request in runnable_objects(focus)} == {
            encoded(request) for _, request in requests
        }, operation
        cases.extend(("describe/" + operation + "/" + label, request) for label, request in requests)
    assert all(request["operation"] in ORDER_FIELDS for _, request in cases), (
        "New operation needs an explicit invariant policy"
    )
    return cases


def permuted(request):
    changed = copy.deepcopy(request)
    for field in ORDER_FIELDS[request["operation"]]:
        if isinstance(changed.get(field), list):
            changed[field].reverse()
    if request["operation"] == "interpretations":
        for field in ("assertions", "signals"):
            if isinstance(changed.get("fixed", {}).get(field), list):
                changed["fixed"][field].reverse()
        for frame in changed["interpretations"]:
            for field in ("assumptions", "signals", "signal_claims", "binding_uses"):
                if isinstance(frame.get(field), list):
                    frame[field].reverse()
    if request["operation"] == "design_bounds":
        for candidate in changed["candidates"]:
            candidate.get("assertions", []).reverse()
            candidate.get("signal_claims", []).reverse()
    return changed


def decision(row):
    """A decision's answer/support/blockers, excluding which sufficient proof won."""
    return {key: json_value(row.get(key)) for key in ("result", "status", "blockers")}


def signal(row):
    return {
        key: json_value(row.get(key)) for key in ("code", "calculation_code", "status", "value", "blockers")
    }


def indexed(rows, projector):
    return {row["id"]: projector(row) for row in rows}


def query(row):
    return {
        "result": row["result"],
        "decision": decision(row.get("decision", {})),
        "standing": row.get("warrant", {}).get("status"),
        "blockers": sorted(row.get("warrant", {}).get("blockers", [])),
    }


def session_snapshot(snapshot):
    """Keep clinical consequences, local support and provenance, not selected proofs or hashes."""
    return {
        "target": json_value(snapshot["target"]),
        "effective_premises": indexed(
            snapshot["effective_premises"],
            lambda row: {
                key: json_value(row.get(key))
                for key in ("kind", "payload", "standing", "origin", "depends_on")
            },
        ),
        "dependency_graph": json_value(snapshot["dependency_graph"]),
        "analyses": indexed(
            snapshot["analyses"],
            lambda row: {
                "target": json_value(row["target"]),
                "dependencies": json_value(row["dependencies"]),
                "answer": semantic_view(row["result"]),
            },
        ),
        "decisions": indexed(
            snapshot["decisions"],
            lambda row: {
                **{
                    key: json_value(row.get(key))
                    for key in (
                        "question",
                        "target",
                        "coverage",
                        "selected",
                        "standing",
                        "origin",
                        "origin_refs",
                        "input_origins",
                        "code",
                        "open_alternatives",
                        "coverage_limit",
                    )
                },
                "alternatives": indexed(
                    row["alternatives"],
                    lambda option: {
                        **{
                            key: json_value(option.get(key))
                            for key in (
                                "label",
                                "analysis",
                                "query",
                                "code",
                                "feasibility_status",
                                "origin_refs",
                            )
                        },
                        "warrant": decision(option["warrant"] or {}),
                    },
                ),
                "distinctions": [
                    {
                        **{
                            key: json_value(check.get(key))
                            for key in (
                                "alternatives",
                                "dependencies",
                                "code",
                                "support_status",
                                "origin_refs",
                            )
                        },
                        "answer": semantic_view(check["result"]) if check["result"] is not None else None,
                    }
                    for check in row["distinctions"]
                ],
            },
        ),
        "limits": json_value(snapshot["limits"]),
        "limits_of_claim": json_value(snapshot["limits_of_claim"]),
    }


def semantic_view(response):
    """Operation-specific comparisons; never compare arbitrary sorted JSON trees."""
    if response["code"] != "complete":
        return {"code": response["code"], "problems": sorted(response["problems"])}
    operation, result = response["operation"], response["result"]
    if operation == "entailment":
        return decision(result["decision"])
    if operation == "signals":
        return indexed(result["signals"], signal)
    if operation == "coordinates":
        return {
            name: {
                "domain": sorted(row["domain"]),
                "state": row["state"],
                "interpolated_domain": sorted(row["interpolated"]["domain"]),
                "interpolated_state": row["interpolated"]["state"],
                "proposals": sorted(encoded(proposal) for proposal in row["proposals"]),
            }
            for name, row in result["coordinates"].items()
        }
    if operation == "corpus":
        # Pair presentation may reverse when input trial order reverses. Keep the
        # whole pair but canonicalize its two oriented trial/value endpoints.
        pairs = []
        for original in result["near_misses"]:
            pair = copy.deepcopy(original)
            if pair["a"] > pair["b"]:
                pair["a"], pair["b"] = pair["b"], pair["a"]
                for field in ("value", "sponsor", "year"):
                    pair[field + "_a"], pair[field + "_b"] = pair[field + "_b"], pair[field + "_a"]
            pairs.append(encoded(pair))
        return {
            "frequency": sorted(encoded(row) for row in result["frequency"]),
            "occupancy": sorted(encoded(row) for row in result["occupancy"]),
            "associations": sorted(encoded(row) for row in result["associations"]),
            "near_misses": sorted(pairs),
            "expectations": sorted(encoded(row) for row in result["expectations"]),
        }
    if operation == "design_bounds":
        return {
            "remaining": sorted(result["remaining"]),
            "consequence": decision(result["consequence"]),
            "candidates": indexed(
                result["candidates"],
                lambda row: {
                    "state": row["state"],
                    "standing": row.get("elimination_status"),
                    "query": decision(row["query_decision"]),
                    "observations": {
                        item["observation"]: {
                            "state": item["state"],
                            "support": item["support"],
                            "standing": item["status"],
                            "decision": decision(item["decision"]),
                        }
                        for item in row["observations"]
                    },
                },
            ),
        }
    if operation == "interpretations":
        return {
            "fixed": indexed(result["fixed"]["queries"], query),
            "interpretations": indexed(
                result["interpretations"],
                lambda row: {
                    "state": row["state"],
                    "queries": indexed(row["queries"], query),
                    "signals": indexed(row["signals"], signal),
                },
            ),
            "consequences": indexed(result["consequences"], query),
            "families": {
                key: sorted(result[key]) for key in ("remaining", "refuted", "incoherent", "unresolved")
            },
        }
    if operation == "source_assertions":
        return sorted(
            encoded(
                {
                    "query": child.get("query"),
                    "operation": child["operation"],
                    "answer": semantic_view(analysis),
                }
            )
            for child, analysis in zip(result["requests"], result["analyses"], strict=True)
        )
    if operation == "design_session":
        return {
            "current": session_snapshot(result),
            "previous": session_snapshot(response["previous_fresh"])
            if response["previous_fresh"] is not None
            else None,
            "diff": {
                key: [{"id": row["id"], "code": row["code"]} for row in rows]
                for key, rows in response["diff"].items()
            }
            if response["diff"] is not None
            else None,
            "work": json_value(response["work"]),
        }
    if operation == "evidence_requests":
        return {
            **{
                key: json_value(result[key])
                for key in (
                    "family",
                    "survivors",
                    "inconsistent",
                    "input_conflicts",
                    "representation",
                    "search",
                    "output",
                    "pairs",
                    "limits",
                )
            },
            "requests": [
                {
                    **{key: json_value(value) for key, value in row.items() if key != "checks"},
                    "checks": {
                        check["candidate"]: {
                            "verdict": check["verdict"],
                            "decision": decision(check["decision"]),
                        }
                        for check in row["checks"]
                    },
                }
                for row in result["requests"]
            ],
        }
    raise AssertionError("No semantic comparison policy for " + operation)


def literal(key, number=18, comparison="ge"):
    return {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant"},
        "predicate": {"class": "Predicate", "kind": "measurement", "key": key},
        "value": {
            "class": "Value",
            "kind": "quantity",
            "comparison": comparison,
            "number": number,
            "unit": "example-unit",
        },
    }


def assertion(identity, body, status="known"):
    return {
        "class": "ScopedAssertion",
        "id": identity,
        "criterion_ref": "invented:invariant-premise",
        "modality": "required",
        "body": copy.deepcopy(body),
        "status": status,
        "resolution": "resolved",
        "rule": {
            "class": "Rule",
            "id": "invented:invariant-rule",
            "version": "1",
            "warrants": ["invented:explicit-test-premise"],
        },
    }
