# Frozen projection interface: packet E (interface v1)

This instantiates C4's named projections. A projector turns one validated protocol check into existing public
child requests and a projection receipt. It runs no operator, reads no prose, adds no clinical relation, and
never widens a scope. The coordinator executes the children through the managed `_child` path, so budget,
reservation and canonical retention are not E's job.

**Preconditions.**
- Packet A's frozen index shape (`ledger.md`, "Return value").
- The public `signals` request extended by the coordinator with an optional per-signal `claims` list. This is
  accepted only for `schedule_coverage`, `finite_policy` and `binomial_design`.
- Until the coordinator lands that extension, E's tests assert the request *shape*. They never run it through
  `service`.

## Module and signature

The module is `TrialLedger/layer2/protocol_projections.py`. Its tests are `tests/test_protocol_projections.py`.

```python
PROJECTIONS: dict[str, str]          # check kind -> "name:version", the registry below

project(index: dict, check_id: str, *, premise_standing: Mapping[str, dict]) -> dict
```

- `index` is exactly what `protocol_objects.validate_protocol` returns. E never re-validates it, and never
  calls `validate_protocol` except in tests.
- `premise_standing` maps each premise id to exactly `{status, resolution, basis}`. The coordinator computes
  it from effective premises. E never reads premise payloads.
- Malformed `check_id` or a missing premise standing raises `ValueError("projection_<code>")`.
- Allowed imports: `copy`, `json`, `hashlib`, `typing`/`collections.abc`, and
  `TrialLedger.layer2.protocol_objects`, for the constants R-DEP/R-EST/R-POL only.
- **Never import** the operators, `signals`, `service`, `session_state` or `design_session`. A projector builds
  requests; it never evaluates them.

### Return value

```text
{"check": id, "kind": kind, "projection": "name:version",
 "children": [{"id": child_id, "request": <public request>, "receipt": <receipt>}],
 "unresolved": [{"code": str, "objects": [ids], "premises": [ids]}],
 "not_computed": null | {"method": object id, "definition": standing_ref, "missing": [names], "inputs": [...]}}
```

- A check with `unresolved` entries still returns every child that could be built. When the unresolved
  binding blocks the only child, `children` is empty, and that is never silent.

### Receipt (C4)

The receipt has exactly these fields:
- `projection`, `version`, `check`;
- `objects`: consumed object ids, in input order;
- `premises`: the union of their support plus the check's support, unique, in input order;
- `target`, `scope`: the check's;
- `bindings`: copied from the check;
- `role_support`;
- `conditions`;
- `request_digest`: sha256 of canonical JSON (`sort_keys=True, separators=(",",":"), ensure_ascii=False`).

`role_support` maps each operator input role to the support entries that role depends on. This is what R1
needs: the coordinator gates a claim row's `determined_by` roles over exactly these entries. `conditions`
lists the `{object, condition}` pairs for any non-null assessment condition. A conditional result is never
applied unconditionally (C4).

## Support entries (C1 and C3: standing is conjunctive)

For an object O, its entries are:
- `{"id": "object:O", "status": O.standing.status, "resolution": O.standing.resolution, "basis": O.standing.basis}`;
- plus one per support premise P: `{"id": "premise:P", **premise_standing[P]}`;
- if O.support is empty: `{"id": "adoption:O", "status": O.standing.status, "resolution": "unresolved",
  "basis": ["no adoption support declared for O"]}`. A drafted object never becomes a known constraint.

A signal's `support` is the union, without duplicate ids, of the entries for every object it consumes, plus
the check's support premises. Order: objects in `check.objects` order, each object's entries in the order
above, then check premises.

## Registry

