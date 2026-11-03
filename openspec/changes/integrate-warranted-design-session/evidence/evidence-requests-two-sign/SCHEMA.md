# Proposed contract: `evidence_requests` (tasks 2a.1–2a.3)

Status: proposal for the lead's sign-off. Field names follow `design_bounds` so a `design_bounds` request's
`candidates` and its result's `remaining` can be passed straight through. Nothing here is wired into
`service`, `result_semantics` or `guide`; those edits belong to the lead.

## Clinical object

Given declared surviving candidate eligibility explanations, list hypothetical participant profiles with an
explicit sign (accepted-and-eligible, or rejected-for-eligibility) that would distinguish them. A returned row is
an investigation request. It is never an observation, a premise, a recommendation or a recovered protocol.

## Request (closed; unknown fields refused)

| Field | Required | Contract |
|---|---|---|
| `operation` | yes | `"evidence_requests"` |
| `study_ref` | yes | nonempty study/version reference; all candidates concern this study |
| `candidates` | yes | array of `design_bounds` candidate objects `{id, assertions}`; `signal_claims` is refused by name (`evidence_requests:candidate:signal_claims_unsupported`) because survival that depended on a signal claim is invisible to a participant-witness search |
| `survivors` | yes | array of candidate ids declared to survive (for example a `design_bounds` result's `remaining`); may be empty; ids unique and present in `candidates` |
| `survival_basis` | yes | nonempty references to the analysis or decision that left these survivors |
| `variables` | yes | nonempty array of `variable` objects: the represented dimensions to vary |
| `context` | no | `{cohort, phase, arm}` entry context, as in `design_bounds`; default open |
| `signs` | no | nonempty unique subset of `accepted`, `rejected`; default both |
| `bound` | no | integer 1..65536 per participant decision; default 4096 |
| `limits` | no | object; any of the keys below |

`variable`: `{id, subject, predicate, time, domain}`. `subject`/`predicate` are tagged model objects; `time` is a
tagged `TemporalScope` or null. They must equal the survivors' literals exactly (canonical subject and predicate;
time compared with certainty/evidence stripped, as entailment keys it; unit as written). A declared variable that
matches no survivor literal is reported as `variable_unrepresented:<id>`, a translation problem, never as
"no separator".

`domain` (closed by kind):

| kind | fields | cells |
|---|---|---|
| `boolean` | — | holds; does not hold |
| `enum` | `members` (nonempty unique strings), `open` (bool) | each declared member plus any member a survivor names; if `open`, one "none of these" cell |
| `integer` | `unit`, `minimum`, `maximum` (integers, at most 64 values) | each integer value; no fractional patients |
| `continuous` | `unit`, `minimum`/`maximum` (number or null, inclusive limits), `cut_points` (numbers) | exact points at every survivor threshold, cut point and declared limit, open intervals between them, and unbounded tails only where no limit is declared |

Other value kinds (`enum_set`, `entity_ref`, `definition_ref`, `unresolved`) are refused by name
(`evidence_requests:variable:unsupported_domain`). Two variables with the same entailment key are refused
(`evidence_requests:variables:duplicate_key`).

`limits` (default / hard maximum): `max_profile_size` 3 / 6; `max_profiles` 2048 / 20000; `max_decisions`
5000 / 50000; `max_requests_per_pair` 3 / 20; `max_requests` 30 / 200; `max_bytes` 65536 / 262144.
Further structural maxima: 32 survivors, 12 variables, 64 cells per variable. Exceeding a hard maximum is a
named refusal; exhausting a budget during search is a named incomplete outcome.

## Search

Profiles are partial assignments of cells to a subset of the declared variables, enumerated by size
(1..`max_profile_size`), then variable order, then cell order. Unspecified variables stay unspecified. A
size-0 profile is not representable as a participant proposition; the "rejected, profile unknown" case belongs
to exception evidence and is recorded as `empty_profile_not_representable` in coverage.

Each (profile, sign, survivor) is evaluated once with `entail.eligibility_witness` and classified with
`design_bounds.witness_verdict` under hypothetically satisfied witness support. A row therefore states what the
existing `design_bounds` consumer would conclude if that observation were supplied with a resolved, accepted
bridge and a count above its exception allowance. Survivors are checked for inconsistency first
(`survivor_inconsistent:<id>`, an input conflict, excluded from separation).

