"""EventStore — Event Sourcing + CQRS for eon-core EventBus.

Append-only event store with SQLite persistence and replay capability.
CQRS: separate write (EventStore) from read (Projection) models.

Usage:
    store = EventStore()
    store.append("task_started", {"query": "Coilia nasus"})
    events = store.get_events("task_started")
    state = store.project(lambda e: e['type'] == 'task_completed')
"""

import json, os, sqlite3, time
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
    """Append-only event store with SQLite persistence."""

    def __init__(self, db_path: str = None):
        self._events: List[StoredEvent] = []
        self._next_id = 1
        self._db_path = db_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'event_store.db')
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._projections: Dict[str, Any] = {}
        self._init_db()
        self.load_from_disk()

    def _init_db(self):
        """Create SQLite schema if not exists."""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON events(timestamp)")
            conn.commit()
            conn.close()
        except Exception:
            pass  # SQLite unavailable — operate in memory-only mode

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

    def query(self, event_type: str = None, since_ts: float = 0,
              limit: int = 100) -> List[StoredEvent]:
        """SQL-powered query — much faster than Python filter for large event logs."""
        try:
            conn = sqlite3.connect(self._db_path)
            sql = "SELECT id, type, data, timestamp FROM events WHERE 1=1"
            params = []
            if event_type:
                sql += " AND type = ?"
                params.append(event_type)
            if since_ts > 0:
                sql += " AND timestamp > ?"
                params.append(since_ts)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            conn.close()
            return [StoredEvent(event_id=r[0], event_type=r[1],
                                data=json.loads(r[2]), timestamp=r[3])
                    for r in rows]
        except Exception:
            return []

    @property
    def count(self) -> int:
        return len(self._events)

    # ── Internal ──

    def _notify(self, event_type: str, event: StoredEvent):
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass  # 单个订阅者失败不影响其他订阅者

    def _persist(self, event: StoredEvent):
        """Write event to SQLite."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT INTO events (id, type, data, timestamp) VALUES (?, ?, ?, ?)",
                (event.event_id, event.event_type,
                 json.dumps(event.data, ensure_ascii=False), event.timestamp)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # 持久化失败不影响运行时（事件保留在内存）

    def load_from_disk(self):
        """Load events from SQLite on startup."""
        try:
            conn = sqlite3.connect(self._db_path)
            rows = conn.execute(
                "SELECT id, type, data, timestamp FROM events ORDER BY id"
            ).fetchall()
            conn.close()
            for r in rows:
                self._events.append(StoredEvent(
                    event_id=r[0], event_type=r[1],
                    data=json.loads(r[2]), timestamp=r[3]))
                self._next_id = max(self._next_id, r[0] + 1)
        except Exception:
            pass  # 数据库不存在或损坏时使用空事件列表
