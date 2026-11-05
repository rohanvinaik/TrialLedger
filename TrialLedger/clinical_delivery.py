"""Common readable delivery over canonical reasoning; no new clinical premises."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from copy import deepcopy

from TrialLedger.record_access import DEFAULT_BYTES, MAX_BYTES, MIN_BYTES, response_bytes

INTENTS = ("unspecified", "compatibility", "necessity", "consistency", "description", "decision")


def augment(response: dict) -> dict:
    """Add one shared clinical projection and summary, retaining every original result field."""
    from TrialLedger.layer2 import clinical_answers
    from TrialLedger.layer2.session_state import digest

    operation = response["operation"]
    if operation == "describe":
        return {
            "summary": {"kind": "discovery", "code": response["code"], "operation": operation},
            **response,
        }
    clinical = clinical_answers.project(operation, response["result"], response["problems"])
    dispositions = Counter(row["disposition"] for row in clinical["findings"])
    summary = {
        "kind": ("inspection" if operation == "prepare" else "reasoning")
        if response["code"] == "complete"
        else "refusal",
        "code": response["code"],
        "operation": operation,
        "findings": len(clinical["findings"]),
        "dispositions": dict(sorted(dispositions.items())),
        "problems": deepcopy(response["problems"]),
    }
    if "answer_diff" in response:
        changes = response["answer_diff"]
        summary["changes"] = (
            {kind: dict(Counter(row["code"] for row in changes.get(kind, []))) for kind in changes}
            if isinstance(changes, dict)
            else None
        )
    reply = {"summary": summary, "clinical": clinical, **response}
    if operation == "design_session" and response["code"] == "complete":
        from TrialLedger.clinical_view import build

        reply["decision_view"] = build(response)
        if isinstance(response.get("result"), dict) and "protocol" in response["result"]:
            reply["protocol_view"] = protocol_delivery_view(response["result"])
    if response["code"] == "complete":
        reply["result_digest"] = digest(response["result"])
        reply["result_digest_scope"] = "result only; excludes summary, presentation and artifact metadata"
    return reply


# Delivery order for protocol findings (interface delivery.md): known conflicts first, then repair choices,
# so a bounded reply can never lose them silently behind lower-priority items.
FINDING_PRIORITY = (
    "conflict",
    "repair_choice",
    "signal_finding",
    "unresolved_projection",
    "not_computed",
    "claim_unsettled",
    "claim_conditional",
    "section",
)


WITNESS_CHARACTERS = 240


def finding_priority_kind(kind: str, outcome: str | None) -> str:
    """Delivery class of one view open item; a failure splits into conflict or repair choice (pure).

    post: __return__ in FINDING_PRIORITY or __return__ == kind
    post: kind != "claim_failure" or __return__ in ("conflict", "repair_choice")
    """
    # Imported here, not at module level: reporting modules never load the reasoning engine on import.
    from TrialLedger.layer2.protocol_outcomes import CONFLICT_OUTCOMES

    if kind == "claim_failure":
        return "conflict" if outcome in CONFLICT_OUTCOMES else "repair_choice"
    return kind


def protocol_condition_words(conditions: list[dict]) -> str:
    """Display the actual conjoined assessment conditions; no name-based interpretation or admission."""
    from TrialLedger.clinical_display import proposition

    rendered = []
    for entry in conditions:
        text = proposition(entry["condition"])["text"]
        wording = f"{entry['object']}: {text}"
        if wording not in rendered:
            rendered.append(wording)
    return "; AND ".join(rendered)


def _protocol_delivery_items(items: list[dict], checks: list[dict]) -> list[dict]:
    """Consolidate repeated remedies without discarding their original canonical rows or references."""
    by_id = {check["id"]: check for check in checks}
    claims = {(check["id"], c["id"]): c for check in checks for c in check["claims"]}
    out: list[dict] = []
    exact: dict[tuple, dict] = {}
    conditional: dict[tuple, dict] = {}
    for item in items:
        key = tuple(item.get(k) for k in ("check", "claim", "text", "ref"))
        if key in exact:
            held = exact[key]
            held.setdefault("members", [deepcopy(held)]).append(deepcopy(item))
            continue
        claim = claims.get((item["check"], item["claim"])) or {}
        if item["kind"] == "claim_conditional" and claim.get("effective_outcome") == "satisfied":
            group = (item["check"], item["ref"])
            if group in conditional:
                held = conditional[group]
                held["members"].append(deepcopy(item))
                held["claims"].append(item["claim"])
                exact[key] = held
                continue
            words = protocol_condition_words(by_id[item["check"]]["conditions"])
            held = {
                **item,
                "claim": None,
                "claims": [item["claim"]],
                "members": [deepcopy(item)],
                "text": f"Check {item['check']}: satisfied claims remain conditional on "
                + (words or "the declared assessment condition")
                + ". Applicability is not established by these calculations.",
            }
            conditional[group] = held
        else:
            held = deepcopy(item)
        out.append(held)
        exact[key] = held
    return out


def protocol_delivery_view(result: dict) -> dict:
    """The one clinical protocol view plus its delivery ordering and decision summaries; no recomputation."""
    from TrialLedger.layer2 import protocol_view
    from TrialLedger.layer2.protocol_outcomes import CONFLICT_OUTCOMES

    view = protocol_view.view(result)
    outcomes = {(c["id"], claim["id"]): claim["outcome"] for c in view["checks"] for claim in c["claims"]}
    ordered = []
    for index, item in enumerate(view["open_items"]):
        kind = finding_priority_kind(item["kind"], outcomes.get((item["check"], item["claim"])))
        rank = FINDING_PRIORITY.index(kind) if kind in FINDING_PRIORITY else len(FINDING_PRIORITY)
        ordered.append((rank, index, {**item, "class": kind}))
    witnesses = {
        (c["id"], claim["id"]): claim.get("witness_wording") for c in view["checks"] for claim in c["claims"]
    }
    for _, _, row in ordered:
        witness = witnesses.get((row["check"], row["claim"]))
        if witness:
            # Bounded for the compact budget; a cut one says so and the full sentence stays at the result.
            row["witness"] = (
                witness if len(witness) <= WITNESS_CHARACTERS else witness[:WITNESS_CHARACTERS] + "…"
            )
            row["witness_truncated"] = len(witness) > WITNESS_CHARACTERS
    view["delivery_findings"] = _protocol_delivery_items(
        [row for _, _, row in sorted(ordered, key=lambda r: (r[0], r[1]))], view["checks"]
    )
    view["check_summaries"] = [
        {
            "id": check["id"],
            "kind": check["kind"],
            "required": check["required"],
            "code": (check.get("summary") or {}).get("code")
            or ("refused" if check.get("refusals") else None),
            "conflicts": sum(
                1
                for claim in check["claims"]
                if claim["admission"] == "accepted"
                and claim["outcome"] in CONFLICT_OUTCOMES
                and claim["application"] != "not_applicable"
            ),
            "repairs": sum(
                1
                for item in view["delivery_findings"]
                if item["check"] == check["id"] and item["class"] == "repair_choice"
            ),
            "conditional": any(claim["application"] == "conditional" for claim in check["claims"])
            or any(row.get("application") == "conditional" for row in check["findings"])
            or any(row.get("application") == "conditional" for row in check["clean_signals"]),
            "standing": check["standing"],
            "resolution": check["resolution"],
            "resolution_causes": list(check["resolution_causes"]),
            **(
                {
                    "condition_wording": protocol_condition_words(check["conditions"]),
                    "condition_ref": f"/response/result/protocol/checks/{index}",
                }
                if check.get("conditions")
                else {}
            ),
            **(
                {"source_readings": deepcopy(check["source_readings"])}
                if check.get("source_readings")
                else {}
            ),
        }
        for index, check in enumerate(view["checks"])
    ]
    schedule = {row["check"]: row for row in view["schedule"]}
    checks = {row["id"]: row for row in view["checks"]}
    view["decisions"] = [
        {
            "id": d["id"],
            "question": d["question"],
            "disposition": d["disposition"],
            "selected": deepcopy(d.get("selected")),
            "alternatives": [_alternative_row(a, schedule, checks) for a in d["alternatives"]],
        }
        for d in result["protocol"].get("decisions", [])
    ]
    return view


def _effective(claim: dict) -> str:
    """An alternative claim's effective outcome: as retained, else unresolved when its support is refused."""
    if claim.get("effective_outcome") is not None:
        return claim["effective_outcome"]
    return claim["outcome"] if claim.get("admission") == "accepted" else "unresolved"


