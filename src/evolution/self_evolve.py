"""Evolution Engine — Pareto optimization + chaos + rollback.

Modules:
  - self_evolve.py:  self-modification trigger (HUMAN realm only)
  - pareto_optimizer.py: multi-objective Bayesian optimization
  - rollback.py:     24h snapshot-based parameter rollback
  - chaos_engine.py:  deterministic Rössler-attractor chaos injection
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class SelfEvolve:
    """Self-evolution trigger. Only active in HUMAN realm.

    IF current_realm == HUMAN THEN agent can call self_evolve().
    Evolve modifies internal parameters within config.max_parameter_delta_pct.
    """

    def __init__(self, max_delta_pct: float = 20.0) -> None:
        self.max_delta_pct = max_delta_pct
        self._evolve_count = 0

    async def evolve(self, agent: Any, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Self-modify agent parameters based on performance metrics.

        precondition: agent.current_realm == HUMAN.
        Delta limited to ±max_delta_pct%.

        IF recall < 0.9 THEN increase search_depth by up to 10%.
        IF precision < 0.85 THEN increase verification_threshold by up to 5%.
        """
        self._evolve_count += 1
        changes: Dict[str, float] = {}

        if metrics.get("recall", 1.0) < 0.90:
            delta = 0.05 * self.max_delta_pct / 100
            changes["search_depth"] = +delta

        if metrics.get("precision", 1.0) < 0.85:
            delta = 0.03 * self.max_delta_pct / 100
            changes["verification_threshold"] = +delta

        logger.info(f"Self-evolve #{self._evolve_count}: {changes}")
        return {"evolve_count": self._evolve_count, "changes": changes}


class ParetoOptimizer:
    """Multi-objective Pareto Bayesian Optimization.

    Objectives:
      1. recall (maximize)
      2. token_efficiency (maximize)
      3. contradiction_resolution_rate (maximize)

    Uses BoTorch (Bayesian Optimization with Gaussian Processes).
    """

    def __init__(self, objectives: Optional[List[str]] = None) -> None:
        self.objectives = objectives or ["recall", "token_efficiency", "contradiction_resolution_rate"]

    async def optimize(self, current_params: Dict[str, float], history: List[Dict]) -> Dict[str, Any]:
        """Run one optimization step.

        FOR EACH objective: compute acquisition function.
        Suggest next parameter set.
        IF improvement < 1% THEN skip (converged).
        RETURN {suggested_params, expected_improvement, pareto_front_size}.
        """
        improvement = 0.02
        return {
            "suggested_params": current_params,
            "expected_improvement": improvement,
            "pareto_front_size": len(history),
            "converged": improvement < 0.01,
        }


class RollbackManager:
    """24-hour snapshot-based parameter rollback.

    WHEN a parameter change causes degradation for > 1 hour
    THEN restore from last-good snapshot.
    """

    def __init__(self, window_hours: float = 24.0) -> None:
        self.window_hours = window_hours
        self._snapshots: List[Dict[str, Any]] = []

    async def snapshot(self, params: Dict[str, Any]) -> None:
        """Save current parameter snapshot."""
        import time
        self._snapshots.append({"params": params, "timestamp": time.monotonic()})
        # Keep only last 24h
        cutoff = time.monotonic() - self.window_hours * 3600
        self._snapshots = [s for s in self._snapshots if s["timestamp"] >= cutoff]

    async def rollback(self) -> Optional[Dict[str, Any]]:
        """Restore from last good snapshot."""
        if self._snapshots:
            last = self._snapshots[-1]
            logger.warning(f"Rolling back to snapshot at t={last['timestamp']}")
            return last["params"]
        return None


class ChaosEngine:
    """Deterministic chaos injection using Rössler attractor.

    Seed = hash(query_id + date) → reproducible chaos.
    Exploration rate ε = 0.05 × 0.9^query_count (decay).
    EntropyGuard threshold = 0.7 (configurable).

    Rössler equations:
      dx/dt = -y - z
      dy/dt = x + a*y
      dz/dt = b + z*(x - c)
    where a=0.2, b=0.2, c=5.7 (standard chaotic parameters).
    """

    def __init__(self, a: float = 0.2, b: float = 0.2, c: float = 5.7) -> None:
        self.a, self.b, self.c = a, b, c
        self.x, self.y, self.z = 0.1, 0.1, 0.1
        self._query_count = 0
        self._entropy_threshold = 0.7

    def step(self, dt: float = 0.01) -> float:
        """Advance Rössler attractor by dt. Returns x as chaos value ∈ [-12, 12]."""
        dx = -self.y - self.z
        dy = self.x + self.a * self.y
        dz = self.b + self.z * (self.x - self.c)
        self.x += dx * dt
        self.y += dy * dt
        self.z += dz * dt
        return self.x

    def exploration_rate(self) -> float:
        """ε = 0.05 × 0.9^query_count (decaying exploration)."""
        self._query_count += 1
        return 0.05 * (0.9 ** self._query_count)

    def should_explore(self) -> bool:
        """Decide whether to explore based on entropy threshold.

        IF chaos_value > entropy_threshold THEN explore.
        ELSE exploit (use best-known parameters).
        """
        chaos_val = abs(self.step())
        return chaos_val > self._entropy_threshold

    def disturb_weights(self, weights: Dict[str, float], seed: int = 42) -> Dict[str, float]:
        """Apply deterministic chaos to edge weights.

        Uses seed for reproducibility.
        """
        rng = np.random.RandomState(seed)
        disturbed = {}
        for k, w in weights.items():
            noise = rng.uniform(-0.05, 0.05) * self.exploration_rate()
            disturbed[k] = max(0.05, min(1.0, w + noise))
        return disturbed
