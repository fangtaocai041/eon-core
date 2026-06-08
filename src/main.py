"""eon-core — 太极·十层同心架构统一内核入口.

Usage:
    python -m eon_core bootstrap              # 启动内核 (DAG + EventBus + Samsara)
    python -m eon_core serve --port 8080      # API 服务模式
    python -m eon_core health                 # 健康检查
    python -m eon_core route "query text"     # 单次查询路由

Bootstrap sequence:
  1. load config/taiji.yaml
  2. create EventBus (async pub/sub)
  3. register 4 vertices (V0 fish / V1 cognitive / V2 porpoise / V3 coilia)
  4. build DAG topology from config.tetrahedron.edges
  5. verify DAG property (assert acyclic)
  6. start health_pulse (every 5s)
  7. BLOOMING → accept events
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure eon-core root is on sys.path for package imports
_eon_root = Path(__file__).resolve().parent.parent
if str(_eon_root) not in sys.path:
    sys.path.insert(0, str(_eon_root))

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eon-core")


async def cmd_bootstrap(args):
    """Bootstrap the kernel and keep running.

    Loads taiji.yaml, creates all components, verifies DAG,
    starts health pulse, and stays alive until Ctrl+C.
    """
    from src.kernel.origin import OriginKernel
    from src.kernel.event_bus import SystemEvent

    kernel = OriginKernel()

    # Bootstrap
    config_path = args.config or "config/taiji.yaml"
    report = await kernel.bootstrap(config_path)

    if not report.success:
        logger.error(f"Bootstrap FAILED: {report.errors}")
        return 1

    logger.info(f"Bootstrap OK: {report.components}")
    logger.info(f"Topology: DAG verified ({kernel.topology.number_of_nodes()} nodes, "
                f"{kernel.topology.number_of_edges()} edges)")
    logger.info(f"Registry: {list(kernel.registry.keys())}")
    logger.info(f"State: {kernel.state.stage.value}")

    # Keep alive
    logger.info("eon-core BLOOMING — press Ctrl+C to stop")
    try:
        while kernel.state.is_alive:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    await kernel.shutdown()
    logger.info("eon-core stopped")
    return 0


async def cmd_health(args):
    """Quick health check — bootstrap, check, shutdown."""
    from src.kernel.origin import OriginKernel

    kernel = OriginKernel()
    config_path = args.config or "config/taiji.yaml"
    report = await kernel.bootstrap(config_path)

    if not report.success:
        print(f"❌ Bootstrap failed: {report.errors}")
        return 1

    print(f"✅ eon-core HEALTHY")
    print(f"   State: {kernel.state.stage.value}")
    print(f"   Vertices: {list(kernel.registry.keys())}")
    print(f"   DAG: {kernel.topology.number_of_nodes()} nodes, {kernel.topology.number_of_edges()} edges")
    print(f"   Components: {list(report.components.keys())}")

    await kernel.shutdown()
    return 0


async def cmd_route(args):
    """Single query route — classify intent, find path, return plan."""
    from src.kernel.origin import OriginKernel
    from src.kernel.event_bus import SystemEvent

    kernel = OriginKernel()
    config_path = args.config or "config/taiji.yaml"
    report = await kernel.bootstrap(config_path)

    if not report.success:
        print(f"❌ Bootstrap failed: {report.errors}")
        return 1

    query = args.query
    event = SystemEvent(
        trace_id="cli-route",
        source="cli",
        payload={"query": query},
    )

    result = await kernel.route_event(event)

    print(f"Query: {query}")
    print(f"Route plan: {result.plan}")
    print(f"Samsara states: {dict(result.samsara_states)}")
    print(f"Filtered out: {result.filtered_out}")
    print(f"Fallback used: {result.fallback_used}")

    await kernel.shutdown()
    return 0


async def cmd_serve(args):
    """Start API server (stub — full implementation requires HTTP framework)."""
    from src.kernel.origin import OriginKernel
    from src.sphere.gateway import SphereGateway

    kernel = OriginKernel()
    config_path = args.config or "config/taiji.yaml"
    report = await kernel.bootstrap(config_path)

    if not report.success:
        logger.error(f"Bootstrap FAILED: {report.errors}")
        return 1

    gateway = SphereGateway(kernel)
    await gateway.initialize()

    logger.info(f"eon-core API server starting on port {args.port}...")
    logger.info("(HTTP server stub — full implementation requires aiohttp/fastapi)")

    # Health check demo
    health = await gateway.health()
    print(f"\nGET /health → {health['status']}")
    print(f"  Uptime: {health['uptime_seconds']:.1f}s")

    try:
        while kernel.state.is_alive:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    await kernel.shutdown()
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="eon-core",
        description="☯️ eon-core — 十层同心动态活体内核",
    )
    parser.add_argument("--config", default="config/taiji.yaml", help="Config file path")
    sub = parser.add_subparsers(dest="command")

    p_boot = sub.add_parser("bootstrap", help="启动内核 (保持运行)")
    p_boot.set_defaults(func=cmd_bootstrap)

    p_health = sub.add_parser("health", help="健康检查")
    p_health.set_defaults(func=cmd_health)

    p_route = sub.add_parser("route", help="查询路由测试")
    p_route.add_argument("query", help="查询文本")
    p_route.set_defaults(func=cmd_route)

    p_serve = sub.add_parser("serve", help="API 服务模式")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    try:
        return asyncio.run(args.func(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
