# Parallel build contract

Read `HANDOFF.md`, the theory, design, contracts and verification before accepting a packet. This plan authorizes no current worker launch by itself; the implementation coordinator starts the apply workflow when instructed. The user intends to hand this plan to another agent. No worker gets to reinterpret that intent or decide what is clinically acceptable.

## P1. Authority and shared workspace

- Work on main in the shared checkout, no branches/worktrees. One coordinator owns integrations and coherent commits. Workers do not commit/push or clean other files. Observe later edits and the current status before beginning; never reset/stash/overwrite someone else's changes.
- The coordinator supplies intent, clinical question, frozen inputs/outputs, exact owned paths and counterexamples. Worker replies contain facts: code changed, tested cases, consumed interfaces, hashes, tool output and unresolved issues. A worker's interpretation is not a new clinical premise or scope decision.
- Use at most the available worker slots and the machine's actual memory budget. Start with one coordinator plus three workers if supported; queue other roles. No one starts a private Serena/Pyright server to multiply memory use. The coordinator supplies fresh reference traces; workers orient through a read-only map/AST and whole units.
- Temporary processes follow `owned-run`. Do not install dependencies or run global convergence/pins in parallel with another worker. A tool being configured somewhere does not prove it is available in this environment.

## P2. Before releasing any worker

The coordinator completes tasks 1.1–1.6, including an interface packet committed as a coherent planning/fixture change under implementation authorization:

1. Current baseline commit/status and the protected v1 public examples.
2. Exact JSON Schema and canonical valid/invalid fixtures for C2–C8. Include the full reused reference, proposition, domain, origin and context shapes; do not tell builders to guess them from this prose. These are mechanical instantiations of this plan, not permission to redesign it.
3. Public new-code/result map, named projection registry and expected leaf/aggregate findings for the TIM-1, END-3, POL-1, STA-1 and OPT-2 cases.
4. Import graph: independent mathematical modules never import session, transport, source acquisition or presentation. Object validation never runs a solver. Projectors call owners; they do not copy their mathematics. The pure clinical view reads canonical results; it never supplies a premise or recomputes a clinical rule.
5. Budget reservation formulas with units and boundary cases. Worker-specific allowed knobs cannot raise hard limits or silently charge a different work category.
6. Fresh symbolic producer/consumer trace and explicit ownership below, including the two exact-query guards and the clinical-output consumers.

If fixture construction reveals a semantic conflict, pause the affected packet and report the exact input/outcome mismatch. Resolve a clerical schema inconsistency in the plan coherently; changes to clinical meaning, epistemic standing, compatibility or public scope require returning to Rohan. No worker silently expands their contract.

## P3. Disjoint worker packets

Paths are proposed new files checked against current status before assignment. If occupied, the coordinator assigns a nonconflicting location and records it; workers may not overwrite them. Test files listed here are authored tests; generated proof files are owned separately by the proof driver.

| Packet | Sole writable production/test paths | Frozen interface and deliverable | Dependencies |
|---|---|---|---|
| A: objects | `TrialLedger/layer2/protocol_objects.py`, `tests/test_protocol_objects.py` | C2/C3 pure validator/normalizer, detached canonical object index/dependency graph; no solver calls | Frozen schema packet |
| B: schedules | `TrialLedger/layer2/protocol_schedule.py`, `tests/test_protocol_schedule.py` | Existing evaluate/check signal contract for schedule_coverage; exact rational union operations, independent endpoint-cell oracle | C4/C5 packet |
| C: policies | `TrialLedger/layer2/protocol_policies.py`, `tests/test_protocol_policies.py` | Existing evaluate/check contract for finite_policy; finite-table reuse and independent graph oracle | C4/C6 packet |
| D: efficacy | `TrialLedger/layer2/protocol_statistics.py`, `tests/test_protocol_statistics.py` | Existing evaluate/check contract for binomial_design; exact tails and independent vector-enumeration oracle | C4/C7 packet |
| E: projection assembly | `TrialLedger/layer2/protocol_projections.py`, `tests/test_protocol_projections.py` | Pure named adapters producing existing child requests plus C4 projection receipts; endpoint/estimand/schedule bindings | A contract frozen; coordinator approves each called owner |
| F: clinical view | `TrialLedger/layer2/protocol_view.py`, `tests/test_protocol_view.py` | Pure canonical-result -> clinical rows/section coverage; no solvers/files/prose interpretation | Frozen result fixtures from B–E and v2 decisions |