def _check_reason(check: dict, baseline: dict | None) -> str:
    """Why one alternative check is not clean: its own claims, or the declared check's not-computed items."""
    from TrialLedger.layer2 import protocol_view

    claims = check.get("claims", [])
    refused = [c for c in claims if c.get("admission") != "accepted"]
    if not claims and not check.get("children") and baseline is not None:
        items = [
            i["text"].removeprefix("No finding: ").rstrip(".") for i in baseline.get("not_computed_items", [])
        ]
        if items:
            return "; ".join(items)
    if refused:
        words = protocol_view.ADMISSION_WORDS
        default = "its support is not accepted"
        return "; ".join(
            f"claim {c['id']} not applied: {words.get(str(c.get('admission')), default)}" for c in refused
        )
    if not claims:
        return "no claim outcomes retained for this check"
    return "; ".join(f"claim {c['id']}: {protocol_view.outcome_words(_effective(c))}" for c in claims)


def _alternative_row(alternative: dict, schedule: dict, checks: dict | None = None) -> dict:
    """One alternative with its own claim outcomes, retained schedule windows and retained binomial plans.

    Windows and statistics are read from each child's retained `schedule` / `statistics` values (the
    alternative's own result). A claim shows its effective outcome and admission, never the raw outcome as if
    applied. When nothing is retained the row says so; nothing is computed here.
    """
    from TrialLedger.layer2 import protocol_view

    rows, claims, deciding, statistics = [], [], [], []
    for check in alternative.get("checks", []):
        values = [v for child in check.get("children", []) for v in child.get("schedule") or []]
        source = schedule.get(check["id"])
        if source is not None or values:
            rows.append(
                {
                    "check": check["id"],
                    "retained": bool(values),
                    **{
                        key: (protocol_view.window_texts(values[0])[key] if values else None)
                        for key in ("permitted", "availability", "feasible", "full_coverage_gap")
                    },
                    "unit": values[0].get("unit") if values else (source or {}).get("unit"),
                    "anchor": values[0].get("anchor") if values else (source or {}).get("anchor"),
                }
            )
        statistics += [
            {"check": check["id"], "text": protocol_view.statistics_text(stat), **stat}
            for child in check.get("children", [])
            for stat in child.get("statistics") or []
        ]
        deciding.append(
            {
                "check": check["id"],
                "required": check.get("required", False),
                "check_code": check.get("check_code"),
                "reason": _check_reason(check, (checks or {}).get(check["id"])),
            }
        )
        claims += [
            {
                "check": check["id"],
                "id": claim["id"],
                "claim": claim["claim"],
                "outcome": claim["outcome"],
                "effective_outcome": _effective(claim),
                "admission": claim.get("admission"),
                "standing": claim["finding_status"],
                "assumed": list(claim.get("assumed", [])),
            }
            for claim in check.get("claims", [])
        ]
    return {
        "id": alternative["id"],
        "label": alternative["label"],
        "frame": alternative["frame"],
        "compatibility": alternative["compatibility"],
        "conditional_checks": list(alternative.get("conditional_checks", [])),
        "assumption_refs": list(alternative.get("assumption_refs", [])),
        "unconditional_application": alternative["unconditional_application"],
        "windows": rows,
        "claim_outcomes": claims,
        "deciding_checks": deciding,
        "statistics": statistics,
        **(
            {"source_readings": deepcopy(alternative["source_readings"])}
            if alternative.get("source_readings")
            else {}
        ),
    }


