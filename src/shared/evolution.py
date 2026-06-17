"""EvolutionExecutor — Generic trigger-based self-evolution engine.

Evaluates a set of configurable triggers against incoming metrics and, when a
trigger fires, adapts parameters within clamped ranges.  Every adaptation is
logged to a JSONL audit trail.

Triggers are defined in a YAML config file (or passed programmatically).
Each trigger specifies:
  - A metric key and threshold with comparator (<, >, <=, >=)
  - How many consecutive sessions must breach the threshold
  - Which parameter to adjust, in which direction, and by how much

Usage:
    from eon_core.shared import EvolutionExecutor

    executor = EvolutionExecutor("config/evolution.yaml")
    metrics = {"error_rate": 0.15, "latency_p99": 2.3, "token_avg": 3200}
    actions = executor.evaluate_and_adapt(metrics)
    for a in actions:
        print(f"{a.trigger_name}: {a.param} {a.old_value} → {a.new_value}")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ═══════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Trigger:
    """A single quantified evolution trigger.

    Attributes:
        id: Short identifier, e.g. ``"T1"``.
        name: Human-readable name, e.g. ``"high_error_rate"``.
        condition: Human-readable description of the condition.
        metric_key: Which key in the *metrics* dict to inspect.
        threshold: Numeric threshold for comparison.
        comparator: One of ``"<"``, ``">"``, ``"<="``, ``">="``.
        consecutive_required: How many consecutive evaluations must breach.
        action: Human-readable description of the adaptation.
        param_to_adjust: Config parameter path (dot-separated for nesting).
        adjust_direction: ``"increase"`` or ``"decrease"``.
        adjust_amount: Magnitude of adjustment.
    """
    id: str
    name: str
    condition: str
    metric_key: str
    threshold: float
    comparator: str          # "<" | ">" | "<=" | ">="
    consecutive_required: int = 3
    action: str = ""
    param_to_adjust: str = ""
    adjust_direction: str = "increase"
    adjust_amount: float = 1.0


@dataclass
class AdaptationAction:
    """A record of one parameter adaptation."""
    trigger_id: str
    trigger_name: str
    param: str
    old_value: float
    new_value: float
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════════════
# EvolutionExecutor
# ═══════════════════════════════════════════════════════════════════

class EvolutionExecutor:
    """Load a YAML evolution config, evaluate triggers, adapt parameters,
    and persist changes plus a JSONL audit log.

    Parameters:
        config_path: Path to a YAML file (see below for format).
        audit_log_path: Where to write the JSONL audit trail.  If
            ``None``, the value from the config's ``evolution.audit_log`` is
            used, defaulting to ``".evolution/audit.jsonl"``.

    **YAML config format** (all keys optional)::

        evolution:
          enabled: true
          audit_log: ".evolution/audit.jsonl"
          history_window: 20
          triggers:
            - id: "E1"
              name: "high_error_rate"
              metric_key: "error_rate"
              threshold: 0.10
              comparator: ">"
              consecutive_required: 3
              action: "decrease batch_size by 10"
              param_to_adjust: "batch_size"
              adjust_direction: "decrease"
              adjust_amount: 10
          adaptive_params:
            batch_size:
              current: 100
              range: [10, 500]
    """

    def __init__(
        self,
        config_path: str = "config/evolution.yaml",
        audit_log_path: Optional[str] = None,
    ):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
        self._triggers: List[Trigger] = []
        self._audit_log_path: Optional[str] = audit_log_path
        self._load_config()

    # ── config loading ─────────────────────────────────────────────

    def _load_config(self) -> None:
        if yaml is None:
            self._config = {}
            return
        if not self.config_path.exists():
            self._config = {}
            return
        try:
            with open(self.config_path, encoding="utf-8") as fh:
                self._config = yaml.safe_load(fh) or {}
        except Exception:
            self._config = {}

        evo = self._config.get("evolution", {})

        # Resolve audit log path
        if self._audit_log_path is None:
            self._audit_log_path = evo.get(
                "audit_log", ".evolution/audit.jsonl"
            )

        # Build triggers from config
        self._triggers = []
        for raw in evo.get("triggers", []):
            self._triggers.append(Trigger(
                id=raw.get("id", ""),
                name=raw.get("name", ""),
                condition=raw.get("condition", ""),
                metric_key=raw.get("metric_key", ""),
                threshold=float(raw.get("threshold", 0)),
                comparator=raw.get("comparator", "<"),
                consecutive_required=int(raw.get("consecutive_required", 3)),
                action=raw.get("action", ""),
                param_to_adjust=raw.get("param_to_adjust", ""),
                adjust_direction=raw.get("adjust_direction", "increase"),
                adjust_amount=float(raw.get("adjust_amount", 1.0)),
            ))

    # ── programmatic trigger management ────────────────────────────

    def add_trigger(self, trigger: Trigger) -> None:
        """Register a trigger programmatically (in addition to YAML ones)."""
        self._triggers.append(trigger)

    def clear_triggers(self) -> None:
        """Remove all triggers (both YAML and programmatic)."""
        self._triggers.clear()

    @property
    def triggers(self) -> List[Trigger]:
        """Return a copy of the current trigger list."""
        return list(self._triggers)

    @property
    def enabled(self) -> bool:
        """Whether evolution is enabled per config."""
        return bool(self._config.get("evolution", {}).get("enabled", False))

    # ── core API ───────────────────────────────────────────────────

    def evaluate_and_adapt(self, metrics: Dict[str, Any]) -> List[AdaptationAction]:
        """Evaluate all triggers against *metrics* and adapt parameters.

        Parameters:
            metrics: Flat dict of metric values, e.g.
                ``{"error_rate": 0.12, "latency": 2.1}``.

        Returns:
            List of ``AdaptationAction`` records, one per triggered adaptation.
            An action with an empty ``param`` indicates a manual-only alert.
        """
        if not self._config.get("evolution", {}).get("enabled", False):
            return []

        # Record session
        history_window = (
            self._config.get("evolution", {}).get("history_window", 20)
        )
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            **metrics,
        })
        if len(self._history) > history_window:
            self._history = self._history[-history_window:]

        actions: List[AdaptationAction] = []

        for trigger in self._triggers:
            if not trigger.param_to_adjust:
                # Manual-only alert (no parameter to adjust)
                if self._evaluate_trigger(trigger):
                    actions.append(AdaptationAction(
                        trigger_id=trigger.id,
                        trigger_name=trigger.name,
                        param="",
                        old_value=0,
                        new_value=0,
                        reason=(
                            f"ALERT: {trigger.condition} — "
                            f"manual intervention required"
                        ),
                    ))
                continue

            if self._evaluate_trigger(trigger):
                action = self._adapt_parameter(trigger)
                if action:
                    actions.append(action)

        # Persist & audit
        if actions:
            self._persist_config()
            self._write_audit(actions)

        return actions

    def _evaluate_trigger(self, trigger: Trigger) -> bool:
        """Return True if the trigger condition is met over the required
        consecutive window."""
        needed = trigger.consecutive_required
        if len(self._history) < needed:
            return False

        recent = self._history[-needed:]
        values = [s.get(trigger.metric_key) for s in recent]
        if any(v is None for v in values):
            return False

        cmp = trigger.comparator
        for v in values:
            v = float(v)
            if cmp == "<" and not (v < trigger.threshold):
                return False
            if cmp == ">" and not (v > trigger.threshold):
                return False
            if cmp == "<=" and not (v <= trigger.threshold):
                return False
            if cmp == ">=" and not (v >= trigger.threshold):
                return False

        return True

    def _adapt_parameter(self, trigger: Trigger) -> Optional[AdaptationAction]:
        """Apply a single parameter adaptation. Returns the action record."""
        adaptive_params = (
            self._config.get("evolution", {}).get("adaptive_params", {})
        )

        if trigger.param_to_adjust not in adaptive_params:
            return None

        param_cfg = adaptive_params[trigger.param_to_adjust]
        old_value = float(param_cfg.get("current", param_cfg.get("value", 0)))
        param_range = param_cfg.get("range", [0, 100])

        if trigger.adjust_direction == "increase":
            new_value = old_value + trigger.adjust_amount
        elif trigger.adjust_direction == "decrease":
            new_value = old_value - trigger.adjust_amount
        else:
            return None

        # Clamp
        new_value = max(param_range[0], min(param_range[1], new_value))

        if new_value == old_value:
            return None

        # Update in-memory
        if "current" in param_cfg:
            param_cfg["current"] = new_value
        else:
            param_cfg["value"] = new_value
        param_cfg["last_adjusted"] = datetime.now().isoformat()

        return AdaptationAction(
            trigger_id=trigger.id,
            trigger_name=trigger.name,
            param=trigger.param_to_adjust,
            old_value=old_value,
            new_value=new_value,
            reason=f"{trigger.condition} → {trigger.action}",
        )

    # ── persistence ────────────────────────────────────────────────

    def _persist_config(self) -> None:
        if yaml is None:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as fh:
                yaml.dump(
                    self._config, fh,
                    allow_unicode=True, default_flow_style=False,
                )
        except Exception:
            pass

    def _write_audit(self, actions: List[AdaptationAction]) -> None:
        if not self._audit_log_path:
            return
        try:
            os.makedirs(
                os.path.dirname(self._audit_log_path) or ".", exist_ok=True
            )
            with open(self._audit_log_path, "a", encoding="utf-8") as fh:
                for a in actions:
                    record = {
                        "timestamp": a.timestamp,
                        "trigger_id": a.trigger_id,
                        "trigger_name": a.trigger_name,
                        "param": a.param,
                        "old_value": a.old_value,
                        "new_value": a.new_value,
                        "reason": a.reason,
                    }
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ── introspection ──────────────────────────────────────────────

    def get_trigger_status(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the current status of every trigger without adapting.

        Returns a list of dicts with keys: id, name, current_value,
        threshold, comparator, triggered, consecutive_checked.
        """
        status: List[Dict[str, Any]] = []
        for trigger in self._triggers:
            value = metrics.get(trigger.metric_key)
            triggered = (
                self._evaluate_trigger(trigger) if value is not None else None
            )
            status.append({
                "id": trigger.id,
                "name": trigger.name,
                "current_value": value,
                "threshold": trigger.threshold,
                "comparator": trigger.comparator,
                "triggered": triggered,
                "consecutive_checked": min(
                    len(self._history), trigger.consecutive_required
                ),
            })
        return status

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return a copy of the rolling metric history."""
        return list(self._history)


# ═══════════════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════════════

def check_all_triggers(
    config_path: str,
    metrics: Dict[str, Any],
    audit_log_path: Optional[str] = None,
) -> Dict[str, Any]:
    """One-liner: load config, evaluate triggers, return summary.

    Returns a dict with keys:
      - ``triggered``: list of trigger names that fired
      - ``adaptations``: list of {param, old, new} dicts
      - ``all_clear``: True when nothing triggered
      - ``alerts``: list of alert reason strings (manual-only triggers)
    """
    executor = EvolutionExecutor(config_path, audit_log_path=audit_log_path)
    actions = executor.evaluate_and_adapt(metrics)
    return {
        "triggered": [a.trigger_name for a in actions],
        "adaptations": [
            {"param": a.param, "old": a.old_value, "new": a.new_value}
            for a in actions if a.param
        ],
        "all_clear": len(actions) == 0,
        "alerts": [a.reason for a in actions if not a.param],
    }
