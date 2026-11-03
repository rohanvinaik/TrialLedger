"""Scoped documentary exception floors; source location never certifies clinical meaning.

Selections locate exact retained values. Separately supplied bindings declare possible failed
requirements for distinct participants, at the named scope and time. Only an accepted entry-only
attribution supplies an eligibility floor. Counts never supply an informative exception ceiling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, cast

from TrialLedger.layer2 import assertions, source_evidence

SCOPE_FIELDS = frozenset({"study", "population", "arm", "time", "version"})
MAX_ITEMS = 256
Extent = Literal["population", "profile"]
TARGETS = frozenset(
    {"entry_eligibility", "treatment_adherence", "assessment_adherence", "other_protocol_requirement"}
)
Scope = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Source:
    id: str
    study_ref: str
    digest: str
    snapshot_json: str


@dataclass(frozen=True)
class Observation:
    id: str
    source: str
    scope: Scope
    count: int
    denominator: int
    located_json: str


@dataclass(frozen=True)
class Binding:
    id: str
    observation: str
    scope: Scope
    possible_targets: tuple[str, ...]
    extent: Extent
    profile: str | None
    status: str
    resolution: str
    basis: tuple[str, ...]
    rule: tuple[str, str]


@dataclass(frozen=True)
class Bundle:
    study_ref: str
    sources: tuple[Source, ...]
    observations: tuple[Observation, ...]
    bindings: tuple[Binding, ...]


def interval_state(lower: int, upper: int | None, maximum: int) -> str:
    """Name interval information without turning an unknown ceiling into zero (pure).

    pre: lower >= 0 and maximum >= 0
    pre: upper is None or upper >= 0
    post: __return__ in ('structural_maximum_conflict', 'ceiling_conflict', 'unknown_ceiling', 'consistent')
    post: (__return__ == 'structural_maximum_conflict') == (lower > maximum)
    post: (__return__ == 'ceiling_conflict') == (lower <= maximum and upper is not None and lower > upper)
    post: (__return__ == 'unknown_ceiling') == (lower <= maximum and upper is None)
    post: (__return__ == 'consistent') == (lower <= maximum and upper is not None and lower <= upper)
    """
    if lower > maximum:
        return "structural_maximum_conflict"
    if upper is None:
        return "unknown_ceiling"
    if lower > upper:
        return "ceiling_conflict"
    return "consistent"


def extent_transfer(source_extent: str, target_extent: str, same_profile: bool) -> str:
    """Transfer floors only in the direction warranted by set inclusion (pure).

    pre: source_extent in ('population', 'profile')
    pre: target_extent in ('population', 'profile')
    post: __return__ in ('population_floor', 'profile_floor', 'no_local_floor', 'profile_mismatch')
    post: (__return__ == 'no_local_floor') == (source_extent == 'population' and target_extent == 'profile')
    post: (__return__ == 'population_floor') == (target_extent == 'population')
    post: __return__ != 'profile_mismatch' or (source_extent == 'profile' and not same_profile)
    post: __return__ != 'profile_mismatch' or target_extent == 'profile'
    post: (__return__ == 'profile_floor') == (source_extent == target_extent == 'profile' and same_profile)
    """
    if target_extent == "population":
        return "population_floor"
    if source_extent == "population":
        return "no_local_floor"
    if not same_profile:
        return "profile_mismatch"
    return "profile_floor"


def attribution_state(entry_possible: bool, target_count: int) -> str:
    """Classify a supplied target intersection, never its recording period (pure).

    pre: 0 <= target_count <= 4
    pre: not entry_possible or target_count > 0
    post: __return__ in ('attribution_conflict', 'entry_eligibility', 'attribution_open', 'non_entry_failure')
    post: (__return__ == 'attribution_conflict') == (target_count == 0)
    post: (__return__ == 'entry_eligibility') == (entry_possible and target_count == 1)
    post: (__return__ == 'attribution_open') == (entry_possible and target_count > 1)
    post: (__return__ == 'non_entry_failure') == (not entry_possible and target_count > 0)
    """
    if target_count == 0:
        return "attribution_conflict"
    if not entry_possible:
        return "non_entry_failure"
    if target_count == 1:
        return "entry_eligibility"
    return "attribution_open"


def _object(value: object, fields: frozenset[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"exception_bounds:{where}:object_required")
    if set(value) != fields:
        raise ValueError(f"exception_bounds:{where}:fields")
    return cast(dict[str, Any], value)


def _text(value: object, where: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"exception_bounds:{where}:text_required")
    return value


def _rows(value: object, where: str, nonempty: bool = False) -> list:
    if type(value) is not list:
        raise ValueError(f"exception_bounds:{where}:list_required")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"resource_bound:exception_bounds:{where}")
    if nonempty and not value:
        raise ValueError(f"exception_bounds:{where}:nonempty_required")
    return value


def _integer(value: object, where: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"exception_bounds:{where}:nonnegative_integer_required")
    return value


def _scope(value: object) -> Scope:
    row = _object(value, SCOPE_FIELDS, "scope")
    return tuple((key, _text(row[key], "scope." + key)) for key in sorted(SCOPE_FIELDS))


def _profile(value: object) -> str:
    if type(value) is dict:
        held = assertions.from_canonical(json.dumps(source_evidence.hydrate(value, []), allow_nan=False))
    else:
        held = value
    if not isinstance(held, assertions.PROPOSITIONS):
        raise ValueError("exception_bounds:profile:proposition_required")
    return assertions.canonical(held)


def _extent(row: dict[str, Any]) -> tuple[Extent, str | None]:
    extent = row["extent"]
    if extent == "population" and type(extent) is str:
        if row["profile"] is not None:
            raise ValueError("exception_bounds:population:profile_must_be_null")
        return "population", None
    if extent == "profile" and type(extent) is str:
        return "profile", _profile(row["profile"])
    raise ValueError("exception_bounds:extent:unsupported")


def _identity(row: dict[str, Any], seen: set[str], where: str) -> str:
    identity = _text(row["id"], where + ".id")
    if identity in seen:
        raise ValueError(f"exception_bounds:{where}:duplicate_id")
    seen.add(identity)
    return identity


def _sources(raw: object) -> tuple[tuple[Source, ...], dict[str, tuple[object, dict]]]:
    result = []
    snapshots: dict[str, tuple[object, dict]] = {}
    seen: set[str] = set()
    for value in _rows(raw, "sources"):
        row = _object(value, frozenset({"id", "study", "digest"}), "source")
        identity = _identity(row, seen, "source")
        snapshot = source_evidence.snapshot(row["study"])
        if type(row["digest"]) is not str or row["digest"] != snapshot["digest"]:
            raise ValueError("exception_bounds:source:stale_digest")
        result.append(
            Source(
                identity,
                snapshot["study_ref"],
                snapshot["digest"],
                json.dumps(snapshot),
            )
        )
        snapshots[identity] = (row["study"], snapshot)
    return tuple(result), snapshots


def _observations(raw: object, snapshots: dict[str, tuple[object, dict]]) -> tuple[Observation, ...]:
    result = []
    seen: set[str] = set()
    fields = frozenset({"id", "source", "scope", "count", "category", "denominator", "context"})
    for value in _rows(raw, "observations"):
        row = _object(value, fields, "observation")
        identity = _identity(row, seen, "observation")
        source = _text(row["source"], "observation.source")
        if source not in snapshots:
            raise ValueError("exception_bounds:observation:unknown_source")
        study, snapshot = snapshots[source]
        anchors = []
        for role in ("count", "category", "denominator"):
            selection = _object(row[role], frozenset({"address", "expected"}), "selection")
            anchors.append({"id": role, "digest": snapshot["digest"], **selection})
        for value in _rows(row["context"], "observation.context", True):
            context = _object(value, frozenset({"id", "address", "expected"}), "context")
            identity_context = _text(context["id"], "context.id")
            if identity_context in ("count", "category", "denominator"):
                raise ValueError("exception_bounds:context:reserved_id")
            anchors.append({"digest": snapshot["digest"], **context})
        located = source_evidence.anchors(study, snapshot, anchors)
        count = source_evidence.strict_integer(located[0]["value"])
        denominator = source_evidence.strict_integer(located[2]["value"])
        if count < 0 or denominator < 0:
            raise ValueError("exception_bounds:observation:invalid_count_range")
        result.append(
            Observation(
                identity,
                source,
                _scope(row["scope"]),
                count,
                denominator,
                json.dumps(located),
            )
        )
    return tuple(result)


def _bindings(raw: object, observations: tuple[Observation, ...]) -> tuple[Binding, ...]:
    result = []
    known = {row.id for row in observations}
    seen: set[str] = set()
    fields = frozenset(
        {
            "id",
            "observation",
            "scope",
            "possible_targets",
            "extent",
            "profile",
            "status",
            "resolution",
            "basis",
            "rule",
        }
    )
    for value in _rows(raw, "bindings"):
        row = _object(value, fields, "binding")
        identity = _identity(row, seen, "binding")
        observation = _text(row["observation"], "binding.observation")
        if observation not in known:
            raise ValueError("exception_bounds:binding:unknown_observation")
        status = _text(row["status"], "binding.status")
        resolution = _text(row["resolution"], "binding.resolution")
        if status not in assertions.STATUSES or resolution not in assertions.RESOLUTIONS:
            raise ValueError("exception_bounds:binding:standing")
        basis = tuple(_text(item, "binding.basis") for item in _rows(row["basis"], "binding.basis", True))
        rule = _object(row["rule"], frozenset({"id", "version"}), "rule")
        targets = tuple(
            _text(item, "binding.possible_targets")
            for item in _rows(row["possible_targets"], "binding.possible_targets", True)
        )
        if len(targets) != len(set(targets)) or not set(targets) <= TARGETS:
            raise ValueError("exception_bounds:binding:invalid_possible_targets")
        extent, profile = _extent(row)
        result.append(
            Binding(
                identity,
                observation,
                _scope(row["scope"]),
                tuple(sorted(targets)),
                extent,
                profile,
                status,
                resolution,
                basis,
                (_text(rule["id"], "rule.id"), _text(rule["version"], "rule.version")),
            )
        )
    return tuple(result)


def prepare(raw: object, study_ref: str) -> Bundle:
    """Validate documentary selections and freeze declarations, without accepting their meaning."""
    _text(study_ref, "study_ref")
    held = source_evidence.hydrate(raw, [])
    row = _object(held, frozenset({"sources", "observations", "bindings"}), "evidence")
    sources, snapshots = _sources(row["sources"])
    observations = _observations(row["observations"], snapshots)
    return Bundle(study_ref, sources, observations, _bindings(row["bindings"], observations))


def _application_problems(
    bundle: Bundle,
    observation: Observation,
    binding: Binding,
    scope: Scope,
    population: str,
    denominator: int,
) -> list[str]:
    source = next(row for row in bundle.sources if row.id == observation.source)
    problems = []
    if source.study_ref != bundle.study_ref:
        problems.append("source_study_mismatch")
    for name, held in (
        ("observation", observation.scope),
        ("binding", binding.scope),
        ("application", scope),
    ):
        if dict(held)["study"] != source.study_ref:
            problems.append(name + "_study_mismatch")
        if dict(held)["version"] != source.digest:
            problems.append(name + "_version_mismatch")
    if observation.scope != binding.scope or binding.scope != scope:
        problems.append("scope_mismatch")
    if dict(scope)["population"] != population:
        problems.append("population_mismatch")
    if observation.denominator != denominator:
        problems.append("denominator_mismatch")
    return problems


@dataclass(frozen=True)
class Application:
    scope: Scope
    population: str
    denominator: int
    extent: Extent
    profile: str | None
    status: str
    resolution: str


def _attributions(bindings: list[Binding]) -> dict:
    accepted = [row for row in bindings if row.status != "proposed" and row.resolution == "resolved"]
    known = [row for row in accepted if row.status == "known"]
    possible = set(TARGETS).intersection(*(set(row.possible_targets) for row in accepted))
    known_possible = set(TARGETS).intersection(*(set(row.possible_targets) for row in known))
    state = attribution_state("entry_eligibility" in possible, len(possible))
    known_state = attribution_state("entry_eligibility" in known_possible, len(known_possible))
    standing = None
    if accepted:
        standing = (
            "known"
            if known_state == "attribution_conflict"
            or (state == "entry_eligibility" and known_state == "entry_eligibility")
            else max((row.status for row in accepted), key=("known", "interpolated").index)
        )
    return {
        "state": state,
        "possible_targets": sorted(possible),
        "known_possible_targets": sorted(known_possible),
        "known_state": known_state,
        "status": standing,
        "accepted_bindings": [row.id for row in accepted],
        "known_bindings": [row.id for row in known],
    }


def _group_result(
    bundle: Bundle, bindings: list[Binding], observation: Observation, use: Application
) -> dict:
    first = bindings[0]
    attribution = _attributions(bindings)
    base = _application_problems(bundle, observation, first, use.scope, use.population, use.denominator)
    transfer = extent_transfer(first.extent, use.extent, first.profile == use.profile)
    if transfer == "profile_mismatch":
        base.append(transfer)
    bridge = []
    if use.status == "proposed":
        bridge.append("bridge_proposed")
    if use.resolution != "resolved":
        bridge.append("bridge_unresolved")
    state = attribution["state"]
    problems = [*base, *bridge]
    if state == "attribution_conflict":
        problems.append("attribution_conflict")
    elif state != "entry_eligibility":
        problems.append(
            "missing_entry_attribution" if state == "attribution_open" else "negative_target_not_eligibility"
        )
    can_transfer = transfer in ("population_floor", "profile_floor")
    possible_floor = (
        observation.count
        if "entry_eligibility" in attribution["possible_targets"] and not base and can_transfer
        else 0
    )
    floor = observation.count if not problems and can_transfer else 0
    independent = floor
    if (
        state == "attribution_conflict"
        and attribution["known_state"] == "entry_eligibility"
        and not base
        and not bridge
        and can_transfer
    ):
        independent = observation.count
    located = json.loads(observation.located_json)
    source_basis = [item["ref"] for item in located]
    contributions = []
    conditional = [floor]
    pending = []
    for binding in bindings:
        accepted = binding.id in attribution["accepted_bindings"]
        possible = set(attribution["possible_targets"])
        if not accepted:
            possible.intersection_update(binding.possible_targets)
        conditional_state = attribution_state("entry_eligibility" in possible, len(possible))
        conditional_floor = (
            observation.count if conditional_state == "entry_eligibility" and not base and can_transfer else 0
        )
        conditional.append(conditional_floor)
        own = [*base, *bridge]
        if binding.status == "proposed":
            own.append("binding_proposed")
        if binding.resolution != "resolved":
            own.append("binding_unresolved")
        pending.extend(problem + ":" + binding.id for problem in own if problem.startswith("binding_"))
        contributions.append(
            {
                "binding": binding.id,
                "observation": observation.id,
                "count": observation.count,
                "reported_lower": observation.count,
                "possible_targets": list(binding.possible_targets),
                "accepted_possible_targets": attribution["possible_targets"].copy(),
                "conditional_possible_targets": sorted(possible),
                "conditional_state": conditional_state,
                "conditional_floor": conditional_floor,
                "denominator": observation.denominator,
                "transfer": transfer,
                "floor": floor if accepted else 0,
                "status": binding.status,
                "resolution": binding.resolution,
                "scope": dict(binding.scope),
                "extent": binding.extent,
                "profile": json.loads(binding.profile) if binding.profile else None,
                "source": observation.source,
                "located": json.loads(observation.located_json),
                "basis": [*source_basis, *binding.basis],
                "meaning_rule": {"id": binding.rule[0], "version": binding.rule[1]},
                "blockers": own,
            }
        )
    blockers = [problem + ":" + first.id for problem in problems]
    if state != "entry_eligibility":
        blockers.extend(pending)
    return {
        "observation": observation.id,
        "bindings": [row.id for row in bindings],
        "scope": dict(first.scope),
        "extent": first.extent,
        "profile": json.loads(first.profile) if first.profile else None,
        "reported_lower": observation.count,
        "denominator": observation.denominator,
        **attribution,
        "applicable": not base,
        "lower": None if state == "attribution_conflict" else floor,
        "conditional_lower": None if state == "attribution_conflict" else max(conditional),
        "independent_lower": independent,
        "possible_floor_upper": max(independent, possible_floor),
        "application_blockers": [problem + ":" + first.id for problem in (*base, *bridge)],
        "blockers": blockers,
        "pending_blockers": pending,
        "contributions": contributions,
    }


def apply(
    bundle: object,
    reference: object,
    population: str,
    denominator: int,
    body: object,
    cap: int | None,
    bridge_status: str,
    bridge_resolution: str,
) -> dict:
    """Prepare exceptions to a positive participation-to-eligibility bridge.

    Precondition: the caller's budget concerns ineligible positive-participation witnesses.
    Rejected witnesses have a different budget predicate; the public caller must gate that use.
    Independent failures combine by MAX. Attributions intersect only for one failure's exact identity.
    """
    if not isinstance(bundle, Bundle):
        raise ValueError("exception_bounds:bundle:prepared_bundle_required")
    _text(population, "population")
    _integer(denominator, "denominator")
    if cap is not None:
        _integer(cap, "cap")
    _text(bridge_status, "bridge.status")
    _text(bridge_resolution, "bridge.resolution")
    if bridge_status not in assertions.STATUSES or bridge_resolution not in assertions.RESOLUTIONS:
        raise ValueError("exception_bounds:bridge:standing")
    ref = _object(reference, frozenset({"bindings", "scope", "extent", "profile"}), "reference")
    scope = _scope(ref["scope"])
    extent, profile = _extent(ref)
    if extent == "profile" and profile != _profile(body):
        raise ValueError("exception_bounds:reference:profile_body_mismatch")
    ids = tuple(
        _text(item, "reference.bindings") for item in _rows(ref["bindings"], "reference.bindings", True)
    )
    if len(ids) != len(set(ids)):
        raise ValueError("exception_bounds:reference:duplicate_binding")
    by_binding = {row.id: row for row in bundle.bindings}
    by_observation = {row.id: row for row in bundle.observations}
    if any(identity not in by_binding for identity in ids):
        raise ValueError("exception_bounds:reference:unknown_binding")
    use = Application(scope, population, denominator, extent, profile, bridge_status, bridge_resolution)
    grouped: dict[tuple, list[Binding]] = {}
    for identity in ids:
        binding = by_binding[identity]
        grouped.setdefault((binding.observation, binding.scope, binding.extent, binding.profile), []).append(
            binding
        )
    groups = [
        _group_result(bundle, rows, by_observation[rows[0].observation], use) for rows in grouped.values()
    ]
    contributions = [row for group in groups for row in group["contributions"]]
    conflict = any(group["state"] == "attribution_conflict" and group["applicable"] for group in groups)
    independent_lower = max([0, *(group["independent_lower"] for group in groups)])
    possible_floor = max([independent_lower, *(group["possible_floor_upper"] for group in groups)])
    conditional_lower = max([independent_lower, *(group["conditional_lower"] or 0 for group in groups)])
    interval = floor_cap_state(independent_lower, possible_floor, cap, denominator)
    blockers = ["exception_upper_unknown"] if cap is None else []
    blockers.extend(problem for group in groups for problem in group["application_blockers"])
    if interval == "attribution_dependent" or conflict:
        blockers.extend(problem for group in groups for problem in group["blockers"])
    blockers = list(dict.fromkeys(blockers))
    code = (
        "attribution_conflict"
        if conflict
        else "conflict"
        if interval in ("ceiling_conflict", "structural_maximum_conflict")
        else "unresolved"
        if blockers
        else "consistent"
    )
    statuses = [
        bridge_status,
        *(
            group["status"]
            for group in groups
            if group["status"] is not None
            and group["applicable"]
            and (group["independent_lower"] or group["state"] == "attribution_conflict")
        ),
    ]
    status = max(statuses, key=("known", "interpolated", "proposed").index)
    basis = list(dict.fromkeys(item for row in contributions for item in row["basis"]))
    check = {
        "target": "entry_eligibility",
        "code": code,
        "lower": None if conflict else independent_lower,
        "upper": cap,
        "structural_maximum": denominator,
        "interval_state": "attribution_conflict" if conflict else interval,
        "independent_lower": independent_lower,
        "independent_interval_state": interval_state(independent_lower, cap, denominator),
        "possible_floor_upper": possible_floor,
        "possible_floor_meaning": (
            "Largest lower-bound constraint supplied by these observations "
            "across represented target readings; "
            "not an upper bound on total exceptions."
        ),
        "conditional_lower": None if conflict else conditional_lower,
        "conditional_interval_state": interval_state(conditional_lower, cap, denominator),
        "independent_conditional_lower": conditional_lower,
        "extent": extent,
        "scope": dict(scope),
        "profile": json.loads(profile) if profile else None,
        "attributions": groups,
        "contributions": contributions,
        "blockers": blockers,
        "pending_blockers": [problem for group in groups for problem in group["pending_blockers"]],
        "basis": basis,
        "rule": "exception-bounds:2",
    }
    return {
        "check": check,
        "status": status,
        "resolution": "conflicting" if conflict else "unresolved" if blockers else "resolved",
        "blockers": blockers,
        "basis": basis.copy(),
        "effective_cap": denominator if cap is None or conflict else min(cap, denominator),
    }


def floor_cap_state(certain: int, possible: int, upper: int | None, maximum: int) -> str:
    """Compatibility with selected evidence, never certification of a total-exception ceiling (pure).

    The possible floor is the largest floor available under the retained attribution alternatives;
    it is not an upper bound on all exceptions. Only attribution uncertainty able to change the
    compatibility result remains a blocker of that result.

    pre: 0 <= certain <= possible
    pre: maximum >= 0
    pre: upper is None or upper >= 0
    post: (__return__ == 'structural_maximum_conflict') == (certain > maximum)
    post: (__return__ == 'unknown_ceiling') == (certain <= maximum and upper is None)
    post: (__return__ == 'ceiling_conflict') == (upper is not None and upper < certain <= maximum)
    post: (__return__=='attribution_dependent')==(upper is not None and certain<=min(upper,maximum)<possible)
    post: (__return__ == 'consistent') == (upper is not None and possible <= min(upper, maximum))
    """
    if certain > maximum:
        return "structural_maximum_conflict"
    if upper is None:
        return "unknown_ceiling"
    if certain > upper:
        return "ceiling_conflict"
    if possible > min(upper, maximum):
        return "attribution_dependent"
    return "consistent"
