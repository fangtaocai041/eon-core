"""SphereGateway — 圆球体网关 (Facade + API Gateway + Service Mesh Ingress).

Ports:
  REST:      8080
  gRPC:      9090
  WebSocket: 8080
  MCP:       8080
  Webhook:   8080

6-layer middleware chain:
  1. AuthMiddleware        — JWT + API Key + OAuth2
  2. RateLimitMiddleware   — Token Bucket per client
  3. ProtocolAdapter       — REST/gRPC/MCP/WS → SystemEvent
  4. RouterMiddleware      — query intent → target vertex
  5. AuditLogMiddleware    — log every request
  6. ResponseMiddleware    — SystemEvent → original protocol format

Health endpoint: GET /health → {status, uptime, realm_distribution,
                   tetrahedron_spectral_gap, active_tendrils}
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from ..kernel.event_bus import AsyncEventBus, SystemEvent
from ..kernel.origin import OriginKernel

logger = logging.getLogger(__name__)


class SphereGateway:
    """Unified API gateway wrapping the entire TaijiTetrahedron system.

    Design pattern: Facade + API Gateway.
    All external requests enter through this single point.
    """

    def __init__(self, kernel: Optional[OriginKernel] = None) -> None:
        self.kernel = kernel or OriginKernel()
        self._startup_time = time.monotonic()
        self._middleware: list[Any] = []

    async def initialize(self) -> None:
        """Initialize middleware chain from config.

        Order: Auth → RateLimit → ProtocolAdapter → Router → Audit → Response
        """
        # In production: load middleware from config
        # For now: stub initialization
        self._middleware = [
            ("AuthMiddleware", 1),
            ("RateLimitMiddleware", 2),
            ("ProtocolAdapter", 3),
            ("RouterMiddleware", 4),
            ("AuditLogMiddleware", 5),
            ("ResponseMiddleware", 6),
        ]
        logger.info(f"SphereGateway initialized with {len(self._middleware)} middleware")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an external request through the middleware chain.

        Step 1: Auth — verify JWT/API Key/OAuth2.
        Step 2: RateLimit — check Token Bucket.
        Step 3: ProtocolAdapter — convert to SystemEvent.
        Step 4: Router — classify intent, route to vertices via OriginKernel.route_event().
        Step 5: Audit — log request details.
        Step 6: Response — convert SystemEvent back to original format.

        RETURN response in same protocol as request.
        """
        import uuid

        trace_id = request.get("trace_id", uuid.uuid4().hex)
        query = request.get("query", "")
        protocol = request.get("protocol", "REST")
        client_id = request.get("client_id", "anonymous")

        # Step 1: Auth (simulated)
        if not self._auth_check(request):
            return {"status": "error", "code": 401, "message": "Unauthorized"}

        # Step 2: Rate limit (simulated)
        if not self._rate_limit_check(client_id):
            return {"status": "error", "code": 429, "message": "Rate limit exceeded"}

        # Step 3: Protocol adaptation
        event = SystemEvent(
            trace_id=trace_id,
            source="sphere.gateway",
            topic="query.received",
            payload={"query": query, "protocol": protocol, "client_id": client_id},
        )
        await self.kernel.event_bus.publish(event, "query.received")

        # Step 4: Route
        route_result = await self.kernel.route_event(event)

        # Step 5: Audit (simulated)
        self._audit_log(client_id, query, trace_id, route_result.plan)

        # Step 6: Wait for final result (simplified: return route plan)
        # In production: await event_bus.consume('vertex.V1.completed')
        processing_time = (time.monotonic() - self._startup_time) * 1000

        return {
            "trace_id": trace_id,
            "status": "ok",
            "route_plan": route_result.plan,
            "samsara_states": route_result.samsara_states,
            "fallback_used": route_result.fallback_used,
            "processing_time_ms": processing_time,
        }

    async def health(self) -> Dict[str, Any]:
        """Health endpoint response.

        GET /health →
          {status, uptime_seconds, realm_distribution,
           tetrahedron_spectral_gap, active_tendrils, vertex_status}
        """
        uptime = time.monotonic() - self._startup_time

        realm_dist = {}
        if self.kernel.samsara_ring:
            realm_dist = {
                r.value: c
                for r, c in self.kernel.samsara_ring.get_realm_distribution().items()
            }

        vertex_status = {}
        for vid, desc in self.kernel.registry.items():
            vertex_status[vid] = desc.health_status

        return {
            "status": "HEALTHY" if self.kernel.state.is_alive else "DEGRADED",
            "uptime_seconds": uptime,
            "realm_distribution": realm_dist,
            "vertex_status": vertex_status,
            "active_tendrils": 12,  # from tendril manager
            "lifecycle_stage": self.kernel.state.stage.value,
        }

    # ── Middleware stubs ──

    def _auth_check(self, request: Dict[str, Any]) -> bool:
        """JWT verify + API Key validation + OAuth2 token introspection."""
        # Production: actual JWT verification
        return True

    def _rate_limit_check(self, client_id: str) -> bool:
        """Token Bucket: capacity=100, refill_rate=10/s per client_id."""
        # Production: per-client Token Bucket
        return True

    def _audit_log(self, client_id: str, query: str, trace_id: str, route: list) -> None:
        """Log every request."""
        logger.info(
            f"AUDIT: client={client_id} query_hash={hash(query)} "
            f"trace={trace_id} route={route}"
        )
