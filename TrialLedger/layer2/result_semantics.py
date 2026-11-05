"""Additive, per-finding descriptions of existing reasoning results.

Adapters name the actual result owners. They never edit clinical payloads, infer
source truth, or turn an open proposition into a person's design choice.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy

from TrialLedger.layer2.entail import weakest_status

CAUSE_KINDS = {
    "coordinate_effect_no_consumer": "translation",
    "coordinate_effect_inactive": "translation",
    "coordinate_effect_withheld": "premise",
    "coordinate_effect_redundant": "constraint",
    "coordinate_effect_narrowed": "constraint",
    "coordinate_effect_guarded": "constraint",
    "selected_out_of_scope": "translation",
    "interpretation_out_of_scope": "translation",
    "interpretation_scope_contrast": "translation",
    "interpretation_answer_contrast": "premise",
    "profile_size_limit": "computation",
    "witness_unresolved": "premise",
    "survivor_inconsistent": "conflict",
    "variable_unrepresented": "translation",
    "unsearched_constraints": "coverage",
    "signs_restricted": "coverage",
    "no_represented_variable": "translation",
    "output_limit": "computation",
    "profile_inconsistent": "translation",
    "OUT_OF_SCOPE": "translation",
    "UNSUPPORTED_QUERY": "unsupported",
    "estimand_missing_support": "premise",
    "estimand_proposed_refused": "premise",
    "estimand_binding_unresolved": "translation",
    "estimand_relevance_unresolved": "translation",
    "estimand_collection_plan_mismatch": "constraint",
    "estimand_availability_conflict": "conflict",
    "estimand_unresolved": "evidence",
    "estimand_missing_relevant": "evidence",
    "estimand_structurally_unavailable": "evidence",
    "estimand_definition_unresolved": "translation",
    "table_uncovered_case": "conflict",
    "table_conflicting_actions": "conflict",
    "table_forbidden_action": "conflict",
    # Protocol operators (connect-protocol-design-workflow). Rohan, 2026-11-04: schedule gaps and an
    # unmet binomial target are the person's repair choice, like estimand_collection_plan_mismatch
    # ("open", constraint); policy failures stay conflicts, like decision-table gaps and forbidden actions.
    "schedule_no_permitted_time": "constraint",
    "schedule_no_feasible_time": "constraint",
    "schedule_outside_window": "constraint",
    "schedule_not_collected": "constraint",
    "schedule_uncovered": "constraint",
    "schedule_unresolved": "evidence",
    "policy_gap": "conflict",
    "policy_competing": "conflict",
    "policy_violation": "conflict",
    "policy_not_established": "conflict",
    "policy_transition_target_infeasible": "conflict",
    "policy_inconsistent_domain": "conflict",
    "policy_work_limit": "computation",
    "binomial_unsupported_method": "unsupported",
    "binomial_assumption_missing": "translation",
    "binomial_claim_not_satisfied": "constraint",
    "binomial_bit_limit": "computation",
    "missing_support": "premise",
    "application_blocked": "translation",
    "definition_analysis_refused": "translation",
    "definition_computation_refused": "computation",
    "definition_empty_antecedent": "translation",
    "definition_proposed_refused": "premise",
    "definition_binding_unresolved": "translation",
    "definition_missing_support": "premise",
    # Protocol checks and relations (trace audit F3).
    "definition_protocol_child_refused": "computation",
    "definition_protocol_child_missing": "translation",
    "projection_scope_mismatch": "translation",
    "projection_scope_too_long": "translation",
    "projection_binding_shape": "translation",
    "projection_slice_5": "translation",
    "projection_collection_plan_conflict": "conflict",
    "adoption_stale_version": "premise",
    "session_work_limit": "computation",
    "external_method_not_computed": "unsupported",
    "stage_scope_mismatch": "translation",
    "stage_unit_mismatch": "translation",
    "stage_binding_unresolved": "translation",
    "stage_total_unknown": "evidence",
    "stage_subset_not_warranted": "premise",
    "exception_upper_unknown": "evidence",
    "exception_bridge_conflict": "conflict",
    "attribution_conflict": "conflict",
    "exception_budget_predicate_mismatch": "translation",
    "missing_entry_attribution": "translation",
    "negative_target_not_eligibility": "translation",
    "profile_mismatch": "translation",
    "population_mismatch": "translation",
    "denominator_mismatch": "translation",
    "source_study_mismatch": "translation",
    "observation_study_mismatch": "translation",
    "binding_study_mismatch": "translation",
    "application_study_mismatch": "translation",
    "observation_version_mismatch": "translation",
    "binding_version_mismatch": "translation",
    "application_version_mismatch": "translation",
    "bridge_proposed": "premise",
    "bridge_unresolved": "translation",
    "binding_proposed": "premise",
    "operator_mismatch": "translation",
    "subjects_mismatch": "translation",
    "subset_not_declared": "translation",
    "partition_not_declared": "translation",
    "definition_not_adopted": "translation",
    "definition_not_found": "translation",
    "definition_version_mismatch": "translation",
    "resource_bound": "computation",
    "proposed_refused": "premise",
    "resolution_unresolved": "premise",
    "standing_not_accepted": "premise",
    "pending_support": "premise",
    "premise_not_resolved": "premise",
    "unresolved_assertion": "premise",
    "conflicting": "premise",
    "interpretation_unresolved": "premise",
    "unresolved_signal": "premise",
    "binding_unresolved": "translation",
    "binding_application_unresolved": "translation",
    "unresolved_rule": "translation",
    "unresolved_scope": "translation",
    "unresolved_literal": "translation",
    "unspecified_boundary": "translation",
    "opaque": "translation",
    "open_scope": "translation",
    "study_mismatch": "translation",
    "scope_mismatch": "translation",
    "scope_incomplete": "translation",
    "query_not_proposition": "unsupported",
    "unsupported_operation": "unsupported",
    "unsupported_domain": "unsupported",
    "below_support": "evidence",
    "insufficient_support": "evidence",
    "class_membership_unresolved": "evidence",
    "unknown_membership": "evidence",
    "rarity_abstained": "evidence",
    "dependency_unresolved": "evidence",
    "dependency_blocked": "conflict",
    "inconsistent_population_total": "conflict",
    "eligibility_frequency_unresolved": "coverage",
    "no_constraint_mentions_query": "coverage",
    "undecided_by_constraints": "constraint",
    "fixed_floor_conflict": "conflict",
    "signal_conflict": "conflict",
    "interpretation_floor_conflict": "conflict",
    "interpretation_refuted": "conflict",
    "interpretation_incoherent": "conflict",
    "selected_interpretation_refused": "premise",
    "request_not_an_object": "invalid",
    "not_an_object": "invalid",
    "not_a_list": "invalid",
    "not_text": "invalid",
    "not_boolean": "invalid",
    "query_proposition_required": "invalid",
}
RESULTS = frozenset(
    (
        "ENTAILED",
        "REFUTED",
        "UNDETERMINED",
        "INCONSISTENT",
        "OUT_OF_SCOPE",
        "UNSUPPORTED_QUERY",
        "CONFLICT",
        "REFUSED",
        "bounded",
        "consistent",
        "permitted_only",
        "feasible",
        "covered",
        "clear",
        "violation",
        "gap",
        "domain_conflict",
        "disjoint",
        "overlap",
        "reachable",
        "unreachable",
        "required",
        "not_required_for_this_estimand",
        "aligned",
        "collection_plan_mismatch",
        "available",
        "missing_relevant",
        "structurally_unavailable",
        "searched",
        "single_survivor",
        "separated",
        "no_separator",
        "not_separated_in_declared_variables",
        "search_incomplete",
        "hypothetical_evidence_request",
        "complete",
        "incomplete",
        "truncated",
        "conflict",
        "unresolved",
        "resolved",
        "unnarrowed",
        "compatible",
        "refuted",
        "incoherent",
        "floor_conflict",
        "conditional",
        "accepted",
        "supported",
        "matched",
        "not_ruled_out",
        "ruled_out",
        "inconsistent",
        "no_witness",
        "witness",
        "computed",
        "proposed",
        "below_support",
        "occupied",
        "empty",
        "unknown",
        "met",
        "not_met",
        "cell",
        "parent",
        "abstain",
        # Protocol operator and claim outcomes (interface operators.md).
        "violated",
        "satisfied",
        "not_satisfied",
        "unsupported_method",
        "limit",
        "inconsistent_domain",
        "no_feasible_time",
        "no_permitted_time",
        "outside_window",
        "not_collected",
        "unknown_target",
        "uncovered",
        "exclusive",
        "competing",
        "not_declared",
        "holds",
        "all_paths_terminate",
        "not_established",
        "not_executed",
    )
)
DISPOSITIONS = frozenset(
    (
        "settled",
        "conditional",
        "conflict",
        "open",
        "not_computed",
        "unsupported",
        "descriptive",
        "translation_question",
        "unclassified",
    )
)


def cause_kind(code: str) -> str:
    """Classify a named cause; unknown codes retain an explicit unknown kind.

    post: __return__ in CAUSE_KINDS.values() or __return__ == 'unclassified'
    """
    return CAUSE_KINDS.get(code.partition(":")[0], "unclassified")


def completion_code(logical_result: str, causes: list[str]) -> str:
    """Whether the named computation completed, independently of its certainty.

    post: __return__ in ('complete', 'limited', 'unsupported', 'invalid', 'unclassified')
    """
    kinds = [cause_kind(code) for code in causes]
    if "computation" in kinds:
        return "limited"
    if logical_result == "UNSUPPORTED_QUERY" or "unsupported" in kinds:
        return "unsupported"
    if logical_result == "REFUSED" and "invalid" in kinds:
        return "invalid"
    if logical_result not in RESULTS or "unclassified" in kinds:
        return "unclassified"
    return "complete"


def disposition_code(logical_result: str, standing: str, completion: str) -> str:
    """Describe a finding without inventing a clinical choice or promoting support.

    post: __return__ in DISPOSITIONS
    """
    if completion in ("unsupported", "invalid"):
        return "unsupported"
    if completion not in ("complete", "limited") or logical_result not in RESULTS:
        return "unclassified"
    if logical_result in (
        "INCONSISTENT",
        "CONFLICT",
        "conflict",
        "inconsistent",
        "refuted",
        "incoherent",
        "floor_conflict",
        "gap",
        "domain_conflict",
        "violation",
        "violated",
        "inconsistent_domain",
        "competing",
        "not_established",
    ):
        return "conflict" if standing in ("known", "interpolated", "proposed") else "unclassified"
    if logical_result in ("not_declared", "not_executed", "unsupported_method", "limit"):
        return "not_computed"
    if logical_result in ("ENTAILED", "REFUTED", "ruled_out"):
        if standing == "known":
            return "settled"
        return "conditional" if standing in ("interpolated", "proposed") else "unclassified"
    if completion == "limited":
        return "not_computed"
    if logical_result in (
        "UNDETERMINED",
        "OUT_OF_SCOPE",
        "unresolved",
        "unnarrowed",
        "unknown",
        "not_ruled_out",
        "no_witness",
        "below_support",
        "abstain",
        "missing_relevant",
        "collection_plan_mismatch",
        "separated",
        "no_separator",
        "not_separated_in_declared_variables",
        "search_incomplete",
        "hypothetical_evidence_request",
        "incomplete",
        "truncated",
        "no_feasible_time",
        "no_permitted_time",
        "outside_window",
        "not_collected",
        "uncovered",
        "unknown_target",
        "not_satisfied",
    ):
        return "open"
    if standing in ("interpolated", "proposed") or logical_result in ("conditional", "proposed"):
        return "conditional"
    if standing != "known":
        return "unclassified"
    return "settled"


def _path(base: str, key: object) -> str:
    return base + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _row(path: str, kind: str, result: str, standing: str | None, blockers: Sequence[str] = ()) -> dict:
    codes = sorted(set(blockers))
    completion = completion_code(result, codes)
    return {
        "path": path,
        "kind": kind,
        "logical_result": result,
        "standing": standing,
        "completion": completion,
        "causes": [{"code": code, "kind": cause_kind(code)} for code in codes],
        "disposition": disposition_code(result, standing or "", completion),
    }


def _decision(row: dict, path: str, kind: str = "logical") -> dict:
    return _row(path, kind, row.get("result", ""), row.get("status"), row.get("blockers", ()))


def _query(row: dict, path: str) -> dict:
    warrant = row.get("warrant", {})
    decision = row.get("decision", {})
    finding = _row(path, "logical", row.get("result", ""), warrant.get("status"), warrant.get("blockers", ()))
    finding["support_path"] = _path(path, "warrant")
    if "contrast" in row:
        finding["contrast_code"] = row["contrast"]["code"]
        finding["contrast_path"] = _path(path, "contrast")
        finding["answer_paths"] = [answer["query_path"] for answer in row["contrast"]["answers"]]
    if decision and decision.get("result") != row.get("result"):
        finding["raw_result"] = decision.get("result")
        finding["raw_path"] = _path(path, "decision")
    return finding


def _signal(row: dict, path: str) -> dict:
    finding = _row(path, "signal", row.get("code", ""), row.get("status"), row.get("blockers", ()))
    if row.get("calculation_code") != row.get("code"):
        finding["raw_result"] = row.get("calculation_code")
        finding["raw_path"] = _path(path, "calculation_code")
    return finding


def _signal_findings(row: dict, path: str) -> list[dict]:
    """Retain stage-local checks under the enclosing signal's actual admission warrant."""
    if row.get("kind") == "decision_table":
        return _table_findings(row, path)
    if row.get("kind") == "estimand":
        return _estimand_findings(row, path)
    if "claim_admission" in row:
        return _protocol_claim_findings(row, path)
    if row.get("kind") != "stages":
        return [_signal(row, path)]
    transitions = row.get("value", {}).get("transitions", [])
    if not transitions:
        return []
    findings = [_signal(row, path)]
    gated = _signal_is_gated(row)
    for index, edge in enumerate(transitions):
        edge_path = _path(_path(_path(path, "value"), "transitions"), index)
        outer = [premise["status"] for premise in row.get("support", ())]
        outer.extend(binding["status"] for binding in row.get("binding_support", ()))
        status = weakest_status(tuple(outer) + (edge["status"],))
        blockers = [*edge["blockers"], *(row["blockers"] if gated else [])]
        finding = _row(
            edge_path, "stage_transition", "unresolved" if gated else edge["code"], status, blockers
        )
        finding["support_path"] = _path(edge_path, "declaration")
        if gated:
            finding["raw_result"] = edge["code"]
            finding["raw_path"] = _path(edge_path, "code")
        elif edge["code"] == "permitted_only" and status == "known":
            finding["disposition"] = "descriptive"
        findings.append(finding)
    return findings


