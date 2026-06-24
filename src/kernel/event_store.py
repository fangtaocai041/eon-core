"""EventStore — Event Sourcing + CQRS for eon-core EventBus.

Replaces transient in-memory events with persistent event log.
All state changes = append-only events. Rebuild state by replaying events.
CQRS: separate write (EventStore) from read (Projection) models.

Usage:
    store = EventStore()
    store.append("task_started", {"query": "Coilia nasus"})
    events = store.get_events("task_started")
    state = store.project(lambda e: e['type'] == 'task_completed')
"""

import json, os, time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class StoredEvent:
    event_id: int
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    version: int = 1


class EventStore:
    """Append-only event store with replay capability."""

    def __init__(self, db_path: str = None):
        self._events: List[StoredEvent] = []
        self._next_id = 1
        self._db_path = db_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'event_store.jsonl')
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._projections: Dict[str, Any] = {}

    def append(self, event_type: str, data: Dict[str, Any]) -> StoredEvent:
        event = StoredEvent(event_id=self._next_id, event_type=event_type, data=data)
        self._events.append(event)
        self._next_id += 1
        self._persist(event)
        self._notify(event_type, event)
        return event

    def get_events(self, event_type: str = None, since_id: int = 0) -> List[StoredEvent]:
        events = self._events[since_id:]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def replay(self, handler: Callable[[StoredEvent], None], since_id: int = 0):
        for event in self._events[since_id:]:
            handler(event)

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)

    def project(self, filter_fn: Callable[[Dict], bool]) -> List[StoredEvent]:
        return [e for e in self._events if filter_fn({'type': e.event_type, **e.data})]

    def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Rebuild entity state by replaying all its events."""
        state = {}
        for event in self._events:
            if event.data.get('id') == entity_id:
                state.update(event.data)
        return state

    def _notify(self, event_type: str, event: StoredEvent):
        for handler in self._subscribers.get(event_type, []):
            try: handler(event)
            except Exception:
                pass  # 单个订阅者失败不影响其他订阅者

    def _persist(self, event: StoredEvent):
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            with open(self._db_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'id': event.event_id, 'type': event.event_type,
                    'data': event.data, 'ts': event.timestamp
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass  # 事件持久化失败不影响运行时（事件仍保留在内存）(self):
        try:
            if os.path.exists(self._db_path):
                with open(self._db_path, encoding='utf-8') as f:
                    for line in f:
                        d = json.loads(line.strip())
                        self._events.append(StoredEvent(
                            event_id=d['id'], event_type=d['type'],
                            data=d['data'], timestamp=d.get('ts', 0)))
                        self._next_id = max(self._next_id, d['id'] + 1)
        except Exception:
            pass  # 磁盘文件不存在或损坏时使用空事件列表
    def count(self) -> int:
        return len(self._events)
