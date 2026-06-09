"""
eon-core 共享 Orchestrator 基类 — 提取 porpoise-agent 和 coilia-agent
的公共数据结构和管线模式。

用法:
    from eon_core.src.orchestrator_base import (
        ResearchPhase, PhaseResult, PipelineResult, VerificationStatus
    )

    class MyPhase(ResearchPhase):
        LITERATURE = "literature_review"
        ANALYSIS = "data_analysis"

    class MyOrchestrator:
        phases = [MyPhase.LITERATURE, MyPhase.ANALYSIS]
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Enums — shared across all domain projects
# ═══════════════════════════════════════════════════════════════


class VerificationStatus(str, Enum):
    """声明验证状态 — 控制输出门控。

    verified:     ≥2 独立来源 → 允许输出
    pending:      仅逻辑推断 → 允许带警告输出
    hypothesis:   有合理性但缺直接证据 → 允许带标记输出
    unverifiable: 无来源或验证路径 → 阻塞输出
    """
    VERIFIED = "verified"
    PENDING = "pending"
    HYPOTHESIS = "hypothesis"
    UNVERIFIABLE = "unverifiable"


class ContradictionType(str, Enum):
    """矛盾类型 — 决定处理策略。

    ANTAGONISTIC:     对抗性 — 必须解决, 输出阻塞
    NON_ANTAGONISTIC: 非对抗性 — 标注并存
    """
    ANTAGONISTIC = "antagonistic"
    NON_ANTAGONISTIC = "non_antagonistic"


# ═══════════════════════════════════════════════════════════════
# Dataclasses — shared result tracking structures
# ═══════════════════════════════════════════════════════════════


@dataclass
class PhaseResult:
    """单阶段执行结果。

    每个管线阶段返回此结构, 由 Orchestrator 聚合。
    """
    phase: str                                    # 阶段名称
    status: str = "completed"                     # completed | failed | skipped
    papers_found: int = 0                         # 本阶段发现的论文数
    tokens_used: int = 0                          # 本阶段消耗的 token
    findings: List[str] = field(default_factory=list)  # 关键发现
    sources: List[str] = field(default_factory=list)   # 引用来源
    errors: List[str] = field(default_factory=list)    # 错误信息
    verification: Optional[VerificationStatus] = None  # 验证状态


@dataclass
class PipelineResult:
    """完整管线执行结果。

    聚合所有阶段的 PhaseResult, 提供统一输出接口。
    """
    species: str = ""                                  # 目标物种
    question: str = ""                                 # 原始问题
    phases_executed: List[str] = field(default_factory=list)
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    total_papers: int = 0
    total_tokens: int = 0
    elapsed_sec: float = 0.0
    stop_reason: str = ""                              # satisfied | budget | dead_end
    synthesis: str = ""                                # 综合摘要

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species": self.species,
            "question": self.question,
            "phases_executed": self.phases_executed,
            "total_papers": self.total_papers,
            "total_tokens": self.total_tokens,
            "elapsed_sec": self.elapsed_sec,
            "stop_reason": self.stop_reason,
            "synthesis": self.synthesis,
            "phases": {
                k: {
                    "papers_found": v.papers_found,
                    "tokens_used": v.tokens_used,
                    "findings": v.findings,
                    "verification": v.verification.value if v.verification else None,
                }
                for k, v in self.phase_results.items()
            },
        }