def _protocol_claim_findings(row: dict, path: str) -> list[dict]:
    """One finding per declared protocol claim, admitted on that claim's own deciding support (R1).

    Consumers read these rows, not only the conservative signal summary. A refused row keeps its raw outcome.
    """
    findings = [_signal(row, path)]
    if row.get("kind") == "schedule_coverage" and findings[0]["disposition"] == "conflict":
        # "violated" is shared with policies; a schedule's failures are all repair choices (open).
        findings[0]["disposition"] = "open"
    statuses = {premise["id"]: premise["status"] for premise in row.get("support", ())}
    for index, claim in enumerate(row["claim_admission"]):
        claim_path = _path(_path(path, "claim_admission"), index)
        # The gate's row carries the claim's effective standing, including operator-internal rules.
        # Reconstructing it from outer support alone would turn an interpolated rule into "known".
        if "status" in claim:
            standing = claim["status"]
        else:
            own = tuple(statuses[i] for i in claim.get("support", ()) if i in statuses)
            standing = weakest_status(own) if own else row.get("status")
        admitted = claim["admission"] in ("accepted", "undetermined")
        causes = [] if admitted else [claim["admission"] + ":" + str(claim["id"])]
        finding = _row(claim_path, "protocol_claim", claim["effective_outcome"], standing, causes)
        finding["support_path"] = _path(claim_path, "support")
        finding["determining_ids"] = list(claim.get("determining_ids", ()))
        if not admitted:
            finding["raw_result"] = claim["outcome"]
            finding["raw_path"] = _path(claim_path, "outcome")
        findings.append(finding)
    return findings


