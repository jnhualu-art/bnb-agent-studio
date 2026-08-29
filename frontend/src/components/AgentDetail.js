import { ref, computed } from 'vue'

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
  name: 'AgentDetail',

  props: {
    category: { type: Object, default: null },
    chainAgent: { type: Object, default: null }
  },

  emits: ['close'],

  setup(props) {
    const hired = ref(false)
    const allocation = ref('1000')

    const live = computed(() => props.category?.live || null)
    const state = computed(() => live.value?.state || null)
    const metrics = computed(() => state.value?.metrics || {})
    const actions = computed(() => state.value?.actions || [])
    const orders = computed(() => (actions.value[0] && actions.value[0].orders) || [])

    const statusText = computed(() => props.category?.status || 'pending')

    const statusClass = computed(() => {
      switch (props.category?.status) {
        case 'running': return 'badge-green'
        case 'halted':
        case 'error': return 'badge-red'
        default: return ''
      }
    })

    /** 按类别展开指标卡片 */
    const metricCards = computed(() => {
      const m = metrics.value
      if (!m || !Object.keys(m).length) return []

      switch (props.category?.key) {
        case 'grid_trading':
          return [
            { label: 'Fair price', display: '$' + fmt(m.fair_price) },
            { label: 'DEX price', display: '$' + fmt(m.dex_price) },
            { label: 'CEX price', display: '$' + fmt(m.cex_price) },
            { label: 'Dislocation', display: fmt(m.dislocation_bps, 2) + ' bps' },
            { label: 'ATR', display: fmt(m.atr_pct, 3) + '%' },
            { label: 'Spread', display: fmt(m.spread_bps, 1) + ' bps' },
            { label: 'Bid', display: '$' + fmt(m.bid), tone: 'good' },
            { label: 'Ask', display: '$' + fmt(m.ask), tone: 'bad' },
            { label: 'Inventory ratio', display: fmt(m.inventory_ratio, 3) },
            { label: 'Skew', display: fmt(m.skew_bps, 1) + ' bps' }
          ]

        case 'yield_optimisation':
          return [
            { label: 'Best APY', display: fmt(m.best_apy, 2) + '%', tone: 'good' },
            { label: 'Best pool', display: m.best_pool || '—', tone: 'good' },
            { label: 'Best project', display: m.best_project || '—' },
            { label: 'Risk-adj score', display: fmt(m.best_score, 2) },
            { label: 'Candidates', display: String(m.candidates ?? '—') },
            { label: 'Current pool', display: m.current_pool || 'none' }
          ]

        case 'health_factor': {
          const hf = m.health_factor
          const tone =
            hf === null || hf === undefined ? '' :
            hf <= 1.0 ? 'bad' :
            hf < 1.15 ? 'bad' :
            hf < 1.5 ? 'warn' : 'good'
          return [
            { label: 'Health factor', display: fmt(hf, 4), tone },
            {
              label: 'Risk level',
              display: m.risk_level || '—',
              tone: m.risk_level === 'CRITICAL' ? 'bad' : m.risk_level === 'WARN' ? 'warn' : 'good'
            },
            { label: 'Supply', display: '$' + fmt(m.supply_usd, 0) },
            { label: 'Borrow', display: '$' + fmt(m.borrow_usd, 0), tone: 'warn' },
            { label: 'Weighted collateral', display: '$' + fmt(m.weighted_collateral_usd, 0) },
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
          return Object.entries(m).map(([k, v]) => ({
            label: k.replace(/_/g, ' '),
            display: fmt(v)
          }))
      }
    })

    function hire() {
      hired.value = true
    }

    return {
      hired,
      allocation,
      live,
      actions,
      orders,
      statusText,
      statusClass,
      metricCards,
      hire
    }
  },

  template: `
  <div class="detail-overlay" @click.self="$emit('close')">
    <div class="detail-panel">

      <!-- ===== 链上 agent 详情 ===== -->
      <template v-if="chainAgent">
        <div class="detail-head">
          <div>
            <div class="detail-title">{{ chainAgent.name || '(unnamed agent)' }}</div>
            <div class="detail-sub">
              ERC-8004 agent #{{ chainAgent.agent_id }} · registered at block
              {{ chainAgent.registered_at_block }}
            </div>
          </div>
          <button class="close-btn" @click="$emit('close')">&times;</button>
        </div>

        <p style="color: var(--text-muted); margin-bottom: 20px">
          {{ chainAgent.description || 'No description provided.' }}
        </p>

        <div class="detail-grid">
          <div class="detail-metric">
            <div class="dm-label">Category</div>
            <div class="dm-value" style="font-size: 14px">{{ chainAgent.category_label }}</div>
          </div>
          <div class="detail-metric">
            <div class="dm-label">Agent ID</div>
            <div class="dm-value" style="font-size: 14px">{{ chainAgent.agent_id }}</div>
          </div>
          <div class="detail-metric">
            <div class="dm-label">Services</div>
            <div class="dm-value" style="font-size: 14px">
              {{ (chainAgent.services || []).length }}
            </div>
          </div>
        </div>

        <div v-if="(chainAgent.services || []).length" style="margin-bottom: 20px">
          <div class="dm-label" style="margin-bottom: 8px">Endpoints</div>
          <div
            v-for="s in chainAgent.services"
            :key="s.name"
            class="mono"
            style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px"
          >
            <strong style="color: var(--text)">{{ s.name }}</strong> — {{ s.endpoint }}
          </div>
        </div>

        <div class="hire-box">
          <div style="font-weight: 600; margin-bottom: 6px">Hire this agent</div>
          <div class="hire-note">
            Registration file resolved from
            <span class="mono">{{ chainAgent.agent_uri || '—' }}</span>
          </div>
          <button class="btn" style="margin-top: 12px" @click="hire">
            Connect wallet to hire
          </button>
          <div class="hire-note">
            Demo build — wallet settlement via Binance x402 is not enabled yet.
          </div>
        </div>
      </template>

      <!-- ===== Reference agent 详情 ===== -->
      <template v-else-if="category">
        <div class="detail-head">
          <div>
            <div class="detail-title">{{ category.label }}</div>
            <div class="detail-sub">
              {{ category.referenceAgent }} · {{ category.description }}
            </div>
          </div>
          <button class="close-btn" @click="$emit('close')">&times;</button>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap">
          <span class="badge badge-accent">live on BSC</span>
          <span class="badge" :class="statusClass">{{ statusText }}</span>
          <span v-if="live && live.network" class="badge">{{ live.network }}</span>
          <span v-if="live && live.dry_run" class="badge badge-blue">dry-run (no real orders)</span>
        </div>

        <div v-if="metricCards.length" class="detail-grid">
          <div v-for="m in metricCards" :key="m.label" class="detail-metric">
            <div class="dm-label">{{ m.label }}</div>
            <div class="dm-value" :class="m.tone">{{ m.display }}</div>
          </div>
        </div>
        <div v-else class="empty" style="padding: 24px">
          First cycle still running — data will appear shortly.
        </div>

        <div v-if="actions.length" style="margin-bottom: 20px">
          <div class="dm-label" style="margin-bottom: 8px">
            Current decision ({{ actions.length }})
          </div>
          <div
            v-for="(a, i) in actions"
            :key="i"
            style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 8px;"
          >
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
              <strong style="font-size: 13px">{{ a.type }}</strong>
              <span class="badge" :class="a.priority === 'HIGH' ? 'badge-red' : ''">
                {{ a.priority || 'NORMAL' }}
              </span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted)">
              {{ a.reason || a.notes || '—' }}
            </div>
          </div>
        </div>

        <div v-if="orders.length">
          <div class="dm-label" style="margin-bottom: 8px">
            Live grid quotes ({{ orders.length }})
          </div>
          <table class="orders-table">
            <thead>
              <tr><th>Side</th><th>Level</th><th>Price</th><th>Size</th></tr>
            </thead>
            <tbody>
              <tr v-for="(o, i) in orders" :key="i">
                <td :class="o.side === 'BUY' ? 'side-buy' : 'side-sell'">{{ o.side }}</td>
                <td>{{ o.level }}</td>
                <td>{{ o.price }}</td>
                <td>{{ o.size }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="hire-box">
          <div style="font-weight: 600; margin-bottom: 6px">Hire this agent</div>
          <div class="hire-note">
            This agent runs continuously against live BSC state and publishes its
            decisions through this marketplace.
          </div>

          <div v-if="!hired" style="margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap">
            <input
              class="input"
              style="min-width: 180px"
              v-model="allocation"
              placeholder="Allocation (USD)"
            />
            <button class="btn" @click="hire" :disabled="!allocation">Hire agent</button>
          </div>

          <div v-else style="margin-top: 12px">
            <div class="badge badge-green" style="margin-bottom: 8px">
              Agent hired — allocation ${{ allocation }} (demo mode)
            </div>
            <div class="hire-note">
              In demo mode no funds move. Production path: Binance x402 payment
              facilitator → agent activation on BSC.
            </div>
          </div>
        </div>
      </template>

    </div>
  </div>
  `
}
