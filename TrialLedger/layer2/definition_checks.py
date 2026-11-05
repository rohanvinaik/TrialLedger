"""Explicit relations between attributed meanings at actual analysis addresses.

Addresses bind documentary objects; the person's typed reading supplies meaning.
Neither matching labels nor differing numbers supplies a clinical relation.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, source_evidence
from TrialLedger.layer2.signals import support_state

LIMIT = 32
RELATIONS = ("implies", "equivalent", "disjoint")
STANDING_FIELDS = {"status", "resolution", "basis"}
OPERAND_FIELDS = {"analysis", "address", "body", *STANDING_FIELDS}
# A protocol operand names a declared protocol check (and child) instead of an analysis (definitions.md).
PROTOCOL_OPERAND_FIELDS = {"protocol_check", "address", "body", *STANDING_FIELDS}


def _operand(raw: object, key: str, analyses: dict, protocol: dict | None) -> dict:
    if type(raw) is dict and "analysis" in raw and "protocol_check" in raw:
        raise ValueError("definition_operand_reference")
    if type(raw) is dict and "protocol_check" in raw:
        fields = set(raw)
        if fields - {"child"} != PROTOCOL_OPERAND_FIELDS:
            raise ValueError("invalid_fields:" + key)
        if protocol is None:
            raise ValueError("definition_protocol_requires_v2")
        if _text(raw["protocol_check"], key + ".protocol_check") not in protocol["checks"]:
            raise ValueError("definition_unknown_protocol_check")
        if "child" in raw and (type(raw["child"]) is not int or raw["child"] < 0):
            raise ValueError("definition_operand_reference")
        return raw
    operand = _object(raw, OPERAND_FIELDS, key)
    if _text(operand["analysis"], key + ".analysis") not in analyses:
        raise ValueError("definition_unknown_analysis")
    return operand


def _operand_target(operand: dict, analyses: dict, protocol: dict | None) -> dict:
    """`protocol` here is the admission index: a dict of declared checks keyed by id."""
    if "protocol_check" in operand and protocol is not None:
        return protocol["checks"][operand["protocol_check"]]["scope"]["target"]
    return analyses[operand["analysis"]]["target"]


def relation_result_code(results: list[str], blocked: bool) -> str:
    """A feasible counterexample refutes the declared relation, never the source (pure).

    post: __return__ in ('consistent', 'conflict', 'unresolved')
    post: not blocked or __return__ == 'unresolved'
    post: __return__ != 'consistent' or (bool(results) and all(x == 'ENTAILED' for x in results))
    """
    if (
        blocked
        or not results
        or any(result not in ("ENTAILED", "REFUTED", "UNDETERMINED") for result in results)
    ):
        return "unresolved"
    return "consistent" if all(result == "ENTAILED" for result in results) else "conflict"


def _object(raw: object, fields: set[str], where: str) -> dict:
    if type(raw) is not dict or set(raw) != fields:
        raise ValueError("definition_fields:" + where)
    return raw


def _text(raw: object, where: str) -> str:
    if type(raw) is not str or not raw:
        raise ValueError("definition_text_required:" + where)
    return raw


def _standing(raw: dict) -> None:
    if raw["status"] not in ("known", "interpolated", "proposed") or raw["resolution"] not in (
        "resolved",
        "partially_resolved",
        "unresolved",
        "conflicting",
    ):
        raise ValueError("definition_invalid_standing")
    basis = raw["basis"]
    if type(basis) is not list or not 1 <= len(basis) <= LIMIT:
        raise ValueError("definition_basis_required")
    for item in basis:
        _text(item, "basis")


def _body(raw: object) -> a.Proposition:
    value = a.from_canonical(json.dumps(raw, allow_nan=False))
    if not isinstance(value, a.PROPOSITIONS):
        raise ValueError("definition_not_proposition")
    return value


def prepare(raw: object, analyses: dict, protocol: dict | None = None) -> list[dict]:
    """Validate declarations without looking up future results or supplying meaning."""
    if type(raw) is not list or len(raw) > LIMIT:
        raise ValueError("definition_checks_limit_or_type")
    seen, out = set(), []
    for value in raw:
        row = _object(value, {"id", "relation", "left", "right", *STANDING_FIELDS}, "check")
        identity = _text(row["id"], "id")
        if identity in seen or row["relation"] not in RELATIONS:
            raise ValueError("definition_duplicate_or_unsupported_relation")
        seen.add(identity)
        _standing(row)
        for key in ("left", "right"):
            operand = _operand(row[key], key, analyses, protocol)
            address = _text(operand["address"], key + ".address")
            if address not in ("/request", "/result") and not address.startswith(("/request/", "/result/")):
                raise ValueError("definition_address_requires_request_or_result")
            _standing(operand)
            _body(operand["body"])
        targets = [_operand_target(row[key], analyses, protocol) for key in ("left", "right")]
        if not source_evidence.exact_json_equal(*targets):
            raise ValueError("definition_target_mismatch")
        out.append(deepcopy(row))
    return out


def _directions(row: dict) -> list[tuple[str, dict, dict]]:
    if row["relation"] == "equivalent":
        return [
            ("left_implies_right", row["left"], row["right"]),
            ("right_implies_left", row["right"], row["left"]),
        ]
    return [(row["relation"], row["left"], row["right"])]


def _source(operand: dict) -> str:
    """The exact computed address a reading is bound to: an analysis, or a protocol check child."""
    if "protocol_check" in operand:
        return f"protocol:{operand['protocol_check']}/{operand.get('child', 0)}#{operand['address']}"
    return operand["analysis"] + "#" + operand["address"]


def _request(identity: str, direction: str, left: dict, right: dict) -> dict:
    body, query = _body(left["body"]), _body(right["body"])
    if direction == "disjoint":
        query = a.Not(query)
    given = a.ScopedAssertion(
        "definition:" + identity + ":" + direction,
        _source(left),
        "required",
        body,
        rule=a.Rule("definition.declared_meaning", "1", warrants=tuple(left["basis"])),
        status=left["status"],
        resolution="resolved",
    )
    return {
        "operation": "entailment",
        "assertions": [json.loads(a.canonical(given))],
        "query": json.loads(a.canonical(query)),
    }


def _protocol_child(protocol: dict | None, operand: dict) -> dict | None:
    """The retained `{request, result}` of a replayed protocol check child, or None when absent."""
    checks = {row["id"]: row for row in (protocol or {}).get("checks", [])}
    children = checks.get(operand["protocol_check"], {}).get("children", [])
    index = operand.get("child", 0)
    if index >= len(children):
        return None
    child = children[index]
    return {"request": child["request"], "result": child["result"]}


def run(
    rows: list[dict],
    analyses: dict,
    execute: Callable[[dict], dict],
    protocol: dict | None = None,
    target: dict | None = None,
) -> list[dict]:
    """Bind actual outputs then freshly compute each accepted declared relation.

    `protocol` is the replayed protocol result (its `checks` rows carry retained children); `target` is the
    session target, which every protocol check has by admission.
    """
    output = []
    for row in rows:
        observed, blockers = {}, []
        for key in ("left", "right"):
            operand = row[key]
            if "protocol_check" in operand:
                analysis = _protocol_child(protocol, operand)
                if analysis is None:
                    # A missing child is a named translation refusal, never a guess.
                    blockers.append("definition_protocol_child_missing:" + operand["protocol_check"])
                    observed[key] = None
                    continue
                refused = "definition_protocol_child_refused:" + operand["protocol_check"]
            else:
                analysis = analyses[operand["analysis"]]
                refused = "definition_analysis_refused:" + operand["analysis"]
            # A missing address is a named translation refusal, never a guessed field.
            observed[key] = deepcopy(source_evidence._selected(analysis, operand["address"]))
            if analysis["result"].get("code") != "complete":
                blockers.append(refused)
            _, found = entail.proposition_formula(_body(operand["body"]))
            blockers.extend(found)
        references = [row, row["left"], row["right"]]
        gate = support_state([ref["status"] for ref in references], [ref["resolution"] for ref in references])
        if gate != "accepted":
            blockers.append("definition_" + gate)
        checks, results = [], []
        if not blockers:
            for direction, left, right in _directions(row):
                checked = execute(_request(row["id"], direction, left, right))
                checks.append({"direction": direction, **checked})
                envelope = checked["result"]
                if envelope.get("code") != "complete":
                    blockers.append("definition_computation_refused")
                    continue
                decision = envelope["result"]["decision"]
                results.append(decision["result"])
                blockers.extend(
                    value for value in decision["blockers"] if value != "undecided_by_constraints"
                )
                if decision["result"] == "INCONSISTENT":
                    blockers.append("definition_empty_antecedent:" + direction)
        code = relation_result_code(results, bool(blockers))
        output.append(
            {
                "id": row["id"],
                "relation": row["relation"],
                "code": code,
                "status": (
                    entail.weakest_status(tuple(ref["status"] for ref in references))
                    if gate == "accepted" and code != "unresolved"
                    else None
                ),
                "target": deepcopy(
                    analyses[row["left"]["analysis"]]["target"] if "analysis" in row["left"] else target
                ),
                "declaration": deepcopy(row),
                "observed": observed,
                "checks": checks,
                "blockers": sorted(set(blockers)),
                "basis": deepcopy(row["basis"]),
                "guarantee": "conditional_on_declared_meanings_and_relation_not_source_truth",
            }
        )
    return output
