"""BaseTendril — 触须探针基类.

Each tendril probes an external source with retract/extend lifecycle.

States:
  EXTENDED   → actively connected and probing
  RETRACTING → closing connection
  RETRACTED  → disconnected, waiting for cooldown
  EXTENDING  → re-establishing connection (regeneration)
  PRUNED     → permanently removed

Lifecycle:
  extend() → EXTENDED
  probe()  → query external source (while EXTENDED)
  retract() → RETRACTED (after 3 consecutive failures)
  regenerate() → EXTENDING → EXTENDED (after cooldown)
  prune()  → PRUNED (after 5 retract-extend cycles in 1h)
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import StrEnum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RetractState(StrEnum):
    EXTENDED = "EXTENDED"
    RETRACTING = "RETRACTING"
    RETRACTED = "RETRACTED"
    EXTENDING = "EXTENDING"
    PRUNED = "PRUNED"
    UNSTABLE = "UNSTABLE"


class TendrilHealth:
    """Health metrics for a tendril."""

    __slots__ = ("consecutive_failures", "last_success", "avg_latency_ms",
                 "retract_extend_cycles", "state")

    def __init__(self) -> None:
        self.consecutive_failures: int = 0
        self.last_success: float = 0.0
        self.avg_latency_ms: float = 0.0
        self.retract_extend_cycles: int = 0
        self.state: RetractState = RetractState.RETRACTED


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, capacity: int = 100, refill_rate: float = 10.0) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(float(self.capacity), self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False


class BaseTendril:
    """Abstract tendril probe for external data sources.

    Subclasses implement specific protocol adapters:
      - REST (PubMed, CrossRef, OpenAlex, Web of Science, etc.)
      - Scraping (Google Scholar, CNKI, Wanfang)
      - MQTT (hydro acoustic monitoring)
      - MCP (Model Context Protocol endpoints)
    """

    def __init__(
        self,
        tendril_id: str,
        target: Dict[str, Any],
        protocol: str = "REST",
        rate_limit: Optional[Dict[str, int]] = None,
    ) -> None:
        self.tendril_id: str = tendril_id
        self.target: Dict[str, Any] = target
        self.protocol: str = protocol
        self.retract_state: RetractState = RetractState.RETRACTED
        self.health: TendrilHealth = TendrilHealth()
        rl = rate_limit or {"capacity": 100, "refill_rate": 10}
        self.rate_limiter: TokenBucket = TokenBucket(
            capacity=rl.get("capacity", 100),
            refill_rate=rl.get("refill_rate", 10),
        )
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: float = 3600.0  # 1 hour default

    async def extend(self) -> None:
        """Establish connection to external source.

        IF state == RETRACTED THEN connect and set state = EXTENDED.
        IF state == EXTENDED THEN no-op.
        IF state == PRUNED THEN raise RuntimeError.
        """
        if self.retract_state == RetractState.PRUNED:
            raise RuntimeError(f"Tendril {self.tendril_id} is PRUNED, cannot extend")

        if self.retract_state == RetractState.RETRACTED:
            self.retract_state = RetractState.EXTENDING
            # Actual connection logic in subclass
            await asyncio.sleep(0.01)  # simulate handshake
            self.retract_state = RetractState.EXTENDED
            logger.info(f"Tendril {self.tendril_id} EXTENDED → {self.target.get('name', '')}")

    async def probe(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Query external source.

        precondition: state == EXTENDED.
        IF rate_limiter.consume() fails THEN return rate_limit_error.
        Check cache first.
        Query external source.
        Update health metrics.

        RETURN {status, data, cached, latency_ms}.
        """
        if self.retract_state != RetractState.EXTENDED:
            return {"status": "error", "error": "tendril_not_extended"}

        if not self.rate_limiter.consume():
            return {"status": "error", "error": "rate_limit_exceeded"}

        # Cache check
        cache_key = f"{query}:{str(params)}"
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.monotonic() - entry["ts"] < self._cache_ttl:
                return {"status": "ok", "data": entry["data"], "cached": True}

        # Query (simulated)
        t0 = time.monotonic()
        try:
            await asyncio.sleep(0.05)  # simulate network
            data = {"query": query, "source": self.target.get("name", ""), "items": []}
            latency = (time.monotonic() - t0) * 1000

            # Cache
            self._cache[cache_key] = {"data": data, "ts": time.monotonic()}

            # Update health
            self.health.last_success = time.monotonic()
            self.health.consecutive_failures = 0
            self.health.avg_latency_ms = (
                0.9 * self.health.avg_latency_ms + 0.1 * latency
            )

            return {"status": "ok", "data": data, "cached": False, "latency_ms": latency}
        except Exception as exc:
            self.health.consecutive_failures += 1
            logger.warning(f"Tendril {self.tendril_id} probe failed: {exc}")
            return {"status": "error", "error": str(exc)}

    async def retract(self) -> None:
        """Close connection to external source.

        IF state == EXTENDED THEN close, set state = RETRACTED.
        """
        if self.retract_state == RetractState.EXTENDED:
            self.retract_state = RetractState.RETRACTING
            await asyncio.sleep(0.01)  # simulate disconnect
            self.retract_state = RetractState.RETRACTED
            self.health.retract_extend_cycles += 1
            logger.info(f"Tendril {self.tendril_id} RETRACTED")

    async def regenerate(self) -> None:
        """Rebuild connection with fresh parameters.

        Only valid from RETRACTED state.
        Sets state = EXTENDING → EXTENDED.
        """
        if self.retract_state == RetractState.RETRACTED:
            await self.extend()
            logger.info(f"Tendril {self.tendril_id} REGENERATED")

    async def health_check(self) -> bool:
        """Quick health check. Returns True if healthy."""
        if self.retract_state != RetractState.EXTENDED:
            return False
        return self.health.consecutive_failures < 3
