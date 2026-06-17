"""WuxingMonitor — 五行健康监控器 (L5 监控与评估层).

五行映射 eon-core 子系统:
  金 (Metal)  → 搜索子系统 (V1 cognitive-search-engine)
  木 (Wood)   → 生长/分析 (V2/V3/V4 领域专研)
  水 (Water)  → 数据流 (V0 fish-ecology-assistant + EventBus)
  火 (Fire)   → 评分/仲裁 (V5 conflict-arbiter)
  土 (Earth)  → 存储/缓存 (项目加载器 + 配置)

每行追踪:
  - 调用次数 (call_count)
  - 成功率 (success_rate)
  - 平均延迟 (avg_latency_ms)
  - 最后状态 (last_status)
  - 最后更新时间

health_report() 返回五行健康面板，含整体评级。

用法:
    monitor = WuxingMonitor()
    monitor.record_call(WuxingElement.METAL, success=True, latency_ms=45.2)
    report = monitor.health_report()
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class WuxingElement(str, Enum):
    """五行元素 — 对应 eon-core 子系统."""
    METAL = "metal"     # 金: 搜索 (V1 cognitive)
    WOOD = "wood"       # 木: 生长/分析 (V2/V3/V4 领域)
    WATER = "water"     # 水: 数据流 (V0 fish + EventBus)
    FIRE = "fire"       # 火: 评分/仲裁 (V5 conflict)
    EARTH = "earth"     # 土: 存储/缓存 (loader + config)


class HealthGrade(str, Enum):
    """健康等级."""
    EXCELLENT = "excellent"     # ≥ 95% 成功率, < 100ms 延迟
    GOOD = "good"               # ≥ 85% 成功率, < 500ms 延迟
    FAIR = "fair"               # ≥ 70% 成功率, < 1000ms 延迟
    DEGRADED = "degraded"       # < 70% 成功率, 或高延迟
    DOWN = "down"                # 连续失败 > 10 次


# ═══════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════

@dataclass
class ElementMetrics:
    """单个五行元素的指标."""
    element: WuxingElement
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    # 最近 100 次调用的延迟 (环形)
    _recent_latencies: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    last_status: str = "unknown"
    last_error: Optional[str] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return self.success_count / self.call_count

    @property
    def avg_latency_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_latency_ms / self.call_count

    @property
    def recent_avg_latency_ms(self) -> float:
        if not self._recent_latencies:
            return 0.0
        return sum(self._recent_latencies) / len(self._recent_latencies)

    @property
    def grade(self) -> HealthGrade:
        if self.call_count == 0:
            return HealthGrade.FAIR
        if self.consecutive_failures > 10:
            return HealthGrade.DOWN
        if self.success_rate >= 0.95 and self.avg_latency_ms < 100:
            return HealthGrade.EXCELLENT
        if self.success_rate >= 0.85 and self.avg_latency_ms < 500:
            return HealthGrade.GOOD
        if self.success_rate >= 0.70:
            return HealthGrade.FAIR
        return HealthGrade.DEGRADED


@dataclass
class WuxingReport:
    """五行健康综合报告."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    elements: Dict[str, ElementMetrics] = field(default_factory=dict)
    overall_grade: HealthGrade = HealthGrade.FAIR
    generation_cycle_ok: bool = True      # 相生循环正常
    restriction_cycle_ok: bool = True     # 相克循环正常
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_grade": self.overall_grade.value,
            "generation_cycle_ok": self.generation_cycle_ok,
            "restriction_cycle_ok": self.restriction_cycle_ok,
            "notes": self.notes,
            "elements": {
                eid: {
                    "element": m.element.value,
                    "call_count": m.call_count,
                    "success_count": m.success_count,
                    "failure_count": m.failure_count,
                    "success_rate": round(m.success_rate, 4),
                    "avg_latency_ms": round(m.avg_latency_ms, 2),
                    "recent_avg_latency_ms": round(m.recent_avg_latency_ms, 2),
                    "grade": m.grade.value,
                    "last_status": m.last_status,
                    "consecutive_failures": m.consecutive_failures,
                }
                for eid, m in self.elements.items()
            },
        }


