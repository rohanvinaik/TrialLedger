"""Independent oracle for the finite_policy operator (packet C', interface v1).

Written from operators.md Packet C, contract C6 and verification V3. It never reads
TrialLedger/layer2/protocol_policies.py. The explorer is a breadth-first search over an
explicitly materialized (state, valuation) node graph with explicit edges. Literal evaluation
alone reuses entail._holds and entail.proposition_formula, plus the decision-table key and
domain helpers that turn literal JSON into scalars. No policy logic is shared with production.

Step one (no production import) reproduces every fixture expectation and checks the malformed
refusals with a small independent validator. Step two compares production against the oracle on
the fixtures and on deterministic random tiny models, and runs metamorphic checks. Step-two tests
import production lazily, so a missing module fails only those tests.
"""

import importlib
import itertools
import json
import random
from collections import deque
from pathlib import Path

import pytest

from TrialLedger.layer2 import decision_tables, entail

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "openspec"
    / "changes"
    / "connect-protocol-design-workflow"
    / "interface"
    / "fixtures"
    / "policy.json"
)
RESERVED = "policy_state"
CLAIM_NAMES = ("coverage", "exclusivity", "prohibition", "invariant", "termination")
DEFAULT_CLAIMS = ("coverage", "exclusivity", "prohibition", "invariant")
FAILING = {"gap", "competing", "violation", "not_established"}
MAX_WITNESS = 64
MAX_VALUATIONS = 4096
MAX_WORK = 1_000_000
RANDOM_SEED = 20261104
RANDOM_MODELS = 60
RULE_STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
WORST_RESOLUTION_ORDER = ("conflicting", "unresolved", "partially_resolved", "resolved")


# ----------------------------------------------------------------------------------------------------------
# JSON builders (mirror the fixture encoding; used only for the random tiny models)
# ----------------------------------------------------------------------------------------------------------


def bool_literal(key, positive=True):
    return {
        "class": "Literal",
        "evidence": [],
        "polarity": "positive" if positive else "negative",
        "predicate": {"class": "Predicate", "key": key, "kind": "measurement"},
        "qualifiers": {"class": "Always"},
        "subject": {"class": "Subject", "kind": "study_procedure", "referent": ""},
        "time": None,
        "value": {
            "class": "Value",
            "comparison": "eq",
            "inclusivity": "unspecified",
            "kind": "boolean",
            "members": [],
            "number": None,
            "unit": "",
            "upper": None,
        },
    }


def state_literal(state):
    literal = bool_literal(RESERVED, True)
    literal["value"] = {
        "class": "Value",
        "comparison": "eq",
        "inclusivity": "unspecified",
        "kind": "enum",
        "members": [state],
        "number": None,
        "unit": "",
        "upper": None,
    }
    return literal


def _rule(identity, status="known", resolution="resolved"):
    return {
        "ref": f"random:{identity}",
        "version": "1",
        "status": status,
        "resolution": resolution,
        "basis": ["random tiny model (oracle test)"],
    }


# ----------------------------------------------------------------------------------------------------------
# Oracle
# ----------------------------------------------------------------------------------------------------------


def _formula(raw):
    body = decision_tables._proposition(raw)
    formula, blockers = entail.proposition_formula(body)
    assert not blockers, blockers
    return formula


def _state_key():
    return next(iter(decision_tables._keys(decision_tables._proposition(state_literal("probe")))))


def _has_cycle(nodes, edges):
    """Iterative three-colour DFS over the explicit node graph."""
    colour = {}
    for root in nodes:
        if root in colour:
            continue
        colour[root] = 1
        stack = [(root, iter(edges.get(root, ())))]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                colour[node] = 2
                stack.pop()
                continue
            state = colour.get(child, 0)
            if state == 1:
                return True
            if state == 0:
                colour[child] = 1
                stack.append((child, iter(edges.get(child, ()))))
    return False


