"""Compositional display of typed statements; no English interpretation or clinical decisions."""

from __future__ import annotations

import json

MAX_NODES = 256
MAX_TEXT = 8192
COMPARISONS = {"eq": "=", "ne": "≠", "lt": "<", "le": "≤", "gt": ">", "ge": "≥"}


class DisplayError(ValueError):
    """The exact representation remains available when display is unsupported or bounded."""


def value_style(kind: str, comparison: str) -> str:
    """Select syntax by declared type, never by a predicate name (pure).

    post: __return__ in ('boolean', 'quantity', 'interval', 'enum', 'set', 'reference', 'unsupported')
    """
    if kind == "boolean":
        return "boolean"
    if kind == "quantity" and comparison in COMPARISONS:
        return "quantity"
    if kind == "interval" and comparison in ("in", "not_in"):
        return "interval"
    if kind == "enum" and comparison in ("eq", "ne", "in", "not_in"):
        return "enum"
    if kind == "enum_set" and comparison in ("in", "not_in"):
        return "set"
    if kind in ("entity_ref", "definition_ref") and comparison == "eq":
        return "reference"
    return "unsupported"


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _value(value) -> str:
    style = value_style(value.kind, value.comparison)
    members = ", ".join(_quoted(v) for v in value.members)
    if style == "boolean":
        return ""
    if style == "quantity":
        return f" {COMPARISONS[value.comparison]} {value.number} {value.unit}".rstrip()
    if style == "interval":
        relation = "in" if value.comparison == "in" else "outside"
        return (
            f" {relation} interval {value.number} to {value.upper} {value.unit}"
            f" (boundaries {value.inclusivity})"
        )
    if style == "enum":
        relation = {"eq": "is", "ne": "is not", "in": "is one of", "not_in": "is none of"}
        return f" {relation[value.comparison]} {{{members}}}"
    if style == "set":
        relation = "includes every member of" if value.comparison == "in" else "includes none of"
        return f" {relation} {{{members}}}"
    if style == "reference":
        return f" refers to {{{members}}}"
    raise DisplayError("unsupported_value_display")


def _time(value) -> str:
    if value is None:
        return ""
    anchor = value.anchor.replace("_", " ")
    if value.anchor_ref:
        anchor += " " + _quoted(value.anchor_ref)
    return (
        f" [time: {value.orientation} {anchor}; lower={value.lower}; upper={value.upper} "
        f"{value.unit}; boundaries {value.inclusivity}; certainty {value.certainty}]"
    )


def _render(item, counter: list[int], depth: int = 0) -> str:
    from TrialLedger.layer2 import assertions as a

    counter[0] += 1
    if counter[0] > MAX_NODES or depth > 32:
        raise DisplayError("display_resource_bound")
    if isinstance(item, a.Always):
        return "always"
    if isinstance(item, a.Opaque):
        raise DisplayError("opaque_display")
    if isinstance(item, a.Not):
        return f"NOT ({_render(item.part, counter, depth + 1)})"
    if isinstance(item, a.AllOf | a.AnyOf):
        join = " AND " if isinstance(item, a.AllOf) else " OR "
        return "(" + join.join(_render(p, counter, depth + 1) for p in item.parts) + ")"
    if not isinstance(item, a.Literal):
        raise DisplayError("unsupported_proposition_display")
    if (
        item.subject.kind == "unresolved"
        or item.predicate.kind == "unresolved"
        or item.polarity == "unresolved"
    ):
        raise DisplayError("unresolved_literal_display")
    subject = item.subject.kind.replace("_", " ")
    if item.subject.referent:
        subject += " " + _quoted(item.subject.referent)
    text = f"{subject}: {_quoted(item.predicate.key)}{_value(item.value)}{_time(item.time)}"
    if not isinstance(item.qualifiers, a.Always):
        text = f"({text} AND {_render(item.qualifiers, counter, depth + 1)})"
    return f"NOT ({text})" if item.polarity == "negative" else text


