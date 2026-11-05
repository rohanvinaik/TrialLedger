"""Search coverage: what a declared registry search does and does not reach (pure decisions only).

A completed retrieval means the DECLARED search finished: the registry answered that exact query and every
page was followed. It does not mean every trial of the clinical concept was found. A condition class is
searched through the registry's MeSH annotations, so a record without them cannot match whatever its text
says; a drug class is searched through the members RxNav returned for it, which is a catalogue, not every
clinically relevant drug.

This module holds the pure decisions: the statements saved in a scope (`search_coverage`), the alternate
condition-text query built with every other filter unchanged (`alternate_query`), the comparison of two
COMPLETE identifier sets (`compare_id_sets`), what may be said when one side is not complete
(`comparison_state`, `difference_words`), the request and unique-study accounting under the acquisition
budget (`comparison_budget`), the retrieval route of each trial (`routes`) and the reading of a record's
condition annotations (`annotation_reading`). The network shell is coverage_run.py. Nothing here reads
pharmacology or the clinical meaning of a term; a trial found only by the alternate search is a candidate
for clinical review, never established disease membership or comparator suitability.
"""

from __future__ import annotations

from typing import Any

from TrialLedger import acquisition

BOUNDARY = (
    "A completed retrieval means the declared search finished, not that every trial of the clinical concept "
    "was found: a record the declared search cannot reach is simply absent, and its absence is not evidence "
    "that no such trial exists."
)
CLASS_CONDITION_ROUTE = (
    "the registry's MeSH annotations of each trial (a condition MeSH term that is the class or has it as an "
    "ancestor)"
)
CLASS_CONDITION_LIMIT = (
    "A trial whose record carries no condition MeSH annotation, or other annotations, cannot match this "
    "search whatever its condition text says; the registry's condition-text search is a different search "
    "and can reach such trials."
)
TEXT_CONDITION_ROUTE = (
    "the registry's own condition-text search (query.cond), which matches text, not a MeSH tree"
)
CATALOGUE_LIMIT = (
    "These are the members RxNav returned for this class in the release named; that does not establish that "
    "every clinically relevant drug is included. A drug RxNav does not list under the class is not searched "
    "unless the person adds it, and an addition is the person's, never RxNav's."
)
ADDITION_ORIGIN = "person_addition"
ADDITION_WORDS = "added by the person; not supplied by RxNav"
# One comparison, whatever its outcome, reads as one of these (comparison_state).
COMPARISON_STATES = ("not_run", "complete", "incomplete", "failed", "snapshot_differs", "not_applicable")
ID_PAGE_SIZE = 1000
DIAGNOSIS_BATCH = 100
DIAGNOSIS_FIELDS = "NCTId,BriefTitle,Condition,Keyword,ConditionBrowseModule"


def alternate_query(scope: Any) -> tuple[str, dict[str, str]]:
    """The registry condition-text query that stands beside a resolved MeSH class search (pure).

    Every other filter is the scope's own, rebuilt from its slots: only the condition-class clause is
    replaced by query.cond with the same term. Returns (code, query):
      ok                              — the alternate query.
      scope_unresolved                — the scope is not resolved, so no query was fixed.
      no_condition_class              — the request holds no condition class: there is nothing to compare.
      condition_text_also_requested   — the request already searches condition text; the two would clash.
      query_not_reproducible          — the slots' clauses do not rebuild the scope's own advanced filter, so
                                        "every other filter unchanged" could not be shown; nothing is built.
    """
    if not isinstance(scope, dict) or scope.get("code") != "resolved":
        return "scope_unresolved", {}
    slots = {slot["slot"]: slot for slot in scope.get("slots", [])}
    if "condition_class" not in slots:
        return "no_condition_class", {}
    if "condition" in slots:
        return "condition_text_also_requested", {}
    query = scope["query"]
    clauses: list[str] = []
    for slot in scope["slots"]:
        if slot["clause"] and slot["slot"] != "condition" and slot["clause"] not in clauses:
            clauses.append(slot["clause"])
    if " AND ".join(clauses) != query.get("filter.advanced", ""):
        return "query_not_reproducible", {}
    kept = [slot["clause"] for slot in scope["slots"] if slot["slot"] not in ("condition_class", "condition")]
    kept = [clause for clause in dict.fromkeys(kept) if clause]
    alternate: dict[str, str] = {}
    if kept:
        alternate["filter.advanced"] = " AND ".join(kept)
    alternate["query.cond"] = slots["condition_class"]["value"]
    alternate |= {name: value for name, value in query.items() if name not in ("filter.advanced",)}
    return "ok", alternate