def _standing(rules):
    """Per-row standing (operators.md, Standing). Unaccepted rules are never known or interpolated."""
    if not rules:
        return "no_rule_support"
    statuses = {rule["status"] for rule in rules}
    if "proposed" in statuses:
        return "proposed_refused"
    if any(rule["resolution"] != "resolved" for rule in rules):
        return "NOT_ACCEPTED"
    return "known" if statuses == {"known"} else "interpolated"


def _envelope(rules):
    """Envelope support: weakest declared status and worst declared resolution."""
    if not rules:
        return None, None
    statuses = {rule["status"] for rule in rules}
    if "proposed" in statuses:
        status = "proposed"
    elif "interpolated" in statuses:
        status = "interpolated"
    else:
        status = "known"
    declared = {rule["resolution"] for rule in rules}
    resolution = next(level for level in WORST_RESOLUTION_ORDER if level in declared)
    return status, resolution


def oracle(data, claims=None):
    """Exhaustive explicit-graph reference result for one finite_policy model."""
    requested = (
        [dict(claim) for claim in claims]
        if claims is not None
        else [{"id": name, "claim": name, "witness_limit": MAX_WITNESS} for name in DEFAULT_CLAIMS]
    )
    states = list(data["states"])
    initial_set = set(data["initial"])
    initial = [state for state in states if state in initial_set]
    terminal = set(data["terminal"])
    transitions = [
        (t["id"], t["from"], t["to"], _formula(t["guard"]), tuple(t["actions"])) for t in data["transitions"]
    ]
    prohibitions = [
        (p["id"], p["state"], _formula(p["condition"]), frozenset(p["actions"]), p["rule"])
        for p in data["prohibitions"]
    ]
    invariants = [(i["id"], i["state"], _formula(i["condition"]), i["rule"]) for i in data["invariants"]]
    constraints = [(c["id"], _formula(c["condition"]), c["rule"]) for c in data["constraints"]]

    domain_choices = decision_tables._domain_options(data["variables"])
    valuations = [{key: value for _, key, value, _ in combo} for combo in itertools.product(*domain_choices)]
    state_key = _state_key()

    def assignment(index, state):
        return {**valuations[index], state_key: state}

    # F(s): valuations satisfying every constraint when the policy state is s.
    feasible = {
        state: [
            index
            for index in range(len(valuations))
            if all(entail._holds(formula, assignment(index, state)) for _, formula, _ in constraints)
        ]
        for state in states
    }

    constraint_ids = [identity for identity, _, _ in constraints]
    prohibition_ids = [p[0] for p in prohibitions]
    invariant_ids = [i[0] for i in invariants]
    envelope_rules = (
        [rule for _, _, rule in constraints] + [p[4] for p in prohibitions] + [i[3] for i in invariants]
    )
    envelope_ids = constraint_ids + prohibition_ids + invariant_ids
    work_reserved = len(states) * len(valuations) * (
        len(constraints) + len(prohibitions) + len(invariants)
    ) + len(valuations) * len(transitions)

    init_nodes = [(state, index) for state in initial for index in feasible[state]]
    if not init_nodes:
        return _inconsistent(
            requested, constraints, prohibitions, invariants, envelope_ids, envelope_rules, work_reserved
        )

    enabled_cache = {}

    def enabled(node):
        if node not in enabled_cache:
            state, index = node
            enabled_cache[node] = [
                t for t in transitions if t[1] == state and entail._holds(t[3], assignment(index, state))
            ]
        return enabled_cache[node]

    seen = set(init_nodes)
    queue = deque(init_nodes)
    order = []
    edges = {}
    gaps = []
    competing = []
    prohibition_hits = 0
    invariant_hits = []
    conflict_ids = set()
    while queue:
        node = queue.popleft()
        order.append(node)
        state, index = node
        here = enabled(node)
        successors = []
        if state not in terminal:
            if not here:
                gaps.append(node)
            if len(here) > 1:
                competing.append(node)
        for transition in here:
            target = transition[2]
            if not feasible[target]:
                conflict_ids.add(transition[0])
                continue
            for successor_index in feasible[target]:
                successor = (target, successor_index)
                successors.append(successor)
                if successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
        edges[node] = successors
        for prohibition in prohibitions:
            p_state, p_formula, p_actions = prohibition[1], prohibition[2], prohibition[3]
            if p_state not in (None, state):
                continue
            for transition in here:
                if set(transition[4]) & p_actions and entail._holds(p_formula, assignment(index, state)):
                    prohibition_hits += 1
        for invariant in invariants:
            i_state, i_formula = invariant[1], invariant[2]
            if i_state in (None, state) and not entail._holds(i_formula, assignment(index, state)):
                invariant_hits.append((node, invariant[0]))

    reached = {state for state, _ in order}
    conflicts = [t[0] for t in transitions if t[0] in conflict_ids]
    has_cycle = _has_cycle(order, edges)
    reasons = []
    if has_cycle:
        reasons.append("reachable_cycle")
    if gaps:
        reasons.append("dead_end")
    if conflicts:
        reasons.append("transition_target_infeasible")
    reasons = sorted(reasons)

    rows = {}
    for claim in requested:
        kind = claim["claim"]
        limit = claim["witness_limit"]
        reason_list = []
        if kind == "coverage":
            count = len(gaps)
            outcome = "gap" if count else "covered"
            determining = constraint_ids
            rules = [rule for _, _, rule in constraints]
        elif kind == "exclusivity":
            count = len(competing)
            outcome = "competing" if count else "exclusive"
            determining = constraint_ids
            rules = [rule for _, _, rule in constraints]
        elif kind == "prohibition":
            count = prohibition_hits
            outcome = "not_declared" if not prohibitions else ("violation" if count else "clear")
            determining = constraint_ids + prohibition_ids
            rules = [rule for _, _, rule in constraints] + [p[4] for p in prohibitions]
        elif kind == "invariant":
            count = len(invariant_hits)
            outcome = "not_declared" if not invariants else ("violation" if count else "holds")
            determining = constraint_ids + invariant_ids
            rules = [rule for _, _, rule in constraints] + [i[3] for i in invariants]
        else:  # termination
            count = len(reasons)
            reason_list = reasons
            outcome = "not_established" if reasons else "all_paths_terminate"
            determining = constraint_ids
            rules = [rule for _, _, rule in constraints]
        rows[claim["id"]] = {
            "claim": kind,
            "outcome": outcome,
            "violations_found": count,
            "witnesses_returned": min(limit, count),
            "witnesses_omitted": count - min(limit, count),
            "reasons": reason_list,
            "standing": _standing(rules),
            "determining_ids": determining,
        }

    failing = [row for row in rows.values() if row["outcome"] in FAILING]
    code = "violated" if (failing or conflicts) else "satisfied"
    blockers = sorted(
        [f"policy_{row['outcome']}:{claim_id}" for claim_id, row in rows.items() if row["outcome"] in FAILING]
        + [f"policy_transition_target_infeasible:{identity}" for identity in conflicts]
    )
    return {
        "code": code,
        "blockers": blockers,
        "support_status": _envelope(envelope_rules)[0],
        "support_resolution": _envelope(envelope_rules)[1],
        "determining_ids": envelope_ids,
        "reachability": {
            "initial_nodes": len(init_nodes),
            "reachable_nodes": len(order),
            "reachable_states": [state for state in states if state in reached],
            "unreachable_states": [state for state in states if state not in reached],
        },
        "transition_conflicts": conflicts,
        "claims": rows,
        "work_reserved": work_reserved,
    }


