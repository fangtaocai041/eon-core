<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║        ☯  EON-CORE  ·  协调内核 v8  ☯                       ║
║  ─────────────────────────────────────────────────────────  ║
║     EventBus · CAS · DAG · Samsara · WuXing · Evolution     ║
║        六道轮回 · 五行动态 · 十层同心 · 道生万物              ║
╚══════════════════════════════════════════════════════════════╝
```

<p align="center">
  🇬🇧 <a href="README.md">English</a>  ·  🇨🇳 <a href="README.zh.md">中文</a>
</p>

[![Python 3.12+](https://img.shields.io/badge/Python%203.12%2B-3776AB?style=flat-square)]()
[![v8.1](https://img.shields.io/badge/v8.1-8A4FCE?style=flat-square)]()
[![CAS](https://img.shields.io/badge/CAS-007EC6?style=flat-square)]()
[![EventBus](https://img.shields.io/badge/EventBus-F59E0B?style=flat-square)]()
[![6 projects](https://img.shields.io/badge/6%20projects-EC4899?style=flat-square)]()
[![E2E 7/7](https://img.shields.io/badge/E2E%207%2F7-6B7280?style=flat-square)]()

<p align="center">
  <a href="https://github.com/fangtaocai041/eon-core/stargazers"><img src="https://img.shields.io/github/stars/fangtaocai041/eon-core?style=social" alt="Stars"></a>
  <a href="https://github.com/fangtaocai041/eon-core/network/members"><img src="https://img.shields.io/github/forks/fangtaocai041/eon-core?style=social" alt="Forks"></a>
</p>

<div align="center"><h3>🌊 万物皆流。</h3></div>

世界是动态的，知识是暂时的，涌现是常态。

</div>

---

## 📑 目录

- [🧠 核心哲学](#-核心哲学)
- [🧩 项目定位](#-项目定位)
- [🚀 快速开始](#-快速开始)
- [🏗️ 架构](#-架构)
- [✨ 核心特性](#-核心特性)
- [🗺️ 十层架构路线图](#-十层架构路线图)
- [☸ 核心创新：Samsara（六道轮回）](#-核心创新samsara六道轮回)
- [📜 版本历史](#-版本历史)
- [🪞 自我评价](#-自我评价)

---

## 🧠 核心哲学

> 🌍 世界是动态的，📖 知识是暂时的，🌟 涌现是常态。

### 📜 三大信条

**🌍 世界是动态的** — 项目独立进化。eon-core 确保它们通过 EventBus 保持同步，无论各自如何变化。

**📖 知识是暂时的** — 来自一个项目的事实通过 EventBus 流向其他项目。昨天的一个项目发现成为今天另一个项目的基础。

**🌟 涌现是常态** — 当多个项目独立得出收敛结论时，系统不是各管各的，而是识别为跨项目涌现信号。

> 道生一，一生二，二生三，三生万物。
> — 《道德经》第四十二章

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 🧩 项目定位

**eon-core** 是三生万物生态体系中的 **Coord（协调中枢）**。

它不存储物种数据（那是 fish 的职责），不执行搜索（那是 cognitive 的职责），不专研特定物种（那是 porpoise/coilia/culter 的职责）。它是轻量协调内核——确保六个项目如一个整体般运作。

### S-T-V-P₁-P₂-P₃-C 架构映射

```
S/V0  📦 fish-ecology-assistant    → 知识供给
V/V1  🔍 cognitive-search-engine   → 搜索验证
Coord ⚙ eon-core                  → 协调中枢（本项目）
P₁    🐬 porpoise-agent           → 江豚专研
P₂    🐟 coilia-agent             → 刀鲚专研
P₃    🐟 culter-agent             → 鲌类专研
C     🔥 conflict-arbiter         → 冲突仲裁
```

核心设计原则：**三角密闭（S、V、Coord）→ 衍生开放（P₁、P₂、P₃、C 无限扩展）**

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 🚀 快速开始

```bash
git clone https://github.com/fangtaocai041/eon-core.git
cd eon-core
pip install -e .
```

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 🏗️ 架构

<details open><summary><b>📂 内核结构（10 模块）</b></summary>

```
src/kernel/          10 模块
├── origin.py              OriginKernel → 协调器单例
├── event_bus.py           AsyncEventBus → 发布订阅 + 死信队列
├── cas_core.py            CAS Core → 智能体发现 + 自适应规则
├── dag_router.py          DAG Router → 拓扑路由（无环验证）
├── yin_yang.py            YinYang Poles → 类型安全极分离
├── wuxing_monitor.py      WuXing → 五元素健康监控
├── samsara_ring.py        Samsara → 六道业力轮回
├── tetrahedron.py         TetrahedronMesh → 谱间隙分析
├── sphere_gateway.py      SphereGateway → 多项目网关
└── cross_project.py       CrossProjectPipeline → 9 路由模板
```

</details>

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## ✨ 核心特性

<details open><summary><b>📋 特性列表</b></summary>

| 特性 | 状态 | 说明 |
|------|:----:|------|
| 🌀 CAS Core | ✅ | 智能体发现 + 自适应规则 + 联盟检测 |
| 🔌 MCP Bridge | ✅ | 跨所有项目的 JSON-RPC 工具注册 |
| 📜 Event Store | ✅ | 仅追加 JSONL + 完整重放能力 |
| 📊 CQRS | ✅ | 跨项目数据读写分离模型 |
| 🚌 AsyncEventBus | ✅ | 进程内发布订阅 + 死信队列 |
| 🔗 Project Loader | ✅ | 6 项目隔离导入 + 依赖解析 |
| 📡 涌现检测 | ✅ | 跨项目共识 + 联盟检测 |
| 🎯 自适应路由 | ✅ | 基于性能历史的学习型智能体选择 |
| 🔀 CrossProjectPipeline | ✅ | 9 路由模式 |
| 🩺 WuXing 监控 | ✅ | 五元素相生相克健康监控 |
| 🧪 E2E Pipeline | ✅ | 跨项目标准管线 E2E 7/7 全通过 |

</details>

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 🗺️ 十层架构路线图

| 层 | 组件 | 状态 |
|:--|------|:----:|
| L0 | ☯ OriginKernel | ✅ 已实现 |
| L1 | ☀️ YinYang Poles | 🔧 配置 |
| L2 | 🔺 5 Vertices (V0-V4) | 🔧 配置 |
| L3 | ☯ 8 Trigrams | 📋 设计中 |
| L4 | △ TetrahedronMesh | 🔧 配置 |
| L5 | 🔥 WuXing Flow | ✅ 已实现 |
| L6 | ☸ Samsara Ring | ✅ 已实现 |
| L7 | 🌐 SphereGateway | 🟡 配置 |

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## ☸ 核心创新：Samsara（六道轮回）

**业力驱动的自愈系统。** 当智能体表现不佳时，它不是被丢弃，而是进入六道轮回——经过冷却、净化、重生，带着从失败中吸取的教训回归。

关键不变量：拓扑 DAG、Yin-Yang 极隔离、EventBus 隔离、谱间隙、DEVA 公平性、NARAKA 自愈、重生原子性（7 步协议 + 快照回滚）。

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 📜 版本历史

| 版本 | 日期 | 主题 |
|------|------|------|
| **v8.1** | 2026-06-18 | 统一协调 7 项目 + culter-agent + conflict-arbiter |
| **v8.0** | 2026-06-10 | 10 层同心架构 + Samsara 业力引擎 |
| **v7.0** | 2026-06-07 | 跨项目协调内核 |

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

## 🪞 自我评价

### 优势
- **事件溯源**：完整审计追踪——每个跨项目操作都被记录，带时间戳
- **真正协调**：事件驱动、松耦合——项目可以独立失败而不互相拖累
- **自愈**：Samsara 业力系统自动检测、隔离、重生失效组件

### 局限
- 专为 Reasonix 生态设计，非通用协调框架
- 需所有 6 个项目都在本地可用
- 无 Web UI，纯 CLI

<p align="right"><a href="#-目录">↑ 返回目录</a></p>

---

## 🌱 万物皆变 · Panta Rhei

> 赫拉克利特说：人不能两次踏进同一条河流。
>
> 我们说：知识会老去，但人类对世界的追问永不落幕。昨日之真理为今日之基石，今日之未知为明日之征途。我们的目光，从不囿于已知的疆界；我们的脚步，终将踏上那片星光璀璨的浩瀚征途。

这个项目不是一套固定的工具集——它是一个**活的系统**。

*最后更新: 2026-06-18 | Reasonix Code · DeepSeek 驱动*

---

<div align="center">

### 🏷️ 技术标签

`协调内核` `事件总线` `CAS` `CQRS` `事件溯源` `DAG` `业力轮回` `五行动态` `MCP桥接` `跨项目` `涌现检测` `自适应路由` `太极` `阴阳` `Reasonix`

<br>

<sub>☯ 属于 **三生万物** 生态体系 · Coord 协调中枢 · 为全部 7 个项目提供内核</sub>

</div>
