# eon-core

**Coordinator layer of the Triangle Core** — Event Bus · Project Loader · Lifecycle.

> Together infinite power, apart top expert engines.

[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![version](https://img.shields.io/badge/version-8.1.0-8b5cf6)]()

---

## What It Actually Does

eon-core is a lightweight (~1,500 line) coordination layer that:

1. **Project Loader** (`scripts/project_loader.py`, 407 lines) — imports sibling project adapters via sys.path isolation, creating a unified access point for all 6 projects in the ecosystem
2. **AsyncEventBus** (`src/kernel/event_bus.py`, 146 lines) — in-process async pub/sub with dead letter queue for cross-component messaging
3. **OriginKernel** (`src/kernel/origin.py`, 120 lines) — singleton coordinator that bootstraps all project adapters and provides unified search/lookup/health API
4. **Lifecycle** (`src/kernel/lifecycle.py`, 100 lines) — 5-stage state machine (SEEDING→SPROUTING→BLOOMING→FRUITING→PRUNING) for system phase management
5. **DAG Config** (`config/taiji.yaml`) — static topology definition for the 6-project ecosystem graph

## What It Does NOT Do

The README previously described a "10-layer concentric architecture" (L0-L9). Only L0 (OriginKernel + EventBus) has runtime code. Layers L1-L9 exist only as prototype definitions in proto/ files and config stubs. Future versions may implement them.

## Architecture

```
eon-core/
  src/
    kernel/origin.py        OriginKernel — coordinator singleton
    kernel/event_bus.py     AsyncEventBus — pub/sub + DLQ
    kernel/lifecycle.py     5-stage lifecycle state machine
    adapter.py              EonCoreAdapter (IProjectAdapter)
    main.py                 CLI entry (bootstrap/search/health)
  scripts/
    project_loader.py       6-project import bridge
    shared_types.py         Canonical ecosystem types
  config/
    taiji.yaml              DAG topology definition
  tests/                    11 tests (newly added)
```

## Current Limitations

- EventBus is in-process only (no Redis/gRPC/external broker)
- No persistent event store or event sourcing
- No runtime DAG routing — topology is config-only
- Lifecycle not integrated with OriginKernel
- gRPC definitions exist but no server implementation

## Integration

```python
from scripts.project_loader import get_cognitive, get_porpoise
cognitive = get_cognitive()
cognitive.search("Coilia nasus")
```

## See Also

- [fish-ecology-assistant](https://github.com/fangtaocai041/fish-ecology-assistant) — V0 Knowledge Supply
- [cognitive-search-engine](https://github.com/fangtaocai041/cognitive-search-engine) — V1 Search Verification
