"""TendrilManager — 触须管理器.

Manages lifecycle of all 12 external probes.

Health cycle (every 30s):
  FOR EACH tendril IN registry:
    IF state == EXTENDED:
      ok = await tendril.health_check().
      IF not ok THEN tendril.consecutive_failures += 1.
      ELSE tendril.consecutive_failures = 0.

    IF consecutive_failures >= 3 THEN await tendril.retract().
    IF state == RETRACTED AND cooldown_elapsed THEN await tendril.regenerate().
    IF retract_extend_cycles > 5 in 1h THEN tendril.state = UNSTABLE; pause 1h.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .base_tendril import BaseTendril, RetractState

logger = logging.getLogger(__name__)


class TendrilManager:
    """Manage the lifecycle of all external probes (tendrils).

    12 registered tendrils:
      V0/qian: google_scholar, pubmed, crossref, openalex
      V0/dui:  cnki, cscd, wanfang
      V1/li:   semantic_scholar, web_of_science
      V2/xun:  hydro_acoustic
      V2/kan:  remote_sensing
      V3/kun:  fishery_stats
    """

    MAX_CONSECUTIVE_FAILURES = 3
    UNSTABLE_THRESHOLD_PER_HOUR = 5
    COOLDOWN_AFTER_RETRACT_S = 30

    def __init__(self, event_bus: Any = None) -> None:
        self.registry: Dict[str, BaseTendril] = {}
        self.event_bus = event_bus
        self._cooldown_timers: Dict[str, float] = {}
        self._unstable_until: Dict[str, float] = {}

    async def grow_tendril(self, spec: Dict[str, Any]) -> BaseTendril:
        """Create and extend a new tendril from spec.

        spec = {id, target: {name, url}, protocol, rate_limit: {capacity, refill_rate}}.

        Create BaseTendril instance.
        await tendril.extend().
        Register in self.registry.
        RETURN tendril instance.
        """
        tendril = BaseTendril(
            tendril_id=spec["id"],
            target=spec.get("target", {}),
            protocol=spec.get("protocol", "REST"),
            rate_limit=spec.get("rate_limit"),
        )
        await tendril.extend()
        self.registry[spec["id"]] = tendril
        logger.info(f"Tendril {spec['id']} grown → {spec.get('target', {}).get('name', '')}")
        return tendril

    async def prune_tendril(self, tendril_id: str) -> None:
        """Permanently remove a tendril.

        Mark PRUNED.
        Remove from registry.
        Log event.
        """
        tendril = self.registry.pop(tendril_id, None)
        if tendril:
            tendril.retract_state = RetractState.PRUNED
            logger.info(f"Tendril {tendril_id} PRUNED")

    async def health_cycle(self) -> Dict[str, Any]:
        """Run one health check cycle across all tendrils.

        schedule: every 30 seconds.

        FOR EACH tendril:
          IF state == EXTENDED:
            Run health_check().
            IF not ok THEN increment consecutive_failures.
            ELSE reset consecutive_failures = 0.

          IF consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            await tendril.retract().
            Set cooldown timer.

          IF state == RETRACTED AND cooldown elapsed:
            await tendril.regenerate().

          IF retract_extend_cycles > UNSTABLE_THRESHOLD_PER_HOUR:
            tendril.state = UNSTABLE; pause 1h.

        RETURN health report.
        """
        report: Dict[str, Any] = {"tendrils": {}, "summary": {}}
        now = time.monotonic()

        for tid, tendril in self.registry.items():
            status = {"state": tendril.retract_state.value, "healthy": True}

            # Check if unstable pause is active
            unstable_until = self._unstable_until.get(tid, 0)
            if now < unstable_until:
                status["state"] = "UNSTABLE_PAUSED"
                report["tendrils"][tid] = status
                continue

            if tendril.retract_state == RetractState.EXTENDED:
                healthy = await tendril.health_check()
                if not healthy:
                    tendril.health.consecutive_failures += 1
                    status["healthy"] = False
                else:
                    tendril.health.consecutive_failures = 0

                # Retract if too many failures
                if tendril.health.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    await tendril.retract()
                    self._cooldown_timers[tid] = now + self.COOLDOWN_AFTER_RETRACT_S
                    status["action"] = "retracted"
                    logger.warning(
                        f"Tendril {tid} retracted after "
                        f"{tendril.health.consecutive_failures} consecutive failures"
                    )

            elif tendril.retract_state == RetractState.RETRACTED:
                cooldown_end = self._cooldown_timers.get(tid, 0)
                if now >= cooldown_end:
                    await tendril.regenerate()
                    status["action"] = "regenerated"
                    logger.info(f"Tendril {tid} regenerated after cooldown")

                # Check unstable: 5+ retract-extend cycles in last hour
                if tendril.health.retract_extend_cycles > self.UNSTABLE_THRESHOLD_PER_HOUR:
                    tendril.retract_state = RetractState.UNSTABLE
                    self._unstable_until[tid] = now + 3600  # pause 1h
                    status["action"] = "unstable_paused_1h"
                    logger.error(f"Tendril {tid} UNSTABLE — paused for 1 hour")

            status["consecutive_failures"] = tendril.health.consecutive_failures
            report["tendrils"][tid] = status

        # Summary
        states = {}
        for status in report["tendrils"].values():
            s = status["state"]
            states[s] = states.get(s, 0) + 1
        report["summary"] = {
            "total": len(self.registry),
            "by_state": states,
            "extended_count": states.get("EXTENDED", 0),
            "retracted_count": states.get("RETRACTED", 0),
            "unstable_count": states.get("UNSTABLE_PAUSED", 0),
        }

        return report

    def get_active_count(self) -> int:
        """Count of EXTENDED tendrils."""
        return sum(
            1 for t in self.registry.values()
            if t.retract_state == RetractState.EXTENDED
        )