def _table_findings(row: dict, path: str) -> list[dict]:
    """Expose completed table checks beside independent unfinished checks and outer gates."""
    findings = [_signal(row, path)]
    gated = _signal_is_gated(row)
    value = row.get("value", {})
    checks = [(name, None, value.get(name)) for name in ("domain", "coverage")]
    checks.extend(
        (name, index, check)
        for name in ("overlaps", "actions", "prohibitions")
        for index, check in enumerate(value.get(name, ()))
    )
    for name, index, check in checks:
        if check is None:
            continue
        check_path = _path(_path(path, "value"), name)
        if index is not None:
            check_path = _path(check_path, index)
        finding = _row(
            check_path,
            "table_" + name,
            "unresolved" if gated else check["state"],
            row.get("status"),
            [*check["blockers"], *(row["blockers"] if gated else [])],
        )
        finding["support_path"] = _path(path, "support")
        if gated:
            finding["raw_result"] = check["state"]
            finding["raw_path"] = _path(check_path, "state")
        elif check.get("same_action") and row.get("status") == "known":
            finding["disposition"] = "descriptive"
        findings.append(finding)
    return findings


def _signal_is_gated(row: dict) -> bool:
    """Consume admission explicitly even when both raw and effective aggregate codes are unresolved."""
    admission = row.get("admission", {})
    return (
        admission.get("code", "accepted") != "accepted"
        or bool(admission.get("application_blockers"))
        or row.get("code") != row.get("calculation_code")
        or ("ungated_code" in row and row["code"] != row["ungated_code"])
    )


