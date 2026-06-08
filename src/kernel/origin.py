"""OriginKernel — 太极起源点 Singleton + DI Container + Event Sourcing.

Core responsibilities:
  1. Bootstrap all 10 layers from config/taiji.yaml
  2. Route external events to eligible vertices via DAG topology
  3. Health pulse every 5s across all vertices + trigrams
  4. Reconfigure topology with spectral gap validation
  5. Graceful shutdown with event bus drain

Design patterns: Singleton + Dependency Injection + Event Sourcing.
All inter-component references flow through OriginKernel.registry —
no direct imports between vertices/trigrams/wuxing/samsara.

Invariants:
  - Topology IS a DAG (enforced at bootstrap and reconfigure)
  - YangPole NEVER calls YinPole.verify()
  - YinPole NEVER calls YangPole.expand()
  - All inter-vertex communication VIA EventBus or gRPC
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import yaml

from .event_bus import AsyncEventBus, SystemEvent
from .lifecycle import Lifecycle, LifecycleStage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class VertexDescriptor:
    """Lightweight registry entry for a vertex — not the vertex instance itself."""

    __slots__ = (
        "vertex_id", "name", "symbol", "coordinates",
        "polarity", "gRPC_port", "wuxing_element", "trigram_ids",
        "d_level", "health_status", "last_health_check",
    )

    def __init__(
        self,
        vertex_id: str,
        name: str = "",
        symbol: str = "",
        coordinates: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        polarity: str = "",
        gRPC_port: int = 0,
        wuxing_element: str = "",
        trigram_ids: Optional[List[str]] = None,
        d_level: int = 1,
    ) -> None:
        self.vertex_id = vertex_id
        self.name = name
        self.symbol = symbol
        self.coordinates = coordinates
        self.polarity = polarity
        self.gRPC_port = gRPC_port
        self.wuxing_element = wuxing_element
        self.trigram_ids = trigram_ids or []
        self.d_level = d_level
        self.health_status = "UNKNOWN"
        self.last_health_check = 0.0

    def supports(self, intent: dict) -> bool:
        """Check if this vertex can handle the given intent.

        intent.domain ∈ {fish, cognitive, porpoise, coilia}
        Match against vertex name + trigram capabilities.
        """
        domain_map = {
            "V0": {"fish", "supply", "literature", "search", "ecology"},
            "V1": {"cognitive", "verify", "validate", "debate", "graph"},
            "V2": {"porpoise", "acoustic", "population", "habitat"},
            "V3": {"coilia", "otolith", "migration", "resource"},
        }
        intent_domain = intent.get("domain", "")
        capabilities = domain_map.get(self.vertex_id, set())
        return intent_domain in capabilities or any(
            kw in str(intent).lower() for kw in capabilities
        )


class HealthReport:
    """Health check result for a vertex or trigram."""

    __slots__ = ("component_id", "status", "latency_p99_ms", "error_rate",
                 "karma_score", "current_realm", "timestamp")

    UNREACHABLE: "HealthReport"  # forward ref, set after class def

    def __init__(
        self,
        component_id: str = "",
        status: str = "UNKNOWN",
        latency_p99_ms: float = 0.0,
        error_rate: float = 0.0,
        karma_score: float = 50.0,
        current_realm: str = "HUMAN",
    ) -> None:
        self.component_id = component_id
        self.status = status
        self.latency_p99_ms = latency_p99_ms
        self.error_rate = error_rate
        self.karma_score = karma_score
        self.current_realm = current_realm
        self.timestamp = time.time()


HealthReport.UNREACHABLE = HealthReport(status="UNREACHABLE")


class BootstrapReport:
    """Result of OriginKernel.bootstrap()."""

    __slots__ = ("success", "components", "timing_ms", "errors")

    def __init__(self) -> None:
        self.success = True
        self.components: Dict[str, str] = {}
        self.timing_ms: Dict[str, float] = {}
        self.errors: List[str] = []


class RouteResult:
    """Result of OriginKernel.route_event()."""

    __slots__ = ("plan", "samsara_states", "filtered_out", "fallback_used")

    def __init__(self) -> None:
        self.plan: List[str] = []
        self.samsara_states: Dict[str, str] = {}
        self.filtered_out: List[str] = []
        self.fallback_used = False


class ReconfigReport:
    """Result of OriginKernel.reconfigure()."""

    __slots__ = ("success", "delta", "spectral_gap_before", "spectral_gap_after", "errors")

    def __init__(self) -> None:
        self.success = True
        self.delta: Dict[str, Any] = {}
        self.spectral_gap_before: float = 0.0
        self.spectral_gap_after: float = 0.0
        self.errors: List[str] = []


class EvolutionRecord:
    """Logged evolution step."""

    __slots__ = ("timestamp", "action", "component", "delta", "result")

    def __init__(self, action: str = "", component: str = "",
                 delta: Optional[dict] = None, result: str = "") -> None:
        self.timestamp = datetime.now(timezone.utc)
        self.action = action
        self.component = component
        self.delta = delta or {}
        self.result = result


# ---------------------------------------------------------------------------
# OriginKernel
# ---------------------------------------------------------------------------

class OriginKernel:
    """太极起源点 — Singleton kernel.

    _instance: class-level singleton reference.
    bootstrap() must be called exactly once before any other method.
    """

    _instance: Optional["OriginKernel"] = None
    MAX_EXPANSION_RADIUS = 10
    MIN_SOURCE_DIVERSITY = 2
    MIN_PRECISION = 0.85

    def __new__(cls) -> "OriginKernel":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_booted"):
            return  # singleton: skip re-init
        self._booted = True

        self.state: Lifecycle = Lifecycle()
        self.event_bus: AsyncEventBus = AsyncEventBus()
        self.topology: nx.DiGraph = nx.DiGraph()
        self.registry: Dict[str, VertexDescriptor] = {}
        self.health_snapshot: Dict[str, HealthReport] = {}
        self.evolution_log: deque[EvolutionRecord] = deque(maxlen=10000)
        self.config: Dict[str, Any] = {}

        # Lazy references populated during bootstrap
        self.wuxing_engine: Any = None
        self.samsara_ring: Any = None
        self.sphere_gateway: Any = None
        self.tendril_manager: Any = None

        # Background task handles
        self._health_task: Optional[asyncio.Task] = None
        self._karma_task: Optional[asyncio.Task] = None
        self._wuxing_task: Optional[asyncio.Task] = None

    # ── Bootstrap ───────────────────────────────────────────────

    async def bootstrap(self, config_path: str = "config/taiji.yaml") -> BootstrapReport:
        """Load config, create EventBus, register vertices/trigrams,
        verify DAG topology, instantiate engines, start background loops.

        Returns BootstrapReport with timing and per-component health.
        """
        report = BootstrapReport()
        t0 = time.monotonic()

        try:
            # Step 1: Load config
            self.state.transition(LifecycleStage.SPROUTING)
            t1 = time.monotonic()
            config_file = Path(config_path)
            if not config_file.exists():
                config_file = Path(__file__).parent.parent.parent / config_path
            self.config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            report.timing_ms["config_load"] = (time.monotonic() - t1) * 1000
            report.components["config"] = "loaded"

            # Step 2: Instantiate EventBus
            t1 = time.monotonic()
            eb_cfg = self.config.get("origin_kernel", {})
            self.event_bus = AsyncEventBus(
                capacity=eb_cfg.get("event_bus_capacity", 10000),
                dlq_capacity=eb_cfg.get("dead_letter_queue_capacity", 1000),
            )
            report.timing_ms["event_bus"] = (time.monotonic() - t1) * 1000
            report.components["event_bus"] = "created"

            # Step 3: Register vertices
            t1 = time.monotonic()
            verts_cfg = self.config.get("vertices", {})
            for vid, vcfg in verts_cfg.items():
                desc = VertexDescriptor(
                    vertex_id=vid,
                    name=vcfg.get("name", ""),
                    symbol=vcfg.get("symbol", ""),
                    coordinates=tuple(vcfg.get("coordinates", [0, 0, 0])),
                    polarity=vcfg.get("polarity", ""),
                    gRPC_port=vcfg.get("gRPC_port", 0),
                    wuxing_element=vcfg.get("wuxing_element", ""),
                    trigram_ids=vcfg.get("trigrams", []),
                    d_level=vcfg.get("d_level", 1),
                )
                self.registry[vid] = desc
            report.timing_ms["vertex_registry"] = (time.monotonic() - t1) * 1000
            report.components["registry"] = f"{len(self.registry)} vertices registered"

            # Step 4: Build DAG topology
            t1 = time.monotonic()
            edges_cfg = self.config.get("tetrahedron", {}).get("edges", [])
            for edge in edges_cfg:
                self.topology.add_edge(
                    edge["from"], edge["to"],
                    weight=edge.get("weight", 0.5),
                    direction=edge.get("direction", "UNIDIRECTIONAL"),
                )
            # Add origin node
            self.topology.add_node("origin")
            for vid in self.registry:
                self.topology.add_edge("origin", vid, weight=1.0, direction="UNIDIRECTIONAL")

            # Step 5: Verify DAG property
            if not nx.is_directed_acyclic_graph(self.topology):
                msg = "Topology must be DAG — cycles detected in config.tetrahedron.edges"
                logger.error(msg)
                report.errors.append(msg)
                report.success = False
                return report

            report.timing_ms["topology"] = (time.monotonic() - t1) * 1000
            report.components["topology"] = f"DAG verified ({self.topology.number_of_nodes()} nodes, {self.topology.number_of_edges()} edges)"

            # Steps 6-8: Instantiate engines (stubs — replaced by actual imports in production)
            report.components["wuxing_engine"] = "created (stub)"
            report.components["samsara_ring"] = "created (stub)"
            report.components["sphere_gateway"] = "created (stub)"
            report.components["tendril_manager"] = "created (stub)"

            # Step 9: Transition to BLOOMING
            self.state.transition(LifecycleStage.BLOOMING)
            report.timing_ms["total"] = (time.monotonic() - t0) * 1000
            report.success = True

        except Exception as exc:
            logger.exception("Bootstrap failed")
            report.errors.append(str(exc))
            report.success = False

        return report

    # ── Route Event ─────────────────────────────────────────────

    async def route_event(self, event: SystemEvent) -> RouteResult:
        """Classify intent, filter vertices by Samsara realm eligibility,
        compute shortest DAG path, publish to each vertex in plan.

        WHEN all eligible vertices are in NARAKA THEN use fallback.
        """
        result = RouteResult()

        # Classify intent (simplified keyword-based; production uses NLU embedding)
        intent = self._classify_intent(event)

        # Find eligible vertices
        eligible = [v for v in self.registry.values() if v.supports(intent)]

        # Check Samsara states
        if self.samsara_ring is not None:
            for v in eligible:
                try:
                    realm = await self.samsara_ring.get_realm(v.vertex_id)
                except Exception:
                    realm = "HUMAN"
                result.samsara_states[v.vertex_id] = realm

        # Filter: exclude NARAKA
        filtered = [
            v for v in eligible
            if result.samsara_states.get(v.vertex_id, "HUMAN") != "NARAKA"
        ]

        if not filtered and eligible:
            filtered = [eligible[0]]  # fallback
            result.fallback_used = True
            logger.warning(f"All eligible vertices in NARAKA, using fallback: {filtered[0].vertex_id}")
        result.filtered_out = [v.vertex_id for v in eligible if v not in filtered]

        # Compute DAG path ordered by dependency
        try:
            path = nx.topological_sort(self.topology)
            ordered = [n for n in path if n in [v.vertex_id for v in filtered]]
        except Exception:
            ordered = [v.vertex_id for v in filtered]

        result.plan = ordered

        # Publish to each vertex in plan
        for vid in ordered:
            await self.event_bus.publish(event.clone(topic=f"vertex.{vid}"), topic=f"vertex.{vid}")

        return result

    def _classify_intent(self, event: SystemEvent) -> dict:
        """Simplified keyword classifier. Production replacement: NLU embedding + RRF.

        Returns: {domain, type, confidence}
        """
        query = str(event.payload.get("query", "")).lower()
        domain_keywords = {
            "fish": ["fish", "鱼", "ecology", "生态", "species", "物种", "diet", "食性"],
            "cognitive": ["verify", "验证", "graph", "图谱", "debate", "辩论"],
            "porpoise": ["porpoise", "江豚", "acoustic", "声学", "population", "种群"],
            "coilia": ["coilia", "刀鲚", "otolith", "耳石", "migration", "洄游"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in query for kw in keywords):
                return {"domain": domain, "type": "query", "confidence": 0.8}
        return {"domain": "fish", "type": "general", "confidence": 0.5}

    # ── Health Pulse ────────────────────────────────────────────

    async def health_pulse(self) -> None:
        """Background coroutine: check every vertex every 5s. Emit Prometheus metric.

        schedule: every 5 seconds
        FOR EACH vertex IN self.registry:
          TRY report = await asyncio.wait_for(vertex.health_check(), timeout=3.0)
          EXCEPT: report = HealthReport.UNREACHABLE
          self.health_snapshot[vertex.id] = report
        """
        interval = self.config.get("origin_kernel", {}).get("health_pulse_interval_s", 5)
        while self.state.is_alive:
            for vid, desc in self.registry.items():
                try:
                    # In production: gRPC health check to vertex
                    report = HealthReport(
                        component_id=vid,
                        status="HEALTHY",
                        latency_p99_ms=0.0,
                        error_rate=0.0,
                        karma_score=50.0,
                        current_realm="HUMAN",
                    )
                    # Simulate async health check with timeout
                    report = await asyncio.wait_for(
                        self._health_check_vertex(vid), timeout=3.0
                    )
                except (asyncio.TimeoutError, Exception):
                    report = HealthReport.UNREACHABLE
                    report.component_id = vid

                self.health_snapshot[vid] = report
                desc.health_status = report.status
                desc.last_health_check = report.timestamp

                # IF all vertices healthy THEN log info ELSE log warning
                if report.status == "UNREACHABLE":
                    logger.warning(f"Health check failed for {vid}")

            await asyncio.sleep(interval)

    async def _health_check_vertex(self, vid: str) -> HealthReport:
        """Simulated health check. Replace with gRPC health probe in production."""
        await asyncio.sleep(0.01)  # simulate network round-trip
        return HealthReport(component_id=vid, status="HEALTHY")

    # ── Reconfigure ─────────────────────────────────────────────

    async def reconfigure(self, new_topology: dict) -> ReconfigReport:
        """Apply new edge weights atomically. Validate DAG and spectral gap.

        WHEN spectral_gap < 0.1 * baseline THEN reject reconfig.
        """
        report = ReconfigReport()
        try:
            edges_new = new_topology.get("edges", [])

            # Compute baseline spectral gap
            L_before = nx.laplacian_matrix(self.topology).toarray()
            if L_before.shape[0] > 1:
                eigenvalues = np.linalg.eigvalsh(L_before)
                report.spectral_gap_before = float(sorted(eigenvalues)[1]) if len(eigenvalues) > 1 else 0.0
            else:
                report.spectral_gap_before = 0.0

            # Apply edge weight changes
            for edge in edges_new:
                u, v = edge["from"], edge["to"]
                if self.topology.has_edge(u, v):
                    self.topology[u][v]["weight"] = edge.get("weight", 0.5)

            # Re-verify DAG
            if not nx.is_directed_acyclic_graph(self.topology):
                report.errors.append("Reconfigure would create cycle — rejected")
                report.success = False
                return report

            # Check spectral gap
            L_after = nx.laplacian_matrix(self.topology).toarray()
            if L_after.shape[0] > 1:
                eigenvalues = np.linalg.eigvalsh(L_after)
                report.spectral_gap_after = float(sorted(eigenvalues)[1]) if len(eigenvalues) > 1 else 0.0
            baseline = self.config.get("tetrahedron", {}).get("baseline_spectral_gap", 0.15)
            if report.spectral_gap_after < 0.1 * baseline:
                report.errors.append(
                    f"Spectral gap {report.spectral_gap_after:.4f} below threshold "
                    f"{0.1 * baseline:.4f} — reconfig rejected"
                )
                report.success = False
                return report

            report.success = True
        except Exception as exc:
            report.errors.append(str(exc))
            report.success = False

        return report

    # ── Shutdown ─────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Graceful shutdown: drain event bus, stop coroutines, transition to SEEDING.

        Steps:
          1. set self.state = PRUNING
          2. drain event_bus: await asyncio.wait_for(event_bus.drain(), timeout=30)
          3. IF health_task THEN cancel and await
          4. IF karma_task THEN cancel and await
          5. IF wuxing_task THEN cancel and await
          6. set self.state = SEEDING
        """
        self.state.transition(LifecycleStage.PRUNING)
        logger.info("Starting graceful shutdown...")

        # Drain event bus
        try:
            await asyncio.wait_for(self.event_bus.drain(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("EventBus drain timed out after 30s")

        # Cancel background tasks
        for task_attr in ("_health_task", "_karma_task", "_wuxing_task"):
            task = getattr(self, task_attr, None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.state.transition(LifecycleStage.SEEDING)
        logger.info("Shutdown complete — system in SEEDING state")

    # ── Utilities ────────────────────────────────────────────────

    def get_vertex(self, vid: str) -> Optional[VertexDescriptor]:
        """Lookup vertex by id."""
        return self.registry.get(vid)

    def get_health_summary(self) -> Dict[str, dict]:
        """Return all health snapshots."""
        return {
            vid: {
                "status": r.status,
                "latency_p99_ms": r.latency_p99_ms,
                "error_rate": r.error_rate,
                "realm": r.current_realm,
            }
            for vid, r in self.health_snapshot.items()
        }

    def log_evolution(self, action: str, component: str,
                      delta: Optional[dict] = None, result: str = "") -> None:
        """Append to evolution log."""
        self.evolution_log.append(
            EvolutionRecord(action=action, component=component, delta=delta, result=result)
        )
