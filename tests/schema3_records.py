"""TEST FIXTURE: landscape.json schema-3 records built from the baseline registry bodies, for the workbook.

The workbook (refine-landscape-record unit C) is built against these until unit A's record lands; the lead
then switches the workbook's tests to A's real records. Nothing here is TrialLedger's record code.

How each part is made:
- every plain field of contract.FIELDS is copied from the saved body (tests/fixtures/contract/studies-*.json)
  by its own API path template, as the registry holds it, nested as the field's name nests it (design §1); a
  value the body does not hold is {"status": "not_stated", "note": "not_reported"}; a results module the body
  does not post is left out, as the contract's example record leaves it out;
- the run fields a reader sees are the rules' own answers: the registry page (links.study_link), PubMed pages
  (links.pubmed_link), document links (links.document_link);
- readings are never synthesized: results_posted (ledger.results_state) and references[].role
  (links.reference_role) are those rules' answers over the body; the universe, drug-class and coordinate
  readings are copied from the contract's hand-checked examples (examples/universes.json, record.json) for
  the trials those examples cover, and absent otherwise;
- the record-level request, scope and manifest are those of a fixture run asking for the trials by number
  (labelled "fixture" where a real run records a value no body holds).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from TrialLedger import contract, landscape, ledger, links, operate, typematrix
from TrialLedger.contract import holds_value, template_values

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
EXAMPLES = FIXTURES / "examples"
BODIES: dict[str, dict[str, Any]] = {
    study["protocolSection"]["identificationModule"]["nctId"]: study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
}
EXAMPLE_RECORD = json.loads((EXAMPLES / "record.json").read_text(encoding="utf-8"))
EXAMPLE_UNIVERSES = json.loads((EXAMPLES / "universes.json").read_text(encoding="utf-8"))
NOT_STATED = {"status": "not_stated", "note": "not_reported"}
STUDY = "studies[]."
# The trials of the mixed-group safety example (examples/safety.json), in its order, then the PTSD trial.
SAMPLE = ("NCT01030536", "NCT02151981", "NCT04852770")


def indexed(body: Any, template: str) -> list[tuple[tuple[int, ...], Any]]:
    """Every node at an API path template with its position in each list it passes through."""
    nodes: list[tuple[tuple[int, ...], Any]] = [((), body)]
    for segment in template.split("."):
        name = segment.removesuffix("[]")
        following = []
        for positions, node in nodes:
            if not isinstance(node, dict) or name not in node:
                continue
            if segment.endswith("[]"):
                held = node[name] if isinstance(node[name], list) else []
                following += [((*positions, i), item) for i, item in enumerate(held)]
            else:
                following.append((positions, node[name]))
        nodes = following
    return nodes


def put(study: dict[str, Any], rest: str, positions: tuple[int, ...], value: Any) -> None:
    """Set `value` at a field's name below the study (lists as "[]"), each list at its position."""
    node: Any = study
    segments = rest.split(".")
    remaining = list(positions)
    for segment in segments[:-1]:
        name = segment.removesuffix("[]")
        if segment.endswith("[]"):
            items = node.setdefault(name, [])
            index = remaining.pop(0)
            items.extend({} for _ in range(index + 1 - len(items)))
            node = items[index]
        else:
            node = node.setdefault(name, {})
    node[segments[-1]] = value


def _offsets(body: dict[str, Any], sources: tuple[str, ...]) -> list[int]:
    """Where each source's first list starts when several sources fill one list (registry order)."""
    offsets, total = [], 0
    for source in sources:
        offsets.append(total)
        head = source.split("[]", 1)[0] + "[]"
        total += len(template_values(body, head))
    return offsets