def _estimand_findings(row: dict, path: str) -> list[dict]:
    """Consume channel-local states/support rather than spreading an unrelated open definition."""
    value = row.get("value", {})
    requirements = value.get("requirements", [])
    dependencies = value.get("dependency_checks", [])
    if not requirements and not dependencies:
        return []
    findings = [_signal(row, path)]
    gated = _signal_is_gated(row)
    outer = [premise["status"] for premise in row.get("support", ())]
    outer.extend(binding["status"] for binding in row.get("binding_support", ()))

    def append(
        local_path: str, kind: str, code: str, status: str | None, blockers: list, support_path: str
    ) -> None:
        standing = weakest_status(tuple(outer) + (status,)) if status is not None else None
        finding = _row(
            local_path,
            kind,
            "unresolved" if gated else code,
            standing,
            [*blockers, *(row["blockers"] if gated else [])],
        )
        finding["support_path"] = support_path
        if gated:
            finding["raw_result"] = code
            finding["raw_path"] = local_path
        findings.append(finding)

    for index, requirement in enumerate(requirements):
        base = _path(_path(_path(path, "value"), "requirements"), index)
        for field, status, blockers in (
            ("relevance", "relevance_status", "relevance_blockers"),
            ("collection_alignment", "collection_status", "collection_blockers"),
            ("actual_input", "actual_status", "actual_blockers"),
        ):
            append(
                _path(base, field),
                "estimand_" + field,
                requirement[field],
                requirement[status],
                requirement[blockers],
                base,
            )
    for index, check in enumerate(dependencies):
        base = _path(_path(_path(path, "value"), "dependency_checks"), index)
        append(
            _path(base, "code"),
            "estimand_dependency",
            check["code"],
            check["status"],
            check["blockers"],
            _path(base, "deciding_refs"),
        )
    return findings


