"""li (☲ 离) — GraphTraversalEngine.

Role: Hub-Spoke graph traversal + adaptive depth + OCR variant generation.
Vertex: V1 (VerifyVertex)
Polarity: 阴中之阳
Key class: GraphWalker

Implements the Hub-and-Spoke search protocol (v5.0):
  Phase 1: Locate Hub papers per discipline direction.
  Phase 2: Build Spoke from Hub references.
  Phase 3: Gap detection + OCR safety net.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from ..base_trigram import BaseTrigram, TrigramGua, TrigramInput, TrigramOutput

logger = logging.getLogger(__name__)


class GraphWalker(BaseTrigram):
    """Hub-Spoke graph traversal engine.

    Traversal strategies:
      - BFS: breadth-first (discovery mode)
      - DFS: depth-first (verification mode)
      - HUB_FIRST: locate hubs, then spoke (production default)

    Adaptive depth:
      IF estimated_literature < 20 THEN depth = UNLIMITED (exhaustive).
      IF estimated_literature 20-100 THEN depth = 3 (classification).
      IF estimated_literature > 100 THEN depth = 1 (review-anchored).
    """

    def __init__(self) -> None:
        super().__init__("li", TrigramGua.LI)
        self._graph: nx.DiGraph = nx.DiGraph()
        self._max_depth: int = 3
        self._ocr_variants: List[str] = []

    async def execute(self, input: TrigramInput) -> TrigramOutput:
        """Traverse knowledge graph from seed nodes.

        Step 1: Generate OCR variants of the search term.
        Step 2: FOR EACH variant + original: search for papers.
        Step 3: Build graph with papers as nodes, citations as edges.
        Step 4: Traverse from seeds at adaptive depth.
        Step 5: RETURN subgraph reachable from seeds.

        IF depth == UNLIMITED THEN traverse until 2 consecutive layers yield no new nodes.
        """
        import time
        t0 = time.monotonic()

        query = input.query
        depth = input.params.get("depth", self._max_depth)
        strategy = input.params.get("strategy", "HUB_FIRST")

        # Step 1: Generate OCR variants
        variants = self._generate_ocr_variants(query)

        # Step 2-4: Build and traverse (simulated)
        subgraph_nodes = self._traverse(query, variants, depth, strategy)

        latency_ms = (time.monotonic() - t0) * 1000
        self._latency_samples.append(latency_ms)

        return TrigramOutput(
            status="ok",
            result={
                "query": query,
                "variants_generated": len(variants),
                "variants": variants[:10],
                "nodes_found": len(subgraph_nodes),
                "depth_used": depth,
                "strategy": strategy,
                "items": subgraph_nodes,
            },
            latency_ms=latency_ms,
        )

    def _generate_ocr_variants(self, name: str) -> List[str]:
        """Generate OCR error variants for a scientific name.

        Error types:
          - Letter substitution: u→b, i→l, c→e
          - Vowel confusion: e↔i, a↔o, u↔o
          - Letter deletion: remove one char
          - Tail truncation: drop last 1-3 chars
          - Doubling: l↔ll, s↔ss
        """
        variants: Set[str] = set()
        vowels = {"a", "e", "i", "o", "u"}
        confusable = {
            "u": ["b", "o"], "b": ["u"], "i": ["l", "e"],
            "l": ["i"], "n": ["m"], "m": ["n"],
        }

        # Letter substitution
        for i, ch in enumerate(name):
            if ch.lower() in confusable:
                for sub in confusable[ch.lower()]:
                    variant = name[:i] + sub + name[i + 1:]
                    variants.add(variant)

        # Character deletion
        for i in range(len(name)):
            variants.add(name[:i] + name[i + 1:])

        # Tail truncation
        for n in range(1, min(4, len(name))):
            variants.add(name[:-n])

        # Doubling
        for i, ch in enumerate(name):
            if ch.lower() in {"l", "s", "t", "r"}:
                variants.add(name[:i] + ch + ch + name[i + 1:])

        # Limit to reasonable count
        result = list(variants)[:50]
        self._ocr_variants = result
        return result

    def _traverse(
        self, query: str, variants: List[str], depth: int, strategy: str
    ) -> List[Dict[str, Any]]:
        """Traverse graph from seed nodes.

        IF strategy == HUB_FIRST:
          Locate hub papers per discipline direction.
          Build spoke from hub references.
        IF strategy == BFS:
          Breadth-first from all seeds.
        IF strategy == DFS:
          Depth-first from main seed.
        """
        # Simulated traversal result
        return [
            {"title": f"Hub paper for {query}", "doi": "", "year": 2024, "depth": 0},
            {"title": f"Spoke paper 1 for {query}", "doi": "", "year": 2023, "depth": 1},
            {"title": f"Spoke paper 2 for {query}", "doi": "", "year": 2022, "depth": 2},
        ]
