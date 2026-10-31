"""The ledger: every value of a study record, with its location and the role the record's structure gives it.

The ledger is the record, entry by entry. Nothing is dropped, merged or rewritten: rebuilding a record from
its leaves reproduces it exactly, in content and in key order (tests/test_ledger.py checks `entries` against
an independent walk of every test record's leaves, and rebuilds each record from them). Roles come
only from structure, the section a value sits in and the identifiers beside it, never from free text. An
absent field is named by absence_state; no view shows it as zero, none or no.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from TrialLedger.registry import redacted_when_withheld

Path = tuple[str | int, ...]

# The roles a record's structure states, by the place of a listed node: (section, module, listing). A place
# with a FIXED role gives it to every node listed there (the outcome type of a registered outcome's section:
# the API metadata dedLinks "Primary Outcome Measure Information", "Secondary Outcome Measure Information",
# "Other Pre-specified Outcome Measures", named by the registry's OutcomeMeasureType values; the table of an
# adverse event). A place with an IDENTIFIED role takes the role's value from one field of the node itself.
P = "protocolSection"
R = "resultsSection"
FIXED_ROLES: dict[Path, tuple[str, str]] = {
    (P, "outcomesModule", "primaryOutcomes"): ("outcome_type", "PRIMARY"),
    (P, "outcomesModule", "secondaryOutcomes"): ("outcome_type", "SECONDARY"),
    (P, "outcomesModule", "otherOutcomes"): ("outcome_type", "OTHER_PRE_SPECIFIED"),
    (R, "adverseEventsModule", "seriousEvents"): ("event_table", "serious"),
    (R, "adverseEventsModule", "otherEvents"): ("event_table", "other"),
}
IDENTIFIED_ROLES: dict[Path, tuple[str, str]] = {
    (P, "referencesModule", "references"): ("reference_type", "type"),
    (P, "armsInterventionsModule", "armGroups"): ("arm", "label"),
    (P, "armsInterventionsModule", "interventions"): ("intervention", "name"),
    (R, "outcomeMeasuresModule", "outcomeMeasures"): ("outcome_type", "type"),
}
# The lists whose entries are result groups, as one-element path slices.
GROUP_PARENTS: tuple[Path, ...] = (("groups",), ("eventGroups",))

# Fields the registry's definitions limit to one study type (Protocol Registration Data Element Definitions:
# «Interventional Study Design (For interventional studies only)», «Observational Study Design (For
# Observational Studies only)», «Study Population Description (For observational studies only)», «Sampling
# Method (For observational studies only)»). Keys are field paths: locations without list indices.
INTERVENTIONAL_ONLY = ("INTERVENTIONAL",)
OBSERVATIONAL_ONLY = ("OBSERVATIONAL",)
APPLIES_TO: dict[str, tuple[str, ...]] = {
    "protocolSection.designModule.phases": INTERVENTIONAL_ONLY,
    "protocolSection.designModule.designInfo.allocation": INTERVENTIONAL_ONLY,
    "protocolSection.designModule.designInfo.interventionModel": INTERVENTIONAL_ONLY,
    "protocolSection.designModule.designInfo.primaryPurpose": INTERVENTIONAL_ONLY,
    "protocolSection.designModule.designInfo.maskingInfo.masking": INTERVENTIONAL_ONLY,
    "protocolSection.designModule.designInfo.observationalModel": OBSERVATIONAL_ONLY,
    "protocolSection.designModule.designInfo.timePerspective": OBSERVATIONAL_ONLY,
    "protocolSection.eligibilityModule.studyPopulation": OBSERVATIONAL_ONLY,
    "protocolSection.eligibilityModule.samplingMethod": OBSERVATIONAL_ONLY,
}

# Fields whose API metadata (rules or description) says «Redacted for Withheld studies», «[Redacted] for
# Withheld studies» or «Marked as [Missing] for Withheld studies» (TrialLedger/registry/ctg-metadata.json).
REDACTED_WHEN_WITHHELD = redacted_when_withheld()

# How a view shows each absence state, in words.
ABSENCE_TEXT = {
    "not_reported": "not reported",
    "not_applicable": "not applicable to this study type",
    "redacted": "redacted (withheld study)",
}


# ── reading the record ────────────────────────────────────────────────────────────────────────────────


def get(obj: Any, *keys: str | int) -> Any:
    """The value at a path of keys and list indices, or None where the path does not exist."""
    for key in keys:
        if isinstance(key, int):
            if not isinstance(obj, list) or not 0 <= key < len(obj):
                return None
            obj = obj[key]
        else:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
    return obj


def as_list(obj: Any) -> list[Any]:
    """`obj` when it is a list, otherwise an empty list."""
    return obj if isinstance(obj, list) else []


def location(path: Path) -> str:
    """A record location, as `protocolSection.outcomesModule.primaryOutcomes[0].measure`."""
    text = ""
    for key in path:
        if isinstance(key, int):
            text += f"[{key}]"
        else:
            text += f".{key}" if text else key
    return text


def field_path(path: Path) -> str:
    """A record location without its list indices, the form the API metadata names fields by."""
    return ".".join(key for key in path if isinstance(key, str))


# ── the ledger itself: lossless leaves, and the structural roles that travel down to them ─────────────


def node_role(path: Path, node: Any) -> tuple[str, str] | None:
    """The role a record node's place and own identifier give everything beneath it (pure — pinned).

    Only structure is read, never free text, and a node gives at most one role:
      a listed node at a place in FIXED_ROLES   — that place's role (an outcome's section, an event's table);
      a listed node at a place in IDENTIFIED_ROLES — the role whose value is the node's own identifier field
                                                  (a reference's type, an arm's label, an intervention's name,
                                                  a posted measure's type), when that field is a string;
      a results-section node with a string groupId, or an entry of a groups list with a string id — its group.
    None when the structure states no role, including an identifier that is absent or not a string.
    """
    own = node if isinstance(node, dict) else {}
    if len(path) == 4 and isinstance(path[3], int):
        fixed = FIXED_ROLES.get(path[:3])
        if fixed is not None:
            return fixed
        identified = IDENTIFIED_ROLES.get(path[:3])
        if identified is not None:
            role, field = identified
            value = own.get(field)
            return (role, value) if isinstance(value, str) else None
    if path[:1] == (R,):
        group = own.get("groupId")
        if isinstance(group, str):
            return ("group", group)
        if path[-2:-1] in GROUP_PARENTS and isinstance(path[-1], int):
            group = own.get("id")
            if isinstance(group, str):
                return ("group", group)
    return None


@dataclass(frozen=True)
class Entry:
    location: str
    value: Any
    role: tuple[tuple[str, str], ...]


def entries(study: dict[str, Any]) -> Iterator[Entry]:
    """The ledger of one study: every leaf, in document order, with its location and its roles."""
    yield from _walk(study, (), {})


def _walk(node: Any, path: Path, roles: dict[str, str]) -> Iterator[Entry]:
    here = dict(roles)
    role = node_role(path, node)
    if role is not None:
        here[role[0]] = role[1]
    if isinstance(node, dict) and node:
        for key, item in node.items():
            yield from _walk(item, (*path, key), here)
    elif isinstance(node, list) and node:
        for index, item in enumerate(node):
            yield from _walk(item, (*path, index), here)
    else:
        yield Entry(location(path), node, tuple(sorted(here.items())))


# ── what the record says about an absent field, and about results ─────────────────────────────────────


def absence_state(
    present: bool,
    redacted_when_withheld: bool,
    applies_to: tuple[str, ...] | None,
    study_type: str | None,
    overall_status: str | None,
) -> str:
    """Why a field holds no value, in the registry's own terms (pure — pinned).

    "reported"       — the field holds a value.
    "not_applicable" — the definitions limit the field to other study types than this study's.
    "redacted"       — a WITHHELD study, and the registry says the field is redacted or marked missing
                       for withheld studies.
    "not_reported"   — otherwise: the record is silent, which is never read as zero, none or no.
    """
    if present:
        return "reported"
    if applies_to is not None and study_type is not None and study_type not in applies_to:
        return "not_applicable"
    if overall_status == "WITHHELD" and redacted_when_withheld:
        return "redacted"
    return "not_reported"


def field_state(study: dict[str, Any], *keys: str | int) -> str:
    """absence_state for the field at `keys` of one study record."""
    value = get(study, *keys)
    name = field_path(keys)
    return absence_state(
        value is not None,
        name in REDACTED_WHEN_WITHHELD,
        APPLIES_TO.get(name),
        get(study, "protocolSection", "designModule", "studyType"),
        get(study, "protocolSection", "statusModule", "overallStatus"),
    )


def results_state(has_results: Any, has_results_section: bool) -> str:
    """What a record states about posted results, from the registry's own flag (pure — pinned).

    "posted"               — hasResults is true and the record holds a results section.
    "not_posted"           — hasResults is false and there is no results section: no results are posted.
    "flag_without_results" — hasResults is true but the record holds no results section.
    "results_without_flag" — the record holds a results section but hasResults is false.
    "flag_not_reported"    — hasResults is absent or not a boolean.
    """
    if not isinstance(has_results, bool):
        return "flag_not_reported"
    if has_results:
        return "posted" if has_results_section else "flag_without_results"
    return "results_without_flag" if has_results_section else "not_posted"
