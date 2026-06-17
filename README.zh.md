# eon-core ⚙️

**三角核心 Coordinator 层** — 事件总线 · 项目加载器 · 生命周期。

> 和则无穷力量，分则顶尖专家引擎。

---

## 实际功能

eon-core 是一个轻量级 (~1,500行) 协调层：

1. **Project Loader** (`scripts/project_loader.py`, 407行) — 通过 sys.path 隔离导入兄弟项目适配器，提供 6 项目统一访问入口
2. **AsyncEventBus** (`src/kernel/event_bus.py`, 146行) — 进程内异步发布/订阅 + 死信队列
3. **OriginKernel** (`src/kernel/origin.py`, 120行) — 单例协调器，启动所有项目适配器，提供统一 search/lookup/health API
4. **Lifecycle** (`src/kernel/lifecycle.py`, 100行) — 5 阶段状态机 (SEEDING→SPROUTING→BLOOMING→FRUITING→PRUNING)
5. **DAG 配置** (`config/taiji.yaml`) — 6 项目生态拓扑静态定义

## 尚未实现

README 此前描述的"十层同心架构" (L0-L9)，仅 L0 (OriginKernel + EventBus) 有运行时代码。L1-L9 仅存在 proto/ 原型定义和配置占位。未来版本可能逐步实现。

## 已知限制

- EventBus 仅进程内 (无 Redis/gRPC 外部代理)
- 无持久化事件存储或事件溯源
- 无运行时 DAG 路由 — 拓扑仅为配置
- Lifecycle 未与 OriginKernel 集成
- gRPC 定义存在但无服务端实现