Scheduling: B/C/D can be built independently once interfaces are frozen. A/E can be queued as slots permit; E may start against the exact frozen A interface, not a worker's evolving return dict. F starts only after representative canonical result fixtures include conditional/limited/refuted outcomes. Final import cycle and runtime consumption checks are the coordinator's responsibility.

**Coordinator-only shared paths:** `session_state.py`, `design_session.py`, `session_projections.py`, `request_preparation.py`, `service.py`, `signals.py`, `definition_checks.py`, `solver_work.py`, `result_semantics.py`, `clinical_answers.py`, existing decision/analysis review and explanation modules, artifact/delivery/revision/export modules, capabilities/discovery/CLI/MCP schemas, all existing shared tests, import contracts, acceptance inventory, README/AGENTS/SKILL/DEVELOPING and OpenSpec tasks/spec syncing. A worker discovering a needed shared edit reports its exact contract need; it does not make the edit.

The coordinator owns a small `protocol_decisions.py` if needed for C8, with one decision responsibility per primitive; it must not become a second session engine. Final module/helper names can change before assignment if behavior/ownership/import direction stay fixed. Public schema, claim semantics and limits cannot drift between packets.

## P4. Packet sent to every builder

Use this complete assignment form (fill concrete values before sending):

> Implement packet [ID] on current main [commit]. Read the linked complete contracts and supplied source-owner units. Clinical question: [one concrete case]. Your writable paths: [exact files only]. Import interface: [versioned schema/fixture hashes]. Must do: [positive obligations]. Must never do: [paired negative obligations]. Production consumers and scope: [coordinator trace]. Limits: [work/representation/output caps]. You may implement and run your authored tests; do not edit shared files, theory, source evidence, proof state, dependency declarations or commit/push. If a boundary is insufficient, return the exact failing case and requested interface change; continue independent work only. Report facts and limitations; do not mark whole-workflow tasks complete. Hand off using P5. Final Detective is scheduled by the coordinator after integration freeze.

No delegation packet can be just “build safety” or “make this medically correct.” Every packet names the information channel, its consumers and its epistemic stop line.

## P5. Worker handoff

Return a packet with: assigned ID and interface version; every changed path and hash; exported signatures; direct-call positive/MUST-NOT tests and actual results; independent oracle and finite domain; malformed/boundary behavior; named codes and support handling; current tool/proof status (including not run); suggested shared edits as factual requirements; unresolved cases. List any file changed outside scope immediately. Do not describe local unit success as CLI/MCP or clinical validation.

The coordinator checks the actual files, hash basis, input contracts and both producer/consumer paths, then integrates. Worker facts are not accepted solely because the handoff says passed. Do not mark checked tasks from a worker narrative without its current evidence.

## P6. Integration and proof lock

Integrate one coherent vertical slice at a time: objects/schedules/dependencies, then finite policy, then exact efficacy, then protocol alternatives/public lifecycle/delivery. Existing independent computations remain available while subsequent slices are incomplete. Run the V6 rotating walkthrough after each substantial slice and before declaring it done. New counterexamples become intent tests plus trace corrections, not only prose notes.

Before final pins: stop all writes to target production files, imported semantic dependencies and relevant authored/generated tests; record the freeze manifest; appoint one proof driver. It follows current literal Detective output and alone writes generated suites/caches/receipts. No simultaneous global convergence or candidate rewrite by another worker. Hash again after every target's prescribed walk. Resume coding only after invalidating affected proof receipts and scheduling their rerun.

Workers may continue on genuinely disjoint unaffected work only if the proof basis has no dependency on it. If unsure, serialize. A proof limitation is handed to Rohan under V4; it does not authorize another agent to waive the task. Finish with current full verification, coherent main commits and push only under the user's implementation authorization and applicable gates.
