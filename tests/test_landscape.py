"""landscape.json — the record of truth: schema v2, the per-study extract, the cohort, and the validator.

Positive: a record assembled from a reading of the test records (a study with posted results in every
module, an observational one with none, production_path's near-miss pair and its audited trial) validates
against schema v2, before and after a JSON round trip; every value read as stated is exactly the record's
value at its source; a field the record holds is known, with its location; a coordinate's known value is
known when resolved, a default's narrowing interpolated and each proposal's narrowing proposed, alone, beside
it (add-scoped-reasoning 1.1); posted measurements and adverse events are read
per arm from the results section; biomarkers come by role from the criteria's atoms and the outcomes'
endpoint classes; each criterion's elements carry their standard tier from the cohort's frequency rows over
all trials; the cohort's frequency, mechanism and occupancy rows are design.xlsx's, warrant aside; the
manifest names each study's digest and their Merkle root; every field of the record is described, and the
record carries what each status and each key of a value means.
Negative: a registered outcome is never efficacy (a study without results states "no results posted" and
lists no measurement, its outcomes still planned); an absent field is not_stated with the ledger's absence
state, never a value; a conflict or several values is unresolved, never known, and a default's narrowing is
never known; an untyped criterion has no
tier and is never not_met; a proposed relation that leaves no value is unresolved, never proposed; an
intervention that is not an experimental drug is never classed or given axes; a reading of other studies, or
of the same studies in another order, raises; the validator names every departure the record itself shows by
its code: an unknown schema version, a changed description, an undescribed or missing field, a field or a
value not of its type (a scalar, an object's keys, a table's columns), a malformed envelope, an unknown or
inadmissible status, a value with no source or link or another study's link, a study whose link is null or
not its own NCT number's, efficacy and safety that disagree on the results, a posted value with no results
section or not from the results section, a coverage row or review question of another study, a manifest whose
digests or root disagree; and landscape.py is outside the derivation code root, so no warrant changes.
"""

import copy
import json
import re
from pathlib import Path

import pytest
from production_path import audited_study, near_miss_study
from records import ongoing_study, results_study
from test_reading_axes import first_line, platinum_answers

import TrialLedger
from TrialLedger import landscape, warrants
from TrialLedger.banks import endpoint_classes, time_points, type_criterion
from TrialLedger.coherence import RELATIONS, SETTINGS, resolve
from TrialLedger.design import sheets
from TrialLedger.landscape import (
    ELIGIBILITY_TEXT,
    FIELDS,
    NOT_EXPERIMENTAL,
    UNTYPED,
    axes_value,
    biomarker_values,
    coordinate_values,
    criterion_sections,
    drug_class_value,
    endpoint_profile,
    landscape_manifest,
    landscape_record,
    outcome_sections,
    posted_events,
    posted_measurements,
    reference_values,
    results_value,
    schema_problems,
    standard_values,
    stated,
    study_extract,
)
from TrialLedger.reading import read_population, study_view
from TrialLedger.workbook import CODE_ROOT

LINK = "https://clinicaltrials.gov/study/NCT01234567"
PLACEBO_EPC = ["N0000191260", "Programmed Death Receptor-1 Blocking Antibody", "has_epc", "DAILYMED"]
ANSWERS = {"Placebo": {"codes": {"DAILYMED:has_epc": "found"}, "classes": [PLACEBO_EPC]}}
# Testamab asked and its lookup failed (lookup_failed); a drug never asked is not_looked_up
# (add-agent-operation 4.2, reading.classes_as_looked_up)
ANSWERS["Testamab"] = {"codes": {"DAILYMED:has_epc": "lookup_failed"}, "classes": []}
STANDARD_RULE = "profile.frequency_rows (all trials), keyed by profile.element_key"


def env(value, status, source, rule="", note="", link=LINK):
    return {"value": value, "status": status, "source": source, "rule": rule, "note": note, "link": link}


def population():
    return [
        results_study(),
        ongoing_study(),
        near_miss_study("NCT09000001", "0-1"),
        near_miss_study("NCT09000002", "0-2"),
        audited_study(),
    ]


def manifest_for(studies):
    return landscape_manifest(
        studies, "2.0.3", "2026-10-30T09:00:03", "c" * 40, {"matched": 5, "read": 5}, landscape.RULE_VERSIONS
    )


def record_for(studies=None):
    studies = population() if studies is None else studies
    reading = read_population(studies, ANSWERS)
    return landscape_record(reading, studies, {"drug": ["Placebo"]}, {"queries": []}, manifest_for(studies))


def envelopes(node, path=""):
    """Every envelope in a record, with its concrete path."""
    if isinstance(node, dict) and tuple(node) == landscape.ENVELOPE:
        return [(path, node)]
    if isinstance(node, dict):
        return [found for key, item in node.items() for found in envelopes(item, f"{path}.{key}")]
    if isinstance(node, list):
        return [found for index, item in enumerate(node) for found in envelopes(item, f"{path}[{index}]")]
    return []


def keys_of(source):
    """A location ("a.b[0].c") as the keys and indices ledger.get reads."""
    keys = []
    for part in source.split("."):
        name, *indices = part.split("[")
        keys.append(name)
        keys += [int(index.rstrip("]")) for index in indices]
    return keys


# ── the record as a whole ─────────────────────────────────────────────────────────────────────────────


def test_a_record_of_the_test_population_validates_before_and_after_a_round_trip():
    record = record_for()
    assert schema_problems(record) == ()
    assert schema_problems(json.loads(json.dumps(record))) == ()
    assert [s["nct"]["value"] for s in record["studies"]] == [
        "NCT01234567",
        "NCT07654321",
        "NCT09000001",
        "NCT09000002",
        "NCT09000004",
    ]
    assert list(record) == [
        "schema_version",
        "request",
        "scope",
        "manifest",
        "studies",
        "cohort",
        "review_queue",
        "coverage",
        "statuses",
        "envelope",
        "fields",
    ]
    assert record["statuses"] == landscape.STATUSES
    assert list(record["envelope"]) == list(landscape.ENVELOPE)
    assert record["request"] == {"drug": ["Placebo"]} and record["scope"] == {"queries": []}


def test_every_value_read_as_stated_is_the_records_own_value_at_its_source():
    studies = population()
    record = record_for(studies)
    checked = 0
    for study, extract in zip(studies, record["studies"], strict=True):
        for _path, value in envelopes(extract):
            assert value["link"] == extract["link"]
            if value["rule"] == "" and value["status"] == "known":
                held = study
                for key in keys_of(value["source"]):
                    held = held[key]
                assert held == value["value"], value["source"]
                checked += 1
            if value["status"] == "not_stated":
                assert value["value"] is None and value["note"] in (
                    "not_reported",
                    "not_applicable",
                    "redacted",
                )
    assert checked == 85


def test_the_cohort_is_design_xlsx_s_profile_warrant_aside():
    studies = population()
    reading = read_population(studies, ANSWERS)
    record = landscape_record(reading, studies, {}, {}, manifest_for(studies))
    book = sheets(reading, {})
    for sheet, table in (
        ("Profile", "frequency"),
        ("Mechanism Signals", "mechanism_signals"),
        ("Occupancy", "occupancy"),
    ):
        rows = [list(row.values()) for row in record["cohort"][table]]
        assert rows == [row[:-1] for row in book[sheet][1]], sheet
    assert record["cohort"]["frequency"], "the population states elements"
    assert record["cohort"]["near_misses"] == [
        {
            "a": "NCT09000001",
            "b": "NCT09000002",
            "difference": "ecog_ps",
            "value_a": "0|1",
            "value_b": "0|1|2",
            "sponsor_a": "",
            "sponsor_b": "",
            "start_year_a": "2025",
            "start_year_b": "2025",
            "predicates_agreeing": 1,
            # the first-line setting of both is the default's conclusion (add-scoped-reasoning 1.1)
            "rests_on": "interpolated",
        }
    ]
    assert record["cohort"]["thresholds"] == {
        "standard_share": 0.9,
        "signal_min_trials": 5,
        "signal_min_sponsors": 3,
    }
    assert record["cohort"]["aligned_near_misses"] == [] and record["cohort"]["structure_relations"] == []


def test_the_cohort_names_its_endpoints_by_class():
    assert record_for()["cohort"]["endpoints"] == [
        {
            "outcome_type": "primary",
            "endpoint_class": "duration_of_response",
            "trials": 1,
            "ncts": ["NCT09000004"],
            "outcomes": 1,
            "time_points": {"24 week": 1},
        },
        {
            "outcome_type": "primary",
            "endpoint_class": "objective_response_rate",
            "trials": 1,
            "ncts": ["NCT01234567"],
            "outcomes": 1,
            "time_points": {},
        },
        {
            "outcome_type": "secondary",
            "endpoint_class": "(no endpoint class)",
            "trials": 1,
            "ncts": ["NCT09000004"],
            "outcomes": 1,
            "time_points": {"12 week": 1},
        },
        {
            "outcome_type": "secondary",
            "endpoint_class": "progression_free_survival",
            "trials": 1,
            "ncts": ["NCT01234567"],
            "outcomes": 1,
            "time_points": {"2 year": 1},
        },
        {
            "outcome_type": "other",
            "endpoint_class": "biomarker_endpoint",
            "trials": 1,
            "ncts": ["NCT01234567"],
            "outcomes": 1,
            "time_points": {},
        },
    ]


def experimental(nct, *names):
    """A first-line near-miss trial whose experimental arm gives every one of `names`."""
    study = near_miss_study(nct, "0-1")
    study["protocolSection"]["armsInterventionsModule"] = {
        "armGroups": [
            {"label": "A", "type": "EXPERIMENTAL", "interventionNames": [f"Drug: {n}" for n in names]}
        ],
        "interventions": [{"type": "DRUG", "name": name} for name in names],
    }
    return study


