<script setup lang="ts">
import { onMounted, ref } from 'vue'

// Mission 一覧（FE-02）。設計指示書 § 6 `GET /api/missions/`。
definePageMeta({ middleware: 'auth' })

interface MissionSummary {
  id: number
  title: string
  title_ja: string
  status: 'cleared' | 'open' | 'locked'
}

const { apiFetch } = useApi()
const { logout } = useAuth()
const router = useRouter()
const store = useTerminalStore()

const missions = ref<MissionSummary[]>([])
const loading = ref(true)
const error = ref('')

const STATUS_LABEL: Record<MissionSummary['status'], string> = {
  cleared: 'クリア済み',
  open: '着手可能',
  locked: '未開放',
}

onMounted(async () => {
  try {
    missions.value = await apiFetch<MissionSummary[]>('/api/missions/')
  } catch {
    error.value = 'Error: failed to load missions'
  } finally {
    loading.value = false
  }
})

function open(m: MissionSummary) {
  if (m.status === 'locked') return
  router.push(`/missions/${m.id}`)
}

function onLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div>
        <p class="tag">CLI_Noir</p>
        <h1>捜査ファイル一覧</h1>
      </div>
      <NoirButton variant="ghost" @click="onLogout">ログアウト</NoirButton>
    </header>

    <p v-if="loading" class="hint">読み込み中…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>

    <ul v-else class="grid">
      <li
        v-for="m in missions"
        :key="m.id"
        class="card"
        :class="m.status"
        @click="open(m)"
      >
        <span class="num">Mission {{ m.id }}</span>
        <h2>{{ m.title }}</h2>
        <p class="ja">{{ m.title_ja }}</p>
        <div class="status-row">
          <span class="status" :class="m.status">{{ STATUS_LABEL[m.status] }}</span>
          <span v-if="store.activeMissionId === m.id" class="status active">捜査中</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-app-deep);
  padding: var(--space-6);
}
.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}
.tag {
  margin: 0;
  font-family: var(--font-accent);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  font-size: var(--text-xs);
  color: var(--brass-400);
}
h1 {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  color: var(--text-body);
}
.hint {
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.hint.error {
  color: var(--term-error);
}
.grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}
.card {
  background: var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900));
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-panel), var(--glow-indigo);
}
.card.locked {
  cursor: not-allowed;
  filter: grayscale(0.6);
  opacity: 0.6;
}
.card.locked:hover {
  transform: none;
  box-shadow: var(--shadow-panel), var(--bezel-brass);
}
.num {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--brass-400);
  letter-spacing: var(--tracking-caps);
}
h2 {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--text-body);
}
.ja {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.status-row {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.status {
  align-self: flex-start;
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  color: var(--text-faint);
}
.status.cleared {
  color: var(--term-success);
  border-color: var(--term-success);
}
.status.open {
  color: var(--accent-quiet);
  border-color: var(--accent);
}
.status.active {
  color: var(--brass-400);
  border-color: var(--brass-600);
}
</style>