def _plain(study: dict[str, Any], body: dict[str, Any], field: contract.Field) -> None:
    rest = field.name.removeprefix(STUDY)
    depth = rest.count("[]")
    if field.form in ("distinct", "count"):
        values = template_values(body, field.source[0])
        held = list(dict.fromkeys(values)) if field.form == "distinct" else len(values)
        put(study, rest, (), held if values else NOT_STATED)
        return
    offsets = _offsets(body, field.source)
    for source, offset in zip(field.source, offsets, strict=True):
        if field.form == "which list":
            word = (
                source.rsplit(".", 1)[-1].removesuffix("[]").removesuffix("Outcomes").removesuffix("Events")
            )
            for positions, _item in indexed(body, source):
                put(study, rest, (positions[0] + offset, *positions[1:]), word)
            continue
        if source.count("[]") > depth:
            # The registry's list below the field's own level is the field's value: its held items, in order.
            cut = [i for i, segment in enumerate(source.split(".")) if segment.endswith("[]")]
            split = cut[depth - 1] + 1 if depth else 0
            head, tail = ".".join(source.split(".")[:split]), ".".join(source.split(".")[split:])
            for positions, node in indexed(body, head) if head else [((), body)]:
                items = [item for item in template_values(node, tail) if holds_value(item)]
                moved = (positions[0] + offset, *positions[1:]) if positions else positions
                put(study, rest, moved, items or NOT_STATED)
            continue
        parent, key = source.rsplit(".", 1)
        parents = indexed(body, parent)
        if depth == 0 and not parents:
            if not parent.startswith("resultsSection"):
                put(study, rest, (), NOT_STATED)
            continue
        for positions, node in parents:
            held = node.get(key.removesuffix("[]")) if isinstance(node, dict) else None
            moved = (positions[0] + offset, *positions[1:]) if positions else positions
            put(study, rest, moved, held if holds_value(held) else NOT_STATED)


def reading(
    rule: str, words: list[Any], result: Any, status: str = "known", note: str = ""
) -> dict[str, Any]:
    return {"status": status, "rule": rule, "words": words, "result": result, "note": note}


def study_record(nct: str) -> dict[str, Any]:
    """One study of a schema-3 record, from its saved body (module docstring)."""
    body = BODIES[nct]
    study: dict[str, Any] = {}
    for field in contract.FIELDS:
        if field.name.startswith(STUDY) and field.kind == "plain":
            _plain(study, body, field)
    study["link"] = links.study_link(nct)[1]
    for reference in study.get("references", []):
        pmid = reference.get("pmid")
        page = links.pubmed_link(pmid if isinstance(pmid, str) else None)[1]
        reference["pubmed"] = page or NOT_STATED
        kind = reference.get("type")
        kind = kind if isinstance(kind, str) else None
        reference["role"] = reading("links.reference_role", [kind], links.reference_role(kind))
    for document in study.get("documents", []):
        name = document.get("filename")
        url = links.document_link(nct, name if isinstance(name, str) else None)[1]
        document["url"] = url or NOT_STATED
    state = ledger.results_state(body.get("hasResults"), "resultsSection" in body)
    status = "not_posted" if state == "not_posted" else "known"
    study["results_posted"] = reading("ledger.results_state", [body.get("hasResults")], state, status)
    if nct in EXAMPLE_UNIVERSES:
        study["universe"] = EXAMPLE_UNIVERSES[nct]
    example = next((held for held in EXAMPLE_RECORD["studies"] if held["nct"] == nct), None)
    if example is not None:
        for position, intervention in enumerate(example.get("interventions", [])):
            if "drug_class" in intervention:
                study["interventions"][position]["drug_class"] = intervention["drug_class"]
        if "coordinates" in example:
            study["coordinates"] = example["coordinates"]
    return study


def fields_dictionary() -> dict[str, dict[str, Any]]:
    return {
        field.name: {"label": field.label, "kind": field.kind, "source": list(field.source)}
        for field in contract.FIELDS
    }


def record_of(ncts: tuple[str, ...] = SAMPLE) -> dict[str, Any]:
    """A schema-3 record of the given trials, in that order (module docstring)."""
    studies = [study_record(nct) for nct in ncts]
    ids = ",".join(ncts)
    retrieval = operate.retrieval_coverage(
        "direct", len(ncts), {"filter.ids": ids}, [BODIES[nct] for nct in ncts]
    )
    return {
        "schema_version": contract.SCHEMA_VERSION,
        "request": {"params": {"filter.ids": ids}},
        "scope": {"query": {"filter.ids": ids}},
        "manifest": {
            "api_version": "fixture (no run)",
            "data_timestamp": "2026-11-01",
            "code_commit": "fixture (no run)",
            "rule_versions": {
                "schema": contract.SCHEMA_VERSION,
                "contract": contract.CONTRACT_VERSION,
                "universes": contract.UNIVERSE_TABLE_VERSION,
                "display": contract.DISPLAY_VERSION,
            },
            "retrieval": retrieval,
        },
        "universes": [universe._asdict() for universe in contract.UNIVERSES],
        "coverage": {"universe": typematrix.UNIVERSE},
        "statuses": dict(landscape.STATUSES),
        "fields": fields_dictionary(),
        "studies": studies,
    }
