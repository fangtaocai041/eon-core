"""
BDI 状态机 (Belief-Desire-Intention Model)
──────────────────────────────────────────
经典 Agent 理论的形式化实现。

Belief (信念): Agent 对当前环境状态的客观认知
  - 来源: 记忆层当前快照 + 最新观察 O_t
  - 更新: 每次感知后进行信念修正

Desire (愿望): Agent 试图达到的最终目标
  - 来源: System Prompt + 用户目标
  - 性质: 持久, 驱动整体行为方向

Intention (意图): 当前正在执行的具体行动计划
  - 来源: 认知层 CoT 分解结果
  - 性质: 临时, 随执行进展而变化

状态演化:
  B_t+1 = update_belief(B_t, O_t)
  D_t+1 = D_t (持久, 除非用户显式修改)
  I_t+1 = replan(I_t, B_t+1, D_t)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class BDIStatus(str, Enum):
    """BDI 系统状态"""
    IDLE = "idle"
    PERCEIVING = "perceiving"           # 感知中: 更新 Belief
    DELIBERATING = "deliberating"       # 审议中: 更新 Intention
    EXECUTING = "executing"             # 执行中: 行动
    REFLECTING = "reflecting"           # 反思中: 评估结果
    DONE = "done"
    FAILED = "failed"


@dataclass
class Belief:
    """
    信念状态 — Agent 对世界的当前认知

    包含:
    - 环境上下文 (当前对话轮次、用户偏好)
    - 领域知识 (从记忆层召回的文献/数据)
    - 当前观察 (最新一次执行结果)
    """
    # 用户上下文
    user_query: str = ""
    user_preferences: dict = field(default_factory=dict)

    # 领域上下文 (从记忆层召回)
    relevant_knowledge: list[dict] = field(default_factory=list)
    recalled_literature: list[dict] = field(default_factory=list)
    recalled_observations: list[dict] = field(default_factory=list)

    # 当前观察 O_t
    last_observation: Optional[dict] = None
    observation_history: list[dict] = field(default_factory=list)

    # 环境状态
    phase: str = ""
    tool_results: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # 置信度追踪
    confidence_scores: dict = field(default_factory=dict)  # {assertion: score}

    # 时间戳
    updated_at: float = field(default_factory=time.time)

    def update_observation(self, observation: dict):
        """接收新观察 O_t → 更新信念"""
        self.last_observation = observation
        self.observation_history.append(observation)
        self.updated_at = time.time()

        # 从观察中提取错误
        if observation.get("error"):
            self.errors.append(str(observation["error"]))

        # 合并工具结果
        if "results" in observation:
            self.tool_results.update(observation["results"])

    def update_knowledge(self, knowledge: list[dict]):
        """更新领域知识 (从记忆层召回)"""
        self.relevant_knowledge = knowledge
        self.updated_at = time.time()

    def get_context_summary(self, max_tokens: int = 2000) -> str:
        """生成信念摘要 (用于注入 LLM 上下文)"""
        parts = [f"User query: {self.user_query}"]

        if self.relevant_knowledge:
            parts.append(f"Relevant knowledge: {len(self.relevant_knowledge)} items")
            for k in self.relevant_knowledge[:3]:
                parts.append(f"  - {k.get('title', k.get('content', str(k)))[:200]}")

        if self.errors:
            parts.append(f"Recent errors: {self.errors[-3:]}")

        if self.tool_results:
            parts.append(f"Tool results available: {list(self.tool_results.keys())}")

        return "\n".join(parts)


@dataclass
class Desire:
    """
    愿望状态 — Agent 的最终目标

    通常由 System Prompt + 用户目标共同定义。
    持久性: 在整个会话期间稳定，除非用户显式修改。
    """
    # 主要目标
    primary_goal: str = ""            # e.g. "完成江豚文献综述"

    # 约束条件
    constraints: list[str] = field(default_factory=list)
    # e.g. ["仅限2020年后文献", "中英文均可"]

    # 质量标准
    quality_thresholds: dict = field(default_factory=dict)
    # e.g. {"min_papers": 10, "min_confidence": 0.7}

    # 禁止行为
    forbidden_actions: list[str] = field(default_factory=list)
    # e.g. ["数据删除", "外部写入"]

    # System prompt 级持久约束
    system_constraints: list[str] = field(default_factory=list)
    # e.g. ["可复现性", "人工确认关键决策"]

    def summarize(self) -> str:
        """愿望摘要"""
        parts = [f"Goal: {self.primary_goal}"]
        if self.constraints:
            parts.append(f"Constraints: {self.constraints}")
        return " | ".join(parts)


@dataclass
class Intention:
    """
    意图状态 — 当前正在执行的行动计划

    由认知层 CoT 分解产生。临时性: 随执行进展而变化。
    """
    # 当前计划步骤列表
    plan: list["PlanStep"] = field(default_factory=list)

    # 执行指针
    current_step_index: int = 0

    # 已完成的步骤
    completed_steps: list["PlanStep"] = field(default_factory=list)

    # 已放弃的路径
    abandoned_paths: list[list["PlanStep"]] = field(default_factory=list)

    # 计划生成方式
    decomposition_method: str = "cot"  # cot | tot | got

    # 时间戳
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def current_step(self) -> Optional["PlanStep"]:
        """当前步骤"""
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        """计划是否全部完成"""
        return self.current_step_index >= len(self.plan)

    def advance(self):
        """前进到下一步"""
        if self.current_step:
            self.current_step.status = StepStatus.COMPLETED
            self.completed_steps.append(self.current_step)
        self.current_step_index += 1
        self.updated_at = time.time()

    def retreat(self):
        """回退到上一步 (用于反思修正)"""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            if self.current_step:
                self.current_step.status = StepStatus.RETRYING
        self.updated_at = time.time()

    def abandon_path(self):
        """放弃当前路径，记录到 abandoned_paths"""
        remaining = self.plan[self.current_step_index:]
        self.abandoned_paths.append(remaining)
        self.plan = self.plan[:self.current_step_index]
        self.updated_at = time.time()

    def get_progress(self) -> dict:
        """进度报告"""
        return {
            "total_steps": len(self.plan),
            "completed": self.current_step_index,
            "remaining": max(0, len(self.plan) - self.current_step_index),
            "progress_pct": (
                self.current_step_index / max(len(self.plan), 1) * 100
            ),
            "current_step": str(self.current_step) if self.current_step else None,
        }


class StepStatus(str, Enum):
    """计划步骤状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """
    单个计划步骤

    对应 CoT 分解中的一个叶子节点，或 ToT 中的一个候选路径节点。
    """
    id: str
    description: str                          # 人类可读描述
    action: str                               # 具体动作 (tool name 或 code)
    action_type: str = "tool_call"            # tool_call | code_exec | query | human_approval
    params: dict = field(default_factory=dict)
    expected_output: str = ""                 # 期望输出
    dependencies: list[str] = field(default_factory=list)  # 依赖的前置步骤 ID
    status: StepStatus = StepStatus.PENDING
    result: Optional[dict] = None
    retries: int = 0
    max_retries: int = 3

    def __str__(self) -> str:
        return f"[{self.status.value}] {self.id}: {self.description}"


