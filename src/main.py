"""eon-core — 协调内核 (道)

架构:
  道 (eon-core) → S(fish-ecology-assistant 知识) + T(cognitive-search-engine 验证)
  → 万物: P₁(porpoise 江豚) + P₂(coilia 刀鲚) + P₃(culter 鲌类) + C(conflict 仲裁)

用法:
    python -m eon_core bootstrap          # 启动内核
    python -m eon_core search "鳤"        # 物种搜索
    python -m eon_core health             # 健康检查

架构: 道 (eon-core) → 一 (workspace) → 二 (project_loader) → 三 (S-T-V 三角) → 万物
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="eon-core 统一协调内核")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("bootstrap", help="启动内核")
    sub.add_parser("health", help="全栈健康检查")
    search_p = sub.add_parser("search", help="物种搜索")
    search_p.add_argument("query", nargs="?", default="鳤")

    args = parser.parse_args()

    from eon_core.kernel.origin import OriginKernel
    kernel = OriginKernel()

    if args.command == "bootstrap":
        asyncio.run(kernel.bootstrap())
        print("  eon-core 内核已启动。使用 health 或 search 命令。")

    elif args.command == "health":
        asyncio.run(kernel.bootstrap())
        result = kernel.health()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.command == "search":
        asyncio.run(kernel.bootstrap())
        result = kernel.search(args.query)
        if hasattr(result, "summary"):
            print(result.summary())
        else:
            print(result)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
