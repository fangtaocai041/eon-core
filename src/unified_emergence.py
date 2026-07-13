"""unified_emergence - re-export shim (split into 4 modules)."""
from __future__ import annotations
from .emergence_types import EmergenceType, DimensionalLevel, EmergenceSignal, DetectionResult, MetricTracker
from .emergence_monitor import EmergenceMonitor, DimensionalEmergenceMonitor, _deduplicate_changes
from .emergence_engine import EmergenceEngine
from .emerge_domains import record_search_result, emerge_domains
