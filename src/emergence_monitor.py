from __future__ import annotations

class EmergenceMonitor:
    """实时涌现监控器 — 持续追踪所有维度的涌现信号。

    核心原理:
      1. 追踪所有维度的指标
      2. 检测突变 (非线性变化)
      3. 分类涌现类型 (beneficial / neutral / harmful)
      4. 检测到涌现时触发适应

    检测规则:
      - ≥3个独立源指向同一意外模式 → EMERGENCE
      - 相变: |Δmetric| > 2σ 偏离基线
      - 自组织临界: 事件规模的幂律分布

    _is_beneficial 通过 constructor 的 beneficial_metrics / harmful_metrics 可配置。
    """

    def __init__(
        self,
        emergence_threshold_sigma: float = 3.0,
        min_sources: int = 3,
        beneficial_metrics: set[str] | None = None,
        harmful_metrics: set[str] | None = None,
    ):
        self.threshold_sigma = emergence_threshold_sigma
        self.min_sources = min_sources
        self.trackers: dict[str, MetricTracker] = {}
        self.signals: list[EmergenceSignal] = []
        self._signal_counter: int = 0
        self._beneficial_metrics = beneficial_metrics or {
            "recall", "precision", "verification_pass_rate",
            "pipeline_success_rate", "success_rate", "accuracy",
            "f1_score", "throughput",
        }
        self._harmful_metrics = harmful_metrics or {
            "error_rate", "latency", "entropy", "false_positive_rate",
            "cost", "response_time", "failure_rate",
        }

    def record(self, metric_name: str, value: float, level: DimensionalLevel):
        """记录一个指标值到指定维度。"""
        key = f"{level.name}:{metric_name}"
        if key not in self.trackers:
            self.trackers[key] = MetricTracker(name=key)
        self.trackers[key].record(value)

    def record_batch(self, metrics: dict[str, float], level: DimensionalLevel):
        """批量记录多个指标。"""
        for name, value in metrics.items():
            self.record(name, value, level)

    def check_emergence(self) -> list[EmergenceSignal]:
        """检查所有追踪指标, 返回新检测到的涌现信号。"""
        new_signals = []

        # 检查单个指标偏差
        anomalous_metrics = []
        for key, tracker in self.trackers.items():
            latest = tracker.latest
            if latest is None:
                continue
            sigma = tracker.deviation_sigma(latest)
            if sigma >= self.threshold_sigma:
                anomalous_metrics.append((key, latest, sigma, tracker.mean))

        # 按维度分组
        by_level: dict[DimensionalLevel, list] = {}
        for key, value, sigma, mean in anomalous_metrics:
            level_str = key.split(":")[0]
            try:
                level = DimensionalLevel[level_str]
            except KeyError:
                continue
            if level not in by_level:
                by_level[level] = []
            by_level[level].append((key, value, sigma, mean))

        # 检查是否 ≥ min_sources 在某个维度触发
        for level, metrics in by_level.items():
            if len(metrics) >= self.min_sources:
                deviations = [m[2] for m in metrics]
                avg_dev = sum(deviations) / len(deviations)
                is_beneficial = self._is_beneficial(metrics)

                signal = EmergenceSignal(
                    id=f"EMG-{self._signal_counter:04d}",
                    timestamp=time.time(),
                    emergence_type=(
                        EmergenceType.PHASE_TRANSITION
                        if avg_dev > 5.0
                        else EmergenceType.BENEFICIAL if is_beneficial
                        else EmergenceType.HARMFUL
                    ),
                    dimensional_level=level,
                    sources=[m[0] for m in metrics],
                    metrics={m[0].split(":")[1]: m[1] for m in metrics},
                    deviation_sigma=avg_dev,
                    description=self._describe_emergence(level, metrics, avg_dev, is_beneficial),
                    confidence=min(1.0, len(metrics) / (self.min_sources + 2)),
                )
                new_signals.append(signal)
                self._signal_counter += 1

        self.signals.extend(new_signals)
        return new_signals

    def _is_beneficial(self, metrics: list[tuple]) -> bool:
        """判断异常方向: 改善还是恶化。

        使用 self._beneficial_metrics (越高越好) 和
        self._harmful_metrics (越低越好) 两组可配置集合。
        可通过 __init__ 的 beneficial_metrics / harmful_metrics 参数自定义。
        """
        for key, value, sigma, mean in metrics:
            metric_name = key.split(":")[1]
            if metric_name in self._beneficial_metrics and value > mean:
                return True
            if metric_name in self._harmful_metrics and value < mean:
                return True
        return False

    def _describe_emergence(self, level: DimensionalLevel, metrics: list[tuple],
                            avg_dev: float, is_beneficial: bool) -> str:
        level_names = {
            DimensionalLevel.D0: "Point (D₀) — 原子状态偏移",
            DimensionalLevel.D1: "Line (D₁) — 轨迹异常",
            DimensionalLevel.D2: "Plane (D₂) — 网格拓扑变化",
            DimensionalLevel.D3: "Body (D₃) — 闭环系统相变",
        }
        metric_names = [m[0].split(":")[1] for m in metrics]
        direction = "改善" if is_beneficial else "退化"
        return (
            f"{level_names.get(level, '未知')}: "
            f"{len(metrics)} 个指标 {direction} ({', '.join(metric_names[:3])}) "
            f"偏差 {avg_dev:.1f}σ"
        )

    @property
    def pending_signals(self) -> list[EmergenceSignal]:
        return [s for s in self.signals if not s.resolved]

    @property
    def phase_transitions(self) -> list[EmergenceSignal]:
        return [s for s in self.signals
                if s.emergence_type == EmergenceType.PHASE_TRANSITION]

    def health_report(self) -> dict:
        """健康报告摘要。"""
        return {
            "tracked_metrics": len(self.trackers),
            "total_signals": len(self.signals),
            "pending_signals": len(self.pending_signals),
            "phase_transitions": len(self.phase_transitions),
            "by_level": {
                "D0": sum(1 for s in self.signals
                          if s.dimensional_level == DimensionalLevel.D0),
                "D1": sum(1 for s in self.signals
                          if s.dimensional_level == DimensionalLevel.D1),
                "D2": sum(1 for s in self.signals
                          if s.dimensional_level == DimensionalLevel.D2),
                "D3": sum(1 for s in self.signals
                          if s.dimensional_level == DimensionalLevel.D3),
            },
        }

    def get_metric_stats(self, metric_name: str, level: DimensionalLevel) -> dict | None:
        """获取指定指标的运行统计。"""
        key = f"{level.name}:{metric_name}"
        t = self.trackers.get(key)
        if not t:
            return None
        return {
            "name": t.name,
            "n": t.n,
            "mean": t.mean,
            "std": t.std,
            "latest": t.latest,
            "deviation_sigma": t.deviation_sigma(t.latest) if t.latest is not None else None,
        }


