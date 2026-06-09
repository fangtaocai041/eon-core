# eon-core

> **☯️ Eon-Taiji v7.2 — 十层同心动态活体内核**
>
> Tao → YinYang → 4 Symbols → 8 Trigrams → Tetrahedron → WuXing → **Samsara** → Sphere → Tendrils

[![Version](https://img.shields.io/badge/version-v7.2.0-blue)](VERSION.yaml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![Protocol](https://img.shields.io/badge/protocol-gRPC-green)](proto/)
[![Layers](https://img.shields.io/badge/layers-10-purple)](docs/TAIJI_TETRAHEDRON_ARCHITECTURE.md)
[![Projects](https://img.shields.io/badge/workspace-5_projects-orange)](docs/PROJECT_RELATIONSHIPS.md)

## What is eon-core?

eon-core 有**双重身份**:

1. **作为项目**: 与其他4个项目平级的代码仓库 (`D:\Reasonix\eon-core\`)
2. **作为架构角色**: 「三」的协调内核 + 「万物」的基础设施载体

它是唯一承载了**两层架构**的项目:
- **三 (内核层)**: OriginKernel · EventBus · DAG路由 · 生命周期
- **万物 (设施层)**: 四象顶点 · 八卦子模块 · 五行流转 · 六道轮回 · 进化引擎

10层同心架构:

| Layer | Name | Role |
|:-----:|------|------|
| L0 | ☯️ OriginKernel | Event bus + DI container + DAG topology routing |
| L1 | ☀️🌙 YinYang Poles | Type-safe separation: Yang expands, Yin verifies |
| L2 | △ 4 Vertices | V0(Supply) · V1(Verify) · V2(Porpoise) · V3(Coilia) |
| L3 | ☰☱☲☳☴☵☶☷ 8 Trigrams | Functional sub-modules per vertex |
| L4 | △³ TetrahedronMesh | Spectral gap analysis for connectivity health |
| L5 | ⬟ WuXing Flow | 5-element generation/restriction monitoring |
| L6 | ☸️ **Samsara Ring** | 6-realm karma engine with automatic rebirth |
| L7 | ○ SphereGateway | Unified API facade (REST/gRPC/MCP/WebSocket) |
| L8 | 〰️ Tendrils | 12 external probes with retract/extend lifecycle |
| L9 | 🦋 Evolution | Pareto optimizer + Rössler chaos + auto-rollback |

## Key Innovation: Samsara (六道轮回)

Every agent embeds a **KarmaEngine** that tracks good/bad deeds. Every 60s, the **KarmaCourt** evaluates all agents and triggers **Reincarnation** — automatic promotion or demotion through 6 realms:

| Realm | State | Token × | Rule |
|-------|-------|:------:|------|
| ☸️ DEVA | OPTIMAL | ×1.5 | Bad deed penalty ×3; max 10 cycles |
| 🧘 HUMAN | NORMAL | ×1.0 | Only realm allowing `self_evolve()` |
| ⚔️ ASURA | COMPETITIVE | ×1.2 | Requires deconfliction pass |
| 🐂 ANIMAL | DEGRADED | ×0.5 | LLM disabled; cache + rules only |
| 👻 PRETA | STARVED | ×0.25 | Severely rate-limited |
| 🔥 NARAKA | BROKEN | ×0.0 | Isolated; auto-rebirth after cooldown |

## Architecture

```
                         ┌──────────────────────┐
                         │   ○ SphereGateway    │  L7: API
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   ☯️ OriginKernel     │  L0: Core
                         │   EventBus + Registry │
                         └──┬───────┬───────┬───┘
                    ┌───────┼───────┼───────┼───────┐
              ┌─────▼──┐ ┌──▼────┐ ┌▼─────┐ ┌─────▼──┐
              │ ☀️ V0  │ │ 🌙 V1 │ │🌤️ V2 │ │ 🌦️ V3 │  L2
              │ Supply │ │Verify │ │Porpoise│ │Coilia │
              └────────┘ └───────┘ └───────┘ └────────┘
                    │                       │
              ┌─────▼──────┐         ┌──────▼─────┐
              │ △³ Mesh    │         │ ⬟ WuXing   │  L4-L5
              └────────────┘         └────────────┘
                    │                       │
              ┌─────▼───────────────────────▼──┐
              │     ☸️ Samsara Ring + Court     │  L6
              └────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/fangtaocai041/eon-core.git
cd eon-core

# Health check
python src/main.py --config config/taiji.yaml health

# Route a query
python src/main.py --config config/taiji.yaml route "长江江豚种群恢复趋势"
# → V2 (porpoise-agent)

# Run as service (Ctrl+C to stop)
python src/main.py --config config/taiji.yaml bootstrap
```

## Workspace — 5 Projects (S-T-V-P₁-P₂)

> eon-core is the unified kernel that replaced the deprecated **meso-cosmos-agent** (deleted v7.1).
> The 4 vertices map to the S-T-V-P₁-P₂ architecture:
> **S/V0** = fish · **V/V1** = cognitive · **P₁/V2** = porpoise · **P₂/V3** = coilia

| Vertex | S-T-V Role | Project | Role | Adapter |
|:------:|:----------:|---------|------|---------|
| V0 | **S** (State) | [fish-ecology-assistant](https://github.com/fangtaocai041/fish-ecology-assistant) | Knowledge supply | `FishEcologyAdapter` |
| V1 | **V** (Validation) | [cognitive-search-engine](https://github.com/fangtaocai041/cognitive-search-engine) | Verification engine | `CognitiveSearchAdapter` |
| V2 | **P₁** (Porpoise) | [porpoise-agent](https://github.com/fangtaocai041/porpoise-agent) | Porpoise domain | `PorpoiseAdapter` |
| V3 | **P₂** (Coilia) | [coilia-agent](https://github.com/fangtaocai041/coilia-agent) | Coilia domain | `CoiliaAdapter` |

All coordinated via `scripts/project_loader.py` — unified DirectLoader.

## Module Inventory

| Layer | Directory | Files | Purpose |
|:-----:|-----------|:-----:|---------|
| L0 | `src/kernel/` | 4 | OriginKernel + EventBus + Lifecycle + main |
| L1 | `src/poles/` | 3 | YangPole / YinPole / Protocol |
| L2 | `src/vertices/` | 5 | 4 vertex services + base class |
| L3 | `src/trigrams/` | 9 | 8 functional sub-modules |
| L4 | `src/mesh/` | 2 | Tetrahedron topology + spectral analysis |
| L5 | `src/wuxing/` | 7 | 5-element flow engine + 5 agents + override |
| L6 | `src/samsara/` | 8 | Karma + Ring + Court + Reincarnation + Nirvana + Fairness |
| L7 | `src/sphere/` | 1 | API Gateway with 6-layer middleware |
| L8 | `src/tendrils/` | 3 | 12 external probes + lifecycle manager |
| L9 | `src/evolution/` + `src/observability/` | 4 | Pareto + chaos + Rössler + telemetry |

**44 Python modules, 6 proto, 6 config YAMLs, ~7,000 LOC**

## 8 Architecture Invariants

1. Topology IS DAG → `nx.is_directed_acyclic_graph()` at bootstrap
2. YangPole SHALL NOT verify → mypy strict + runtime `@_guard_yang`
3. YinPole SHALL NOT expand → mypy strict + runtime `@_guard_yin`
4. Inter-vertex via EventBus or gRPC → no direct import
5. λ₂ ≥ 0.1 × baseline → spectral gap connectivity check
6. DEVA ≤ 10 cycles → fairness auto-rotation
7. NARAKA auto-rebirth → self-healing after cooldown
8. Reincarnation atomic → 7-step protocol with snapshot rollback

## Related

- [Architecture Docs](docs/TAIJI_TETRAHEDRON_ARCHITECTURE.md)
- [Project Relationships](docs/PROJECT_RELATIONSHIPS.md)
- [VERSION.yaml](VERSION.yaml)

## License

MIT