def test_a_cohort_with_classes_aligned_pairs_and_structure_relations_is_design_xlsx_s():
    """Two classified classes, a trial whose second drug is unclassed (so it occupies no cell), an aligned
    pair and a shared structure class: every cohort table is the design sheets' or the reading's, by name."""
    studies = [
        near_miss_study("NCT09000001", "0-1"),
        near_miss_study("NCT09000002", "0-2"),
        experimental("NCT09000005", "Placebo", "XB-9"),
        experimental("NCT09000006", "Gamma"),
        first_line("NCT11", "0-1", "AB-1"),
        first_line("NCT12", "0-2", "AB-2"),
        first_line("NCT21", "0-1", "Cisplatin"),
        first_line("NCT22", "0-1", "Carboplatin"),
    ]
    held = {
        **platinum_answers(),
        **ANSWERS,
        "Gamma": {"codes": {}, "classes": [["N1", "Kinase Inhibitor", "has_epc", "DAILYMED"]]},
    }
    reading = read_population(studies, held)
    cohort = landscape.cohort_section(reading)
    book = sheets(reading, {})
    for sheet, table in (
        ("Profile", "frequency"),
        ("Mechanism Signals", "mechanism_signals"),
        ("Occupancy", "occupancy"),
    ):
        assert [list(row.values()) for row in cohort[table]] == [row[:-1] for row in book[sheet][1]], sheet
        assert cohort[table], table
    assert {row["class"] for row in cohort["occupancy"]} == {PLACEBO_EPC[1], "Kinase Inhibitor"}
    mixed = [row for row in cohort["occupancy"] if row["setting"] == "advanced_first_line"]
    # occupancy reads the known setting only (add-scoped-reasoning, Decision 7): no relation is strict, so
    # every first-line trial's known setting is unnarrowed, none occupies a cell, and each one of a class (or
    # with an unclassed drug) could fall in it, counted apart
    assert [(row["class"], row["occupying"], row["could_fall_here"], row["state"]) for row in mixed] == [
        ("Kinase Inhibitor", 0, 6, "unknown"),
        (PLACEBO_EPC[1], 0, 7, "unknown"),
    ]
    assert cohort["aligned_near_misses"] == [
        {
            "a": "NCT11",
            "b": "NCT12",
            "difference": "ecog_ps",
            "value_a": "0|1",
            "value_b": "0|1|2",
            "sponsor_a": "",
            "sponsor_b": "",
            "start_year_a": "2025",
            "start_year_b": "2025",
            "predicates_agreeing": 0,
            "basis_a": "rxclass",
            "basis_b": "rxclass",
            "rests_on": "interpolated",
        }
    ]
    assert cohort["structure_relations"] == [
        {
            "rxcui_a": "2555",
            "name_a": "cisplatin",
            "rxcui_b": "40048",
            "name_b": "carboplatin",
            "taxonomy": "FDASPL:has_chemical_structure",
            "class": "N0000175073 Platinum-containing Compounds",
            "release": "05-Oct-2026",
        }
    ]


def test_occupancy_lists_the_observed_classes_in_order_whatever_order_they_are_seen_in():
    """Six classes, seen in no particular order: every setting lists them sorted, as design.xlsx does."""
    classes = ["Zeta", "Alpha", "Mu", "Beta", "Omega", "Kappa"]
    views = [
        {
            "nct": f"NCT0000000{index}",
            "sponsor": "S",
            "coordinates": {"setting": {"domain": ("advanced_first_line",)}},
            "itemize": "itemized",
            "elements": [],
            "drugs": [("D", "classified", [klass], "D")],
            "coverage": {
                "content": "present",
                "evidence": (("inclusion", "unspecified"), ("exclusion", "unspecified")),
            },
            "outcomes": [],
        }
        for index, klass in enumerate(classes)
    ]
    reading = {
        "views": views,
        "pairs": [],
        "pair_status": [],
        "aligned_pairs": [],
        "aligned_pair_status": [],
        "structure_relations": [],
    }
    occupancy = landscape.cohort_section(reading)["occupancy"]
    for setting in ("adjuvant", "advanced_first_line"):
        assert [row["class"] for row in occupancy if row["setting"] == setting] == sorted(classes)
    assert {row["state"] for row in occupancy if row["setting"] == "advanced_first_line"} == {"occupied"}


def test_the_review_queue_and_coverage():
    record = record_for()
    assert [(row["nct"], row["kind"], row["priority"], row["answer"]) for row in record["review_queue"]] == [
        ("NCT01234567", "drug_class_unresolved", 3, None),
        ("NCT09000001", "eligibility_abbreviated", 3, None),
        ("NCT09000002", "eligibility_abbreviated", 3, None),
    ]
    assert record["review_queue"][0]["options"] == [PLACEBO_EPC[1], "none of these"]
    coverage = record["coverage"]
    assert coverage["universe"]["study_type"] == "INTERVENTIONAL"
    assert [row["universe"] for row in coverage["studies"]] == ["in_universe"] + [
        "observational_unsupported"
    ] * 4
    assert coverage["studies"][0]["coordinates"]["phase"] == ["PHASE2"]
    assert len(coverage["types"]) > 20 and {row["status"] for row in coverage["types"]} == {
        "unsupported",
        "unmeasured",
    }


VERSIONS = {"landscape_schema": "1", "design": "design-1", "relations": {"r1": "approved"}}


def test_the_manifest_names_each_study_and_their_root():
    studies = population()
    digests = [warrants.study_digest(study) for study in studies]
    manifest = landscape_manifest(studies, "2.0.3", "2026-10-30T09:00:03", "c" * 40, {"matched": 5}, VERSIONS)
    assert manifest == {
        "api_version": "2.0.3",
        "data_timestamp": "2026-10-30T09:00:03",
        "study_digests": digests,
        "merkle_root": warrants.merkle_root(digests),
        "code_commit": "c" * 40,
        "rule_versions": VERSIONS,
        "retrieval": {"matched": 5},
    }
    assert list(manifest) == list(landscape.MANIFEST_KEYS)


def test_the_rule_versions_name_the_schema_the_tool_the_design_the_code_root_and_each_relation():
    assert {
        "landscape_schema": landscape.SCHEMA_VERSION,
        "trialledger": TrialLedger.__version__,
        "design": "design-2",
        "derivation_code_root": CODE_ROOT,
        "relations": {relation.id: relation.approval for relation in RELATIONS},
        "relation_kinds": {relation.id: relation.kind for relation in RELATIONS},
    } == landscape.RULE_VERSIONS
    # schema 2: the coordinates' three statuses, the pairs' rests_on and the relation kinds
    assert landscape.SCHEMA_VERSION == "2"
    assert set(landscape.RULE_VERSIONS["relation_kinds"].values()) == {"default", "proposal"}


def test_a_manifest_owns_its_rule_versions_and_an_empty_pull_has_the_empty_root():
    manifest = landscape_manifest([], "2.0.3", "t", "c", {}, VERSIONS)
    assert (manifest["study_digests"], manifest["merkle_root"]) == ([], warrants.digest("empty"))
    manifest["rule_versions"]["relations"].clear()
    assert VERSIONS["relations"] == {"r1": "approved"}


REFUSED = ("ValueError", ("the reading is not of these studies, in this order",))


def test_a_reading_of_other_studies_is_refused():
    studies = population()
    reading = read_population(studies[:2], ANSWERS)
    assert raised(landscape_record, reading, studies, {}, {}, manifest_for(studies)) == REFUSED


def test_a_reading_of_the_same_studies_in_another_order_is_refused():
    """Two studies with no posted results, read in the other order: the count agrees, nothing else does."""
    studies = [ongoing_study(), audited_study()]
    reading = read_population(studies[::-1], ANSWERS)
    assert raised(landscape_record, reading, studies, {}, {}, manifest_for(studies)) == REFUSED
    assert (
        raised(landscape_record, read_population(studies, ANSWERS), studies, {}, {}, manifest_for(studies))
        is None
    )


def test_a_start_after_the_data_timestamp_is_after_the_present_and_none_reads_open_ended():
    study = results_study()
    study["protocolSection"]["statusModule"]["startDateStruct"]["date"] = "2026-12-01"
    reading = read_population([study], {})
    late = landscape_record(reading, [study], {}, {}, manifest_for([study]))
    assert late["coverage"]["studies"][0]["universe"] == "after_present"
    for stamp in (None, "", 20261030):
        unstamped = {**manifest_for([study]), "data_timestamp": stamp}
        universe = landscape_record(reading, [study], {}, {}, unstamped)["coverage"]["studies"][0]["universe"]
        assert universe == "in_universe", stamp


def test_a_record_owns_its_description_and_universe():
    studies = population()
    reading = read_population(studies, ANSWERS)
    record = landscape_record(reading, studies, {}, {}, manifest_for(studies))
    record["fields"]["studies"]["meaning"] = "changed"
    record["statuses"]["known"] = "changed"
    record["envelope"].clear()
    record["coverage"]["universe"]["unsupported"].clear()
    assert FIELDS["studies"]["meaning"] == "every study read, in the pull's order"
    assert landscape.UNIVERSE["unsupported"]
    fresh = record_for()
    assert fresh["fields"] == FIELDS and fresh["coverage"]["universe"] == landscape.UNIVERSE
    assert fresh["statuses"] == landscape.STATUSES and fresh["envelope"] == landscape.ENVELOPE_MEANINGS


def test_every_field_is_described_with_its_statuses_and_source():
    statuses = set(landscape.STATUSES)
    for path, entry in FIELDS.items():
        assert list(entry) == ["meaning", "type", "statuses", "source"], path
        assert entry["meaning"] and entry["source"] and entry["type"], path
        assert set(entry["statuses"]) <= statuses, path
        assert bool(entry["statuses"]) == entry["type"].startswith(("value", "list of value")), path
    assert landscape.SECTIONS == (
        "schema_version",
        "request",
        "scope",
        "manifest",
        "studies",
        "cohort",
        "review_queue",
        "coverage",
        "statuses",
        "envelope",
        "fields",
    )
    assert FIELDS["studies[].efficacy.measurements"]["statuses"] == ["known"]
    assert "not_posted" in FIELDS["studies[].efficacy.results"]["statuses"]


