"""Does the registry send its CSV with a UTF-8 byte-order mark? A probe for comparison (d)'s difference.

Run from the repository's root (`.venv/bin/python -m acceptance.probe_bom --date D`), live: it asks the API
for the selection's CSV in several request forms and with several request headers, and writes, for each, the
first three bytes, the length and the SHA-256 of the body, and whether the body is exactly the pulled
studies.csv, or the pulled studies.csv without a leading byte-order mark, to
`acceptance/runs/<D>/bom-probe.json`. The default page size (10) answers with the first page only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
URL = "https://clinicaltrials.gov/api/v2/studies"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    ids = ",".join(json.loads((HERE / "selection.json").read_text(encoding="utf-8"))["nct_ids"])
    pulled = (HERE / "runs" / args.date / "pull" / "studies.csv").read_bytes()
    forms = [
        ({"pageSize": 100, "countTotal": "true"}, {}),
        ({"pageSize": 100}, {}),
        ({"pageSize": 1000}, {}),
        ({"pageSize": 1000, "countTotal": "true"}, {}),
        ({}, {}),
        ({"pageSize": 1000}, {"Accept": "text/csv"}),
        ({"pageSize": 1000}, {"Accept-Encoding": "identity"}),
        ({"pageSize": 1000}, {"Accept": "*/*", "User-Agent": "acceptance-probe"}),
    ]
    out = []
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        for params, headers in forms:
            time.sleep(1.0)
            response = client.get(URL, params={"filter.ids": ids, "format": "csv", **params}, headers=headers)
            body = response.content
            out.append(
                {
                    "params": params,
                    "headers": headers,
                    "status": response.status_code,
                    "first_bytes": body[:3].hex(),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "next_page_token": response.headers.get("x-next-page-token") is not None,
                    "equals_pulled": body == pulled,
                    "equals_pulled_without_bom": b"\xef\xbb\xbf" + body == pulled,
                }
            )
    payload = {
        "probed_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pulled_first_bytes": pulled[:3].hex(),
        "pulled_sha256": hashlib.sha256(pulled).hexdigest(),
        "responses": out,
    }
    path = HERE / "runs" / args.date / "bom-probe.json"
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
