<p align="center">
  🇨🇳 <a href="README.zh.md">中文</a>
</p>

<div align="center">
  <h1>☯️ eon-core — Coordination Kernel</h1>
  <p><strong>Triangle Core Coordinator (T) · 三生万物 v8.1</strong></p>
  <p>OriginKernel · EventBus · YinYang Poles · Tetrahedron Mesh · WuXing · Samsara · Sphere Gateway</p>
  <p>🔗 <a href="https://github.com/fangtaocai041/eon-core">GitHub</a></p>
</div>

<p align="center">
  <a href="../VERSION.yaml"><img src="https://img.shields.io/badge/workspace-v8.1.0-blue" alt="Workspace:v8.1.0"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python"></a>
  <a href="proto/"><img src="https://img.shields.io/badge/protocol-gRPC-green" alt="gRPC"></a>
  <a href="#"><img src="https://img.shields.io/badge/layers-10-purple" alt="Layers:10"></a>
  <a href="#"><img src="https://img.shields.io/badge/adapters-6-orange" alt="Adapters:6"></a>
</p>

## What is eon-core?

The **coordination kernel** of the 三生万物 architecture. Dual nature:

1. **As a project**: Code repo alongside 6 other projects
2. **As an architecture role**: Triangle Core coordinator + infrastructure host

**Two layers**:
- **Kernel (Triangle Core)**: OriginKernel · EventBus · DAG routing · Lifecycle state machine
- **Infrastructure (Derived)**: Vertex adapters · 8 Trigrams · WuXing monitoring · Samsara karma · Self-evolution

## Architecture

```
                  OriginKernel (Singleton)
                       │
          ┌────────────┼────────────┐
          │            │            │
     YangPole      YinPole     EventBus
     (expand)      (verify)    (async queue)
          │            │            │
          └────────────┼────────────┘
                       │
              TetrahedronMesh
              (spectral gap + chaos)
                       │
          ┌────────────┼────────────┐
          │            │            │
     V0(fish)    V1(cognitive)  V2(porpoise)
     V3(coilia)  V4(culter)    V5(conflict)
                       │
          ┌────────────┼────────────┐
          │            │            │
     8 Trigrams    WuXing       Samsara
     (子模块)     (5-element)   (karma)
```

## 10-Layer Architecture

| Layer | Module | Component |
|:-----:|--------|-----------|
| 1 | OriginKernel | Bootstrap, DI container, event sourcing |
| 2 | EventBus | Async pub/sub, all inter-component communication |
| 3 | YinYang Poles | YangPole (expand/search) + YinPole (contract/verify) |
| 4 | Tetrahedron Mesh | DAG topology, spectral gap, chaos disturbance |
| 5 | Vertices (6) | V0-V5 adapters for all 6 sibling projects |
| 6 | Trigrams (8) | MetaSearch, ChineseGateway, GraphTraversal, Debate, Acoustic, Population, Otolith, Resource |
| 7 | WuXing | Wood/Fire/Earth/Metal/Water monitoring (15s cycle) |
| 8 | Samsara | KarmaEngine + KarmaCourt + Reincarnation (60s cycle) |
| 9 | Sphere Gateway | REST/gRPC/WebSocket/MCP unified API |
| 10 | Tendrils + Evolution | External probes + self-evolution (ChaosEngine + ParEGO) |

## 8 Runtime Invariants

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-001 | Topology IS DAG | bootstrap + reconfigure |
| INV-002 | YangPole.verify() raises RuntimeError | mypy strict + runtime |
| INV-003 | YinPole.expand() raises RuntimeError | mypy strict + runtime |
| INV-004 | No direct vertex-to-vertex import | import linter + code review |
| INV-005 | Spectral gap λ₂ ≥ 0.1 × baseline | reconfigure + health_pulse |
| INV-006 | DEVA count ≤ 25% of agents | KarmaCourt.audit_fairness() |
| INV-007 | NARAKA agents auto-reincarnate | SamsaraRing.run_karma_cycle() |
| INV-008 | Reincarnation atomicity (7-step + snapshot) | ReincarnationProtocol.execute() |

## Quick Start

```bash
# Health check
python eon-core/src/main.py --config eon-core/config/taiji.yaml health

# Route test
python eon-core/src/main.py --config eon-core/config/taiji.yaml route "长江江豚种群恢复"

# Via project_loader
python -c "from scripts.project_loader import get_eon; a=get_eon(); print(a.info())"

# Via coordinator
python -c "from scripts.coordinator import coordinator; print(coordinator.health('eon'))"
```

## Directory Structure

```
eon-core/
├── config/                        # taiji.yaml, COMPATIBILITY_MATRIX.yaml, tendrils_registry.yaml, wuxing_flow.yaml
├── proto/                         # gRPC protobuf definitions (event_bus, sphere_gateway, vertex_*)
├── src/
│   ├── adapter.py                 # IProjectAdapter → EonCoreAdapter
│   ├── kernel/                    # OriginKernel, EventBus, Lifecycle
│   ├── poles/                     # YangPole + YinPole
│   ├── vertices/                  # 6 vertex adapters (v0_fish .. v5_conflict)
│   ├── trigrams/                  # 8 functional sub-modules
│   ├── mesh/                      # TetrahedronMesh
│   ├── wuxing/                    # 5-element monitoring
│   ├── samsara/                   # Karma engine, court, ring, reincarnation
│   ├── sphere/                    # API gateway
│   ├── tendrils/                  # External probes
│   └── evolution/                 # Self-evolution, chaos engine, search optimizer
├── tests/
├── scripts/
└── README.md
```

## Linked Projects

| Project | Role | Relationship |
|---------|------|-------------|
| [fish-ecology-assistant](../fish-ecology-assistant/) | Knowledge V0 | Vertex V0 — species knowledge supply |
| [cognitive-search-engine](../cognitive-search-engine/) | Validation V1 | Vertex V1 — literature search & verification |
| [porpoise-agent](../porpoise-agent/) | P₁ Porpoise | Vertex V2 — porpoise domain specialist |
| [coilia-agent](../coilia-agent/) | P₂ Coilia | Vertex V3 — coilia domain specialist |
| [culter-agent](../culter-agent/) | P₃ Culter | Vertex V4 — culter domain specialist |
| [conflict-arbiter](../conflict-arbiter/) | C Conflict | Vertex V5 — conflict arbitration |