def _coordinates(result: dict, base: str) -> list[dict]:
    findings = []
    for name, row in result.get("coordinates", {}).items():
        path = _path(_path(base, "coordinates"), name)
        findings.append(_row(path, "coordinate", row.get("state", ""), "known"))
        if "interpolated" in row:
            findings.append(
                _row(
                    _path(path, "interpolated"),
                    "coordinate",
                    row["interpolated"].get("state", ""),
                    "interpolated",
                )
            )
        for index, proposal in enumerate(row.get("proposals", ())):
            findings.append(
                _row(
                    _path(_path(path, "proposals"), index),
                    "coordinate",
                    proposal.get("state", ""),
                    "proposed",
                )
            )
    for index, row in enumerate(result.get("admission", ())):
        code = row.get("code", "")
        findings.append(
            _row(
                _path(_path(base, "admission"), index),
                "admission",
                "accepted" if code == "accepted" else "unresolved",
                row.get("standing", {}).get("status"),
                () if code == "accepted" else (code,),
            )
        )
    for index, effect in enumerate(result.get("effects", ())):
        path = _path(_path(base, "effects"), index)
        finding = _row(
            path,
            "coordinate_effect",
            "computed",
            effect["standing"].get("status"),
            ("coordinate_effect_" + effect["code"],),
        )
        finding["effect"] = effect["code"]
        finding["support_path"] = path
        finding["disposition"] = (
            "translation_question"
            if effect["code"] in ("no_consumer", "inactive")
            else "open"
            if effect["code"] == "withheld"
            else "descriptive"
        )
        findings.append(finding)
    return findings


def _corpus(result: dict, base: str) -> list[dict]:
    findings = []
    for index, row in enumerate(result.get("frequency", ())):
        path = _path(_path(base, "frequency"), index)
        findings.append(_row(path, "corpus_statistic", "computed", "known"))
        if row.get("lower") is not None:
            findings.append(
                _row(
                    _path(path, "tier"),
                    "corpus_eligibility_interval",
                    row.get("tier", ""),
                    "known",
                    ("eligibility_frequency_unresolved",) if row.get("unresolved", 0) else (),
                )
            )
    for field in ("associations", "occupancy"):
        for index, row in enumerate(result.get(field, ())):
            code = row.get("status", "") if field == "associations" else row.get("state", "")
            findings.append(
                _row(
                    _path(_path(base, field), index),
                    "corpus_statistic",
                    code,
                    "proposed" if code == "proposed" else "known",
                    ("below_support",) if code == "below_support" else (),
                )
            )
    for index, _ in enumerate(result.get("near_misses", ())):
        findings.append(
            _row(_path(_path(base, "near_misses"), index), "corpus_comparison", "computed", "known")
        )
    for field in ("association_abstentions", "near_miss_abstentions", "pending"):
        for index, row in enumerate(result.get(field, ())):
            findings.append(
                _row(
                    _path(_path(base, field), index),
                    "admission",
                    "unresolved",
                    row.get("standing", {}).get("status"),
                    (row.get("code", "pending_support"),),
                )
            )
    for index, row in enumerate(result.get("expectations", ())):
        path = _path(_path(base, "expectations"), index)
        rarity = row.get("rarity", ())
        code = rarity[0] if rarity else ""
        findings.append(
            _row(path, "corpus_statistic", code, "known", ("rarity_abstained",) if code == "abstain" else ())
        )
        for pending_index, pending in enumerate(row.get("pending", ())):
            findings.append(
                _row(
                    _path(_path(path, "pending"), pending_index),
                    "admission",
                    "unresolved",
                    pending.get("standing", {}).get("status"),
                    (pending.get("code", "pending_support"),),
                )
            )
    # These are exact descriptions of the declared set, not closure of a clinical decision.
    for finding in findings:
        if finding["disposition"] == "settled":
            finding["disposition"] = "descriptive"
    return findings


