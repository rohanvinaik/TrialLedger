"""Named explanatory decisions over computed effects, never new clinical deduction rules."""

from __future__ import annotations

CONTRAST_CODES = (
    "none",
    "selected_out_of_scope",
    "interpretation_out_of_scope",
    "interpretation_scope_contrast",
    "interpretation_answer_contrast",
)


def relation_application_code(
    missing_required: bool, missing_alternative: bool, lines_fit: bool, forbidden: bool
) -> str:
    """An active veto requires all positive requirements, including the line-domain guard.

    post: __return__ in ('missing_required', 'missing_alternative', 'lines_outside', 'guarded', 'applicable')
    post: __return__ != 'applicable' or not (missing_required or missing_alternative)
    post: __return__ != 'applicable' or (lines_fit and not forbidden)
    post: any((missing_required,missing_alternative,not lines_fit,forbidden)) or __return__=='applicable'
    post: __return__ != 'guarded' or not (missing_required or missing_alternative)
    post: __return__ != 'guarded' or (lines_fit and forbidden)
    post: any((missing_required,missing_alternative,not lines_fit,not forbidden)) or __return__=='guarded'
    """
    if missing_required:
        return "missing_required"
    if missing_alternative:
        return "missing_alternative"
    if not lines_fit:
        return "lines_outside"
    return "guarded" if forbidden else "applicable"


def coordinate_effect_code(
    accepted: bool, has_consumer: bool, active: bool, narrowed: bool, guarded: bool
) -> str:
    """Keep admission, missing wiring, positive activation and negative guarding distinct.

    post: __return__ in ('withheld', 'no_consumer', 'inactive', 'narrowed', 'guarded', 'redundant')
    post: (__return__ == 'withheld') == (not accepted)
    post: __return__ != 'narrowed' or (accepted and has_consumer and active and narrowed)
    post: __return__ != 'guarded' or (accepted and has_consumer and not (narrowed and active) and guarded)
    """
    if not accepted:
        return "withheld"
    if not has_consumer:
        return "no_consumer"
    if narrowed and active:
        return "narrowed"
    if guarded:
        return "guarded"
    return "redundant" if active else "inactive"


def interpretation_contrast_code(results: tuple[str, ...], selected: bool) -> str:
    """Describe scope and answer contrasts without altering a common logical verdict.

    post: __return__ in CONTRAST_CODES
    post: __return__ != 'selected_out_of_scope' or (selected and results == ('OUT_OF_SCOPE',))
    post: __return__ != 'interpretation_scope_contrast' or 'OUT_OF_SCOPE' in results
    post: __return__ != 'interpretation_scope_contrast' or len(set(results)) > 1
    """
    if not results:
        return "none"
    if selected and results == ("OUT_OF_SCOPE",):
        return "selected_out_of_scope"
    if "OUT_OF_SCOPE" in results:
        return "interpretation_scope_contrast" if len(set(results)) > 1 else "interpretation_out_of_scope"
    return "interpretation_answer_contrast" if len(set(results)) > 1 else "none"
