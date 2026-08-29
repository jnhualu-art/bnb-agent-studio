"""
Health Factor Monitoring Agent
==============================
官方类别: Health Factor Monitoring — "Protects lending positions from liquidation"

真实链上实现: 直接读 Venus Protocol (BSC) 的借贷仓位, 计算健康因子。

数据流(全部链上, 无 mock):
  1. Comptroller.getAssetsIn(account)      -> 用户已进入的市场
  2. vToken.getAccountSnapshot(account)    -> (error, vToken余额, 借款额, 汇率)
  3. Oracle.getUnderlyingPrice(vToken)     -> 底层资产美元价格(1e18 标量)
  4. Comptroller.markets(vToken)           -> 抵押因子 collateralFactorMantissa
  5. 计算:
       抵押值 = Σ(余额 × 汇率 × 价格 × 抵押因子)
       借款值 = Σ(借款 × 价格)
       健康因子 HF = 抵押值 / 借款值
  6. HF < 告警阈值 -> 建议追加抵押或还款; HF <= 1.0 -> 可被清算, 紧急告警

风控(继承基类 + 本 agent 专属):
  - HF 低于 liquidation_warn_hf 立即产出告警动作
  - 数据陈旧 / 价格异常 -> 停止决策
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass

# 允许从 backend/ 与 backend/agents/ 两个层级导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

from base_agent import (
    CATEGORY_HEALTH_FACTOR,
    AgentConfig,
    BaseAgent,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Venus Protocol — BSC 主网地址
# ---------------------------------------------------------------------------

VENUS_COMPTROLLER = "0xfD36E2c2a6789Db23113685031d7F16329158384"
# Oracle 地址一律从 Comptroller.oracle() 动态读取(实测硬编码地址会失效:
# 0xd8B6... 与 ResilientOracle 0xf19B... 在 BSC 上均无合约代码)
VBNB = "0xA07c5b74C9B40447a954e1466938b865b6BBea36"   # 无 underlying, 原生 BNB

BSC_RPCS = [
    "https://bsc.publicnode.com",
    "https://1rpc.io/bnb",
]

COMPTROLLER_ABI = [
    {
        "inputs": [],
        "name": "getAllMarkets",
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getAssetsIn",
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getAccountLiquidity",
        "outputs": [
            {"name": "", "type": "uint256"},
            {"name": "", "type": "uint256"},
            {"name": "", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "oracle",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "markets",
        "outputs": [
            {"name": "isListed", "type": "bool"},
            {"name": "collateralFactorMantissa", "type": "uint256"},
            {"name": "isVenus", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

VTOKEN_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "getAccountSnapshot",
        "outputs": [
            {"name": "", "type": "uint256"},
            {"name": "", "type": "uint256"},
            {"name": "", "type": "uint256"},
            {"name": "", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "underlying",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

ORACLE_ABI = [
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "getUnderlyingPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

MANTISSA = 10**18


@dataclass
class HealthFactorConfig(AgentConfig):
    """Health Factor agent 专属参数"""

    monitored_address: str = ""        # 被监控的钱包(必填)
    warn_hf: float = 1.5               # 低于此值告警
    critical_hf: float = 1.15          # 低于此值紧急
    target_hf: float = 2.0             # 建议维持的目标
    rpc_url: str = ""
    rpc_throttle_sec: float = 0.35     # 公共 RPC 限流保护, 不加间隔会被 403


class HealthFactorAgent(BaseAgent):
    CATEGORY = CATEGORY_HEALTH_FACTOR

    def __init__(self, config: HealthFactorConfig | None = None):
        super().__init__(config or HealthFactorConfig())
        self.config: HealthFactorConfig

        from erc8004 import make_web3, pick_rpc  # 复用 backend/erc8004.py 的 RPC 工具

        self.rpc_url = self.config.rpc_url or pick_rpc(BSC_RPCS)
        self.w3 = make_web3(self.rpc_url, timeout=25)
        self.comptroller = self.w3.eth.contract(
            address=Web3.to_checksum_address(VENUS_COMPTROLLER), abi=COMPTROLLER_ABI
        )

        # oracle 动态解析: 绝不硬编码, Venus 换 oracle 时可自动跟随
        self.oracle_address = self.comptroller.functions.oracle().call()
        self.oracle = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.oracle_address), abi=ORACLE_ABI
        )
        self._decimals_cache: dict[str, int] = {}

    # ------------------------------------------------------------------
    # 数据层
    # ------------------------------------------------------------------

    def fetch_market_data(self) -> dict:
        """读取被监控地址的全部 Venus 仓位快照"""
        account = Web3.to_checksum_address(self.config.monitored_address)
        assets = self.comptroller.functions.getAssetsIn(account).call()

        positions = []
        for vtoken in assets:
            try:
                pos = self._read_position(vtoken, account)
                if pos:
                    positions.append(pos)
            except Exception as exc:
                logger.warning("read position %s failed: %s", vtoken, exc)

            # 公共 RPC 速率限制保护(实测连续调用会被 403)
            if self.config.rpc_throttle_sec:
                time.sleep(self.config.rpc_throttle_sec)

        return {"timestamp": time.time(), "positions": positions, "assets": len(assets)}

    def _read_position(self, vtoken: str, account: str) -> dict | None:
        vtoken_cs = Web3.to_checksum_address(vtoken)
        v = self.w3.eth.contract(address=vtoken_cs, abi=VTOKEN_ABI)

        err, v_balance, borrow, exchange_rate = v.functions.getAccountSnapshot(account).call()
        if err != 0:
            return None
        if v_balance == 0 and borrow == 0:
            return None

        # 抵押因子
        _, collateral_factor, _ = self.comptroller.functions.markets(vtoken_cs).call()

        # 价格(1e18 标量)
        price = self.oracle.functions.getUnderlyingPrice(vtoken_cs).call()

        # 底层资产 decimals
        decimals = self._underlying_decimals(vtoken_cs)

        # 底层资产数量 = vToken余额 × 汇率 / 1e18
        underlying_amount = (v_balance * exchange_rate) / MANTISSA

        supply_usd = (underlying_amount * price) / MANTISSA / (10 ** decimals)
        borrow_usd = (borrow * price) / MANTISSA / (10 ** decimals)

        try:
            symbol = v.functions.symbol().call()
        except Exception:
            symbol = vtoken_cs[:10]

        return {
            "vtoken": vtoken_cs,
            "symbol": symbol,
            "v_token_balance": v_balance,
            "borrow_balance": borrow,
            "exchange_rate": exchange_rate,
            "price_usd": price / MANTISSA / (10 ** max(0, decimals - 18)) if decimals < 18 else price / MANTISSA,
            "collateral_factor": collateral_factor / MANTISSA,
            "supply_usd": round(supply_usd, 2),
            "borrow_usd": round(borrow_usd, 2),
            "decimals": decimals,
        }

    def _underlying_decimals(self, vtoken_cs: str) -> int:
        if vtoken_cs.lower() == VBNB.lower():
            return 18
        if vtoken_cs in self._decimals_cache:
            return self._decimals_cache[vtoken_cs]

        try:
            v = self.w3.eth.contract(address=vtoken_cs, abi=VTOKEN_ABI)
            underlying = v.functions.underlying().call()
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(underlying), abi=ERC20_ABI
            )
            decimals = token.functions.decimals().call()
        except Exception:
            decimals = 18

        self._decimals_cache[vtoken_cs] = decimals
        return decimals

    # ------------------------------------------------------------------
    # 策略核心
    # ------------------------------------------------------------------

    def compute_health_factor(self, positions: list[dict]) -> tuple[float | None, dict]:
        """
        计算健康因子。

        HF = Σ(抵押 × 抵押因子) / Σ(借款)
        无借款时返回 None(表示无限安全)。
        """
        weighted_collateral = sum(
            p["supply_usd"] * p["collateral_factor"] for p in positions
        )
        total_borrow = sum(p["borrow_usd"] for p in positions)

        detail = {
            "supply_usd": round(sum(p["supply_usd"] for p in positions), 2),
            "borrow_usd": round(total_borrow, 2),
            "weighted_collateral_usd": round(weighted_collateral, 2),
        }

        if total_borrow <= 0:
            return None, detail

        hf = weighted_collateral / total_borrow
        return hf, detail

    def run_cycle(self) -> dict:
        positions = self._current_data.get("positions", [])
        if not positions:
            return {
                "metrics": {"positions": 0, "health_factor": None},
                "actions": [],
                "notes": f"no Venus position for {self.config.monitored_address}",
            }

        hf, detail = self.compute_health_factor(positions)

        actions = []
        notes = ""
        if hf is None:
            notes = "no borrow -> no liquidation risk"
        else:
            if hf <= 1.0:
                level = "CRITICAL"
                notes = f"HF {hf:.3f} <= 1.0 -> liquidatable NOW"
            elif hf < self.config.critical_hf:
                level = "CRITICAL"
                notes = f"HF {hf:.3f} < {self.config.critical_hf} -> urgent"
            elif hf < self.config.warn_hf:
                level = "WARN"
                notes = f"HF {hf:.3f} < {self.config.warn_hf} -> caution"
            else:
                level = "SAFE"
                notes = f"HF {hf:.3f} healthy"

            if level in ("WARN", "CRITICAL"):
                actions.append(self._build_protection_action(positions, hf, level))

        metrics = {
            "positions": len(positions),
            "health_factor": round(hf, 4) if hf else None,
            "risk_level": level if hf else "SAFE",
            "monitored": self.config.monitored_address,
            **detail,
        }

        return {"metrics": metrics, "actions": actions, "notes": notes, "positions": positions}

    def _build_protection_action(self, positions: list[dict], hf: float, level: str) -> dict:
        """计算需要追加多少抵押 / 还多少借款才能回到目标 HF"""
        weighted = sum(p["supply_usd"] * p["collateral_factor"] for p in positions)
        borrow = sum(p["borrow_usd"] for p in positions)
        target = self.config.target_hf

        # 方案 A: 还款(降低分子需求) — 需还到 borrow' = weighted / target
        repay_needed = max(0.0, borrow - weighted / target)

        # 方案 B: 追加抵押 — 需要补充的加权抵押 = target*borrow - weighted
        collateral_gap = max(0.0, target * borrow - weighted)
        best_cf = max((p["collateral_factor"] for p in positions), default=0.5)
        add_collateral_usd = collateral_gap / best_cf if best_cf else 0.0

        return {
            "type": "PROTECT",
            "level": level,
            "current_hf": round(hf, 4),
            "target_hf": target,
            "option_a_repay_usd": round(repay_needed, 2),
            "option_b_add_collateral_usd": round(add_collateral_usd, 2),
            "dry_run": self.config.dry_run,
        }

    # ------------------------------------------------------------------
    # 风控扩展: HF 过低直接拉响 kill-switch
    # ------------------------------------------------------------------

    def check_risk(self, metrics: dict) -> tuple[bool, str]:
        allowed, reason = super().check_risk(metrics)
        if not allowed:
            return allowed, reason

        hf = metrics.get("health_factor")
        if hf is not None and hf <= 1.0:
            # 不停止监控, 但要标记紧急 (监控类 agent 停机反而更危险)
            self.state.notes = f"CRITICAL: HF={hf:.3f} liquidatable"
        return True, reason


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    addr = os.getenv("MONITOR_ADDRESS", "")
    if not addr:
        print("请设置 MONITOR_ADDRESS 环境变量(要监控的钱包地址)")
        return

    cfg = HealthFactorConfig(
        agent_name="hfsentinel.agent",
        agent_description=(
            "Monitors Venus lending positions on BSC and protects them from "
            "liquidation. Reads live on-chain snapshots (getAccountSnapshot + "
            "oracle price + collateral factor), computes health factor, and "
            "outputs concrete repay / add-collateral amounts to restore target HF."
        ),
        monitored_address=addr,
        dry_run=True,
        network="mainnet",
        cycle_interval_sec=0,
    )

    agent = HealthFactorAgent(cfg)
    agent.run(cycles=1)

    print("\n" + "=" * 70)
    print("FINAL STATUS")
    print("=" * 70)
    print(json.dumps(agent.current_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
