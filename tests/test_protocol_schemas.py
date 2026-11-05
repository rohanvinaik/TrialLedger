"""Schema-only checks of the published JSON Schemas for contracts C2-C8 (task 1.4).

No validator library is installed and none may be added, so this file carries a small explicit validator for
the keyword subset the schemas use. Supported validation keywords, and nothing else:

    type (a single name: object, array, string, integer, number, boolean, null; bool is never an integer)
    const, enum (type-strict: True is not 1, 1 is not 1.0)
    properties, required, additionalProperties (the booleans false or true only)
    items (one schema), minItems, maxItems, uniqueItems (type-strict structural equality)
    minLength, maxLength, minimum, maximum
    pattern (must be written ^...$ and is applied with re.fullmatch to the text between the anchors)
    oneOf (exactly one branch matches), anyOf (at least one branch matches)
    $ref, only as "#/$defs/NAME" in the same document or "FILE.schema.json#/$defs/NAME" in a sibling file

Annotation keywords ignored by validation: $schema, $id, $comment, $defs, title, description, version.

Any other keyword in a schema (allOf, not, if, format, patternProperties, a list-valued type, a schema-valued
additionalProperties, ...) raises SchemaError when the schema is checked, so a schema can never silently go
unchecked. minLength, maxLength and uniqueItems are additions to the minimal subset asked for: the contracts
need nonempty strings, bounded identifiers and unique lists.

Schemas describe structure only. Their semantic refusals (dangling references, cycles, version and adoption
rules, interval emptiness, cross-field limits) stay in the code and are listed in OUT_OF_SCHEMA_SCOPE below.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from TrialLedger.layer2 import run

ROOT = Path(__file__).resolve().parent.parent
CHANGE = ROOT / "openspec" / "changes" / "connect-protocol-design-workflow" / "interface"
SCHEMAS = CHANGE / "schemas"
FIXTURES = CHANGE / "fixtures"

VALIDATION_KEYWORDS = frozenset(
    {
        "type",
        "const",
        "enum",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "pattern",
        "oneOf",
        "anyOf",
        "$ref",
    }
)
ANNOTATIONS = frozenset({"$schema", "$id", "$comment", "$defs", "title", "description", "version"})
ROOT_ONLY = frozenset({"$schema", "$id", "version", "$defs"})
TYPES = frozenset({"object", "array", "string", "integer", "number", "boolean", "null"})
DRAFT = "https://json-schema.org/draft/2020-12/schema"


class SchemaError(Exception):
    """A schema this validator cannot check faithfully; never a validation failure of an instance."""


def load_registry() -> dict[str, dict]:
    return {path.name: json.loads(path.read_text()) for path in sorted(SCHEMAS.glob("*.schema.json"))}


def resolve(reference: str, current: str, registry: dict[str, dict]) -> tuple[dict, str]:
    file, _, fragment = reference.partition("#")
    name = file or current
    if name not in registry:
        raise SchemaError(f"unresolvable $ref file: {reference}")
    prefix = "/$defs/"
    if not fragment.startswith(prefix) or "/" in fragment[len(prefix) :]:
        raise SchemaError(f"unsupported $ref form: {reference}")
    defs = registry[name].get("$defs", {})
    key = fragment[len(prefix) :]
    if key not in defs:
        raise SchemaError(f"unresolvable $ref: {reference}")
    return defs[key], name


def check_schema(
    schema: object, name: str, registry: dict[str, dict], path: str = "$", root: bool = False
) -> None:
    """Fail loudly unless every keyword of this schema (recursively) is supported and well-typed."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: a schema must be an object")
    for key in schema:
        if key in VALIDATION_KEYWORDS:
            continue
        if key in ANNOTATIONS:
            if key in ROOT_ONLY and not root:
                raise SchemaError(f"{path}: {key} is only allowed at the document root")
            continue
        raise SchemaError(f"{path}: unsupported keyword {key!r}")
    if "$ref" in schema:
        extra = set(schema) - {"$ref"} - (ANNOTATIONS - ROOT_ONLY)
        if extra:
            raise SchemaError(f"{path}: $ref must stand alone, found {sorted(extra)}")
        seen = set()
        target, target_name = schema["$ref"], name
        while True:  # a chain of bare $refs must end
            if target in seen:
                raise SchemaError(f"{path}: $ref cycle through {target}")
            seen.add(target)
            resolved, target_name = resolve(target, target_name, registry)
            if "$ref" not in resolved:
                break
            target = resolved["$ref"]
    if "type" in schema and (not isinstance(schema["type"], str) or schema["type"] not in TYPES):
        raise SchemaError(f"{path}: type must be one of {sorted(TYPES)}")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise SchemaError(f"{path}: enum must be a nonempty list")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise SchemaError(f"{path}: required must be a list of names")
        if len(set(required)) != len(required):
            raise SchemaError(f"{path}: required repeats a name")
    if "additionalProperties" in schema:
        if not isinstance(schema["additionalProperties"], bool):
            raise SchemaError(f"{path}: additionalProperties must be a boolean")
        if schema["additionalProperties"] is False:
            declared = set(schema.get("properties", {}))
            if set(schema.get("required", [])) - declared:
                raise SchemaError(f"{path}: required names a property that a closed object does not declare")
    for key in ("minItems", "maxItems", "minLength", "maxLength"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise SchemaError(f"{path}: {key} must be a nonnegative integer")
    for key in ("minimum", "maximum"):
        if key in schema and (type(schema[key]) not in (int, float)):
            raise SchemaError(f"{path}: {key} must be a number")
    if "uniqueItems" in schema and type(schema["uniqueItems"]) is not bool:
        raise SchemaError(f"{path}: uniqueItems must be a boolean")
    if "pattern" in schema:
        pattern = schema["pattern"]
        if not isinstance(pattern, str) or not (pattern.startswith("^") and pattern.endswith("$")):
            raise SchemaError(f"{path}: pattern must be anchored ^...$")
        try:
            re.compile(pattern[1:-1])
        except re.error as error:
            raise SchemaError(f"{path}: pattern does not compile: {error}") from error
    for key in ("oneOf", "anyOf"):
        if key in schema:
            if not isinstance(schema[key], list) or not schema[key]:
                raise SchemaError(f"{path}: {key} must be a nonempty list")
            for index, branch in enumerate(schema[key]):
                check_schema(branch, name, registry, f"{path}/{key}/{index}")
    if "items" in schema:
        check_schema(schema["items"], name, registry, path + "/items")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise SchemaError(f"{path}: properties must be an object")
        for prop, sub in schema["properties"].items():
            check_schema(sub, name, registry, f"{path}/properties/{prop}")
    if root:
        for def_name, sub in schema.get("$defs", {}).items():
            check_schema(sub, name, registry, f"{path}/$defs/{def_name}")


def same(left: object, right: object) -> bool:
    """Type-strict JSON equality: True is not 1 and 1 is not 1.0."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)  # type: ignore[union-attr]
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right, strict=True))  # type: ignore[arg-type]
    return left == right


def kind_of(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return type(value) is int
    return type(value) in (int, float)


def discriminated_out(instance: object, branch: dict, name: str, registry: dict[str, dict]) -> bool:
    """True when a const property of the instance certainly fails this branch (a speed-up only)."""
    if "$ref" in branch:
        branch, name = resolve(branch["$ref"], name, registry)
    if not isinstance(instance, dict):
        return False
    return any(
        "const" in sub and key in instance and not same(instance[key], sub["const"])
        for key, sub in branch.get("properties", {}).items()
    )


def errors(
    instance: object, schema: dict, name: str, registry: dict[str, dict], path: str = "$"
) -> list[str]:
    """Every violation of the schema by the instance, as path-prefixed text; empty means valid."""
    if "$ref" in schema:
        target, target_name = resolve(schema["$ref"], name, registry)
        return errors(instance, target, target_name, registry, path)
    found: list[str] = []
    if "type" in schema and not kind_of(instance, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "const" in schema and not same(instance, schema["const"]):
        found.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and not any(same(instance, option) for option in schema["enum"]):
        found.append(f"{path}: {instance!r} is not in the enum")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            found.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            found.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and re.fullmatch(schema["pattern"][1:-1], instance) is None:
            found.append(f"{path}: does not match {schema['pattern']}")
    if type(instance) in (int, float):
        if "minimum" in schema and instance < schema["minimum"]:
            found.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            found.append(f"{path}: above {schema['maximum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            found.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            found.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and any(
            same(a, b) for index, a in enumerate(instance) for b in instance[index + 1 :]
        ):
            found.append(f"{path}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(instance):
                found.extend(errors(item, schema["items"], name, registry, f"{path}/{index}"))
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                found.append(f"{path}: missing {key}")
        for key, value in instance.items():
            if key in properties:
                found.extend(errors(value, properties[key], name, registry, f"{path}/{key}"))
            elif schema.get("additionalProperties") is False:
                found.append(f"{path}: unexpected {key}")
    for key in ("oneOf", "anyOf"):
        if key in schema:
            matches = sum(
                not discriminated_out(instance, branch, name, registry)
                and not errors(instance, branch, name, registry, path)
                for branch in schema[key]
            )
            if key == "oneOf" and matches != 1:
                found.append(f"{path}: matched {matches} oneOf branches, not exactly one")
            if key == "anyOf" and matches == 0:
                found.append(f"{path}: matched no anyOf branch")
    return found


REGISTRY = load_registry()


def validate(instance: object, file: str, definition: str) -> list[str]:
    schema, name = resolve(f"{file}#/$defs/{definition}", file, REGISTRY)
    return errors(instance, schema, name, REGISTRY)


# ---------------------------------------------------------------------------------------------------------
# What the schemas cannot say. Every refusal code below is a semantic (cross-field, cross-object or
# arithmetic) rule that stays in the code. A malformed fixture whose code is listed here is not required to
# fail schema validation; every other malformed fixture must.
# ---------------------------------------------------------------------------------------------------------

OUT_OF_SCHEMA_SCOPE = {
    # protocol ledger (protocol_objects.py)
    "protocol_duplicate_object": "unique by the id field, not by whole-object equality",
    "protocol_duplicate_check": "unique by the id field",
    "protocol_duplicate_section": "unique by the id field",
    "protocol_scope_target": "scope.target must equal the session target; the schema sees only its shape",
    "protocol_unknown_source": "needs the session source index",
    "protocol_origin_digest": "needs the retained source snapshot reference",
    "protocol_origin_pointer": "needs the retained source study to resolve the pointer",
    "protocol_hypothesis_cannot_supply_fact": "relates origin.kind to standing.status across fields",
    "protocol_unknown_premise": "needs the session premise index",
    "protocol_adoption_mismatch": "support must be an adoption premise naming this exact id and version",
    "protocol_unknown_object": "dangling reference; needs the object id set",
    "protocol_dependency_cycle": "whole-graph property",
    "protocol_unlisted_reference": "data references must appear in depends_on (cross-field)",
    "protocol_reference_kind": "a referenced id must name an object of the expected kind",
    "protocol_unknown_requirement": "collection.event_handling.requirement must name an estimand requirement",
    "protocol_unknown_policy_variable": "policy binding variable must name a model variable",
    "protocol_external_missing": "missing names must be disjoint from input names",
    "protocol_check_objects": "per-kind object patterns (counts by kind and declared links)",
    "protocol_empty_interval": "lower <= upper comparison of rationals",
    "protocol_infinite_inclusive": "inclusion at an infinite endpoint",
    "protocol_rational_bit_limit": "256-bit component cap",
    # protocol decisions (protocol_decisions.py)
    "protocol_option_unknown_object": "replacement id must exist in the session protocol",
    "protocol_option_kind_changed": "replacement must keep the baseline object's kind",
    "protocol_option_target_changed": "replacement must keep the baseline object's scope.target",
    "protocol_option_unknown_check": "check ids must be declared",
    "protocol_option_missing_required_check": "every required check on the target must be listed",
    "protocol_option_context_mismatch": "optional check sets must agree across alternatives",
    "protocol_option_no_required_check": "needs the session check set",
    "protocol_option_selection": "selected.alternative must name an alternative",
    # definition relations (definition_checks.py)
    "definition_operand_reference": "a valid child index beside exactly one reference kind",
    "definition_unknown_protocol_check": "needs the declared check ids",
    "definition_protocol_requires_v2": "needs the session schema_version",
    "definition_target_mismatch": "both operands must carry the same target",
    # finite_policy (protocol_policies.py)
    "policy_reserved_variable": "no variable may use the reserved policy_state key",
    "policy_undeclared_variable": "propositions may read only declared variables",
    "policy_terminal_outgoing": "terminal states have no outgoing transition",
    "policy_unknown_action": "action ids must be declared",
    "policy_unknown_state": "state names must be declared",
    "policy_duplicate_id": "unique by the id field",
    "policy_duplicate_claim": "each claim kind and id at most once",
    "policy_valuation_limit": "product of domain sizes at most 4096",
    # schedule_coverage (protocol_schedule.py)
    "schedule_rational_bit_limit": "256-bit component cap",
    "schedule_empty_interval": "lower <= upper comparison of rationals",
    "schedule_infinite_inclusive": "inclusion at an infinite endpoint",
    "schedule_duplicate_claim": "each claim kind and id at most once",
    # binomial_design (protocol_statistics.py)
    "binomial_invalid_probabilities": "0 <= p0 < p1 <= 1",
    "binomial_rational_bit_limit": "256-bit component cap",
    "binomial_duplicate_claim": "unique claim ids",
}

# Codes whose structural part the schema does check; the remainder is semantic.
PARTLY_SEMANTIC = {
    "protocol_invalid_proposition": "tag and shape are structural; the rest is assertions/entail",
    "policy_invalid_initial": "nonempty is structural; being a subset of the states is semantic",
    "policy_invalid_terminal": "uniqueness is structural; being a subset of the states is semantic",
    "binomial_invalid_critical_count": "an integer >= 0 is structural; <= n + 1 is semantic",
    "binomial_invalid_claims": "ids, enums and rational syntax are structural; value in [0, 1] is semantic",
    "protocol_data_fields": "key sets and types are structural; uniqueness by name or id is semantic",
}

# Individual fixture cases that carry a structural code but whose actual defect is semantic.
CASE_SCOPE_EXCEPTIONS = {
    "objects:estimand_duplicate_requirement": "requirement ids unique by the id field",
    "objects:external_duplicate_input": "inputs unique by the name field",
    "binomial:k-too-large": "critical_count <= n + 1 is a cross-field bound",
    "binomial:claim-value-out-of-range": "claim value in [0, 1] is a numeric range on a rational string",
}


def prefix_of(code: str) -> str:
    return code.split(":")[0]


def is_out_of_scope(code: str) -> bool:
    return prefix_of(code) in OUT_OF_SCHEMA_SCOPE


def is_semantic_remainder(code: str) -> bool:
    return is_out_of_scope(code) or prefix_of(code) in PARTLY_SEMANTIC or code.startswith("table_")


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------------------------------------
# The validator itself
# ---------------------------------------------------------------------------------------------------------


def test_the_docstring_names_every_supported_validation_keyword():
    for keyword in VALIDATION_KEYWORDS:
        assert keyword in __doc__, keyword


@pytest.mark.parametrize(
    "keyword,value",
    [
        ("allOf", [{}]),
        ("not", {}),
        ("if", {}),
        ("then", {}),
        ("else", {}),
        ("format", "date"),
        ("patternProperties", {}),
        ("propertyNames", {}),
        ("dependentRequired", {}),
        ("minProperties", 1),
        ("maxProperties", 1),
        ("exclusiveMinimum", 0),
        ("exclusiveMaximum", 0),
        ("multipleOf", 2),
        ("contains", {}),
        ("prefixItems", []),
        ("unevaluatedProperties", False),
        ("$dynamicRef", "#x"),
        ("$anchor", "x"),
        ("definitions", {}),
    ],
)
def test_an_unsupported_keyword_fails_loudly_instead_of_passing_silently(keyword, value):
    with pytest.raises(SchemaError, match="unsupported keyword"):
        check_schema({"type": "object", keyword: value}, "x.schema.json", {"x.schema.json": {}})
    with pytest.raises(SchemaError, match="unsupported keyword"):
        check_schema({"properties": {"a": {keyword: value}}}, "x.schema.json", {"x.schema.json": {}})
    with pytest.raises(SchemaError, match="unsupported keyword"):
        check_schema({"oneOf": [{"items": {keyword: value}}]}, "x.schema.json", {"x.schema.json": {}})


@pytest.mark.parametrize(
    "schema,message",
    [
        ({"type": ["string", "null"]}, "type must be one of"),
        ({"type": "float"}, "type must be one of"),
        ({"additionalProperties": {"type": "string"}}, "additionalProperties must be a boolean"),
        ({"required": ["a", "a"]}, "repeats a name"),
        ({"required": [1]}, "list of names"),
        (
            {"type": "object", "properties": {}, "required": ["a"], "additionalProperties": False},
            "does not declare",
        ),
        ({"pattern": "[0-9]+"}, "anchored"),
        ({"pattern": "^(a$"}, "does not compile"),
        ({"oneOf": []}, "nonempty list"),
        ({"enum": []}, "nonempty list"),
        ({"minItems": -1}, "nonnegative"),
        ({"minItems": True}, "nonnegative"),
        ({"uniqueItems": 1}, "boolean"),
        ({"$ref": "#/$defs/missing"}, "unresolvable"),
        ({"$ref": "nowhere.schema.json#/$defs/a"}, "unresolvable"),
        ({"$ref": "#/properties/a"}, "unsupported $ref form"),
        ({"$ref": "#/$defs/a", "type": "string"}, "must stand alone"),
        ({"$defs": {}}, "only allowed at the document root"),
        ({"version": "1"}, "only allowed at the document root"),
    ],
)
def test_malformed_schemas_are_refused_by_the_checker(schema, message):
    registry = {"x.schema.json": {"$defs": {"a": {"type": "string"}}}}
    with pytest.raises(SchemaError, match=re.escape(message)):
        check_schema(schema, "x.schema.json", registry)


def test_a_bare_ref_cycle_is_refused():
    registry = {"x.schema.json": {"$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}}}}
    with pytest.raises(SchemaError, match="cycle"):
        check_schema({"$ref": "#/$defs/a"}, "x.schema.json", registry)


def check(instance, schema):
    registry = {"x.schema.json": {"$defs": {"s": {"type": "string"}}}}
    check_schema(schema, "x.schema.json", registry)
    return errors(instance, schema, "x.schema.json", registry)


@pytest.mark.parametrize(
    "instance,schema,valid",
    [
        # type: bool is not an integer or a number; an integer is a number; a float is not an integer
        (True, {"type": "integer"}, False),
        (1, {"type": "integer"}, True),
        (1.0, {"type": "integer"}, False),
        (True, {"type": "number"}, False),
        (1, {"type": "number"}, True),
        (1.5, {"type": "number"}, True),
        (None, {"type": "null"}, True),
        (0, {"type": "null"}, False),
        ([], {"type": "array"}, True),
        ({}, {"type": "array"}, False),
        ("x", {"type": "string"}, True),
        (b"x".decode() + "", {"type": "boolean"}, False),
        # const and enum are type strict
        (True, {"const": 1}, False),
        (1, {"const": True}, False),
        (1.0, {"const": 1}, False),
        (1, {"const": 1}, True),
        ([1], {"const": [True]}, False),
        ({"a": 1}, {"const": {"a": 1}}, True),
        (True, {"enum": [1, 2]}, False),
        ("b", {"enum": ["a", "b"]}, True),
        ("c", {"enum": ["a", "b"]}, False),
        # strings
        ("", {"type": "string", "minLength": 1}, False),
        ("ab", {"type": "string", "maxLength": 1}, False),
        ("ab", {"type": "string", "minLength": 2, "maxLength": 2}, True),
        ("12", {"type": "string", "pattern": "^[0-9]+$"}, True),
        ("12\n", {"type": "string", "pattern": "^[0-9]+$"}, False),
        ("a12", {"type": "string", "pattern": "^[0-9]+$"}, False),
        # numbers
        (0, {"type": "integer", "minimum": 1}, False),
        (1, {"type": "integer", "minimum": 1, "maximum": 1}, True),
        (2, {"type": "integer", "maximum": 1}, False),
        # arrays
        ([1], {"type": "array", "minItems": 2}, False),
        ([1, 2, 3], {"type": "array", "maxItems": 2}, False),
        ([1, 1], {"type": "array", "uniqueItems": True}, False),
        ([1, True], {"type": "array", "uniqueItems": True}, True),
        ([[1], [1]], {"type": "array", "uniqueItems": True}, False),
        (["a", 1], {"type": "array", "items": {"type": "string"}}, False),
        (["a"], {"type": "array", "items": {"$ref": "#/$defs/s"}}, True),
        ([1], {"type": "array", "items": {"$ref": "#/$defs/s"}}, False),
        # objects
        ({"a": 1}, {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}, True),
        ({}, {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}, False),
        ({"a": "x"}, {"type": "object", "properties": {"a": {"type": "integer"}}}, False),
        ({"a": 1, "b": 2}, {"type": "object", "properties": {"a": {}}, "additionalProperties": False}, False),
        ({"a": 1, "b": 2}, {"type": "object", "properties": {"a": {}}, "additionalProperties": True}, True),
        ({"a": 1, "b": 2}, {"type": "object", "properties": {"a": {}}}, True),
        # oneOf is exactly one, anyOf is at least one
        (1, {"oneOf": [{"type": "integer"}, {"type": "number"}]}, False),
        (1.5, {"oneOf": [{"type": "integer"}, {"type": "number"}]}, True),
        ("x", {"oneOf": [{"type": "integer"}, {"type": "number"}]}, False),
        (1, {"anyOf": [{"type": "integer"}, {"type": "number"}]}, True),
        ("x", {"anyOf": [{"type": "integer"}, {"type": "number"}]}, False),
    ],
)
def test_the_subset_validator_applies_each_keyword_as_documented(instance, schema, valid):
    assert (check(instance, schema) == []) is valid, check(instance, schema)


def test_a_schema_with_a_ref_to_a_sibling_file_resolves_through_the_registry():
    registry = {
        "a.schema.json": {"$defs": {"x": {"$ref": "b.schema.json#/$defs/y"}}},
        "b.schema.json": {"$defs": {"y": {"type": "integer"}}},
    }
    schema = {"$ref": "a.schema.json#/$defs/x"}
    check_schema(schema, "a.schema.json", registry)
    assert errors(3, schema, "a.schema.json", registry) == []
    assert errors("3", schema, "a.schema.json", registry) == ["$: expected integer"]


# ---------------------------------------------------------------------------------------------------------
# The published schema files
# ---------------------------------------------------------------------------------------------------------

EXPECTED_FILES = {
    "binomial-design.schema.json",
    "common.schema.json",
    "decision.schema.json",
    "definition-relation.schema.json",
    "finite-policy.schema.json",
    "protocol.schema.json",
    "schedule-coverage.schema.json",
    "session.schema.json",
}
# Definitions that are entry points rather than building blocks; every other definition must be referenced.
ENTRY_POINTS = {
    "common.schema.json": {"rational", "interval_union", "scope", "standing_ref", "premise_origin"},
    "protocol.schema.json": {
        "protocol",
        "protocol_admitted",
        "object",
        "check",
        "check_admitted",
        "section",
        "adoption_premise",
        "binding_condition_applicability",
        "binding_operation",
    },
    "decision.schema.json": {"decision", "protocol_options"},
    "definition-relation.schema.json": {"definition_checks", "relation"},
    "schedule-coverage.schema.json": {"data", "claims"},
    "finite-policy.schema.json": {"data", "claims"},
    "binomial-design.schema.json": {"data", "claims"},
    "session.schema.json": {"request", "session_v2"},
}


def test_exactly_the_expected_schema_files_are_published():
    assert set(REGISTRY) == EXPECTED_FILES
    assert set(ENTRY_POINTS) == EXPECTED_FILES


@pytest.mark.parametrize("name", sorted(EXPECTED_FILES))
def test_every_schema_file_is_well_formed_under_the_supported_subset(name):
    document = REGISTRY[name]
    check_schema(document, name, REGISTRY, root=True)
    assert document["$schema"] == DRAFT
    assert document["$id"].endswith("/" + name)
    assert document["version"] == "1"
    assert document["title"] and document["description"]
    assert document["$defs"]


def test_all_ids_are_distinct_and_versioned_in_one_path():
    ids = [document["$id"] for document in REGISTRY.values()]
    assert len(set(ids)) == len(ids)
    assert {i.rsplit("/", 1)[0] for i in ids} == {"https://trialledger.invalid/schemas/protocol/1"}


def referenced(node: object, name: str, found: set[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            file, _, fragment = node["$ref"].partition("#")
            found.add((file or name, fragment.removeprefix("/$defs/")))
        for value in node.values():
            referenced(value, name, found)
    elif isinstance(node, list):
        for value in node:
            referenced(value, name, found)


def test_every_definition_is_used_or_a_declared_entry_point():
    found: set[tuple[str, str]] = set()
    for name, document in REGISTRY.items():
        referenced(document["$defs"], name, found)
    unused = {
        (name, key)
        for name, document in REGISTRY.items()
        for key in document["$defs"]
        if (name, key) not in found and key not in ENTRY_POINTS[name]
    }
    assert unused == set()
    for name, keys in ENTRY_POINTS.items():
        assert keys <= set(REGISTRY[name]["$defs"]), name


def test_every_closed_object_requires_exactly_what_it_declares_unless_marked_optional():
    """Closed objects list their fields as required; the few optional fields are named here."""
    optional = {
        ("common.schema.json", "subject"): {"referent"},
        ("common.schema.json", "predicate"): {"key"},
        ("common.schema.json", "value"): {"comparison", "members", "number", "upper", "unit", "inclusivity"},
        ("common.schema.json", "temporal_scope"): {
            "anchor_ref",
            "lower",
            "upper",
            "unit",
            "inclusivity",
            "certainty",
            "evidence",
        },
        ("common.schema.json", "literal"): {"polarity", "time", "qualifiers", "evidence"},
        ("decision.schema.json", "evidence_entry"): {"note", "scope"},
        ("decision.schema.json", "protocol_options"): {"evidence"},
        ("decision.schema.json", "legacy_decision"): {"evidence"},
        ("definition-relation.schema.json", "protocol_operand"): {"child"},
        ("session.schema.json", "session_v2"): {"definition_checks"},
    }
    seen = 0
    for name, document in REGISTRY.items():
        for key, schema in document["$defs"].items():
            if schema.get("additionalProperties") is not False:
                continue
            seen += 1
            gap = set(schema["properties"]) - set(schema["required"])
            assert gap == optional.get((name, key), set()), (name, key)
    assert seen > 60


# ---------------------------------------------------------------------------------------------------------
# Parity of the schemas' constants with the code that is the ground truth
# ---------------------------------------------------------------------------------------------------------


def const_values(node: dict) -> list:
    return [branch["properties"]["kind"]["const"] for branch in node]


def defs(name: str) -> dict:
    return REGISTRY[name]["$defs"]


def test_schema_enums_equal_the_code_vocabularies():
    from TrialLedger.layer2 import assertions as a
    from TrialLedger.layer2 import (
        design_session,
        protocol_decisions,
        protocol_objects,
        protocol_policies,
        protocol_schedule,
        protocol_statistics,
        session_state,
    )

    common, protocol = defs("common.schema.json"), defs("protocol.schema.json")
    assert common["status"]["enum"] == list(protocol_objects.STATUSES)
    assert common["resolution"]["enum"] == list(protocol_objects.RESOLUTIONS)
    assert set(protocol_policies.STATUSES) == set(protocol_objects.STATUSES)
    assert set(protocol_statistics.STATUSES) == set(protocol_objects.STATUSES)
    assert set(protocol_policies.RESOLUTIONS) == set(protocol_objects.RESOLUTIONS)
    assert set(protocol_statistics.RESOLUTIONS) == set(protocol_objects.RESOLUTIONS)
    assert const_values([protocol["object_" + k] for k in protocol_objects.KINDS]) == list(
        protocol_objects.KINDS
    )
    assert [b["$ref"] for b in protocol["object"]["oneOf"]] == [
        f"#/$defs/object_{k}" for k in protocol_objects.KINDS
    ]
    assert protocol["check"]["properties"]["kind"]["enum"] == list(protocol_objects.CHECK_KINDS)
    other = protocol["check_other"]["properties"]["kind"]["enum"]
    typed = [
        protocol[k]["properties"]["kind"]["const"]
        for k in ("check_schedule", "check_finite_policy", "check_binomial_design")
    ]
    assert sorted(other + typed) == sorted(protocol_objects.CHECK_KINDS)
    assert protocol["section_requested"]["properties"]["id"]["enum"] == list(protocol_objects.SECTIONS)
    assert protocol["section_not_applicable"]["properties"]["id"]["enum"] == list(protocol_objects.SECTIONS)
    assert protocol["data_measurement"]["properties"]["mode"]["enum"] == list(protocol_objects.MODES)
    assert protocol["data_collection"]["properties"]["mode"]["enum"] == list(protocol_objects.MODES)
    assert protocol["assumption"]["properties"]["role"]["enum"] == list(protocol_objects.ROLES)
    assert protocol["data_efficacy_binomial"]["properties"]["method"]["const"] == protocol_objects.METHODS[0]
    assert protocol["data_efficacy_external"]["properties"]["method"]["const"] == protocol_objects.METHODS[1]
    assert sorted(
        common["origin_choice"]["properties"]["kind"]["enum"] + ["source_interpretation"]
    ) == sorted(protocol_objects.ORIGIN_KINDS)
    assert common["origin_interpretation"]["properties"]["kind"]["const"] == "source_interpretation"
    # object fields, check fields, section fields and data key sets
    for kind in protocol_objects.KINDS:
        assert set(protocol["object_" + kind]["properties"]) == protocol_objects.OBJECT_FIELDS, kind
        assert set(
            protocol["data_" + kind if kind != "efficacy" else "data_efficacy_binomial"]["properties"]
        ) == set(protocol_objects.DATA_FIELDS[kind]), kind
    assert set(protocol["check"]["properties"]) == protocol_objects.CHECK_FIELDS
    assert set(protocol["section_requested"]["properties"]) == protocol_objects.SECTION_FIELDS
    assert set(protocol["protocol"]["properties"]) == protocol_objects.ENVELOPE
    assert set(protocol["data_estimand"]["properties"]) == set(protocol_objects.R_EST)
    assert set(protocol["data_endpoint"]["properties"]["dependencies"]["anyOf"][1]["properties"]) == set(
        protocol_objects.R_DEP
    )
    assert set(protocol["data_policy"]["properties"]["model"]["properties"]) == set(protocol_objects.R_POL)
    assert set(protocol["binomial_parameters"]["properties"]) == protocol_objects.BINOMIAL_FIELDS
    # ceilings
    assert protocol["protocol"]["properties"]["objects"]["maxItems"] == protocol_objects.MAX_OBJECTS
    assert protocol["protocol"]["properties"]["checks"]["maxItems"] == protocol_objects.MAX_CHECKS
    assert protocol["protocol"]["properties"]["sections"]["maxItems"] == len(protocol_objects.SECTIONS)
    assert common["id_text"]["maxLength"] == protocol_objects.MAX_TEXT
    assert common["basis"]["maxItems"] == protocol_objects.MAX_BASIS
    assert common["interval_union"]["maxItems"] == 32 == protocol_objects.protocol_numbers.MAX_INTERVALS
    assert set(common["interval"]["properties"]) == protocol_objects.protocol_numbers.INTERVAL_FIELDS
    # the typed-proposition vocabularies
    assert common["literal"]["properties"]["polarity"]["enum"] == sorted(a.POLARITIES)
    assert common["subject"]["properties"]["kind"]["enum"] == sorted(a.SUBJECT_KINDS)
    assert common["predicate"]["properties"]["kind"]["enum"] == sorted(a.PREDICATE_KINDS)
    assert common["value"]["properties"]["kind"]["enum"] == sorted(a.VALUE_KINDS)
    assert common["value"]["properties"]["comparison"]["enum"] == sorted(
        set().union(*a.KIND_COMPARISONS.values())
    )
    assert common["value"]["properties"]["inclusivity"]["enum"] == sorted(a.INCLUSIVITIES)
    assert common["temporal_scope"]["properties"]["orientation"]["enum"] == sorted(a.ORIENTATIONS)
    assert common["temporal_scope"]["properties"]["anchor"]["enum"] == sorted(a.ANCHOR_KINDS)
    assert common["temporal_scope"]["properties"]["certainty"]["enum"] == sorted(a.CERTAINTIES)
    assert common["evidence"]["properties"]["kind"]["enum"] == sorted(a.EVIDENCE_KINDS)
    assert sorted(
        c["const"]
        for p in (common["literal"], common["all_of"], common["any_of"], common["not"], common["opaque"])
        for c in [p["properties"]["class"]]
    ) == sorted(name for name in ("Literal", "AllOf", "AnyOf", "Not", "Opaque"))
    assert {cls.__name__ for cls in a.PROPOSITIONS} == {"Literal", "AllOf", "AnyOf", "Not", "Opaque"}
    # operators
    assert defs("schedule-coverage.schema.json")["claim"]["properties"]["claim"]["enum"] == list(
        protocol_schedule.CLAIM_KINDS
    )
    assert set(defs("schedule-coverage.schema.json")["data"]["properties"]) == set(protocol_schedule.FIELDS)
    assert (
        defs("schedule-coverage.schema.json")["data"]["properties"]["scope"]["maxLength"]
        == protocol_schedule.MAX_SCOPE
    )
    assert (
        defs("schedule-coverage.schema.json")["data"]["properties"]["anchor"]["maxLength"]
        == protocol_schedule.MAX_ANCHOR
    )
    assert (
        defs("schedule-coverage.schema.json")["data"]["properties"]["unit"]["maxLength"]
        == protocol_schedule.MAX_UNIT
    )
    assert defs("schedule-coverage.schema.json")["claims"]["maxItems"] == len(protocol_schedule.CLAIM_KINDS)
    pol = defs("finite-policy.schema.json")
    assert set(pol["data"]["properties"]) == set(protocol_policies.FIELDS)
    assert pol["claim"]["properties"]["claim"]["enum"] == list(protocol_policies.CLAIMS)
    assert pol["claims"]["maxItems"] == len(protocol_policies.CLAIMS)
    assert pol["claim"]["properties"]["witness_limit"]["maximum"] == protocol_policies.MAX_WITNESSES
    assert pol["action"]["properties"]["scope"]["properties"]["level"]["enum"] == list(
        protocol_policies.LEVELS
    )
    assert pol["data"]["properties"]["states"]["maxItems"] == protocol_policies.MAX_STATES
    assert pol["data"]["properties"]["actions"]["maxItems"] == protocol_policies.MAX_ACTIONS
    assert pol["data"]["properties"]["transitions"]["maxItems"] == protocol_policies.MAX_TRANSITIONS
    for field in ("constraints", "prohibitions", "invariants"):
        assert pol["data"]["properties"][field]["maxItems"] == protocol_policies.MAX_RULES, field
    assert pol["data"]["properties"]["scope"]["maxLength"] == protocol_policies.MAX_TEXT
    from TrialLedger.layer2 import decision_tables

    assert pol["data"]["properties"]["variables"]["maxItems"] == decision_tables.MAX_DOMAINS
    assert pol["variable"]["properties"]["values"]["maxItems"] == decision_tables.MAX_VALUES
    binomial = defs("binomial-design.schema.json")
    assert set(binomial["data"]["properties"]) == set(protocol_statistics.DATA_FIELDS)
    assert set(binomial["assumption"]["properties"]) == set(protocol_statistics.ASSUMPTION_FIELDS)
    assert set(binomial["claim"]["properties"]) == set(protocol_statistics.CLAIM_FIELDS)
    assert binomial["assumption"]["properties"]["role"]["enum"] == list(protocol_statistics.ROLES)
    assert binomial["claim"]["properties"]["quantity"]["enum"] == list(protocol_statistics.QUANTITIES)
    assert binomial["claim"]["properties"]["comparison"]["enum"] == list(protocol_statistics.COMPARISONS)
    assert binomial["data"]["properties"]["n"]["maximum"] == protocol_statistics.MAX_N
    assert binomial["data"]["properties"]["critical_count"]["maximum"] == protocol_statistics.MAX_N + 1
    assert binomial["data"]["properties"]["assumptions"]["maxItems"] == protocol_statistics.MAX_ASSUMPTIONS
    assert binomial["claims"]["maxItems"] == protocol_statistics.MAX_CLAIMS
    # decisions, session limits, operations
    decision = defs("decision.schema.json")
    assert set(decision["protocol_options"]["properties"]) == protocol_decisions.FIELDS | {"evidence"}
    assert set(decision["alternative"]["properties"]) == protocol_decisions.ALTERNATIVE_FIELDS
    assert (
        decision["protocol_options"]["properties"]["alternatives"]["maxItems"]
        == protocol_decisions.MAX_ALTERNATIVES
    )
    assert (
        decision["alternative"]["properties"]["replace_objects"]["maxItems"]
        == protocol_decisions.MAX_REPLACEMENTS
    )
    session = defs("session.schema.json")
    assert {k: v["maximum"] for k, v in session["limits"]["properties"].items()} == session_state.HARD_LIMITS
    assert set(session["analysis"]["properties"]["operation"]["enum"]) == session_state.OPERATIONS
    assert set(session["premise"]["properties"]["kind"]["enum"]) == session_state.KINDS - {"adoption"}
    assert set(session["session_v2"]["properties"]) == session_state.SESSION_FIELDS | {
        "protocol",
        "definition_checks",
    }
    assert set(session["session_v2"]["required"]) == session_state.SESSION_FIELDS | {"protocol"}
    relation = defs("definition-relation.schema.json")
    from TrialLedger.layer2 import definition_checks

    assert relation["relation"]["properties"]["relation"]["enum"] == list(definition_checks.RELATIONS)
    assert relation["definition_checks"]["maxItems"] == definition_checks.LIMIT
    assert set(relation["protocol_operand"]["properties"]) == definition_checks.PROTOCOL_OPERAND_FIELDS | {
        "child"
    }
    assert set(relation["analysis_operand"]["properties"]) == definition_checks.OPERAND_FIELDS
    assert design_session is not None


def test_every_out_of_scope_code_exists_in_its_owning_source():
    owners = {
        "protocol_option_": ("protocol_decisions.py", "protocol_option_"),
        "protocol_": ("protocol_objects.py", "protocol_"),
        "definition_": ("definition_checks.py", ""),
        "policy_": ("protocol_policies.py", ""),
        "schedule_": ("protocol_schedule.py", ""),
        "binomial_": ("protocol_statistics.py", ""),
    }
    layer2 = ROOT / "TrialLedger" / "layer2"
    numbers = (layer2 / "protocol_numbers.py").read_text()
    for code in {**OUT_OF_SCHEMA_SCOPE, **PARTLY_SEMANTIC}:
        owner = next(o for o in owners if code.startswith(o))
        file, prefix = owners[owner]
        text = (layer2 / file).read_text()
        token = code.removeprefix(prefix) if prefix else code
        shared = code.split("_", 1)[1]  # operators reuse protocol_numbers codes under their own prefix
        in_numbers = shared in ("empty_interval", "infinite_inclusive", "rational_bit_limit") and (
            f'"_{shared}"' in numbers or f'"{shared}"' in numbers
        )
        assert f'"{token}' in text or in_numbers, code


# ---------------------------------------------------------------------------------------------------------
# Fixtures: valid ones validate, structural refusals fail, semantic refusals are listed above
# ---------------------------------------------------------------------------------------------------------

OBJECT_CASES = fixture("objects.json")["cases"]
OPERATORS = {
    "schedule": ("schedule-coverage.schema.json", fixture("schedule.json")),
    "policy": ("finite-policy.schema.json", fixture("policy.json")),
    "binomial": ("binomial-design.schema.json", fixture("binomial.json")),
}
FIXTURE_COUNTS: dict[str, int] = {}


def operator_errors(file: str, case: dict) -> list[str]:
    found = validate(case["data"], file, "data")
    if case["claims"] is not None:
        found += validate(case["claims"], file, "claims")
    return found


def test_every_valid_object_fixture_validates_as_a_ledger_protocol():
    valid = [case for case in OBJECT_CASES if "expect" in case]
    assert len(valid) >= 3
    for case in valid:
        assert validate(case["protocol"], "protocol.schema.json", "protocol") == [], case["id"]
    FIXTURE_COUNTS["objects_valid"] = len(valid)


def test_the_all_kinds_fixture_exercises_every_kind_check_kind_and_section_state():
    protocol = next(c for c in OBJECT_CASES if c["id"] == "valid_all_kinds")["protocol"]
    assert {o["kind"] for o in protocol["objects"]} == set(
        defs("protocol.schema.json")["data_efficacy_binomial"]
        and [
            "measurement",
            "endpoint",
            "estimand",
            "assessment",
            "collection",
            "efficacy",
            "policy",
            "external_method",
        ]
    )
    assert {c["kind"] for c in protocol["checks"]} == {
        "temporal",
        "schedule",
        "dependencies",
        "estimand",
        "definition",
        "decision_table",
        "finite_policy",
        "binomial_design",
        "external_method",
    }
    assert {s["state"] for s in protocol["sections"]} == {"requested", "not_applicable"}
    assert {o["origin"]["kind"] for o in protocol["objects"]} == {"user_choice", "source_interpretation"}
    assert {o["data"].get("method") for o in protocol["objects"] if o["kind"] == "efficacy"} == {
        "binomial_design",
        "external_method",
    }
    assert any(
        b["object"] is None and b["premise"]
        for o in protocol["objects"]
        if o["kind"] == "policy"
        for b in o["data"]["bindings"]
    )
    assert any(
        b["premise"] is None and b["object"]
        for o in protocol["objects"]
        if o["kind"] == "policy"
        for b in o["data"]["bindings"]
    )


def classify(fixture_name: str, case: dict) -> str:
    code = case["refusal"]
    if f"{fixture_name}:{case['id']}" in CASE_SCOPE_EXCEPTIONS or is_out_of_scope(code):
        return "out_of_scope"
    return "structural"


def test_every_malformed_fixture_is_classified_and_structural_ones_fail_the_schema():
    structural = out_of_scope = 0
    unclassified = []
    for case in (c for c in OBJECT_CASES if "refusal" in c):
        kind = classify("objects", case)
        if kind == "out_of_scope":
            out_of_scope += 1
            continue
        structural += 1
        found = validate(case["protocol"], "protocol.schema.json", "protocol")
        if not found:
            unclassified.append((case["id"], case["refusal"]))
    assert unclassified == [], (
        "structural refusals the schema accepts: add them to OUT_OF_SCHEMA_SCOPE or fix the schema"
    )
    FIXTURE_COUNTS["objects_structural"] = structural
    FIXTURE_COUNTS["objects_out_of_scope"] = out_of_scope
    assert structural >= 40 and out_of_scope >= 25


def test_out_of_scope_listing_is_exactly_the_semantic_codes_the_object_fixtures_use():
    used = {prefix_of(c["refusal"]) for c in OBJECT_CASES if "refusal" in c and is_out_of_scope(c["refusal"])}
    expected = {
        "protocol_duplicate_object",
        "protocol_duplicate_check",
        "protocol_duplicate_section",
        "protocol_scope_target",
        "protocol_unknown_source",
        "protocol_origin_digest",
        "protocol_origin_pointer",
        "protocol_unknown_premise",
        "protocol_unknown_object",
        "protocol_dependency_cycle",
        "protocol_unlisted_reference",
        "protocol_reference_kind",
        "protocol_unknown_requirement",
        "protocol_unknown_policy_variable",
        "protocol_external_missing",
        "protocol_check_objects",
        "protocol_empty_interval",
    }
    assert used == expected
    # Codes that no object fixture exercises are still named, so none passes silently.
    assert {"protocol_adoption_mismatch", "protocol_hypothesis_cannot_supply_fact"} <= set(
        OUT_OF_SCHEMA_SCOPE
    )
    # every code the fixtures use is either listed as semantic or covered by a structural keyword
    every = {prefix_of(c["refusal"]) for c in OBJECT_CASES if "refusal" in c}
    assert {c for c in every if c not in OUT_OF_SCHEMA_SCOPE}, "some codes must be structural"


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_every_valid_operator_fixture_validates_and_every_structural_refusal_fails(name):
    file, document = OPERATORS[name]
    for case in document["cases"]:
        assert operator_errors(file, case) == [], (name, case["id"])
    structural = out_of_scope = 0
    for case in document["malformed"]:
        if classify(name, case) == "out_of_scope":
            out_of_scope += 1
            continue
        structural += 1
        assert operator_errors(file, case), (name, case["id"], case["refusal"])
    FIXTURE_COUNTS[f"{name}_valid"] = len(document["cases"])
    FIXTURE_COUNTS[f"{name}_structural"] = structural
    FIXTURE_COUNTS[f"{name}_out_of_scope"] = out_of_scope
    assert structural >= 6 and out_of_scope >= 3


def test_operator_fixtures_cover_nulls_empty_unions_and_open_bounds():
    data = [c["data"] for c in OPERATORS["schedule"][1]["cases"]]
    assert any(d["available"] is None for d in data) and any(d["available"] == [] for d in data)
    assert any(d["permitted"] == [] for d in data)
    assert any(d["nominal"] is None for d in data)
    assert any(i["lower"] is None or i["upper"] is None for d in data for i in d["available"] or [])


# ---------------------------------------------------------------------------------------------------------
# Result fixtures and the public describe -> prepare path
# ---------------------------------------------------------------------------------------------------------

RESULT_FILES = sorted((FIXTURES / "results").glob("*.json"))
OPERATOR_FILE = {
    "schedule_coverage": "schedule-coverage.schema.json",
    "finite_policy": "finite-policy.schema.json",
    "binomial_design": "binomial-design.schema.json",
}


def test_the_result_fixtures_exist():
    assert len(RESULT_FILES) >= 8


@pytest.mark.parametrize("path", RESULT_FILES, ids=lambda p: p.stem)
def test_every_result_fixture_request_validates_as_a_v2_session_request(path):
    request = json.loads(path.read_text())["request"]
    assert validate(request, "session.schema.json", "request") == []
    assert validate(request["session"]["protocol"], "protocol.schema.json", "protocol") == []


@pytest.mark.parametrize("path", RESULT_FILES, ids=lambda p: p.stem)
def test_operator_children_retained_in_the_result_fixtures_match_the_operator_schemas(path):
    result = json.loads(path.read_text())["result"]
    seen = 0
    for check in result["protocol"]["checks"]:
        for child in check["children"]:
            for signal in child["request"].get("signals", []):
                file = OPERATOR_FILE[signal["kind"]]
                assert validate(signal["data"], file, "data") == [], (path.stem, signal["id"])
                assert validate(signal["claims"], file, "claims") == [], (path.stem, signal["id"])
                seen += 1
    assert seen == sum(
        len(child["request"].get("signals", []))
        for check in result["protocol"]["checks"]
        for child in check["children"]
    )


def test_the_result_fixtures_cover_all_three_operators_and_a_protocol_decision():
    kinds, decisions = set(), 0
    for path in RESULT_FILES:
        document = json.loads(path.read_text())
        for check in document["result"]["protocol"]["checks"]:
            for child in check["children"]:
                kinds |= {s["kind"] for s in child["request"].get("signals", [])}
        decisions += sum(
            d.get("kind") == "protocol_options" for d in document["request"]["session"]["decisions"]
        )
    assert kinds == set(OPERATOR_FILE)
    assert decisions >= 1


def test_the_session_example_from_describe_validates_after_prepare():
    described = run({"operation": "describe", "view": "protocol"})
    assert described["code"] == "complete", described
    prepared = run(described["result"]["example"])
    assert prepared["code"] == "complete", prepared
    request = prepared["result"]["request"]
    assert request["operation"] == "design_session"
    assert request["session"]["schema_version"] == 2
    assert validate(request, "session.schema.json", "request") == []
    protocol = request["session"]["protocol"]
    assert validate(protocol, "protocol.schema.json", "protocol") == []
    assert validate(protocol, "protocol.schema.json", "protocol_admitted") == []
    assert [o["kind"] for o in protocol["objects"]] == ["measurement", "assessment", "collection"]
    assert [c["kind"] for c in protocol["checks"]] == ["schedule"]
    # prepare filled the closed envelope fields; a missing one would not validate
    mutilated = copy.deepcopy(request)
    del mutilated["session"]["protocol"]["objects"][0]["scope"]
    assert validate(mutilated, "session.schema.json", "request")


def test_the_described_example_can_be_run_and_its_replayed_children_match_the_operator_schemas():
    prepared = run(run({"operation": "describe", "view": "protocol"})["result"]["example"])
    reply = run(prepared["result"]["request"])
    assert reply["code"] == "complete", reply
    children = [c for check in reply["result"]["protocol"]["checks"] for c in check["children"]]
    assert children
    for child in children:
        for signal in child["request"]["signals"]:
            file = OPERATOR_FILE[signal["kind"]]
            assert validate(signal["data"], file, "data") == []
            assert validate(signal["claims"], file, "claims") == []


# ---------------------------------------------------------------------------------------------------------
# Hand-built constructs: bindings, adoption premise, decision, definition relation
# ---------------------------------------------------------------------------------------------------------


def literal() -> dict:
    return {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
        "predicate": {"class": "Predicate", "kind": "measurement", "key": "invented_score"},
        "value": {"class": "Value", "kind": "quantity", "comparison": "ge", "number": 20, "unit": "points"},
    }


def standing_fields() -> dict:
    return {"status": "proposed", "resolution": "resolved", "basis": ["user:invented"]}


def test_typed_propositions_accept_the_canonical_forms_and_refuse_untagged_ones():
    lit = literal()
    for good in (
        lit,
        {"class": "Not", "part": lit},
        {"class": "AllOf", "parts": [lit, {"class": "Opaque", "ref": "unread"}]},
        {"class": "AnyOf", "parts": [lit, {"class": "Not", "part": lit}]},
        {**lit, "qualifiers": {"class": "Always"}, "polarity": "negative", "time": None, "evidence": []},
        {**lit, "qualifiers": {"class": "Not", "part": lit}},
        {
            **lit,
            "time": {
                "class": "TemporalScope",
                "orientation": "before",
                "anchor": "randomization",
                "upper": 7.0,
            },
        },
    ):
        assert validate(good, "common.schema.json", "proposition") == [], good
    for bad in (
        {"class": "Always"},  # a condition, not a proposition
        {"class": "AllOf", "parts": [lit]},  # at least two parts
        {"class": "Not"},
        {"class": "Opaque", "ref": ""},
        {"class": "Unknown"},
        {k: v for k, v in lit.items() if k != "class"},
        {**lit, "polarity": "maybe"},
        {**lit, "extra": 1},
        {**lit, "value": {**lit["value"], "number": True}},
        {**lit, "value": {**lit["value"], "members": [1]}},
        {**lit, "time": {"class": "TemporalScope", "orientation": "before"}},
        "literal",
        [lit],
    ):
        assert validate(bad, "common.schema.json", "proposition"), bad
    assert validate({"class": "Always"}, "common.schema.json", "condition") == []


def test_check_bindings_have_a_generic_ledger_shape_and_two_closed_named_shapes():
    protocol = defs("protocol.schema.json")
    assert set(protocol["binding_operation"]["properties"]["projection"]["enum"]) == {
        "temporal_request",
        "decision_table_request",
    }
    from TrialLedger.layer2 import protocol_projections

    assert protocol["binding_condition_applicability"]["properties"]["projection"]["const"] == (
        protocol_projections.APPLICABILITY
    )
    assert {protocol_projections.PROJECTIONS[k].split(":")[0] for k in ("temporal", "decision_table")} == set(
        protocol["binding_operation"]["properties"]["projection"]["enum"]
    )
    good = {"projection": "condition_applicability", "premises": ["p1", "p2"]}
    assert validate(good, "protocol.schema.json", "binding_condition_applicability") == []
    assert validate(good, "protocol.schema.json", "binding") == []
    for bad in (
        {"projection": "condition_applicability"},
        {**good, "premises": []},
        {**good, "premises": ["p1", "p1"]},
        {**good, "x": 1},
    ):
        assert validate(bad, "protocol.schema.json", "binding_condition_applicability"), bad
    op = {"projection": "temporal_request", "data": {"anything": 1}}
    assert validate(op, "protocol.schema.json", "binding_operation") == []
    for bad in (
        {"projection": "schedule_window_coverage", "data": {}},
        {"projection": "temporal_request"},
        {"projection": "temporal_request", "data": []},
    ):
        assert validate(bad, "protocol.schema.json", "binding_operation"), bad
    assert validate({"data": {}}, "protocol.schema.json", "binding")


def adoption() -> dict:
    return {
        "id": "adopt:o1:v1",
        "kind": "adoption",
        "payload": {"objects": [{"id": "o1", "version": "v1"}], "status": "known", "resolution": "resolved"},
        "origin": {"kind": "user_choice", "ref": "user:invented", "source": None, "analysis": None},
        "depends_on": [],
    }


def test_the_adoption_premise_is_closed_and_user_attributed():
    assert validate(adoption(), "protocol.schema.json", "adoption_premise") == []
    cases = []
    for edit in (
        lambda p: p["payload"].update(objects=[]),
        lambda p: p["payload"].update(objects=[{"id": "o1", "version": "v1"}] * 2),
        lambda p: p["payload"].update(objects=[{"id": "o1"}]),
        lambda p: p["payload"].update(status="certain"),
        lambda p: p["payload"].update(extra=1),
        lambda p: p["origin"].update(kind="hypothesis"),
        lambda p: p["origin"].update(source="s"),
        lambda p: p["origin"].update(analysis="a"),
        lambda p: p.update(kind="assertion"),
        lambda p: p.update(extra=1),
        lambda p: p.pop("depends_on"),
    ):
        mutated = adoption()
        edit(mutated)
        cases.append(mutated)
    for bad in cases:
        assert validate(bad, "protocol.schema.json", "adoption_premise"), bad
    # inside a session, an adoption premise is read as an adoption and a stray kind is not
    assert validate(adoption(), "session.schema.json", "any_premise") == []
    odd = adoption()
    odd["payload"] = {"anything": 1}
    assert validate(odd, "session.schema.json", "any_premise")


def decision_target() -> dict:
    return {
        "kind": "new_trial",
        "ref": "draft",
        "scope": {"study": "draft", "population": "general", "arm": "all", "time": "entry", "version": "v1"},
    }


def replacement_object() -> dict:
    protocol = next(c for c in OBJECT_CASES if c["id"] == "valid_all_kinds")["protocol"]
    return copy.deepcopy(next(o for o in protocol["objects"] if o["id"] == "a1"))


def protocol_decision() -> dict:
    return {
        "kind": "protocol_options",
        "id": "d1",
        "question": "Which invented window?",
        "target": decision_target(),
        "coverage": "declared_design",
        "selected": None,
        "alternatives": [
            {"id": "a", "label": "as drafted", "replace_objects": [], "checks": ["c1"]},
            {"id": "b", "label": "wider", "replace_objects": [replacement_object()], "checks": ["c1"]},
        ],
    }


def test_the_protocol_options_decision_is_closed_and_replacements_are_complete_objects():
    assert validate(protocol_decision(), "decision.schema.json", "protocol_options") == []
    assert validate(protocol_decision(), "decision.schema.json", "decision") == []
    selected = protocol_decision()
    selected["selected"] = {"alternative": "a", "origin": "user", "basis": ["user:invented"]}
    selected["evidence"] = [
        {"id": "e1", "source": "s", "anchor": {"pointer": "/x"}, "role": "quote", "note": "n"}
    ]
    assert validate(selected, "decision.schema.json", "protocol_options") == []

    def edit(mutate):
        value = protocol_decision()
        mutate(value)
        return value

    bad = [
        edit(lambda d: d.update(coverage="represented_restriction")),
        edit(lambda d: d.update(extra=1)),
        edit(lambda d: d.pop("selected")),
        edit(lambda d: d.update(alternatives=d["alternatives"][:1])),
        edit(lambda d: d.update(alternatives=d["alternatives"] * 9)),
        edit(lambda d: d["alternatives"][0].update(extra=1)),
        edit(lambda d: d["alternatives"][0].pop("checks")),
        edit(lambda d: d["alternatives"][0].update(checks=["c1", "c1"])),
        edit(lambda d: d["alternatives"][0].update(checks=[1])),
        edit(lambda d: d["alternatives"][0].update(replace_objects=[replacement_object()] * 17)),
        edit(lambda d: d["alternatives"][1]["replace_objects"][0].pop("scope")),
        edit(lambda d: d["alternatives"][1]["replace_objects"][0].update(kind="source")),
        edit(lambda d: d.update(selected={"alternative": "a", "origin": "model", "basis": ["x"]})),
        edit(lambda d: d.update(selected={"alternative": "a", "origin": "user", "basis": []})),
        edit(lambda d: d.update(evidence=[{"id": "e1", "source": "s", "anchor": "x", "role": "inference"}])),
        edit(lambda d: d.update(kind="query")),
    ]
    for value in bad:
        assert validate(value, "decision.schema.json", "protocol_options"), value
    # a decision with a kind key can only be a protocol decision; one without cannot be
    legacy = {
        "id": "q1",
        "question": "Which age?",
        "target": decision_target(),
        "coverage": "represented_restriction",
        "alternatives": [
            {"id": "o", "label": "older", "analysis": "an1", "query": {"class": "Not"}},
            {"id": "y", "label": "younger", "analysis": "an2", "query": {}},
        ],
        "selected": None,
    }
    assert validate(legacy, "decision.schema.json", "decision") == []
    assert validate({**legacy, "kind": "query"}, "decision.schema.json", "decision")
    assert validate({**legacy, "coverage": "declared_design", "extra": 1}, "decision.schema.json", "decision")


def relation() -> dict:
    return {
        "id": "r1",
        "relation": "implies",
        "left": {
            "protocol_check": "c1",
            "address": "/request/signals/0/data",
            "body": literal(),
            **standing_fields(),
        },
        "right": {"analysis": "an1", "address": "/result", "body": literal(), **standing_fields()},
        **standing_fields(),
    }


def test_the_definition_relation_accepts_a_protocol_check_operand_beside_an_analysis_operand():
    assert validate(relation(), "definition-relation.schema.json", "relation") == []
    with_child = relation()
    with_child["left"]["child"] = 2
    assert validate(with_child, "definition-relation.schema.json", "relation") == []
    assert validate([relation()], "definition-relation.schema.json", "definition_checks") == []

    def edit(mutate):
        value = relation()
        mutate(value)
        return value

    bad = [
        edit(lambda r: r["left"].update(analysis="an1")),  # both references
        edit(lambda r: r["right"].update(protocol_check="c1")),  # both references
        edit(lambda r: r["left"].pop("protocol_check")),  # neither reference
        edit(lambda r: r["left"].update(child=-1)),
        edit(lambda r: r["left"].update(child=True)),
        edit(lambda r: r["right"].update(child=0)),  # child belongs to protocol operands only
        edit(lambda r: r["left"].update(address="/other")),
        edit(lambda r: r["left"].update(address="/requests")),
        edit(lambda r: r["right"].update(address="")),
        edit(lambda r: r.update(relation="similar")),
        edit(lambda r: r["left"].update(status="certain")),
        edit(lambda r: r["left"].update(basis=[])),
        edit(lambda r: r["left"].update(body={"class": "Always"})),
        edit(lambda r: r.update(extra=1)),
        edit(lambda r: r.pop("basis")),
    ]
    for value in bad:
        assert validate(value, "definition-relation.schema.json", "relation"), value
    for address in ("/request", "/result", "/request/a/b", "/result/0"):
        row = relation()
        row["right"]["address"] = address
        assert validate(row, "definition-relation.schema.json", "relation") == [], address
    assert validate([relation()] * 33, "definition-relation.schema.json", "definition_checks")


def test_the_session_schema_pins_the_v2_envelope():
    request = json.loads(RESULT_FILES[0].read_text())["request"]

    def edit(mutate):
        value = copy.deepcopy(request)
        mutate(value)
        return value

    bad = [
        edit(lambda r: r["session"].update(schema_version=1)),
        edit(lambda r: r["session"].update(schema_version=True)),
        edit(lambda r: r["session"].pop("protocol")),
        edit(lambda r: r["session"].update(unknown=1)),
        edit(lambda r: r.update(operation="entailment")),
        edit(lambda r: r.pop("previous")),
        edit(lambda r: r["session"]["limits"].update(max_analyses=129)),
        edit(lambda r: r["session"]["limits"].update(max_solver_work=0)),
        edit(lambda r: r["session"]["limits"].pop("max_output_bytes")),
        edit(lambda r: r["session"]["protocol"].update(schema_version=2)),
        edit(lambda r: r["session"]["protocol"]["checks"][0].update(claims=[{"id": "x", "claim": "bogus"}])),
    ]
    for value in bad:
        assert validate(value, "session.schema.json", "request"), value
    with_previous = copy.deepcopy(request)
    with_previous["previous"] = {
        "session": copy.deepcopy(request["session"]),
        "result": {"code": "complete"},
        "expected_result_digest": "abc",
    }
    assert validate(with_previous, "session.schema.json", "request") == []
    with_previous["previous"]["session"]["schema_version"] = 1
    assert validate(with_previous, "session.schema.json", "request")
    with_relation = copy.deepcopy(request)
    with_relation["session"]["definition_checks"] = [relation()]
    assert validate(with_relation, "session.schema.json", "request") == []


# ---------------------------------------------------------------------------------------------------------
# Differential: the schemas against the code, one mutation at a time
# ---------------------------------------------------------------------------------------------------------


def walk(node: object, path: tuple = ()):
    yield path
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, (*path, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, (*path, index))


def at(root: object, path: tuple):
    for key in path:
        root = root[key]  # type: ignore[index]
    return root


def mutations(root: object):
    """Every single-step structural edit: delete a key, add a key, or swap a value for another type."""
    for path in walk(root):
        if not path:
            continue
        value, parent = at(root, path), at(root, path[:-1])
        if isinstance(parent, dict):
            edited = copy.deepcopy(root)
            del at(edited, path[:-1])[path[-1]]  # type: ignore[arg-type]
            yield ("delete", path), edited
        for replacement in ("X", 7, True, None, [], {}, ""):
            if type(replacement) is type(value) and replacement == value:
                continue
            edited = copy.deepcopy(root)
            at(edited, path[:-1])[path[-1]] = replacement  # type: ignore[index]
            yield ("replace", path, replacement), edited
        if isinstance(value, dict):
            edited = copy.deepcopy(root)
            at(edited, path)["zz_extra"] = 1  # type: ignore[index]
            yield ("extra", path), edited


def ledger_context():
    from tests import test_protocol_objects as objects_test

    return objects_test


def test_the_ledger_schema_never_rejects_what_the_code_accepts_and_misses_only_listed_semantic_rules():
    from TrialLedger.layer2 import protocol_objects

    helper = ledger_context()
    base = helper.valid()
    stricter, weaker, agree = [], {}, 0
    for description, edited in mutations(base):
        found = validate(edited, "protocol.schema.json", "protocol")
        try:
            protocol_objects.validate_protocol(edited, **helper.context())
            code = None
        except ValueError as error:
            code = str(error)
        if found and code is None:
            stricter.append((description, found[:1]))
        elif code and not found:
            weaker.setdefault(code, description)
        else:
            agree += 1
    assert stricter == []
    unlisted = {c: d for c, d in weaker.items() if not is_semantic_remainder(c)}
    assert unlisted == {}, "the code refuses structurally what the schema accepts"
    assert agree > 4000
    assert {prefix_of(c) for c in weaker} >= {
        "protocol_scope_target",
        "protocol_unknown_object",
        "protocol_unlisted_reference",
    }


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_each_operator_schema_never_rejects_what_the_operator_accepts_and_misses_only_listed_rules(name):
    from TrialLedger.layer2 import assertions, protocol_policies, protocol_schedule, protocol_statistics

    module, kind = {
        "schedule": (protocol_schedule, "schedule_coverage"),
        "policy": (protocol_policies, "finite_policy"),
        "binomial": (protocol_statistics, "binomial_design"),
    }[name]
    file, document = OPERATORS[name]
    stricter, unlisted, agree = [], {}, 0
    for case in document["cases"][:2]:
        root = {"data": case["data"], "claims": case["claims"] if case["claims"] is not None else []}
        for description, edited in mutations(root):
            if len(description[1]) < 2:
                continue
            found = validate(edited["data"], file, "data") + validate(edited["claims"], file, "claims")
            try:
                module.validate(kind, edited["data"], edited["claims"])
                code = None
            except assertions.ModelError:
                code = "model_error"  # Value kind/comparison fit: the assertion model's rule
            except ValueError as error:
                code = str(error)
            if found and code is None:
                stricter.append((description, found[:1]))
            elif code and not found and code != "model_error" and not is_semantic_remainder(code):
                unlisted.setdefault(code, description)
            else:
                agree += 1
    assert stricter == []
    assert unlisted == {}
    assert agree > 100


# ---------------------------------------------------------------------------------------------------------
# Ceilings: the schemas and the code agree on the edge, one inside and one over
# ---------------------------------------------------------------------------------------------------------


def grown(items: list, count: int) -> list:
    """The list extended to count items by cloning the last one under a fresh id or name."""
    out = list(items)
    while len(out) < count:
        clone = copy.deepcopy(out[-1])
        if isinstance(clone, dict) and "id" in clone:
            clone["id"] = f"{clone['id']}-g{len(out)}"
        elif isinstance(clone, str):
            clone = f"{clone}-g{len(out)}"
        out.append(clone)
    return out


def test_policy_ceilings_agree_with_the_code_one_inside_and_one_over():
    from TrialLedger.layer2 import protocol_policies

    base = copy.deepcopy(OPERATORS["policy"][1]["cases"][0])
    claims = [{"id": "coverage", "claim": "coverage", "witness_limit": 1}]
    prohibition = base["data"]["prohibitions"][0]
    # constraints and invariants are cloned from a prohibition so the base needs nothing new
    base["data"]["constraints"] = [
        {"id": "k0", "condition": prohibition["condition"], "rule": prohibition["rule"]}
    ]
    base["data"]["invariants"] = [{**copy.deepcopy(prohibition), "id": "i0", "actions": []}]
    ceilings = {
        "states": protocol_policies.MAX_STATES,
        "actions": protocol_policies.MAX_ACTIONS,
        "transitions": protocol_policies.MAX_TRANSITIONS,
        "constraints": protocol_policies.MAX_RULES,
        "prohibitions": protocol_policies.MAX_RULES,
        "invariants": protocol_policies.MAX_RULES,
    }
    for field, limit in ceilings.items():
        for count, accepted in ((limit, True), (limit + 1, False)):
            data = copy.deepcopy(base["data"])
            data[field] = grown(data[field], count)
            schema_ok = validate(data, "finite-policy.schema.json", "data") == []
            try:
                protocol_policies.validate("finite_policy", data, claims)
                code_ok = True
            except ValueError:
                code_ok = False
            assert (schema_ok, code_ok) == (accepted, accepted), (field, count)


def test_other_ceilings_agree_with_the_code_one_inside_and_one_over():
    from TrialLedger.layer2 import protocol_objects, protocol_schedule, protocol_statistics

    schedule = copy.deepcopy(OPERATORS["schedule"][1]["cases"][0]["data"])
    piece = {"lower": "1", "upper": "2", "lower_inclusive": True, "upper_inclusive": True}
    for count, accepted in ((32, True), (33, False)):
        data = {**schedule, "permitted": [piece] * count, "available": None}
        schema_ok = validate(data, "schedule-coverage.schema.json", "data") == []
        code_ok = True
        try:
            protocol_schedule.validate("schedule_coverage", data, [{"id": "e", "claim": "existence"}])
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), count
    binomial = copy.deepcopy(OPERATORS["binomial"][1]["cases"][0]["data"])
    for n, accepted in ((512, True), (513, False)):
        data = {**binomial, "n": n, "critical_count": 1}
        schema_ok = validate(data, "binomial-design.schema.json", "data") == []
        try:
            protocol_statistics.validate("binomial_design", data, [])
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), n
    for k, accepted in ((513, True), (514, False)):
        data = {**binomial, "n": 512, "critical_count": k}
        schema_ok = validate(data, "binomial-design.schema.json", "data") == []
        try:
            protocol_statistics.validate("binomial_design", data, [])
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), k
    for count, accepted in ((16, True), (17, False)):
        assumptions = grown(binomial["assumptions"], count)
        for index, item in enumerate(assumptions):
            item["ref"] = f"user:assumption-{index}"
        data = {**binomial, "assumptions": assumptions}
        schema_ok = validate(data, "binomial-design.schema.json", "data") == []
        try:
            protocol_statistics.validate("binomial_design", data, [])
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), count
    claim = {"id": "c0", "quantity": "power", "comparison": ">=", "value": "1/2"}
    for count, accepted in ((16, True), (17, False)):
        claims = grown([claim], count)
        schema_ok = validate(claims, "binomial-design.schema.json", "claims") == []
        try:
            protocol_statistics.validate("binomial_design", binomial, claims)
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), count
    # identifier length (256) and basis size (32) in the ledger
    helper = ledger_context()
    for length, accepted in ((256, True), (257, False)):
        protocol = helper.valid()
        protocol["objects"] = [protocol["objects"][1]]  # m0, which depends on nothing
        protocol["objects"][0]["id"] = "x" * length
        protocol["checks"], protocol["sections"] = [], []
        schema_ok = validate(protocol, "protocol.schema.json", "protocol") == []
        try:
            protocol_objects.validate_protocol(protocol, **helper.context())
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), length
    for size, accepted in ((32, True), (33, False)):
        protocol = helper.valid()
        protocol["objects"] = [protocol["objects"][1]]
        protocol["objects"][0]["standing"]["basis"] = [f"b{i}" for i in range(size)]
        protocol["checks"], protocol["sections"] = [], []
        schema_ok = validate(protocol, "protocol.schema.json", "protocol") == []
        try:
            protocol_objects.validate_protocol(protocol, **helper.context())
            code_ok = True
        except ValueError:
            code_ok = False
        assert (schema_ok, code_ok) == (accepted, accepted), size


def test_zz_report_fixture_counts():
    """Fixture counts the run validated and rejected, printed with -s and checked only for presence."""
    print("\nschema fixture counts:", json.dumps(FIXTURE_COUNTS, sort_keys=True))
