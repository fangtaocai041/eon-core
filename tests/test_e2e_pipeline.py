r"""test_e2e_pipeline.py — 跨项目标准管道端到端测试.

验证标准管道: fish.search → cognitive.verify → conflict.arbitrate → fish.score

用法:
    cd D:\Reasonix\eon-core
    python -m pytest tests/test_e2e_pipeline.py -v
    或
    python tests/test_e2e_pipeline.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure eon-core is on sys.path
_eon_root = Path(__file__).resolve().parent.parent
if str(_eon_root) not in sys.path:
    sys.path.insert(0, str(_eon_root))
# Also ensure workspace root for scripts.adapter_protocol
_workspace = _eon_root.parent
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))


# ═══════════════════════════════════════════════════════════════
# Test 1: 导入链验证
# ═══════════════════════════════════════════════════════════════

def test_import_chain():
    """验证所有适配器可独立导入."""
    # fishkb from fish-ecology
    from scripts.project_loader import get_fish
    fish = get_fish()
    assert fish is not None, "fish adapter 应为非空"

    # cognitive validator
    from scripts.project_loader import get_cognitive
    cog = get_cognitive()
    assert cog is not None, "cognitive adapter 应为非空"

    # conflict arbiter
    from scripts.project_loader import get_conflict
    conflict = get_conflict()
    assert conflict is not None, "conflict adapter 应为非空"

    print(f"  [OK] All 3 adapters imported: fish, cognitive, conflict")


# ═══════════════════════════════════════════════════════════════
# Test 2: fishkb 从 fish-ecology 独立导入
# ═══════════════════════════════════════════════════════════════

def test_fishkb_standalone():
    """fishkb 能从 fish-ecology 独立调用."""
    from scripts.project_loader import get_fish
    fish = get_fish()

    # search 应返回有效结果
    result = fish.search("鳤", species="Ochetobius elongatus")
    assert isinstance(result, dict), "search 应返回 dict"
    assert "status" in result, "结果应包含 status"
    print(f"  [OK] fish.search('鳤') → status={result.get('status')}, "
          f"known_species={result.get('known_species', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 3: cognitive validator 独立调用
# ═══════════════════════════════════════════════════════════════

def test_cognitive_validator_standalone():
    """cognitive 的 validator 能独立调用."""
    from scripts.project_loader import get_cognitive
    cog = get_cognitive()

    # search 应返回有效结果
    result = cog.search("Ochetobius elongatus", limit=3)
    assert isinstance(result, dict), "search 应返回 dict"
    print(f"  [OK] cognitive.search('Ochetobius elongatus') → "
          f"status={result.get('status')}, total={result.get('total', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 4: conflict arbiter 独立调用
# ═══════════════════════════════════════════════════════════════

def test_conflict_arbiter_standalone():
    """conflict 的 arbiter 能独立调用."""
    from scripts.project_loader import get_conflict
    conflict = get_conflict()

    result = conflict.search(
        "Ochetobius elongatus",
        sources=[
            {"source": "iucn", "protection_level": "EN", "iucn": "Endangered"},
            {"source": "chinese_red_list", "protection_level": "二级", "iucn": "Vulnerable"},
        ],
    )
    assert isinstance(result, dict), "search 应返回 dict"
    print(f"  [OK] conflict.search('Ochetobius elongatus') → "
          f"conflict_level={result.get('conflict_level', 'N/A')}")


# ═══════════════════════════════════════════════════════════════
# Test 5: CrossProjectPipeline 加载所有适配器
# ═══════════════════════════════════════════════════════════════

def test_cross_project_loads_all_adapters():
    """eon-core 的 cross_project 能加载所有适配器."""
    from src.kernel.cross_project import CrossProjectPipeline

    async def _load():
        cp = CrossProjectPipeline()
        await cp.bootstrap(load_all=True)
        return cp

    cp = asyncio.run(_load())
    assert cp.is_bootstrapped, "Pipeline 应为已 bootstrap"
    assert cp.adapter_count >= 3, (
        f"至少应加载 3 个适配器, 实际: {cp.adapter_count}"
    )

    loaded = cp.loaded_projects
    print(f"  [OK] CrossProjectPipeline loaded: {cp.adapter_count} adapters: {loaded}")

    # 验证关键适配器已加载
    assert "fish" in loaded, "fish adapter 应加载"
    assert "cognitive" in loaded, "cognitive adapter 应加载"
    assert "conflict" in loaded, "conflict adapter 应加载"


# ═══════════════════════════════════════════════════════════════
# Test 6: 标准管道端到端
# ═══════════════════════════════════════════════════════════════

def test_standard_pipeline():
    """标准管道: fish.search → cognitive.verify → conflict.arbitrate → fish.score"""
    from src.kernel.cross_project import CrossProjectPipeline, Route

    async def _run():
        cp = CrossProjectPipeline()
        await cp.bootstrap(load_all=True)
        result = await cp.run("鳤", route=Route.STANDARD, species="Ochetobius elongatus")
        return result

    result = asyncio.run(_run())

    # 基本断言
    assert result.query == "鳤", "查询应为 '鳤'"
    assert result.route == "standard", "路由应为 'standard'"
    assert result.stages_completed >= 1, (
        f"至少 1 个阶段应成功, 实际: {result.stages_completed}"
    )

    # 打印阶段详情
    print(f"\n  Pipeline result for '{result.query}':")
    print(f"  Trace: {result.trace_id}")
    print(f"  Stages completed: {result.stages_completed}/{len(result.stages)}")
    print(f"  Stop reason: {result.stop_reason}")

    for pid, stage in result.stages.items():
        icon = "✅" if stage.status.value == "completed" else "❌"
        print(f"    {icon} {pid}: {stage.status.value} "
              f"({stage.duration_ms:.0f}ms)"
              f"{' — ' + stage.error if stage.error else ''}")

    # 综合摘要
    synthesis = result.synthesis
    print(f"\n  Synthesis: {synthesis['completed']} completed, "
          f"{synthesis['failed']} failed, "
          f"total_duration: {result.total_duration_ms:.0f}ms")

    # 验证管道至少 fish.search 阶段存在
    assert "fish" in result.stages, "应包含 fish 阶段"

    # to_dict 可用
    d = result.to_dict()
    assert isinstance(d, dict), "to_dict 应返回 dict"
    assert "stages" in d, "to_dict 应包含 stages"
    assert "synthesis" in d, "to_dict 应包含 synthesis"

    print(f"  [OK] Standard pipeline e2e test passed")

    if result.errors:
        print(f"  ⚠️  Non-fatal errors: {result.errors}")


# ═══════════════════════════════════════════════════════════════
# Test 7: 标准管道结果验证 — stages_completed 属性
# ═══════════════════════════════════════════════════════════════

def test_stages_completed_property():
    """验证 CrossProjectResult.stages_completed 属性正确计数."""
    from src.kernel.cross_project import (
        CrossProjectResult, StageStatus, StageOutput,
    )

    result = CrossProjectResult(query="test", route="standard")
    result.stages["fish"] = StageOutput(
        project="fish", status=StageStatus.COMPLETED, data={"ok": True}
    )
    result.stages["cognitive"] = StageOutput(
        project="cognitive", status=StageStatus.COMPLETED, data={"ok": True}
    )
    result.stages["conflict"] = StageOutput(
        project="conflict", status=StageStatus.FAILED, error="timeout"
    )

    assert result.stages_completed == 2, (
        f"应有 2 个完成阶段, 实际: {result.stages_completed}"
    )
    print(f"  [OK] stages_completed = {result.stages_completed}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("E2E Standard Pipeline Tests")
    print("=" * 60)

    tests = [
        ("Import Chain", test_import_chain),
        ("fishkb Standalone", test_fishkb_standalone),
        ("Cognitive Validator Standalone", test_cognitive_validator_standalone),
        ("Conflict Arbiter Standalone", test_conflict_arbiter_standalone),
        ("CrossProject Loads All Adapters", test_cross_project_loads_all_adapters),
        ("Standard Pipeline E2E", test_standard_pipeline),
        ("stages_completed Property", test_stages_completed_property),
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
