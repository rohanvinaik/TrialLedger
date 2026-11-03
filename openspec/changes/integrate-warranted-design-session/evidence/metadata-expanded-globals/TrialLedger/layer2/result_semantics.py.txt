"""Additive, per-finding descriptions of existing reasoning results.

Adapters name the actual result owners. They never edit clinical payloads, infer
source truth, or turn an open proposition into a person's design choice.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy

CAUSE_KINDS = {
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
    ):
        return "conflict" if standing in ("known", "interpolated", "proposed") else "unclassified"
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
            findings.append(_signal(row, _path(_path(path, "signal_checks"), signal_index)))
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
        _signal(row, _path(_path(base, "signals"), index))
        for index, row in enumerate(result.get("signals", ()))
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
        _signal(row, _path(_path(fixed_path, "signals"), index))
        for index, row in enumerate(fixed.get("signals", ()))
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
                _signal(row, _path(_path(path, field), signal_index))
                for signal_index, row in enumerate(frame.get(field, ()))
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
            for field in ("path", "raw_path", "support_path"):
                if field in copied:
                    copied[field] = prefix + copied[field]
            findings.append(copied)
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
    adapters = {
        "coordinates": _coordinates,
        "corpus": _corpus,
        "design_bounds": _design_bounds,
        "interpretations": _interpretations,
        "source_assertions": _source_assertions,
    }
    if not isinstance(result, dict):
        findings = [_row("/result", "unclassified", "", None)]
    elif operation == "entailment":
        findings = [_decision(result.get("decision", {}), "/result/decision")]
    elif operation == "signals":
        findings = [
            _signal(row, _path("/result/signals", index))
            for index, row in enumerate(result.get("signals", ()))
        ]
        findings.extend(_applications(result, "/result"))
    elif operation in adapters:
        findings = adapters[operation](result, "/result")
    else:
        findings = [_row("/result", "unclassified", "", None)]
    kind = "inspection" if operation == "source_assertions" and not findings else "reasoning"
    if operation not in (*adapters, "entailment", "signals"):
        kind = "inspection"
    return {"version": 1, "kind": kind, "findings": findings}