def _design_bounds(result: dict, base: str) -> list[dict]:
    findings = []
    for index, candidate in enumerate(result.get("candidates", ())):
        path = _path(_path(base, "candidates"), index)
        query = candidate.get("query_decision", {})
        blockers = _candidate_causes(candidate) if candidate.get("state") == "unresolved" else ()
        findings.append(
            _row(path, "candidate", candidate.get("state", ""), candidate.get("elimination_status"), blockers)
        )
        findings.append(_decision(query, _path(path, "query_decision")))
        for observation_index, row in enumerate(candidate.get("observations", ())):
            observation_path = _path(_path(path, "observations"), observation_index)
            blockers = list(row.get("decision", {}).get("blockers", ()))
            if row.get("support") in ("proposed_refused", "binding_unresolved"):
                blockers.append(row["support"])
            findings.append(
                _row(observation_path, "witness", row.get("state", ""), row.get("status"), blockers)
            )
        for signal_index, row in enumerate(candidate.get("signal_checks", ())):
            findings.extend(_signal_findings(row, _path(_path(path, "signal_checks"), signal_index)))
    consequence = result.get("consequence", {})
    blockers = list(consequence.get("blockers", ()))
    if consequence.get("result") == "UNDETERMINED":
        for candidate in result.get("candidates", ()):
            if candidate.get("id") in result.get("remaining", ()):
                blockers.extend(_candidate_causes(candidate))
    findings.append(
        _row(
            _path(base, "consequence"),
            "candidate_family_consequence",
            consequence.get("result", ""),
            consequence.get("status"),
            blockers,
        )
    )
    findings.extend(
        finding
        for index, row in enumerate(result.get("signals", ()))
        for finding in _signal_findings(row, _path(_path(base, "signals"), index))
    )
    findings.extend(_applications(result, base))
    return findings


def _applications(result: dict, base: str) -> list[dict]:
    """Describe gates from their actual public owners, preserving every cause and warrant."""
    findings = []
    for field, kind in (("exception_checks", "exception_bridge"), ("binding_checks", "binding")):
        for index, row in enumerate(result.get(field, ())):
            code = "conflict" if row["code"] == "attribution_conflict" else row["code"]
            path = _path(_path(base, field), index)
            finding = _row(path, kind, code, row.get("status"), row.get("blockers", ()))
            finding["support_path"] = path
            findings.append(finding)
    return findings


def _candidate_causes(candidate: dict) -> list[str]:
    """Read the effective candidate's own unresolved checks, never unrelated signals."""
    blockers = list(candidate.get("query_decision", {}).get("blockers", ()))
    for row in candidate.get("observations", ()):
        if row.get("state") == "unresolved":
            blockers.extend(row.get("decision", {}).get("blockers", ()))
            if row.get("support") in ("proposed_refused", "binding_unresolved"):
                blockers.append(row["support"])
    for row in candidate.get("signal_checks", ()):
        if row.get("code") == "unresolved":
            blockers.extend(row.get("blockers", ()))
    return blockers


def _interpretations(result: dict, base: str) -> list[dict]:
    findings = []
    fixed = result.get("fixed", {})
    fixed_path = _path(base, "fixed")
    if "consistency" in fixed:
        findings.append(_decision(fixed["consistency"], _path(fixed_path, "consistency"), "consistency"))
    findings.extend(
        _query(row, _path(_path(fixed_path, "queries"), index))
        for index, row in enumerate(fixed.get("queries", ()))
    )
    findings.extend(
        finding
        for index, row in enumerate(fixed.get("signals", ()))
        for finding in _signal_findings(row, _path(_path(fixed_path, "signals"), index))
    )
    for index, frame in enumerate(result.get("interpretations", ())):
        path = _path(_path(base, "interpretations"), index)
        warrant = frame.get("warrant", {})
        findings.append(
            _row(
                path,
                "interpretation",
                frame.get("state", ""),
                warrant.get("status"),
                warrant.get("blockers", ()),
            )
        )
        findings.extend(
            _query(row, _path(_path(path, "queries"), query_index))
            for query_index, row in enumerate(frame.get("queries", ()))
        )
        for field in ("signals", "signal_checks"):
            findings.extend(
                finding
                for signal_index, row in enumerate(frame.get(field, ()))
                for finding in _signal_findings(row, _path(_path(path, field), signal_index))
            )
        for binding_index, row in enumerate(frame.get("bindings", ())):
            findings.append(
                _row(
                    _path(_path(path, "bindings"), binding_index),
                    "binding",
                    row.get("code", ""),
                    row.get("status"),
                    row.get("blockers", ()),
                )
            )
    findings.extend(
        _query(row, _path(_path(base, "consequences"), index))
        for index, row in enumerate(result.get("consequences", ()))
    )
    return findings