def test_every_object_value_holds_exactly_the_keys_its_field_names():
    """Every envelope of the record whose value is an object holds the keys `fields` names for it, in order;
    an object the record holds is shown as it holds it."""
    record = record_for()
    checked = set()
    for index, extract in enumerate(record["studies"]):
        for path, value in envelopes(extract, f"studies[{index}]"):
            field = re.sub(r"\[\d+\]", "[]", path).removesuffix("[]")
            kind = FIELDS[field]["type"]
            if "object: " not in kind or value["value"] is None or kind.endswith(f"{landscape.AS_HELD})"):
                continue
            keys = kind.split("object: ", 1)[1].removesuffix(")").split(", ")
            assert list(value["value"]) == keys, path
            checked.add(field)
    named = {path for path, entry in FIELDS.items() if "object: " in entry["type"]}
    held = {path for path in named if FIELDS[path]["type"].endswith(f"{landscape.AS_HELD})")}
    unseen = {
        "studies[].biomarkers.eligibility",
        "studies[].biomarkers.outcome",
        "studies[].unsectioned[].atoms",
    }
    assert checked == named - held - unseen
    # the population types no unsectioned criterion, no biomarker criterion and no biomarker outcome
    text = "* EGFR mutation positive"
    roles = biomarker_values(
        [(0, "unsectioned", text, type_criterion(text))],
        [outcome("primary", "ctDNA clearance", "8 weeks")],
        LINK,
    )
    assert list(roles["eligibility"][0]["value"]) == list(landscape.BIOMARKER_KEYS)
    assert list(roles["outcome"][0]["value"]) == list(landscape.BIOMARKER_OUTCOME_KEYS)
    [criterion] = criterion_sections([(0, "unsectioned", text, type_criterion(text))], LINK)["unsectioned"]
    assert list(criterion["atoms"][0]["value"]) == list(landscape.ATOM_KEYS)


def test_landscape_is_outside_the_derivation_code_root():
    package = Path(landscape.__file__).parent
    assert "landscape.py" not in {path.name for path in warrants.derivation_files(package)}


# ── the per-study extract ─────────────────────────────────────────────────────────────────────────────


def test_a_study_with_results_reads_its_ten_points():
    record = record_for()
    first = record["studies"][0]
    assert first["population"]["minimum_age"] == env(
        "18 Years", "known", "protocolSection.eligibilityModule.minimumAge"
    )
    assert [c["text"]["value"] for c in first["inclusion"]] == ["* Age 18 to 65", "* Stage II disease"]
    assert [c["text"]["value"] for c in first["exclusion"]] == [
        "* Pregnancy",
        "* Prior therapy with \\>2 lines",
    ]
    assert first["unsectioned"] == []
    assert [o["measure"]["value"] for o in first["outcomes"]["primary"]] == ["Objective response rate"]
    assert first["outcomes"]["primary"][0]["endpoint_classes"]["value"] == ["objective_response_rate"]
    assert first["exploratory_measures"] == first["outcomes"]["other"]
    assert [m["value"]["arm"] for m in first["efficacy"]["measurements"]] == ["Testamab", "Placebo"]
    assert [m["value"]["value"] for m in first["efficacy"]["measurements"]] == ["21", "6"]
    assert first["efficacy"]["results"]["value"] == "results posted"
    assert [e["value"]["arm"] for e in first["safety"]["events"]] == ["Testamab", "Placebo"] * 2
    assert [p["value"]["role"] for p in first["publications"]] == [
        "reports results from this study, as the responsible party marked it",
        "added by the registry, not by the responsible party; its role is not stated",
        "entered by the responsible party, not marked as reporting results",
    ]
    assert first["documents"][0]["value"]["url"] == (
        "https://cdn.clinicaltrials.gov/large-docs/67/NCT01234567/Prot_SAP_000.pdf"
    )
    assert first["sponsor"]["value"] == "Example Pharma" and first["phases"]["value"] == ["PHASE2"]


def test_a_study_without_results_states_no_results_posted_and_keeps_its_outcomes_planned():
    study = results_study()
    del study["resultsSection"]
    study["hasResults"] = False
    record = record_for([study])
    extract = record["studies"][0]
    no_results = env("no results posted", "not_posted", "hasResults", "ledger.results_state")
    assert extract["efficacy"] == {"results": no_results, "measurements": []}
    assert extract["safety"]["results"] == no_results
    assert extract["safety"]["groups"] == [] and extract["safety"]["events"] == []
    assert extract["safety"]["time_frame"] == env(
        None, "not_stated", "resultsSection.adverseEventsModule.timeFrame", note="not_reported"
    )
    assert extract["outcomes"]["primary"][0]["measure"]["status"] == "known"
    assert schema_problems(record) == ()


def test_the_near_miss_trials_read_their_coordinates_and_standard_language():
    record = record_for()
    first = record["studies"][2]
    coordinates = first["line_of_therapy_and_setting"]
    # the first-line setting is a default's conclusion: interpolated, never known (add-scoped-reasoning 1.1)
    assert (coordinates["setting"]["value"], coordinates["setting"]["status"]) == (
        list(SETTINGS),
        "unresolved",
    )
    assert (coordinates["setting_interpolated"]["value"], coordinates["setting_interpolated"]["status"]) == (
        ["advanced_first_line"],
        "interpolated",
    )
    assert coordinates["setting_proposed"] == []
    assert coordinates["prior_advanced_lines"]["note"] == "resolved; 1|2|3+ removed by criterion 2"
    tiers = {
        e["value"]["element"]: e["value"]["tier"] for c in first["standard_language"] for e in c["elements"]
    }
    assert tiers == {
        "inclusion:stage:IV": "unresolved",
        "inclusion:prior_lines=0": "unresolved",
        "inclusion:extent:advanced": "unresolved",
        "inclusion:extent:metastatic": "unresolved",
        "inclusion:ecog_ps=0|1": "unresolved",
        "exclusion:condition=autoimmune_disease": "unresolved",
    }
    assert first["interventions"][0]["drug_class"]["value"]["classes"] == [PLACEBO_EPC[1]]
    assert first["eligibility"]["coverage"]["value"]["exclusion"] == "abbreviation_stated"


def test_study_extract_reads_one_study_from_its_view():
    study = audited_study()
    view = study_view(study, {})
    extract = study_extract(study, view, {})
    link = "https://clinicaltrials.gov/study/NCT09000004"
    assert extract["nct"] == env(
        "NCT09000004", "known", "protocolSection.identificationModule.nctId", link=link
    )
    assert extract["digest"] == warrants.study_digest(study) and extract["link"] == link
    assert [c["piece"] for c in extract["inclusion"]] == [1] and [
        c["piece"] for c in extract["exclusion"]
    ] == [3]
    assert extract["standard_language"][1]["elements"] == [
        env(None, "unresolved", ELIGIBILITY_TEXT, STANDARD_RULE, UNTYPED, link)
    ]
    assert extract["standard_language"][0]["elements"][0]["note"] == "not profiled"
    assert [i["drug_class"]["value"]["state"] for i in extract["interventions"]] == [
        "stated_by_record",
        "not_looked_up",
    ]
    assert extract["arms"][0]["source"] == "protocolSection.armsInterventionsModule.armGroups[0]"


def test_the_results_flag_and_section_are_read_apart_and_a_permission_keys_its_own_element():
    """A flag without a results section and an empty results section under the flag are each read as the
    ledger reads them; a permitted atom's element is keyed by its effective section, as the profile counts
    it."""
    study = audited_study()
    study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
        "Exclusion Criteria:\n\n* Prior anti-PD-1 therapy is permitted\n"
    )
    study["hasResults"] = True
    flagged = study_extract(study, study_view(study, {}), {})
    assert flagged["efficacy"]["results"]["note"] == "flag_without_results"
    assert [e["value"]["element"] for e in flagged["standard_language"][0]["elements"]] == [
        "permitted:prior_agent:PD-1"
    ]
    study["resultsSection"] = {}
    assert study_extract(study, study_view(study, {}), {})["efficacy"]["results"]["value"] == "results posted"


# ── the decisions on one value ────────────────────────────────────────────────────────────────────────


def test_a_field_the_record_holds_is_known_exactly_as_held():
    study = results_study()
    assert stated(study, ("protocolSection", "eligibilityModule", "stdAges"), LINK) == env(
        ["ADULT"], "known", "protocolSection.eligibilityModule.stdAges"
    )
    study["protocolSection"]["eligibilityModule"]["stdAges"] = []
    assert stated(study, ("protocolSection", "eligibilityModule", "stdAges"), "x")["value"] == []
    assert stated(study, ("hasResults",), LINK) == env(True, "known", "hasResults")
    assert stated(study, ("protocolSection", "armsInterventionsModule", "armGroups", 1, "type"), LINK)[
        "source"
    ] == ("protocolSection.armsInterventionsModule.armGroups[1].type")


def test_an_absent_field_is_not_stated_with_its_absence_state_never_a_value():
    assert stated(ongoing_study(), ("protocolSection", "eligibilityModule", "maximumAge"), LINK) == env(
        None, "not_stated", "protocolSection.eligibilityModule.maximumAge", note="not_reported"
    )
    assert stated(results_study(), ("protocolSection", "eligibilityModule", "studyPopulation"), LINK)[
        "note"
    ] == ("not_applicable")
    withheld = ongoing_study()
    withheld["protocolSection"]["statusModule"]["overallStatus"] = "WITHHELD"
    del withheld["protocolSection"]["conditionsModule"]
    assert stated(withheld, ("protocolSection", "conditionsModule", "conditions"), LINK)["note"] == "redacted"


KNOWN_RULE = "coherence.resolve, known: stated evidence and strict relations"
INTERPOLATED_RULE = "coherence.resolve, interpolated: default relations added"
RESECTION = "coherence.resolve, proposal adjuvant_or_perioperative_when_resection_required alone"
NOT_ADJUVANT = (
    "neoadjuvant|definitive_chemoradiation|consolidation_after_chemoradiation|advanced_first_line"
    "|advanced_previously_treated|maintenance|local_consolidative_therapy"
)


