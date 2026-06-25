<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║        ☯  EON-CORE  ·  Coordination Kernel v8  ☯            ║
║  ─────────────────────────────────────────────────────────  ║
║     EventBus · CAS · DAG · Samsara · WuXing · Evolution     ║
║        六道轮回 · 五行动态 · 十层同心 · 道生万物              ║
╚══════════════════════════════════════════════════════════════╝
```

<p align="center">
  🇨🇳 <a href="README.zh.md">中文</a>  ·  🇬🇧 <a href="README.md">English</a>
</p>

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

<p align="center">
  <a href="https://github.com/fangtaocai041/eon-core/stargazers"><img src="https://img.shields.io/github/stars/fangtaocai041/eon-core?style=social" alt="Stars"></a>
  <a href="https://github.com/fangtaocai041/eon-core/network/members"><img src="https://img.shields.io/github/forks/fangtaocai041/eon-core?style=social" alt="Forks"></a>
</p>

<div align="center"><h3>🌊 Everything flows.</h3></div>

The world is dynamic, knowledge is temporary, emergence is the norm.

</div>

---

## 📑 Table of Contents

- [🏛️ Philosophy](#-philosophy)
- [🧩 What This Is](#-what-this-is)
- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture](#-architecture)
- [✨ Features](#-features)
- [🗺️ 10-Layer Architecture Roadmap](#-10-layer-architecture-roadmap)
- [📁 Project Structure](#-project-structure)
- [📜 Version History](#-version-history)
- [🪞 Self-Assessment](#-self-assessment)
- [🔗 Ecosystem](#-ecosystem)
- [📝 Changelog](#-changelog)

---

## 🏛️ Philosophy

> The river flows, knowledge drifts, emergence patterns.

This is not a slogan. It is the operating system running through every line of code, every search, every analysis.

**eon-core** is the **Coord (Coordination Hub)** in the SanShengWanWu ecosystem. It is the central nervous system connecting all 6 projects — not a controller, but a coordinator. It enables cross-project communication, event-driven workflows, adaptive routing, and emergence detection across the entire ecosystem.

### 📜 Three Tenets

**🌊 The River Flows** — Projects evolve independently. eon-core ensures they stay connected without coupling them. Loose coupling, high cohesion, event-driven.

**🍂 Knowledge Drifts** — Facts from one project flow to others through the EventBus. Verification crosses project boundaries. No knowledge silo survives.

**🌟 Emergence Patterns** — When multiple projects independently arrive at converging conclusions, the CAS core detects the coalition. This is cross-project emergence — the whole ecosystem knowing more than any single agent.

### ⚖ Why This Matters

| Scenario | Without eon-core | With eon-core |
|:---------|:-----------------|:--------------|
| Cross-project verification | Manual copy-paste | EventBus auto-route + verify_claims() |
| Knowledge sync | Stale copies | CAS adaptive propagation |
| Pipeline orchestration | Ad-hoc scripts | DAG topology + CrossProjectPipeline (9 modes) |
| Emergence detection | Siloed missed signals | Coalition detection across all 6 projects |
| Error recovery | Lost in limbo | Dead Letter Queue + replay |

> 道生一，一生二，二生三，三生万物。
> From One comes Two, from Two comes Three, from Three come all things.

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

## 🧩 What This Is

**eon-core** is the coordination kernel. It does not store species data (that's S/V0), does not search literature (that's V/V1), does not analyze porpoise acoustics (that's P₁) — it connects, routes, verifies, and evolves.

### S-T-V-P₁-P₂-P₃-C Architecture Mapping

```
eon-core (Coord) → coordinates the entire ecosystem:

  ┌─────────────── Triangle Core ───────────────┐
  │                                             │
  │  S/V0  fish-ecology-assistant                │
  │        → knowledge supply                   │
  │                                             │
  │  V/V1  cognitive-search-engine               │
  │        → search verification                │
  │                                             │
  │  Coord  eon-core  ← this project             │
  │        → coordination                       │
  │                                             │
  ├─────────────── Derived Projects ─────────────┤
  │                                             │
  │  P₁   porpoise-agent    (porpoise expert)   │
  │  P₂   coilia-agent      (coilia expert)     │
  │  P₃   culter-agent      (culter expert)     │
  │  C     conflict-arbiter  (arbitration)       │
  │                                             │
  └──────────────────────────────────────────────┘
  All 6 projects load coordination.yaml as their
  single source of architectural truth.
