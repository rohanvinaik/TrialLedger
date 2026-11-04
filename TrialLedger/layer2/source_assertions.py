"""Content-bound source quotations and explicitly hypothetical clinical readings.

Only the registry's structured integer age fields have a direct rule here. A located
quotation warrants its location, never the clinical meaning of a submitted hypothesis.
The compiler creates new request objects and never changes the supplied registry record.
"""

from __future__ import annotations

import dataclasses
import json
import re
from copy import deepcopy
from typing import Any

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import interpretation_bindings, signals
from TrialLedger.layer2 import source_evidence as source

AGE = re.compile(r"(0|[1-9][0-9]*) (Minutes|Hours|Days|Weeks|Months|Years)\Z")
AGE_FIELDS = {"minimumAge": "ge", "maximumAge": "le"}
HYPOTHESIS = "hypothesis:source-location-is-not-semantic-warrant"
MAX_ITEMS = 1000
RULE_VERSION = "1"
FRAME_FIELDS = {
    "id",
    "label",
    "origin",
    "basis",
    "anchors",
    "assumptions",
    "signals",
    "signal_claims",
    "binding_uses",
}
REQUEST_FIELDS = {
    "operation",
    "study",
    "expected_digest",
    "anchors",
    "interpretations",
    "bindings",
    "queries",
    "context",
    "bound",
    "selected",
}


def age_state(present: bool, value: object) -> str:
    """Classify one complete structured field without normalizing it.

    post: __return__ in ('missing', 'null', 'empty', 'not_applicable', 'malformed', 'unsupported', 'compiled')
    post: present or __return__ == 'missing'
    post: __return__ != 'compiled' or isinstance(value, str)
    """
    if not present:
        return "missing"
    if value is None:
        return "null"
    if not isinstance(value, str):
        return "malformed"
    if value == "":
        return "empty"
    if value == "N/A":
        return "not_applicable"
    return "compiled" if AGE.fullmatch(value) else "unsupported"


