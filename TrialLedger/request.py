"""A user's question as a structured request, resolved symbolically into one registry query
(add-agent-operation, Decisions 4 and 5).

The request is a JSON object of optional slots (REQUEST_SLOTS): `drug` (names), `drug_class` (an RxClass
class, by name or id, with its source: EPC, MoA or ATC), `mechanism` (a target of the sourced crosswalk),
`condition` (a term, searched by the registry's own condition search, query.cond), `condition_class` (a MeSH
descriptor read with everything under it), `phase`, `status`, `study_type`, `start_from`, `start_to` (the
start date's range) and `params` (raw registry parameters for anything else). `request_problems` refuses an
empty request, an unknown slot, a malformed value and a raw parameter `ingest.check_query` refuses, each by a
named code.

Resolution is a pure reading of answers already fetched: nothing here touches the network. `lookups_needed`
names the RxNav requests the request still needs (each as one URL line, the key its answer is held under), and
`resolve_scope` reads the answers into the resolved scope: every slot, every expansion with its source, the
RxNav release and the request it rests on, and the final registry query, or the named codes of what cannot
resolve, so that no registry query is sent for a scope that is short. A drug class resolves to its member
drugs by RxClass (classMembers, the class confirmed first by byName or byId), the class with its subclasses
in the source's own hierarchy (classTree), every subclass listed and each member reached through a subclass
attributed to it, the request excluding subclasses only when it says so; a drug named by the person to its
RxNorm names (its concept's name and, for a salt, a brand or another form of one ingredient, that
ingredient's); a class member to its own name, its ingredient searched only as a member the class lists and
otherwise shown as a candidate; a mechanism to the ATC classes the crosswalk aligns to it, only an entailed
relation expanded, each class confirmed by byId before its members are asked; a condition class to the
registry's own MeSH tree, as the descriptor or an ancestor. Each name is searched in the intervention's name
or its other names. The names of one slot are joined by OR and the slots by AND.

The registry forms emitted are the ones sample.py uses and verified live (AREA[StudyType],
AREA[StartDate]RANGE, AREA[Phase], the condition MeSH term or ancestor, OR groups), and the forms of
NEW_FORMS, each tried live on the date it names (tests/test_request_live.py, counts in
tests/request_query_forms.json).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import quote, urlencode

from TrialLedger.classes import (
    CLASS_SOURCES,
    CROSSWALK,
    RESOLVED,
    RXNAV,
    RXNAV_VERSION,
    RXNORM_IDS,
    RXNORM_PROPERTIES,
    RXNORM_RELATED,
    class_members_request,
    class_tree_request,
    direct_members_request,
    name_identity,
    request_text,
    rxclass_members,
    rxclass_tree,
    rxnav_release,
    rxnorm_concepts,
    rxnorm_ids,
    target_alignment,
)
from TrialLedger.ingest import check_query
from TrialLedger.registry import enum_labels

REQUEST_SLOTS = (
    "drug",
    "drug_class",
    "mechanism",
    "condition",
    "condition_class",
    "phase",
    "status",
    "study_type",
    "start_from",
    "start_to",
    "params",
)
# The slots resolved into filter.advanced; `condition` is the registry's query.cond, `params` is sent as
# given.
ADVANCED_SLOTS = tuple(slot for slot in REQUEST_SLOTS if slot not in ("condition", "params"))
PHASES = tuple(enum_labels("Phase"))
STATUSES = tuple(enum_labels("Status"))
STUDY_TYPES = tuple(enum_labels("StudyType"))
JOIN = "the names of one slot are joined by OR, the slots by AND"
# The registry forms emitted here that sample.py had not verified, each with the date it was tried live and
# returned trials (an unknown status value is refused with HTTP 400; a name no trial holds returns none). A
# drug name is searched in the intervention's name or its other names (the ruling of 2026-11-01: sponsors put
# the identifying name in either), several names grouped inside each area, which the registry answered as it
# answers the names one by one and in half the length (tests/request_query_forms.json).
NEW_FORMS = {
    'AREA[InterventionName]"<name>"': "2026-11-01",
    'AREA[InterventionOtherName]"<name>"': "2026-11-01",
    'AREA[<area>]("<name>" OR "<name>")': "2026-11-01",
    "AREA[OverallStatus]": "2026-11-01",
    "AREA[StartDate]RANGE[<date>,MAX]": "2026-11-01",
    "AREA[StartDate]RANGE[MIN,<date>]": "2026-11-01",
}
# The registry refuses a request line longer than about 8 KB with HTTP 414 (measured 2026-11-01: a URL of
# 8,185 characters answered, one of 8,234 refused). A query whose parameters, written as urlencode with
# quote writes them (letters, digits, "_.-~" and "/" kept, every other byte as %XX), exceed QUERY_LIMIT is not
# sent: the paging parameters TrialLedger adds and a page token need the rest. The measure is no shorter than
# the URL httpx sends (the EPC Kinase Inhibitor query in the grouped name-or-other-name form: 4,071 here; its
# whole URL as sent, with countTotal, pageSize and fields, 3,505, tests/request_query_forms.json; 4,163 and
# 3,919 in the first round's InterventionName-only form).
QUERY_LIMIT = 7000
# What the scope's one RxNav release rests on: version.json is asked once, in the first round; the answers of
# later rounds are not re-dated here. Re-reading it after the last round and refusing a change is the step
# protocol's (add-agent-operation 3.1), as the registry's snapshot is checked.
RELEASE_BASIS = "version.json asked once, in the first round; assumed, not re-read, for the later rounds"
RXCLASS_BY_NAME = f"{RXNAV}/rxclass/class/byName.json"
RXCLASS_BY_CLASS_ID = f"{RXNAV}/rxclass/class/byId.json"


def lookup_url(url: str, params: dict[str, str]) -> str:
    """One RxNav request as one line, the URL with its parameters as asked: the key its answer is held
    under."""
    return request_text({"url": url, "params": params})


def _iso_date(value: Any) -> bool:
    """Whether a value is a calendar date written YYYY-MM-DD, and nothing else (pure — pinned)."""
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def slot_value_ok(slot: str, value: Any) -> bool:
    """Whether one slot's value is well formed (pure — pinned).

    drug: a non-empty list of names, each non-blank and without a double quote (it is quoted in the query).
    drug_class: an object of a source (EPC, MoA or ATC) and exactly one of a name or an id, non-blank, and
    optionally `subclasses`: "include", "exclude" or a non-empty list of non-blank subclass ids to exclude;
    nothing else. mechanism and condition: a non-blank string. condition_class: a non-blank string without a
    double quote. phase and status: a non-empty list of the registry's values (Phase, Status); study_type: one
    StudyType value. start_from and start_to: a date written YYYY-MM-DD. params: a non-empty object of string
    names and values. Any other slot: never.
    """
    if slot in ("mechanism", "condition", "condition_class"):
        return (
            isinstance(value, str) and bool(value.strip()) and (slot != "condition_class" or '"' not in value)
        )
    if slot == "drug":
        return (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(name, str) and name.strip() and '"' not in name for name in value)
        )
    if slot in ("phase", "status"):
        allowed = PHASES if slot == "phase" else STATUSES
        return isinstance(value, list) and bool(value) and all(item in allowed for item in value)
    if slot == "study_type":
        return value in STUDY_TYPES
    if slot in ("start_from", "start_to"):
        return _iso_date(value)
    if slot == "drug_class":
        if not isinstance(value, dict) or not set(value) <= {"name", "id", "source", "subclasses"}:
            return False
        named = [value[key] for key in ("name", "id") if key in value]
        rule = value.get("subclasses", "include")
        return (
            value.get("source") in tuple(CLASS_SOURCES)
            and len(named) == 1
            and isinstance(named[0], str)
            and bool(named[0].strip())
            and (
                rule in ("include", "exclude")
                or (
                    isinstance(rule, list)
                    and bool(rule)
                    and all(isinstance(item, str) and item.strip() for item in rule)
                )
            )
        )
    if slot == "params":
        return (
            isinstance(value, dict)
            and bool(value)
            and all(isinstance(name, str) and isinstance(text, str) for name, text in value.items())
        )
    return False


def request_problems(request: Any) -> tuple[str, list[str]]:
    """Whether a request can be resolved as written (pure — pinned).

    Returns a code and the slots or parameters it concerns, sorted where not in slot order:
      "ok"               — resolve it.
      "not_an_object"    — the request is not a JSON object.
      "empty_request"    — no slot given: it would ask for every registered study.
      "unknown_slot"     — a name that is no slot of REQUEST_SLOTS; nothing is guessed.
      "malformed_value"  — a slot whose value is not of its form (slot_value_ok), or a start_from after the
                           start_to; in slot order.
      "params_<code>"    — the raw parameters, as ingest.check_query refuses them ("params_reserved",
                           "params_empty_value", "params_filters_ignored").
      "params_conflict"  — a raw parameter the slots set themselves: filter.advanced beside any slot resolved
                           into it, or query.cond beside `condition`.
    """
    if not isinstance(request, dict):
        return "not_an_object", []
    if not request:
        return "empty_request", []
    unknown = sorted(str(name) for name in request if name not in REQUEST_SLOTS)
    if unknown:
        return "unknown_slot", unknown
    malformed = [slot for slot in REQUEST_SLOTS if slot in request and not slot_value_ok(slot, request[slot])]
    if not malformed and request.get("start_from", "") > request.get("start_to", "9999-12-31"):
        malformed = ["start_from", "start_to"]
    if malformed:
        return "malformed_value", malformed
    raw = request.get("params", {})
    code, names = check_query(raw) if raw else ("ok", [])
    if code != "ok":
        return f"params_{code}", names
    owned = {"filter.advanced"} if any(slot in request for slot in ADVANCED_SLOTS) else set()
    clash = sorted(set(raw) & (owned | ({"query.cond"} if "condition" in request else set())))
    if clash:
        return "params_conflict", clash
    return "ok", []


def class_request(drug_class: dict[str, str]) -> str:
    """The RxClass request that confirms a requested class: byName (with the source's class type) for a name,
    byId for an id."""
    if "id" in drug_class:
        return lookup_url(RXCLASS_BY_CLASS_ID, {"classId": drug_class["id"]})
    kind = CLASS_SOURCES[drug_class["source"]][0]
    return lookup_url(RXCLASS_BY_NAME, {"className": drug_class["name"], "classTypes": kind})


def class_matches(status: int, body: Any) -> tuple[str, list[list[str]]]:
    """The classes in one RxClass byName or byId response (pure — pinned).

    found        — HTTP 200 and at least one class; each [classId, className, classType], once, sorted.
    not_found    — HTTP 200 and an object without rxclassMinConceptList (RxClass's answer for a name or an id
                   it does not hold, observed 2026-11-01).
    malformed    — HTTP 200 but the body is not an object, the listing is not an object holding a non-empty
                   list, or a class lacks a string id, name or type.
    lookup_failed — any other HTTP status.
    """
    if status != 200:
        return "lookup_failed", []
    if not isinstance(body, dict):
        return "malformed", []
    listing = body.get("rxclassMinConceptList")
    if listing is None:
        return "not_found", []
    entries = listing.get("rxclassMinConcept") if isinstance(listing, dict) else None
    if not isinstance(entries, list) or not entries:
        return "malformed", []
    found: set[tuple[str, str, str]] = set()
    for entry in entries:
        fields = (
            [entry.get(key) for key in ("classId", "className", "classType")]
            if isinstance(entry, dict)
            else []
        )
        if not fields or not all(isinstance(field, str) for field in fields):
            return "malformed", []
        found.add((fields[0], fields[1], fields[2]))
    return "found", [list(match) for match in sorted(found)]


def class_resolution(source: str, code: str, matches: list[list[str]]) -> tuple[str, list[list[str]]]:
    """Which one class a requested drug class is, from class_matches' answer (pure — pinned).

    found                 — exactly one class of the source's class type (CLASS_SOURCES): that class.
    class_ambiguous       — more than one of that type: the candidates, sorted; none is chosen.
    class_source_mismatch — RxClass holds the name or id, but not as a class of that source: the classes it
                            holds, sorted.
    class_not_found       — RxClass holds no such class.
    class_lookup_failed   — the request failed; class_malformed — its answer was malformed. Neither is ever
                            read as "no such class".
    """
    if code in ("lookup_failed", "malformed"):
        return f"class_{code}", []
    if code != "found":
        return "class_not_found", []
    kind = CLASS_SOURCES[source][0]
    fitting = sorted(match for match in matches if match[2] == kind)
    if not fitting:
        return "class_source_mismatch", sorted(matches)
    return ("found" if len(fitting) == 1 else "class_ambiguous"), fitting


def mechanism_rows(mechanism: str) -> tuple[str, list[tuple[str, str, str, str, bool, str, str]]]:
    """The crosswalk rows a requested mechanism names, and whether any is expanded (pure — pinned).

    The mechanism is matched to a crosswalk target letter for letter apart from case and surrounding space.
    Rows are classes.target_alignment's (target, ATC id, ATC name, relation, member, RxClass request, read);
    only a row whose relation entails membership (classes.entails_membership) is expanded into its members.
    found                       — at least one row is expanded; every row is listed, expanded or not.
    mechanism_not_entailed      — the target has rows, none expanded: each listed with its relation.
    mechanism_not_in_crosswalk  — no crosswalk row names the target.
    """
    wanted = mechanism.strip().casefold()
    targets = [target for target in dict.fromkeys(row[0] for row in CROSSWALK) if target.casefold() == wanted]
    if not targets:
        return "mechanism_not_in_crosswalk", []
    rows = target_alignment(targets)
    return ("found" if any(row[4] for row in rows) else "mechanism_not_entailed"), rows


def identity_chain(name: str, answers: dict[str, Any]) -> tuple[list[str], list[tuple[str, list]]]:
    """The RxNorm requests that resolve one drug name's identity, as far as the answers let them go
    (pure — pinned).

    As classes.lookup_axes asks them: the concepts of exactly that name; when there is exactly one, its
    properties; when that one concept is not an ingredient (IN), its related ingredients. Returns (the URLs,
    in order, the first unanswered one last; [ids, concept, ingredients], each as rxnorm_ids and
    rxnorm_concepts read it), a request not to be made being ("not_asked", []) and one made but not yet
    answered ("pending", []).
    """
    urls = [lookup_url(RXNORM_IDS, {"name": name, "search": "0"})]
    parts: list[tuple[str, list]] = [("pending", []), ("not_asked", []), ("not_asked", [])]
    if urls[0] not in answers:
        return urls, parts
    parts[0] = rxnorm_ids(*answers[urls[0]])
    if parts[0][0] != "found" or len(parts[0][1]) != 1:
        return urls, parts
    rxcui = parts[0][1][0]
    urls.append(lookup_url(RXNORM_PROPERTIES.format(rxcui=rxcui), {}))
    if urls[1] not in answers:
        parts[1] = ("pending", [])
        return urls, parts
    parts[1] = rxnorm_concepts(*answers[urls[1]])
    if parts[1][0] != "found" or len(parts[1][1]) != 1 or parts[1][1][0][2] == "IN":
        return urls, parts
    urls.append(lookup_url(RXNORM_RELATED.format(rxcui=rxcui), {"tty": "IN"}))
    parts[2] = rxnorm_concepts(*answers[urls[2]]) if urls[2] in answers else ("pending", [])
    return urls, parts


def member_identity(member: list[str], answers: dict[str, Any]) -> tuple[list[str], list[tuple[str, list]]]:
    """The identity of one class member, already an RxNorm concept (pure — pinned).

    `member` is rxclass_members' (rxcui, name, tty, relation). As identity_chain returns it: its concept is
    the member itself; an ingredient (IN) needs no request; any other member's related ingredients are
    asked.
    """
    rxcui, name, tty = member[0], member[1], member[2]
    parts: list[tuple[str, list]] = [("found", [rxcui]), ("found", [(rxcui, name, tty)]), ("not_asked", [])]
    if tty == "IN":
        return [], parts
    url = lookup_url(RXNORM_RELATED.format(rxcui=rxcui), {"tty": "IN"})
    parts[2] = rxnorm_concepts(*answers[url]) if url in answers else ("pending", [])
    return [url], parts


def subclass_attribution(
    class_id: str,
    members: list[list[Any]],
    tree: list[list[str]],
    direct: dict[str, list[list[Any]]],
    rule: Any,
) -> tuple[str, list[str], list[list[Any]], list[list[Any]]]:
    """Each subclass of a class, each member's subclasses, and which members are searched (pure — pinned).

    A class means the class with its subclasses in the source's own hierarchy, and nothing is hidden.
    `members` are the class's (rxclass_members': rxcui, name, tty, relations); `tree` is rxclass_tree's
    (id, name, type, parent); `direct` maps each subclass id to its own members (rxclass_members' of
    direct_members_request); `rule` is the request's `subclasses`: "include", "exclude" (every subclass) or
    the ids of the subclasses to exclude, each with every subclass under it. A member's `via` is every
    subclass that lists it as DIRECT, in the tree's order ("trastuzumab, via HER2/neu Receptor Antagonist").
    A member the class lists as DIRECT is always searched; any other member is excluded when it has a via and
    every subclass of its via is excluded. Returns (code, detail, subclasses as [id, name, parent, excluded]
    in the tree's order, members as [rxcui, name, tty, relations, via as [[id, name]], searched]):
      found                — every member placed.
      tree_not_of_class    — the tree's top classes are not exactly the class (detail: their ids).
      subclass_not_in_class — an id to exclude is no subclass of the class (detail: those ids, sorted).
      member_unattributed  — a subclass is excluded and a member that is not DIRECT has no via, so whether it
                             is excluded cannot be read (detail: their names).
    """
    roots = [entry[0] for entry in tree if entry[3] == ""]
    if roots != [class_id]:
        return "tree_not_of_class", roots, [], []
    below = [entry for entry in tree if entry[3] != ""]
    ids = list(dict.fromkeys(entry[0] for entry in below))
    if isinstance(rule, list):
        unknown = sorted({item for item in rule if item not in ids})
        if unknown:
            return "subclass_not_in_class", unknown, [], []
        excluded = set(rule)
        for _ in below:
            excluded |= {entry[0] for entry in below if entry[3] in excluded}
    else:
        excluded = set(ids) if rule == "exclude" else set()
    names = {entry[0]: entry[1] for entry in reversed(below)}
    own = {sub_id: {row[0] for row in direct.get(sub_id, []) if "DIRECT" in row[3]} for sub_id in ids}
    rows: list[list[Any]] = []
    unplaced: list[str] = []
    for rxcui, name, tty, relations in members:
        via = [[sub_id, names[sub_id]] for sub_id in ids if rxcui in own[sub_id]]
        dropped = "DIRECT" not in relations and bool(via) and {pair[0] for pair in via} <= excluded
        if excluded and not via and "DIRECT" not in relations:
            unplaced.append(name)
        rows.append([rxcui, name, tty, list(relations), via, not dropped])
    if unplaced:
        return "member_unattributed", unplaced, [], []
    subclasses = [[entry[0], entry[1], entry[3], entry[0] in excluded] for entry in below]
    return "found", [], subclasses, rows


def drug_names(asked: str, source: str, parts: list[tuple[str, list]]) -> tuple[str, list[list[str]]]:
    """The names one drug is searched by, each with its source (pure — pinned).

    `asked` is the name as requested or as RxClass gives a member (its source `source`); `parts` is
    identity_chain's or member_identity's [ids, concept, ingredients].
    pending       — an answer is still awaited: no names yet.
    lookup_failed — a request failed; malformed — an answer was malformed: no names, never the name alone,
                    since the scope would then be silently short.
    otherwise the identity code of classes.name_identity, with the names: the name asked; when RxNorm resolves
    it, its concept's name ("rxnorm_concept"); and when it is a salt, a brand or another form of one
    ingredient, that ingredient's name ("rxnorm_ingredient"). A name already listed, apart from case, is not
    listed again. A combination is searched by its own names, never by one of its ingredients.
    """
    codes = [part[0] for part in parts]
    for code in ("pending", "lookup_failed", "malformed"):
        if code in codes:
            return code, []
    ids, concept, ingredients = ([*part] for part in parts)
    code, _rxcui, _ingredients = name_identity(ids, concept, ingredients)
    named = [(asked, source)]
    if code in RESOLVED:
        named.append((concept[1][0][1], "rxnorm_concept"))
    if code in ("salt", "brand", "other_form"):
        named += [(part[1], "rxnorm_ingredient") for part in ingredients[1]]
    names: list[list[str]] = []
    for name, origin in named:
        if name.casefold() not in {kept[0].casefold() for kept in names}:
            names.append([name, origin])
    return code, names


def member_names(
    member: list[Any], parts: list[tuple[str, list]], listed: list[str]
) -> tuple[str, list[list[str]], list[list[str]]]:
    """The names one class member is searched by, and the names it is not searched by (pure — pinned).

    `member` is rxclass_members' (rxcui, name, tty, relations); `parts` is member_identity's; `listed` are
    the rxcuis of the class's members that are searched. As drug_names reads them, with its codes, except that
    the ingredient of a member that is not itself an ingredient (a salt or a biosimilar, PIN; a brand; another
    form) is never searched for it, since that would widen the class to the ingredient's every form
    (bevacizumab-awwb to bevacizumab admits the reference product's trials): an ingredient the class itself
    lists as a member is searched as that member, and any other is a candidate, [name, "rxnorm_ingredient",
    its relation to the member], shown and not searched. Returns (code, names, candidates).
    """
    code, found = drug_names(member[1], "rxclass_member", parts)
    names = [name for name in found if name[1] != "rxnorm_ingredient"]
    if code not in ("salt", "brand", "other_form"):
        return code, names, []
    held = {name[0].casefold() for name in names}
    relation = f"the ingredient of {member[1]} ({member[2]})"
    candidates = [
        [part[1], "rxnorm_ingredient", relation]
        for part in parts[2][1]
        if part[0] not in listed and part[1].casefold() not in held
    ]
    return code, names, candidates


def any_of(area: str, values: list[str], quoted: bool) -> str:
    """One registry search area holding any of the values: AREA[area]value, joined by OR in parentheses when
    there are several; a quoted value is written in double quotes."""
    terms = [
        f'AREA[{area}]"{value}"' if quoted else f"AREA[{area}]{value}" for value in dict.fromkeys(values)
    ]
    return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"


def name_clause(names: list[str]) -> str:
    """Drug names searched in the intervention's name or its other names (pure — pinned).

    Sponsors put the identifying name in either: (AREA[InterventionName]X OR AREA[InterventionOtherName]X), X
    one quoted name or, for several, the quoted names joined by OR in parentheses, each once, in the order
    first given (NEW_FORMS).
    """
    quoted = [f'"{name}"' for name in dict.fromkeys(names)]
    held = quoted[0] if len(quoted) == 1 else "(" + " OR ".join(quoted) + ")"
    return f"(AREA[InterventionName]{held} OR AREA[InterventionOtherName]{held})"


def condition_clause(term: str) -> str:
    """A MeSH descriptor with everything under it: the condition MeSH term or ancestor, sample.py's form."""
    return f'(AREA[ConditionMeshTerm]"{term}" OR AREA[ConditionAncestorTerm]"{term}")'


def _class_expansion(
    slot: str, drug_class: dict[str, str], answers: dict[str, Any]
) -> tuple[dict[str, Any], str, list[list[str]]]:
    """One class's confirmation as an expansion (its request, its code, the classes RxClass gave), with
    class_resolution's code and classes beside it ("pending" while unanswered)."""
    url = class_request(drug_class)
    found = class_matches(*answers[url]) if url in answers else ("pending", [])
    code, matches = (
        class_resolution(drug_class["source"], *found) if found[0] != "pending" else ("pending", [])
    )
    expansion = {"slot": slot, "kind": "class", "source": drug_class["source"], "request": url}
    return expansion | {"code": code, "classes": matches}, code, matches


def _members_expansion(
    slot: str, class_id: str, source: str, answers: dict[str, Any], asked=class_members_request
) -> tuple[dict[str, Any], list[list[Any]]]:
    """One class's members as an expansion (its request, its code, its members, each member's relations as a
    list), and the members as lists; `asked` builds the request (classMembers, or direct_members_request)."""
    url = lookup_url(*asked(class_id, source))
    code, members = rxclass_members(*answers[url]) if url in answers else ("pending", [])
    listed = [[rxcui, name, tty, list(relations)] for rxcui, name, tty, relations in members]
    expansion: dict[str, Any] = {"slot": slot, "kind": "class_members", "class": class_id, "source": source}
    expansion |= {"request": url, "code": code, "members": listed}
    return expansion, json.loads(json.dumps(listed))


def _subclass_expansions(
    slot: str, class_id: str, source: str, rule: Any, members: tuple[str, list[list[Any]]], answers: dict
) -> tuple[list[dict[str, Any]], list[str], list[list[Any]], list[list[Any]]]:
    """A class's subclasses as expansions, and which of its members are searched (pure — pinned).

    `members` is the class's classMembers answer as read ([code, members], each member a list). Asked in
    order: the class's tree (classTree), then each subclass the tree lists below the class, once, by its own
    members (classMembers with trans=1). Returns (the expansions: class_tree, one subclass_members per
    subclass, and subclass_attribution once read; the requests made, in order; the stops, each [slot, code,
    detail]; the members to search, as [rxcui, name, tty, relations]):
      subclasses_<code>        — the tree is not_found, lookup_failed or malformed (detail: the class id).
      subclass_members_<code>  — a subclass's own members are lookup_failed or malformed (detail: its id).
      subclass_attribution's code, when not found (its detail).
    The attribution is read only when nothing stopped, no answer is pending and the class's members were
    found; until then no member is searched (a class without members is resolve_scope's stop, no_members).
    """
    tree_url = lookup_url(*class_tree_request(class_id))
    tree_code, tree = rxclass_tree(*answers[tree_url]) if tree_url in answers else ("pending", [])
    head = {"slot": slot, "kind": "class_tree", "class": class_id, "source": source, "request": tree_url}
    expansions = [head | {"code": tree_code, "classes": [list(entry) for entry in tree]}]
    lookups, stops = [tree_url], []
    if tree_code in ("not_found", "lookup_failed", "malformed"):
        stops.append([slot, f"subclasses_{tree_code}", [class_id]])
    waiting = "pending" in (tree_code, members[0])
    direct: dict[str, list[list[Any]]] = {}
    for sub_id in dict.fromkeys(entry[0] for entry in tree if entry[3]):
        expansion, own = _members_expansion(slot, sub_id, source, answers, direct_members_request)
        expansion["kind"] = "subclass_members"
        expansions.append(expansion)
        lookups.append(expansion["request"])
        if expansion["code"] in ("lookup_failed", "malformed"):
            stops.append([slot, f"subclass_members_{expansion['code']}", [sub_id]])
        waiting = waiting or expansion["code"] == "pending"
        direct[sub_id] = own
    if stops or waiting or members[0] != "found":
        return expansions, lookups, stops, []
    tree_rows = [list(entry) for entry in tree]
    code, detail, subclasses, rows = subclass_attribution(class_id, members[1], tree_rows, direct, rule)
    head = {"slot": slot, "kind": "subclass_attribution", "class": class_id, "source": source, "rule": rule}
    expansions.append(head | {"code": code, "detail": detail, "subclasses": subclasses, "members": rows})
    if code != "found":
        stops.append([slot, code, detail])
    return expansions, lookups, stops, [row[:4] for row in rows if row[5]]


def resolve_scope(request: Any, answers: dict[str, Any]) -> dict[str, Any]:
    """The resolved scope of a request, read from the RxNav answers already fetched (pure — pinned).

    `answers` maps each request (lookup_url) to its [status, body]. The scope holds the request's check, every
    slot with the clause it resolved to, every expansion (its source, the RxNav release, its request and its
    code), the requests needed so far (`lookups`) and those not yet answered (`pending`), each thing that
    cannot resolve as [slot, code, detail] (`stops`), and, once resolved, the registry query. The release is
    rxnav_release's [code, version, request] of version.json, asked once in the first round, and what it rests
    on is stated (`release_basis`, RELEASE_BASIS); a release RxNav fails to state or states malformed is kept
    as its code, its version "", and stops nothing. Every class, the requested one or one an entailed
    crosswalk row names, is confirmed (class_request) before its members and its tree are asked; then each
    subclass's own members; then subclass_attribution reads which members are searched (every subclass
    listed, each member with the subclasses it is reached through, the request's `subclasses` applied; a
    mechanism's class with all of them), and only those members' names are asked. A class member's ingredient
    is searched only as a member the class lists, never for the member (member_names; the others are its
    expansion's `candidates`). Each slot's names are searched in the intervention's name or other names
    (name_clause). Its code:
      refused          — request_problems refuses the request (its code in `check`).
      unresolved       — something cannot resolve (`stops`): class_not_found, class_ambiguous with the
                         candidates, class_source_mismatch, class_lookup_failed, class_malformed (for the
                         slot drug_class or mechanism), mechanism_not_in_crosswalk, mechanism_not_entailed
                         with the rows, no_members, members_lookup_failed, members_malformed,
                         subclasses_not_found, subclasses_lookup_failed, subclasses_malformed (the tree),
                         subclass_members_lookup_failed, subclass_members_malformed, tree_not_of_class,
                         subclass_not_in_class, member_unattributed (subclass_attribution's),
                         name_lookup_failed, name_malformed, name_not_quotable; or, for the query itself (slot
                         "query"), query_<code> when check_query refuses it and query_too_long, with its
                         escaped length and QUERY_LIMIT, when the registry would refuse its URL. No query is
                         sent, whatever is still pending.
      awaiting_lookups — nothing has failed and an RxNav answer is still awaited (`pending`).
      resolved         — every slot resolved: `query` is the registry query to send.
    """
    check = request_problems(request)
    scope: dict[str, Any] = {"code": "refused", "check": [check[0], list(check[1])], "join": JOIN}
    scope |= {"slots": [], "expansions": [], "lookups": [], "pending": [], "stops": [], "query": {}}
    scope |= {"release": ["not_asked", "", ""], "release_basis": ""}
    if check[0] != "ok":
        return scope
    lookups: list[str] = []
    stops: list[list[Any]] = []
    expansions: list[dict[str, Any]] = []
    # Each drug to name: (slot, name, source, its requests, its identity parts, and for a class member the
    # member itself and the rxcuis of the class's members searched, else None).
    drugs: list[tuple[str, str, str, list[str], list[tuple[str, list]], Any]] = []
    for name in request.get("drug", []):
        urls, parts = identity_chain(name, answers)
        drugs.append(("drug", name, "request", urls, parts, None))
    # Each class is confirmed before its members are asked: the requested one, and each ATC class an entailed
    # crosswalk row names (RxClass answers {} alike for an unknown class id and a class with no member).
    wanted: list[tuple[str, dict[str, Any]]] = []
    if "drug_class" in request:
        wanted.append(("drug_class", request["drug_class"]))
    if "mechanism" in request:
        code, rows = mechanism_rows(request["mechanism"])
        listed = [list(row) for row in rows]
        expansions.append(
            {"slot": "mechanism", "kind": "crosswalk", "source": "classes.CROSSWALK"}
            | {"code": code, "rows": listed}
        )
        if code != "found":
            stops.append(["mechanism", code, listed or [request["mechanism"]]])
        wanted += [("mechanism", {"id": row[1], "source": "ATC"}) for row in rows if row[4]]
    classes: list[tuple[str, str, str, Any]] = []
    for slot, drug_class in wanted:
        expansion, code, matches = _class_expansion(slot, drug_class, answers)
        lookups.append(expansion["request"])
        expansions.append(expansion)
        rule = json.loads(json.dumps(drug_class.get("subclasses", "include")))
        if code == "found":
            classes.append((slot, matches[0][0], drug_class["source"], rule))
        elif code != "pending":
            stops.append([slot, code, matches])
    # A class means the class with its subclasses: each member is searched unless the request excludes every
    # subclass it is reached through (subclass_attribution), and only once every answer about them is in.
    for slot, class_id, source, rule in classes:
        expansion, members = _members_expansion(slot, class_id, source, answers)
        lookups.append(expansion["request"])
        expansions.append(expansion)
        if expansion["code"] == "not_found":
            stops.append([slot, "no_members", [class_id]])
        elif expansion["code"] in ("lookup_failed", "malformed"):
            stops.append([slot, f"members_{expansion['code']}", [class_id]])
        held = (expansion["code"], members)
        more, asked, halted, searched = _subclass_expansions(slot, class_id, source, rule, held, answers)
        expansions += more
        lookups += asked
        stops += halted
        listed = [member[0] for member in searched]
        for member in searched:
            urls, parts = member_identity(member, answers)
            drugs.append((slot, member[1], "rxclass_member", urls, parts, (member, listed)))
    names: dict[str, list[str]] = {}
    for slot, drug, source, urls, parts, membership in drugs:
        lookups += urls
        if membership is None:
            code, found_names = drug_names(drug, source, parts)
            candidates: list[list[str]] = []
        else:
            code, found_names, candidates = member_names(membership[0], parts, membership[1])
        expansions.append(
            {"slot": slot, "kind": "drug_names", "drug": drug, "source": "RxNorm"}
            | {"requests": urls, "code": code, "names": found_names, "candidates": candidates}
        )
        if code in ("lookup_failed", "malformed"):
            stops.append([slot, f"name_{code}", [drug]])
        unquotable = [name for name, _origin in found_names if '"' in name]
        if unquotable:
            stops.append([slot, "name_not_quotable", unquotable])
        names.setdefault(slot, [])
        names[slot] += [name for name, _origin in found_names]
    release_url = lookup_url(RXNAV_VERSION, {})
    release: tuple[str, str] = ("not_asked", "")
    if lookups:
        lookups.insert(0, release_url)
        release = rxnav_release(*answers[release_url]) if release_url in answers else ("pending", "")
    pending = [url for url in dict.fromkeys(lookups) if url not in answers]
    scope |= {"lookups": list(dict.fromkeys(lookups)), "pending": pending, "stops": stops}
    scope["release"] = [release[0], release[1], release_url if lookups else ""]
    scope["release_basis"] = RELEASE_BASIS if lookups else ""
    for expansion in expansions:
        if expansion["kind"] != "crosswalk":
            expansion["release"] = release[1]
    scope["expansions"] = expansions
    clauses: list[str] = []
    for slot in REQUEST_SLOTS:
        if slot not in request:
            continue
        value = json.loads(json.dumps(request[slot]))
        clause = ""
        if slot in ("drug", "drug_class", "mechanism") and names.get(slot):
            clause = name_clause(names[slot])
        elif slot == "condition_class":
            clause = condition_clause(value)
        elif slot in ("phase", "status", "study_type"):
            area = {"phase": "Phase", "status": "OverallStatus", "study_type": "StudyType"}[slot]
            clause = any_of(area, value if isinstance(value, list) else [value], quoted=False)
        elif slot in ("start_from", "start_to"):
            low, high = request.get("start_from", "MIN"), request.get("start_to", "MAX")
            clause = f"AREA[StartDate]RANGE[{low},{high}]"
        elif slot == "condition":
            clause = value
        if clause and slot != "condition" and clause not in clauses:
            clauses.append(clause)
        scope["slots"].append({"slot": slot, "value": value, "clause": clause})
    if stops:
        scope["code"] = "unresolved"
        return scope
    if pending:
        scope["code"] = "awaiting_lookups"
        return scope
    query = {"filter.advanced": " AND ".join(clauses)} if clauses else {}
    query |= {"query.cond": request["condition"]} if "condition" in request else {}
    query |= request.get("params", {})
    verdict, concerned = check_query(query)
    length = len(urlencode(query, quote_via=quote))
    if verdict == "ok" and length > QUERY_LIMIT:
        verdict, concerned = "too_long", [length, QUERY_LIMIT]
    if verdict != "ok":
        scope["stops"] = [["query", f"query_{verdict}", concerned]]
        scope["code"] = "unresolved"
        return scope
    scope["query"] = query
    scope["code"] = "resolved"
    return scope


def lookups_needed(request: Any, answers: dict[str, Any]) -> list[str]:
    """The RxNav requests a request still needs before its scope can resolve (pure — pinned).

    As lookup_url lines, in the order resolution asks them, the RxNav release first whenever any is needed;
    none for a refused request or one whose scope already cannot resolve (resolve_scope's `unresolved`).
    """
    scope = resolve_scope(request, answers)
    return list(scope["pending"]) if scope["code"] == "awaiting_lookups" else []
