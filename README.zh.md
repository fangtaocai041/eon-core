<p align="center">
  🇬🇧 <a href="README.md">English</a>
</p>

<div align="center">
  <h1>☯️ eon-core — 协调内核</h1>
  <p><strong>三角核心协调器 (T) · 三生万物 v8.1</strong></p>
  <p>OriginKernel · EventBus · 阴阳两极 · 四面体网格 · 五行 · 六道 · Sphere 网关</p>
  <p>🔗 <a href="https://github.com/fangtaocai041/eon-core">GitHub</a></p>
</div>

<p align="center">
  <a href="../VERSION.yaml"><img src="https://img.shields.io/badge/workspace-v8.1.0-blue" alt="Workspace:v8.1.0"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python"></a>
  <a href="proto/"><img src="https://img.shields.io/badge/protocol-gRPC-green" alt="gRPC"></a>
  <a href="#"><img src="https://img.shields.io/badge/layers-10-purple" alt="Layers:10"></a>
  <a href="#"><img src="https://img.shields.io/badge/adapters-6-orange" alt="Adapters:6"></a>
</p>

## 什么是 eon-core？

三生万物架构的**协调内核**。双重身份：

1. **作为项目**: 与 6 个同级项目并列的代码仓库
2. **作为架构角色**: 三角核心协调器 + 万物基础设施宿主

**两层结构**:
- **内核 (三角核心)**: OriginKernel · EventBus · DAG 路由 · 生命周期状态机
- **基础设施 (万物)**: 顶点适配器 · 8 卦子模块 · 五行监控 · 六道业力 · 自进化

## 十层架构

| 层 | 模块 | 组件 |
|:--:|------|------|
| 1 | OriginKernel | 启动引导、依赖注入、事件溯源 |
| 2 | EventBus | 异步发布/订阅，所有组件间通信 |
| 3 | 阴阳两极 | YangPole (扩张/搜索) + YinPole (收敛/验证) |
| 4 | 四面体网格 | DAG 拓扑、谱间隙、混沌扰动 |
| 5 | 顶点 (6个) | V0-V5 适配器，代理全部 6 个同级项目 |
| 6 | 八卦 (8个) | 元搜索、中文网关、图谱遍历、辩论、声学、种群、耳石、资源 |
| 7 | 五行 | 木火土金水监控 (15s 周期) |
| 8 | 六道 | KarmaEngine + KarmaCourt + 转生 (60s 周期) |
| 9 | Sphere 网关 | REST/gRPC/WebSocket/MCP 统一 API |
| 10 | 探针 + 进化 | 外部服务探针 + 自进化 (ChaosEngine + ParEGO) |

## 8 条运行时不变式

| ID | 不变式 | 执行点 |
|----|--------|--------|
| INV-001 | 拓扑必须是 DAG | bootstrap + reconfigure |
| INV-002 | YangPole.verify() 必须抛出 RuntimeError | mypy strict + runtime |
| INV-003 | YinPole.expand() 必须抛出 RuntimeError | mypy strict + runtime |
| INV-004 | 禁止顶点间直接 import | import linter + code review |
| INV-005 | 谱间隙 λ₂ ≥ 0.1 × baseline | reconfigure + health_pulse |
| INV-006 | DEVA 数量 ≤ 25% | KarmaCourt.audit_fairness() |
| INV-007 | NARAKA 自动转生 | SamsaraRing.run_karma_cycle() |
| INV-008 | 转生原子性 (7 步协议 + 快照) | ReincarnationProtocol.execute() |

## 快速开始

```bash
# 健康检查
python eon-core/src/main.py --config eon-core/config/taiji.yaml health

# 路由测试
python eon-core/src/main.py --config eon-core/config/taiji.yaml route "长江江豚种群恢复"

# 通过 project_loader
python -c "from scripts.project_loader import get_eon; a=get_eon(); print(a.info())"

# 通过 coordinator
python -c "from scripts.coordinator import coordinator; print(coordinator.health('eon'))"
```

## 目录结构

```
eon-core/
├── config/                        # taiji.yaml, COMPATIBILITY_MATRIX.yaml 等
├── proto/                         # gRPC protobuf 定义
├── src/
│   ├── adapter.py                 # IProjectAdapter → EonCoreAdapter
│   ├── kernel/                    # OriginKernel, EventBus, Lifecycle
│   ├── poles/                     # YangPole + YinPole
│   ├── vertices/                  # 6 个顶点适配器 (v0_fish .. v5_conflict)
│   ├── trigrams/                  # 8 个功能子模块
│   ├── mesh/                      # TetrahedronMesh
│   ├── wuxing/                    # 五行监控
│   ├── samsara/                   # 六道业力
│   ├── sphere/                    # API 网关
│   ├── tendrils/                  # 外部探针
│   └── evolution/                 # 自进化引擎
├── tests/
├── scripts/
└── README.md
```

## 关联项目

| 项目 | 角色 | 关系 |
|------|------|------|
| [fish-ecology-assistant](../fish-ecology-assistant/) | 知识供给 V0 | 顶点 V0 — 物种知识供给 |
| [cognitive-search-engine](../cognitive-search-engine/) | 搜索验证 V1 | 顶点 V1 — 文献搜索与验证 |
| [porpoise-agent](../porpoise-agent/) | P₁ 江豚 | 顶点 V2 — 江豚领域专研 |
| [coilia-agent](../coilia-agent/) | P₂ 刀鲚 | 顶点 V3 — 刀鲚领域专研 |
| [culter-agent](../culter-agent/) | P₃ 鲌类 | 顶点 V4 — 鲌类领域专研 |
| [conflict-arbiter](../conflict-arbiter/) | C 冲突仲裁 | 顶点 V5 — 冲突仲裁 |
