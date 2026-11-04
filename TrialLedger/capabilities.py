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
OPERATIONS = ("describe", *REASONING_OPERATIONS)
DISCOVERY_VIEWS = ("overview", *REASONING_OPERATIONS, "worked_session", "full")
REASONING_WORDS = ", ".join(REASONING_OPERATIONS)