def _kind_support(kind, constraints, prohibitions, invariants):
    """determining_ids and rules a claim row rests on: constraints, plus its own kind of obligation."""
    determining = [identity for identity, _, _ in constraints]
    rules = [rule for _, _, rule in constraints]
    if kind == "prohibition":
        determining += [p[0] for p in prohibitions]
        rules += [p[4] for p in prohibitions]
    elif kind == "invariant":
        determining += [i[0] for i in invariants]
        rules += [i[3] for i in invariants]
    return determining, rules


def _inconsistent(
    requested, constraints, prohibitions, invariants, envelope_ids, envelope_rules, work_reserved
):
    rows = {}
    for claim in requested:
        kind = claim["claim"]
        determining, rules = _kind_support(kind, constraints, prohibitions, invariants)
        rows[claim["id"]] = {
            "claim": kind,
            "outcome": "inconsistent_domain",
            "violations_found": 0,
            "witnesses_returned": 0,
            "witnesses_omitted": 0,
            "reasons": [],
            "standing": _standing(rules),
            "determining_ids": determining,
        }
    return {
        "code": "inconsistent_domain",
        "blockers": ["policy_inconsistent_domain"],
        "support_status": _envelope(envelope_rules)[0],
        "support_resolution": _envelope(envelope_rules)[1],
        "determining_ids": envelope_ids,
        "reachability": None,
        "transition_conflicts": [],
        "claims": rows,
        "work_reserved": work_reserved,
    }


