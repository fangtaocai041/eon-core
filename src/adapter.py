"""EonCoreAdapter — eon-core coordinator adapter."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict

from _shared.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class EonCoreAdapter(BaseAdapter):
    project_name = "eon-core"
    _core_attr = "_kernel"
    role = "coordinator"
    version = "v7.3.0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._group_meeting: Any = None
        self._init_group_meeting()

    def _init_group_meeting(self):
        """P2: Init GroupMeeting (sub-PHD advisor-student loop)."""
        try:
            from .group_meeting import get_group_meeting
            self._group_meeting = get_group_meeting()
        except ImportError:
            try:
                # fallback: direct import when __package__ not set
                import sys as _sys
                _gp = str(Path(__file__).resolve().parent)
                if _gp not in _sys.path:
                    _sys.path.insert(0, _gp)
                from group_meeting import get_group_meeting as _ggm
                self._group_meeting = _ggm()
            except Exception as exc:
                logger.warning(f"GroupMeeting init failed: {exc}")

    def _init_engine(self, **kwargs):
        try:
            # pip 安装后: from kernel.origin import OriginKernel
            from kernel.origin import OriginKernel
        except ImportError:
            try:
                # 未安装时: 直接文件导入
                import importlib.util
                _p = Path(__file__).resolve().parent / "kernel" / "origin.py"
                _spec = importlib.util.spec_from_file_location("origin", str(_p))
                _mod = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                OriginKernel = _mod.OriginKernel
            except Exception:
                raise ImportError("OriginKernel not found via pip or direct path")
        try:
            self._kernel = OriginKernel()
            self._engine = self._kernel
        except Exception as exc:
            logger.debug("eon-core OriginKernel init failed: %s", exc)
            self._kernel = None

    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        if self._kernel and hasattr(self._kernel, 'route_event'):
            try:
                event = {
                    "query": query,
                    "species": kwargs.get("species", query),
                    "action": kwargs.get("action", "SEARCH"),
                    "domain": kwargs.get("domain", ""),
                }
                result = self._kernel.route_event(event)
                return {
                    "status": "ok", "kernel": "OriginKernel",
                    "chain": getattr(result, "vertex_chain", []),
                    "trace_id": getattr(result, "trace_id", ""), "result": result,
                }
            except Exception as exc:
                return {"status": "error", "error": str(exc), "query": query}
        return {
            "status": "standalone", "query": query,
            "note": "OriginKernel not bootstrapped",
            "topology": self._topology_snapshot(),
        }

    def _extend_health(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "role": self.role,
            "architecture": "OriginKernel + EventBus + DAG",
            "note": "kernel instance exists" if self._kernel else "kernel not bootstrapped",
        }

    def fast_search(self, query: str) -> Dict[str, Any]:
        try:
            from .cross_adapters import CrossProjectPipeline
            return CrossProjectPipeline().run(query, route="standard")
        except Exception as e:
            return {"query": query, "error": str(e)[:60], "fast_path": True}

    def deep_analyze(self, query: str) -> Dict[str, Any]:
        try:
            from .cross_adapters import CrossProjectPipeline
            return CrossProjectPipeline().run(query, route="full")
        except Exception as e:
            return {"query": query, "error": str(e)[:60]}

    def _topology_snapshot(self) -> Dict[str, Any]:
        return {
            "vertices": {
                "V0": {"project": "fish-ecology-assistant", "polarity": "yin"},
                "V1": {"project": "cognitive-search-engine", "polarity": "yang"},
                "V2": {"project": "porpoise-agent", "polarity": "yin"},
                "V3": {"project": "coilia-agent", "polarity": "yang"},
                "V4": {"project": "culter-agent", "polarity": "yin"},
                "V5": {"project": "conflict-arbiter", "polarity": "fire"},
            },
            "pathways": {
                "P1": "V0(fish) -> V1(cognitive)",
                "P2": "V1 -> V0",
                "P3": "V1 -> V2|V3|V4",
                "P4": "any -> V5(conflict)",
            },
        }

    def info(self) -> Dict[str, Any]:
        """P2: Version + capabilities + group_meeting."""
        caps = [
            "orchestration", "event_routing", "cross_project_pipeline",
            "emergence_detection", "topology_management",
        ]
        gm_ok = bool(self._group_meeting)
        if gm_ok:
            caps.append("group_meeting")
        return {
            "project": self.project_name,
            "version": self.version,
            "role": self.role,
            "capabilities": caps,
            "group_meeting_available": gm_ok,
            "architecture": "OriginKernel + EventBus + DAG",
        }

    # ── P2: GroupMeeting proxy methods ──

    def gm_start_session(self, topic: str) -> Dict[str, Any]:
        """开始一个组会会话（导师设定研究主题）. AI 博士生开始工作."""
        if not self._group_meeting:
            return {"status": "unavailable", "note": "GroupMeeting not loaded"}
        sid = self._group_meeting.start_session(topic)
        return {"status": "ok", "session_id": sid, "topic": topic,
                "message": f"组会开始，主题：{topic}"}

    def gm_next_round(self, session_id: str, advisor_guidance: str) -> Dict[str, Any]:
        """新一轮组会 — 导师给出指导."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        record = self._group_meeting.next_round(session_id, advisor_guidance)
        return {"status": "ok", "record": record}

    def gm_report_back(self, session_id: str, result: dict,
                        decisions: list = None) -> Dict[str, Any]:
        """AI 博士生汇报实验结果."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        record = self._group_meeting.report_back(session_id, result, decisions=decisions)
        return {"status": "ok", "record": record}

    def gm_bayesian_summary(self, session_id: str) -> Dict[str, Any]:
        """贝叶斯总结 — 学习轨迹和置信度演变."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        return self._group_meeting.bayesian_summary(session_id)

    def gm_list_sessions(self) -> Dict[str, Any]:
        """列出所有组会会话."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        return {"status": "ok", "sessions": self._group_meeting.list_sessions()}

    def gm_close_session(self, session_id: str) -> Dict[str, Any]:
        """结束组会会话."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        return self._group_meeting.close_session(session_id)

    def gm_confidence_trend(self, session_id: str) -> Dict[str, Any]:
        """返回置信度趋势."""
        if not self._group_meeting:
            return {"status": "unavailable"}
        return {"status": "ok", "trend": self._group_meeting.confidence_trend(session_id)}

    def gm_health(self) -> Dict[str, Any]:
        """组会系统健康."""
        if not self._group_meeting:
            return {"name": "group-meeting", "available": False}
        return self._group_meeting.health()


def get_adapter(**kwargs):
    return EonCoreAdapter(**kwargs)
