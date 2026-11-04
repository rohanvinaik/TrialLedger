# Frozen ledger interface: packet A, protocol objects (interface v1)

This instantiates contracts C2, C3, the C4 check envelope and the C10 ceilings for the pure object validator. It
runs no solver and evaluates no claim. Projection of objects into operator requests is packet E (`projections.md`,
frozen before E starts). Contracts C1 through C3 govern everything here.

## Module and signature

The module is `TrialLedger/layer2/protocol_objects.py`. Its tests are `tests/test_protocol_objects.py`.

```python
validate_protocol(protocol: object, *, target: dict, premises: Mapping[str, dict],
                  sources: Mapping[str, dict]) -> dict
```

**Arguments.**
- `protocol` is the raw v2 `session.protocol` value. Detach it with `copy.deepcopy`; never mutate the input.
- `target` is the session's already-validated `new_trial` target, `{kind, ref, scope}`.
- `premises` is the already-validated v1 premise index `{id: premise}` from `session_state.prepare`. Packet A
  reads only the keys and, where noted, `premise["kind"]`.
- `sources` is the already-validated source index `{id: {"snapshot": {"study_ref": str, ...}, "study": dict, ...}}`.

**Errors.** Malformed input raises `ValueError("protocol_<code>")`; the full list is below. Every error is a
translation refusal, never a clinical finding.

**Allowed imports.**
- `copy`, `json`, `typing`, `collections.abc`;
- `TrialLedger.layer2.protocol_numbers`;
- `TrialLedger.layer2.assertions` and `TrialLedger.layer2.entail`, for `proposition_formula` blockers only;
- `TrialLedger.layer2.source_evidence`, for `_selected(study, pointer)` only.

