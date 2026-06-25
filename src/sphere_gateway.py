"""
sphere_gateway.py — SphereGateway 圆球体网关

统一的 HTTP API 入口，将 workspace 所有能力暴露为 RESTful 服务。

启动:
    uvicorn eon_core.sphere_gateway:app --host 0.0.0.0 --port 8000 --reload
    或
    python -m eon_core.sphere_gateway

端点:
    GET  /health             全项目健康仪表盘
    GET  /api/v1/domains      12 领域知识图谱
    POST /api/v1/search       物种文献搜索
    GET  /api/v1/lookup       知识库查询
    POST /api/v1/arbitrate    保护等级冲突仲裁
    GET  /api/v1/emergence    涌现信号查询
    GET  /api/v1/traits       物种形态性状 (FISHMORPH)

设计参考: FastAPI 最佳实践、OpenAPI 自动文档、统一响应格式
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Path setup — 确保 workspace 和共享模块可导入 ──
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SHARED = str(_ROOT / "eon-core" / "src" / "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sphere-gateway")

# ── App ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    _load_workspace()
    _load_domains()
    _load_fishmorph()
    _load_emergence()
    elapsed = (time.perf_counter() - t0) * 1000
    loaded = sum(1 for v in _startup_ok.values() if v)
    total = len(_startup_ok)
    logger.info(f"SphereGateway ready — {loaded}/{total} services ({elapsed:.0f}ms)")
    yield


app = FastAPI(
    title="SphereGateway",
    description="三生万物工作区统一 API 网关",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Response Models ───────────────────────────────────────────────────

class APIResponse(BaseModel):
    status: str = "ok"
    data: Any = None
    elapsed_ms: float = 0
    error: Optional[str] = None


class SearchRequest(BaseModel):
    species: str = Field(..., description="物种中文名或学名", examples=["刀鲚"])
    group: str = Field("standard", description="搜索模式: quick/standard/full/chinese/preprint/species")
    limit: int = Field(10, ge=1, le=100)


class ArbitrateRequest(BaseModel):
    species: str = Field(..., examples=["鳤"])
    sources: List[Dict[str, str]] = Field(default=[], description="保护等级来源列表")
    region: str = Field("china", description="区域策略: china/global")


class TraitsQuery(BaseModel):
    name: str = Field(..., examples=["Coilia nasus"])


# ── Lazy Service Loader ───────────────────────────────────────────────

_services: Dict[str, Any] = {}
_startup_ok: Dict[str, bool] = {}


def _get_service(name: str):
    if name in _services:
        return _services[name]
    return None


def _load_workspace():
    """延迟加载 workspace 统一入口。"""
    if "workspace" in _services:
        return
    try:
        from workspace import (
            search_species, lookup_species, assess_conflict,
            health_check, senses_health,
        )
        _services["workspace"] = True
        _services["search"] = search_species
        _services["lookup"] = lookup_species
        _services["arbitrate"] = assess_conflict
        _services["health_check"] = health_check
        _services["senses_health"] = senses_health
        _startup_ok["workspace"] = True
        logger.info("workspace 已加载")
    except Exception as e:
        _startup_ok["workspace"] = False
        logger.warning(f"workspace 加载失败: {e}")


def _load_fishmorph():
    if "fishmorph" in _services:
        return
    try:
        csv_path = Path(__file__).resolve().parent.parent.parent / "fish-ecology-assistant" / "data" / "fishmorph" / "fishmorph.csv"
        if csv_path.exists():
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "fish-ecology-assistant" / "src"))
            from fishmorph_loader import FishmorphLoader
            loader = FishmorphLoader(str(csv_path))
            loader.load()
            _services["fishmorph"] = loader
            _startup_ok["fishmorph"] = True
            logger.info(f"FISHMORPH 已加载: {len(loader._by_species)} species")
        else:
            _startup_ok["fishmorph"] = False
            logger.info("FISHMORPH 数据未下载")
    except Exception as e:
        _startup_ok["fishmorph"] = False
        logger.warning(f"FISHMORPH 加载失败: {e}")


def _load_domains():
    if "domains" in _services:
        return
    try:
        from domains import ALL_DOMAIN_NAMES, create_all_domains
        _services["domains"] = {
            "names": ALL_DOMAIN_NAMES,
            "count": len(ALL_DOMAIN_NAMES),
        }
        _startup_ok["domains"] = True
    except Exception as e:
        _startup_ok["domains"] = False
        logger.warning(f"domains 加载失败: {e}")


def _load_emergence():
    if "emergence" in _services:
        return
    try:
        import json
        fpath = Path(__file__).resolve().parent.parent.parent / "cognitive-search-engine" / "data" / "emergence_state.json"
        if fpath.exists():
            data = json.loads(fpath.read_text(encoding="utf-8"))
            _services["emergence"] = data
            _startup_ok["emergence"] = True
        else:
            _services["emergence"] = {"signals": {}, "modes": {}}
            _startup_ok["emergence"] = False
    except Exception:
        _services["emergence"] = {"signals": {}, "modes": {}}
        _startup_ok["emergence"] = False




# ── Routes ────────────────────────────────────────────────────────────

@app.get("/health", response_model=APIResponse, tags=["System"])
async def health():
    """全项目健康仪表盘。"""
    t0 = time.perf_counter()
    checker = _get_service("health_check")
    if checker:
        result = checker()
    else:
        result = {"status": "DEGRADED", "error": "workspace not loaded"}
    return APIResponse(
        data=result,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@app.get("/api/v1/domains", response_model=APIResponse, tags=["Knowledge"])
async def list_domains():
    """12 领域知识图谱列表。"""
    domains = _services.get("domains", {})
    return APIResponse(data={
        "domains": domains.get("names", []),
        "count": domains.get("count", 0),
    })


@app.post("/api/v1/search", response_model=APIResponse, tags=["Search"])
async def search_species(req: SearchRequest):
    """物种文献搜索 — 自动路由到 19 引擎。"""
    t0 = time.perf_counter()
    searcher = _get_service("search")
    if not searcher:
        raise HTTPException(503, "search service not available")
    result = searcher(req.species, group=req.group, limit=req.limit)
    return APIResponse(
        data={
            "species": result.species_name,
            "mode": result.mode,
            "total": len(result.papers),
            "categories": {k: len(v) for k, v in (result.categories or {}).items()},
            "emergence": result.emergence_signals if hasattr(result, "emergence_signals") else [],
            "jhu_count": result.jhu_count,
            "papers_top5": [
                {"title": p.title[:100], "year": p.year, "doi": p.doi}
                for p in result.papers[:5]
            ],
        },
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
        error=result.error if hasattr(result, "error") and result.error else None,
    )


@app.get("/api/v1/lookup", response_model=APIResponse, tags=["Knowledge"])
async def lookup_species(
    name: str = Query(..., description="物种名", examples=["刀鲚"]),
):
    """知识库查询 — 物种画像 + 保护等级 + 分布。"""
    t0 = time.perf_counter()
    looker = _get_service("lookup")
    if not looker:
        raise HTTPException(503, "lookup service not available")
    result = looker(name)
    return APIResponse(
        data={
            "known": result.get("known_species", False),
            "scientific_name": result.get("scientific_name", name),
            "chinese_name": result.get("chinese_name", ""),
            "family": result.get("species_data", {}).get("family", ""),
            "conservation": result.get("species_data", {}).get("conservation", ""),
            "distribution": result.get("species_data", {}).get("distribution", {}),
            "conflict_verdict": result.get("conflict_verdict"),
        },
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@app.post("/api/v1/arbitrate", response_model=APIResponse, tags=["Conservation"])
async def arbitrate(req: ArbitrateRequest):
    """保护等级冲突仲裁 — 中国权威加权。"""
    t0 = time.perf_counter()
    arbiter = _get_service("arbitrate")
    if not arbiter:
        raise HTTPException(503, "arbitration service not available")
    result = arbiter(req.species, sources=req.sources, region=req.region)
    return APIResponse(
        data={
            "conflict_level": result.get("conflict_level"),
            "consensus": result.get("consensus"),
            "verdict": result.get("verdict"),
            "region": req.region,
        },
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@app.get("/api/v1/emergence", response_model=APIResponse, tags=["Emergence"])
async def emergence_status(
    species: Optional[str] = Query(None, description="物种筛选"),
):
    """涌现信号查询 — 跨搜索累积的研究趋势。"""
    emergence = _services.get("emergence", {})
    signals = emergence.get("signals", {})
    modes = emergence.get("modes", {})

    if species:
        return APIResponse(data={
            "species": species,
            "mode": modes.get(species, "normal"),
            "signals": signals.get(species, []),
        })

    return APIResponse(data={
        "species_tracked": len(modes),
        "surge_species": [k for k, v in modes.items() if v == "surge"],
        "stalled_species": [k for k, v in modes.items() if v == "stalled"],
        "modes": modes,
    })


@app.get("/api/v1/traits", response_model=APIResponse, tags=["Morphology"])
async def species_traits(
    name: str = Query(..., description="物种学名", examples=["Coilia nasus"]),
):
    """FISHMORPH 形态性状查询 — 体长、延长比、眼位、口位等 10 个性状。"""
    loader = _get_service("fishmorph")
    if not loader:
        raise HTTPException(503, "FISHMORPH data not loaded. Download first.")

    summary = loader.get_trait_summary(name)
    if summary.get("records", 0) == 0:
        raise HTTPException(404, f"No trait data for '{name}'")

    return APIResponse(data=summary)


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SPHERE_PORT", 8000))
    logger.info(f"Starting SphereGateway on port {port}")
    logger.info(f"  API docs: http://localhost:{port}/docs")
    logger.info(f"  Health:   http://localhost:{port}/health")
    uvicorn.run(app, host="0.0.0.0", port=port)