def unchanged_filters(class_query: dict[str, str], text_query: dict[str, str]) -> bool:
    """Whether two queries differ only in how the condition is searched (pure): every parameter
    other than filter.advanced and query.cond is equal, and the advanced filters differ only by the
    condition-class clause being replaced by query.cond."""
    others = lambda query: {k: v for k, v in query.items() if k not in ("filter.advanced", "query.cond")}  # noqa: E731
    if others(class_query) != others(text_query) or "query.cond" in class_query:
        return False
    return "query.cond" in text_query


def search_coverage(
    request: Any, slots: list[dict[str, Any]], expansions: list[dict[str, Any]]
) -> dict[str, Any]:
    """The coverage statements one resolved scope carries (pure).

    `boundary` always; `condition` when the request searches a condition (its route and limit in words);
    `drug_catalogue` when a drug class or mechanism is expanded (the class, the RxNav release the members
    came from, the members returned, the explicit additions with their origin, and the catalogue limit).
    Empty parts are left out, never filled.
    """
    held: dict[str, Any] = {"boundary": BOUNDARY}
    asked = request if isinstance(request, dict) else {}
    if "condition_class" in asked:
        held["condition"] = {
            "slot": "condition_class",
            "term": asked["condition_class"],
            "route": CLASS_CONDITION_ROUTE,
            "limit": CLASS_CONDITION_LIMIT,
            "alternate_search": "condition_text",
        }
    elif "condition" in asked:
        held["condition"] = {"slot": "condition", "term": asked["condition"], "route": TEXT_CONDITION_ROUTE}
    classed = [e for e in expansions if e.get("kind") == "class" and e.get("code") == "found"]
    if classed:
        returned = [
            row[1]
            for e in expansions
            if e.get("kind") == "subclass_attribution" and e.get("code") == "found"
            for row in e["members"]
            if row[5]
        ]
        added = [
            e["drug"]
            for e in expansions
            if e.get("kind") == "drug_names" and e.get("source_origin") == ADDITION_ORIGIN
        ]
        releases = sorted({e.get("release", "") for e in classed if e.get("release")})
        held["drug_catalogue"] = {
            "catalogue": "RxClass, through RxNav",
            "classes": [
                {"source": e["source"], "id": e["classes"][0][0], "name": e["classes"][0][1]} for e in classed
            ],
            "release": releases[0] if releases else "",
            "members_returned": returned,
            "additions": [
                {
                    "name": name,
                    "origin": ADDITION_ORIGIN,
                    "words": ADDITION_WORDS,
                    "also_listed_by_rxnav": name.casefold() in {m.casefold() for m in returned},
                }
                for name in added
            ],
            "limit": CATALOGUE_LIMIT,
        }
    return held


def coverage_words(coverage: Any) -> list[str]:
    """A scope's coverage statements as plain lines, for the preview and the workbook (pure).
    Not a dictionary of statements, or one with nothing: no line."""
    if not isinstance(coverage, dict) or not coverage:
        return []
    lines = ["Coverage boundary: " + str(coverage.get("boundary", BOUNDARY))]
    condition = coverage.get("condition")
    if isinstance(condition, dict):
        lines.append(f"Condition {condition.get('term')} is searched through {condition.get('route')}.")
        if condition.get("limit"):
            lines.append(str(condition["limit"]))
    catalogue = coverage.get("drug_catalogue")
    if isinstance(catalogue, dict):
        names = ", ".join(catalogue.get("members_returned") or []) or "none"
        release = catalogue.get("release") or "not stated"
        lines.append(
            f"Drug class members, as {catalogue.get('catalogue')} release {release} returned them: {names}."
        )
        for addition in catalogue.get("additions") or []:
            also = "; RxNav also lists it as a member" if addition.get("also_listed_by_rxnav") else ""
            lines.append(f"Also searched: {addition['name']} ({addition['words']}{also}).")
        lines.append(str(catalogue.get("limit", CATALOGUE_LIMIT)))
    return lines


def compare_id_sets(class_ids: list[str], text_ids: list[str]) -> dict[str, Any]:
    """Two COMPLETE identifier sets, compared as sets (pure).

    Counts alone never establish a difference: equal counts can hold different trials, and a repeated
    identifier is one trial. Returns the intersection, class_only and text_only (sorted, each once), the
    counts of unique identifiers on each side and how many repeats were dropped.
    """
    class_set, text_set = set(class_ids), set(text_ids)
    return {
        "intersection": sorted(class_set & text_set),
        "class_only": sorted(class_set - text_set),
        "text_only": sorted(text_set - class_set),
        "class_unique": len(class_set),
        "text_unique": len(text_set),
        "class_repeats_dropped": len(class_ids) - len(class_set),
        "text_repeats_dropped": len(text_ids) - len(text_set),
    }


