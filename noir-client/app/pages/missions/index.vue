<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

/*
 * Mission 一覧（FE-02）。設計指示書 § 6 `GET /api/missions/`。
 * 見た目は MissionHeader（60 年代フレンチ映画ポスター: poster black の地・赤の斜め切り抜き・
 * Jost の見出し・Josefin のタグ・brass のチップ）と同じ意匠で組む（2026-09-13 ユーザー指示）。
 * ClaudeDesign 側に mission-list コンポーネントは無いため、ここは既存トークン + MissionHeader の
 * 組み合わせで実装する（トークン・書体の正は ClaudeDesign。docs/design-system/README.md）。
 */
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
  cleared: 'Case Closed',
  open: 'Open',
  locked: 'Sealed',
}

const clearedCount = computed(() => missions.value.filter(m => m.status === 'cleared').length)
const progress = computed(() => (missions.value.length ? `解決 ${clearedCount.value} / ${missions.value.length}` : ''))

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
    <MissionHeader tag="CLI_Noir" title="Case Files" subtitle="捜査ファイル一覧" :rank="progress" />

    <div class="toolbar">
      <p class="lead">
        <template v-if="store.activeMissionId != null">
          捜査中の事件は <span class="lead-strong">Mission {{ store.activeMissionId }}</span>。封印された事件は前の事件を解決すると開く。
        </template>
        <template v-else>
          すべての事件を解決済み。
        </template>
      </p>
      <NoirButton variant="ghost" @click="onLogout">ログアウト</NoirButton>
    </div>

    <p v-if="loading" class="hint">読み込み中…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>

    <ul v-else class="grid">
      <li
        v-for="m in missions"
        :key="m.id"
        class="card"
        :class="[m.status, { active: store.activeMissionId === m.id }]"
        :aria-disabled="m.status === 'locked'"
        @click="open(m)"
      >
        <div class="cutout" aria-hidden="true" />
        <div class="body">
          <span class="tag">Mission {{ m.id }}</span>
          <h2 class="title">{{ m.title }}</h2>
          <span class="sub">{{ m.title_ja }}</span>
          <div class="foot">
            <span class="chip" :class="m.status">{{ STATUS_LABEL[m.status] }}</span>
            <span v-if="store.activeMissionId === m.id" class="chip active">捜査中</span>
          </div>
        </div>
        <span v-if="m.status === 'cleared'" class="stamp" aria-hidden="true">Closed</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-app-deep);
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
}
.lead {
  margin: 0;
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.lead-strong {
  font-family: var(--font-mono);
  color: var(--brass-400);
}
.hint {
  padding: var(--space-6);
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.hint.error {
  color: var(--term-error);
}

/* --- ポスター調カード（MissionHeader の帯をカードに縮めたもの） --- */
.grid {
  list-style: none;
  margin: 0;
  padding: var(--space-6);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
}
.card {
  position: relative;
  overflow: hidden;
  background: var(--hairline-scan), var(--poster-black);
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card), var(--bezel-brass);
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-panel), var(--glow-indigo);
}
.cutout {
  position: absolute;
  top: -20%;
  left: -6%;
  width: 34px;
  height: 140%;
  background: var(--poster-red);
  transform: skewX(-12deg);
  opacity: 0.9;
}
.body {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-4) var(--space-4) var(--space-4) calc(var(--space-4) + 32px);
  min-height: 132px;
}
.tag {
  font-family: var(--font-accent);
  font-weight: var(--weight-medium);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--poster-mustard);
}
.title {
  margin: 0;
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  font-size: var(--text-xl);
  line-height: 1;
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
  color: var(--poster-cream);
}
.sub {
  align-self: flex-start;
  font-family: var(--font-display);
  font-size: var(--text-sm);
  color: var(--poster-red);
  background: var(--poster-black);
  padding: 1px 6px;
  margin-left: -6px;
}
.foot {
  margin-top: auto;
  padding-top: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.chip {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  color: var(--text-faint);
  background: rgba(255, 255, 255, 0.02);
}
.chip.cleared {
  color: var(--term-success);
  border-color: var(--term-success);
}
.chip.open {
  color: var(--accent-quiet);
  border-color: var(--accent);
}
.chip.active {
  color: var(--brass-400);
  border-color: var(--brass-600);
  box-shadow: var(--glow-brass);
  background: rgba(201, 162, 75, 0.06);
}

/* 捜査中の事件: brass の縁取りで一枚だけ光らせる */
.card.active {
  border-color: var(--brass-400);
  box-shadow: var(--shadow-card), var(--bezel-brass), var(--glow-brass);
}

/* 解決済み: 赤いスタンプを斜めに押す（ポスターの "CASE CLOSED"） */
.stamp {
  position: absolute;
  top: 14px;
  right: 12px;
  transform: rotate(-10deg);
  font-family: var(--font-accent);
  font-weight: var(--weight-medium);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--poster-red);
  border: 2px solid var(--poster-red);
  border-radius: 2px;
  padding: 2px 8px;
  opacity: 0.85;
  pointer-events: none;
}
.card.cleared .cutout {
  background: var(--poster-mustard);
  opacity: 0.7;
}

/* 未開放: 色を落として封印されている感じに。クリックはできない */
.card.locked {
  cursor: not-allowed;
  filter: grayscale(0.7);
  opacity: 0.55;
}
.card.locked .cutout {
  background: var(--gray-600);
}
.card.locked .sub {
  color: var(--text-faint);
}
.card.locked:hover {
  transform: none;
  box-shadow: var(--shadow-card), var(--bezel-brass);
}

@media (max-width: 720px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .grid {
    padding: var(--space-4);
    grid-template-columns: 1fr;
  }
}
</style>
