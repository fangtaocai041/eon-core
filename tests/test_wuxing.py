"""Tests for WuxingMonitor — 五行健康监控器."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.kernel.wuxing_monitor import (
    WuxingMonitor,
    WuxingElement,
    WuxingReport,
    ElementMetrics,
    HealthGrade,
)


class TestWuxingElement:
    """测试五行元素枚举."""

    def test_all_five_elements(self):
        elements = list(WuxingElement)
        assert len(elements) == 5
        names = {e.value for e in elements}
        assert names == {"metal", "wood", "water", "fire", "earth"}

    def test_generation_cycle(self):
        """相生: 金生水→水生木→木生火→火生土→土生金"""
        gen = WuxingMonitor._GENERATION
        assert gen[WuxingElement.METAL] == WuxingElement.WATER
        assert gen[WuxingElement.WATER] == WuxingElement.WOOD
        assert gen[WuxingElement.WOOD] == WuxingElement.FIRE
        assert gen[WuxingElement.FIRE] == WuxingElement.EARTH
        assert gen[WuxingElement.EARTH] == WuxingElement.METAL

    def test_restriction_cycle(self):
        """相克: 金克木→木克土→土克水→水克火→火克金"""
        res = WuxingMonitor._RESTRICTION
        assert res[WuxingElement.METAL] == WuxingElement.WOOD
        assert res[WuxingElement.WOOD] == WuxingElement.EARTH
        assert res[WuxingElement.EARTH] == WuxingElement.WATER
        assert res[WuxingElement.WATER] == WuxingElement.FIRE
        assert res[WuxingElement.FIRE] == WuxingElement.METAL


class TestElementMetrics:
    """测试单元素指标."""

    def test_initial_state(self):
        m = ElementMetrics(element=WuxingElement.METAL)
        assert m.call_count == 0
        assert m.success_rate == 1.0
        assert m.avg_latency_ms == 0.0
        assert m.grade == HealthGrade.FAIR
        assert m.consecutive_failures == 0

    def test_success_recording(self):
        m = ElementMetrics(element=WuxingElement.WATER)
        m.call_count = 10
        m.success_count = 10
        m.total_latency_ms = 450.0
        assert m.success_rate == 1.0
        assert m.avg_latency_ms == 45.0
        # 100% success, < 100ms → EXCELLENT
        assert m.grade == HealthGrade.EXCELLENT

    def test_partial_failure(self):
        m = ElementMetrics(element=WuxingElement.FIRE)
        m.call_count = 100
        m.success_count = 75
        m.failure_count = 25
        m.total_latency_ms = 80000.0  # 800ms avg
        assert m.success_rate == 0.75
        assert m.avg_latency_ms == 800.0
        # 75% → FAIR
        assert m.grade == HealthGrade.FAIR

    def test_degraded(self):
        m = ElementMetrics(element=WuxingElement.WOOD)
        m.call_count = 50
        m.success_count = 30
        m.failure_count = 20
        m.total_latency_ms = 60000.0
        assert m.success_rate == 0.6
        # < 70% → DEGRADED
        assert m.grade == HealthGrade.DEGRADED

    def test_down_due_to_consecutive_failures(self):
        m = ElementMetrics(element=WuxingElement.EARTH)
        m.call_count = 20
        m.success_count = 9
        m.failure_count = 11
        m.consecutive_failures = 11
        assert m.grade == HealthGrade.DOWN

    def test_recent_latencies(self):
        m = ElementMetrics(element=WuxingElement.METAL)
        for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
            m._recent_latencies.append(lat)
        assert m.recent_avg_latency_ms == 30.0


class TestWuxingMonitor:
    """测试五行监控器."""

    def test_initial_state(self):
        monitor = WuxingMonitor()
        snapshot = monitor.snapshot()
        assert len(snapshot) == 5
        for elem in WuxingElement:
            assert elem.value in snapshot
            assert snapshot[elem.value]["calls"] == 0

    def test_record_call_success(self):
        monitor = WuxingMonitor()
        monitor.record_call(WuxingElement.METAL, success=True, latency_ms=45.0)
        m = monitor.metal
        assert m.call_count == 1
        assert m.success_count == 1
        assert m.failure_count == 0
        assert m.last_status == "ok"
        assert m.consecutive_failures == 0

    def test_record_call_failure(self):
        monitor = WuxingMonitor()
        monitor.record_call(
            WuxingElement.WATER, success=False, latency_ms=500.0, error="timeout"
        )
        m = monitor.water
        assert m.call_count == 1
        assert m.success_count == 0
        assert m.failure_count == 1
        assert m.last_status == "error"
        assert m.last_error == "timeout"
        assert m.consecutive_failures == 1

    def test_consecutive_failures_tracking(self):
        monitor = WuxingMonitor()
        for i in range(5):
            monitor.record_call(WuxingElement.FIRE, success=False, error=f"fail_{i}")
        m = monitor.fire
        assert m.call_count == 5
        assert m.failure_count == 5
        assert m.consecutive_failures == 5

        # One success resets
        monitor.record_call(WuxingElement.FIRE, success=True)
        assert m.consecutive_failures == 0

    def test_record_batch(self):
        monitor = WuxingMonitor()
        monitor.record_batch(
            WuxingElement.WOOD,
            successes=80,
            failures=20,
            latencies_ms=[10.0] * 100,
        )
        m = monitor.wood
        assert m.call_count == 100
        assert m.success_count == 80
        assert m.failure_count == 20
        assert m.consecutive_failures == 20
        assert abs(m.avg_latency_ms - 10.0) < 0.1

    def test_health_report_all_healthy(self):
        monitor = WuxingMonitor()
        # All elements excellent
        for elem in WuxingElement:
            monitor.record_batch(elem, successes=100, failures=0, latencies_ms=[10.0] * 100)

        report = monitor.health_report()
        assert isinstance(report, WuxingReport)
        assert report.overall_grade == HealthGrade.EXCELLENT
        assert report.generation_cycle_ok is True
        assert report.restriction_cycle_ok is True

    def test_health_report_degraded(self):
        monitor = WuxingMonitor()
        # One element down
        monitor.record_batch(WuxingElement.METAL, successes=100, failures=0, latencies_ms=[10.0] * 100)
        monitor.record_batch(WuxingElement.WATER, successes=100, failures=0, latencies_ms=[10.0] * 100)
        monitor.record_batch(WuxingElement.WOOD, successes=100, failures=0, latencies_ms=[10.0] * 100)
        monitor.record_batch(WuxingElement.FIRE, successes=100, failures=0, latencies_ms=[10.0] * 100)
        # Earth degraded: 40% failure rate but < 10 consecutive (don't trigger DOWN)
        # record 3 failures, then 1 success, repeat — so consecutive never exceeds 3
        for _ in range(10):
            monitor.record_call(WuxingElement.EARTH, success=False, latency_ms=100.0)
            monitor.record_call(WuxingElement.EARTH, success=False, latency_ms=100.0)
            monitor.record_call(WuxingElement.EARTH, success=False, latency_ms=100.0)
            monitor.record_call(WuxingElement.EARTH, success=True, latency_ms=100.0)

        report = monitor.health_report()
        assert report.overall_grade in (HealthGrade.DEGRADED, HealthGrade.FAIR)

    def test_health_report_to_dict(self):
        monitor = WuxingMonitor()
        monitor.record_call(WuxingElement.METAL, success=True, latency_ms=10.0)
        report = monitor.health_report()
        d = report.to_dict()
        assert "timestamp" in d
        assert "overall_grade" in d
        assert "elements" in d
        assert "metal" in d["elements"]
        assert d["elements"]["metal"]["call_count"] == 1

    def test_reset_element(self):
        monitor = WuxingMonitor()
        monitor.record_call(WuxingElement.METAL, success=True, latency_ms=10.0)
        assert monitor.metal.call_count == 1

        monitor.reset_element(WuxingElement.METAL)
        assert monitor.metal.call_count == 0
        assert monitor.metal.success_count == 0

    def test_reset_all(self):
        monitor = WuxingMonitor()
        for elem in WuxingElement:
            monitor.record_call(elem, success=True, latency_ms=10.0)

        monitor.reset_all()
        for elem in WuxingElement:
            m = monitor.get_element_metrics(elem)
            assert m.call_count == 0

    def test_uptime(self):
        monitor = WuxingMonitor()
        uptime = monitor.uptime_seconds
        assert uptime >= 0

    def test_property_accessors(self):
        monitor = WuxingMonitor()
        monitor.record_call(WuxingElement.METAL, success=True, latency_ms=15.0)
        assert monitor.metal.call_count == 1
        assert monitor.wood.call_count == 0
        assert monitor.water.call_count == 0
        assert monitor.fire.call_count == 0
        assert monitor.earth.call_count == 0


class TestHealthGrade:
    """测试健康等级."""

    def test_all_grades_exist(self):
        grades = list(HealthGrade)
        assert len(grades) == 5
        values = {g.value for g in grades}
        assert values == {"excellent", "good", "fair", "degraded", "down"}
