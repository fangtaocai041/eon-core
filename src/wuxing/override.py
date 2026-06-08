"""WuXing OverrideToken — escalation mechanism.

Rule: WHEN ke_signal is rejected by target 3 consecutive times
      WITHOUT target metric improvement
      THEN escalate from ADVISORY → MANDATORY.
"""

from __future__ import annotations

from typing import Any


class OverrideToken:
    """Escalation token for WuXing ke restriction signals.

    Tracks rejection count. After override_threshold (default 3)
    consecutive rejections without improvement, escalates severity.
    """

    def __init__(self, threshold: int = 3) -> None:
        self.rejection_count: int = 0
        self.last_signal: Any = None
        self.escalated: bool = False
        self._threshold = threshold

    def record_rejection(self, signal: Any) -> None:
        """Record a rejected ke signal.

        IF rejection_count >= threshold THEN set escalated = True.
        """
        self.rejection_count += 1
        self.last_signal = signal
        if self.rejection_count >= self._threshold:
            self.escalated = True

    def record_improvement(self) -> None:
        """Reset rejection counter when target metric improves."""
        self.rejection_count = 0
        self.escalated = False

    def escalate(self, signal: Any) -> Any:
        """Escalate signal severity.

        IF escalated THEN severity = MANDATORY.
        ELSE return signal unchanged.
        """
        if self.escalated and signal:
            signal.severity = "MANDATORY"
        return signal

    def reset(self) -> None:
        """Full reset."""
        self.rejection_count = 0
        self.last_signal = None
        self.escalated = False
