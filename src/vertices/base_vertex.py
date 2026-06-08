"""BaseVertex — 四象顶点抽象基类.

Each vertex:
  - Has coordinates in tetrahedron 3D space
  - Owns one YangPole and one YinPole
  - Hosts 0-2 Trigrams
  - Has an embedded KarmaEngine
  - Is assigned one WuXing element
  - Communicates via EventBus or gRPC (no direct vertex-to-vertex import)

Geometry: tetrahedron vertices at (±1, ±1, ±1) with sign pattern:
  V0: ( 1,  1,  1) — SupplyVertex
  V1: ( 1, -1, -1) — VerifyVertex
  V2: (-1,  1, -1) — DomainVertexP1
  V3: (-1, -1,  1) — DomainVertexP2
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class EdgeConfig:
    """Directed edge between vertices."""
    weight: float = 0.5
    direction: str = "UNIDIRECTIONAL"  # UNIDIRECTIONAL | BIDIRECTIONAL
    latency_ms: float = 50.0
    capacity: int = 100
    circuit_breaker: str = "CLOSED"  # CLOSED | OPEN | HALF_OPEN


@dataclass
class HealthReport:
    """Vertex health report — refreshed every 5s by health_pulse."""
    status: str = "UNKNOWN"
    component_id: str = ""
    latency_p99_ms: float = 0.0
    error_rate: float = 0.0
    karma_score: float = 50.0
    current_realm: str = "HUMAN"
    timestamp: float = field(default_factory=time.time)


class BaseVertex(ABC):
    """Abstract vertex in the tetrahedron mesh.

    Each vertex implements:
      - on_event(event) → SystemEvent   (handle incoming EventBus message)
      - health_check() → HealthReport   (self + all trigrams)
      - evolve() → EvolutionDelta       (self-modification)
    """

    def __init__(
        self,
        vertex_id: str,
        coordinates: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        yang_pole: Optional[Any] = None,
        yin_pole: Optional[Any] = None,
        wuxing_element: str = "",
    ) -> None:
        self.vertex_id: str = vertex_id
        self.coordinates: Tuple[float, float, float] = coordinates
        self.yang_pole: Any = yang_pole
        self.yin_pole: Any = yin_pole
        self.trigrams: List[Any] = []
        self.karma_engine: Any = None
        self.wuxing_element: str = wuxing_element
        self.health: HealthReport = HealthReport(component_id=vertex_id)
        self.connections: Dict[str, EdgeConfig] = {}

    # ── Abstract ──

    @abstractmethod
    async def on_event(self, event: Any) -> Any:
        """Handle an EventBus event routed to this vertex.

        IF yang event (search/expand/supply) THEN delegate to yang_pole.
        IF yin event (verify/contract) THEN delegate to yin_pole.
        RETURN processed SystemEvent.
        """
        ...

    @abstractmethod
    async def evolve(self) -> "EvolutionDelta":
        """Self-modify parameters. Called only in HUMAN realm."""
        ...

    # ── Concrete ──

    async def health_check(self) -> HealthReport:
        """Check self health + all trigram health.

        FOR EACH trigram: check health(); IF unreachable THEN status=UNREACHABLE.
        RETURN aggregated HealthReport.
        """
        all_healthy = True
        for tri in self.trigrams:
            try:
                tri_health = await tri.health()
                if tri_health.status == "UNREACHABLE":
                    all_healthy = False
            except Exception:
                all_healthy = False

        self.health.status = "HEALTHY" if all_healthy else "DEGRADED"
        self.health.timestamp = time.time()
        return self.health

    def distance_to(self, other: "BaseVertex") -> float:
        """Euclidean distance in tetrahedron 3D space."""
        return float(np.linalg.norm(
            np.array(self.coordinates) - np.array(other.coordinates)
        ))

    def register_trigram(self, trigram: Any) -> None:
        """Attach a trigram to this vertex. Max 2 per vertex."""
        if len(self.trigrams) >= 2:
            raise ValueError(f"Vertex {self.vertex_id} already has 2 trigrams")
        self.trigrams.append(trigram)
        trigram.parent_vertex = self

    def connect(self, target_id: str, edge: EdgeConfig) -> None:
        """Add a directed connection to another vertex."""
        self.connections[target_id] = edge

    def supports(self, intent: dict) -> bool:
        """Check if this vertex supports the given intent.

        Override in subclasses for domain-specific routing.
        """
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.vertex_id}) at {self.coordinates}>"


@dataclass
class EvolutionDelta:
    """Result of vertex.evolve()."""
    vertex_id: str = ""
    parameter_changes: Dict[str, float] = field(default_factory=dict)
    reason: str = ""
    success: bool = False
