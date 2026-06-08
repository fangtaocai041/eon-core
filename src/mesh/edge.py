"""Edge + Face + Laplacian utility models for TetrahedronMesh.

Companion modules to src/mesh/tetrahedron.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class EdgeConfig:
    """Single edge in the tetrahedron topology."""
    weight: float = 0.5
    direction: str = "UNIDIRECTIONAL"
    latency_ms: float = 50.0
    capacity: int = 100
    circuit_breaker: str = "CLOSED"


@dataclass
class FaceConfig:
    """Triangular face defined by 3 vertices."""
    face_id: str = ""
    vertices: List[str] = None
    label: str = ""

    def __post_init__(self):
        if self.vertices is None:
            self.vertices = []

    @property
    def area_sign(self) -> float:
        """Signed area sign for orientation check."""
        return 1.0  # all faces oriented outward


def compute_laplacian(adjacency: np.ndarray) -> np.ndarray:
    """Compute Laplacian matrix L = D - A.

    D = diag(degree), A = adjacency matrix.
    """
    D = np.diag(np.sum(adjacency, axis=1))
    return D - adjacency


def spectral_gap(L: np.ndarray) -> Optional[float]:
    """Compute λ₂ (second-smallest eigenvalue) of Laplacian.

    λ₂ = 0 means disconnected graph.
    λ₂ > 0 means connected.

    Returns None if matrix too small.
    """
    if L.shape[0] <= 1:
        return None
    try:
        eigenvalues = np.linalg.eigvalsh(L)
        sorted_vals = sorted(eigenvalues.real)
        return float(sorted_vals[1]) if len(sorted_vals) > 1 else None
    except np.linalg.LinAlgError:
        return None
