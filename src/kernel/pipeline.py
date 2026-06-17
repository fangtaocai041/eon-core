"""Pipeline — 统一管道调度器 (L0 太极引擎).

从 taiji.yaml 读取 DAG 拓扑 → Kahn 拓扑排序 → 阶段执行。
支持单项查询 (search) 和全管道运行 (run)。

核心职责:
  1. load_topology(): 解析 taiji.yaml 中的 tetrahedron.edges + vertices
  2. topological_sort(): Kahn 算法保证 DAG 无环顺序
  3. execute_stage(): 单阶段执行并返回 PhaseResult
  4. run(): 全管道编排: fish.search → cognitive.verify → domain.assess → conflict.arbitrate → fish.score

用法:
    pipeline = Pipeline()
    pipeline.load_topology()
    order = pipeline.topological_sort()
    result = pipeline.run("珠星三块鱼", mode="auto")
    print(result.to_dict())
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from src.kernel.event_bus import SystemEvent

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════

@dataclass
class StageResult:
    """单阶段执行结果."""
    stage_id: str                               # e.g. "V0", "V1", "V2"
    stage_name: str                             # e.g. "SupplyVertex"
    project: str                                # e.g. "fish-ecology-assistant"
    status: str = "pending"                     # pending | running | completed | failed | skipped
    duration_ms: float = 0.0
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    trace_id: str = ""


@dataclass
class PipelineResult:
    """全管道执行结果."""
    query: str = ""
    mode: str = "auto"
    trace_id: str = ""
    stages_executed: List[str] = field(default_factory=list)
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    stop_reason: str = ""                       # completed | early_exit | error
    synthesis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "trace_id": self.trace_id,
            "stages_executed": self.stages_executed,
            "total_duration_ms": self.total_duration_ms,
            "stop_reason": self.stop_reason,
            "synthesis": self.synthesis,
            "stages": {
                k: {
                    "stage_name": v.stage_name,
                    "project": v.project,
                    "status": v.status,
                    "duration_ms": v.duration_ms,
                    "error": v.error,
                    "output_keys": list(v.output.keys()) if v.output else [],
                }
                for k, v in self.stage_results.items()
            },
        }


# ═══════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════

class Pipeline:
    """统一管道调度器。

    读取 taiji.yaml 中的 DAG 拓扑 (tetrahedron.edges + vertices)，
    转换为可执行管道：拓扑排序 → 逐阶段调度。

    管道默认路径:
      V0(fish.search) → V1(cognitive.verify) → V2/P1(porpoise) |
      V3/P2(coilia) | V4/P3(culter) → V5(conflict.arbitrate) → 聚合

    模式:
      - "auto": 自动选择所有可达顶点
      - "search_only": 仅 V0 → V1
      - "verify_only": 仅 V1
      - "domain_p1": V0 → V1 → V2
      - "domain_p2": V0 → V1 → V3
      - "domain_p3": V0 → V1 → V4
      - "full": V0 → V1 → V2|V3|V4 → 聚合
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or str(
            Path(__file__).resolve().parent.parent.parent / "config" / "taiji.yaml"
        )
        self._config: Dict[str, Any] = {}
        self._vertices: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        # adjacency: vertex_id → [successor_ids]
        self._adjacency: Dict[str, List[str]] = {}
        # indegree for Kahn's algorithm
        self._indegree: Dict[str, int] = {}
        self._loaded = False
        # Registered stage executors: stage_id → Callable
        self._executors: Dict[str, Callable] = {}
        # Event bus reference (set by OriginKernel)
        self._event_bus: Any = None

    # ── Topology loading ──

    def load_topology(self) -> None:
        """读取 taiji.yaml 并构建 DAG 数据结构.

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 拓扑定义不合法
        """
        with open(self._config_path, "r", encoding="utf-8") as fh:
            self._config = yaml.safe_load(fh)

        # Parse vertices
        vertices_raw = self._config.get("vertices", {})
        if not vertices_raw:
            raise ValueError("taiji.yaml missing 'vertices' section")
        self._vertices = {vid: dict(v) for vid, v in vertices_raw.items()}
        logger.info(f"Pipeline loaded {len(self._vertices)} vertices")

        # Parse edges from tetrahedron section
        tetra = self._config.get("tetrahedron", {})
        self._edges = list(tetra.get("edges", []))
        logger.info(f"Pipeline loaded {len(self._edges)} edges")

        # Build adjacency and indegree maps
        self._adjacency = {vid: [] for vid in self._vertices}
        self._indegree = {vid: 0 for vid in self._vertices}

        for edge in self._edges:
            src = edge["from"]
            dst = edge["to"]
            if src not in self._vertices:
                logger.warning(f"Edge source '{src}' not in vertices, skipping")
                continue
            if dst not in self._vertices:
                logger.warning(f"Edge destination '{dst}' not in vertices, skipping")
                continue
            self._adjacency.setdefault(src, []).append(dst)
            self._indegree[dst] = self._indegree.get(dst, 0) + 1
            # Ensure src is in indegree too
            self._indegree.setdefault(src, 0)

        self._loaded = True
        logger.info(
            f"Pipeline DAG built: {len(self._vertices)} vertices, "
            f"{sum(len(v) for v in self._adjacency.values())} directed edges"
        )

    # ── Topological sort (Kahn's algorithm) ──

    def topological_sort(self) -> List[str]:
        """Kahn算法生成拓扑排序。

        保证: 对每条边 u→v, u 在结果中排在 v 之前。

        Returns:
            拓扑排序后的顶点 ID 列表

        Raises:
            RuntimeError: 未加载拓扑
            ValueError: 检测到环路 (DAG 不变式违反)
        """
        if not self._loaded:
            raise RuntimeError("Topology not loaded. Call load_topology() first.")

        # Copy indegree (Kahn modifies it)
        indeg = dict(self._indegree)

        # Queue: all vertices with indegree 0
        queue: deque[str] = deque(vid for vid, d in indeg.items() if d == 0)
        result: List[str] = []

        while queue:
            u = queue.popleft()
            result.append(u)
            for v in self._adjacency.get(u, []):
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)

        if len(result) != len(self._vertices):
            remaining = set(self._vertices) - set(result)
            raise ValueError(
                f"DAG invariant violated: cycle detected involving vertices {remaining}. "
                f"Topology must be acyclic (INV-001)."
            )

        logger.info(f"Topological order: {' → '.join(result)}")
        return result

    # ── Executor registration ──

    def register_executor(self, stage_id: str, executor: Callable) -> None:
        """注册阶段执行器。执行器签名: async fn(stage_id, context) -> StageResult"""
        self._executors[stage_id] = executor
        logger.debug(f"Executor registered for stage {stage_id}")

    def set_event_bus(self, bus: Any) -> None:
        """注入 EventBus 引用 (用于阶段间事件发布)."""
        self._event_bus = bus

    # ── Stage execution ──

    async def execute_stage(self, stage_id: str, context: dict) -> StageResult:
        """执行单个管道阶段。

        Args:
            stage_id: 顶点 ID (V0, V1, V2, V3, V4, V5)
            context: 管道上下文 (query, species, trace_id, ...)

        Returns:
            StageResult 包含状态、耗时和输出
        """
        vertex = self._vertices.get(stage_id)
        if vertex is None:
            return StageResult(
                stage_id=stage_id,
                stage_name="unknown",
                project="unknown",
                status="failed",
                error=f"Unknown stage_id: {stage_id}",
            )

        stage_name = vertex.get("name", stage_id)
        project = vertex.get("project", "unknown")
        result = StageResult(
            stage_id=stage_id,
            stage_name=stage_name,
            project=project,
            status="running",
            trace_id=context.get("trace_id", uuid.uuid4().hex),
        )

        t0 = time.perf_counter()

        try:
            # Try registered executor first
            executor = self._executors.get(stage_id)
            if executor is not None:
                raw = await executor(stage_id, context)
                result.output = raw if isinstance(raw, dict) else {"raw": str(raw)[:1000]}
            else:
                # Default: try to delegate via project loader
                raw = await self._default_executor(stage_id, context)
                result.output = raw

            result.status = "completed"
        except Exception as exc:
            logger.exception(f"Stage {stage_id} ({stage_name}) failed: {exc}")
            result.status = "failed"
            result.error = str(exc)

        result.duration_ms = (time.perf_counter() - t0) * 1000

        # Publish stage completion event if bus is available
        if self._event_bus is not None:
            try:
                event = SystemEvent(
                    trace_id=result.trace_id,
                    source="pipeline",
                    topic=f"pipeline.stage.{result.status}",
                    payload={
                        "stage_id": stage_id,
                        "stage_name": stage_name,
                        "project": project,
                        "status": result.status,
                        "duration_ms": result.duration_ms,
                    },
                )
                await self._event_bus.publish(event, f"pipeline.stage.{result.status}")
            except Exception:
                logger.debug("EventBus publish skipped (bus unavailable)")

        logger.info(
            f"Stage {stage_id} ({stage_name}): {result.status} "
            f"in {result.duration_ms:.0f}ms"
        )
        return result

    async def _default_executor(self, stage_id: str, context: dict) -> Dict[str, Any]:
        """默认执行器 — 通过 project_loader 委托给对应项目适配器。

        映射:
          V0 → fish.search(query)
          V1 → cognitive.search(query)
          V2 → porpoise.search(query)
          V3 → coilia.search(query)
          V4 → culter.search(query)
          V5 → conflict.arbitrate(context=prior_stage_outputs)
        """
        vertex = self._vertices.get(stage_id, {})
        project = vertex.get("project", "")
        query = context.get("query", "")
        species = context.get("species", query)

        # Build project→loader mapping
        loader_map = {
            "fish-ecology-assistant": ("get_fish", "search"),
            "cognitive-search-engine": ("get_cognitive", "search"),
            "porpoise-agent": ("get_porpoise", "search"),
            "coilia-agent": ("get_coilia", "search"),
            "culter-agent": ("get_culter", "search"),
            "conflict-arbiter": ("get_conflict", "arbitrate"),
        }

        loader_info = loader_map.get(project)
        if loader_info is None:
            return {"status": "skipped", "reason": f"No loader for project={project}"}

        loader_name, method = loader_info

        try:
            from scripts.project_loader import (
                get_cognitive, get_fish, get_porpoise, get_coilia,
                get_culter, get_conflict,
            )
            loaders = {
                "get_fish": get_fish,
                "get_cognitive": get_cognitive,
                "get_porpoise": get_porpoise,
                "get_coilia": get_coilia,
                "get_culter": get_culter,
                "get_conflict": get_conflict,
            }
            loader_fn = loaders.get(loader_name)
            if loader_fn is None:
                return {"status": "skipped", "reason": f"Loader {loader_name} not found"}

            adapter = loader_fn()
            if hasattr(adapter, method):
                fn = getattr(adapter, method)
                if method == "arbitrate":
                    return fn(context=context)
                return fn(query, species=species)
            elif hasattr(adapter, "search"):
                return adapter.search(query, species=species)
            else:
                return {"status": "skipped", "reason": f"No search method on {project}"}
        except ImportError:
            logger.debug(f"Project loader unavailable for {project}, stage {stage_id} skipped")
            return {"status": "skipped", "reason": "project_loader not available"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    # ── Full pipeline run ──

    async def run(self, query: str, mode: str = "auto") -> PipelineResult:
        """执行完整管道。

        管道顺序:
          1. V0(fish) — 知识库查询
          2. V1(cognitive) — 文献搜索验证
          3. V2|V3|V4 — 领域专研 (根据 mode 选择)
          4. 聚合结果 (单物种无需 V5 仲裁)

        Args:
            query: 物种名或研究问题
            mode: "auto" | "search_only" | "verify_only" |
                  "domain_p1" | "domain_p2" | "domain_p3" | "full"

        Returns:
            PipelineResult 包含所有阶段结果和综合摘要
        """
        if not self._loaded:
            self.load_topology()

        trace_id = uuid.uuid4().hex
        t0 = time.perf_counter()

        result = PipelineResult(
            query=query,
            mode=mode,
            trace_id=trace_id,
        )

        context: Dict[str, Any] = {
            "query": query,
            "species": query,
            "trace_id": trace_id,
            "mode": mode,
            "stage_outputs": {},
        }

        # Determine which stages to run based on mode
        mode_routes: Dict[str, List[str]] = {
            "auto":        ["V0", "V1"],
            "search_only": ["V0", "V1"],
            "verify_only": ["V1"],
            "domain_p1":   ["V0", "V1", "V2"],
            "domain_p2":   ["V0", "V1", "V3"],
            "domain_p3":   ["V0", "V1", "V4"],
            "full":        ["V0", "V1", "V2", "V3", "V4"],
        }
        stages_to_run = mode_routes.get(mode, ["V0", "V1"])

        # Ensure topological order
        try:
            topo_order = self.topological_sort()
        except ValueError:
            # If cycle, fall back to configured order
            topo_order = stages_to_run

        ordered_stages = [s for s in topo_order if s in stages_to_run]

        logger.info(
            f"Pipeline [{trace_id}] starting: "
            f"query='{query}', mode={mode}, stages={ordered_stages}"
        )

        early_exit = False

        for stage_id in ordered_stages:
            # Update context with prior outputs
            context["stage_outputs"] = {
                sid: sr.output
                for sid, sr in result.stage_results.items()
            }

            stage_result = await self.execute_stage(stage_id, context)
            result.stages_executed.append(stage_id)
            result.stage_results[stage_id] = stage_result

            # Publish pipeline stage done event
            if self._event_bus is not None:
                try:
                    SE = _get_system_event()
                    event = SE(
                        trace_id=trace_id,
                        source="pipeline",
                        topic="pipeline.stage.done",
                        payload={
                            "stage_id": stage_id,
                            "status": stage_result.status,
                            "duration_ms": stage_result.duration_ms,
                        },
                    )
                    await self._event_bus.publish(event, "pipeline.stage.done")
                except Exception:
                    pass

            # Early exit on V0/V1 failure
            if stage_result.status == "failed" and stage_id in ("V0", "V1"):
                result.stop_reason = "early_exit"
                early_exit = True
                logger.warning(
                    f"Pipeline [{trace_id}] early exit: "
                    f"stage {stage_id} failed — {stage_result.error}"
                )
                break

            # Stop after V0+V1 if mode is search_only
            if mode == "search_only" and stage_id == "V1":
                result.stop_reason = "completed"
                break

        if not early_exit:
            # Generate synthesis
            result.synthesis = self._synthesize(result)
            result.stop_reason = result.stop_reason or "completed"

        result.total_duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            f"Pipeline [{trace_id}] done: "
            f"{len(result.stages_executed)} stages, "
            f"{result.total_duration_ms:.0f}ms, "
            f"stop={result.stop_reason}"
        )

        return result

    def _synthesize(self, result: PipelineResult) -> str:
        """聚合所有阶段结果生成综合摘要."""
        parts: List[str] = []

        # V0 summary
        v0 = result.stage_results.get("V0")
        if v0 and v0.status == "completed":
            output = v0.output
            if isinstance(output, dict):
                items = output.get("items", [])
                total = output.get("total", len(items))
                parts.append(f"Fish knowledge base: {total} records found")

        # V1 summary
        v1 = result.stage_results.get("V1")
        if v1 and v1.status == "completed":
            output = v1.output
            if isinstance(output, dict):
                total = output.get("total", 0)
                parts.append(f"Cognitive search: {total} papers verified")

        # Domain stages
        for vid in ("V2", "V3", "V4"):
            vr = result.stage_results.get(vid)
            if vr and vr.status == "completed":
                name = vr.stage_name
                parts.append(f"{name}: domain assessment complete")

        if not parts:
            return "No stages completed successfully."

        return " | ".join(parts)

    # ── Utilities ──

    def get_vertex_info(self, stage_id: str) -> Optional[Dict[str, Any]]:
        """获取顶点配置信息."""
        return self._vertices.get(stage_id)

    def get_downstream_stages(self, stage_id: str) -> List[str]:
        """获取某阶段的所有下游阶段."""
        return list(self._adjacency.get(stage_id, []))

    def get_upstream_stages(self, stage_id: str) -> List[str]:
        """获取某阶段的所有上游阶段 (反向邻接)."""
        upstream: List[str] = []
        for src, targets in self._adjacency.items():
            if stage_id in targets:
                upstream.append(src)
        return upstream

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def vertex_count(self) -> int:
        return len(self._vertices)

    @property
    def edge_count(self) -> int:
        return len(self._edges)
