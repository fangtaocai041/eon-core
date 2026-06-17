# Changelog — eon-core

> 版本变更记录。参见 ROADMAP.md 了解技术改进路线图。

## v8.2.0 — 2026-06-27

### 🔀 CrossProjectPipeline + E2E 测试

- 🔀 **CrossProjectPipeline**: `src/kernel/cross_project.py` — 9 路由模板 (STANDARD/FAST/DOMAIN_P1-3/ARBITRATE/FULL/CUSTOM/DYNAMIC)
- 🧬 **Pipeline 模块**: `src/kernel/pipeline.py` — DAG 拓扑加载 + 阶段执行器
- 🩺 **WuXing 监控**: `src/kernel/wuxing_monitor.py` — 五元素健康监控 (生成/克制循环)
- 🧪 **E2E 管道测试**: `tests/test_e2e_pipeline.py` — 7/7 全部通过 (导入链/独立验证/跨项目加载/标准管道/阶段完成)
- 🧪 **跨项目集成测试**: `tests/test_cross_project_integration.py` — 10 测试 (适配器加载/管道启动/路由/协议合规)
- 📋 测试总数 15→35+

---

## v8.1.0 — 2026-06-11
- 🪶 精简僵尸代码 — 重建轻量协调内核
- WuXing→Monitoring 去神秘化
- 删除 wuxing_flow.yaml

## v8.0.0 — 2026-06-10
- 🔄 架构修正 — 道→S+T→万物
- project_loader sys.path 重定向

## v7.0.0 — 2026-06-07
- 🏛️ 十层同心架构初始发布
