"""SSEStreamEmitter — Server-Sent Events streaming for agent output.

Adds real-time streaming to porpoise-agent's ReAct loop.
Each Think→Act→Observe→Reflect phase emits SSE events to the client.

Usage:
    emitter = SSEStreamEmitter()
    async for event in emitter.stream_reasoning(react_loop.run(question)):
        print(event)  # or send to Web client via FastAPI StreamingResponse
"""

import asyncio, json, time
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any


@dataclass
class SSEEvent:
    event_type: str  # "think", "act", "observe", "reflect", "done", "error"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        return f"event: {self.event_type}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


class SSEStreamEmitter:
    """Emits agent reasoning as Server-Sent Events."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def emit(self, event_type: str, data: Dict[str, Any] = None):
        """Emit a single SSE event."""
        event = SSEEvent(event_type=event_type, data=data or {})
        await self._queue.put(event)

    async def emit_think(self, reasoning: str, engine: str = ""):
        await self.emit("think", {"reasoning": reasoning, "engine": engine})

    async def emit_act(self, action: str, progress: float = 0.0):
        await self.emit("act", {"action": action, "progress": progress})

    async def emit_observe(self, findings: list, count: int = 0):
        await self.emit("observe", {"findings": findings[:5], "total": count or len(findings)})

    async def emit_reflect(self, satisfied: bool, gaps: list = None):
        await self.emit("reflect", {"satisfied": satisfied, "gaps": gaps or []})

    async def emit_done(self, summary: str = ""):
        await self.emit("done", {"summary": summary})

    async def emit_error(self, message: str):
        await self.emit("error", {"message": message})

    async def stream(self) -> AsyncIterator[str]:
        """Async generator yielding SSE-formatted strings."""
        while True:
            event = await self._queue.get()
            yield event.to_sse()
            if event.event_type in ("done", "error"):
                break

    def close(self):
        self._queue.put_nowait(SSEEvent("done", {"closed": True}))


# FastAPI integration:
# @app.get("/agent/stream")
# async def agent_stream(question: str):
#     emitter = SSEStreamEmitter()
#     async def run():
#         await emitter.emit_think(f"Analyzing: {question}")
#         # ... run ReAct loop, calling emitter at each phase ...
#         await emitter.emit_done("Analysis complete")
#     asyncio.create_task(run())
#     return StreamingResponse(emitter.stream(), media_type="text/event-stream")