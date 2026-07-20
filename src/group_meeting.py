"""GroupMeeting — 组会编排协议 (重构版).

融入现有体系:
  - 贝叶斯信念: 委托 _bayesian.BetaBelief (不再自计算)
  - 综述总结: 委托 review_synthesizer.ReviewSynthesizer
  - 跨项目调用: 委托 cross_adapters
  - 暴露接口: sphere_gateway HTTP endpoint
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── 知识库桥接 (延迟加载) ──
_KB_BRIDGE = None

def _get_kb():
    global _KB_BRIDGE
    if _KB_BRIDGE is None:
        try:
            from core.knowledge_base_bridge import get_kb_bridge
            _KB_BRIDGE = get_kb_bridge()
        except ImportError:
            try:
                import sys as _sys
                from pathlib import Path
                _p = str(Path(__file__).resolve().parent.parent.parent / "core")
                if _p not in _sys.path:
                    _sys.path.insert(0, _p)
                from knowledge_base_bridge import get_kb_bridge
                _KB_BRIDGE = get_kb_bridge()
            except Exception:
                _KB_BRIDGE = None
    return _KB_BRIDGE


@dataclass
class MeetingRecord:
    """一次组会记录."""
    round: int
    session_id: str
    timestamp: str = ""
    advisor_guidance: str = ""
    student_result: Dict[str, Any] = field(default_factory=dict)
    belief_before: float = 0.5
    belief_after: float = 0.5
    decisions: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")


@dataclass
class ResearchSession:
    """研究会话."""
    session_id: str
    topic: str
    created_at: str = ""
    rounds: List[MeetingRecord] = field(default_factory=list)
    status: str = "active"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")


class GroupMeeting:
    """组会编排器 — 导师-AI 博士生协作循环.

    核心循环: advisor.guide() -> AI.act() -> AI.report() -> belief.update()
    贝叶斯信念: 委托 _bayesian.BetaBelief (统一信任模型)
    组会总结: 委托 review_synthesizer (6阶段 RCCA 分析)
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, ResearchSession] = {}
        self._beta_belief = self._init_bayesian()

    @staticmethod
    def _init_bayesian() -> Any:
        """初始化贝叶斯信念模型."""
        try:
            from _bayesian import BetaBelief
            return BetaBelief(alpha=2, beta=2)
        except ImportError:
            return None

    @staticmethod
    def _get_synthesizer():
        """获取 review_synthesizer (延迟加载)."""
        try:
            from src.review_synthesizer import ReviewSynthesizer
            return ReviewSynthesizer(max_think_steps=4)
        except ImportError:
            try:
                from eon_core.src.review_synthesizer import ReviewSynthesizer
                return ReviewSynthesizer(max_think_steps=4)
            except ImportError:
                return None

    def start_session(self, topic: str) -> str:
        sid = f"gm-{uuid.uuid4().hex[:8]}"
        self._sessions[sid] = ResearchSession(session_id=sid, topic=topic)
        return sid

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [{
            "session_id": sid, "topic": s.topic,
            "status": s.status, "rounds": len(s.rounds),
            "created_at": s.created_at,
        } for sid, s in self._sessions.items()
          if status is None or s.status == status]

    def close_session(self, session_id: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            return {"status": "error", "error": f"Session not found: {session_id}"}
        sess.status = "completed"
        return {"status": "ok", "session_id": session_id,
                "total_rounds": len(sess.rounds)}

    def next_round(self, session_id: str, advisor_guidance: str) -> MeetingRecord:
        """新一轮组会: 导师给出指导, 记录当前信念."""
        sess = self._get_or_raise(session_id)
        round_num = len(sess.rounds) + 1

        # 用 BetaBelief 计算当前信念
        belief = self._compute_belief(sess)

        record = MeetingRecord(
            round=round_num,
            session_id=session_id,
            advisor_guidance=advisor_guidance,
            belief_before=belief,
        )
        sess.rounds.append(record)
        return record

    def report_back(self, session_id: str, result: Dict[str, Any],
                    decisions: Optional[List[str]] = None) -> MeetingRecord:
        """AI 博士生汇报: 更新信念, 记录决策."""
        sess = self._get_or_raise(session_id)
        if not sess.rounds:
            raise ValueError(f"No rounds started for {session_id}")

        current = sess.rounds[-1]
        current.student_result = result
        current.decisions = decisions or []

        # 信念更新: 委托 BetaBelief
        current.belief_after = self._update_belief(sess, result)
        return current

    def bayesian_summary(self, session_id: str) -> Dict[str, Any]:
        """贝叶斯总结: 置信度轨迹 + review_synthesizer 分析."""
        sess = self._get_or_raise(session_id)
        if not sess.rounds:
            return {"session_id": session_id, "rounds": 0}

        # 置信度轨迹
        trend = [r.belief_after for r in sess.rounds]

        # 尝试委托 review_synthesizer 生成深度分析
        syn = self._get_synthesizer()
        synopsis = ""
        if syn:
            try:
                from src.review_synthesizer import Paper
                papers = []
                for r in sess.rounds:
                    result = r.student_result
                    if result and result.get("key_findings"):
                        findings = "; ".join(result["key_findings"][:3])
                        papers.append(Paper(
                            title=f"Round {r.round}: {r.advisor_guidance[:60]}",
                            abstract=findings,
                        ))
                if papers:
                    review = syn.synthesize(papers, species=sess.topic)
                    synopsis = review.markdown[:2000] if review.markdown else ""
            except Exception:
                synopsis = "(synthesis via review_synthesizer unavailable)"

        # 知识库理论推荐
        kb = _get_kb()
        kb_suggestions = []
        if kb:
            try:
                kb_suggestions = kb.suggest_for_topic(sess.topic)
            except Exception:
                kb_suggestions = []

        return {
            "session_id": session_id,
            "topic": sess.topic,
            "total_rounds": len(sess.rounds),
            "status": sess.status,
            "confidence_trend": trend,
            "final_confidence": trend[-1] if trend else 0.5,
            "all_decisions": [d for r in sess.rounds for d in r.decisions],
            "synthesis": synopsis,
            "kb_suggestions": kb_suggestions,  # 生态学理论推荐
        }

    def confidence_trend(self, session_id: str) -> List[float]:
        sess = self._get_or_raise(session_id)
        return [r.belief_after for r in sess.rounds]

    def health(self) -> Dict[str, Any]:
        active = sum(1 for s in self._sessions.values() if s.status == "active")
        total_rounds = sum(len(s.rounds) for s in self._sessions.values())
        return {
            "name": "group-meeting",
            "available": True,
            "bayesian_available": self._beta_belief is not None,
            "review_synthesizer_available": self._get_synthesizer() is not None,
            "active_sessions": active,
            "total_sessions": len(self._sessions),
            "total_rounds": total_rounds,
        }

    # ── 内部 ──

    def _get_or_raise(self, session_id: str) -> ResearchSession:
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session not found: {session_id}")
        return sess

    def _compute_belief(self, sess: ResearchSession) -> float:
        """用 BetaBelief 计算当前信念均值."""
        if not self._beta_belief:
            return 0.5
        b = self._beta_belief.__class__(alpha=2, beta=2)
        for r in sess.rounds:
            if r.student_result:
                b.update(successes=1, trials=1)
        return round(b.mean(), 4)

    def _update_belief(self, sess: ResearchSession,
                       result: Dict[str, Any]) -> float:
        """信念更新: 成功/失败 + 证据强度."""
        if not self._beta_belief:
            return 0.5
        b = self._beta_belief.__class__(alpha=2, beta=2)
        for r in sess.rounds[:-1]:
            if r.student_result:
                b.update(successes=1, trials=1)
        # 本轮证据
        success = bool(result and result.get("status") == "ok")
        strength = self._evidence_strength(result)
        b.update(successes=strength if success else 0,
                 trials=strength)
        return round(b.mean(), 4)

    @staticmethod
    def _evidence_strength(result: Dict[str, Any]) -> int:
        """评估证据强度 (1-5)."""
        s = 1
        if result.get("papers_found"):
            s += min(result["papers_found"] // 5, 2)
        if result.get("key_findings"):
            s += min(len(result["key_findings"]), 2)
        if result.get("status") == "ok":
            s += 1
        return min(s, 5)


_instance: Optional[GroupMeeting] = None

def get_group_meeting() -> GroupMeeting:
    global _instance
    if _instance is None:
        _instance = GroupMeeting()
    return _instance
