"""AsyncEventBus — topic-based pub/sub with dead-letter queue.

Design:
  - Per-topic asyncio.Queue for decoupled consumers
  - Subscriber registry: topic → List[Callable]
  - Dead-letter queue (DLQ) for undeliverable events
  - Capacity-bounded with backpressure

Usage:
  bus = AsyncEventBus(capacity=10000, dlq_capacity=1000)
  await bus.subscribe("vertex.V0", handler)
  event_id = await bus.publish(event, "vertex.V0")
  event = await bus.consume("vertex.V0", timeout=30.0)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    """Async pub/sub event bus with per-topic queues and DLQ."""

    def __init__(self, capacity: int = 10000, dlq_capacity: int = 1000) -> None:
        self._queues: Dict[str, asyncio.Queue[SystemEvent]] = {}
        self._subscribers: Dict[str, Dict[str, Callable]] = {}
        self._dlq: asyncio.Queue[SystemEvent] = asyncio.Queue(maxsize=dlq_capacity)
        self._capacity = capacity
        self._published_count: int = 0
        self._dlq_count: int = 0

    async def publish(self, event: SystemEvent, topic: str) -> str:
        """Push event to topic queue. Returns event_id.

        IF topic queue doesn't exist THEN create it.
        IF queue is full THEN push to DLQ.
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
        }