def present(response: dict, *, intent: str = "unspecified", question: str = "") -> dict:
    """A declared clinical question guides wording; it never changes a logical outcome."""
    if not isinstance(intent, str) or intent not in INTENTS:
        raise ValueError("unsupported_question_intent")
    if not isinstance(question, str) or len(question) > 4096:
        raise ValueError("invalid_clinical_question")
    if intent == "unspecified" and not question:
        return dict(response)
    return {
        **response,
        "presentation": {
            "intent": intent,
            "question": question,
            "origin": "caller_declared_question; not authenticated confirmation",
        },
    }


def compact_budget_code(value: object) -> str:
    """Only integer reply budgets in the supported inclusive range are admitted.

    post: __return__ in ('valid_compact_budget', 'max_bytes_out_of_range')
    """
    if type(value) is not int or not MIN_BYTES <= value <= MAX_BYTES:
        return "max_bytes_out_of_range"
    return "valid_compact_budget"


def _compact_finding(row: dict, address: str) -> dict:
    """Keep decision channels; the exact scope and full support remain at their source address."""
    fields = ("path", "kind", "outcome", "status", "standing", "disposition", "completion", "blockers")
    return {
        **{key: deepcopy(row[key]) for key in fields if key in row},
        "scope_ref": address + "/scope",
        "canonical_ref": address,
    }


