"""Tests for Pipeline — 统一管道调度器."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.kernel.pipeline import Pipeline, PipelineResult, StageResult
from src.kernel.event_bus import AsyncEventBus


class TestPipelineTopology:
    """测试 DAG 拓扑加载和拓扑排序."""

    def test_load_topology(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        assert pipeline.is_loaded
        assert pipeline.vertex_count >= 5  # V0-V4
        assert pipeline.edge_count >= 4

    def test_topological_sort(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        order = pipeline.topological_sort()
        # V0 must precede V1 (fish→cognitive)
        assert order.index("V0") < order.index("V1")
        # V1 must precede all domain vertices
        for dv in ("V2", "V3", "V4"):
            if dv in order:
                assert order.index("V1") < order.index(dv)
        # All vertices present
        assert "V0" in order
        assert "V1" in order

    def test_topological_sort_no_cycle(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        order = pipeline.topological_sort()
        # A valid topological sort should have all vertices
        assert len(order) == pipeline.vertex_count

    def test_topological_sort_without_load_raises(self):
        pipeline = Pipeline()
        with pytest.raises(RuntimeError, match="not loaded"):
            pipeline.topological_sort()

    def test_get_vertex_info(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        v0 = pipeline.get_vertex_info("V0")
        assert v0 is not None
        assert v0["project"] == "fish-ecology-assistant"
        assert v0["stv_role"] == "S (State)"

    def test_get_downstream_stages(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        # V0(fish) → V1(cognitive)
        downstream = pipeline.get_downstream_stages("V0")
        assert "V1" in downstream

    def test_get_upstream_stages(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        # V1(cognitive) ← V0(fish)
        upstream = pipeline.get_upstream_stages("V1")
        assert "V0" in upstream


class TestStageExecution:
    """测试阶段执行."""

    @pytest.mark.asyncio
    async def test_execute_missing_stage(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        result = await pipeline.execute_stage("V99", {"query": "test"})
        assert result.status == "failed"
        assert "Unknown stage_id" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_stage_returns_stage_result(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        result = await pipeline.execute_stage("V0", {
            "query": "test",
            "trace_id": "test-trace",
        })
        assert isinstance(result, StageResult)
        assert result.stage_id == "V0"
        assert result.status in ("completed", "failed", "skipped")

    @pytest.mark.asyncio
    async def test_execute_stage_with_registered_executor(self):
        pipeline = Pipeline()
        pipeline.load_topology()

        call_log = []

        async def my_executor(stage_id, context):
            call_log.append((stage_id, context.get("query")))
            return {"custom": True, "query": context["query"]}

        pipeline.register_executor("V0", my_executor)
        result = await pipeline.execute_stage("V0", {"query": "珠星三块鱼"})
        assert result.status == "completed"
        assert call_log == [("V0", "珠星三块鱼")]
        assert result.output.get("custom") is True


class TestPipelineRun:
    """测试全管道运行."""

    @pytest.mark.asyncio
    async def test_run_without_load(self):
        pipeline = Pipeline()
        # Auto-loads on run
        result = await pipeline.run("test", mode="search_only")
        assert isinstance(result, PipelineResult)
        assert result.query == "test"
        assert result.mode == "search_only"

    @pytest.mark.asyncio
    async def test_run_auto_mode(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        result = await pipeline.run("珠星三块鱼", mode="auto")
        assert isinstance(result, PipelineResult)
        assert len(result.stages_executed) >= 1
        assert result.total_duration_ms >= 0
        assert result.stop_reason in ("completed", "early_exit", "error")

    @pytest.mark.asyncio
    async def test_run_search_only_mode(self):
        pipeline = Pipeline()
        pipeline.load_topology()
        result = await pipeline.run("test", mode="search_only")
        # search_only should run V0+V1
        executed = result.stages_executed
        assert "V0" in executed or "V1" in executed
        assert isinstance(result.to_dict(), dict)

    def test_pipeline_result_to_dict(self):
        result = PipelineResult(
            query="test",
            mode="auto",
            trace_id="abc123",
            stages_executed=["V0", "V1"],
            total_duration_ms=150.0,
            stop_reason="completed",
            synthesis="Test synthesis",
        )
        d = result.to_dict()
        assert d["query"] == "test"
        assert d["trace_id"] == "abc123"
        assert d["total_duration_ms"] == 150.0
        assert d["stop_reason"] == "completed"


class TestPipelineWithEventBus:
    """测试 Pipeline 与 EventBus 集成."""

    @pytest.mark.asyncio
    async def test_event_bus_injection(self):
        bus = AsyncEventBus(capacity=100, log_size=50)
        pipeline = Pipeline()
        pipeline.load_topology()
        pipeline.set_event_bus(bus)

        # Register a simple executor
        async def v0_executor(stage_id, context):
            return {"result": "ok"}

        pipeline.register_executor("V0", v0_executor)

        result = await pipeline.execute_stage("V0", {
            "query": "test",
            "trace_id": "bus-test",
        })
        assert result.status == "completed"

        # Check all events in log (no topic filter) — the topic is set inside publish
        all_events = bus.event_log()
        # At least the event we published should be there
        assert len(all_events) >= 1, f"Expected >=1 events in log, got {len(all_events)}"
        # Check the topic
        published_topics = [e.topic for e in all_events]
        assert any("pipeline.stage" in t for t in published_topics), \
            f"No pipeline.stage event found in topics: {published_topics}"