# ----------------------------------------------------------------------------------------------------------
# Independent validator for the malformed refusal fixtures (step one)
# ----------------------------------------------------------------------------------------------------------


def _literals(node):
    if isinstance(node, dict):
        if node.get("class") == "Literal":
            yield node
        for value in node.values():
            yield from _literals(value)
    elif isinstance(node, list):
        for value in node:
            yield from _literals(value)


def detected_defects(data, claims):
    """Every refusal code whose defect this validator finds in the input (no ordering assumed)."""
    found = set()
    expected_fields = {
        "scope",
        "version",
        "variables",
        "constraints",
        "states",
        "initial",
        "terminal",
        "actions",
        "transitions",
        "prohibitions",
        "invariants",
    }
    if set(data) != expected_fields:
        found.add("policy_data_fields")
    states = data["states"]
    state_set = set(states)
    declared_keys = set()
    product = 1
    for variable in data["variables"]:
        product *= len(variable["values"])
        for value in variable["values"]:
            key = value["predicate"]["key"]
            if key == RESERVED:
                found.add("policy_reserved_variable")
            declared_keys.add(key)
    if product > MAX_VALUATIONS:
        found.add("policy_valuation_limit")
    for literal in _literals(data):
        key = literal["predicate"]["key"]
        if key == RESERVED:
            if any(member not in state_set for member in literal["value"]["members"]):
                found.add("policy_unknown_state")
        elif key not in declared_keys:
            found.add("policy_undeclared_variable")
    if len(set(states)) != len(states) or any(not s for s in states):
        found.add("policy_invalid_states")
    initial = data["initial"]
    if not initial or len(set(initial)) != len(initial) or not set(initial) <= state_set:
        found.add("policy_invalid_initial")
    terminal = data["terminal"]
    if len(set(terminal)) != len(terminal) or not set(terminal) <= state_set:
        found.add("policy_invalid_terminal")
    action_ids = [a["id"] for a in data["actions"]]
    action_set = set(action_ids)
    if len(action_set) != len(action_ids):
        found.add("policy_duplicate_id")
    for action in data["actions"]:
        scope = action["scope"]
        if scope["level"] not in {"participant", "cohort", "study"} or not scope["ref"]:
            found.add("policy_invalid_action")
    terminal_set = set(terminal)
    transition_ids = [t["id"] for t in data["transitions"]]
    if len(set(transition_ids)) != len(transition_ids):
        found.add("policy_duplicate_id")
    for transition in data["transitions"]:
        if transition["from"] not in state_set or transition["to"] not in state_set:
            found.add("policy_unknown_state")
        if transition["from"] in terminal_set:
            found.add("policy_terminal_outgoing")
        if any(action not in action_set for action in transition["actions"]):
            found.add("policy_unknown_action")
    for prohibition in data["prohibitions"]:
        if prohibition["state"] is not None and prohibition["state"] not in state_set:
            found.add("policy_unknown_state")
        if any(action not in action_set for action in prohibition["actions"]):
            found.add("policy_unknown_action")
        found.update(_rule_defects(prohibition["rule"]))
    for invariant in data["invariants"]:
        if invariant["actions"]:
            found.add("policy_invariant_actions")
        found.update(_rule_defects(invariant["rule"]))
    for constraint in data["constraints"]:
        found.update(_rule_defects(constraint["rule"]))
    all_ids = [c["id"] for c in data["constraints"]] + [p["id"] for p in data["prohibitions"]]
    all_ids += [i["id"] for i in data["invariants"]]
    if len(set(all_ids)) != len(all_ids):
        found.add("policy_duplicate_id")
    if claims is not None:
        if not claims:
            found.add("policy_invalid_claims")
        names = [c["claim"] for c in claims]
        if len(set(c["id"] for c in claims)) != len(claims) or len(set(names)) != len(names):
            found.add("policy_duplicate_claim")
        for claim in claims:
            limit = claim["witness_limit"]
            if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= MAX_WITNESS:
                found.add("policy_invalid_claims")
    return found


