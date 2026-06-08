"""WuXingFlowEngine — 五行流转引擎.

5 elements in sheng (generation) cycle:
  WOOD → FIRE → EARTH → METAL → WATER → WOOD

5 elements in ke (restriction) pentagram:
  WOOD→EARTH, EARTH→WATER, WATER→FIRE, FIRE→METAL, METAL→WOOD

Runs every 15 seconds:
  1. Collect metrics from each WuXingAgent
  2. Flow sheng: pass growth metrics downstream
  3. Check ke: IF restriction condition met THEN emit advisory
  4. Rotate pentagram (ω=0.01 rad/s)
"""

from __future__ import annotations

import asyncio
import logging
import math
from enum import StrEnum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WuXingElement(StrEnum):
    WOOD = "WOOD"
    FIRE = "FIRE"
    EARTH = "EARTH"
    METAL = "METAL"
    WATER = "WATER"


# Sheng (generation) pairs: clockwise
_SHENG_PAIRS: List[Tuple[WuXingElement, WuXingElement]] = [
    (WuXingElement.WOOD, WuXingElement.FIRE),
    (WuXingElement.FIRE, WuXingElement.EARTH),
    (WuXingElement.EARTH, WuXingElement.METAL),
    (WuXingElement.METAL, WuXingElement.WATER),
    (WuXingElement.WATER, WuXingElement.WOOD),
]

# Ke (restriction) pairs: pentagram star
_KE_PAIRS: List[Tuple[WuXingElement, WuXingElement]] = [
    (WuXingElement.WOOD, WuXingElement.EARTH),
    (WuXingElement.EARTH, WuXingElement.WATER),
    (WuXingElement.WATER, WuXingElement.FIRE),
    (WuXingElement.FIRE, WuXingElement.METAL),
    (WuXingElement.METAL, WuXingElement.WOOD),
]


class WuXingSignal:
    """Signal emitted during ke (restriction) check."""

    __slots__ = ("source", "target", "severity", "condition", "meaning", "timestamp")

    def __init__(
        self,
        source: WuXingElement,
        target: WuXingElement,
        severity: str = "INFO",
        condition: str = "",
        meaning: str = "",
    ) -> None:
        self.source = source
        self.target = target
        self.severity = severity
        self.condition = condition
        self.meaning = meaning
        self.timestamp = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0


