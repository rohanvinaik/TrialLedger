"""Import-light public names shared by discovery and transport schemas.

This inventory imports no reporting or reasoning implementation. Actual dispatch coverage is
checked independently so adding a name cannot manufacture a working capability.
"""

REASONING_OPERATIONS = (
    "entailment",
    "coordinates",
    "corpus",
    "design_bounds",
    "evidence_requests",
    "signals",
    "interpretations",
    "source_assertions",
    "design_session",
)
PREPARATION_OPERATIONS = ("prepare",)
OPERATIONS = ("describe", *PREPARATION_OPERATIONS, *REASONING_OPERATIONS)
DISCOVERY_VIEWS = (
    "overview",
    *PREPARATION_OPERATIONS,
    "protocol",
    *REASONING_OPERATIONS,
    "delivery",
    "worked_session",
    "full",
)
REASONING_WORDS = ", ".join(REASONING_OPERATIONS)
