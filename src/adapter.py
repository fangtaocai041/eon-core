"""EonCoreAdapter — eon-core 协调内核的 IProjectAdapter 实现.

三角核心的协调者适配器。与其他5个项目的 adapter.py 对齐，
使 eon-core 可通过 project_loader 统一加载。

核心函数: route_event(event) → VertexChain
  - 通过 OriginKernel 的 DAG 拓扑路由到对应顶点
  - 返回执行链路和状态

独立/集成双模式:
  独立模式: 自检健康状态和拓扑快照
  集成模式: 通过 EventBus 协调所有顶点
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from scripts.adapter_protocol import IProjectAdapter
except ImportError:
    IProjectAdapter = object


class EonCoreAdapter(IProjectAdapter):
    """Adapter for eon-core (三角·协调器 — OriginKernel + EventBus + DAG路由)."""

    project_name = "eon-core"

    def __init__(self) -> None:
        self._kernel: Any = None
        self._init_kernel()

    def _init_kernel(self) -> None:
        """Lazy-init OriginKernel. 仅在导入成功时加载。"""
        try:
            from eon_core.src.kernel.origin import OriginKernel
            self._kernel = OriginKernel.get_instance()
        except Exception as exc:
            logger.debug(f"eon-core OriginKernel not available (standalone mode): {exc}")
            self._kernel = None

    # ── IProjectAdapter interface ──

    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """路由事件到顶点链。

        Args:
            query: 物种名或研究问题
            **kwargs:
                species: 物种学名 (可选)
                action: SEARCH | ASSESS | COMPARE | MONITOR
                domain: 领域限定 (可选)

        Returns:
            {status, chain, results, trace_id}
        """
        if self._kernel and hasattr(self._kernel, 'route_event'):
            try:
                event = {
                    "query": query,
                    "species": kwargs.get("species", query),
                    "action": kwargs.get("action", "SEARCH"),
                    "domain": kwargs.get("domain", ""),
                }
                result = self._kernel.route_event(event)
                return {
                    "status": "ok",
                    "kernel": "OriginKernel",
                    "chain": getattr(result, "vertex_chain", []),
                    "trace_id": getattr(result, "trace_id", ""),
                    "result": result,
                }
            except Exception as exc:
                return {"status": "error", "error": str(exc), "query": query}

        # Standalone mode — return topology snapshot
        return {
            "status": "standalone",
            "query": query,
            "note": "eon-core OriginKernel not bootstrapped. Run 'python -m eon_core.src.main' to start.",
            "topology": self._topology_snapshot(),
        }

    def health(self) -> Dict[str, Any]:
        """返回内核健康状态 + 拓扑快照。"""
        base = {
            "project": self.project_name,
            "version": "v7.3.0",
            "role": "三角核心·协调内核",
            "architecture": "OriginKernel + EventBus + YinYangPoles + SamsaraRing + TetrahedronMesh",
        }
        if self._kernel and hasattr(self._kernel, 'health_pulse'):
            try:
                pulse = self._kernel.health_pulse()
                base["status"] = "HEALTHY" if pulse else "DEGRADED"
                base["pulse"] = pulse
                return base
            except Exception as exc:
                base["status"] = "ERROR"
                base["error"] = str(exc)
                return base
        base["status"] = "STANDBY"
        base["note"] = "OriginKernel not bootstrapped"
        return base

    def info(self) -> Dict[str, Any]:
        """返回内核能力清单。"""
        info = {
            "project": self.project_name,
            "version": "v7.3.0",
            "role": "三角核心·协调内核 (T/Transition)",
            "element": "中 (Center)",
            "capabilities": [
                "event_bus — 异步事件总线 (所有子系统通信唯一通道)",
                "yin_yang_poles — YangPole(扩张·搜索) + YinPole(收敛·验证)",
                "tetrahedron_mesh — 四面体拓扑 + 谱间隙计算 + 混沌扰动",
                "vertex_routing — DAG拓扑路由到 V0(fish)/V1(cognitive)/V2(porpoise)/V3(coilia)",
                "samsara_karma — 六道业力评估 + KarmaCourt + Reincarnation",
                "sphere_gateway — REST/gRPC/WebSocket/MCP 统一API网关",
                "tendril_probes — 外部服务连接管理",
                "self_evolution — 规则自进化 + ChaosEngine(Rössler) + ParEGO优化",
                "lifecycle_sm — 五阶段状态机 SEEDING→SPROUTING→BLOOMING→FRUITING→PRUNING",
            ],
            "invariants": [
                "INV-001: Topology IS DAG",
                "INV-002: YangPole.verify() raises RuntimeError",
                "INV-003: YinPole.expand() raises RuntimeError",
                "INV-004: No direct vertex-to-vertex import",
                "INV-005: Spectral gap λ₂ ≥ 0.1 × baseline",
                "INV-006: DEVA count ≤ 25% of total agents",
                "INV-007: NARAKA agents auto-reincarnate after cooldown",
                "INV-008: Reincarnation atomicity (7-step protocol + snapshot rollback)",
            ],
        }
        return info

    # ── Internal ──

    def _topology_snapshot(self) -> Dict[str, Any]:
        """返回当前拓扑结构的静态快照。"""
        return {
            "vertices": {
                "V0": {"project": "fish-ecology-assistant", "role": "知识供给 (S/State)", "polarity": "yin"},
                "V1": {"project": "cognitive-search-engine", "role": "搜索验证 (V/Validation)", "polarity": "yang"},
                "V2": {"project": "porpoise-agent", "role": "江豚专研 (P₁)", "polarity": "yin"},
                "V3": {"project": "coilia-agent", "role": "刀鲚专研 (P₂)", "polarity": "yang"},
                "V4": {"project": "culter-agent", "role": "鲌类专研 (P₃)", "polarity": "yin"},
                "V5": {"project": "conflict-arbiter", "role": "冲突仲裁 (C)", "polarity": "fire"},
            },
            "pathways": {
                "P1": "V0(fish) → V1(cognitive)",
                "P2": "V1(cognitive) → V0(fish)",
                "P3": "V1(cognitive) → V2(porpoise) | V3(coilia) | V4(culter)",
                "P4": "any → V5(conflict)",
                "P5": "V5(conflict) → user",
            },
            "mesh": "TetrahedronMesh — 谱间隙 λ₂ ≥ 0.1 × baseline, 混沌扰动 100 queries/step",
            "samsara": "KarmaCourt 60s cycle — DEVA/HUMAN/ASURA/ANIMAL/PRETA/NARAKA",
        }


def get_adapter() -> EonCoreAdapter:
    return EonCoreAdapter()