| check kind | projection | Children | Role support |
|---|---|---|---|
| schedule | `schedule_window_coverage:1` | One `signals` request with one signal. `kind` is `schedule_coverage`. `data` is `{scope: S, anchor: A.anchor, unit: A.unit, nominal: A.nominal, permitted: A.permitted, available: C.availability}`, where A is the assessment and C the collection; anchor and unit come only from A, by the named relation. `claims` is `check.claims` | `permitted` and `nominal` take A's entries; `available` takes C's entries |
| finite_policy | `finite_policy_model:1` | `kind: finite_policy`, `data: P.model` (deep copy), `claims: check.claims` | `model` takes P's entries plus the entries of every bound object and premise in `P.bindings` |
| binomial_design | `binomial_efficacy:1` | `kind: binomial_design`. `data` is `{scope: S, **E.parameters, assumptions: [...]}`, with one assumption per `E.assumptions` item: `{role, ref: "premise:"+premise, version: E.version, **premise_standing[premise]}`. `claims: check.claims` | `parameters` takes the efficacy and endpoint entries; `assumptions` takes the premise entries |
| estimand | `estimand_declaration:1` | `kind: estimand`, `data: Est.data` (deep copy). **No** `claims` key: the existing operator supports none | `estimand` takes Est's entries |
| dependencies | `endpoint_dependencies:1` | `kind: dependencies`, `data: Endpoint.dependencies`, with no `claims` key | `dependencies` takes the endpoint's and its variable measurement's entries |
| temporal, decision_table | `temporal_request:1` / `decision_table_request:1` | The check's single binding `{projection: <this name>, data: {...}}` becomes `kind: temporal`/`decision_table`, `data` unchanged. Any other binding shape gives `unresolved`: `projection_binding_shape` | `data` takes the entries of the check's objects |
| external_method | `external_method_declaration:1` | No children. `not_computed` comes from the external_method object, or from an efficacy's referenced one | none |
| definition | Not projected by E in wave 2 | `unresolved`: `projection_slice_5` (DEF-1/2 bind to actual analysis addresses, task 5.4) | none |

- **Scope string.** S = `json.dumps(check["scope"], sort_keys=True, separators=(",",":"), ensure_ascii=False)`.
  If S is over 1024 characters, the result is `unresolved`: `projection_scope_too_long`.
- **Scope equality.** Every consumed object's scope must equal the check's scope exactly, as canonical JSON.
  Otherwise the result is `unresolved`: `projection_scope_mismatch`, naming the objects, with no child. A
  projector never widens, intersects or aligns scopes (TIM-5, SCP-2, C1.8). A supported alignment relation is
  later work.
- **Request shape.** Each signals request is exactly `{"operation": "signals", "signals": [signal]}`. The child
  id and the signal id are `"<check id>:<projection name>"`.
- **Role support on the child (added after Rohan's R1 decision).**
  - Each claim-kind child signal (schedule_coverage, finite_policy, binomial_design) also carries
    `"role_support": {role: [support entry ids]}`, built from the receipt's `role_support` entries.
  - The keys are the operator's roles: schedule `permitted`/`nominal`/`available`; policy `model`; binomial
    `parameters`/`assumptions`.
  - Each list holds the unique `id`s of that role's entries, in entry order. Every id must also appear in the
    signal's `support`.
  - estimand, dependencies, temporal and decision_table children carry no `role_support`. The public request
    refuses it for those kinds.

## Acceptance for packet E (direct-call tests in `tests/test_protocol_projections.py`)

**Positive.**
- For each registry row, build a valid index from packet A's `fixtures/objects.json`, call
  `protocol_projections.project(...)` by name, and assert:
  - the exact child request;
  - the receipt fields and `request_digest`;
  - `role_support`.
- A schedule child's `data` must be byte-identical to what packet B's fixture TIM-1 would need, given the same
  numbers.

**MUST-NOT.**
- An object with empty support never projects known-and-resolved support: the adoption entry is present.
- A proposed support premise appears in support and in role_support. It is never dropped or upgraded.
- A scope mismatch yields `unresolved` and no child.
- A label or id that resembles another object's never creates a binding.
- An assessment condition always appears in `conditions`.
- Repeated projection of the same check yields the same digest.
- The index and `premise_standing` are not mutated.
- No operator, `signals` or `service` import. Check this in a subprocess `sys.modules` test, as packet A does.

## Integration correction (coordinator, after the second external review on 2026-11-04)

**Check-wide support is explicit in every role.** Every `check.support` premise entry is appended to every role's
support entries, so it appears in the receipt's `role_support` and in the child signal's `role_support` ids.
Previously check premises appeared in no role, and the gate inferred them as common from their absence. A premise
that also backed one object, such as the collection plan, therefore escaped the check-wide gate, and declaring it
check-wide didn't even change the request digest.

The paired regression in `tests/test_protocol_review_repairs.py` covers both sides:
- collection-only proposed support leaves a known outside-window finding admitted;
- the same premise declared check-wide withholds it, and the request digest changes.

**The applicability binding is separate from operation bindings** (third external review). Temporal and
decision-table projectors count only non-`condition_applicability` bindings toward their single operation
binding. The managed session validates the applicability binding (task 2.9), so the two coexist.
