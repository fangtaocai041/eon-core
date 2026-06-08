"""tu_earth (🪨 土) — NourishmentMonitor.

Attached to: V0 (SupplyVertex — fish)
Metrics:
  - supply_freshness: ratio of new vs cached results
  - knowledge_duplication: duplicate rate across sources
  - source_diversity_index: Shannon diversity of source usage
"""

from __future__ import annotations

from typing import Any, Dict


class NourishmentMonitor:
    """Monitor knowledge supply quality for EARTH element.

    Attached to V0 (SupplyVertex) — tracks information nourishment.
    """

    def __init__(self) -> None:
        self.supply_freshness: float = 0.75
        self.knowledge_duplication: float = 0.30
        self.source_diversity_index: float = 2.1  # Shannon index

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current nourishment metrics."""
        return {
            "supply_freshness": self.supply_freshness,
            "knowledge_duplication": self.knowledge_duplication,
            "source_diversity_index": self.source_diversity_index,
        }

    async def receive_sheng(self, source: str, data: Dict[str, Any]) -> None:
        """Receive sheng from FIRE (throughput → supply quality)."""
        throughput = data.get("event_throughput", 10.0)
        if throughput > 20:
            self.knowledge_duplication *= 0.95  # reduce dup with higher throughput

    async def observe(self, **kwargs) -> None:
        """Update metrics from external observation."""
        if "freshness" in kwargs:
            self.supply_freshness = kwargs["freshness"]
