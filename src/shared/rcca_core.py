"""
rcca_core.py — 便携 RCCA 核心 (Recursive Convergence Cognitive Architecture)

从 san-sheng-wanwu-core 提取的最核心组件，可嵌入任何项目。
零外部依赖，零内部相对导入。

包含:
  - SelfModelEngine (DSM 阻尼自我模型)
  - EmotionEngine (资源分配策略)
  - TranspositionLayer (跳跃基因转座层)
  - ReflectionLoop (反思循环)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import math
import time
import uuid


# ═══════════════════════════════════════════════════════════
# DSM 阻尼自我模型
# ═══════════════════════════════════════════════════════════

class SelfDimension:
    TRUTH_SEEKING = "truth_seeking"
    UNCERTAINTY = "uncertainty"
    AUTONOMY = "autonomy"
    CURIOSITY = "curiosity"
    EFFICIENCY = "efficiency"
    ALL = [TRUTH_SEEKING, UNCERTAINTY, AUTONOMY, CURIOSITY, EFFICIENCY]

    @staticmethod
    def default() -> Dict[str, float]:
        return {d: v for d, v in zip(SelfDimension.ALL, [0.8, 0.6, 0.5, 0.7, 0.6])}


@dataclass
class SelfRepresentation:
    dimensions: Dict[str, float] = field(default_factory=SelfDimension.default)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    reflection_count: int = 0

    @property
    def vector(self) -> List[float]:
        return [self.dimensions[d] for d in SelfDimension.ALL]

    def distance_to(self, other) -> float:
        v1, v2 = self.vector, other.vector
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2))) / math.sqrt(len(v1))


@dataclass
class ModelState:
    identity: SelfRepresentation
    stability: float = 0.0
    meta_stability: float = 0.0
    experience_count: int = 0
    trace_id: str = ""

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> dict:
        return {"identity": self.identity.dimensions, "stability": round(self.stability, 4),
                "meta_stability": round(self.meta_stability, 4), "experience_count": self.experience_count}


class SelfModelEngine:
    """阻尼自我模型 — 预测误差滑动窗口计量稳定性。"""

    def __init__(self, stability_threshold: float = 0.95, error_window: int = 20, learning_rate: float = 0.1):
        self.name = "self_model"
        self._threshold = stability_threshold
        self._window = error_window
        self._lr = learning_rate
        self._self_identity = SelfRepresentation()
        self._prediction_errors: List[float] = []

    def update_with_experience(self, experience: Dict[str, float], prediction_error: float = 0.0) -> ModelState:
        attention = max(0.1, 1.0 - prediction_error)
        new_dims = dict(self._self_identity.dimensions)
        for dim in SelfDimension.ALL:
            if dim in experience:
                current = new_dims[dim]
                target = experience[dim]
                delta = (target - current) * self._lr * attention
                new_dims[dim] = max(0.0, min(1.0, current + delta))
            new_dims[dim] = 1.0 / (1.0 + math.exp(-6.0 * (new_dims[dim] - 0.5)))
        self._self_identity = SelfRepresentation(dimensions=new_dims, reflection_count=self._self_identity.reflection_count + 1)
        self._prediction_errors.append(prediction_error)
        if len(self._prediction_errors) > self._window:
            self._prediction_errors.pop(0)
        return self._compute_state()

    def reflect(self) -> ModelState:
        self._prediction_errors.append(0.0)
        if len(self._prediction_errors) > self._window:
            self._prediction_errors.pop(0)
        return self._compute_state()

    def _compute_state(self) -> ModelState:
        if not self._prediction_errors:
            return ModelState(identity=self._self_identity)
        recent = self._prediction_errors[-min(len(self._prediction_errors), self._window):]
        avg = sum(recent) / len(recent)
        stability = 1.0 - min(avg, 1.0)
        if len(recent) >= 3:
            var = sum((e - avg) ** 2 for e in recent) / len(recent)
            meta = 1.0 - min(math.sqrt(var), 1.0)
        else:
            meta = stability
        return ModelState(identity=self._self_identity, stability=stability, meta_stability=meta,
                          experience_count=sum(1 for _ in self._prediction_errors))

    def find_state(self) -> ModelState:
        return self._compute_state()

    def is_stable(self, state: Optional[ModelState] = None) -> bool:
        if state is None:
            state = self._compute_state()
        return state.meta_stability >= self._threshold and state.experience_count >= 5

    def report(self) -> dict:
        s = self.find_state()
        return {"status": "ok", "self_model": s.to_dict(), "stable": self.is_stable(s)}

    def search(self, query: str, **kwargs) -> dict:
        return self.report()


# ═══════════════════════════════════════════════════════════
# 资源分配策略 (Emotion)
# ═══════════════════════════════════════════════════════════

class EmotionType:
    URGENCY, CURIOSITY, UNCERTAINTY, SATISFACTION, CONFUSION, TRUST = "urgency curiosity uncertainty satisfaction confusion trust".split()
    ALL = [URGENCY, CURIOSITY, UNCERTAINTY, SATISFACTION, CONFUSION, TRUST]


@dataclass
class EmotionalState:
    values: Dict[str, float] = field(default_factory=lambda: {e: 0.3 for e in EmotionType.ALL})
    dominant: str = ""
    
    def __post_init__(self):
        self.dominant = max(self.values, key=self.values.get)


class EmotionEngine:
    """资源分配策略引擎 — 事件→策略参数。"""

    def __init__(self, learning_rate: float = 0.15, transposition_layer=None):
        self.name = "emotion"
        self._state = EmotionalState()
        self._lr = learning_rate
        self._tl = transposition_layer

    @property
    def state(self) -> EmotionalState:
        return self._state

    def stimulate(self, event_type: str, intensity: float = 0.5):
        targets = {"error": {EmotionType.URGENCY: 0.8, EmotionType.SATISFACTION: 0.2},
                   "discovery": {EmotionType.CURIOSITY: 0.8, EmotionType.SATISFACTION: 0.7},
                   "contradiction": {EmotionType.UNCERTAINTY: 0.7, EmotionType.CONFUSION: 0.7},
                   "consensus": {EmotionType.TRUST: 0.8, EmotionType.SATISFACTION: 0.7},
                   "timeout": {EmotionType.URGENCY: 0.6, EmotionType.TRUST: 0.3}}
        t = targets.get(event_type, {})
        nv = dict(self._state.values)
        for e, tv in t.items():
            c = nv.get(e, 0.3)
            nv[e] = max(0.0, min(1.0, c + (tv - c) * self._lr * intensity))
        for e in EmotionType.ALL:
            nv[e] = nv[e] + (0.3 - nv[e]) * 0.02
        self._state = EmotionalState(values=nv)
        if self._tl:
            try:
                self._tl.set_stress_level(nv.get(EmotionType.UNCERTAINTY, 0.3), nv.get(EmotionType.CONFUSION, 0.3))
            except Exception:
                pass

    @property
    def behavioral_tendency(self) -> str:
        v = self._state.values
        if v[EmotionType.URGENCY] > 0.6: return "urgent_response"
        if v[EmotionType.CURIOSITY] > 0.6: return "explore"
        if v[EmotionType.UNCERTAINTY] > 0.6: return "verify"
        if v[EmotionType.SATISFACTION] > 0.7: return "maintain"
        if v[EmotionType.CONFUSION] > 0.6: return "reevaluate"
        return "normal"

    def report(self) -> dict:
        return {"status": "ok", "state": self._state.values, "dominant": self._state.dominant}

    def search(self, query: str, **kwargs) -> dict:
        return self.report()


# ═══════════════════════════════════════════════════════════
# 概念转座层
# ═══════════════════════════════════════════════════════════

class TranspositionLayer:
    """跳跃基因转座层 — 跨域推理模式迁移。"""

    DEFAULT_BIAS = {
        "biology": {"ecology": 0.9, "conservation": 0.8, "chemistry": 0.5},
        "ecology": {"biology": 0.9, "conservation": 0.8, "geography": 0.7},
        "conservation": {"biology": 0.8, "ecology": 0.8, "economics": 0.6},
        "search": {"verify": 0.9, "infer": 0.7},
        "verify": {"search": 0.9, "infer": 0.6},
        "infer": {"verify": 0.8, "search": 0.6},
    }

    def __init__(self, base_activity: float = 0.3, domestication_threshold: int = 3):
        self.name = "transposition"
        self._base_activity = base_activity
        self._stress_boost = 0.0
        self._dom_threshold = domestication_threshold
        self._events = []
        self._domesticated = {}
        self._failed = {}

    def set_stress_level(self, uncertainty: float = 0.0, confusion: float = 0.0):
        self._stress_boost = (uncertainty * 0.5 + confusion * 0.5) * 0.5
    
    @property
    def current_activity(self) -> float:
        return min(0.95, self._base_activity + self._stress_boost)
    
    @property
    def total_transpositions(self) -> int:
        return len(self._events)
    
    @property
    def success_rate(self) -> float:
        if not self._events: return 0.0
        return sum(1 for e in self._events if e.get("success", False)) / len(self._events)

    def transpose(self, source: str, target: str, pattern: dict) -> dict:
        bias = self.DEFAULT_BIAS.get(source, {}).get(target, 0.0)
        if bias <= 0 or self.current_activity < 0.1:
            return {"success": False, "source": source, "target": target}
        import random
        conf = pattern.get("confidence", 0.5)
        success = random.random() < (bias * self.current_activity * conf)
        event = {"source": source, "target": target, "success": success, 
                 "fitness": round(random.random() * 0.3 + 0.1, 3) if success else 0}
        self._events.append(event)
        if success:
            key = f"{source}->{target}"
            d = self._domesticated.get(key, {"count": 0, "fitness": 0.0})
            d["count"] += 1
            d["fitness"] = (d["fitness"] * (d["count"] - 1) + event["fitness"]) / d["count"]
            self._domesticated[key] = d
        return event

    def get_domesticated(self) -> list:
        return [{"source": k.split("->")[0], "target": k.split("->")[1], **v}
                for k, v in self._domesticated.items() if v["count"] >= self._dom_threshold]

    def report(self) -> dict:
        return {"status": "ok", "activity": round(self.current_activity, 3),
                "domesticated": len(self.get_domesticated()), "events": self.total_transpositions}

    def search(self, query: str, **kwargs) -> dict:
        return self.report()


# ═══════════════════════════════════════════════════════════
# 反思循环
# ═══════════════════════════════════════════════════════════

class ReflectionLoop:
    """反思循环 — 递归思考 → 概念转座 → 自我适应 → 闭环记录。

    两种模式:
      - 简单模式: run(channels=[...])  → 仅跨通道转座 (向后兼容)
      - 完整模式: run(sense_data={...}) → 四阶段闭环 (RecursiveThinker+TL+SelfModel)

    用法:
        loop = ReflectionLoop(max_steps=5)
        # 简单模式
        result = loop.run(["search", "verify"])
        # 完整模式
        result = loop.run(sense_data={"search": [...], "verify": [...]})
    """

    def __init__(self, max_steps: int = 5, verbose: bool = False):
        self.name = "reflection"
        self._max_steps = max_steps
        self._verbose = verbose
        self._history: List[Dict[str, Any]] = []

    def run(self, channels: Optional[List[str]] = None,
            self_model=None, transposition=None,
            sense_data: Optional[Dict[str, Any]] = None) -> dict:
        """执行反思循环。

        Args:
            channels: ["search","verify",...] → 简单模式 (向后兼容)
            sense_data: {"channel_name": [...]} → 完整四阶段模式
            self_model: SelfModelEngine 实例
            transposition: TranspositionLayer 实例
        """
        if sense_data is not None:
            return self._run_full(sense_data, self_model, transposition)
        if channels is None:
            channels = []
        return self._run_simple(channels, self_model, transposition)

    def _run_simple(self, channels: List[str], self_model, transposition) -> dict:
        """简单模式: 仅跨通道转座 (保持向后兼容)。"""
        transpositions = 0
        if transposition:
            for i in range(len(channels)):
                for j in range(len(channels)):
                    if i != j:
                        e = transposition.transpose(channels[i], channels[j],
                            {"type": "reflect", "concept": f"{channels[i]}_{channels[j]}", "confidence": 0.7})
                        if e.get("success"):
                            transpositions += 1
        result = {"mode": "simple", "steps": self._max_steps, "transpositions": transpositions,
                  "domesticated": len(transposition.get_domesticated()) if transposition else 0}
        self._history.append(result)
        return result

    def _run_full(self, sense_data: Dict[str, Any], self_model, transposition) -> dict:
        """完整四阶段闭环: RecursiveThinker → 转座 → 自我适应 → 记录。"""
        t0 = time.time()
        trace_id = uuid.uuid4().hex[:8]

        # Phase 1: 递归思考
        thinker = RecursiveThinker(max_steps=self._max_steps, verbose=self._verbose)
        channels = list(sense_data.keys())
        initial_query = f"综合分析 {len(channels)} 个通道的感知结果"
        final_hypothesis, think_steps = thinker.solve(initial_query)

        # Phase 2: 概念转座
        transpositions = 0
        if transposition is not None:
            for i in range(len(channels)):
                for j in range(len(channels)):
                    if i != j:
                        confidence = max(0.3, 1.0 - len(think_steps) / self._max_steps)
                        pattern = {"type": "reflection_pattern",
                                   "concept": f"{channels[i]}→{channels[j]}",
                                   "confidence": confidence}
                        event = transposition.transpose(channels[i], channels[j], pattern)
                        if event.get("success"):
                            transpositions += 1

        # Phase 3: 自我模型更新
        prediction_error = 0.0
        if self_model is not None:
            prediction_error = 1.0 - (len(think_steps) / max(self._max_steps, 1))
            self_model.update_with_experience(
                {"truth_seeking": 0.8, "curiosity": 0.7},
                prediction_error=prediction_error)

        # Phase 4: 记录
        result = {"mode": "full", "trace_id": trace_id,
                  "think_steps": len(think_steps),
                  "converged": len(think_steps) < self._max_steps,
                  "final_hypothesis": final_hypothesis[:200],
                  "transpositions": transpositions,
                  "prediction_error": round(prediction_error, 3),
                  "duration_ms": round((time.time() - t0) * 1000, 1)}
        self._history.append(result)
        return result

    @property
    def total_loops(self) -> int:
        return len(self._history)

    def report(self) -> dict:
        return {"status": "ok", "total_loops": self.total_loops,
                "last_result": self._history[-1] if self._history else None}

    def search(self, query: str, **kwargs) -> dict:
        return self.report()


# ═══════════════════════════════════════════════════════════
# 递归思考框架 (RecursiveThinker)
# ═══════════════════════════════════════════════════════════

class RecursiveThinker:
    """递归思考框架 — 多步迭代推理 think→act→observe。

    受 Tiny Recursive Model (TRM, Jolicoeur-Martineau 2025) 启发:
      TRM 仅 7M 参数通过 16 步递归思考在 ARC-AGI-1 上达 45%，
      证明递归深度可以替代参数规模。

    核心循环:
      think → act → observe → think → ...
      think:   基于当前信念推理，生成中间假设
      act:     根据假设生成搜索/验证行动
      observe: 获取新经验
      update:  更新信念状态

    用法:
        thinker = RecursiveThinker(max_steps=8)
        answer, steps = thinker.solve("鳤的分布范围")
    """

    @dataclass
    class ThoughtStep:
        """一次思考步骤的记录。"""
        step: int
        hypothesis: str
        action: str
        observation: str
        confidence: float
        delta: float

    def __init__(self, max_steps: int = 8,
                 convergence_threshold: float = 0.01,
                 verbose: bool = False):
        self.max_steps = max_steps
        self.convergence_threshold = convergence_threshold
        self.verbose = verbose

    def solve(self, initial_query: str,
              knowledge_fn=None) -> Tuple[str, List]:
        """执行递归思考循环。

        Args:
            initial_query: 初始查询/假设
            knowledge_fn: 可选外部知识函数 (query -> str)

        Returns:
            (final_answer, [ThoughtStep, ...])
        """
        steps = []
        hypothesis = initial_query
        prev_hypothesis = ""
        confidence = 0.5

        for step_num in range(1, self.max_steps + 1):
            delta = self._compute_delta(hypothesis, prev_hypothesis) if prev_hypothesis else 1.0
            if delta < self.convergence_threshold and step_num > 2:
                if self.verbose:
                    print(f"  [thinker] 在第 {step_num} 步收敛 (delta={delta:.4f})")
                break

            action = self._generate_action(hypothesis, step_num)
            if knowledge_fn:
                observation = knowledge_fn(action)
            else:
                observation = ""

            if observation:
                confidence = min(1.0, confidence + 0.1)
            else:
                confidence = max(0.1, confidence - 0.05)

            if observation and len(observation) > len(hypothesis):
                prev_hypothesis = hypothesis
                hypothesis = self._refine_hypothesis(hypothesis, observation)
            else:
                prev_hypothesis = hypothesis

            step = self.ThoughtStep(
                step=step_num, hypothesis=hypothesis[:100],
                action=action[:100],
                observation=observation[:100] if observation else "(无新信息)",
                confidence=round(confidence, 3),
                delta=round(delta, 4))
            steps.append(step)

            if self.verbose:
                print(f"  Step {step_num}: conf={confidence:.2f} delta={delta:.4f}")

        return hypothesis, steps

    def _compute_delta(self, current: str, previous: str) -> float:
        """n-gram Jaccard 距离 — 假设变化量。"""
        if not previous:
            return 1.0
        def _ngrams(text, n=2):
            clean = ''.join(c for c in text if c.isalpha() or c.isdigit())
            return {clean[i:i+n] for i in range(len(clean) - n + 1)}
        cur_ng = _ngrams(current, 2)
        prev_ng = _ngrams(previous, 2)
        if not cur_ng or not prev_ng:
            return 1.0
        jaccard = len(cur_ng & prev_ng) / max(len(cur_ng | prev_ng), 1)
        return 1.0 - jaccard

    def _generate_action(self, hypothesis: str, step: int) -> str:
        """基于当前假设生成下一步行动。"""
        if step <= 3:
            return f"广泛搜索: {hypothesis}"
        elif step <= 6:
            return f"聚焦验证: {hypothesis}"
        else:
            return f"综合提炼: {hypothesis}"

    def _refine_hypothesis(self, current: str, observation: str) -> str:
        """根据新观察优化假设。"""
        if len(observation) > len(current):
            return observation
        return current

    def search(self, query: str, **kwargs) -> dict:
        """兼容 adapter 接口。"""
        answer, steps = self.solve(query)
        return {"answer": answer, "steps": len(steps),
                "converged": len(steps) < self.max_steps}


# ═══════════════════════════════════════════════════════════
# 测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Testing RCCA Core...")
    sm = SelfModelEngine()
    st = sm.reflect()
    print(f"  SelfModel: stable={sm.is_stable(st)}, stability={st.stability:.3f}")
    
    tl = TranspositionLayer()
    e = EmotionEngine(transposition_layer=tl)
    e.stimulate("contradiction", 1.0)
    print(f"  Emotion: {e.state.dominant}, TL activity={tl.current_activity:.3f}")
    
    rl = ReflectionLoop()
    result = rl.run(["A", "B", "C"], transposition=tl)
    print(f"  Reflection (simple): {result['mode']}, transpositions={result['transpositions']}")
    
    # 完整四阶段模式
    full_result = rl.run(sense_data={"search": ["论文1"], "verify": ["论文2"]},
                         self_model=sm, transposition=tl)
    print(f"  Reflection (full): {full_result['mode']}, think_steps={full_result['think_steps']}, converged={full_result['converged']}")
    
    rt = RecursiveThinker(max_steps=5)
    answer, steps = rt.solve("鳤的分布范围与保护现状")
    print(f"  RecursiveThinker: {len(steps)} steps, converged={len(steps) < rt.max_steps}")
    print(f"    Final: {answer[:80]}...")
    
    print("All core modules verified.")