def _object(value: object, allowed: set[str], required: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise source.BridgeError(f"{where}:object_required")
    if set(value) - allowed:
        raise source.BridgeError(f"{where}:unknown_fields")
    if required - set(value):
        raise source.BridgeError(f"{where}:missing_fields")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise source.BridgeError(f"{where}:nonempty_text_required")
    return value


def _rows(value: object, where: str) -> list:
    if not isinstance(value, list):
        raise source.BridgeError(f"{where}:list_required")
    if len(value) > MAX_ITEMS:
        raise source.BridgeError(f"{where}:resource_bound")
    return value


def _texts(value: object, where: str) -> list[str]:
    rows = [_text(item, where) for item in _rows(value, where)]
    if not rows:
        raise source.BridgeError(f"{where}:nonempty_list_required")
    return rows


def _model(value: object, cls: type | tuple[type, ...], where: str) -> Any:
    if not isinstance(value, dict):
        raise source.BridgeError(f"{where}:tagged_object_required")
    try:
        item = a.from_canonical(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise source.BridgeError(f"{where}:{error}") from error
    if not isinstance(item, cls):
        raise source.BridgeError(f"{where}:wrong_model_class")
    return item


def _plain(item: object) -> dict:
    return json.loads(a.canonical(item))


def _selected_anchors(value: object, located: list[dict], where: str) -> list[dict]:
    refs = _texts(value, where)
    if len(set(refs)) != len(refs):
        raise source.BridgeError(f"{where}:duplicate_anchor_ref")
    by_id = {row["id"]: row for row in located}
    if any(ref not in by_id for ref in refs):
        raise source.BridgeError(f"{where}:unknown_anchor_ref")
    return [by_id[ref] for ref in refs]


def _anchored_model(item: object, evidence: tuple[a.Evidence, ...]) -> object:
    """Replace provenance, preserving every submitted proposition and scope field."""
    if isinstance(item, a.Literal):
        return dataclasses.replace(
            item,
            evidence=evidence,
            qualifiers=_anchored_model(item.qualifiers, evidence),
            time=dataclasses.replace(item.time, evidence=evidence) if item.time is not None else None,
        )
    if isinstance(item, a.AllOf | a.AnyOf):
        return dataclasses.replace(item, parts=tuple(_anchored_model(p, evidence) for p in item.parts))
    if isinstance(item, a.Not):
        return dataclasses.replace(item, part=_anchored_model(item.part, evidence))
    return item


def _assumption(raw: dict, anchors: list[dict]) -> dict:
    item = _model(raw, a.ScopedAssertion, "assumption")
    refs = tuple(row["ref"] for row in anchors)
    evidence = tuple(
        a.Evidence("text_span" if "span" in row else "record_field", row["ref"]) for row in anchors
    )
    spans = tuple(a.Span(row["span"]["start"], row["span"]["end"]) for row in anchors if "span" in row)
    return _plain(
        dataclasses.replace(
            item,
            criterion_ref="|".join(refs),
            span=spans,
            body=_anchored_model(item.body, evidence),
            applicability=_anchored_model(item.applicability, evidence),
            rule=(
                a.UNRESOLVED_RULE
                if item.rule == a.UNRESOLVED_RULE
                else a.Rule("source-anchored-hypothesis", RULE_VERSION, premises=refs, warrants=(HYPOTHESIS,))
            ),
            status="proposed",
        )
    )


def _local_signals(raw: object, anchors: list[dict]) -> list[dict]:
    out = []
    for item in _rows(raw, "signals"):
        row = _object(
            item, {"id", "kind", "data", "support", "bindings"}, {"id", "kind", "data", "support"}, "signal"
        )
        identity = _text(row["id"], "signal.id")
        kind = _text(row["kind"], "signal.kind")
        if not isinstance(row["data"], dict):
            raise source.BridgeError("signal.data:object_required")
        support: list[dict[str, Any]] = []
        for value in _rows(row["support"], "signal.support"):
            entry = _object(
                value,
                {"id", "status", "resolution", "basis"},
                {"id", "status", "resolution", "basis"},
                "support",
            )
            _text(entry["id"], "support.id")
            _texts(entry["basis"], "support.basis")
            if entry["status"] not in a.STATUSES or entry["resolution"] not in a.RESOLUTIONS:
                raise source.BridgeError("support:invalid_standing")
            support.append(
                {**entry, "status": "proposed", "basis": [*(anchor["ref"] for anchor in anchors), HYPOTHESIS]}
            )
        if not support or len({row["id"] for row in support}) != len(support):
            raise source.BridgeError("signal:missing_or_duplicate_support")
        bindings = row.get("bindings", {})
        if not isinstance(bindings, dict) or len(bindings) > MAX_ITEMS:
            raise source.BridgeError("signal.bindings:object_required")
        bound = {
            _text(ref, "signal.binding"): _model(body, a.PROPOSITIONS, "signal.binding")
            for ref, body in bindings.items()
        }
        # Operators validate their complete typed data; proposed support cannot constrain a design.
        signals.evaluate(
            signals.Signal(
                identity,
                kind,
                row["data"],
                tuple(
                    signals.Support(p["id"], p["status"], p["resolution"], tuple(p["basis"])) for p in support
                ),
                bound,
            )
        )
        evidence = tuple(
            a.Evidence("text_span" if "span" in anchor else "record_field", anchor["ref"])
            for anchor in anchors
        )
        out.append(
            {
                **row,
                "support": support,
                "bindings": {ref: _plain(_anchored_model(body, evidence)) for ref, body in bound.items()},
            }
        )
    if len({row["id"] for row in out}) != len(out):
        raise source.BridgeError("signals:duplicate_id")
    return out


def _frames(raw: object, located: list[dict], items: int) -> list[dict]:
    out = []
    for original in _rows(raw, "interpretations"):
        original = _object(
            original, FRAME_FIELDS, {"id", "label", "origin", "basis", "anchors"}, "interpretation"
        )
        anchors = _selected_anchors(original["anchors"], located, "interpretation.anchors")
        row = _object(
            source.hydrate(original, anchors),
            FRAME_FIELDS,
            {"id", "label", "origin", "basis", "anchors"},
            "interpretation",
        )
        for field in ("assumptions", "signals", "signal_claims", "binding_uses"):
            items += len(_rows(row.get(field, []), field))
        if items > MAX_ITEMS:
            raise source.BridgeError("resource_bound:source_assertions")
        for name in ("id", "label"):
            _text(row[name], "interpretation." + name)
        if row["origin"] not in ("assistant", "user", "source"):
            raise source.BridgeError("interpretation:unsupported_origin")
        _texts(row["basis"], "interpretation.basis")
        assumptions = [_assumption(item, anchors) for item in row.get("assumptions", [])]
        if len({item["id"] for item in assumptions}) != len(assumptions):
            raise source.BridgeError("assumptions:duplicate_id")
        local_signals = _local_signals(row.get("signals", []), anchors)
        claims = []
        for value in _rows(row.get("signal_claims", []), "signal_claims"):
            claim = _object(value, {"signal", "claim"}, {"signal", "claim"}, "signal_claim")
            if claim["signal"] not in {s["id"] for s in local_signals}:
                raise source.BridgeError("signal_claim:unknown_signal")
            if not isinstance(claim["claim"], dict):
                raise source.BridgeError("signal_claim:object_required")
            target = next(s for s in local_signals if s["id"] == claim["signal"])
            signals.operator(target["kind"]).check(target["kind"], target["data"], [claim["claim"]])
            claims.append(claim)
        out.append(
            {
                "id": row["id"],
                "label": row["label"],
                "origin": row["origin"],
                "basis": [*(anchor["ref"] for anchor in anchors), HYPOTHESIS],
                "assumptions": assumptions,
                "signals": local_signals,
                "signal_claims": claims,
                "binding_uses": row.get("binding_uses", []),
            }
        )
    if len({row["id"] for row in out}) != len(out):
        raise source.BridgeError("interpretations:duplicate_id")
    return out


def _bindings(raw: object, located: list[dict], study_ref: str) -> list[dict]:
    out = []
    fields = set(interpretation_bindings.BINDING_FIELDS)
    for original in _rows(raw, "bindings"):
        original = _object(original, fields | {"anchors"}, fields | {"anchors"}, "binding")
        anchors = _selected_anchors(original["anchors"], located, "binding.anchors")
        row = _object(
            source.hydrate(original, anchors), fields | {"anchors"}, fields | {"anchors"}, "binding"
        )
        # Validate the submitted shape before replacing caller provenance and standing.
        interpretation_bindings.parse_bindings([{k: row[k] for k in fields}], study_ref)
        out.append(
            {
                **{k: row[k] for k in fields},
                "status": "proposed",
                "sources": [anchor["source"] for anchor in anchors],
                "basis": [*(anchor["ref"] for anchor in anchors), HYPOTHESIS],
            }
        )
    interpretation_bindings.parse_bindings(out, study_ref)
    return out


def _age_floor(study: dict, snapshot: dict) -> tuple[list[dict], list[dict]]:
    fixed = []
    coverage = []
    protocol = study.get("protocolSection")
    if not isinstance(protocol, dict):
        code = "missing" if "protocolSection" not in study else "null" if protocol is None else "malformed"
        return [], [{"address": "/protocolSection", "code": code, "value": deepcopy(protocol)}]
    module = protocol.get("eligibilityModule")
    if not isinstance(module, dict):
        code = "missing" if "eligibilityModule" not in protocol else "null" if module is None else "malformed"
        return [], [
            {"address": "/protocolSection/eligibilityModule", "code": code, "value": deepcopy(module)}
        ]
    for field, comparison in AGE_FIELDS.items():
        value = module.get(field)
        address = "/protocolSection/eligibilityModule/" + field
        code = age_state(field in module, value)
        row = {"address": address, "code": code, "value": deepcopy(value)}
        coverage.append(row)
        if code != "compiled":
            continue
        number, unit = value.split(" ")
        ref = snapshot["study_ref"] + "#" + address
        item = a.ScopedAssertion(
            "registry-age-" + field,
            ref,
            "required",
            a.Literal(
                a.Subject("participant"),
                a.Predicate("measurement", "age"),
                a.Value("quantity", comparison, number=int(number), unit=unit),
                evidence=(a.Evidence("record_field", ref),),
            ),
            rule=a.Rule("ctg-structured-general-eligibility-age", RULE_VERSION, premises=(ref,)),
            status="known",
            resolution="resolved",
        )
        fixed.append(_plain(item))
        row.update(assertion=item.id, rule="ctg-structured-general-eligibility-age", ref=ref)
    for field, value in module.items():
        if field not in AGE_FIELDS:
            escaped = field.replace("~", "~0").replace("/", "~1")
            coverage.append(
                {
                    "address": "/protocolSection/eligibilityModule/" + escaped,
                    "code": "unresolved_retained",
                    "value": deepcopy(value),
                }
            )
    return fixed, coverage


def _uncompiled_roots(study: dict, snapshot: dict) -> list[dict]:
    """Name retained study regions outside the direct compiler without duplicating their contents."""
    addresses = []
    for field in study:
        escaped = field.replace("~", "~0").replace("/", "~1")
        if field != "protocolSection":
            addresses.append("/" + escaped)
    protocol = study.get("protocolSection")
    if isinstance(protocol, dict):
        for field in protocol:
            if field != "eligibilityModule":
                escaped = field.replace("~", "~0").replace("/", "~1")
                addresses.append("/protocolSection/" + escaped)
    return [
        {
            "address": address,
            "ref": snapshot["study_ref"] + "#" + address,
            "code": "unresolved_retained",
            "reason": "outside_structured_age_direct_rules",
        }
        for address in sorted(addresses)
    ]


def _request_budget(request: dict, fixed_count: int) -> int:
    """Bound declared objects and repeated solver work before compiling frame contents."""
    frames = _rows(request.get("interpretations", []), "interpretations")
    bindings = _rows(request.get("bindings", []), "bindings")
    queries = _rows(request.get("queries", []), "queries")
    items = fixed_count + len(frames) + len(bindings) + len(queries)
    if items > MAX_ITEMS or len(queries) * (len(frames) + 1) > MAX_ITEMS:
        raise source.BridgeError("resource_bound:source_assertions")
    return items


def _prepare(request: dict) -> dict:
    """Prepare inspectable source-bound requests without executing a reasoning service."""
    _object(request, REQUEST_FIELDS, {"operation", "study"}, "request")
    if request["operation"] != "source_assertions":
        raise source.BridgeError("unsupported_operation")
    snapshot = source.snapshot(request["study"])
    if "expected_digest" in request and request["expected_digest"] != snapshot["digest"]:
        raise source.BridgeError("source_digest_mismatch")
    located = source.anchors(request["study"], snapshot, request.get("anchors", []))
    fixed, coverage = _age_floor(request["study"], snapshot)
    coverage.extend(_uncompiled_roots(request["study"], snapshot))
    items = _request_budget(request, len(fixed))
    frames = _frames(request.get("interpretations", []), located, items)
    bindings = _bindings(request.get("bindings", []), located, snapshot["study_ref"])
    parsed_bindings = interpretation_bindings.parse_bindings(bindings, snapshot["study_ref"])
    for frame in frames:
        if any(item["id"] in {row["id"] for row in fixed} for item in frame["assumptions"]):
            raise source.BridgeError("assumptions:duplicate_fixed_id")
        interpretation_bindings.parse_uses(
            frame["binding_uses"],
            parsed_bindings,
            {row["id"] for row in frame["signals"]},
            snapshot["study_ref"],
        )
    queries = []
    for value in _rows(request.get("queries", []), "queries"):
        row = _object(source.hydrate(value, located), {"id", "body"}, {"id", "body"}, "query")
        _text(row["id"], "query.id")
        _model(row["body"], a.PROPOSITIONS, "query.body")
        queries.append(row)
    if len({row["id"] for row in queries}) != len(queries):
        raise source.BridgeError("queries:duplicate_id")
    if "selected" in request and not frames:
        raise source.BridgeError("selected_without_interpretations")
    if "selected" in request and request["selected"] not in {frame["id"] for frame in frames}:
        raise source.BridgeError("unknown_selected_interpretation")
    if "context" in request:
        context = _object(request["context"], {"cohort", "arm", "phase"}, set(), "context")
        for key, item in context.items():
            if item is not None:
                _text(item, "context." + key)
    if "bound" in request and (type(request["bound"]) is not int or not 1 <= request["bound"] <= 65536):
        raise source.BridgeError("invalid_resource_bound")
    options = {key: deepcopy(request[key]) for key in ("context", "bound") if key in request}
    requests = []
    if queries and frames:
        requests = [
            {
                "operation": "interpretations",
                "study_ref": snapshot["study_ref"],
                "fixed": {"assertions": fixed, "signals": []},
                "bindings": bindings,
                "interpretations": frames,
                "queries": queries,
                **options,
                **({"selected": request["selected"]} if "selected" in request else {}),
            }
        ]
    elif queries:
        requests = [
            {"operation": "entailment", "assertions": fixed, "query": query["body"], **options}
            for query in queries
        ]
    return {
        "source": snapshot,
        "anchors": located,
        "fixed": {"assertions": fixed, "signals": []},
        "interpretations": frames,
        "bindings": bindings,
        "coverage": coverage,
        "submitted": {
            "interpretations": deepcopy(request.get("interpretations", [])),
            "bindings": deepcopy(request.get("bindings", [])),
        },
        "requests": requests,
        "limits": [
            "Structured ages describe registry general eligibility, not verified actual protocol.",
            "A located quotation proves quotation only; clinical readings remain hypothetical.",
            "No unit conversion, automatic binding joins, clinical text interpretation or source mutation.",
        ],
    }


def prepare(request: dict) -> dict:
    """Return a detached compilation or a named bridge refusal, never a service call."""
    try:
        return _prepare(request)
    except source.BridgeError:
        raise
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        raise source.BridgeError(str(error)) from error
