# For agents (and humans) arriving fresh — read before proposing anything

**TrialLedger is a classical-AI project. It is not ML.** It may look like it
is "missing the model." It is not — that is the thesis. Before proposing ANY architecture,
approach, or "improvement":

1. Read `docs/THEORY_OF_THE_CASE.md` (this folder) — the design and why classical AI wins
   here. If it is still a stub, ask the founder to fill it (or fill it WITH them) before
   proposing architecture.
2. **Restate the mechanism in your own words** and have the founder confirm it. A
   correct-sounding paraphrase is not the test; the data-flow is.
3. Never reframe the symbolic / deterministic / vector-symbolic / data-geometry /
   story-understanding design as ML. Never propose a model, CNN, transformer, ensemble, or
   classifier as the default. Iterate the *encoder / data geometry / signal*, never model
   capacity.

**Four different things, never collapsed:**
- **AI** — the genus (reasoning, representation, symbolic and vector-symbolic computation).
- **ML** — one narrow, **avoidable** species (gradient-fit models).
- **Classical AI** — symbolic / vector-symbolic / deterministic. Usually the architecture here.
- **Story-understanding intelligence** — Regenesis (the founder's Python port of Winston's
  Genesis; in the MCP list as `mcp__Regenesis__*`). A distinct thing again.

**Know your own bias (this is why the gate exists).** You — and LLMs generally — are
disproportionately drawn to ML and reflexively skeptical of classical AI. It feels like
domain knowledge; it is a prior overriding what the founder specified. The tells: "this
is really ML, just small/downstream"; "you'll need a model for the hard part"; "the
deterministic part is elegant but it caps out"; using "no algorithm beats its data" to
smuggle a model back in.

**The one escape hatch:** the founder may deliberately place a small, bounded model at some
tail of a pipeline (a registration/normalization utility; a <1% candidate-selection
residual). That is the founder's explicit call — never your default, never "the
architecture," never the win path. When they ask, comply; never volunteer it.

Canonical, fully-worked example of this apparatus:
`~/Projects/Kaggle_Killer/competitions/RSNA_Knee/`. Global law: `~/Projects/SquishOS/ops/agents/global.md`
("AI is not ML — the classical-AI default"; the scaffold's original pointer, `~/.claude/CLAUDE.md`, was
retired in the 2026-10-20 purge).

---

# TrialLedger — what an agent working here must keep true

TrialLedger pulls ClinicalTrials.gov records through the API in `spec/ctg-oas-v2.yaml` and writes
`studies.json` (records as sent, plus provenance) and `studies.csv` (the API's own CSV). That ingestion
layer is built. The reasoning layers are designed in `docs/THEORY_OF_THE_CASE.md` and specified, one
change at a time, under `openspec/changes/`. The README explains the system to its clinical readers.

## The rule this project exists for

No code here interprets, summarises or rewrites study content, and no agent does either. The founder's
first prompt names the failure this project rejects: handing trial pages to a chatbot to "parse". Every
value a person reads traces to a named field of the record, or to a named rule over such fields; what
cannot be traced is shown as unresolved, never filled.

## Shape

- `TrialLedger/ingest.py`: the network shell (`Session`, `fetch_version`, `fetch_json_pages`,
  `fetch_csv_pages`, `pull`). Every decision it makes is a pure function beside it, tagged
  `(pure — pinned)`, returning a named code.
- `TrialLedger/record.py`: writes a complete pull, both files or nothing.
- `TrialLedger/cli.py`: `trialledger pull NAME=VALUE ...`, the entry point.
- `spec/ctg-oas-v2.yaml`: the vendored contract; `tests/test_spec_contract.py` holds the code to it.

## Gate

`scripts/ci_local.sh` is the gate: `uv sync --locked`, ruff check, ruff format check, pytest, then
`detective audit --two-sign --check` on every function tagged `(pure — pinned)` (the list is read from the
code). `uvx ty check --python .venv TrialLedger` is advisory. Live calls are opt-in: `uv run pytest -m live`.

## Detective

Run from this repo's `.venv` with the local checkouts first:
`PYTHONPATH=$HOME/tools/Detective:$HOME/tools/Wesker .venv/bin/detective ...`. Every pinned decision here
was converged with `--two-sign`, which the printed DO THIS lines omit; keep adding it.

A new decision is written unwired, given direct-call intent tests for both signs, converged with
`--two-sign` in isolation, and only then wired into the shell. Five `retry_delay` survivors are flagged
equivalent with proofs in their notes; an edit to `retry_delay` un-flags them. The flags and supplied
inputs live in the gitignored `.detective/` on the machine that made them.

## Open items

- `detective decompose TrialLedger/cli.py::parse_query_args --apply` stops on five crash-only survivors and
  asks for them to be flagged equivalent or killed by `--input`; converge says the same five are not
  equivalence candidates. Neither repair is truthful, so the split is not applied.
- `detective audit` reports 3 (`classify_json_page`) and 1 (`classify_csv_page`) survivors as
  unproven-equivalent that `converge`, using the supplied inputs, certifies as crash-only; and every audit
  names `converge` as its next action, including right after a COMPLETE converge.
- `detective survey` still lists `pull` and `write_record` as I/O-bound; `extract` reports an unresolved
  interface for both and proposes nothing. Their decisions are pinned or covered by durability tests.
