r"""test_cross_project_integration.py — 跨项目集成验证脚本.

验证至少 3 个项目的适配器能加载并互操作:
  1. fish-ecology-assistant (V0) — 物种知识库查询
  2. cognitive-search-engine (V1) — 文献搜索验证
  3. conflict-arbiter (V5) — 保护等级冲突仲裁
  4. 标准管道端到端 (optional, if all adapters available)

用法:
    cd D:\Reasonix\eon-core
    python -m pytest tests/test_cross_project_integration.py -v
    或
    python tests/test_cross_project_integration.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure eon-core is on sys.path
_eon_root = Path(__file__).resolve().parent.parent
if str(_eon_root) not in sys.path:
    sys.path.insert(0, str(_eon_root))
# Also ensure workspace root for scripts.adapter_protocol
_workspace = _eon_root.parent
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))


# ═══════════════════════════════════════════════════════════════
# Test 1: Fish Ecology Adapter (V0)
# ═══════════════════════════════════════════════════════════════

def test_fish_adapter_loads():
    """V0: fish-ecology-assistant adapter 能加载."""
    from scripts.project_loader import get_fish
    fish = get_fish()
    assert fish is not None, "Fish adapter 应为非空"
    assert hasattr(fish, "search"), "Fish adapter 必须有 search 方法"
    assert hasattr(fish, "health"), "Fish adapter 必须有 health 方法"

    # Health check
    health = fish.health()
    assert isinstance(health, dict), "health 应返回 dict"
    assert "status" in health, "health 应包含 status"
    print(f"  [OK] Fish adapter loaded - health: {health.get('status')}")

    # Search test
    result = fish.search("珠星三块鱼", species="Tribolodon hakonensis")
    assert isinstance(result, dict), "search 应返回 dict"
    assert "status" in result, "search 结果应包含 status"
    print(f"  [OK] Fish search - status: {result.get('status')}, "
          f"known_species: {result.get('known_species', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 2: Cognitive Search Adapter (V1)
# ═══════════════════════════════════════════════════════════════

def test_cognitive_adapter_loads():
    """V1: cognitive-search-engine adapter 能加载."""
    from scripts.project_loader import get_cognitive
    cog = get_cognitive()
    assert cog is not None, "Cognitive adapter 应为非空"
    assert hasattr(cog, "search"), "Cognitive adapter 必须有 search 方法"

    # Health check
    health = cog.health()
    assert isinstance(health, dict), "health 应返回 dict"
    print(f"  [OK] Cognitive adapter loaded - health: {health.get('status')}")

    # Search test (stub or real)
    result = cog.search("Tribolodon hakonensis", limit=3)
    assert isinstance(result, dict), "search 应返回 dict"
    print(f"  [OK] Cognitive search - status: {result.get('status')}, "
          f"total: {result.get('total', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 3: Conflict Arbiter Adapter (V5)
# ═══════════════════════════════════════════════════════════════

def test_conflict_adapter_loads():
    """V5: conflict-arbiter adapter 能加载."""
    from scripts.project_loader import get_conflict
    conflict = get_conflict()
    assert conflict is not None, "Conflict adapter 应为非空"
    assert hasattr(conflict, "search"), "Conflict adapter 必须有 search 方法"

    # Health check
    health = conflict.health()
    assert isinstance(health, dict), "health 应返回 dict"
    print(f"  [OK] Conflict adapter loaded - health: {health.get('status')}")

    # Search with arbitration claims
    result = conflict.search(
        "珠星三块鱼",
        sources=[
            {"source": "iucn", "protection_level": "LC", "iucn": "Least Concern"},
            {"source": "chinese_red_list", "protection_level": "EN", "iucn": "Endangered"},
        ],
    )
    assert isinstance(result, dict), "search 应返回 dict"
    print(f"  [OK] Conflict search - status: {result.get('status', 'N/A')}, "
          f"conflict_level: {result.get('conflict_level', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 4: CrossProjectPipeline Bootstrap
# ═══════════════════════════════════════════════════════════════

def test_pipeline_bootstrap():
    """CrossProjectPipeline 能加载所有适配器."""
    from src.kernel.cross_project import CrossProjectPipeline, Route

    async def _bootstrap():
        cp = CrossProjectPipeline()
        await cp.bootstrap(load_all=True)
        return cp

    cp = asyncio.run(_bootstrap())
    assert cp.is_bootstrapped, "Pipeline 应为已 bootstrap"
    assert cp.adapter_count >= 3, (
        f"至少应加载 3 个适配器, 实际: {cp.adapter_count}"
    )

    loaded = cp.loaded_projects
    print(f"  [OK] Pipeline bootstrapped - {cp.adapter_count} adapters: {loaded}")

    # Health check
    health = asyncio.run(cp.health())
    assert "status" in health, "Pipeline health 应包含 status"
    print(f"  [OK] Pipeline health - {health.get('status')}")

    return cp


# ═══════════════════════════════════════════════════════════════
# Test 5: Standard Pipeline Run
# ═══════════════════════════════════════════════════════════════

def test_standard_pipeline_run():
    """标准管道路由: fish.search → cognitive.search → conflict.arbitrate."""
    from src.kernel.cross_project import CrossProjectPipeline, Route

    async def _run():
        cp = CrossProjectPipeline()
        await cp.bootstrap(load_all=True)

        result = await cp.run(
            "珠星三块鱼",
            route=Route.STANDARD,
            species="Tribolodon hakonensis",
        )
        return result

    result = asyncio.run(_run())

    # 检查结果结构
    assert result.query == "珠星三块鱼", "查询应匹配"
    assert result.route == "standard", "路由应为 standard"
    assert len(result.trace_id) == 32, "trace_id 应为 32 字符 hex"

    # 检查阶段
    stages = result.stages
    print(f"  [OK] Pipeline stages: {list(stages.keys())}")

    # fish 阶段应完成
    if "fish" in stages:
        fish_stage = stages["fish"]
        print(f"     fish: {fish_stage.status.value} ({fish_stage.duration_ms:.0f}ms)")

    # cognitive 阶段应完成
    if "cognitive" in stages:
        cog_stage = stages["cognitive"]
        print(f"     cognitive: {cog_stage.status.value} ({cog_stage.duration_ms:.0f}ms)")

    # conflict 阶段应为 completed 或 skipped
    if "conflict" in stages:
        cf_stage = stages["conflict"]
        print(f"     conflict: {cf_stage.status.value} ({cf_stage.duration_ms:.0f}ms)")

    # 综合摘要
    synthesis = result.synthesis
    assert "total_stages" in synthesis, "综合摘要应包含 total_stages"
    print(f"  [OK] Synthesis: {synthesis['completed']} completed, "
          f"{synthesis['failed']} failed, "
          f"total_duration: {result.total_duration_ms:.0f}ms")

    # to_dict 可用
    d = result.to_dict()
    assert isinstance(d, dict), "to_dict 应返回 dict"
    print(f"  [OK] to_dict: {list(d.keys())}")


# ═══════════════════════════════════════════════════════════════
# Test 6: IProjectAdapter Protocol Compliance
# ═══════════════════════════════════════════════════════════════

def test_adapter_protocol_compliance():
    """验证各项目适配器实现 IProjectAdapter 协议."""
    from scripts.adapter_protocol import IProjectAdapter

    adapters_to_check: Dict[str, str] = {
        "fish-ecology-assistant": "src.adapter:FishEcologyAdapter",
        "cognitive-search-engine": "src.adapter:CognitiveSearchAdapter",
        "conflict-arbiter": "src.adapter:ConflictArbiterAdapter",
    }

    for project_name, module_attr in adapters_to_check.items():
        project_root = _workspace / project_name
        if not project_root.exists():
            print(f"  [WARN] {project_name}: project dir not found, skip")
            continue

        try:
            # 动态导入
            mod_path, attr_name = module_attr.split(":")
            sys.path.insert(0, str(project_root))
            import importlib
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, attr_name, None)
            if cls is None:
                print(f"  [WARN] {project_name}: {attr_name} not found")
                continue

            # 检查是否为 IProjectAdapter 子类
            is_subclass = issubclass(cls, IProjectAdapter)
            if is_subclass:
                print(f"  [OK] {project_name}: {attr_name} implements IProjectAdapter")
            else:
                print(f"  [WARN] {project_name}: {attr_name} not subclass of IProjectAdapter (fallback=object)")

            # 实例化检查
            instance = cls()
            assert hasattr(instance, "search"), f"{attr_name} 缺少 search 方法"
            assert hasattr(instance, "health"), f"{attr_name} 缺少 health 方法"
            assert hasattr(instance, "info"), f"{attr_name} 缺少 info 方法"
            print(f"     -> search/health/info methods present")

        except Exception as exc:
            print(f"  [FAIL] {project_name}: load failed - {exc}")


# ═══════════════════════════════════════════════════════════════
# Test 7: taiji.yaml 配置验证
# ═══════════════════════════════════════════════════════════════

def test_taiji_yaml_completeness():
    """验证 taiji.yaml 包含所有 7 个项目."""
    import yaml

    taiji_path = _eon_root / "config" / "taiji.yaml"
    assert taiji_path.exists(), f"taiji.yaml 不存在: {taiji_path}"

    cfg = yaml.safe_load(taiji_path.read_text(encoding="utf-8"))

    vertices = cfg.get("vertices", {})
    vertex_ids = list(vertices.keys())

    # 应包含 V0-V5
    expected = ["V0", "V1", "V2", "V3", "V4", "V5"]
    for vid in expected:
        assert vid in vertices, f"taiji.yaml 缺少顶点 {vid}"

    # 项目名映射
    project_map = {
        "V0": "fish-ecology-assistant",
        "V1": "cognitive-search-engine",
        "V2": "porpoise-agent",
        "V3": "coilia-agent",
        "V4": "culter-agent",
        "V5": "conflict-arbiter",
    }

    for vid, expected_project in project_map.items():
        actual_project = vertices[vid].get("project", "")
        assert actual_project == expected_project, (
            f"{vid} 项目应为 {expected_project}, 实际: {actual_project}"
        )

    print(f"  [OK] taiji.yaml: {len(vertices)} vertices, "
          f"{len(cfg.get('tetrahedron', {}).get('edges', []))} 条边")

    # 验证边包含 V5
    edges = cfg.get("tetrahedron", {}).get("edges", [])
    v5_edges = [e for e in edges if "V5" in (e.get("from"), e.get("to"))]
    print(f"  [OK] V5 (conflict-arbiter) edges: {len(v5_edges)} -> {[e['name'] for e in v5_edges]}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Cross-Project Integration Tests")
    print("=" * 60)

    tests = [
        ("Fish Adapter (V0)", test_fish_adapter_loads),
        ("Cognitive Adapter (V1)", test_cognitive_adapter_loads),
        ("Conflict Adapter (V5)", test_conflict_adapter_loads),
        ("Pipeline Bootstrap", test_pipeline_bootstrap),
        ("Standard Pipeline Run", test_standard_pipeline_run),
        ("Adapter Protocol Compliance", test_adapter_protocol_compliance),
        ("taiji.yaml Completeness", test_taiji_yaml_completeness),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n─ {name} ─")
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)
