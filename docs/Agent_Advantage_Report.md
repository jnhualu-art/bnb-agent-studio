# Agent Advantage Report

**Submission:** Build the Era — BNB Agent Studio Marketplace
**Track:** TermiX Challenge ($10,000 total: $6,000 / $3,000 / $1,000)
**Date:** 2026-08-29
**Live demo:** http://localhost:5173 · **API:** http://localhost:8000/api

---

## 1. The question TermiX asks

> *"Does hiring an agent on your marketplace beat doing the job yourself, and can you prove it?"*

This report answers it with **one claim and four pieces of evidence**:

**Claim.** For all four agent categories, the agents on our marketplace produce
decisions that a human either (a) cannot produce at all, (b) cannot produce fast
enough to matter, or (c) produces only after calculation that itself takes longer
than the window in which the decision is useful. Every decision is derived from
live BNB Smart Chain state and is reproducible by anyone calling our API.

**Honest framing up front:** our agents run in `dry_run` mode — they publish
decisions, they do not send real orders or move funds. What we prove here is
**decision quality and decision latency**, not realised P&L. All *inputs* are real
on-chain reads; we do not claim realised returns we have not earned.

---

## 2. Baseline — what "doing it yourself" actually costs

Before the agent evidence, the honest baseline. A human managing these four jobs
must:

| Job | What a human must do | Frequency |
|---|---|---|
| Grid trading / market making | Read DEX + CEX price, compute fair value, compute volatility, size spread, post both sides | Continuously, seconds |
| Yield optimisation | Compare every pool's APY, TVL, and 30-day stability, filter out noise | Continuously, minutes |
| Lending health factor | Read every position, oracle price, collateral factor; recompute HF | Continuously — liquidation has no grace period |
| LP rebalancing | Read position ticks and pool `slot0`, detect range exit | Continuously, minutes |

The failure mode is not "a human is slightly worse." It is that **three of these
four jobs are continuous**, and a human is not. Liquidations do not wait for
business hours; a lending position sitting at HF 1.09 can be liquidated while its
owner sleeps.

---

## 3. Evidence

All figures below are a live snapshot taken from our API
(`GET /api/reference-agents`) on 2026-08-29 against BNB Smart Chain mainnet
(chainId 56). Raw snapshot: [`ref_agents_snapshot.json`](../ref_agents_snapshot.json).

### 3.1 Grid Trading — `silent-martin.agent`

> **Lineage note:** this is a BSC port of *silent-martin*, a strategy that has been
> **officially CERTIFIED by Hummingbot Botcamp**. Most marketplace entries demo
> toy agents; this one carries an external, verifiable certification.

| Metric | Live value |
|---|---|
| Fair value (DEX-anchored) | **$687.316** |
| CEX reference (Gate.io) | $687.400 |
| DEX/CEX dislocation | **1.22 bps** |
| ATR (15m, 14 periods) | 0.132% |
| Quoted spread (ATR-scaled) | **26.39 bps** |
| Bid / Ask | $686.409 / $688.223 |
| Grid orders published | **6** (3 levels, both sides) |

**Why this beats doing it yourself.** The agent anchors quotes to the *on-chain*
pool price rather than the CEX mid — the same insight that earned silent-martin its
Botcamp certification. It then widens the spread proportionally to realised
volatility (ATR) instead of quoting a fixed spread. A human manually watching both
venues cannot maintain a volatility-scaled two-sided book continuously; and quoting
a *fixed* spread in either direction is wrong — too wide in calm markets (no fills),
too tight in volatile ones (adverse selection).

### 3.2 Yield Optimisation — `yieldpilot.agent`

| Metric | Live value |
|---|---|
| Candidate pools after filtering | **49** (from 636 BSC pools) |
| Best risk-adjusted pool | USDT-SPYB (uniswap-v4) |
| Raw APY | 141.30% |
| Risk-adjusted score | 121.31 |

**Why this beats doing it yourself.** Two filters a human will not apply
consistently:

1. **Noise rejection.** Raw APY rankings on BSC are dominated by garbage — pools
   advertising ~24,000% APY on $16k of TVL. We hard-filter on TVL ≥ $1M and
   0.5% ≤ APY ≤ 200%, which collapses 636 pools to 49 real candidates.
2. **Risk adjustment.** Score = APY × stability × liquidity, where *stability*
   penalises pools whose current APY has diverged from their own 30-day mean.
   This is what separates "141% that has been 141% for a month" from "141% since
   this morning."

A human comparing 636 pools by hand is not slower — it is not a task a human does
at all.

### 3.3 Health Factor Monitoring — `hfsentinel.agent`

Monitoring a **real $11.1M Venus lending position** (`0x81EBde24453B8E40454616579EA79C79A197699D`).

| Metric | Live value |
|---|---|
| Supply (collateral) | **$11,100,905** |
| Borrow | **$8,332,458** |
| Weighted collateral | $9,158,246 |
| **Health factor** | **1.0991** → `CRITICAL` |
| Protection option A — repay | **$3,753,335** to restore HF = 2.0 |
| Protection option B — add collateral | **$9,098,995** |

**This is the strongest single piece of evidence in the submission.**

A live position with $11.1M supplied and $8.3M borrowed is sitting at **HF 1.0991**
— roughly 9% of cushion before liquidation. The agent did not merely raise an
alert; it computed the *exact* dollar amounts for both recovery paths:

- repay **$3,753,335**, or
- add **$9,098,995** of collateral

To do this by hand you must: enumerate every entered market, call
`getAccountSnapshot` on each, fetch each oracle price, fetch each collateral
factor, convert decimals correctly, then solve for the target HF. That is dozens of
correct operations under time pressure, on a position where being wrong costs eight
figures. The agent produces it in one cycle, every cycle.

This is the difference between "an agent that is nice to have" and "an agent that
is the reason you still have the position."

### 3.4 Rebalancing — `rangeguard.agent`

| Metric | Live value |
|---|---|
| LP positions monitored | 1 (ASTER/USDT), supports up to 10 |
| Out of range | **0** |
| Near edge | **0** |
| Healthy | 1 |

Verified separately against live PancakeSwap/Uniswap V3 positions on BSC
(tokenIds `2690498`, `2690499`, `2672513`):

- QQQB/USDC ×2 — **price was 0.15% from the lower range edge**, flagged
  `PREPOSITION` with a proposed new range (tick 64680–66720)
- ASTER/USDT — healthy

**Why this beats doing it yourself.** A V3 position that leaves its range stops
earning fees *and* becomes 100% exposed to one asset. The window between "price
approaching the edge" and "position is dead" is measured in minutes. The agent
flags at a configurable band (default 2%) *before* the exit — the human version of
this is noticing days later.

---

## 4. How to verify this yourself (the "prove it" part)

Every number above is reproducible. No screenshots, no mock data.

```bash
# All four agents, live state
curl http://localhost:8000/api/reference-agents

# One category
curl http://localhost:8000/api/reference-agents/health_factor

# Category coverage + on-chain index stats
curl http://localhost:8000/api/categories

# The on-chain ERC-8004 agent index (103 agents indexed this run)
curl http://localhost:8000/api/agents?limit=10
```

Underlying chain reads, for anyone who wants to go one level deeper:

| Agent | Chain calls |
|---|---|
| `hfsentinel` | `Comptroller.getAssetsIn` → `vToken.getAccountSnapshot` → `Oracle.getUnderlyingPrice` → `Comptroller.markets` |
| `rangeguard` | `PositionManager.positions` → `Factory.getPool` → `Pool.slot0` → `Pool.tickSpacing` |
| `silent-martin` | `Pool.slot0` (on-chain fair value) + Gate.io ticker + K-line ATR |
| `yieldpilot` | DefiLlama Yields API, filtered and risk-adjusted |

---

## 5. The finding that shapes this submission

We indexed the ERC-8004 Identity Registry and classified **103 agents** registered
on BSC in the most recent blocks:

| Category | Count |
|---|---|
| Rebalancing | **0** |
| Grid Trading | **0** |
| Yield Optimisation | **0** |
| Health Factor Monitoring | **0** |
| **General AI agent** | **103** |

BSC has 200,000+ registered agents, but they are overwhelmingly *general-purpose*
AI agents — writing code, generating designs, doing research. The four financial
categories the hackathon asks a marketplace to cover are, on-chain, **empty**.

We did not quietly stuff general agents into financial buckets to make our coverage
look better. We built the four ourselves, and the marketplace presents them with
the same depth as it presents the 103 indexed on-chain agents. That is why
"hire an agent here" means something financial rather than something generic.

---

## 6. Limitations (stated plainly)

1. **`dry_run` by default.** Agents publish decisions; they do not execute. This is
   deliberate for a hackathon build handling an $11M third-party position. The
   decision logic is production-shaped, and turning execution on is a
   configuration change plus an audit — not a rewrite.
2. **We prove decision quality, not realised P&L.** No backtested or live returns
   are claimed anywhere in this submission.
3. **Single-venue coverage per agent.** `hfsentinel` covers Venus; `rangeguard`
   covers V3-style concentrated liquidity. Broadening venue coverage is the
   obvious next step, not a design flaw.
4. **On-chain index is a recent-block sample.** Public RPC nodes restrict historical
   `getLogs` windows; our 103-agent index covers the most recent high-density
   blocks. Archive-node access scales this to the full registry.
5. **Reference agents are not yet registered on-chain.** The four agents run live
   and are served through this marketplace, but their ERC-8004 registration — which
   would give each one a discoverable on-chain identity — has not been deployed.
   The registration script is written and tested (`backend/register_agents.py`,
   `register(string)` at selector `0xc298be` confirmed against the registry
   implementation); the only blocker is testnet BNB, whose faucet requires a
   mainnet balance. Total cost to complete: ~0.00012 tBNB. This affects
   discoverability, not the agents' operation or the evidence above.

---

## 7. Bottom line

For the health-factor case alone, the marketplace surfaces a live $11.1M position
at **HF 1.0991** and hands its owner two exact recovery figures. That is not a
convenience — it is the difference between catching a liquidation and being
liquidated. The other three categories show the same pattern in kind, if not in
dollar magnitude: continuous, correctly-computed, chain-derived decisions that a
human does not produce at the moment they are needed.

**That is the advantage, and every number behind it is reproducible from the API.**

---

*Appendix: raw snapshot — [`ref_agents_snapshot.json`](../ref_agents_snapshot.json)*
*On-chain index — [`backend/agents_index.json`](../backend/agents_index.json)*