def _rule_defects(rule):
    defects = set()
    if rule.get("status") not in RULE_STATUSES or rule.get("resolution") not in RESOLUTIONS:
        defects.add("policy_invalid_rule")
    if not rule.get("basis"):
        defects.add("policy_invalid_rule")
    return defects


# ----------------------------------------------------------------------------------------------------------
# Deterministic random tiny models (step two)
# ----------------------------------------------------------------------------------------------------------


def _random_formula(rng, keys, states, depth):
    roll = rng.random()
    if depth == 0 or roll < 0.35:
        if rng.random() < 0.2:
            return state_literal(rng.choice(states))
        return bool_literal(rng.choice(keys), rng.random() < 0.5)
    if roll < 0.55:
        return {"class": "Not", "part": _random_formula(rng, keys, states, depth - 1)}
    op = "AllOf" if roll < 0.78 else "AnyOf"
    return {"class": op, "parts": [_random_formula(rng, keys, states, depth - 1) for _ in range(2)]}


def _rule_for(rng, identity):
    status = "proposed" if rng.random() < 0.15 else rng.choice(["known", "known", "interpolated"])
    roll = rng.random()
    if roll < 0.6:
        resolution = "resolved"
    elif roll < 0.75:
        resolution = "partially_resolved"
    elif roll < 0.9:
        resolution = "unresolved"
    else:
        resolution = "conflicting"
    return _rule(identity, status, resolution)


