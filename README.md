# ⚙️ eon-core

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge) ![Version](https://img.shields.io/badge/Version-v8.1-blueviolet?style=for-the-badge) ![CAS](https://img.shields.io/badge/CAS-Adaptive-success?style=for-the-badge) ![MCP](https://img.shields.io/badge/MCP-Protocol-important?style=for-the-badge) ![Event](https://img.shields.io/badge/Event-Sourcing-critical?style=for-the-badge) ![CQRS](https://img.shields.io/badge/CQRS-Read%2FWrite-informational?style=for-the-badge) ![Pub/Sub](https://img.shields.io/badge/Pub%2FSub-EventBus-ff69b4?style=for-the-badge) ![6 Projects](https://img.shields.io/badge/6%20Projects-Loaded-orange?style=for-the-badge) ![DAG](https://img.shields.io/badge/DAG-Topology-red?style=for-the-badge)

> 🔄 Coordination Hub — Complex Adaptive System with MCP protocol, Event Sourcing, and CQRS.
> The center that holds the triangle together.

[English](README.md) · [中文](README.zh.md) · [CHANGELOG](CHANGELOG.md)

---

## 📖 Table of Contents

- [Philosophy](#-philosophy)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Ecosystem](#-ecosystem)

---

## 🏛️ Philosophy

> The river flows, knowledge drifts, emergence patterns.

This is not a slogan. It is the operating system running through every line of code, every search, every analysis.

### 📜 Three Tenets

**🌊 The River Flows** — Packages update, species migrate, consensus shifts, climate reshapes. Today's certainty is tomorrow's footnote. We place knowledge on a timeline and view it dynamically.

**🍂 Knowledge Drifts** — The foundation of science is falsifiability (Popper). No discovery is final — only the best current explanation. We speak in calibrated language: evidence suggests, not proves.

**🌟 Emergence Patterns** — Life, consciousness, ecosystems, AI reasoning — all emergent. When three or more independent sources converge on the same unexpected pattern, the system flags emergence — never dismisses it as noise.

### ⚖️ Why This Matters

| Scenario | Traditional | Dynamic Worldview |
|:---------|:-----------|:-------------------|
| Citations | Studies prove | Smith (2022) found X; Jones (2024) added Y |
| Outliers | Dismiss as noise | Three or more sources → emergence signal |
| Knowledge Decay | Handbook frozen | Review records include next review date |
| Method | Fixed pipeline | Dynamic selection, dynamic confidence |

> 道生一，一生二，二生三，三生万物。

From One comes Two, from Two comes Three, from Three come all things.



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

## 🏗️ Architecture

```
eon-core/
  src/kernel/
  ├── origin.py         OriginKernel — coordinator singleton
  ├── event_bus.py      AsyncEventBus — pub/sub + DLQ
  ├── lifecycle.py      5-stage state machine
  ├── cas_core.py       Complex Adaptive System coordinator
  ├── mcp_bridge.py     MCP protocol tool bridge
  └── event_store.py    Event Sourcing + CQRS
  scripts/
  ├── project_loader.py 6-project import bridge
  └── shared_types.py   Canonical ecosystem types
  config/
  └── taiji.yaml        DAG topology definition
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌀 CAS Architecture | Complex Adaptive System with agent discovery + adaptation |
| 🔌 MCP Protocol | Model Context Protocol for cross-project tool communication |
| 📜 Event Sourcing | Append-only event store with replay capability |
| 📊 CQRS | Separate write (EventStore) and read (Projection) models |
| 🚌 AsyncEventBus | In-process pub/sub with dead letter queue |
| 🔗 Project Loader | Zero-conflict isolation import for 6 sibling projects |
| 📡 Emergence Detection | Multi-agent consensus + coalition pattern detection |
| 🎯 Adaptive Orchestration | Learned rules for agent selection based on task context |

---

## 📁 Project Structure

```
eon-core/
  (see Architecture section above)
```

---

## 🔗 Ecosystem

This project is the Coordination Hub (Coord) in the SanShengWanWu ecosystem.

```
Triangle Core (sealed 3):
  📦 fish-ecology-assistant    → Knowledge Supply (V0)
  🔍 cognitive-search-engine   → Search Verification (V1)
  ⚙️ eon-core                  → Coordination Hub (Coord)

Derived Projects (open N):
  🐬 porpoise-agent    → P₁ Porpoise Expert
  🐟 coilia-agent      → P₂ Coilia Expert
  🐟 culter-agent      → P₃ Culter Expert
  🔥 conflict-arbiter  → C  Conflict Arbitration
```

> 🔥 Together infinite power, apart top expert engines.

---

🌱 **Everything Flows · Panta Rhei**

> Heraclitus said: No man ever steps in the same river twice.
>
> We say: You cannot analyze today''s ecological data with last month''s code.

This project is not a fixed toolset — it is a **living system**. Every component has built-in expiration mechanisms, version tracking, and emergence awareness. As your research deepens, packages update, and new methods emerge, it evolves with you.

*Last updated: 2026-06-17　|　Environment: Reasonix Code · DeepSeek Powered*

