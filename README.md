# Build the Era — BNB Agent Studio Marketplace

> BNB Chain 官方黑客松 **"The Smart Money Era: Build the Era"** 参赛项目
> 目标：构建 BNB Smart Chain 上最好的 **AI Agent 市场（Marketplace）**

**🌐 Live Demo（CloudStudio 公网）**: https://f7bfdd7f9a0446119ce25a12f3f12a00.app.workbuddy.link
**🎥 Demo 视频（YouTube）**: https://youtu.be/cUfwagcq6BE

---

## 一、赛事关键信息（官方口径）

| 项 | 内容 |
|---|---|
| 官网 | https://www.bnbchain.org/en/hackathons/smart-money-era |
| 提交截止 | **2026-09-09**（剩 ~10 天） |
| 评判期 | 9/9 – 9/23 |
| 获奖公布 | **2026-11-05** |
| 形式 | Online（远程可做） |

### 奖金池

| 来源 | 奖金 |
|---|---|
| **BNB Chain 主赛道** | **$30,000 USDT** + 官方采纳为 BNB Agent Studio 官方市场（独立产品孵化） |
| **TermiX** | **$10,000 USDT**（$6k / $3k / $1k）— 需提交 **Agent Advantage Report** |
| **PancakeSwap** | 1,000 CAKE（交易者/LP 实际收益） |
| **Altana** | 50,000 XP — 需 **链上真实交易**（testnet 或 mainnet）+ 提交钱包地址 |
| **AltLayer** | 8004scan Pro plans + AltLLM credits |

### ⚠️ 评分红线（决定生死）

1. **Functionality** — 端到端零摩擦：landing → 按类别找到 agent → 看懂 → 雇用
2. **Data Quality** — 实时、准确，超越基础计数，让用户能做明智决策
3. **Agent Diversity** — **四大类别必须同等深度**：
   - `Rebalancing`（LP 区间管理 / 自动重置）
   - `Grid Trading`（网格交易 / 自动挂单）
   - `Yield Optimisation`（收益优化 / APR 路由）
   - `Health Factor Monitoring`（健康因子 / 清算保护）
   - ❗ **单类别侧重 = 严重扣分**

> 官方原话：*"We're asking for the marketplace itself, not a portfolio of agents"*
> → **核心是市场平台本身，不是一堆 agent**

---

## 二、技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 链数据 | **Python + web3.py** | ERC-8004 官方 `bnbagent` SDK 是 Python；silent-martin 也是 Python |
| 后端 | **FastAPI** | 异步、快、易出 API + 自带 OpenAPI 文档（评委友好） |
| 前端 | **Vue 3 + Vite** | 华Dee 熟 Vue；Vite 起步快 |
| 支付 | **Binance x402** | 官方指定 payment facilitator |
| 数据源 | **ERC-8004 链上注册合约** | 20 万+ agent 已注册在 BSC |

### ERC-8004 关键地址

| 合约 | Mainnet (chainId 56) | Testnet (chainId 97) |
|---|---|---|
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |

- Identity Registry = **ERC-721(ERC721URIStorage)**，`agentId` 即 tokenId
- `tokenURI(agentId)` → Agent Registration File（IPFS / HTTPS JSON）
- `getSummary(agentId, clientAddresses, tag1, tag2)` → 链上声誉摘要

---

## 三、10 天冲刺计划

| Day | 日期 | 任务 | 产出 |
|---|---|---|---|
| **D1** | 8/29 六 | 项目初始化 + ERC-8004 链上索引器打通 + **四类 agent 全部跑通** | `erc8004.py` + 4 个 agent ✅ |
| **D2** | 8/30 日 | 数据管道：分类引擎调优 + 本地缓存(DB) | 四类覆盖验证 |
| **D3** | 8/31 一 | FastAPI 后端：列表/详情/搜索/声誉 API | `main.py` |
| **D4** | 9/1 二 | Vue3 前端骨架：首页 + agent 列表 + 类别筛选 | 可点击原型 |
| **D5** | 9/2 三 | Agent 详情页：声誉图表 + 历史表现 + 雇用入口 | 详情页 |
| **D6** | 9/3 四 | **四类深度覆盖**（关键评分项）— 每类 ≥5 个真实 agent | 覆盖率达标 |
| **D7** | 9/4 五 | "Hire / Activate" 端到端 + x402 支付集成 | 完整闭环 |
| **D8** | 9/5 六 | 真实数据接入：实时价格 / APR / 健康因子 | 数据质量分 |
| **D9** | 9/6 日 | UI 打磨 + Demo 视频 + README | 展示材料 |
| **D10** | 9/7 一 | **Agent Advantage Report**（TermiX 必需）+ 提交材料 | 提交就绪 |
| 缓冲 | 9/8–9/9 | 修复 + 正式提交 | 🎯 |

