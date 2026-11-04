"""Counterexample checks for explicit routing contracts; not clinical source warrants."""

from TrialLedger.layer2.definition_checks import relation_result_code
from TrialLedger.layer2.design_session import revision_change_code
from TrialLedger.layer2.entail import scope_blocker_code


def scope(blocker: str, result: str, connected: bool, deciding: bool) -> str:
    """post: __return__ != 'unrelated_scope' or (blocker.startswith('open_scope:') and not deciding)"""
    return scope_blocker_code(blocker, result, connected, deciding)


def relation(results: list[str], blocked: bool) -> str:
    """post: __return__ != 'consistent' or not blocked
    post: __return__ != 'consistent' or bool(results)
    post: __return__ != 'consistent' or all(x == 'ENTAILED' for x in results)
    """
    return relation_result_code(results, blocked)


def requirements(question_equal: bool, answer_equal: bool, requirements_equal: bool) -> str:
    """post: __return__ != 'requirements_changed' or question_equal
    post: __return__ != 'requirements_changed' or answer_equal
    post: __return__ != 'requirements_changed' or not requirements_equal
    """
    return revision_change_code(
        True, True, True, question_equal, True, answer_equal, True, True, True, False, requirements_equal
    )
