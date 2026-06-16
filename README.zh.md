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

**eon-core** 是三角核心生态系统的协调内核（道），承担双重角色：

1. **作为项目** — 与 6 个同级项目并列的代码仓库
2. **作为协调器** — 路由项目间事件、管理 DAG 拓扑（taiji.yaml）、提供统一搜索/健康 API

### 🧩 架构角色

三生万物架构中，eon-core 是 **Coordinator（协调者）**。S（知识供给）和 V（搜索验证）的阴阳对立，由它统一为三。它不生产知识，也不验证知识——它确保系统作为一个整体运转。

```
三生万物架构：
  道 (eon-core)
  ├── S/V0  fish-ecology-assistant    → 知识供给（阴·静）
  ├── V/V1  cognitive-search-engine   → 搜索验证（阳·动）
  ├── V2    porpoise-agent            → 江豚专研
  ├── V3    coilia-agent              → 刀鲚专研
  ├── V4    culter-agent              → 鲌类专研
  └── C     conflict-arbiter          → 冲突仲裁
```

| 🧩 模块 | 🎯 职责 |
|:---------|:--------|
| **OriginKernel** | 协调内核单例 — bootstrap → search/lookup/health |
| **AsyncEventBus** | 基于 topic 的异步发布/订阅（带死信队列 DLQ） |
| **Lifecycle** | 5 阶段状态机（播种→发芽→开花→结果→修剪） |
| **ProjectLoader** | 导入隔离的 6 项目桥接器（DirectLoader） |

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
import asyncio

kernel = OriginKernel()
asyncio.run(kernel.bootstrap())      # bootstrap() 是 async 方法，无参数
result = kernel.search("珠星三块鱼")
print(result)
print(kernel.health())
```

---

## 🚀 核心功能

### 🎯 OriginKernel 协调器

`OriginKernel` 读取 `config/taiji.yaml` 配置，加载 6 个项目适配器，对外暴露统一 API。

```python
from eon_core.src.kernel.origin import OriginKernel
import asyncio

kernel = OriginKernel()

# 启动内核（async）
asyncio.run(kernel.bootstrap())

# 统一搜索入口 → 委托 workspace.search_species()
result = kernel.search("江豚栖息地")

# 知识库查询 → 委托 workspace.lookup_species()
profile = kernel.lookup("Ochetobius elongatus")

# 全栈健康检查 → 轮询所有 6 项目
status = kernel.health()
print(f"Projects loaded: {status['eon_core']['projects_loaded']}")
```

### 📡 AsyncEventBus 事件总线

基于 topic 的异步发布/订阅，带死信队列（DLQ）。

```python
from eon_core.src.kernel.event_bus import AsyncEventBus, SystemEvent
import asyncio

bus = AsyncEventBus(capacity=10000, dlq_capacity=1000)

async def handler(event: SystemEvent):
    print(f"收到 topic={event.topic}: {event.payload}")

# 订阅 topic
sub = await bus.subscribe("vertex.V0", handler)

# 发布事件
event = SystemEvent(topic="vertex.V0", payload={"species": "Coilia nasus"})
event_id = await bus.publish(event, topic="vertex.V0")

# 消费事件（等待下一个）
consumed = await bus.consume("vertex.V0", timeout=30.0)

# 取消订阅
await sub.unsubscribe()
```

### 🔌 ProjectLoader 项目桥接

使用 `importlib` 零进程导入隔离，支持 6 项目（fish/cognitive/porpoise/coilia/culter/conflict）。

```python
from scripts.project_loader import get_fish, load_all

# 单项目加载
fish = get_fish()            # → FishEcologyAdapter wrapper
result = fish.search("鳤 保护等级")

# 批量预加载全部 6 项目
status = load_all()
print(f"可用: {sum(status.values())}/{len(status)}")
```

### 🔄 生命周期状态机

5 阶段状态机：SEEDING → SPROUTING → BLOOMING → FRUITING → PRUNING → SEEDING

```python
from eon_core.src.kernel.lifecycle import Lifecycle, LifecycleStage

lc = Lifecycle()                    # 初始: SEEDING
lc.transition(LifecycleStage.SPROUTING)
lc.transition(LifecycleStage.BLOOMING)
print(lc.is_alive)                  # True（仅 SEEDING/PRUNING 时为 False）
print(lc.accepts_events)            # True（仅 BLOOMING 接受外部事件）
print(lc.allows_mutation)           # True
print(lc.summary())                 # {stage, uptime_seconds, transition_count}
```

---

## 📁 项目架构

```
eon-core/
├── src/
│   ├── adapter.py                ← EonCoreAdapter（跨项目接口）
│   ├── main.py                   ← CLI 入口
│   ├── orchestrator_base.py      ← 共享管线数据类
│   └── kernel/
│       ├── origin.py             ← OriginKernel 协调内核（道）
│       ├── event_bus.py          ← AsyncEventBus 事件总线
│       └── lifecycle.py          ← 5 阶段状态机
├── config/
│   ├── taiji.yaml                ← DAG 拓扑定义（单一口径）
│   ├── COMPATIBILITY_MATRIX.yaml ← 顶点兼容性矩阵
│   └── tendrils_registry.yaml    ← 12 个外部探针
├── proto/
│   ├── event_bus.proto
│   ├── sphere_gateway.proto
│   ├── vertex_v0_supply.proto
│   ├── vertex_v1_verify.proto
│   ├── vertex_v2_domain_p1.proto
│   └── vertex_v3_domain_p2.proto
├── scripts/
│   ├── project_loader.py         ← 6 项目导入隔离桥接（DirectLoader）
│   └── shared_types.py           ← 跨项目枚举
├── tests/
├── pyproject.toml
└── Dockerfile
```

---

## 🔗 DAG 拓扑

定义在 `config/taiji.yaml（v7.4）`：

```
V0 (fish-ecology-assistant) ──→ V1 (cognitive-search-engine) ──→ V2 (porpoise-agent)
                                                              ──→ V3 (coilia-agent)
                                                              ──→ V4 (culter-agent)
```

顶点兼容性在 `COMPATIBILITY_MATRIX.yaml` 中定义。

---

## 🔗 关联项目

| 🏗️ 项目 | 🔗 顶点 | 🎯 角色 |
|:---------|:--------:|:--------|
| fish-ecology-assistant | V0 | 知识供给 — `lookup_species() → SpeciesProfile` |
| cognitive-search-engine | V1 | 搜索验证 — `search_species() → SearchResult` |
| porpoise-agent | V2 | 江豚专研 — `analyze_contradiction() → Route` |
| coilia-agent | V3 | 刀鲚专研 — `assess_species() → Assessment` |
| culter-agent | V4 | 鲌类专研 — `assess_culter_species() → SpeciesAssessment` |
| conflict-arbiter | C | 冲突仲裁 — 保护级别冲突检测 |

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
