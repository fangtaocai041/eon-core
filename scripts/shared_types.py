"""Shared enums for eon-core, porpoise-agent, coilia-agent.

Canonical source for VerificationStatus and ContradictionType.
Imported by src/orchestrator_base.py for cross-project data structures.

v7.4 — created during de-dup to fix missing import in orchestrator_base.py.
"""

from __future__ import annotations

from enum import Enum


class VerificationStatus(str, Enum):
    """Verification outcome for a pipeline phase result."""

    UNVERIFIED = "unverified"          # Not yet checked
    VERIFIED = "verified"              # Passed verification
    CONTRADICTED = "contradicted"      # Failed — contradiction found
    NEEDS_REVIEW = "needs_review"      # Uncertain — manual review needed
    STALE = "stale"                    # Previously verified but now outdated


class ContradictionType(str, Enum):
    """Type of contradiction detected between sources.

    Used by: eon-core orchestrator_base, porpoise-agent orchestrator.
    """

    # ── eon-core / coilia-agent ──
    FACTUAL = "factual"                # Conflicting factual claims
    METHODOLOGICAL = "methodological"  # Different methods yield different results
    TEMPORAL = "temporal"              # Time-series data conflict
    SOURCE_QUALITY = "source_quality"  # Conflict due to source reliability
    INTERPRETIVE = "interpretive"      # Same data, different interpretation

    # ── porpoise-agent ──
    NON_ANTAGONISTIC = "non_antagonistic"  # Compatible contradictions (default)
    ANTAGONISTIC = "antagonistic"          # Must resolve — blocks progress
    STRUCTURAL = "structural"              # Inherent system constraint
    PHASIC = "phasic"                      # Phase-boundary transition tension

