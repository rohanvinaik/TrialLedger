"""The population reading: each study read once into a view, and everything computed across the views.

`read_population` is the one producer the outputs consume: `design.sheets` lays the reading out as
design.xlsx and `symbolic.symbolic_output` renders it as the JSON of `trialledger resolve`. Each study's
eligibility is itemized and typed and its coverage read (content, sectioning, what the record says of its own
coverage in each section), its coordinates resolved, its experimental drugs classed (RxClass, or a
target its own record states) and given their axes (RxNorm identity by the own name, ATC and structure classes
with their standing and warrants, the own entry's targets aligned to ATC), every intervention entry's modality
and cell extractions read with their warrants, its intervention MeSH scoped, its outcomes and results typed
and its frozen expectations observed; across the views, the classes known to the population, each view's
review flags, the near-miss pairs as written, the aligned pairs (ATC) and the structure relations.
"""

from __future__ import annotations

from typing import Any

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.banks import endpoint_classes, stated_targets, time_points, type_criterion
from TrialLedger.coherence import COORDINATES, resolve
from TrialLedger.criteria import eligibility_coverage, itemize
from TrialLedger.expectations import FROZEN, autoimmune_exclusion
from TrialLedger.modality import entry_properties
from TrialLedger.nearmiss import near_misses
from TrialLedger.profile import element_key
from TrialLedger.review import flags_for