def _compact_change(row: dict, address: str) -> dict:
    """Preserve every change axis without echoing before/after projections."""
    fields = ("id", "code", "changes", "axes", "limited")
    return {**{key: deepcopy(row[key]) for key in fields if key in row}, "canonical_ref": address}


def _compact_decision(row: dict, address: str) -> dict:
    """Overview of a coherent stored view, with no shortened source excerpts."""
    fields = ("id", "caller_question", "decision_code", "selected", "coverage")
    return {
        **{key: deepcopy(row[key]) for key in fields if key in row},
        "options_count": len(row.get("options", [])),
        "evidence_count": len(row.get("evidence", [])),
        "canonical_ref": address,
    }


def _compact_edit(row: dict, address: str) -> dict:
    from TrialLedger.layer2.session_state import digest

    return {
        "path": row["path"],
        "before_digest": digest(row["before"]),
        "after_digest": digest(row["after"]),
        "canonical_ref": address,
        **({"mechanical": row["mechanical"]} if "mechanical" in row else {}),
    }


def _compact_page(total: int, returned: int = 0) -> dict:
    return {
        "offset": 0,
        "returned": returned,
        "total": total,
        "next_offset": returned if returned < total else None,
    }


_Group = tuple[list, dict, list, str, Callable[[dict, str], dict]]
REPLY_RESERVE = 128


def _with_address(row: dict, address: str) -> dict:
    return {**deepcopy(row), "canonical_ref": address}


def _compact_header(response: dict, artifact: dict, max_bytes: int) -> dict:
    return {
        "code": response["code"],
        "operation": response["operation"],
        "artifact": {key: artifact[key] for key in ("id", "bytes", "schema_version") if key in artifact},
        "view": "compact",
        "max_bytes": max_bytes,
        "canonical_ref": "/response",
        "canonical_result": "Full request/response retained unchanged. Read canonical_ref with "
        "reason_result part address; follow page.next_offset.",
    }


def _compact_preparation(preparation: dict) -> dict:
    out = {
        "artifact": preparation["artifact"],
        "meaning": preparation["meaning"],
        "defaults": len(preparation["defaults"]),
        "origins": len(preparation["origins"]),
        "canonical_ref": "/response/preparation",
    }
    if "applies_to" in preparation:
        out["applies_to"] = preparation["applies_to"]
    return out


def _decision_view_groups(response: dict, reply: dict) -> list[_Group]:
    if "decision_view" not in response:
        return []
    rows = response["decision_view"]
    section = {"decisions": [], "page": _compact_page(len(rows)), "canonical_ref": "/response/decision_view"}
    reply["decision_view"] = section
    return [(section["decisions"], section["page"], rows, section["canonical_ref"], _compact_decision)]


