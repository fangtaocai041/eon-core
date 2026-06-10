"""OriginKernel — 协调内核 (道).

三生万物架构:
  道 (eon-core) → S(fish-ecology-assistant 知识) + T(cognitive-search-engine 搜索验证)
  → 万物: P₁(porpoise 江豚) + P₂(coilia 刀鲚) + P₃(culter 鲌类) + C(conflict 仲裁)

职责:
  1. 读取 coordination.yaml 配置
  2. 通过 project_loader 加载全部 7 项目适配器
  3. 对外暴露统一 API: search/lookup/health
  4. 健康检查: 每 5 秒轮询所有项目

不重叠:
  - 不实现任何搜索逻辑 (委托给 cognitive)
  - 不实现任何知识库逻辑 (委托给 fish)
  - 不实现任何领域逻辑 (委托给 porpoise/coilia/culter/conflict)
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("eon-core")


class OriginKernel:
    """统一协调内核 — 道.

    用法:
        kernel = OriginKernel()
        asyncio.run(kernel.bootstrap())
        result = kernel.search("珠星三块鱼")
        print(result.summary())
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or str(
            Path(__file__).resolve().parent.parent / "config" / "taiji.yaml"
        )
        self._adapters: Dict[str, Any] = {}
        self._workspace = None
        self._started_at: Optional[float] = None
        self._healthy = False

    async def bootstrap(self):
        """启动内核: 加载配置 + 项目适配器 + 启动健康检查."""
        self._started_at = time.time()
        _root = Path(__file__).resolve().parent.parent.parent

        # 加载 workspace 统一入口
        _ws_path = str(_root)
        import sys as _sys
        if _ws_path not in _sys.path:
            _sys.path.insert(0, _ws_path)
        from workspace import search_species, lookup_species, health_check
        self._workspace = {
            "search": search_species,
            "lookup": lookup_species,
            "health": health_check,
        }

        # 通过 project_loader 加载全部适配器
        from scripts.project_loader import (
            get_cognitive, get_fish, get_porpoise, get_coilia,
            get_culter, get_conflict,
        )
        projects = {
            "cognitive": get_cognitive,
            "fish": get_fish,
            "porpoise": get_porpoise,
            "coilia": get_coilia,
            "culter": get_culter,
            "conflict": get_conflict,
        }
        for name, loader in projects.items():
            try:
                self._adapters[name] = loader()
                logger.info(f"  ✅ {name} loaded")
            except Exception as e:
                logger.warning(f"  ⚠️  {name} failed: {e}")

        self._healthy = True
        logger.info(f"  ✅ eon-core 内核就绪 ({len(self._adapters)}/6 projects)")

    def search(self, query: str, **kwargs) -> Any:
        """统一搜索入口."""
        if not self._workspace:
            raise RuntimeError("Kernel not bootstrapped")
        return self._workspace["search"](query, **kwargs)

    def lookup(self, query: str) -> Dict[str, Any]:
        """知识库查询."""
        if not self._workspace:
            raise RuntimeError("Kernel not bootstrapped")
        return self._workspace["lookup"](query)

    def health(self) -> Dict[str, Any]:
        """全栈健康检查."""
        if not self._workspace:
            return {"status": "error", "error": "not bootstrapped"}
        result = self._workspace["health"]()
        result["eon_core"] = {
            "status": "healthy" if self._healthy else "degraded",
            "uptime_s": int(time.time() - (self._started_at or time.time())),
            "projects_loaded": len(self._adapters),
        }
        return result

    async def health_pulse(self):
        """每5秒健康心跳."""
        while True:
            try:
                self.health()
            except Exception:
                self._healthy = False
            await asyncio.sleep(5)
