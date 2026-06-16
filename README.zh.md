# eon-core ⚙️

**三角核心 Coordinator 层** — 协调内核 · 事件总线 · 五行监控。

> 🌊 万物皆变 · Panta Rhei
>
> 道生一，一生二，二生三，三生万物。

[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![version](https://img.shields.io/badge/version-8.1.0-8b5cf6)]()
[![projects](https://img.shields.io/badge/projects-6-22c55e)]()

[English](README.md) · [中文](README.zh.md) · [更新日志](CHANGELOG.md)

---

## 📋 项目简介

**eon-core** 是三角核心生态系统的协调内核，承担双重角色：

1. **作为项目** — 与 6 个同级项目并列的代码仓库
2. **作为协调器** — 路由项目间事件、管理 DAG 拓扑、提供统一搜索/健康 API

| 🧩 模块 | 🎯 职责 |
|:---------|:--------|
| **OriginKernel** | 协调内核单例 — 启动、搜索、健康脉冲 |
| **AsyncEventBus** | 基于主题的异步发布/订阅（带死信队列） |
| **Lifecycle** | 5 阶段状态机（播种→发芽→开花→结果→修剪） |
| **ProjectLoader** | 导入隔离的 6 项目桥接器 |
| **DAG 拓扑** | YAML 定义的有向无环图路由 |

---

## ⚡ 快速开始

### 📦 安装

```bash
git clone https://github.com/fangtaocai041/eon-core.git
cd eon-core
pip install -e .
```

### 🎮 CLI 使用

```bash
# 启动内核
python -m eon_core bootstrap

# 统跨项目搜索
python -m eon_core search "长江江豚种群恢复"

# 健康检查
python -m eon_core health
```

### ✅ 验证安装

```python
from eon_core.src.kernel.origin import OriginKernel

kernel = OriginKernel()
kernel.bootstrap(config_path="config/taiji.yaml")
print(kernel.health())
```

---

## 🚀 核心功能

### 🎯 OriginKernel 协调器

```python
from eon_core.src.kernel.origin import OriginKernel

kernel = OriginKernel()
kernel.bootstrap(config_path="config/taiji.yaml")
result = kernel.search(query="江豚栖息地", region="china")
```

### 📡 AsyncEventBus 事件总线

```python
from eon_core.src.kernel.event_bus import AsyncEventBus, SystemEvent
import asyncio

bus = AsyncEventBus(capacity=10000)

async def handler(event):
    print(f"收到: {event.topic}")

bus.subscribe("search.result", handler)
await bus.publish(SystemEvent(topic="search.result", payload={"species": "Coilia nasus"}))
```

### 🔌 ProjectLoader 项目桥接

```python
from eon_core.scripts.project_loader import get_fish, load_all

fish = get_fish()
result = fish.search("鳤 保护等级")

# 预加载全部 6 个项目
status = load_all()
print(f"可用: {sum(status.values())}/{len(status)}")
```

### 🔄 生命周期状态机

```python
from eon_core.src.kernel.lifecycle import Lifecycle, LifecycleStage

lc = Lifecycle()
lc.transition_to(LifecycleStage.BLOOMING)
print(lc.is_alive)       # True
print(lc.accepts_events)  # True
```

---

## 📁 项目架构

```
eon-core/
├── src/
│   ├── adapter.py                ← EonCoreAdapter (跨项目接口)
│   ├── main.py                   ← CLI 入口
│   ├── orchestrator_base.py      ← 共享管线数据类
│   └── kernel/
│       ├── origin.py             ← OriginKernel 协调内核
│       ├── event_bus.py          ← AsyncEventBus 事件总线
│       └── lifecycle.py          ← 5 阶段状态机
├── config/
│   ├── taiji.yaml                ← DAG 拓扑定义
│   ├── COMPATIBILITY_MATRIX.yaml ← 顶点兼容性矩阵
│   └── tendrils_registry.yaml    ← 12 个外部探针
├── proto/                        ← gRPC protobuf
├── scripts/
│   ├── project_loader.py         ← 6 项目导入隔离桥接
│   └── shared_types.py           ← 跨项目枚举
├── pyproject.toml
└── Dockerfile
```

---

## 🔗 DAG 拓扑

```
V0 (鱼类知识) ──→ V1 (搜索验证) ──→ V2 (江豚) / V3 (刀鲚) / V4 (鲌类)
```

定义在 `config/taiji.yaml`。

---

## 🔗 关联项目

| 🏗️ 项目 | 🔗 顶点 | 🎯 角色 |
|:---------|:--------:|:--------|
| fish-ecology-assistant | V0 | 知识供给 |
| cognitive-search-engine | V1 | 搜索验证 |
| porpoise-agent | V2 | 江豚专研 |
| coilia-agent | V3 | 刀鲚专研 |
| culter-agent | V4 | 鲌类专研 |
| conflict-arbiter | V5 | 冲突仲裁 |

## 📜 许可证

MIT

---

> 🌊 万物皆变 · Panta Rhei
>
> 🏛️ 赫拉克利特说：人不能两次踏进同一条河流。
>
> 💻 我们说：系统也不该两次犯同一个错误。
>
> **📅 最后更新: 2026-06-21 · 🖥️ Reasonix Code · ⚡ DeepSeek 驱动**

[⬆ 回到顶部](#)