def random_model(rng, index):
    variable_count = rng.randint(1, 2)
    keys = [f"p{j}" for j in range(variable_count)]
    variables = [
        {"id": f"v{j}", "values": [bool_literal(key, True), bool_literal(key, False)]}
        for j, key in enumerate(keys)
    ]
    count = rng.randint(2, 4)
    states = [f"s{j}" for j in range(count)]
    initial_pick = set(rng.sample(states, rng.randint(1, count)))
    terminal_pick = set(rng.sample(states, rng.randint(0, count - 1)))
    initial = [s for s in states if s in initial_pick]
    terminal = [s for s in states if s in terminal_pick]
    nonterminal = [s for s in states if s not in terminal_pick]
    actions = [
        {"id": f"a{j}", "scope": {"level": "cohort", "ref": "draft:random"}, "description": f"action {j}"}
        for j in range(rng.randint(1, 3))
    ]
    action_ids = [a["id"] for a in actions]
    transitions = []
    for j in range(rng.randint(1, 5)):
        transitions.append(
            {
                "id": f"t{j}",
                "from": rng.choice(nonterminal),
                "to": rng.choice(states),
                "guard": _random_formula(rng, keys, states, 2),
                "actions": rng.sample(action_ids, rng.randint(1, len(action_ids))),
            }
        )
    constraints = []
    if rng.random() < 0.3:
        constraints.append(
            {
                "id": "c0",
                "condition": _random_formula(rng, keys, states, 1),
                "rule": _rule_for(rng, f"{index}:c0"),
            }
        )
    if rng.random() < 0.35:
        # POL-7 pattern: no valuation is feasible in one state, so a transition into it is a target conflict.
        dead = rng.choice(states)
        lit = bool_literal(rng.choice(keys), True)
        for identity, body in (("c-dead-a", lit), ("c-dead-b", {"class": "Not", "part": lit})):
            constraints.append(
                {
                    "id": identity,
                    "condition": {
                        "class": "AnyOf",
                        "parts": [{"class": "Not", "part": state_literal(dead)}, body],
                    },
                    "rule": _rule_for(rng, f"{index}:{identity}"),
                }
            )
        if rng.random() < 0.7:
            transitions.append(
                {
                    "id": f"t{len(transitions)}",
                    "from": rng.choice(nonterminal),
                    "to": dead,
                    "guard": _random_formula(rng, keys, states, 1),
                    "actions": [rng.choice(action_ids)],
                }
            )
    prohibitions = []
    if rng.random() < 0.3:
        prohibitions.append(
            {
                "id": "q0",
                "state": rng.choice([None] + states),
                "condition": _random_formula(rng, keys, states, 1),
                "actions": rng.sample(action_ids, rng.randint(1, len(action_ids))),
                "rule": _rule_for(rng, f"{index}:q0"),
            }
        )
    invariants = []
    if rng.random() < 0.25:
        invariants.append(
            {
                "id": "i0",
                "state": rng.choice([None] + states),
                "condition": _random_formula(rng, keys, states, 1),
                "actions": [],
                "rule": _rule_for(rng, f"{index}:i0"),
            }
        )
    names = rng.sample(CLAIM_NAMES, rng.randint(1, 5))
    claims = [{"id": name, "claim": name, "witness_limit": rng.randint(0, 3)} for name in names]
    data = {
        "scope": f"draft:random-{index}",
        "version": "interface-v1",
        "variables": variables,
        "constraints": constraints,
        "states": states,
        "initial": initial,
        "terminal": terminal,
        "actions": actions,
        "transitions": transitions,
        "prohibitions": prohibitions,
        "invariants": invariants,
    }
    return data, claims


def random_models():
    rng = random.Random(RANDOM_SEED)
    return [random_model(rng, index) for index in range(RANDOM_MODELS)]


def _fixture():
    return json.loads(FIXTURE_PATH.read_text())


def _fixture_cases():
    return _fixture()["cases"]


def _production_module():
    return importlib.import_module("TrialLedger.layer2.protocol_policies")


def _compare_to_oracle(result, expected, label):
    """Compare a production result envelope against the oracle result for the same input."""
    assert result["code"] == expected["code"], label
    assert sorted(result["blockers"]) == expected["blockers"], label
    assert result.get("support_status") == expected["support_status"], label
    assert result.get("support_resolution") == expected["support_resolution"], label
    assert result.get("determining_ids") == expected["determining_ids"], label
    value = result["value"]
    if expected["reachability"] is not None:
        reach = value["reachability"]
        for key, want in expected["reachability"].items():
            assert reach[key] == want, (label, key)
    produced_conflicts = sorted({c["transition"] for c in value["transition_target_conflicts"]})
    assert produced_conflicts == sorted(expected["transition_conflicts"]), label
    rows = {row["id"]: row for row in value["claims"]}
    assert set(rows) == set(expected["claims"]), label
    for claim_id, want in expected["claims"].items():
        row = rows[claim_id]
        where = (label, claim_id)
        assert row["outcome"] == want["outcome"], where
        assert row["violations_found"] == want["violations_found"], where
        assert len(row["witnesses"]) == want["witnesses_returned"], where
        assert row["reasons"] == want["reasons"], where
        if want["standing"] == "NOT_ACCEPTED":
            assert row["standing"] in {"proposed_refused", "binding_unresolved", "missing_support"}, where
        else:
            assert row["standing"] == want["standing"], where
        assert row["determining_ids"] == want["determining_ids"], where
    assert value["work"]["reserved"] == expected["work_reserved"], label
    assert value["work"]["used"] <= value["work"]["reserved"], label


