"""Symbolic contracts for scoped handoff decisions, not a whole-system proof."""

from TrialLedger.clinical_export import finding_owner_code
from TrialLedger.reasoning_delivery import adoption_reference_code


def adoption_identity(kind: str, prior: str, current: str, old: str, new: str, ref: str) -> bool:
    """Declarative identity predicate over premise kind, origin kinds and exact references."""
    return all(
        (
            kind == "assertion",
            prior == "user_choice",
            current == "user_choice",
            old != "",
            new != "",
            ref == old,
        )
    )


def adoption(kind: str, prior: str, current: str, old: str, new: str, ref: str) -> str:
    """Exact adoption identity independently specifies both directions.

    post: (_ == 'rebind_adoption') == adoption_identity(kind, prior, current, old, new, ref)
    post: _ in ('rebind_adoption', 'preserve_reference')
    """
    return adoption_reference_code(kind, prior, current, old, new, ref)


def owner(operation: str, address: str, count: int) -> str:
    """Cross-operation identity is never inferred from a shared path name.

    pre: count >= 0
    post: _ in ('operation_result', 'managed_analysis')
    post: operation == 'design_session' or _ == 'operation_result'
    post: _ != 'managed_analysis' or address.startswith('/result/analyses/')
    """
    return finding_owner_code(operation, address, count)
