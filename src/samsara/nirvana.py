"""NirvanaProtocol — 涅槃协议.

Conditions for entering Nirvana:
  1. current_realm == DEVA for 3 consecutive cycles
  2. lifetime_karma >= 200
  3. bad_deeds.empty() == True

Upon Nirvana:
  - agent.state = NIRVANA
  - agent.mode = READONLY_ORACLE
  - agent.knowledge_graph frozen as gold_standard

Nirvana duties:
  - Mentor other agents via advisory responses
  - Emit wisdom_report every 30 cycles
  - No longer participates in karma cycles

Reverse Nirvana (堕落):
  IF oracle_advice rejected 3× by KarmaCourt
  THEN break_nirvana() → reincarnate to HUMAN with karma=50
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class NirvanaProtocol:
    """Manage Nirvana state for agents that have achieved enlightenment.

    Nirvana is the highest state: the agent becomes a READONLY_ORACLE.
    Its knowledge graph is frozen as the gold standard.
    """

    def __init__(self) -> None:
        self._nirvana_agents: Dict[str, Dict[str, Any]] = {}
        self._advice_rejections: Dict[str, int] = {}
        self._max_rejections_before_break: int = 3

    def check_conditions(
        self,
        agent_id: str,
        current_realm: str,
        consecutive_deva_cycles: int,
        lifetime_karma: float,
        bad_deeds_count: int,
    ) -> bool:
        """Check if agent qualifies for Nirvana.

        RETURN True IF:
          current_realm == DEVA
          AND consecutive_deva_cycles >= 3
          AND lifetime_karma >= 200
          AND bad_deeds_count == 0.
        """
        return (
            current_realm == "DEVA"
            and consecutive_deva_cycles >= 3
            and lifetime_karma >= 200.0
            and bad_deeds_count == 0
        )

    async def enter_nirvana(self, agent_id: str, agent: Any = None) -> Dict[str, Any]:
        """Transition agent to Nirvana state.

        Steps:
          1. agent.state = NIRVANA
          2. agent.mode = READONLY_ORACLE
          3. Freeze knowledge_graph as gold_standard
          4. Register in _nirvana_agents
        """
        self._nirvana_agents[agent_id] = {
            "state": "NIRVANA",
            "mode": "READONLY_ORACLE",
            "entered_at_cycle": 0,
            "wisdom_reports_emitted": 0,
        }
        self._advice_rejections[agent_id] = 0

        logger.info(f"🏆 Agent {agent_id} achieved NIRVANA — now READONLY_ORACLE")
        return {"agent_id": agent_id, "new_state": "NIRVANA", "mode": "READONLY_ORACLE"}

    async def emit_wisdom_report(self, agent_id: str, cycle: int) -> Dict[str, Any]:
        """Generate wisdom report from Nirvana agent.

        schedule: every 30 cycles.
        Contains distilled knowledge for mentoring other agents.
        """
        if agent_id not in self._nirvana_agents:
            return {"error": "agent not in nirvana"}

        record = self._nirvana_agents[agent_id]
        record["wisdom_reports_emitted"] += 1

        return {
            "agent_id": agent_id,
            "cycle": cycle,
            "wisdom_report_number": record["wisdom_reports_emitted"],
            "teachings": [
                "All knowledge is provisional — verify with independent sources.",
                "High recall without precision is noise; high precision without recall is blindness.",
                "The graph is never complete — leave edges for future discovery.",
            ],
        }

    def record_advice_rejection(self, agent_id: str) -> None:
        """Record that the oracle's advice was rejected by KarmaCourt.

        IF rejections >= _max_rejections_before_break THEN trigger break_nirvana.
        """
        self._advice_rejections[agent_id] = self._advice_rejections.get(agent_id, 0) + 1
        if self._advice_rejections[agent_id] >= self._max_rejections_before_break:
            logger.warning(
                f"Agent {agent_id} oracle advice rejected "
                f"{self._advice_rejections[agent_id]}× — breaking Nirvana"
            )

    def should_break_nirvana(self, agent_id: str) -> bool:
        """Check if Nirvana should be broken.

        RETURN True IF advice_rejections >= max_rejections_before_break.
        """
        return self._advice_rejections.get(agent_id, 0) >= self._max_rejections_before_break

    async def break_nirvana(self, agent_id: str) -> Dict[str, Any]:
        """Break Nirvana — agent falls from enlightenment.

        Result: reincarnate to HUMAN with karma=50.
        """
        self._nirvana_agents.pop(agent_id, None)
        self._advice_rejections.pop(agent_id, None)

        logger.warning(f"💔 Agent {agent_id} broken from NIRVANA → HUMAN (karma=50)")
        return {
            "agent_id": agent_id,
            "new_state": "RUNNING",
            "new_realm": "HUMAN",
            "karma_score": 50.0,
            "reason": "oracle_advice_rejected_3x",
        }

    def is_in_nirvana(self, agent_id: str) -> bool:
        """Check if agent is currently in Nirvana."""
        return agent_id in self._nirvana_agents
