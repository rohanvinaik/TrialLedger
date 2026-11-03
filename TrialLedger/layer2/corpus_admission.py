"""Project corpus premises into explicit consumer admission without changing source records.

Low-level profile and near-miss operators keep their typed-input preconditions. This boundary admits only
known/resolved support, preserves pending feature declarations, and keeps each consumer's scope separate.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from TrialLedger.layer2 import admission, profile

SCALARS = frozenset({"classes", "setting_domain", "typed", "eligibility_content", "coverage"})
MAPPINGS = frozenset({"elements", "representation", "predicates"})
ASSOCIATION_FIELDS = frozenset({"elements", "classes", "typed", "eligibility_content", "coverage"})
FREQUENCY_FIELDS = (
    "stratum",
    "element",
    "stating",
    "absence_established",
    "unresolved_empty",
    "unresolved_untyped",
    "unresolved_abbreviated",
    "unresolved_unspecified",
    "unresolved",
    "trials",
    "statement_rate",
    "lower",
    "upper",
    "surprisal_bits",
    "sponsors",
    "tier",
    "estimand",
)
MAX_ITEMS = 1000
MAX_FEATURES = 10000


def _standing(raw: object, label: str) -> dict:
    """An explicit null is malformed; omission is handled separately through inheritance."""
    if raw is None:
        raise ValueError("null_standing:" + label)
    return admission.read_standing(raw, label)


def _support(item: dict) -> tuple[dict, dict[tuple[str, ...], dict]]:
    label = "trial:" + item["id"]
    inherited = (
        _standing(item["standing"], label) if "standing" in item else admission.read_standing(None, label)
    )
    overrides = item.get("feature_standings", {})
    if not isinstance(overrides, dict) or set(overrides) - SCALARS - MAPPINGS:
        raise ValueError("invalid_feature_standings:" + label)
    fields = {}
    for key in SCALARS:
        if key in overrides and key not in item:
            raise ValueError("missing_override_target:" + label + ":" + key)
        fields[(key,)] = _standing(overrides[key], label + ":" + key) if key in overrides else inherited
    for key in MAPPINGS:
        values = item.get(key, [] if key == "elements" else {})
        targets = set(values)
        given = overrides.get(key, {})
        if not isinstance(given, dict) or set(given) - targets:
            raise ValueError("invalid_feature_targets:" + label + ":" + key)
        if len(given) > MAX_ITEMS or len(targets) > MAX_ITEMS:
            raise ValueError("resource_bound:" + label + ":" + key)
        for target in sorted(targets):
            fields[(key, target)] = (
                _standing(given[target], label + ":" + key + ":" + target) if target in given else inherited
            )
    return inherited, fields


def _value(item: dict, path: tuple[str, ...]) -> Any:
    if len(path) == 1:
        return deepcopy(item.get(path[0]))
    if path[0] == "elements":
        return path[1]
    return deepcopy(item[path[0]][path[1]])


def _profile(item: dict, fields: dict[tuple[str, ...], dict]) -> profile.Trial:
    def accepted(path: tuple[str, ...]) -> bool:
        return admission.code(fields[path]) == "accepted"

    elements = [element for element in item["elements"] if accepted(("elements", element))]
    return (
        item["id"],
        item["sponsor"],
        item["stratum"],
        bool(item.get("typed", False) and accepted(("typed",))),
        elements,
        list(item.get("classes", [])) if accepted(("classes",)) else [],
        bool(item.get("class_unresolved", True) or not accepted(("classes",))),
        item.get("eligibility_content", "present") if accepted(("eligibility_content",)) else "present",
        tuple(item.get("coverage", {}).items()) if accepted(("coverage",)) else (),
    )


def _frequency(items: list[dict], projected: list[profile.Trial], standings: list[dict]) -> list[dict]:
    """Extend existing statement counts with pending declarations and zero-admitted rows."""
    rows: dict[tuple[str, str], dict[str, Any]] = {
        (row[0], row[1]): dict(zip(FREQUENCY_FIELDS, row, strict=True))
        for row in profile.frequency_rows(projected)
    }
    universe = sorted({(item["stratum"], element) for item in items for element in item["elements"]})
    result = []
    for stratum, element in universe:
        cohort = [
            (item, trial, fields)
            for item, trial, fields in zip(items, projected, standings, strict=True)
            if item["stratum"] == stratum
        ]
        n = len(cohort)
        eligibility = element.split(":", 1)[0] in profile.ELIGIBILITY_SECTIONS
        row = rows.get((stratum, element))
        if row is None:
            row = dict(
                zip(
                    FREQUENCY_FIELDS,
                    (
                        stratum,
                        element,
                        0,
                        0 if eligibility else None,
                        *([0] * 5 if eligibility else [None] * 5),
                        n,
                        0.0,
                        0.0 if eligibility else None,
                        1.0 if eligibility else None,
                        None,
                        0,
                        "unresolved" if eligibility else "",
                        "statement rate and full-criteria interval"
                        if eligibility
                        else "statement rate only (not an eligibility element)",
                    ),
                    strict=True,
                )
            )
        pending = 0
        unresolved_pending = 0
        silence = {"empty": 0, "no_rule_match": 0, "abbreviated": 0, "unspecified": 0}
        for item, trial, fields in cohort:
            declared = element in item["elements"]
            if declared and admission.code(fields[("elements", element)]) != "accepted":
                pending += 1
            if element in trial[4] or not eligibility:
                continue
            if (declared and admission.code(fields[("elements", element)]) != "accepted") or any(
                admission.code(fields[(key,)]) != "accepted"
                for key in ("typed", "eligibility_content", "coverage")
            ):
                unresolved_pending += 1
            else:
                typed = any(e.split(":", 1)[0] in profile.ELIGIBILITY_SECTIONS for e in trial[4])
                silence[profile.element_silence(element, trial[7], typed, trial[8])] += 1
        stating = cast(int, row["stating"])
        row.update(
            pending_stating=pending,
            pending_statement_lower=round(stating / n, 4),
            pending_statement_upper=round((stating + pending) / n, 4),
            unresolved_pending=unresolved_pending if eligibility else None,
        )
        if eligibility:
            row.update(
                unresolved_empty=silence["empty"],
                unresolved_untyped=silence["no_rule_match"],
                unresolved_abbreviated=silence["abbreviated"],
                unresolved_unspecified=silence["unspecified"],
                unresolved=n - stating,
            )
        result.append(row)
    return sorted(result, key=lambda row: (row["stratum"], -row["stating"], row["element"]))


def _occupancy(cells: list[tuple[str, str]], memberships: list[dict]) -> list[dict]:
    """Keep independent known class and setting constraints while widening only a pending dimension."""
    rows = []
    for setting, klass in cells:
        occupants = possible = 0
        for item in memberships:
            class_matches = not item["classes_known"] or klass in item["classes"]
            if setting not in item["setting_domain"] or not class_matches:
                continue
            definite = (
                item["setting_known"]
                and item["setting_domain"] == (setting,)
                and item["classes_known"]
                and klass in item["classes"]
            )
            if definite:
                occupants += 1
            else:
                possible += 1
        rows.append(
            {
                "setting": setting,
                "class": klass,
                "occupants": occupants,
                "possible": possible,
                "state": "occupied" if occupants else "unknown" if possible else "empty",
            }
        )
    return rows


def prepare(trials: list[dict], cells: list[tuple[str, str]]) -> dict:
    """Prepare detached per-consumer inputs from service-validated trial values and explicit standings."""
    if not isinstance(trials, list) or len(trials) > MAX_ITEMS or len(cells) > MAX_ITEMS:
        raise ValueError("resource_bound:corpus_admission")
    items = deepcopy(trials)
    ledgers = []
    pending = []
    projected = []
    all_fields = []
    pairs = []
    occupancy = []
    memberships = []
    blocked = {}
    pair_blocked = []
    feature_count = 0
    requested_settings = tuple(sorted({cell[0] for cell in cells}))
    for item in items:
        inherited, fields = _support(item)
        feature_count += len(fields)
        if feature_count > MAX_FEATURES:
            raise ValueError("resource_bound:corpus_features")
        all_fields.append(fields)
        records = []
        for path, standing in sorted(fields.items()):
            record = {
                "trial": item["id"],
                "stratum": item["stratum"],
                "feature": list(path),
                "value": _value(item, path),
                "standing": deepcopy(standing),
                "code": admission.code(standing),
                "basis": deepcopy(item["basis"]),
            }
            records.append(record)
            if record["code"] != "accepted":
                pending.append(deepcopy(record))
        ledgers.append({"id": item["id"], "standing": deepcopy(inherited), "features": records})
        trial = _profile(item, fields)
        projected.append(trial)
        relevant = [
            record
            for record in records
            if record["feature"][0] in ASSOCIATION_FIELDS and record["code"] != "accepted"
        ]
        if item.get("class_unresolved", True):
            relevant.append(
                {
                    "trial": item["id"],
                    "stratum": item["stratum"],
                    "feature": ["class_unresolved"],
                    "value": True,
                    "classes": deepcopy(item.get("classes", [])),
                    "standing": deepcopy(fields[("classes",)]),
                    "code": "class_membership_unresolved",
                    "basis": deepcopy(item["basis"]),
                }
            )
        if relevant:
            blocked.setdefault(item["stratum"], []).extend(deepcopy(relevant))
        near = [
            record
            for record in records
            if record["feature"][0] in ("representation", "predicates") and record["code"] != "accepted"
        ]
        if near:
            pair_blocked.append({"trial": item["id"], "code": "pending_support", "features": deepcopy(near)})
        else:
            pairs.append(
                (
                    item["id"],
                    deepcopy(item.get("representation", {})),
                    deepcopy(item.get("predicates", {})),
                    item["sponsor"],
                    item.get("start_year", ""),
                )
            )
        setting_known = admission.code(fields[("setting_domain",)]) == "accepted"
        classes_known = admission.code(fields[("classes",)]) == "accepted"
        domain = tuple(item.get("setting_domain", [])) if setting_known else requested_settings
        if cells and setting_known and not domain:
            raise ValueError("occupancy_requires_nonempty_setting_domains")
        classes_known = classes_known and not item.get("class_unresolved", True)
        classes = tuple(item.get("classes", [])) if classes_known else ()
        memberships.append(
            {
                "id": item["id"],
                "setting_domain": domain,
                "setting_known": setting_known,
                "classes": classes,
                "classes_known": classes_known,
            }
        )
        # A legacy tuple cannot express setting_known. Retain it only as a trace, never as the safe output.
        occupancy.append((item["id"], domain, classes))
    abstentions = [
        {
            "stratum": stratum,
            "code": "pending_support",
            "trials": sorted({row["trial"] for row in records}),
            "features": records,
        }
        for stratum, records in sorted(blocked.items())
    ]
    return {
        "trials": projected,
        "association_trials": [trial for trial in projected if trial[2] not in blocked],
        "pairs": pairs,
        "occupancy_trials": occupancy,
        "occupancy_membership": memberships,
        "occupancy": _occupancy(cells, memberships),
        "admission": ledgers,
        "pending": pending,
        "association_abstentions": abstentions,
        "near_miss_abstentions": pair_blocked,
        "frequency": _frequency(items, projected, all_fields),
    }


def frequency(trials: list[dict]) -> list[dict]:
    """Return admitted statement counts and explicit pending bounds without inventing absent elements."""
    return prepare(trials, [])["frequency"]


def expectations(item: dict, rows: list[tuple[str, str]]) -> dict:
    """Admit observation rows without changing their source observation states or joining corpus trials."""
    inherited = (
        _standing(item["standing"], "expectation")
        if "standing" in item
        else admission.read_standing(None, "expectation")
    )
    overrides = item.get("observation_standings")
    if "observation_standings" in item and (not isinstance(overrides, list) or len(overrides) != len(rows)):
        raise ValueError("invalid_observation_standings")
    if len(rows) > MAX_ITEMS:
        raise ValueError("resource_bound:expectation_observations")
    admitted = []
    ledger = []
    pending = []
    for index, row in enumerate(rows):
        standing = _standing(overrides[index], f"observation:{index}") if overrides is not None else inherited
        record = {
            "index": index,
            "observation": deepcopy(row),
            "standing": deepcopy(standing),
            "code": admission.code(standing),
            "basis": deepcopy(item["basis"]),
        }
        ledger.append(record)
        if record["code"] == "accepted":
            admitted.append(deepcopy(row))
        else:
            pending.append(deepcopy(record))
    return {
        "observations": admitted,
        "admitted_count": len(admitted),
        "pending": pending,
        "admission": ledger,
    }