def test_a_resolved_coordinate_is_known_and_a_proposed_narrowing_is_proposed():
    resolved = resolve([("inclusion", "prior_lines", ("0",), "advanced", "criterion 1")])
    assert coordinate_values(resolved["prior_advanced_lines"], "src", LINK) == (
        env(["0"], "known", "src", KNOWN_RULE, "resolved; 1|2|3+ removed by criterion 1"),
        env(["0"], "known", "src", INTERPOLATED_RULE, "no default relation narrows it"),
        [],
    )
    resected = resolve([("inclusion", "resection", ("resected",), "", "criterion 0")])
    known, interpolated, proposed = coordinate_values(resected["setting"], "src", LINK)
    assert (known["status"], known["note"]) == ("unresolved", "unnarrowed")
    assert known["value"] == list(resected["setting"]["domain"])
    assert (interpolated["status"], interpolated["note"]) == ("unresolved", "no default relation narrows it")
    assert proposed == [
        env(
            ["adjuvant", "perioperative"],
            "proposed",
            "src",
            RESECTION,
            f"unresolved; {NOT_ADJUVANT} removed by adjuvant_or_perioperative_when_resection_required",
        )
    ]


def test_a_defaults_narrowing_is_interpolated_never_known():
    """Positive: stage IV and no prior advanced line: the first-line default narrows the setting to one value,
    interpolated, with the removal it made. Negative: the known setting stays wide and unresolved."""
    row = resolve(
        [
            ("inclusion", "stage", ("IV",), "", "criterion 0"),
            ("inclusion", "prior_lines", ("0",), "advanced", "criterion 1"),
        ]
    )["setting"]
    known, interpolated, proposed = coordinate_values(row, "src", LINK)
    assert (known["value"], known["status"], known["note"]) == (list(SETTINGS), "unresolved", "unnarrowed")
    others = "|".join(s for s in SETTINGS if s != "advanced_first_line")
    assert interpolated == env(
        ["advanced_first_line"],
        "interpolated",
        "src",
        INTERPOLATED_RULE,
        f"resolved; {others} removed by first_line_when_no_prior_advanced_therapy",
    )
    assert proposed == []


def test_a_conflict_or_several_values_is_unresolved_never_known():
    conflict = resolve(
        [
            ("inclusion", "prior_lines", ("0",), "advanced", "criterion 1"),
            ("exclusion", "prior_lines", ("0",), "advanced", "criterion 2"),
        ]
    )
    known, interpolated, proposed = coordinate_values(conflict["prior_advanced_lines"], "src", LINK)
    assert known == env(
        [],
        "unresolved",
        "src",
        KNOWN_RULE,
        "conflict; 1|2|3+ removed by criterion 1; 0 removed by criterion 2",
    )
    assert (interpolated["status"], interpolated["note"]) == ("unresolved", "no default relation narrows it")
    assert proposed == []
    several = resolve([("inclusion", "prior_lines", ("0", "1"), "advanced", "criterion 1")])
    assert coordinate_values(several["prior_advanced_lines"], "src", LINK)[0]["status"] == "unresolved"


def test_a_proposed_relation_that_leaves_no_value_is_unresolved_never_proposed():
    """A resection required (a proposal: adjuvant or perioperative) and a prior advanced line required (a
    default: previously treated or maintenance): the proposal, alone on the interpolated domain, leaves
    nothing, a conflict at its own level only."""
    row = resolve(
        [
            ("inclusion", "resection", ("resected",), "", "criterion 0"),
            ("inclusion", "prior_lines", ("1", "2", "3+"), "advanced", "criterion 1"),
        ]
    )["setting"]
    known, interpolated, proposed = coordinate_values(row, "src", LINK)
    assert (known["value"], known["status"]) == (list(SETTINGS), "unresolved")
    assert (interpolated["value"], interpolated["status"]) == (
        ["advanced_previously_treated", "maintenance"],
        "interpolated",
    )
    assert proposed == [
        env(
            [],
            "unresolved",
            "src",
            RESECTION,
            "conflict; advanced_previously_treated|maintenance removed by "
            "adjuvant_or_perioperative_when_resection_required",
        )
    ]


@pytest.mark.parametrize(
    "state, value, status, note",
    [
        ("posted", "results posted", "known", ""),
        ("not_posted", "no results posted", "not_posted", ""),
        ("flag_not_reported", "the results flag is not reported", "not_stated", "flag_not_reported"),
        (
            "flag_without_results",
            "the registry flags results as posted, but this record holds no results section",
            "unresolved",
            "flag_without_results",
        ),
        (
            "results_without_flag",
            "this record holds a results section, but the registry's results flag is false",
            "unresolved",
            "results_without_flag",
        ),
    ],
)
def test_results_are_posted_or_no_results_posted(state, value, status, note):
    assert results_value(state, LINK) == env(value, status, "hasResults", "ledger.results_state", note)


def test_an_untyped_criterion_has_no_tier_and_is_never_not_met():
    assert standard_values([], {"x": (1.0, 1.0, 1.0, "met")}, LINK) == [
        env(None, "unresolved", ELIGIBILITY_TEXT, STANDARD_RULE, UNTYPED)
    ]
    assert standard_values(["inclusion:x"], {}, LINK) == [
        env(
            {
                "element": "inclusion:x",
                "tier": None,
                "statement_rate": None,
                "lower_bound": None,
                "upper_bound": None,
            },
            "unresolved",
            ELIGIBILITY_TEXT,
            STANDARD_RULE,
            "not profiled",
        )
    ]
    # an element not profiled does not end the criterion: the next one is still read
    after = standard_values(["inclusion:x", "inclusion:a"], {"inclusion:a": (1.0, 1.0, 1.0, "met")}, LINK)
    assert [(v["value"]["element"], v["status"]) for v in after] == [
        ("inclusion:x", "unresolved"),
        ("inclusion:a", "known"),
    ]


def test_each_element_carries_its_tier_once():
    tiers = {
        "inclusion:a": (0.95, 0.95, 1.0, "met"),
        "inclusion:b": (0.1, 0.1, 0.2, "not_met"),
        "inclusion:c": (0.5, 0.5, 1.0, "unresolved"),
    }
    values = standard_values(["inclusion:a", "inclusion:b", "inclusion:a", "inclusion:c"], tiers, LINK)
    assert values == [
        env(
            {"element": e, "tier": t[3], "statement_rate": t[0], "lower_bound": t[1], "upper_bound": t[2]},
            status,
            ELIGIBILITY_TEXT,
            STANDARD_RULE,
            note,
        )
        for e, t, status, note in (
            ("inclusion:a", tiers["inclusion:a"], "known", ""),
            ("inclusion:b", tiers["inclusion:b"], "known", ""),
            ("inclusion:c", tiers["inclusion:c"], "unresolved", "unresolved"),
        )
    ]


def outcome(kind, measure, frame):
    return (kind, measure, frame, endpoint_classes(measure), time_points(frame))


def test_biomarkers_come_by_role_from_the_atoms_and_the_outcomes():
    text = "* Prior anti-PD-1 therapy is permitted; ALK negative"
    criteria = [
        (2, "inclusion", text, type_criterion(text)),
        (4, "exclusion", "* EGFR mutation", type_criterion("* EGFR mutation")),
    ]
    outcomes = [
        outcome("primary", "Overall survival", "5 years"),
        outcome("primary", "ctDNA clearance", "Week 8, 8 weeks"),
        outcome("secondary", "Change in PD-L1 expression", "12 weeks"),
        outcome("other", "Tumour mutational burden", "Baseline"),
    ]
    roles = biomarker_values(criteria, outcomes, LINK)
    assert roles["eligibility"] == [
        env(
            {
                "biomarker": "ALK",
                "states": ["negative"],
                "params": {},
                "span": "ALK",
                "piece": 2,
                "section": "inclusion",
            },
            "known",
            ELIGIBILITY_TEXT,
            "banks.biomarker_status",
            "piece 2",
        ),
        env(
            {
                "biomarker": "EGFR",
                "states": ["positive"],
                "params": {},
                "span": "EGFR",
                "piece": 4,
                "section": "exclusion",
            },
            "known",
            ELIGIBILITY_TEXT,
            "banks.biomarker_status",
            "piece 4",
        ),
    ]
    assert roles["outcome"] == [
        env(
            {
                "outcome_type": "primary",
                "measure": "ctDNA clearance",
                "time_frame": "Week 8, 8 weeks",
                "time_points": ["8 week"],
            },
            "known",
            "protocolSection.outcomesModule.primaryOutcomes[1]",
            "banks.endpoint_classes",
        ),
        env(
            {
                "outcome_type": "secondary",
                "measure": "Change in PD-L1 expression",
                "time_frame": "12 weeks",
                "time_points": ["12 week"],
            },
            "known",
            "protocolSection.outcomesModule.secondaryOutcomes[0]",
            "banks.endpoint_classes",
        ),
    ]
    assert roles["exploratory"] == [
        env(
            {
                "outcome_type": "other",
                "measure": "Tumour mutational burden",
                "time_frame": "Baseline",
                "time_points": [],
            },
            "known",
            "protocolSection.outcomesModule.otherOutcomes[0]",
            "banks.endpoint_classes",
        )
    ]


def test_a_drug_target_or_an_unnamed_endpoint_is_no_biomarker():
    text = "* No prior anti-PD-L1 antibody"
    criteria = [(0, "exclusion", text, type_criterion(text))]
    roles = biomarker_values(criteria, [outcome("primary", "Overall survival", "5 years")], LINK)
    assert roles == {"eligibility": [], "outcome": [], "exploratory": []}
    permitted = "* EGFR mutation is permitted"
    found = biomarker_values([(1, "exclusion", permitted, type_criterion(permitted))], [], LINK)
    assert found["eligibility"][0]["value"]["section"] == "permitted"


def test_another_atom_before_a_biomarker_does_not_hide_it_and_time_points_are_a_list():
    text = "* ECOG 0-1 and EGFR mutation positive"
    atoms = type_criterion(text)
    assert [atom[1] for atom in atoms] == ["ecog_ps", "biomarker:EGFR"]
    found = biomarker_values([(1, "inclusion", text, atoms)], [], LINK)
    assert [(v["value"]["biomarker"], v["value"]["states"]) for v in found["eligibility"]] == [
        ("EGFR", ["positive"])
    ]
    held = biomarker_values([], [("other", "ctDNA", "8 weeks", ["biomarker_endpoint"], ("8 week",))], LINK)
    assert held["exploratory"][0]["value"]["time_points"] == ["8 week"]


