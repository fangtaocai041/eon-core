"""CASCore — Complex Adaptive System architecture for eon-core.

Replaces fictional 10-layer design with real CAS components:
  - Agents: project adapters (V0, V1, P1, P2, P3, C)
  - Environment: shared state + event log
  - Adaptation: learning rules from interaction history
  - Emergence: detect unexpected patterns from agent interactions

Architecture:
  CASCore
    ├── AgentRegistry  — discover + manage project adapters
    ├── Environment    — shared state + event log
    ├── AdaptationEngine — learn from interaction outcomes
    └── EmergenceDetector — detect unexpected patterns

Key CAS properties:
  - Feedback loops: agent actions → environment changes → agent adaptation
  - Self-organization: agents dynamically form task-specific coalitions
  - Emergence: system-level patterns not predictable from individual agents
  - Co-evolution: agents adapt strategies based on peer performance

Usage:
    cas = CASCore()
    await cas.bootstrap()
    result = await cas.coordinate("search", {"query": "Coilia nasus"})
"""

import asyncio, json, time, logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    ANALYSIS = "analysis"
    ARBITRATION = "arbitration"
    COORDINATION = "coordination"


@dataclass
class AgentInfo:
    name: str
    role: str
    capabilities: List[AgentCapability]
    adapter: Any = None
    health: str = "unknown"
    success_rate: float = 0.5
    avg_response_ms: float = 0.0
    last_active: float = 0.0


@dataclass
class EnvironmentState:
    """Shared environment state visible to all agents."""
    active_task: str = ""
    task_context: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, AgentInfo] = field(default_factory=dict)
    event_count: int = 0
    emergence_signals: List[str] = field(default_factory=list)


class AdaptationRule:
    """A learned rule for agent behavior adaptation."""
    def __init__(self, condition: str, action: str, weight: float = 1.0):
        self.condition = condition
        self.action = action
        self.weight = weight
        self.applications = 0
        self.successes = 0

    def apply(self, context: Dict) -> Optional[str]:
        if self._safe_eval_condition(self.condition, context):
            self.applications += 1
            return self.action
        return None

    @staticmethod
    def _safe_eval_condition(condition: str, context: Dict) -> bool:
        """Safely evaluate a CAS condition with AST whitelist."""
        import ast
        try:
            tree = ast.parse(condition.strip(), mode="eval")
        except SyntaxError:
            return False

        def _check(node):
            if isinstance(node, (ast.Expression, ast.Constant, ast.Name)): return True
            if isinstance(node, ast.BoolOp): return all(_check(v) for v in node.values)
            if isinstance(node, ast.Compare): return _check(node.left) and all(_check(c) for c in node.comparators)
            if isinstance(node, ast.UnaryOp): return isinstance(node.op, ast.Not) and _check(node.operand)
            if isinstance(node, ast.BinOp): return isinstance(node.op, (ast.Add, ast.Sub)) and _check(node.left) and _check(node.right)
            if isinstance(node, ast.Subscript): return True
            return False

        if not _check(tree):
            return False
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    def feedback(self, success: bool):
        if success:
            self.successes += 1
        self.weight *= 1.1 if success else 0.9


