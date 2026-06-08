# eon-core

> **☯️ Eon-Taiji v7.2 — 十层同心动态活体内核**
>
> 道生一(太极)·一生二(两仪)·二生三(四象三角体)·三生万物(八卦触须)·万物在五行中流转·在六道中轮回

[![Version](https://img.shields.io/badge/version-v7.2.0-blue)](VERSION.yaml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![Layers](https://img.shields.io/badge/layers-10-purple)](docs/TAIJI_TETRAHEDRON_ARCHITECTURE.md)
[![Projects](https://img.shields.io/badge/workspace-5_projects-orange)](docs/PROJECT_RELATIONSHIPS.md)

## 什么是 eon-core？

协调 4 个领域 AI Agent 的**十层同心统一内核**：

| 层 | 名称 | 职责 |
|:--:|------|------|
| L0 | ☯️ 太极起源点 | EventBus + 依赖注入 + DAG 拓扑路由 |
| L1 | ☀️🌙 两仪双极 | 类型安全分离：阳扩展、阴验证 |
| L2 | △ 四象顶点 | V0(知识供给)·V1(验证引擎)·V2(江豚)·V3(刀鲚) |
| L3 | ☰☱☲☳☴☵☶☷ 八卦子模块 | 每顶点衍生两个功能模块 |
| L4 | △³ 三角体网格 | 谱间隙分析 · 连通性健康检测 |
| L5 | ⬟ 五行流转 | 相生相克监控循环 |
| L6 | ☸️ **六道轮回** | 业力引擎 · 自动转生 · 涅槃 |
| L7 | ○ 圆球体网关 | 统一 API (REST/gRPC/MCP/WebSocket) |
| L8 | 〰️ 触须探针 | 12 外部数据源 · 伸缩自愈生命周期 |
| L9 | 🦋 进化引擎 | Pareto 优化 + Rössler 混沌 + 自动回滚 |

## 核心创新：六道轮回 (Samsara)

每个 Agent 内嵌 **KarmaEngine（业力引擎）**，实时追踪善业/恶业。每 60 秒 **KarmaCourt（业力法庭）** 评估所有 Agent，触发 **Reincarnation（转生）**——在六道中自动升降：

| 道 | 状态 | Token倍率 | 特殊规则 |
|----|------|:--------:|----------|
| ☸️ 天道 | 最优 | ×1.5 | 恶业扣分×3；最长10周期 |
| 🧘 人道 | 正常 | ×1.0 | 唯一可主动 `self_evolve()` |
| ⚔️ 阿修罗道 | 竞争 | ×1.2 | 产出需二次验证 |
| 🐂 畜生道 | 降级 | ×0.5 | 禁用LLM，仅缓存+规则 |
| 👻 饿鬼道 | 匮乏 | ×0.25 | 严酷限流 |
| 🔥 地狱道 | 熔断 | ×0.0 | 完全隔离；冷却后自动重生 |

## 快速开始

```bash
git clone https://github.com/fangtaocai041/eon-core.git
cd eon-core

# 健康检查
python src/main.py --config config/taiji.yaml health

# 查询路由
python src/main.py --config config/taiji.yaml route "长江江豚种群恢复趋势"
# → V2 (porpoise-agent 江豚专研)

# 持续运行
python src/main.py --config config/taiji.yaml bootstrap
```

## 工作区 — 五项目协同

| 顶点 | 项目 | 角色 | 适配器 |
|:----:|------|------|--------|
| V0 | fish-ecology-assistant | 知识供给 | FishEcologyAdapter |
| V1 | cognitive-search-engine | 验证引擎 | CognitiveSearchAdapter |
| V2 | porpoise-agent | 江豚专研 (P₁) | PorpoiseAdapter |
| V3 | coilia-agent | 刀鲚专研 (P₂) | CoiliaAdapter |

全部通过 `scripts/project_loader.py` 统一加载——单一直联入口。

## 模块清单

| 层 | 目录 | 文件数 | 功能 |
|:--:|------|:-----:|------|
| L0 | `src/kernel/` | 4 | 起源内核 + 事件总线 + 生命周期 + CLI |
| L1 | `src/poles/` | 3 | 阳极/阴极抽象 + 通信协议 |
| L2 | `src/vertices/` | 5 | 4 顶点服务 + 基类 |
| L3 | `src/trigrams/` | 9 | 8 功能子模块 (☰☱☲☳☴☵☶☷) |
| L4 | `src/mesh/` | 2 | 四面体拓扑 + 谱分析 |
| L5 | `src/wuxing/` | 7 | 五行流转引擎 + 5 代理 |
| L6 | `src/samsara/` | 8 | 业力 + 轮回环 + 法庭 + 转生 + 涅槃 |
| L7 | `src/sphere/` | 1 | API 网关 (6 层中间件) |
| L8 | `src/tendrils/` | 3 | 12 探针 + 生命周期管理 |
| L9 | `src/evolution/` + `src/observability/` | 4 | Pareto + 混沌 + 遥测 |

**44 Python 模块, 6 proto, 6 YAML 配置, ~7,000 行**

## 8 条架构不变量

1. 拓扑必须是无环图 → bootstrap 时 `nx.is_directed_acyclic_graph()`
2. 阳极不得调用验证 → mypy strict + 运行时 `@_guard_yang`
3. 阴极不得调用扩展 → mypy strict + 运行时 `@_guard_yin`
4. 顶点间通信必须通过 EventBus 或 gRPC
5. λ₂ ≥ 0.1 × 基线 → 谱间隙连通性检查
6. 天道最长 10 周期 → 公平性自动轮换
7. 地狱道冷却后自动重生 → 自愈
8. 每次转生原子化 → 7 步协议 + 快照回滚

## 相关文档

- [架构全量文档](docs/TAIJI_TETRAHEDRON_ARCHITECTURE.md)
- [项目关系文档](docs/PROJECT_RELATIONSHIPS.md)
- [VERSION.yaml](VERSION.yaml)

## 许可证

MIT
