"""CircuitBreaker — 熔断器模式，防止多项目级联故障.

三生万物架构中有 6 个适配器(项目), 一个项目挂掉不应拖垮整个管线.
CircuitBreaker 提供:
  - CLOSED → OPEN → HALF_OPEN 三态转换
  - 基于滑动窗口的失败率检测 (非固定计数)
  - 半开后单请求探测, 成功即恢复

Usage:
    from eon_core.shared import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(name="cognitive-search", failure_threshold=5)

    async with breaker:
        result = await call_api()

    # Or sync:
    if breaker.can_pass():
        try:
            result = call_api()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            raise
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing fast
    HALF_OPEN = "half_open"    # Testing recovery


@dataclass
class CircuitBreaker:
    """熔断器 — per-resource failure isolation.

    Attributes:
        name: Resource/endpoint identifier (e.g. "cognitive-search").
        failure_threshold: Failures within *window_sec* to trip open.
        recovery_timeout_sec: Seconds before transitioning OPEN → HALF_OPEN.
        half_open_max_requests: Max test requests in HALF_OPEN state.
        window_sec: Sliding window for failure counting (default 60s).
        success_threshold: Consecutive successes in HALF_OPEN to reset.
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout_sec: float = 30.0
    half_open_max_requests: int = 1
    window_sec: float = 60.0
    success_threshold: int = 2

    # Internal state (not in __init__)
    _state: CircuitState = CircuitState.CLOSED
    _failure_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    _last_failure_time: float = 0.0
    _half_open_requests: int = 0
    _consecutive_successes: int = 0
    _total_calls: int = 0
    _total_failures: int = 0

    def __post_init__(self):
        self._state = CircuitState.CLOSED
        self._failure_times = deque(maxlen=1000)
        self._last_failure_time = 0.0
        self._half_open_requests = 0
        self._consecutive_successes = 0
        self._total_calls = 0
        self._total_failures = 0

    # ── Public API ────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        """Current circuit state (auto-transitions OPEN → HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout_sec:
                logger.info(f"Circuit [{self.name}] OPEN → HALF_OPEN (recovery timeout elapsed)")
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
                self._consecutive_successes = 0
        return self._state

    def can_pass(self) -> bool:
        """Check if a request can proceed through the circuit.

        Returns True if CLOSED or HALF_OPEN (with capacity), False if OPEN.
        """
        s = self.state
        if s == CircuitState.CLOSED:
            return True
        if s == CircuitState.OPEN:
            return False
        # HALF_OPEN: allow limited test requests
        if self._half_open_requests < self.half_open_max_requests:
            self._half_open_requests += 1
            return True
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self._total_calls += 1
        if self._state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.success_threshold:
                logger.info(f"Circuit [{self.name}] HALF_OPEN → CLOSED (recovered)")
                self._state = CircuitState.CLOSED
                self._failure_times.clear()
                self._consecutive_successes = 0
                self._half_open_requests = 0

    def record_failure(self) -> None:
        """Record a failed call and possibly trip the circuit."""
        self._total_calls += 1
        self._total_failures += 1
        now = time.time()
        self._failure_times.append(now)
        self._last_failure_time = now

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit [{self.name}] HALF_OPEN → OPEN (test request failed)")
            self._state = CircuitState.OPEN
            self._consecutive_successes = 0
            self._half_open_requests = 0
            return

        # Sliding window check
        self._prune_old_failures(now)
        if len(self._failure_times) >= self.failure_threshold:
            logger.warning(
                f"Circuit [{self.name}] CLOSED → OPEN "
                f"({len(self._failure_times)} failures in {self.window_sec}s window)"
            )
            self._state = CircuitState.OPEN
            self._consecutive_successes = 0

    def reset(self) -> None:
        """Manually reset to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_times.clear()
        self._half_open_requests = 0
        self._consecutive_successes = 0
        logger.info(f"Circuit [{self.name}] manually reset to CLOSED")

    def get_stats(self) -> dict:
        """Return current state and statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "failure_rate": round(self._total_failures / max(self._total_calls, 1), 4),
            "recent_failures": len(self._failure_times),
            "window_sec": self.window_sec,
            "threshold": self.failure_threshold,
        }

    # ── Context manager support ───────────────────────────────────

    def __enter__(self) -> CircuitBreaker:
        if not self.can_pass():
            raise CircuitBreakerOpenError(
                f"Circuit [{self.name}] is OPEN — request blocked"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None and exc_type is not CircuitBreakerOpenError:
            self.record_failure()
        elif exc_type is None:
            self.record_success()

    # ── Internal ──────────────────────────────────────────────────

    def _prune_old_failures(self, now: float) -> None:
        """Remove failures outside the sliding window."""
        cutoff = now - self.window_sec
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is OPEN and blocking a request."""
    pass


class CircuitBreakerRegistry:
    """Global registry of circuit breakers, keyed by resource name.

    Provides a single point of management for all breakers across projects.
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str, **defaults) -> CircuitBreaker:
        """Get or create a circuit breaker.

        Args:
            name: Resource name (e.g. "cognitive-search").
            **defaults: Default kwargs for new CircuitBreaker instances.

        Returns:
            CircuitBreaker instance (shared).
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name, **defaults)
        return self._breakers[name]

    def all_stats(self) -> dict[str, dict]:
        """Return stats for all registered breakers."""
        return {name: cb.get_stats() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all breakers to CLOSED."""
        for cb in self._breakers.values():
            cb.reset()

    def health(self) -> dict:
        """Return health summary for monitoring."""
        stats = self.all_stats()
        open_breakers = [n for n, s in stats.items() if s["state"] == "open"]
        return {
            "total": len(stats),
            "open": len(open_breakers),
            "open_breakers": open_breakers,
            "healthy": len(open_breakers) == 0,
        }


# Singleton registry
_registry: Optional[CircuitBreakerRegistry] = None


def get_registry() -> CircuitBreakerRegistry:
    """Get the global CircuitBreakerRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


# ── Decorator for easy integration ──────────────────────────────

def with_circuit_breaker(name: str, **breaker_kwargs):
    """Decorator: wrap a sync function with a circuit breaker.

    Usage:
        @with_circuit_breaker("cognitive-search", failure_threshold=3)
        def search_species(query: str) -> list:
            ...
    """
    registry = get_registry()
    breaker = registry.get(name, **breaker_kwargs)

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            with breaker:
                return func(*args, **kwargs)
        return wrapper
    return decorator
