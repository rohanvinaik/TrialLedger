"""Near-miss pairs: two trials alike on a declared representation, differing in exactly one design predicate.

Winston's near miss names the one difference that matters; here it names the one design choice that separates
two otherwise matched trials (add-design-surprise, Decision 5, after Codex's reading): every feature of the
declared representation must be known and equal for both trials (an unknown never matches), exactly one
predicate known for both must differ, and each pair carries the sponsors and start years, because shared
sponsor templates and eras confound. A pair is "one difference under representation R", never a claim that the
trials are otherwise identical, and an outcome difference between them is an association to investigate.
"""

from __future__ import annotations

Trial = tuple[str, dict[str, str], dict[str, str], str, str]  # nct, representation, predicates, sponsor, era


def near_misses(trials: list[Trial]) -> list[tuple[str, str, str, str, str, str, str, str, str, int]]:
    """Every near-miss pair (pure — pinned).

    A trial is (nct, representation, predicates, lead sponsor, start year); a value "" is unknown. Two trials
    pair when their representations have the same keys, every value known and equal, and exactly one
    predicate known for both differs. Returns (nct a, nct b, the differing predicate, its value in a, in b,
    sponsor a, sponsor b, year a, year b, the number of predicates known for both and equal), a before b in
    the order given, pairs in order of a then b.
    """
    groups: dict[tuple, list[Trial]] = {}
    for trial in trials:
        representation = trial[1]
        if not representation or any(value == "" for value in representation.values()):
            continue
        groups.setdefault(tuple(sorted(representation.items())), []).append(trial)
    pairs = []
    for members in groups.values():
        for i, (nct_a, _, predicates_a, sponsor_a, era_a) in enumerate(members):
            for nct_b, _, predicates_b, sponsor_b, era_b in members[i + 1 :]:
                shared = [
                    key
                    for key in predicates_a
                    if key in predicates_b and predicates_a[key] != "" and predicates_b[key] != ""
                ]
                differing = [key for key in shared if predicates_a[key] != predicates_b[key]]
                if len(differing) == 1:
                    key = differing[0]
                    pairs.append(
                        (
                            nct_a,
                            nct_b,
                            key,
                            predicates_a[key],
                            predicates_b[key],
                            sponsor_a,
                            sponsor_b,
                            era_a,
                            era_b,
                            len(shared) - 1,
                        )
                    )
    order = {trial[0]: index for index, trial in enumerate(trials)}
    return sorted(pairs, key=lambda pair: (order[pair[0]], order[pair[1]]))
