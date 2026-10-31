# TrialLedger

Pulls ClinicalTrials.gov study records through the official API (v2, described by `spec/ctg-oas-v2.yaml`)
and writes them to a new directory:

- `studies.json`: every matching study exactly as the API returned it, plus provenance (the query, the
  API version, the registry's data timestamp, the retrieval time, the study count).
- `studies.csv`: ClinicalTrials.gov's own spreadsheet (`format=csv`) for the same query, opened in Excel,
  Numbers or Google Sheets. A UTF-8 byte-order mark is added so Excel reads accented characters correctly;
  no cell is changed.

Nothing in TrialLedger interprets study content. It sends the query, checks that what came back is complete,
and writes it down.

## Use

```bash
uv sync
uv run trialledger pull filter.ids=NCT04852770
uv run trialledger pull filter.ids=NCT04852770,NCT01030536 --out my_studies
uv run trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING
uv run trialledger pull "filter.advanced=AREA[StartDate]RANGE[2024-01-01,2024-01-31]" query.cond=asthma
```

Each `NAME=VALUE` is a `/studies` parameter from the spec, sent as given; the API rejects unknown names.
`query.*` parameters search the API's search areas and rank results by relevance, so they can match more than
one field; `filter.*` parameters restrict the set. `uv run trialledger pull --help` lists examples.

## What it guarantees

A pull is written only when all of these hold; otherwise nothing is written and the exit status is non-zero:

- every page of both formats was received, following the API's page tokens to the end;
- the number of studies equals the API's reported total, with no duplicates;
- the JSON record and the spreadsheet hold the same NCT IDs;
- the registry's data timestamp was the same at the start and at the end of the pull;
- server errors (429, 500, 502, 503, 504) and dropped connections were retried and then succeeded.

Exit status: `0` written; `1` the pull or the write failed and nothing was written; `2` the query was refused
before anything was sent (for example, an NCT-ID-only `query.*` value beside a filter, which the API answers
by silently ignoring the filter).

Requests are spaced 1.25 s apart. ClinicalTrials.gov publishes no rate limit; HTTP 429 is honoured.

## Check

```bash
scripts/ci_local.sh          # ruff, the test suite, and a Detective audit of every pinned decision
uv run pytest -m live        # one pull against the real API (opt-in)
```