def proposition(value: object, reference: str = "") -> dict:
    """Display the validated typed query and preserve a reference on every fallback."""
    from TrialLedger.layer2 import assertions

    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        model = assertions.from_canonical(json.dumps(parsed, ensure_ascii=False, allow_nan=False))
        text = _render(model, [0])
        if len(text) > MAX_TEXT:
            raise DisplayError("display_resource_bound")
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        return {
            "code": str(error) if isinstance(error, DisplayError) else "unsupported_typed_display",
            "text": "Open the exact typed representation; its full display is unresolved here.",
            "canonical_ref": reference,
            "origin": "typed_representation; no clinical prose interpretation",
        }
    return {
        "code": "displayed",
        "text": text,
        "canonical_ref": reference,
        "origin": "typed_representation; predicate names are caller-declared",
    }


def _scope(value) -> str:
    if value.kind in ("all_of", "any_of"):
        join = " AND " if value.kind == "all_of" else " OR "
        return "(" + join.join(_scope(part) for part in value.parts) + ")"
    return value.kind.replace("_", " ") + (" " + _quoted(value.ref) if value.ref else "")


def assertion(value: object, reference: str = "") -> dict:
    """Show force, applicability and cohort without certifying the premise's truth."""
    if not isinstance(value, dict) or value.get("class") != "ScopedAssertion":
        return {
            "code": "unsupported_assertion_display",
            "text": "Open the exact premise.",
            "canonical_ref": reference,
        }
    body = proposition(value.get("body"), reference + "/body")
    force = {
        "required": "Requires",
        "excluded": "Excludes",
        "permitted": "Explicitly permits",
        "definitional": "Defines",
        "descriptive": "Describes",
        "unresolved": "Unresolved force for",
    }.get(value.get("modality"), "Unresolved force for")
    text = f"{force} {body['text']}"
    applicability = value.get("applicability", {"class": "Always"})
    if applicability != {"class": "Always"}:
        condition = proposition(applicability, reference + "/applicability")
        text = f"If {condition['text']}, {text[0].lower() + text[1:]}"
        if condition["code"] != "displayed":
            body = {**body, "code": condition["code"]}
    from TrialLedger.layer2 import assertions

    try:
        model = assertions.from_canonical(json.dumps(value, ensure_ascii=False, allow_nan=False))
        if not isinstance(model, assertions.ScopedAssertion):
            raise ValueError("not_assertion")
        if model.cohort.kind != "all_participants":
            text += "; declared scope: " + _scope(model.cohort)
    except (ValueError, TypeError, RecursionError):
        return {
            "code": "unsupported_assertion_display",
            "text": "Open the exact premise.",
            "canonical_ref": reference,
        }
    return {
        "code": body["code"],
        "text": text,
        "canonical_ref": reference,
        "standing": value.get("status"),
        "resolution": value.get("resolution"),
        "origin": "display of a declared premise, not source-truth certification",
    }


def outcome(result: str) -> str:
    """Wording of the logical result, without interpreting an option label (pure)."""
    return {
        "ENTAILED": "Required by the represented criteria.",
        "REFUTED": "Ruled out by the represented criteria.",
        "UNDETERMINED": "Read the specific open cause; this verdict alone does not establish feasibility.",
        "INCONSISTENT": "The represented criteria conflict; resolve their contradiction first.",
        "OUT_OF_SCOPE": "The represented restriction addresses another declared scope.",
    }.get(result, "Unresolved result; inspect its exact code and warrant.")


def decision_outcome(warrant: dict, feasibility: str) -> str:
    if (
        warrant.get("result") == "UNDETERMINED"
        and feasibility == "feasible"
        and warrant.get("blockers") == ["undecided_by_constraints"]
    ):
        return "Both this proposition and its negation fit the represented restrictions; neither is required."
    return outcome(warrant.get("result", ""))