```

Key design principle: **Triangle is sealed (S, V, Coord) → Derived is open (P₁, P₂, P₃, C, ...)**. New derived projects can join without modifying the triangle core.

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

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

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

## 🏗️ Architecture

<details open><summary><b>📂 Kernel Structure (10 modules)</b></summary>

```
eon-core/
  src/kernel/          → IMPLEMENTED (10 modules)
  ├── origin.py              OriginKernel → coordinator singleton
  ├── event_bus.py           AsyncEventBus → pub/sub + Dead Letter Queue
  ├── lifecycle.py           5-stage state machine
  ├── cas_core.py            Complex Adaptive System coordinator
  ├── mcp_bridge.py          MCP protocol tool bridge
  ├── event_store.py         Event Sourcing + CQRS
  ├── pipeline.py            DAG topology + stage executor
  ├── wuxing_monitor.py      WuXing health monitor
  └── cross_project.py       CrossProjectPipeline → 9 routing templates
  src/                  → IMPLEMENTED (shared engines)
  └── unified_emergence.py   统一涌现检测引擎 (融合 p/f/c 三项目)
  docs/                 → IMPLEMENTED
  └── emergence-engine-guide.md  涌现引擎数据投喂指南
  proto/                → IMPLEMENTED (6 proto files)
  ├── event_bus.proto
  ├── sphere_gateway.proto
  ├── vertex_v0_supply.proto
  ├── vertex_v1_verify.proto
  ├── vertex_v2_domain_p1.proto
  └── vertex_v3_domain_p2.proto
  config/               → IMPLEMENTED (5 yaml files)
  ├── taiji.yaml             DAG topology definition
  ├── samsara.yaml           Samsara ring config
  ├── tetrahedron_topology.yaml
  ├── wuxing_flow.yaml
  └── tendrils_registry.yaml
```

</details>

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

## ✨ Features

<details open><summary><b>📋 Feature List</b></summary>

| Feature | Status | Description |
|---------|:------:|-------------|
| 🌀 CAS Core | ✅ | Agent discovery + adaptation rules + coalition detection |
| 🔌 MCP Bridge | ✅ | JSON-RPC tool registry across all projects |
| 📜 Event Store | ✅ | Append-only JSONL + full replay capability |
| 📊 CQRS | ✅ | Separate write/read models for cross-project data |
| 🚌 AsyncEventBus | ✅ | In-process pub/sub + Dead Letter Queue |
| 🔗 Project Loader | ✅ | 6-project isolated import with dependency resolution |
| 📡 Emergence Detection | ✅ | Consensus + coalition detection across projects |
| 🎯 Adaptive Routing | ✅ | Learned agent selection via performance history |
| 🔀 CrossProjectPipeline | ✅ | 9 routing modes (standard/fast/domain_p1-3/arbitrate/full/custom/dynamic) |
| 🩺 WuXing Monitor | ✅ | 5-element health monitoring with generation/control cycles |
| 🧪 E2E Pipeline | ✅ | Cross-project standard pipeline E2E 7/7 all passing |
| 🧪 Test Suite | ✅ | 15+ tests passing across all modules |

</details>

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

---

## 🧬 Unified Emergence Engine

> **融合三项目涌现能力** — 实时 Z-score 监控 + 批次三层分析 + 自组织领域发现

| Module | Source | Capability |
|--------|:------:|------------|
| `EmergenceMonitor` | p项目 (porpoise) | 实时 Z-score 异常检测 · D₀~D₃ 维度追踪 · D₂→D₃ 相变检测 |
| `EmergenceEngine` | f项目 (fish) | 离线批次分析 · Layer 1 异常 · Layer 2 突变点(CUSUM) · Layer 3 6理论模式匹配 |
| `emerge_domains()` | c项目 (cognitive) | 自组织领域发现 · 跨数据库共现聚类 |

### Quick Usage

```python
from eon_core.unified_emergence import EmergenceMonitor, EmergenceEngine

# 在线监控
mon = EmergenceMonitor(emergence_threshold_sigma=3.0, min_sources=3)
mon.record("recall", 0.85, DimensionalLevel.D1)
signals = mon.check_emergence()

