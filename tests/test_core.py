"""Tests for eon-core — Coordination Hub (Coord)."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestOriginKernel:
    """Test the OriginKernel singleton coordinator."""

    def test_import(self):
        from src.kernel.origin import OriginKernel
        assert OriginKernel is not None

    def test_creation(self):
        from src.kernel.origin import OriginKernel
        kernel = OriginKernel()
        assert kernel is not None

    def test_creation(self):
        from src.kernel.origin import OriginKernel
        kernel = OriginKernel.__new__(OriginKernel)
        assert kernel is not None


class TestAsyncEventBus:
    """Test the event bus."""

    def test_import(self):
        from src.kernel.event_bus import AsyncEventBus
        assert AsyncEventBus is not None

    def test_creation(self):
        from src.kernel.event_bus import AsyncEventBus
        bus = AsyncEventBus()
        assert bus is not None


class TestLifecycle:
    """Test lifecycle state machine."""

    def test_import(self):
        from src.kernel.lifecycle import Lifecycle, LifecycleStage
        assert Lifecycle is not None

    def test_creation(self):
        from src.kernel.lifecycle import Lifecycle
        lc = Lifecycle()
        assert lc is not None
        # is_alive is likely a property
        alive = lc.is_alive() if callable(lc.is_alive) else lc.is_alive
        assert alive in (True, False)

    def test_summary(self):
        from src.kernel.lifecycle import Lifecycle
        lc = Lifecycle()
        summary = lc.summary()
        assert isinstance(summary, dict)


class TestEonCoreAdapter:
    """Test the EonCoreAdapter cross-project interface."""

    def test_import(self):
        from src.adapter import EonCoreAdapter
        assert EonCoreAdapter is not None

    def test_info(self):
        from src.adapter import EonCoreAdapter
        adapter = EonCoreAdapter()
        info = adapter.info()
        assert info["project"] == "eon-core"
        assert "role" in info

    def test_health(self):
        from src.adapter import EonCoreAdapter
        adapter = EonCoreAdapter()
        health = adapter.health()
        assert "status" in health

    def test_search(self):
        from src.adapter import EonCoreAdapter
        adapter = EonCoreAdapter()
        result = adapter.search("test query")
        assert isinstance(result, dict)