# ═══════════════════════════════════════════════════════════
# Part 3: 维度演进监控 — DimensionalEmergenceMonitor
# ═══════════════════════════════════════════════════════════

class DimensionalEmergenceMonitor(EmergenceMonitor):
    """维度演进专用涌现监控器。

    与 dimensional_evolution.py 集成, 检测 D₀→D₁→D₂→D₃ 的相变。
    """

    def track_dimension_transition(
        self,
        from_level: DimensionalLevel,
        to_level: DimensionalLevel,
        transition_cost: float,
    ):
        """记录一次维度跃迁事件。"""
        self.record(
            f"transition_cost_{from_level.name}_to_{to_level.name}",
            transition_cost,
            to_level,
        )
        self.record("current_dimension", to_level.value, to_level)

    def check_dimensional_emergence(self) -> Optional[EmergenceSignal]:
        """专门检查维度相变。"""
        signals = self.check_emergence()
        for sig in signals:
            if sig.emergence_type == EmergenceType.PHASE_TRANSITION:
                return sig

        # 检查 D₂→D₃ 跃迁: 多个未解决的 D₂ 信号累积
        d2_count = sum(
            1 for s in self.signals
            if s.dimensional_level == DimensionalLevel.D2 and not s.resolved
        )
        if d2_count >= self.min_sources:
            self._signal_counter += 1
            signal = EmergenceSignal(
                id=f"EMG-{self._signal_counter:04d}",
                timestamp=time.time(),
                emergence_type=EmergenceType.PHASE_TRANSITION,
                dimensional_level=DimensionalLevel.D3,
                sources=[f"D2_signal_{i}" for i in range(d2_count)],
                metrics={"d2_signal_count": d2_count},
                deviation_sigma=4.0,
                description=(
                    f"Body (D₃) 涌现: {d2_count} 个 D₂ 信号累积"
                    f" — 自组织临界 → 闭环系统形成"
                ),
                confidence=min(0.9, d2_count / 6),
            )
            self.signals.append(signal)
            return signal

        return None


