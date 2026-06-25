"""StateGraphTopology — LangGraph-inspired state graph for agent orchestration.

Replaces fixed topology types with conditional edge routing based on typed state.
Pattern: LangGraph StateGraph with nodes=agents, edges=transitions, state=typed dict.

Usage:
    graph = StateGraphTopology()
    graph.add_agent("literature", literature_agent)
    graph.add_agent("critic", critic_agent)
    graph.add_conditional_edge("literature", router_func, {"pass":"critic","fail":"literature"})
    result = graph.invoke({"query": "Coilia nasus migration"})
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypedDict
from enum import Enum


class AgentState(TypedDict, total=False):
    query: str
    findings: List[str]
    iteration: int
    max_iterations: int
    confidence: float
    errors: List[str]
    next_agent: str


@dataclass
class GraphNode:
    name: str
    agent: Any
    func: Optional[Callable] = None

@dataclass  
class GraphEdge:
    source: str
    target: str
    condition: Optional[Callable[[AgentState], bool]] = None


class StateGraphTopology:
    """LangGraph-inspired state graph for agent topology."""

    def __init__(self, max_iterations: int = 10):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._entry: str = ""
        self._max_iter = max_iterations

    def add_agent(self, name: str, agent: Any, func: Callable = None):
        self._nodes[name] = GraphNode(name=name, agent=agent, func=func)
        if not self._entry:
            self._entry = name

    def add_edge(self, source: str, target: str):
        self._edges.append(GraphEdge(source=source, target=target))

    def add_conditional_edge(self, source: str, condition: Callable[[AgentState], str],
                             targets: Dict[str, str]):
        """Conditional routing: condition(state) -> next_node_name."""
        for cond_val, target in targets.items():
            self._edges.append(GraphEdge(
                source=source, target=target,
                condition=lambda s, v=cond_val, c=condition: c(s) == v
            ))

    def invoke(self, state: AgentState) -> AgentState:
        """Execute the state graph from entry node."""
        current = self._entry
        state.setdefault('iteration', 0)
        state.setdefault('max_iterations', self._max_iter)
        state.setdefault('findings', [])
        state.setdefault('errors', [])

        while state['iteration'] < state['max_iterations']:
            node = self._nodes.get(current)
            if not node:
                break

            try:
                if node.func:
                    node.func(state)
                elif hasattr(node.agent, 'run'):
                    result = node.agent.run(state.get('query', ''))
                    if isinstance(result, dict):
                        state['findings'].extend(result.get('findings', []))
                state['confidence'] = min(1.0, state.get('confidence', 0.3) + 0.1)
            except Exception as e:
                state['errors'].append(f"{current}: {e}")

            state['iteration'] += 1
            state['next_agent'] = self._route(current, state)
            if state['next_agent'] == current:
                break
            current = state['next_agent']

        return state

    def _route(self, current: str, state: AgentState) -> str:
        for edge in self._edges:
            if edge.source == current:
                if edge.condition and not edge.condition(state):
                    continue
                return edge.target
        return current
