"""eon-core — 协调中枢。"""
from .adapter import EonCoreAdapter, get_adapter
from .group_meeting import GroupMeeting, get_group_meeting
from .review_synthesizer import ReviewSynthesizer, Paper, ReviewResult
from .emergence_engine import EmergenceEngine
from .emergence_monitor import EmergenceMonitor
from .sphere_gateway import app

__version__ = "v7.3.0"

__all__ = [
    "EonCoreAdapter", "get_adapter",
    "GroupMeeting", "get_group_meeting",
    "ReviewSynthesizer", "Paper", "ReviewResult",
    "EmergenceEngine", "EmergenceMonitor",
    "app",
]
