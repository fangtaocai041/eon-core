"""ThompsonBandit — Generic Thompson Sampling multi-armed bandit.

A Bayesian decision-making primitive: each arm has a Beta-distributed reward
probability. The bandit samples from each arm's posterior and selects the
top-n arms, naturally balancing exploration vs exploitation.

Mathematics (Thompson 1933; Agrawal & Goyal 2012):
  For arm i: alpha_i = successes + 1,  beta_i = failures + 1
  Sample θ_i ~ Beta(alpha_i, beta_i), select arms with largest θ_i
  Update: success → alpha_i += 1;  failure → beta_i += 1

Usage:
    from eon_core.shared import ThompsonBandit

    bandit = ThompsonBandit()
    arms = bandit.select_arms(5)
    # ... use arms ...
    bandit.update("arm_a", success=True)
    bandit.update("arm_b", success=False)
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ArmStats:
    """Per-arm Beta-distribution state and optional metadata.

    Attributes:
        successes: Count of successful trials.
        failures: Count of failed trials.
        weight: Prior importance weight (1.0 = neutral).
        categories: Tags for context-based grouping (e.g. ["api", "fast"]).
    """
    successes: int = 0
    failures: int = 0
    weight: float = 1.0
    categories: List[str] = field(default_factory=list)

    @property
    def alpha(self) -> float:
        return self.successes + 1

    @property
    def beta(self) -> float:
        return self.failures + 1

    @property
    def win_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.5

    @property
    def trials(self) -> int:
        return self.successes + self.failures


class ThompsonBandit:
    """Thompson Sampling multi-armed bandit for generic arm selection.

    Arms are created lazily on first use. Supports optional arm metadata
    (weights, categories) and JSON persistence so learning survives restarts.

    Parameters:
        state_file: Optional path to a JSON file for persisting arm stats.
        default_weight: Weight assigned to arms created implicitly via ``update``.
    """

    def __init__(
        self,
        state_file: Optional[str] = None,
        default_weight: float = 1.0,
    ):
        self._arms: Dict[str, ArmStats] = {}
        self._default_weight = default_weight
        self._state_file = state_file
        if self._state_file:
            self._load_state()

    # ── registration ──────────────────────────────────────────────

    def register_arm(
        self,
        name: str,
        weight: float = 1.0,
        categories: Optional[List[str]] = None,
        successes: int = 0,
        failures: int = 0,
    ) -> None:
        """Register (or overwrite) an arm with optional metadata and priors."""
        self._arms[name] = ArmStats(
            successes=successes,
            failures=failures,
            weight=weight,
            categories=categories or [],
        )

    def remove_arm(self, name: str) -> None:
        """Remove an arm from the bandit entirely."""
        self._arms.pop(name, None)

    # ── core API ───────────────────────────────────────────────────

    def select_arms(self, n: int = 1, exploration_bonus: float = 0.0) -> List[str]:
        """Return the top-*n* arm names according to Thompson Sampling.

        Parameters:
            n: How many arms to return (must be ≥ 1).
            exploration_bonus: Additive epsilon-greedy weight added to each
                sample to encourage exploration.  0.0 = pure Thompson.

        Returns:
            Sorted list of arm names (best first).  If there are fewer
            registered arms than *n*, all are returned.
        """
        if not self._arms:
            return []

        n = max(1, min(n, len(self._arms)))

        samples: List[tuple[str, float]] = []
        for name, stats in self._arms.items():
            theta = random.betavariate(stats.alpha, stats.beta)
            theta *= stats.weight
            theta += exploration_bonus
            samples.append((name, theta))

        samples.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in samples[:n]]

    def update(self, arm_name: str, success: bool) -> None:
        """Update the Beta posterior for *arm_name* after a trial.

        If *arm_name* is not yet registered it is created implicitly with
        the *default_weight* and no categories.

        Parameters:
            arm_name: Name of the arm that was tried.
            success: ``True`` if the trial was a success, ``False`` otherwise.
        """
        if arm_name not in self._arms:
            self._arms[arm_name] = ArmStats(weight=self._default_weight)

        stats = self._arms[arm_name]
        if success:
            stats.successes += 1
        else:
            stats.failures += 1

        # Periodic auto-save every 10 trials per arm
        if self._state_file and stats.trials % 10 == 0:
            self._save_state()

    # ── introspection ──────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return a summary dict keyed by arm name."""
        return {
            name: {
                "successes": s.successes,
                "failures": s.failures,
                "win_rate": round(s.win_rate, 3),
                "trials": s.trials,
                "alpha": s.alpha,
                "beta": s.beta,
                "weight": s.weight,
                "categories": s.categories,
            }
            for name, s in sorted(
                self._arms.items(), key=lambda kv: kv[1].win_rate, reverse=True
            )
        }

    def arm_names(self) -> List[str]:
        """Return all currently registered arm names."""
        return list(self._arms.keys())

    # ── persistence ────────────────────────────────────────────────

    def save_state(self, path: Optional[str] = None) -> None:
        """Persist arm stats to a JSON file (explicit save)."""
        target = path or self._state_file
        if not target:
            return
        self._state_file = target
        self._save_state()

    def load_state(self, path: str) -> None:
        """Load arm stats from a JSON file, merging into current state."""
        self._state_file = path
        self._load_state()

    def _save_state(self) -> None:
        if not self._state_file:
            return
        try:
            os.makedirs(os.path.dirname(self._state_file) or ".", exist_ok=True)
            data = {
                name: {
                    "s": s.successes,
                    "f": s.failures,
                    "w": s.weight,
                    "c": s.categories,
                }
                for name, s in self._arms.items()
            }
            with open(self._state_file, "w") as fh:
                json.dump(data, fh, indent=2)
        except Exception:
            pass  # best-effort persistence

    def _load_state(self) -> None:
        if not self._state_file or not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file) as fh:
                data = json.load(fh)
            for name, d in data.items():
                self._arms[name] = ArmStats(
                    successes=d.get("s", 0),
                    failures=d.get("f", 0),
                    weight=d.get("w", self._default_weight),
                    categories=d.get("c", []),
                )
        except Exception:
            pass
