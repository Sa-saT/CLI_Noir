<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { CommandEntry } from '~/components/CommandPanel.vue'
import type { SaveEntry } from '~/components/SaveSelectModal.vue'

/*
 * ゲーム画面（設計指示書 § 3 ルーティング `/missions/{id}`。DESIGN.md § 7）。
 *
 * Phase E（FE3-01/FE3-02）: 「常時ターミナル」導入により、このページは**表示切替専用**
 * になった。WebSocket 接続のライフサイクル（connect/disconnect）は `app.vue` が
 * ログイン状態にひもづけて管理する — このページからは一切呼ばない。
 * ページが担うのはブリーフィング（事件ファイル）・ヒント・コマンド一覧の表示切替のみ。
 * 「捜査を開始する」はブリーフィングカードを閉じるボタンであり、接続はしない。
 * ターミナル本体（scrollback・接続状態）は Pinia store（app/stores/terminal.ts）が
 * 唯一の真実で、Mission ページを行き来しても消えない。
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
const selectedCommand = ref('')

// ブリーフィング（事件ファイル）カードの開閉。Mission 切替時とページ初回表示時は開く。
const briefingOpen = ref(true)

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

// 次 Mission への遷移など、同一コンポーネントのまま id だけ変わるケースに対応。
// 接続には触らない（常時接続。app.vue 管理）。
watch(missionId, (id) => {
  revealedHints.value = 0
  briefingOpen.value = true
  loadMission(id)
})

function closeBriefing() {
  if (!mission.value || mission.value.status === 'locked') return
  briefingOpen.value = false
}

function onSelectCommand(name: string) {
  selectedCommand.value = name
}

// UX-01b: Ctrl+C は入力を破棄するのみでサーバーへは送らず、実 bash と同じ見た目
// （プロンプト + 入力途中文字列 + ^C）をスクロールバックに残す。
function onInterrupt(line: string) {
  store.pushEchoedInput(`${line}^C`, store.promptState)
}

// --- 捜査中の事件とこのページの Mission が異なる場合の案内（表示切替専用ページのため、
// `sh case_file.sh` の判定対象は store.activeMissionId であり、このページの mission
// とは限らない） ---
const missionMismatch = computed(() => store.activeMissionId !== missionId.value)

// --- FE-07: セーブ選択（再ログイン時の commit 一覧） ---
const saves = computed<SaveEntry[]>(() => store.commits.map((c, idx) => ({
  hash: `#${c.id}`,
  message: c.message || '(無題のセーブ)',
  when: c.created_at ?? '',
  mission: c.mission_id != null ? `Mission ${c.mission_id}` : '',
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

  <div v-else class="screen">
    <div class="ga-header">
      <MissionHeader
        :tag="`Mission ${mission.id}`"
        :title="mission.title"
        :subtitle="mission.title_ja"
        :rank="rank"
      />
      <p v-if="store.connected && missionMismatch" class="mismatch">
        <template v-if="store.activeMissionId != null">
          捜査中の事件は
          <NuxtLink :to="`/missions/${store.activeMissionId}`">Mission {{ store.activeMissionId }}</NuxtLink>
          です — <code>sh case_file.sh</code> はそちらを判定します
        </template>
        <template v-else>
          すべての事件を解決済み
        </template>
      </p>
    </div>

    <div class="ga-scene scene-col">
      <SceneOverlay
        :image="sceneImage"
        :badge="briefingOpen ? 'Case File' : 'Scène'"
        :card-title="briefingOpen ? mission.title_ja : ''"
        :card-body="briefingOpen ? mission.description : ''"
      >
        <NoirButton
          v-if="briefingOpen"
          variant="primary"
          size="lg"
          :disabled="mission.status === 'locked'"
          @click="closeBriefing"
        >
          {{ mission.status === 'locked' ? 'この事件はまだ開放されていない' : '捜査を開始する' }}
        </NoirButton>
      </SceneOverlay>
      <div v-if="store.pendingResume" class="resume-overlay">
        <SaveSelectModal
          title="セーブを選んで再開"
          subtitle="記録された commit から選択してください"
          :saves="saves"
          @resume="onResume"
          @start-over="onStartOver"
        />
      </div>
      <ClearEffect v-if="store.missionCleared" class="clear-overlay" @next="onNext" />
    </div>

    <aside class="ga-rail rail">
      <NoirButton variant="ghost" @click="briefingOpen = true">事件ファイルを見る</NoirButton>
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
        @clear="store.clearScrollback"
        @interrupt="onInterrupt"
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
  display: flex;
  flex-direction: column;
}
.mismatch {
  margin: 0;
  padding: var(--space-2) var(--space-6);
  background: var(--poster-black);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.mismatch a {
  color: var(--brass-400);
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