# ═══════════════════════════════════════════════════════════════
# WuxingMonitor
# ═══════════════════════════════════════════════════════════════

class WuxingMonitor:
    """五行健康监控器。

    五行相生 (generation cycle):
      金生水 → 水生木 → 木生火 → 火生土 → 土生金
      Metal→Water→Wood→Fire→Earth→Metal

    五行相克 (restriction cycle):
      金克木 → 木克土 → 土克水 → 水克火 → 火克金
      Metal→Wood→Earth→Water→Fire→Metal

    生成关系 (每行是否正常输出到下一行):
      - 金(搜索) → 水(数据流): 搜索结果流入 EventBus
      - 水(数据流) → 木(分析): 数据进入领域分析
      - 木(分析) → 火(仲裁): 分析结果进入评分
      - 火(仲裁) → 土(存储): 仲裁结果持久化
      - 土(存储) → 金(搜索): 缓存加速搜索

    克制关系 (每行是否受制衡):
      - 若某行过强 (success_rate > 0.99, latency < 10ms)，检查克制方是否健康
    """

    # 相生: Metal→Water→Wood→Fire→Earth→Metal
    _GENERATION: Dict[WuxingElement, WuxingElement] = {
        WuxingElement.METAL: WuxingElement.WATER,
        WuxingElement.WATER: WuxingElement.WOOD,
        WuxingElement.WOOD: WuxingElement.FIRE,
        WuxingElement.FIRE: WuxingElement.EARTH,
        WuxingElement.EARTH: WuxingElement.METAL,
    }

    # 相克: Metal→Wood→Earth→Water→Fire→Metal
    _RESTRICTION: Dict[WuxingElement, WuxingElement] = {
        WuxingElement.METAL: WuxingElement.WOOD,
        WuxingElement.WOOD: WuxingElement.EARTH,
        WuxingElement.EARTH: WuxingElement.WATER,
        WuxingElement.WATER: WuxingElement.FIRE,
        WuxingElement.FIRE: WuxingElement.METAL,
    }

    def __init__(self) -> None:
        self._elements: Dict[WuxingElement, ElementMetrics] = {
            elem: ElementMetrics(element=elem) for elem in WuxingElement
        }
        self._started_at = datetime.now(timezone.utc)

    # ── Record API ──

    def record_call(
        self,
        element: WuxingElement,
        *,
        success: bool = True,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """记录一次五行元素调用。

        Args:
            element: 五行元素
            success: 调用是否成功
            latency_ms: 调用延迟 (毫秒)
            error: 错误信息 (失败时)
        """
        metrics = self._elements[element]
        metrics.call_count += 1
        metrics.total_latency_ms += latency_ms
        metrics._recent_latencies.append(latency_ms)
        metrics.last_updated = datetime.now(timezone.utc)

        if success:
            metrics.success_count += 1
            metrics.last_status = "ok"
            metrics.consecutive_failures = 0
        else:
            metrics.failure_count += 1
            metrics.last_status = "error"
            metrics.last_error = error
            metrics.consecutive_failures += 1

    def record_batch(
        self,
        element: WuxingElement,
        successes: int = 0,
        failures: int = 0,
        latencies_ms: Optional[List[float]] = None,
    ) -> None:
        """批量记录调用 (避免多次调用减少记录开销)."""
        metrics = self._elements[element]
        total = successes + failures
        metrics.call_count += total
        metrics.success_count += successes
        metrics.failure_count += failures

        if latencies_ms:
            total_lat = sum(latencies_ms)
            metrics.total_latency_ms += total_lat
            for lat in latencies_ms:
                metrics._recent_latencies.append(lat)

        if failures > 0:
            metrics.last_status = "error"
            metrics.consecutive_failures += failures
        else:
            metrics.last_status = "ok"
            metrics.consecutive_failures = 0

        metrics.last_updated = datetime.now(timezone.utc)

    def reset_element(self, element: WuxingElement) -> None:
        """重置单个元素的指标."""
        self._elements[element] = ElementMetrics(element=element)

    def reset_all(self) -> None:
        """重置所有元素指标."""
        for elem in WuxingElement:
            self._elements[elem] = ElementMetrics(element=elem)
        self._started_at = datetime.now(timezone.utc)

    # ── Health report ──

    def health_report(self) -> WuxingReport:
        """生成五行健康综合报告。

        检查:
          1. 每行健康等级
          2. 相生循环: 每行是否正常输出到下一行
          3. 相克循环: 是否有某行过强需要制衡
          4. 整体评级
        """
        report = WuxingReport()
        report.elements = {
            elem.value: self._elements[elem] for elem in WuxingElement
        }

        notes: List[str] = []

        # 1. Check per-element grade
        grades = [m.grade for m in self._elements.values()]

        # 2. Check generation cycle
        for src, dst in self._GENERATION.items():
            src_m = self._elements[src]
            dst_m = self._elements[dst]
            # If source has failures, downstream may be starved
            if src_m.grade in (HealthGrade.DEGRADED, HealthGrade.DOWN):
                if dst_m.grade in (HealthGrade.EXCELLENT, HealthGrade.GOOD):
                    notes.append(
                        f"generation_warning: {src.value}({src_m.grade.value}) "
                        f"→ {dst.value}({dst_m.grade.value}) — "
                        f"downstream still healthy, may be using cached data"
                    )

        if not notes:
            report.generation_cycle_ok = True
        else:
            report.generation_cycle_ok = all(
                "generation_warning" in n for n in notes
            )

        # 3. Check restriction cycle
        restriction_notes: List[str] = []
        for restrictor, restricted in self._RESTRICTION.items():
            r_m = self._elements[restrictor]
            rd_m = self._elements[restricted]
            # If restrictor is down but restricted is over-active
            if r_m.grade in (HealthGrade.DEGRADED, HealthGrade.DOWN):
                if rd_m.call_count > 100 and rd_m.success_rate > 0.9:
                    restriction_notes.append(
                        f"restriction_breach: {restrictor.value}({r_m.grade.value}) "
                        f"cannot restrict {restricted.value}({rd_m.grade.value}) — "
                        f"unchecked growth risk"
                    )

        report.restriction_cycle_ok = len(restriction_notes) == 0
        notes.extend(restriction_notes)

        # 4. Overall grade
        if any(g == HealthGrade.DOWN for g in grades):
            report.overall_grade = HealthGrade.DOWN
        elif any(g == HealthGrade.DEGRADED for g in grades):
            report.overall_grade = HealthGrade.DEGRADED
        elif any(g == HealthGrade.FAIR for g in grades):
            report.overall_grade = HealthGrade.FAIR
        elif all(g == HealthGrade.EXCELLENT for g in grades):
            report.overall_grade = HealthGrade.EXCELLENT
        else:
            report.overall_grade = HealthGrade.GOOD

        report.notes = notes
        return report

    # ── Quick accessors ──

    def get_element_metrics(self, element: WuxingElement) -> ElementMetrics:
        return self._elements[element]

    @property
    def metal(self) -> ElementMetrics:
        return self._elements[WuxingElement.METAL]

    @property
    def wood(self) -> ElementMetrics:
        return self._elements[WuxingElement.WOOD]

    @property
    def water(self) -> ElementMetrics:
        return self._elements[WuxingElement.WATER]

    @property
    def fire(self) -> ElementMetrics:
        return self._elements[WuxingElement.FIRE]

    @property
    def earth(self) -> ElementMetrics:
        return self._elements[WuxingElement.EARTH]

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    # ── Snapshot ──

    def snapshot(self) -> Dict[str, Any]:
        """快速快照 (轻量, 不含完整报告)."""
        return {
            elem.value: {
                "calls": m.call_count,
                "success_rate": round(m.success_rate, 3),
                "avg_ms": round(m.avg_latency_ms, 1),
                "grade": m.grade.value,
                "last": m.last_status,
                "consecutive_fails": m.consecutive_failures,
            }
            for elem, m in self._elements.items()
        }
