"""EmergenceBridge — 感知涌现闭环: 物理世界 → 涌现检测 → 进化适应.

三体智子的感知方式:
  感知触角收集物理世界信号 → 涌现引擎检测模式 → 进化引擎调整参数

闭环:
  PerceptionBridge.tendrils
      ↓ (raw signals)
  EmergenceMonitor
      ↓ (D₀→D₁→D₂→D₃ 维度跃迁检测)
  EvolutionExecutor
      ↓ (参数自适应)
  Coordinator / CircuitBreaker
      ↓ (行为变更)
  Physical world impact

Usage:
    from eon_core_shared.emergence_bridge import EmergenceBridge

    bridge = EmergenceBridge()
    bridge.start(interval_sec=300)  # 5分钟扫描一次
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmergenceEvent:
    """一次涌现事件的记录."""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""          # "phase_transition" | "anomaly" | "theory_match"
    dimensional_level: int = 0    # D₀=0, D₁=1, D₂=2, D₃=3
    source: str = ""              # Which tendril triggered it
    summary: str = ""             # Human-readable
    evolution_action: str = ""    # What evolution did
    confidence: float = 0.0


class EmergenceBridge:
    """感知 → 涌现 → 进化 闭环控制器.

    定期从 PerceptionBridge 读取感知读数,
    送入 EmergenceMonitor 检测涌现模式,
    触发 EvolutionExecutor 进行参数自适应.
    """

    def __init__(self,
                 data_dir: str = "data/emergence",
                 log_path: str = "data/emergence/emergence_events.jsonl"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        # Cached imports (lazy)
        self._perception = None
        self._monitor = None
        self._engine = None
        self._evolution = None

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._events: List[EmergenceEvent] = []
        self._last_scan_time: float = 0

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, interval_sec: float = 300.0,
              emergence_threshold_sigma: float = 3.0) -> None:
        """Start background emergence monitoring.

        Args:
            interval_sec: Polling interval (default 5 min).
            emergence_threshold_sigma: Z-score threshold for emergence.
        """
        if self._running:
            return

        self._lazy_init(emergence_threshold_sigma)
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_sec,),
            daemon=True,
            name="emergence-bridge"
        )
        self._thread.start()
        logger.info(f"Emergence bridge started (interval={interval_sec}s)")

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def scan_once(self, force: bool = False) -> List[EmergenceEvent]:
        """Execute one emergence scan cycle.

        Args:
            force: Skip cooldown check.

        Returns:
            List of emergence events detected.
        """
        if not force and time.time() - self._last_scan_time < 60:
            return []

        self._lazy_init()
        self._last_scan_time = time.time()
        events: List[EmergenceEvent] = []

        # 1. Get perception readings
        readings = self._get_perception_readings()

        # 2. Feed into emergence monitor
        for reading in readings:
            metric_name = f"{reading.get('tendril', 'unknown')}_signals"
            metric_value = len(reading.get('signals', []))
            confidence = reading.get('confidence', 0.0)

            # Record in emergence monitor
            self._monitor.record(metric_name, metric_value,
                                 self._DimensionalLevel.D1)
            if confidence > 0.7:
                self._monitor.record(f"{metric_name}_high_conf", metric_value,
                                     self._DimensionalLevel.D2)

            # Check for D₂→D₃ phase transition (≥10 signals with high confidence)
            if metric_value >= 10 and confidence >= 0.7:
                event = EmergenceEvent(
                    event_type="phase_transition",
                    dimensional_level=3,
                    source=reading.get('tendril', ''),
                    summary=f"D2->D3: {metric_value} signals in {reading.get('tendril', '?')}",
                    confidence=confidence,
                )

                # Trigger evolution adaptation
                if self._evolution:
                    try:
                        metrics = {
                            "emergence_signals": metric_value,
                            "sources": len(readings),
                        }
                        actions = self._evolution.evaluate_and_adapt(metrics)
                        if actions:
                            event.evolution_action = "; ".join(
                                f"{a.param}:{a.old_value}->{a.new_value}"
                                for a in actions
                            )
                            logger.info(f"Evolution adapted due to emergence: {event.summary}")
                    except Exception as e:
                        logger.debug(f"Evolution adaptation skipped: {e}")

                events.append(event)

        # 3. Self-organizing domain discovery
        domains = self._run_domain_discovery(readings)

        # 4. Log and store
        for ev in events:
            self._events.append(ev)
            self._log_event(ev)

        return events

    def get_events(self, limit: int = 20) -> List[dict]:
        """Return recent emergence events."""
        return [{
            "timestamp": ev.timestamp,
            "datetime": datetime.fromtimestamp(ev.timestamp).isoformat(),
            "type": ev.event_type,
            "dimension": f"D{ev.dimensional_level}",
            "source": ev.source,
            "summary": ev.summary,
            "evolution": ev.evolution_action,
            "confidence": ev.confidence,
        } for ev in self._events[-limit:]]

    def get_stats(self) -> dict:
        """Return monitoring statistics."""
        return {
            "running": self._running,
            "total_events": len(self._events),
            "last_scan": self._last_scan_time,
            "perception_loaded": self._perception is not None,
            "monitor_loaded": self._monitor is not None,
            "evolution_loaded": self._evolution is not None,
        }

    # ── Internal ──────────────────────────────────────────────────

    def _lazy_init(self, emergence_threshold_sigma: float = 3.0) -> None:
        """Lazy-import all dependencies."""
        if self._monitor is not None:
            return

        eon_shared = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..',
                         'eon-core', 'src', 'shared')
        )
        eon_src = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..',
                         'eon-core', 'src')
        )
        cog_src = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..',
                         'cognitive-search-engine', 'src')
        )

        for p in [eon_shared, eon_src, cog_src]:
            import sys as _s
            if p not in _s.path:
                _s.path.insert(0, p)

        # Perception bridge (from cognitive-search-engine)
        try:
            from perception_bridge import PerceptionBridge
            self._perception = PerceptionBridge(
                data_dir=str(self._data_dir / "perception")
            )
        except ImportError:
            logger.debug("PerceptionBridge not available")

        # Emergence monitor
        try:
            from unified_emergence import EmergenceMonitor, DimensionalLevel
            self._monitor = EmergenceMonitor(
                emergence_threshold_sigma=emergence_threshold_sigma,
                min_sources=3,
            )
            self._DimensionalLevel = DimensionalLevel
        except ImportError:
            logger.debug("EmergenceMonitor not available")

        # Evolution executor
        try:
            from evolution import EvolutionExecutor
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..',
                'config', 'evolution.yaml'
            )
            if os.path.exists(config_path):
                self._evolution = EvolutionExecutor(config_path)
        except ImportError:
            logger.debug("EvolutionExecutor not available")

    def _get_perception_readings(self) -> List[dict]:
        """Get latest readings from perception bridge."""
        if self._perception is None:
            return []

        try:
            report = self._perception.scan_all()
            readings = []
            for name, reading in report.tendrils.items():
                readings.append({
                    "tendril": name,
                    "signals": reading.signals,
                    "confidence": reading.confidence,
                    "alert_level": reading.alert_level,
                    "summary": reading.summary,
                })
            return readings
        except Exception as e:
            logger.debug(f"Perception scan failed: {e}")
            return []

    def _run_domain_discovery(self, readings: List[dict]) -> List[str]:
        """Run self-organizing domain discovery on perception data."""
        if not readings:
            return []

        suggestions = []
        for reading in readings:
            if reading.get("signals") and reading.get("confidence", 0) > 0.5:
                for sig in reading["signals"][:3]:
                    topic = sig.split("]")[-1].strip() if "]" in sig else sig
                    suggestions.append(topic)

        return suggestions[:10]

    def _monitor_loop(self, interval_sec: float) -> None:
        """Background monitoring thread."""
        while self._running:
            try:
                events = self.scan_once()
                if events:
                    logger.info(f"Emergence: {len(events)} events detected")
                time.sleep(interval_sec)
            except Exception:
                time.sleep(interval_sec)

    def _log_event(self, event: EmergenceEvent) -> None:
        """Persist emergence event to JSONL."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": event.timestamp,
                    "datetime": datetime.fromtimestamp(event.timestamp).isoformat(),
                    "type": event.event_type,
                    "dimension": f"D{event.dimensional_level}",
                    "source": event.source,
                    "summary": event.summary,
                    "evolution": event.evolution_action,
                    "confidence": event.confidence,
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass
