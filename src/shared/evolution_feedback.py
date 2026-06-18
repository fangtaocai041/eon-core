"""EvolutionFeedbackLoop — 连接熔断器 → 进化引擎的反馈回路.

当熔断器跳闸 (OPEN) 时自动触发进化引擎调整参数,
形成 thermostat-like 自修复闭环:

  Circuit trips (failure spike)
      ↓
  Evolution evaluates triggers
      ↓
  Parameters adapt (timeout↑, concurrency↓, etc.)
      ↓
  Circuit resets → test recovery
      ↓
  Success → parameters lock; Failure → further adaptation

Usage:
    from eon_core_shared.evolution_feedback import EvolutionFeedbackLoop

    loop = EvolutionFeedbackLoop()
    loop.attach("cognitive-search", cb, evolution_config="config/evolution.yaml")
    loop.start()  # background monitoring thread
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
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Check availability of EvolutionExecutor
try:
    import sys as _efs
    import os as _efo
    _e = _efo.path.normpath(_efo.path.join(_efo.path.dirname(__file__), '..', '..', '..', 'eon-core', 'src', 'shared'))
    if _e not in _efs.path:
        _efs.path.insert(0, _e)
    from evolution import EvolutionExecutor
    _HAVE_EVOLUTION = True
except ImportError:
    _HAVE_EVOLUTION = False


@dataclass
class FeedbackRule:
    """一条反馈规则: 熔断器条件 → 进化动作."""
    circuit_name: str                 # 熔断器名称
    trigger_on_state: str = "open"    # "open" | "half_open" | "threshold"
    min_failures: int = 3             # 最少失败次数才触发
    evolution_config: str = ""        # 进化引擎配置文件路径
    param_overrides: Dict[str, Any] = field(default_factory=dict)
    cooldown_sec: float = 120.0       # 同一规则冷却时间
    last_fired: float = 0.0

    def can_fire(self) -> bool:
        return time.time() - self.last_fired >= self.cooldown_sec


@dataclass
class AdaptationEvent:
    """一次进化适应事件的记录."""
    timestamp: float = field(default_factory=time.time)
    circuit_name: str = ""
    trigger: str = ""
    old_params: dict = field(default_factory=dict)
    new_params: dict = field(default_factory=dict)
    action: str = ""
    success: bool = False


class EvolutionFeedbackLoop:
    """熔断器 → 进化引擎 反馈闭环.

    自动检测熔断器状态变化, 触发进化引擎参数调整.
    每个熔断器独立跟踪, 冷却期内不重复触发.
    """

    def __init__(self, log_path: str = "data/evolution_feedback.jsonl"):
        self._rules: Dict[str, FeedbackRule] = {}
        self._events: list = []
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._checked_circuits: set = set()

    # ── Configuration ─────────────────────────────────────────────

    def attach(self, circuit_name: str,
               cb: Any,  # CircuitBreaker instance
               evolution_config: str = "",
               trigger_on_state: str = "open",
               min_failures: int = 3,
               cooldown_sec: float = 120.0) -> None:
        """Attach a circuit breaker to the feedback loop.

        Args:
            circuit_name: Name matching the circuit breaker.
            cb: CircuitBreaker instance (duck-typed, needs .state/.get_stats()).
            evolution_config: Path to evolution YAML config.
            trigger_on_state: "open" | "half_open".
            min_failures: Minimum failures to trigger.
            cooldown_sec: Seconds between repeated triggers.
        """
        rule = FeedbackRule(
            circuit_name=circuit_name,
            trigger_on_state=trigger_on_state,
            min_failures=min_failures,
            evolution_config=evolution_config,
            cooldown_sec=cooldown_sec,
        )
        self._rules[circuit_name] = rule
        logger.info(f"Feedback loop attached: {circuit_name} [trigger={trigger_on_state}]")

    def detach(self, circuit_name: str) -> None:
        """Remove a circuit from feedback monitoring."""
        self._rules.pop(circuit_name, None)

    def set_param_override(self, circuit_name: str, key: str, value: Any) -> None:
        """Set a parameter override for a circuit's evolution."""
        if circuit_name in self._rules:
            self._rules[circuit_name].param_overrides[key] = value

    # ── Execution ─────────────────────────────────────────────────

    def check_and_adapt(self, circuit_name: str, cb_state: str,
                        cb_stats: dict) -> Optional[AdaptationEvent]:
        """Check a circuit and trigger adaptation if needed.

        Args:
            circuit_name: Name of the circuit.
            cb_state: Current state string ("open", "half_open", "closed").
            cb_stats: Stats dict from get_stats().

        Returns:
            AdaptationEvent if triggered, None otherwise.
        """
        rule = self._rules.get(circuit_name)
        if not rule:
            return None

        # Only trigger on matching state
        if cb_state != rule.trigger_on_state:
            return None

        # Check min failures
        if cb_stats.get("total_failures", 0) < rule.min_failures:
            return None

        # Check cooldown
        with self._lock:
            if not rule.can_fire():
                return None
            rule.last_fired = time.time()

        # Execute adaptation
        event = self._execute_adaptation(circuit_name, cb_stats, rule)
        return event

    def start(self, interval_sec: float = 30.0,
              circuit_registry: Any = None) -> None:
        """Start background monitoring thread.

        Args:
            interval_sec: Polling interval.
            circuit_registry: CircuitBreakerRegistry with .all_stats().
        """
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_sec, circuit_registry),
            daemon=True,
            name="evolution-feedback"
        )
        self._thread.start()
        logger.info(f"Evolution feedback loop started (interval={interval_sec}s)")

    def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_events(self, limit: int = 20) -> list:
        """Return recent adaptation events."""
        return self._events[-limit:]

    def get_stats(self) -> dict:
        """Return feedback loop statistics."""
        return {
            "monitored_circuits": len(self._rules),
            "total_events": len(self._events),
            "running": self._running,
            "has_evolution": _HAVE_EVOLUTION,
        }

    # ── Internal ──────────────────────────────────────────────────

    def _execute_adaptation(self, circuit_name: str,
                            stats: dict, rule: FeedbackRule) -> AdaptationEvent:
        """Execute parameter adaptation via evolution engine."""
        event = AdaptationEvent(
            circuit_name=circuit_name,
            trigger=f"circuit_{rule.trigger_on_state}",
            old_params={"delay": stats.get("delay", 0),
                        "failures": stats.get("total_failures", 0)},
        )

        if _HAVE_EVOLUTION and rule.evolution_config:
            try:
                executor = EvolutionExecutor(rule.evolution_config)
                metrics = {
                    "error_rate": stats.get("failure_rate", 0),
                    "total_failures": stats.get("total_failures", 0),
                }
                actions = executor.evaluate_and_adapt(metrics)
                for a in actions:
                    event.action += f"{a.param}: {a.old_value}->{a.new_value}; "
                event.success = bool(actions)
                event.new_params["evolution_actions"] = len(actions)
            except Exception as e:
                logger.warning(f"Evolution adaptation failed: {e}")
                event.success = False

        if rule.param_overrides:
            event.new_params["overrides"] = rule.param_overrides

        self._events.append(event)
        self._log_event(event)

        logger.info(
            f"Adaptation: {circuit_name} "
            f"trigger={event.trigger} "
            f"success={event.success}"
        )
        return event

    def _monitor_loop(self, interval_sec: float,
                      registry: Any) -> None:
        """Background monitoring thread."""
        while self._running and registry:
            try:
                stats = registry.all_stats()
                for name, s in stats.items():
                    event = self.check_and_adapt(name, s.get("state", ""), s)
                    if event and event.success:
                        logger.info(f"Auto-adapted {name} via evolution feedback")
                time.sleep(interval_sec)
            except Exception:
                time.sleep(interval_sec)

    def _log_event(self, event: AdaptationEvent) -> None:
        """Persist adaptation event to JSONL."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": event.timestamp,
                    "datetime": datetime.fromtimestamp(event.timestamp).isoformat(),
                    "circuit": event.circuit_name,
                    "trigger": event.trigger,
                    "success": event.success,
                    "action": event.action,
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass
