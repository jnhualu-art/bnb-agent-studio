import { computed } from 'vue'

const ICONS = {
  rebalancing: '⟳',
  grid_trading: '▤',
  yield_optimisation: '↑',
  health_factor: '◈'
}

function fmt(v, digits = 2) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`
    if (Math.abs(v) >= 1e3) return v.toLocaleString('en-US', { maximumFractionDigits: 0 })
    return v.toFixed(digits)
  }
  return String(v)
}

export default {
  name: 'CategoryCard',

  props: {
    cat: { type: Object, required: true }
  },

  emits: ['select'],

  setup(props) {
    const icon = computed(() => ICONS[props.cat.key] || '◆')

    const statusText = computed(() => props.cat.status || 'pending')

    const statusClass = computed(() => {
      switch (props.cat.status) {
        case 'running': return 'badge-green'
        case 'halted': return 'badge-red'
        case 'error': return 'badge-red'
        default: return ''
      }
    })

    /** 按类别提取关键指标 — 保证四类展示深度一致(各 4 项) */
    const metrics = computed(() => {
      const live = props.cat.live
      if (!live || !live.state || !live.state.metrics) return []
      const m = live.state.metrics
      const s = live.state

      switch (props.cat.key) {
        case 'grid_trading':
          return [
            { label: 'Fair price', display: '$' + fmt(m.fair_price) },
            { label: 'Spread', display: fmt(m.spread_bps, 1) + ' bps' },
            { label: 'DEX/CEX gap', display: fmt(m.dislocation_bps, 2) + ' bps' },
            { label: 'Grid orders', display: String((s.actions && s.actions[0] && s.actions[0].orders) ? s.actions[0].orders.length : 0) }
          ]

        case 'yield_optimisation':
          return [
            { label: 'Best APY', display: fmt(m.best_apy, 2) + '%', tone: 'good' },
            { label: 'Pool', display: m.best_pool || '—' },
            { label: 'Candidates', display: String(m.candidates ?? '—') },
            { label: 'Risk-adj score', display: fmt(m.best_score, 1) }
          ]

        case 'health_factor': {
          const hf = m.health_factor
          const tone =
            hf === null || hf === undefined ? '' :
            hf <= 1.0 ? 'bad' :
            hf < 1.15 ? 'bad' :
            hf < 1.5 ? 'warn' : 'good'
          return [
            { label: 'Health factor', display: fmt(hf, 3), tone },
            {
              label: 'Risk level',
              display: m.risk_level || '—',
              tone: m.risk_level === 'CRITICAL' ? 'bad' : m.risk_level === 'WARN' ? 'warn' : 'good'
            },
            { label: 'Borrow', display: '$' + fmt(m.borrow_usd, 0) },
            { label: 'Positions', display: String(m.positions ?? '—') }
          ]
        }

        case 'rebalancing':
          return [
            { label: 'LP positions', display: String(m.positions ?? '—') },
            {
              label: 'Out of range',
              display: String(m.out_of_range ?? '—'),
              tone: m.out_of_range > 0 ? 'bad' : 'good'
            },
            {
              label: 'Near edge',
              display: String(m.near_edge ?? '—'),
              tone: m.near_edge > 0 ? 'warn' : 'good'
            },
            { label: 'Healthy', display: String(m.healthy ?? '—'), tone: 'good' }
          ]

        default:
          return []
      }
    })

    return { icon, statusText, statusClass, metrics }
  },

  template: `
  <div class="cat-card" @click="$emit('select')">
    <div class="cat-icon">{{ icon }}</div>
    <div class="cat-name">{{ cat.label }}</div>
    <div class="cat-desc">{{ cat.description }}</div>

    <div class="cat-agent">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="cat-agent-name">{{ cat.referenceAgent || '—' }}</span>
        <span class="badge" :class="statusClass">{{ statusText }}</span>
      </div>

      <div v-if="metrics.length" class="cat-metrics">
        <div v-for="m in metrics" :key="m.label" class="metric-row">
          <span class="metric-label">{{ m.label }}</span>
          <span class="metric-value" :class="m.tone">{{ m.display }}</span>
        </div>
      </div>
      <div v-else class="metric-row" style="margin-top:8px">
        <span class="metric-label">awaiting first cycle…</span>
      </div>

      <div style="margin-top:10px; display:flex; gap:6px; flex-wrap:wrap;">
        <span class="badge badge-accent">live on BSC</span>
        <span v-if="cat.onchainIndexed > 0" class="badge">
          {{ cat.onchainIndexed }} on-chain
        </span>
      </div>
    </div>
  </div>
  `
}
