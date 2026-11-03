"""Typed temporal, regimen and directional-relation evidence; no clinical text interpretation.

All identifiers refer only within the explicitly supplied scope/version. Callers own source binding and
epistemic support. Candidate claims are conjoined jointly with those source constraints. These operators
answer consistency questions; a consistent partial graph does not establish the actual protocol.
"""

from __future__ import annotations

import re
from fractions import Fraction

MAX_NODES = 32
MAX_ROWS = 256
MAX_NUMBER_CHARS = 512
EXACT_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+|\d+/\d+)")
KINDS = ("temporal", "regimen", "relations")
RELATIONS = ("is_a", "instance_of", "has_ingredient", "associated")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
INPUTS = {
    "temporal": {
        "required": ("scope", "unit", "origin", "resolution", "events", "constraints"),
        "fields": {
            "scope": "bound study/cohort/participant-course identity; no calendar-to-followup projection",
            "unit": "nonempty exact unit identity; units are never converted",
            "origin": "declared event id anchoring this one timeline",
            "resolution": "resolved, partially_resolved, unresolved or conflicting",
            "events": "distinct nonempty event ids, maximum 32",
            "constraints": "records: before, after, lower, upper, lower_inclusive, upper_inclusive",
        },
        "claims": (
            "same constraint records; all claims are conjoined. Bounds mean lower <= t(after)-t(before) "
            "<= upper with explicit inclusive flags; null is unbounded. Numbers are integers or exact "
            "decimal/rational strings, never binary floats. Unknown events remain unresolved."
        ),
        "limits": {
            "nodes": MAX_NODES,
            "rows_including_claims": MAX_ROWS,
            "numeric_string_characters": MAX_NUMBER_CHARS,
            "integer_bits": 2048,
        },
    },
    "regimen": {
        "required": ("scope", "stage", "resolution", "arms", "products"),
        "fields": {
            "scope": "nonempty identity binding local arms, products, time and source version",
            "stage": "planned or observed; no implicit transfer between them",
            "resolution": "resolved, partially_resolved, unresolved or conflicting",
            "arms": "{id,role,products,products_complete}; role assigned/aggregate/observational/unresolved",
            "products": "{id,ingredients,ingredients_complete}; exact identities, no alias expansion",
            "absent_products": "optional array of {arm,product} explicit negatives",
        },
        "claims": (
            "records with arm and products, ingredients, absent_products or absent_ingredients; optional "
            "products_complete/ingredients_complete require their corresponding list. False completeness "
            "means only known members. Claims against non-assigned/unbound groups remain unresolved."
        ),
        "limits": {"arms": MAX_NODES, "products": MAX_NODES, "claims": MAX_ROWS},
    },
    "relations": {
        "required": ("scope", "version", "resolution", "triples", "disjoint"),
        "fields": {
            "scope": "nonempty identity binding entities, indication and population",
            "version": "nonempty terminology/rule edition identity, never inferred from words",
            "resolution": "resolved, partially_resolved, unresolved or conflicting",
            "triples": "at most 256 {subject,relation,object,polarity}; positive or negative",
            "disjoint": "two distinct class ids per pair; disjointness alone does not assert existence",
        },
        "claims": (
            "additional triples, jointly conjoined. is_a is reflexive/transitive over declared classes; "
            "instance_of inherits only upward. has_ingredient and associated stay direct. No negative "
            "membership is inferred from absence. At most 32 distinct identifiers and 256 total triples."
        ),
        "limits": {"identifiers": MAX_NODES, "rows_including_claims": MAX_ROWS},
    },
}

