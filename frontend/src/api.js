/**
 * API 客户端
 *
 * 所有数据来自 FastAPI 后端(backend/main.py), 后端再读链 / 跑 agent,
 * 前端不做任何链上调用, 保证展示的数据与 agent 真实状态一致。
 */

// 零构建模式: 直连 FastAPI 后端(后端已开 CORS, 无需 Vite proxy)
const BASE =
  (typeof window !== 'undefined' && window.__API_BASE__) ||
  'http://127.0.0.1:8000/api'

async function fetchJSON(path) {
  try {
    const res = await fetch(`${BASE}${path}`)
    if (!res.ok) {
      throw new Error(`API ${path} failed: ${res.status}`)
    }
    return res.json()
  } catch (err) {
    // 离线 fallback: CloudStudio 纯静态部署无后端时, 回退读本地真实链上快照
    const localPath = '/data' + path + '.json'
    try {
      const r2 = await fetch(localPath)
      if (!r2.ok) throw new Error(`local ${localPath} ${r2.status}`)
      console.warn(`[api] 后端不可用, 使用本地快照: ${localPath}`)
      return r2.json()
    } catch (e2) {
      throw err
    }
  }
}

export function buildQuery(params = {}) {
  const usp = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') usp.append(k, v)
  })
  const qs = usp.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  health: () => fetchJSON('/health'),

  /** 官方四大类别 + 各类别覆盖统计 */
  categories: () => fetchJSON('/categories'),

  /** 本项目自建的四类 reference agent 实时状态 */
  referenceAgents: () => fetchJSON('/reference-agents'),

  /** 单个类别的 reference agent */
  referenceAgent: (category) => fetchJSON(`/reference-agents/${category}`),

  /** 链上索引的 ERC-8004 agent 列表 */
  agents: (params = {}) => fetchJSON(`/agents${buildQuery(params)}`),

  /** 单个链上 agent 详情 */
  agent: (agentId) => fetchJSON(`/agents/${agentId}`)
}

export default api
