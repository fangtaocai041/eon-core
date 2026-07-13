from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
from .emergence_types import EmergenceType, DimensionalLevel, EmergenceSignal, DetectionResult, MetricTracker
from .emergence_monitor import EmergenceMonitor, DimensionalEmergenceMonitor, _deduplicate_changes

KNOWN_PATTERNS: list[dict] = [
    {"name": "asymmetric_recovery", "signal": "body_size_recovery > diversity_recovery",
     "theory": "Asymmetric Recovery", "test_statistic": "ratio", "threshold": 2.0,
     "direction": "above", "priority": "P0"},
]

class EmergenceEngine:
    """离线涌现分析引擎 — 三层架构。

    Layer 1: 时间序列异常检测 → 发现"意外"
    Layer 2: 突变点检测 → 定位"何时发生"
    Layer 3: 理论匹配 → 解释"为什么"

    与 EmergenceMonitor 的实时监控不同,
    EmergenceEngine 处理完整的批次数据集。
    """

    KNOWN_PATTERNS = KNOWN_PATTERNS

    def __init__(
        self,
        data_path: str | Path | None = None,
        feedback_file: str | Path | None = None,
    ) -> None:
        self._data_path = Path(data_path) if data_path else Path("data")
        self._feedback_file = (
            Path(feedback_file) if feedback_file
            else Path.cwd() / "logs" / "catalog_feedback.jsonl"
        )

    # ── Layer 1: 异常检测 ──

    @staticmethod
    def detect_anomalies(
        time_series: list[float],
        dates: list[int],
        method: str = "zscore",
        sensitivity: float = 0.05,
    ) -> list[dict]:
        """Layer 1 — 时间序列异常检测。

        方法:
          - "zscore": 标准化偏差法 (≥3σ 为异常, 附带 p-value)
          - "iqr":    四分位距法 (附带 p-value)
          - "window": 滑动窗口法

        Args:
            time_series: 数值序列
            dates:       对应年份
            method:      "zscore" | "iqr" | "window"
            sensitivity: 灵敏度 (0.01-0.10)

        Returns:
            [{"year": int, "value": float, "z_score": float,
              "p_value": float|None, "is_anomaly": bool}, ...]
        """
        n = len(time_series)
        if n < 5:
            return [{"year": d, "value": v, "is_anomaly": False}
                    for d, v in zip(dates, time_series)]

        # Z-score 方法
        if method == "zscore":
            mean = sum(time_series) / n
            variance = sum((x - mean) ** 2 for x in time_series) / n
            std = math.sqrt(variance) if variance > 0 else 1.0
            threshold = max(2.0, 3.0 - sensitivity * 20)
            results = []
            for year, value in zip(dates, time_series):
                z = (value - mean) / std
                p_val = (2.0 * (1.0 - _norm.cdf(abs(z)))
                         if _HAS_SCIPY else None)
                results.append({
                    "year": year,
                    "value": value,
                    "z_score": round(z, 3),
                    "p_value": round(p_val, 6) if p_val is not None else None,
                    "is_anomaly": abs(z) > threshold,
                })
            return results

        # IQR 方法
        if method == "iqr":
            sorted_vals = sorted(time_series)
            q1 = sorted_vals[n // 4]
            q3 = sorted_vals[3 * n // 4]
            iqr_val = q3 - q1
            lower = q1 - 1.5 * iqr_val
            upper = q3 + 1.5 * iqr_val
            mean_val = sum(time_series) / n
            std_val = math.sqrt(sum((x - mean_val) ** 2 for x in time_series) / n) or 1.0
            results = []
            for year, value in zip(dates, time_series):
                z = (value - mean_val) / std_val
                p_val = (2.0 * (1.0 - _norm.cdf(abs(z)))
                         if _HAS_SCIPY else None)
                results.append({
                    "year": year,
                    "value": value,
                    "z_score": round(z, 3),
                    "p_value": round(p_val, 6) if p_val is not None else None,
                    "is_anomaly": value < lower or value > upper,
                })
            return results

        # 滑动窗口方法
        if method == "window":
            window_size = max(3, n // 3)
            results = []
            for i, (year, value) in enumerate(zip(dates, time_series)):
                left = max(0, i - window_size)
                window = time_series[left:i]
                if len(window) < 2:
                    results.append({
                        "year": year, "value": value,
                        "z_score": 0.0, "is_anomaly": False,
                    })
                    continue
                w_mean = sum(window) / len(window)
                w_var = sum((x - w_mean) ** 2 for x in window) / len(window)
                w_std = math.sqrt(w_var) if w_var > 0 else 1.0
                z = (value - w_mean) / w_std
                threshold = max(1.5, 2.5 - sensitivity * 20)
                results.append({
                    "year": year,
                    "value": value,
                    "z_score": round(z, 3),
                    "is_anomaly": abs(z) > threshold,
                })
            return results

        raise ValueError(f"未知检测方法: {method}")

    # ── Layer 2: 突变点检测 ──

    @staticmethod
    def detect_change_points(
        time_series: list[float],
        dates: list[int],
        method: str = "cusum",
        min_segment_length: int = 3,
        cusum_threshold: float = 3.0,
        pelt_penalty: float = 3.0,
    ) -> list[dict]:
        """Layer 2 — 突变点检测 (含 CUSUM + PELT)。

        方法:
          - "cusum":   CUSUM 累积和检测 (默认, 适合生态数据渐进变化)
          - "pelt":    PELT-like 二分分割 (自动定位, 无需预知突变点数)
          - "sliding": 滑动窗口对比 (保留向后兼容)
          - "diff":    差分法 (连续点差异 > 阈值)

        CUSUM (Page 1954):
          双边累积和, 追踪偏离参考均值的累积偏差。
          当累积和超过阈值时标记突变点，然后重置。
          适合检测生态学中禁捕/污染等事件的渐进影响。

        Returns:
            [{"year": int, "change_type": "up"|"down",
              "magnitude": float, "confidence": float, "method": str}, ...]
        """
        n = len(time_series)
        if n < min_segment_length * 2:
            return []

        # ═══════════════════════════
        # CUSUM — 累积和控制图
        # ═══════════════════════════
        if method == "cusum":
            series_mean = sum(time_series) / n
            series_std = math.sqrt(
                sum((x - series_mean) ** 2 for x in time_series) / n
            ) or 1.0

            s_pos = 0.0  # 向上累积
            s_neg = 0.0  # 向下累积
            results = []
            ref = series_mean
            drift = 0.5 * series_std

            for i, (year, value) in enumerate(zip(dates, time_series)):
                z = (value - ref) / series_std
                s_pos = max(0.0, s_pos + z - drift / series_std)
                s_neg = min(0.0, s_neg + z + drift / series_std)

                if s_pos >= cusum_threshold:
                    results.append({
                        "year": year, "index": i,
                        "change_type": "up",
                        "magnitude": round(s_pos, 3),
                        "confidence": min(1.0, s_pos / (cusum_threshold * 2)),
                        "method": "cusum",
                    })
                    s_pos = 0.0

                if s_neg <= -cusum_threshold:
                    results.append({
                        "year": year, "index": i,
                        "change_type": "down",
                        "magnitude": round(abs(s_neg), 3),
                        "confidence": min(1.0, abs(s_neg) / (cusum_threshold * 2)),
                        "method": "cusum",
                    })
                    s_neg = 0.0

            return _deduplicate_changes(results, min_segment_length)

        # ═══════════════════════════
        # PELT-like 二分分割
        # ═══════════════════════════
        if method == "pelt":
            n_pts = len(time_series)
            C = [0.0] * n_pts
            cp = [0] * n_pts

            total_mean = sum(time_series) / n_pts
            total_std = math.sqrt(
                sum((x - total_mean) ** 2 for x in time_series) / n_pts
            ) or 1.0

            for t in range(min_segment_length, n_pts):
                best_cost = float("inf")
                best_s = t
                for s in range(min_segment_length, t - min_segment_length + 1):
                    seg1 = time_series[s:t+1]
                    seg0 = time_series[cp[s-1]:s] if s > 0 else time_series[:s]
                    cost = C[s-1] if s > 0 else 0.0
                    for seg in [seg0, seg1]:
                        if len(seg) > 1:
                            seg_mean = sum(seg) / len(seg)
                            cost += sum((x - seg_mean) ** 2 for x in seg) / (total_std ** 2)
                    cost += pelt_penalty
                    if cost < best_cost:
                        best_cost = cost
                        best_s = s
                C[t] = best_cost
                cp[t] = best_s

            changes_indices = []
            t = n_pts - 1
            while t > min_segment_length:
                s = cp[t]
                if s > 0 and s < t:
                    left_seg = time_series[s-min_segment_length:s+1]
                    right_seg = time_series[s+1:t+1]
                    left_m = sum(left_seg) / len(left_seg) if left_seg else 0
                    right_m = sum(right_seg) / len(right_seg) if right_seg else 0
                    effect = (right_m - left_m) / total_std
                    changes_indices.append({
                        "index": s,
                        "year": dates[s] if s < len(dates) else dates[-1],
                        "change_type": "up" if effect > 0 else "down",
                        "magnitude": round(abs(effect), 3),
                        "confidence": min(1.0, abs(effect) / 2.0),
                        "method": "pelt",
                    })
                t = s - 1

            return sorted(
                _deduplicate_changes(changes_indices, min_segment_length),
                key=lambda x: x["year"],
            )

        # ═══════════════════════════
        # 滑动窗口 (向后兼容)
        # ═══════════════════════════
        if method == "sliding":
            series_mean = sum(time_series) / n
            series_var = sum((x - series_mean) ** 2 for x in time_series) / n
            series_std = math.sqrt(series_var) if series_var > 0 else 1.0
            results = []
            for i in range(min_segment_length, n - min_segment_length + 1):
                left = time_series[i - min_segment_length:i]
                right = time_series[i:i + min_segment_length]
                left_mean = sum(left) / len(left)
                right_mean = sum(right) / len(right)
                diff = right_mean - left_mean
                effect = abs(diff) / series_std
                if effect >= 0.5:
                    results.append({
                        "year": dates[i], "index": i,
                        "change_type": "up" if diff > 0 else "down",
                        "magnitude": round(effect, 3),
                        "confidence": min(1.0, effect / 2.0),
                        "method": "sliding",
                    })
            return _deduplicate_changes(results, min_segment_length)

        # 差分法 (向后兼容)
        if method == "diff":
            series_mean = sum(time_series) / n
            series_std = math.sqrt(
                sum((x - series_mean) ** 2 for x in time_series) / n
            ) or 1.0
            results = []
            for i in range(1, n):
                diff = time_series[i] - time_series[i - 1]
                effect = abs(diff) / series_std
                if effect >= 1.0:
                    results.append({
                        "year": dates[i], "index": i,
                        "change_type": "up" if diff > 0 else "down",
                        "magnitude": round(effect, 3),
                        "confidence": min(1.0, effect / 3.0),
                        "method": "diff",
                    })
            return _deduplicate_changes(results, min_segment_length)

        raise ValueError(f"未知检测方法: {method}")

    # ── Layer 3: 理论-数据匹配 ──

    @staticmethod
    def match_theory(
        observations: dict[str, float],
        species: str = "",
    ) -> list[dict]:
        """Layer 3 — 将观察到的模式与已知理论预测匹配。

        支持 direction 字段: "above", "below", "peak"
        确保 "body_size_slope / diversity_slope" 等复合统计量
        已在 observations 中预先构造好 (由 scan() 自动完成)。

        Returns:
            [{"pattern_name": str, "theory": str, "match_score": float,
              "evidence": str, "priority": str}, ...]
        """
        matches = []
        for pattern in KNOWN_PATTERNS:
            stat = pattern["test_statistic"]
            if stat in observations:
                value = observations[stat]
                direction = pattern.get("direction", "above")
                threshold = pattern["threshold"]

                matched = False
                match_score = 0.0
                if direction == "above" and value >= threshold:
                    matched = True
                    match_score = (
                        min(value / threshold, 1.0) if threshold > 0 else 1.0
                    )
                elif direction == "below" and value <= threshold:
                    matched = True
                    match_score = (
                        min(threshold / max(value, 0.001), 1.0)
                        if value > 0 else 1.0
                    )
                elif direction == "peak":
                    matched = value > 0
                    match_score = min(value, 1.0) if matched else 0.0

                if matched:
                    matches.append({
                        "pattern_name": pattern["name"],
                        "theory": pattern["theory"],
                        "match_score": round(match_score, 4),
                        "threshold": threshold,
                        "observed": value,
                        "priority": pattern["priority"],
                        "signal": pattern["signal"],
                        "direction": direction,
                    })
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    # ── 综合扫描 ──

    # ── v9.0: 率失真度量 (Rate-Distortion) ──
    # 马毅论点: "压缩 = 智能的数学等价物"
    # 熵不够——需要率失真 R(D) = min I(X;Z) s.t. E[d(X,Z)] ≤ D
    # 度量的是: 用多少比特把数据编码到预设精度

    @staticmethod
    def effective_dimension(data: dict[str, list],
                            variance_threshold: float = 0.95) -> dict:
        """PCA 有效维度 —— 真正的低维性检测。

        马毅: "真实数据分布在巨大的高维空间中只占据极低维的流形"
        这里用 PCA 特征值谱估计: 需要多少个主成分才能解释 95% 方差。

        Returns:
            {effective_dim, total_dim, ratio, is_low_dimensional}
            - 如果 effective_dim << total_dim → 数据有强低维结构
            - 如果 ratio > 0.5 → 数据近乎完全随机, 理论匹配无意义
        """
        import math

        series = []
        for key, values in data.items():
            if key == "years" or not isinstance(values, list):
                continue
            if len(values) >= 3:
                series.append(values)

        total_dim = len(series)
        if total_dim < 2:
            return {"effective_dim": total_dim, "total_dim": total_dim,
                    "ratio": 1.0, "is_low_dimensional": True}

        # 对齐长度
        min_len = min(len(s) for s in series)
        aligned = [s[:min_len] for s in series]
        n = min_len

        # 协方差矩阵 (total_dim × total_dim)
        means = [sum(s) / n for s in aligned]
        cov = [[0.0] * total_dim for _ in range(total_dim)]
        for i in range(total_dim):
            for j in range(total_dim):
                cov[i][j] = sum(
                    (aligned[i][k] - means[i]) * (aligned[j][k] - means[j])
                    for k in range(n)
                ) / (n - 1) if n > 1 else 0

        # 特征值: 对 2×2 用解析解, 否则用幂迭代
        if total_dim == 2:
            # 2×2 协方差矩阵的解析特征值
            a, b = cov[0][0], cov[0][1]
            c, d = cov[1][0], cov[1][1]  # c == b 但用 c 保持形式
            trace = a + d
            det = a * d - b * c
            disc = trace * trace - 4 * det
            if disc < 0:
                disc = 0
            eigenvalues = [
                (trace + disc ** 0.5) / 2,
                (trace - disc ** 0.5) / 2,
            ]
        else:
            eigenvalues = EmergenceEngine._power_iteration_eigenvalues(cov, total_dim)

        # 有效维度: 95% 方差需要多少个成分
        total_var = sum(eigenvalues)
        if total_var < 1e-9:
            return {"effective_dim": 1, "total_dim": total_dim,
                    "ratio": 1.0 / total_dim, "is_low_dimensional": True}

        cumulative = 0
        effective_dim = 0
        for ev in sorted(eigenvalues, reverse=True):
            cumulative += ev / total_var
            effective_dim += 1
            if cumulative >= variance_threshold:
                break

        ratio = effective_dim / total_dim

        # 谱间隙判据: 主导特征值是否远超其他
        # 如果 λ₁ > 5 × mean(λ₂...λₙ), 数据有强低维结构
        sorted_ev = sorted(eigenvalues, reverse=True)
        if total_dim >= 2 and sorted_ev[0] > 1e-9:
            mean_rest = sum(sorted_ev[1:]) / (total_dim - 1) if total_dim > 1 else 0
            spectral_gap = sorted_ev[0] / max(mean_rest, 1e-12)
        else:
            spectral_gap = 1.0

        is_low_dim = ratio <= 0.75 or spectral_gap > 3.0  # 75%维度内 或 主导特征值3x以上

        return {
            "effective_dim": effective_dim,
            "total_dim": total_dim,
            "ratio": round(ratio, 3),
            "spectral_gap": round(spectral_gap, 1),
            "is_low_dimensional": is_low_dim,
            "eigenvalues": [round(e, 4) for e in sorted_ev],
        }

    @staticmethod
    def _power_iteration_eigenvalues(matrix: list[list[float]],
                                      n: int) -> list[float]:
        """用收缩法求所有特征值 (无需 numpy)。

        算法: 幂迭代求最大特征值 → 收缩矩阵 → 重复。
        O(n³), 但 n 通常很小 (数据维度 ≤ 20)。
        """
        import math
        eigenvalues = []
        M = [row[:] for row in matrix]  # copy

        for _ in range(n):
            # 幂迭代求最大特征值
            v = [1.0] * n
            for _ in range(50):  # 幂迭代, 通常 < 10 次收敛
                w = [sum(M[i][j] * v[j] for j in range(n)) for i in range(n)]
                norm = math.sqrt(sum(x * x for x in w))
                if norm < 1e-12:
                    break
                v = [x / norm for x in w]

            # Rayleigh 商: λ = v^T M v / v^T v
            Mv = [sum(M[i][j] * v[j] for j in range(n)) for i in range(n)]
            lam = sum(v[i] * Mv[i] for i in range(n)) / sum(
                v[i] * v[i] for i in range(n)
            ) if sum(v[i] * v[i] for i in range(n)) > 1e-12 else 0

            eigenvalues.append(abs(lam))

            # 收缩: M = M - λ v v^T
            for i in range(n):
                for j in range(n):
                    M[i][j] -= lam * v[i] * v[j]

        return eigenvalues

    def scan(
        self,
        species: str = "",
        data: dict[str, Any] | None = None,
        auto_theory: bool = True,
        anomaly_method: str = "zscore",
        change_method: str = "cusum",
        sensitivity: float = 0.05,
    ) -> list[dict]:
        """一键扫描: 异常→突变→理论匹配 + 自动反馈记录。

        Args:
            species: 物种名
            data: {"years": [2021,2022,...], "biomass": [1.0,2.1,...], ...}
            auto_theory: 是否自动计算并匹配理论
            anomaly_method: 异常检测方法 ("zscore"|"iqr"|"window")
            change_method: 突变点检测方法 ("cusum"|"pelt"|"sliding"|"diff")
            sensitivity: 灵敏度 (0.01-0.10)

        Returns:
            DetectionResult 格式的 dict 列表
        """
        results: list[dict] = []
        if not data:
            return [{"detection_type": "status",
                     "description": "需要提供时间序列数据"}]

        years = data.get("years", [])
        if not years:
            return [{"detection_type": "status",
                     "description": "需要提供年份序列"}]

        # Layer 1: 异常检测
        for key, values in data.items():
            if key == "years" or not isinstance(values, list):
                continue
            if len(values) != len(years):
                continue
            try:
                anomalies = self.detect_anomalies(
                    values, years, method=anomaly_method,
                    sensitivity=sensitivity,
                )
                for a in anomalies:
                    if a.get("is_anomaly"):
                        results.append({
                            "detection_type": "anomaly",
                            "species": species,
                            "variable": key,
                            "description": (
                                f"{species} {key} 在 {a['year']} 年出现异常 "
                                f"(z_score={a['z_score']})"
                            ),
                            "confidence": min(1.0, abs(a["z_score"]) / 4.0),
                            "evidence": a,
                            "suggested_theory": "",
                            "suggested_action": f"检查 {key} 在 {a['year']} 年的数据来源",
                            **a,
                        })
            except Exception:
                continue

        # Layer 2: 突变点检测
        for key, values in data.items():
            if key == "years" or not isinstance(values, list):
                continue
            if len(values) != len(years):
                continue
            try:
                changes = self.detect_change_points(
                    values, years, method=change_method,
                )
                for c in changes:
                    results.append({
                        "detection_type": "change_point",
                        "species": species,
                        "variable": key,
                        "description": (
                            f"{species} {key} 在 {c['year']} 年发生"
                            f"{'上升' if c['change_type']=='up' else '下降'}突变"
                        ),
                        "confidence": c["confidence"],
                        "evidence": c,
                        "suggested_theory": "",
                        "suggested_action": "标注该突变点并追溯原因",
                        **c,
                    })
            except Exception:
                continue


        if auto_theory:
            # Step 1: 计算简单斜率
            observations: dict[str, float] = {}
            for key, values in data.items():
                if key == "years" or not isinstance(values, list):
                    continue
                if len(values) >= 3:
                    n = len(values)
                    x_mean = sum(range(n)) / n
                    y_mean = sum(values) / n
                    slope = (
                        sum((i - x_mean) * (v - y_mean)
                            for i, v in enumerate(values))
                        / sum((i - x_mean) ** 2 for i in range(n))
                        if n > 1 else 0
                    )
                    if abs(slope) > 0.001:
                        observations[f"{key}_slope"] = slope

            # Step 2: 自动构造复合统计量 (使理论模式可匹配)
            # 例如: "body_size_slope / diversity_slope" → 从已有 slope 推算
            for pattern in KNOWN_PATTERNS:
                stat = pattern["test_statistic"]
                expr = stat.strip()

                # 处理 "A / B" 比值
                if " / " in expr:
                    parts = [p.strip() for p in expr.split(" / ")]
                    if all(p in observations for p in parts):
                        observations[expr] = observations[parts[0]] / max(
                            observations[parts[1]], 0.001
                        )

                # 处理 "A vs B" 对比
                elif " vs " in expr:
                    parts = [p.strip() for p in expr.split(" vs ")]
                    if all(p in observations for p in parts):
                        observations[expr] = abs(
                            observations[parts[0]] - observations[parts[1]]
                        )

            theory_matches = self.match_theory(observations, species)
            for tm in theory_matches:
                results.append({
                    "detection_type": "theory_match",
                    "species": species,
                    "description": (
                        f"理论匹配: {tm['pattern_name']} — {tm['theory']}"
                    ),
                    "confidence": tm["match_score"],
                    "evidence": tm,
                    "suggested_theory": tm["theory"],
                    "suggested_action": f"基于 {tm['pattern_name']} 撰写论文",
                    **tm,
                })

        # 自动记录反馈 (供 emerge_domains 积累数据)
        self._record_feedback(species, results)

        # ── v8.0: Holland 涌现 + MoE 稀疏路由集成 ──
        results = self._enhance_with_holland(results, species, data)
        # ──────────────────────────────────────────

        return results

    def _enhance_with_holland(self, results: list[dict], species: str,
                               data: dict[str, list]) -> list[dict]:
        """v8.0: 用 Holland 涌现 + MoE 路由增强扫描结果。

        非破坏性: 失败时返回原始结果, 不抛异常。
        """
        try:
            # v9.0: holland/deepseek modules now live in san-sheng-wanwu-core/src/cortex/
            import sys as _sys, os as _os
            _cortex_path = _os.path.normpath(_os.path.join(
                _os.path.dirname(__file__), '..', '..',
                'san-sheng-wanwu-core', 'src', 'cortex'
            ))
            if _cortex_path not in _sys.path:
                _sys.path.insert(0, _cortex_path)
            from holland.cas_engine import CASCognitiveEngine
            from deepseek.moe_router import MoETheoryRouter
            from deepseek.grpo_evolution import EmergenceBridge

            # 1. Holland CAS 涌现扫描
            cas = CASCognitiveEngine()
            holland_score = cas.scan(
                papers=[], species=species, data=data
            )
            results.append({
                "detection_type": "holland_emergence",
                "species": species,
                "description": f"Holland 涌现指数: {holland_score.holland_index:.2f}",
                "confidence": holland_score.holland_index,
                "holland_score": {
                    "index": holland_score.holland_index,
                    "emergent": holland_score.is_emergent,
                    "dims_active": holland_score.dimensions_active,
                    "breakdown": {
                        "aggregation": holland_score.aggregation,
                        "tagging": holland_score.tagging,
                        "nonlinear": holland_score.nonlinear,
                        "flows": holland_score.flows,
                        "diversity": holland_score.diversity,
                        "internal_models": holland_score.internal_models,
                        "blocks": holland_score.blocks,
                    },
                },
            })

            # 2. 如果涌现, 生成假说
            if holland_score.is_emergent:
                hypotheses = cas.generate_hypotheses(holland_score, species)
                for h in hypotheses:
                    results.append({
                        "detection_type": "holland_hypothesis",
                        "species": species,
                        "description": h,
                        "confidence": holland_score.holland_index,
                    })

            # 3. MoE 稀疏理论路由 (替代品 — 与原有 theory_match 互补)
            obs = self._extract_observations(data)
            if obs:
                router = MoETheoryRouter()
                moe_matches = router.match(obs, top_k=3)
                for m in moe_matches:
                    # 避免重复 (原有 match_theory 已产生 theory_match)
                    if not any(
                        r.get("pattern_name") == m["pattern_name"]
                        for r in results
                    ):
                        results.append({
                            "detection_type": "moe_theory_match",
                            "species": species,
                            "description": (f"MoE 路由匹配: {m['theory']} "
                                           f"(域: {m['active_domain']})"),
                            "confidence": m["confidence"],
                            "pattern_name": m["pattern_name"],
                            "theory": m["theory"],
                            "match_score": m["match_score"],
                        })

            # 4. GRPO 反馈桥接
            bridge = EmergenceBridge()
            active_dims = [k for k, v in {
                "aggregation": holland_score.aggregation,
                "nonlinear": holland_score.nonlinear,
                "flows": holland_score.flows,
                "diversity": holland_score.diversity,
                "blocks": holland_score.blocks,
            }.items() if v > 0.3]
            bridge.feed_holland_score(
                holland_index=holland_score.holland_index,
                active_dimensions=active_dims,
                matched_theories=[
                    r for r in results
                    if r.get("detection_type") in ("theory_match", "moe_theory_match")
                ],
            )

        except Exception:
            pass  # 非破坏性: 增强失败不影响原有功能

        return results

    def _extract_observations(self, data: dict[str, list]) -> dict[str, float]:
        """从时间序列数据中提取观测特征 (供 MoE 路由器使用)。"""
        obs = {}
        for key, values in data.items():
            if key == "years" or not isinstance(values, list) or len(values) < 2:
                continue
            n = len(values)
            x_mean = sum(range(n)) / n
            y_mean = sum(values) / n
            if n > 1:
                slope = (
                    sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
                    / sum((i - x_mean) ** 2 for i in range(n))
                )
                obs[f"{key}_slope"] = round(slope, 4)
        return obs

    def _record_feedback(self, species: str, results: list[dict]):
        """自动记录扫描结果到反馈日志, 供 emerge_domains 使用。"""
        try:
            self._feedback_file.parent.mkdir(parents=True, exist_ok=True)
            counters: dict[str, int] = {}
            for r in results:
                dt = r.get("detection_type", "unknown")
                counters[dt] = counters.get(dt, 0) + 1

            with open(self._feedback_file, "a", encoding="utf-8") as f:
                record = {
                    "ts": datetime.now().isoformat(),
                    "query": f"scan:{species}",
                    "db": "emergence_engine",
                    "result_count": len(results),
                    "useful": len(results) > 0,
                    "details": counters,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 反馈记录失败不影响主流程

    def signals_summary(self) -> list[dict]:
        """⚠️ STUB: 已检测到的所有涌现信号摘要。

        TODO: 实际实现需要从 self.signals 列表中读取并格式化。
        """
        # 尝试从内部状态提取实际信号
        try:
            if hasattr(self, 'signals') and self.signals:
                return [s.summary() if hasattr(s, 'summary') else s
                        for s in self.signals]
        except Exception:
            pass
        import warnings
        warnings.warn(
            "EmergenceEngine.signals_summary() is a STUB — returns empty list. "
            "Signals are tracked internally but not yet exposed via this method.",
            FutureWarning,
            stacklevel=2,
        )
        return []


# ═══════════════════════════════════════════════════════════
# Part 5: 自组织领域发现 (来自 c 项目 catalog_loader)
# ═══════════════════════════════════════════════════════════