class WuXingFlowEngine:
    """五行流转引擎.

    schedule: every 15 seconds.
    """

    def __init__(self, event_bus: Any = None) -> None:
        self.agents: Dict[WuXingElement, Any] = {}
        self.event_bus = event_bus
        self.rotation_angle: float = 0.0
        self.rotation_speed: float = 0.01  # rad/s
        self._override_threshold: int = 3

    def register_agent(self, element: WuXingElement, agent: Any) -> None:
        """Register a WuXing agent."""
        self.agents[element] = agent

    async def run_cycle(self) -> Dict[str, Any]:
        """Execute one full WuXing cycle.

        Step 1: FOR EACH agent: collect metrics.
        Step 2: Flow sheng: pass metrics from source to target.
        Step 3: Check ke: IF restriction condition met THEN emit advisory.
        Step 4: Rotate pentagram.

        RETURN WuXingReport {agents, sheng_flows, ke_advisories, rotation_angle}.
        """
        agent_reports: Dict[str, Any] = {}
        ke_advisories: List[WuXingSignal] = []

        # Step 1: Collect metrics
        for element, agent in self.agents.items():
            try:
                metrics = await agent.collect_metrics()
                agent_reports[element.value] = metrics
            except Exception:
                agent_reports[element.value] = {"status": "error"}

        # Step 2: Sheng flow
        for src, tgt in _SHENG_PAIRS:
            if src in self.agents and tgt in self.agents:
                try:
                    await self._flow_sheng(src, tgt, agent_reports)
                except Exception:
                    logger.debug(f"Sheng flow {src.value}→{tgt.value} skipped")

        # Step 3: Ke check
        for src, tgt in _KE_PAIRS:
            if src in self.agents and tgt in self.agents:
                signal = await self._check_ke(src, tgt, agent_reports)
                if signal and signal.severity in ("WARNING", "MANDATORY"):
                    ke_advisories.append(signal)
                    # Publish to EventBus if available
                    if self.event_bus:
                        from ..kernel.event_bus import SystemEvent
                        event = SystemEvent(
                            source=f"wuxing.{src.value}",
                            topic="wuxing.advisory",
                            payload={
                                "source": src.value,
                                "target": tgt.value,
                                "severity": signal.severity,
                                "condition": signal.condition,
                                "meaning": signal.meaning,
                            },
                        )
                        await self.event_bus.publish(event, "wuxing.advisory")

        # Step 4: Rotate
        self.rotation_angle = (self.rotation_angle + self.rotation_speed) % (2 * math.pi)

        return {
            "agents": agent_reports,
            "ke_advisories": [
                {"source": sig.source.value, "target": sig.target.value,
                 "severity": sig.severity, "meaning": sig.meaning}
                for sig in ke_advisories
            ],
            "rotation_angle_rad": self.rotation_angle,
        }

    async def _flow_sheng(
        self, source: WuXingElement, target: WuXingElement, reports: Dict[str, Any]
    ) -> None:
        """Pass metrics from source agent to target agent.

        WOOD→FIRE: growth rate → drive optimizer
        FIRE→EARTH: throughput → supply quality
        EARTH→METAL: supply freshness → convergence check
        METAL→WATER: convergence stability → adaptation signal
        WATER→WOOD: adaptation signal → growth trigger
        """
        src_agent = self.agents.get(source)
        tgt_agent = self.agents.get(target)
        if src_agent and tgt_agent:
            src_report = reports.get(source.value, {})
            # Pass relevant metrics — each agent knows what to accept
            try:
                await tgt_agent.receive_sheng(source, src_report)
            except Exception:
                pass

    async def _check_ke(
        self, source: WuXingElement, target: WuXingElement, reports: Dict[str, Any]
    ) -> Optional[WuXingSignal]:
        """Check ke (restriction) condition.

        WOOD→EARTH: graph_growth > 2× baseline → warn of overload
        EARTH→WATER: supply_duplication > 60% → slow adaptation
        WATER→FIRE: external_changes > threshold → cool drive
        FIRE→METAL: throughput > 0.9× capacity → reduce convergence
        METAL→WOOD: false_positive > 15% → suggest pruning

        IF condition triggers THEN return WuXingSignal.
        ELSE return None.
        """
        src_report = reports.get(source.value, {})

        # Simplified threshold checks
        if source == WuXingElement.WOOD and target == WuXingElement.EARTH:
            growth = src_report.get("graph_node_growth_rate", 0)
            if growth > 2.0:
                return WuXingSignal(source, target, "WARNING",
                                    f"growth={growth:.2f}>2.0",
                                    "Graph growth surge → warn EARTH of info overload")
        elif source == WuXingElement.EARTH and target == WuXingElement.WATER:
            dup = src_report.get("knowledge_duplication", 0)
            if dup > 0.60:
                return WuXingSignal(source, target, "ADVISORY",
                                    f"duplication={dup:.2f}>0.60",
                                    "Knowledge duplication high → slow WATER adaptation")
        elif source == WuXingElement.WATER and target == WuXingElement.FIRE:
            ext = src_report.get("external_event_response_time", 0)
            if ext > 5.0:
                return WuXingSignal(source, target, "COOLING",
                                    f"response_time={ext:.1f}s>5s",
                                    "External changes rapid → cool FIRE throughput")
        elif source == WuXingElement.FIRE and target == WuXingElement.METAL:
            util = src_report.get("throughput_utilization", 0)
            if util > 0.9:
                return WuXingSignal(source, target, "WARNING",
                                    f"utilization={util:.2f}>0.9",
                                    "Throughput near capacity → warn METAL")
        elif source == WuXingElement.METAL and target == WuXingElement.WOOD:
            fp = src_report.get("false_positive_rate", 0)
            if fp > 0.15:
                return WuXingSignal(source, target, "PRUNING",
                                    f"fp_rate={fp:.2f}>0.15",
                                    "High false positives → suggest WOOD prune graph")

        return None
