# Quality

Measured at commit `5598ea6` on 2026-11-02 with Python 3.14.7. The README
badges show the same measures for the latest commit, refreshed on every push to `main` by the
[quality workflow](.github/workflows/quality.yml) and published to https://rohanvinaik.github.io/TrialLedger/.

| Measure | Value |
|---|---|
| Tests | 3,566 passing (10 opt-in live-registry tests deselected) |
| Line coverage | 97.7% of 8,660 statements |
| Branch coverage | 95.5% of 3,558 branches |
| Mutation score, pinned decisions | 95.5% of 3,205 planted bugs caught, across all 198 functions marked "pure — pinned" (3,062 failed a test, 0 timed out, 143 survived) |
| Mutation score, other functions | 61.0% of 1,091 planted bugs caught, across a seeded random sample of 60 of the remaining functions; 29 of them have no test that names them, so tests that catch bugs indirectly were not run and this bound is looser |
| Detective certificates | 122 of 198 pinned decisions recorded complete |
| Runtime dependencies | 2 (httpx, openpyxl) |
| Package | 638 functions, 23,146 non-blank lines |

## How it is measured

[`scripts/quality_metrics.py`](scripts/quality_metrics.py) measures one commit in throwaway `git archive`
copies; the working checkout is never modified. Reproduce from the repository root:

```bash
uv run --with coverage --with pytest-cov python scripts/quality_metrics.py --workers 8
```

- **Coverage** runs the whole suite under coverage.py with the classic tracer, counting statements and
  branches in the `TrialLedger` package.
- **Mutation score** plants one simple bug at a time inside a function body (comparison flipped, `and`/`or`
  swapped, boolean flipped, integer incremented, string constant changed), runs the test files that name
  the function (or, failing that, import its module) and counts the bug caught if a test fails or times
  out. Every pinned decision is measured; the other functions are a seeded random sample. The score is a
  lower bound: tests elsewhere that catch a bug indirectly are not run, and equivalent mutants (changes
  that cannot alter behavior) are not removed. Every survivor is listed in
  [`quality/survivors.md`](quality/survivors.md).
- **On each push** the quality workflow re-runs the suite under coverage in full, and re-measures mutants
  only for functions whose code, or whose selected test files, changed since the last published measurement
  (or this committed baseline). A 30-minute budget bounds each run; a function not reached keeps its previous
  result, marked stale, and is re-measured on the next run. The tests badge comes from a separate workflow.
- **Detective certificates** are read from `tests/detective/certificates.json`, as recorded by Detective's
  two-sign audit; this report does not re-run that audit.

These numbers describe how thoroughly the code is specified and tested. They are not a clinical validation
of any trial interpretation.
