"""Apply declared bindings to ordinary signal consumers without assuming hypotheses.

Frame-local assumption behavior remains owned by interpretations. This adapter reuses
its strict declaration/use checks and appends their ordinary-operation support gates.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from TrialLedger.layer2 import interpretation_bindings as binding_engine
from TrialLedger.layer2 import signals as evidence


def _fresh_support_id(binding_id: str, occupied: set[str]) -> str:
    """Allocate a deterministic local identity without overwriting an existing source."""
    base = "binding-use:" + binding_id
    identity = base
    suffix = 0
    while identity in occupied:
        suffix += 1
        identity = f"{base}:{suffix}"
    occupied.add(identity)
    return identity


def gate_signals(
    prepared: tuple[evidence.Signal, ...],
    raw_bindings: object,
    raw_uses: object,
    study_ref: str,
) -> tuple[tuple[evidence.Signal, ...], list[dict[str, Any]]]:
    """Append binding support and exact blockers before any ordinary signal consumption.

    Existing parsers/checks own identity, relation, operator and scope decisions. A
    proposed binding is never assumed here. Each returned row retains the complete
    binding declaration, including source digests, and its generated support identity.
    Original objects, data, support and already-established application blockers survive.
    """
    bindings = binding_engine.parse_bindings(raw_bindings, study_ref)
    uses = binding_engine.parse_uses(raw_uses, bindings, {signal.id for signal in prepared}, study_ref)
    checked = binding_engine.check_uses(bindings, uses, prepared, study_ref)
    by_binding = {binding.id: binding for binding in bindings}
    by_signal = {signal.id: signal for signal in prepared}
    occupied = {signal.id: {item.id for item in signal.support} for signal in prepared}
    rows = []
    for checked_row in checked:
        binding = by_binding[checked_row["binding"]]
        signal = by_signal[checked_row["signal"]]
        blockers = list(checked_row["blockers"])
        if binding.status == "proposed":
            blockers.append("proposed_refused:" + binding.id)
        support_id = _fresh_support_id(binding.id, occupied[signal.id])
        support = evidence.Support(
            support_id,
            binding.status,
            "unresolved" if blockers else binding.resolution,
            tuple(checked_row["basis"]),
        )
        by_signal[signal.id] = replace(
            signal,
            support=(*signal.support, support),
            application_blockers=tuple(dict.fromkeys((*signal.application_blockers, *blockers))),
        )
        rows.append(
            {
                **checked_row,
                "checked_code": checked_row["code"],
                "code": "unresolved" if blockers else checked_row["code"],
                "blockers": list(dict.fromkeys(blockers)),
                "support_id": support_id,
                "declaration": asdict(binding),
            }
        )
    return tuple(by_signal[signal.id] for signal in prepared), rows
