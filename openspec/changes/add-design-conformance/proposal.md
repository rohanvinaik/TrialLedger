# Proposal: the design is enforced by the gate, not by the founder's vigilance

## Why

On 2026-11-02, during refine-landscape-record, three "quick fixes" were approved and merged that contradict the
project's own theory and design: a word list deciding that a trial is outside oncology, an intervention judged a
placebo from its name, and a refined cue-word rule deciding a criterion's role. A fourth, a "treats the cancer"
gate decided by drug-class membership, turned a designed default (add-scoped-reasoning Decision 5) into a known
fact. Each passed review because reviews checked local correctness, not the mechanism. The founder's thesis
(docs/THEORY_OF_THE_CASE.md Part III 6-7 and the corrections accepted on 2026-10-31; add-scoped-assertions
Decisions 1, 6-8 and A3; add-scoped-reasoning Decisions 3-5 and 11) was in the repository throughout. The founder,
paraphrased: they can specify the thesis but cannot police every change; a quick fix that violates the explicit
contract defeats the point of the project.

The principle every reading must obey: recognition (a word, a unit, a gene symbol) is legitimate encoding that
produces typed evidence with its span; meaning is assigned only by eliminating alternatives across independent
evidence, the same evidence never counted twice; where the sources do not decide, the value is unresolved and shown so;
domain rules apply only within the indications they declare; a default is interpolated, never known.

## What changes

1. **A lexical-decision inventory the gate enforces.** Every regular expression and every literal word or phrase
   collection in the reading modules, and every data resource they load, is declared in a conformance table
   (`TrialLedger/conformance.py`) as `recognition` (it produces evidence with a span and decides nothing) or
   `decision` (it contributes to assigning meaning), each decision entry naming its warrant from a closed set
   (design §2). An AST test fails the gate on any undeclared collection or resource, any decision without a
   warrant, and any citation to a decision that does not exist.
2. **A trace for every change to reading logic, enforced at push.** A commit that changes a reading module must
   name, in its message, a trace file in the repository (`openspec/changes/<change>/traces/<name>.md`) present in
   that commit's tree, holding: the observations and what each measures; which share a source; the candidate
   interpretations; the binding relations; the eliminations with their warrants; what stays unresolved; the
   perturbations (reword, negate, change the target, remove a source) and their consequences without a new phrase
   rule. The push gate refuses a commit that changes a reading module without one.
3. **An independent design review recorded beside the trace.** Every trace carries an independent reading of the
   change against the theory and the design (Codex, model-only, by the SquishOS consultation protocol, or another
   reviewer), with its verdict (conforms, conforms with named limits, does not conform) and the resolution of any
   disagreement, and the hashes of the code and data it reviewed. The push gate refuses a trace without one, or
   one reviewed against other code.
3b. **The same checks on GitHub on every push to main.** The founder keeps pushing directly to main; the checks
   run there too, so a skipped local hook is caught and reported, and the next push waits until it is fixed.
4. **Standing rules where every builder reads them.** DEVELOPING.md (the rule, the inventory, the trace and review
   requirements), AGENTS.md (one pointer for developers), and the brief template every build agent receives.
5. **The path to the MVP, persisted.** `openspec/MVP_PATH.md`: every remaining change toward layer one and layer
   two in dependency order, each with its entry conditions, acceptance criteria, what it may claim, and its
   design obligations; DEVELOPING.md points to it.

## Out of scope

Judging whether a rule's reading is clinically right (that is each change's own acceptance and the audit of
add-targeted-questions); building the scoped-assertions compiler (add-scoped-assertions 2.x).