def test_an_experimental_drugs_class_is_known_from_rxclass_or_its_own_entry():
    rule = "classes.drug_class (NLM RxClass, has_epc)"
    found = ("XB-1", "classified", ["PD-1 Blocker"], "XB-1")
    value = {"state": "classified", "classes": ["PD-1 Blocker"], "resolved_by": "XB-1"}
    assert drug_class_value(found, "src", LINK) == env(value, "known", "src", rule)
    # the classes are carried as a list, whatever sequence the reading holds them in
    assert drug_class_value(("XB-1", "classified", ("PD-1 Blocker",), "XB-1"), "src", LINK)["value"] == value
    stated_class = ("XB-1", "stated_by_record", ["stated: PD-1"], "description")
    assert drug_class_value(stated_class, "src", LINK) == env(
        {"state": "stated_by_record", "classes": ["stated: PD-1"], "resolved_by": "description"},
        "known",
        "src",
        "banks.stated_targets (the entry's own description)",
    )


@pytest.mark.parametrize("state", ["unresolved", "lookup_failed"])
def test_an_unclassed_or_non_experimental_drug_is_unresolved(state):
    value = {"state": state, "classes": [], "resolved_by": ""}
    assert drug_class_value(("XB-1", state, [], ""), "src", LINK) == env(
        value, "unresolved", "src", "classes.drug_class (NLM RxClass, has_epc)", state
    )
    assert drug_class_value(None, "src", LINK) == env(
        None, "unresolved", "src", "classes.experimental_drugs", NOT_EXPERIMENTAL
    )


def axes(identity, reason):
    return {
        "drug": "XB-1",
        "identity": identity,
        "reason": reason,
        "identities": [],
        "assertions": [],
        "targets": ["PD-1"],
        "alignment": [],
        "atc": ("", []),
    }


def test_axes_resolved_by_the_own_name_are_known():
    rendered = {
        "drug": "XB-1",
        "identity": "resolved",
        "reason": "own_name",
        "names": [],
        "classes": [],
        "targets": ["PD-1"],
        "alignment": [],
        "atc": {"basis": "", "classes": []},
    }
    assert axes_value(axes("resolved", "own_name"), "src", LINK) == env(
        rendered, "known", "src", "classes.drug_axes through reading.drug_axes_view"
    )


@pytest.mark.parametrize(
    "identity, reason", [("not_looked_up", "own_name_not_looked_up"), ("conflict", "alias_other_concept")]
)
def test_axes_not_resolved_or_of_no_experimental_drug_are_unresolved(identity, reason):
    held = axes_value(axes(identity, reason), "src", LINK)
    assert (held["status"], held["note"], held["value"]["identity"]) == (
        "unresolved",
        f"{identity}: {reason}",
        identity,
    )
    assert axes_value(None, "src", LINK) == env(
        None, "unresolved", "src", "classes.experimental_drugs", NOT_EXPERIMENTAL
    )


def test_endpoints_by_class_with_their_time_points():
    trials = [
        ("NCT2", [outcome("primary", "Overall survival", "Up to 5 years"), outcome("other", "Notes", "")]),
        (
            "NCT1",
            [
                outcome("primary", "Overall survival and progression-free survival", "5 years, 5 years"),
                outcome("secondary", "Overall survival", "2 years"),
            ],
        ),
        ("NCT3", [outcome("primary", "Progression-free survival", "6 months")]),
    ]
    assert endpoint_profile(trials) == [
        ("primary", "overall_survival", 2, ["NCT1", "NCT2"], 2, [("5 year", 2)]),
        ("primary", "progression_free_survival", 2, ["NCT1", "NCT3"], 2, [("5 year", 1), ("6 month", 1)]),
        ("secondary", "overall_survival", 1, ["NCT1"], 1, [("2 year", 1)]),
        ("other", "(no endpoint class)", 1, ["NCT2"], 1, []),
    ]
    assert endpoint_profile([]) == [] and endpoint_profile([("NCT1", [])]) == []


def test_more_trials_rank_first_and_a_time_point_counts_once_an_outcome():
    trials = [
        ("NCT1", [("primary", "m", "f", ["progression_free_survival"], ("5 year", "5 year"))]),
        ("NCT2", [("primary", "m", "f", ["progression_free_survival", "overall_survival"], ())]),
    ]
    assert endpoint_profile(trials) == [
        ("primary", "progression_free_survival", 2, ["NCT1", "NCT2"], 2, [("5 year", 1)]),
        ("primary", "overall_survival", 1, ["NCT2"], 1, []),
    ]


# ── the assembly functions ────────────────────────────────────────────────────────────────────────────


def test_criteria_go_to_their_sections_with_their_atoms():
    criteria = [
        (0, "unsectioned", "* Adults", []),
        (2, "inclusion", "* ECOG 0-1", type_criterion("* ECOG 0-1")),
        (4, "exclusion", "* Pregnancy", type_criterion("* Pregnancy")),
    ]
    sections = criterion_sections(criteria, LINK)
    assert sections["unsectioned"] == [
        {
            "piece": 0,
            "text": env("* Adults", "known", ELIGIBILITY_TEXT, "criteria.itemize", "piece 0"),
            "atoms": [],
        }
    ]
    assert sections["inclusion"][0]["atoms"] == [
        env(
            {
                "bank": "performance_status",
                "concept": "ecog_ps",
                "values": ["0", "1"],
                "params": {},
                "span": "0-1",
                "section": "inclusion",
                "element": "inclusion:ecog_ps=0|1",
            },
            "known",
            ELIGIBILITY_TEXT,
            "banks.performance_status",
            "piece 2",
        )
    ]
    assert [atom["value"]["element"] for atom in sections["exclusion"][0]["atoms"]] == [
        "exclusion:condition=pregnancy_or_breastfeeding"
    ]
    assert criterion_sections([], LINK) == {"inclusion": [], "exclusion": [], "unsectioned": []}


def test_an_atom_keeps_its_criterions_section_but_carries_its_effective_one():
    text = "* Prior anti-PD-1 therapy is permitted"
    [criterion] = criterion_sections([(3, "exclusion", text, type_criterion(text))], LINK)["exclusion"]
    assert [(a["value"]["section"], a["value"]["element"]) for a in criterion["atoms"]] == [
        ("permitted", "permitted:prior_agent:PD-1")
    ]


def test_outcomes_are_planned_by_type_with_their_bank_readings():
    study = results_study()
    view = study_view(study, {})
    sections = outcome_sections(study, view["outcomes"], LINK)
    assert sections["secondary"] == [
        {
            "measure": env(
                "Progression-free survival",
                "known",
                "protocolSection.outcomesModule.secondaryOutcomes[0].measure",
            ),
            "time_frame": env(
                "Up to 2 years", "known", "protocolSection.outcomesModule.secondaryOutcomes[0].timeFrame"
            ),
            "description": env(
                None,
                "not_stated",
                "protocolSection.outcomesModule.secondaryOutcomes[0].description",
                note="not_reported",
            ),
            "endpoint_classes": env(
                ["progression_free_survival"],
                "known",
                "protocolSection.outcomesModule.secondaryOutcomes[0].measure",
                "banks.endpoint_classes",
            ),
            "time_points": env(
                ["2 year"],
                "known",
                "protocolSection.outcomesModule.secondaryOutcomes[0].timeFrame",
                "banks.time_points",
            ),
        }
    ]
    assert list(sections) == ["primary", "secondary", "other"]
    assert outcome_sections(ongoing_study(), [], LINK) == {"primary": [], "secondary": [], "other": []}
    # the bank readings are carried as lists, whatever sequence the reading holds them in
    held = outcome_sections(study, [("primary", "m", "f", ("overall_survival",), ("1 week",))], LINK)[
        "primary"
    ][0]
    assert (held["endpoint_classes"]["value"], held["time_points"]["value"]) == (
        ["overall_survival"],
        ["1 week"],
    )


def test_posted_measurements_pair_with_the_readings_rows():
    study = results_study()
    results = study_view(study, {})["results"]
    measured = posted_measurements(study, results, LINK)
    assert measured[1] == env(
        {
            "outcome_type": "PRIMARY",
            "measure": "Objective response rate",
            "time_frame": "Week 24",
            "unit": "Participants",
            "param_type": "COUNT_OF_PARTICIPANTS",
            "dispersion_type": None,
            "arm": "Placebo",
            "group_id": "OG001",
            "class": None,
            "category": None,
            "value": "6",
            "spread": None,
            "lower_limit": None,
            "upper_limit": None,
            "endpoint_classes": ["objective_response_rate"],
        },
        "known",
        "resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[1]",
        "landscape.posted_measurements",
    )
    with pytest.raises(ValueError):
        posted_measurements(study, results[:1], LINK)
    assert posted_measurements(ongoing_study(), [], LINK) == []


def measured(
    measure, unit, param, dispersion, arm, group, klass, category, value, spread, low, high, classes
):
    return {
        "outcome_type": measure[0],
        "measure": measure[1],
        "time_frame": measure[2],
        "unit": unit,
        "param_type": param,
        "dispersion_type": dispersion,
        "arm": arm,
        "group_id": group,
        "class": klass,
        "category": category,
        "value": value,
        "spread": spread,
        "lower_limit": low,
        "upper_limit": high,
        "endpoint_classes": classes,
    }