# ----------------------------------------------------------------------------------------------------------
# Step one: oracle versus fixture expectations (no production import)
# ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", _fixture_cases(), ids=[c["id"] for c in _fixture_cases()])
def test_oracle_reproduces_fixture_expectations(case):
    expected = case["expect"]
    got = oracle(case["data"], case["claims"])
    assert got["code"] == expected["code"]
    if "support_status" in expected:
        assert got["support_status"] == expected["support_status"]
    if "support_resolution" in expected:
        assert got["support_resolution"] == expected["support_resolution"]
    if "determining_ids" in expected:
        assert got["determining_ids"] == expected["determining_ids"]
    if "reachability" in expected:
        for key, want in expected["reachability"].items():
            assert got["reachability"][key] == want, key
    if "transition_target_conflicts" in expected:
        assert got["transition_conflicts"] == expected["transition_target_conflicts"]
    for claim_id, want in expected["claims"].items():
        row = got["claims"][claim_id]
        assert row["outcome"] == want["outcome"], claim_id
        assert row["violations_found"] == want["violations_found"], claim_id
        assert row["witnesses_returned"] == want["witnesses_returned"], claim_id
        assert row["reasons"] == want["reasons"], claim_id
        if "standing" in want:
            assert row["standing"] == want["standing"], claim_id


@pytest.mark.parametrize("case", _fixture()["malformed"], ids=[m["id"] for m in _fixture()["malformed"]])
def test_oracle_validator_detects_named_refusal(case):
    detected = detected_defects(case["data"], case["claims"])
    assert case["refusal"] in detected, (case["id"], sorted(detected))


def test_oracle_validator_accepts_every_valid_fixture_case():
    for case in _fixture_cases():
        assert detected_defects(case["data"], case["claims"]) == set(), case["id"]


def test_random_models_cover_the_mandatory_oracle_cases():
    """Terminal, dead-end, cycle, infeasible-target and violation cases are exercised, not assumed."""
    seen = set()
    for data, claims in random_models():
        result = oracle(data, claims)
        seen.add(result["code"])
        if result["transition_conflicts"]:
            seen.add("transition_target_infeasible")
        for row in result["claims"].values():
            if row["claim"] == "termination":
                seen.update(row["reasons"])
            if row["claim"] == "coverage" and row["outcome"] == "gap":
                seen.add("gap")
            if row["claim"] == "exclusivity" and row["outcome"] == "competing":
                seen.add("competing")
            if row["outcome"] in {"violation", "holds", "clear"}:
                seen.add(row["outcome"])
    required = {
        "violated",
        "satisfied",
        "inconsistent_domain",
        "transition_target_infeasible",
        "reachable_cycle",
        "dead_end",
        "gap",
        "competing",
        "violation",
        "clear",
        "holds",
    }
    assert required <= seen, sorted(required - seen)


def test_oracle_random_models_are_valid_by_the_oracle_validator():
    for index, (data, claims) in enumerate(random_models()):
        assert detected_defects(data, claims) == set(), index


# ----------------------------------------------------------------------------------------------------------
# Step two: production comparisons (lazy import; fails until protocol_policies exists)
# ----------------------------------------------------------------------------------------------------------


def _claims_for(case):
    if case["claims"] is not None:
        return case["claims"]
    return [{"id": name, "claim": name, "witness_limit": MAX_WITNESS} for name in DEFAULT_CLAIMS]


def test_production_matches_oracle_on_every_fixture_case():
    module = _production_module()
    for case in _fixture_cases():
        claims = (
            case["claims"]
            if case["claims"] is not None
            else [{"id": name, "claim": name, "witness_limit": MAX_WITNESS} for name in DEFAULT_CLAIMS]
        )
        result = module.check("finite_policy", case["data"], claims)
        expected = oracle(case["data"], claims)
        _compare_to_oracle(result, expected, case["id"])


def test_production_matches_oracle_on_random_tiny_models():
    module = _production_module()
    models = random_models()
    assert len(models) >= 40
    for index, (data, claims) in enumerate(models):
        result = module.check("finite_policy", data, claims)
        expected = oracle(data, claims)
        _compare_to_oracle(result, expected, f"random-{RANDOM_SEED}-{index}")


