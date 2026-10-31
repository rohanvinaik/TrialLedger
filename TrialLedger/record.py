"""Write a complete pull to disk: both files, or nothing at all."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from TrialLedger import __version__
from TrialLedger.ingest import API_BASE, Pull

JSON_NAME = "studies.json"
CSV_NAME = "studies.csv"
UTF8_BOM = "﻿"  # tells Excel the CSV is UTF-8; it changes no cell


def write_record(pull: Pull, out_dir: Path) -> list[Path]:
    """Create `out_dir` holding studies.json (the raw records plus provenance) and studies.csv.

    studies.csv is the API's own CSV for the same query, byte for byte, after a UTF-8 byte-order mark.
    The files are written into `<out_dir>.partial` and renamed into place only when both are complete,
    so a failure leaves no record at all. An existing `out_dir` is never overwritten.
    """
    if out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists; TrialLedger never overwrites a record")
    staging = out_dir.with_name(out_dir.name + ".partial")
    staging.mkdir(parents=True)
    try:
        record = {
            "provenance": {
                "source": f"{API_BASE}/studies",
                "query": pull.query,
                "api_version": pull.api_version,
                "data_timestamp": pull.data_timestamp,
                "retrieved_at": pull.retrieved_at,
                "study_count": pull.total_count,
                "spreadsheet": f"{CSV_NAME}: ClinicalTrials.gov's own CSV (format=csv) for this query",
                "tool": f"TrialLedger {__version__}",
            },
            "studies": pull.studies,
        }
        (staging / JSON_NAME).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / CSV_NAME).write_text(UTF8_BOM + pull.csv_text, encoding="utf-8", newline="")
        staging.rename(out_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return [out_dir / JSON_NAME, out_dir / CSV_NAME]
