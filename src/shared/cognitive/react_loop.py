"""
ReAct 主循环 (Reasoning and Acting Loop)
─────────────────────────────────────────
经典的闭环反馈控制系统: Think → Act → Observe → Reflect

这是整个 Agent 的核心执行引擎。基于 DeepSeek 优化。

循环逻辑:
    WHILE NOT DONE AND steps < max_steps:
        1. THINK:     模型推理 → 生成行动计划
        2. ACT:       执行计划 (工具调用 / 代码执行)
        3. OBSERVE:   捕获执行结果
        4. REFLECT:   评估结果 → 决定继续/修正/停止
        5. MEMORIZE:  持久化关键信息到记忆层

与 MDP 形式化的对应:
    - State S_t:    (Belief, Memory)
    - Action A_t:   (Tool call / Code exec)
    - Observation:  执行结果 O_t+1
    - Policy π:     LLM 决策 (Think 阶段)
    - Transition:   S_t+1 = f(S_t, A_t, O_t+1)

与 BDI 模型的对应:
    - Think → Deliberation (更新 Intention)
    - Act   → Execution (执行 Intention)
    - Observe → Perception (更新 Belief)
    - Reflect → BDI 对齐检查 + 修正
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class LoopStatus(str, Enum):
    """ReAct 循环状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    DONE = "done"
    MAX_STEPS = "max_steps_reached"
    ERROR = "error"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class ReActStep:
    """单次 ReAct 循环记录"""
    step_id: int
    thought: str = ""               # Think 阶段的推理
    action: Optional[dict] = None   # Act 阶段的动作
    observation: Optional[dict] = None  # Observe 阶段的结果
    reflection: Optional[str] = None    # Reflect 阶段的反思
    status: LoopStatus = LoopStatus.IDLE
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0


@dataclass
class ReActContext:
    """ReAct 循环上下文"""
    user_query: str
    max_steps: int = 50
    max_tool_calls_per_step: int = 5
    timeout_seconds: float = 300.0
    require_approval: set[str] = field(default_factory=set)  # 需要人工审批的动作


