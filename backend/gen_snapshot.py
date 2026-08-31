"""
生成前端离线快照 (供 CloudStudio 纯静态部署)
============================================
本地跑 4 个 reference agent + 读链上索引, 输出 frontend/data/*.json。
前端 api.js / demo.html 在 fetch 后端失败时回退读这些本地文件,
使纯静态部署也能展示完整 marketplace + demo(数据是最近一次真实链上快照)。
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main  # noqa: E402
from agents.base_agent import CATEGORY_META  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "..", "frontend", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def run_with_retry(agent, key, max_attempts=3):
    """跑 agent, yield 偶发网络抖动时重试, 取 current_status()"""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            agent.run(cycles=1)
            st = agent.current_status()
            if isinstance(st, dict):
                s = (st.get("state") or {}).get("status")
                if s != "error" or key != "yield_optimisation":
                    return st, None
            return st, None
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"  [{key}] attempt {attempt} failed: {exc}", flush=True)
            time.sleep(2)
    # 全部失败: 构造 error 状态
    return {
        "name": agent.config.agent_name,
        "category": key,
        "category_label": CATEGORY_META.get(key, {}).get("label", key),
        "state": {"status": "error", "notes": str(last_exc)},
    }, last_exc


print("[SNAPSHOT] building reference agents ...", flush=True)
agents = main.build_reference_agents()
ref_state = {}
for key, agent in agents.items():
    print(f"  run {key} ...", flush=True)
    st, _ = run_with_retry(agent, key)
    ref_state[key] = st

# 链上索引
index = main.load_index()
cats = {}
for key, meta in CATEGORY_META.items():
    ref = ref_state.get(key, {})
    cats[key] = {
        "label": meta["label"],
        "description": meta["desc"],
        "reference_agent": ref.get("name"),
        "reference_agent_status": (ref.get("state") or {}).get("status"),
        "onchain_indexed": index.get("category_stats", {}).get(key, 0),
    }

snapshot = {
    "reference_agents": {
        "total": len(agents),
        "refresh_interval_sec": int(os.getenv("REFRESH_INTERVAL", 300)),
        "last_refresh": time.time(),
        "agents": list(ref_state.values()),
    },
    "categories": {
        "categories": cats,
        "onchain_total": index.get("total", 0),
        "onchain_uncategorised": index.get("category_stats", {}).get("uncategorised", 0),
    },
    "agents_sample": {
        "total": index.get("total", 0),
        "offset": 0,
        "limit": 6,
        "agents": index.get("agents", [])[:6],
        "scan_blocks": index.get("scan_blocks"),
    },
}

files = {
    "reference-agents": snapshot["reference_agents"],
    "categories": snapshot["categories"],
    "agents": snapshot["agents_sample"],
}
for name, payload in files.items():
    path = os.path.join(DATA_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[WRITE] {path} ({len(json.dumps(payload))} bytes)", flush=True)

print("[SNAPSHOT] done. output ->", os.path.abspath(DATA_DIR), flush=True)
