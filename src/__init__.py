"""
TaijiTetrahedron-Samsara v7.4 — 十层同心动态活体架构.

Layers:
  L0: 太极起源点 (OriginKernel + EventBus)
  L1: 两仪双极 (YangPole / YinPole)
  L2: 四象顶点 (4 gRPC Vertex services)
  L3: 八卦子模块 (8 Trigrams)
  L4: 三角体网格 (TetrahedronMesh spectral analysis)
  L5: 监控与评估 (Monitoring & Karma)
  L6: 六道轮回环 (Samsara karma/reincarnation)
  L7: 圆球体网关 (SphereGateway API facade)
  L8: 触须探针 (12 external probes)
  L9: 进化引擎 + 可观测性 (Evolution + Observability)

Shared Modules:
  unified_emergence  — 统一涌现检测引擎 (融合 p/f/c 三项目)
  rcca_core          — 便携 RCCA 核心 5 模块 (RecursiveThinker / SelfModel / Emotion / Transposition / ReflectionLoop)
  review_synthesizer — 综述合成引擎 (论文列表 → 结构化综述 Markdown)

from eon_core.shared import ThompsonBandit, PIDRateLimiter, generate_variants, EvolutionExecutor
"""

import sys as _sys
from pathlib import Path as _Path

# ── Ensure self-imports resolve correctly when imported cross-project ──
_PROJECT_ROOT = str(_Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

def _load_version():
    """Read version from VERSION.yaml — single source of truth."""
    try:
        import yaml
        _vpath = _Path(__file__).resolve().parent.parent.parent / "VERSION.yaml"
        with open(_vpath, encoding="utf-8") as _f:
            _data = yaml.safe_load(_f)
        _key = _Path(__file__).resolve().parent.parent.name
        return _data.get("projects", {}).get(_key, {}).get("version", "0.0.0")
    except Exception:
        return "0.0.0"

__version__ = _load_version()
__code__ = "TaijiTetrahedron-Samsara-v7.4"
__project__ = "eon-core"