def comparison_state(
    class_side: dict[str, Any], text_side: dict[str, Any], same_snapshot: bool | None
) -> str:
    """Whether a comparison may be read as a comparison (pure).

    Each side is {"state": complete|incomplete|failed|not_run, ...}; `same_snapshot` is whether both were read
    from one registry data snapshot (None when unknown).
      incomplete       — the class search itself is not complete (nothing to compare with).
      not_run          — the alternate search was never asked.
      failed           — the alternate search failed (an empty or partial id list is then not evidence).
      incomplete       — a side is not complete (stopped by budget, pages not all followed).
      snapshot_differs — both complete, but the registry data changed between them or cannot be told.
      complete         — both sides complete, from one snapshot: the sets may be compared.
    """
    states = (class_side.get("state"), text_side.get("state"))
    if class_side.get("state") != "complete":
        return "incomplete"
    if text_side.get("state") == "not_run":
        return "not_run"
    if "failed" in states:
        return "failed"
    if states != ("complete", "complete"):
        return "incomplete"
    return "complete" if same_snapshot is True else "snapshot_differs"


def difference_words(state: str, comparison: dict[str, Any] | None) -> str:
    """What may be said about additional trials, given the comparison's state (pure).

    Only a complete comparison says anything about differences; an empty text_only is then "none under these
    two declared searches", never "no additional trials exist". Anything else says why nothing is claimed.
    """
    if state == "not_applicable":
        return "No comparison applies: the request holds no condition class to compare with a text search."
    if state != "complete" or comparison is None:
        why = {
            "not_run": "the alternate search was not run",
            "failed": "the alternate search failed",
            "incomplete": "a retrieval did not complete",
            "snapshot_differs": "the two searches were read from different registry snapshots",
        }.get(state, "the comparison did not complete")
        return f"Comparison incomplete ({why}); no statement is made about trials the class search misses."
    both = len(comparison["intersection"])
    only_text, only_class = len(comparison["text_only"]), len(comparison["class_only"])
    if not only_text:
        return (
            "Under these two declared searches the condition-text search found no trial the class search "
            f"missed ({both} in both, {only_class} class-only); this does not show that no other trial "
            "exists."
        )
    return (
        f"The condition-text search found {only_text} trial(s) the class search did not return "
        f"({both} in both, {only_class} class-only). They are candidates for clinical review, not "
        "established disease membership or comparator suitability."
    )


def cumulative_request_count(
    recorded: int, retained_responses: list[str], accounted_responses: list[str]
) -> int:
    """Add newly retained exchanges to recorded attempts without erasing failures (pure).

    pre: type(recorded) is int and recorded >= 0
    post: __return__ >= recorded
    post: __return__ == recorded + len(set(retained_responses) - set(accounted_responses))
    """
    return recorded + len(set(retained_responses) - set(accounted_responses))


