"""mu_wood (🪵 木) — GrowthMonitor.

Attached to: V1 (VerifyVertex — cognitive)
Metrics:
  - graph_node_growth_rate: new nodes per cycle
  - new_species_per_month: novel species discoveries
  - variant_coverage_pct: OCR variant coverage
"""

from __future__ import annotations

from typing import Any, Dict


class GrowthMonitor:
    """Monitor knowledge graph growth for WOOD element.

    Attached to V1 (VerifyVertex) — tracks cognitive expansion.
    """

    def __init__(self) -> None:
        self.graph_node_growth_rate: float = 1.0
        self.new_species_per_month: float = 3.0
        self.variant_coverage_pct: float = 0.92
        self._baseline_growth: float = 1.0

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current growth metrics."""
        return {
            "graph_node_growth_rate": self.graph_node_growth_rate,
            "new_species_per_month": self.new_species_per_month,
            "variant_coverage_pct": self.variant_coverage_pct,
            "growth_vs_baseline": self.graph_node_growth_rate / max(self._baseline_growth, 0.01),
        }

    async def receive_sheng(self, source: str, data: Dict[str, Any]) -> None:
        """Receive sheng from WATER (adaptation → growth trigger)."""
        adaptation_signal = data.get("adaptation_speed_ms", 0)
        if adaptation_signal > 0:
            self.graph_node_growth_rate *= 1.05  # +5% growth boost

    async def observe(self, **kwargs) -> None:
        """Update metrics from external observation."""
        if "graph_growth" in kwargs:
            self.graph_node_growth_rate = kwargs["graph_growth"]
