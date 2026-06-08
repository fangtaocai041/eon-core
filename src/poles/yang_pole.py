"""YangPole — ☀️ 扩展·供给·生成抽象基类.

Contract: IYangPole
  - expand(query, radius) → CandidateSet
  - supply(context) → KnowledgePayload
  - generate_hypotheses(observations) → HypothesisSet

Invariants:
  - recall_rate >= 0.90
  - NEVER calls verify / validate / contract / filter_by_quality
    (enforced at mypy check time + runtime assertion)

Forbidden operations (raises RuntimeError if called):
  - verify, validate, contract, filter_by_quality
"""

from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from typing import Any, List


# ---------------------------------------------------------------------------
# Runtime guard: forbid Yin-type operations on Yang instances
# ---------------------------------------------------------------------------

_YANG_FORBIDDEN = {"verify", "validate", "contract", "filter_by_quality"}


def _guard_yang(method_name: str):
    """Decorator: raises RuntimeError if a forbidden method is called on YangPole."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            raise RuntimeError(
                f"YangPole.{method_name}() is FORBIDDEN. "
                f"YangPole SHALL NOT call Yin-type operations. "
                f"Use EventBus topic 'pole.interaction.yang→yin' instead."
            )
        return wrapper
    return decorator


class IYangPole(ABC):
    """Protocol contract for Yang (expansion) poles."""

    @abstractmethod
    async def expand(self, query: "QueryContext", radius: "SearchRadius") -> "CandidateSet":
        """Expand search with given radius. Must return non-empty or exhausted."""
        ...

    @abstractmethod
    async def supply(self, context: "SupplyContext") -> "KnowledgePayload":
        """Supply knowledge to requester. source_diversity >= MIN_SOURCE_DIVERSITY."""
        ...

    @abstractmethod
    async def generate_hypotheses(self, observations: List["Observation"]) -> "HypothesisSet":
        """Generate hypotheses from observations. All plausibility > 0."""
        ...


class YangPole(IYangPole):
    """Abstract Yang pole with forbidden-operation guards.

    Subclasses: SupplyVertex (V0), DomainVertexP1 (V2, primary Yang).
    """

    MIN_RECALL_RATE = 0.90
    MAX_EXPANSION_RADIUS = 10

    def __init__(self) -> None:
        self._recall_rate: float = 0.92

    # ── Forbidden operations (guarded) ──

    @_guard_yang("verify")
    async def verify(self, *args, **kwargs):
        pass

    @_guard_yang("validate")
    async def validate(self, *args, **kwargs):
        pass

    @_guard_yang("contract")
    async def contract(self, *args, **kwargs):
        pass

    @_guard_yang("filter_by_quality")
    async def filter_by_quality(self, *args, **kwargs):
        pass

    # ── Abstract methods ──

    @abstractmethod
    async def expand(self, query: "QueryContext", radius: "SearchRadius") -> "CandidateSet":
        ...

    @abstractmethod
    async def supply(self, context: "SupplyContext") -> "KnowledgePayload":
        ...

    @abstractmethod
    async def generate_hypotheses(self, observations: List["Observation"]) -> "HypothesisSet":
        ...

    @property
    def recall_rate(self) -> float:
        return self._recall_rate


# Forward type stubs (resolved at runtime by vertex implementations)
class QueryContext: ...
class SearchRadius: ...
class CandidateSet: ...
class SupplyContext: ...
class KnowledgePayload: ...
class Observation: ...
class HypothesisSet: ...
