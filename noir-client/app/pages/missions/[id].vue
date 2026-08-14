<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CommandEntry } from '~/components/CommandPanel.vue'
import type { SaveEntry } from '~/components/SaveSelectModal.vue'

/*
 * ゲーム画面（設計指示書 § 3 ルーティング `/missions/{id}`。DESIGN.md § 7）。
 * 未着手時は Mission 詳細（ブリーフィング）を表示し、「捜査を開始する」で
 * WebSocket 接続 → 実ターミナルへ遷移する（FE-02 の詳細+開始導線と、
 * 設計指示書 § 3 の固定ルーティングを両立させるため、ページ内 state で切替える）。
 *
 * FE-04: TerminalView を useTerminalSocket/Pinia store に接続し、モック evaluator
 * を撤去（旧実装は app/pages/index.vue にあった）。コマンド一覧の Mission 連動
 * （FE-05）・場面画像の current_path 連動（FE-06）・セーブ選択（FE-07）は後続タスク。
 */
definePageMeta({ middleware: 'auth' })

interface MissionDetail {
  id: number
  title: string
  title_ja: string
  description: string
  allowed_commands: string[]
  status: 'cleared' | 'open' | 'locked'
  hints: string[]
}

const route = useRoute()
const router = useRouter()
const { apiFetch } = useApi()
const store = useTerminalStore()
const socket = useTerminalSocket()

const missionId = computed(() => Number(route.params.id))
const mission = ref<MissionDetail | null>(null)
const loadError = ref('')
const started = ref(false)
const selectedCommand = ref('')

// --- HINT-01: 3段階ヒントの仮UI（サーバー側に状態は持たせない。ページ離脱でリセット） ---
const revealedHints = ref(0)
function revealNextHint() {
  if (!mission.value) return
  revealedHints.value = Math.min(revealedHints.value + 1, mission.value.hints.length)
}

const commands = computed<CommandEntry[]>(() => buildCommandEntries(mission.value?.allowed_commands ?? []))
const detail = computed(() => {
  if (!selectedCommand.value) return null
  return { name: selectedCommand.value, ...commandDetailFor(selectedCommand.value) }
})
const rank = computed(() => (mission.value ? rankLabelFor(mission.value.allowed_commands) : ''))

async function loadMission(id: number) {
  loadError.value = ''
  mission.value = null
  try {
    mission.value = await apiFetch<MissionDetail>(`/api/missions/${id}/`)
  } catch (err) {
    const statusCode = (err as { statusCode?: number })?.statusCode
    loadError.value = statusCode === 404 ? 'Error: mission not found' : 'Error: failed to load mission'
  }
}

onMounted(() => loadMission(missionId.value))

// 次 Mission への遷移など、同一コンポーネントのまま id だけ変わるケースに対応
watch(missionId, (id) => {
  socket.disconnect()
  started.value = false
  revealedHints.value = 0
  loadMission(id)
})

onBeforeUnmount(() => socket.disconnect())

function start() {
  if (!mission.value || mission.value.status === 'locked') return
  started.value = true
  socket.connect(missionId.value)
}

function onSelectCommand(name: string) {
  selectedCommand.value = name
}

// --- FE-07: セーブ選択（再ログイン時の commit 一覧） ---
const saves = computed<SaveEntry[]>(() => store.commits.map((c, idx) => ({
  hash: `#${c.id}`,
  message: c.message || '(無題のセーブ)',
  when: c.created_at ?? '',
  latest: idx === store.commits.length - 1,
})))

function onResume(hash: string) {
  const id = Number(hash.replace('#', ''))
  socket.resume(id)
}
function onStartOver() {
  socket.skipResume()
}

// --- FE-06: 場面画像の current_path 連動（DESIGN.md § 1。前方一致の最長一致） ---
const SCENE_IMAGES: Record<string, string> = {
  'office:/root': '/images/office.png',
  // 'amusement_park:/gate': '/images/amusement_park_gate.png', // Mission3 用画像の到着時に追加
}
function resolveScene(host: string, path: string): string {
  let bestPrefix = ''
  let img = ''
  for (const [key, val] of Object.entries(SCENE_IMAGES)) {
    const sep = key.indexOf(':')
    const h = key.slice(0, sep)
    const prefix = key.slice(sep + 1)
    if (h !== host) continue
    if (path !== prefix && !path.startsWith(`${prefix}/`)) continue
    if (prefix.length > bestPrefix.length) {
      bestPrefix = prefix
      img = val
    }
  }
  return img
}
const sceneImage = computed(() => resolveScene(store.displayHost, store.currentPath))

function onNext() {
  const next = store.nextMissionId
  store.missionCleared = false
  if (next) router.push(`/missions/${next}`)
  else router.push('/missions')
}
</script>

