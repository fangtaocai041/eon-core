"""
cross_adapters.py — 跨项目能力集成适配器

每个适配器是一个薄包装层，将其他项目的核心能力按照本项目的
接口规范进行适配。遵循"最小导入，最大兼容"原则。

所有适配器使用 try/except ImportError 实现优雅降级：
- 如果目标项目可用 → 使用真实实现
- 如果目标项目不可用 → 使用嵌入式 fallback 或返回 None

Usage:
    from eon_core.cross_adapters import (
        kb_first_lookup,      # fish-ecology → anywhere: KB-First 查询
        bdi_deliberate,       # porpoise → fish: BDI 决策
        reflexion_analyze,    # porpoise → anywhere: 自我反思
        thompson_select,      # cognitive → anywhere: Thompson 引擎选择
        pid_wait,             # cognitive → anywhere: PID 限速
        check_emergence,      # infrastructure → anywhere: 涌现检测
        generate_variants,    # cognitive → anywhere: OCR 变体
    )
"""

import sys, os, logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# fish-ecology-assistant → anywhere: KB-First 查询
# ═══════════════════════════════════════════════════════

def kb_first_lookup(species_name: str, language: str = "auto") -> Optional[dict]:
    """查询 fish-ecology-assistant 知识库。

    在调用外部搜索之前，先检查本地受信知识库。
    这是对抗 LLM 幻觉的第一道防线。

    Returns:
        dict with keys: found, species, conservation, family, source
        None if fish-ecology-assistant unavailable
    """
    try:
        FISH_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'fish-ecology-assistant')
        sys.path.insert(0, FISH_ROOT)
        from fishkb.search import kb_first_lookup as _lookup
        return _lookup(species_name, language)
    except ImportError:
        logger.debug("fish-ecology-assistant not available for KB-First lookup")
        return None


# ═══════════════════════════════════════════════════════
# porpoise-agent → fish: BDI 决策
# ═══════════════════════════════════════════════════════

def bdi_deliberate(belief: dict, desire: dict) -> Optional[dict]:
    """使用 porpoise-agent 的 BDI 状态机进行决策。

    将信念和愿望映射为意图。这是从无状态的"直接执行"
    到有状态的"信念驱动决策"的升级路径。

    Args:
        belief: 当前信念状态 (从 KB + 观察构建)
        desire: 目标状态 (从用户查询 + 系统目标构建)

    Returns:
        dict with keys: intention, confidence, reasoning
        None if porpoise-agent unavailable
    """
    try:
        PORPOISE_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'porpoise-agent')
        sys.path.insert(0, os.path.join(PORPOISE_ROOT, 'src'))
        from cognitive.bdi import BDICoordinator, Belief, Desire

        coordinator = BDICoordinator()
        b = Belief(**{k: v for k, v in belief.items() if k in Belief.__dataclass_fields__})
        d = Desire(goal=desire.get('goal', ''), priority=desire.get('priority', 1))
        intention = coordinator.deliberate(b, d)
        return {
            'intention': intention.action if hasattr(intention, 'action') else str(intention),
            'confidence': getattr(intention, 'confidence', 0.5),
            'reasoning': getattr(intention, 'reasoning', ''),
        }
    except (ImportError, TypeError) as e:
        logger.debug(f"porpoise-agent BDI not available: {e}")
        return None


# ═══════════════════════════════════════════════════════
# porpoise-agent → anywhere: 自我反思
# ═══════════════════════════════════════════════════════

def reflexion_analyze(error_context: dict) -> Optional[dict]:
    """使用 porpoise-agent 的 Reflexion 进行错误根因分析。

    将"知道出错了"升级为"知道哪里出错了和为什么"。

    Returns:
        dict with keys: diagnosis, suggestion, severity, credit_node
    """
    try:
        PORPOISE_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'porpoise-agent')
        sys.path.insert(0, os.path.join(PORPOISE_ROOT, 'src'))
        from cognitive.reflexion import Critic, Reflection, ReflectionType, Severity

        critic = Critic()
        reflection = critic.analyze(
            error_type=error_context.get('type', 'unknown'),
            observation=error_context.get('observation', ''),
            context=error_context.get('context', {}),
        )
        return {
            'diagnosis': reflection.diagnosis,
            'suggestion': reflection.suggestion,
            'severity': reflection.severity.value if hasattr(reflection.severity, 'value') else str(reflection.severity),
            'credit_node': reflection.source_node,
        }
    except ImportError as e:
        logger.debug(f"porpoise-agent Reflexion not available: {e}")
        return None


# ═══════════════════════════════════════════════════════
# cognitive-search-engine → anywhere: Thompson 引擎选择
# ═══════════════════════════════════════════════════════

def thompson_select(arms: list[str], n: int = 3, context: dict = None) -> list[str]:
    """Thompson Sampling 多臂老虎机选择最优后端。

    替代硬编码优先级的智能后端选择器。
    """
    try:
        from thompson import ThompsonBandit
        bandit = ThompsonBandit(state_file=None)
        # Register arms with optional weights from context
        for arm in arms:
            weight = context.get('weights', {}).get(arm, 1.0) if context else 1.0
            bandit.update(arm, success=True)  # Initialize with neutral prior
        return bandit.select_arms(n)
    except ImportError:
        return arms[:n]  # fallback: return first n


# ═══════════════════════════════════════════════════════
# cognitive-search-engine → anywhere: PID 自适应限速 (带缓存)
# ═══════════════════════════════════════════════════════

_PID_LIMITER_CACHE: dict = {}

def pid_wait(resource_key: str, success: bool) -> float:
    """PID 自适应速率控制 (实例缓存, 跨调用保持状态)."""
    try:
        from pid_limiter import PIDRateLimiter
        if resource_key not in _PID_LIMITER_CACHE:
            _PID_LIMITER_CACHE[resource_key] = PIDRateLimiter()
        return _PID_LIMITER_CACHE[resource_key].wait(resource_key, success)
    except ImportError:
        return 1.0 if not success else 0.0


# ═══════════════════════════════════════════════════════
# infrastructure → anywhere: 涌现检测
# ═══════════════════════════════════════════════════════

def check_emergence(metric_name: str, value: float, level: int = 1) -> Optional[dict]:
    """统一涌现检测 — 检查当前观测是否构成涌现信号。"""
    try:
        EON_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
        sys.path.insert(0, EON_SRC)
        from unified_emergence import EmergenceMonitor, DimensionalLevel

        monitor = EmergenceMonitor(emergence_threshold_sigma=3.0, min_sources=3)
        level_map = {0: DimensionalLevel.D0, 1: DimensionalLevel.D1, 2: DimensionalLevel.D2, 3: DimensionalLevel.D3}
        monitor.record(metric_name, value, level_map.get(level, DimensionalLevel.D1))
        signals = monitor.check_emergence()
        if signals:
            return {
                'emergence': True,
                'signals': [{'type': s.emergence_type.value, 'sigma': s.deviation_sigma, 'description': s.description} for s in signals]
            }
        return {'emergence': False}
    except ImportError as e:
        logger.debug(f"Emergence monitor not available: {e}")
        return None


# ═══════════════════════════════════════════════════════
# cognitive-search-engine → anywhere: OCR 变体生成
# ═══════════════════════════════════════════════════════

def generate_name_variants(name: str, max_variants: int = 20) -> list[str]:
    """生成学名的 OCR/拼写变体安全网。"""
    try:
        from variant_generator import generate_variants
        return generate_variants(name, max_variants)
    except ImportError:
        return [name]  # fallback: return original only
