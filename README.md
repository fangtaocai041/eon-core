# eon-core

> **十层同心动态活体架构** — Tao → YinYang → 4 Symbols → 8 Trigrams → Tetrahedron → WuXing → **Samsara** → Sphere → Tendrils

[![Version](https://img.shields.io/badge/version-v7.0.0-blue)](VERSION.yaml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![Protocol](https://img.shields.io/badge/protocol-gRPC-green)](proto/)
[![Architecture](https://img.shields.io/badge/layers-10-purple)](docs/TAIJI_TETRAHEDRON_ARCHITECTURE.md)

## What is eon-core?

A **10-layer concentric dynamic living architecture** that coordinates 4 domain-specific AI agents (fish ecology, cognitive search, porpoise research, coilia research) through:

- **☯️ OriginKernel** — central event bus + DI container + DAG topology routing
- **☀️🌙 Yin-Yang Poles** — strict type-level separation of expansion vs. verification
- **△ Tetrahedron Mesh** — spectral gap analysis for connectivity health
- **⬟ WuXing Flow** — 5-element generation/restriction monitoring cycles
- **☸️ Samsara Ring** — 6-realm karma engine with automatic rebirth/reincarnation
- **○ Sphere Gateway** — unified API facade (REST/gRPC/MCP/WebSocket)
- **〰️ Tendrils** — 12 external probes with retract/extend lifecycle

## Key Innovation: Samsara (六道轮回)

Every agent (vertex & trigram) has an embedded **KarmaEngine** that tracks good/bad deeds. Every 60 seconds, the **KarmaCourt** evaluates all agents and may trigger **Reincarnation** — automatic promotion or demotion through 6 realms:

| Realm | State | Token Multiplier | Special Rule |
|-------|-------|:----------------:|--------------|
| ☸️ DEVA (天道) | OPTIMAL | ×1.5 | Bad deed penalty ×3; max 10 cycles |
| 🧘 HUMAN (人道) | NORMAL | ×1.0 | Only realm where `self_evolve()` is allowed |
| ⚔️ ASURA (阿修罗) | COMPETITIVE | ×1.2 | Requires deconfliction pass |
| 🐂 ANIMAL (畜生) | DEGRADED | ×0.5 | LLM disabled; cache + rules only |
| 👻 PRETA (饿鬼) | STARVED | ×0.25 | Severely rate-limited |
| 🔥 NARAKA (地狱) | BROKEN | ×0.0 | Isolated; auto-rebirth after cooldown |

## Quick Start

```bash
# Clone
git clone https://github.com/nenuyo/eon-core.git
cd eon-core

# Bootstrap the kernel
python -c "import asyncio; from src.kernel.origin import OriginKernel; asyncio.run(OriginKernel().bootstrap())"
```

## Architecture

```
                         ┌──────────────────────┐
                         │   ○ SphereGateway    │  L7: API入口
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   ☯️ OriginKernel     │  L0: 太极起源点
                         │   EventBus + Registry │
                         └──┬───────┬───────┬───┘
                    ┌───────┼───────┼───────┼───────┐
              ┌─────▼──┐ ┌──▼────┐ ┌▼─────┐ ┌─────▼──┐
              │ ☀️ V0  │ │ 🌙 V1 │ │🌤️ V2 │ │ 🌦️ V3 │  L2: 四象
              │ Supply │ │Verify │ │Porpoise│ │Coilia │
              └────────┘ └───────┘ └───────┘ └────────┘
                    │                       │
              ┌─────▼──────┐         ┌──────▼─────┐
              │ △³ Mesh    │         │ ⬟ WuXing   │  L4-L5
              └────────────┘         └────────────┘
                    │                       │
              ┌─────▼───────────────────────▼──┐
              │     ☸️ Samsara Ring + Court     │  L6: 六道轮回
              └────────────────────────────────┘
```

## Module Inventory

| Layer | Directory | Files | Purpose |
|:-----:|-----------|:-----:|---------|
| L0 | `src/kernel/` | 3 | OriginKernel + EventBus + Lifecycle |
| L1 | `src/poles/` | 3 | YangPole / YinPole / Protocol |
| L2 | `src/vertices/` | 5 | 4 gRPC vertex services + base class |
| L3 | `src/trigrams/` | 9 | 8 functional sub-modules (☰☱☲☳☴☵☶☷) |
| L4 | `src/mesh/` | 2 | Tetrahedron topology + spectral analysis |
| L5 | `src/wuxing/` | 7 | 5-element flow engine + override |
| L6 | `src/samsara/` | 8 | Karma + Ring + Court + Reincarnation + Nirvana + Fairness |
| L7 | `src/sphere/` | 1 | API Gateway with 6-layer middleware |
| L8 | `src/tendrils/` | 3 | 12 external probes + lifecycle manager |
| L9 | `src/evolution/` + `src/observability/` | 2 | Pareto optimizer + chaos + telemetry |

**Total: 43 Python modules, 6 proto files, 6 config YAMLs, ~6,000 LOC**

## 8 Architecture Invariants

1. Topology IS DAG — enforced at bootstrap + reconfig
2. YangPole SHALL NOT call YinPole.verify() — mypy strict + runtime guard
3. YinPole SHALL NOT call YangPole.expand() — mypy strict + runtime guard
4. All inter-vertex communication via EventBus or gRPC — no direct import
5. Spectral gap λ₂ ≥ 0.1 × baseline — connectivity health check
6. No agent in DEVA > 10 cycles — fairness auto-rotation
7. NARAKA agents auto-reincarnate after cooldown — self-healing
8. Every reincarnation is atomic with 7-step rollback — transaction safety

## Relationship to Existing Projects

`eon-core` is the **coordination kernel** that wraps 4 existing projects as gRPC microservices:

```
eon-core/              ← NEW (this repo)
  ├── V0 → fish-ecology-assistant    (knowledge supply, port 50051)
  ├── V1 → cognitive-search-engine   (verification engine, port 50052)
  ├── V2 → porpoise-agent            (porpoise domain, port 50053)
  └── V3 → coilia-agent              (coilia domain, port 50054)
```

The existing projects continue to run independently. `eon-core` adds:
- Event-driven routing with DAG topology guarantee
- Automatic quality-based resource allocation (Samsara realms)
- Health monitoring every 5 seconds
- 12 external data probes with self-healing lifecycle

## License

MIT
