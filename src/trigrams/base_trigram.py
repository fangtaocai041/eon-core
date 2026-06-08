"""BaseTrigram — 八卦子模块抽象基类.

Each trigram:
  - Has a gua_symbol (☰☱☲☳☴☵☶☷)
  - Belongs to a parent BaseVertex
  - Embeds a KarmaEngine
  - Exposes execute(input) → TrigramOutput
  - Exposes health() → HealthReport

Design: each trigram is a self-contained functional module
that can be composed into vertices. Trigram instances are
NEVER imported directly — they are registered via vertex.register_trigram().
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, Optional


class TrigramGua(StrEnum):
    QIAN = "☰"  # 乾 — Heaven/Creative
    DUI  = "☱"  # 兑 — Lake/Joyous
    LI   = "☲"  # 离 — Fire/Clinging
    ZHEN = "☳"  # 震 — Thunder/Arousing
    XUN  = "☴"  # 巽 — Wind/Gentle
    KAN  = "☵"  # 坎 — Water/Abysmal
    GEN  = "☶"  # 艮 — Mountain/Still
    KUN  = "☷"  # 坤 — Earth/Receptive


@dataclass
class TrigramInput:
    """Input to trigram.execute()."""
    query: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""


@dataclass
class TrigramOutput:
    """Output from trigram.execute()."""
    status: str = "ok"
    result: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class TrigramHealth:
    """Health report for a trigram."""
    status: str = "UNKNOWN"
    latency_p99_ms: float = 0.0
    error_rate: float = 0.0
    karma_score: float = 50.0


class BaseTrigram(ABC):
    """Abstract trigram — functional sub-module of a vertex.

    Each trigram is registered to exactly ONE parent vertex.
    """

    def __init__(
        self,
        trigram_id: str,
        gua: TrigramGua,
        enabled: bool = True,
    ) -> None:
        self.trigram_id: str = trigram_id
        self.gua_symbol: str = gua.value
        self.parent_vertex: Any = None
        self.karma_engine: Any = None
        self.enabled: bool = enabled
        self.config: Dict[str, Any] = {}
        self._latency_samples: list[float] = []

    @abstractmethod
    async def execute(self, input: TrigramInput) -> TrigramOutput:
        """Execute the trigram's core function.

        Subclass implements the specific logic:
          - qian: parallel search + RRF fusion
          - dui:  CNKI/CSCD/万方 adapter
          - li:   graph traversal
          - zhen: multi-model debate
          - xun:  acoustic analysis
          - kan:  population modeling
          - gen:  otolith analysis
          - kun:  resource assessment
        """
        ...

    async def health(self) -> TrigramHealth:
        """Return trigram health metrics.

        IF enabled == False THEN status = DISABLED.
        IF error_rate > 0.10 THEN status = DEGRADED.
        ELSE status = HEALTHY.
        """
        if not self.enabled:
            return TrigramHealth(status="DISABLED")

        error_rate = 0.0  # track from execute() failures
        p99 = 0.0
        if self._latency_samples:
            sorted_samples = sorted(self._latency_samples)
            idx = int(len(sorted_samples) * 0.99)
            p99 = sorted_samples[min(idx, len(sorted_samples) - 1)]

        status = "DEGRADED" if error_rate > 0.10 else "HEALTHY"

        return TrigramHealth(
            status=status,
            latency_p99_ms=p99,
            error_rate=error_rate,
            karma_score=self.karma_engine.karma_score if self.karma_engine else 50.0,
        )

    def belong_to(self) -> Any:
        """Return the parent vertex this trigram is attached to."""
        return self.parent_vertex

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.trigram_id}) {self.gua_symbol}>"
