"""
eon-core/shared/cognitive — 通用认知引擎 (源自 porpoise-agent P₁)

BDI/ReAct/Reflexion/Decomposer — 所有 Agent 项目共享的认知架构原语。
"""

from .bdi import (
    BDIStatus, Belief, Desire, Intention, StepStatus, PlanStep, BDICoordinator,
)
from .react_loop import (
    LoopStatus, ReActStep, ReActContext, ReActLoop,
)
from .reflexion import (
    ReflectionType, Severity, Reflection, CreditNode,
    Critic, CreditAssigner, FeedbackLoop,
)
from .decomposer import (
    DecompositionStrategy, NodeStatus, ThoughtNode,
    DecompositionPlan, TaskDecomposer,
)
from .search import (
    SearchStrategy, ThoughtNode as SearchThoughtNode,
    SearchResult, SearchConfig, ThoughtTreeSearch,
    GraphThoughtNode, GraphThoughtSearch,
)
from .stategraph import (
    AgentState, GraphNode, GraphEdge, StateGraphTopology,
)

__all__ = [
    "BDIStatus", "Belief", "Desire", "Intention", "StepStatus", "PlanStep", "BDICoordinator",
    "LoopStatus", "ReActStep", "ReActContext", "ReActLoop",
    "ReflectionType", "Severity", "Reflection", "CreditNode", "Critic", "CreditAssigner", "FeedbackLoop",
    "DecompositionStrategy", "NodeStatus", "ThoughtNode", "DecompositionPlan", "TaskDecomposer",
    "SearchStrategy", "SearchResult", "SearchConfig", "ThoughtTreeSearch",
    "GraphThoughtNode", "GraphThoughtSearch",
    "AgentState", "GraphNode", "GraphEdge", "StateGraphTopology",
]
