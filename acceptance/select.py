"""Layer one's acceptance test, step 1: a prospective, seeded selection of twenty trials from the registry.

Run once, before anything is compared, from the repository's root: `.venv/bin/python -m
acceptance.select` (as a module, so that this file never shadows the standard library's `select`). It writes
`acceptance/selection.json` with the criteria, the seed, every stratum and the query each one sent, every draw
it made (its window, the count the registry reported and the IDs it chose among), the twenty NCT numbers, the
facts that make them diverse (phase, overall status, study type, results posted or not, lead sponsor class,
record size, NCT ID aliases), the registry's data version before and after, the file's own creation time and
the SHA-256 of this script. It refuses to overwrite an existing selection: the selection is fixed before any
comparison and never redrawn.

This script is independent of TrialLedger: it imports nothing from the package and reads only the registry's
API (spec/ctg-oas-v2.yaml) and its vendored enum table (TrialLedger/registry/ctg-enums.json, the registry's
own `/studies/enums`). Each stratum is an Essie expression in `filter.advanced` over the registry's own search
areas (StudyType, Phase, OverallStatus, HasResults, LeadSponsorClass, NCTIdAlias:size, StudyFirstPostDate).

How a trial is drawn from a stratum: when the registry counts at most `WHOLE_STRATUM` studies in it, all
their IDs are read and one is chosen; otherwise a month of first posting is drawn (seeded) and the stratum is
narrowed to it (to its year when the month holds none, and a new month is drawn when the year holds none,
up to `MAX_WINDOWS` times), all IDs in that window are read and one is chosen. A choice is
`random.Random(f"{seed}/{stratum}/{attempt}")` over the sorted IDs, so the same registry snapshot gives the
same draw. Two strata choose by record size: the largest, or the smallest, of five such draws, measured as the
bytes of the study's JSON (format=json). A trial already chosen by an earlier stratum is drawn again.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import httpx

API = "https://clinicaltrials.gov/api/v2"
SEED = 20261101
WHOLE_STRATUM = 3000
MAX_WINDOWS = 12
FIRST_YEAR = 2000
LAST_MONTH = (2026, 9)
SIZE_DRAWS = 5
PAUSE = 0.6
HERE = Path(__file__).resolve().parent
OUT = HERE / "selection.json"

INT = "AREA[StudyType]INTERVENTIONAL"
OBS = "AREA[StudyType]OBSERVATIONAL"
EXP = "AREA[StudyType]EXPANDED_ACCESS"

# Each stratum: (name, what it is for, how it chooses, its expressions in order of preference). The first
# expression the registry counts any study for is the one used; the later ones relax the stratum and are
# used only when the earlier hold no study (each recorded with its count).
STRATA = [
    (
        "phase1_completed_results_industry",
        "Phase 1, completed, results posted, industry sponsor",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE1 AND AREA[OverallStatus]COMPLETED AND AREA[HasResults]true"
            " AND AREA[LeadSponsorClass]INDUSTRY"
        ],
    ),
    (
        "phase2_terminated_results_other",
        "Phase 2, terminated, results posted, sponsor class OTHER (universities, hospitals)",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE2 AND AREA[OverallStatus]TERMINATED AND AREA[HasResults]true"
            " AND AREA[LeadSponsorClass]OTHER"
        ],
    ),
    (
        "phase3_completed_results_industry_largest",
        "Phase 3, completed, results posted, industry sponsor: the largest record of five draws",
        "largest",
        [
            f"{INT} AND AREA[Phase]PHASE3 AND AREA[OverallStatus]COMPLETED AND AREA[HasResults]true"
            " AND AREA[LeadSponsorClass]INDUSTRY"
        ],
    ),
    (
        "phase3_recruiting_industry",
        "Phase 3, recruiting, no results, industry sponsor",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE3 AND AREA[OverallStatus]RECRUITING AND AREA[HasResults]false"
            " AND AREA[LeadSponsorClass]INDUSTRY"
        ],
    ),
    (
        "phase4_completed_no_results_other",
        "Phase 4, completed, no results posted, sponsor class OTHER",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE4 AND AREA[OverallStatus]COMPLETED AND AREA[HasResults]false"
            " AND AREA[LeadSponsorClass]OTHER"
        ],
    ),
    (
        "early_phase1_not_yet_recruiting",
        "Early Phase 1, not yet recruiting",
        "random",
        [f"{INT} AND AREA[Phase]EARLY_PHASE1 AND AREA[OverallStatus]NOT_YET_RECRUITING"],
    ),
    (
        "phase_na_recruiting_other",
        "Phase not applicable (devices, behaviour), recruiting, sponsor class OTHER",
        "random",
        [f"{INT} AND AREA[Phase]NA AND AREA[OverallStatus]RECRUITING AND AREA[LeadSponsorClass]OTHER"],
    ),
    (
        "phase1_phase2_active_nih",
        "Phases 1 and 2 combined, active not recruiting, NIH sponsor",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE1 AND AREA[Phase]PHASE2 AND AREA[OverallStatus]ACTIVE_NOT_RECRUITING"
            " AND AREA[LeadSponsorClass]NIH",
            f"{INT} AND AREA[Phase]PHASE1 AND AREA[Phase]PHASE2 AND AREA[OverallStatus]ACTIVE_NOT_RECRUITING",
        ],
    ),
    (
        "phase2_phase3_results_fed",
        "Phases 2 and 3 combined, results posted, other US federal sponsor (FED)",
        "random",
        [
            f"{INT} AND AREA[Phase]PHASE2 AND AREA[Phase]PHASE3 AND AREA[HasResults]true"
            " AND AREA[LeadSponsorClass]FED",
            f"{INT} AND AREA[Phase]PHASE2 AND AREA[Phase]PHASE3 AND AREA[HasResults]true",
        ],
    ),
    (
        "interventional_withdrawn",
        "Withdrawn before enrolling",
        "random",
        [f"{INT} AND AREA[OverallStatus]WITHDRAWN"],
    ),
    (
        "interventional_suspended",
        "Suspended",
        "random",
        [f"{INT} AND AREA[OverallStatus]SUSPENDED"],
    ),
    (
        "interventional_unknown_status",
        "Status unknown (not verified for two years)",
        "random",
        [f"{INT} AND AREA[OverallStatus]UNKNOWN"],
    ),
    (
        "enrolling_by_invitation_network",
        "Enrolling by invitation, network sponsor (NETWORK)",
        "random",
        [
            "AREA[OverallStatus]ENROLLING_BY_INVITATION AND AREA[LeadSponsorClass]NETWORK",
            "AREA[OverallStatus]ENROLLING_BY_INVITATION",
        ],
    ),
    (
        "observational_recruiting_other",
        "Observational, recruiting, sponsor class OTHER",
        "random",
        [f"{OBS} AND AREA[OverallStatus]RECRUITING AND AREA[LeadSponsorClass]OTHER"],
    ),
    (
        "observational_completed_results",
        "Observational, completed, results posted",
        "random",
        [f"{OBS} AND AREA[OverallStatus]COMPLETED AND AREA[HasResults]true"],
    ),
    (
        "observational_other_gov",
        "Observational, non-US government sponsor (OTHER_GOV)",
        "random",
        [f"{OBS} AND AREA[LeadSponsorClass]OTHER_GOV"],
    ),
    (
        "expanded_access_available",
        "Expanded access, available",
        "random",
        [f"{EXP} AND AREA[OverallStatus]AVAILABLE"],
    ),
    (
        "expanded_access_closed",
        "Expanded access, no longer available or approved for marketing",
        "random",
        [f"{EXP} AND (AREA[OverallStatus]NO_LONGER_AVAILABLE OR AREA[OverallStatus]APPROVED_FOR_MARKETING)"],
    ),
    (
        "nct_id_aliases",
        "A record whose identification lists NCT ID aliases (obsolete or duplicate NCT numbers)",
        "random",
        ["AREA[NCTIdAlias:size]RANGE[1,MAX]"],
    ),
    (
        "individual_sponsor_smallest",
        "An individual as lead sponsor (INDIV): the smallest record of five draws",
        "smallest",
        ["AREA[LeadSponsorClass]INDIV"],
    ),
]

CRITERIA = (
    "Twenty trials, one per stratum, so that together they span every study type (interventional, "
    "observational, expanded access); the phases EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4 and NA, "
    "with two combined-phase records; the overall statuses COMPLETED, TERMINATED, RECRUITING, "
    "NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, WITHDRAWN, SUSPENDED, UNKNOWN, ENROLLING_BY_INVITATION and "
    "the expanded-access statuses; results posted and not; the lead sponsor classes INDUSTRY, OTHER, NIH, "
    "FED, NETWORK, OTHER_GOV and INDIV; record size from the smallest of five draws to the largest of five; "
    "and at least one record whose identification lists NCT ID aliases. Strata are fixed in this script "
    "before any draw; the draws are seeded; nothing about TrialLedger's output informs them."
)


def month_draw(seed: int, stratum: str, attempt: int) -> tuple[int, int]:
    """(pure — pinned)

    The (year, month) of first posting a stratum's draw `attempt` narrows to, uniform over the months from
    January of FIRST_YEAR to LAST_MONTH, from the seed alone.
    """
    months = (LAST_MONTH[0] - FIRST_YEAR) * 12 + LAST_MONTH[1]
    index = random.Random(f"{seed}/{stratum}/month/{attempt}").randrange(months)
    return FIRST_YEAR + index // 12, index % 12 + 1


def window_expression(expression: str, year: int, month: int | None) -> str:
    """(pure — pinned)

    The stratum's expression narrowed to studies first posted in that month (or, with month None, that year).
    """
    if month is None:
        low, high = f"{year}-01-01", f"{year}-12-31"
    else:
        low = f"{year}-{month:02d}-01"
        high = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    return f"({expression}) AND AREA[StudyFirstPostDate]RANGE[{low},{high}]"


def choose(ids: list[str], seed: int, stratum: str, attempt: int) -> str | None:
    """(pure — pinned)

    One ID from a window's IDs, seeded and independent of the order the registry listed them in; None when
    the window holds none.
    """
    pool = sorted(set(ids))
    if not pool:
        return None
    return random.Random(f"{seed}/{stratum}/choice/{attempt}").choice(pool)


def record_facts(study: dict, size: int) -> dict:
    """(pure — pinned)

    The facts that place a study in the selection's diversity: phase, overall status, study type, results,
    lead sponsor class, size in bytes of its JSON and its NCT ID aliases, read from the record as the API
    names them.
    """
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    return {
        "nctId": ident.get("nctId"),
        "phases": protocol.get("designModule", {}).get("phases", []),
        "overallStatus": protocol.get("statusModule", {}).get("overallStatus"),
        "studyType": protocol.get("designModule", {}).get("studyType"),
        "hasResults": study.get("hasResults"),
        "leadSponsorClass": protocol.get("sponsorCollaboratorsModule", {})
        .get("leadSponsor", {})
        .get("class"),
        "recordBytes": size,
        "nctIdAliases": ident.get("nctIdAliases", []),
    }


def coverage(facts: list[dict]) -> dict:
    """(pure — pinned)

    How many of the selected trials hold each value of each diversity dimension; a record with several phases
    counts once for each and once for its combination.
    """

    def tally(values: list[str]) -> dict:
        out: dict[str, int] = {}
        for value in values:
            out[value] = out.get(value, 0) + 1
        return dict(sorted(out.items()))

    phases = [phase for fact in facts for phase in fact["phases"]]
    combined = ["+".join(fact["phases"]) for fact in facts if len(fact["phases"]) > 1]
    sizes = sorted(fact["recordBytes"] for fact in facts)
    return {
        "phase": tally(phases),
        "combined_phases": tally(combined),
        "no_phase_field": sum(1 for fact in facts if not fact["phases"]),
        "overallStatus": tally([str(fact["overallStatus"]) for fact in facts]),
        "studyType": tally([str(fact["studyType"]) for fact in facts]),
        "hasResults": tally([str(fact["hasResults"]) for fact in facts]),
        "leadSponsorClass": tally([str(fact["leadSponsorClass"]) for fact in facts]),
        "with_nct_id_aliases": sum(1 for fact in facts if fact["nctIdAliases"]),
        "recordBytes": {"min": sizes[0], "median": sizes[len(sizes) // 2], "max": sizes[-1]} if sizes else {},
    }


class Registry:
    """The live API, paced and retried on a server error or rate limit; every request kept for the record."""

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=120, follow_redirects=False)
        self.requests: list[dict] = []

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        for attempt in range(5):
            time.sleep(PAUSE)
            response = self.client.get(API + path, params=params)
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(2**attempt * 2)
                continue
            self.requests.append({"path": path, "params": params, "status": response.status_code})
            response.raise_for_status()
            return response
        raise RuntimeError(f"{path} {params}: the registry kept failing")

    def version(self) -> dict:
        return self.get("/version").json()

    def ids(self, expression: str, limit_pages: int = 10) -> tuple[int, list[str]]:
        params = {"filter.advanced": expression, "fields": "NCTId", "pageSize": 1000, "countTotal": "true"}
        page = self.get("/studies", params).json()
        total, found = page.get("totalCount", 0), []
        for _ in range(limit_pages):
            found += [s["protocolSection"]["identificationModule"]["nctId"] for s in page.get("studies", [])]
            token = page.get("nextPageToken")
            if not token:
                break
            page = self.get("/studies", {**params, "pageToken": token}).json()
        return total, found

    def count(self, expression: str) -> int:
        params = {"filter.advanced": expression, "fields": "NCTId", "pageSize": 1, "countTotal": "true"}
        return self.get("/studies", params).json().get("totalCount", 0)

    def study(self, nct: str) -> bytes:
        return self.get(f"/studies/{nct}", {"format": "json"}).content


def draw_one(api: Registry, expression: str, total: int, stratum: str, attempt: int, log: list) -> str | None:
    """One draw from a stratum: the whole stratum when small, else a seeded month (or its year) of it."""
    if total <= WHOLE_STRATUM:
        _, ids = api.ids(expression)
        nct = choose(ids, SEED, stratum, attempt)
        log.append({"attempt": attempt, "window": "whole stratum", "count": len(ids), "chosen": nct})
        return nct
    for window in range(MAX_WINDOWS):
        year, month = month_draw(SEED, stratum, attempt * 100 + window)
        for scope in (month, None):
            narrowed = window_expression(expression, year, scope)
            count, ids = api.ids(narrowed)
            label = f"{year}-{scope:02d}" if scope else f"{year}"
            if ids:
                nct = choose(ids, SEED, stratum, attempt * 100 + window)
                log.append(
                    {
                        "attempt": attempt,
                        "window": label,
                        "expression": narrowed,
                        "count": count,
                        "ids_read": len(ids),
                        "chosen": nct,
                    }
                )
                return nct
            log.append({"attempt": attempt, "window": label, "count": count, "chosen": None})
    return None


def select() -> dict:
    api = Registry()
    started = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    version_before = api.version()
    chosen: list[str] = []
    strata_out = []
    facts = []
    for name, purpose, rule, expressions in STRATA:
        tried = []
        expression, total = None, 0
        for candidate in expressions:
            total = api.count(candidate)
            tried.append({"expression": candidate, "count": total})
            if total:
                expression = candidate
                break
        log: list[dict] = []
        candidates = []
        attempt = 0
        wanted = SIZE_DRAWS if rule in ("largest", "smallest") else 1
        while expression and len(candidates) < wanted and attempt < 40:
            nct = draw_one(api, expression, total, name, attempt, log)
            attempt += 1
            if nct is None:
                break
            if nct in chosen or nct in [c["nctId"] for c in candidates]:
                log.append({"attempt": attempt - 1, "redrawn": nct, "why": "already chosen"})
                continue
            body = api.study(nct)
            candidates.append(
                {"nctId": nct, "recordBytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            )
        if not candidates:
            raise SystemExit(f"stratum {name} yielded no trial: {tried} {log}")
        if rule == "largest":
            pick = max(candidates, key=lambda c: (c["recordBytes"], c["nctId"]))
        elif rule == "smallest":
            pick = min(candidates, key=lambda c: (c["recordBytes"], c["nctId"]))
        else:
            pick = candidates[0]
        chosen.append(pick["nctId"])
        study = json.loads(api.study(pick["nctId"]))
        fact = record_facts(study, pick["recordBytes"])
        facts.append({"stratum": name, **fact})
        strata_out.append(
            {
                "name": name,
                "purpose": purpose,
                "rule": rule,
                "expressions_tried": tried,
                "expression": expression,
                "count": total,
                "draws": log,
                "candidates": candidates,
                "chosen": pick["nctId"],
            }
        )
        print(f"{name}: {pick['nctId']} ({pick['recordBytes']} bytes)", file=sys.stderr)
    version_after = api.version()
    return {
        "what": "TrialLedger layer-one acceptance test (add-agent-operation 7.1): the frozen selection",
        "created_at": started,
        "written_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code": {
            "file": "acceptance/select.py",
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "seed": SEED,
        "criteria": CRITERIA,
        "method": {
            "whole_stratum_at_most": WHOLE_STRATUM,
            "max_windows": MAX_WINDOWS,
            "months": f"{FIRST_YEAR}-01 to {LAST_MONTH[0]}-{LAST_MONTH[1]:02d}",
            "size_draws": SIZE_DRAWS,
            "choice": "random.Random(f'{seed}/{stratum}/choice/{attempt}').choice(sorted IDs)",
        },
        "registry": {
            "api": API,
            "version_before": version_before,
            "version_after": version_after,
            "requests": len(api.requests),
        },
        "strata": strata_out,
        "nct_ids": chosen,
        "facts": facts,
        "coverage": coverage(facts),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        print(f"{out} exists: the selection is frozen and never redrawn", file=sys.stderr)
        return 2
    selection = select()
    out.write_text(json.dumps(selection, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(" ".join(selection["nct_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
