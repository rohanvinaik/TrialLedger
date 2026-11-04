# Replacing the obsolete record-reader characterization

The authorized index change exposes `brief_title`, `acronym` and `official_title` beside
the NCT identity. The historical generated test expected the earlier index shape. Its
complete `-vv` failure showed exactly those three added fields, each `None` in the
two-study synthetic record, with all older values and paging unchanged.

The first canonical-owner run named that precise failing test and prescribed:

```text
DO THIS:  pytest 'tests/detective/test_TrialLedger_mcp_server_record_view_e2e7b64d3c_synth.py::test_record_view_golden[args6-expected6]'

  · Then decide        is the TEST's expectation wrong, or is the CODE broken?
                       Detective will not touch it — that call is yours alone.
  · After fixing       detective converge 'TrialLedger/evidence_access.py::record_view' --two-sign
```

The test expectation is superseded by the explicitly authorized additional source
fields. Production code was not changed to satisfy the old expectation. The lead's
fresh Serena reference query for `test_record_view_golden` returned no code consumers.
The obsolete file was copied byte-for-byte before retirement; its SHA256 is
`cee0b5473848144538b3ae48685fcc62bba228cb19a201b5ea8dd38db3be172c`.
The preserved copy is outside Git at
`/tmp/trialledger-final-proof-packets-20261104/stale-record-view-characterization/`.

The six authored checks for the title fields, source-status distinctions, exact index
field contract and paging passed after that retirement. This does not claim that the
replacement mutation walk has completed; its separate receipt records that outcome.

The governing instruction is the complete **Running converge** subsection in
`/Users/rohanvinaik/tools/Detective/AGENTS.md`, read in the context of that whole file:

> ## Running converge
>
> Bare first, to find the gap:
>
> ```bash
> PYTHONPATH=$PP .venv/bin/detective converge 'Detective/converge.py::line_proof_basis' > run.log 2>&1
> # then Read run.log IN FULL — never tail it
> ```
>
> Then follow the `DO THIS` block **literally** — one `--input` per uncovered line, read straight off the `Uncovered`
> conditions — and re-run until `✓ COMPLETE`:
>
> ```bash
> PYTHONPATH=$PP .venv/bin/detective converge 'Detective/certify.py::write_disposition' \
>   --input "(True, 'other.py::f', 'mine.py::f')" \
>   --input "(True, '', 'mine.py::f')" > run.log 2>&1
> # then Read run.log IN FULL — never tail it
> ```
>
> - Compute real digests and paths rather than inventing them (`D=$(python3 -c "import hashlib;...")`).
> - Read `converge --help` for the input grammar rather than guessing it.
> - `modulo N unproven-equivalent` **counts as done**. Candidate-equivalents are undecidable and get resolved by
>   `detective flag`, never by grinding.
> - A stale generated golden is **regenerated, not hand-patched**: `rm` the `*_synth.py` and re-run converge.
> - Between runs, keep a cached verdict or a recalled `--input` from masking a change, without destroying user data:
>   - `pins.json` and `verdict_cache.json` are regeneratable (`Detective/pins.py`), so clear them:
>     `rm -f .detective/pins.json .detective/verdict_cache.json`.
>   - `inputs.json` is **user data**: `Detective/samples.py` says supplied inputs are never purged, and `.detective/` is
>     gitignored, so a deletion cannot be recovered. **Never delete it in place.** To measure without recall, run in a
>     disposable copy of the project, or move it aside and put it back:
>     `mv .detective/inputs.json <scratch>/inputs.json.bak` … `mv <scratch>/inputs.json.bak .detective/inputs.json`.
>   - These are **FILES, not directories**. The old `.detective/pins` / `.detective/samples` PATHS DO NOT EXIST, so
>     `rm -rf`-ing them is a silent no-op that leaves supplied inputs recalled.
>   - Measured: converge kept re-applying stale `--input`s across runs, masking the true no-input behaviour.
> - Every command resolves the testing **regime** first and REFUSES on a shadowed target or a conflicting conftest. A
>   refusal is the tool working; `detective regime` is where the reason is. Never work around it.

No generated assertion was hand-edited. The canonical owner is
`TrialLedger/evidence_access.py::record_view`; the old MCP symbol is a compatibility
alias. A new complete characterization, if produced, is adopted wholesale from the
fresh owner run. The old alias certificate is not silently represented as current.
