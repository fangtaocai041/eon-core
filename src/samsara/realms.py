"""SamsaraRealm — 六道定义.

Six realms in the samsara wheel:
  DEVA    (天道) — OPTIMAL, karma ≥ 85, 1.5× tokens
  HUMAN   (人道) — NORMAL,  karma ∈ [40, 85), 1.0× tokens
  ASURA   (阿修罗) — COMPETITIVE, karma ∈ [60, 90), 1.2× tokens
  ANIMAL  (畜生道) — DEGRADED, karma ∈ [20, 40), 0.5× tokens
  PRETA   (饿鬼道) — STARVED, karma ∈ [10, 20), 0.25× tokens
  NARAKA  (地狱道) — CIRCUIT_BROKEN, karma < 10, 0.0× tokens

Each realm has:
  - karma_threshold: minimum karma to enter
  - token_budget_multiplier: resource allocation factor
  - search_depth: how deep to search
  - max_stay_cycles: maximum cycles before forced transition
  - confidence_modifier: multiplier on output confidence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class SamsaraRealm(StrEnum):
    DEVA = "DEVA"
    HUMAN = "HUMAN"
    ASURA = "ASURA"
    ANIMAL = "ANIMAL"
    PRETA = "PRETA"
    NARAKA = "NARAKA"


# Realm ordering for comparison (higher = better)
_REALM_ORDER: dict[SamsaraRealm, int] = {
    SamsaraRealm.NARAKA: 0,
    SamsaraRealm.PRETA: 1,
    SamsaraRealm.ANIMAL: 2,
    SamsaraRealm.HUMAN: 3,
    SamsaraRealm.ASURA: 4,
    SamsaraRealm.DEVA: 5,
}


def realm_compare(a: SamsaraRealm, b: SamsaraRealm) -> int:
    """Compare two realms: -1 if a<b, 0 if equal, 1 if a>b."""
    return (_REALM_ORDER.get(a, 0) > _REALM_ORDER.get(b, 0)) - (
        _REALM_ORDER.get(a, 0) < _REALM_ORDER.get(b, 0)
    )


def realm_gt(a: SamsaraRealm, b: SamsaraRealm) -> bool:
    """Is realm a better than realm b?"""
    return _REALM_ORDER.get(a, 0) > _REALM_ORDER.get(b, 0)


@dataclass
class RealmConfig:
    """Configuration for a single realm."""

    realm: SamsaraRealm
    name_cn: str = ""
    karma_threshold: float = 50.0
    token_budget_multiplier: float = 1.0
    gpu_priority: str = "MEDIUM"
    search_depth: int = -1  # -1 = unlimited
    max_stay_cycles: int = -1  # -1 = unlimited
    confidence_modifier: Optional[float] = 1.0
    initial_karma: float = 50.0
    special_rule: str = ""


# Default realm configs
DEFAULT_REALMS: dict[SamsaraRealm, RealmConfig] = {
    SamsaraRealm.DEVA: RealmConfig(
        realm=SamsaraRealm.DEVA,
        name_cn="天道",
        karma_threshold=85.0,
        token_budget_multiplier=1.5,
        gpu_priority="HIGH",
        search_depth=-1,  # unlimited
        max_stay_cycles=10,
        confidence_modifier=1.1,
        initial_karma=85.0,
        special_rule="bad_deed_penalty_multiplier=3.0",
    ),
    SamsaraRealm.HUMAN: RealmConfig(
        realm=SamsaraRealm.HUMAN,
        name_cn="人道",
        karma_threshold=40.0,
        token_budget_multiplier=1.0,
        gpu_priority="MEDIUM",
        search_depth=-1,  # standard
        max_stay_cycles=-1,  # unlimited
        confidence_modifier=1.0,
        initial_karma=50.0,
        special_rule="唯一可主动触发self_evolve()的状态",
    ),
    SamsaraRealm.ASURA: RealmConfig(
        realm=SamsaraRealm.ASURA,
        name_cn="阿修罗道",
        karma_threshold=60.0,
        token_budget_multiplier=1.2,
        gpu_priority="MEDIUM_HIGH",
        search_depth=3,
        max_stay_cycles=5,
        confidence_modifier=0.9,
        initial_karma=60.0,
        special_rule="产出需经DeconflictionPass二次验证",
    ),
    SamsaraRealm.ANIMAL: RealmConfig(
        realm=SamsaraRealm.ANIMAL,
        name_cn="畜生道",
        karma_threshold=20.0,
        token_budget_multiplier=0.5,
        gpu_priority="LOW",
        search_depth=1,
        max_stay_cycles=8,
        confidence_modifier=0.7,
        initial_karma=30.0,
        special_rule="禁用LLM推理链，仅缓存+规则匹配",
    ),
    SamsaraRealm.PRETA: RealmConfig(
        realm=SamsaraRealm.PRETA,
        name_cn="饿鬼道",
        karma_threshold=10.0,
        token_budget_multiplier=0.25,
        gpu_priority="LOWEST",
        search_depth=1,
        max_stay_cycles=12,
        confidence_modifier=0.5,
        initial_karma=15.0,
        special_rule="rate_limiter_tokens=normal×0.25",
    ),
    SamsaraRealm.NARAKA: RealmConfig(
        realm=SamsaraRealm.NARAKA,
        name_cn="地狱道",
        karma_threshold=0.0,
        token_budget_multiplier=0.0,
        gpu_priority="NONE",
        search_depth=0,
        max_stay_cycles=5,
        confidence_modifier=None,
        initial_karma=5.0,
        special_rule="完全隔离+后台自检+冷却max(30s,severity×60s)",
    ),
}
