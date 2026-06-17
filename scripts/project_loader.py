"""project_loader — 统一项目加载器 (DirectLoader v7.4).

Import bridge between eon-core and the 6 external projects:
  fish-ecology-assistant → V0 (knowledge supply)
  cognitive-search-engine → V1 (literature verification)
  porpoise-agent → V2 (porpoise domain research)
  coilia-agent → V3 (coilia domain research)
  culter-agent → V4 (culter domain research)
  conflict-arbiter → V5 (conservation arbitration)

Each loader returns a wrapper with a uniform .search(query, **kwargs) → dict interface.
Uses import isolation to avoid module name collisions (all projects use src.* namespace).
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ── Compute workspace root ──
_WORKSPACE = str(Path(__file__).resolve().parent.parent.parent)
_EON_ROOT = str(Path(__file__).resolve().parent.parent)


def _import_from_project(project_name: str, module_path: str, attr_name: str) -> Any:
    """Import attr_name from module_path within project_name, with sys.path isolation.

    Clears cached src.* modules between imports so different projects'
    src.adapter / src.orchestrator modules don't collide.
    Restores sys.path AND sys.modules on exit to avoid corrupting
    the calling module's import state.
    """
    project_root = os.path.join(_WORKSPACE, project_name)

    # Pre-load workspace scripts.adapter_protocol using direct path
    # to avoid CWD shadowing (eon-core/scripts/ vs workspace/scripts/).
    _adapter_protocol_path = os.path.join(_WORKSPACE, "scripts", "adapter_protocol.py")
    if os.path.isfile(_adapter_protocol_path) and "scripts.adapter_protocol" not in sys.modules:
        try:
            import importlib.util as _iu
            _spec = _iu.spec_from_file_location(
                "scripts.adapter_protocol", _adapter_protocol_path,
                submodule_search_locations=[os.path.dirname(_adapter_protocol_path)]
            )
            if _spec and _spec.loader:
                _mod = _iu.module_from_spec(_spec)
                # Ensure parent package 'scripts' is in sys.modules
                if "scripts" not in sys.modules:
                    _scripts_path = os.path.join(_WORKSPACE, "scripts", "__init__.py")
                    if os.path.isfile(_scripts_path):
                        _scripts_spec = _iu.spec_from_file_location(
                            "scripts", _scripts_path,
                            submodule_search_locations=[os.path.dirname(_scripts_path)]
                        )
                        if _scripts_spec and _scripts_spec.loader:
                            _scripts_mod = _iu.module_from_spec(_scripts_spec)
                            sys.modules["scripts"] = _scripts_mod
                            _scripts_spec.loader.exec_module(_scripts_mod)
                sys.modules["scripts.adapter_protocol"] = _mod
                _spec.loader.exec_module(_mod)
        except Exception:
            pass

    # Save current state (after pre-load to include adapter_protocol in snapshot)
    old_path = list(sys.path)
    old_modules = dict(sys.modules)

    # Clear cached src.* + scripts.* from other projects
    # scripts.* must also be cleared: eon-core/scripts/__init__.py (regular package) 
    # caches scripts.* and would shadow workspace-level scripts/ namespace.
    for k in list(sys.modules):
        if k == "src" or k.startswith("src."):
            del sys.modules[k]
        if k == "scripts" or k.startswith("scripts."):
            del sys.modules[k]

    # Set sys.path: this project first, then workspace root (for scripts/ redirects)
    # NOTE: _EON_ROOT is NOT added to path - otherwise eon-core/scripts/__init__.py
    # (regular package) would shadow D:/Reasonix/scripts/ (namespace package).
    # Empty strings ('') and relative paths ('.', '..') also cause shadowing — 
    # resolve them to absolute before filtering.
    _norm_ws = os.path.normpath(_WORKSPACE)
    _new_path = [project_root, _WORKSPACE]
    for p in old_path:
        # Resolve empty/relative paths to absolute for accurate filtering
        if p == '':
            # Empty string = CWD, which is typically under _WORKSPACE
            continue
        try:
            abs_p = os.path.normpath(os.path.abspath(p))
        except Exception:
            abs_p = os.path.normpath(p)
        if abs_p.startswith(_norm_ws):
            continue
        _new_path.append(p)
    sys.path = _new_path

    try:
        mod = __import__(module_path, fromlist=[attr_name])
        result = getattr(mod, attr_name)
        return result
    except Exception:
        raise
    finally:
        # Restore to pre-import state — fully revert sys.modules
        # to avoid src package pollution across projects.
        # The returned class/factory keeps a reference to its module
        # so it won't be garbage-collected even after we remove it
        # from sys.modules.
        sys.path = old_path
        sys.modules.clear()
        sys.modules.update(old_modules)


# ═══════════════════════════════════════════════════════════════
# Lazy-loaded singletons — created on first access
# ═══════════════════════════════════════════════════════════════

_fish: Optional[Any] = None
_cognitive: Optional[Any] = None
_porpoise: Optional[Any] = None
_coilia: Optional[Any] = None


class _ProjectWrapper:
    """Uniform wrapper around external project adapters.

    Provides .search(query, **kwargs) → dict interface
    regardless of the underlying project's API shape.
    Also supports .arbitrate(context) for conflict-arbiter.
    """

    def __init__(self, name: str, search_fn: Callable) -> None:
        self._name = name
        self._search = search_fn

    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search on the wrapped project.

        Returns: {status, items, total, sources_used, ...}
        """
        try:
            result = self._search(query, **kwargs)
            if isinstance(result, dict):
                return result
            # If result is a dataclass/object, convert
            if hasattr(result, "to_dict"):
                return result.to_dict()
            return {"status": "ok", "items": [], "raw": str(result)[:500]}
        except Exception as exc:
            logger.warning(f"{self._name}.search() failed: {exc}")
            return {"status": "error", "error": str(exc), "items": []}

    def arbitrate(self, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute conflict arbitration.

        For conflict-arbiter adapter: resolves multi-source conflicts.
        Delegates to search() with action='arbitrate' so the underlying
        adapter can route to the appropriate arbiter method.

        Args:
            context: Dict with prior_outputs, species, query, etc.
        """
        ctx = context or {}
        species = ctx.get("species", ctx.get("query", ""))
        prior_outputs = ctx.get("prior_outputs", {})

        # Extract claims from prior stage outputs
        sources = []
        claims = []
        for pid, data in prior_outputs.items():
            if isinstance(data, dict):
                items = data.get("items", data.get("knowledge_items", []))
                for item in items if isinstance(items, list) else []:
                    if isinstance(item, dict):
                        src = item.get("source", item.get("type", pid))
                        val = item.get("data", item)
                        claims.append({
                            "source": str(src)[:200],
                            "claim": str(item.get("scientific", item.get("title", "")))[:200],
                            "weight": item.get("credibility_score", 50),
                            "value": 50,
                        })

        try:
            return self._search(species, sources=sources, claims=claims, **kwargs)
        except Exception as exc:
            logger.warning(f"{self._name}.arbitrate() failed: {exc}")
            return {"status": "error", "error": str(exc)}

    def health(self) -> Dict[str, Any]:
        """Return health status from the wrapped project adapter.

        Delegates to adapter.health() if the wrapped object has it,
        otherwise returns basic wrapper-level status.
        """
        try:
            # If the wrapped _search is bound to an adapter with health(), call it
            import types
            if hasattr(self._search, '__self__'):
                adapter = self._search.__self__
                if hasattr(adapter, 'health'):
                    result = adapter.health()
                    if isinstance(result, dict):
                        return result
            return {"status": "ok", "project": self._name, "wrapper": True}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "project": self._name}


# ── Fish Ecology Assistant (V0 — knowledge supply) ──

def get_fish():
    """Get FishEcologyAdapter wrapper for species knowledge lookup.

    Uses FishEcologyAdapter.search(query, max_results=20).
    """
    global _fish
    if _fish is not None:
        return _fish

    try:
        FishEcologyAdapter = _import_from_project(
            "fish-ecology-assistant", "src.adapter", "FishEcologyAdapter"
        )

        def _fish_search(query: str, **kwargs) -> Dict[str, Any]:
            adapter = FishEcologyAdapter()
            max_results = kwargs.get("max_results", 20)
            return adapter.search(query, max_results=max_results)

        _fish = _ProjectWrapper("fish-ecology-assistant", _fish_search)
        logger.info("fish-ecology-assistant loaded via DirectLoader")
        return _fish

    except Exception as exc:
        logger.warning(f"fish-ecology-assistant unavailable: {exc}")
        return None


# ── Cognitive Search Engine (V1 — literature verification) ──

def get_cognitive():
    """Get cognitive-search-engine wrapper for literature search + verification.

    Uses unified_search.coordinated_search() with post-search filtering:
      1. group='standard' (5 academic engines, no web_search/baidu noise)
      2. Relevance check: species name OR fish biology keywords in title
      3. Credibility scoring via validator.credibility_score()
      4. Sort by year desc + credibility
    """
    global _cognitive
    if _cognitive is not None:
        return _cognitive

    try:
        cog_adapter_cls = _import_from_project(
            "cognitive-search-engine", "src.adapter", "CognitiveSearchAdapter"
        )

        def _cog_search_fn(query: str, **kwargs) -> Dict[str, Any]:
            import re
            from dataclasses import dataclass

            @dataclass
            class _Paper:
                doi: str = ""
                title: str = ""
                year: Any = None
                journal: str = ""

            limit = kwargs.get("limit", 10)
            group = kwargs.get("group", "standard")

            # Step 1: Full pipeline search
            adapter = cog_adapter_cls()
            result = adapter.search(query, group=group, limit=limit)
            raw_papers = result.get("papers", result.get("results", [])) if isinstance(result, dict) else []

            # Step 2: Topic relevance filter
            def _relevant(p):
                t = (p.get("title") or "").lower()
                # Species name match → relevant
                species_hits = ["tribolodon", "pseudaspius", "hakonensis",
                                "leuciscus", "brandti", "sachalinensis"]
                if any(s in t for s in species_hits):
                    return True
                # Chinese name match
                if any(s in t for s in ["三块鱼", "滩头鱼", "珠星"]):
                    return True
                # Irrelevant Chinese topics → drop
                noise_cn = ["区块链", "三星堆", "轧机", "台风", "臭氧", "脂质体",
                            "细胞减少", "分子印迹", "供应链", "金融", "冶金", "冷却"]
                if any(n in t for n in noise_cn):
                    return False
                # Fish biology keywords
                fish_kw = ["cyprinid", "dace", "redfin", "fish", "freshwater",
                           "spawn", "migrat", "parasit", "helminth", "pharyngeal",
                           "fishway", "genetic", "phyloge", "phylogen", "genom",
                           "transcriptom", "morpholog", "speciation"]
                if any(f in t for f in fish_kw):
                    return True
                return True  # default: keep

            relevant = [p for p in raw_papers if _relevant(p)]

            # Step 3: Credibility scoring + sort
            # Try to import real validator.credibility_score; fallback to heuristics
            _credibility_score = None
            try:
                from cognitive_search_engine.src.validator import credibility_score as _real_cs
                _credibility_score = _real_cs
            except Exception:
                pass

            scored = []
            for p in relevant:
                pp = _Paper(doi=p.get("doi", ""), title=p.get("title", ""),
                            year=p.get("year"), journal=p.get("journal", ""))
                cs = 50  # default
                if _credibility_score is not None:
                    try:
                        cs = _credibility_score(pp)
                    except Exception:
                        pass
                else:
                    # Heuristic: journal presence + year freshness
                    if p.get("journal"):
                        cs += 20
                    year_str = str(p.get("year", ""))[:4]
                    if year_str.isdigit():
                        yr = int(year_str)
                        if yr >= 2020:
                            cs += 15
                        elif yr >= 2010:
                            cs += 10
                        elif yr >= 2000:
                            cs += 5
                p["credibility_score"] = min(cs, 100)
                scored.append(p)

            scored.sort(key=lambda x: (
                int(str(x.get("year", 0))[:4]) if str(x.get("year", "")).isdigit() else 0,
                x.get("credibility_score", 50)
            ), reverse=True)

            return {
                "status": "ok",
                "total": len(scored),
                "items": scored,
                "raw_total": len(raw_papers),
                "filtered_out": len(raw_papers) - len(scored),
                "sources_used": getattr(result, "source_distribution", {}),
            }

        _cognitive = _ProjectWrapper("cognitive-search-engine", _cog_search_fn)
        logger.info("cognitive-search-engine loaded via DirectLoader")
        return _cognitive

    except Exception as exc:
        logger.warning(f"cognitive-search-engine unavailable: {exc}")
        return None


# ── Porpoise Agent (V2 — porpoise domain research) ──

def get_porpoise():
    """Get porpoise-agent wrapper for acoustic + population analysis.

    Uses PorpoiseAdapter.search(query) — standard IProjectAdapter interface.
    """
    global _porpoise
    if _porpoise is not None:
        return _porpoise

    try:
        PorpoiseAdapter = _import_from_project(
            "porpoise-agent", "src.adapter", "PorpoiseAdapter"
        )

        def _porpoise_search(query: str, **kwargs) -> Dict[str, Any]:
            adapter = PorpoiseAdapter()
            domain = kwargs.get("domain", "")
            return adapter.search(query, domain=domain)

        _porpoise = _ProjectWrapper("porpoise-agent", _porpoise_search)
        logger.info("porpoise-agent loaded via DirectLoader")
        return _porpoise

    except Exception as exc:
        logger.warning(f"porpoise-agent unavailable: {exc}")
        return None


# ── Coilia Agent (V3 — coilia domain research) ──

def get_coilia():
    """Get coilia-agent wrapper for otolith + resource assessment.

    Uses CoiliaAdapter.search(query).
    """
    global _coilia
    if _coilia is not None:
        return _coilia

    try:
        CoiliaAdapter = _import_from_project(
            "coilia-agent", "src.adapter", "CoiliaAdapter"
        )

        def _coilia_search(query: str, **kwargs) -> Dict[str, Any]:
            adapter = CoiliaAdapter()
            domain = kwargs.get("domain", "")
            if domain == "otolith":
                return adapter.search(f"analyze otolith microchemistry: {query}")
            elif domain == "resource":
                return adapter.search(f"assess fishery resources: {query}")
            return adapter.search(query)

        _coilia = _ProjectWrapper("coilia-agent", _coilia_search)
        logger.info("coilia-agent loaded via DirectLoader")
        return _coilia

    except Exception as exc:
        logger.warning(f"coilia-agent unavailable: {exc}")
        return None


# ── Culter Agent (V4 — culter domain research) ──

_culter: Optional[Any] = None


def get_culter():
    """Get culter-agent wrapper for age-growth + genomics + trophic ecology.

    Uses CulterAdapter.search(query) with get_adapter() factory.
    CulterOrchestrator has 9-phase pipeline covering:
      growth, genomics, genetics, trophic isotopes, coexistence, resource, habitat.
    """
    global _culter
    if _culter is not None:
        return _culter

    try:
        CulterAdapter = _import_from_project(
            "culter-agent", "src.adapter", "CulterAdapter"
        )

        def _culter_search(query: str, **kwargs) -> Dict[str, Any]:
            adapter = CulterAdapter()
            domain = kwargs.get("domain", "")
            if domain == "growth":
                return adapter.search(f"analyze age and growth: {query}")
            elif domain == "genomics":
                return adapter.search(f"analyze genomics: {query}")
            elif domain == "trophic":
                return adapter.search(f"analyze trophic ecology stable isotopes: {query}")
            elif domain == "resource":
                return adapter.search(f"assess fishery resources: {query}")
            return adapter.search(query)

        _culter = _ProjectWrapper("culter-agent", _culter_search)
        logger.info("culter-agent loaded via DirectLoader")
        return _culter

    except Exception as exc:
        logger.warning(f"culter-agent unavailable: {exc}")
        return None


_conflict = None


def get_conflict():
    """Get conflict-arbiter for multi-source conservation arbitration.

    已合并到 cognitive-search-engine (T验证层).
    Uses cognitive-search-engine/src/conflict_adapter.py.
    """
    global _conflict
    if _conflict is not None:
        return _conflict

    try:
        ConflictArbiterAdapter = _import_from_project(
            "conflict-arbiter", "src.adapter", "ConflictArbiterAdapter"
        )

        def _conflict_search(species_name: str, **kwargs) -> Dict[str, Any]:
            adapter = ConflictArbiterAdapter()
            sources = kwargs.get("sources", [])
            claims = kwargs.get("claims", [])
            region = kwargs.get("region", "china")
            return adapter.search(species_name, sources=sources, claims=claims, region=region)

        _conflict = _ProjectWrapper("conflict-arbiter", _conflict_search)
        logger.info("conflict-arbiter loaded via DirectLoader")
        return _conflict

    except Exception as exc:
        logger.warning(f"conflict-arbiter unavailable: {exc}")
        return None


# ── Convenience ──

def load_all() -> Dict[str, bool]:
    """Pre-load all 6 projects. Returns status dict."""
    return {
        "fish": get_fish() is not None,
        "cognitive": get_cognitive() is not None,
        "porpoise": get_porpoise() is not None,
        "coilia": get_coilia() is not None,
        "culter": get_culter() is not None,
        "conflict": get_conflict() is not None,
    }
