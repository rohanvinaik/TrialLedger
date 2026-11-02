"""Versioned MeSH identities and pure indication scope, never a clinical category classifier.

MeSH terms are strictly synonymous within one concept, not across every concept of a descriptor:
https://hhs.github.io/meshrdf/terms . This adapter accepts a descriptor's own label or a term of its
preferred concept only. Nonpreferred-concept identities require a separately typed relation and abstain here.
SPARQL/versioned graph contract: https://hhs.github.io/meshrdf/sparql-and-uri-requests .
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API_VERSION = "1.0.1"
RULE_VERSION = "indication-scope/1"
MESH = "https://id.nlm.nih.gov/mesh"
LIMIT = 1000


@dataclass(frozen=True)
class MeshIdentity:
    descriptor: str
    label: str
    trees: tuple[str, ...]
    year: str


@dataclass(frozen=True)
class SourceEvidence:
    url: str
    year: str
    retrieved_at: str
    digest: str
    body_b64: str
    api_version: str = API_VERSION


@dataclass(frozen=True)
class LookupResult:
    code: str
    identities: tuple[MeshIdentity, ...] = ()
    sources: tuple[SourceEvidence, ...] = ()


def lookup_url(label: str, year: str) -> str:
    """Exact descriptor/preferred-concept term query; JSON encoding prevents query injection."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("invalid_label")
    if not isinstance(year, str) or not re.fullmatch(r"[0-9]{4}", year):
        raise ValueError("fixed_mesh_year_required")
    literal = json.dumps(label.strip(), ensure_ascii=False)
    query = f"""PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?descriptor ?label ?tree FROM <http://id.nlm.nih.gov/mesh/{year}> WHERE {{
?descriptor a meshv:TopicalDescriptor; rdfs:label ?label; meshv:treeNumber ?tree.
{{ FILTER(LCASE(STR(?label)) = LCASE({literal})) }} UNION {{
?descriptor meshv:preferredConcept ?concept.
?concept meshv:term ?term.
?term (meshv:prefLabel|meshv:altLabel|rdfs:label) ?termLabel.
FILTER(LCASE(STR(?termLabel)) = LCASE({literal}))
}}
}}"""
    return (
        MESH + "/sparql?" + urlencode({"query": query, "format": "JSON", "year": year, "limit": str(LIMIT)})
    )


def parse_response(body: bytes, year: str) -> LookupResult:
    """Parse the whole SPARQL answer; malformed/truncated input never establishes an indication."""
    try:
        data = json.loads(body)
    except (ValueError, TypeError, UnicodeDecodeError):
        return LookupResult("malformed")
    rows = (
        data.get("results", {}).get("bindings")
        if isinstance(data, dict) and isinstance(data.get("results"), dict)
        else None
    )
    if not isinstance(rows, list):
        return LookupResult("malformed")
    if len(rows) >= LIMIT:
        return LookupResult("result_limit")
    found: dict[str, tuple[str, set[str]]] = {}
    prefix = f"http://id.nlm.nih.gov/mesh/{year}/"
    for row in rows:
        if not isinstance(row, dict):
            return LookupResult("malformed")
        descriptor, label, tree = (row.get(key) for key in ("descriptor", "label", "tree"))
        if not all(isinstance(part, dict) for part in (descriptor, label, tree)):
            return LookupResult("malformed")
        assert isinstance(descriptor, dict) and isinstance(label, dict) and isinstance(tree, dict)
        uri, name, tree_uri = (part.get("value") for part in (descriptor, label, tree))
        if (
            descriptor.get("type") != "uri"
            or label.get("type") != "literal"
            or tree.get("type") != "uri"
            or not isinstance(uri, str)
            or not uri.startswith(prefix)
            or not re.fullmatch(r"D[0-9]+", uri.removeprefix(prefix))
            or not isinstance(name, str)
            or not name.strip()
            or not isinstance(tree_uri, str)
            or not tree_uri.startswith(prefix)
            or not re.fullmatch(r"[A-Z][0-9]{2}(?:\.[0-9]{3})*", tree_uri.removeprefix(prefix))
        ):
            return LookupResult("malformed")
        identifier = uri.removeprefix(prefix)
        if identifier in found and found[identifier][0] != name:
            return LookupResult("malformed")
        found.setdefault(identifier, (name, set()))[1].add(tree_uri.removeprefix(prefix))
    identities = tuple(
        MeshIdentity(key, name, tuple(sorted(trees)), year) for key, (name, trees) in sorted(found.items())
    )
    return LookupResult(
        "resolved" if len(identities) == 1 else "ambiguous" if identities else "not_found", identities
    )


def is_disease(identity: MeshIdentity) -> bool:
    """Declared scope policy: disease C except C23 processes, or F03 mental disorders."""
    return any(
        (tree.startswith("C") and not tree.startswith("C23")) or tree == "F03" or tree.startswith("F03.")
        for tree in identity.trees
    )


def relation(left: MeshIdentity, right: MeshIdentity) -> str:
    """Typed tree relation, never a contradiction from an extra/unrelated descriptor."""
    if left.year != right.year or not left.trees or not right.trees:
        return "scope_unresolved"
    if left.descriptor == right.descriptor:
        return "equivalent"
    broader = any(b.startswith(a + ".") for a in left.trees for b in right.trees)
    narrower = any(a.startswith(b + ".") for a in left.trees for b in right.trees)
    if broader and narrower:
        return "scope_unresolved"
    if broader:
        return "compatible_broader"
    if narrower:
        return "compatible_narrower"
    return "unexplained_discrepancy"


