"""
BNB Agent Studio Marketplace — FastAPI 后端
============================================
把两大数据源统一成 API, 供前端(Vue3)消费:

  1. **链上索引 agent** —— ERC-8004 注册表里的真实 agent(读 agents_index.json)
  2. **四类 reference agent** —— 本项目自建、真实运行的四个策略 agent
     (Rebalancing / Grid Trading / Yield Optimisation / Health Factor)

四类 agent 由后台线程定期跑一轮, 状态缓存在内存, API 直接返回最新快照,
避免每个请求都触发链上调用导致超时。
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.grid_agent import GridConfig, GridTradingAgent
from agents.health_factor_agent import HealthFactorAgent, HealthFactorConfig
from agents.rebalancing_agent import RebalancingAgent, RebalancingConfig
from agents.yield_agent import YieldConfig, YieldOptimisationAgent
from base_agent import CATEGORY_META

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "agents_index.json")

# 后台刷新间隔(秒) — agent 每轮要多次链上调用, 不宜太频繁
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", 300))

app = FastAPI(
    title="BNB Agent Studio Marketplace API",
    description="AI agent marketplace for BNB Smart Chain (Build the Era hackathon)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # hackathon demo, 生产需收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 全局状态
# ---------------------------------------------------------------------------

reference_agents: dict[str, Any] = {}
reference_state: dict[str, dict] = {}
_state_lock = threading.Lock()
_last_refresh: float = 0.0


# ---------------------------------------------------------------------------
# 四类 reference agent 初始化(参数均为已实测通过的配置)
# ---------------------------------------------------------------------------

def build_reference_agents() -> dict[str, Any]:
    agents: dict[str, Any] = {}

    # 1) Grid Trading — silent-martin BSC 版
    try:
        agents["grid_trading"] = GridTradingAgent(
            GridConfig(
                agent_name="silent-martin.agent",
                dry_run=True,
                network="mainnet",
                cycle_interval_sec=0,
            )
        )
    except Exception as exc:
        logger.warning("grid agent init failed: %s", exc)

    # 2) Yield Optimisation — DefiLlama 风险调整 APY 路由
    try:
        agents["yield_optimisation"] = YieldOptimisationAgent(
            YieldConfig(
                agent_name="yieldpilot.agent",
                dry_run=True,
                network="mainnet",
                cycle_interval_sec=0,
            )
        )
    except Exception as exc:
        logger.warning("yield agent init failed: %s", exc)

    # 3) Health Factor — Venus 借贷清算保护
    hf_addr = os.getenv("HF_MONITOR_ADDRESS", "0x81EBde24453B8E40454616579EA79C79A197699D")
    try:
        agents["health_factor"] = HealthFactorAgent(
            HealthFactorConfig(
                agent_name="hfsentinel.agent",
                monitored_address=hf_addr,
                dry_run=True,
                network="mainnet",
                cycle_interval_sec=0,
            )
        )
    except Exception as exc:
        logger.warning("health factor agent init failed: %s", exc)

    # 4) Rebalancing — V3 LP 区间守护
    token_ids_raw = os.getenv("RB_TOKEN_IDS", "2690498,2690499,2672513")
    token_ids = [int(x) for x in token_ids_raw.split(",") if x.strip()]
    try:
        agents["rebalancing"] = RebalancingAgent(
            RebalancingConfig(
                agent_name="rangeguard.agent",
                token_ids=token_ids,
                dry_run=True,
                network="mainnet",
                cycle_interval_sec=0,
            )
        )
    except Exception as exc:
        logger.warning("rebalancing agent init failed: %s", exc)

    return agents


def refresh_worker() -> None:
    """后台线程: 定期跑一轮四类 agent, 刷新状态缓存"""
    global _last_refresh

    while True:
        for key, agent in list(reference_agents.items()):
            try:
                agent.run(cycles=1)
                with _state_lock:
                    reference_state[key] = agent.current_status()
                logger.info("[%s] refreshed", key)
            except Exception as exc:
                logger.exception("[%s] refresh failed: %s", key, exc)
                with _state_lock:
                    reference_state[key] = {
                        "name": agent.config.agent_name,
                        "category": key,
                        "category_label": CATEGORY_META.get(key, {}).get("label", key),
                        "state": {"status": "error", "notes": str(exc)},
                    }
        _last_refresh = time.time()
        time.sleep(REFRESH_INTERVAL)


@app.on_event("startup")
def on_startup() -> None:
    reference_agents.update(build_reference_agents())
    logger.info("initialized %s reference agents", len(reference_agents))
    threading.Thread(target=refresh_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# 链上索引(ERC-8004)
# ---------------------------------------------------------------------------

def load_index() -> dict:
    if not os.path.exists(INDEX_PATH):
        return {"total": 0, "agents": [], "category_stats": {}, "scan_blocks": 0}
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict:
    return {
        "service": "BNB Agent Studio Marketplace API",
        "chain": "BSC (chainId 56)",
        "endpoints": [
            "/api/health",
            "/api/agents",
            "/api/agents/{agent_id}",
            "/api/reference-agents",
            "/api/reference-agents/{category}",
            "/api/categories",
        ],
    }


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "reference_agents": len(reference_agents),
        "refreshed_agents": len(reference_state),
        "last_refresh": _last_refresh,
        "index_loaded": os.path.exists(INDEX_PATH),
    }


@app.get("/api/agents")
def list_agents(
    category: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """链上索引的 ERC-8004 agent 列表(支持类别筛选与关键词搜索)"""
    data = load_index()
    agents = data.get("agents", [])

    if category:
        agents = [a for a in agents if a.get("category") == category]
    if q:
        ql = q.lower()
        agents = [
            a for a in agents
            if ql in (a.get("name") or "").lower()
            or ql in (a.get("description") or "").lower()
        ]

    total = len(agents)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "agents": agents[offset : offset + limit],
        "scan_blocks": data.get("scan_blocks"),
    }


@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: int) -> dict:
    data = load_index()
    for a in data.get("agents", []):
        if a.get("agent_id") == agent_id:
            return a
    raise HTTPException(status_code=404, detail=f"agent {agent_id} not found")


@app.get("/api/reference-agents")
def list_reference_agents() -> dict:
    """本项目自建的四类 reference agent 实时状态"""
    with _state_lock:
        return {
            "total": len(reference_agents),
            "refresh_interval_sec": REFRESH_INTERVAL,
            "last_refresh": _last_refresh,
            "agents": list(reference_state.values()),
        }


@app.get("/api/reference-agents/{category}")
def get_reference_agent(category: str) -> dict:
    with _state_lock:
        if category not in reference_agents:
            raise HTTPException(status_code=404, detail=f"category {category} not found")
        return reference_state.get(
            category,
            {
                "name": reference_agents[category].config.agent_name,
                "category": category,
                "state": {"status": "pending", "notes": "first cycle not finished yet"},
            },
        )


@app.get("/api/categories")
def categories() -> dict:
    """官方四大类别 + 各类别覆盖统计"""
    data = load_index()
    index_stats = data.get("category_stats", {})

    result = {}
    for key, meta in CATEGORY_META.items():
        ref = reference_state.get(key, {})
        result[key] = {
            "label": meta["label"],
            "description": meta["desc"],
            "reference_agent": ref.get("name"),
            "reference_agent_status": (ref.get("state") or {}).get("status"),
            "onchain_indexed": index_stats.get(key, 0),
        }

    return {
        "categories": result,
        "onchain_total": data.get("total", 0),
        "onchain_uncategorised": index_stats.get("uncategorised", 0),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