# 离线分析
engine = EmergenceEngine()
results = engine.scan(data={"years": [2018,...,2025], "biomass": [100,...,260]})
```

> 📖 数据投喂指南: [docs/emergence-engine-guide.md](docs/emergence-engine-guide.md)


## 🗺️ 10-Layer Architecture Roadmap

> Architecture defined in taiji.yaml; implementation progresses layer by layer.

| Layer | Name | Status | Description |
|:-----:|------|:------:|-------------|
| L0 | ☯ OriginKernel | ✅ IMPLEMENTED | EventBus + DI + DAG routing |
| L1 | ☀️ YinYang Poles | 🔧 CONFIG | Type-safe separation in taiji.yaml |
| L2 | 🔺 5 Vertices | 🔧 CONFIG | V0-V5 in tetrahedron topology |
| L3 | ☰☱☲☳☴☵☶☷ 8 Trigrams | 🟡 CONFIG | Defined as vertex.trigrams mappings |
| L4 | △ TetrahedronMesh | 🔧 CONFIG | Spectral gap analysis config |
| L5 | 🔥 WuXing Flow | ✅ IMPLEMENTED | wuxing_monitor.py generation/restriction |
| L6 | ☸ Samsara Ring | 🟡 CONFIG | samsara.yaml karma engine config |
| L7 | 🌐 SphereGateway | 🟡 CONFIG | sphere_gateway.proto defined |
| L8 | 〰 Tendrils | 🟡 CONFIG | tendrils_registry.yaml (12 probes) |
| L9 | 🦋 Evolution | 🔮 PLANNED | Pareto optimizer + chaos engine |

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

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

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

## 🪞 Self-Assessment

### Strengths
- **True coordination**: Event-driven, loosely coupled — projects can fail independently without cascading
- **Architecture as code**: `coordination.yaml` is the single source of truth for all 6 projects
- **Event Sourcing**: Complete audit trail — every cross-project action is recorded and replayable
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

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

## 🔗 Ecosystem

This project is the **Coordination Hub (Coord)** in the SanShengWanWu ecosystem.

```
S-T-V-P₁-P₂-P₃-C Architecture (coordinated by eon-core — this project):

  S/V0  📦 fish-ecology-assistant    → Knowledge Supply
  V/V1  🔍 cognitive-search-engine   → Search Verification
  Coord ⚙ eon-core                  → Coordination Hub — this project

  P₁   🐬 porpoise-agent           → Porpoise Expert
  P₂   🐟 coilia-agent             → Coilia Expert
  P₃   🐟 culter-agent             → Culter Expert
  C     🔥 conflict-arbiter         → Conflict Arbitration
```

> 🔥 Together infinite power, apart top expert engines.

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

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

<p align="right"><a href="#-table-of-contents">↑ Back to top</a></p>

---

🌱 **Everything Flows · Panta Rhei**

> Heraclitus said: No man ever steps in the same river twice.
>
> We say: You cannot coordinate today's ecosystem with last month's architecture.

This project is not a fixed toolset — it is a **living system**. Every component has built-in expiration mechanisms, version tracking, and emergence awareness. As your research deepens, packages update, and new methods emerge, it evolves with you.


> 🔧 Agent constraints: [AGENTS.md](../AGENTS.md) · [core-constitution.md](../.reasonix/core-constitution.md) · [research-first](../skills/research-first.md) · [retro-session](../skills/retro-session.md)

*Last updated: 2026-06-18 | Environment: Reasonix Code · DeepSeek Powered*

---

<div align="center">

### 🏷️ Tech & Topics

`coordination` `event-bus` `cas` `cqrs` `event-sourcing` `dag` `wuxing` `mcp-bridge` `cross-project` `emergence-detection` `adaptive-routing` `taiji` `yinyang` `reasonix` `shared-engine`

<br>

<sub>☯ Part of the **SanShengWanWu** ecosystem · Coord (Coordination Hub) · The kernel for all 7 projects</sub>

</div>


---

## 🧬 RCCA 集成 (v2.1.0 便携核心)

本项目已集成 [san-sheng-wanwu-core](https://github.com/fangtaocai041/san-sheng-wanwu-core) 的便携 RCCA 核心模块。

### 已部署的核心能力

| 模块 | 类名 | 用途 |
|:-----|:-----|:-----|
| 阻尼自我模型 | `SelfModelEngine` | 预测误差滑动窗口 → 稳定性检测 |
| 资源分配策略 | `EmotionEngine` | 事件驱动策略选择 → 行为倾向 |
| 概念转座层 | `TranspositionLayer` | 跳跃基因逻辑: 跨域推理模式迁移 |
| 反思循环 | `ReflectionLoop` | 递归思考→转座→自我适应闭环 |

### 快速开始

```python
from src.rcca_core import SelfModelEngine, EmotionEngine, TranspositionLayer, ReflectionLoop

# 初始化自我模型
sm = SelfModelEngine()
state = sm.reflect()  # 稳定性自检

# 情感驱动的转座
tl = TranspositionLayer()
e = EmotionEngine(transposition_layer=tl)
e.stimulate("discovery", 0.8)  # 发现新知识 → 自动推送到转座层

# 跨域转座：将搜索策略从 A 通道迁移到 B 通道
result = tl.transpose("search", "verify", {"concept": "cross_domain", "confidence": 0.9})

# 反思循环
loop = ReflectionLoop()
report = loop.run(["scholar", "cnki", "ncbi"], transposition=tl)
```

### 版本

核心版本: **RCCA v2.1.0** (2026-06-20) · 零外部依赖 · 即插即用