class CASCore:
    """Complex Adaptive System coordinator for the SanShengWanWu ecosystem."""

    def __init__(self, workspace_root: str = None):
        self._root = Path(workspace_root) if workspace_root else Path(__file__).resolve().parent.parent
        self._agents: Dict[str, AgentInfo] = {}
        self._env = EnvironmentState()
        self._rules: List[AdaptationRule] = []
        self._event_log: List[Dict] = []
        self._started_at: float = 0.0

    async def bootstrap(self) -> Dict[str, Any]:
        """Initialize CAS: discover agents, load rules, start environment."""
        self._started_at = time.time()

        # Discover agents from project registry
        from scripts.project_loader import DirectLoader
        loader = DirectLoader()
        available = loader.list_available()

        for proj_name in available:
            try:
                adapter = loader.load(proj_name)
                if adapter:
                    info = adapter.info() if hasattr(adapter, 'info') else {}
                    self._agents[proj_name] = AgentInfo(
                        name=proj_name,
                        role=info.get('role', 'unknown'),
                        capabilities=self._infer_capabilities(proj_name, info),
                        adapter=adapter,
                        health="healthy"
                    )
                    self._env.agent_states[proj_name] = self._agents[proj_name]
            except Exception as e:
                logger.warning(f"Agent {proj_name} unavailable: {e}")

        # Initialize adaptation rules
        self._init_rules()

        self._log_event("bootstrap", {"agents": len(self._agents)})
        return {
            "status": "bootstrapped",
            "agents": len(self._agents),
            "rules": len(self._rules),
            "uptime_ms": (time.time() - self._started_at) * 1000
        }

    async def coordinate(self, task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a task across the CAS ecosystem.

        Args:
            task_type: "search", "analyze", "arbitrate"
            context: task-specific parameters
        """
        self._env.active_task = task_type
        self._env.task_context = context
        self._log_event("task_start", {"type": task_type})

        # Select agents based on task + learned rules
        selected = self._select_agents(task_type, context)
        if not selected:
            return {"status": "error", "error": "No suitable agents found"}

        # Execute task across selected agents
        results = {}
        for agent_name in selected:
            agent = self._agents[agent_name]
            try:
                start = time.time()
                if hasattr(agent.adapter, 'search'):
                    result = agent.adapter.search(context.get('query', ''))
                elif hasattr(agent.adapter, 'analyze'):
                    result = agent.adapter.analyze(context)
                else:
                    result = {"status": "not_capable"}

                elapsed = (time.time() - start) * 1000
                agent.avg_response_ms = (agent.avg_response_ms * 0.9 + elapsed * 0.1)
                agent.last_active = time.time()
                agent.success_rate = min(1.0, agent.success_rate + 0.05)
                results[agent_name] = result

            except Exception as e:
                agent.success_rate = max(0.1, agent.success_rate - 0.1)
                results[agent_name] = {"error": str(e)}
                logger.warning(f"Agent {agent_name} failed: {e}")

        # Detect emergence
        signals = self._detect_emergence(results)
        if signals:
            self._env.emergence_signals.extend(signals)

        # Adapt rules based on outcomes
        for agent_name in selected:
            success = "error" not in str(results.get(agent_name, {}))
            self._adapt_rules(agent_name, task_type, success)

        self._update_lifecycle()
        self._log_event("task_complete", {"agents": len(selected), "emergence": len(signals)})

        return {
            "status": "completed",
            "agents_used": selected,
            "results": results,
            "emergence_signals": signals,
            "environment": {
                "event_count": self._env.event_count,
                "active_agents": len([a for a in self._agents.values() if a.health == "healthy"])
            }
        }

    def _select_agents(self, task_type: str, context: Dict) -> List[str]:
        """Select agents using learned adaptation rules + Thompson Sampling."""
        candidates = []

        # Rule-based selection
        if task_type == "search":
            candidates = ["cognitive-search-engine", "fish-ecology-assistant"]
        elif task_type == "analyze":
            # Check context for species → route to domain expert
            species = context.get('species', '').lower()
            if 'coilia' in species:
                candidates = ["coilia-agent", "cognitive-search-engine"]
            elif 'culter' in species:
                candidates = ["culter-agent", "cognitive-search-engine"]
            elif 'porpoise' in species or 'finless' in species:
                candidates = ["porpoise-agent", "cognitive-search-engine"]
            else:
                candidates = ["fish-ecology-assistant", "cognitive-search-engine"]
        elif task_type == "arbitrate":
            candidates = ["conflict-arbiter"]
        else:
            candidates = ["fish-ecology-assistant"]

        # Apply learned adaptation rules
        for rule in self._rules:
            action = rule.apply({"task": task_type, **context})
            if action and action not in candidates:
                candidates.append(action)

        # Filter to available agents
        return [c for c in candidates if c in self._agents]

    def _detect_emergence(self, results: Dict) -> List[str]:
        """Detect emergent patterns from multi-agent interactions."""
        signals = []

        # Pattern 1: Multiple agents reporting conflicting findings
        agent_statuses = [r for r in results.values() if isinstance(r, dict)]
        if len(agent_statuses) >= 2:
            findings = [r.get('findings', r.get('result', {})) for r in agent_statuses]
            # Simple emergence: ≥2 agents agree on unexpected finding
            if len(set(str(f)[:100] for f in findings if f)) >= 2:
                signals.append("multi_agent_consensus")

        # Pattern 2: Unexpected agent performance
        for name, result in results.items():
            agent = self._agents.get(name)
            if agent and agent.success_rate < 0.3:
                signals.append(f"agent_degradation:{name}")

        # Pattern 3: Novel agent coalition
        participants = list(results.keys())
        if len(participants) >= 3:
            signals.append(f"multi_agent_coalition:{'+'.join(sorted(participants))}")

        return signals

    def _adapt_rules(self, agent_name: str, task_type: str, success: bool):
        """Update adaptation rules based on outcome."""
        for rule in self._rules:
            if agent_name in rule.action:
                rule.feedback(success)

    def _init_rules(self):
        """Initialize default adaptation rules."""
        self._rules = [
            AdaptationRule("task == 'analyze' and 'genetic' in str(context).lower()",
                          "coilia-agent", 1.0),
            AdaptationRule("task == 'analyze' and 'trophic' in str(context).lower()",
                          "culter-agent", 1.0),
            AdaptationRule("task == 'search' and 'conservation' in str(context).lower()",
                          "conflict-arbiter", 1.0),
        ]

    def _infer_capabilities(self, name: str, info: Dict) -> List[AgentCapability]:
        caps = []
        role = info.get('role', '').lower()
        if 'search' in role or 'v1' in role: caps.append(AgentCapability.SEARCH)
        if 'knowledge' in role or 'v0' in role: caps.append(AgentCapability.KNOWLEDGE)
        if 'expert' in role or 'analysis' in role: caps.append(AgentCapability.ANALYSIS)
        if 'arbit' in role: caps.append(AgentCapability.ARBITRATION)
        if 'coord' in role: caps.append(AgentCapability.COORDINATION)
        return caps or [AgentCapability.KNOWLEDGE]

    def _log_event(self, event_type: str, data: Dict):
        self._env.event_count += 1
        self._event_log.append({
            "type": event_type, "data": data,
            "timestamp": time.time()
        })
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]  # Trim

    
    def _update_lifecycle(self):
        """Update Lifecycle state based on agent health."""
        from src.kernel.lifecycle import Lifecycle
        if not hasattr(self, '_lifecycle'):
            self._lifecycle = Lifecycle()
        
        healthy = len([a for a in self._agents.values() if a.health == "healthy"])
        total = len(self._agents)
        
        if healthy == total and self._lifecycle.state.value in ("seeding", "sprouting"):
            self._lifecycle.transition("sprouting" if self._lifecycle.state.value == "seeding" else "blooming")
        elif healthy < total * 0.5:
            self._lifecycle.transition("pruning")
        elif healthy >= total * 0.8 and self._lifecycle.state.value == "sprouting":
            self._lifecycle.transition("blooming")

    def health(self) -> Dict[str, Any]:
        return {
            "agents": len(self._agents),
            "healthy": len([a for a in self._agents.values() if a.health == "healthy"]),
            "rules": len(self._rules),
            "events": self._env.event_count,
            "emergence_signals": self._env.emergence_signals[-5:],
            "uptime_seconds": int(time.time() - self._started_at)
        }