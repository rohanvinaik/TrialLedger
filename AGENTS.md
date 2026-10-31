# AGENTS.md — TrialLedger

TrialLedger pulls ClinicalTrials.gov records through the API in `spec/ctg-oas-v2.yaml` and writes
`studies.json` (records as sent, plus provenance) and `studies.csv` (the API's own CSV). The README says how
to run it. This file holds what an agent working on it must keep true.

## The rule this project exists for

No code here interprets, selects, summarises or rewrites study content, and no agent does either. Records and
spreadsheet rows are written as the API sent them. Shaping the data for people is the next phase, worked out
with the owner; it is not decided by an agent.

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
equivalent with proofs in their notes; an edit to `retry_delay` un-flags them.

## Open items

- `detective decompose TrialLedger/cli.py::parse_query_args --apply` stops on five crash-only survivors and
  asks for them to be flagged equivalent or killed by `--input`; converge says the same five are not
  equivalence candidates. Neither repair is truthful, so the split is not applied.
- `detective audit` reports 3 (`classify_json_page`) and 1 (`classify_csv_page`) survivors as
  unproven-equivalent that `converge`, using the supplied inputs, certifies as crash-only; and every audit
  names `converge` as its next action, including right after a COMPLETE converge.
- `detective survey` still lists `pull` and `write_record` as I/O-bound; `extract` reports an unresolved
  interface for both and proposes nothing. Their decisions are pinned or covered by durability tests.
