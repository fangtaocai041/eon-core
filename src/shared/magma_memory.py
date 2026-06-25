"""
memory/magma.py — 四维正交图谱记忆 (嵌套记忆层级增强版 v2.0)

架构:
  热记忆 (Hot) — 当前 session, TTL=300s, 快速衰减, 小容量
  温记忆 (Warm) — 近期 session, TTL=24h, 中等衰减
  冷记忆 (Cold) — 巩固后永久, 无衰减或极慢

每层独立维护四张正交关系图:
  语义图 (Semantic) — 内容相似性
  时序图 (Temporal) — 时间关联
  因果图 (Causal)   — 因果关系链
  实体图 (Entity)   — 实体间关系

检索策略:
  - DSA 风格选择性注意力: 先用轻量索引器预筛选相关子图
  - 再在子图上执行密集推理
  - 结果按层级加权: Hot > Warm > Cold

学术渊源:
  - Google Nested Learning (NeurIPS 2025): 多速度更新的内存
  - DeepSeek Sparse Attention (2025): 闪电索引器 + Token 选择器
  - MAGMA (arXiv 2601.03236): 四维正交图谱记忆

语义编码器:
  - CharacterNgramEncoder (内置, 零依赖) — 基于中文汉字 n-gram
  - HuggingFaceEncoder (可选) — 需安装 sentence-transformers
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import hashlib
import math
import time
import uuid


# ═══════════════════════════════════════════════════════════════
# 语义编码器 (相似度计算) — 与 v1 兼容
# ═══════════════════════════════════════════════════════════════

def _char_ngrams(text: str, n: int = 2) -> Set[str]:
    """生成中文文本的字符 n-gram。"""
    clean = ''.join(c for c in text if c.isalpha() or c.isdigit())
    return {clean[i:i+n] for i in range(len(clean) - n + 1)}


def _jaccard(a: Set, b: Set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


class CharacterNgramEncoder:
    """字符 n-gram 语义编码器 (零依赖)。"""
    def __init__(self, n: int = 2):
        self.n = n
        self.name = "char_ngram"

    def encode(self, text: str) -> Set[str]:
        return _char_ngrams(text, self.n)

    def similarity(self, a: str, b: str) -> float:
        ngrams_a = self.encode(a)
        ngrams_b = self.encode(b)
        bigram_sim = _jaccard(ngrams_a, ngrams_b)
        tri_a = _char_ngrams(a, 3)
        tri_b = _char_ngrams(b, 3)
        trigram_sim = _jaccard(tri_a, tri_b)
        return bigram_sim * 0.6 + trigram_sim * 0.4


class HuggingFaceEncoder:
    """基于 sentence-transformers 的语义编码器 (可选)。"""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.name = f"huggingface/{model_name}"
        self._model = None
        self._model_name = model_name

    def _lazy_load(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

    def encode(self, text: str) -> list:
        self._lazy_load()
        return self._model.encode(text).tolist()

    def similarity(self, a: str, b: str) -> float:
        self._lazy_load()
        emb_a = self._model.encode(a)
        emb_b = self._model.encode(b)
        dot = sum(x * y for x, y in zip(emb_a, emb_b))
        norm_a = math.sqrt(sum(x * x for x in emb_a))
        norm_b = math.sqrt(sum(x * x for x in emb_b))
        return dot / max(norm_a * norm_b, 1e-8)


def create_encoder(backend: str = "char_ngram", **kwargs) -> Any:
    if backend == "huggingface":
        return HuggingFaceEncoder(**kwargs)
    return CharacterNgramEncoder(**kwargs)


# ═══════════════════════════════════════════════════════════════
# 记忆层级配置
# ═══════════════════════════════════════════════════════════════

class MemoryTier:
    """记忆层级定义。"""
    HOT = "hot"      # 工作记忆: 当前 session, 快速衰减
    WARM = "warm"    # 短期记忆: 跨 session, 中等衰减
    COLD = "cold"    # 长期记忆: 巩固后, 不遗忘

    TIERS = [HOT, WARM, COLD]

    # 每层 TTL (秒)
    TTL = {
        HOT: 300,      # 5 分钟
        WARM: 86400,   # 24 小时
        COLD: float('inf'),  # 永久
    }

    # 每层容量上限
    CAPACITY = {
        HOT: 50,
        WARM: 500,
        COLD: float('inf'),
    }

    # 每层遗忘曲线参数 (半衰期, 小时)
    HALF_LIFE_HOURS = {
        HOT: 0.05,     # ~3 分钟
        WARM: 4.0,     # ~4 小时
        COLD: 8760,    # ~1 年 (几乎不遗忘)
    }


def forgetting_curve(hours_elapsed: float, half_life_hours: float) -> float:
    """通用遗忘曲线: R(t) = e^(-t * ln(2) / half_life)

    与 Ebbinghaus 形式一致但可配置半衰期。
    """
    if half_life_hours <= 0:
        return 0.0
    return math.exp(-hours_elapsed * math.log(2) / half_life_hours)


# ═══════════════════════════════════════════════════════════════
# 图数据结构 (与 v1 兼容)
# ═══════════════════════════════════════════════════════════════

class RelationType:
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    CAUSAL = "causal"
    ENTITY = "entity"


@dataclass
class MemoryNode:
    """记忆图谱中的一个节点。"""
    node_id: str = ""
    content: str = ""
    summary: str = ""
    entities: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    importance: float = 0.5
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.node_id:
            self.node_id = uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.summary:
            self.summary = self.content[:80]

    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600


@dataclass
class SignNode(MemoryNode):
    """符号学节点 — Peirce 三元符号模型。

    语言学/符号学扩展:
      sign_type: icon | index | symbol
      signifier:  能指 — 符号本身 ("鳤" 这个字)
      signified:  所指 — 概念 ("一种长江珍稀鱼类")
      referent:   指称对象 — 外部世界实体 ("Ochetobius elongatus")

    示例:
      node = SignNode(content="鳤是一种珍稀鱼类",
                      sign_type="symbol",
                      signifier="鳤",
                      signified="长江珍稀鱼类",
                      referent="Ochetobius elongatus")

    参考: Peirce (1903), Saussure (1916)
    """
    sign_type: str = "symbol"    # icon | index | symbol
    signifier: str = ""           # 能指
    signified: str = ""           # 所指
    referent: str = ""            # 指称对象


@dataclass
class Relation:
    source_id: str
    target_id: str
    rel_type: str
    weight: float = 1.0
    label: str = ""


# ═══════════════════════════════════════════════════════════════
# 嵌套层级记忆 (v2.0 核心)
# ═══════════════════════════════════════════════════════════════

class MagmaMemory:
    """四维正交图谱记忆 v2.0 — 嵌套记忆层级。

    每层 (Hot/Warm/Cold) 维护一组独立的四维图。
    检索时从所有层级融合结果，按层级加权 (Hot > Warm > Cold)。

    用法 (API 与 v1 兼容):
        mem = MagmaMemory()
        node = mem.add("鳤是珍稀鱼类")
        results = mem.search("鳤的保护现状")
    """

    def __init__(self, encoder_backend: str = "char_ngram", **encoder_kwargs):
        self.name = "magma"
        self._encoder = create_encoder(encoder_backend, **encoder_kwargs)
        self._encoder_name = encoder_backend

        # 嵌套记忆层级 { tier: { node_id: MemoryNode } }
        self._tiers: Dict[str, Dict[str, MemoryNode]] = {
            MemoryTier.HOT: {},
            MemoryTier.WARM: {},
            MemoryTier.COLD: {},
        }

        # 每层四维图 { tier: { rel_type: { source_id: [Relation] } } }
        self._graphs: Dict[str, Dict[str, Dict[str, List[Relation]]]] = {
            tier: {
                rt: {} for rt in [RelationType.TEMPORAL, RelationType.SEMANTIC,
                                  RelationType.CAUSAL, RelationType.ENTITY]
            } for tier in MemoryTier.TIERS
        }

    # ── 写入 ──

    def add(self, content: str, entities: Optional[List[str]] = None,
            importance: float = 0.5, metadata: Optional[Dict] = None,
            tier: str = MemoryTier.HOT) -> MemoryNode:
        """添加一条记忆到指定层级 (默认热记忆)。"""
        node = MemoryNode(
            content=content,
            entities=entities or self._extract_entities(content),
            importance=importance,
            metadata={**(metadata or {}), "tier": tier},
        )

        # 写入指定层级
        nodes = self._tiers[tier]
        nodes[node.node_id] = node

        # 与该层级内的现有节点自动建立关系
        for existing in list(nodes.values()):
            if existing.node_id == node.node_id:
                continue

            semantic_score = self._calc_semantic(node, existing)
            if semantic_score > 0.25:
                self._relate(node.node_id, existing.node_id,
                            RelationType.SEMANTIC, semantic_score, tier=tier)

            entity_overlap = set(node.entities) & set(existing.entities)
            if entity_overlap:
                union_size = len(set(node.entities) | set(existing.entities))
                self._relate(node.node_id, existing.node_id,
                            RelationType.ENTITY,
                            len(entity_overlap) / max(union_size, 1), tier=tier)

            time_diff = abs(node.timestamp - existing.timestamp)
            threshold = 300 if tier == MemoryTier.HOT else 3600
            if time_diff < threshold:
                temporal_weight = 1.0 - (time_diff / threshold)
                self._relate(node.node_id, existing.node_id,
                            RelationType.TEMPORAL, temporal_weight,
                            "concurrent" if time_diff < threshold * 0.1 else "precedes",
                            tier=tier)

        # 容量管理: 超出时淘汰最旧的
        self._evict_if_needed(tier)

        return node

    def add_warm(self, content: str, **kwargs) -> MemoryNode:
        """快捷方法: 添加到温记忆。"""
        return self.add(content, tier=MemoryTier.WARM, **kwargs)

    def add_cold(self, content: str, **kwargs) -> MemoryNode:
        """快捷方法: 添加到冷记忆 (巩固后)。"""
        return self.add(content, tier=MemoryTier.COLD, **kwargs)

    def promote(self, node_id: str, from_tier: str = MemoryTier.HOT,
                to_tier: str = MemoryTier.WARM) -> bool:
        """将记忆从低层提升到高层。"""
        source = self._tiers[from_tier]
        if node_id not in source:
            return False
        node = source.pop(node_id)
        node.metadata["tier"] = to_tier
        node.metadata["promoted_at"] = time.time()
        self._tiers[to_tier][node_id] = node

        # 复制关系到目标层 (简化: 全部迁移)
        for rel_type in self._graphs[from_tier]:
            if node_id in self._graphs[from_tier][rel_type]:
                edges = self._graphs[from_tier][rel_type].pop(node_id)
                self._graphs[to_tier][rel_type][node_id] = edges

        return True

    def relate(self, source_id: str, target_id: str,
               rel_type: str = RelationType.CAUSAL,
               weight: float = 1.0, label: str = "",
               tier: str = MemoryTier.HOT):
        """手动建立两个节点之间的关系 (API 兼容 v1)。"""
        self._relate(source_id, target_id, rel_type, weight, label, tier=tier)

    def _relate(self, source_id: str, target_id: str,
                rel_type: str, weight: float, label: str = "",
                tier: str = MemoryTier.HOT):
        """在指定层级的关系图上添加边。"""
        nodes = self._tiers[tier]
        if source_id not in nodes or target_id not in nodes:
            return
        rel = Relation(source_id, target_id, rel_type, weight, label)
        self._graphs[tier][rel_type].setdefault(source_id, []).append(rel)

    def _evict_if_needed(self, tier: str):
        """超出容量时淘汰最旧的节点。"""
        capacity = MemoryTier.CAPACITY[tier]
        if capacity == float('inf'):
            return
        nodes = self._tiers[tier]
        if len(nodes) <= capacity:
            return
        # 按时间戳排序, 删除最旧的
        sorted_ids = sorted(nodes.keys(), key=lambda nid: nodes[nid].timestamp)
        for old_id in sorted_ids[:len(sorted_ids) - capacity]:
            del nodes[old_id]
            for rel_type in self._graphs[tier]:
                self._graphs[tier][rel_type].pop(old_id, None)

    # ── 检索 (DSA 风格选择性注意力) ──

    def search(self, query: str, top_k: int = 10,
               tiers: Optional[List[str]] = None) -> List[MemoryNode]:
        """检索记忆: DSA 风格的选择性图遍历。

        步骤:
          1. 闪电索引: 用 n-gram 生成查询指纹, 快速找候选层
          2. Token 选择: 在每个层级中找到 top-3 锚点
          3. 稀疏注意力: 只在锚点周围进行图遍历
          4. 层级融合: 按 Hot > Warm > Cold 加权

        Args:
            query: 查询文本
            top_k: 返回结果数
            tiers: 检索的层级列表 (默认全部)
        """
        if tiers is None:
            tiers = [t for t in MemoryTier.TIERS if self._tiers[t]]

        # 1. 闪电索引: 查询指纹 = n-gram 集合
        query_ngrams = self._encoder.encode(query)
        query_entities = self._extract_entities(query)

        # 层级加权系数: Hot > Warm > Cold
        tier_weights = {MemoryTier.HOT: 1.0, MemoryTier.WARM: 0.7, MemoryTier.COLD: 0.4}
        tier_search_order = [MemoryTier.HOT, MemoryTier.WARM, MemoryTier.COLD]

        scored: Dict[str, Tuple[float, str]] = {}  # node_id -> (score, tier)

        for tier in tier_search_order:
            if tier not in tiers:
                continue
            nodes = self._tiers[tier]
            if not nodes:
                continue
            tw = tier_weights[tier]

            for nid, node in nodes.items():
                score = 0.0
                # 实体匹配
                if query_entities and node.entities:
                    overlap = len(set(query_entities) & set(node.entities))
                    score += overlap * 0.3 * tw
                # 语义相似度
                semantic = self._encoder.similarity(query, node.content)
                score += semantic * 0.3 * tw
                # 关键词包含
                if query.lower() in node.content.lower():
                    score += 0.2 * tw
                # 遗忘曲线衰减
                hl = MemoryTier.HALF_LIFE_HOURS[tier]
                recall = forgetting_curve(node.age_hours, hl)
                score *= recall * node.importance

                if score > 0:
                    # 已经存在则取更高分
                    existing = scored.get(nid)
                    if existing is None or score > existing[0]:
                        scored[nid] = (score, tier)

        if not scored:
            return []

        # 2. Token 选择: 选每层 top-3 锚点
        anchors_per_tier = {}
        for nid, (score, tier) in scored.items():
            anchors_per_tier.setdefault(tier, []).append((nid, score))
        for tier in anchors_per_tier:
            anchors_per_tier[tier].sort(key=lambda x: x[1], reverse=True)
            anchors_per_tier[tier] = anchors_per_tier[tier][:3]

        # 3. 稀疏注意力: 从锚点出发沿图遍历 (限 depth=2)
        visited: Set[str] = set()
        results: Dict[str, float] = {}

        for tier, anchors in anchors_per_tier.items():
            for anchor_id, _ in anchors:
                self._traverse(anchor_id, visited, results,
                              depth=0, max_depth=2, tier=tier)

        # 4. 层级融合排序
        sorted_ids = sorted(results, key=results.get, reverse=True)[:top_k]

        # 从对应层级取节点
        result_nodes = []
        for nid in sorted_ids:
            for tier in MemoryTier.TIERS:
                if nid in self._tiers[tier]:
                    result_nodes.append(self._tiers[tier][nid])
                    break
        return result_nodes

    def _traverse(self, node_id: str, visited: Set[str],
                  results: Dict[str, float], depth: int, max_depth: int,
                  tier: str = MemoryTier.HOT):
        """从指定节点出发, 沿四维图遍历 (限当前层级)。"""
        if depth > max_depth or node_id in visited:
            return
        visited.add(node_id)

        decay = 0.7 ** depth
        # 遗忘曲线衰减
        if node_id in self._tiers[tier]:
            node = self._tiers[tier][node_id]
            hl = MemoryTier.HALF_LIFE_HOURS[tier]
            recall = forgetting_curve(node.age_hours, hl)
            decay *= recall

        results[node_id] = results.get(node_id, 0) + decay

        for rel_type in [RelationType.TEMPORAL, RelationType.SEMANTIC,
                        RelationType.CAUSAL, RelationType.ENTITY]:
            relations = self._graphs[tier][rel_type].get(node_id, [])
            for rel in relations:
                next_id = rel.target_id
                if next_id not in visited:
                    decayed = decay * rel.weight
                    results[next_id] = results.get(next_id, 0) + decayed
                    self._traverse(next_id, visited, results,
                                  depth + 1, max_depth, tier)

    # ── 辅助 ──

    def _extract_entities(self, text: str) -> List[str]:
        words = text.split()
        entities = []
        for w in words:
            clean = w.strip("，。！？、""''（）()《》【】[]·,").strip()
            if len(clean) >= 2:
                if clean[0].isupper() or any(c.isalpha() for c in clean):
                    entities.append(clean)
        return entities

    def _calc_semantic(self, a: MemoryNode, b: MemoryNode) -> float:
        return self._encoder.similarity(a.content, b.content)

    # ── 层级管理 ──

    def get_tier_sizes(self) -> Dict[str, int]:
        return {t: len(self._tiers[t]) for t in MemoryTier.TIERS}

    def age_out_hot(self) -> int:
        """将超时的热记忆降级为温记忆。"""
        now = time.time()
        promoted = 0
        for nid, node in list(self._tiers[MemoryTier.HOT].items()):
            if now - node.timestamp > MemoryTier.TTL[MemoryTier.HOT]:
                if self.promote(nid, MemoryTier.HOT, MemoryTier.WARM):
                    promoted += 1
        return promoted

    # ── 统计 (API 兼容 v1) ──

    @property
    def node_count(self) -> int:
        return sum(len(ns) for ns in self._tiers.values())

    @property
    def edge_count(self) -> int:
        total = 0
        for tier in MemoryTier.TIERS:
            for g in self._graphs[tier].values():
                for edges in g.values():
                    total += len(edges)
        return total

    def stats(self) -> dict:
        return {
            "nodes": self.node_count,
            "edges": self.edge_count,
            "tiers": self.get_tier_sizes(),
            "graphs": {t: {rt: sum(len(es) for es in g.values())
                          for rt, g in self._graphs[t].items()}
                      for t in MemoryTier.TIERS},
            "encoder": self._encoder_name,
        }

    def report(self) -> dict:
        return {"status": "ok", "stats": self.stats()}
