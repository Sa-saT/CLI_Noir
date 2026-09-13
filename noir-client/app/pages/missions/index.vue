<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

/*
 * Mission 一覧（FE-02）。設計指示書 § 6 `GET /api/missions/`。
 * 見た目は DesignSystem の Game Screen（ui_kits/detective-terminal）を参照して組む（2026-09-13 ユーザー指示）:
 *   - ヘッダー = MissionHeader（ポスター帯）そのまま
 *   - 背景 = scene と同じ poster-blue → poster-black のグラデ + mustard の光 + 赤の斜め切り抜き（円形マスク）
 *   - カード = scene-caption の紙（cream の紙に赤いハードシャドウ）。開いている事件だけ紙で、封印中は
 *     暗い封筒（scene-badge の細い cream 枠）にして視線が着手可能な事件へ行くようにする
 *   - 解決済みは赤いゴム印 "CLOSED"（ネット上のスタンプ表現の定番: 2.5rem 前後・3〜4px 枠・-12° 回転・
 *     multiply で紙に沈める）
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
  cleared: '',
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
    <div class="backdrop" aria-hidden="true" />
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
        <div class="body">
          <span class="tag">Mission {{ m.id }}</span>
          <h2 class="title">{{ m.title }}</h2>
          <span class="sub">{{ m.title_ja }}</span>
          <div class="foot">
            <span v-if="STATUS_LABEL[m.status]" class="badge" :class="m.status">{{ STATUS_LABEL[m.status] }}</span>
            <span v-if="store.activeMissionId === m.id" class="badge active">捜査中</span>
          </div>
        </div>
        <span v-if="m.status === 'cleared'" class="stamp" aria-hidden="true">Closed</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
/* --- 背景: DesignSystem の scene と同じ組み立て（poster-blue → black のグラデ + mustard の光 + 赤い切り抜き） --- */
.page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(110% 80% at 70% 25%, rgba(217, 165, 33, 0.20), transparent 55%),
    linear-gradient(155deg, var(--poster-blue) 0%, var(--poster-black) 62%);
  background-attachment: fixed;
  isolation: isolate;
}
.backdrop {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: var(--poster-red);
  /* scene::before と同じ斜めの赤 + 円形の抜き。一覧では主役はカードなので薄く敷く */
  clip-path: polygon(0 0, 34% 0, 22% 100%, 0 100%);
  -webkit-mask-image: radial-gradient(circle at 20% 34%, transparent 0, transparent 12vw, #000 calc(12vw + 1px));
  mask-image: radial-gradient(circle at 20% 34%, transparent 0, transparent 12vw, #000 calc(12vw + 1px));
  opacity: 0.18;
}
.page > * {
  position: relative;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid rgba(242, 232, 213, 0.12);
  background: rgba(20, 16, 12, 0.35);
}
.lead {
  margin: 0;
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--poster-cream);
  opacity: 0.85;
}
.lead-strong {
  font-family: var(--font-mono);
  color: var(--poster-mustard);
}
.hint {
  padding: var(--space-6);
  color: var(--poster-cream);
  font-family: var(--font-mono);
}
.hint.error {
  color: var(--term-error);
}

/* --- カード --- */
.grid {
  list-style: none;
  margin: 0;
  padding: var(--space-6) var(--space-6) var(--space-8, 3rem);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: var(--space-5);
}
.card {
  position: relative;
  min-height: 150px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.body {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-4) var(--space-4) var(--space-3);
}
.tag {
  font-family: var(--font-accent);
  font-weight: var(--weight-semibold);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
}
.title {
  margin: 2px 0 0;
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  font-size: var(--text-xl);
  line-height: 1;
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
}
.sub {
  font-family: var(--font-display);
  font-size: var(--text-sm);
}
.foot {
  margin-top: auto;
  padding-top: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 22px;
}
.badge {
  font-family: var(--font-accent);
  font-weight: var(--weight-semibold);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  padding: 3px 8px 2px;
  border: 1px solid currentColor;
}

/* 開いている事件 = 紙（scene-caption: cream の紙 + 赤いハードシャドウ） */
.card.open,
.card.cleared {
  background: var(--poster-cream);
  color: var(--poster-black);
  box-shadow: 5px 5px 0 var(--poster-red);
}
.card.open .tag,
.card.cleared .tag {
  color: var(--poster-red);
}
.card.open .sub,
.card.cleared .sub {
  color: var(--poster-blue);
}
.card.open:hover,
.card.cleared:hover {
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 var(--poster-red);
}
.badge.open {
  color: var(--poster-red);
}
/* 捜査中の一枚だけ影を mustard にし、黒地のバッジで示す */
.card.active {
  box-shadow: 5px 5px 0 var(--poster-mustard);
}
.card.active:hover {
  box-shadow: 8px 8px 0 var(--poster-mustard);
}
.badge.active {
  color: var(--poster-cream);
  background: var(--poster-black);
  border-color: var(--poster-black);
}

/* 解決済み: 赤いゴム印を斜めに押す */
.card.cleared .title,
.card.cleared .sub {
  opacity: 0.55;
}
.stamp {
  position: absolute;
  top: 50%;
  right: 6%;
  transform: translateY(-50%) rotate(-12deg);
  font-family: var(--font-accent);
  font-weight: var(--weight-bold);
  font-size: clamp(1.9rem, 2.6vw, 2.5rem);
  line-height: 1;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--poster-red);
  border: 4px double var(--poster-red);
  border-radius: 6px;
  padding: 6px 14px 2px;
  opacity: 0.8;
  mix-blend-mode: multiply;
  pointer-events: none;
  /* インクのかすれ: 粗いドットのマスクで所々薄くする */
  -webkit-mask-image: radial-gradient(circle at 30% 40%, #000 0 80%, rgba(0, 0, 0, 0.55) 81%),
    repeating-radial-gradient(circle at 70% 60%, rgba(0, 0, 0, 0.75) 0 2px, #000 3px 5px);
  mask-image: radial-gradient(circle at 30% 40%, #000 0 80%, rgba(0, 0, 0, 0.55) 81%),
    repeating-radial-gradient(circle at 70% 60%, rgba(0, 0, 0, 0.75) 0 2px, #000 3px 5px);
  -webkit-mask-composite: source-in;
  mask-composite: intersect;
}

/* 封印中 = 暗い封筒（scene-badge の細い cream 枠）。視線を着手可能な紙へ */
.card.locked {
  cursor: not-allowed;
  background: rgba(20, 16, 12, 0.55);
  color: var(--poster-cream);
  border: 1px solid rgba(242, 232, 213, 0.22);
  box-shadow: none;
}
.card.locked .tag {
  color: rgba(242, 232, 213, 0.45);
}
.card.locked .title {
  color: rgba(242, 232, 213, 0.55);
}
.card.locked .sub {
  color: rgba(242, 232, 213, 0.4);
}
.badge.locked {
  color: rgba(242, 232, 213, 0.5);
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