def test_every_posted_measurement_of_every_class_and_category_is_read_with_its_own_fields():
    """Two measures, the first with two classes (titled, with titled categories) and groups the second lacks;
    a measurement whose group the groups do not name reads no arm."""
    survival = {
        "type": "PRIMARY",
        "title": "Overall survival",
        "timeFrame": "5 years",
        "unitOfMeasure": "months",
        "paramType": "MEDIAN",
        "dispersionType": "95% Confidence Interval",
        "groups": [{"id": "OG000", "title": "Arm A"}, {"id": "OG001", "title": "Arm B"}],
        "classes": [
            {
                "title": "All",
                "categories": [
                    {
                        "title": "Overall",
                        "measurements": [
                            {"groupId": "OG000", "value": "12.1", "lowerLimit": "10.0", "upperLimit": "14.2"},
                            {
                                "groupId": "OG001",
                                "value": "9.8",
                                "spread": "2.1",
                                "lowerLimit": "8",
                                "upperLimit": "11",
                            },
                        ],
                    }
                ],
            },
            {
                "title": "Subgroup",
                "categories": [{"title": "PD-L1 high", "measurements": [{"groupId": "OG9", "value": "15"}]}],
            },
        ],
    }
    notes = {
        "type": "OTHER_PRE_SPECIFIED",
        "title": "Notes",
        "classes": [{"categories": [{"measurements": [{"groupId": "X", "value": "1"}]}]}],
    }
    # a measure with no classes, a class with no categories, a category with no measurements: nothing posted
    survival["classes"] += [{"title": "Empty"}, {"title": "Bare", "categories": [{"title": "None posted"}]}]
    unposted = {"type": "SECONDARY", "title": "Overall survival at 2 years"}
    study = {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [survival, notes, unposted]}}}
    rows = [(row[0], tuple(row[1]), *row[2:]) for row in study_view(study, {})["results"]]
    first = ("PRIMARY", "Overall survival", "5 years")
    shared = ("months", "MEDIAN", "95% Confidence Interval")
    base = "resultsSection.outcomeMeasuresModule.outcomeMeasures"
    expected = [
        (
            measured(
                first,
                *shared,
                "Arm A",
                "OG000",
                "All",
                "Overall",
                "12.1",
                None,
                "10.0",
                "14.2",
                ["overall_survival"],
            ),
            f"{base}[0].classes[0].categories[0].measurements[0]",
        ),
        (
            measured(
                first,
                *shared,
                "Arm B",
                "OG001",
                "All",
                "Overall",
                "9.8",
                "2.1",
                "8",
                "11",
                ["overall_survival"],
            ),
            f"{base}[0].classes[0].categories[0].measurements[1]",
        ),
        (
            measured(
                first,
                *shared,
                None,
                "OG9",
                "Subgroup",
                "PD-L1 high",
                "15",
                None,
                None,
                None,
                ["overall_survival"],
            ),
            f"{base}[0].classes[1].categories[0].measurements[0]",
        ),
        (
            measured(
                ("OTHER_PRE_SPECIFIED", "Notes", None),
                None,
                None,
                None,
                None,
                "X",
                None,
                None,
                "1",
                None,
                None,
                None,
                [],
            ),
            f"{base}[1].classes[0].categories[0].measurements[0]",
        ),
    ]
    assert posted_measurements(study, rows, LINK) == [
        env(value, "known", source, "landscape.posted_measurements") for value, source in expected
    ]


def test_posted_events_are_read_per_arm_and_never_filled():
    groups, events = posted_events(results_study(), LINK)
    assert groups[1] == env(
        {
            "group_id": "EG001",
            "title": "Placebo",
            "deaths_affected": 0,
            "deaths_at_risk": 60,
            "serious_affected": 2,
            "serious_at_risk": 60,
            "other_affected": 20,
            "other_at_risk": 60,
        },
        "known",
        "resultsSection.adverseEventsModule.eventGroups[1]",
        "landscape.posted_events",
    )
    assert events[3] == env(
        {
            "table": "other",
            "term": "Fatigue",
            "organ_system": "General disorders",
            "source_vocabulary": None,
            "assessment_type": None,
            "group_id": "EG001",
            "arm": "Placebo",
            "affected": 10,
            "at_risk": None,
            "events": 12,
        },
        "known",
        "resultsSection.adverseEventsModule.otherEvents[0].stats[1]",
        "landscape.posted_events",
    )
    assert [e["value"]["table"] for e in events] == ["serious", "serious", "other", "other"]
    assert events[0] == env(
        {
            "table": "serious",
            "term": "Pneumonitis",
            "organ_system": "Respiratory, thoracic and mediastinal disorders",
            "source_vocabulary": "MedDRA 21.0",
            "assessment_type": "SYSTEMATIC_ASSESSMENT",
            "group_id": "EG000",
            "arm": "Testamab",
            "affected": 3,
            "at_risk": 60,
            "events": 4,
        },
        "known",
        "resultsSection.adverseEventsModule.seriousEvents[0].stats[0]",
        "landscape.posted_events",
    )
    assert posted_events(ongoing_study(), LINK) == ([], [])
    # an event with no statistics posts nothing per arm
    bare = {"resultsSection": {"adverseEventsModule": {"otherEvents": [{"term": "Rash"}]}}}
    assert posted_events(bare, LINK) == ([], [])


def test_publications_carry_their_registry_role_and_documents_their_link():
    references, documents = reference_values(results_study(), "NCT01234567", LINK)
    assert references[2] == env(
        {
            "pmid": None,
            "type": "BACKGROUND",
            "role": "entered by the responsible party, not marked as reporting results",
            "citation": "Author C. Background. J Ex. 2015.",
            "pubmed": "",
        },
        "known",
        "protocolSection.referencesModule.references[2]",
        "links.reference_role",
    )
    assert references[0]["value"] == {
        "pmid": "31589554",
        "type": "RESULT",
        "role": "reports results from this study, as the responsible party marked it",
        "citation": "Author A. Results paper. J Ex. 2020.",
        "pubmed": "https://pubmed.ncbi.nlm.nih.gov/31589554/",
    }
    assert documents == [
        env(
            {
                "type": "Prot_SAP",
                "label": "Study Protocol and Statistical Analysis Plan",
                "has_protocol": True,
                "has_sap": True,
                "has_icf": False,
                "date": "2019-01-07",
                "upload_date": "2020-05-01T09:08",
                "filename": "Prot_SAP_000.pdf",
                "url": "https://cdn.clinicaltrials.gov/large-docs/67/NCT01234567/Prot_SAP_000.pdf",
            },
            "known",
            "documentSection.largeDocumentModule.largeDocs[0]",
            "links.document_link",
        )
    ]
    assert reference_values(results_study(), "not an id", LINK)[1][0]["value"]["url"] == ""
    assert reference_values(audited_study(), "NCT09000004", LINK)[1] == []


def test_interventions_carry_their_class_axes_and_modality():
    study = audited_study()
    entries = landscape.intervention_sections(study, study_view(study, {}), LINK)
    xb1, placebo = entries
    assert xb1["entry"] == env(
        {"type": "DRUG", "name": "XB-1", "description": "XB-1 is an anti-PD-1 antibody"},
        "known",
        "protocolSection.armsInterventionsModule.interventions[0]",
    )
    assert xb1["drug_class"]["value"] == {
        "state": "stated_by_record",
        "classes": ["stated: PD-1"],
        "resolved_by": "description",
    }
    assert (xb1["axes"]["status"], xb1["axes"]["note"]) == (
        "unresolved",
        "not_looked_up: own_name_not_looked_up",
    )
    assert [(m["value"]["value"], m["status"]) for m in xb1["modality"]] == [("antibody", "known")]
    assert xb1["modality"][0]["source"].startswith(
        "protocolSection.armsInterventionsModule.interventions[0]."
    )
    assert placebo["drug_class"]["value"]["state"] == "not_looked_up" and placebo["modality"] == []
    unnamed = audited_study()
    unnamed["protocolSection"]["armsInterventionsModule"]["interventions"][0]["name"] = ["XB-1"]
    view = study_view(audited_study(), {})
    assert landscape.intervention_sections(unnamed, view, LINK)[0]["drug_class"]["note"] == NOT_EXPERIMENTAL


# ── the validator ─────────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def valid():
    return json.loads(json.dumps(record_for()))


def broken(record, change):
    copied = copy.deepcopy(record)
    change(copied)
    return schema_problems(copied)


def test_a_record_that_is_not_an_object_is_refused():
    assert schema_problems([]) == (("not_an_object", ""),)
    assert schema_problems(None) == (("not_an_object", ""),)


def test_the_version_and_the_description_are_the_schemas(valid):
    # a record of schema 1 (before the coordinates' statuses) is not read as schema 2
    assert broken(valid, lambda r: r.update(schema_version="1")) == (
        ("unknown_schema_version", "schema_version"),
    )
    assert broken(valid, lambda r: r["fields"].pop("cohort")) == (("fields_differ", "fields"),)
    assert broken(valid, lambda r: r["statuses"].update(known="likely")) == (("statuses_differ", "statuses"),)
    assert broken(valid, lambda r: r["envelope"].pop("note")) == (("envelope_differ", "envelope"),)


def test_an_undescribed_or_missing_field_is_named(valid):
    assert broken(valid, lambda r: r["studies"][1]["population"].update(age="old")) == (
        ("undescribed_field", "studies[1].population.age"),
    )
    assert broken(valid, lambda r: r.update(extra=1)) == (("undescribed_field", "extra"),)
    assert broken(valid, lambda r: r["studies"][0].pop("sponsor")) == (
        ("missing_field", "studies[0].sponsor"),
    )
    assert broken(valid, lambda r: r["manifest"].pop("retrieval")) == (
        ("missing_field", "manifest.retrieval"),
    )


def test_a_wrong_type_is_named(valid):
    assert broken(valid, lambda r: r.update(cohort=[])) == (("wrong_type", "cohort"),)
    assert broken(valid, lambda r: r["studies"][0].update(arms={})) == (("wrong_type", "studies[0].arms"),)
    assert broken(valid, lambda r: r["cohort"].update(frequency="rows")) == (
        ("wrong_type", "cohort.frequency"),
    )
    assert broken(valid, lambda r: r["studies"].append("NCT1")) == (
        ("wrong_type", "studies[5]"),
        ("study_mismatch", "coverage.studies"),
        ("digest_mismatch", "manifest.study_digests"),
    )


