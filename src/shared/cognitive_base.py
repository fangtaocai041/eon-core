"""
cognitive_base.py — Shared BDI base types (minimal, safe subset).

Only types that are IDENTICAL across coilia/cutter cognitive_analyzer.
Desire/Intention/Reflection/CognitiveResult differ between projects
(theme_id vs phase_id, different field sets) and remain local.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CognitiveState(str, Enum):
    """BDI cognitive states — from porpoise-agent BDI pattern."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    DELIBERATING = "deliberating"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    DONE = "done"


@dataclass
class Belief:
    """What the agent knows about a domain question (identical in coilia/culter)."""
    species_data: Dict[str, Any] = field(default_factory=dict)
    prior_knowledge: List[str] = field(default_factory=list)
    search_results: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    confidence: float = 0.0
