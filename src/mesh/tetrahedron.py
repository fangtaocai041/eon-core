"""TetrahedronMesh — 三角体网格拓扑分析.

4 vertices (V0, V1, V2, V3) forming a regular tetrahedron in 3D space.
OriginKernel sits at (0,0,0) — the centroid.

Key metrics:
  - Adjacency matrix A (4×4)
  - Degree matrix D (4×4 diagonal)
  - Laplacian L = D - A
  - Spectral gap λ₂: second-smallest eigenvalue of L
    → measures connectivity health: λ₂ ≥ 0.1 × baseline

Operations:
  - compute_centroid() → center of tetrahedron
  - shortest_path(v1, v2) → Dijkstra on weighted adjacency
  - spectral_gap() → λ₂
  - disturb_weights(chaos_factor, seed) → random edge weight perturbation
  - collapse_edge(v1, v2, reason) → circuit break an edge
  - expand_to_pentahedron(new_vertex) → grow from 4→5 vertices
  - is_healthy() → λ₂ ≥ 0.1 × baseline
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EdgeConfig:
    """Configuration for a single tetrahedron edge."""

    __slots__ = ("weight", "direction", "latency_ms", "capacity", "circuit_breaker")

    def __init__(
        self,
        weight: float = 0.5,
        direction: str = "UNIDIRECTIONAL",
        latency_ms: float = 50.0,
        capacity: int = 100,
    ) -> None:
        self.weight = max(0.0, min(1.0, weight))
        self.direction = direction
        self.latency_ms = latency_ms
        self.capacity = capacity
        self.circuit_breaker = "CLOSED"  # CLOSED | OPEN | HALF_OPEN


class FaceConfig:
    """Configuration for a tetrahedron triangular face."""

    __slots__ = ("face_id", "vertices", "label")

    def __init__(self, face_id: str, vertices: List[str], label: str = "") -> None:
        self.face_id = face_id
        self.vertices = vertices
        self.label = label


class TetrahedronMesh:
    """4-vertex tetrahedron topology with spectral analysis.

    Fields:
      vertices: Dict[str, BaseVertex] — {V0, V1, V2, V3}
      edges: Dict[Tuple[str,str], EdgeConfig] — 6 edges
      faces: Dict[str, FaceConfig] — 4 triangular faces
      A: 4×4 adjacency matrix (weighted)
      L: 4×4 Laplacian matrix L = D - A
      baseline_lambda2: spectral gap baseline
    """

    def __init__(self, origin: Any = None) -> None:
        self.vertices: Dict[str, Any] = {}
        self.origin = origin  # OriginKernel reference
        self.edges: Dict[Tuple[str, str], EdgeConfig] = {}
        self.faces: Dict[str, FaceConfig] = {}
        self._A: np.ndarray = np.zeros((4, 4))
        self._L: np.ndarray = np.zeros((4, 4))
        self.baseline_lambda2: float = 0.15

    # ── Matrix computation ──

    def _recompute_matrices(self) -> None:
        """Recompute A and L from current edge weights."""
        n = len(self.vertices)
        if n == 0:
            return

        idx_map = {vid: i for i, vid in enumerate(sorted(self.vertices.keys()))}
        self._A = np.zeros((n, n))
        for (u, v), edge in self.edges.items():
            if u in idx_map and v in idx_map:
                i, j = idx_map[u], idx_map[v]
                self._A[i, j] = edge.weight
                if edge.direction == "BIDIRECTIONAL":
                    self._A[j, i] = edge.weight

        D = np.diag(np.sum(self._A, axis=1))
        self._L = D - self._A

    # ── Geometry ──

    def compute_centroid(self) -> np.ndarray:
        """Centroid of all vertices.

        RETURN np.mean([v.coordinates for v in vertices], axis=0).
        """
        if not self.vertices:
            return np.zeros(3)
        coords = np.array([v.coordinates for v in self.vertices.values()])
        return np.mean(coords, axis=0)

    def shortest_path(self, v1: str, v2: str) -> List[str]:
        """Dijkstra shortest path on weighted adjacency matrix.

        IF no path exists THEN return empty list.
        """
        if v1 not in self.vertices or v2 not in self.vertices:
            return []

        n = len(self.vertices)
        idx_map = {vid: i for i, vid in enumerate(sorted(self.vertices.keys()))}
        rev_map = {i: vid for vid, i in idx_map.items()}

        # Dijkstra
        dist = {i: float("inf") for i in range(n)}
        prev: Dict[int, Optional[int]] = {i: None for i in range(n)}
        start = idx_map[v1]
        end = idx_map[v2]
        dist[start] = 0.0
        unvisited = set(range(n))

        while unvisited:
            u = min(unvisited, key=lambda x: dist[x])
            unvisited.remove(u)
            if u == end:
                break
            if dist[u] == float("inf"):
                break
            for v in range(n):
                if self._A[u, v] > 0:
                    alt = dist[u] + (1.0 / self._A[u, v])  # cost = 1/weight
                    if alt < dist[v]:
                        dist[v] = alt
                        prev[v] = u

        # Reconstruct path
        path: List[str] = []
        curr: Optional[int] = end
        while curr is not None:
            path.append(rev_map[curr])
            curr = prev[curr]
        path.reverse()
        return path if path[0] == v1 else []

    # ── Spectral analysis ──

    def spectral_gap(self) -> float:
        """Compute λ₂: second-smallest eigenvalue of Laplacian.

        Measures connectivity health.
        λ₂ = 0 means the graph is disconnected.
        λ₂ ≥ 0.1 × baseline means healthy connectivity.

        RETURN λ₂ or 0.0 if matrix is too small.
        """
        if self._L.shape[0] <= 1:
            return 0.0
        try:
            eigenvalues = np.linalg.eigvalsh(self._L)
            sorted_eigs = sorted(eigenvalues)
            return float(sorted_eigs[1]) if len(sorted_eigs) > 1 else 0.0
        except np.linalg.LinAlgError:
            logger.warning("Spectral gap computation failed — matrix may be singular")
            return 0.0

    # ── Dynamic operations ──

    async def disturb_weights(self, chaos_factor: float, seed: int = 42) -> None:
        """Randomly perturb edge weights within ±chaos_factor range.

        rng = np.random.RandomState(seed).
        FOR EACH edge:
          delta = rng.uniform(-chaos_factor, chaos_factor) * edge.weight.
          edge.weight = np.clip(edge.weight + delta, 0.05, 1.0).

        This tests robustness of routing under edge weight uncertainty.
        """
        rng = np.random.RandomState(seed)
        for edge in self.edges.values():
            delta = rng.uniform(-chaos_factor, chaos_factor) * edge.weight
            edge.weight = max(0.05, min(1.0, edge.weight + delta))
        self._recompute_matrices()

    async def collapse_edge(self, v1: str, v2: str, reason: str = "") -> None:
        """Circuit-break an edge.

        Sets circuit_breaker = OPEN, weight = 0.0.
        Recomputes Laplacian.
        Logs warning.

        Use case: vertex unreachable or excessive error rate on that edge.
        """
        key = (v1, v2)
        if key in self.edges:
            edge = self.edges[key]
            edge.circuit_breaker = "OPEN"
            edge.weight = 0.0
            self._recompute_matrices()
            logger.warning(f"Edge {v1}↔{v2} COLLAPSED: {reason}")

        # Also check reverse for bidirectional edges
        rev_key = (v2, v1)
        if rev_key in self.edges and self.edges[rev_key].direction == "BIDIRECTIONAL":
            self.edges[rev_key].circuit_breaker = "OPEN"
            self.edges[rev_key].weight = 0.0

    async def expand_to_pentahedron(self, new_vertex: Any, coords: np.ndarray) -> "TetrahedronMesh":
        """Expand from tetrahedron (4 vertices) to pentahedron (5+ vertices).

        precondition: len(self.vertices) == 4.
        Creates edges from all existing vertices to new vertex with weight=0.5.
        RETURNS self (mutated in place) for chaining.
        """
        if len(self.vertices) != 4:
            raise ValueError(f"Must have exactly 4 vertices to expand, got {len(self.vertices)}")

        vid = new_vertex.vertex_id
        for existing_vid in list(self.vertices.keys()):
            self.edges[(existing_vid, vid)] = EdgeConfig(weight=0.5, direction="UNIDIRECTIONAL")

        self.vertices[vid] = new_vertex
        self._recompute_matrices()
        return self

    # ── Health ──

    def is_healthy(self) -> bool:
        """Check connectivity health.

        RETURN spectral_gap() >= 0.1 * baseline_lambda2.
        """
        return self.spectral_gap() >= 0.1 * self.baseline_lambda2
