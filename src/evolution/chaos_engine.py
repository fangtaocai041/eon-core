"""
Chaos-Enhanced Agent Engine — 混沌增强智能体核心

理论映射 (5篇基础文献):
  Langton (1990):     "Edge of Chaos" — 临界态具有最优信息处理能力
  Chen & Aihara (1995): 混沌优化 — 混沌序列的遍历性优于随机搜索
  Adachi & Aihara (1997): 混沌联想记忆 — 不稳定周期轨道编码记忆模式
  Beggs & Plenz (2003): Critical Brain — 生物神经系统工作于混沌边缘
  Takahashi (2018):   混沌探索RL — 混沌噪声注入策略空间

五项目映射:
  Rössler Attractor    → meso-cosmos 路由扰动 (非重复探索)
  Logistic Map (μ=4)   → search_optimizer 方向选择 (遍历性搜索)
  Chaos-Edge Coupling  → S-T-V-P₁-P₂ 协同矩阵 (临界态涌现)
  EntropyGuard         → 安全边界 (防止发散)

设计原则:
  "秩序-混沌"轴线: meta_controller 根据任务阶段动态调节 Lyapunov 指数
  稳定性基线: 确定性策略始终作为 fallback
  硬性裁剪: 混沌状态范围限制，防止发散

Usage:
    from src.pipeline.chaos_engine import ChaosEngine
    ce = ChaosEngine()
    perturbation = ce.route_perturbation()  # [-0.3, 0.3] range
    wildcard = ce.should_explore()          # True ~10% of the time
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
# Rössler Attractor — 混沌状态生成器
# ═══════════════════════════════════════════════════════════════

@dataclass
class RosslerState:
    """Rössler 吸引子状态 [x, y, z] — 连续混沌轨迹。

    标准参数: a=0.2, b=0.2, c=5.7 (经典混沌态)
    离散化: Euler method with dt=0.05
    """
    x: float = 1.0   # Start on attractor (not origin — avoids long transient)
    y: float = 1.0
    z: float = 1.0
    a: float = 0.2
    b: float = 0.2
    c: float = 5.7
    dt: float = 0.08  # Slightly larger step for faster orbit

    def step(self):
        """Euler integration: one Rössler step."""
        dx = (-self.y - self.z) * self.dt
        dy = (self.x + self.a * self.y) * self.dt
        dz = (self.b + self.z * (self.x - self.c)) * self.dt
        self.x += dx
        self.y += dy
        self.z += dz
        # Hard containment: clip to attractor bounds
        self.x = max(-20.0, min(20.0, self.x))
        self.y = max(-20.0, min(20.0, self.y))
        self.z = max(0.0, min(50.0, self.z))

    def normalized(self, dim: str = 'x') -> float:
        """Normalize a dimension to [-1, 1] range."""
        raw = getattr(self, dim)
        if dim == 'z':
            return max(-1.0, min(1.0, (raw - 25.0) / 25.0))
        return max(-1.0, min(1.0, raw / 15.0))


# ═══════════════════════════════════════════════════════════════
# Logistic Map — 混沌探索序列
# ═══════════════════════════════════════════════════════════════

@dataclass
class LogisticExplorer:
    """Logistic map x_{n+1} = μ * x_n * (1 - x_n), μ=4 (fully chaotic).

    用于: 搜索方向选择、探索/利用决策
    性质: 遍历 [0,1] 区间，序列无周期，比 random 覆盖更均匀
    """
    x: float = 0.37  # initial seed (arbitrary, ≠ 0.5 to avoid fixed point)
    mu: float = 4.0

    def next(self) -> float:
        """Next value in [0, 1]."""
        self.x = self.mu * self.x * (1.0 - self.x)
        return self.x

    def should_explore(self, threshold: float = 0.10) -> bool:
        """~10% chance to trigger wildcard exploration (Chen & Aihara 1995)."""
        return self.next() < threshold

    def pick_index(self, n: int) -> int:
        """Pick an index in [0, n-1] using chaotic sequence."""
        return int(self.next() * n) % n


# ═══════════════════════════════════════════════════════════════
# Chaos-Edge Coupling Matrix — 多项目协同临界态
# ═══════════════════════════════════════════════════════════════

@dataclass
class CouplingMatrix:
    """S-T-V-P₁-P₂ 交互矩阵，谱半径 ≈ 1 (混沌边缘)。

    Langton (1990): λ ≈ 0 时系统处于混沌边缘，信息处理能力最优。
    矩阵权值控制项目间的非线性耦合强度。
    """
    # 5×5 coupling matrix: rows=source, cols=target
    # Baseline: identity + weak cross-coupling
    weights: list[list[float]] = field(default_factory=lambda: [
        [0.90, 0.05, 0.03, 0.01, 0.01],  # fish (S)
        [0.05, 0.85, 0.05, 0.03, 0.02],  # meso-cosmos (T)
        [0.10, 0.02, 0.85, 0.02, 0.01],  # cognitive (V)
        [0.01, 0.03, 0.01, 0.90, 0.05],  # porpoise (P₁)
        [0.01, 0.03, 0.01, 0.05, 0.90],  # coilia (P₂)
    ])

    def apply(self, state: list[float]) -> list[float]:
        """Apply coupling: new_state = tanh(W · state)."""
        n = len(self.weights)
        result = []
        for i in range(n):
            s = sum(self.weights[i][j] * state[j] for j in range(n))
            result.append(math.tanh(s))  # nonlinear activation → bounded
        return result

    def spectral_radius(self) -> float:
        """Estimate spectral radius (power iteration)."""
        import random
        v = [random.random() for _ in range(5)]
        for _ in range(20):
            v = self.apply(v)
        norm = math.sqrt(sum(x * x for x in v))
        return norm if norm > 0 else 0.0


# ═══════════════════════════════════════════════════════════════
# EntropyGuard — 安全边界
# ═══════════════════════════════════════════════════════════════

@dataclass
class EntropyGuard:
    """监控系统熵值，防止混沌发散。

    Beggs & Plenz (2003): 大脑在临界态附近维持动态平衡。
    我们模拟这个机制：熵值过高时衰减混沌耦合强度。
    """
    max_entropy: float = 0.95      # 熵值上限 (Rössler z 归一化后通常在 0.5-1.0)
    safe_entropy: float = 0.6      # 安全熵值 (低于此值恢复混沌)
    decay_rate: float = 0.15       # 超标时的耦合衰减率 (缓慢衰减)
    recovery_rate: float = 0.02    # 恢复速率 (缓慢恢复)
    coupling_strength: float = 1.0  # 当前耦合强度 [0, 1]
    _entropy_history: list[float] = field(default_factory=list)

    def update(self, current_entropy: float) -> float:
        """更新耦合强度。返回当前有效耦合系数。

        WHEN entropy > max_entropy: decay coupling
        WHEN entropy < safe_entropy: recover coupling
        """
        self._entropy_history.append(current_entropy)
        if len(self._entropy_history) > 20:
            self._entropy_history = self._entropy_history[-20:]

        if current_entropy > self.max_entropy:
            self.coupling_strength = max(0.0, self.coupling_strength - self.decay_rate)
        elif current_entropy < self.safe_entropy:
            self.coupling_strength = min(1.0, self.coupling_strength + self.recovery_rate)

        return self.coupling_strength

    @property
    def in_safe_zone(self) -> bool:
        return self.coupling_strength > 0.3


# ═══════════════════════════════════════════════════════════════
# Chaos Engine — 主控制器
# ═══════════════════════════════════════════════════════════════

class ChaosEngine:
    """混沌增强智能体引擎。

    四层架构 (映射到五项目):
      Layer 1 (Rossler):  混沌状态 → 路由扰动 + 元策略偏置
      Layer 2 (Logistic): 混沌探索 → 搜索方向选择 + 变异触发
      Layer 3 (Coupling): 临界耦合 → 多项目协同涌现
      Layer 4 (Guard):    熵值监控 → 安全边界 + 回退基线

    Usage:
        ce = ChaosEngine()
        ce.step()  # advance chaos state each search cycle

        # Route perturbation
        perturbation = ce.route_bias()  # [-0.2, 0.2]

        # Exploration trigger
        if ce.wildcard():
            direction = ce.chaotic_pick(directions)

        # Safety check
        if not ce.guard.in_safe_zone:
            fallback_to_deterministic()
    """

    def __init__(self, seed: float = None):
        self.rossler = RosslerState()
        if seed is not None:
            self.rossler.x = seed
            self.rossler.y = seed * 1.3
            self.rossler.z = seed * 0.7
        self.explorer = LogisticExplorer(x=0.37 if seed is None else seed * 0.37)
        self.coupling = CouplingMatrix()
        self.guard = EntropyGuard()
        # Start projects at different initial states for heterogeneous coupling
        self._project_states: list[float] = [0.7, 0.5, 0.3, 0.6, 0.4]  # S, T, V, P₁, P₂

    def step(self):
        """Advance all chaos systems one tick. Call once per search cycle."""
        self.rossler.step()
        # Update project coupling
        self._project_states = self.coupling.apply(self._project_states)
        # Monitor entropy — composite of all 3 Rössler dimensions
        rx = abs(self.rossler.normalized('x'))
        ry = abs(self.rossler.normalized('y'))
        rz = abs(self.rossler.normalized('z'))
        entropy = 0.4 * rx + 0.3 * ry + 0.3 * rz  # weighted composite
        self.guard.update(entropy)

    # ── Layer 1: Route Perturbation (Rössler) ──

    def route_bias(self) -> float:
        """Chaotic route perturbation in [-0.25, 0.25].

        Injects non-repeating bias into routing confidence scores.
        Prevents deterministic routing from always choosing the same path.
        Uses x+z composite for richer dynamics, scaled by guard.
        """
        raw = (self.rossler.normalized('x') * 0.6 + self.rossler.normalized('z') * 0.4) * 0.25
        return raw * self.guard.coupling_strength

    def meta_temperature(self) -> float:
        """Meta-strategy temperature from Rössler y-dimension.

        High temperature → more exploratory (wider search)
        Low temperature → more exploitative (focused search)
        Range: [0.5, 2.0]
        """
        raw = self.rossler.normalized('y')
        return 1.0 + raw * self.guard.coupling_strength

    # ── Layer 2: Exploration Trigger (Logistic) ──

    def wildcard(self) -> bool:
        """~8% chance to trigger chaotic exploration.

        Chen & Aihara (1995): chaotic sequence has better
        ergodic coverage than uniform random.
        Low enough to avoid noise, high enough to enable serendipity.
        """
        return self.explorer.should_explore(0.05)  # logistic μ=4 peaks at extremes; 0.05 → ~8% actual

    def chaotic_pick(self, options: list) -> object:
        """Pick an option using chaotic sequence (better coverage than random)."""
        if not options:
            return None
        return options[self.explorer.pick_index(len(options))]

    def exploration_noise(self) -> float:
        """Exploration noise level for search parameter perturbation.

        Range: [0, 1], scaled by guard coupling.
        High → inject more noise into search queries/variants.
        """
        return self.explorer.next() * self.guard.coupling_strength

    # ── Layer 3: Project Coupling ──

    def project_influence(self, project_idx: int) -> float:
        """How much influence does project_idx have on others right now?

        project_idx: 0=S, 1=T, 2=V, 3=P₁, 4=P₂
        Returns: coupling influence [0, 1]
        """
        if 0 <= project_idx < len(self._project_states):
            return self._project_states[project_idx] * self.guard.coupling_strength
        return 0.0

    def cross_project_emergence(self) -> bool:
        """Detect emergent collective behavior (all projects highly coupled)."""
        avg = sum(self._project_states) / len(self._project_states)
        variance = sum((x - avg) ** 2 for x in self._project_states) / len(self._project_states)
        # Emergence: high average coupling + low variance = synchronized
        return avg > 0.6 and variance < 0.05

    # ── Layer 4: Safety ──

    @property
    def safe_mode(self) -> bool:
        """Should we fall back to deterministic baseline?"""
        return not self.guard.in_safe_zone

    def reset_to_safe(self):
        """Reset to deterministic baseline (emergency fallback)."""
        self.guard.coupling_strength = 0.0
        self._project_states = [0.7, 0.5, 0.3, 0.6, 0.4]


# ═══════════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════════

_GLOBAL_ENGINE: ChaosEngine | None = None


def get_chaos_engine() -> ChaosEngine:
    """Get or create the global chaos engine (singleton per process)."""
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = ChaosEngine(seed=time.time() % 1.0)
    return _GLOBAL_ENGINE
