"""A fake RxNav for the lookup tests: RxNorm's identity answers and RxClass's answers by concept, in the
live service's shapes (read 2026-11-01), every request recorded.

`names` maps a name to the RxNorm concepts of exactly that name; `concepts` maps a concept to its (name, term
type); `ingredients` a non-ingredient concept to its ingredients' concepts; `classes` a concept to the RxClass
entries RxClass holds of it, each (class id, class name, class type, relation, relation source, subject
concept). A request whose name, concept or URL is in `failing` answers 503; `release` is what version.json
answers, or a list of what it answers in turn.
"""

from __future__ import annotations

import threading
from typing import Any

from TrialLedger import classes as rx

RELEASE = {"version": "05-Oct-2026", "apiVersion": "3.1.356"}


class FakeRxNav:
    def __init__(
        self,
        names: dict[str, list[str]],
        concepts: dict[str, tuple[str, str]],
        ingredients: dict[str, list[str]] | None = None,
        classes: dict[str, list[tuple[str, str, str, str, str, str]]] | None = None,
        failing: set[str] | None = None,
        release: Any = None,
    ) -> None:
        self.names, self.concepts = names, concepts
        self.ingredients, self.classes = ingredients or {}, classes or {}
        self.failing = failing or set()
        self.releases = list(release) if isinstance(release, list) else [release or RELEASE]
        self.asked: list[tuple[str, dict[str, str]]] = []
        self.lock = threading.Lock()

    def concept(self, rxcui: str) -> dict[str, str]:
        name, tty = self.concepts[rxcui]
        return {"rxcui": rxcui, "name": name, "tty": tty}

    def __call__(self, url: str, params: dict[str, str]) -> tuple[int, Any]:
        with self.lock:
            self.asked.append((url, dict(params)))
        key = params.get("name") or params.get("rxcui") or url.rsplit("/", 2)[-2]
        if url in self.failing or key in self.failing:
            return 503, None
        if url == rx.RXNAV_VERSION:
            with self.lock:
                return 200, self.releases.pop(0) if len(self.releases) > 1 else self.releases[0]
        if url == rx.RXNORM_IDS:
            held = self.names.get(params["name"])
            return 200, {"idGroup": {"rxnormId": held} if held else {"name": params["name"]}}
        if url.endswith("/properties.json"):
            return 200, {"properties": self.concept(key)}
        if url.endswith("/related.json"):
            parts = [self.concept(part) for part in self.ingredients.get(key, [])]
            return 200, {"relatedGroup": {"conceptGroup": [{"tty": "IN", "conceptProperties": parts}]}}
        if url == rx.RXCLASS_BY_RXCUI:
            entries = [
                {
                    "minConcept": self.concept(subject),
                    "rxclassMinConceptItem": {"classId": cid, "className": name, "classType": kind},
                    "rela": rela,
                    "relaSource": source,
                }
                for cid, name, kind, rela, source, subject in self.classes.get(key, [])
            ]
            return 200, {"rxclassDrugInfoList": {"rxclassDrugInfo": entries}} if entries else {}
        raise AssertionError(f"RxNav was asked what this lookup never asks: {url} {params}")

    def count(self, url: str) -> int:
        return sum(asked == url for asked, _ in self.asked)
