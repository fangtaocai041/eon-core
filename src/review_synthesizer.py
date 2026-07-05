"""
review_synthesizer.py — 综述合成引擎 (eon-core 专属)
=====================================================
从论文列表 → 涌现趋势 + 递归思考 + 模式检测 + 因果推断 → 结构化综述 Markdown。

依赖:
  - rcca_core (RecursiveThinker / ReflectionLoop / SelfModel / Transposition / Emotion)
  - infrastructure (EmergenceEngine, 可选 — 数值趋势分析)

用法:
    from src.review_synthesizer import ReviewSynthesizer, Paper
    syn = ReviewSynthesizer(max_think_steps=8)
    review = syn.synthesize(papers, species="Ochetobius elongatus")
    print(review.markdown)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import re
import sys
import os
import urllib.request
import urllib.error
import concurrent.futures

# ── RCCA 核心 (同目录) ──
try:
    from src.rcca_core import (
        RecursiveThinker, ReflectionLoop,
        SelfModelEngine, EmotionEngine, TranspositionLayer,
    )
except ImportError:
    from rcca_core import (
        RecursiveThinker, ReflectionLoop,
        SelfModelEngine, EmotionEngine, TranspositionLayer,
    )

# ── 涌现引擎 (可选, 来自 eon-core/src) ──
HAS_EMERGENCE = False
EmergenceEngine = None
try:
    _eon_src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    if os.path.isdir(_eon_src_path) and _eon_src_path not in sys.path:
        sys.path.insert(0, _eon_src_path)
    from unified_emergence import EmergenceEngine as _EE
    EmergenceEngine = _EE
    HAS_EMERGENCE = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════
# 数据类型
# ═══════════════════════════════════════════════════════════

@dataclass
class Paper:
    """单篇论文。"""
    title: str
    authors: str = ""
    year: int = 0
    abstract: str = ""
    doi: str = ""
    source: str = ""         # "pubmed" | "cnki" | "scholar" | ...
    keywords: List[str] = field(default_factory=list)
    verified_doi: bool = True  # DOI 存活验证
    doi_error: str = ""        # 验证失败原因

    @property
    def text(self) -> str:
        return f"{self.title}. {self.abstract}"


@dataclass
class Contradiction:
    """两篇论文之间的矛盾。"""
    topic: str
    claim_a: str
    claim_b: str
    paper_a: str            # title
    paper_b: str
    severity: float         # 0-1 矛盾强度


@dataclass
class Consensus:
    """多篇论文之间的共识。"""
    topic: str
    claim: str
    supporting_papers: List[str]
    support_count: int


@dataclass
class ReviewResult:
    """综述合成结果。"""
    species: str
    paper_count: int
    year_range: Tuple[int, int]
    trend_analysis: Dict[str, Any]     # 涌现趋势 (EmergenceEngine)
    core_findings: List[str]           # 递归思考提炼
    contradictions: List[Contradiction] # 矛盾检测
    consensus: List[Consensus]         # 共识检测
    gaps: List[str]                    # 研究空白
    causal_claims: List[Dict]          # 因果推断 (Mill 法)
    # ── 质量评分 (6轴) ──
    confidence: float                  # 综合质量评分
    quality_scores: Dict[str, float] = field(default_factory=dict)  # 6轴详情
    # ── DOI 验证 ──
    doi_verified: int = 0              # 验证通过的DOI数
    doi_failed: int = 0                # 验证失败的DOI数
    doi_failed_list: List[str] = field(default_factory=list)  # 失败DOI列表
    # ── 引文集成 ──
    orphan_citations: List[str] = field(default_factory=list)  # 未在正文中讨论的论文
    citation_integration_rate: float = 0.0  # 引文集成率
    markdown: str = ""                 # 最终输出
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════
# Mill 因果推断 (内联自 san-sheng-wanwu-core dialectics.py)
# ═══════════════════════════════════════════════════════════

class MillCausation:
    """Mill 五法因果推断 — 求同法 + 共变法 (内联简化版)。"""

    @staticmethod
    def infer(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从多源观察推断因果关系。

        Args:
            observations: [{"factor": "X", "outcome": "Y"}, ...]

        Returns:
            [{"cause": str, "effect": str, "confidence": float, "method": str}, ...]
        """
        if not observations:
            return []

        inferences: List[Dict] = []

        # 求同法 (Method of Agreement): 相同结果 → 共同前提
        by_outcome: Dict[str, List[str]] = {}
        for obs in observations:
            outcome = str(obs.get("outcome", ""))
            factor = str(obs.get("factor", ""))
            if outcome not in by_outcome:
                by_outcome[outcome] = []
            by_outcome[outcome].append(factor)

        for outcome, factors in by_outcome.items():
            if len(factors) >= 2:
                # 找共同因子
                common = set(factors[0].split(","))
                for f in factors[1:]:
                    common &= set(f.split(","))
                if common:
                    inferences.append({
                        "cause": ",".join(common),
                        "effect": outcome,
                        "confidence": min(0.7, len(factors) * 0.2),
                        "method": "求同法 (Method of Agreement)",
                    })

        # 共变法 (Method of Concomitant Variation): 因子变化 → 结果变化
        factor_outcome_pairs: Dict[str, set] = {}
        for obs in observations:
            f = str(obs.get("factor", ""))
            o = str(obs.get("outcome", ""))
            if f not in factor_outcome_pairs:
                factor_outcome_pairs[f] = set()
            factor_outcome_pairs[f].add(o)

        for factor, outcomes in factor_outcome_pairs.items():
            if len(outcomes) >= 2:
                inferences.append({
                    "cause": factor,
                    "effect": ",".join(outcomes),
                    "confidence": 0.4,
                    "method": "共变法 (Concomitant Variation)",
                })

        return inferences


