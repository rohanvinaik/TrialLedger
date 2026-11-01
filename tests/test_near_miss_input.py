"""A study view as the near-miss decision reads it.

Positive: one setting under approved relations and drugs whose classes are all known (RxClass or stated by
the record) make a known representation; the first inclusion ECOG atom and every inclusion histology are
predicates; a present or negated checkpoint expectation is a predicate.
Negative: several candidate settings, a setting only proposed relations narrow, an unresolved drug or no drugs
leave the representation unknown; exclusion atoms are not predicates; an expectation not documented,
unresolved or not applicable is unknown.
"""

from TrialLedger.reading import near_miss_input

PD1 = "Programmed Death Receptor-1 Blocking Antibody"


def view(settings=("advanced_first_line",), drugs=None, criteria=(), status="present", proposed=None):
    return {
        "nct": "NCT1",
        "coordinates": {"setting": {"domain": settings, "with_proposed": proposed or settings}},
        "drugs": [("pembrolizumab", "classified", [PD1], "dailymed")] if drugs is None else drugs,
        "criteria": list(criteria),
        "observations": {"checkpoint": (status, "", [], [])} if status else {},
        "sponsor": "S",
        "start_year": "2019",
    }


def atom(concept, values):
    return ("bank", concept, values, (), 0, 1)


def test_a_known_representation_and_its_predicates():
    criteria = [
        (0, "inclusion", "", [atom("ecog_ps", ("0", "1")), atom("histology", ("squamous",))]),
        (1, "inclusion", "", [atom("ecog_ps", ("0", "1", "2")), atom("histology", ("adeno",))]),
        (2, "exclusion", "", [atom("histology", ("small_cell",)), atom("ecog_ps", ("3",))]),
    ]
    drugs = [
        ("a", "classified", ["Kinase Inhibitor"], "x"),
        ("b", "classified", [PD1, "Kinase Inhibitor"], "x"),
    ]
    assert near_miss_input(view(drugs=drugs, criteria=criteria)) == (
        "NCT1",
        {"setting": "advanced_first_line", "classes": f"Kinase Inhibitor + {PD1}"},
        {"ecog_ps": "0|1", "histology": "adeno|squamous", "autoimmune_exclusion": "present"},
        "S",
        "2019",
    )
    assert (
        near_miss_input(view(status="explicitly_negated"))[2]["autoimmune_exclusion"] == "explicitly_negated"
    )


def test_unknowns_stay_unknown():
    two = near_miss_input(view(settings=("advanced_first_line", "maintenance")))
    assert two[1]["setting"] == ""
    assert near_miss_input(view(settings=()))[1]["setting"] == ""
    unresolved = [("a", "classified", [PD1], "x"), ("b", "unresolved", [], "")]
    assert near_miss_input(view(drugs=unresolved))[1]["classes"] == ""
    assert near_miss_input(view(drugs=[("a", "stated_by_record", ["stated: PD-1"], "d")]))[1]["classes"] == (
        "stated: PD-1"
    )
    many = ("advanced_first_line", "advanced_previously_treated")
    assert near_miss_input(view(settings=many, proposed=("advanced_first_line",)))[1]["setting"] == ""
    assert near_miss_input(view(drugs=[]))[1]["classes"] == ""
    excluded = [(0, "exclusion", "", [atom("ecog_ps", ("2",)), atom("histology", ("squamous",))])]
    assert near_miss_input(view(criteria=excluded))[2] == {
        "ecog_ps": "",
        "histology": "",
        "autoimmune_exclusion": "present",
    }
    for status in ("not_documented", "unresolved", "not_applicable", ""):
        assert near_miss_input(view(status=status))[2]["autoimmune_exclusion"] == ""


def test_the_class_key_is_sorted_whatever_order_the_drugs_name_them():
    """Positive: the classes are joined in sorted order, so two trials of the same classes always match.
    Negative: the order in which a record lists its drugs never changes the representation."""
    names = ["Zeta", "Epsilon", "Delta", "Gamma", "Beta", "Alpha"]
    drugs = [(name, "classified", [name], "x") for name in names]
    expected = "Alpha + Beta + Delta + Epsilon + Gamma + Zeta"
    assert near_miss_input(view(drugs=drugs))[1]["classes"] == expected
    assert near_miss_input(view(drugs=drugs[::-1]))[1]["classes"] == expected
