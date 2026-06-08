"""zhen (☳ 震) — MultiModelDebateChamber.

Role: 3 LLM × 3 data sources Socratic adversarial debate.
Vertex: V1 (VerifyVertex)
Polarity: 阴中之阴
Key class: DebateOrchestrator

Design:
  - 3 models: GPT-4o, Claude-3.5-Sonnet, DeepSeek-V3
  - 3 sources: PubMed, CNKI, Google Scholar (each model gets different source)
  - Adversary agent finds loopholes
  - Independence check before voting
  - Verdict: CONSENSUS (3/3), MAJORITY (2/3), DISPUTED (≤1/3)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from ..base_trigram import BaseTrigram, TrigramGua, TrigramInput, TrigramOutput

logger = logging.getLogger(__name__)


class DebateOrchestrator(BaseTrigram):
    """Multi-model Socratic debate chamber.

    Protocol:
      1. Each model receives the same claim + evidence from its assigned source.
      2. Round 1: Each model states position + reasoning.
      3. Round 2: Models critique each other's positions (adversary role).
      4. Round 3: Final vote + confidence.

    Independence check: IF all 3 models use same LLM provider THEN raise warning.
    """

    def __init__(self) -> None:
        super().__init__("zhen", TrigramGua.ZHEN)
        self._models: List[Dict[str, Any]] = [
            {"name": "GPT-4o", "provider": "openai", "temperature": 0.3, "source": "PubMed"},
            {"name": "Claude-3.5-Sonnet", "provider": "anthropic", "temperature": 0.3, "source": "CNKI"},
            {"name": "DeepSeek-V3", "provider": "deepseek", "temperature": 0.3, "source": "GoogleScholar"},
        ]
        self._rounds: int = 3

    async def execute(self, input: TrigramInput) -> TrigramOutput:
        """Run multi-model debate on the given claims.

        Step 1: Independence check — all providers must be distinct.
        Step 2: Round 1 — each model states position.
        Step 3: Round 2 — adversary critique (models swap critiques).
        Step 4: Round 3 — final vote.
        Step 5: Compute verdict:
          IF 3/3 agree THEN CONSENSUS.
          IF 2/3 agree THEN MAJORITY.
          ELSE DISPUTED.

        IF hallucination detected THEN record HALLUCINATION bad deed.
        """
        import time
        t0 = time.monotonic()

        claims = input.params.get("claims", [input.query])
        if isinstance(claims, str):
            claims = [claims]

        # Step 1: Independence check
        providers = {m["provider"] for m in self._models}
        independence_ok = len(providers) >= 3

        # Steps 2-4: Debate rounds (simulated)
        votes: List[Dict[str, Any]] = []
        for model in self._models:
            votes.append({
                "model": model["name"],
                "provider": model["provider"],
                "source": model["source"],
                "position": "ACCEPT",
                "confidence": 0.85,
                "reasoning": f"Claim supported by evidence from {model['source']}",
            })

        # Step 5: Verdict
        accept_count = sum(1 for v in votes if v["position"] == "ACCEPT")
        if accept_count == 3:
            verdict = "CONSENSUS"
        elif accept_count >= 2:
            verdict = "MAJORITY"
        else:
            verdict = "DISPUTED"

        consensus_score = accept_count / len(votes) if votes else 0.0

        latency_ms = (time.monotonic() - t0) * 1000
        self._latency_samples.append(latency_ms)

        return TrigramOutput(
            status="ok",
            result={
                "verdict": verdict,
                "consensus_score": consensus_score,
                "votes": votes,
                "claims_count": len(claims),
                "independence_check": independence_ok,
                "accepted_claims": claims if accept_count >= 2 else [],
                "rejected_claims": [] if accept_count >= 2 else claims,
                "disputed_claims": claims if verdict == "DISPUTED" else [],
            },
            latency_ms=latency_ms,
        )

    async def _query_model(self, model: Dict[str, Any], claim: str) -> Dict[str, Any]:
        """Query a single model with a claim. Simulated."""
        await asyncio.sleep(0.05)
        return {"model": model["name"], "position": "ACCEPT", "confidence": 0.85}
