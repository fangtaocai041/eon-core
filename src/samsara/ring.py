"""SamsaraRing — 六道轮回环管理.

Manages all agents' karma cycles every 60 seconds:
  1. FOR EACH agent: evaluate karma → digest.
  2. KarmaCourt convenes → verdicts.
  3. FOR EACH verdict WHERE reincarnate:
     ReincarnationProtocol.execute(agent, from_realm, to_realm).
  4. Increment cycle counter.
  5. Publish metrics.

Rotation: ω = 0.005 rad/s (slow rotation of the hexagon).
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .karma_engine import KarmaEngine, KarmaVerdict
from .realms import SamsaraRealm
from .court import KarmaCourt
from .reincarnation import ReincarnationProtocol

logger = logging.getLogger(__name__)


class SamsaraAgentRecord:
    """Record for each registered agent in the samsara ring."""

    __slots__ = ("agent_id", "karma_engine", "current_realm", "realm_cycles",
                 "reincarnation_count", "nirvana")

    def __init__(self, agent_id: str, karma_engine: KarmaEngine) -> None:
        self.agent_id = agent_id
        self.karma_engine = karma_engine
        self.current_realm = SamsaraRealm.HUMAN
        self.realm_cycles = 0
        self.reincarnation_count = 0
        self.nirvana = False


@dataclass
class ReincarnationEvent:
    agent_id: str
    from_realm: SamsaraRealm
    to_realm: SamsaraRealm
    cycle: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


@dataclass
class CycleReport:
    cycle: int
    verdicts: list
    realm_counts: Dict[SamsaraRealm, int]
    reincarnations: int = 0


class SamsaraRing:
    """六道轮回环 — manages karma cycles for all agents.

    schedule: every 60 seconds (KARMA_CYCLE).
    """

    def __init__(self, event_bus: Any = None) -> None:
        self.agents: Dict[str, SamsaraAgentRecord] = {}
        self.realm_counts: Dict[SamsaraRealm, int] = {
            r: 0 for r in SamsaraRealm
        }
        self.cycle_counter: int = 0
        self.reincarnation_log: deque[ReincarnationEvent] = deque(maxlen=5000)
        self.karma_court = KarmaCourt(self)
        self.reincarnation_protocol = ReincarnationProtocol()
        self.event_bus = event_bus
        self.rotation_angle: float = 0.0
        self.rotation_speed: float = 0.005  # rad/s

    async def register_agent(self, agent_id: str, initial_karma: float = 50.0) -> None:
        """Register a new agent in the samsara ring.

        IF agent already registered THEN warn and skip.
        """
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already registered in SamsaraRing")
            return

        engine = KarmaEngine(agent_id=agent_id)
        engine.karma_score = initial_karma
        engine.current_realm = SamsaraRealm.HUMAN

        record = SamsaraAgentRecord(agent_id=agent_id, karma_engine=engine)
        self.agents[agent_id] = record
        self.realm_counts[SamsaraRealm.HUMAN] += 1
        logger.info(f"Agent {agent_id} registered in SamsaraRing (karma={initial_karma})")

    async def run_karma_cycle(self) -> CycleReport:
        """Execute one full karma cycle.

        Step 1: FOR EACH agent: evaluate_cycle() → KarmaDigest.
        Step 2: KarmaCourt.convene(digests) → verdicts.
        Step 3: FOR EACH verdict WHERE reincarnate:
                  ReincarnationProtocol.execute(agent, from, to).
        Step 4: Increment cycle_counter.
        Step 5: Publish metrics.
        """
        self.cycle_counter += 1

        # Step 1: Evaluate all agents
        digests: List[KarmaVerdict] = []
        for agent_id, record in self.agents.items():
            digest = await record.karma_engine.evaluate_cycle()
            digests.append(digest)

        # Step 2: KarmaCourt convenes
        verdicts = await self.karma_court.convene(digests)

        # Step 3: Execute reincarnations
        reincarnation_count = 0
        for verdict in verdicts:
            if hasattr(verdict, 'reincarnate') and verdict.reincarnate:
                try:
                    await self.reincarnation_protocol.execute(
                        verdict.agent_id,
                        verdict.from_realm,
                        verdict.to_realm,
                    )
                    # Update realm counts
                    record = self.agents.get(verdict.agent_id)
                    if record:
                        old_realm = record.current_realm
                        new_realm = verdict.to_realm
                        self.realm_counts[old_realm] = max(0, self.realm_counts.get(old_realm, 1) - 1)
                        self.realm_counts[new_realm] = self.realm_counts.get(new_realm, 0) + 1
                        record.current_realm = new_realm
                        record.realm_cycles = 0
                        record.reincarnation_count += 1

                    self.reincarnation_log.append(ReincarnationEvent(
                        agent_id=verdict.agent_id,
                        from_realm=verdict.from_realm,
                        to_realm=verdict.to_realm,
                        cycle=self.cycle_counter,
                    ))
                    reincarnation_count += 1
                except Exception as exc:
                    logger.error(f"Reincarnation failed for {verdict.agent_id}: {exc}")

        # Step 4: Rotate
        self.rotation_angle = (self.rotation_angle + self.rotation_speed) % (2 * 3.14159)

        # Step 5: Publish metrics
        if self.event_bus:
            try:
                from ..kernel.event_bus import SystemEvent
                event = SystemEvent(
                    source="samsara.ring",
                    topic="samsara.metrics",
                    payload={
                        "cycle": self.cycle_counter,
                        "realm_distribution": {
                            r.value: c for r, c in self.realm_counts.items()
                        },
                        "reincarnations_this_cycle": reincarnation_count,
                    },
                )
                await self.event_bus.publish(event, "samsara.metrics")
            except Exception:
                pass

        return CycleReport(
            cycle=self.cycle_counter,
            verdicts=verdicts,
            realm_counts=dict(self.realm_counts),
            reincarnations=reincarnation_count,
        )

    async def get_realm(self, agent_id: str) -> SamsaraRealm:
        """Get current realm for an agent.

        IF agent not registered THEN return HUMAN (safe default).
        """
        record = self.agents.get(agent_id)
        if record is None:
            return SamsaraRealm.HUMAN
        return record.current_realm

    def get_realm_distribution(self) -> Dict[SamsaraRealm, int]:
        """Return current realm distribution."""
        return dict(self.realm_counts)
