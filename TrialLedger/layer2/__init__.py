"""Symbolic trial-design components, isolated from registry reporting.

``run`` exposes the existing typed reasoning operations. It does not compile clinical
prose, certify the supplied premises, or claim to write a complete new protocol.
"""

from TrialLedger.layer2.service import run

__all__ = ["run"]