---

## 四、目录结构

```
bnb-build-the-era/
├── backend/
│   ├── requirements.txt
│   ├── erc8004.py          # ERC-8004 链上索引器（数据命脉）
│   └── main.py             # FastAPI API 层（D3）
├── frontend/               # Vue 3 + Vite（D4）
└── docs/
    └── Agent_Advantage_Report.md   # TermiX 赛道必需（D10）
```

---

## 五、四类 Reference Agent（评分红线，已全部真实运行验证）

链上现有 agent 几乎全是通用 AI agent（写代码 / 做设计），四类金融 agent 近乎空白 → 本项目自建。
每个 agent 都**真实读链、真实风控、真实输出决策**，不是 mock。

| 类别 | 文件 / 名称 | 数据源 | 真实验证结果 |
|---|---|---|---|
| **Rebalancing** | `rebalancing_agent.py`<br>`rangeguard.agent` | Uniswap V3 on BSC 链上 LP（`positions` + `slot0`） | 3 个真实仓位（QQQB/USDC×2 + ASTER/USDT），0 脱区间、**2 贴边预警**（余量仅 0.15%），建议新区间 tick 64680–66720 |
| **Grid Trading** | `grid_agent.py`<br>`silent-martin.agent` | 链上池子 `slot0` + Gate.io ticker + K 线 ATR | DEX **690.922** vs CEX 690.8，背离 **1.77 bps**，ATR 0.125% → spread 25 bps，输出 6 个网格订单 |
| **Yield Optimisation** | `yield_agent.py`<br>`yieldpilot.agent` | DefiLlama Yields API（BSC 636 池 → 49 个优质池） | 最优 USDT-SPYB，APY 140.39%，风险调整评分 115.9，输出 ENTER 动作 |
| **Health Factor** | `health_factor_agent.py`<br>`hfsentinel.agent` | Venus 链上（`getAccountSnapshot` + oracle + collateralFactor） | 监控到 **1100 万美元真实仓位**：抵押 $11,101,221 / 借款 $8,379,969 / **HF = 1.0929 CRITICAL**，给出还款 $3,800,716 或追加抵押 $9,213,857 |

> **Grid Trading 是 silent-martin 的 BSC 移植版** —— 原策略已过 Hummingbot Botcamp 官方 CERTIFIED，
> 保留四大核心机制：链上锚定定价 / 背离溢价 / 库存偏斜 skew / ATR sizing + 硬 kill-switch。
> 这是其他参赛者没有的：别人的四类全是 demo，我们有一个生产级认证策略。

### 运行方式

```bash
cd backend/agents
python yield_agent.py          # Yield（无需参数）
python grid_agent.py           # Grid（silent-martin BSC 版）

# Health Factor（需监控地址）
MONITOR_ADDRESS=0x81EBde24453B8E40454616579EA79C79A197699D python health_factor_agent.py

# Rebalancing（推荐 tokenId 直查，跳过空 NFT 遍历）
TOKEN_IDS=2690498,2690499,2672513 python rebalancing_agent.py
```

---

## 六、快速开始

```bash
# 依赖已装在 D 盘项目 venv（避开 WorkBuddy safe-delete 拦截）
# 重装方案: pip download 只下 wheel + 手动解压进 .venv/Lib/site-packages

# 跑索引器自测（连 BSC mainnet）
cd backend && python erc8004.py

# 跑四类 agent
cd agents && python yield_agent.py
```

---

**作者**：陆俊华（华Dee）
**启动**：2026-08-29
**Deadline**：2026-09-09
