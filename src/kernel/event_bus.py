"""AsyncEventBus — topic-based pub/sub with dead-letter queue + ring-buffer event log.

Design:
  - Per-topic asyncio.Queue for decoupled consumers
  - Subscriber registry: topic → List[Callable]
  - Dead-letter queue (DLQ) for undeliverable events
  - Capacity-bounded with backpressure
  - Ring-buffer event log (last N events) for debugging/replay
  - Standard topic helpers: search.complete, verify.complete, pipeline.stage.done

Usage:
  bus = AsyncEventBus(capacity=10000, dlq_capacity=1000, log_size=100)
  await bus.subscribe("vertex.V0", handler)
  event_id = await bus.publish(event, "vertex.V0")
  event = await bus.consume("vertex.V0", timeout=30.0)
  recent = bus.event_log()  # Last 100 events
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Standard topic constants
TOPIC_SEARCH_COMPLETE = "search.complete"
TOPIC_VERIFY_COMPLETE = "verify.complete"
TOPIC_PIPELINE_STAGE_DONE = "pipeline.stage.done"
TOPIC_PIPELINE_STAGE_FAILED = "pipeline.stage.failed"
TOPIC_CROSS_PROJECT_DONE = "cross_project.done"
TOPIC_HEALTH_PULSE = "health.pulse"


@dataclass(slots=True)
class SystemEvent:
    """Canonical event type flowing through the EventBus."""

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    karma_context: Optional[Dict[str, Any]] = None

    def clone(self, *, topic: Optional[str] = None, source: Optional[str] = None) -> "SystemEvent":
        """Create a copy with optional overrides (new event_id)."""
        import copy
        new = copy.deepcopy(self)
        new.event_id = uuid.uuid4().hex
        if topic is not None:
            new.topic = topic
        if source is not None:
            new.source = source
        return new


@dataclass
class Subscription:
    """Handle returned on subscribe — used for unsubscribe."""
    topic: str
    handler_id: str
    _bus: "AsyncEventBus" = field(repr=False)

    async def unsubscribe(self) -> None:
        await self._bus.unsubscribe(self.topic, self.handler_id)


class AsyncEventBus:
    """Async pub/sub event bus with per-topic queues, DLQ, and ring-buffer event log."""

    def __init__(
        self,
        capacity: int = 10000,
        dlq_capacity: int = 1000,
        log_size: int = 100,
    ) -> None:
        self._queues: Dict[str, asyncio.Queue[SystemEvent]] = {}
        self._subscribers: Dict[str, Dict[str, Callable]] = {}
        self._dlq: asyncio.Queue[SystemEvent] = asyncio.Queue(maxsize=dlq_capacity)
        self._capacity = capacity
        self._published_count: int = 0
        self._dlq_count: int = 0
        # Ring buffer for event log (thread-safe)
        self._event_log: deque[SystemEvent] = deque(maxlen=log_size)
        self._log_lock = threading.Lock()

    async def publish(self, event: SystemEvent, topic: str) -> str:
        """Push event to topic queue. Returns event_id.

        IF topic queue doesn't exist THEN create it.
        IF queue is full THEN push to DLQ.
        Always appends to ring-buffer event log.
        """
        event.topic = topic
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=self._capacity)

        queue = self._queues[topic]
        try:
            await asyncio.wait_for(queue.put(event), timeout=5.0)
            self._published_count += 1
        except (asyncio.QueueFull, asyncio.TimeoutError):
            logger.warning(f"EventBus queue full for topic={topic}, routing to DLQ")
            await self._dlq.put(event)
            self._dlq_count += 1

        # Append to ring-buffer event log (thread-safe)
        with self._log_lock:
            self._event_log.append(event)

        return event.event_id

    async def subscribe(self, topic: str, handler: Callable) -> Subscription:
        """Register a handler for a topic. Returns Subscription handle."""
        if topic not in self._subscribers:
            self._subscribers[topic] = {}
        handler_id = f"handler_{uuid.uuid4().hex[:8]}"
        self._subscribers[topic][handler_id] = handler
        logger.debug(f"Subscribed handler={handler_id} to topic={topic}")
        return Subscription(topic=topic, handler_id=handler_id, _bus=self)

    async def unsubscribe(self, topic: str, handler_id: str) -> None:
        """Remove a handler from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic].pop(handler_id, None)
            logger.debug(f"Unsubscribed handler={handler_id} from topic={topic}")

    async def consume(self, topic: str, timeout: float = 30.0) -> SystemEvent:
        """Await next event on topic. Raises TimeoutError if no event within timeout."""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=self._capacity)

        queue = self._queues[topic]
        try:
            event = await asyncio.wait_for(queue.get(), timeout=timeout)
            # Notify subscribers
            subs = self._subscribers.get(topic, {})
            for handler in subs.values():
                try:
                    await handler(event)
                except Exception:
                    logger.exception(f"Subscriber handler failed for topic={topic}")
            return event
        except asyncio.TimeoutError:
            raise TimeoutError(f"No event on topic={topic} within {timeout}s")

    async def drain(self, timeout: float = 30.0) -> None:
        """Drain all queues during shutdown."""
        for topic, queue in self._queues.items():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        logger.info("EventBus drained")

    @property
    def stats(self) -> dict:
        return {
            "published_count": self._published_count,
            "dlq_count": self._dlq_count,
            "topic_count": len(self._queues),
            "subscriber_count": sum(len(s) for s in self._subscribers.values()),
            "event_log_size": len(self._event_log),
        }

    # ── Event log (ring buffer) ──

    def event_log(self, limit: Optional[int] = None) -> List[SystemEvent]:
        """Return recent events from the ring buffer (most recent last).

        Args:
            limit: Optional cap on returned events (most recent N).
        """
        with self._log_lock:
            events = list(self._event_log)
        if limit is not None:
            events = events[-limit:]
        return events

    def event_log_by_topic(self, topic: str, limit: Optional[int] = None) -> List[SystemEvent]:
        """Return recent events filtered by topic."""
        with self._log_lock:
            events = [e for e in self._event_log if e.topic == topic]
        if limit is not None:
            events = events[-limit:]
        return events

    def event_log_summary(self) -> List[Dict[str, Any]]:
        """Return lightweight summary of recent events (no payload)."""
        with self._log_lock:
            return [
                {
                    "event_id": e.event_id,
                    "trace_id": e.trace_id,
                    "timestamp": e.timestamp.isoformat(),
                    "source": e.source,
                    "topic": e.topic,
                }
                for e in self._event_log
            ]

    # ── Synchronous publish (for non-async contexts) ──

    def publish_sync(self, event: SystemEvent, topic: str) -> str:
        """Synchronous publish — schedules on the running loop or creates one.

        Use this from non-async contexts (e.g., health checks, sync callbacks).
        """
        event.topic = topic
        try:
            loop = asyncio.get_running_loop()
            _owns_loop = False
        except RuntimeError:
            loop = asyncio.new_event_loop()
            _owns_loop = True

        try:
            if loop.is_running():
                # Schedule on running loop
                future = asyncio.run_coroutine_threadsafe(
                    self.publish(event, topic), loop
                )
                return future.result(timeout=10)
            else:
                return loop.run_until_complete(self.publish(event, topic))
        finally:
            if _owns_loop:
                loop.close()
