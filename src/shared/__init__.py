"""eon-core shared modules — reusable primitives for all 7 Reasonix projects.

Exports:
    ThompsonBandit          — Thompson Sampling multi-armed bandit
    PIDRateLimiter          — PID-controlled adaptive rate limiter
    generate_variants       — OCR / scientific-name variant generator
    generate_full_species_variants — Full binomial variant generator
    EvolutionExecutor       — Trigger-based self-evolution engine
    CircuitBreaker          — Failure isolation (熔断器)
    CircuitBreakerRegistry  — Global circuit breaker registry
    CircuitState            — Circuit breaker states
    CircuitBreakerOpenError — Raised when circuit is OPEN
    with_circuit_breaker    — Decorator for easy integration
    get_registry            — Get global CircuitBreakerRegistry singleton
    CheckpointManager       — Pipeline checkpoint/resume for crash resilience
    EvolutionFeedbackLoop   — Circuit breaker → evolution engine feedback loop
    EmergenceBridge         — Perception → emergence → evolution closed loop
"""

from .thompson import ThompsonBandit
from .pid_limiter import PIDRateLimiter
from .variant_generator import generate_variants, generate_full_species_variants
from .evolution import EvolutionExecutor
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitBreakerOpenError,
    CircuitState,
    get_registry,
    with_circuit_breaker,
)
from .checkpoint import CheckpointManager
from .evolution_feedback import EvolutionFeedbackLoop, AdaptationEvent
from .emergence_bridge import EmergenceBridge, EmergenceEvent

__all__ = [
    "ThompsonBandit",
    "PIDRateLimiter",
    "generate_variants",
    "generate_full_species_variants",
    "EvolutionExecutor",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitBreakerOpenError",
    "CircuitState",
    "get_registry",
    "with_circuit_breaker",
]
