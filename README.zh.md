# ⚙️ 永世内核

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python) ![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge) ![Version](https://img.shields.io/badge/Version-v8.1.0-blueviolet?style=for-the-badge) ![CAS](https://img.shields.io/badge/CAS-Adaptive-success?style=for-the-badge) ![MCP](https://img.shields.io/badge/MCP-Protocol-orange?style=for-the-badge) ![Event](https://img.shields.io/badge/Event-Sourcing-yellow?style=for-the-badge) ![CQRS](https://img.shields.io/badge/CQRS-Read%2FWrite-red?style=for-the-badge) ![Pub/Sub](https://img.shields.io/badge/Pub%2FSub-EventBus-9cf?style=for-the-badge) ![6 Projects](https://img.shields.io/badge/6%20Projects-Loaded-ff69b4?style=for-the-badge) ![DAG](https://img.shields.io/badge/DAG-Topology-important?style=for-the-badge)

> 🔄 协调中枢 — 复杂自适应系统，MCP协议，事件溯源，CQRS。
> 三角之中，万物之轴。

[English](README.md) · [中文](README.zh.md) · [更新日志](CHANGELOG.md)

---

## 📖 目录

- [哲学](#-哲学)
- [快速开始](#-快速开始)
- [架构](#-架构)
- [功能特性](#-功能特性)
- [项目结构](#-项目结构)
- [生态体系](#-生态体系)

---

## 🏛️ 哲学

> 🌍 世界是动态的。📖 知识是暂时的。🌟 涌现是常态。

### 📜 三大信条

**🌍 世界是动态的** — R包在更新，物种分布变化，科学共识在演进。今天正确的结论，六个月后可能过时。

**📖 知识是暂时的** — 科学的基石是可证伪（波普尔）。没有发现是终极真理——只有当前最佳解释。我们用校准语言：证据表明，而非证明。

**🌟 涌现是常态** — 生命、意识、生态系统、AI推理——都是涌现现象。当≥3个独立来源指向同一意外模式，系统标记为涌现信号。

### ⚖️ 为什么这对研究很重要

| 场景 | 传统做法 | 动态世界观 |
|:-----|:--------|:----------|
| 引用 | 研究证明 | Smith(2022)发现X，Jones(2024)补充Y |
| 异常值 | 当作噪声 | ≥3来源→涌现信号 |
| 知识衰减 | 手册冻结 | 含下次审查日期 |

> 道生一，一生二，二生三，三生万物。

这是三角之核心，承载 430 种长江鱼类。


## 🚀 快速开始

```bash
git clone git@github.com:fangtaocai041/eon-core.git
cd eon-core
pip install -e .
python -m eon_core bootstrap
```

---

## 🏗️ 架构

```
eon-core/
  src/kernel/
  ├── origin.py         OriginKernel — 协调器单例
  ├── event_bus.py      AsyncEventBus — 发布/订阅 + 死信队列
  ├── lifecycle.py      5阶段状态机
  ├── cas_core.py       复杂自适应系统协调器
  ├── mcp_bridge.py     MCP 协议工具桥
  └── event_store.py    事件溯源 + CQRS
  scripts/
  ├── project_loader.py 6项目导入桥
  └── shared_types.py   规范生态类型
  config/
  └── taiji.yaml        DAG 拓扑定义
```

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🌀 CAS 架构 | 复杂自适应系统，智能体发现+自适应 |
| 🔌 MCP 协议 | 跨项目工具通信标准化 |
| 📜 事件溯源 | 只追加事件存储+回放 |
| 📊 CQRS | 读写分离 (EventStore + Projection) |
| 🚌 异步事件总线 | 进程内发布/订阅 + 死信队列 |
| 🔗 项目加载器 | 6项目零冲突隔离导入 |
| 📡 涌现检测 | 多智能体共识+联盟模式检测 |
| 🎯 自适应编排 | 任务上下文驱动的智能体选择 |

---

## 📁 项目结构

```
eon-core/
  (见上方架构图)
```

---

## 🔗 生态体系

本项目是「三生万物」生态的 协调中枢 (Coord)。

```
三角核心 (sealed 3):
  📦 fish-ecology-assistant    → 知识供给 (V0)
  🔍 cognitive-search-engine   → 搜索验证 (V1)
  ⚙️ eon-core                  → 协调内核 (Coord)

万物衍生 (open N):
  🐬 porpoise-agent    → P₁ 江豚专研
  🐟 coilia-agent      → P₂ 刀鲚专研
  🐟 culter-agent      → P₃ 鲌类专研
  🔥 conflict-arbiter  → C  冲突仲裁
```

> 🔥 和则无穷力量，分则顶尖专家引擎。

---
*SanShengWanWu Ecosystem · MIT License · fangtaocai041*