def read_population(studies: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    """Every study read once, with the RxClass `answers`, and what is computed across them: the views, the
    classes classified anywhere in the population, each view's review flags (in the order of the views), each
    view as the near-miss decision reads it, and the near-miss pairs."""
    views = [study_view(study, answers) for study in studies]
    known_classes = sorted({c for v in views for _, s, e, _ in v["drugs"] if s == "classified" for c in e})
    near_miss_trials = [near_miss_input(view) for view in views]
    aligned = [
        aligned_near_miss_input(view, trial) for view, trial in zip(views, near_miss_trials, strict=True)
    ]
    basis = {trial[0]: b for trial, b in aligned}
    aligned_pairs = [(*pair, basis[pair[0]], basis[pair[1]]) for pair in near_misses([t for t, _ in aligned])]
    return {
        "views": views,
        "known_classes": known_classes,
        "flags": [review_flags(view, known_classes) for view in views],
        "near_miss_trials": near_miss_trials,
        "pairs": near_misses(near_miss_trials),
        "aligned_pairs": aligned_pairs,
        "structure_relations": structure_relations(views),
    }


def effective_section(section: str, params: tuple) -> str:
    """The section an atom's claim belongs to, once its own wording is read (pure — pinned).

    A permission ("prior therapy is permissible") is "permitted", never a requirement, whatever its section; a
    mention its text negates ("non-pregnant", "unless using contraception") belongs to the other section
    (inclusion to exclusion, exclusion to inclusion); otherwise the criterion's own section.
    """
    held = dict(params)
    if held.get("modality") == "permitted":
        return "permitted"
    if held.get("text_polarity") == "excluded":
        return {"inclusion": "exclusion", "exclusion": "inclusion"}.get(section, section)
    return section


def study_view(study: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    """One study as the design layers read it: eligibility coverage, criteria with atoms, evidence,
    coordinates, elements, classes."""
    protocol = study.get("protocolSection", {})
    nct = protocol.get("identificationModule", {}).get("nctId", "")
    text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria") or ""
    text = text if isinstance(text, str) else ""
    code, pieces = itemize(text)
    content, sectioning, coverage, markers = eligibility_coverage(text, pieces)
    readable = [(section, text[start:end]) for _kind, section, start, end in pieces]
    criteria, evidence, elements = [], [], []
    for index, (kind, section, start, end) in enumerate(pieces):
        if kind != "criterion":
            continue
        atoms = type_criterion(text[start:end])
        criteria.append((index, section, text[start:end], atoms))
        for _bank, concept, values, params, _s, _e in atoms:
            effective = effective_section(section, params)
            evidence.append((effective, concept, values, dict(params).get("scope", ""), f"criterion {index}"))
            elements.append(element_key(effective, concept, values, params))
    names = rx.drug_names(study)
    arms_module = protocol.get("armsInterventionsModule", {})
    descriptions = {
        item.get("name"): " ".join(str(item.get(k) or "") for k in ("name", "description"))
        for item in arms_module.get("interventions", []) or []
        if isinstance(item, dict)
    }
    # An arm's description names its whole combination ("SCT-I10A plus docetaxel"), so an agent word in it
    # cannot be attributed to one drug: only the intervention's own entry is read.
    drugs = []
    for drug in rx.experimental_drugs(study):
        state, found, resolved_by = rx.drug_class(answers, names[drug])
        epc = sorted({c[1] for c in found if c[2] == "has_epc"})
        if state != "classified":
            stated = stated_targets(descriptions.get(drug, ""))
            if stated:
                state, epc, resolved_by = "stated_by_record", [f"stated: {s}" for s in stated], "description"
        drugs.append((drug, state, epc, resolved_by))
    digest = warrants.study_digest(study)
    entries = [
        (index, item)
        for index, item in enumerate(arms_module.get("interventions", []) or [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]
    entry_names = {
        item["name"]: [item["name"], *[n for n in item.get("otherNames") or [] if isinstance(n, str)]]
        for _, item in entries
    }
    properties = []
    for index, item in entries:
        base = f"protocolSection.armsInterventionsModule.interventions[{index}]"
        texts = [(f"{base}.name", item["name"], True)]
        texts += [
            (f"{base}.otherNames[{i}]", n, True)
            for i, n in enumerate(item.get("otherNames") or [])
            if isinstance(n, str)
        ]
        if isinstance(item.get("description"), str):
            texts.append((f"{base}.description", item["description"], False))
        properties += [
            (*e, warrants.digest("extraction", digest, *e)) for e in entry_properties(item["name"], texts)
        ]
    meshes = study.get("derivedSection", {}).get("interventionBrowseModule", {}).get("meshes")
    outcomes = []
    for kind, key in (
        ("primary", "primaryOutcomes"),
        ("secondary", "secondaryOutcomes"),
        ("other", "otherOutcomes"),
    ):
        for outcome in protocol.get("outcomesModule", {}).get(key, []) or []:
            measure, frame = str(outcome.get("measure") or ""), str(outcome.get("timeFrame") or "")
            classes = endpoint_classes(measure)
            outcomes.append((kind, measure, frame, classes, time_points(frame)))
            if kind == "primary":
                elements.extend(f"primary:endpoint:{c}" for c in classes)
    results = []
    for measure in (study.get("resultsSection", {}).get("outcomeMeasuresModule", {}) or {}).get(
        "outcomeMeasures", []
    ) or []:
        groups = {g.get("id"): g.get("title") for g in measure.get("groups", []) or [] if isinstance(g, dict)}
        title = str(measure.get("title") or "")
        for klass in measure.get("classes", []) or []:
            for category in klass.get("categories", []) or []:
                for m in category.get("measurements", []) or []:
                    results.append(
                        (
                            title,
                            endpoint_classes(title),
                            str(measure.get("type") or ""),
                            str(measure.get("unitOfMeasure") or ""),
                            str(measure.get("paramType") or ""),
                            str(measure.get("timeFrame") or ""),
                            str(groups.get(m.get("groupId"), "")),
                            str(klass.get("title") or category.get("title") or ""),
                            str(m.get("value") or ""),
                            str(m.get("spread") or ""),
                            str(m.get("lowerLimit") or ""),
                            str(m.get("upperLimit") or ""),
                        )
                    )
    return {
        "nct": nct,
        "digest": digest,
        "sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        "start_year": str(protocol.get("statusModule", {}).get("startDateStruct", {}).get("date", ""))[:4],
        "status": protocol.get("statusModule", {}).get("overallStatus", ""),
        "itemize": code,
        "coverage": {
            "content": content,
            "sectioning": sectioning,
            "evidence": coverage,
            "markers": [
                (kind, scope, piece, start, end, text[start:end])
                for kind, scope, piece, start, end in markers
            ],
        },
        "criteria": criteria,
        "coordinates": resolve(evidence),
        "elements": elements,
        "drugs": drugs,
        "drug_axes": [
            drug_axes_view(drug, names[drug], descriptions.get(drug, ""), answers) for drug, *_ in drugs
        ],
        "properties": properties,
        "intervention_mesh": rx.mesh_scope(meshes, entry_names),
        "outcomes": outcomes,
        "results": results,
        "observations": {
            expectation.id: _observe(expectation, readable, code, coverage, drugs) for expectation in FROZEN
        },
    }


def _observe(expectation, readable, code, coverage, drugs) -> tuple[str, str, list[str], list[str]]:
    """One trial's observation of a frozen expectation: (status, reason, cited texts, qualifiers); `coverage`
    is the trial's coverage evidence per section, which tells an abbreviated record's silence from others'."""
    classes = {c for _, state, epc, _ in drugs if state in ("classified", "stated_by_record") for c in epc}
    if not classes & set(expectation.applies_to):
        return "not_applicable", "no experimental drug of the expectation's classes", [], []
    if code == "empty":
        return "unresolved", "no eligibility text", [], []
    status, reason, indices, qualifiers = autoimmune_exclusion(readable, coverage)
    return status, reason, [readable[i][1] for i in indices], qualifiers


def near_miss_input(view: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, str], str, str]:
    """A study view as the near-miss decision reads it: its representation (its setting when the record and
    the approved relations leave one value; its experimental drugs' classes when every drug's class is known,
    from RxClass or stated by its own record), its design predicates (the ECOG values and histologies its
    inclusion criteria state, the checkpoint expectation when present or admitted), its lead sponsor and its
    start year. Anything not known is "". Known means read from the record or derived from it by an approved
    rule; a proposed relation's narrowing is not known (the founder, 2026-10-31). Eligibility coverage needs
    no handling here: every predicate is a stated value or "", and "" never matches, so a silent record
    (empty, abbreviated or unspecified) is never read as differing."""
    setting = view["coordinates"]["setting"]["domain"]
    drugs = view["drugs"]
    classified = drugs and all(state in ("classified", "stated_by_record") for _, state, _, _ in drugs)
    classes = " + ".join(sorted({c for _, _, epc, _ in drugs for c in epc})) if classified else ""
    ecog, histologies = "", set()
    for _index, section, _text, atoms in view["criteria"]:
        for _bank, concept, values, _params, _s, _e in atoms:
            if section == "inclusion" and concept == "ecog_ps" and not ecog:
                ecog = "|".join(values)
            if section == "inclusion" and concept == "histology":
                histologies |= set(values)
    status = next(iter(view["observations"].values()), ("", "", [], []))[0]
    return (
        view["nct"],
        {"setting": setting[0] if len(setting) == 1 else "", "classes": classes},
        {
            "ecog_ps": ecog,
            "histology": "|".join(sorted(histologies)),
            "autoimmune_exclusion": status if status in ("present", "explicitly_negated") else "",
        },
        view["sponsor"],
        view["start_year"],
    )


def drug_axes_view(drug: str, aliases: list[str], entry: str, answers: dict[str, Any]) -> dict:
    """One experimental drug's axes, apart from its EPC and MoA classes: its RxNorm identity decided by its
    own name (with the reason when it is not resolved), its ATC and structure classes with their standing and
    warrants, the targets its own entry (`entry`: its name and description) states of it and their crosswalk
    alignment, and its ATC classes for the aligned near-miss representation with their basis."""
    code, reason, identities, assertions = rx.drug_axes(aliases, answers)
    targets = rx.own_targets(entry)
    alignment = rx.target_alignment(targets)
    known = [a[2] for a in assertions if a[1] == "ATC" and a[5] == "known"]
    return {
        "drug": drug,
        "identity": code,
        "reason": reason,
        "identities": identities,
        "assertions": assertions,
        "targets": targets,
        "alignment": alignment,
        "atc": rx.drug_atc(known, targets, alignment),
    }


def aligned_near_miss_input(view: dict[str, Any], trial: tuple) -> tuple[tuple, str]:
    """A study view as the aligned near-miss reading reads it, and the weakest basis it rests on.

    `trial` is the view's near_miss_input, already computed by read_population; its setting, predicates,
    sponsor and year are kept, and the drug representation is the experimental drugs' ATC classes, known when
    every drug has them: from RxClass for the drug's own resolved concept (`rxclass`), or entailed by the
    crosswalk for a target its own entry states (`crosswalk`, the weaker). A pair through this reading is
    alignment, labelled with each trial's basis, never a match as written."""
    nct, representation, predicates, sponsor, year = trial
    atc = [axes["atc"] for axes in view["drug_axes"]]
    known = bool(atc) and all(basis for basis, _ in atc)
    classes = " + ".join(sorted({c for _, held in atc for c in held})) if known else ""
    basis = ("crosswalk" if any(b == "crosswalk" for b, _ in atc) else "rxclass") if known else ""
    return (nct, {"setting": representation["setting"], "atc": classes}, predicates, sponsor, year), basis


def structure_relations(views: list[dict[str, Any]]) -> list[tuple[str, str, str, str, str, str, str]]:
    """Every shares_structure_class relation between two distinct drugs of the population, each drug keyed by
    the RxNorm concept (rxcui) its known structure classes are asserted of, never by a name; never homology.
    Returns (rxcui a, name a, rxcui b, name b, taxonomy, "<class id> <class name>", release), sorted."""
    held: dict[str, set[tuple[str, str, str, str]]] = {}
    names: dict[str, str] = {}
    for view in views:
        for axes in view["drug_axes"]:
            for _alias, axis, class_id, name, _kind, standing, rxcui, subject, release, *_ in axes[
                "assertions"
            ]:
                if axis != "ATC" and standing == "known":
                    held.setdefault(rxcui, set()).add((axis, class_id, name, release))
                    names.setdefault(rxcui, subject)
    drugs = sorted(held)
    return [
        (a, names[a], b, names[b], *relation[2:])
        for i, a in enumerate(drugs)
        for b in drugs[i + 1 :]
        for relation in rx.shares_structure_class((a, sorted(held[a])), (b, sorted(held[b])))
    ]


def review_flags(view: dict[str, Any], known_classes: list[str]) -> list[tuple]:
    """The review flags of one study view: what the symbolic reading leaves for an expert or a model, the
    record's own abbreviation markers among them."""
    return flags_for(
        [(drug, state) for drug, state, _, _ in view["drugs"]],
        {
            name: (list(row["domain"]), row["state"], [c[2] for c in row["causes"]])
            for name, row in view["coordinates"].items()
        },
        {name: list(values) for name, values in COORDINATES.items()},
        {eid: (s, r, c) for eid, (s, r, c, _) in view["observations"].items()},
        known_classes,
        [
            (scope, f"piece {piece}, characters {start}-{end}: {said}")
            for kind, scope, piece, start, end, said in view["coverage"]["markers"]
            if kind == "abbreviation_stated"
        ],
    )


def drug_aliases(studies: list[dict[str, Any]]) -> list[str]:
    """Every drug, biological or genetic intervention's name and other names of the studies, for RxClass's
    EPC and MoA classes (the Classes sheet shows every answer)."""
    return [alias for study in studies for aliases in rx.drug_names(study).values() for alias in aliases]


def axes_aliases(studies: list[dict[str, Any]]) -> list[str]:
    """The names and other names of every experimental arm's drug, biological or genetic intervention: the
    only names whose axes the reading reads, so the only ones RxNav is asked about."""
    out = []
    for study in studies:
        names = rx.drug_names(study)
        out += [alias for drug in rx.experimental_drugs(study) for alias in names[drug]]
    return out
