"""modality — modality facets and cell properties, read only from an intervention's own entry.

Positive: an antibody, an antibody-drug conjugate, a radioligand, a CAR-T product, a gene therapy and a
vaccine are each read from their entry's wording as known facets, with subject, property, value, polarity,
scope, location, rule and status; a CAR-T product's lineage, engineering, preparation and donor relationship
are read as separate cell properties; a name's stem (-mab, -cel) is an interpolated facet, and the cell
properties under an interpolated cell facet are interpolated; one mention is one extraction ("CAR-T cell
therapy" is one cell facet).
Negative: patient-history or eligibility wording inside an entry ("No prior CAR-T therapy", "previously
treated with", "patients who received CAR-T cells") is `history`, never asserts the modality and unlocks no
cell property; a T cell named in an antibody's mechanism is not the antibody's lineage; "non-small cell" is no
cell facet; a negated facet ("non-antibody") is negated, never asserted, and a negated cell facet licenses no
cell property; a name stem is never known.
"""

from TrialLedger.modality import SCOPE, entry_properties, history_clause, mentions

ENTRY = "protocolSection.armsInterventionsModule.interventions[0]"


def facets(subject, texts):
    return [(e[1], e[2], e[3], e[7]) for e in entry_properties(subject, texts)]


def test_an_antibody_entry_is_an_antibody_and_its_mechanism_is_not_a_lineage():
    text = "SHR-1316 is a humanized anti-PD-L1 monoclonal antibody that restores T cell activity"
    out = entry_properties("SHR-1316", [(f"{ENTRY}.description", text, False)])
    assert out == [
        (
            "SHR-1316",
            "modality",
            "antibody",
            "asserted",
            SCOPE,
            f"{ENTRY}.description[46:54]",
            "facet:antibody",
            "known",
        )
    ]
    assert text[46:54] == "antibody"


def test_a_conjugate_and_a_radioligand_are_their_own_facets():
    adc = "Datopotamab deruxtecan, a TROP2-directed antibody-drug conjugate"
    assert ("modality", "conjugate", "asserted", "known") in facets("Dato-DXd", [(ENTRY, adc, False)])
    assert ("modality", "antibody", "asserted", "known") in facets("Dato-DXd", [(ENTRY, adc, False)])
    radio = "177Lu-PSMA-617, a radioligand therapy"
    assert {f[1] for f in facets("Lu-PSMA", [(ENTRY, radio, False)])} == {"radioactive"}


def test_a_car_t_product_has_separate_cell_properties():
    text = "Autologous CAR-T cells, genetically modified and ex vivo expanded, given as one cell infusion"
    out = facets("XB-2", [(f"{ENTRY}.description", text, False)])
    assert ("modality", "cell", "asserted", "known") in out
    assert {(p, v) for p, v, _, _ in out if p != "modality"} == {
        ("lineage", "T cell"),
        ("engineering", "chimeric antigen receptor"),
        ("engineering", "genetically modified"),
        ("preparation", "expanded"),
        ("donor relationship", "autologous"),
    }
    assert {s for *_, s in out} == {"known"}


def test_gene_and_vaccine_facets_are_read_from_the_entry():
    assert {f[1] for f in facets("V", [(ENTRY, "An mRNA cancer vaccine", False)])} == {"gene", "vaccine"}
    assert {f[1] for f in facets("G", [(ENTRY, "Adenoviral vector gene therapy", False)])} == {"gene"}


def test_a_name_stem_is_interpolated_at_most():
    out = facets("Testamab", [(f"{ENTRY}.name", "Testamab", True)])
    assert out == [("modality", "antibody", "asserted", "interpolated")]
    assert facets("Testamab", [(f"{ENTRY}.description", "Testamab", False)]) == []
    stem = facets("lifileucel", [(f"{ENTRY}.name", "lifileucel", True), (ENTRY, "autologous", False)])
    assert ("modality", "cell", "asserted", "interpolated") in stem
    assert ("donor relationship", "autologous", "asserted", "interpolated") in stem


def test_negated_and_absent_wording_states_nothing_more():
    assert facets("X", [(ENTRY, "A non-antibody small molecule", False)]) == [
        ("modality", "antibody", "negated", "known")
    ]
    assert facets("X", [(ENTRY, "For non-small cell lung cancer", False)]) == []
    assert facets("X", [(ENTRY, "Not a cell therapy; autologous", False)]) == [
        ("modality", "cell", "negated", "known")
    ]
    assert facets("Pembrolizumab", [(ENTRY, "Pembrolizumab 200 mg every 3 weeks", False)]) == []


def test_prior_car_t_in_an_entry_is_the_patients_history_not_the_modality():
    # the founder's example, written inside an intervention's own entry
    assert facets("XB-3", [(ENTRY, "No prior CAR-T therapy; autologous", False)]) == [
        ("modality", "cell", "history", "known")
    ]
    for text in (
        "XB-3 for patients previously treated with CAR-T cell therapy, autologous",
        "XB-3 in patients who received CAR-T cells and were excluded from allogeneic transplant",
    ):
        out = facets("XB-3", [(ENTRY, text, False)])
        assert {p for p, *_ in out} == {"modality"}, text
        assert {polarity for _, _, polarity, _ in out} == {"history"}, text
    stem = facets("tisagenlecleucel", [(f"{ENTRY}.name", "Prior tisagenlecleucel", True)])
    assert stem == [("modality", "cell", "history", "interpolated")]


def test_history_wording_in_its_own_clause_leaves_the_entrys_assertion():
    out = facets("XB-2", [(ENTRY, "Autologous CAR-T cells. Patients who received CAR-T are excluded", False)])
    assert ("modality", "cell", "asserted", "known") in out
    assert ("modality", "cell", "history", "known") in out
    assert ("lineage", "T cell", "history", "known") in out
    assert history_clause("XB-1 is given to patients who received ")
    assert history_clause("No prior ")
    assert not history_clause("Patients who received docetaxel. XB-2 is an ")
    assert not history_clause("")


def test_prior_to_is_a_time_not_the_patients_history():
    out = facets("XB-2", [(ENTRY, "Prior to infusion, autologous CAR-T cells are thawed", False)])
    assert ("modality", "cell", "asserted", "known") in out
    assert ("donor relationship", "autologous", "asserted", "known") in out
    assert not history_clause("Prior to infusion, autologous ")
    assert history_clause("No prior ") and history_clause("Patients with prior ")


def test_one_mention_is_one_extraction():
    out = entry_properties("XB-2", [(ENTRY, "CAR-T cell therapy", False)])
    assert [(e[1], e[2], e[5]) for e in out if e[1] == "modality"] == [("modality", "cell", f"{ENTRY}[0:18]")]
    assert mentions(r"\bCAR-T\b|cell therapy", "CAR-T cell therapy") == [(0, 18)]
    assert mentions(r"\bCAR-T\b|cell therapy", "CAR-T, then cell therapy") == [(0, 5), (12, 24)]
    assert mentions(r"x", "") == []
