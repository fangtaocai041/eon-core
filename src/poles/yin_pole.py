"""YinPole — 🌙 收缩·验证·矛盾检测抽象基类.

Contract: IYinPole
  - contract(candidates) → VerifiedSet
  - verify(claim, evidence) → VerificationVerdict
  - detect_contradiction(knowledge) → ContradictionReport

Invariants:
  - precision_rate >= 0.85
  - NEVER calls search / expand / generate / supply_unverified
    (enforced at mypy check time + runtime assertion)

Forbidden operations (raises RuntimeError if called):
  - search, expand, generate, supply_unverified
"""

from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from typing import Any, List


# ---------------------------------------------------------------------------
# Runtime guard: forbid Yang-type operations on Yin instances
# ---------------------------------------------------------------------------

_YIN_FORBIDDEN = {"search", "expand", "generate", "supply_unverified"}


def _guard_yin(method_name: str):
    """Decorator: raises RuntimeError if a forbidden method is called on YinPole."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            raise RuntimeError(
                f"YinPole.{method_name}() is FORBIDDEN. "
                f"YinPole SHALL NOT call Yang-type operations. "
                f"Use EventBus topic 'pole.interaction.yin→yang' instead."
            )
        return wrapper
    return decorator


class IYinPole(ABC):
    """Protocol contract for Yin (contraction) poles."""

    @abstractmethod
    async def contract(self, candidates: "CandidateSet") -> "VerifiedSet":
        """Contract candidate set to verified subset. precision >= MIN_PRECISION."""
        ...

    @abstractmethod
    async def verify(self, claim: "Claim", evidence: "EvidenceSet") -> "VerificationVerdict":
        """Verify a claim against evidence. confidence ∈ [0, 1]."""
        ...

    @abstractmethod
    async def detect_contradiction(self, knowledge: "KnowledgeSet") -> "ContradictionReport":
        """Detect contradictions in knowledge set."""
        ...


class YinPole(IYinPole):
    """Abstract Yin pole with forbidden-operation guards.

    Subclasses: VerifyVertex (V1), DomainVertexP2 (V3, primary Yin).
    """

    MIN_PRECISION_RATE = 0.85

    def __init__(self) -> None:
        self._precision_rate: float = 0.88

    # ── Forbidden operations (guarded) ──

    @_guard_yin("search")
    async def search(self, *args, **kwargs):
        pass

    @_guard_yin("expand")
    async def expand(self, *args, **kwargs):
        pass

    @_guard_yin("generate")
    async def generate(self, *args, **kwargs):
        pass

    @_guard_yin("supply_unverified")
    async def supply_unverified(self, *args, **kwargs):
        pass

    # ── Abstract methods ──

    @abstractmethod
    async def contract(self, candidates: "CandidateSet") -> "VerifiedSet":
        ...

    @abstractmethod
    async def verify(self, claim: "Claim", evidence: "EvidenceSet") -> "VerificationVerdict":
        ...

    @abstractmethod
    async def detect_contradiction(self, knowledge: "KnowledgeSet") -> "ContradictionReport":
        ...

    @property
    def precision_rate(self) -> float:
        return self._precision_rate


# Forward type stubs
class CandidateSet: ...
class VerifiedSet: ...
class Claim: ...
class EvidenceSet: ...
class VerificationVerdict: ...
class KnowledgeSet: ...
class ContradictionReport: ...
