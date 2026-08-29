# Demo 视频分镜脚本

**目标时长**：3–4 分钟（黑客松评委平均只看前 90 秒，前 60 秒必须把最强证据亮出来）
**录制工具**：

| 工具 | 说明 |
|---|---|
| **OBS Studio**（推荐） | 免费，https://obsproject.com ，可录窗口 + 麦克风 |
| Windows Game Bar | `Win + G` 直接录，零安装，但只能录单个窗口 |
| Loom | 在线录屏，免费版有 5 分钟限制 |

---

## 录前准备（2 分钟）

```powershell
# 终端 1：后端（端口 8000）
cd D:\WorkBuddy\bnb-build-the-era\backend
D:\WorkBuddy\bnb-build-the-era\.venv\Scripts\python.exe main.py

# 终端 2：前端（端口 5173）
cd D:\WorkBuddy\bnb-build-the-era\frontend
C:\Users\John\.workbuddy\binaries\python\versions\3.13.12\python.exe -m http.server 5173 --bind 127.0.0.1
```

确认浏览器打开 `http://localhost:5173` 能看到数据（四类卡片都有数字，不是 "awaiting first cycle"）。

> 建议录前先点一次页面右上角 **Refresh**，确保数据是最新一轮。

---

## 分镜

### 镜头 1 — 开场 · 市场首页（0:00–0:30）

**画面**：浏览器全屏 `http://localhost:5173`，从顶部缓慢滚到四类卡片区。

**旁白要点**：
> 这是 BNB Agent Studio Marketplace —— 一个建在 BNB Smart Chain 上的 AI agent 市场。
> 它的核心问题是：BSC 上有 20 万个注册 agent，但没有一个地方能找到、比较、雇用它们。
> 更麻烦的是——官方要求的四类金融 agent，链上一个都没有。

**关键动作**：鼠标划过四类卡片，让评委看到四张卡片**信息密度一样**（不是一详三略）。

---

### 镜头 2 — 杀手锏 · Health Factor（0:30–1:15）⭐ 最重要

**画面**：点 **Health Factor Monitoring** 卡片 → 详情弹窗。

**旁白要点**：
> 这个 agent 正在监控一个真实仓位——一千一百万美元。
> 抵押 1110 万，借款 833 万，健康因子 1.0991，已经进入 CRITICAL。
> 它不只报警，它直接给出两条恢复路径的精确金额：
> 还款 375 万，或者补抵押 909 万。
>
> 人要做这件事，得枚举每个市场、调预言机、取抵押因子、解方程——
> 在一个算错就损失八位数的仓位上。它一轮就出结果，每轮都出。

**关键动作**：鼠标指向 `health_factor: 1.0991` 和 `option_a_repay_usd` 两个数字，停留 2 秒。

> 💡 **这一段是整个提交的胜负手**，语速放慢，数字念清楚。

---

### 镜头 3 — 另外三类（1:15–2:00）

**画面**：依次点开 **Grid Trading** → **Yield Optimisation** → **Rebalancing**，每个停 12–15 秒。

**旁白要点**：

- **Grid Trading（silent-martin）**
  > 这是 silent-martin 的 BSC 移植版——原版已经过了 Hummingbot Botcamp 的官方认证。
  > 它不按 CEX 中间价报价，而是锚定链上池子价格；
  > 现在 DEX 687.32、CEX 687.4，背离 1.22 个基点，
  > 报价价差按 ATR 波动率自动放到 26 个基点，挂出 6 个网格单。

- **Yield Optimisation（yieldpilot）**
  > BSC 上有 636 个池子，但排前面的全是噪音——两万四千个点的 APY，池子才一万六千美元。
  > 它先用 TVL 和 APY  sanity bound 过滤，得到 49 个真候选，
  > 再按 APY × 稳定性 × 流动性打分——稳定性会惩罚那些 APY 刚从自己 30 天均值跳起来的池子。

- **Rebalancing（rangeguard）**
  > V3 的 LP 一旦脱离价格区间，就既不赚手续费、又变成单边裸多头。
  > 它盯着链上 tick，在价格贴到边界 2% 以内就提前预警。
  > 实测抓到过 QQQB/USDC 的仓位只剩 0.15% 的余量。

---

### 镜头 4 — 链上索引 · 103 个 agent（2:00–2:35）

**画面**：滚到 **On-chain agents** 区，在搜索框敲一个词（比如 `crypto`），展示筛选。

**旁白要点**：
> 市场还索引了 ERC-8004 注册表里真实的链上 agent——这一轮抓到 103 个。
> 但分类结果很说明问题：四大金融类，**一个都没有**；103 个全是通用 agent——
> 写代码的、做设计的、做研究的。
>
> 我们没有把这些通用 agent 硬塞进金融分类里充数。
> 四类是我们自己建的：真实读链、真实风控、真实输出决策。

---

### 镜头 5 — Hire 端到端闭环（2:35–3:05）

**画面**：回到任一类别详情 → 滚到底部 **Hire this agent** → 填 `1000` → 点 **Hire agent**。

**旁白要点**：
> 雇用流程是通的：选 agent、填额度、确认。
> 现在是 demo 模式不动真钱，生产路径接 Binance 的 x402 支付。

---

### 镜头 6 — 收尾 · 证明数据是真的（3:05–3:30）

**画面**：切到终端，跑一条 curl，展示 API 返回原始 JSON。

```bash
curl http://127.0.0.1:8000/api/reference-agents/health_factor
```

**旁白要点**：
> 最后——报告里每个数字都可以自己验。
> 这条 API 返回的就是刚才那个健康因子的原始数据。
> 没有截图，没有 mock，链上读什么，这里就是什么。

**结尾字幕**（3 秒）：
```
BNB Agent Studio Marketplace
Build the Era · BNB Smart Chain · chainId 56
```

---

## 录制检查清单

录完逐条对照，别急着传：

- [ ] 四类卡片**都出现了真实数字**（不是 "awaiting first cycle"）
- [ ] Health Factor 的 `1.0991` 和两个金额**清晰可读**（这是得分点）
- [ ] 前 60 秒就把 Health Factor 亮出来了（评委可能只看开头）
- [ ] 鼠标移动不要太快，关键数字停 2 秒
- [ ] 没有暴露私钥、API key 等敏感信息（录制前清屏或换终端窗口）
- [ ] 画面 1080p，音量清晰（有旁白就配字幕）

---

## 导出

- 格式：MP4（H.264），1080p
- 时长：控制在 4 分钟内
- 上传：YouTube / Bilibili 非公开链接，或按提交表单要求上传文件
