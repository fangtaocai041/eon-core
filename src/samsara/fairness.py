"""FairnessAuditor — 六道公平性审计.

Ensures no agent permanently dominates DEVA realm.
Enforces:
  - Max 25% of agents in DEVA at any time
  - Max 10 cycles stay in DEVA (forced demotion rotation)
  - NARAKA agents have guaranteed rebirth path
  - Nirvana agents are excluded from realm counts

Design pattern: Observer — monitors SamsaraRing for fairness violations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .realms import SamsaraRealm

logger = logging.getLogger(__name__)


class FairnessAuditor:
    """Audit the fairness of realm distribution.

    Independent observer that checks for:
      - DEVA over-concentration (> 25% of agents)
      - DEVA stay duration violations (> 10 cycles)
      - NARAKA stagnation (agents stuck > 5 cycles without rebirth)
      - Equal opportunity: all agents must have a path to DEVA
    """

    MAX_DEVA_FRACTION: float = 0.25
    MAX_DEVA_CYCLES: int = 10
    MAX_NARAKA_CYCLES: int = 5
    AUDIT_INTERVAL_CYCLES: int = 3

    def __init__(self, samsara_ring: Any = None) -> None:
        self.samsara_ring = samsara_ring
        self._violations: List[Dict[str, Any]] = []
        self._audit_count: int = 0

    async def audit(self) -> Dict[str, Any]:
        """Run a full fairness audit.

        Returns:
          {
            "violations": [...],
            "recommendations": [...],
            "deva_fraction": float,
            "total_agents": int,
            "realm_distribution": dict,
          }
        """
        self._audit_count += 1
        violations: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        if self.samsara_ring is None:
            return {
                "violations": [],
                "recommendations": ["samsara_ring not configured"],
                "deva_fraction": 0.0,
                "total_agents": 0,
                "realm_distribution": {},
            }

        counts = self.samsara_ring.realm_counts
        total = sum(counts.values()) or 1
        deva_count = counts.get(SamsaraRealm.DEVA, 0)
        naraka_count = counts.get(SamsaraRealm.NARAKA, 0)
        deva_fraction = deva_count / total

        # Check 1: DEVA over-concentration
        if deva_fraction > self.MAX_DEVA_FRACTION:
            violations.append({
                "type": "DEVA_OVER_CONCENTRATION",
                "severity": "HIGH",
                "detail": (
                    f"DEVA agents: {deva_count}/{total} "
                    f"({deva_fraction:.0%}) exceeds max {self.MAX_DEVA_FRACTION:.0%}"
                ),
            })
            recommendations.append(
                "FORCE_DEMOTION: rotate longest-stay DEVA agents to HUMAN"
            )

        # Check 2: DEVA stay duration
        for agent_id, record in self.samsara_ring.agents.items():
            if record.current_realm == SamsaraRealm.DEVA:
                if record.realm_cycles > self.MAX_DEVA_CYCLES:
                    violations.append({
                        "type": "DEVA_STAY_VIOLATION",
                        "severity": "MEDIUM",
                        "agent_id": agent_id,
                        "detail": (
                            f"Agent {agent_id} in DEVA for {record.realm_cycles} "
                            f"cycles (max {self.MAX_DEVA_CYCLES})"
                        ),
                    })
                    recommendations.append(
                        f"FORCE_DEMOTION: {agent_id} from DEVA to HUMAN"
                    )

        # Check 3: NARAKA stagnation
        for agent_id, record in self.samsara_ring.agents.items():
            if record.current_realm == SamsaraRealm.NARAKA:
                if record.realm_cycles > self.MAX_NARAKA_CYCLES:
                    violations.append({
                        "type": "NARAKA_STAGNATION",
                        "severity": "CRITICAL",
                        "agent_id": agent_id,
                        "detail": (
                            f"Agent {agent_id} stuck in NARAKA for "
                            f"{record.realm_cycles} cycles (max {self.MAX_NARAKA_CYCLES})"
                        ),
                    })
                    recommendations.append(
                        f"FORCE_REBIRTH: {agent_id} from NARAKA to HUMAN immediately"
                    )

        # Check 4: Equal opportunity — is there a path for every agent?
        blocked_agents = [
            aid for aid, rec in self.samsara_ring.agents.items()
            if rec.current_realm == SamsaraRealm.NARAKA and rec.realm_cycles > 3
        ]
        if blocked_agents:
            recommendations.append(
                f"UNBLOCK: agents {blocked_agents} need escalated rebirth review"
            )

        self._violations.extend(violations)

        return {
            "audit_cycle": self._audit_count,
            "violations": violations,
            "recommendations": recommendations,
            "deva_fraction": deva_fraction,
            "total_agents": total,
            "realm_distribution": {
                realm.value: count for realm, count in counts.items()
            },
        }

    def get_violation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent violation history."""
        return self._violations[-limit:]

    def clear_violations(self) -> None:
        """Clear violation history (e.g., after all resolved)."""
        self._violations.clear()
