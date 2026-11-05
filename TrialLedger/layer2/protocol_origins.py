"""Copy attributed source readings from the inputs a protocol check actually references.

This is provenance projection, not admission or clinical interpretation. The retained receipt supplies
the gating closure; a source location authenticates neither the reading nor a person's confirmation.
"""

from copy import deepcopy


def source_readings(objects: list[dict], check: dict) -> list[dict]:
    """Source-interpreted check inputs, including linked inputs and named unresolved inputs.

    Origin is an independent channel: this function never changes a verdict, standing or admission.
    Entries describe check inputs, not a claim that every input determines every individual finding.
    """
    identities = list(check.get("objects") or [])
    for child in check.get("children") or []:
        receipt = child.get("receipt") or {}
        identities.extend(receipt.get("closure") or receipt.get("objects") or [])
    for unresolved in check.get("unresolved") or []:
        identities.extend(unresolved.get("objects") or [])
    by_id = {obj["id"]: obj for obj in objects}
    return [
        {"object": identity, "origin": deepcopy(by_id[identity]["origin"])}
        for identity in dict.fromkeys(identities)
        if identity in by_id and (by_id[identity].get("origin") or {}).get("kind") == "source_interpretation"
    ]