def resolve_indication(
    conditions: list[str],
    lookups: dict[str, LookupResult],
    declared_indications: tuple[str, ...],
    registry_mesh: tuple[MeshIdentity, ...] = (),
    own_assertions: tuple[MeshIdentity, ...] = (),
) -> dict:
    """Pure pack scope. Declared IDs include any explicitly covered narrower descriptors.

    Unread/ambiguous condition sources prevent lower-priority derived MeSH from authorizing a pack.
    An established indication within a pack authorizes it; a broader term cannot deny or authorize a
    narrower pack. Without a comparable declared descriptor's tree evidence, a nonmatching ID abstains.
    """
    sources = [
        {
            "text": text,
            "code": lookups.get(text, LookupResult("not_looked_up")).code,
            "identities": [asdict(i) for i in lookups.get(text, LookupResult("not_looked_up")).identities],
            "sources": [asdict(s) for s in lookups.get(text, LookupResult("not_looked_up")).sources],
        }
        for text in conditions
    ]
    established = tuple(
        i
        for text in conditions
        if text in lookups and lookups[text].code == "resolved"
        for i in lookups[text].identities
        if is_disease(i)
    )
    unread = any(row["code"] not in ("resolved", "not_found") for row in sources)
    decided_by = "conditions" if established else ""
    if not established and not unread:
        established = tuple(i for i in own_assertions if is_disease(i))
        decided_by = "own_assertions" if established else ""
    # No condition at all may use registry-derived evidence; a stated unrecognized condition stays unresolved.
    if not established and not conditions and not unread:
        established = tuple(i for i in registry_mesh if is_disease(i))
        decided_by = "registry_mesh" if established else ""
    declared = tuple(
        i
        for answer in lookups.values()
        if answer.code == "resolved"
        for i in answer.identities
        if i.descriptor in declared_indications and is_disease(i)
    )
    matching = [i.descriptor for i in established if i.descriptor in declared_indications]
    if matching:
        code = "applicable"
    elif (
        not established
        or not declared
        or unread
        or any(
            relation(i, target) in ("compatible_broader", "scope_unresolved")
            for i in established
            for target in declared
        )
    ):
        code = "scope_unresolved"
    else:
        code = "inapplicable"
    discrepancies = [
        {"established": i.descriptor, "registry": j.descriptor, "relation": relation(i, j)}
        for i in established
        for j in registry_mesh
    ]
    return {
        "code": code,
        "rule": RULE_VERSION,
        "decided_by": decided_by,
        "conditions": list(conditions),
        "indications": [asdict(i) for i in established],
        "declared_indications": list(declared_indications),
        "sources": sources,
        "relationships": discrepancies,
    }


class MeshLookup:
    """Sequential, fixed-year adapter. Cache verifies URL, year, body digest and parser version on replay.

    One instance performs requests serially; scheduling across instances belongs to the run integrator.
    Failures remain retryable; negative valid responses are cached. No model reads source material.
    """

    def __init__(
        self, cache: Path, *, year: str = "2026", fetch: Callable[[str], bytes] | None = None
    ) -> None:
        lookup_url("validation", year)
        self.cache, self.year, self.fetch = cache, year, fetch or self._fetch

    @staticmethod
    def _fetch(url: str) -> bytes:
        with urlopen(url, timeout=30) as response:
            return response.read()

    def lookup(self, label: str) -> LookupResult:
        try:
            url = lookup_url(label, self.year)
        except ValueError:
            return LookupResult("malformed_request")
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.exists():
            try:
                saved = json.loads(path.read_bytes())
                source = SourceEvidence(**saved)
                body = base64.b64decode(source.body_b64, validate=True)
                if (
                    source.url != url
                    or source.year != self.year
                    or source.api_version != API_VERSION
                    or source.digest != hashlib.sha256(body).hexdigest()
                    or not source.retrieved_at
                ):
                    return LookupResult("cache_invalid")
            except (ValueError, TypeError, OSError):
                return LookupResult("cache_invalid")
        else:
            try:
                body = self.fetch(url)
            except (OSError, TimeoutError):
                return LookupResult("unavailable")
            if not isinstance(body, bytes):
                return LookupResult("malformed")
            source = SourceEvidence(
                url,
                self.year,
                datetime.now(UTC).isoformat(),
                hashlib.sha256(body).hexdigest(),
                base64.b64encode(body).decode("ascii"),
            )
        answer = parse_response(body, self.year)
        self.cache.mkdir(parents=True, exist_ok=True)
        if answer.code in ("resolved", "ambiguous", "not_found"):
            if not path.exists():
                path.write_text(json.dumps(asdict(source), sort_keys=True) + "\n")
        else:
            # Keep failed source bytes for review. Malformed/truncated replies never become cache hits.
            failed = self.cache / "failures"
            failed.mkdir(exist_ok=True)
            quarantine = failed / f"{key}-{source.digest}.json"
            if path.exists():
                path.replace(quarantine)
            elif not quarantine.exists():
                quarantine.write_text(json.dumps(asdict(source), sort_keys=True) + "\n")
        return LookupResult(answer.code, answer.identities, (source,))