A pair (A, B) is separated by (P, sign) when the verdict eliminates exactly one of them and the other is
`not_ruled_out`. A separator is suppressed as non-minimal only when an already-found separator for the same
pair, sign and eliminated side uses a subset of its literals.

## Result

| Field | Contract |
|---|---|
| `basis`, `study_ref`, `premises` | as other operations; `premises` echoes the request |
| `family` | `conflict` (no consistent survivor), `single_survivor` (no within-family separation needed), `searched` |
| `survivors` | consistent survivor ids searched; `inconsistent` lists excluded ids |
| `search` | `{state: complete/incomplete, profiles_examined, decisions, causes}` |
| `output` | `{state: complete/truncated, found, returned, omitted, causes}`; `omitted` counts only found rows |
| `pairs` | per unordered survivor pair: `{candidates, outcome, requests, found, causes}` with outcome `separated`, `no_separator`, `not_separated_in_declared_variables` or `search_incomplete` |
| `requests` | rows below, least-specified first, deterministic ties |
| `representation` | `unrepresented_variables`, `unsearched_constraints`, `coverage` notes |
| `limits` | text: hypothetical requests only; declared family only; no evidence availability claimed |

Request row (structurally unable to pass as an observation: no `count`, `bridge`, `basis` or `status` field):

`{id, kind: "hypothetical_evidence_request", observed: false, sign, profile, profile_size, specified,
cells, eliminates, accommodates, undecided, checks, required_premises, seek, conditional_status, scope}`

- `checks`: one per survivor: `{candidate, verdict, decision}` with the complete returned decision.
- `required_premises`: by sign. Accepted: attributed participation, an accepted and resolved eligibility bridge,
  count above the exception allowance; elimination holds even if the eliminated candidate has further
  unrepresented criteria. Rejected: eligibility-attributed rejection, an accepted and resolved bridge, count
  above the misattribution allowance, and `complete_candidate_eligibility:<id>` for each eliminated candidate.
- `seek`: accepted → participation records bound to eligibility at entry; rejected → eligibility-attributed
  screening or adjudication records. No claim that such records exist; corpus silence is never a negative witness.
- `conditional_status`: weakest status of the eliminating decisions; the supplied observation's own standing
  would further bound it.

## Codes

Outcomes: `conflict`, `single_survivor`, `searched`, `separated`, `no_separator`,
`not_separated_in_declared_variables`, `search_incomplete`, `complete`, `incomplete`, `truncated`.
Causes: `resource_bound:profiles`, `resource_bound:decisions`, `profile_size_limit`,
`witness_unresolved:<candidate>` (with the decision's own blockers), `survivor_inconsistent:<id>`,
`variable_unrepresented:<id>`, `unsearched_constraints`, `output_limit:requests`, `output_limit:bytes`,
`output_limit:per_pair`.
Refusals: `evidence_requests:<where>:<problem>` and `resource_bound:evidence_requests:<what>`.

## Lead-owned integration needed

1. `service`: dispatch `"evidence_requests": evidence_requests.evaluate`; add `evidence_requests_guide.INPUTS`
   to `INPUTS` and a focused `describe` view.
2. `result_semantics`: an adapter; every request row is an open evidence question (never settled); family
   `conflict` is a conflict; `search_incomplete` with `resource_bound` is not_computed.
3. `guide.py` answer guide entries for the outcome codes above.
4. Metadata vocabulary test: classify the cause codes above.

## Contract decisions after the independent test pass

1. `undecided` in a request row is a list of candidate ids, like `eliminates` and `accommodates`; blockers stay
   in the complete `checks` decisions.
2. `inconsistent` is a top-level list of candidate ids; `input_conflicts` carries the
   `survivor_inconsistent:<id>` codes. These are input conflicts, not search limits, so they never mark the
   search incomplete.
3. `representation.coverage` holds bare codes (`empty_profile_not_representable`, `variable_unrepresented:<id>`);
   their explanations live in the discovery result guide.
4. Each row's `scope` records `study_ref`, `context` and the `bound` used, so a replay through `design_bounds`
   uses the same per-decision limit. A higher bound can only turn an undecided check into a decided one; it
   never reverses a decided elimination or accommodation.
5. Refusal codes keep the house style `evidence_requests:<where>:<problem>` with a dotted `where`
   (for example `evidence_requests:domain.integer:reversed_limits`), as `exception_bounds` already does.
6. The decision budget is checked per profile for all requested signs together, so a profile is never
   half-evaluated; consistency prechecks count toward `max_decisions`.
