"""KarmaRecord / KarmaDigest / KarmaContext — 业力数据结构.

Separated from karma_engine.py for clean imports.
These are pure data classes with no engine logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class KarmaRecord:
    """A single karma event (good or bad deed).

    Stored in KarmaEngine.good_deeds / KarmaEngine.bad_deeds deques.
    Decays over time per the decay function.
    """

    deed_type: str
    score: float
    half_life_cycles: int = 5
    cooldown_cycles: int = 0
    cycle_recorded: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    def current_weight(self, current_cycle: int) -> float:
        """Compute decayed weight: score × 0.5^(age / half_life).

        IF half_life_cycles <= 0 THEN return score unchanged.
        IF age <= 0 THEN return score unchanged.
        """
        age = current_cycle - self.cycle_recorded
        if age <= 0 or self.half_life_cycles <= 0:
            return self.score
        return self.score * (0.5 ** (age / self.half_life_cycles))


@dataclass(slots=True)
class KarmaDigest:
    """Summary of an agent's karma state for one cycle.

    Submitted to KarmaCourt for evaluation.
    """

    agent_id: str = ""
    current_realm: str = ""
    karma_score: float = 50.0
    suggested_realm: str = ""
    good_deeds_count: int = 0
    bad_deeds_count: int = 0
    lifetime_karma: float = 50.0
    realm_duration: int = 0
    confidence: float = 1.0
    reason: str = ""


@dataclass(slots=True)
class KarmaContext:
    """Context passed with SystemEvent for karma tracking.

    Embedded in every SystemEvent.karma_context field.
    """

    agent_id: str = ""
    expected_quality: float = 0.8
    deadline_seconds: float = 30.0


@dataclass(slots=True)
class KarmaVerdict:
    """Result of KarmaEngine.evaluate_cycle()."""

    current_realm: str = ""
    karma_score: float = 50.0
    suggested_realm: str = ""
    confidence: float = 1.0
    reason: str = ""


# ── Good deed definitions (constant lookup table) ──

GOOD_DEED_SPECS: Dict[str, Dict[str, Any]] = {
    "HIGH_RECALL": {
        "condition": "recall >= 0.98",
        "base_score": +3,
        "half_life_cycles": 5,
        "cooldown_cycles": 0,
    },
    "HIGH_PRECISION": {
        "condition": "precision >= 0.95",
        "base_score": +2,
        "half_life_cycles": 5,
        "cooldown_cycles": 0,
    },
    "LOW_LATENCY": {
        "condition": "latency_p99_ms < 500",
        "base_score": +1,
        "half_life_cycles": 3,
        "cooldown_cycles": 0,
    },
    "USER_SATISFACTION": {
        "condition": "user_rating >= 4.5",
        "base_score": +5,
        "half_life_cycles": 8,
        "cooldown_cycles": 0,
    },
    "NOVEL_DISCOVERY": {
        "condition": "cache_hit == false AND result.is_novel",
        "base_score": +4,
        "half_life_cycles": 3,
        "cooldown_cycles": 0,
    },
    "SUCCESSFUL_COLLABORATION": {
        "condition": "cross_vertex_request_success",
        "base_score": +3,
        "half_life_cycles": 3,
        "cooldown_cycles": 0,
    },
}

# ── Bad deed definitions (constant lookup table) ──

BAD_DEED_SPECS: Dict[str, Dict[str, Any]] = {
    "HALLUCINATION": {
        "condition": "hallucination_rate > 0.10",
        "base_score": -5,
        "score_multiplier": "hallucination_rate",
        "cooldown_cycles": 3,
    },
    "TIMEOUT": {
        "condition": "request_timed_out",
        "base_score": -3,
        "cooldown_cycles": 2,
    },
    "CONTRADICTION_LOST": {
        "condition": "self_claim_proven_wrong",
        "base_score": -4,
        "cooldown_cycles": 0,
    },
    "RATE_LIMIT_HIT": {
        "condition": "rate_limiter_triggered",
        "base_score": -2,
        "cooldown_cycles": 1,
    },
    "RESOURCE_WASTE": {
        "condition": "tokens_used > budget * 1.5 AND quality_score < 0.5",
        "base_score": -3,
        "cooldown_cycles": 3,
    },
    "STALE_RESPONSE": {
        "condition": "cache_age_seconds > config.cache_ttl * 2",
        "base_score": -1,
        "cooldown_cycles": 1,
    },
}
