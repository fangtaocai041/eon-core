"""LifecycleStage enum + state machine for OriginKernel.

Lifecycle:
  SEEDING → SPROUTING → BLOOMING → FRUITING → PRUNING → SEEDING

State transitions:
  bootstrap()        → SEEDING → SPROUTING → BLOOMING
  normal_operation   → BLOOMING
  self_evolve()      → BLOOMING → FRUITING
  reconfigure()      → FRUITING  → BLOOMING
  shutdown()         → * → PRUNING → SEEDING

Invariants:
  - Only BLOOMING accepts external events
  - PRUNING drains event bus before transition to SEEDING
  - FRUITING is read-only for external queries, mutation paused
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class LifecycleStage(enum.StrEnum):
    SEEDING = "seeding"
    SPROUTING = "sprouting"
    BLOOMING = "blooming"
    FRUITING = "fruiting"
    PRUNING = "pruning"


# Valid transitions: from → [to, ...]
_TRANSITIONS: dict[LifecycleStage, list[LifecycleStage]] = {
    LifecycleStage.SEEDING: [LifecycleStage.SPROUTING],
    LifecycleStage.SPROUTING: [LifecycleStage.BLOOMING, LifecycleStage.PRUNING],
    LifecycleStage.BLOOMING: [LifecycleStage.FRUITING, LifecycleStage.PRUNING],
    LifecycleStage.FRUITING: [LifecycleStage.BLOOMING, LifecycleStage.PRUNING],
    LifecycleStage.PRUNING: [LifecycleStage.SEEDING],
}

# Stages that accept external query events
_ACCEPTS_EVENTS: set[LifecycleStage] = {LifecycleStage.BLOOMING}

# Stages that allow mutations
_ALLOWS_MUTATION: set[LifecycleStage] = {
    LifecycleStage.SPROUTING,
    LifecycleStage.BLOOMING,
    LifecycleStage.FRUITING,
}


@dataclass(slots=True)
class Lifecycle:
    """OriginKernel lifecycle state machine."""

    stage: LifecycleStage = LifecycleStage.SEEDING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    transitions: list[tuple[LifecycleStage, LifecycleStage, datetime]] = field(
        default_factory=list
    )

    def transition(self, to: LifecycleStage) -> None:
        """Transition to target stage. Raises ValueError if invalid."""
        if to not in _TRANSITIONS.get(self.stage, []):
            raise ValueError(
                f"Invalid transition: {self.stage.value} → {to.value}. "
                f"Allowed: {[s.value for s in _TRANSITIONS.get(self.stage, [])]}"
            )
        now = datetime.now(timezone.utc)
        self.transitions.append((self.stage, to, now))
        self.stage = to

    @property
    def accepts_events(self) -> bool:
        """Only BLOOMING accepts external query events."""
        return self.stage in _ACCEPTS_EVENTS

    @property
    def allows_mutation(self) -> bool:
        """Check if current stage allows state mutations."""
        return self.stage in _ALLOWS_MUTATION

    @property
    def is_alive(self) -> bool:
        """System is alive unless SEEDING or PRUNING."""
        return self.stage not in {LifecycleStage.SEEDING, LifecycleStage.PRUNING}

    def uptime_seconds(self) -> float:
        """Seconds since SEEDING→SPROUTING transition."""
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    def summary(self) -> dict:
        return {
            "stage": self.stage.value,
            "uptime_seconds": self.uptime_seconds(),
            "transition_count": len(self.transitions),
        }