EXAMPLES = {
    "temporal": {
        "scope": "invented:cohort-A:participant-course:v1",
        "unit": "day",
        "origin": "randomization",
        "resolution": "resolved",
        "events": ["induction_end", "randomization", "dose"],
        "constraints": [
            {
                "before": "induction_end",
                "after": "randomization",
                "lower": 0,
                "upper": None,
                "lower_inclusive": False,
                "upper_inclusive": True,
            },
            {
                "before": "randomization",
                "after": "dose",
                "lower": 0,
                "upper": 7,
                "lower_inclusive": True,
                "upper_inclusive": True,
            },
        ],
    },
    "regimen": {
        "scope": "invented:study:protocol-v1:cohort-A",
        "stage": "planned",
        "resolution": "resolved",
        "arms": [{"id": "arm-A", "role": "assigned", "products": ["product-AB"], "products_complete": True}],
        "products": [
            {
                "id": "product-AB",
                "ingredients": ["ingredient-A", "ingredient-B"],
                "ingredients_complete": True,
            }
        ],
    },
    "relations": {
        "scope": "invented:condition-universe",
        "version": "invented:edition-1",
        "resolution": "resolved",
        "triples": [
            {"subject": "child", "relation": "is_a", "object": "parent", "polarity": "positive"},
            {"subject": "person", "relation": "instance_of", "object": "child", "polarity": "positive"},
        ],
        "disjoint": [],
    },
}


