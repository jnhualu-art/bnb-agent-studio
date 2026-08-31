"""
4 个 reference agent 健康检查 (Build the Era 提交前验证)
======================================================
逐个实例化 + run(1 cycle) + 取 current_status(), 确认评审打开时不出错。
复用 main.build_reference_agents() 的实例化参数, 保证与线上一致。
"""
import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main  # noqa: E402

agents = main.build_reference_agents()
print(f"[INIT] 初始化成功 {len(agents)} 个 agent: {list(agents.keys())}", flush=True)

results = []
for key, agent in agents.items():
    try:
        print(f"[RUN ] {key} ...", flush=True)
        agent.run(cycles=1)
        st = agent.current_status()
        cat = st.get("category") if isinstance(st, dict) else None
        state_status = None
        if isinstance(st, dict) and isinstance(st.get("state"), dict):
            state_status = st["state"].get("status")
        results.append(
            {
                "key": key,
                "name": agent.config.agent_name,
                "status": "OK",
                "category": cat,
                "state_status": state_status,
            }
        )
        print(f"     -> OK (category={cat}, state={state_status})", flush=True)
    except Exception as exc:  # noqa: BLE001
        results.append(
            {
                "key": key,
                "name": getattr(agent.config, "agent_name", key),
                "status": "FAIL",
                "error": traceback.format_exc()[-1000:],
            }
        )
        print(f"     -> FAIL: {exc}", flush=True)

print("\n=== HEALTHCHECK RESULT ===")
print(json.dumps(results, indent=2, ensure_ascii=False))
ok = sum(1 for r in results if r["status"] == "OK")
print(f"\n{ok}/{len(results)} agents OK")