def _answer_diff_groups(response: dict, reply: dict) -> list[_Group]:
    if not isinstance(response.get("answer_diff"), dict):
        if "answer_diff" in response:
            reply["answer_diff"] = (
                None
                if response["answer_diff"] is None
                else {"navigation": "exact_artifact", "canonical_ref": "/response/answer_diff"}
            )
        return []
    changes = response["answer_diff"]
    section: dict = {"canonical_ref": "/response/answer_diff", "pages": {}}
    reply["answer_diff"] = section
    groups: list[_Group] = []
    for kind in changes:
        rows = changes.get(kind, [])
        shown_changes: list = []
        change_page = _compact_page(len(rows))
        section[kind] = shown_changes
        section["pages"][kind] = change_page
        groups.append((shown_changes, change_page, rows, f"/response/answer_diff/{kind}", _compact_change))
    return groups


def _protocol_block(view: dict) -> dict:
    return {
        "canonical_ref": "/response/protocol_view",
        "sections": [
            {key: row[key] for key in ("id", "declared", "coverage", "findings", "findings_text")}
            for row in view["sections"]
        ],
        "decisions": [
            {
                "id": d["id"],
                "disposition": d["disposition"],
                "alternatives": [
                    {key: a[key] for key in ("id", "label", "compatibility")} for a in d["alternatives"]
                ],
            }
            for d in view["decisions"]
        ],
        "findings": [],
        "checks": [],
        "pages": {
            "findings": _compact_page(len(view["delivery_findings"])),
            "checks": _compact_page(len(view["check_summaries"])),
        },
    }


def _protocol_groups(response: dict, reply: dict) -> list[_Group]:
    if "protocol_view" not in response:
        return []
    view = response["protocol_view"]
    protocol = _protocol_block(view)
    reply["protocol"] = protocol
    return [
        (
            protocol["findings"],
            protocol["pages"]["findings"],
            view["delivery_findings"],
            "/response/protocol_view/delivery_findings",
            _with_address,
        ),
        (
            protocol["checks"],
            protocol["pages"]["checks"],
            view["check_summaries"],
            "/response/protocol_view/check_summaries",
            _with_address,
        ),
    ]


def _clinical_groups(response: dict, reply: dict) -> list[_Group]:
    if "clinical" not in response:
        return []
    clinical = response["clinical"]
    rows = clinical["findings"]
    section = {
        "version": clinical["version"],
        "operation": clinical["operation"],
        "findings": [],
        "page": _compact_page(len(rows)),
        "canonical_ref": "/response/clinical/findings",
    }
    reply["clinical"] = section
    return [(section["findings"], section["page"], rows, section["canonical_ref"], _compact_finding)]


def _delivery_groups(response: dict, reply: dict) -> list[_Group]:
    if "delivery" not in response:
        return []
    delivery = response["delivery"]
    rows = delivery["edits"]
    section = {
        "previous_artifact": delivery["previous_artifact"],
        "edits": [],
        "page": _compact_page(len(rows)),
        "canonical_ref": "/response/delivery/edits",
    }
    reply["delivery"] = section
    return [(section["edits"], section["page"], rows, section["canonical_ref"], _compact_edit)]


def _degraded_reply(
    response: dict, artifact: dict, max_bytes: int, reply: dict, groups: list[_Group]
) -> dict:
    """The navigation-only reply when even the summaries do not fit the budget."""
    degraded = {
        "code": response["code"],
        "operation": response["operation"],
        "artifact": {"id": artifact["id"]},
        "view": "compact",
        "max_bytes": max_bytes,
        "navigation": "exact_artifact",
        "canonical_ref": "/response",
        "pages": {address: _compact_page(len(rows)) for _shown, _page, rows, address, _project in groups},
        "omitted_fields": reply["omitted_fields"],
    }
    if "protocol_view" in response:
        # The protocol block did not fit: name it as omitted, keep the counts that matter, say where
        # the rest is retained.
        summaries = response["protocol_view"]["check_summaries"]
        degraded["omitted_fields"] = [*reply["omitted_fields"], "protocol"]
        degraded["protocol_omitted"] = {
            "conflicts": sum(c["conflicts"] for c in summaries),
            "repair_choices": sum(c["repairs"] for c in summaries),
            "canonical_ref": "/response/protocol_view",
        }
    return degraded


