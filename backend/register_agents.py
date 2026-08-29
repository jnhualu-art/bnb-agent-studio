"""
ERC-8004 注册脚本 — 把四个 reference agent 注册上链
=====================================================
让市场里的 agent 从"我们数据库里的一条记录"变成"链上可发现的 ERC-721 资产"。

合约事实(已通过字节码 selector 探测确认):
  - BSC testnet Identity Registry: 0x8004A818BFB912233c491871b3d84c89A494BD9e (proxy)
  - 实现合约:                      0x7274e874CA62410a93Bd8bf61c69d8045E399c02
  - register(string agentURI)  selector 0xc298be  ✅ 存在
  - register()                 selector 0xa3a008  ✅ 存在

agentURI 两种模式:
  - data URI (默认): 把 registration JSON 内联成 base64, 完全自包含,
                     不依赖 IPFS / GitHub / 任何外部服务, 立即可用
  - http(s) URL:     --base-url https://raw.githubusercontent.com/.../silent-martin.json
                     更省 gas, 但需要先把 JSON 托管到公网

用法:
  # 1) 先生成一个专用测试钱包(别用主钱包)
  python register_agents.py --generate-wallet

  # 2) 领 testnet BNB 水龙头, 然后注册
  set ERC8004_PRIVATE_KEY=0x...
  python register_agents.py --network testnet

  # 3) 用 https 托管 JSON 注册(省 gas)
  python register_agents.py --network testnet --base-url https://example.com/agents
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web3 import Web3
from eth_account import Account

from erc8004 import make_web3
from agents.base_agent import CATEGORY_META

IDENTITY_REGISTRY = {
    "testnet": "0x8004A818BFB912233c491871b3d84c89A494BD9e",
    "mainnet": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
}

RPCS = {
    "testnet": [
        "https://bsc-testnet.publicnode.com",
        "https://data-seed-prebsc-1-s1.bnbchain.org:8545/",
    ],
    "mainnet": [
        *([f"https://bnb-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_BSC_KEY')}"] if os.getenv("ALCHEMY_BSC_KEY") else []),
        "https://bsc.publicnode.com",
    ],
}

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()

REGISTER_ABI = [
    {
        "inputs": [{"name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# 四个 reference agent 的身份定义(与 backend/main.py 保持一致)
AGENT_SPECS = [
    {
        "key": "grid_trading",
        "name": "silent-martin.agent",
        "description": (
            "BSC port of silent-martin, a Hummingbot Botcamp CERTIFIED market-making "
            "strategy. Anchors every quote to the on-chain DEX pool price instead of CEX "
            "mid, widens spread on DEX/CEX dislocation, applies inventory skew toward a "
            "target ratio, sizes spread by ATR volatility, and halts on stale data or "
            "extreme dislocation via hard kill-switches."
        ),
        "tags": ["Grid Trading", "Market Making", "Botcamp Certified"],
    },
    {
        "key": "rebalancing",
        "name": "rangeguard.agent",
        "description": (
            "Monitors PancakeSwap V3 and Uniswap V3 concentrated-liquidity positions on "
            "BSC and keeps them in range. Reads live position ticks and pool slot0, detects "
            "out-of-range (zero fee accrual, full single-sided exposure), and proposes a "
            "new range aligned to the pool tickSpacing."
        ),
        "tags": ["Rebalancing", "LP Management", "Concentrated Liquidity"],
    },
    {
        "key": "yield_optimisation",
        "name": "yieldpilot.agent",
        "description": (
            "Routes stablecoin liquidity across BSC pools by risk-adjusted APY. Filters "
            "noise pools via a TVL floor and APY sanity bounds, scores candidates by "
            "APY x stability (30d mean deviation) x liquidity (TVL), and migrates only "
            "when uplift exceeds the gas-cost threshold."
        ),
        "tags": ["Yield Optimisation", "APR Routing", "DeFi"],
    },
    {
        "key": "health_factor",
        "name": "hfsentinel.agent",
        "description": (
            "Monitors Venus lending positions on BSC and protects them from liquidation. "
            "Reads live on-chain snapshots (getAccountSnapshot + oracle price + collateral "
            "factor), computes health factor, and outputs concrete repay or add-collateral "
            "amounts to restore the target health factor."
        ),
        "tags": ["Health Factor", "Liquidation Protection", "Venus"],
    },
]


def build_registration_file(spec: dict, service_endpoint: str = "") -> dict:
    """生成符合 ERC-8004 的 registration file(对齐 TermiX 平台实测格式)"""
    meta = CATEGORY_META.get(spec["key"], {"label": spec["key"], "desc": ""})
    services = []
    if service_endpoint:
        services.append({"name": "A2A", "endpoint": service_endpoint, "version": "0.3.0"})

    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": spec["name"],
        "description": spec["description"],
        "image": "",
        "services": services,
        "x402Support": True,
        "active": True,
        "registrations": [],
        "supportedTrust": ["reputation"],
        "tags": spec["tags"],
        "attributes": [{"trait_type": "category", "value": meta["label"]}],
    }


def build_data_uri(reg: dict) -> str:
    """把 JSON 内联成 data URI — 零外部依赖"""
    payload = json.dumps(reg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "data:application/json;base64," + base64.b64encode(payload).decode()


def slugify(name: str) -> str:
    return name.replace(".agent", "").replace(".", "-")


def register_one(
    w3: Web3,
    account,
    registry_addr: str,
    uri: str,
) -> tuple[str, int, int | None]:
    """发送 register 交易, 返回 (tx_hash, status, agent_id)"""
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(registry_addr), abi=REGISTER_ABI
    )

    tx = contract.functions.register(uri).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 800_000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)

    # mint 出的 tokenId 就是 agentId
    agent_id = None
    for log in receipt["logs"]:
        topics = log["topics"]
        if len(topics) == 4 and topics[0].hex().lower() == TRANSFER_TOPIC.lower():
            agent_id = int(topics[3].hex(), 16)

    return tx_hash.hex(), receipt["status"], agent_id


def main() -> None:
    ap = argparse.ArgumentParser(description="Register reference agents on ERC-8004")
    ap.add_argument("--network", choices=["testnet", "mainnet"], default="testnet")
    ap.add_argument(
        "--base-url",
        default="",
        help="若设置, agentURI 用 {base_url}/{slug}.json 而非 data URI(省 gas, 需先托管)",
    )
    ap.add_argument("--service-endpoint", default="", help="A2A / MCP 端点")
    ap.add_argument(
        "--generate-wallet", action="store_true", help="生成一个新的测试钱包并退出"
    )
    ap.add_argument("--out", default="registered_agents.json")
    args = ap.parse_args()

    if args.generate_wallet:
        acct = Account.create()
        print("=== 新的测试钱包(请自行保管私钥) ===")
        print(f"address    : {acct.address}")
        print(f"private key: {acct.key.hex()}")
        print()
        print("testnet BNB 水龙头: https://testnet.bnbchain.org/faucet-smart")
        return

    pk = os.getenv("ERC8004_PRIVATE_KEY", "").strip()
    if not pk:
        print("请设置环境变量 ERC8004_PRIVATE_KEY")
        print("  没有钱包? 先跑: python register_agents.py --generate-wallet")
        return

    # 兼容不带 0x 前缀的私钥(Account.from_key 需要 hexstr 带前缀)
    if not pk.startswith("0x"):
        pk = "0x" + pk

    account = Account.from_key(pk)

    # 选一个可用 RPC
    w3 = None
    for url in RPCS[args.network]:
        try:
            candidate = make_web3(url, timeout=25)
            if candidate.is_connected():
                w3 = candidate
                print(f"RPC: {url}")
                break
        except Exception:
            continue
    if w3 is None:
        print("没有可用的 RPC 节点")
        return

    balance = w3.eth.get_balance(account.address)
    print(f"account: {account.address}")
    print(f"balance: {w3.from_wei(balance, 'ether')} BNB")
    if balance == 0:
        print("\n余额为 0, 先去水龙头领 testnet BNB:")
        print("  https://testnet.bnbchain.org/faucet-smart")
        return

    registry = IDENTITY_REGISTRY[args.network]
    results = []

    for spec in AGENT_SPECS:
        reg = build_registration_file(spec, args.service_endpoint)

        if args.base_url:
            uri = f"{args.base_url.rstrip('/')}/{slugify(spec['name'])}.json"
        else:
            uri = build_data_uri(reg)

        print()
        print("=" * 66)
        print(f"registering {spec['name']}  [{spec['key']}]")
        print(f"  uri length: {len(uri)} chars")

        try:
            tx_hash, status, agent_id = register_one(w3, account, registry, uri)
            print(f"  tx     : {tx_hash}")
            print(f"  status : {'ok' if status == 1 else 'FAILED'}")
            print(f"  agentId: {agent_id}")

            results.append(
                {
                    "name": spec["name"],
                    "category": spec["key"],
                    "category_label": CATEGORY_META.get(spec["key"], {}).get("label", ""),
                    "agent_id": agent_id,
                    "tx_hash": tx_hash,
                    "status": status,
                    "uri": uri if args.base_url else uri[:80] + "…(data uri)",
                    "network": args.network,
                }
            )
        except Exception as exc:
            print(f"  FAILED: {exc}")
            results.append(
                {"name": spec["name"], "category": spec["key"], "error": str(exc)}
            )

        time.sleep(1)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "network": args.network,
                "chain_id": w3.eth.chain_id,
                "registry": registry,
                "owner": account.address,
                "agents": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 66)
    print(f"saved -> {out_path}")
    if args.network == "testnet":
        print("查看: https://testnet.8004scan.io/agents?chain=97")
    else:
        print("查看: https://www.8004scan.io/agents?chain=56")


if __name__ == "__main__":
    main()
