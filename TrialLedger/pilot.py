"""The auditor pilot's seeded selections (add-targeted-questions, task 4): which questions are labelled blind,
and the planted mutations whose right answers are known by construction.

A mutation keeps a real question's envelope and changes only its claim: the values (a value the text does not
state: expected `wrong_value`), the section's polarity (inclusion read as exclusion or the reverse: expected
`wrong_polarity_or_modality`), or the concept (another trial's claim made of this criterion: expected
`unsupported`). It tests whether a model challenges a supplied answer, the anchoring a model that sees
TrialLedger's reading is exposed to.

Both draws are taken over the sample's own units: a question drawn as a supplement (`drawn_as`) is left out
unless the caller asks for it, since its trial was not drawn with the strata's probabilities.
"""

from __future__ import annotations

import random

from TrialLedger.questions import ATOM_CLAIM_OPTIONS, atom_claim, question

FLIP = {"inclusion": "exclusion", "exclusion": "inclusion", "permitted": "inclusion"}


def drawn_units(questions: list[dict], include_supplement: bool) -> list[dict]:
    """The questions a pilot or a rate draws from (pure — pinned): those drawn as "sample", and with
    `include_supplement` those drawn as "supplement" too. A question with no `drawn_as` was written before
    supplements existed, when every audited trial was the sample's, and counts as "sample"; any other label
    is never drawn."""
    allowed = {"sample", "supplement"} if include_supplement else {"sample"}
    return [q for q in questions if q.get("drawn_as", "sample") in allowed]


def to_label(questions: list[dict], n: int, seed: str) -> list[str]:
    """The ids of `n` atom-claim questions to label blind, drawn by seed from their distinct ids in sorted
    order (pure — pinned); all of them when there are fewer. The pilot's declared units are atom claims
    (tasks.md 4, 2026-10-31), so another kind of question never enters this draw."""
    kinds = {q["id"]: q["kind"] for q in questions}
    ids = sorted(found for found, kind in kinds.items() if kind == "atom_claim")
    return random.Random(seed).sample(ids, min(max(n, 0), len(ids)))


def changed_values(values: list[str], seen: list[str]) -> list[str]:
    """Values a criterion does not state (pure — pinned): one more than the largest when every value is a
    whole number ("0|1" -> "0|1|2"); otherwise the first value seen elsewhere for the same concept that is not
    among them, in place of them; [] when neither exists."""
    if values and all(v.isdigit() for v in values):
        return [*values, str(max(int(v) for v in values) + 1)]
    other = next((v for v in seen if v not in values), None)
    return [other] if other is not None else []


def mutations(questions: list[dict], n: int, seed: str) -> list[tuple[dict, str]]:
    """Up to `n` seeded atom-claim questions, each turned into the mutations its parts allow, with the verdict
    each must receive (pure — pinned). Every mutation keeps the original envelope and options."""
    claims = sorted((q for q in questions if q["kind"] == "atom_claim"), key=lambda q: q["id"])
    chosen = random.Random(seed).sample(claims, min(max(n, 0), len(claims)))
    seen: dict[str, list[str]] = {}
    stated: dict[tuple[str, int], set[str]] = {}
    for q in claims:
        target = q["target"]
        stated.setdefault((target["nct"], target["piece"]), set()).add(target["concept"])
        values = seen.setdefault(target["concept"], [])
        values.extend(v for v in target["values"] if v not in values)
    out = []
    for q in chosen:
        target = q["target"]
        params = tuple(tuple(p) for p in target["params"])
        values = changed_values(target["values"], seen[target["concept"]])
        if values:
            claim = atom_claim(("", target["concept"], tuple(values), params, 0, 0), target["section"])
            out.append((_mutant(q, claim, "values"), "wrong_value"))
        if target["section"] in FLIP:
            atom = ("", target["concept"], tuple(target["values"]), params, 0, 0)
            claim = atom_claim(atom, FLIP[target["section"]])
            out.append((_mutant(q, claim, "polarity"), "wrong_polarity_or_modality"))
        here = stated[(target["nct"], target["piece"])]
        foreign = next((o for o in claims if o["target"]["concept"] not in here), None)
        if foreign is not None:
            other = foreign["target"]
            atom = (
                "",
                other["concept"],
                tuple(other["values"]),
                tuple(tuple(p) for p in other["params"]),
                0,
                0,
            )
            out.append((_mutant(q, atom_claim(atom, target["section"]), "concept"), "unsupported"))
    return out


def _mutant(original: dict, claim: str, kind: str) -> dict:
    target = {**original["target"], "claim": claim, "mutation": kind, "of": original["id"]}
    made = question("atom_claim", target, original["envelope"], ATOM_CLAIM_OPTIONS)
    return made | ({"drawn_as": original["drawn_as"]} if "drawn_as" in original else {})
