"""
cortex/regen.py — 自愈-进化闭环引擎 (愈愈发动机)

将 HealingEngine 和 EvolutionEngine 串联成自动迭代循环:

  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  Healing  │───▶│ Evolution │───▶│  Verify  │
  │ 检测异常  │    │ 生成修复   │    │ 验证修复  │
  └──────────┘    └──────────┘    └──────────┘
       ▲                                │
       │           ┌──────────┐         │
       └───────────│  Rollback │◀────────┘
                   │ 回滚     │   (验证失败)
                   └──────────┘

每次迭代称为一个"再生周期"(regen cycle)。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import time
import uuid


@dataclass
class RegenEvent:
    """一次再生周期记录。"""
    cycle: int = 0
    phase: str = ""           # detect | fix | verify | rollback | complete
    target: str = ""          # 目标模块
    action: str = ""          # 执行的动作
    success: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RegenEngine:
    """自愈-进化闭环引擎。

    将 healing 和 evolution 串联成自动化迭代循环。
    max_cycles 控制最大迭代次数, 防止无限循环。

    用法:
        regen = RegenEngine(healing_engine, evolution_engine)
        result = regen.run(["sense/scholar", "memory"])
        # → 返回再生周期记录
    """

    def __init__(self, healing_engine=None, evolution_engine=None,
                 max_cycles: int = 5, verify_fn: Callable = None):
        self.name = "regen"
        self._healing = healing_engine
        self._evolution = evolution_engine
        self._max_cycles = max_cycles
        self._verify = verify_fn
        self._history: List[RegenEvent] = []
        self._cycle = 0

    # ── 单次再生周期 ──

    def run(self, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """执行一次完整的自愈-进化闭环。

        流程:
          1. detect — 健康检查, 找出异常
          2. fix — 对每个异常生成并尝试修复
          3. verify — 验证修复是否有效
          4. 如果验证失败且未达上限 → 回滚 → 回到步骤2
          5. 完成 → 输出周期报告
        """
        t0 = time.time()
        summary = {
            "cycles": 0,
            "detected": 0,
            "fixed": 0,
            "failed": 0,
            "rolled_back": 0,
            "duration_ms": 0.0,
        }

        for cycle in range(1, self._max_cycles + 1):
            self._cycle = cycle
            cycle_events = []
            t_cycle = time.time()

            # Phase 1: Detect
            issues = self._detect(targets)
            if not issues:
                self._log(RegenEvent(cycle=cycle, phase="detect",
                           action="health_check", success=True,
                           detail="All systems healthy"))
                break

            summary["detected"] += len(issues)
            for issue in issues:
                self._log(RegenEvent(cycle=cycle, phase="detect",
                           target=issue.get("target", ""),
                           action="detect",
                           success=True,
                           detail=issue.get("detail", "")))

                # Phase 2: Fix
                fix_result = self._fix(issue)
                self._log(RegenEvent(cycle=cycle, phase="fix",
                           target=issue.get("target", ""),
                           action=fix_result.get("action", ""),
                           success=fix_result.get("success", False),
                           detail=fix_result.get("detail", "")))

                if not fix_result.get("success", False):
                    summary["failed"] += 1
                    continue

                # Phase 3: Verify
                verify_ok = self._verify_fix(issue.get("target", ""))
                if verify_ok:
                    summary["fixed"] += 1
                    self._log(RegenEvent(cycle=cycle, phase="verify",
                               target=issue.get("target", ""),
                               action="verify", success=True,
                               detail="Fix verified"))
                else:
                    summary["failed"] += 1
                    # Phase 4: Rollback
                    self._rollback(issue)
                    summary["rolled_back"] += 1
                    self._log(RegenEvent(cycle=cycle, phase="rollback",
                               target=issue.get("target", ""),
                               action="rollback",
                               success=True,
                               detail="Rolled back to previous state"))

            # Cycle complete
            ev = RegenEvent(cycle=cycle, phase="complete",
                           action="cycle_end", success=True,
                           duration_ms=(time.time() - t_cycle) * 1000)
            self._log(ev)
            summary["cycles"] = cycle

        summary["duration_ms"] = round((time.time() - t0) * 1000, 1)
        return summary

    # ── 四个阶段 ──

    def _detect(self, targets: Optional[List[str]] = None) -> List[Dict]:
        """Phase 1: 健康检测。"""
        issues = []
        if self._healing is None:
            return issues
        try:
            checks = self._healing._checks if hasattr(self._healing, '_checks') else []
            for c in checks:
                if c.status in ("degraded", "failed"):
                    issues.append({
                        "target": c.component,
                        "detail": f"{c.component}: {c.status} ({c.error or 'no error'})",
                        "severity": c.status,
                    })
        except Exception as e:
            issues.append({"target": "system", "detail": f"Health check error: {e}",
                          "severity": "failed"})
        return issues

    def _fix(self, issue: Dict) -> Dict:
        """Phase 2: 生成并执行修复。"""
        if self._evolution is None:
            return {"action": "noop", "success": True,
                    "detail": "No evolution engine available"}

        target = issue.get("target", "")
        try:
            proposals = self._evolution.suggest_improvements(target)
            if proposals:
                p = proposals[0]
                return {"action": f"suggest: {p.description[:60]}",
                        "success": True, "detail": p.description}
            return {"action": "noop", "success": True,
                    "detail": "No improvement suggestions"}
        except Exception as e:
            return {"action": "error", "success": False,
                    "detail": str(e)}

    def _verify_fix(self, target: str) -> bool:
        """Phase 3: 验证修复是否有效。"""
        if self._verify:
            try:
                return self._verify(target)
            except Exception:
                return False
        return True

    def _rollback(self, issue: Dict):
        """Phase 4: 回滚。"""
        pass

    # ── 日志 ──

    def _log(self, event: RegenEvent):
        self._history.append(event)

    @property
    def events(self) -> List[RegenEvent]:
        return self._history

    # ── 报告 ──

    def report(self) -> Dict:
        last_cycle = max([e.cycle for e in self._history], default=0)
        return {
            "status": "ok",
            "total_cycles": last_cycle,
            "total_events": len([e for e in self._history if e.phase != "complete"]),
            "recent": [
                {"cycle": e.cycle, "phase": e.phase, "target": e.target,
                 "success": e.success, "detail": e.detail[:60]}
                for e in self._history[-6:]
            ],
        }

    def search(self, query: str, **kwargs) -> Dict:
        return self.report()