def test_a_malformed_value_is_named(valid):
    assert broken(valid, lambda r: r["studies"][0].update(sponsor="Example Pharma")) == (
        ("malformed_value", "studies[0].sponsor"),
    )
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].pop("note")) == (
        ("malformed_value", "studies[0].sponsor"),
    )
    reordered = {"status": "known", "value": "x", "source": "s", "rule": "", "note": "", "link": LINK}
    assert broken(valid, lambda r: r["studies"][0].update(sponsor=reordered)) == (
        ("malformed_value", "studies[0].sponsor"),
    )


def test_a_status_outside_the_vocabulary_or_its_field_is_named(valid):
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(status="likely")) == (
        ("unknown_status", "studies[0].sponsor"),
    )
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(status=["known"])) == (
        ("unknown_status", "studies[0].sponsor"),
    )
    posted = "studies[0].efficacy.measurements[0]"
    assert broken(
        valid, lambda r: r["studies"][0]["efficacy"]["measurements"][0].update(status="not_posted")
    ) == (("status_not_allowed", posted),)
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(status="proposed")) == (
        ("status_not_allowed", "studies[0].sponsor"),
    )


def test_a_value_without_its_source_or_its_studys_link_is_named(valid):
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(source="")) == (
        ("no_source", "studies[0].sponsor"),
    )
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(source="", rule="a rule")) == ()
    assert broken(valid, lambda r: r["studies"][0]["sponsor"].update(link="")) == (
        ("no_link", "studies[0].sponsor"),
    )
    assert broken(
        valid, lambda r: r["studies"][0]["sponsor"].update(link="https://clinicaltrials.gov/study/NCT1")
    ) == (("wrong_link", "studies[0].sponsor"),)


def test_a_posted_value_not_from_the_results_section_is_named(valid):
    def planned_as_posted(record):
        record["studies"][0]["safety"]["events"][0]["source"] = (
            "protocolSection.outcomesModule.primaryOutcomes[0]"
        )

    assert broken(valid, planned_as_posted) == (("posted_not_from_results", "studies[0].safety.events[0]"),)

    def other_section(record):
        record["studies"][0]["outcomes"]["primary"][0]["measure"]["source"] = "anything"

    assert broken(valid, other_section) == ()


def test_a_manifest_that_disagrees_with_its_studies_is_named(valid):
    assert broken(valid, lambda r: r["manifest"]["study_digests"].reverse()) == (
        ("digest_mismatch", "manifest.study_digests"),
        ("root_mismatch", "manifest.merkle_root"),
    )
    assert broken(valid, lambda r: r["manifest"].update(merkle_root="0" * 64)) == (
        ("root_mismatch", "manifest.merkle_root"),
    )
    assert broken(valid, lambda r: r["manifest"].update(study_digests=[1, 2, 3, 4, 5])) == (
        ("wrong_type", "manifest.study_digests"),
        ("digest_mismatch", "manifest.study_digests"),
        ("root_mismatch", "manifest.merkle_root"),
    )
    assert broken(valid, lambda r: r["studies"][0].update(digest="0" * 64)) == (
        ("digest_mismatch", "manifest.study_digests"),
    )


def test_a_nested_value_is_held_to_its_studys_link(valid):
    other = "https://clinicaltrials.gov/study/NCT1"
    assert broken(valid, lambda r: r["studies"][0]["population"]["sex"].update(link=other)) == (
        ("wrong_link", "studies[0].population.sex"),
    )
    assert broken(valid, lambda r: r["studies"][0].pop("link")) == (("missing_field", "studies[0].link"),)


def test_one_problem_does_not_end_the_walk(valid):
    def several(record):
        record["cohort"] = []
        record["studies"][0].pop("sponsor")
        record["studies"][0]["phases"] = "PHASE2"
        record["studies"][0]["study_type"] = "INTERVENTIONAL"
        record["studies"][1]["population"]["sex"]["status"] = "likely"

    assert broken(valid, several) == (
        ("wrong_type", "cohort"),
        ("missing_field", "studies[0].sponsor"),
        ("malformed_value", "studies[0].phases"),
        ("malformed_value", "studies[0].study_type"),
        ("unknown_status", "studies[1].population.sex"),
    )


def test_problems_are_named_level_by_level(valid):
    def shallow_and_deep(record):
        record["studies"][0]["sponsor"]["status"] = "likely"
        record["studies"][1]["population"]["sex"]["status"] = "likely"

    assert broken(valid, shallow_and_deep) == (
        ("unknown_status", "studies[0].sponsor"),
        ("unknown_status", "studies[1].population.sex"),
    )


@pytest.mark.parametrize("value", [list(landscape.ENVELOPE), 5, "Example Pharma", None])
def test_anything_but_an_envelope_is_malformed(valid, value):
    assert broken(valid, lambda r: r["studies"][0].update(sponsor=value)) == (
        ("malformed_value", "studies[0].sponsor"),
    )


def test_a_posted_value_needs_a_results_section_source(valid):
    first = "studies[0].efficacy.measurements[0]"
    for source in (None, "resultsSectionCopy.outcomeMeasures[0]"):
        assert broken(
            valid, lambda r, s=source: r["studies"][0]["efficacy"]["measurements"][0].update(source=s)
        ) == (("posted_not_from_results", first),)


@pytest.mark.parametrize(
    "change, problems",
    [
        (lambda r: r.update(manifest=[1]), (("wrong_type", "manifest"),)),
        (lambda r: r.update(studies="NCT1"), (("wrong_type", "studies"),)),
        (
            lambda r: r["manifest"].update(study_digests=None),
            (
                ("wrong_type", "manifest.study_digests"),
                ("digest_mismatch", "manifest.study_digests"),
                ("root_mismatch", "manifest.merkle_root"),
            ),
        ),
        (
            lambda r: r["manifest"].update(study_digests=[*r["manifest"]["study_digests"][:4], 1]),
            (
                ("wrong_type", "manifest.study_digests"),
                ("digest_mismatch", "manifest.study_digests"),
                ("root_mismatch", "manifest.merkle_root"),
            ),
        ),
    ],
)
def test_a_manifest_or_studies_of_the_wrong_type_is_named_once(valid, change, problems):
    assert broken(valid, change) == problems


def test_a_wrong_section_does_not_end_its_level_and_digests_held_otherwise_than_as_a_list_are_refused(valid):
    def wrong_manifest(record):
        record["manifest"] = [1]
        record["studies"][0]["sponsor"] = "Example Pharma"

    assert broken(valid, wrong_manifest) == (
        ("wrong_type", "manifest"),
        ("malformed_value", "studies[0].sponsor"),
    )
    held_as_tuple = copy.deepcopy(valid)
    held_as_tuple["manifest"]["study_digests"] = tuple(held_as_tuple["manifest"]["study_digests"])
    assert schema_problems(held_as_tuple) == (
        ("wrong_type", "manifest.study_digests"),
        ("digest_mismatch", "manifest.study_digests"),
        ("root_mismatch", "manifest.merkle_root"),
    )


def raised(call, *args):
    """What a call raises, as a value: (the exception's type name, its args)."""
    try:
        call(*args)
    except Exception as error:
        return type(error).__name__, error.args
    return None


def test_every_intervention_entry_reads_its_class_axes_and_modality_in_full():
    study = results_study()
    view = study_view(study, {})
    base = "protocolSection.armsInterventionsModule.interventions"
    entries = study["protocolSection"]["armsInterventionsModule"]["interventions"]
    not_experimental = env(None, "unresolved", f"{base}[1]", "classes.experimental_drugs", NOT_EXPERIMENTAL)
    assert landscape.intervention_sections(study, view, LINK) == [
        {
            "entry": env(entries[0], "known", f"{base}[0]"),
            "drug_class": env(
                {"state": "not_looked_up", "classes": [], "resolved_by": ""},
                "unresolved",
                f"{base}[0]",
                "classes.drug_class (NLM RxClass, has_epc)",
                "not_looked_up",
            ),
            "axes": env(
                {
                    "drug": "Testamab",
                    "identity": "not_looked_up",
                    "reason": "own_name_not_looked_up",
                    "names": [],
                    "classes": [],
                    "targets": [],
                    "alignment": [],
                    "atc": {"basis": "", "classes": []},
                },
                "unresolved",
                f"{base}[0]",
                "classes.drug_axes through reading.drug_axes_view",
                "not_looked_up: own_name_not_looked_up",
            ),
            "modality": [
                env(
                    {
                        "property": "modality",
                        "value": "antibody",
                        "polarity": "asserted",
                        "scope": "intervention entry",
                        "warrant": view["properties"][0][8],
                    },
                    "interpolated",
                    f"{base}[0].name[0:8]",
                    "name_stem:antibody",
                )
            ],
        },
        {
            "entry": env(entries[1], "known", f"{base}[1]"),
            "drug_class": not_experimental,
            "axes": not_experimental,
            "modality": [],
        },
    ]
    pair = near_miss_study("NCT09000001", "0-1")
    [placebo] = landscape.intervention_sections(pair, study_view(pair, ANSWERS), LINK)
    assert placebo["drug_class"] == env(
        {"state": "classified", "classes": [PLACEBO_EPC[1]], "resolved_by": "Placebo"},
        "known",
        f"{base}[0]",
        "classes.drug_class (NLM RxClass, has_epc)",
    )


def test_a_view_without_its_drugs_or_axes_is_refused_by_name():
    assert raised(landscape.intervention_sections, {}, {"x": None}, "x") == ("KeyError", ("drugs",))
    assert raised(landscape.intervention_sections, {}, {"drugs": []}, "x") == ("KeyError", ("drug_axes",))


# ── what the record itself shows: types, links, results and the studies it names ─────────────────────

OTHER = "https://clinicaltrials.gov/study/NCT07654321"


def test_a_studys_link_is_its_own_nct_numbers_page_and_a_null_one_exempts_nothing(valid):
    assert broken(valid, lambda r: r["studies"][0].update(link=None)) == (("wrong_link", "studies[0].link"),)

    def null_link_and_another_studys_value(record):
        record["studies"][0]["link"] = None
        record["studies"][0]["sponsor"]["link"] = "https://clinicaltrials.gov/study/NCT1"

    assert broken(valid, null_link_and_another_studys_value) == (
        ("wrong_link", "studies[0].link"),
        ("wrong_link", "studies[0].sponsor"),
    )