def test_production_work_reservation_matches_the_contract_formula():
    module = _production_module()
    for case in _fixture_cases():
        expected = oracle(case["data"], case["claims"])
        assert module.work_reservation(case["data"]) == expected["work_reserved"], case["id"]
        assert expected["work_reserved"] <= MAX_WORK, case["id"]
    for index, (data, _claims) in enumerate(random_models()):
        assert module.work_reservation(data) == oracle(data, None)["work_reserved"], index


def test_evaluate_is_check_with_the_four_default_claims():
    module = _production_module()
    defaults = [{"id": name, "claim": name, "witness_limit": MAX_WITNESS} for name in DEFAULT_CLAIMS]
    for case in _fixture_cases():
        if case["claims"] is not None:
            continue
        assert module.evaluate("finite_policy", case["data"]) == module.check(
            "finite_policy", case["data"], defaults
        ), case["id"]


def test_reordering_transitions_changes_no_truth_value_or_count():
    module = _production_module()
    models = [(c["data"], _claims_for(c)) for c in _fixture_cases() if len(c["data"]["transitions"]) > 1]
    models += [(d, c) for d, c in random_models() if len(d["transitions"]) > 1]
    assert models
    for index, (data, claims) in enumerate(models):
        reordered = {**data, "transitions": list(reversed(data["transitions"]))}
        base = module.check("finite_policy", data, claims)
        other = module.check("finite_policy", reordered, claims)
        assert base["code"] == other["code"], index
        assert base["blockers"] == other["blockers"], index
        assert base["support_status"] == other["support_status"], index
        assert base["determining_ids"] == other["determining_ids"], index
        assert base["value"]["reachability"] == other["value"]["reachability"], index
        assert sorted(c["transition"] for c in base["value"]["transition_target_conflicts"]) == sorted(
            c["transition"] for c in other["value"]["transition_target_conflicts"]
        ), index
        base_rows = {r["id"]: r for r in base["value"]["claims"]}
        other_rows = {r["id"]: r for r in other["value"]["claims"]}
        for claim_id, row in base_rows.items():
            twin = other_rows[claim_id]
            for field in ("outcome", "violations_found", "reasons", "standing", "determining_ids"):
                assert row[field] == twin[field], (index, claim_id, field)


def test_duplicating_an_equivalent_constraint_changes_only_determining_ids():
    module = _production_module()
    models = [(c["data"], _claims_for(c)) for c in _fixture_cases() if c["data"]["constraints"]]
    models += [(d, c) for d, c in random_models() if d["constraints"]]
    assert models
    for index, (data, claims) in enumerate(models):
        original = data["constraints"][0]
        duplicate_id = f"dup-{original['id']}"
        duplicate = {"id": duplicate_id, "condition": original["condition"], "rule": original["rule"]}
        doubled = {**data, "constraints": list(data["constraints"]) + [duplicate]}
        k = len(data["constraints"])
        base = module.check("finite_policy", data, claims)
        twin = module.check("finite_policy", doubled, claims)
        assert base["code"] == twin["code"], index
        assert base["blockers"] == twin["blockers"], index
        assert base["support_status"] == twin["support_status"], index
        assert base["value"]["reachability"] == twin["value"]["reachability"], index
        assert base["value"]["transition_target_conflicts"] == twin["value"]["transition_target_conflicts"], (
            index
        )
        base_rows = {r["id"]: r for r in base["value"]["claims"]}
        twin_rows = {r["id"]: r for r in twin["value"]["claims"]}
        for claim_id, row in base_rows.items():
            other = twin_rows[claim_id]
            for field in ("outcome", "violations_found", "reasons", "standing", "witnesses"):
                assert row[field] == other[field], (index, claim_id, field)
            old_ids = row["determining_ids"]
            assert other["determining_ids"] == old_ids[:k] + [duplicate_id] + old_ids[k:], (index, claim_id)
        assert (
            twin["determining_ids"]
            == base["determining_ids"][:k] + [duplicate_id] + base["determining_ids"][k:]
        )
