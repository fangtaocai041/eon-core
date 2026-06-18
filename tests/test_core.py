"""Tests for eon-core — Coordination Hub (Coord)."""
import sys
from pathlib import Path

# Ensure eon-core's src is importable (before other projects' src)
_eon_root = str(Path(__file__).resolve().parent.parent)
if _eon_root not in sys.path:
    sys.path.insert(0, _eon_root)

import pytest

from src.kernel.origin import OriginKernel
from src.kernel.event_bus import AsyncEventBus
from src.kernel.lifecycle import Lifecycle, LifecycleStage
from src.adapter import EonCoreAdapter


class TestOriginKernel:
    """Test the OriginKernel singleton coordinator."""

    def test_import(self):
        assert OriginKernel is not None

    def test_creation(self):
        kernel = OriginKernel()
        assert kernel is not None

    def test_new_creation(self):
        kernel = OriginKernel.__new__(OriginKernel)
        assert kernel is not None


class TestAsyncEventBus:
    """Test the event bus."""

    def test_import(self):
        assert AsyncEventBus is not None

    def test_creation(self):
        bus = AsyncEventBus()
        assert bus is not None

    def test_event_log(self):
        bus = AsyncEventBus(log_size=50)
        log = bus.event_log()
        assert isinstance(log, list)
        assert len(log) == 0


class TestLifecycle:
    """Test lifecycle state machine."""

    def test_import(self):
        assert Lifecycle is not None

    def test_creation(self):
        lc = Lifecycle()
        assert lc is not None
        alive = lc.is_alive() if callable(lc.is_alive) else lc.is_alive
        assert alive in (True, False)

    def test_summary(self):
        lc = Lifecycle()
        summary = lc.summary()
        assert isinstance(summary, dict)

    def test_transitions(self):
        lc = Lifecycle()
        assert lc.stage == LifecycleStage.SEEDING
        lc.transition(LifecycleStage.SPROUTING)
        assert lc.stage == LifecycleStage.SPROUTING
        lc.transition(LifecycleStage.BLOOMING)
        assert lc.stage == LifecycleStage.BLOOMING


class TestEonCoreAdapter:
    """Test the EonCoreAdapter cross-project interface."""

    def test_import(self):
        assert EonCoreAdapter is not None

    def test_info(self):
        adapter = EonCoreAdapter()
        info = adapter.info()
        assert info["project"] == "eon-core"
        assert "role" in info

    def test_health(self):
        adapter = EonCoreAdapter()
        health = adapter.health()
        assert "status" in health

    def test_search(self):
        adapter = EonCoreAdapter()
        result = adapter.search("test query")
        assert isinstance(result, dict)
