![Python 3.12+](https://img.shields.io/badge/Python%203.12%2B-3776AB?style=flat-square)
  ![MIT](https://img.shields.io/badge/MIT-34D058?style=flat-square)
  ![v8.1](https://img.shields.io/badge/v8.1-8A4FCE?style=flat-square)
  ![CAS](https://img.shields.io/badge/CAS-007EC6?style=flat-square)
  ![MCP Bridge](https://img.shields.io/badge/MCP%20Bridge-FE7D37?style=flat-square)
  ![Event Sourcing](https://img.shields.io/badge/Event%20Sourcing-D73A4A?style=flat-square)
  ![CQRS](https://img.shields.io/badge/CQRS-0EA5E9?style=flat-square)
  ![6 projects](https://img.shields.io/badge/6%20projects-EC4899?style=flat-square)
  ![EventBus](https://img.shields.io/badge/EventBus-F59E0B?style=flat-square)
  ![E2E 7/7](https://img.shields.io/badge/E2E%207%2F7-6B7280?style=flat-square)
  [![DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/fangtaocai041/eon-core)
</p>

[English](README.md) · [中文](README.zh.md)

<div align="center"><h3>🌊 Everything flows.</h3></div>

The world is dynamic, knowledge is temporary, emergence is the norm.

---

## 📖 Table of Contents

- [Philosophy](#-philosophy)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Version History](#-version-history)
- [Self-Assessment](#-self-assessment)
- [Ecosystem](#-ecosystem)

---

## 🏛?Philosophy

> The river flows, knowledge drifts, emergence patterns.

This is not a slogan. It is the operating system running through every line of code, every search, every analysis.

**eon-core** is the **Coord (Coordination Hub)** in the SanShengWanWu ecosystem. It is the central nervous system connecting all 6 projects ?not a controller, but a coordinator. It enables cross-project communication, event-driven workflows, adaptive routing, and emergence detection across the entire ecosystem.

### 📜 Three Tenets

**🌊 The River Flows** ?Projects evolve independently. eon-core ensures they stay connected without coupling them. Loose coupling, high cohesion, event-driven.

**🍂 Knowledge Drifts** ?Facts from one project flow to others through the EventBus. Verification crosses project boundaries. No knowledge silo survives.

**🌟 Emergence Patterns** ?When multiple projects independently arrive at converging conclusions, the CAS core detects the coalition. This is cross-project emergence ?the whole ecosystem knowing more than any single agent.

### ⚖ Why This Matters

| Scenario | Without eon-core | With eon-core |
|:---------|:-----------------|:--------------|
| Cross-project verification | Manual copy-paste | EventBus auto-route + verify_claims() |
| Knowledge sync | Stale copies | CAS adaptive propagation |
| Pipeline orchestration | Ad-hoc scripts | DAG topology + CrossProjectPipeline (9 modes) |
| Emergence detection | Siloed missed signals | Coalition detection across all 6 projects |
| Error recovery | Lost in limbo | Dead Letter Queue + replay |

> 道生一，一生二，二生三，三生万物?
From One comes Two, from Two comes Three, from Three come all things.

---

## 🧩 What This Is

**eon-core** is the coordination kernel. It does not store species data (that's S/V0), does not search literature (that's V/V1), does not analyze porpoise acoustics (that's P? ?it connects, routes, verifies, and evolves.

### S-T-V-P?P?Architecture Mapping

```
eon-core (Coord) ?coordinates the entire ecosystem:

  ┌─────────────── Triangle Core ───────────────?  ?                                             ?  ? S/V0  fish-ecology-assistant                ?  ?        ?knowledge supply                   ?  ?        ?                                   ?  ? V/V1  cognitive-search-engine               ?  ?        ?search verification                ?  ?        ?                                   ?  ? Coord  eon-core  ?this project             ?  ?        ?coordination                       ?  ?                                             ?  ├─────────────── Derived Projects ─────────────?  ?                                             ?  ? P?   porpoise-agent    (porpoise expert)   ?  ? P?   coilia-agent      (coilia expert)     ?  ? P?   culter-agent      (culter expert)     ?  ? C     conflict-arbiter  (arbitration)       ?  ?                                             ?  └──────────────────────────────────────────────?
  All 6 projects load coordination.yaml as their
  single source of architectural truth.
```

Key design principle: **Triangle is sealed (S, V, Coord) ?Derived is open (P? P? P? C, ...)**. New derived projects can join without modifying the triangle core.

---

## 🚀 Quick Start

```bash
# Clone
git clone git@github.com:fangtaocai041/eon-core.git
cd eon-core

# Install
pip install -e .

# Run
python -m eon_core bootstrap
```

---

## 🏗?Architecture

```
eon-core/
  src/kernel/          ??IMPLEMENTED (10 modules)
  ├── origin.py              OriginKernel ?coordinator singleton
  ├── event_bus.py           AsyncEventBus ?pub/sub + Dead Letter Queue
  ├── lifecycle.py           5-stage state machine
  ├── cas_core.py            Complex Adaptive System coordinator
  ├── mcp_bridge.py          MCP protocol tool bridge
  ├── event_store.py         Event Sourcing + CQRS
  ├── pipeline.py            DAG topology + stage executor
  ├── wuxing_monitor.py      WuXing health monitor
  └── cross_project.py       CrossProjectPipeline ?9 routing templates
  proto/                ??IMPLEMENTED (6 proto files)
  ├── event_bus.proto
  ├── sphere_gateway.proto
  ├── vertex_v0_supply.proto
  ├── vertex_v1_verify.proto
  ├── vertex_v2_domain_p1.proto
  └── vertex_v3_domain_p2.proto
  config/               ??IMPLEMENTED (5 yaml files)
  ├── taiji.yaml             DAG topology definition
  ├── samsara.yaml           Samsara ring config
  ├── tetrahedron_topology.yaml
  ├── wuxing_flow.yaml
  └── tendrils_registry.yaml
```

---

## ?Features

| Feature | Status | Description |
|---------|:------:|-------------|
| 🌀 CAS Core | ?| Agent discovery + adaptation rules + coalition detection |
| 🔌 MCP Bridge | ?| JSON-RPC tool registry across all projects |
| 📜 Event Store | ?| Append-only JSONL + full replay capability |
| 📊 CQRS | ?| Separate write/read models for cross-project data |
| 🚌 AsyncEventBus | ?| In-process pub/sub + Dead Letter Queue |
| 🔗 Project Loader | ?| 6-project isolated import with dependency resolution |
| 📡 Emergence Detection | ?| Consensus + coalition detection across projects |
| 🎯 Adaptive Routing | ?| Learned agent selection via performance history |
| 🔀 CrossProjectPipeline | ?| 9 routing modes (standard/fast/domain_p1-3/arbitrate/full/custom/dynamic) |
| 🩺 WuXing Monitor | ?| 5-element health monitoring with generation/control cycles |
| 🧪 E2E Pipeline | ?| Cross-project standard pipeline E2E 7/7 all passing |
| 🧪 Test Suite | ?| 15+ tests passing across all modules |

---

## 🗺?10-Layer Architecture Roadmap

> Architecture defined in taiji.yaml; implementation progresses layer by layer.

| Layer | Name | Status | Description |
|:-----:|------|:------:|-------------|
| L0 | ☯ OriginKernel | ?IMPLEMENTED | EventBus + DI + DAG routing |
| L1 | ☀?YinYang Poles | ?CONFIG | Type-safe separation in taiji.yaml |
| L2 | ?5 Vertices | ?CONFIG | V0-V5 in tetrahedron topology |
| L3 | ☰☱☲☳☴☵☶☷ 8 Trigrams | 🟡 CONFIG | Defined as vertex.trigrams mappings |
| L4 | △?TetrahedronMesh | ?CONFIG | Spectral gap analysis config |
| L5 | ?WuXing Flow | ?IMPLEMENTED | wuxing_monitor.py generation/restriction |
| L6 | ☸ Samsara Ring | 🟡 CONFIG | samsara.yaml karma engine config |
| L7 | ?SphereGateway | 🟡 CONFIG | sphere_gateway.proto defined |
| L8 | 〰 Tendrils | 🟡 CONFIG | tendrils_registry.yaml (12 probes) |
| L9 | 🦋 Evolution | 🔮 PLANNED | Pareto optimizer + chaos engine |

---

## ☸ Core Innovation: Samsara (六道轮回)

| Realm | State | Token × | Rule |
|-------|-------|:------:|------|
| ☸ DEVA | OPTIMAL | ×1.5 | Bad deed penalty ×3; max 10 cycles |
| 🧘 HUMAN | NORMAL | ×1.0 | Only realm allowing self_evolve() |
| ⚔ ASURA | COMPETITIVE | ×1.2 | Requires deconfliction pass |
| 🐂 ANIMAL | DEGRADED | ×0.5 | LLM disabled; cache + rules only |
| 👻 PRETA | STARVED | ×0.25 | Severely rate-limited |
| 🔥 NARAKA | BROKEN | ×0.0 | Isolated; auto-rebirth after cooldown |

---

## 📁 Project Structure

```
eon-core/
  (see Architecture section above)
```

---

## 📜 Version History

| Version | Date | Highlights |
|---------|------|------------|
| **v8.1** | 2026-06-17 | CrossProjectPipeline 9 routing modes, WuXing Monitor, E2E 7/7 |
| v8.0 | 2026-06-12 | CAS core coalition detection, adaptive routing |
| v7.1 | 2026-06-07 | Removed meso-cosmos-agent; consolidated coordination into eon-core |
| v7.0 | 2026-06-05 | Event Sourcing + CQRS, EventBus with DLQ |
| v6.0 | 2026-06-01 | MCP Bridge, project loader, initial DAG pipeline |

---

## 🪞 Self-Assessment

### Strengths
- **True coordination**: Event-driven, loosely coupled ?projects can fail independently without cascading
- **Architecture as code**: `coordination.yaml` is the single source of truth for all 6 projects
- **Event Sourcing**: Complete audit trail ?every cross-project action is recorded and replayable
- **Adaptive routing**: Performance-history-based agent selection improves over time
- **WuXing Monitor**: Proactive health checks with systemic generation/control feedback loops

### Current Limitations
- Single-process event bus (no distributed deployment yet)
- CAS adaptation rules are rule-based, not ML-learned
- Cross-project latency not yet optimized for real-time use cases
- No external monitoring dashboard (WuXing logs to console/file)

### Roadmap
- [ ] Distributed EventBus (Redis/Kafka backend)
- [ ] ML-based CAS adaptation rule learning
- [ ] Real-time cross-project dashboard
- [ ] gRPC inter-process communication for multi-machine deployment

---

## 🔗 Ecosystem

This project is the **Coordination Hub (Coord)** in the SanShengWanWu ecosystem.

```
S-T-V-P?P?Architecture (coordinated by eon-core ?this project):

  S/V0  📦 fish-ecology-assistant    ?Knowledge Supply
  V/V1  🔍 cognitive-search-engine   ?Search Verification
  Coord ⚙ eon-core                  ?Coordination Hub ?this project

  P?   🐬 porpoise-agent           ?Porpoise Expert
  P?   🐟 coilia-agent             ?Coilia Expert
  P?   🐟 culter-agent             ?Culter Expert
  C     🔥 conflict-arbiter         ?Conflict Arbitration
```

> 🔥 Together infinite power, apart top expert engines.

---

## 📝 Changelog

### v8.0 (2026-06-18)
- Cross-project coalition detection with CAS core
- Adaptive routing based on performance history
- WuXing Monitor: 5-element health monitoring with generation/control cycles
- CrossProjectPipeline: 9 routing modes for flexible orchestration
- Event Sourcing + CQRS: append-only JSONL + full replay capability
- AsyncEventBus with Dead Letter Queue for reliable messaging
- MCP Bridge: JSON-RPC tool registry across all 6 projects
- E2E Pipeline: 7/7 cross-project standard pipeline tests passing

### v7.0 (2026-06-11)
- Removed meso-cosmos-agent; consolidated coordination into eon-core
- Introduced Event Sourcing pattern with append-only event store
- Added CQRS: separate write/read models for cross-project data
- Added Dead Letter Queue for failed event recovery and replay
- Enhanced project loader with dependency resolution across 6 projects

### v6.0 (2026-06-05)
- MCP protocol tool bridge (JSON-RPC registry)
- 6-project isolated import bridge
- Initial DAG topology pipeline
- Stage executor + lifecycle state machine
- OriginKernel coordinator singleton

---

🌱 **Everything Flows · Panta Rhei**

> Heraclitus said: No man ever steps in the same river twice.
>
> We say: You cannot coordinate today's ecosystem with last month's architecture.

This project is not a fixed toolset ?it is a **living system**. Every component has built-in expiration mechanisms, version tracking, and emergence awareness. As your research deepens, packages update, and new methods emerge, it evolves with you.

*Last updated: 2026-06-18　|　Environment: Reasonix Code · DeepSeek Powered*
