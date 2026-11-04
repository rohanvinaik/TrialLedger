# Quality

Tests and coverage measured at commit `5598ea6` on 2026-11-02 with Python 3.14.7.
Mutation results have the separate basis below. This file is a retained snapshot; live README
badges show the latest successful publication, which may lag main. They are published by the
[quality workflow](.github/workflows/quality.yml) and published to https://rohanvinaik.github.io/TrialLedger/.

| Measure | Value |
|---|---|
| Tests | 3,566 passing (10 opt-in live-registry tests deselected) |
| Line coverage | 97.7% of 8,660 statements |
| Branch coverage | 95.5% of 3,558 branches |
| Mutation score, pinned decisions | 95.5% of 3,205 planted bugs caught, across 198 recorded functions marked "pure — pinned" (3,062 failed a test, 0 timed out, 143 survived) |
| Mutation measurement basis | 95.5% · 5598ea6 · Measured; census date: 2026-11-02. Scope counts include the pinned decisions and the separate sampled functions; unavailable-baseline count refers to pinned decisions only. |
| Mutation score, other functions | 61.0% of 1,091 planted bugs caught, across a seeded random sample of 60 of the remaining functions; 29 of them have no test that names them, so tests that catch bugs indirectly were not run and this bound is looser |
| Detective certificates | 122 of 198 pinned decisions recorded complete at `5598ea6`; audit not rerun or freshness-validated |
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
- **On each push** the quality workflow publishes tests and coverage before starting mutation work, then
  publishes the completed census if that run finishes. The first publication preserves the prior census's
  own commit and date; it never relabels it as a measurement of the new code. A newer push can cancel the
  slow run without withholding already-published tests. The separate Actions badge reports suite status.
  The census re-measures mutants
  only for functions whose code, or whose selected test files, changed since the last published measurement
  (or this committed baseline). A 30-minute budget bounds each run; a function not reached keeps its previous
  result, marked stale, and is re-measured on the next run. Stale results remain in the historical aggregate;
  the badge names their count and says Partial (or Historical when its commit differs from coverage).
  Unmeasured targets and pinned functions without a passing selected-test baseline also remain visible.
  Reuse checks function bodies and selected tests, not the entire transitive dependency graph; Measured
  describes that census basis, not proof of every path at the current commit. See the published
  [snapshot report](https://rohanvinaik.github.io/TrialLedger/quality.md) for its exact basis and date.
- **Detective certificates** are read from `tests/detective/certificates.json`, as recorded by Detective's
  two-sign audit; this report does not re-run that audit or certify that its recorded basis is still current.

These numbers describe how thoroughly the code is specified and tested. They are not a clinical validation
of any trial interpretation.
