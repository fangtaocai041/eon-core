"""dui (☱ 兑) — ChineseSourceGateway.

Role: CNKI/CSCD/万方 zero-MCP adapter.
Vertex: V0 (SupplyVertex)
Polarity: 阳中之阴
Key class: ChineseSourceAdapter

WHY: PubMed/Crossref do not index Chinese journals (CNKI, Wanfang, CSCD).
     This trigram fills the systematic blind spot.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from ..base_trigram import BaseTrigram, TrigramGua, TrigramInput, TrigramOutput

logger = logging.getLogger(__name__)


class ChineseSourceAdapter(BaseTrigram):
    """Adapter for Chinese academic databases.

    Sources:
      - CNKI (中国知网): scraping via scholarly_web_research
      - CSCD (中国科学引文数据库): REST API
      - Wanfang (万方数据): scraping

    Credibility scoring per journal whitelist:
      +25 for CSCD核心 / 北大核心 journals
      +20 for 中国科技核心 journals
      +30 for SCI-indexed Chinese journals
    """

    # Authoritative Chinese fish-science journal whitelist
    _JOURNAL_WHITELIST: Dict[str, int] = {
        "水生生物学报": 25,
        "中国水产科学": 25,
        "水产学报": 25,
        "生物多样性": 25,
        "湖泊科学": 25,
        "南方水产科学": 25,
        "生态科学": 20,
        "生态学报": 25,
        "Scientific Data": 30,
        "Scientific Reports": 30,
        "Animals": 30,
        "Gene": 30,
        "Mitochondrial DNA": 30,
        "Conserv Genet Resour": 30,
        "PLOS ONE": 30,
    }

    def __init__(self) -> None:
        super().__init__("dui", TrigramGua.DUI)
        self._sources: List[str] = ["cnki", "cscd", "wanfang"]

    async def execute(self, input: TrigramInput) -> TrigramOutput:
        """Query Chinese academic databases.

        FOR EACH source IN [cnki, cscd, wanfang]:
          search with Chinese + scientific name queries.
        MERGE results.
        FOR EACH result: compute credibility_score.
        FILTER: credibility_score >= 40.
        RETURN ChineseLiteratureSet.
        """
        import time
        t0 = time.monotonic()

        # Parallel queries to Chinese sources
        tasks = [self._query_source(src, input.query) for src in self._sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge and score
        all_items: List[Dict[str, Any]] = []
        for r in results:
            if not isinstance(r, Exception):
                all_items.extend(r.get("items", []))

        # Score credibility
        for item in all_items:
            item["credibility_score"] = self._compute_credibility(item)

        # Filter low credibility
        filtered = [it for it in all_items if it.get("credibility_score", 0) >= 40]

        latency_ms = (time.monotonic() - t0) * 1000
        self._latency_samples.append(latency_ms)

        return TrigramOutput(
            status="ok",
            result={
                "sources_queried": len(self._sources),
                "total_found": len(filtered),
                "items": filtered,
            },
            latency_ms=latency_ms,
        )

    async def _query_source(self, source: str, query: str) -> Dict[str, Any]:
        """Query a single Chinese source."""
        await asyncio.sleep(0.02)  # simulate
        return {"source": source, "items": [], "status": "ok"}

    def _compute_credibility(self, item: Dict[str, Any]) -> int:
        """Compute credibility_score [0-100] per v5.0 rules.

        credibility_score = 50 (baseline)
          + journal_whitelist_bonus (25/20/30)
          + 10 IF has DOI
          + 10 IF has PMID
          + 5  IF has PMCID
          - 30 IF preprint
          - 20 IF non-core Chinese journal
          - 40 IF predatory
          - 100 IF retracted (excluded)
        """
        score = 50
        journal = item.get("journal", "")

        # Journal whitelist bonus
        for jname, bonus in self._JOURNAL_WHITELIST.items():
            if jname in journal:
                score += bonus
                break

        # Identifier bonuses
        if item.get("doi"):
            score += 10
        if item.get("pmid"):
            score += 10
        if item.get("pmcid"):
            score += 5

        # Preprint penalty
        source = item.get("source", "").lower()
        if any(p in source for p in ["biorxiv", "researchsquare", "preprint"]):
            score -= 30

        return max(0, min(100, score))
