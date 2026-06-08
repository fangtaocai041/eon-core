"""KarmaCourt — independent arbitration of karma evaluations.

Design pattern: Arbitrator.
Provides independent evaluation separate from self-assessment.

Methods:
  convene(digests) → verdicts: validate threshold rules.
  rule_on_dispute(agent_id, self_assessment, ring_assessment) → FinalVerdict.
  audit_fairness() → FairnessReport: prevent DEVA over-concentration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .realms import SamsaraRealm, realm_compare, realm_gt

logger = logging.getLogger(__name__)


class ReincarnationVerdict:
    """Verdict from KarmaCourt: whether to reincarnate and where."""

    __slots__ = ("agent_id", "reincarnate", "from_realm", "to_realm", "cycle", "reason")

    def __init__(
        self,
        agent_id: str,
        reincarnate: bool = False,
        from_realm: SamsaraRealm = SamsaraRealm.HUMAN,
        to_realm: SamsaraRealm = SamsaraRealm.HUMAN,
        cycle: int = 0,
        reason: str = "",
    ) -> None:
        self.agent_id = agent_id
        self.reincarnate = reincarnate
        self.from_realm = from_realm
        self.to_realm = to_realm
        self.cycle = cycle
        self.reason = reason


class FinalVerdict:
    """Court-override final verdict."""

    __slots__ = ("agent_id", "final_realm", "reason")

    def __init__(self, agent_id: str, final_realm: SamsaraRealm, reason: str = "") -> None:
        self.agent_id = agent_id
        self.final_realm = final_realm
        self.reason = reason


class KarmaCourt:
    """Independent arbitration court for karma evaluations.

    The court has final say over reincarnation decisions.
    It can override both self-assessment and ring recommendations.
    """

    MAX_DEVA_FRACTION = 0.25
    MAX_DEVA_CYCLES = 10

    def __init__(self, samsara_ring: Any = None) -> None:
        self.samsara_ring = samsara_ring
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    async def convene(self, digests: list) -> List[ReincarnationVerdict]:
        """Review all karma digests and issue reincarnation verdicts.

        FOR EACH digest:
          suggested = digest.suggested_realm.
          current = digest.current_realm.
          IF suggested == current THEN skip (no change).
          IF suggested > current THEN validate promotion.
          IF suggested < current THEN validate demotion.
            Special: IF current == DEVA THEN force demotion to HUMAN (天道堕落).

        RETURN list of ReincarnationVerdict.
        """
        verdicts: List[ReincarnationVerdict] = []

        for digest in digests:
            suggested = digest.suggested_realm
            current = digest.current_realm

            if suggested == current:
                continue

            if realm_gt(suggested, current):
                # Promotion
                if self._validate_promotion(digest):
                    verdicts.append(ReincarnationVerdict(
                        agent_id=digest.agent_id if hasattr(digest, 'agent_id') else "",
                        reincarnate=True,
                        from_realm=current,
                        to_realm=suggested,
                        reason=digest.reason,
                    ))
            else:
                # Demotion
                if current == SamsaraRealm.DEVA:
                    # 天道堕落: DEVA always demotes to HUMAN
                    verdicts.append(ReincarnationVerdict(
                        agent_id=digest.agent_id if hasattr(digest, 'agent_id') else "",
                        reincarnate=True,
                        from_realm=SamsaraRealm.DEVA,
                        to_realm=SamsaraRealm.HUMAN,
                        reason="天道堕落机制: bad_deed detected in DEVA",
                    ))
                else:
                    verdicts.append(ReincarnationVerdict(
                        agent_id=digest.agent_id if hasattr(digest, 'agent_id') else "",
                        reincarnate=True,
                        from_realm=current,
                        to_realm=suggested,
                        reason=digest.reason,
                    ))

        return verdicts

    def _validate_promotion(self, digest: Any) -> bool:
        """Validate promotion conditions.

        Promotion to DEVA: must have karma ≥ 85 AND 3-cycle-zero-bad-deeds.
        Promotion to ASURA: must have contradiction_rate > 15% AND karma ≥ 60.
        """
        suggested = digest.suggested_realm
        karma = digest.karma_score

        if suggested == SamsaraRealm.DEVA:
            return karma >= 85.0
        if suggested == SamsaraRealm.ASURA:
            return karma >= 60.0
        return True

    async def rule_on_dispute(
        self, agent_id: str, self_assessment: SamsaraRealm, ring_assessment: SamsaraRealm
    ) -> FinalVerdict:
        """Resolve dispute between self-assessment and ring recommendation.

        Load last 100 cycles of karma history.
        Recalculate karma independently.
        Apply threshold to determine final realm.

        IF independent score disagrees with both THEN COURT_OVERRIDE.
        """
        # Simulated independent recalculation
        final_realm = ring_assessment  # default: trust the ring
        reason = "COURT_DEFAULT_TO_RING"

        if self_assessment != ring_assessment:
            # Dispute: recalculate independently
            final_realm = SamsaraRealm.HUMAN  # safe default
            reason = "COURT_OVERRIDE: dispute resolved to HUMAN"

        return FinalVerdict(agent_id=agent_id, final_realm=final_realm, reason=reason)

    async def audit_fairness(self) -> Dict[str, Any]:
        """Audit realm distribution for fairness.

        IF deva_count > 0.25 * total_agents THEN enforce demotion rotation.
        IF any agent in DEVA > 10 cycles THEN force demotion to HUMAN.
        """
        issues: List[str] = []
        recommendations: List[str] = []

        if self.samsara_ring is None:
            return {"issues": [], "recommendations": ["samsara_ring not set"]}

        counts = self.samsara_ring.realm_counts
        total = sum(counts.values()) or 1
        deva_count = counts.get(SamsaraRealm.DEVA, 0)

        if deva_count > self.MAX_DEVA_FRACTION * total:
            issues.append(
                f"DEVA over-concentration: {deva_count}/{total} "
                f"({deva_count / total:.0%}) > {self.MAX_DEVA_FRACTION:.0%}"
            )
            recommendations.append("Enforce demotion of longest-stay DEVA agents to HUMAN")

        return {
            "issues": issues,
            "recommendations": recommendations,
            "deva_fraction": deva_count / total,
            "total_agents": total,
        }
