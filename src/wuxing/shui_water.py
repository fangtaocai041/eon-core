"""shui_water (💧 水) — FlowAdaptor.

Attached to: V3 (DomainVertexP2 — coilia)
Metrics:
  - adaptation_speed_ms: time to adapt to new external data
  - external_event_response_time: latency from external event to system reaction
  - migration_pattern_detection_rate: novel patterns found / total patterns
"""

from __future__ import annotations

from typing import Any, Dict


class FlowAdaptor:
    """Adapt to external changes for WATER element.

    Attached to V3 (Coilia) — tracks fluid adaptation to environmental data.
    """

    def __init__(self) -> None:
        self.adaptation_speed_ms: float = 300.0
        self.external_event_response_time: float = 2.5  # seconds
        self.migration_pattern_detection_rate: float = 0.72

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current adaptation metrics."""
        return {
            "adaptation_speed_ms": self.adaptation_speed_ms,
            "external_event_response_time": self.external_event_response_time,
            "migration_pattern_detection_rate": self.migration_pattern_detection_rate,
        }

    async def receive_sheng(self, source: str, data: Dict[str, Any]) -> None:
        """Receive sheng from METAL (convergence → adaptation signal)."""
        stability = data.get("conclusion_stability", 0.5)
        if stability > 0.9:
            self.adaptation_speed_ms *= 0.9  # faster adaptation

    async def observe(self, **kwargs) -> None:
        """Update metrics from external observation."""
        if "adaptation" in kwargs:
            self.adaptation_speed_ms = kwargs["adaptation"]
