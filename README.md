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

## 🎯 核心哲学

> 世界是动态的，知识是暂时的，涌现是常态。

这是三角之 **Coordinator（协调者）**。S（知识）和 V（验证）的阴阳对立，由它统一为三。它不生产知识，也不验证知识——它确保系统作为一个整体运转。

### 🔗 在三角中的角色
```
```
三生万物架构：
  S/V0  fish-ecology-assistant    → 知识供给（阴·静）
  V/V1  cognitive-search-engine   → 搜索验证（阳·动）
  Coord eon-core                  → 协调内核（太极点） ← 你在这里
```
```

---
```
## 🧩 这个项目是什么
```
它是整个三角核心的神经系统。负责：
- **DAG 拓扑路由** — 任务在 S ↔ V 之间的流动路径，定义于 `config/taiji.yaml`
- **EventBus** — 跨项目事件发布/订阅（带死信队列）
- **WuXing 健康监控** — 五行（金木水火土）映射到系统组件健康
- **Samsara 业力引擎** — 6 道轮回：任务失败 → 分析原因 → 重生重试
```
> 赫拉克利特说：人不能两次踏进同一条河流。
>
> 我们说：系统也不该两次犯同一个错误。
```

---
```
## ⚡ 快速上手
```
```python
from eon_core.src.kernel.origin import OriginKernel
import asyncio
```
kernel = OriginKernel()
asyncio.run(kernel.bootstrap())
print(kernel.health())      # 全系统健康
result = kernel.search("长江江豚")   # 统一搜索
```
```

---
```
## 🚀 核心能力
```
| 🚀 能力 | 📝 说明 |
|:---------|:--------|
| **10 层同心架构** | OriginKernel → YinYang → Vertices → ... → Sphere |
| **DAG 路由** | 有向无环图，任务最优路径，定义于 `taiji.yaml` |
| **EventBus** | 跨项目异步事件通信（带 DLQ） |
| **WuXing 监控** | 五行映射系统健康（金木水火土） |
| **Samsara 引擎** | 6 道轮回（失败→重生→重试）|
| **Tetrahedron Mesh** | 四面体网格拓扑 |
| **6 Adapters** | fish / cognitive / porpoise / coilia / culter / conflict |
```

---
```
## 📁 项目架构
```
```
eon-core/
├── src/kernel/
│   ├── origin.py           ← OriginKernel 协调内核
│   ├── event_bus.py        ← AsyncEventBus 事件总线
│   └── lifecycle.py        ← 5 阶段状态机
├── config/
│   ├── taiji.yaml           ← DAG 拓扑定义（v7.4）
│   ├── COMPATIBILITY_MATRIX.yaml
│   └── tendrils_registry.yaml
├── proto/                   ← 6 gRPC protobuf 定义
├── scripts/
│   ├── project_loader.py    ← 6 项目 DirectLoader
│   └── shared_types.py
├── tests/
└── pyproject.toml
```


## 🔗 生态体系
```
> 🔥 和则无穷力量，分则顶尖专家引擎。
```
本项目是「三生万物」生态的 Coord。
```
```
三角核心 (sealed 3):
  📦 fish-ecology-assistant    → 知识供给 (V0)
  🔍 cognitive-search-engine   → 搜索验证 (V1)
  ⚙️ eon-core                  → 协调内核 (Coord)
```
万物衍生 (open N):
  🐬 porpoise-agent    → 江豚专研 (P₁)
  🐟 coilia-agent      → 刀鲚专研 (P₂)
  🐟 culter-agent      → 鲌类专研 (P₃)
  🔥 conflict-arbiter  → 冲突仲裁 (C)
```

> 🌊 万物皆变 · Panta Rhei
>
> 🏛️ 赫拉克利特说：人不能两次踏进同一条河流。
>
> 💻 我们说：系统也不该两次犯同一个错误。
>
> **📅 最后更新: 2026-06-17 · 🖥️ Reasonix Code · ⚡ DeepSeek 驱动**

[⬆ 回到顶部](#)
