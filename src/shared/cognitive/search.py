"""
思维树/图搜索 (Tree/Graph of Thoughts Search)
──────────────────────────────────────────────
在推理空间中进行结构化搜索。

ToT (Tree of Thoughts):
    - 树状搜索: 每个节点生成 k 个候选子节点
    - BFS: 逐层展开，每层保留 top-b 节点
    - DFS: 深度优先，失败时回溯
    - 启发式评估: 对每个候选"想法"评分

GoT (Graph of Thoughts):
    - DAG 结构: 允许多个推理分支合并
    - 合并操作: 不同分支的结果可以聚合
    - 协同操作: 分支之间可以互相增强
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import heapq
import math
import random
import time

logger = logging.getLogger(__name__)


class SearchStrategy(str, Enum):
    """搜索策略"""
    BFS = "bfs"           # 广度优先 (逐层展开)
    DFS = "dfs"           # 深度优先 (先探索一条路径)
    BEAM = "beam"         # 束搜索 (每层保留 top-b)
    MCTS = "mcts"         # 蒙特卡洛树搜索
    BEST_FIRST = "best_first"  # 最佳优先


@dataclass
class ThoughtNode:
    """
    思维节点 — 推理树/图中的一个"想法"

    每个节点包含:
    - 状态: 当前的局部推理结果
    - 评估分数: 启发式评估 (0-1)
    - 访问次数: 用于 MCTS
    """
    id: str
    content: str                          # 节点内容 (推理片段)
    parent_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)
    merge_sources: list[str] = field(default_factory=list)  # GoT 合并来源

    # 评估
    score: float = 0.0                    # 启发式评分 (0-1)
    value: float = 0.0                    # MCTS 价值
    visits: int = 0                       # MCTS 访问次数

    # 元数据
    depth: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def __lt__(self, other: "ThoughtNode") -> bool:
        return self.score > other.score  # 逆序 (大→小)

    def __repr__(self) -> str:
        return f"ThoughtNode({self.id}, score={self.score:.3f}, depth={self.depth})"


@dataclass
class SearchResult:
    """搜索结果"""
    best_path: list[ThoughtNode]           # 最佳路径 (根→叶)
    best_score: float
    nodes_explored: int
    nodes_pruned: int
    iterations: int
    elapsed_ms: float
    all_nodes: dict[str, ThoughtNode] = field(default_factory=dict)


# ── 搜索配置 ───────────────────────────────────────────────

@dataclass
class SearchConfig:
    """搜索配置"""
    strategy: SearchStrategy = SearchStrategy.BFS
    max_depth: int = 5
    max_nodes: int = 100
    beam_width: int = 3                 # Beam Search 宽度
    branch_factor: int = 3              # 每个节点生成的候选数
    exploration_weight: float = 1.414   # MCTS UCB 探索权重
    min_score_threshold: float = 0.3    # 最低评分阈值 (低于则剪枝)
    timeout_ms: float = 30000.0         # 超时


# ── 思维树搜索器 ──────────────────────────────────────────

class ThoughtTreeSearch:
    """
    思维树搜索器 — 在推理空间中进行结构化搜索

    支持策略:
    - BFS: 逐层展开, 每层保留 top-b (Beam Search)
    - DFS: 深度优先, 失败时回溯到父节点
    - Beam: 标准束搜索
    - Best-First: 全局按分数优先展开
    - MCTS: 蒙特卡洛树搜索 (UCB 选择)

    用法:
        searcher = ThoughtTreeSearch(
            expand_fn=my_expand_fn,    # 生成子节点
            evaluate_fn=my_eval_fn,    # 评估节点
            config=SearchConfig(strategy=SearchStrategy.BEAM, beam_width=3),
        )
        result = searcher.search(root_node)
    """

    def __init__(
        self,
        expand_fn: Callable[[ThoughtNode], list[ThoughtNode]],
        evaluate_fn: Callable[[ThoughtNode], float],
        config: Optional[SearchConfig] = None,
    ):
        self.expand_fn = expand_fn
        self.evaluate_fn = evaluate_fn
        self.config = config or SearchConfig()

        self._node_counter = 0
        self._nodes: dict[str, ThoughtNode] = {}
        self._pruned_count = 0
        logger.info(f"ThoughtTreeSearch initialized (strategy={self.config.strategy})")

    def search(self, root: ThoughtNode) -> SearchResult:
        """主搜索入口"""
        start = time.time()
        root.depth = 0
        root.score = self.evaluate_fn(root)
        self._register_node(root)

        strategy_map = {
            SearchStrategy.BFS: self._search_bfs,
            SearchStrategy.DFS: self._search_dfs,
            SearchStrategy.BEAM: self._search_bfs,  # beam = BFS with top-b selection
            SearchStrategy.BEST_FIRST: self._search_best_first,
            SearchStrategy.MCTS: self._search_mcts,
        }
        searcher = strategy_map.get(self.config.strategy, self._search_bfs)
        result = searcher(root)
        result.elapsed_ms = (time.time() - start) * 1000
        result.all_nodes = dict(self._nodes)

        logger.info(
            f"Search complete: {result.nodes_explored} explored, "
            f"{result.nodes_pruned} pruned, "
            f"best_score={result.best_score:.3f}, "
            f"{result.elapsed_ms:.0f}ms"
        )
        return result

    def _register_node(self, node: ThoughtNode):
        """注册节点"""
        self._nodes[node.id] = node

    def _new_id(self) -> str:
        self._node_counter += 1
        return f"N{self._node_counter:04d}"

    # ── BFS / Beam Search ────────────────────────────

    def _search_bfs(self, root: ThoughtNode) -> SearchResult:
        """BFS + Beam: 逐层展开，每层保留 top-b"""
        config = self.config
        current_level = [root]
        nodes_explored = 1
        depth = 0

        for depth in range(config.max_depth):
            if not current_level or nodes_explored >= config.max_nodes:
                break

            # 展开当前层所有节点
            next_level = []
            for node in current_level:
                if nodes_explored >= config.max_nodes:
                    break
                children = self._expand_and_evaluate(node)
                next_level.extend(children)
                nodes_explored += len(children)

            if not next_level:
                break

            # Beam: 保留 top-b
            if config.strategy in (SearchStrategy.BEAM, SearchStrategy.BFS):
                next_level.sort(key=lambda n: n.score, reverse=True)
                pruned = next_level[config.beam_width:]
                next_level = next_level[:config.beam_width]
                self._pruned_count += len(pruned)

            current_level = next_level

        # 找最佳叶节点
        best = self._find_best_leaf(root)
        return SearchResult(
            best_path=self._trace_path(best),
            best_score=best.score,
            nodes_explored=nodes_explored,
            nodes_pruned=self._pruned_count,
            iterations=depth + 1,
            elapsed_ms=0.0,
        )

    # ── DFS ──────────────────────────────────────────

    def _search_dfs(self, root: ThoughtNode) -> SearchResult:
        """深度优先搜索 (带回溯)"""
        config = self.config
        best_node = root
        best_score = root.score
        nodes_explored = 1

        def dfs(node: ThoughtNode):
            nonlocal best_node, best_score, nodes_explored

            if node.depth >= config.max_depth:
                return
            if nodes_explored >= config.max_nodes:
                return

            children = self._expand_and_evaluate(node)
            nodes_explored += len(children)

            for child in children:
                if child.score > best_score:
                    best_score = child.score
                    best_node = child
                dfs(child)

        dfs(root)

        return SearchResult(
            best_path=self._trace_path(best_node),
            best_score=best_score,
            nodes_explored=nodes_explored,
            nodes_pruned=self._pruned_count,
            iterations=nodes_explored,
            elapsed_ms=0.0,
        )

    # ── Best-First ───────────────────────────────────

    def _search_best_first(self, root: ThoughtNode) -> SearchResult:
        """最佳优先搜索: 全局按分数展开"""
        config = self.config
        heap: list[tuple[float, int, ThoughtNode]] = []
        counter = 0  # tie-breaker

        heapq.heappush(heap, (-root.score, counter, root))
        counter += 1
        nodes_explored = 1
        best_node = root
        best_score = root.score

        while heap and nodes_explored < config.max_nodes:
            _, _, node = heapq.heappop(heap)

            if node.depth >= config.max_depth:
                continue

            children = self._expand_and_evaluate(node)
            nodes_explored += len(children)

            for child in children:
                if child.score > best_score:
                    best_score = child.score
                    best_node = child
                heapq.heappush(heap, (-child.score, counter, child))
                counter += 1

        return SearchResult(
            best_path=self._trace_path(best_node),
            best_score=best_score,
            nodes_explored=nodes_explored,
            nodes_pruned=self._pruned_count,
            iterations=counter,
            elapsed_ms=0.0,
        )

    # ── MCTS ─────────────────────────────────────────

    def _search_mcts(self, root: ThoughtNode) -> SearchResult:
        """蒙特卡洛树搜索"""
        config = self.config
        start = time.time()
        iterations = 0

        while (
            iterations < config.max_nodes
            and (time.time() - start) * 1000 < config.timeout_ms
        ):
            # Selection
            node = self._mcts_select(root)

            # Expansion
            if node.visits > 0 and node.depth < config.max_depth:
                children = self._expand_and_evaluate(node)
                if children:
                    node = random.choice(children)

            # Simulation (rollout)
            value = self._mcts_simulate(node)

            # Backpropagation
            self._mcts_backprop(node, value)

            iterations += 1

        # Best child of root
        best_child = max(
            self._nodes.get(cid, root) for cid in root.children_ids
        ) if root.children_ids else root
        best_child = best_child if isinstance(best_child, ThoughtNode) else root

        return SearchResult(
            best_path=self._trace_path(best_child),
            best_score=best_child.value,
            nodes_explored=len(self._nodes),
            nodes_pruned=self._pruned_count,
            iterations=iterations,
            elapsed_ms=0.0,
        )

    def _mcts_select(self, node: ThoughtNode) -> ThoughtNode:
        """MCTS Selection: UCB1"""
        current = node
        while current.children_ids:
            best_ucb = -float("inf")
            best_child = current

            for cid in current.children_ids:
                child = self._nodes.get(cid)
                if not child:
                    continue
                if child.visits == 0:
                    return child

                # UCB = value/visits + C * sqrt(ln(parent_visits)/visits)
                exploitation = child.value / child.visits
                exploration = self.config.exploration_weight * math.sqrt(
                    math.log(current.visits + 1) / child.visits
                )
                ucb = exploitation + exploration

                if ucb > best_ucb:
                    best_ucb = ucb
                    best_child = child

            current = best_child
            if current.visits == 0:
                return current

        return current

    def _mcts_simulate(self, node: ThoughtNode) -> float:
        """MCTS Simulation: 快速 rollout"""
        # 简化的 rollout: 使用启发式评分
        current = node
        depth = node.depth
        value = current.score

        while depth < self.config.max_depth and random.random() < 0.5:
            # 模拟生成子节点 (不实际注册)
            value = value * 0.9 + random.random() * 0.1  # 模拟衰减
            depth += 1

        return max(0.0, min(1.0, value))

    def _mcts_backprop(self, node: ThoughtNode, value: float):
        """MCTS Backpropagation"""
        current_id = node.id
        while current_id:
            current = self._nodes.get(current_id)
            if not current:
                break
            current.visits += 1
            current.value += value
            current_id = current.parent_id or ""

    # ── 辅助方法 ─────────────────────────────────────

    def _expand_and_evaluate(self, node: ThoughtNode) -> list[ThoughtNode]:
        """展开节点 → 生成候选子节点 → 评估"""
        # 使用 expand_fn 生成候选
        candidates = self.expand_fn(node)

        children = []
        for candidate in candidates[:self.config.branch_factor]:
            child = ThoughtNode(
                id=self._new_id(),
                content=candidate.content if hasattr(candidate, 'content') else str(candidate),
                parent_id=node.id,
                depth=node.depth + 1,
            )
            # 评估
            child.score = self.evaluate_fn(child)
            node.children_ids.append(child.id)
            self._register_node(child)

            # 剪枝
            if child.score < self.config.min_score_threshold:
                self._pruned_count += 1
                continue

            children.append(child)

        return children

    def _trace_path(self, node: ThoughtNode) -> list[ThoughtNode]:
        """从节点回溯到根"""
        path = [node]
        current_id = node.parent_id
        while current_id:
            parent = self._nodes.get(current_id)
            if not parent:
                break
            path.append(parent)
            current_id = parent.parent_id or ""
        path.reverse()
        return path

    def _find_best_leaf(self, root: ThoughtNode) -> ThoughtNode:
        """找所有节点中评分最高的叶节点"""
        best = root
        best_score = root.score

        for node in self._nodes.values():
            if node.score > best_score:
                best_score = node.score
                best = node

        return best


# ── 图思维搜索器 ────────────────────────────────────────────

@dataclass
class GraphThoughtNode(ThoughtNode):
    """
    图思维节点 — 支持合并和协同操作

    与树节点的区别:
    - 可以有多个父节点 (merge_sources)
    - 支持聚合操作 (多个分支的结论合并)
    - 支持协同操作 (分支间互相增强)
    """
    merge_sources: list[str] = field(default_factory=list)
    aggregation_type: str = ""  # concat | vote | weighted_avg | llm_synthesis


class GraphThoughtSearch(ThoughtTreeSearch):
    """
    图思维搜索 (Graph of Thoughts)

    在 ToT 基础上，允许:
    1. 分支合并: 多个推理路径的结果合并为一个新节点
    2. 协同增强: 一个分支的结论可以增强另一个分支

    对应 GoT 论文的核心操作:
    - Aggregate: f(node_a, node_b) → node_c
    - Refine: g(node) → node'
    - Generate: 标准展开
    """

    def __init__(
        self,
        expand_fn: Callable,
        evaluate_fn: Callable,
        aggregate_fn: Optional[Callable] = None,  # (nodes: list[ThoughtNode]) → ThoughtNode
        config: Optional[SearchConfig] = None,
    ):
        super().__init__(expand_fn, evaluate_fn, config)
        self.aggregate_fn = aggregate_fn
        self._merge_candidates: list[tuple[str, str]] = []  # 待合并的节点对
        logger.info("GraphThoughtSearch initialized")

    def search(self, root: ThoughtNode) -> SearchResult:
        """图搜索: BFS 展开 + 定期合并"""
        result = super().search(root)

        # 后处理: 尝试合并高相似度分支
        if self.aggregate_fn:
            self._try_merge_branches()

        return result

    def _try_merge_branches(self):
        """尝试合并相似的分支"""
        nodes = list(self._nodes.values())
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i + 1:]:
                # 简单启发式: 同深度 + 相似内容
                if (
                    node_a.depth == node_b.depth
                    and self._similarity(node_a.content, node_b.content) > 0.7
                ):
                    self._merge_candidates.append((node_a.id, node_b.id))

        # 执行合并
        for id_a, id_b in self._merge_candidates[:5]:  # 限制合并次数
            node_a = self._nodes.get(id_a)
            node_b = self._nodes.get(id_b)
            if node_a and node_b and self.aggregate_fn:
                merged = self.aggregate_fn([node_a, node_b])
                if merged:
                    merged.id = self._new_id()
                    merged.merge_sources = [id_a, id_b]
                    merged.aggregation_type = "llm_synthesis"
                    merged.depth = max(node_a.depth, node_b.depth) + 1
                    merged.score = max(node_a.score, node_b.score) * 1.05  # 微奖励
                    self._register_node(merged)
                    logger.debug(f"Merged {id_a} + {id_b} → {merged.id}")

    def _similarity(self, text_a: str, text_b: str) -> float:
        """简单的 Jaccard 相似度"""
        if not text_a or not text_b:
            return 0.0
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)
