"""
统计真实 agent 的 category / tags 分布, 用于设计四大类别映射表。

背景: TermiX 平台注册的 agent 自带权威分类字段
  - termix.profile.category  (如 "Automation & Ops")
  - tags                     (如 ["Agent Orchestration"])
关键词猜测在这批数据上完全失效, 必须以真实分布为准。
"""

import asyncio
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from erc8004 import ERC8004Indexer

SCAN_BLOCKS = int(os.getenv("SCAN_BLOCKS", 30000))
CONCURRENCY = int(os.getenv("CONCURRENCY", 15))


async def main() -> None:
    indexer = ERC8004Indexer(network=os.getenv("NETWORK", "mainnet"))
    if not indexer.is_connected:
        print("RPC 连接失败")
        return

    latest = indexer.w3.eth.block_number
    from_block = max(0, latest - SCAN_BLOCKS)
    print(f"scanning {from_block} -> {latest} (span {SCAN_BLOCKS})\n")

    mints = indexer.scan_minted_agents(from_block, latest)
    print(f"found {len(mints)} mint events\n")

    # 并发抓 registration file
    semaphore = asyncio.Semaphore(CONCURRENCY)
    regs: dict[int, dict] = {}

    async def _fetch(agent_id: int) -> None:
        async with semaphore:
            uri = indexer.get_agent_uri(agent_id)
            if not uri:
                return
            async with httpx.AsyncClient() as client:
                reg = await indexer.fetch_registration(client, uri)
                if reg:
                    regs[agent_id] = reg

    await asyncio.gather(*(_fetch(aid) for aid, _ in mints))

    print(f"fetched {len(regs)} registration files\n")

    categories: Counter = Counter()
    tags: Counter = Counter()
    namespaces: Counter = Counter()

    for reg in regs.values():
        termix = reg.get("termix") or {}
        profile = termix.get("profile") or {}
        cat = profile.get("category")
        if cat:
            categories[str(cat)] += 1
        ns = termix.get("namespace")
        if ns:
            namespaces[str(ns)] += 1
        for tag in reg.get("tags") or []:
            tags[str(tag)] += 1

    print("=" * 70)
    print(f"termix.profile.category 分布 (共 {sum(categories.values())} 个有分类)")
    print("=" * 70)
    for cat, n in categories.most_common(40):
        print(f"  {n:>5}  {cat}")

    print()
    print("=" * 70)
    print(f"tags 分布 (共 {len(tags)} 种)")
    print("=" * 70)
    for tag, n in tags.most_common(40):
        print(f"  {n:>5}  {tag}")

    print()
    print("=" * 70)
    print("namespace 分布")
    print("=" * 70)
    for ns, n in namespaces.most_common(10):
        print(f"  {n:>5}  {ns}")

    # 落盘供后续设计映射表
    out = {
        "scan_blocks": SCAN_BLOCKS,
        "mints": len(mints),
        "fetched": len(regs),
        "categories": dict(categories.most_common()),
        "tags": dict(tags.most_common()),
        "namespaces": dict(namespaces.most_common()),
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "category_stats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已落盘: {path}")


if __name__ == "__main__":
    asyncio.run(main())
