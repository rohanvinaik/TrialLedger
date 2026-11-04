"""Operational NIH acquisition budgets, separate from clinical evidence and local replay.

Only registry network work is budgeted. Published source values, clinical thresholds and
already-retained legacy reports are not limited by these operational defaults.
"""

from __future__ import annotations

import re
from typing import Literal

DEFAULT_MAX_STUDIES = 1000
DEFAULT_MAX_REGISTRY_REQUESTS = 100
POLICY_FIELDS = ("max_studies", "max_registry_requests")
PolicyCode = Literal[
    "ok", "not_an_object", "unknown_field", "invalid_max_studies", "invalid_max_registry_requests"
]
ExpansionCode = Literal["within_budget", "study_expansion", "request_expansion", "invalid_cost"]
PlanKind = Literal["ids", "studies", "json_csv", "run"]


def policy_problem(value: object) -> PolicyCode:
    """Validate an explicitly supplied policy; partial objects use the documented defaults.

    Booleans are never integer budgets. Unknown fields are never silently ignored.
    """
    if not isinstance(value, dict):
        return "not_an_object"
    if any(key not in POLICY_FIELDS for key in value):
        return "unknown_field"
    for key in POLICY_FIELDS:
        if key in value and (type(value[key]) is not int or value[key] <= 0):
            return "invalid_max_studies" if key == "max_studies" else "invalid_max_registry_requests"
    return "ok"


def registry_plan_requests(
    studies: int, kind: PlanKind, page_size: int = 100, id_page_size: int = 1000
) -> int:
    """Successful registry exchanges for the complete declared plan, including both snapshots.

    First JSON/CSV pages are fetched even for an empty match; run study batches are not.
    Extra token pages and retries are additionally checked against actual request counts.
    """
    if (
        type(studies) is not int
        or studies < 0
        or type(page_size) is not int
        or page_size <= 0
        or type(id_page_size) is not int
        or id_page_size <= 0
    ):
        raise ValueError("invalid_acquisition_plan")
    pages = max(1, (studies + page_size - 1) // page_size)
    ids = max(1, (studies + id_page_size - 1) // id_page_size)
    if kind == "ids":
        return 2 + ids
    if kind == "studies":
        return 3 + pages
    if kind == "json_csv":
        return 3 + 2 * pages
    if kind == "run":
        return 2 + ids + (studies + page_size - 1) // page_size
    raise ValueError("invalid_acquisition_plan")


def expected_id_count(query: dict[str, str]) -> int | None:
    """An explicit ID filter bounds the intended scope; tokens are not clinical identities.

    Keep the registry's own identity/alias/malformed-ID accounting independent. Duplicate
    request tokens cannot authorize an unintended larger response.
    """
    if "filter.ids" not in query:
        return None
    return len({part.upper() for part in re.split(r"[,|\s]+", query["filter.ids"]) if part})


def effective_policy(
    value: object = None, *, expected_studies: int | None = None, expected_requests: int | None = None
) -> dict[str, int]:
    """Resolve defaults or an explicit override without changing the clinical query.

    An explicit identifier scope supplies its intended study count and complete page plan;
    deliberate large ID lists therefore do not masquerade as accidental broad searches.
    """
    if value is not None and policy_problem(value) != "ok":
        raise ValueError("acquisition." + policy_problem(value))
    given = value if isinstance(value, dict) else {}
    studies = DEFAULT_MAX_STUDIES if expected_studies is None else max(1, expected_studies)
    requests = (
        DEFAULT_MAX_REGISTRY_REQUESTS
        if expected_requests is None
        else max(DEFAULT_MAX_REGISTRY_REQUESTS, expected_requests)
    )
    return {
        "max_studies": given.get("max_studies", studies),
        "max_registry_requests": given.get("max_registry_requests", requests),
    }


def expansion_code(
    max_studies: int,
    max_registry_requests: int,
    total: int | None,
    registry_requests: int,
    planned_registry_requests: int,
) -> ExpansionCode:
    """Decide on observed scope and whole-plan/actual work; equality is admissible.

    Costs cannot be negative, bool or unknown numeric types. An unknown total does not
    prevent enforcing actual/planned request work; a valid zero total is not missing.
    """
    if any(type(value) is not int or value <= 0 for value in (max_studies, max_registry_requests)):
        return "invalid_cost"
    if any(type(value) is not int or value < 0 for value in (registry_requests, planned_registry_requests)):
        return "invalid_cost"
    if total is not None and (type(total) is not int or total < 0):
        return "invalid_cost"
    if total is not None and total > max_studies:
        return "study_expansion"
    if max(registry_requests, planned_registry_requests) > max_registry_requests:
        return "request_expansion"
    return "within_budget"


def refusal_detail(
    policy: dict[str, int], total: int | None, registry_requests: int, planned_registry_requests: int
) -> str:
    """Operational context for a named stop; the operator can scope or explicitly budget it."""
    return (
        f"observed studies={total}; max_studies={policy['max_studies']}; "
        f"registry_requests={registry_requests}; planned_registry_requests={planned_registry_requests}; "
        f"max_registry_requests={policy['max_registry_requests']}. Keep the saved evidence. "
        "Revise the clinical search scope or explicitly set acquisition budgets "
        "for the intended pull in a new run."
    )
