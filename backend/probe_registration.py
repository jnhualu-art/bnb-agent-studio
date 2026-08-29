"""
调查工具: dump 真实 ERC-8004 registration file 结构

用途: 分类引擎必须基于真实数据设计, 不能凭空猜关键词。
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from erc8004 import ERC8004Indexer

SCAN_BLOCKS = int(os.getenv("SCAN_BLOCKS", 9000))
PROBE_COUNT = int(os.getenv("PROBE_COUNT", 4))


async def main() -> None:
    indexer = ERC8004Indexer(network=os.getenv("NETWORK", "mainnet"))
    if not indexer.is_connected:
        print("RPC 连接失败")
        return

    latest = indexer.w3.eth.block_number
    from_block = max(0, latest - SCAN_BLOCKS)
    print(f"scanning {from_block} -> {latest}\n")

    mints = indexer.scan_minted_agents(from_block, latest)
    print(f"found {len(mints)} mints\n")

    dumped = 0
    async with httpx.AsyncClient() as client:
        for agent_id, block in mints:
            if dumped >= PROBE_COUNT:
                break
            uri = indexer.get_agent_uri(agent_id)
            if not uri:
                continue
            reg = await indexer.fetch_registration(client, uri)
            if not reg:
                continue

            dumped += 1
            print("=" * 70)
            print(f"agent_id={agent_id}  block={block}")
            print(f"uri={uri}")
            print("-" * 70)
            print(json.dumps(reg, ensure_ascii=False, indent=2)[:2500])
            print()

    if dumped == 0:
        print("未抓到任何 registration file, 尝试扩大 SCAN_BLOCKS")


if __name__ == "__main__":
    asyncio.run(main())
