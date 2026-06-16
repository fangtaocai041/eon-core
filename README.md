# eon-core ☯️

**三角核心 Coordinator 层** — 协调内核 · 事件总线 · 五行监控。

> 万物皆变 · Panta Rhei
>
> 道生一，一生二，二生三，三生万物。

[中文版](README.zh.md) · [更新日志](CHANGELOG.md)

---

## 核心哲学

> 世界是动态的，知识是暂时的，涌现是常态。

这是三角之 **Coordinator（协调者）**。S（知识）和 V（验证）的阴阳对立，由它统一为三。它不生产知识，也不验证知识——它确保系统作为一个整体运转。

### 在三角中的角色

```
三生万物架构：
  S/V0  fish-ecology-assistant    → 知识供给（阴·静）
  V/V1  cognitive-search-engine   → 搜索验证（阳·动）
  Coord eon-core                  → 协调内核（太极点） ← 你在这里
```

---

## 这个项目是什么

它是整个三角核心的神经系统。负责：
- **DAG 拓扑路由** — 任务在 S ↔ V 之间的流动路径
- **EventBus** — 跨项目事件发布/订阅
- **WuXing 健康监控** — 五行（金木水火土）映射到系统组件健康
- **Samsara 业力引擎** — 6 道轮回：任务失败 → 分析原因 → 重生重试

> 赫拉克利特说：人不能两次踏进同一条河流。
>
> 我们说：系统也不该两次犯同一个错误。

---

## 快速上手

```python
from src.origin_kernel import OriginKernel

kernel = OriginKernel()
kernel.health()           # 全系统健康
kernel.route("search")    # DAG 路由
```

---

## 核心能力

| 能力 | 说明 |
|:-----|:------|
| **10 层同心架构** | OriginKernel → YinYang → Vertices → ... → Sphere |
| **DAG 路由** | 有向无环图，任务最优路径 |
| **EventBus** | 跨项目事件通信 |
| **WuXing 监控** | 五行映射系统健康 |
| **Samsara 引擎** | 6 道轮回（失败→重生→重试）|
| **Tetrahedron Mesh** | 四面体网格拓扑 |
| **6 Adapters** | fish / cognitive / porpoise / coilia / conflict / culter |

---

> 鱼在水里，你在岸上，代码在中间。
> 愿协调和河流一样自然流淌。
>
> **最后更新: 2026-06-21 · Reasonix Code · DeepSeek 驱动**