def _restore_omitted_fields(response: dict, reply: dict, max_bytes: int) -> None:
    """Return each omitted summary field whole when it still fits the budget."""
    for key in tuple(reply["omitted_fields"]):
        if key == "diagnostics":
            continue
        reply[key] = deepcopy(response[key])
        if response_bytes(reply) <= max_bytes - REPLY_RESERVE:
            reply["omitted_fields"].remove(key)
        else:
            del reply[key]


def _admit_rows(reply: dict, groups: list[_Group], max_bytes: int) -> None:
    """Round-robin one row per group while the reply fits; a rejected row is removed, never shortened."""
    active = list(groups)
    while active:
        following = []
        for shown, page, rows, address, project in active:
            index = len(shown)
            if index == len(rows):
                continue
            shown.append(project(rows[index], f"{address}/{index}"))
            page.update(_compact_page(len(rows), len(shown)))
            if response_bytes(reply) > max_bytes - REPLY_RESERVE and "witness" in shown[-1]:
                # The worded example trace is optional: drop it before dropping the finding, and say so.
                shown[-1] = {
                    **{k: v for k, v in shown[-1].items() if k not in ("witness", "witness_truncated")},
                    "witness_omitted": True,
                }
            if response_bytes(reply) <= max_bytes - REPLY_RESERVE:
                following.append((shown, page, rows, address, project))
            else:
                shown.pop()
                page.update(_compact_page(len(rows), len(shown)))
        active = following


def compact(response: dict, artifact: dict, *, max_bytes: int = DEFAULT_BYTES) -> dict:
    """Bound a retained reply and expose exact navigation for every omitted field and row.

    The conservative counter includes pretty whitespace and escaped Unicode. The reserved 128 bytes
    cover the MCP tool-name field and CLI trailing newline. No source value is shortened.
    """
    from TrialLedger.reasoning_artifacts import artifact_id_code

    code = compact_budget_code(max_bytes)
    if code != "valid_compact_budget":
        raise ValueError(code)
    if type(artifact) is not dict or artifact_id_code(artifact.get("id")) != "valid_artifact_id":
        raise ValueError("compact_requires_canonical_artifact")
    reply = _compact_header(response, artifact, max_bytes)
    if "preparation" in response:
        reply["preparation"] = _compact_preparation(response["preparation"])
    # A group admits a contiguous prefix. If a summary cannot fit, next_offset still names that row.
    # Each channel gets a turn; a long finding list cannot crowd out every revision or decision row.
    groups: list[_Group] = [
        *_decision_view_groups(response, reply),
        *_answer_diff_groups(response, reply),
        *_protocol_groups(response, reply),
        *_clinical_groups(response, reply),
        *_delivery_groups(response, reply),
    ]
    fields = (
        "summary",
        "problems",
        "result_digest",
        "result_digest_scope",
        "presentation",
        "diagnostics",
        "input_diagnostics",
    )
    reply["omitted_fields"] = [key for key in fields if key in response]
    if response_bytes(reply) > max_bytes - REPLY_RESERVE:
        return _degraded_reply(response, artifact, max_bytes, reply, groups)
    _restore_omitted_fields(response, reply, max_bytes)
    _admit_rows(reply, groups, max_bytes)
    protocol = reply.get("protocol")
    if protocol is not None:
        # Truncation names what it omitted; every omitted row stays reachable at its canonical address.
        protocol["omitted"] = {
            name: page["total"] - page["returned"] for name, page in protocol["pages"].items()
        }
    return reply
