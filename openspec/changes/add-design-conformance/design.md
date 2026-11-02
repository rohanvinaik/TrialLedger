# Design: add-design-conformance

## 1. What counts as a reading module

The modules whose code assigns or projects meaning read from a registry record: `TrialLedger/banks.py`,
`criteria.py`, `coherence.py`, `universes.py`, `reading.py`, `eligibility.py`, `modality.py`, `landscape.py`
(its reading functions), `predicates.py`, `assertions.py`, `entail.py`, `expectations.py`, `profile.py`,
`semantics/` and any module a later change adds to this list. The list is data in `TrialLedger/conformance.py`
(`READING_MODULES`), and a test fails when a module under `TrialLedger/` imports one of them and assigns a
reading without being listed itself (a reading assigned elsewhere is the failure this change exists to stop).

## 2. The inventory and its test

`conformance.LEXICAL` holds one entry per lexical collection in a reading module: its module and name, its kind
(`recognition` or `decision`), what it recognizes or decides, and, for a decision, `authorized_by` (a design
decision id, e.g. "add-scoped-assertions D7", "add-scoped-reasoning Decision 4") and `eliminates` (the
alternatives it takes part in eliminating and the independent evidence it is combined with). A collection is
lexical when it is a module-level or function-level constant built from string literals (a regex from
`re.compile` or a pattern string; a tuple, list, set, frozenset or dict whose keys or members are string literals
of words or phrases), detected by walking the module's AST. An inline test is lexical too and is inventoried the same way, keyed by its function
and the literal: a comparison, membership test or string method (`==`, `!=`, `in`, `not in`, `startswith`,
`endswith`, `find`, `index`, `count`, `replace`, `split` on a literal separator that is a word) against a string
literal that holds a letter, and any `re` call whose pattern is a literal; literals that are registry field
names, enum codes the API defines (declared in `contract.DISPLAY`'s enums) or JSON keys of the record are
structural and exempt by a declared list, which the test also checks is only structural (each exempt literal
must occur in the API metadata or the contract). The test (`tests/test_conformance.py`):
- every lexical collection in a reading module has an entry, and every entry names a collection that exists;
- a `decision` entry cites a decision id present in a design document of an open or archived change (the ids are
  read from the documents' headings and numbered decisions, so a citation to nothing fails);
- a `decision` entry names its warrant, one of a closed set: (a) a structured registry field states the value;
  (b) an unambiguous grammatical construction, two-sign tested and confirmed on data it was not written on,
  establishes a scoped assertion (add-scoped-assertions A3); (c) an ontology relation supports a declared
  entailment; (d) several observations of distinct provenance jointly eliminate the alternatives of an ambiguous
  reading (it names them in `eliminates`); (e) a default supplies a conclusion that is shown as interpolated, with
  its defeaters. A word match alone is none of these, and "two sources agree" is not a warrant by itself: (d)
  requires that the observations eliminate alternatives, not that they coincide;
- recognition entries are free of decision words in their purpose ("decides", "assigns", "is") — a wording check
  only, the substance being the review of §4.

The inventory starts from the code as it stands after refine-landscape-record's conformance commits: each
existing collection is classified, and each existing `decision` either cites its authority or is listed in
`conformance.LEGACY` with the compiler task that replaces it (add-scoped-assertions 2.x, add-scoped-reasoning 5),
shown in the workbook as a legacy reading. LEGACY may only shrink: a test pins its size to a declared maximum
that each change may lower and none may raise.

## 3. The trace requirement at push

`scripts/push_checks.py` gains a check over the commits a push sends: for each commit whose diff touches a file in
`READING_MODULES` (code, not tests or docstrings alone, judged by comparing the module's AST with comments and
docstrings stripped before and after), the commit message must contain a line `Trace: <path>`; the path must
exist in that commit's tree under `openspec/changes/*/traces/`; the file must hold the sections of the trace
template (`openspec/changes/add-design-conformance/trace-template.md`) and a `Review:` section with a verdict
from the closed set {conforms, conforms with named limits, does not conform} and the reviewer named. The trace
records the content hash of each reading module and data resource the review read (`Reviewed:` lines, path and
hash); the check refuses the commit when any reading module or resource the commit changes has a hash in the
commit's tree different from the one reviewed, so a valid-looking trace cannot be attached to code it did not
review. The conformance inputs themselves (`TrialLedger/conformance.py`, its test, the push check, the trace
template) count as reading modules for this requirement. A missing or malformed trace, a stale review, or a
verdict of "does not conform" refuses the push with the reason. The check is pure over
the diff and the tree (a function of literal inputs, two-sign tested and converged).

## 4. The review

The reviewer reads the trace and the diff against docs/THEORY_OF_THE_CASE.md Part III and IV and the cited design
decisions, and answers: does any decision in the change assign meaning from one lexical observation; does it count
the same evidence twice; does it turn a default into a known value; does it apply a domain rule outside its declared
indications; is anything the sources do not decide shown unresolved. Codex model-only (SquishOS consultation
protocol) is the default reviewer; its verdict and the lead's resolution of any disagreement go in the trace.

## 5. The brief template and the rules

`DEVELOPING.md` gains a section "Reading logic: the design is the contract" with the principle, the inventory, the
trace and the review; every build agent's brief includes it verbatim (the template lives at
`openspec/changes/add-design-conformance/brief-rules.md`). AGENTS.md gains one sentence pointing developers there.

## 6. The MVP path

`openspec/MVP_PATH.md` lists, in dependency order, every change from now to a complete layer one and layer two:
its purpose, entry conditions (which changes and tasks must be done), acceptance criteria (what is run, measured
and read, by whom), what it may claim and what it may not, and the design decisions it is bound by. It is updated
by the change that completes a step, in the same commit that ticks the step's last task.

## 7. What the harness guarantees, bounded (an adversarial review, Codex model-only, 2026-11-02)

Applied to the four shortcuts that prompted this change, the inventory and the trace as first specified catch an
unregistered collection and force a reviewed record; they do not stop a mislabelled "recognition" entry, a
decision in an unlisted module or loaded from a data file, a decision over codes or IDs with no word in it (the
ATC gate), a rubber-stamp review, an edit to the conformance inputs themselves, or a local hook skipped. The
additions that make the guarantee real:

1. **Enforcement off the builder's machine, within the founder's workflow.** The founder works by direct push to
   main (ruled 2026-11-02); branch protection and required pull requests are not used. A GitHub Actions workflow
   runs the gate, the conformance test and the trace check on every push to main, so a push made with the local
   hook skipped is still checked, and a failure is visible on the commit and notified. The bound: a bad push can
   land; it cannot land unseen. The local push gate also refuses any push while the latest GitHub run on main for
   these checks has failed (when the run's state can be read; when it cannot, it says so and does not refuse), so
   a failure is fixed before more work lands on it.
2. **The conformance inputs are protected by the same trace.** Changes to `TrialLedger/conformance.py`, its
   exemptions, its test, the push check and the trace template need a reviewed trace like any reading change
   (§3), and a trace never authorizes a change to the inputs that judge it in the same commit. LEGACY is frozen by
   identity and by behaviour (each legacy decision's name, its literal set's hash, and its pinned inputs and
   outputs), not by count alone: replacing one legacy shortcut with another at the same count fails.
3. **Data is inventoried like code.** Any vocabulary, table or resource a reading module loads at run time (JSON,
   YAML, CSV, a generated file) is declared, versioned and hashed in the inventory; an undeclared runtime load in a
   reading module fails the test.
4. **Executable counterexamples.** The four failures, and Codex's perturbations (the same evidence repeated is not
   counted twice; renaming an irrelevant name changes no reading; removing a required independent source yields
   unresolved; keeping ATC membership while changing the indication never promotes a default to known; a nausea
   trial in chemotherapy patients is not "outside oncology"; a placebo arm with two candidates stays unresolved),
   run at the real entry point (`trialledger landscape` over fixture registry pages) and assert the required
   unresolved or default outcome.
5. **Reviews bind to the computation.** The review reads the code, the data and the trace together; "conforms
   with named limits" may only name coverage limits (what stays unresolved), never a waiver of the principle.
6. **The real boundary is mediation.** Every accepted reading passing through a checked derivation (evidence
   identities, spans, candidates, bindings, eliminations, indication scope, status), built only by registered
   decision operations, is add-scoped-assertions' compiler and consumer contracts (its groups 2 and 6). Until then
   this change gives detection and accountability, and the claim it makes is bounded so: no unregistered lexical
   or data-driven decision, no reading change without a reviewed trace, and the four known shortcut kinds pinned
   by counterexamples, checked on every push to main.

## 8. What the compiler must carry, so independence is computed, not declared

The trace's independence section is prose; the computation must hold the same facts. The first structural slice
of add-scoped-assertions (MVP_PATH step 3) therefore carries, for every observation: its identity, its source
location (field and span), its derivation ancestry (a derived index term, such as the registry's condition MeSH
derived from the trial's own words, descends from those words and is not independent of them; differently named
API fields are not independent for that reason alone), its scope, and the constraint it supplies. The same
evidence is never counted twice toward a reading; one piece of evidence may of course support several different
readings. Consumers accept readings only as checked derivations (premises and evidence references,
bindings and scope, the statuses the consumer accepts, and named failures when the proof does not check), and a
legacy reading has its own type, which a consumer requiring a structurally established assertion refuses; the
workbook label (task 1.3) shows it, the type enforces it.
