"""The one owner of the protocol outcome classifications (a dependency-free leaf).

Policy failures are conflicts (incompatible, blocking); schedule gaps and an unmet binomial target are the
person's repair choice, in comparisons as in the clinical labels (Rohan, 2026-11-04). Every protocol
consumer (decisions, the clinical view, delivery) imports these sets instead of restating them.
"""

from __future__ import annotations

CONFLICT_OUTCOMES = frozenset({"gap", "competing", "violation", "not_established", "inconsistent_domain"})
REPAIR_OUTCOMES = frozenset(
    {"no_feasible_time", "no_permitted_time", "outside_window", "not_collected", "uncovered", "not_satisfied"}
)
CONFLICT_CODES = frozenset({"conflict", "inconsistent", "violated"})