class ReActLoop:
    """
    ReAct 主循环引擎

    用法:
        loop = ReActLoop(
            model_client=deepseek_client,
            tool_registry=tools,
            bdi=bdi_coordinator,
            memory=memory_store,
        )
        result = await loop.run("搜索江豚被动声学监测文献")
    """

    def __init__(
        self,
        model_client: Any = None,               # LLM client (OpenAI-compatible)
        tool_registry: Any = None,              # ToolRegistry
        bdi: Any = None,                        # BDICoordinator
        memory: Any = None,                     # MemoryManager
        config: Optional[dict] = None,
    ):
        self.model = model_client
        self.tools = tool_registry
        self.bdi = bdi
        self.memory = memory
        self.config = config or {}

        # 循环状态
        self.steps: list[ReActStep] = []
        self.status = LoopStatus.IDLE
        self.final_result: Optional[dict] = None
        self._step_counter = 0

        # Hook points (可注入自定义逻辑)
        self.on_think: Optional[Callable] = None
        self.on_act: Optional[Callable] = None
        self.on_observe: Optional[Callable] = None
        self.on_reflect: Optional[Callable] = None

        # 中断信号
        self._should_stop = False
        self._pending_approval: Optional[str] = None

        logger.info("ReActLoop initialized")

    async def run(
        self,
        user_query: str,
        context: Optional[ReActContext] = None,
    ) -> dict[str, Any]:
        """
        主执行入口

        Args:
            user_query: 用户查询
            context: 循环上下文 (max_steps 等)

        Returns:
            dict: 最终结果，包含 reasoning_traces
        """
        ctx = context or ReActContext(user_query=user_query)
        start_time = time.time()
        logger.info(f"ReAct loop started: {user_query[:100]}")

        # 初始化 BDI
        if self.bdi:
            self.bdi.belief.user_query = user_query

        # ── 主循环 ─────────────────────────────────────
        while self._step_counter < ctx.max_steps and not self._should_stop:

            # 检查超时
            if time.time() - start_time > ctx.timeout_seconds:
                logger.warning("ReAct loop timeout")
                self.status = LoopStatus.MAX_STEPS
                break

            step = ReActStep(step_id=self._step_counter)

            try:
                # 1. THINK — 生成行动计划
                step_start = time.time()
                step.thought = await self._think(ctx)
                step.status = LoopStatus.THINKING

                # 检查是否完成
                if self._is_done(step.thought):
                    self.status = LoopStatus.DONE
                    step.duration_ms = (time.time() - step_start) * 1000
                    self.steps.append(step)
                    break

                # 2. ACT — 执行行动
                step.status = LoopStatus.ACTING
                step.action = await self._act(step.thought, ctx)
                self._step_counter += 1

                # 人工审批检查
                if step.action and step.action.get("requires_approval"):
                    self.status = LoopStatus.WAITING_APPROVAL
                    self._pending_approval = step.action.get("approval_message")
                    step.duration_ms = (time.time() - step_start) * 1000
                    self.steps.append(step)
                    break

                # 3. OBSERVE — 捕获结果
                step.status = LoopStatus.OBSERVING
                step.observation = await self._observe(step.action)

                # 4. REFLECT — 评估与反思
                step.status = LoopStatus.REFLECTING
                step.reflection = await self._reflect(step)

                # 5. 更新 BDI
                if self.bdi and step.observation:
                    self.bdi.perceive(step.observation)

                # 6. 记忆持久化
                if self.memory and step.observation:
                    await self._memorize(step)

                step.status = LoopStatus.IDLE  # 等待下一轮
                step.duration_ms = (time.time() - step_start) * 1000

            except Exception as e:
                logger.error(f"ReAct step {self._step_counter} failed: {e}")
                step.status = LoopStatus.ERROR
                step.observation = {"error": str(e)}

            self.steps.append(step)

            # 错误次数过多 → 停止
            error_count = sum(1 for s in self.steps if s.status == LoopStatus.ERROR)
            if error_count > 5:
                logger.error("Too many errors, stopping")
                self.status = LoopStatus.ERROR
                break

        # ── 生成最终结果 ──────────────────────────────
        elapsed = time.time() - start_time
        self.final_result = self._compile_result(elapsed)
        logger.info(f"ReAct loop finished: {len(self.steps)} steps, {elapsed:.1f}s")
        return self.final_result

    async def _think(self, ctx: ReActContext) -> str:
        """
        THINK 阶段: 模型推理

        调用 LLM 生成下一步行动计划。
        如果 on_think hook 存在，则调用之。
        """
        if self.on_think:
            return await self.on_think(ctx)

        # 默认: 构建 prompt → 调用 LLM
        if self.model:
            response = await self._call_model_for_think(ctx)
            return response
        else:
            # 无模型时的 fallback (测试用)
            return self._fallback_think(ctx)

    def _fallback_think(self, ctx: ReActContext) -> str:
        """无 LLM 时的 fallback 推理 (基于关键词)"""
        query_lower = ctx.user_query.lower()

        if any(kw in query_lower for kw in ["搜索", "search", "文献", "paper"]):
            return "SEARCH_LITERATURE: 在 PubMed 和 Semantic Scholar 中搜索相关文献"
        elif any(kw in query_lower for kw in ["分析", "analyze", "声学", "acoustic"]):
            return "ANALYZE_ACOUSTIC: 加载音频文件 → 预处理 → 检测脉冲 → 分类"
        elif any(kw in query_lower for kw in ["报告", "report", "生成"]):
            return "GENERATE_REPORT: 汇总结果 → 生成结构化报告"
        else:
            return "CLARIFY: 需要更多信息来确定任务"

    async def _call_model_for_think(self, ctx: ReActContext) -> str:
        """调用 LLM 进行推理"""
        try:
            messages = self._build_think_messages(ctx)
            response = await self.model.chat.completions.create(
                model=self.config.get("model", "deepseek-chat"),
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Model think call failed: {e}")
            return self._fallback_think(ctx)

    def _build_think_messages(self, ctx: ReActContext) -> list[dict]:
        """构建 Think 阶段的 messages"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个研究助手 Agent。请根据用户查询决定下一步行动。"
                    "输出格式: ACTION: <action_name>(<params>)\n"
                    "可用动作: SEARCH_LITERATURE, ANALYZE_ACOUSTIC, "
                    "ESTIMATE_ABUNDANCE, GENERATE_REPORT, CLARIFY, DONE"
                ),
            },
            {"role": "user", "content": ctx.user_query},
        ]

        # 注入最近步骤的观察
        recent_obs = [
            s.observation for s in self.steps[-3:]
            if s.observation
        ]
        if recent_obs:
            obs_text = "\n".join(str(o) for o in recent_obs)
            messages.append({
                "role": "assistant",
                "content": f"Recent observations:\n{obs_text}",
            })

        # 注入 BDI 上下文
        if self.bdi:
            messages.append({
                "role": "system",
                "content": self.bdi.belief.get_context_summary(),
            })

        return messages

    async def _act(self, thought: str, ctx: ReActContext) -> Optional[dict]:
        """
        ACT 阶段: 执行行动

        解析 thought → 调用对应工具。
        """
        if self.on_act:
            return await self.on_act(thought, ctx)

        action = self._parse_action(thought)
        if not action:
            return None

        # 通过 ToolRegistry 执行
        if self.tools:
            try:
                result = self.tools.call(action["name"], **action.get("params", {}))
                action["result"] = result
                return action
            except Exception as e:
                logger.error(f"Tool call failed: {action['name']}: {e}")
                action["error"] = str(e)
                return action

        return action

    def _parse_action(self, thought: str) -> Optional[dict]:
        """从 thought 中解析出动作"""
        import re

        # 匹配: ACTION: name(params) 或 name(params)
        match = re.search(
            r'(?:ACTION:\s*)?(\w+)\s*\(([^)]*)\)',
            thought,
            re.IGNORECASE,
        )
        if match:
            name = match.group(1).lower()
            params_str = match.group(2)

            # 简单参数解析 (key=value 或 仅值)
            params = {}
            if params_str.strip():
                for part in params_str.split(","):
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        params[k.strip()] = v.strip().strip("\"'")
                    else:
                        params["query"] = part

            return {"name": name, "params": params, "raw": thought}

        # 匹配 DONE / CLARIFY 等无参数动作
        if re.match(r'^\s*(DONE|CLARIFY|STOP)\s*$', thought, re.IGNORECASE):
            return {"name": thought.strip().lower(), "params": {}, "raw": thought}

        return None

    async def _observe(self, action: Optional[dict]) -> dict:
        """
        OBSERVE 阶段: 捕获执行结果

        将工具执行结果 + 环境反馈封装为 Observation。
        """
        if self.on_observe:
            return await self.on_observe(action)

        if not action:
            return {"status": "no_action", "error": "No action to observe"}

        observation = {
            "action_name": action.get("name"),
            "params": action.get("params"),
            "result": action.get("result"),
            "error": action.get("error"),
            "timestamp": time.time(),
        }

        # 标记是否需要人工审批
        if action.get("name") in (
            "field_survey_plan", "conservation_recommendation",
            "data_deletion", "external_api_write",
        ):
            observation["requires_approval"] = True
            observation["approval_message"] = (
                f"Action '{action['name']}' requires human approval. Proceed?"
            )

        return observation

    async def _reflect(self, step: ReActStep) -> Optional[str]:
        """
        REFLECT 阶段: 评估结果

        检查:
        - 执行是否成功?
        - 结果是否符合预期?
        - 是否需要修正路径?
        - 是否触发 BDI 对齐问题?
        """
        if self.on_reflect:
            return await self.on_reflect(step)

        if not step.observation:
            return "No observation to reflect on"

        reflections = []

        # 错误检查
        if step.observation.get("error"):
            reflections.append(
                f"Error detected: {step.observation['error']}. "
                f"Will retry with adjusted parameters."
            )
            # 通知 BDI 进行路径回溯
            if self.bdi:
                self.bdi.intention.retreat()

        # 结果验证
        if step.observation.get("result") == "not_implemented":
            reflections.append(
                "Tool not yet implemented. May need alternative approach."
            )

        # BDI 对齐检查
        if self.bdi and not self.bdi.check_alignment():
            reflections.append(
                "BDI misalignment detected. Revising intention."
            )

        # 完成度检查
        if step.action and step.action.get("name") == "done":
            reflections.append("Task marked as done. Verifying completeness.")
            if self.bdi and not self.bdi.intention.is_complete:
                reflections.append(
                    "WARNING: DONE called but intention plan is incomplete. "
                    f"({self.bdi.intention.get_progress()['progress_pct']:.0f}% complete)"
                )

        return "\n".join(reflections) if reflections else "Step completed successfully"

    def _is_done(self, thought: str) -> bool:
        """检查是否应该终止循环"""
        done_signals = ["DONE", "STOP", "FINISHED", "COMPLETE"]
        return any(sig in thought.upper() for sig in done_signals)

    async def _memorize(self, step: ReActStep):
        """持久化关键信息到记忆层"""
        if not self.memory:
            return
        try:
            self.memory.add_document(
                collection="execution_log",
                document=str(step.observation),
                metadata={
                    "step_id": step.step_id,
                    "action": step.action.get("name") if step.action else "",
                },
            )
        except Exception as e:
            logger.debug(f"Memorize failed (non-critical): {e}")

    def _compile_result(self, elapsed: float) -> dict[str, Any]:
        """编译最终结果"""
        # 从步骤中提取关键信息
        responses = []
        papers = []
        acoustic = None

        for step in self.steps:
            if step.observation:
                obs = step.observation
                if obs.get("result") and isinstance(obs["result"], dict):
                    r = obs["result"]
                    if "papers" in r:
                        papers.extend(r["papers"])
                    if "response" in r:
                        responses.append(r["response"])
                    if "n_clicks" in r:
                        acoustic = r

        return {
            "status": self.status.value,
            "steps": len(self.steps),
            "elapsed_seconds": elapsed,
            "response": "\n\n".join(responses) if responses else None,
            "papers": papers if papers else None,
            "acoustic": acoustic,
            "reasoning_traces": [
                {
                    "step": s.step_id,
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                    "reflection": s.reflection,
                }
                for s in self.steps
            ],
            "bdi_snapshot": self.bdi.get_state_snapshot() if self.bdi else None,
        }

    def stop(self):
        """发送停止信号"""
        self._should_stop = True
        logger.info("Stop signal sent to ReAct loop")

    def approve(self):
        """人工审批通过 → 继续执行"""
        self._pending_approval = None
        self.status = LoopStatus.IDLE
        self._should_stop = False
        logger.info("Human approval received, resuming")