def test_a_study_moved_whole_to_another_studys_page_is_named_at_every_value(valid):
    def relinked(record):
        record["studies"][0]["link"] = OTHER
        for _path, value in envelopes(record["studies"][0]):
            value["link"] = OTHER

    problems = broken(valid, relinked)
    assert problems[0] == ("wrong_link", "studies[0].link")
    assert {code for code, _ in problems} == {"wrong_link"}
    assert len(problems) == 1 + len(envelopes(valid["studies"][0]))


@pytest.mark.parametrize(
    "change, problem",
    [
        (lambda r: r["manifest"].update(api_version=5), ("wrong_type", "manifest.api_version")),
        (lambda r: r["cohort"].update(frequency=[{"x": 1}]), ("wrong_type", "cohort.frequency")),
        (lambda r: r["coverage"].update(universe="x"), ("wrong_type", "coverage.universe")),
        (lambda r: r["review_queue"][0].pop("answer"), ("wrong_type", "review_queue")),
        (
            lambda r: r["studies"][0]["standard_language"][0].update(piece="a"),
            ("wrong_type", "studies[0].standard_language[0].piece"),
        ),
        (
            lambda r: r["studies"][0]["standard_language"][0].update(piece=True),
            ("wrong_type", "studies[0].standard_language[0].piece"),
        ),
        (
            lambda r: r["studies"][0]["population"]["sex"].update(value=42),
            ("wrong_value_type", "studies[0].population.sex"),
        ),
        (
            lambda r: r["studies"][0]["efficacy"]["measurements"][0].update(value={"anything": 1}),
            ("wrong_value_type", "studies[0].efficacy.measurements[0]"),
        ),
        (
            lambda r: r["studies"][0]["arms"][0].update(value="Arm A"),
            ("wrong_value_type", "studies[0].arms[0]"),
        ),
        (lambda r: r["studies"][0]["sponsor"].update(value=None), ("wrong_value_type", "studies[0].sponsor")),
    ],
)
def test_a_field_or_a_value_not_of_its_type_is_named(valid, change, problem):
    assert broken(valid, change) == (problem,)


def test_efficacy_and_safety_agree_on_the_results_and_nothing_is_posted_without_them(valid):
    """The second study (NCT07654321) posts no results: shown as posted in efficacy alone, it disagrees with
    safety; posted words under a not_posted status are inconsistent; a measurement under it is posted without
    results."""
    assert valid["studies"][1]["efficacy"]["results"]["status"] == "not_posted"

    def efficacy_posted(record):
        record["studies"][1]["efficacy"]["results"].update(value="results posted", status="known")

    assert broken(valid, efficacy_posted) == (("results_differ", "studies[1].safety.results"),)

    def posted_words(record):
        for section in ("efficacy", "safety"):
            record["studies"][1][section]["results"]["value"] = "results posted"

    assert broken(valid, posted_words) == (("results_inconsistent", "studies[1].efficacy.results"),)

    def measured_without_results(record):
        measurement = copy.deepcopy(record["studies"][0]["efficacy"]["measurements"][0])
        measurement["link"] = OTHER
        record["studies"][1]["efficacy"]["measurements"] = [measurement]

    assert broken(valid, measured_without_results) == (
        ("posted_without_results", "studies[1].efficacy.measurements"),
    )

    def both_posted(record):
        for section in ("efficacy", "safety"):
            record["studies"][1][section]["results"].update(value="results posted", status="known")

    # changed alike in both, the record cannot show it: only re-deriving it from the study record can
    assert broken(valid, both_posted) == ()


def test_coverage_and_the_review_queue_name_the_records_studies(valid):
    assert broken(valid, lambda r: r["coverage"]["studies"].reverse()) == (
        ("study_mismatch", "coverage.studies"),
    )
    assert broken(valid, lambda r: r["review_queue"][0].update(nct="NCT00000000")) == (
        ("study_mismatch", "review_queue[0]"),
    )


@pytest.mark.parametrize(
    "kind, value, holds",
    [
        ("opaque", None, True),
        ("string", "x", True),
        ("string", 1, False),
        ("integer", 3, True),
        ("integer", True, False),
        ("integer", 3.0, False),
        ("boolean", False, True),
        ("boolean", 0, False),
        ("object", {}, True),
        ("object", [], False),
        ("list of string", ["a"], True),
        ("list of string", ["a", 1], False),
        ("list of string", ("a",), False),
        (f"object: {landscape.AS_HELD}", {"anything": 1}, True),
        (f"object: {landscape.AS_HELD}", "x", False),
        ("object: a, b", {"a": 1, "b": 2}, True),
        ("object: a, b", {"b": 2, "a": 1}, False),
        ("object: a, b", {"a": 1}, False),
        ("object: a, b", ["a", "b"], False),
        ("list of row: a, b", [{"a": 1, "b": 2}], True),
        ("list of row: a, b", [], True),
        ("list of row: a, b", [{"a": 1}], False),
        ("list of row: a, b", {"a": 1, "b": 2}, False),
        ("list of row: a, b", ({"a": 1, "b": 2},), False),
        ("list of row: a, b", {}, False),
        ("section", {}, False),
        ("section", [], False),
        ("value(string)", "x", False),
    ],
)
def test_a_type_holds_exactly_its_own_values(kind, value, holds):
    assert landscape.type_holds(kind, value) is holds


def test_one_values_problems_are_read_from_its_own_envelope(valid):
    sponsor = valid["studies"][0]["sponsor"]
    assert landscape.envelope_problems(sponsor, "studies[].sponsor", "s", LINK) == []
    absent = env(None, "not_stated", "protocolSection.eligibilityModule.maximumAge", note="not_reported")
    assert landscape.envelope_problems(absent, "studies[].population.maximum_age", "m", LINK) == []
    assert landscape.envelope_problems(
        {**absent, "status": "known"}, "studies[].population.maximum_age", "m", LINK
    ) == [("wrong_value_type", "m")]
    assert landscape.envelope_problems("Example Pharma", "studies[].sponsor", "s", LINK) == [
        ("malformed_value", "s")
    ]
    planned = {
        **valid["studies"][0]["efficacy"]["measurements"][0],
        "status": "proposed",
        "source": "",
        "rule": "",
    }
    assert landscape.envelope_problems(planned, "studies[].efficacy.measurements", "e", OTHER) == [
        ("status_not_allowed", "e"),
        ("no_source", "e"),
        ("wrong_link", "e"),
        ("posted_not_from_results", "e"),
    ]


def test_a_studys_results_are_read_only_where_the_walk_admits_them(valid):
    assert landscape.results_problems(valid["studies"][0], "studies[0]") == []
    assert landscape.results_problems(valid["studies"][1], "studies[1]") == []
    assert landscape.results_problems({}, "s") == []
    assert landscape.results_problems({"efficacy": {}, "safety": {}}, "s") == []
    assert landscape.results_problems({"efficacy": {"results": 1}, "safety": {}}, "s") == [
        ("results_differ", "s.safety.results")
    ]
    unknown = env("x", "unresolved", "hasResults", "ledger.results_state", "no_such_state")
    held = {"efficacy": {"results": unknown}, "safety": {"results": unknown}}
    assert landscape.results_problems(held, "s") == [("results_inconsistent", "s.efficacy.results")]


def test_nothing_is_posted_under_a_flag_without_a_results_section():
    """The registry flags results but the record holds no results section: every posted list that holds
    anything is named, in order; the same lists under posted results are not."""
    flagged = results_value("flag_without_results", LINK)
    lists = {"measurements": [1]}, {"groups": [1], "events": [1]}
    study = {"efficacy": {"results": flagged, **lists[0]}, "safety": {"results": flagged, **lists[1]}}
    assert landscape.results_problems(study, "s") == [
        ("posted_without_results", "s.efficacy.measurements"),
        ("posted_without_results", "s.safety.groups"),
        ("posted_without_results", "s.safety.events"),
    ]
    posted = results_value("posted", LINK)
    study = {"efficacy": {"results": posted, **lists[0]}, "safety": {"results": posted, **lists[1]}}
    assert landscape.results_problems(study, "s") == []


def test_results_that_differ_and_are_inconsistent_are_named_both_and_a_reordered_envelope_is_the_walks():
    posted_words = {**results_value("not_posted", LINK), "value": "results posted"}
    study = {"efficacy": {"results": posted_words}, "safety": {"results": results_value("not_posted", LINK)}}
    assert landscape.results_problems(study, "s") == [
        ("results_differ", "s.safety.results"),
        ("results_inconsistent", "s.efficacy.results"),
    ]
    reordered = dict(reversed(list(results_value("not_posted", LINK).items())))
    study = {"efficacy": {"results": reordered, "measurements": [1]}, "safety": {"results": reordered}}
    assert landscape.results_problems(study, "s") == []


def test_the_studies_named_elsewhere_are_the_records_own():
    assert landscape.study_mismatches({"studies": "x"}) == []
    # sections not of their type are the walk's to name: nothing is read from them here
    shapes = {
        "studies": [{"nct": "NCT1"}, []],
        "coverage": {"studies": {"NCT1": 1}},
        "review_queue": {"nct": "NCT2"},
    }
    assert landscape.study_mismatches(shapes) == []
    assert (
        landscape.study_mismatches({**shapes, "coverage": [1], "review_queue": [["NCT2"], {"nct": None}]})
        == []
    )
    record = {
        "studies": [{"nct": {"value": "NCT1"}}, "not a study"],
        "coverage": {"studies": [{"nct": "NCT1"}, {"nct": None}]},
        "review_queue": [{"nct": "NCT2"}, "not a row", {"nct": "NCT1"}],
    }
    assert landscape.study_mismatches(record) == [("study_mismatch", "review_queue[0]")]
    record["coverage"]["studies"].pop()
    assert landscape.study_mismatches(record) == [
        ("study_mismatch", "coverage.studies"),
        ("study_mismatch", "review_queue[0]"),
    ]
