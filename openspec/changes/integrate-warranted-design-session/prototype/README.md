# Session input prototype before schema freeze

This is a finite input-design experiment, **not** an implemented `design_session` operation or a proposed
replacement clinical language. The sources are the retained real IPASS and ARCHER 1050 snapshots from the
planning investigation. Clinical readings, working assumptions and actual source facts remain separate.
No clinician has confirmed these readings or made the open design choices recorded here.

## Concrete input and expansion

`session-input.json` contains two exact parsed-study snapshots once, five scoped question definitions,
four existing source-analysis payloads, a hypothetical witness request and its two exception-cap variants.
The complete source-bound baseline and schedule readings are retained; their bodies, scopes, local support,
status and resolution are not rewritten. A question is keyed by its source as well as its identity; two
studies asking the same age question are not made one study.

`revision.json` changes only the active sensitivity variant from cap 48 to cap 49, naming the parent
snapshot's canonical digest. This is a change to an investigation assumption, not the user's clinical
choice. `clinical_choices` is empty. The two open new-trial questions are explicitly assistant-authored
handoff labels, not computed dispositions or an exhaustive protocol decision list.

The finite adapter in `replay.py` restores only known slots: source snapshot/digest, scoped query references
and the exception bridge's maximum/basis. It is not a generic executable template or arbitrary JSON-edit
engine. Each legacy child request must equal its retained original as a complete parsed JSON object before
execution. The new age-corpus child must equal the separately written explicit reference under
`reference/`. The complete actual expanded child requests/results are under `runs/`.

Run from the repository's environment:

```bash
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label session-prototype-replay -- \
  uv run python openspec/changes/integrate-warranted-design-session/prototype/replay.py \
  --output /tmp/trialledger-prototype-fresh-replay
```

## Observed public behavior

The retained `replay-receipt.json` records twelve historical public CLI executions: six analyses for each revision. Each revision
fully reruns the four source analyses, its selected sensitivity request and the derived age-corpus request.
The operation names remain `source_assertions`, `design_bounds` and `corpus`; no unbuilt API was called.

- All ten executed legacy child requests exactly equal their original requests. Every original result
  field is preserved. The comparison permits additional result metadata, so this is not a claim of
  byte-identical output after later additive changes.
- The age projection returns two stating records out of two in both revisions. It reads the actual fixed
  direct-age assertions, verifies their rule/version/origin reference and exact supported shape, copies
  their standing into the one age feature and derives the structural `typed` flag from the prepared
  eligibility elements. Trial-wide standing remains proposed; no other criterion is represented.
- With maximum exceptions 48, the remaining candidate IDs are `requires_never` and `unrestricted`.
  With maximum 49, `no_joint` also remains. The common query stays `UNDETERMINED` in both cases because
  the unrestricted candidate is retained.
- The input snapshot is unchanged by each replay. Fixed age results, source-bound proposed overlap and
  rival proposed schedule readings are rerun independently of the cap change.

The source-bound overlap reading remains proposed. The separate sensitivity request retains its existing
explicitly hypothetical interpolated support. Factoring source identity must not merge those environments
or make their standings agree. This prototype has not admitted either bridge as a real historical fact.

## Authoring inventory

`burden-inventory.json` defines the categories and computes the counts. They describe this exemplar's
representation, not Shannon information, general translation effort or semantic completeness.

| Declaration | Separate requests | Prototype caller representation |
|---|---:|---:|
| Source snapshot occurrences in the four source analyses | 4 | 2 snapshots, referenced 4 times |
| Scoped question object occurrences | 7 | 5 definitions, referenced 7 times |
| Listed independent reading/candidate/bridge/sensitivity definitions | 11 | 11, unchanged |
| Known age-feature standing declarations in explicit corpus reference | 2 | 0; copied from verified direct-age outputs |
| Corpus structural `typed` declarations in explicit reference | 2 | 0; derived from prepared elements |

The prototype adds eight categories of administration: prototype identity/version/revision, analysis IDs,
source refs, question refs, active sensitivity variant, projection member refs, parent digest and open
question labels. It also makes two previously implicit new-trial handoff questions explicit. The original
separate request files did not encode those decision-list questions; a working brief may already hold them.

The experiment therefore demonstrates removal of four independent caller declarations for the narrow
age projection and sharing of repeated source/query objects. It does **not** demonstrate that a general
session reduces total authoring effort: it retains all eleven listed material semantic definitions and adds
references that an assistant can mistype. No conclusion about splitting or keeping the session change is
made by this prototype; that choice belongs to the lead and the user.

## Integration decision and current replay

Retain the bounded session integration. The material reduction is the removal of independently supplied
age-feature standing and structural typing declarations, and the ability to check source origin and
revision dependencies once. This supports a narrower engineering claim than reducing total authoring:
the clinical interpretations still have to be supplied and accepted, while consequential admission
declarations can be derived and checked. The administration remains explicit and is tested by strict
schema and replay checks; it is not treated as a reduction in clinical meaning.

Current replay compares against the complete retained expanded request/result pairs in `runs/`, rather
than requiring the removed loose planning capture. It requires a new output directory outside this
prototype and refuses to overwrite the historical references. The archived original capture remains
restorable under `evidence/registry-run/RESTORE.md`; the prototype does not need another source copy.

## Questions not settled by the prototype

- What historical eligibility-exception ceiling, if any, is supported? The chosen 48/49 variants are
  sensitivity assumptions, not answers to that empirical question.
- Which participant-count, common-population and entry-time bindings can be established from source rules,
  and which remain clinical interpretations? Source location alone supplies none of those relations.
- Which schedule anchoring reading should govern the new trial? Both proposed comparator readings remain.
- Which comparator restrictions should the new trial adopt, and is any WHO/ECOG relation warranted?
  Neither relation nor adoption is introduced here.
- How should the eventual session represent dependencies without asking the assistant to duplicate the
  existing assertion/signal objects? The finite exemplar adapter is not a general schema decision.

This prototype has no new production module, no MCP verification, no Detective pin and no full-suite claim.
It demonstrates exact request expansion and current public CLI behavior for the stated finite packet.
