# ⚙️ 永世内核

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge) ![协议](https://img.shields.io/badge/%E5%8D%8F%E8%AE%AE-MIT-brightgreen?style=for-the-badge) ![版本](https://img.shields.io/badge/%E7%89%88%E6%9C%AC-v8.1-blueviolet?style=for-the-badge) ![CAS](https://img.shields.io/badge/CAS-%E8%87%AA%E9%80%82%E5%BA%94-success?style=for-the-badge) ![MCP](https://img.shields.io/badge/MCP-%E5%8D%8F%E8%AE%AE-important?style=for-the-badge) ![事件](https://img.shields.io/badge/%E4%BA%8B%E4%BB%B6-%E6%BA%AF%E6%BA%90-critical?style=for-the-badge) ![CQRS](https://img.shields.io/badge/CQRS-%E8%AF%BB%E5%86%99-informational?style=for-the-badge) ![发布](https://img.shields.io/badge/%E5%8F%91%E5%B8%83-%E6%80%BB%E7%BA%BF-ff69b4?style=for-the-badge) ![6项目](https://img.shields.io/badge/6%E9%A1%B9%E7%9B%AE-%E5%8A%A0%E8%BD%BD-orange?style=for-the-badge) ![DAG](https://img.shields.io/badge/DAG-%E6%8B%93%E6%89%91-red?style=for-the-badge)

> 🔄 协调中枢 — 复杂自适应系统，MCP协议，事件溯源，CQRS。
🔄 协调中枢 — 复杂自适应系统，MCP协议，事件溯源，CQRS。
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

> 万象流转，真知若寄，涌现成章。

此非口号。乃贯穿每一行代码、每一次检索、每一份分析之操作系统。

### 📜 三谛

**🌊 万象流转** — R包迭代，物种迁徙，共识更迭，气候重塑生态。今日之确论，半载后或为陈迹。吾辈不视任何知识为永恒真理，而将其置于时间轴上，以动态眼光审之。

**🍂 真知若寄** — 科学之基石，在于可证伪（波普尔）。无发现乃终极真理——唯有「当下最佳解释」。吾辈用校准之语：「证据提示」而非「证明」，「Smith (2022) 发现」而非「研究表明」。每一条输出，皆镌刻时间之锚。

**🌟 涌现成章** — 生命、意识、生态、AI推理——莫非涌现。不可执一隅以窥全豹。当≥3个独立来源指向同一意外模式，系统不以其为噪声而弃之，乃标记为涌现信号而追踪之。

### ⚖️ 何以重要

| 事境 | 旧习 | 新观 |
|:-----|:----|:----|
| 引用 | 「研究证明」 | 「Smith(2022) 发现 X，Jones(2024) 补 Y」 |
| 异常 | 视为噪声弃之 | ≥3 来源 → 涌现信号，持续追踪 |
| 知识衰减 | 手册尘封不更 | 审查记录含「下次审查日期」 |
| 方法选择 | 流水线一成不变 | 择法动态，信心动态 |

> 道生一，一生二，二生三，三生万物。

此为三角之根，载 430 种长江鱼类。


## 📜 三大信条

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

🌱 **万物皆变 · Panta Rhei**

> 赫拉克利特说：人不能两次踏进同一条河流。
>
> 我们说：你也不能用上个月的代码分析今天的生态数据。

这个项目不是一套固定的工具集——它是一个**活的系统**。每个组件都内置了过期机制、版本追踪和涌现感知。随着你的研究深入、R包更新、新方法涌现，它会和你一起进化。

*最后更新：2026-06-17　|　适用环境：Reasonix Code · DeepSeek 驱动*