def _source_assertions(result: dict, base: str) -> list[dict]:
    findings = []
    for index, answer in enumerate(result.get("analyses", ())):
        prefix = _path(_path(base, "analyses"), index)
        child = answer.get("metadata")
        if child is None:
            child = metadata(answer.get("operation", ""), answer.get("result"), answer.get("problems", ()))
        for row in child.get("findings", ()):
            copied = deepcopy(row)
            for field in ("path", "raw_path", "support_path", "contrast_path"):
                if field in copied:
                    copied[field] = prefix + copied[field]
            if "answer_paths" in copied:
                copied["answer_paths"] = [prefix + path for path in copied["answer_paths"]]
            findings.append(copied)
    return findings


def _evidence_findings(result: dict, base: str) -> list[dict]:
    """Investigation requests stay open; enumeration and output limits remain separate channels."""
    findings = []
    conflict_statuses = []
    for index, check in enumerate(result.get("input_checks", ())):
        decision = check["decision"]
        if decision["result"] == "INCONSISTENT":
            path = _path(_path(_path(base, "input_checks"), index), "decision")
            findings.append(_decision(decision, path))
            conflict_statuses.append(decision["status"])
    status = weakest_status(tuple(conflict_statuses)) if conflict_statuses else "known"
    family = _row(
        _path(base, "family"), "candidate_family", result["family"], status, result["input_conflicts"]
    )
    if result["family"] in ("searched", "single_survivor"):
        family["disposition"] = "descriptive"
    findings.append(family)
    for name in ("search", "output"):
        value = result[name]
        finding = _row(_path(base, name), "evidence_" + name, value["state"], "known", value["causes"])
        if value["state"] == "complete":
            finding["disposition"] = "descriptive"
        findings.append(finding)
    for index, pair in enumerate(result["pairs"]):
        separated = pair["outcome"] == "separated"
        finding = _row(
            _path(_path(base, "pairs"), index),
            "evidence_pair",
            pair["outcome"],
            None,
            () if separated else pair["causes"],
        )
        if separated and pair["causes"]:
            finding["context_causes"] = [
                {"code": cause, "kind": cause_kind(cause)} for cause in pair["causes"]
            ]
        findings.append(finding)
    for index, row in enumerate(result["requests"]):
        path = _path(_path(base, "requests"), index)
        finding = _row(path, "hypothetical_evidence_request", row["kind"], row["conditional_status"])
        finding["hypothetical"] = True
        finding["support_path"] = _path(path, "required_premises")
        findings.append(finding)
    return findings


