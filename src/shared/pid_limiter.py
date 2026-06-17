"""PIDRateLimiter — PID-controlled adaptive rate limiter.

A feedback-control loop that auto-tunes the delay between actions (e.g. API
calls, batch jobs) to converge on a configurable target error rate.  Uses
three-term PID control with integral anti-windup clamping.

Mathematics:
  e(t)  = target_error_rate - current_error_rate
  u(t)  = Kp·e(t) + Ki·∫e(t)dt + Kd·de(t)/dt
  delay = clamp(base_delay + u(t), min_delay, max_delay)

Usage:
    from eon_core.shared import PIDRateLimiter

    limiter = PIDRateLimiter(target_error_rate=0.05)
    for resource in worklist:
        delay = limiter.wait(resource, success=True)
        time.sleep(delay)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ResourceState:
    """Per-resource PID state."""
    successes: int = 0
    failures: int = 0
    total_requests: int = 0
    integral_error: float = 0.0
    last_error: float = 0.0
    current_delay: float = 1.0
    # Rolling window for recent-failure detection (anti-thrashing)
    _recent_outcomes: List[bool] = field(default_factory=list)


class PIDRateLimiter:
    """PID controller for adaptive rate limiting of named resources.

    Each resource key (e.g. API host name, queue id) gets its own independent
    PID state.  Call ``wait`` after **every** action to feed the result back
    into the controller.

    Parameters:
        target_error_rate: Desired long-run error rate (0.0–1.0).
        kp: Proportional gain — reacts to instantaneous error.
        ki: Integral gain — corrects accumulated bias.
        kd: Derivative gain — dampens oscillations.
        min_delay: Floor delay in seconds.
        max_delay: Ceiling delay in seconds.
        base_delay: Starting delay before any feedback.
        window_size: Number of recent outcomes to track for anti-thrashing.
    """

    def __init__(
        self,
        target_error_rate: float = 0.05,
        kp: float = 0.5,
        ki: float = 0.1,
        kd: float = 0.2,
        min_delay: float = 0.1,
        max_delay: float = 10.0,
        base_delay: float = 1.0,
        window_size: int = 10,
    ):
        self._target = target_error_rate
        self._kp = kp
        self._ki = ki
        self._kd = kd
        self._min = min_delay
        self._max = max_delay
        self._base = base_delay
        self._window_size = window_size
        self._resources: Dict[str, ResourceState] = {}

    # ── core API ───────────────────────────────────────────────────

    def wait(self, resource_key: str, success: bool) -> float:
        """Feed the outcome of the last action and return seconds to wait.

        Call this **after** every action on *resource_key*.  The returned
        delay should be used **before** the *next* action on the same key.

        Parameters:
            resource_key: An arbitrary string identifying the resource
                (e.g. ``"pubmed"``, ``"gpu_queue"``).
            success: ``True`` if the last action succeeded, ``False`` if it
                failed (error, timeout, rate-limit hit, etc.).

        Returns:
            Recommended delay in seconds (float).
        """
        if resource_key not in self._resources:
            self._resources[resource_key] = ResourceState()
            self._resources[resource_key].current_delay = self._base

        state = self._resources[resource_key]
        state.total_requests += 1
        if success:
            state.successes += 1
        else:
            state.failures += 1

        # Rolling window of recent outcomes (anti-thrashing)
        state._recent_outcomes.append(success)
        if len(state._recent_outcomes) > self._window_size:
            state._recent_outcomes = state._recent_outcomes[-self._window_size:]

        # Compute error signal
        error_rate = state.failures / max(state.total_requests, 1)
        error = self._target - error_rate   # positive = doing well, negative = too many errors

        # PID terms
        p_term = self._kp * error

        # Integral with anti-windup clamping (±5)
        state.integral_error += error
        if state.integral_error > 5.0:
            state.integral_error = 5.0
        elif state.integral_error < -5.0:
            state.integral_error = -5.0
        i_term = self._ki * state.integral_error

        d_term = self._kd * (error - state.last_error)
        state.last_error = error

        # Compute delay
        adjustment = p_term + i_term + d_term
        state.current_delay = max(
            self._min, min(self._max, self._base + adjustment)
        )

        # Adaptive reduction: if error rate is well below target and we have
        # enough history, slowly reduce the delay to increase throughput.
        if error_rate < self._target and state.total_requests > 20:
            state.current_delay = max(self._min, state.current_delay * 0.95)

        # Anti-thrashing: after a burst of recent failures, increase delay
        # sharply to give the remote side time to recover.
        recent_failures = sum(1 for ok in state._recent_outcomes if not ok)
        if recent_failures >= 3:
            state.current_delay = min(self._max, state.current_delay * 1.5)

        return state.current_delay

    # ── introspection ──────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Return per-resource summary: delay, error_rate, requests."""
        return {
            key: {
                "delay": round(s.current_delay, 2),
                "error_rate": round(
                    s.failures / max(s.total_requests, 1), 3
                ),
                "requests": s.total_requests,
            }
            for key, s in self._resources.items()
        }

    def reset(self, resource_key: str) -> None:
        """Reset PID state for a single resource."""
        self._resources.pop(resource_key, None)

    def reset_all(self) -> None:
        """Reset PID state for all resources."""
        self._resources.clear()
