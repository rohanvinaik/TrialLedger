"""A scripted stand-in for the ClinicalTrials.gov API, served through httpx.MockTransport.

Each queue holds what successive requests to that endpoint receive: an httpx.Response, or an exception
class that is raised as a transport failure. Every request is recorded, and so is every sleep.
"""

import httpx
import pytest

from TrialLedger.ingest import API_BASE

DATA_TIMESTAMP = "2026-10-30T09:00:04"
CSV_HEADER_ROW = "NCT Number,Study Title,Study URL\r\n"


def version(data_timestamp=DATA_TIMESTAMP, api_version="2.0.5"):
    return httpx.Response(200, json={"apiVersion": api_version, "dataTimestamp": data_timestamp})


def study(nct_id):
    return {"protocolSection": {"identificationModule": {"nctId": nct_id, "briefTitle": f"T {nct_id}"}}}


def json_page(nct_ids, total=None, token=None):
    body = {"studies": [study(nct_id) for nct_id in nct_ids]}
    if total is not None:
        body["totalCount"] = total
    if token is not None:
        body["nextPageToken"] = token
    return httpx.Response(200, json=body)


def csv_row(nct_id):
    return f'{nct_id},"Title of {nct_id}, with a comma",https://clinicaltrials.gov/study/{nct_id}\r\n'


def csv_page(nct_ids, total=None, token=None, header=False):
    body = (CSV_HEADER_ROW if header else "") + "".join(csv_row(nct_id) for nct_id in nct_ids)
    headers = {"content-type": "text/csv"}
    if total is not None:
        headers["x-total-count"] = str(total)
    if token is not None:
        headers["x-next-page-token"] = token
    return httpx.Response(200, headers=headers, content=body.encode("utf-8"))


class FakeAPI:
    def __init__(self, versions=None, json_pages=(), csv_pages=()):
        self.versions = list(versions if versions is not None else [version(), version()])
        self.json_pages = list(json_pages)
        self.csv_pages = list(csv_pages)
        self.requests = []
        self.sleeps = []

    def _serve(self, request):
        self.requests.append(request)
        if request.url.path == "/api/v2/version":
            queue = self.versions
        elif request.url.path == "/api/v2/studies":
            queue = self.json_pages if request.url.params.get("format") == "json" else self.csv_pages
        else:
            raise AssertionError(f"unexpected request: {request.url}")
        if not queue:
            raise AssertionError(f"no scripted response left for {request.url}")
        item = queue.pop(0)
        if isinstance(item, type) and issubclass(item, Exception):
            raise item("scripted transport failure", request=request)
        return item

    def client(self):
        return httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(self._serve), follow_redirects=False
        )

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def studies_requests(self, fmt):
        return [r for r in self.requests if r.url.path == "/api/v2/studies" and r.url.params["format"] == fmt]


@pytest.fixture
def no_clock():
    """A monotonic clock that never advances, so every throttle wait is recorded at full length."""
    return lambda: 0.0