def _session_findings(result: dict, base: str) -> list[dict]:
    """Retain every actual child finding and the separately computed question context."""
    findings = []

    def extend_child(child: dict, prefix: str) -> None:
        for raw in child.get("metadata", {}).get("findings", ()):
            finding = deepcopy(raw)
            for field in ("path", "raw_path", "support_path", "contrast_path"):
                if field in finding:
                    finding[field] = prefix + finding[field]
            if "answer_paths" in finding:
                finding["answer_paths"] = [prefix + path for path in finding["answer_paths"]]
            findings.append(finding)

    for index, analysis in enumerate(result.get("analyses", ())):
        prefix = _path(_path(_path(base, "analyses"), index), "result")
        extend_child(analysis["result"], prefix)
    # Protocol checks (v2): every child envelope is classified like any child analysis, so the headline
    # summary counts protocol conflicts and repair choices (walkthrough finding, 2026-11-04).
    protocol = result.get("protocol") or {}
    for index, check in enumerate(protocol.get("checks", ())):
        for number, child in enumerate(check.get("children", ())):
            prefix = _path(_path(_path(_path(_path(base, "protocol"), "checks"), index), "children"), number)
            extend_child(child["result"], _path(prefix, "result"))
    # A check that is unresolved, limited or not computed is an open item in the headline, never silence
    # (trace audit F4): one finding per such check, with each named cause.
    for index, check in enumerate(protocol.get("checks", ())):
        causes = [str(entry.get("code")) for entry in check.get("unresolved") or ()]
        if check.get("not_computed") is not None:
            causes.append("external_method_not_computed")
        if causes:
            path = _path(_path(_path(base, "protocol"), "checks"), index)
            findings.append(_row(path, "protocol_check", "unresolved", None, causes))
    protocol_dispositions = {
        "blocker": "conflict",
        "repair_choice": "open",
        "design_choice": "open",
        "evidence_question": "open",
        "settled_within_declared_alternatives": "settled",
        "no_compatible_alternative": "open",
    }
    for index, decision in enumerate(protocol.get("decisions", ())):
        path = _path(_path(_path(base, "protocol"), "decisions"), index)
        findings.append(
            {
                "path": path,
                "kind": "protocol_decision",
                "logical_result": decision["disposition"],
                "standing": None,
                "completion": "complete",
                "causes": [],
                "disposition": protocol_dispositions.get(decision["disposition"], "unclassified"),
                "session_disposition": decision["disposition"],
                "support_path": path,
            }
        )
    for index, check in enumerate(result.get("definition_checks", ())):
        path = _path(_path(base, "definition_checks"), index)
        finding = _row(path, "definition_relation", check["code"], check["status"], check["blockers"])
        finding["support_path"] = _path(path, "declaration")
        findings.append(finding)
    dispositions = {
        "blocker": "conflict",
        "translation_question": "translation_question",
        "computation_task": "not_computed",
        "evidence_question": "open",
        "unrepresented_design_question": "open",
        "design_choice": "open",
        "options_not_distinguished": "open",
        "chosen_by_person": "open",
        "chosen_with_open_checks": "open",
        "settled_within_declared_alternatives": "settled",
    }
    for index, decision in enumerate(result.get("decisions", ())):
        path = _path(_path(base, "decisions"), index)
        for number, distinction in enumerate(decision.get("distinctions", ())):
            if distinction.get("result") is not None:
                prefix = _path(_path(_path(path, "distinctions"), number), "result")
                extend_child(distinction["result"], prefix)
        code, standing = decision["code"], decision.get("standing")
        disposition = dispositions.get(code, "unclassified")
        if disposition == "settled" and standing in ("interpolated", "proposed"):
            disposition = "conditional"
        blockers = {
            cause
            for option in decision["alternatives"]
            for cause in (option.get("warrant") or {}).get("blockers", ())
        }
        findings.append(
            {
                "path": path,
                "kind": "session_decision",
                "logical_result": code,
                "standing": standing,
                "completion": "limited" if code == "computation_task" else "complete",
                "causes": [{"code": cause, "kind": cause_kind(cause)} for cause in sorted(blockers)],
                "disposition": disposition,
                "session_disposition": code,
                "origin": deepcopy(decision["origin"]),
                "coverage": {
                    "target": deepcopy(decision["target"]),
                    "declared": decision["coverage"],
                    "limit": decision["coverage_limit"],
                },
                "support_path": path,
            }
        )
    return findings


def metadata(operation: str, result: object, problems: Sequence[str] = ()) -> dict:
    """Describe existing outputs at envelope level without changing their payloads."""
    if problems:
        findings = []
        for index, problem in enumerate(problems):
            finding = _row(_path("/problems", index), "request", "REFUSED", None, (problem,))
            if finding["completion"] not in ("limited", "unsupported"):
                # A refusal already establishes that no clinical answer was admitted. Its unfamiliar
                # detailed reason remains intact; this context warrants request repair, not a diagnosis.
                finding["completion"] = "invalid"
                finding["disposition"] = "translation_question"
                for cause in finding["causes"]:
                    if cause["kind"] == "unclassified":
                        cause["kind"] = "translation"
            findings.append(finding)
        return {
            "version": 1,
            "kind": "refusal",
            "findings": findings,
        }
    if operation == "describe":
        return {"version": 1, "kind": "discovery", "findings": []}
    if operation == "prepare":
        return {"version": 1, "kind": "inspection", "findings": []}
    adapters = {
        "coordinates": _coordinates,
        "corpus": _corpus,
        "design_bounds": _design_bounds,
        "interpretations": _interpretations,
        "source_assertions": _source_assertions,
        "design_session": _session_findings,
        "evidence_requests": _evidence_findings,
    }
    if not isinstance(result, dict):
        findings = [_row("/result", "unclassified", "", None)]
    elif operation == "entailment":
        findings = [_decision(result.get("decision", {}), "/result/decision")]
    elif operation == "signals":
        findings = [
            finding
            for index, row in enumerate(result.get("signals", ()))
            for finding in _signal_findings(row, _path("/result/signals", index))
        ]
        findings.extend(_applications(result, "/result"))
    elif operation in adapters:
        findings = adapters[operation](result, "/result")
    else:
        findings = [_row("/result", "unclassified", "", None)]
    kind = (
        "inspection"
        if operation in ("source_assertions", "signals", "design_session") and not findings
        else "reasoning"
    )
    if operation not in (*adapters, "entailment", "signals"):
        kind = "inspection"
    return {"version": 1, "kind": kind, "findings": findings}