<template>
  <div v-if="loadError" class="center hint error">{{ loadError }}</div>
  <div v-else-if="!mission" class="center hint">読み込み中…</div>

  <div v-else-if="!started" class="briefing">
    <MissionHeader
      :tag="`Mission ${mission.id}`"
      :title="mission.title"
      :subtitle="mission.title_ja"
      :rank="rank"
    />
    <SceneOverlay
      class="briefing-scene"
      :image="sceneImage"
      badge="Case File"
      :card-title="mission.title_ja"
      :card-body="mission.description"
    >
      <NoirButton
        variant="primary"
        size="lg"
        :disabled="mission.status === 'locked'"
        @click="start"
      >
        {{ mission.status === 'locked' ? 'この事件はまだ開放されていない' : '捜査を開始する' }}
      </NoirButton>
    </SceneOverlay>
  </div>

  <div v-else class="screen">
    <MissionHeader
      class="ga-header"
      :tag="`Mission ${mission.id}`"
      :title="mission.title"
      :subtitle="mission.title_ja"
      :rank="rank"
    />

    <div class="ga-scene scene-col">
      <SceneOverlay :image="sceneImage" badge="Scène" />
      <div v-if="store.pendingResume" class="resume-overlay">
        <SaveSelectModal
          title="セーブを選んで再開"
          :subtitle="`Mission ${mission.id} — 記録された commit から選択してください`"
          :saves="saves"
          @resume="onResume"
          @start-over="onStartOver"
        />
      </div>
      <ClearEffect v-if="store.missionCleared" class="clear-overlay" @next="onNext" />
    </div>

    <aside class="ga-rail rail">
      <CommandPanel :commands="commands" @select="onSelectCommand" />
      <CommandDetail
        v-if="detail"
        :name="detail.name"
        :syntax="detail.syntax"
        :real="detail.real"
        :in-game="detail.inGame"
      />
      <div v-if="mission.hints.length" class="hint-box">
        <NoirButton
          variant="secondary"
          :disabled="revealedHints >= mission.hints.length"
          @click="revealNextHint"
        >
          ヒントを見る ({{ revealedHints }}/{{ mission.hints.length }})
        </NoirButton>
        <ol v-if="revealedHints > 0" class="hint-list">
          <li v-for="(h, i) in mission.hints.slice(0, revealedHints)" :key="i">{{ h }}</li>
        </ol>
      </div>
    </aside>

    <section class="ga-term term">
      <TerminalView
        :lines="store.lines"
        :prompt="store.promptState"
        :connected="store.connected"
        @command="socket.exec"
      />
    </section>
  </div>
</template>

<style scoped>
.center {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-app-deep);
}
.hint {
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.hint.error {
  color: var(--term-error);
}
.briefing {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-app-deep);
}
.briefing-scene {
  flex: 1;
  margin: var(--space-6);
}
.screen {
  display: grid;
  grid-template-columns: 1fr var(--rail-command-w);
  grid-template-rows: auto 1fr var(--terminal-h);
  grid-template-areas:
    "header header"
    "scene  rail"
    "term   rail";
  height: 100vh;
  min-height: 640px;
  background: var(--bg-app-deep);
  overflow: hidden;
}
.ga-header {
  grid-area: header;
}
.ga-scene {
  grid-area: scene;
  position: relative;
  min-width: 0;
  overflow: hidden;
}
.ga-scene :deep(.scene) {
  height: 100%;
  border: 0;
  border-radius: 0;
}
.clear-overlay {
  position: absolute;
  inset: 0;
}
.resume-overlay {
  /* fixed: 画面全体を覆い、選択が済むまでターミナル操作をさせない（scene 領域内の
     absolute overlay だと下部ターミナルの入力がそのまま操作できてしまうため） */
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 8, 6, 0.72);
  backdrop-filter: blur(2px);
}
.ga-rail {
  grid-area: rail;
  border-left: 1px solid var(--brass-600);
  box-shadow: var(--bezel-brass);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
}
.ga-rail :deep(.panel) {
  width: 100%;
}
.ga-rail :deep(.detail) {
  width: 100%;
}
.hint-box {
  width: var(--rail-command-w);
  max-width: 100%;
  background: linear-gradient(180deg, var(--gray-800), var(--gray-900));
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card), var(--bezel-brass);
  padding: var(--space-3);
  font-family: var(--font-ui);
}
.hint-list {
  margin: var(--space-3) 0 0;
  padding-left: 1.2em;
  color: var(--text-body);
  font-size: var(--text-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.ga-term {
  grid-area: term;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border-top: 1px solid var(--brass-600);
}

@media (max-width: 720px) {
  .screen {
    display: flex;
    flex-direction: column;
    height: auto;
  }
  .ga-scene {
    min-height: var(--scene-min-h);
  }
  .ga-rail {
    border-left: none;
  }
  .ga-term {
    height: var(--terminal-h);
    min-height: 260px;
  }
}
</style>