# ═══════════════════════════════════════════════════════════
# Part 4: 离线批次分析 — EmergenceEngine (三层: 异常→突变→理论)
# ═══════════════════════════════════════════════════════════


def _deduplicate_changes(
    changes: list[dict],
    min_segment_length: int = 3,
) -> list[dict]:
    """去重突变点: 相近年份只保留效应量最大的。"""
    if len(changes) <= 1:
        return changes
    deduped = [changes[0]]
    for r in changes[1:]:
        if r["year"] - deduped[-1]["year"] <= min_segment_length:
            if r["magnitude"] > deduped[-1]["magnitude"]:
                deduped[-1] = r
        else:
            deduped.append(r)
    return deduped


KNOWN_PATTERNS: list[dict] = [
    {
        "name": "非对称恢复",
        "signal": "体型恢复速率 > 多样性恢复速率",
        "theory": "非对称恢复假说 (蔡方陶 2026)",
        "test_statistic": "body_size_slope / diversity_slope",
        "threshold": 2.0,
        "direction": "above",
        "priority": "P0",
    },
    {
        "name": "K策略者悖论",
        "signal": "K策略者恢复率 > r策略者恢复率",
        "theory": "r-K选择理论 (MacArthur 1967) + 受损基数假说",
        "test_statistic": "K_recovery_rate / r_recovery_rate",
        "threshold": 1.5,
        "direction": "above",
        "priority": "P1",
    },
    {
        "name": "连通性效应",
        "signal": "通江湖泊恢复 > 隔离湖泊恢复",
        "theory": "岛屿生物地理学 (MacArthur & Wilson 1967)",
        "test_statistic": "connected_lake_recovery / isolated_lake_recovery",
        "threshold": 1.3,
        "direction": "above",
        "priority": "P1",
    },
    {
        "name": "中度干扰",
        "signal": "物种多样性在中等干扰时最高",
        "theory": "中度干扰假说 (Connell 1978)",
        "test_statistic": "H_diversity vs disturbance_level",
        "threshold": 0.0,
        "direction": "peak",
        "priority": "P2",
    },
    {
        "name": "自然流态断裂",
        "signal": "水文改变量 > 历史变异范围 → 鱼类群落退化",
        "theory": "自然流态范式 (Poff 1997) + 道法自然",
        "test_statistic": "hydrologic_alteration vs community_change",
        "threshold": 1.0,
        "direction": "above",
        "priority": "P1",
    },
    {
        "name": "降维打击",
        "signal": "群落组成越过不可逆阈值",
        "theory": "状态转换模型 (Westoby 1989) + 三体降维打击",
        "test_statistic": "state_transition_detected",
        "threshold": 0,
        "direction": "above",
        "priority": "P0",
    },
]

