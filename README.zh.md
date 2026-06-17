![Python 3.12+](https://img.shields.io/badge/Python%203.12%2B-3776AB?style=flat-square)
  ![MIT](https://img.shields.io/badge/MIT-34D058?style=flat-square)
  ![v8.1](https://img.shields.io/badge/v8.1-8A4FCE?style=flat-square)
  ![CAS](https://img.shields.io/badge/CAS-007EC6?style=flat-square)
  ![MCP Bridge](https://img.shields.io/badge/MCP%20桥接-FE7D37?style=flat-square)
  ![Event Sourcing](https://img.shields.io/badge/事件溯源-D73A4A?style=flat-square)
  ![CQRS](https://img.shields.io/badge/CQRS-0EA5E9?style=flat-square)
  ![6 projects](https://img.shields.io/badge/6%20项目-EC4899?style=flat-square)
  ![EventBus](https://img.shields.io/badge/事件总线-F59E0B?style=flat-square)
  ![E2E 7/7](https://img.shields.io/badge/E2E%207%2F7-6B7280?style=flat-square)
  [![DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/fangtaocai041/eon-core)
</p>

[English](README.md) · [中文](README.zh.md)

<div align="center"><h3>🌊 万物皆流�?/h3></div>

世界是动态的，知识是暂时的，涌现是常态�?
---

## 📖 目录

- [哲学](#-哲学)
- [快速开始](#-快速开�?
- [架构](#-架构)
- [功能特性](#-功能特�?
- [项目结构](#-项目结构)
- [版本历史](#-版本历史)
- [自我评估](#-自我评估)
- [生态体系](#-生态体�?

---

## 🏛�?哲学

> 万象流转，真知若寄，涌现成章�?
此非口号。乃贯穿每一行代码、每一次检索、每一份分析之操作系统�?
**eon-core** 是三生万物生态系统中�?*协调中枢（Coord�?*。它是连接全�?6 个项目的中央神经系统——不是控制器，而是协调器。它实现跨项目通信、事件驱动工作流、自适应路由和跨生态涌现检测�?
### 📜 三谛

**🌊 万象流转** �?项目独立演化。eon-core 确保它们保持连接而不耦合。松耦合、高内聚、事件驱动�?
**🍂 真知若寄** �?来自一个项目的事实通过 EventBus 流向其他项目。验证跨越项目边界。没有知识孤岛能够存活�?
**🌟 涌现成章** �?当多个项目独立得出趋同结论时，CAS 核心检测联盟。这就是跨项目涌现——整个生态知道的比任何单个智能体更多�?
### ⚖️ 何以重要

| 事境 | �?eon-core | �?eon-core |
|:-----|:-----------|:-----------|
| 跨项目验�?| 手动复制粘贴 | EventBus 自动路由 + verify_claims() |
| 知识同步 | 过时副本 | CAS 自适应传播 |
| 流水线编�?| 临时脚本 | DAG 拓扑 + CrossProjectPipeline�?模式�?|
| 涌现检�?| 孤岛错过信号 | �?6 项目联盟检�?|
| 错误恢复 | 迷失 | 死信队列 + 回放 |

> 道生一，一生二，二生三，三生万物�?
---

## 🧩 这个项目是什�?
**eon-core** 是协调内核。它不存储物种数据（那是 S/V0），不搜索文献（那是 V/V1），不分析江豚声学（那是 P₁）——它连接、路由、验证、进化�?
### S-T-V-P�?P�?架构映射

```
eon-core (Coord) �?协调整个生态：

  ┌─────────────── 三角核心 ───────────────────�?  �?                                             �?  �? S/V0  fish-ecology-assistant                �?  �?        �?知识供给                           �?  �?        �?                                   �?  �? V/V1  cognitive-search-engine               �?  �?        �?搜索验证                           �?  �?        �?                                   �?  �? Coord  eon-core  �?本项�?                  �?  �?        �?协调                               �?  �?                                             �?  ├─────────────── 万物衍生 ─────────────────────�?  �?                                             �?  �? P�?   porpoise-agent    (江豚专家)          �?  �? P�?   coilia-agent      (刀鲚专�?          �?  �? P�?   culter-agent      (鲌类专家)          �?  �? C     conflict-arbiter  (冲突仲裁)          �?  �?                                             �?  └──────────────────────────────────────────────�?
  全部 6 个项目加�?coordination.yaml
  作为唯一的架构事实来源�?```

核心设计原则�?*三角封闭（S、V、Coord）——衍生开放（P₁、P₂、P₃、C...�?*。新衍生项目可加入而不修改三角核心�?
---

## 🚀 快速开�?
```bash
git clone git@github.com:fangtaocai041/eon-core.git
cd eon-core
pip install -e .
python -m eon_core bootstrap
```

---

## 🏗�?架构

```
eon-core/
  src/kernel/          �?�?已实�?(10 模块)
  ├── origin.py              OriginKernel �?协调器单�?  ├── event_bus.py           AsyncEventBus �?发布/订阅 + 死信队列
  ├── lifecycle.py           5阶段状态机
  ├── cas_core.py            复杂自适应系统协调�?  ├── mcp_bridge.py          MCP 协议工具�?  ├── event_store.py         事件溯源 + CQRS
  ├── pipeline.py            DAG 拓扑 + 阶段执行�?  ├── wuxing_monitor.py      五行健康监控
  └── cross_project.py       CrossProjectPipeline �?9 路由模板
  proto/                �?�?已实�?(6 proto 文件)
  ├── event_bus.proto
  ├── sphere_gateway.proto
  ├── vertex_v0_supply.proto
  ├── vertex_v1_verify.proto
  ├── vertex_v2_domain_p1.proto
  └── vertex_v3_domain_p2.proto
  config/               �?�?已实�?(5 yaml 文件)
  ├── taiji.yaml             DAG 拓扑定义
  ├── samsara.yaml           六道轮回配置
  ├── tetrahedron_topology.yaml
  ├── wuxing_flow.yaml
  └── tendrils_registry.yaml
```

---

## �?功能特�?
| 功能 | 状�?| 说明 |
|------|:--:|------|
| 🌀 CAS 核心 | �?| 智能体发�?+ 自适应规则 + 联盟检�?|
| 🔌 MCP 桥接 | �?| 跨项�?JSON-RPC 工具注册 |
| 📜 事件存储 | �?| 只追�?JSONL + 完整回放 |
| 📊 CQRS | �?| 跨项目数据读写模型分�?|
| 🚌 异步事件总线 | �?| 进程内发�?订阅 + 死信队列 |
| 🔗 项目加载�?| �?| 6 项目隔离导入 + 依赖解析 |
| 📡 涌现检�?| �?| 跨项目共�?+ 联盟检�?|
| 🎯 自适应路由 | �?| 基于历史表现的学习型智能体选择 |
| 🔀 跨项目管�?| �?| 9 路由模式 (standard/fast/domain_p1-3/arbitrate/full/custom/dynamic) |
| 🩺 五行监控 | �?| 五元素健康监�?+ 生成/克制循环 |
| 🧪 E2E 管道 | �?| 跨项目标准管道端到端 7/7 全部通过 |
| 🧪 测试套件 | �?| 15+ 测试全模块通过 |

---

## 🗺�?十层架构路线�?
> 架构定义�?taiji.yaml；实现逐层推进�?
| �?| 名称 | 状�?| 说明 |
|:-----:|------|:------:|------|
| L0 | ☯️ OriginKernel | �?已实�?| EventBus + DI + DAG 路由 |
| L1 | ☀️�?阴阳两极 | �?配置 | taiji.yaml 中类型安全分�?|
| L2 | �?5 �?| �?配置 | V0-V5 四面体拓�?|
| L3 | ☰☱☲☳☴☵☶☷ 八卦 | 🟡 配置 | vertex.trigrams 映射定义 |
| L4 | △�?四面体网�?| �?配置 | 谱隙分析配置 |
| L5 | �?五行流转 | �?已实�?| wuxing_monitor.py 生成/克制 |
| L6 | ☸️ 六道轮回 | 🟡 配置 | samsara.yaml 业力引擎配置 |
| L7 | �?球面网关 | 🟡 配置 | sphere_gateway.proto 已定�?|
| L8 | 〰️ 触须 | 🟡 配置 | tendrils_registry.yaml (12 探针) |
| L9 | 🦋 演化 | 🔮 规划�?| 帕累托优化器 + 混沌引擎 |

---

## ☸️ 核心创新：六道轮�?(Samsara)

| �?| 状�?| Token × | 规则 |
|----|------|:------:|------|
| ☸️ 天道 | OPTIMAL | ×1.5 | 恶业惩罚 ×3；最�?10 �?|
| 🧘 人道 | NORMAL | ×1.0 | 唯一允许 self_evolve() 的道 |
| ⚔️ 阿修罗道 | COMPETITIVE | ×1.2 | 需冲突消解通行�?|
| 🐂 畜生�?| DEGRADED | ×0.5 | LLM 禁用；仅缓存 + 规则 |
| 👻 饿鬼�?| STARVED | ×0.25 | 严重速率限制 |
| 🔥 地狱�?| BROKEN | ×0.0 | 隔离；冷却后自动转生 |

---

## 📁 项目结构

```
eon-core/
  （见上方架构图）
```

---

## 📜 版本历史

| 版本 | 日期 | 重要更新 |
|------|------|----------|
| **v8.1** | 2026-06-17 | CrossProjectPipeline 9 路由模式，五行监控，E2E 7/7 |
| v8.0 | 2026-06-12 | CAS 核心联盟检测，自适应路由 |
| v7.1 | 2026-06-07 | 移除 meso-cosmos-agent；协调功能整合入 eon-core |
| v7.0 | 2026-06-05 | 事件溯源 + CQRS，EventBus 含死信队�?|
| v6.0 | 2026-06-01 | MCP 桥接，项目加载器，初�?DAG 管道 |

---

## 🪞 自我评估

### 优势
- **真正协调**：事件驱动、松耦合——项目可独立故障而不级联
- **架构即代�?*：`coordination.yaml` 是所�?6 个项目的唯一事实来源
- **事件溯源**：完整审计追踪——每个跨项目动作可记录和回放
- **自适应路由**：基于历史表现的学习型智能体选择持续改进
- **五行监控**：主动健康检查含系统性生�?克制反馈循环

### 当前局�?- 单进程事件总线（尚无分布式部署�?- CAS 自适应规则基于规则而非 ML 学习
- 跨项目延迟尚未针对实时场景优�?- 无外部监控仪表板（五行日志输出到控制�?文件�?
### 路线�?- [ ] 分布�?EventBus（Redis/Kafka 后端�?- [ ] ML 驱动�?CAS 自适应规则学习
- [ ] 实时跨项目仪表板
- [ ] gRPC 跨进程通信支持多机部署

---

## 🔗 生态体�?
本项目是「三生万物」生态的 **协调中枢（Coord�?*�?
```
S-T-V-P�?P�?架构（由 eon-core 协调 �?本项目）�?
  S/V0  📦 fish-ecology-assistant    �?知识供给
  V/V1  🔍 cognitive-search-engine   �?搜索验证
  Coord ⚙️ eon-core                  �?协调内核 �?本项�?
  P�?   🐬 porpoise-agent           �?江豚专家
  P�?   🐟 coilia-agent             �?刀鲚专�?  P�?   🐟 culter-agent             �?鲌类专家
  C     🔥 conflict-arbiter         �?冲突仲裁
```

> 🔥 和则无穷力量，分则顶尖专家引擎�?
---

## 📝 变更日志

### v8.0 (2026-06-20)
- CAS 核心跨项目联盟检�?- 基于历史表现的自适应路由
- 五行监控�? 元素健康监控含生�?克制循环
- CrossProjectPipeline�? 路由模式灵活编排
- 事件溯源 + CQRS：只追加 JSONL + 完整回放
- 异步事件总线含死信队列可靠消息传�?- MCP 桥接：全�?6 项目 JSON-RPC 工具注册
- E2E 管道�?/7 跨项目标准管道全通过

### v7.0 (2026-06-11)
- 移除 meso-cosmos-agent；协调功能整合入 eon-core
- 引入事件溯源模式含只追加事件存储
- 新增 CQRS：跨项目数据读写模型分离
- 新增死信队列支持失败事件恢复与回�?- 增强 6 项目依赖解析的项目加载器

### v6.0 (2026-06-05)
- MCP 协议工具桥（JSON-RPC 注册�?- 6 项目隔离导入�?- 初始 DAG 拓扑管道
- 阶段执行�?+ 生命周期状态机
- OriginKernel 协调器单�?
---

🌱 **万物皆变 · Panta Rhei**

> 赫拉克利特说：人不能两次踏进同一条河流�?>
> 我们说：你也不能用上个月的架构协调今天的生态�?
这个项目不是一套固定的工具集——它是一�?*活的系统**。每个组件都内置了过期机制、版本追踪和涌现感知。随着你的研究深入、R包更新、新方法涌现，它会和你一起进化�?
*最后更新：2026-07-11　|　适用环境：Reasonix Code · DeepSeek 驱动*