def _object(value: object, required: set[str], optional: set[str] | frozenset[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ValueError("graph_not_an_object")
    if required - value.keys():
        raise ValueError("graph_missing_field")
    if value.keys() - required - optional:
        raise ValueError("graph_unknown_field")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("graph_identity_required")
    return value


def _rows(value: object, limit: int = MAX_ROWS) -> list:
    if not isinstance(value, list):
        raise ValueError("graph_list_required")
    if len(value) > limit:
        raise ValueError("resource_bound:graph_rows")
    return value


def _ids(value: object, limit: int = MAX_ROWS) -> list[str]:
    found = [_text(item) for item in _rows(value, limit)]
    if len(set(found)) != len(found):
        raise ValueError("graph_duplicate_id")
    return found


def _flag(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("graph_boolean_required")
    return value


def _binding(data: dict, kind: str) -> list[str]:
    _text(data["scope"])
    resolution = data["resolution"]
    if not isinstance(resolution, str) or resolution not in RESOLUTIONS:
        raise ValueError("graph_invalid_resolution")
    return [] if resolution == "resolved" else [f"{kind}_binding:{resolution}"]


def _result(kind: str, code: str, value: dict, blockers: list[str] | tuple[str, ...] = ()) -> dict:
    return {"code": code, "value": value, "blockers": sorted(set(blockers)), "rule": f"graph.{kind}:1"}


def _number(value: object) -> Fraction | None:
    if value is None:
        return None
    if type(value) is not int and not isinstance(value, str):
        raise ValueError("graph_exact_number_required")
    if isinstance(value, str):
        if len(value) > MAX_NUMBER_CHARS:
            raise ValueError("resource_bound:graph_number")
        if EXACT_NUMBER.fullmatch(value) is None:
            raise ValueError("graph_invalid_number")
    elif value.bit_length() > 2048:
        raise ValueError("resource_bound:graph_number")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("graph_invalid_number") from error


def _plain(value: Fraction | None) -> int | str | None:
    if value is None:
        return None
    return value.numerator if value.denominator == 1 else str(value)


def bound_tightness(left: str, left_strict: bool, right: str, right_strict: bool) -> str:
    """Compare two validated exact upper bounds, retaining strictness (pure — pinned).

    At the same numeric endpoint, a strict bound is tighter. Both bounds use the same declared unit.
    """
    a, b = Fraction(left), Fraction(right)
    if a < b or (a == b and left_strict and not right_strict):
        return "tighter"
    if a == b and left_strict == right_strict:
        return "equal"
    return "looser"


def temporal_closure(events: list[str], constraints: list[dict]) -> dict:
    """Exact dense-time difference closure over validated nodes/constraints.

    A distance from i to j bounds t(j)-t(i). Strictness composes by OR, so a zero-length strict cycle is a
    contradiction without inventing a minimum time step. The domain is rational/dense, not integer days.
    """
    distances: dict[tuple[str, str], tuple[Fraction, bool]] = {(e, e): (Fraction(0), False) for e in events}
    for row in constraints:
        lower, upper = _number(row["lower"]), _number(row["upper"])
        edges = []
        if upper is not None:
            edges.append((row["before"], row["after"], upper, not row["upper_inclusive"]))
        if lower is not None:
            edges.append((row["after"], row["before"], -lower, not row["lower_inclusive"]))
        for before, after, number, strict in edges:
            old = distances.get((before, after))
            if old is None or bound_tightness(str(number), strict, str(old[0]), old[1]) == "tighter":
                distances[before, after] = (number, strict)
    for middle in events:
        for before in events:
            for after in events:
                left, right = distances.get((before, middle)), distances.get((middle, after))
                if left is None or right is None:
                    continue
                number, strict = left[0] + right[0], left[1] or right[1]
                old = distances.get((before, after))
                if old is None or bound_tightness(str(number), strict, str(old[0]), old[1]) == "tighter":
                    distances[before, after] = (number, strict)
    if any(number < 0 or (number == 0 and strict) for e in events for number, strict in [distances[e, e]]):
        return {"code": "conflict", "bounds": []}
    bounds = []
    for before in events:
        for after in events:
            if before == after:
                continue
            low, high = distances.get((after, before)), distances.get((before, after))
            if low is None and high is None:
                continue
            bounds.append(
                {
                    "before": before,
                    "after": after,
                    "lower": _plain(-low[0]) if low else None,
                    "upper": _plain(high[0]) if high else None,
                    "lower_inclusive": not low[1] if low else None,
                    "upper_inclusive": not high[1] if high else None,
                }
            )
    return {"code": "consistent", "bounds": bounds}


def _time_row(value: object) -> dict:
    row = _object(value, {"before", "after", "lower", "upper", "lower_inclusive", "upper_inclusive"})
    _text(row["before"])
    _text(row["after"])
    _number(row["lower"])
    _number(row["upper"])
    _flag(row["lower_inclusive"])
    _flag(row["upper_inclusive"])
    return row


def _temporal(data: dict, claims: list[dict]) -> dict:
    data = _object(data, set(INPUTS["temporal"]["required"]))
    blockers = _binding(data, "temporal")
    _text(data["unit"])
    origin = _text(data["origin"])
    events = _ids(data["events"], MAX_NODES)
    if not events:
        raise ValueError("graph_empty_events")
    rows = [_time_row(row) for row in _rows(data["constraints"]) + _rows(claims)]
    _rows(rows)
    mentioned = {origin, *(row[key] for row in rows for key in ("before", "after"))}
    blockers.extend(f"unbound_event:{event}" for event in mentioned - set(events))
    if blockers:
        return _result("temporal", "unresolved", {}, blockers)
    closure = temporal_closure(events, rows)
    return _result(
        "temporal",
        closure["code"],
        {"scope": data["scope"], "unit": data["unit"], "origin": origin, "bounds": closure["bounds"]},
    )


def membership_problem(required: list[str], absent: list[str], complete: list[list[str]]) -> str:
    """Contradiction among positive, explicit negative and exact membership sets (pure — pinned)."""
    positive = set(required).union(*(set(members) for members in complete))
    if positive.intersection(absent):
        return "required_absent"
    if complete and any(set(members) != set(complete[0]) for members in complete[1:]):
        return "complete_sets_disagree"
    if complete and positive - set(complete[0]):
        return "required_outside_complete"
    return "ok"


def graph_disposition(blockers: list[str], conflict: bool) -> str:
    """Unresolved graph binding cannot supply a contradiction verdict (pure — pinned)."""
    if blockers:
        return "unresolved"
    if conflict:
        return "conflict"
    return "consistent"


def _membership(required: list[str], absent: list[str], complete: list[list[str]]) -> dict:
    problem = membership_problem(required, absent, complete)
    return {
        "code": "consistent" if problem == "ok" else "conflict",
        "problem": problem,
        "required": sorted(set(required).union(*(set(row) for row in complete))),
        "absent": sorted(set(absent)),
        "complete": bool(complete),
    }


def _regimen(data: dict, claims: list[dict]) -> dict:
    data = _object(data, set(INPUTS["regimen"]["required"]), {"absent_products"})
    blockers = _binding(data, "regimen")
    if data["stage"] not in ("planned", "observed"):
        raise ValueError("graph_invalid_stage")
    arms, products = {}, {}
    for raw in _rows(data["arms"], MAX_NODES):
        row = _object(raw, {"id", "role", "products", "products_complete"})
        identity = _text(row["id"])
        if identity in arms:
            raise ValueError("graph_duplicate_arm")
        if row["role"] not in ("assigned", "aggregate", "observational", "unresolved"):
            raise ValueError("graph_invalid_arm_role")
        _ids(row["products"])
        _flag(row["products_complete"])
        arms[identity] = row
    for raw in _rows(data["products"], MAX_NODES):
        row = _object(raw, {"id", "ingredients", "ingredients_complete"})
        identity = _text(row["id"])
        if identity in products:
            raise ValueError("graph_duplicate_product")
        _ids(row["ingredients"])
        _flag(row["ingredients_complete"])
        products[identity] = row
    extras: dict[str, list[dict]] = {identity: [] for identity in arms}
    for raw in _rows(claims):
        row = _object(
            raw,
            {"arm"},
            {
                "products",
                "products_complete",
                "ingredients",
                "ingredients_complete",
                "absent_products",
                "absent_ingredients",
            },
        )
        arm = _text(row["arm"])
        if len(row) == 1:
            raise ValueError("graph_empty_regimen_claim")
        for key in ("products", "ingredients", "absent_products", "absent_ingredients"):
            if key in row:
                _ids(row[key])
        for key in ("products", "ingredients"):
            if key + "_complete" in row:
                _flag(row[key + "_complete"])
                if key not in row:
                    raise ValueError("graph_complete_without_members")
        if arm not in arms:
            blockers.append(f"unbound_arm:{arm}")
        elif arms[arm]["role"] != "assigned":
            blockers.append(f"not_assigned_arm:{arm}")
        else:
            extras[arm].append(row)
    absences: dict[str, list[str]] = {identity: [] for identity in arms}
    for raw in _rows(data.get("absent_products", [])):
        row = _object(raw, {"arm", "product"})
        arm, product = _text(row["arm"]), _text(row["product"])
        if arm not in arms:
            blockers.append(f"unbound_arm:{arm}")
        else:
            absences[arm].append(product)
    result = {}
    conflict = False
    for identity, arm in arms.items():
        if arm["role"] == "unresolved":
            blockers.append(f"unresolved_arm_role:{identity}")
        if arm["role"] != "assigned":
            continue
        rows = extras[identity]
        required = [*arm["products"], *(p for r in rows for p in r.get("products", []))]
        absent = [*absences[identity], *(p for r in rows for p in r.get("absent_products", []))]
        complete = [arm["products"]] if arm["products_complete"] else []
        complete += [r["products"] for r in rows if r.get("products_complete", False)]
        held = _membership(required, absent, complete)
        conflict = conflict or held["code"] == "conflict"
        missing = set(held["required"]) - products.keys()
        blockers.extend(f"unbound_product:{product}" for product in missing)
        known = [products[p] for p in held["required"] if p in products]
        ingredients = [i for product in known for i in product["ingredients"]]
        ingredients += [i for row in rows for i in row.get("ingredients", [])]
        exact_ingredients = []
        if held["complete"] and not missing and all(p["ingredients_complete"] for p in known):
            exact_ingredients.append([i for product in known for i in product["ingredients"]])
        exact_ingredients += [r["ingredients"] for r in rows if r.get("ingredients_complete", False)]
        ingredients_held = _membership(
            ingredients, [i for r in rows for i in r.get("absent_ingredients", [])], exact_ingredients
        )
        conflict = conflict or ingredients_held["code"] == "conflict"
        result[identity] = {"products": held, "ingredients": ingredients_held}
    code = graph_disposition(blockers, conflict)
    return _result(
        "regimen", code, {"scope": data["scope"], "stage": data["stage"], "arms": result}, blockers
    )


def relation_conflict(positive: list[list[str]], negative: list[list[str]], disjoint: list[list[str]]) -> str:
    """Find an explicit polarity clash or an inhabited disjoint class pair (pure — pinned).

    A class can be empty, so subclassing two disjoint classes alone is not a contradiction. An instance in
    both is. has_ingredient and associated triples do not establish instance_of membership.
    """
    known = {tuple(row) for row in positive}
    if known.intersection(tuple(row) for row in negative):
        return "positive_negative"
    memberships: dict[str, set[str]] = {}
    for subject, relation, target in positive:
        if relation == "instance_of":
            memberships.setdefault(subject, set()).add(target)
    if any(a in classes and b in classes for classes in memberships.values() for a, b in disjoint):
        return "disjoint_membership"
    return "ok"


def relation_closure(triples: list[dict], disjoint: list[list[str]]) -> dict:
    """Close only declared subtype and instance relations; other relations stay direct."""
    positive = {(r["subject"], r["relation"], r["object"]) for r in triples if r["polarity"] == "positive"}
    negative = {(r["subject"], r["relation"], r["object"]) for r in triples if r["polarity"] == "negative"}
    classes = {
        v
        for s, r, o in positive | negative
        for v in ((s, o) if r == "is_a" else (o,) if r == "instance_of" else ())
    }
    classes.update(v for pair in disjoint for v in pair)
    positive.update((c, "is_a", c) for c in classes)
    for _ in range(MAX_NODES + 1):
        additions = {
            (s, relation, parent)
            for s, relation, child in positive
            if relation in ("is_a", "instance_of")
            for sub, rel, parent in positive
            if rel == "is_a" and child == sub
        }
        if additions <= positive:
            break
        positive |= additions
    known, absent = [list(row) for row in sorted(positive)], [list(row) for row in sorted(negative)]
    problem = relation_conflict(known, absent, disjoint)
    return {
        "code": "consistent" if problem == "ok" else "conflict",
        "problem": problem,
        "positive": known,
        "negative": absent,
    }


def _triple(raw: object) -> dict:
    row = _object(raw, {"subject", "relation", "object", "polarity"})
    _text(row["subject"])
    _text(row["object"])
    if row["relation"] not in RELATIONS:
        raise ValueError("graph_unsupported_relation")
    if row["polarity"] not in ("positive", "negative"):
        raise ValueError("graph_invalid_polarity")
    return row


def _relations(data: dict, claims: list[dict]) -> dict:
    data = _object(data, set(INPUTS["relations"]["required"]))
    blockers = _binding(data, "relations")
    _text(data["version"])
    triples = [_triple(row) for row in _rows(data["triples"]) + _rows(claims)]
    _rows(triples)
    disjoint = []
    for raw in _rows(data["disjoint"]):
        pair = _ids(raw, 2)
        if len(pair) != 2:
            raise ValueError("graph_disjoint_pair_required")
        disjoint.append(pair)
    identifiers = {r[key] for r in triples for key in ("subject", "object")}
    identifiers.update(v for pair in disjoint for v in pair)
    if len(identifiers) > MAX_NODES:
        raise ValueError("resource_bound:graph_nodes")
    if blockers:
        return _result("relations", "unresolved", {}, blockers)
    closure = relation_closure(triples, disjoint)
    return _result(
        "relations", closure["code"], {"scope": data["scope"], "version": data["version"], **closure}
    )


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Check all candidate claims together; unresolved binding never becomes contradiction."""
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError("unsupported_graph_kind")
    functions = {"temporal": _temporal, "regimen": _regimen, "relations": _relations}
    return functions[kind](data, _rows(claims))


def evaluate(kind: str, data: dict) -> dict:
    """Compute one independent source graph without adding candidate claims."""
    return check(kind, data, [])
