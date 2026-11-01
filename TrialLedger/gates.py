"""Symbolic gates on the auditor's answers: when, given a claim's kind and what the rules can re-derive, a
model's challenge is resolved without a human (the founder, 2026-11-01: an over-challenge is a warrant for a
sub-rule that resolves it on the accept or the decline side).

Each gate is a pure decision with its provenance in provenance.PROVENANCE. A gate never changes a reading; it
records, beside the model's answer, that the answer is overruled and by which rule.
"""

from __future__ import annotations

from TrialLedger.banks import named_conditions
from TrialLedger.reading import effective_section


def mention_value_gate(question: dict, verdict: str) -> bool:
    """Whether a model's "wrong_value" on a named-condition claim is overruled (pure — pinned).

    Derived from the auditor pilot of 2026-11-01 (18-trial stratified sample, development data): of the 30
    claims Claude labelled right that qwen3:8b challenged, 25 were "wrong_value" on named-condition claims,
    the model grading the concept's name as a value. The gate fires only when the claim is an atom claim of
    the condition concept, the verdict is "wrong_value", the rules re-derive that very condition from the
    target text, in the claim's own effective section, with the claim's own window (or none on both). On the
    pilot it overruled 25 right claims and 3 wrong ones (alternatives, population scope, a conditional
    obligation: the scoped-assertion layer's cases). Any other answer: False."""
    target = question.get("target", {})
    if (
        question.get("kind") != "atom_claim"
        or verdict != "wrong_value"
        or target.get("concept") != "condition"
    ):
        return False
    held = question["envelope"]["target"]
    concept = (target.get("values") or [""])[0]
    window = dict(tuple(p) for p in target.get("params", [])).get("window")
    for _concept, values, params, _s, _e in named_conditions(held["text"]):
        if values[0] != concept:
            continue
        derived = dict(params)
        return (
            effective_section(held["section"], params) == target.get("section")
            and derived.get("window") == window
        )
    return False
