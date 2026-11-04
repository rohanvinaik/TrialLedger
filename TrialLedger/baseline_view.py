"""Lossless, source-addressed baseline tables for a separate clinical review export.

`baseline_tables` groups existing measurements by source class/category. It performs
no aggregation, population binding, unit conversion or clinical interpretation.
Consumers display `row['category'].get('title')` and each value's raw
`measurement.get('value')`. Every value retains its local group resolution and all
matching denominator scopes; unresolved groups must not be placed in guessed columns.
The ordinary long-format source workbook remains independent of this view.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class BaselineViewError(ValueError):
    """A malformed source container cannot be represented as an empty table."""


def group_code(group: object, identities: list[object]) -> str:
    """Resolve only an exact local group identifier, never its title (pure — pinned).

    post: __return__ in ('missing_group', 'invalid_group', 'unknown_group', 'ambiguous_group', 'unique')
    """
    if group is None or group == "":
        return "missing_group"
    if not isinstance(group, str):
        return "invalid_group"
    count = identities.count(group)
    if count == 0:
        return "unknown_group"
    if count > 1:
        return "ambiguous_group"
    return "unique"


def _items(parent: dict[str, Any], name: str, source: str) -> list[dict[str, Any]]:
    """Read a source list without treating malformed content as no observations."""
    if name not in parent:
        return []
    value = parent[name]
    if not isinstance(value, list):
        raise BaselineViewError(f"malformed_collection:{source}/{name}")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise BaselineViewError(f"malformed_item:{source}/{name}/{index}")
    return value


def _held(parent: dict[str, Any], name: str, source: str) -> dict[str, Any]:
    """Missing, null, zero and false remain distinct copied field states."""
    return {"present": name in parent, "value": deepcopy(parent.get(name)), "source": f"{source}/{name}"}


def _metadata(parent: dict[str, Any], collections: set[str]) -> dict[str, Any]:
    return deepcopy({key: value for key, value in parent.items() if key not in collections})


def _denominators(scopes: list[tuple[str, dict[str, Any], str]], group: object) -> list[dict[str, Any]]:
    """Copy every matching count, with its original scope and denominator metadata."""
    result = []
    if group_code(group, [group]) != "unique":
        return result
    for scope, parent, source in scopes:
        for d, denominator in enumerate(_items(parent, "denominators", source)):
            address = f"{source}/denominators/{d}"
            for c, count in enumerate(_items(denominator, "counts", address)):
                if count.get("group") == group:
                    result.append(
                        {
                            "scope": scope,
                            "source": f"{address}/counts/{c}",
                            "units": deepcopy(denominator.get("units")),
                            "value": deepcopy(count.get("value")),
                            "count": deepcopy(count),
                            "definition": _metadata(denominator, {"counts"}),
                        }
                    )
    return result


def _groups(
    baseline: dict[str, Any], measure: dict[str, Any], module_source: str, source: str
) -> list[dict[str, Any]]:
    result = []
    scopes = [("measure", measure, source), ("module", baseline, module_source)]
    for index, group in enumerate(_items(baseline, "groups", module_source)):
        identity = group.get("id")
        result.append(
            {
                "id": deepcopy(identity),
                "title": deepcopy(group.get("title")),
                "source": f"{module_source}/groups/{index}",
                "definition": deepcopy(group),
                "denominators": _denominators(scopes, identity),
            }
        )
    return result


def _measurement(
    measurement: dict[str, Any],
    source: str,
    measure: dict[str, Any],
    measure_source: str,
    groups: list[dict[str, Any]],
    scopes: list[tuple[str, dict[str, Any], str]],
) -> dict[str, Any]:
    group = measurement.get("group")
    return {
        "source": source,
        "group": deepcopy(group),
        "group_code": group_code(group, [item["id"] for item in groups]),
        "group_sources": [item["source"] for item in groups if item["id"] == group],
        "measurement": deepcopy(measurement),
        "parameter": _held(measure, "param_type", measure_source),
        "unit": _held(measure, "unit", measure_source),
        "dispersion": _held(measure, "dispersion_type", measure_source),
        "denominators": _denominators(scopes, group),
    }


def _table_rows(
    baseline: dict[str, Any],
    measure: dict[str, Any],
    module_source: str,
    source: str,
    groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    classes = _items(measure, "classes", source)
    for k, klass in enumerate(classes or [{}]):
        class_source = f"{source}/classes/{k}" if classes else source
        categories = _items(klass, "categories", class_source)
        for c, category in enumerate(categories or [{}]):
            category_source = f"{class_source}/categories/{c}" if categories else class_source
            scopes = [
                ("class", klass, class_source),
                ("measure", measure, source),
                ("module", baseline, module_source),
            ]
            measurements = _items(category, "measurements", category_source)
            rows.append(
                {
                    "source": category_source,
                    "class": _metadata(klass, {"categories"}),
                    "category": _metadata(category, {"measurements"}),
                    "classes": _held(measure, "classes", source)
                    if not classes
                    else {"present": True, "source": f"{source}/classes"},
                    "categories": _held(klass, "categories", class_source)
                    if not categories
                    else {"present": True, "source": f"{class_source}/categories"},
                    "measurements": _held(category, "measurements", category_source)
                    if not measurements
                    else {"present": True, "source": f"{category_source}/measurements"},
                    "values": [
                        _measurement(
                            value, f"{category_source}/measurements/{m}", measure, source, groups, scopes
                        )
                        for m, value in enumerate(measurements)
                    ],
                }
            )
    return rows


def _table(
    trial: object, baseline: dict[str, Any], measure: dict[str, Any], module_source: str, source: str
) -> dict[str, Any]:
    groups = _groups(baseline, measure, module_source, source)
    return {
        "id": f"{trial}:baseline:{source.rsplit('/', 1)[-1]}",
        "trial": deepcopy(trial),
        "title": deepcopy(measure.get("title")),
        "source": source,
        "population": {
            "measure": _held(measure, "population", source),
            "module": _held(baseline, "population", module_source),
        },
        "measure": _metadata(measure, {"classes"}),
        "module": _metadata(baseline, {"groups", "measures"}),
        "groups": groups,
        "rows": _table_rows(baseline, measure, module_source, source, groups),
    }


def baseline_tables(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Copy source baseline tables without mutating the record or selecting an effective population.

    A module without listed measures yields a source-state table with no values. It
    does not assert zero observations, no baseline population or unposted results.
    """
    if not isinstance(record, dict):
        raise BaselineViewError("not_an_object:record")
    if "studies" not in record:
        raise BaselineViewError("missing_collection:/studies")
    tables = []
    for s, study in enumerate(_items(record, "studies", "")):
        module_source = f"/studies/{s}/baseline"
        baseline = study.get("baseline")
        if not isinstance(baseline, dict):
            raise BaselineViewError(f"malformed_baseline:{module_source}")
        measures = _items(baseline, "measures", module_source)
        for m, measure in enumerate(measures):
            tables.append(
                _table(study.get("nct"), baseline, measure, module_source, f"{module_source}/measures/{m}")
            )
        if not measures:
            table = _table(study.get("nct"), baseline, {}, module_source, module_source)
            table["availability"] = _held(baseline, "measures", module_source)
            table["rows"] = []
            tables.append(table)
    return tables
