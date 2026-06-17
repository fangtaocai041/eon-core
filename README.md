# ⚙️ eon-core

[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-8.1.0-8b5cf6)]()
[![Frontier](https://img.shields.io/badge/frontier-CAS|MCP|EventSourcing|CQRS-orange)]()

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

> 道生一，一生二，二生三，三生万物。The Coordinator is the One that unifies Knowledge (S) and Verification (V) into the Three.

This is the **Coordinator** of the Triangle. It does not produce knowledge or verify it — it ensures the ecosystem functions as a unified whole. Now rebuilt as a Complex Adaptive System (CAS) with Event Sourcing, CQRS, MCP protocol bridge, and adaptive agent orchestration.

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
*SanShengWanWu Ecosystem · MIT License · fangtaocai041*
