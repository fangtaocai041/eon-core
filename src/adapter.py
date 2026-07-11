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

    def health(self) -> Dict[str, Any]:
        base = {
            "project": self.project_name, "version": self.version,
            "role": self.role, "architecture": "OriginKernel + EventBus + DAG",
        }
        if self._kernel:
            base["status"] = "HEALTHY"
            base["note"] = "kernel instance exists"
        else:
            base["status"] = "STANDBY"
            base["note"] = "kernel not bootstrapped"
        try:
            from _bayesian import BetaBelief
            b = BetaBelief(alpha=10, beta=3)
            if base["status"] == "HEALTHY":
                b.update(successes=1, trials=1)
            base["bayesian_coordination_confidence"] = round(b.mean(), 4)
        except ImportError:
            pass
        return base

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


def get_adapter(**kwargs):
    return EonCoreAdapter(**kwargs)