def comparison_budget(
    policy: dict[str, int],
    class_total: int | None,
    text_total: int | None,
    spent_requests: int,
    id_page_size: int = ID_PAGE_SIZE,
    diagnosed: int = 0,
    retained_requests: int = 0,
) -> dict[str, Any]:
    """The comparison's cost against the one acquisition budget, before any further page is asked (pure —
    pinned).

    `spent_requests` are the registry requests the class search already made. The comparison adds one
    /version request at each end and the alternate search's identifier pages (`text_total` known after the
    first page; one page assumed before it), plus one request per DIAGNOSIS_BATCH of `diagnosed` trials
    (records read only for their condition annotations, never hydrated). Unique studies are the larger of
    the two searches' totals: the comparison reads identifiers only and hydrates nothing. Returns the plan
    and acquisition.expansion_code's verdict ("within_budget" or the named expansion), equality admissible.
    `spent_requests` includes prior comparison attempts. `retained_requests` counts reusable responses for
    this plan, so only work still missing is reserved; retained evidence is never charged twice.
    """
    pages = max(1, -(-(text_total or 0) // id_page_size))
    added = 2 + pages + (-(-diagnosed // DIAGNOSIS_BATCH) if diagnosed else 0)
    if type(retained_requests) is not int or retained_requests < 0:
        raise ValueError("coverage_invalid_retained_cost")
    remaining = max(0, added - retained_requests)
    unique = max(class_total or 0, text_total or 0)
    verdict = acquisition.expansion_code(
        policy["max_studies"],
        policy["max_registry_requests"],
        None if text_total is None else unique,
        spent_requests,
        spent_requests + remaining,
    )
    return {
        "added_requests": added,
        "retained_requests": retained_requests,
        "remaining_requests": remaining,
        "spent_requests": spent_requests,
        "planned_requests": spent_requests + remaining,
        "unique_studies": unique,
        "max_studies": policy["max_studies"],
        "max_registry_requests": policy["max_registry_requests"],
        "verdict": verdict,
    }


def routes(class_ids: list[str], text_ids: list[str]) -> dict[str, list[str]]:
    """Each trial's retrieval route(s), kept when the sets are merged (pure): "class" when the MeSH
    class search returned it, "text" when the condition-text search did, both when both did. In first-seen
    order, the class search first."""
    held: dict[str, list[str]] = {}
    for route, ids in (("class", class_ids), ("text", text_ids)):
        for nct_id in ids:
            if route not in held.setdefault(nct_id, []):
                held[nct_id].append(route)
    return held


def annotation_state(has_fields: bool, has_values: bool, malformed: bool) -> str:
    """Classify the supplied annotation structure without supplying clinical meaning (pure).

    pre: type(has_fields) is bool and type(has_values) is bool and type(malformed) is bool
    post: __return__ in ('missing', 'empty', 'present', 'malformed')
    post: (__return__ == 'malformed') == malformed
    post: malformed or ((__return__ == 'present') == has_values)
    """
    if malformed:
        return "malformed"
    if has_values:
        return "present"
    return "empty" if has_fields else "missing"


def _annotation_arrays(study: dict) -> tuple[list[str], list[str], str, list[str]]:
    """Read the two supplied term arrays, retaining valid terms beside malformed fields."""
    missing: dict = {}
    derived = study.get("derivedSection", missing)
    if not isinstance(derived, dict):
        return [], [], "malformed", ["/derivedSection"]
    browse = derived.get("conditionBrowseModule", missing)
    if not isinstance(browse, dict):
        return [], [], "malformed", ["/derivedSection/conditionBrowseModule"]
    values: dict[str, list[str]] = {"meshes": [], "ancestors": []}
    problems = []
    for key in values:
        if key not in browse:
            continue
        path = "/derivedSection/conditionBrowseModule/" + key
        rows = browse[key]
        if not isinstance(rows, list):
            problems.append(path)
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("term"), str) or not row["term"]:
                problems.append(f"{path}/{index}")
            else:
                values[key].append(row["term"])
    state = annotation_state(any(key in browse for key in values), any(values.values()), bool(problems))
    return values["meshes"], values["ancestors"], state, problems


def annotation_reading(study: Any, term: str) -> dict[str, Any]:
    """What one record's condition annotations say about a class term (pure).

    Reads only the registry's own fields: derivedSection.conditionBrowseModule's meshes and ancestors, and the
    declared conditions and keywords. `annotation` is "none" (no condition MeSH annotation at all),
    "under_class" (the class term is a MeSH term or ancestor), or "other" (annotated, but not under the
    class). `annotation_state` preserves missing, empty, present and malformed supplied fields. A known
    matching term remains usable beside a malformed field; otherwise malformed annotations are unreadable,
    never "none". A non-object record reads "unreadable".
    """
    if not isinstance(study, dict):
        return {"annotation": "unreadable"}
    protocol = study.get("protocolSection")
    protocol = protocol if isinstance(protocol, dict) else {}
    conditions = protocol.get("conditionsModule")
    conditions = conditions if isinstance(conditions, dict) else {}
    meshes, ancestors, state, problems = _annotation_arrays(study)
    wanted = term.casefold()
    held = [t for t in (*meshes, *ancestors) if isinstance(t, str)]
    if any(t.casefold() == wanted for t in held):
        kind = "under_class"
    elif state == "malformed":
        kind = "unreadable"
    elif not held:
        kind = "none"
    else:
        kind = "other"
    identification = protocol.get("identificationModule")
    identification = identification if isinstance(identification, dict) else {}
    return {
        "nct_id": identification.get("nctId"),
        "title": identification.get("briefTitle"),
        "conditions": conditions.get("conditions") or [],
        "keywords": conditions.get("keywords") or [],
        "mesh_terms": [t for t in meshes if isinstance(t, str)],
        "mesh_ancestors": [t for t in ancestors if isinstance(t, str)],
        "annotation": kind,
        "annotation_state": state,
        "annotation_problems": problems,
    }
