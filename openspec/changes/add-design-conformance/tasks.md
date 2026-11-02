# Tasks: add-design-conformance

## 0. Before

- [ ] 0.1 refine-landscape-record's conformance commits merged (the three shortcuts removed, the treats-the-cancer
      gate removed, indication gating per add-scoped-reasoning Decision 4), so the inventory starts from code that
      conforms or names its legacy readings.

## 1. The inventory (enforced by the gate)

- [ ] 1.1 `TrialLedger/conformance.py`: READING_MODULES, LEXICAL (every lexical collection classified recognition
      or decision, each decision with authorized_by and eliminates), LEGACY (decisions awaiting the compiler, each
      with the task that replaces it) and LEGACY_MAX.
- [ ] 1.2 `tests/test_conformance.py`: the AST walk; undeclared collection, stale entry, uncited decision, citation
      to no decision, decision with no independent source, LEGACY above LEGACY_MAX, an unlisted module assigning a
      reading — each fails; both signs tested with planted modules.
- [ ] 1.3 The workbook marks a reading that rests on a LEGACY decision as a legacy reading (Read me and the
      Readings sheet), so a reviewer sees which readings the designed mechanism does not yet produce.

## 2. The trace (enforced at push)

- [ ] 2.1 `openspec/changes/add-design-conformance/trace-template.md` with the required sections and the closed
      review verdicts.
- [ ] 2.2 `scripts/push_checks.py`: commits touching a reading module's code (AST without comments and docstrings)
      need `Trace: <path>` to a well-formed trace in the commit's tree with a review verdict other than "does not
      conform"; refusals named; pure decision converged; both signs tested, including a docstring-only change
      (no trace needed) and a code change hidden in a large commit (trace needed).
- [ ] 2.3 The traces of refine-landscape-record's conformance commits written retroactively with Codex's review,
      so the first push under the check passes honestly.

## 2b. What makes it real (design §7)

- [ ] 2.4 GitHub Actions workflow running the gate, the conformance test and the trace check on pushes and pull
      requests to main; branch protection (required status check, no force-push, no direct push to main) set by
      the founder, who alone administers it.
- [ ] 2.5 CODEOWNERS: the conformance inputs (conformance.py, its test, the push check, the trace template)
      require the founder's review.
- [ ] 2.6 Runtime data resources of reading modules inventoried, versioned and hashed; an undeclared load fails.
- [ ] 2.7 The executable counterexamples of design §7.4 at the real entry point.
- [ ] 2.8 LEGACY frozen by identity and behaviour (each legacy decision's inputs and outputs pinned).

## 3. The rules where builders read them

- [ ] 3.1 DEVELOPING.md "Reading logic: the design is the contract"; AGENTS.md one pointer.
- [ ] 3.2 `brief-rules.md`: the text every build agent's brief carries verbatim.

## 4. The MVP path

- [ ] 4.1 `openspec/MVP_PATH.md`: every remaining change in dependency order with entry conditions, acceptance
      criteria, claims allowed and forbidden, and binding design decisions; DEVELOPING.md points to it.
- [ ] 4.2 Each later change ticks its step in MVP_PATH.md in the commit that completes it (checked by a test that
      every change named in MVP_PATH exists under openspec/changes or archive, and every done step's change has
      all tasks ticked).
