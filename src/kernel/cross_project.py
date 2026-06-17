"""CrossProjectPipeline — 跨项目管道编排器 (L0 协调核心).

从 project_loader 加载所有项目适配器, 构建标准管道:
  fish.search → cognitive.verify → conflict.arbitrate → fish.score

支持:
  - 标准管道 (standard): fish.search → cognitive.verify → conflict.arbitrate → fish.score
  - 快速管道 (fast): fish.search → fish.score (跳过高成本阶段)
  - 领域管道 (domain_p1/p2/p3): fish.search → 特定领域 → fish.score
  - 仲裁管道 (arbitrate): 仅冲突仲裁
  - 全栈管道 (full): fish.search → cognitive.verify → conflict.arbitrate → eon.analyze → fish.score
  - 自定义路由 (custom): 用户定义阶段顺序
  - 动态路由 (dynamic): 根据之前阶段结果决定下一阶段

与 Pipeline 的关系:
  - Pipeline 负责 DAG 拓扑 → 阶段执行 (底层)
  - CrossProjectPipeline 负责项目适配器加载 + 管道模板 (上层)

用法:
    cp = CrossProjectPipeline()
    await cp.bootstrap()
    result = await cp.run("珠星三块鱼", route="standard")
    print(result.to_dict())
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.kernel.event_bus import SystemEvent

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class Route(str, Enum):
    """预定义管道路由."""
    STANDARD = "standard"       # fish.search → cognitive.verify → conflict.arbitrate → fish.score
    FAST = "fast"               # fish.search → fish.score (跳过高成本阶段)
    DOMAIN_P1 = "domain_p1"     # fish.search → porpoise.search → fish.score
    DOMAIN_P2 = "domain_p2"     # fish.search → coilia.search → fish.score
    DOMAIN_P3 = "domain_p3"     # fish.search → culter.search → fish.score
    ARBITRATE = "arbitrate"    # conflict.arbitrate (仅仲裁)
    CUSTOM = "custom"           # 用户定义
    DYNAMIC = "dynamic"         # 根据结果动态决定
    FULL = "full"               # fish.search → cognitive.verify → conflict.arbitrate → eon.analyze → fish.score


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ═══════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════

@dataclass
class StageOutput:
    """跨项目阶段输出."""
    project: str
    status: StageStatus
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossProjectResult:
    """跨项目管道结果."""
    query: str = ""
    route: str = "standard"
    trace_id: str = ""
    stages: Dict[str, StageOutput] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    stop_reason: str = ""
    synthesis: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "route": self.route,
            "trace_id": self.trace_id,
            "total_duration_ms": self.total_duration_ms,
            "stop_reason": self.stop_reason,
            "synthesis": self.synthesis,
            "errors": self.errors,
            "stages": {
                pid: {
                    "project": s.project,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "data_keys": list(s.data.keys()) if s.data else [],
                }
                for pid, s in self.stages.items()
            },
        }


# ═══════════════════════════════════════════════════════════════
# CrossProjectPipeline
# ═══════════════════════════════════════════════════════════════

class CrossProjectPipeline:
    """跨项目管道编排器。

    使用预定义路由模板编排跨项目执行流程.
    """

    # 路由模板: route → [(project_key, method, required)]
    # required=True 表示失败时管道中止
    _ROUTE_TEMPLATES: Dict[Route, List[Tuple[str, str, bool]]] = {
        Route.STANDARD: [
            ("fish", "search", True),
            ("cognitive", "verify", True),
            ("conflict", "arbitrate", False),
            ("fish", "score", False),
        ],
        Route.FAST: [
            ("fish", "search", True),
            ("fish", "score", False),
        ],
        Route.DOMAIN_P1: [
            ("fish", "search", True),
            ("porpoise", "search", False),
            ("fish", "score", False),
        ],
        Route.DOMAIN_P2: [
            ("fish", "search", True),
            ("coilia", "search", False),
            ("fish", "score", False),
        ],
        Route.DOMAIN_P3: [
            ("fish", "search", True),
            ("culter", "search", False),
            ("fish", "score", False),
        ],
        Route.ARBITRATE: [
            ("conflict", "arbitrate", True),
        ],
        Route.FULL: [
            ("fish", "search", True),
            ("cognitive", "verify", True),
            ("conflict", "arbitrate", False),
            ("eon", "analyze", False),
            ("fish", "score", False),
        ],
    }

    def __init__(self) -> None:
        self._adapters: Dict[str, Any] = {}
        self._bootstrapped = False
        self._event_bus: Any = None
        # 自定义路由: list of (project_key, method)
        self._custom_route: Optional[List[Tuple[str, str]]] = None
        # 动态路由规则: (prev_stage_key, prev_status) → next_stage
        self._dynamic_rules: Dict[str, Callable] = {}

    # ── Bootstrap ──

    async def bootstrap(self, load_all: bool = True) -> None:
        """加载所有项目适配器。

        Args:
            load_all: True=加载全部7个项目 (含eon-core); False=仅加载 fish + cognitive
        """
        from scripts.project_loader import (
            get_fish, get_cognitive, get_porpoise, get_coilia,
            get_culter, get_conflict, get_eon,
        )

        loaders: Dict[str, Any] = {
            "fish": get_fish,
            "cognitive": get_cognitive,
        }

        if load_all:
            loaders.update({
                "porpoise": get_porpoise,
                "coilia": get_coilia,
                "culter": get_culter,
                "conflict": get_conflict,
                "eon": get_eon,
            })

        for name, loader_fn in loaders.items():
            try:
                adapter = loader_fn()
                self._adapters[name] = adapter
                logger.info(f"  ✅ CrossProject adapter '{name}' loaded")
            except Exception as exc:
                logger.warning(f"  ⚠️  CrossProject adapter '{name}' failed: {exc}")

        self._bootstrapped = True
        logger.info(
            f"CrossProjectPipeline bootstrapped: "
            f"{len(self._adapters)} adapters loaded"
        )

    # ── Route configuration ──

    def set_custom_route(self, stages: List[Tuple[str, str]]) -> None:
        """设置自定义路由。

        Args:
            stages: [(project_key, method), ...]
                例: [("fish", "search"), ("cognitive", "search")]
        """
        self._custom_route = stages
        logger.info(f"Custom route set: {[f'{p}.{m}' for p, m in stages]}")

    def add_dynamic_rule(
        self,
        condition_key: str,
        rule: Callable[[StageOutput], Optional[Tuple[str, str]]],
    ) -> None:
        """添加动态路由规则。

        Args:
            condition_key: 规则名 (如 "if_fish_has_results")
            rule: 函数, 接收上一阶段 StageOutput, 返回 (project_key, method) 或 None
        """
        self._dynamic_rules[condition_key] = rule

    def set_event_bus(self, bus: Any) -> None:
        """注入 EventBus (用于阶段间事件发布)."""
        self._event_bus = bus

    # ── Run ──

    async def run(
        self,
        query: str,
        route: Route = Route.STANDARD,
        *,
        species: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CrossProjectResult:
        """执行跨项目管道。

        Args:
            query: 查询字符串
            route: 路由模板
            species: 物种名 (默认使用 query)
            context: 额外上下文

        Returns:
            CrossProjectResult
        """
        if not self._bootstrapped:
            await self.bootstrap()

        trace_id = uuid.uuid4().hex
        t0 = time.perf_counter()
        species = species or query

        result = CrossProjectResult(
            query=query,
            route=route.value,
            trace_id=trace_id,
        )

        ctx: Dict[str, Any] = {
            "trace_id": trace_id,
        }
        if context:
            ctx.update(context)

        # species/query 已通过显式参数传递，不在 ctx 中重复
        _species = species or query
        _query = query

        # Resolve stages to run
        if route == Route.CUSTOM:
            if not self._custom_route:
                result.stop_reason = "no_custom_route"
                result.errors.append("Custom route requested but not configured")
                return result
            stages = [(p, m, False) for p, m in self._custom_route]
        elif route == Route.DYNAMIC:
            stages: List[Tuple[str, str, bool]] = [("fish", "search", True)]
        else:
            stages = list(self._ROUTE_TEMPLATES.get(route, self._ROUTE_TEMPLATES[Route.STANDARD]))

        logger.info(
            f"CrossProject [{trace_id}]: query='{query}', "
            f"route={route.value}, adapter_count={len(self._adapters)}"
        )

        for stage_idx, (project_key, method, required) in enumerate(stages):
            adapter = self._adapters.get(project_key)

            if adapter is None:
                msg = f"Adapter '{project_key}' not loaded"
                if required:
                    result.errors.append(msg)
                    result.stop_reason = "adapter_missing"
                    break
                logger.warning(msg)
                continue

            stage_t0 = time.perf_counter()
            stage_output = StageOutput(
                project=project_key,
                status=StageStatus.RUNNING,
            )

            try:
                # Call adapter method
                if method in ("verify", "score", "analyze"):
                    # These methods benefit from prior stage outputs
                    prior_outputs = {
                        pid: s.data
                        for pid, s in result.stages.items()
                        if s.status == StageStatus.COMPLETED
                    }
                    method_ctx = dict(ctx)
                    method_ctx["prior_outputs"] = prior_outputs
                    method_ctx["species"] = _species
                    # Note: "query" NOT added — passed as first positional arg
                    if hasattr(adapter, method):
                        fn = getattr(adapter, method)
                        if asyncio.iscoroutinefunction(fn):
                            raw = await fn(_query, **method_ctx)
                        else:
                            raw = fn(_query, **method_ctx)
                    elif hasattr(adapter, "search"):
                        raw = adapter.search(_query, **method_ctx)
                    else:
                        raw = {"status": "skipped", "reason": f"No '{method}' method"}

                elif method == "arbitrate":
                    # arbitrate(context_dict) — needs full context as first arg
                    prior_outputs = {
                        pid: s.data
                        for pid, s in result.stages.items()
                        if s.status == StageStatus.COMPLETED
                    }
                    arb_ctx = dict(ctx)
                    arb_ctx["prior_outputs"] = prior_outputs
                    arb_ctx["species"] = _species
                    arb_ctx["query"] = _query
                    if hasattr(adapter, method):
                        fn = getattr(adapter, method)
                        raw = fn(arb_ctx)
                    elif hasattr(adapter, "search"):
                        raw = adapter.search(_query, **arb_ctx)
                    else:
                        raw = {"status": "skipped", "reason": f"No '{method}' method"}

                elif hasattr(adapter, method):
                    fn = getattr(adapter, method)
                    if asyncio.iscoroutinefunction(fn):
                        raw = await fn(_query, species=_species, **ctx)
                    else:
                        raw = fn(_query, species=_species, **ctx)
                elif hasattr(adapter, "search"):
                    raw = adapter.search(_query, species=_species, **ctx)
                else:
                    raw = {"status": "skipped", "reason": f"No '{method}' method"}

                stage_output.data = raw if isinstance(raw, dict) else {"raw": str(raw)[:1000]}
                stage_output.status = StageStatus.COMPLETED

                # Publish stage done event
                if self._event_bus is not None:
                    try:
                        event = SystemEvent(
                            trace_id=trace_id,
                            source="cross_project",
                            topic=f"cross_project.{project_key}.done",
                            payload={
                                "project": project_key,
                                "method": method,
                                "status": "completed",
                            },
                        )
                        await self._event_bus.publish(
                            event, f"cross_project.{project_key}.done"
                        )
                    except Exception:
                        pass

            except Exception as exc:
                stage_output.status = StageStatus.FAILED
                stage_output.error = str(exc)
                result.errors.append(f"{project_key}.{method}: {exc}")
                logger.exception(f"Stage {project_key}.{method} failed")

                if required:
                    result.stop_reason = f"required_stage_failed:{project_key}"
                    stage_output.duration_ms = (time.perf_counter() - stage_t0) * 1000
                    result.stages[project_key] = stage_output
                    break

            stage_output.duration_ms = (time.perf_counter() - stage_t0) * 1000
            result.stages[project_key] = stage_output

            # Dynamic routing: after fish.search, decide next
            if route == Route.DYNAMIC and project_key == "fish":
                next_stage = await self._resolve_dynamic(stage_output)
                if next_stage:
                    stages.append((next_stage[0], next_stage[1], False))
                else:
                    # Default: cognitive
                    stages.append(("cognitive", "search", True))

        # Generate synthesis
        if result.stages:
            result.synthesis = self._build_synthesis(result)
            if not result.stop_reason:
                result.stop_reason = "completed"

        result.total_duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            f"CrossProject [{trace_id}]: done in {result.total_duration_ms:.0f}ms, "
            f"{len(result.stages)} stages, stop={result.stop_reason}"
        )

        return result

    async def _resolve_dynamic(
        self, stage_output: StageOutput
    ) -> Optional[Tuple[str, str]]:
        """应用动态路由规则."""
        for rule_name, rule_fn in self._dynamic_rules.items():
            try:
                next_stage = rule_fn(stage_output)
                if next_stage is not None:
                    logger.debug(f"Dynamic rule '{rule_name}' → {next_stage}")
                    return next_stage
            except Exception as exc:
                logger.warning(f"Dynamic rule '{rule_name}' error: {exc}")
        return None

    def _build_synthesis(self, result: CrossProjectResult) -> Dict[str, Any]:
        """聚合各阶段输出生成综合摘要."""
        synthesis: Dict[str, Any] = {
            "total_stages": len(result.stages),
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "per_project": {},
        }

        for pid, stage in result.stages.items():
            synthesis["per_project"][pid] = {
                "status": stage.status.value,
                "duration_ms": stage.duration_ms,
            }
            if stage.status == StageStatus.COMPLETED:
                synthesis["completed"] += 1
            elif stage.status == StageStatus.FAILED:
                synthesis["failed"] += 1
            else:
                synthesis["skipped"] += 1

        return synthesis

    # ── Health ──

    async def health(self) -> Dict[str, Any]:
        """所有适配器健康检查."""
        statuses: Dict[str, Any] = {}
        all_ok = True

        for name, adapter in self._adapters.items():
            try:
                if hasattr(adapter, "health"):
                    statuses[name] = adapter.health()
                else:
                    statuses[name] = {"status": "ok", "note": "no health method"}
            except Exception as exc:
                statuses[name] = {"status": "error", "error": str(exc)}
                all_ok = False

        return {
            "status": "healthy" if all_ok else "degraded",
            "adapters_loaded": len(self._adapters),
            "adapters": statuses,
        }

    # ── Properties ──

    @property
    def is_bootstrapped(self) -> bool:
        return self._bootstrapped

    @property
    def adapter_count(self) -> int:
        return len(self._adapters)

    @property
    def loaded_projects(self) -> List[str]:
        return list(self._adapters.keys())


# ═══════════════════════════════════════════════════════════════
# CrossProjectResult helpers
# ═══════════════════════════════════════════════════════════════

# (extend via monkey-patch — avoids circular dependency)
def _result_stages_completed(self: CrossProjectResult) -> int:
    """Number of stages that completed successfully."""
    return sum(
        1 for s in self.stages.values()
        if s.status == StageStatus.COMPLETED
    )

CrossProjectResult.stages_completed = property(_result_stages_completed)
