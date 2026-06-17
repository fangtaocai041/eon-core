"""eon-core shared modules — reusable primitives for all 7 Reasonix projects.

Exports:
    ThompsonBandit      — Thompson Sampling multi-armed bandit
    PIDRateLimiter      — PID-controlled adaptive rate limiter
    generate_variants   — OCR / scientific-name variant generator
    EvolutionExecutor   — Trigger-based self-evolution engine
"""

from .thompson import ThompsonBandit
from .pid_limiter import PIDRateLimiter
from .variant_generator import generate_variants
from .evolution import EvolutionExecutor

__all__ = [
    "ThompsonBandit",
    "PIDRateLimiter",
    "generate_variants",
    "EvolutionExecutor",
]