# ── BDI 协调器 ──────────────────────────────────────────────

class BDICoordinator:
    """
    BDI 协调器 — 管理 Belief/Desire/Intention 三者之间的交互

    执行循环:
        WHILE NOT DONE:
            perceive()      → 更新 Belief
            deliberate()    → 生成/修正 Intention
            execute_one()   → 执行一步
            IF error:
                reflect()   → 反思 → 修正 Intention

    状态转移函数:
        M_t+1 = Φ(M_t, O_t, A_t)   (记忆演化)
        B_t+1 = update_belief(B_t, O_t)
        I_t+1 = replan(I_t, B_t+1, D_t) if mismatch else I_t
    """

    def __init__(self):
        self.belief = Belief()
        self.desire = Desire()
        self.intention = Intention()
        self.status = BDIStatus.IDLE
        self._step_counter = 0
        logger.info("BDICoordinator initialized")

    def configure_desire(
        self,
        primary_goal: str,
        constraints: Optional[list[str]] = None,
        quality_thresholds: Optional[dict] = None,
        forbidden_actions: Optional[list[str]] = None,
    ):
        """配置愿望 (通常从 System Prompt + 用户目标生成)"""
        self.desire.primary_goal = primary_goal
        if constraints:
            self.desire.constraints = constraints
        if quality_thresholds:
            self.desire.quality_thresholds = quality_thresholds
        if forbidden_actions:
            self.desire.forbidden_actions = forbidden_actions
        logger.info(f"Desire configured: {self.desire.summarize()}")

    def perceive(self, observation: dict):
        """
        感知: 接收外部观察 O_t → 更新信念 B_t

        对应 MDP 中的 Observation & Belief Update:
            B_t+1 = update_belief(B_t, O_t)
        """
        self.status = BDIStatus.PERCEIVING
        self.belief.update_observation(observation)
        logger.debug(f"Belief updated (obs #{len(self.belief.observation_history)})")

    def deliberate(self, new_plan: list[PlanStep], method: str = "cot"):
        """
        审议: 根据当前信念和愿望，生成/修正意图

        对应策略函数:
            π(A_t | O_t, M_t) → Intention
        """
        self.status = BDIStatus.DELIBERATING
        self.intention = Intention(
            plan=new_plan,
            decomposition_method=method,
        )
        logger.info(f"Intention created: {len(new_plan)} steps via {method}")

    def revise_intention(self, revised_plan: list[PlanStep]):
        """修正意图 (反思后)"""
        old_plan = self.intention.plan
        self.intention.plan = revised_plan
        self.intention.current_step_index = 0
        self.intention.updated_at = __import__("time").time()
        logger.info(f"Intention revised: {len(old_plan)} → {len(revised_plan)} steps")

    def check_alignment(self) -> bool:
        """
        检查 Belief-Desire-Intention 对齐

        对齐条件:
        - 当前意图的预期结果与愿望一致
        - 信念中没有矛盾信息
        - 没有触发禁止操作
        """
        # 简化的对齐检查
        if self.intention.current_step:
            action = self.intention.current_step.action
            if action in self.desire.forbidden_actions:
                logger.warning(f"BDI misalignment: forbidden action {action}")
                return False
        return True

    def get_state_snapshot(self) -> dict:
        """获取 BDI 状态快照 (用于审计/调试)"""
        return {
            "status": self.status.value,
            "belief": {
                "user_query": self.belief.user_query[:200],
                "n_observations": len(self.belief.observation_history),
                "n_errors": len(self.belief.errors),
            },
            "desire": {
                "goal": self.desire.primary_goal[:200],
                "n_constraints": len(self.desire.constraints),
            },
            "intention": self.intention.get_progress(),
        }
