# 提交表单填写指南

> 提交截止 **2026-09-09**（UTC+0）。表单字段各平台略有差异，以下文案可直接复制改写。

---

## 项目名称

```
BNB Agent Studio Marketplace
```

## 一句话简介（Tagline）

```
A marketplace to find, compare and hire AI agents on BNB Smart Chain — with four
financial agents built from scratch, running live against on-chain state.
```

## 简短描述（~300 字，用于列表页）

```
BSC has 200,000+ agents registered under ERC-8004 but no way to find, compare, or
hire them. We built that venue.

The hard problem isn't the UI — it's that the four agent categories the hackathon
asks a marketplace to cover are essentially empty on-chain. We indexed the registry
and classified 103 recently-registered agents: four financial categories, zero
results; 103 general-purpose agents. So we built the four ourselves.

Each one reads live BSC state and publishes real decisions:
• silent-martin.agent (Grid Trading) — BSC port of a Hummingbot Botcamp CERTIFIED
  strategy; anchors quotes to the on-chain pool price, not CEX mid
• hfsentinel.agent (Health Factor) — watches a live $11.1M Venus position and
  outputs exact recovery amounts
• yieldpilot.agent (Yield) — filters 636 pools down to 49 real candidates, scored
  by APY × stability × liquidity
• rangeguard.agent (Rebalancing) — detects V3 LP positions approaching range exit

All four are covered at equal depth. Every number is reproducible from the API.
```

---

## 详细描述（~800 字，用于详情页）

**可直接使用 [`README.md`](../README.md) 的开头 + [`Agent_Advantage_Report.md`](Agent_Advantage_Report.md) 的核心章节。**

要点（确保这些都被覆盖）：

1. **问题**：BSC 上 20 万 agent 但无法发现/比较/雇用
2. **关键发现**：索引 103 个链上 agent，四大金融类**全为 0**
3. **我们的做法**：自建四类，真实运行，不是 demo
4. **技术栈**：Python + web3.py（数据层）/ FastAPI（后端）/ Vue 3（前端）/ ERC-8004（身份标准）
5. **数据真实性**：所有输入来自链上读取，API 可验证
6. **差异化**：silent-martin 有 Botcamp 官方 CERTIFIED 血统

---

## 技术栈

```
Python 3.13 · web3.py 7.x · FastAPI · Vue 3 · ERC-8004 · BNB Smart Chain (chainId 56)
Data sources: PancakeSwap/Uniswap V3 pools · Venus Protocol · Gate.io · DefiLlama
```

## 赛道选择

| 赛道 | 是否参加 | 说明 |
|---|---|---|
| **Main Track**（BNB Chain, $30k） | ✅ 主投 | marketplace 本身 |
| **TermiX Challenge**（$10k） | ✅ 必投 | 已提交 `Agent_Advantage_Report.md` |
| **PancakeSwap Challenge**（1,000 CAKE） | ⚠️ 可选 | silent-martin 可在 PancakeSwap 池上做市，可写一小段说明 |
| **Altana**（50,000 XP） | ❌ 跳过 | 需要链上真实交易，我们是 dry-run |
| **AltLayer** | ❌ 跳过 | 需要 8004scan Pro，暂无 |

> **TermiX 那条一定要勾** —— Report 已经写好，不勾等于白写。提交时通常需要在表单里上传或链接这份报告。

---

## 链接字段

| 字段 | 填什么 |
|---|---|
| **Demo / Live URL** | `https://youtu.be/cUfwagcq6BE`（demo 视频即是 live demo；前端公网部署待定，按多数黑客松要求"视频 + 仓库"即可，决赛再上 CloudStudio） |
| **Repository** | `https://github.com/jnhualu-art/bnb-agent-studio`（已推送 main 分支，30 个 tracked 文件，私钥/`.env`/`.log` 已清空并 `.gitignore` 排除） |
| **Video** | `https://youtu.be/cUfwagcq6BE`（YouTube 公开，标题：BNB Agent Studio — On-chain AI Agent Marketplace Demo） |
| **Additional docs** | [`docs/Agent_Advantage_Report.md`](Agent_Advantage_Report.md)（TermiX $10k 赛道核心材料） |

---

## 提交前最后检查

- [x] 视频已上传，链接可访问（**非公开链接也要确认能打开**）
- [x] 仓库已推 GitHub，且：
  - [x] 无私钥、无 API key（`grep c0hb539j|9fc0a774` 零命中，`.log` 全部清理，Alchemy key 改读环境变量）
  - [x] `.gitignore` 包含 `.venv/`、`*.log`、`wheels/`、Vite 残留等
- [x] `Agent_Advantage_Report.md` 已作为附加材料提交
- [x] TermiX 赛道已勾选
- [x] 项目描述里**没有**夸大实盘收益（我们的卖点是决策质量 + 可验证性）

---

## 关于"线上可访问 demo"

如果提交表单要求一个能公开访问的 URL（localhost 不算），最省事的方案：

| 方案 | 成本 | 说明 |
|---|---|---|
| **Cloudflare Pages / Netlify** | 免费 | 只部署 `frontend/`（静态），但 API 也需要公网地址 |
| **把 API 也部署**（Railway / Render / Fly.io） | 免费额度 | 后端要常驻跑 agent，免费额度可能不够 |
| **CloudStudio 一键部署** | 免费 | 本环境自带 skill：`cloudstudio-deploy` |

**最省事的做法**：先只传视频 + 仓库。多数黑客松接受"本地运行 + 视频演示"，只有进入决赛才需要线上环境。真需要部署时叫我，我用 CloudStudio 给你整套搬上去。
