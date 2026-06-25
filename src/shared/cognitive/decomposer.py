"""
任务分解器 (Task Decomposer)
─────────────────────────────
将复杂研究问题分解为可执行的子任务。

支持三种范式:

1. CoT (Chain of Thought) — 线性分解
   输入: 复杂问题
   输出: [Step1, Step2, Step3, ...]  (线性序列)
   适用: 流程明确、步骤间有强依赖关系的任务

2. ToT (Tree of Thoughts) — 树状搜索
   输入: 复杂问题
   输出: 候选路径树, 支持 BFS/DFS 搜索 + 回溯
   适用: 存在多个可行路径、需要探索方案的任务

3. GoT (Graph of Thoughts) — 图状推理
   输入: 复杂问题
   输出: 有向无环图 (DAG), 支持分支合并与协同
   适用: 多分支可并行、结果需聚合的任务

策略选择:
   文献量 < 20       → ToT BFS (穷举探索)
   文献量 20-200     → CoT (分类归纳)
   文献量 > 200      → CoT (满意模式, 8-12篇即止)
   多分支协同        → GoT DAG
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


class DecompositionStrategy(str, Enum):
    """分解策略"""
    COT = "cot"            # Chain of Thought 线性分解
    TOT_BFS = "tot_bfs"    # Tree of Thoughts 广度优先
    TOT_DFS = "tot_dfs"    # Tree of Thoughts 深度优先
    GOT = "got"            # Graph of Thoughts DAG


class NodeStatus(str, Enum):
    """节点状态"""
    PENDING = "pending"
    EXPLORING = "exploring"
    EVALUATED = "evaluated"
    PRUNED = "pruned"           # 启发式评估后被剪枝
    SELECTED = "selected"       # 被选为执行路径
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ThoughtNode:
    """
    思维节点 — ToT/GoT 中的基本单元

    对应论文中 "thought" 的形式化:
    - 一个节点 = 一个推理步骤的候选方案
    - 每个节点可被启发式评估 (heuristic evaluation)
    - 节点间通过边连接 (依赖 / 协同)
    """
    id: str
    content: str                                  # 思维内容
    parent_id: Optional[str] = None               # 父节点 (树结构)
    children_ids: list[str] = field(default_factory=list)  # 子节点
    merge_sources: list[str] = field(default_factory=list) # GoT 合并来源

    # 评估
    score: float = 0.0                            # 启发式评分 (0-1)
    evaluation: str = ""                          # 评估理由

    # 执行
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[dict] = None

    # 元数据
    depth: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class DecompositionPlan:
    """
    分解计划 — 分解器的输出

    包含:
    - 线性步骤列表 (CoT 模式)
    - 思维树 (ToT 模式)
    - 思维图 (GoT 模式)
    """
    strategy: DecompositionStrategy
    question: str
    linear_steps: list[dict] = field(default_factory=list)
    tree_root: Optional[ThoughtNode] = None
    graph_nodes: dict[str, ThoughtNode] = field(default_factory=dict)
    graph_edges: list[tuple[str, str]] = field(default_factory=list)  # (from, to)
    metadata: dict = field(default_factory=dict)


class TaskDecomposer:
    """
    任务分解器

    根据问题复杂度和文献量自动选择分解策略。

    用法:
        decomposer = TaskDecomposer(model_client=deepseek)
        plan = await decomposer.decompose(
            question="综述近五年长江江豚被动声学监测研究进展",
            estimated_volume=45,  # 预估文献量
        )
    """

    def __init__(
        self,
        model_client: Any = None,
        default_strategy: DecompositionStrategy = DecompositionStrategy.COT,
    ):
        self.model = model_client
        self.default_strategy = default_strategy
        logger.info(f"TaskDecomposer initialized (default={default_strategy})")

    def select_strategy(
        self,
        question: str,
        estimated_volume: int = 0,
        has_parallel_branches: bool = False,
    ) -> DecompositionStrategy:
        """
        自适应策略选择

        规则:
            volume < 20          → ToT BFS (穷举, 一篇不漏)
            20 ≤ volume < 200    → CoT (分类归纳)
            volume ≥ 200         → CoT (满意模式)
            parallel_branches    → GoT DAG
        """
        if has_parallel_branches:
            return DecompositionStrategy.GOT
        elif estimated_volume < 20:
            return DecompositionStrategy.TOT_BFS
        else:
            return DecompositionStrategy.COT

    async def decompose(
        self,
        question: str,
        estimated_volume: int = 50,
        has_parallel_branches: bool = False,
        strategy: Optional[DecompositionStrategy] = None,
        max_branches: int = 5,
        max_depth: int = 4,
    ) -> DecompositionPlan:
        """
        分解复杂问题为可执行步骤

        Args:
            question: 研究问题
            estimated_volume: 预估文献/数据量
            has_parallel_branches: 是否有多分支协同需求
            strategy: 强制使用的策略 (None = 自动选择)
            max_branches: ToT/GoT 最大分支数
            max_depth: ToT 最大深度

        Returns:
            DecompositionPlan: 分解计划
        """
        strategy = strategy or self.select_strategy(
            question, estimated_volume, has_parallel_branches
        )
        logger.info(f"Decomposing with {strategy.value}: {question[:100]}")

        if strategy == DecompositionStrategy.COT:
            return await self._decompose_cot(question)
        elif strategy in (DecompositionStrategy.TOT_BFS, DecompositionStrategy.TOT_DFS):
            return await self._decompose_tot(
                question, strategy, max_branches, max_depth
            )
        elif strategy == DecompositionStrategy.GOT:
            return await self._decompose_got(
                question, max_branches, max_depth
            )
        else:
            return await self._decompose_cot(question)

    # ── CoT 线性分解 ─────────────────────────────────

    async def _decompose_cot(self, question: str) -> DecompositionPlan:
        """
        Chain of Thought 分解

        将问题拆解为线性的子任务序列。
        每个子任务有明确的依赖关系 (前置步骤完成才能开始下一步)。
        """
        # 基于领域模板 + LLM 细化
        steps = self._get_domain_template(question)

        if self.model:
            steps = await self._refine_with_llm(question, steps)

        return DecompositionPlan(
            strategy=DecompositionStrategy.COT,
            question=question,
            linear_steps=steps,
        )

    def _get_domain_template(self, question: str) -> list[dict]:
        """
        基于领域关键词匹配预定义模板

        这不是"硬编码" — 而是领域知识的工程化表达。
        LLM 可在后续 refine 阶段修改。
        """
        q = question.lower()

        # 文献综述模板
        if any(kw in q for kw in ["综述", "回顾", "进展", "review", "survey"]):
            return [
                {
                    "id": "cot-1", "description": "分解研究问题为3-5个子问题",
                    "action": "decompose_question", "action_type": "tool_call",
                    "dependencies": [],
                },
                {
                    "id": "cot-2", "description": "多源文献检索 (PubMed/Semantic Scholar/Google Scholar)",
                    "action": "search_literature", "action_type": "tool_call",
                    "dependencies": ["cot-1"],
                },
                {
                    "id": "cot-3", "description": "按标题+摘要进行相关性筛选 (高/中/低)",
                    "action": "filter_papers", "action_type": "tool_call",
                    "dependencies": ["cot-2"],
                },
                {
                    "id": "cot-4", "description": "深度阅读高相关文献，提取方法/数据/结论",
                    "action": "deep_read", "action_type": "tool_call",
                    "dependencies": ["cot-3"],
                },
                {
                    "id": "cot-5", "description": "交叉引用追踪 + 知识图谱更新",
                    "action": "citation_tracking", "action_type": "tool_call",
                    "dependencies": ["cot-4"],
                },
                {
                    "id": "cot-6", "description": "生成结构化综述草稿",
                    "action": "generate_report", "action_type": "tool_call",
                    "dependencies": ["cot-5"],
                },
            ]

        # 声学分析模板
        if any(kw in q for kw in ["声学", "acoustic", "click", "pam", "脉冲"]):
            return [
                {
                    "id": "ac-1", "description": "加载并验证音频数据",
                    "action": "load_acoustic_file", "action_type": "tool_call",
                    "dependencies": [],
                },
                {
                    "id": "ac-2", "description": "预处理: 带通滤波 100-180 kHz",
                    "action": "preprocess_audio", "action_type": "tool_call",
                    "dependencies": ["ac-1"],
                },
                {
                    "id": "ac-3", "description": "Click 脉冲检测 (SPL 阈值 -134 dB)",
                    "action": "detect_clicks", "action_type": "tool_call",
                    "dependencies": ["ac-2"],
                },
                {
                    "id": "ac-4", "description": "Click Train 提取 + Buzz 检测",
                    "action": "extract_click_trains", "action_type": "tool_call",
                    "dependencies": ["ac-3"],
                },
                {
                    "id": "ac-5", "description": "特征提取 (18+ 特征) + 分类",
                    "action": "extract_features", "action_type": "code_exec",
                    "dependencies": ["ac-4"],
                },
                {
                    "id": "ac-6", "description": "行为推断 + 昼夜节律分析",
                    "action": "behavior_inference", "action_type": "code_exec",
                    "dependencies": ["ac-5"],
                },
                {
                    "id": "ac-7", "description": "生成声学分析报告",
                    "action": "generate_report", "action_type": "tool_call",
                    "dependencies": ["ac-6"],
                },
            ]

        # 默认通用模板
        return [
            {
                "id": "gen-1", "description": "理解并澄清研究问题",
                "action": "clarify_question", "action_type": "tool_call",
                "dependencies": [],
            },
            {
                "id": "gen-2", "description": "检索相关知识 (文献/数据/记忆)",
                "action": "retrieve_knowledge", "action_type": "tool_call",
                "dependencies": ["gen-1"],
            },
            {
                "id": "gen-3", "description": "执行核心分析",
                "action": "execute_analysis", "action_type": "code_exec",
                "dependencies": ["gen-2"],
            },
            {
                "id": "gen-4", "description": "验证结果 + 生成报告",
                "action": "generate_report", "action_type": "tool_call",
                "dependencies": ["gen-3"],
            },
        ]

    async def _refine_with_llm(
        self, question: str, template_steps: list[dict]
    ) -> list[dict]:
        """使用 LLM 细化模板步骤"""
        if not self.model:
            return template_steps

        try:
            steps_text = "\n".join(
                f"{s['id']}: {s['description']}" for s in template_steps
            )
            response = await self.model.chat.completions.create(
                model="deepseek-chat",
                messages=[{
                    "role": "system",
                    "content": (
                        "你是一个任务分解专家。根据用户问题，优化以下步骤模板。"
                        "你可以: 增加/删除/重排步骤、修改描述、调整依赖关系。"
                        "保持 JSON 输出格式。"
                    ),
                }, {
                    "role": "user",
                    "content": f"问题: {question}\n\n模板步骤:\n{steps_text}",
                }],
                temperature=0.3,
                max_tokens=2048,
            )
            # 简化: 直接返回模板 (实际应 parse JSON)
            logger.debug("LLM refinement requested but using template fallback")
            return template_steps
        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}")
            return template_steps

    # ── ToT 树状搜索分解 ─────────────────────────────

    async def _decompose_tot(
        self,
        question: str,
        strategy: DecompositionStrategy,
        max_branches: int,
        max_depth: int,
    ) -> DecompositionPlan:
        """
        Tree of Thoughts 分解

        生成根节点 → 在每个深度层生成多个候选分支
        → 启发式评估 → 剪枝 → BFS/DFS 搜索最佳路径

        对应论文:
            Yao et al. (2023). Tree of Thoughts.
        """
        # 创建根节点
        root = ThoughtNode(
            id="tot-root",
            content=question,
            depth=0,
            status=NodeStatus.EXPLORING,
        )

        # BFS 或 DFS 搜索
        if strategy == DecompositionStrategy.TOT_BFS:
            selected = await self._tot_bfs(root, max_branches, max_depth)
        else:
            selected = await self._tot_dfs(root, max_branches, max_depth)

        # 从选中节点回溯路径
        linear_steps = self._trace_path(selected) if selected else []

        return DecompositionPlan(
            strategy=strategy,
            question=question,
            linear_steps=linear_steps,
            tree_root=root,
            metadata={
                "max_branches": max_branches,
                "max_depth": max_depth,
                "search_strategy": strategy.value,
                "selected_node": selected.id if selected else None,
            },
        )

    async def _tot_bfs(
        self,
        root: ThoughtNode,
        max_branches: int,
        max_depth: int,
    ) -> Optional[ThoughtNode]:
        """
        BFS 搜索思维树

        逐层展开 → 每层生成候选 → 评估 → 剪枝 → 保留下一步候选
        """
        current_level = [root]

        for depth in range(1, max_depth + 1):
            next_level = []

            for node in current_level:
                if node.status == NodeStatus.PRUNED:
                    continue

                # 生成候选子节点
                candidates = await self._generate_candidates(
                    node, max_branches, depth
                )

                # 启发式评估 + 排序
                for candidate in candidates:
                    self._heuristic_evaluate(candidate)
                    node.children_ids.append(candidate.id)
                    candidate.parent_id = node.id
                    candidate.depth = depth

                # 保留 top-k
                candidates.sort(key=lambda n: n.score, reverse=True)
                survivors = candidates[:max(1, max_branches // 2)]
                next_level.extend(survivors)

            # 深度限制
            if depth >= max_depth:
                break

            current_level = next_level

        # 返回评分最高的叶子节点
        all_leaves = [n for n in current_level if not n.children_ids]
        if not all_leaves:
            all_leaves = current_level

        if all_leaves:
            best = max(all_leaves, key=lambda n: n.score)
            best.status = NodeStatus.SELECTED
            return best

        return root

    async def _tot_dfs(
        self,
        root: ThoughtNode,
        max_branches: int,
        max_depth: int,
    ) -> Optional[ThoughtNode]:
        """
        DFS 搜索思维树

        沿一条路径深入 → 回溯到有希望的分支 → 重复
        """
        best_leaf: Optional[ThoughtNode] = None
        best_score = 0.0

        async def dfs(node: ThoughtNode, depth: int):
            nonlocal best_leaf, best_score

            if depth >= max_depth:
                if node.score > best_score:
                    best_score = node.score
                    best_leaf = node
                return

            candidates = await self._generate_candidates(node, max_branches, depth)
            for candidate in candidates:
                self._heuristic_evaluate(candidate)
                node.children_ids.append(candidate.id)
                candidate.parent_id = node.id
                candidate.depth = depth

            # 按评分排序，优先探索高分节点
            candidates.sort(key=lambda n: n.score, reverse=True)

            for candidate in candidates:
                if candidate.score < 0.3:
                    candidate.status = NodeStatus.PRUNED
                    continue
                candidate.status = NodeStatus.EXPLORING
                await dfs(candidate, depth + 1)

        await dfs(root, 0)

        if best_leaf:
            best_leaf.status = NodeStatus.SELECTED

        return best_leaf

    async def _generate_candidates(
        self, parent: ThoughtNode, n: int, depth: int
    ) -> list[ThoughtNode]:
        """
        为父节点生成候选子节点

        在真实场景中，这应该调用 LLM 生成多个候选方案。
        这里提供基于模板的启发式生成。
        """
        candidates = []

        # 基于深度和父节点内容生成候选
        templates_by_depth = {
            1: [
                "检索 PubMed 获取核心文献",
                "检索 Semantic Scholar 获取相关文献",
                "检索 Google Scholar 获取灰色文献",
                "查物种知识库获取背景信息",
            ],
            2: [
                "按标题筛选相关文献",
                "按摘要筛选相关文献",
                "按引用数排序筛选",
            ],
            3: [
                "深度阅读方法学部分",
                "提取关键数据和结论",
                "识别研究空白和争议",
            ],
            4: [
                "汇总所有发现",
                "生成结构化综述",
                "生成对比分析表",
            ],
        }

        templates = templates_by_depth.get(depth, [f"Step {depth} - 继续分析"])

        for i, template in enumerate(templates[:n]):
            candidates.append(ThoughtNode(
                id=f"{parent.id}-{i}",
                content=template,
                parent_id=parent.id,
                depth=depth,
            ))

        return candidates

    def _heuristic_evaluate(self, node: ThoughtNode):
        """
        启发式评估节点

        评估维度:
        - 可行性: 是否可执行?
        - 信息增益: 预期获得多少新信息?
        - 风险: 失败概率?
        """
        # 简化的启发式: 基于内容关键词打分
        content_lower = node.content.lower()
        score = 0.5  # 基线

        # 正向关键词
        if any(kw in content_lower for kw in ["pubmed", "检索", "文献", "综述"]):
            score += 0.2
        if any(kw in content_lower for kw in ["深度", "分析", "验证"]):
            score += 0.15
        if any(kw in content_lower for kw in ["生成", "汇总", "报告"]):
            score += 0.1

        # 负向 (过于宽泛)
        if any(kw in content_lower for kw in ["继续", "可能", "尝试"]):
            score -= 0.1

        node.score = max(0.0, min(1.0, score))
        node.evaluation = f"Heuristic score: {node.score:.2f}"

    def _trace_path(self, leaf: ThoughtNode) -> list[dict]:
        """从叶子节点回溯到根的路径"""
        path: list[ThoughtNode] = []
        current: Optional[ThoughtNode] = leaf

        while current is not None:
            path.append(current)
            # 找父节点 (简化: 通过 parent_id 和 id 匹配)
            # 实际实现需维护节点字典
            break  # 简化版只返回叶子

        path.reverse()
        return [
            {
                "id": node.id,
                "description": node.content,
                "action": "tool_call",
                "dependencies": [node.parent_id] if node.parent_id else [],
                "score": node.score,
            }
            for node in path
        ]

    # ── GoT 图状推理分解 ─────────────────────────────

    async def _decompose_got(
        self,
        question: str,
        max_branches: int,
        max_depth: int,
    ) -> DecompositionPlan:
        """
        Graph of Thoughts 分解

        生成 DAG: 节点 = 思维步骤, 边 = 依赖/协同
        支持:
        - 分支: 一个节点分出多个子节点 (并行探索)
        - 合并: 多个节点的结果汇聚到一个节点 (Aggregation)
        - 协同: 节点间交换信息 (Synergy)

        对应论文:
            Besta et al. (2024). Graph of Thoughts.
        """
        nodes: dict[str, ThoughtNode] = {}
        edges: list[tuple[str, str]] = []

        # 入口节点
        root = ThoughtNode(
            id="got-root",
            content=f"分析问题: {question[:100]}",
            depth=0,
            status=NodeStatus.EXPLORING,
        )
        nodes[root.id] = root

        # 分支层: 并行子任务
        parallel_tasks = self._get_parallel_tasks(question)
        for i, task in enumerate(parallel_tasks[:max_branches]):
            task_node = ThoughtNode(
                id=f"got-task-{i}",
                content=task,
                parent_id=root.id,
                depth=1,
                status=NodeStatus.PENDING,
            )
            nodes[task_node.id] = task_node
            edges.append((root.id, task_node.id))
            root.children_ids.append(task_node.id)

        # 聚合层: 合并并行结果
        aggregation = ThoughtNode(
            id="got-aggregate",
            content="聚合所有并行分支的结果, 去重并排序",
            depth=2,
            merge_sources=[t.id for t in nodes.values() if t.depth == 1],
            status=NodeStatus.PENDING,
        )
        nodes[aggregation.id] = aggregation
        for task_id in aggregation.merge_sources:
            edges.append((task_id, aggregation.id))

        # 输出层
        output = ThoughtNode(
            id="got-output",
            content="生成最终综合输出",
            parent_id=aggregation.id,
            depth=3,
            status=NodeStatus.PENDING,
        )
        nodes[output.id] = output
        edges.append((aggregation.id, output.id))
        aggregation.children_ids.append(output.id)

        # 线性化 (拓扑排序)
        linear_steps = self._topological_sort(nodes, edges)

        return DecompositionPlan(
            strategy=DecompositionStrategy.GOT,
            question=question,
            linear_steps=linear_steps,
            graph_nodes=nodes,
            graph_edges=edges,
            metadata={
                "n_nodes": len(nodes),
                "n_edges": len(edges),
                "has_parallel": len(root.children_ids) > 1,
                "has_merge": len(aggregation.merge_sources) > 1,
            },
        )

    def _get_parallel_tasks(self, question: str) -> list[str]:
        """获取可并行的子任务"""
        q = question.lower()

        if any(kw in q for kw in ["文献", "综述", "review"]):
            return [
                "PubMed 检索英文学术文献",
                "CNKI/万方检索中文学术文献",
                "Google Scholar 灰色文献 + 引用追踪",
                "检索物种知识库获取背景信息",
            ]
        elif any(kw in q for kw in ["声学", "acoustic", "pam"]):
            return [
                "加载并验证音频数据",
                "提取环境参数 (水深/温度/噪声)",
                "预处理: 带通滤波 + 脉冲检测",
                "参考历史数据对比分析",
            ]
        else:
            return [
                "检索相关文献",
                "查阅知识库",
                "分析历史数据",
            ]

    def _topological_sort(
        self,
        nodes: dict[str, ThoughtNode],
        edges: list[tuple[str, str]],
    ) -> list[dict]:
        """拓扑排序 DAG → 线性步骤"""
        # 简化: 按深度排序
        sorted_nodes = sorted(nodes.values(), key=lambda n: (n.depth, n.id))

        steps = []
        for node in sorted_nodes:
            deps = [
                src for src, dst in edges
                if dst == node.id and src in nodes
            ]
            steps.append({
                "id": node.id,
                "description": node.content,
                "action": "tool_call",
                "action_type": "tool_call",
                "dependencies": deps,
                "merge_sources": node.merge_sources,
            })

        return steps
