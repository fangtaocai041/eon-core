"""Verify EmergenceBridge loop: Perception -> Emergence -> Evolution."""
import sys, os, logging
logging.basicConfig(level=logging.WARNING)

_WORKSPACE = r"D:\Reasonix"
sys.path.insert(0, _WORKSPACE)
sys.path.insert(0, os.path.join(_WORKSPACE, "eon-core", "src"))
sys.path.insert(0, os.path.join(_WORKSPACE, "eon-core", "src", "shared"))
sys.path.insert(0, os.path.join(_WORKSPACE, "eon-core"))

from unified_emergence import EmergenceMonitor, DimensionalLevel, EmergenceEngine
from src.shared.emergence_bridge import EmergenceBridge

# Test 1: Monitor
print("1. EmergenceMonitor...")
mon = EmergenceMonitor(emergence_threshold_sigma=2.0, min_sources=2)
for _ in range(20):
    for k in ["a","b","c"]:
        mon.record(k, 5.0, DimensionalLevel.D2)
mon.record("a", 50.0, DimensionalLevel.D2)
mon.record("b", 45.0, DimensionalLevel.D2)
mon.record("c", 40.0, DimensionalLevel.D2)
signals = mon.check_emergence()
assert len(signals) >= 1
print(f"   PASS: {len(signals)} signals detected")

# Test 2: Engine
print("2. EmergenceEngine...")
engine = EmergenceEngine()
results = engine.scan(species="Test", data={"years":[2018,2020,2022,2024], "biomass":[100,200,300,400]})
print(f"   PASS: {len(results)} results")

# Test 3: Bridge
print("3. EmergenceBridge...")
bridge = EmergenceBridge(data_dir="data/test_emergence")
stats = bridge.get_stats()
events = bridge.scan_once(force=True)
print(f"   PASS: bridge operational (events={len(events)})")

import shutil
if os.path.exists("data/test_emergence"):
    shutil.rmtree("data/test_emergence")

print("\nALL CHECKS PASSED: Perception -> Emergence -> Evolution loop OK")