**Never import** `dependency_evidence`, `estimand_evidence`, the protocol operators, `session_state`,
`design_session` or anything that imports them. The literal key lists R-DEP, R-EST and R-POL below are copied
into `protocol_objects.py` as module constants. A coordinator integration test (not packet A's) asserts that
they equal `dependency_evidence.INPUTS`, `estimand_evidence.INPUTS` and `protocol_policies.INPUTS`.
`session_state` and `design_session` are excluded for a further reason: Those modules will import
this one, and a cycle is a refusal. Write the small `_object`/`_text`/`_rows` helpers locally, in the style of
`decision_tables`.

## Return value: a detached canonical index

```text
{
  "schema_version": 1,
  "objects": {id: <deep-copied object>},
  "kinds": {id: kind},
  "order": [ids, dependencies first; ties in input order],
  "dependents": {id: [ids that list it in depends_on, in input order]},
  "references": {id: {"objects": [object ids named inside data, sorted],
                      "premises": [support ids, input order],
                      "sources": [origin.source] or []}},
  "checks": {id: <deep-copied check>},
  "check_order": [check ids in input order],
  "sections": {name: {"state": "requested" | "not_applicable" | "not_requested",
                      "objects": [...], "basis": [...]}}
}
```

- `sections` contains all eight names. Omitted sections are `not_requested`, with empty `objects` and `basis`.
- Packet A computes no standing combination and no coverage verdict; that is coordinator work.

## Protocol envelope

- `protocol` has exactly `schema_version` (the int 1, never `True`), `objects`, `checks` and `sections`
  (`protocol_fields`, `protocol_version`).
- Each of `objects`, `checks` and `sections` is a list, possibly empty (`protocol_not_list`).
- Ceilings:
  - 256 objects (`protocol_object_limit`);
  - 128 checks (`protocol_check_limit`);
  - 8 sections, enforced by uniqueness over the eight names.
- Object IDs and check IDs are separate namespaces. Each is a nonempty string of at most 256 characters
  (`protocol_invalid_id`) and unique within its namespace (`protocol_duplicate_object`,
  `protocol_duplicate_check`).

## Object envelope (C3)

Every object has exactly `id`, `kind`, `scope`, `version`, `origin`, `standing`, `support`, `depends_on` and
`data` (`protocol_object_fields`).

| Field | Rule | Codes |
|---|---|---|
| kind | One of measurement, endpoint, estimand, assessment, collection, efficacy, policy or external_method | `protocol_unknown_kind` |
| scope | Exactly `{target, context}`. `target` must equal the session target, compared as canonical JSON. `context` is exactly `{cohort, phase, arm}`, each a nonempty string or null; null means open, never inferred | `protocol_scope_fields`, `protocol_scope_target`, `protocol_scope_context` |
| version | Nonempty string of at most 256 characters: the definition edition, independent of the draft revision | `protocol_invalid_version` |
| origin | Exactly `{kind, ref, source, analysis}`; see below | `protocol_origin_*` |
| standing | Exactly `{status, resolution, basis}`. `status` ∈ known/interpolated/proposed; `resolution` ∈ resolved/partially_resolved/unresolved/conflicting; `basis` holds 1–32 unique nonempty strings | `protocol_invalid_standing` |
| support | A unique list of premise ids, each present in `premises`. May be empty: adoption then stays unresolved, which is not an error | `protocol_unknown_premise`, `protocol_duplicate_support` |
| depends_on | A unique list of object ids that exist. Every object id named inside `data` must be listed (`protocol_unlisted_reference`). Extra explicit dependencies are allowed. No cycles, including a self-cycle (`protocol_dependency_cycle`) | `protocol_unknown_object`, `protocol_duplicate_dependency` |

**Origin rules.** These are the subset of `session_state._origin` that applies to a protocol object:
- `kind` ∈ user_choice, hypothesis or source_interpretation. `source_rule` and `derived` refuse with
  `protocol_origin_kind`, because a protocol object is never a compiled source rule or an analysis output.
- `ref` is a nonempty string.
- `analysis` must be null (`protocol_origin_analysis`).
- user_choice and hypothesis need `source: null` (`protocol_origin_source`).
- source_interpretation needs a `source` present in `sources` (`protocol_unknown_source`), and a `ref` that
  starts with `sources[source]["snapshot"]["study_ref"] + "#"` (`protocol_origin_digest`).
  `source_evidence._selected(study, pointer)` must resolve the rest; any exception from it becomes
  `protocol_origin_pointer`.

**Standing reference.** The `standing_ref` used below is the existing estimand standing reference
`{ref, version, status, resolution, basis}`, with the same rules as standing plus nonempty `ref` and `version`.
The code is `protocol_invalid_reference`.

**Typed proposition.** A `typed proposition` is the tagged canonical JSON accepted by
`assertions.from_canonical`. It must be an instance of `assertions.PROPOSITIONS`, and
`entail.proposition_formula` must return no blockers (`protocol_invalid_proposition`).

## Closed `data` per kind

Fields are exact (`protocol_data_fields:<kind>`). "ID of K" means an object id whose kind is K
(`protocol_reference_kind`).

| kind | data fields |
|---|---|
| measurement | `definition`: a standing_ref. `unit`: nonempty string or null (null means unresolved). `mode`: observed, imputed or derived. `baseline`: ID of measurement, or null. A baseline may not name the object itself (that is a cycle) |
| endpoint | `variable`: ID of measurement. `definition`: a standing_ref. `estimand`: ID of estimand, or null. `dependencies`: null, or a dict whose key set is exactly {scope, version, rules, adopted, available, unavailable, conditions} (literal list R-DEP). Deep validation is the operator's job at projection time |
| estimand | A dict whose key set is exactly {scope, version, id, definitions, events, requirements, collection_plan, data_state, dependencies} (literal list R-EST). Deep validation happens at projection time. Its `requirements[*].id` values must be unique nonempty strings, because collections refer to them |
| assessment | `measurement`: ID of measurement. `anchor`: nonempty string. `unit`: nonempty string. `nominal`: rational or null. `permitted`: union or null (`protocol_numbers` with prefix `protocol`). `condition`: typed proposition or null. A null condition means unconditional within this exact scope, not all populations |
| collection | `assessment`: ID of assessment. `mode`: observed, imputed or derived. `availability`: union or null (prefix `protocol`). `event_handling`: null, or exactly `{estimand, requirement}`, where `estimand` is an ID of estimand and `requirement` names one of that estimand's `requirements[*].id` (`protocol_unknown_requirement`) |
| efficacy | `endpoint`: ID of endpoint. `method`: binomial_design or external_method. `parameters`: for binomial_design, exactly `{model, direction, n, critical_count, p0, p1}`, with only a shape check here (strings and ints; packet D validates the values). For external_method, an ID of external_method. `assumptions`: a unique list of `{role, premise}`, where `role` ∈ fixed_n, iid_binary or alignment and `premise` is in `premises`. Roles may repeat across different premises; missing roles are allowed, because packet D reports them |
| policy | `model`: a dict whose key set is exactly {scope, version, variables, constraints, states, initial, terminal, actions, transitions, prohibitions, invariants} (literal list R-POL; deep validation is packet C's job at projection time). `bindings`: a unique list of exactly `{variable, object, premise}`. `variable` is a nonempty string that must equal a `model.variables[*].id` (`protocol_unknown_policy_variable`). Exactly one of `object` (an object id) or `premise` (a premise id) is non-null (`protocol_invalid_binding`) |
| external_method | `definition`: a standing_ref. `inputs`: a unique-by-name list of exactly `{name, value, unit, ref}`, where `value` and `unit` are strings or null and `ref` is an object id, a premise id or null. `missing`: a unique list of nonempty names, disjoint from the input names (`protocol_external_missing`) |

When a data reference names an object, it counts as a data reference and must also appear in `depends_on`.
Data references are `measurement.baseline`, `endpoint.variable`, `endpoint.estimand`,
`assessment.measurement`, `collection.assessment`, `collection.event_handling.estimand`, `efficacy.endpoint`,
`efficacy.parameters` (external), `policy.bindings[*].object` and `external_method.inputs[*].ref` (when it names
an object).

## Check envelope (C4): shape only

Every check has exactly `id`, `kind`, `scope`, `objects`, `bindings`, `claims`, `required` and `support`
(`protocol_check_fields`).

| Field | Rule |
|---|---|
| kind | temporal, schedule, dependencies, estimand, definition, decision_table, finite_policy, binomial_design or external_method (`protocol_unknown_check_kind`) |
| scope | Same contract as an object's scope |
| objects | Unique existing object ids (`protocol_unknown_object`, `protocol_duplicate_dependency`) |
| bindings | A list of dicts, each with a nonempty string `projection` field. Their content is frozen by packet E's projection registry and is not validated here |
| claims | A list. The operator validates it |
| required | A strict bool (`protocol_invalid_required`) |
| support | A unique list of premise ids that exist |

**Object pattern per check kind** (`protocol_check_objects:<kind>`): exact counts by object kind, in any order.

| check kind | objects |
|---|---|
| schedule | Exactly one assessment and exactly one collection, and that collection's `assessment` is that assessment |
| dependencies | Exactly one endpoint, whose `dependencies` is non-null |
| estimand | Exactly one estimand |
| finite_policy | Exactly one policy |
| binomial_design | Exactly one efficacy with method binomial_design, plus its endpoint |
| external_method | Exactly one efficacy with method external_method plus its external_method object, or exactly one external_method alone |
| temporal, definition, decision_table | Any declared objects, possibly none. These reuse existing request shapes through bindings |

## Sections

- Each section has exactly `{id, state, objects, basis}` (`protocol_section_fields`).
- `id` is one of population, eligibility, interventions, endpoints, assessments, efficacy, safety or
  exploratory, and is unique (`protocol_unknown_section`, `protocol_duplicate_section`).
- `state` ∈ requested or not_applicable. `objects` is a unique list of existing object ids. `basis` is a unique
  list of nonempty strings.
- not_applicable needs a nonempty basis (`protocol_not_applicable_basis`). requested may have an empty basis.
- Eligibility and intervention sections may list no objects; they cite premises through check bindings.

## Acceptance for packet A (direct-call tests in `tests/test_protocol_objects.py`)

**Positive.**
- One valid object of each kind, a valid check of each kind pattern, and a valid section set. The returned
  index is deep-detached: mutating the input after the call must not change the index, and the reverse.
- Forward references resolve after whole-graph validation.
- `order` puts dependencies first.
- Empty `objects`/`checks`/`sections` are valid, and all eight sections come back `not_requested`.

**MUST-NOT.** Each of these must raise its named code:
- duplicate, dangling, cyclic or self-cyclic objects;
- `True` as schema_version, `1` as required, or a float rational;
- an unknown field at any level;
- a data reference missing from `depends_on`;
- a wrong-kind reference;
- a collection pointing at an unknown requirement;
- a `source_rule` origin, or a hypothesis carrying a source;
- a source_interpretation pointer that doesn't resolve;
- an omitted versus null context key;
- a not_applicable section with an empty basis;
- a 257th object.

**MUST-NOT also covers these non-errors:**
- An empty `support` list must not refuse.
- An own `known` status must not be returned as effective standing; packet A returns none.
- No solver or operator module may be imported. A test runs a **subprocess**
  (`sys.executable -c ...`) that imports `TrialLedger.layer2.protocol_objects`, validates one valid fixture,
  and asserts that `sys.modules` contains none of:
  - `TrialLedger.layer2.decision_tables`, `.dependency_evidence`, `.estimand_evidence`;
  - `.protocol_schedule`, `.protocol_policies`, `.protocol_statistics`;
  - `.session_state`, `.design_session`.

  An in-process check is not acceptable: the full suite has already imported them.

**Fixtures.**
- `fixtures/objects.json`, written by packet A. Each case has `{id, protocol, expect | refusal}` and a builder
  helper inside the test that supplies `target`, `premises` and `sources`.
- Use invented values only: no clinical defaults.
- The coordinator reviews these fixtures before integration.
