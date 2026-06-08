"""SupplyVertex (V0) — ☀️ 太阳·老阳.

Role: 广度知识供给 — 11-engine parallel search, maximize recall ≥ 98%.
Project: fish-ecology-assistant
gRPC port: 50051

Trigrams:
  - qian (☰ 乾): MetaSearchEngine — 11-engine parallel search + RRF fusion
  - dui  (☱ 兑): ChineseSourceGateway — CNKI/CSCD/万方 adapter

Extends: BaseVertex + YangPole (primary)
WuXing element: EARTH (承载·化育)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..kernel.event_bus import SystemEvent
from ..poles.yang_pole import YangPole
from .base_vertex import BaseVertex, EvolutionDelta, HealthReport

logger = logging.getLogger(__name__)


class SupplyVertex(BaseVertex, YangPole):
    """V0 — 知识供给顶点.

    Receives search queries from EventBus topic 'vertex.V0',
    delegates to qian (meta search) + dui (Chinese gateway) trigrams,
    merges results with LOW confidence, publishes to 'vertex.V0.completed'.
    """

    def __init__(self) -> None:
        BaseVertex.__init__(
            self,
            vertex_id="V0",
            coordinates=(1.0, 1.0, 1.0),
            wuxing_element="EARTH",
        )
        YangPole.__init__(self)
        self._recall_rate: float = 0.96
        self.gRPC_port: int = 50051
        self._engines: List[Dict[str, Any]] = [
            {"name": "pubmed", "weight": 1.0},
            {"name": "crossref", "weight": 1.0},
            {"name": "openalex", "weight": 1.0},
            {"name": "semantic_scholar", "weight": 1.0},
            {"name": "google_scholar", "weight": 0.8},
            {"name": "cnki", "weight": 0.7},
            {"name": "cscd", "weight": 0.6},
            {"name": "wanfang", "weight": 0.5},
            {"name": "web_of_science", "weight": 0.9},
            {"name": "europe_pmc", "weight": 1.0},
            {"name": "arxiv", "weight": 0.3},
        ]

    # ── EventBus handler ──

    async def on_event(self, event: SystemEvent) -> SystemEvent:
        """Handle routed event from OriginKernel.

        WHEN event.topic == 'vertex.V0' THEN run parallel search.
        WHEN query type is 'search' THEN call expand().
        ELSE call supply().
        """
        query = event.payload.get("query", "")
        search_type = event.payload.get("search_type", "search")

        if search_type == "search":
            result = await self._do_parallel_search(query, event.trace_id)
        else:
            result = await self._do_supply({"query": query, "requester": event.source})

        event.payload["result"] = result
        event.payload["confidence"] = "LOW"  # R4: Yang output is LOW confidence
        return event

    # ── YangPole abstract implementations ──

    async def expand(self, query, radius) -> Any:
        """Expand search across all engines within radius.

        precondition: radius > 0 AND radius <= MAX_EXPANSION_RADIUS
        postcondition: len(result) > 0 OR result.exhausted == True
        """
        return await self._do_parallel_search(
            query.query if hasattr(query, "query") else str(query),
            trace_id="",
        )

    async def supply(self, context) -> Any:
        """Supply knowledge to requester.

        precondition: context.requester is not None
        postcondition: result.source_diversity >= MIN_SOURCE_DIVERSITY
        """
        return await self._do_supply(context)

    async def generate_hypotheses(self, observations) -> Any:
        """Generate hypotheses from observations.

        postcondition: all(h.plausibility > 0 for h in result)
        """
        return {"hypotheses": [], "plausibility": []}

    # ── Internal ──

    async def _do_parallel_search(self, query: str, trace_id: str) -> Dict[str, Any]:
        """Parallel search across all 11 engines.

        FOR EACH engine: query engine with timeout=30s.
        MERGE results with RRF fusion.
        IF recall >= 0.98 THEN record HIGH_RECALL karma deed.
        RETURN merged CandidateSet.
        """
        engines_to_use = self._engines[:11]  # all 11 engines

        # In production: asyncio.gather across gRPC calls to each engine
        # For now: stub that simulates parallel search
        results = []
        for eng in engines_to_use:
            # Simulated engine result
            results.append({
                "engine": eng["name"],
                "weight": eng["weight"],
                "items": [],
                "status": "ok",
            })

        merged = {
            "query": query,
            "trace_id": trace_id,
            "total_engines": len(engines_to_use),
            "successful_engines": len(results),
            "items": [],
            "merged_by": "RRF_fusion",
            "recall_estimate": self._recall_rate,
            "source_diversity": len({r["engine"] for r in results}),
        }

        # IF recall >= 0.98 THEN record good deed
        if self._recall_rate >= 0.98 and self.karma_engine:
            await self.karma_engine.record_deed(
                "HIGH_RECALL", +3,
                {"query": query[:100], "recall": self._recall_rate},
            )

        return merged

    async def _do_supply(self, context: Any) -> Dict[str, Any]:
        """Supply knowledge — implement with actual search logic."""
        return {
            "source_diversity": 3,
            "unique_sources": 3,
            "items": [],
        }

    # ── Health ──

    async def health_check(self) -> HealthReport:
        report = await super().health_check()
        report.karma_score = self.karma_engine.karma_score if self.karma_engine else 50.0
        report.current_realm = (
            self.karma_engine.current_realm.value
            if self.karma_engine and hasattr(self.karma_engine.current_realm, "value")
            else "HUMAN"
        )
        return report

    async def evolve(self) -> EvolutionDelta:
        return EvolutionDelta(vertex_id="V0", reason="no_change", success=True)
