"""
unified_emergence.py — 统一涌现检测引擎
=========================================
融合三项目涌现能力:
  - p项目 (porpoise-agent): 实时 Z-score 监控 + D₀/D₁/D₂/D₃ 维度感知
  - f项目 (fish-ecology-assistant): 三层分析（异常→突变→理论匹配）+ 6理论模式
  - c项目 (cognitive-search-engine): 自组织领域发现 (emerge_domains)

架构:
  Online (实时监控)              Offline (批次分析)
  ┌─────────────────────┐      ┌──────────────────────┐
  │  EmergenceMonitor    │      │  EmergenceEngine     │
  │  · Z-score 异常检测   │      │  · Layer 1 异常      │
  │  · D₀~D₃ 维度追踪    │      │  · Layer 2 突变点     │
  │  · D₂→D₃ 相变检测    │      │  · Layer 3 理论匹配   │
  └─────────────────────┘      └──────────────────────┘
          │                            │
          └──────────┬─────────────────┘
                     ▼
          ┌──────────────────────┐
          │  emerge_domains()    │
          │  自组织领域发现       │
          └──────────────────────┘

Usage:
    # 实时监控
    mon = EmergenceMonitor(emergence_threshold_sigma=3.0, min_sources=3)
    mon.record("recall", 0.85, DimensionalLevel.D1)
    signals = mon.check_emergence()

    # 离线分析
    engine = EmergenceEngine()
    results = engine.scan(data={"years": [2018,...,2025], "biomass": [100,...,260]})

    # 自组织领域发现
    suggestions = emerge_domains(catalog)
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# scipy — 可选 (p-value 统计显著性)
try:
    from scipy.stats import norm as _norm
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ═══════════════════════════════════════════════════════════
# Part 1: 基础类型 — 信号、维度、检测结果
# ═══════════════════════════════════════════════════════════

class EmergenceType(Enum):
    """涌现类型分类。"""
    BENEFICIAL = "beneficial"          # 系统意外改善
    NEUTRAL = "neutral"                # 有趣但无害
    HARMFUL = "harmful"                # 系统意外退化
    PHASE_TRANSITION = "phase_transition"  # 维度跃迁 (D₁→D₂ 等)
    ANOMALY = "anomaly"                # 无法解释的离群点


class DimensionalLevel(Enum):
    """维度等级 (D₀→D₁→D₂→D₃ 严格包含层次)。"""
    D0 = 0  # Point — 原子状态
    D1 = 1  # Line — 因果轨迹
    D2 = 2  # Plane — 拓扑网格
    D3 = 3  # Body — 闭环实体


@dataclass
class EmergenceSignal:
    """实时涌现事件信号 (来自 porpoise-agent)。"""
    id: str
    timestamp: float
    emergence_type: EmergenceType
    dimensional_level: DimensionalLevel
    sources: list[str]              # 确认该信号的独立源
    metrics: dict[str, float]       # 异常指标
    deviation_sigma: float          # 偏离基线多少σ
    description: str
    confidence: float               # 0-1
    resolved: bool = False
    resolution_note: str = ""


@dataclass
class DetectionResult:
    """离线批次分析检测结果 (取代 f 项目原 EmergenceSignal)。"""
    detection_type: str  # "anomaly" | "change_point" | "theory_match"
    species: str         # 物种名
    description: str     # 人类可读描述
    confidence: float    # 0-1
    evidence: dict       # 数据证据
    suggested_theory: str = ""
    suggested_action: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MetricTracker:
    """运行统计追踪器 — Welford 在线方差算法。

    使用 Welford (1962) 单次遍历、数值稳定算法计算均值和方差。
    修正了原 _sum/_sum_sq 只加不减的溢出 bug。

    Reference:
      B. P. Welford (1962). "Note on a Method for Calculating Corrected
      Sums of Squares and Products". Technometrics 4(3):419–420.
    """
    name: str
    history: deque = field(default_factory=lambda: deque(maxlen=100))
    # Welford accumulator
    _n: int = 0
    _mean: float = 0.0
    _M2: float = 0.0   # 二阶中心矩 (sum of squared deviations)

    def record(self, value: float):
        """记录一个新值 (Welford 在线更新)。"""
        self.history.append(value)
        self._n += 1
        delta = value - self._mean
        self._mean += delta / self._n
        delta2 = value - self._mean
        self._M2 += delta * delta2

    @property
    def mean(self) -> float:
        return self._mean if self._n > 0 else 0.0

    @property
    def variance(self) -> float:
        """样本方差 (n-1 分母)。"""
        if self._n < 2:
            return 1.0
        return self._M2 / (self._n - 1)

    @property
    def std(self) -> float:
        return math.sqrt(max(self.variance, 0.0)) or 1.0

    @property
    def latest(self) -> Optional[float]:
        return self.history[-1] if self.history else None

    def deviation_sigma(self, value: float) -> float:
        """当前值偏离均值多少个标准差。"""
        return abs(value - self.mean) / max(self.std, 0.001)

    @property
    def n(self) -> int:
        return self._n

    def stats(self) -> dict:
        """返回完整统计摘要。"""
        return {
            "name": self.name,
            "n": self._n,
            "mean": round(self.mean, 6),
            "std": round(self.std, 6),
            "variance": round(self.variance, 6),
            "latest": self.latest,
            "sigma": round(self.deviation_sigma(self.latest), 3) if self.latest is not None else None,
        }


# ═══════════════════════════════════════════════════════════
# Part 2: 实时监控 — EmergenceMonitor (p项目原版)
# ═══════════════════════════════════════════════════════════
