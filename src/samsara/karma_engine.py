"""KarmaEngine — embedded karma scoring per vertex/trigram.

Embedded in: BaseVertex, BaseTrigram.

Scoring:
  karma_score ∈ [0, 100], initialized at 50.
  Good deeds: +score with exponential decay (half-life in cycles).
  Bad deeds: −score with cooldown (can't repeat same bad deed during cooldown).

Decay function:
  karma_weight(t) = initial_score × 0.5^(t / half_life_cycles)

Methods:
  record_deed(deed_type, score, context) → append, apply decay, recalc.
  evaluate_cycle() → {current_realm, karma_score, suggested_realm, confidence}.
  should_reincarnate() → Optional[SamsaraRealm] (target realm or None).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .realms import (
    DEFAULT_REALMS,
    SamsaraRealm,
    RealmConfig,
    realm_compare,
    realm_gt,
)


@dataclass
class KarmaRecord:
    """A single karma event (good or bad deed)."""

    deed_type: str
    score: float
    half_life_cycles: int = 5
    cooldown_cycles: int = 0
    cycle_recorded: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    def current_weight(self, current_cycle: int) -> float:
        """Compute decayed weight: score × 0.5^(age / half_life)."""
        age = current_cycle - self.cycle_recorded
        if age <= 0:
            return self.score
        if self.half_life_cycles <= 0:
            return self.score
        return self.score * (0.5 ** (age / self.half_life_cycles))


@dataclass
class KarmaVerdict:
    """Result of evaluate_cycle()."""

    current_realm: SamsaraRealm
    karma_score: float
    suggested_realm: SamsaraRealm
    confidence: float = 1.0
    reason: str = ""


# Good deed definitions
GOOD_DEEDS: Dict[str, Dict[str, Any]] = {
    "HIGH_RECALL":           {"base_score": +3, "half_life": 5, "cooldown": 0},
    "HIGH_PRECISION":        {"base_score": +2, "half_life": 5, "cooldown": 0},
    "LOW_LATENCY":           {"base_score": +1, "half_life": 3, "cooldown": 0},
    "USER_SATISFACTION":     {"base_score": +5, "half_life": 8, "cooldown": 0},
    "NOVEL_DISCOVERY":       {"base_score": +4, "half_life": 3, "cooldown": 0},
    "SUCCESSFUL_COLLABORATION": {"base_score": +3, "half_life": 3, "cooldown": 0},
}

BAD_DEEDS: Dict[str, Dict[str, Any]] = {
    "HALLUCINATION":         {"base_score": -5, "cooldown": 3},
    "TIMEOUT":               {"base_score": -3, "cooldown": 2},
    "CONTRADICTION_LOST":    {"base_score": -4, "cooldown": 0},
    "RATE_LIMIT_HIT":        {"base_score": -2, "cooldown": 1},
    "RESOURCE_WASTE":        {"base_score": -3, "cooldown": 3},
    "STALE_RESPONSE":        {"base_score": -1, "cooldown": 1},
}


class KarmaEngine:
    """Embedded karma scoring engine.

    Each vertex and trigram embeds one KarmaEngine instance.
    """

    def __init__(self, agent_id: str = "") -> None:
        self.agent_id: str = agent_id
        self.karma_score: float = 50.0
        self.good_deeds: deque[KarmaRecord] = deque(maxlen=100)
        self.bad_deeds: deque[KarmaRecord] = deque(maxlen=100)
        self.current_realm: SamsaraRealm = SamsaraRealm.HUMAN
        self.realm_duration: int = 0  # cycles in current realm
        self.lifetime_karma: float = 50.0
        self.nirvana_progress: float = 0.0
        self._cycle: int = 0
        self._realm_configs: Dict[SamsaraRealm, RealmConfig] = dict(DEFAULT_REALMS)

    async def record_deed(
        self, deed_type: str, score_multiplier: float = 1.0, context: Optional[Dict] = None
    ) -> None:
        """Record a karma event.

        IF deed_type is a good deed:
          Look up in GOOD_DEEDS, compute decayed score, append.
        IF deed_type is a bad deed:
          Check cooldown — IF same type recorded within cooldown_cycles THEN skip.
          Apply DEVA penalty multiplier (3.0×) if applicable.
          Append with negative score.

        Recalculate karma_score from all active deeds.
        """
        context = context or {}

        if deed_type in GOOD_DEEDS:
            spec = GOOD_DEEDS[deed_type]
            record = KarmaRecord(
                deed_type=deed_type,
                score=spec["base_score"] * score_multiplier,
                half_life_cycles=spec["half_life"],
                cycle_recorded=self._cycle,
                context=context,
            )
            self.good_deeds.append(record)

        elif deed_type in BAD_DEEDS:
            spec = BAD_DEEDS[deed_type]

            # Cooldown check: skip if same bad deed in cooldown
            cooldown = spec["cooldown"]
            if cooldown > 0:
                for recent in reversed(self.bad_deeds):
                    if recent.deed_type == deed_type and (self._cycle - recent.cycle_recorded) < cooldown:
                        return  # still in cooldown

            penalty = spec["base_score"] * score_multiplier

            # DEVA penalty: 3× multiplier for bad deeds in天道
            if self.current_realm == SamsaraRealm.DEVA:
                penalty *= 3.0

            record = KarmaRecord(
                deed_type=deed_type,
                score=penalty,
                cycle_recorded=self._cycle,
                cooldown_cycles=cooldown,
                context=context,
            )
            self.bad_deeds.append(record)

        # Recalculate
        self._recalc_karma()

    def _recalc_karma(self) -> None:
        """Recalculate karma_score from all active deeds.

        karma_score = 50 + Σ(good_deed.current_weight(cycle)) + Σ(bad_deed.score).
        Clamped to [0, 100].
        """
        score = 50.0
        for deed in self.good_deeds:
            score += deed.current_weight(self._cycle)
        for deed in self.bad_deeds:
            # Bad deeds don't decay (they represent permanent dings)
            age = self._cycle - deed.cycle_recorded
            if age <= deed.cooldown_cycles + 3:  # active for cooldown+3 cycles
                score += deed.score
        self.karma_score = max(0.0, min(100.0, score))
        self.lifetime_karma = max(self.lifetime_karma, self.karma_score)

    async def evaluate_cycle(self) -> KarmaVerdict:
        """Evaluate karma at end of cycle.

        Determine suggested realm from karma_score thresholds.
        IF karma ≥ 85 THEN suggest DEVA.
        ELIF karma ≥ 60 THEN suggest ASURA.
        ELIF karma ≥ 40 THEN suggest HUMAN.
        ELIF karma ≥ 20 THEN suggest ANIMAL.
        ELIF karma ≥ 10 THEN suggest PRETA.
        ELSE suggest NARAKA.

        Also check special conditions:
        - DEVA requires 3-cycle zero bad deeds.
        - NARAKA if circuit breaker triggered (5 failures).
        """
        self._cycle += 1
        self.realm_duration += 1

        score = self.karma_score
        suggested = SamsaraRealm.HUMAN
        reason = ""

        if score >= 85:
            # Check DEVA condition: no bad deeds in last 3 cycles
            recent_bad = sum(
                1 for d in self.bad_deeds
                if (self._cycle - d.cycle_recorded) <= 3
            )
            if recent_bad == 0:
                suggested = SamsaraRealm.DEVA
                reason = "karma≥85 AND 3-cycle-zero-bad-deeds"
            else:
                suggested = SamsaraRealm.ASURA
                reason = "karma≥85 but recent bad deeds prevent DEVA"
        elif score >= 60:
            suggested = SamsaraRealm.ASURA
            reason = "karma≥60"
        elif score >= 40:
            suggested = SamsaraRealm.HUMAN
            reason = "karma≥40"
        elif score >= 20:
            suggested = SamsaraRealm.ANIMAL
            reason = "karma≥20"
        elif score >= 10:
            suggested = SamsaraRealm.PRETA
            reason = "karma≥10"
        else:
            suggested = SamsaraRealm.NARAKA
            reason = "karma<10"

        return KarmaVerdict(
            current_realm=self.current_realm,
            karma_score=score,
            suggested_realm=suggested,
            confidence=0.9,
            reason=reason,
        )

    async def should_reincarnate(self) -> Optional[SamsaraRealm]:
        """Check if reincarnation is needed.

        IF suggested_realm > current_realm THEN promote.
        IF suggested_realm < current_realm THEN demote.
        IF suggested == current THEN None.

        Max stay check: IF realm_duration >= max_stay_cycles THEN force demotion.
        """
        verdict = await self.evaluate_cycle()
        suggested = verdict.suggested_realm

        if suggested == self.current_realm:
            # Check max stay
            cfg = self._realm_configs.get(self.current_realm)
            if cfg and cfg.max_stay_cycles > 0 and self.realm_duration >= cfg.max_stay_cycles:
                # Force demotion: DEVA→HUMAN, ASURA→HUMAN, etc.
                if self.current_realm == SamsaraRealm.DEVA:
                    return SamsaraRealm.HUMAN
                elif self.current_realm == SamsaraRealm.ASURA:
                    return SamsaraRealm.HUMAN
                elif self.current_realm == SamsaraRealm.ANIMAL:
                    return SamsaraRealm.PRETA
                elif self.current_realm == SamsaraRealm.PRETA:
                    return SamsaraRealm.NARAKA
                elif self.current_realm == SamsaraRealm.NARAKA:
                    return SamsaraRealm.HUMAN  # rebirth
            return None

        return suggested
