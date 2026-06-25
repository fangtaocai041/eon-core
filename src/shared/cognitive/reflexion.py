"""
自我反思机制 (Reflexion)
──────────────────────────
赋予 Agent 评价自身轨迹的能力。

当执行层遭遇失败时，Critic 生成语言反馈 (Verbal Feedback)，
作为下一次迭代的先验上下文。实现信用分配 (Credit Assignment)，
识别导致失败的具体逻辑节点。

核心组件:
- Critic: 内部评估器 — 分析错误，生成修正建议
- CreditAssigner: 信用分配 — 定位失败节点
- FeedbackLoop: 反馈闭环 — 将反思注入下一次迭代
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import re
import time

logger = logging.getLogger(__name__)


class ReflectionType(str, Enum):
    """反思类型"""
    ERROR_CORRECTION = "error_correction"     # 错误修正
    PATH_BACKTRACK = "path_backtrack"         # 路径回溯
    QUALITY_IMPROVE = "quality_improve"       # 质量提升
    CONSTRAINT_VIOLATION = "constraint_violation"  # 约束违反
    SUCCESS_ANALYSIS = "success_analysis"     # 成功分析 (正反馈)


class Severity(str, Enum):
    """反思严重程度"""
    CRITICAL = "critical"   # IF severity==CRITICAL THEN stop_and_fix()
    HIGH = "high"           # IF severity==HIGH THEN revise_with_priority()
    MEDIUM = "medium"       # IF severity==MEDIUM THEN suggest_improvement()
    LOW = "low"             # IF severity==LOW THEN log_and_continue()
    INFO = "info"           # IF severity==INFO THEN record_only()


@dataclass
class Reflection:
    """
    反思记录 — Critic 生成的评估
    """
    type: ReflectionType
    severity: Severity
    step_id: Optional[int] = None           # 关联的执行步骤
    source_node: Optional[str] = None       # 失败的逻辑节点 (信用分配)
    observation: str = ""                   # 观察到的现象
    diagnosis: str = ""                     # 诊断 (根因分析)
    suggestion: str = ""                    # 修正建议
    verbal_feedback: str = ""              # 语言反馈 (注入下一次迭代)
    timestamp: float = field(default_factory=time.time)

    def to_context(self) -> str:
        """转化为可注入上下文的反思路径"""
        return (
            f"[REFLECTION] {self.severity.value.upper()}: {self.diagnosis}\n"
            f"Suggestion: {self.suggestion}"
        )


@dataclass
class CreditNode:
    """
    信用节点 — 推理树中的一个逻辑节点
    """
    id: str
    description: str
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)
    success: Optional[bool] = None    # None = 未评估
    contribution: float = 1.0         # 对最终结果的贡献权重
    blame_score: float = 0.0          # 失败归因分数


# ── Critic 评估器 ──────────────────────────────────────────

class Critic:
    """
    内部批评家 — 评价 Agent 自身的执行轨迹

    职责:
    1. 分析执行错误 (代码报错 / API 失败 / 工具异常)
    2. 评估结果质量 (是否符合 Desire 中的质量标准)
    3. 生成可操作的修正建议
    4. 进行信用分配 (定位失败的具体逻辑节点)
    """

    def __init__(self, quality_thresholds: Optional[dict] = None):
        self.thresholds = quality_thresholds or {
            "min_confidence": 0.7,
            "min_papers": 5,
            "max_error_rate": 0.1,
            "min_test_coverage": 0.8,
        }
        self.reflections: list[Reflection] = []
        logger.info("Critic initialized")

    def evaluate(
        self,
        step_id: int,
        action: Optional[dict],
        observation: Optional[dict],
        expected_output: str = "",
    ) -> list[Reflection]:
        """
        评估单个执行步骤

        Args:
            step_id: 步骤 ID
            action: 执行的动作
            observation: 观察到的结果
            expected_output: 期望输出描述

        Returns:
            list[Reflection]: 反思列表
        """
        reflections: list[Reflection] = []

        if not observation:
            return reflections

        # 1. 错误检测
        if observation.get("error"):
            r = self._analyze_error(step_id, action, observation)
            reflections.append(r)

        # 2. 结果质量评估
        quality_issues = self._check_quality(step_id, observation)
        reflections.extend(quality_issues)

        # 3. 约束违反检查
        constraint_issues = self._check_constraints(step_id, action, observation)
        reflections.extend(constraint_issues)

        # 4. 期望匹配检查
        if expected_output:
            match_issue = self._check_expectation(
                step_id, observation, expected_output
            )
            if match_issue:
                reflections.append(match_issue)

        self.reflections.extend(reflections)
        return reflections

    def _analyze_error(
        self,
        step_id: int,
        action: Optional[dict],
        observation: dict,
    ) -> Reflection:
        """分析执行错误 → 生成修正建议"""
        error_msg = str(observation.get("error", "Unknown error"))
        action_name = action.get("name", "unknown") if action else "unknown"

        # 错误分类
        diagnosis, suggestion = self._classify_error(error_msg, action_name)

        return Reflection(
            type=ReflectionType.ERROR_CORRECTION,
            severity=Severity.HIGH,
            step_id=step_id,
            source_node=action_name,
            observation=error_msg,
            diagnosis=diagnosis,
            suggestion=suggestion,
            verbal_feedback=(
                f"Step {step_id} ({action_name}) failed with error: {error_msg}. "
                f"Diagnosis: {diagnosis}. Suggested fix: {suggestion}"
            ),
        )

    def _classify_error(self, error_msg: str, action_name: str) -> tuple[str, str]:
        """错误分类 → (诊断, 建议)"""
        error_lower = error_msg.lower()

        if "timeout" in error_lower or "timed out" in error_lower:
            return (
                "API 调用超时 — 可能网络问题或查询过于复杂",
                "重试时增加 timeout 参数，或拆分为更小的子查询",
            )
        elif "not found" in error_lower or "404" in error_lower:
            return (
                "资源未找到 — 路径或 ID 可能错误",
                "验证资源路径和标识符，使用 list 操作确认存在性",
            )
        elif "permission" in error_lower or "403" in error_lower or "401" in error_lower:
            return (
                "权限不足 — API key 可能失效或权限不足",
                "检查 API key 配置和权限范围",
            )
        elif "rate limit" in error_lower or "429" in error_lower:
            return (
                "请求频率限制 — 短时间内请求过多",
                "增加请求间隔 (exponential backoff)，或合并批量请求",
            )
        elif "not_implemented" in error_lower:
            return (
                "功能尚未实现 — 工具为桩代码",
                "使用替代方法或手动完成此步骤",
            )
        elif "memory" in error_lower or "out of memory" in error_lower:
            return (
                "内存不足 — 数据量可能过大",
                "分批处理数据，或使用流式处理",
            )
        elif "syntax" in error_lower or "indentation" in error_lower:
            return (
                "代码语法错误 — 工程语言化层生成的代码有误",
                "检查代码生成逻辑，增加 AST 校验环节",
            )
        elif "import" in error_lower or "module" in error_lower:
            return (
                "依赖缺失 — 所需 Python 包未安装",
                f"自动安装缺失包: pip install <package>",
            )
        else:
            return (
                f"未分类错误: {error_msg[:200]}",
                "检查日志获取详细信息，可尝试重新执行",
            )

    def _check_quality(
        self,
        step_id: int,
        observation: dict,
    ) -> list[Reflection]:
        """质量评估"""
        reflections = []

        result = observation.get("result", {})
        if not isinstance(result, dict):
            return reflections

        # 文献搜索质量
        if "papers" in result and "query" in result:
            n_papers = len(result.get("papers", []))
            if n_papers < self.thresholds.get("min_papers", 5):
                reflections.append(Reflection(
                    type=ReflectionType.QUALITY_IMPROVE,
                    severity=Severity.MEDIUM,
                    step_id=step_id,
                    observation=f"Only {n_papers} papers found (threshold: {self.thresholds['min_papers']})",
                    diagnosis="搜索结果不足 — 可能查询范围过窄",
                    suggestion="扩展查询词（增加同义词、近缘种），或切换数据源",
                    verbal_feedback=f"Low recall: {n_papers} papers. Try broader search terms.",
                ))

        # 置信度检查
        if "confidence" in result:
            conf = result["confidence"]
            if conf < self.thresholds.get("min_confidence", 0.7):
                reflections.append(Reflection(
                    type=ReflectionType.QUALITY_IMPROVE,
                    severity=Severity.MEDIUM,
                    step_id=step_id,
                    observation=f"Low confidence: {conf:.2f}",
                    diagnosis="分类/预测置信度低于阈值",
                    suggestion="收集更多训练数据或使用更复杂的模型",
                    verbal_feedback=f"Low confidence ({conf:.2f}) — result may be unreliable.",
                ))

        return reflections

    def _check_constraints(
        self,
        step_id: int,
        action: Optional[dict],
        observation: dict,
    ) -> list[Reflection]:
        """约束违反检查"""
        reflections = []

        # 数据删除操作
        if action and action.get("name") in ("delete", "remove", "clear"):
            reflections.append(Reflection(
                type=ReflectionType.CONSTRAINT_VIOLATION,
                severity=Severity.CRITICAL,
                step_id=step_id,
                diagnosis="触发了数据删除操作 — 需要人工确认",
                suggestion="暂停执行，等待用户确认后再继续",
                verbal_feedback="CRITICAL: Data deletion attempted. Awaiting human approval.",
            ))

        return reflections

    def _check_expectation(
        self,
        step_id: int,
        observation: dict,
        expected_output: str,
    ) -> Optional[Reflection]:
        """检查实际输出是否匹配期望"""
        result = observation.get("result", {})
        if isinstance(result, dict) and result.get("status") == "not_implemented":
            return Reflection(
                type=ReflectionType.PATH_BACKTRACK,
                severity=Severity.HIGH,
                step_id=step_id,
                observation=f"Expected: {expected_output}, got: not_implemented",
                diagnosis="目标功能尚未实现，需要替代路径",
                suggestion="使用替代工具或请求用户提供替代方案",
                verbal_feedback=f"Expected output '{expected_output}' not available. Need alternative.",
            )
        return None

    def generate_summary(self) -> str:
        """生成反思摘要 (注入下一次对话)"""
        if not self.reflections:
            return "No reflections — execution clean."

        recent = self.reflections[-5:]  # 最近 5 条
        lines = ["## Reflection Summary", ""]
        for r in recent:
            lines.append(f"- [{r.severity.value}] {r.diagnosis}")
            if r.suggestion:
                lines.append(f"  → {r.suggestion}")
        return "\n".join(lines)


# ── 信用分配器 ──────────────────────────────────────────────

class CreditAssigner:
    """
    信用分配器 — 定位失败的逻辑节点

    当多步推理失败时，需要识别出具体是哪一步导致了失败，
    而不是盲目重试整个计划。这对应强化学习中的 Credit Assignment Problem。

    方法:
    - 后向传播: 从失败节点沿依赖链向上追踪
    - 对比分析: 比较成功路径与失败路径的差异
    - 贡献度评估: 每个节点对最终结果的贡献权重
    """

    def __init__(self):
        self.nodes: dict[str, CreditNode] = {}
        logger.info("CreditAssigner initialized")

    def build_from_plan(self, steps: list) -> dict[str, CreditNode]:
        """从执行计划构建信用节点图"""
        self.nodes.clear()
        prev_id = None

        for step in steps:
            step_id = step.id if hasattr(step, 'id') else str(len(self.nodes))
            node = CreditNode(
                id=step_id,
                description=step.description if hasattr(step, 'description') else str(step),
                parent_id=prev_id,
            )
            if prev_id and prev_id in self.nodes:
                self.nodes[prev_id].children.append(step_id)
            self.nodes[step_id] = node
            prev_id = step_id

        return self.nodes

    def assign_blame(self, failed_step_id: str) -> dict[str, float]:
        """
        从失败节点反向追踪，分配责任

        算法: 后向传播 blame_score
        1. 失败节点 blame = 1.0
        2. 沿父节点链向上传播，按贡献度衰减
        3. 返回每个节点的责任分数
        """
        blame_scores: dict[str, float] = {}

        if failed_step_id not in self.nodes:
            return blame_scores

        # 直接失败节点
        blame_scores[failed_step_id] = 1.0

        # 向上传播 (衰减因子 0.5)
        current = self.nodes[failed_step_id]
        decay = 0.5
        while current.parent_id and current.parent_id in self.nodes:
            parent = self.nodes[current.parent_id]
            blame_scores[current.parent_id] = blame_scores.get(
                current.parent_id, 0
            ) + decay
            decay *= 0.5
            current = parent

        # 归一化
        total = sum(blame_scores.values())
        if total > 0:
            for node_id in blame_scores:
                blame_scores[node_id] /= total
                self.nodes[node_id].blame_score = blame_scores[node_id]

        return blame_scores

    def get_root_cause(self, failed_step_id: str) -> Optional[CreditNode]:
        """获取根本原因节点 (责任链的起点)"""
        if failed_step_id not in self.nodes:
            return None

        current = self.nodes[failed_step_id]
        while current.parent_id and current.parent_id in self.nodes:
            parent = self.nodes[current.parent_id]
            if parent.blame_score < 0.1:
                break
            current = parent

        return current


# ── 反馈闭环 ────────────────────────────────────────────────

class FeedbackLoop:
    """
    反馈闭环 — 将 Critic 的反思注入下一次迭代

    工作流:
    1. Critic 评估当前步骤 → 生成 Reflection
    2. FeedbackLoop 收集 Reflection
    3. 在下一轮 Think 前，将 Reflection 注入 LLM 上下文
    4. LLM 基于反思调整决策

    对应 Reflexion 论文的核心机制:
        Actor:   生成行动
        Evaluator (Critic): 评估结果
        Self-Reflection: 生成语言反馈 → 注入 Actor 的记忆
    """

    def __init__(self, max_history: int = 10):
        self.history: list[Reflection] = []
        self.max_history = max_history
        self.critic = Critic()
        self.assigner = CreditAssigner()
        logger.info("FeedbackLoop initialized")

    def process_step(
        self,
        step_id: int,
        action: Optional[dict],
        observation: Optional[dict],
        expected_output: str = "",
    ) -> list[Reflection]:
        """
        处理一个执行步骤: 评估 → 信用分配 → 记录

        Returns:
            list[Reflection]: 新生成的反思
        """
        # 1. Critic 评估
        reflections = self.critic.evaluate(
            step_id, action, observation, expected_output
        )

        # 2. 信用分配 (如果有错误)
        for r in reflections:
            if r.type == ReflectionType.ERROR_CORRECTION and r.source_node:
                self.assigner.assign_blame(r.source_node)

        # 3. 记录
        self.history.extend(reflections)

        # 4. 修剪历史
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return reflections

    def get_context_for_next_iteration(self) -> str:
        """
        获取反思上下文 (注入下一轮 LLM 调用)

        Returns:
            str: 格式化的反思上下文
        """
        if not self.history:
            return ""

        # 只取最近的反思 (避免上下文膨胀)
        recent = self.history[-5:]
        criticals = [r for r in recent if r.severity == Severity.CRITICAL]
        highs = [r for r in recent if r.severity == Severity.HIGH]

        lines = ["## Previous Reflections (learn from these)", ""]

        # 优先展示严重问题
        for r in criticals + highs:
            lines.append(f"- **{r.severity.value.upper()}**: {r.diagnosis}")
            if r.suggestion:
                lines.append(f"  → Fix: {r.suggestion}")

        if not criticals and not highs:
            for r in recent[-3:]:
                lines.append(f"- {r.diagnosis}")

        lines.append("")
        lines.append("**Instruction**: Adjust your next action based on these reflections.")
        return "\n".join(lines)

    def should_retry(self, max_retries: int = 3) -> bool:
        """判断是否应该重试"""
        recent_failures = [
            r for r in self.history[-max_retries:]
            if r.type == ReflectionType.ERROR_CORRECTION
            and r.severity in (Severity.CRITICAL, Severity.HIGH)
        ]
        return len(recent_failures) < max_retries

    def clear(self):
        """清空反思历史"""
        self.history.clear()
        self.critic.reflections.clear()
