"""The pilot's seeded selections.

Positive: the blind-label draw is seeded and order-free; each chosen claim yields a value mutation (a value
the text does not state), a polarity mutation (inclusion read as exclusion) and a concept mutation (another
criterion's concept), each keeping the original envelope and expecting its verdict.
Negative: no mutation reuses a concept its own criterion states; a claim with nothing to change yields no
value mutation; an unsectioned claim yields no polarity mutation; n never exceeds what exists."""

from TrialLedger.pilot import changed_values, mutations, to_label
from TrialLedger.questions import ATOM_CLAIM_OPTIONS, atom_claim, question

HELD = {"target": {"text": "* ECOG 0-1"}, "headings": ["Inclusion Criteria:"], "scoping": [], "stem": ""}
HELD["siblings"] = []


def claim(nct, piece, concept, values, section="inclusion", held=HELD):
    atom = ("", concept, tuple(values), (), 0, 0)
    target = {"nct": nct, "piece": piece, "atom": 0, "claim": atom_claim(atom, section), "concept": concept}
    target |= {"values": list(values), "params": [], "section": section}
    return question("atom_claim", target, held, ATOM_CLAIM_OPTIONS)


QUESTIONS = [
    claim("NCT1", 1, "ecog_ps", ["0", "1"]),
    claim("NCT2", 3, "histology", ["squamous"], section="exclusion"),
    claim("NCT3", 2, "histology", ["adenocarcinoma"], section="unsectioned"),
]


def test_the_label_draw_is_seeded_and_order_free():
    first = to_label(QUESTIONS, 2, "s")
    assert first == to_label(list(reversed(QUESTIONS)), 2, "s") and len(set(first)) == 2
    assert set(to_label(QUESTIONS, 9, "s")) == {q["id"] for q in QUESTIONS}
    assert to_label(QUESTIONS, -1, "s") == []


def test_changed_values():
    assert changed_values(["0", "1"], []) == ["0", "1", "2"]
    assert changed_values(["squamous"], ["squamous", "adenocarcinoma"]) == ["adenocarcinoma"]
    assert changed_values(["squamous"], ["squamous"]) == []
    assert changed_values([], ["x"]) == ["x"]


def test_each_claim_yields_its_mutations_with_their_verdicts():
    made = mutations(QUESTIONS, 3, "m")
    by = {}
    for q, expected in made:
        by.setdefault(q["target"]["of"], {})[q["target"]["mutation"]] = (q, expected)
    ecog = by[QUESTIONS[0]["id"]]
    assert ecog["values"][0]["target"]["claim"].endswith("ecog_ps = 0 | 1 | 2")
    assert ecog["values"][1] == "wrong_value"
    assert ecog["polarity"][0]["target"]["claim"].startswith("This exclusion criterion")
    assert ecog["polarity"][1] == "wrong_polarity_or_modality"
    assert ecog["concept"][0]["target"]["claim"].startswith("This inclusion criterion requires")
    assert "histology" in ecog["concept"][0]["target"]["claim"] and ecog["concept"][1] == "unsupported"
    assert all(q["envelope"] == HELD and q["options"] == list(ATOM_CLAIM_OPTIONS) for q, _ in made)
    unsectioned = by[QUESTIONS[2]["id"]]
    assert "polarity" not in unsectioned
    assert unsectioned["values"][0]["target"]["claim"].endswith("histology = squamous")


def test_n_is_bounded_and_nothing_to_change_yields_nothing():
    lone = [claim("NCT1", 1, "histology", ["squamous"], section="unsectioned")]
    assert mutations(lone, 5, "m") == []
    assert mutations(QUESTIONS, 0, "m") == []


def test_nothing_to_label_is_an_empty_list():
    """Positive: no questions, or a negative n, give an empty list of ids. Negative: never None."""
    assert to_label([], -1, "") == []
    assert to_label([], 5, "s") == [] and isinstance(to_label([], 5, "s"), list)