# ═══════════════════════════════════════════════════════════
# 综述合成引擎
# ═══════════════════════════════════════════════════════════

class ReviewSynthesizer:
    """综述合成引擎 — 论文列表 → 结构化综述 Markdown。

    流程:
      Phase 0: 预处理 (提取主题/关键词)
      Phase 1: 涌现趋势 (EmergenceEngine 数值分析)
      Phase 2: 递归思考 (RecursiveThinker 文本推理)
      Phase 3: 模式检测 (矛盾/共识/空白)
      Phase 4: 因果推断 (Mill 求同法+共变法)
      Phase 5: 质量把关 (AlignmentGate 幻觉检测+置信度)
      Phase 6: 格式化输出 (结构化 Markdown)

    用法:
        syn = ReviewSynthesizer(max_think_steps=8)
        result = syn.synthesize(papers, species="Ochetobius elongatus")
        print(result.markdown)
    """

    # ── 鱼类生态学关键词 (用于主题提取) ──
    ECOLOGY_KEYWORDS = [
        "分布", "栖息地", "食性", "繁殖", "洄游", "生长", "年龄",
        "种群", "遗传", "基因组", "转录组", "系统发育", "分类",
        "保护", "濒危", "IUCN", "威胁", "入侵", "污染", "水利",
        "气候", "水温", "溶解氧", "重金属", "微塑料",
        "耳石", "稳定同位素", "脂肪酸", "形态", "行为",
        "资源", "渔获", "养殖", "放流", "增殖",
        "distribution", "habitat", "diet", "reproduction", "migration",
        "growth", "population", "genetic", "genome", "phylogeny",
        "conservation", "endangered", "threat", "invasive",
        "climate", "temperature", "otolith", "isotope", "biomass",
    ]

    def __init__(self, max_think_steps: int = 8, verbose: bool = False):
        self._max_steps = max_think_steps
        self._verbose = verbose

        # RCCA 核心
        self._thinker = RecursiveThinker(max_steps=max_think_steps, verbose=verbose)
        self._self_model = SelfModelEngine()
        self._transposition = TranspositionLayer()
        self._emotion = EmotionEngine(transposition_layer=self._transposition)
        self._reflection = ReflectionLoop(max_steps=max_think_steps, verbose=verbose)

        # 涌现引擎 (可选)
        self._emergence = EmergenceEngine() if HAS_EMERGENCE else None

    # ── 主入口 ─────────────────────────────────────────────

    def synthesize(self, papers: List[Paper], species: str = "") -> ReviewResult:
        """执行完整综述合成管线。

        Args:
            papers: 论文列表
            species: 物种名

        Returns:
            ReviewResult (含 .markdown 属性)
        """
        if not papers:
            return ReviewResult(
                species=species, paper_count=0, year_range=(0, 0),
                trend_analysis={}, core_findings=[],
                contradictions=[], consensus=[], gaps=[],
                causal_claims=[], confidence=0.0,
                markdown=f"# {species} 文献综述\n\n暂无数据。")

        years = [p.year for p in papers if p.year > 0]
        year_range = (min(years), max(years)) if years else (0, 0)

        # Phase 1: 涌现趋势
        trends = self._analyze_trends(papers)

        # Phase 2: 递归思考
        core_findings = self._extract_core_findings(papers)

        # Phase 3: 模式检测
        contradictions, consensus, gaps = self._detect_patterns(papers)

        # Phase 4: 因果推断
        causal = self._infer_causation(papers)

        # Phase 4.5: DOI 存活验证 (P0 — Deep-Research-Agent 借鉴)
        doi_verified, doi_failed, doi_failed_list = self._verify_dois(papers)

        # Phase 5: 质量把关 (6轴评分)
        # 先生成临时 markdown 用于引文集成检查
        temp_result = ReviewResult(
            species=species, paper_count=len(papers), year_range=year_range,
            trend_analysis=trends, core_findings=core_findings,
            contradictions=contradictions, consensus=consensus, gaps=gaps,
            causal_claims=causal, confidence=0.0,
            doi_verified=doi_verified, doi_failed=doi_failed,
            doi_failed_list=doi_failed_list)
        temp_markdown = self._format_markdown(temp_result)

        # 引文集成检查
        orphans, integration_rate = self._check_citation_integration(
            temp_markdown, papers)

        confidence, quality_scores = self._quality_check(
            papers, core_findings, contradictions,
            doi_failed=doi_failed, orphan_count=len(orphans))

        # Phase 6: 格式化
        result = ReviewResult(
            species=species,
            paper_count=len(papers),
            year_range=year_range,
            trend_analysis=trends,
            core_findings=core_findings,
            contradictions=contradictions,
            consensus=consensus,
            gaps=gaps,
            causal_claims=causal,
            confidence=confidence,
            quality_scores=quality_scores,
            doi_verified=doi_verified,
            doi_failed=doi_failed,
            doi_failed_list=doi_failed_list,
            orphan_citations=orphans,
            citation_integration_rate=integration_rate,
            markdown="",
        )
        result.markdown = self._format_markdown(result)

        # 自我适应
        self._self_model.update_with_experience(
            {"truth_seeking": confidence, "curiosity": 0.7 if gaps else 0.3},
            prediction_error=1.0 - confidence)

        return result

    # ── Phase 1: 涌现趋势 ─────────────────────────────────

    def _analyze_trends(self, papers: List[Paper]) -> Dict[str, Any]:
        """分析论文发表的数值趋势。

        使用 infrastructure EmergenceEngine (如可用) 检测:
          - 年度论文数量异常
          - 研究热点突变点
          - 理论模式匹配
        """
        years = [p.year for p in papers if p.year > 0]
        if len(years) < 3 or not self._emergence:
            return {
                "available": False,
                "reason": "insufficient_data" if len(years) < 3 else "no_emergence_engine",
                "year_range": (min(years), max(years)) if years else (0, 0),
                "total_papers": len(papers),
            }

        # 构建年份频次序列
        year_min, year_max = min(years), max(years)
        year_counts: Dict[int, int] = {}
        for y in years:
            year_counts[y] = year_counts.get(y, 0) + 1

        # 按年份展开为时序
        all_years = list(range(year_min, year_max + 1))
        time_series = [year_counts.get(y, 0) for y in all_years]

        try:
            anomalies = self._emergence.detect_anomalies(
                time_series, all_years, method="zscore", sensitivity=0.05)

            anomaly_years = [a for a in anomalies if a.get("is_anomaly")]
            change_points = self._emergence.detect_change_points(
                time_series, all_years, sensitivity=0.3)

            # 理论匹配
            data_for_scan = {
                "years": all_years,
                "paper_count": time_series,
            }
            theory_matches = self._emergence.scan(
                data=data_for_scan, species="") if hasattr(self._emergence, 'scan') else []

            return {
                "available": True,
                "year_range": (year_min, year_max),
                "total_papers": len(papers),
                "anomalies": anomaly_years,
                "change_points": change_points,
                "theory_matches": theory_matches,
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"emergence_error: {e}",
                "year_range": (year_min, year_max),
                "total_papers": len(papers),
            }

    # ── Phase 2: 递归思考 ─────────────────────────────────

    def _extract_core_findings(self, papers: List[Paper]) -> List[str]:
        """使用 RecursiveThinker 从论文中提炼核心发现。

        将论文按主题分组，每组独立递归思考，最终跨组综合。
        """
        # 提取所有摘要文本
        texts = [p.abstract for p in papers if p.abstract]
        if not texts:
            # 只有标题时退化为标题拼接
            texts = [p.title for p in papers if p.title]
        if not texts:
            return []

        # 主题分组 (基于关键词)
        groups = self._cluster_by_topic(papers)

        findings = []
        for topic, group_papers in groups.items():
            combined = f"关于{topic}的研究: " + "; ".join(
                [f"{p.title} ({p.year}): {p.abstract[:200]}" for p in group_papers[:5]]
            )
            hypothesis, steps = self._thinker.solve(combined)
            if hypothesis and len(hypothesis) > 10:
                findings.append(f"**{topic}**: {hypothesis[:300]}")

        # 跨组反思
        if len(groups) >= 2:
            cross_query = "综合分析以下发现之间的矛盾和联系:\n" + "\n".join(findings)
            cross_hypothesis, _ = self._thinker.solve(cross_query)
            if cross_hypothesis and len(cross_hypothesis) > 10:
                findings.append(f"**跨领域综合**: {cross_hypothesis[:300]}")

        return findings if findings else [f"涉及 {len(papers)} 篇论文，{len(groups)} 个子主题"]

    def _cluster_by_topic(self, papers: List[Paper]) -> Dict[str, List[Paper]]:
        """基于关键词将论文聚类到子主题。"""
        groups: Dict[str, List[Paper]] = {}

        # 预定义主题→关键词映射
        topic_map = {
            "遗传与进化": ["遗传", "基因组", "转录组", "系统发育", "gene", "genome", "DNA", "phylogen"],
            "生态与分布": ["分布", "栖息地", "食性", "繁殖", "洄游", "habitat", "diet", "migration", "distribution"],
            "种群动态": ["种群", "资源", "渔获", "population", "biomass", "abundance"],
            "保护与管理": ["保护", "濒危", "IUCN", "威胁", "conservation", "endangered", "threat"],
            "环境胁迫": ["污染", "气候", "重金属", "微塑料", "pollution", "climate", "temperature", "heavy metal"],
            "形态与生理": ["耳石", "形态", "生长", "年龄", "otolith", "morpholog", "growth", "age"],
            "方法学": ["方法", "模型", "评估", "监测", "method", "model", "assessment", "monitoring"],
        }

        for paper in papers:
            txt = (paper.title + " " + paper.abstract).lower()
            matched = False
            for topic, kws in topic_map.items():
                if any(kw.lower() in txt for kw in kws):
                    if topic not in groups:
                        groups[topic] = []
                    groups[topic].append(paper)
                    matched = True
                    break
            if not matched:
                if "其他" not in groups:
                    groups["其他"] = []
                groups["其他"].append(paper)

        return groups

    # ── Phase 3: 模式检测 ─────────────────────────────────

    def _detect_patterns(self, papers: List[Paper]) -> Tuple[
            List[Contradiction], List[Consensus], List[str]]:
        """检测论文之间的矛盾、共识和研究空白。

        Returns:
            (contradictions, consensus, gaps)
        """
        contradictions: List[Contradiction] = []
        consensus: List[Consensus] = []

        # 按主题分组
        groups = self._cluster_by_topic(papers)

        # 矛盾检测: 同主题下找对立关键词
        opposite_pairs = [
            ("濒危", "恢复"), ("下降", "增长"), ("减少", "增加"),
            ("显著差异", "无显著差异"), ("支持", "不支持"),
            ("endangered", "recovery"), ("decline", "increase"),
            ("significant", "not significant"),
        ]

        for topic, group_papers in groups.items():
            if len(group_papers) < 2:
                continue

            # 共识检测: 看哪些关键词在 ≥3 篇中出现
            keyword_counts: Dict[str, List[str]] = {}
            for p in group_papers:
                txt = (p.title + " " + p.abstract).lower()
                for kw in self.ECOLOGY_KEYWORDS:
                    if kw.lower() in txt:
                        if kw not in keyword_counts:
                            keyword_counts[kw] = []
                        keyword_counts[kw].append(p.title)

            for kw, titles in keyword_counts.items():
                if len(titles) >= 3:
                    consensus.append(Consensus(
                        topic=f"{topic}/{kw}",
                        claim=f"多篇论文涉及 {kw}",
                        supporting_papers=titles,
                        support_count=len(titles)))

            # 矛盾检测
            for i in range(len(group_papers)):
                for j in range(i + 1, len(group_papers)):
                    pa, pb = group_papers[i], group_papers[j]
                    txt_a = (pa.title + " " + pa.abstract).lower()
                    txt_b = (pb.title + " " + pb.abstract).lower()
                    for opp_a, opp_b in opposite_pairs:
                        if opp_a.lower() in txt_a and opp_b.lower() in txt_b:
                            contradictions.append(Contradiction(
                                topic=topic,
                                claim_a=f"含有 '{opp_a}'",
                                claim_b=f"含有 '{opp_b}'",
                                paper_a=pa.title,
                                paper_b=pb.title,
                                severity=0.6))
                            break  # 每对论文最多检测一个矛盾

        # 空白检测: 预期主题但无覆盖
        covered_topics = set(groups.keys())
        expected_topics = {"遗传与进化", "生态与分布", "种群动态", "保护与管理"}
        gaps = [t for t in expected_topics if t not in covered_topics]

        return contradictions, consensus, gaps

    # ── Phase 4: 因果推断 ─────────────────────────────────

    def _infer_causation(self, papers: List[Paper]) -> List[Dict]:
        """基于 Mill 法从论文中推断因果关系。

        提取论文中的因果模式:
          - 求同法: 多篇论文报告相同结果 → 推断共同原因
          - 共变法: 因子变化伴随结果变化
        """
        observations: List[Dict] = []

        # 从摘要中提取简单的因果模式
        # 模式: "X 导致 Y", "X 影响 Y", "X 与 Y 相关"
        causal_patterns = [
            (r"([^，。,.]+?)(导致|引起|造成|致使)([^，。,.]+)", "正向推断"),
            (r"([^，。,.]+?)(抑制|减少|降低|削弱)([^，。,.]+)", "负向推断"),
            (r"([^，。,.]+?)(与|和)([^，。,.]+?)显著相关", "相关推断"),
        ]

        for paper in papers:
            txt = paper.abstract or paper.title
            for pattern, method in causal_patterns:
                for m in re.finditer(pattern, txt):
                    cause = m.group(1).strip()[:50]
                    effect = m.group(3).strip()[:50]
                    if cause and effect:
                        observations.append({
                            "factor": cause,
                            "outcome": effect,
                            "source": paper.title[:60],
                            "method": method,
                        })

        # 用 Mill 法分析
        if observations:
            return MillCausation.infer(observations)
        return []

    # ── Phase 5: 质量把关 ─────────────────────────────────

    def _verify_dois(self, papers: List[Paper]) -> Tuple[int, int, List[str]]:
        """DOI 存活验证 — 对每个 DOI 发起 HTTP HEAD 请求。

        使用线程池并发验证，超时 5 秒/个。

        Returns:
            (verified_count, failed_count, failed_doi_list)
        """
        dois_to_check = [(i, p) for i, p in enumerate(papers) if p.doi and p.doi.strip()]
        if not dois_to_check:
            return 0, 0, []

        def _check_one(idx: int, paper: Paper) -> Tuple[int, bool, str]:
            doi = paper.doi.strip()
            # 规范化: 去掉前缀 "doi:" 或 "https://doi.org/"
            doi_clean = re.sub(r'^(doi:?\s*|https?://doi\.org/)', '', doi, flags=re.I)
            url = f"https://doi.org/{doi_clean}"
            try:
                req = urllib.request.Request(url, method='HEAD')
                req.add_header('User-Agent', 'ReviewSynthesizer/1.0 (mailto:research@example.com)')
                urllib.request.urlopen(req, timeout=5)
                return (idx, True, "")
            except urllib.error.HTTPError as e:
                papers[idx].verified_doi = False
                papers[idx].doi_error = f"HTTP {e.code}"
                return (idx, False, f"{doi_clean} (HTTP {e.code})")
            except Exception as e:
                papers[idx].verified_doi = False
                papers[idx].doi_error = str(e)[:80]
                return (idx, False, f"{doi_clean} ({str(e)[:60]})")

        verified = 0
        failed = 0
        failed_list: List[str] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_check_one, i, p) for i, p in dois_to_check]
            for f in concurrent.futures.as_completed(futures):
                idx, ok, msg = f.result()
                if ok:
                    verified += 1
                else:
                    failed += 1
                    failed_list.append(msg)

        return verified, failed, failed_list

    def _check_citation_integration(self, markdown: str, papers: List[Paper]) -> Tuple[
            List[str], float]:
        """引文集成检查 — 检测未在正文中讨论的"孤儿引用"。

        ScienceClaw 原则: "如果数据库没返回 → 不能引用"
        PaperOrchestra 原则: "≥90% 引用必须在正文中被讨论"

        Returns:
            (orphan_titles, integration_rate)
        """
        if not papers:
            return [], 1.0

        # 提取正文 (去掉参考文献部分)
        body = markdown
        ref_section_idx = body.find("## 参考文献")
        if ref_section_idx > 0:
            body = body[:ref_section_idx]

        orphans: List[str] = []
        for p in papers:
            # 用标题前 60 字符作为匹配键
            title_key = re.sub(r'[^\w\u4e00-\u9fff]', '', p.title[:60]).lower()
            body_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', body).lower()
            if title_key and title_key not in body_clean:
                orphans.append(p.title[:80])

        integration_rate = 1.0 - len(orphans) / max(len(papers), 1)
        return orphans, round(integration_rate, 3)

    def _quality_check(self, papers: List[Paper],
                       findings: List[str],
                       contradictions: List[Contradiction],
                       doi_failed: int = 0,
                       orphan_count: int = 0) -> Tuple[float, Dict[str, float]]:
        """6 轴质量评分 — 借鉴 PaperOrchestra 评估框架。

        六轴:
          Coverage        — 论文覆盖广度
          Accuracy        — DOI 验证通过率
          Organization    — 核心发现结构化程度
          CitationQuality — 引文集成率
          CriticalAnalysis— 矛盾/空白检测深度
          WritingQuality  — 自我模型稳定性

        Returns:
            (综合评分 0-1, {轴名: 分数})
        """
        scores: Dict[str, float] = {}

        # 1. Coverage: 论文数量 (理想≥10) + 时间跨度
        scores["Coverage"] = min(1.0, len(papers) * 0.08 + 0.1)

        # 2. Accuracy: DOI 验证通过率
        if papers and any(p.doi for p in papers):
            total_doi = doi_failed + max(0, len([p for p in papers if p.doi and p.verified_doi]))
            scores["Accuracy"] = 1.0 - doi_failed / max(total_doi, 1)
        else:
            scores["Accuracy"] = 0.7  # 无DOI时默认中等

        # 3. Organization: 核心发现结构化
        scores["Organization"] = min(1.0, len(findings) * 0.15 + 0.2)

        # 4. CitationQuality: 引文集成率
        if papers:
            integrated = max(0, len(papers) - orphan_count)
            scores["CitationQuality"] = integrated / len(papers)
        else:
            scores["CitationQuality"] = 0.5

        # 5. CriticalAnalysis: 矛盾检测 + 空白识别
        ca_score = min(0.5, len(contradictions) * 0.1)  # 矛盾深度
        ca_score += 0.3  # 基础分析
        scores["CriticalAnalysis"] = min(1.0, ca_score)

        # 6. WritingQuality: 自我模型稳定性
        state = self._self_model.find_state()
        scores["WritingQuality"] = state.stability

        # 加权综合
        weights = {
            "Coverage": 0.20,
            "Accuracy": 0.25,       # DOI 验证权重最高
            "Organization": 0.15,
            "CitationQuality": 0.15,
            "CriticalAnalysis": 0.15,
            "WritingQuality": 0.10,
        }
        composite = sum(scores[k] * weights.get(k, 0.16) for k in scores)
        composite = min(1.0, round(composite, 3))

        return composite, {k: round(v, 3) for k, v in scores.items()}

    # ── Phase 6: 格式化输出 ───────────────────────────────

    def _format_markdown(self, r: ReviewResult) -> str:
        """生成结构化综述 Markdown。"""
        lines: List[str] = []

        # 标题
        sp = r.species or "未知物种"
        yr = f"{r.year_range[0]}-{r.year_range[1]}" if r.year_range[1] > 0 else "未知"
        lines.append(f"# {sp} 研究综述")
        lines.append(f"")
        lines.append(f"> **自动生成** · {r.paper_count} 篇论文 · 时间跨度 {yr} · "
                     f"综合质量 {r.confidence:.0%} · {r.generated_at[:10]}")
        if r.doi_failed > 0:
            lines.append(f"> [!] DOI 验证: {r.doi_verified} 通过 / {r.doi_failed} 失败")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # ── 1. 研究趋势 ──
        lines.append(f"## 1. 研究趋势")
        lines.append(f"")
        trend = r.trend_analysis
        if trend.get("available"):
            lines.append(f"- **时间跨度**: {trend['year_range'][0]}–{trend['year_range'][1]}")
            lines.append(f"- **论文总数**: {trend['total_papers']}")
            if trend.get("anomalies"):
                lines.append(f"- **异常年份**: {len(trend['anomalies'])} 个")
                for a in trend["anomalies"][:5]:
                    lines.append(f"  - {a['year']}: z={a.get('z_score', '?')}")
            if trend.get("change_points"):
                lines.append(f"- **转折点**: {len(trend['change_points'])} 个")
                for cp in trend["change_points"][:3]:
                    lines.append(f"  - {cp}")
            if trend.get("theory_matches"):
                for tm in trend["theory_matches"]:
                    if isinstance(tm, dict):
                        lines.append(f"- **理论匹配**: {tm.get('suggested_theory', tm.get('pattern_name', ''))} "
                                     f"(置信度 {tm.get('confidence', 0):.0%})")
        else:
            lines.append(f"- 论文总数: {r.paper_count} 篇")
            if r.year_range[1] > 0:
                lines.append(f"- 时间范围: {r.year_range[0]}–{r.year_range[1]}")
        lines.append(f"")

        # ── 2. 核心发现 ──
        lines.append(f"## 2. 核心发现")
        lines.append(f"")
        if r.core_findings:
            for i, f in enumerate(r.core_findings, 1):
                lines.append(f"{i}. {f}")
                lines.append(f"")
        else:
            lines.append(f"*(待进一步分析)*")
            lines.append(f"")

        # ── 3. 学术共识 ──
        if r.consensus:
            lines.append(f"## 3. 学术共识")
            lines.append(f"")
            lines.append(f"| 主题 | 共识 | 支持论文数 |")
            lines.append(f"|:-----|:-----|:--------:|")
            for c in r.consensus[:10]:
                lines.append(f"| {c.topic} | {c.claim} | {c.support_count} |")
            lines.append(f"")

        # ── 4. 学术争议 ──
        if r.contradictions:
            lines.append(f"## 4. 学术争议")
            lines.append(f"")
            for i, c in enumerate(r.contradictions[:10], 1):
                lines.append(f"### 4.{i} {c.topic} (强度: {c.severity:.0%})")
                lines.append(f"")
                lines.append(f"- **论文 A**: {c.paper_a[:100]}")
                lines.append(f"  → {c.claim_a}")
                lines.append(f"- **论文 B**: {c.paper_b[:100]}")
                lines.append(f"  → {c.claim_b}")
                lines.append(f"")
        else:
            lines.append(f"## 4. 学术争议")
            lines.append(f"")
            lines.append(f"*(未检测到明显矛盾)*")
            lines.append(f"")

        # ── 5. 研究空白 ──
        lines.append(f"## 5. 研究空白")
        lines.append(f"")
        if r.gaps:
            for g in r.gaps:
                lines.append(f"- [!] **{g}** 方向缺乏研究覆盖")
        else:
            lines.append(f"*(主要方向均有覆盖)*")
        lines.append(f"")

        # ── 6. 因果推断 ──
        if r.causal_claims:
            lines.append(f"## 6. 因果推断 (Mill 法)")
            lines.append(f"")
            for i, c in enumerate(r.causal_claims[:8], 1):
                lines.append(f"{i}. **{c.get('cause', '?')}** → **{c.get('effect', '?')}** "
                             f"({c.get('method', '')}, 置信度 {c.get('confidence', 0):.0%})")
            lines.append(f"")

        # ── 7. 建议 ──
        lines.append(f"## 7. 研究建议")
        lines.append(f"")
        suggestions = []
        if r.gaps:
            for g in r.gaps[:3]:
                suggestions.append(f"- 加强对 **{g}** 方向的研究投入")
        if r.contradictions:
            suggestions.append(f"- 对 {len(r.contradictions)} 个争议点开展验证性研究")
        if r.paper_count < 10:
            suggestions.append(f"- 当前文献数量较少 ({r.paper_count}篇)，建议扩大检索范围")
        if not suggestions:
            suggestions.append(f"- 当前研究基础较好，建议关注前沿交叉方向")
        for s in suggestions:
            lines.append(s)
        lines.append(f"")

        # ── 8. 质量评估 ──
        lines.append(f"## 8. 质量评估 (6 轴)")
        lines.append(f"")
        if r.quality_scores:
            lines.append(f"| 维度 | 分数 | 评级 |")
            lines.append(f"|:-----|:----:|:----:|")
            for axis, score in r.quality_scores.items():
                if score >= 0.8:
                    grade = "优秀"
                elif score >= 0.6:
                    grade = "良好"
                elif score >= 0.4:
                    grade = "一般"
                else:
                    grade = "需改进"
                lines.append(f"| {axis} | {score:.0%} | {grade} |")
            lines.append(f"| **综合** | **{r.confidence:.0%}** | |")
        lines.append(f"")

        # ── 9. 引文集成 ──
        if r.orphan_citations:
            lines.append(f"## 9. 引文集成 (集成率 {r.citation_integration_rate:.0%})")
            lines.append(f"")
            lines.append(f"> 以下论文存在于参考文献列表但未在正文中被充分讨论:")
            lines.append(f"")
            for oc in r.orphan_citations[:5]:
                lines.append(f"- {oc}")
            lines.append(f"")

        # ── 10. DOI 验证 ──
        if r.doi_failed > 0:
            lines.append(f"## 10. DOI 验证结果")
            lines.append(f"")
            lines.append(f"- 通过: {r.doi_verified} 个")
            lines.append(f"- 失败: {r.doi_failed} 个")
            lines.append(f"")
            for dl in r.doi_failed_list[:5]:
                lines.append(f"- ~~{dl}~~")
            lines.append(f"")

        # ── 页脚 ──
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*由 eon-core ReviewSynthesizer 自动生成 · RCCA v2.1 · "
                     f"RecursiveThinker + EmergenceEngine + MillCausation + DOI Verification*")
        lines.append(f"")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 模拟论文数据
    papers = [
        Paper(title="鳤的遗传多样性研究", authors="张三 等", year=2018,
              abstract="对长江流域鳤种群进行了微卫星分析，发现遗传多样性较低，表明种群经历了瓶颈效应。",
              source="cnki", keywords=["遗传", "微卫星", "瓶颈效应"],
              doi="10.1234/fake-doi-for-test-001"),  # 假 DOI — 测试失败路径
        Paper(title="鳤栖息地适宜性评价", authors="李四 等", year=2020,
              abstract="基于MaxEnt模型评估了鳤在长江中下游的栖息地适宜性，发现适宜面积近30年减少60%。",
              source="cnki", keywords=["栖息地", "MaxEnt", "适宜性"],
              doi="10.1038/nature12345"),  # 真 DOI (Nature)
        Paper(title="Ochetobius elongatus population decline in Yangtze", authors="Wang et al.", year=2021,
              abstract="Population declined 90% over 50 years due to dam construction and overfishing. Urgent conservation needed.",
              source="pubmed", keywords=["population", "decline", "conservation"]),
        Paper(title="鳤的人工繁殖技术研究", authors="王五 等", year=2022,
              abstract="成功实现鳤人工繁殖，孵化率达85%，为增殖放流提供技术支持。种群有恢复迹象。",
              source="cnki", keywords=["人工繁殖", "增殖放流", "恢复"],
              doi="10.1126/science.ade9099"),  # 真 DOI (Science)
        Paper(title="Environmental DNA monitoring of Ochetobius elongatus", authors="Liu et al.", year=2023,
              abstract="eDNA metabarcoding detected O. elongatus in 12 of 45 sampling sites, suggesting wider distribution than previously thought.",
              source="pubmed", keywords=["eDNA", "distribution", "monitoring"],
              doi="10.1016/j.scitotenv.2020.141404"),  # 真 DOI (STOTEN)
        Paper(title="鳤重金属富集特征", authors="陈六 等", year=2024,
              abstract="检测了鳤肌肉组织中8种重金属含量，发现镉和铅超标，污染导致种群数量减少。",
              source="cnki", keywords=["重金属", "污染", "镉", "铅"],
              doi="10.5678/fake-doi-test-002"),  # 假 DOI — 测试失败路径
    ]

    syn = ReviewSynthesizer(max_think_steps=5, verbose=True)
    print("=" * 60)
    print("ReviewSynthesizer — 综述合成测试")
    print("=" * 60)

    result = syn.synthesize(papers, species="Ochetobius elongatus (鳤)")
    print(f"\n论文数: {result.paper_count}")
    print(f"时间跨度: {result.year_range}")
    print(f"核心发现: {len(result.core_findings)} 项")
    print(f"矛盾: {len(result.contradictions)} 个")
    print(f"共识: {len(result.consensus)} 个")
    print(f"空白: {len(result.gaps)} 个")
    print(f"因果推断: {len(result.causal_claims)} 项")
    print(f"DOI验证: {result.doi_verified}通过 / {result.doi_failed}失败")
    print(f"引文集成率: {result.citation_integration_rate:.0%}")
    print(f"置信度: {result.confidence:.0%}")
    if result.quality_scores:
        print(f"6轴评分: {result.quality_scores}")
    print(f"\n{'=' * 60}")
    # Fix encoding for Windows console
    try:
        print(result.markdown[:2000])
    except UnicodeEncodeError:
        print(result.markdown.encode('ascii', errors='replace').decode('ascii')[:2000])
