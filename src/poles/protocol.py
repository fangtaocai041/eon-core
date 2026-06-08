"""YinYangProtocol — 两仪通信协议类型约束.

Rules (enforced at mypy strict + runtime):
  R1: YangPole SHALL NOT call YinPole.verify()
  R2: YinPole SHALL NOT call YangPole.expand()
  R3: Cross-pole communication MUST go through EventBus
      with topic 'pole.interaction.{yang|yin}'
  R4: YangPole output SHALL be marked confidence='LOW'.
      YinPole upgrades to 'HIGH' after verification.
  R5: YangPole output SHALL pass through YinPole.contract()
      before being delivered as final result.

Enforcement:
  - Python Protocol classes for static checking
  - mypy --strict mode
  - Runtime assertion decorators in yang_pole.py / yin_pole.py
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IYangPoleProtocol(Protocol):
    """Structural type for Yang (expansion) poles."""

    async def expand(self, query, radius) -> object: ...
    async def supply(self, context) -> object: ...
    async def generate_hypotheses(self, observations) -> object: ...


@runtime_checkable
class IYinPoleProtocol(Protocol):
    """Structural type for Yin (contraction) poles."""

    async def contract(self, candidates) -> object: ...
    async def verify(self, claim, evidence) -> object: ...
    async def detect_contradiction(self, knowledge) -> object: ...


# ---------------------------------------------------------------------------
# Cross-pole communication router
# ---------------------------------------------------------------------------

class PoleInteractionRouter:
    """All cross-pole messages route through this, published to EventBus.

    Topic pattern: pole.interaction.{source_polarity}.{target_polarity}
      - pole.interaction.yang.yin  → Yang→Yin (supply→verify)
      - pole.interaction.yin.yang  → Yin→Yang (request expansion)

    WHY: Prevents direct import coupling between poles.
    """

    TOPIC_YANG_TO_YIN = "pole.interaction.yang.yin"
    TOPIC_YIN_TO_YANG = "pole.interaction.yin.yang"

    def __init__(self) -> None:
        self._confidence_map = {"yang": "LOW", "yin": "HIGH"}

    @staticmethod
    def wrap_yang_output(data: dict, source: str = "") -> dict:
        """Wrap Yang output with LOW confidence marker."""
        return {
            **data,
            "confidence": "LOW",
            "source": source,
            "verification_status": "pending",
        }

    @staticmethod
    def wrap_yin_output(data: dict, source: str = "") -> dict:
        """Wrap Yin output with HIGH confidence marker."""
        return {
            **data,
            "confidence": "HIGH",
            "source": source,
            "verification_status": "verified",
        }

    @staticmethod
    def validate_cross_pole_event(event: dict) -> bool:
        """Validate that cross-pole event has required fields.

        Returns True if valid, False otherwise.
        """
        required = {"source_pole", "target_pole", "payload"}
        return all(k in event for k in required)
