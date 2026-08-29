import { ref, onMounted } from 'vue'
import api from './api.js'
import CategoryCard from './components/CategoryCard.js'
import AgentDetail from './components/AgentDetail.js'

export default {
  name: 'App',
  components: { CategoryCard, AgentDetail },

  setup() {
    const categories = ref([])
    const agents = ref([])
    const loading = ref(true)
    const error = ref('')
    const agentsError = ref('')
    const search = ref('')
    const filterCategory = ref('')
    const selected = ref(null)
    const selectedChainAgent = ref(null)
    const stats = ref({})

    let searchTimer = null

    /** 合并 /categories 与 /reference-agents 两份数据 */
    async function loadCategories() {
      const [catRes, refRes] = await Promise.all([
        api.categories(),
        api.referenceAgents()
      ])

      const refByCat = {}
      ;(refRes.agents || []).forEach((a) => {
        refByCat[a.category] = a
      })

      categories.value = Object.entries(catRes.categories || {}).map(([key, meta]) => ({
        key,
        label: meta.label,
        description: meta.description,
        referenceAgent: meta.reference_agent,
        status: meta.reference_agent_status,
        onchainIndexed: meta.onchain_indexed,
        live: refByCat[key] || null
      }))

      stats.value = {
        onchainTotal: catRes.onchain_total,
        referenceAgents: refRes.total
      }
    }

    async function loadAgents() {
      agentsError.value = ''
      try {
        const res = await api.agents({
          category: filterCategory.value,
          q: search.value,
          limit: 50
        })
        agents.value = res.agents || []
      } catch (e) {
        agentsError.value = `Failed to load on-chain agents: ${e.message}`
      }
    }

    function debouncedLoadAgents() {
      clearTimeout(searchTimer)
      searchTimer = setTimeout(loadAgents, 350)
    }

    async function loadAll() {
      loading.value = true
      error.value = ''
      try {
        await Promise.all([loadCategories(), loadAgents()])
      } catch (e) {
        error.value = `Failed to load data: ${e.message}`
      } finally {
        loading.value = false
      }
    }

    function openDetail(cat) {
      selected.value = cat
      selectedChainAgent.value = null
    }
    function openChainAgent(agent) {
      selectedChainAgent.value = agent
      selected.value = null
    }
    function closeDetail() {
      selected.value = null
      selectedChainAgent.value = null
    }

    onMounted(loadAll)

    return {
      categories,
      agents,
      loading,
      error,
      agentsError,
      search,
      filterCategory,
      selected,
      selectedChainAgent,
      stats,
      debouncedLoadAgents,
      loadAgents,
      loadAll,
      openDetail,
      openChainAgent,
      closeDetail
    }
  },

  template: `
  <div>
    <header class="header">
      <div class="container header-inner">
        <div class="logo">
          <div class="logo-mark">B</div>
          <div>BNB Agent Studio <span>Marketplace</span></div>
        </div>
        <div class="header-stats">
          <div class="hstat">
            <div class="hstat-value">{{ stats.onchainTotal ?? '—' }}</div>
            <div class="hstat-label">On-chain agents</div>
          </div>
          <div class="hstat">
            <div class="hstat-value">{{ stats.referenceAgents ?? '—' }}</div>
            <div class="hstat-label">Reference agents</div>
          </div>
          <div class="hstat">
            <div class="hstat-value">56</div>
            <div class="hstat-label">Chain ID</div>
          </div>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="container">
        <h1>Find, compare and hire AI agents on BNB Chain</h1>
        <p>
          One venue to browse agents registered under ERC-8004, see how they actually
          perform on-chain, and put them to work in a few clicks.
        </p>
        <div class="hero-badges">
          <span class="badge badge-accent">Build the Era Hackathon</span>
          <span class="badge">ERC-8004 Trustless Agents</span>
          <span class="badge">BNB Smart Chain</span>
          <span class="badge badge-green">Live on-chain data</span>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div class="section-head">
          <div>
            <h2 class="section-title">Reference agents</h2>
            <div class="section-sub">
              Built by us, running live on BSC — all four categories covered at equal depth
            </div>
          </div>
          <button class="btn btn-ghost" @click="loadAll" :disabled="loading">Refresh</button>
        </div>

        <div v-if="error" class="error-box">{{ error }}</div>

        <div v-if="loading && !categories.length" class="loading">Loading agents…</div>
        <div v-else class="cat-grid">
          <CategoryCard
            v-for="cat in categories"
            :key="cat.key"
            :cat="cat"
            @select="openDetail(cat)"
          />
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div class="section-head">
          <div>
            <h2 class="section-title">On-chain agents</h2>
            <div class="section-sub">
              Indexed from the ERC-8004 Identity Registry on BSC
            </div>
          </div>
        </div>

        <div class="filters">
          <input
            class="input"
            v-model="search"
            @input="debouncedLoadAgents"
            placeholder="Search agents by name or description…"
          />
          <select class="select" v-model="filterCategory" @change="loadAgents">
            <option value="">All categories</option>
            <option v-for="cat in categories" :key="cat.key" :value="cat.key">
              {{ cat.label }}
            </option>
          </select>
        </div>

        <div v-if="agentsError" class="error-box">{{ agentsError }}</div>
        <div v-else-if="!agents.length" class="empty">No on-chain agents indexed yet.</div>

        <table v-else class="agent-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Description</th>
              <th>Category</th>
              <th>ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in agents" :key="a.agent_id" @click="openChainAgent(a)" style="cursor:pointer">
              <td class="agent-name-cell">{{ a.name || '(unnamed)' }}</td>
              <td class="agent-desc-cell">{{ (a.description || '').slice(0, 110) || '—' }}</td>
              <td><span class="badge">{{ a.category_label }}</span></td>
              <td class="mono">{{ a.agent_id }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      <div class="container">
        BNB Agent Studio Marketplace · Build the Era hackathon submission ·
        Data read live from BNB Smart Chain (chainId 56)
      </div>
    </footer>

    <AgentDetail
      v-if="selected || selectedChainAgent"
      :category="selected"
      :chain-agent="selectedChainAgent"
      @close="closeDetail"
    />
  </div>
  `
}
