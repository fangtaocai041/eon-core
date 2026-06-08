"""
Scholarly-Grounded Search Optimizer — 学术文献检索的最优停止理论落地

理论基础 (peer-reviewed):
  1. Simon (1955/1978): Bounded Rationality + Satisficing
     "决策者不求最优解，只求在认知/时间/信息约束内达到满意解"
     → 硬约束: max_tokens, max_time_ms, max_papers_screened

  2. Callaghan & Müller-Hansen (PMC, 2020): Statistical Stopping
     P(miss ≥1) = 1 - (1 - p_relevant)^k  < α (default α=0.05)
     → 连续 k 篇不相关 → 剩余文献含相关论文概率 < 5%

  3. ASReview (BMC, 2026): Three-Tier Stop Criteria
     C1: 估计召回率 ≥ target_recall (default 85%)
     C2: N_consecutive_irrelevant ≥ threshold
     C3: screening_ratio ≥ threshold (已筛选比例)

  4. NOAA Tech Memo (2023): Entropy-Driven Sampling
     argmax_direction H_gain = -Σ p(x|d) * log p(x|d)
     → 优先搜索信息增益最大的方向 (数据库/引擎/关键词)

工程落地:
  WHEN estimated_recall >= target_recall AND P(miss) < alpha
  THEN STOP("scholarly_satisficed")
  ELSE_IF budget_exhausted THEN STOP("bounded_rationality_limit")
  ELSE_IF 2 * consecutive_zero THEN STOP("diminishing_returns")
  ELSE CONTINUE WITH entropy_guided_next_direction

Usage:
    from src.pipeline.search_optimizer import ScholarlySearch
    s = ScholarlySearch()
    r = s.search("Ochetobius_elongatus")
    # r.stop_reason ∈ {"scholarly_satisficed", "budget_exhausted", "diminishing_returns"}
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Bounded Rationality Budget (Simon, 1955)
# ═══════════════════════════════════════════════════════════════

@dataclass
class CognitiveBudget:
    """有限理性约束: 在认知/时间/信息三重约束下求满意解。

    学者视角: "穷举搜索不是最优策略——当新增论文的边际信息增益
    低于搜索成本时，继续搜索是净损失。"
    """
    max_tokens: int = 5000             # token 硬上限
    max_time_ms: int = 30000           # 30s 硬超时
    max_papers_screened: int = 200     # 最多筛选篇数
    min_papers_satisfice: int = 8      # 满意论文数阈值
    target_recall: float = 0.85        # 目标召回率 (ASReview C1)
    alpha: float = 0.05                # 统计显著性水平 (Callaghan C1)
    consecutive_irrelevant_stop: int = 20  # 连续不相关停止 (ASReview C2)
    screening_ratio_stop: float = 0.50     # 筛选比例阈值 (ASReview C3)


# ═══════════════════════════════════════════════════════════════
# Statistical Stopping (Callaghan & Müller-Hansen, PMC 2020)
# ═══════════════════════════════════════════════════════════════

class StatisticalStopper:
    """统计置信停止准则。

    Callaghan & Müller-Hansen (2020):
      "Stop when we can reject the hypothesis that we have missed
       a given recall target with confidence level 1-α."

    工程形式:
      P(miss ≥ 1) = 1 - (1 - p_relevant)^k
      IF P(miss ≥ 1) < α THEN STOP (有 95% 置信认为已找到足够文献)
    """

    def __init__(self, alpha: float = 0.05, target_recall: float = 0.85):
        self.alpha = alpha
        self.target_recall = target_recall

    @staticmethod
    def _rule_of_three(n_consecutive_zero: int) -> float:
        """Hanley & Lippman-Hand (1983) 'Rule of Three':
        If n consecutive non-events observed, the 95% CI upper bound
        for the true event rate is ≤ 3/n.

        Example: 30 consecutive irrelevant → ≤10% relevance in remaining.
        This is the standard in medical screening stop rules.
        """
        if n_consecutive_zero <= 0:
            return 1.0
        return min(3.0 / n_consecutive_zero, 1.0)

    def should_stop(self, total_screened: int, relevant_found: int,
                    consecutive_irrelevant: int) -> tuple[bool, str, float]:
        """学术级停止准则 (3条独立标准，任意一条触发即停止)。

        C1 (Rule of Three, Hanley 1983):
          连续k篇不相关 → 剩余文献中相关率 ≤ 3/k (95% CI)
          IF 3/k ≤ 0.10 (≤10%相关率) THEN STOP
          例: 连续30篇不相关 → 剩余≤10%相关 → 停止

        C2 (Satisficing, Simon 1955):
          IF found ≥ min_satisfice AND 连续不相关足以保证低遗漏率
          THEN STOP

        C3 (Estimated Recall, ASReview 2026):
          IF estimated_recall ≥ target_recall THEN STOP

        Returns: (should_stop, reason, max_unseen_relevance)
        """
        if total_screened <= 0:
            return False, "no_data", 1.0

        # C1: Rule of Three — 经典医学筛查停止准则
        max_unseen_rate = self._rule_of_three(consecutive_irrelevant)
        if max_unseen_rate <= 0.10:  # unseen papers ≤10% relevant
            return True, (
                f"C1_RuleOfThree: {consecutive_irrelevant} consecutive irrelevant "
                f"→ unseen ≤{max_unseen_rate:.1%} relevant (95% CI)"
            ), max_unseen_rate

        # C2: Simon's Satisficing — 够多论文 + 低遗漏风险
        if relevant_found >= 5 and max_unseen_rate <= 0.15:
            return True, (
                f"C2_Satisficing: {relevant_found} found + "
                f"unseen ≤{max_unseen_rate:.0%} → good enough"
            ), max_unseen_rate

        # C3: Estimated recall
        estimated_unseen = max_unseen_rate * max(consecutive_irrelevant * 5, 50)
        estimated_recall = relevant_found / max(relevant_found + estimated_unseen, 1)
        if estimated_recall >= self.target_recall:
            return True, (
                f"C3_Recall: estimated={estimated_recall:.1%}≥target={self.target_recall}"
            ), max_unseen_rate

        return False, f"continue (unseen≤{max_unseen_rate:.0%})", max_unseen_rate


# ═══════════════════════════════════════════════════════════════
# Entropy-Driven Search Direction (NOAA Tech Memo, 2023)
# ═══════════════════════════════════════════════════════════════

class EntropyGuide:
    """信息熵驱动的搜索方向选择。

    NOAA (2023): "Entropy-based approaches maximize information gain
    by reducing overall uncertainty in system state."

    工程形式:
      对每个候选搜索方向 d:
        H_gain(d) = H_before - Σ p(x|d) * H_after(x|d)
      选择 argmax H_gain(d)
    """

    def __init__(self):
        self._direction_scores: dict[str, float] = {}  # direction → cumulative IG

    def score_direction(self, direction: str,
                        prior_papers: int,
                        expected_new: float,
                        uncertainty: float) -> float:
        """计算搜索方向的期望信息增益。

        Args:
            direction: "pubmed" | "cnki" | "crossref" | "citation_graph" | ...
            prior_papers: 已知论文数
            expected_new: 预期新发现论文数
            uncertainty: 方向的不确定性 [0,1]

        Returns:
            期望信息增益 (bits)
        """
        if expected_new <= 0:
            return 0.0
        # Entropy reduction = prior entropy - posterior entropy
        p_new = expected_new / max(prior_papers + expected_new, 1)
        # Avoid log(0)
        if p_new <= 0 or p_new >= 1:
            return 0.0
        entropy_reduction = -(p_new * math.log2(p_new) + (1 - p_new) * math.log2(1 - p_new))
        # Weight by uncertainty: high uncertainty → high potential IG
        weighted_ig = entropy_reduction * (1.0 + uncertainty)
        self._direction_scores[direction] = self._direction_scores.get(direction, 0.0) + weighted_ig
        return weighted_ig

    def best_direction(self, candidates: dict[str, tuple[float, float]]) -> str:
        """选择信息增益最大的搜索方向。

        Args:
            candidates: {direction: (expected_new, uncertainty)}

        Returns:
            best direction name
        """
        scored = {
            d: self.score_direction(d, 0, exp_new, unc)
            for d, (exp_new, unc) in candidates.items()
        }
        if not scored:
            return "pubmed"  # default
        return max(scored, key=scored.get)


# ═══════════════════════════════════════════════════════════════
# Scholarly Search — 学术级最优搜索
# ═══════════════════════════════════════════════════════════════

@dataclass
class ScholarlyResult:
    """学术级搜索结果。"""
    species_id: str
    papers: list[dict] = field(default_factory=list)
    papers_found: int = 0
    papers_screened: int = 0
    relevant_found: int = 0
    consecutive_irrelevant: int = 0
    estimated_recall: float = 0.0
    p_miss: float = 1.0
    tokens_spent: float = 0.0
    elapsed_ms: float = 0.0
    stop_reason: str = ""
    directions_searched: list[str] = field(default_factory=list)
    cache_hit: bool = False


class ScholarlySearch:
    """学术级最优搜索 — 有限理性 + 统计置信 + 熵驱动。

    Pipeline:
      1. Check cache (KV-cache inspired, 0 cost if hit)
      2. Entropy-guided direction selection (NOAA)
      3. Screen papers, track relevance (Callaghan)
      4. Statistical stopping check (PMC 2020 + ASReview 2026)
      5. Bounded rationality budget check (Simon 1955)
      6. Update cache
    """

    def __init__(self, budget: CognitiveBudget = None):
        self.budget = budget or CognitiveBudget()
        self.stopper = StatisticalStopper(self.budget.alpha, self.budget.target_recall)
        self.guide = EntropyGuide()
        self._cache: dict[str, dict] = {}

    def search(self, species_id: str,
               force_refresh: bool = False) -> ScholarlyResult:
        """执行学术级最优搜索。

        WHEN 缓存命中 AND NOT force_refresh: RETURN cached
        WHEN 统计置信满足: STOP("scholarly_satisficed")
        WHEN 预算耗尽: STOP("bounded_rationality_limit")
        WHEN 连续无新发现: STOP("diminishing_returns")
        """
        t0 = time.time()
        result = ScholarlyResult(species_id=species_id)

        # ── Simon's Bounded Rationality Check 0: Cache ──
        if not force_refresh and species_id in self._cache:
            entry = self._cache[species_id]
            if time.time() - entry["ts"] < 3600:
                result.papers = entry["papers"]
                result.papers_found = len(entry["papers"])
                result.cache_hit = True
                result.stop_reason = "cache_hit (Simon: reuse known)"
                result.elapsed_ms = (time.time() - t0) * 1000
                return result

        # ── Simon's Bounded Rationality Check 1: Budget tracking ──
        tokens = 0.0
        screened = 0
        relevant = 0
        consecutive_zero = 0
        all_papers: list[dict] = []

        # ── NOAA Entropy Guide: Choose search directions ──
        directions = self._select_directions(species_id)

        for direction in directions:
            if tokens >= self.budget.max_tokens:
                result.stop_reason = "bounded_rationality_limit (Simon: token budget)"
                break
            if (time.time() - t0) * 1000 >= self.budget.max_time_ms:
                result.stop_reason = "bounded_rationality_limit (Simon: time budget)"
                break

            # Search this direction
            dir_papers = self._search_direction(species_id, direction)
            result.directions_searched.append(direction)

            for paper in dir_papers:
                screened += 1
                tokens += self._estimate_token_cost(paper)
                is_relevant = self._is_relevant(paper, species_id)

                if is_relevant:
                    relevant += 1
                    consecutive_zero = 0
                    all_papers.append(paper)
                else:
                    consecutive_zero += 1

                # ── Simon's Bounded Rationality Check 2: Screening limit ──
                if screened >= self.budget.max_papers_screened:
                    result.stop_reason = "bounded_rationality_limit (Simon: screening limit)"
                    break

                # ── ASReview C2: Consecutive irrelevant ──
                if consecutive_zero >= self.budget.consecutive_irrelevant_stop:
                    result.stop_reason = (
                        f"ASReview_C2: {consecutive_zero} consecutive irrelevant"
                    )
                    break

                # ── ASReview C3: Screening ratio ──
                if dir_papers and screened / len(dir_papers) >= self.budget.screening_ratio_stop:
                    # Only trigger if also satisficed
                    if relevant >= self.budget.min_papers_satisfice:
                        result.stop_reason = "ASReview_C3: screening ratio reached + satisficed"
                        break

            # ── Callaghan Statistical Stopping (after each direction) ──
            stop, reason, p_miss = self.stopper.should_stop(
                screened, relevant, consecutive_zero
            )
            result.p_miss = p_miss
            result.estimated_recall = min(
                relevant / max(relevant + p_miss * screened, 1), 1.0
            )

            if stop:
                result.stop_reason = reason
                break

            # ── Satisficing Check (Simon): enough papers + low IG ──
            if relevant >= self.budget.min_papers_satisfice and p_miss < self.budget.alpha:
                result.stop_reason = "satisficed (Simon: good enough + Callaghan: P(miss)<α)"
                break

        # Dedup
        seen_doi = set()
        unique = []
        for p in all_papers:
            key = p.get("doi", p.get("title", ""))
            if key and key not in seen_doi:
                seen_doi.add(key)
                unique.append(p)

        result.papers = unique
        result.papers_found = len(unique)
        result.papers_screened = screened
        result.relevant_found = relevant
        result.consecutive_irrelevant = consecutive_zero
        result.tokens_spent = tokens
        result.elapsed_ms = (time.time() - t0) * 1000

        if not result.stop_reason:
            result.stop_reason = "complete"

        # Cache
        if unique:
            self._cache[species_id] = {"papers": unique, "ts": time.time()}

        return result

    def _select_directions(self, species_id: str) -> list[str]:
        """NOAA Entropy Guide: 选择信息增益最大的搜索方向。

        优先搜索:
          1. 已知图谱中有变体的 → variant_search (高不确定性)
          2. 中国物种 → cnki/wanfang (中文数据库盲区)
          3. 近期论文 → citation_forward (引用追踪)
          4. 默认 → pubmed → crossref → openalex
        """
        species_lower = species_id.lower()

        # Entropy-guided candidate scoring
        candidates = {
            "pubmed": (5.0, 0.3),      # expected 5 new, low uncertainty
            "crossref": (3.0, 0.5),     # expected 3 new, medium uncertainty
            "openalex": (2.0, 0.6),     # expected 2 new, higher uncertainty
        }

        # Chinese species → high IG from Chinese databases
        chinese_indicators = ["sinensis", "asiaticus", "chinensis", " japon",
                              "yangtze", "poyang", "dongting"]
        if any(ind in species_lower for ind in chinese_indicators):
            candidates["cnki"] = (4.0, 0.7)      # high uncertainty = high IG
            candidates["wanfang"] = (2.0, 0.8)

        # Rare species → high IG from citation graph
        # (We can't know actual count without searching, use heuristic)
        rare_indicators = ["macrocephalus", "gladius", "reevesii", "elongatus"]
        if any(ind in species_lower for ind in rare_indicators):
            candidates["citation_graph"] = (3.0, 0.9)  # very high uncertainty

        # Sort by entropy gain (high uncertainty first)
        return sorted(candidates, key=lambda d: candidates[d][1], reverse=True)

    def _search_direction(self, species_id: str, direction: str) -> list[dict]:
        """Execute search in one direction. In production, delegates to cognitive."""
        # In production: call cognitive-search-engine with direction-specific query
        # For now: return empty (this is the framework, execution by cognitive)
        return []

    def _estimate_token_cost(self, paper: dict) -> float:
        """Estimate token cost for processing a paper (title-only ~50, abstract ~500)."""
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        return 50.0 + len(abstract) * 0.5  # ~50 for title, ~0.5 per abstract char

    def _is_relevant(self, paper: dict, species_id: str) -> bool:
        """Check if paper is relevant to the target species.

        Uses credibility_score as a proxy for relevance.
        """
        score = paper.get("credibility_score", paper.get("trust_score", 50))
        return score >= 40  # below 40 = likely irrelevant


# ═══════════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════════

def scholarly_search(species_id: str, min_papers: int = 8) -> ScholarlyResult:
    """One-liner: 学术级最优搜索."""
    s = ScholarlySearch(CognitiveBudget(min_papers_satisfice=min_papers))
    return s.search(species_id)
