<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CommandEntry } from '~/components/CommandPanel.vue'
import type { SaveEntry } from '~/components/SaveSelectModal.vue'
import type { CodexCommand, CodexError, Fragment } from '~/types/ws'
import type { FieldCardData } from '~/components/FieldCard.vue'

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
  field_card: FieldCardData | null
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
  hintGlow.value = false
}

// --- STORY-01: 停滞（stall）判定（フロント側ローカル。Mission ごとに一度だけ発火） ---
// サーバーからは来ない。60秒無操作、または `result` の ok=false が3回連続で発火する。
const hintGlow = ref(false)
let stallFired = false
let stallTimer: ReturnType<typeof setTimeout> | null = null

function clearStallTimer() {
  if (stallTimer) {
    clearTimeout(stallTimer)
    stallTimer = null
  }
}
function scheduleStallTimer() {
  clearStallTimer()
  if (stallFired) return
  // ブリーフィングを読んでいる間は「停滞」ではない。閉じてから計測を始める
  if (briefingOpen.value) return
  stallTimer = setTimeout(fireStall, 60000)
}
function fireStall() {
  if (stallFired) return
  // 捜査中でない（クリア済み等の）Mission ページを眺めているだけなら口を出さない
  if (store.activeMissionId !== missionId.value) return
  stallFired = true
  clearStallTimer()
  store.enqueueStory([{
    id: 'stall',
    mission_id: missionId.value,
    text: '……手が止まっている。焦らなくていい。ヒントを見るのは恥じゃない。',
  }])
  if (mission.value && mission.value.hints.length > 0) hintGlow.value = true
}
// 操作（scrollback の変化）を最後の操作時刻とみなし、そのたびにタイマーを引き直す。
watch(() => store.lines.length, () => scheduleStallTimer())
// 連続失敗3回で即発火。
watch(() => store.consecutiveErrors, (n) => {
  if (n >= 3) fireStall()
})
onBeforeUnmount(clearStallTimer)

const commands = computed<CommandEntry[]>(() => buildCommandEntries(mission.value?.allowed_commands ?? []))
const detail = computed(() => {
  if (!selectedCommand.value) return null
  return { name: selectedCommand.value, ...commandDetailFor(selectedCommand.value) }
})
// ヘッダーのランクは接続中はプレイヤーの現在ランク（state.rank）、未接続時は Mission の
// allowed_commands から推定する旧ロジックにフォールバック
const rank = computed(() => {
  const base = store.rank ? `Lv.${store.rank.level} ${store.rank.name}` : (mission.value ? rankLabelFor(mission.value.allowed_commands) : '')
  // やらかし体験室（Mission29）: 予備の機械に繋いでいる間は本物の世界が退避中であることを明示する
  return store.sandbox ? `SANDBOX · ${base}` : base
})

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

onMounted(() => {
  loadMission(missionId.value)
  scheduleStallTimer()
})

// 次 Mission への遷移など、同一コンポーネントのまま id だけ変わるケースに対応。
// 接続には触らない（常時接続。app.vue 管理）。
watch(missionId, (id) => {
  revealedHints.value = 0
  briefingOpen.value = true
  stallFired = false
  hintGlow.value = false
  scheduleStallTimer()
  loadMission(id)
})

// 事件が解決したらブリーフィングカードは閉じる（クリア演出は中心が半透明で、開いたままだと
// 「MISSION COMPLETE!」の下にカードが透けて読めない）。
watch(() => store.missionCleared, (cleared) => {
  if (cleared) briefingOpen.value = false
})

function closeBriefing() {
  if (!mission.value || mission.value.status === 'locked') return
  briefingOpen.value = false
  scheduleStallTimer()
}

function onSelectCommand(name: string) {
  // 同じコマンドをもう一度クリックしたら閉じる（× ボタンと同じ）
  selectedCommand.value = selectedCommand.value === name ? '' : name
}

// UX-01b: Ctrl+C は入力を破棄するのみでサーバーへは送らず、実 bash と同じ見た目
// （プロンプト + 入力途中文字列 + ^C）をスクロールバックに残す。
function onInterrupt(line: string) {
  store.pushEchoedInput(`${line}^C`, store.promptState)
}

// --- スマート捜査ボーナス / タイムアタック演出（ゲーム機能 3・7。表示のみ） ---
function fmtSec(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
const BONUS_LABEL: Record<string, string> = { SMART: 'スマート捜査 +50', NEAR: '手際よし +20', PIPE: 'パイプ一閃 +20' }
const verdict = computed(() => {
  const sc = store.lastScore
  if (!sc) return ''
  const parts = [`${sc.commands} 手 / 目安 ${sc.par} 手`]
  if (sc.elapsed_seconds != null) parts.push(fmtSec(sc.elapsed_seconds))
  for (const b of sc.bonuses) parts.push(BONUS_LABEL[b] ?? b)
  parts.push(`${sc.score} pt`)
  return parts.join(' · ')
})
// 経過時間（演出のみ。目安を過ぎても失敗にはならない）
const now = ref(Date.now())
let clock: ReturnType<typeof setInterval> | null = null
onMounted(() => { clock = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => { if (clock) clearInterval(clock) })
const elapsed = computed(() => {
  if (!store.missionStartedAt || store.activeMissionId !== missionId.value) return null
  const started = Date.parse(store.missionStartedAt)
  if (Number.isNaN(started)) return null
  return Math.max(0, Math.floor((now.value - started) / 1000))
})
const overTarget = computed(() => elapsed.value != null && elapsed.value > store.targetMinutes * 60)

// --- 現場実習カード（ゲーム機能 11）: クリア演出（と辞令）の後に発行。クリア済み Mission のページからも再表示 ---
// クリアした Mission のカードは、次 Mission のページに移った後に出すので詳細を別に取る
const fieldCard = ref<{ tag: string, card: FieldCardData } | null>(null)
const fieldCardManual = ref(false)
watch(() => [store.missionCleared, store.pendingRankUp, store.pendingFieldCard] as const, async ([cleared, rankUp, pending]) => {
  if (cleared || rankUp || pending == null) return
  if (fieldCard.value?.tag === `Mission ${pending}`) return
  try {
    const detail = await apiFetch<MissionDetail>(`/api/missions/${pending}/`)
    if (detail.field_card) fieldCard.value = { tag: `Mission ${detail.id}`, card: detail.field_card }
    else store.dismissFieldCard()
  } catch {
    store.dismissFieldCard()
  }
}, { immediate: true })
function closeFieldCard() {
  fieldCardManual.value = false
  fieldCard.value = null
  store.dismissFieldCard()
}
function showFieldCardAgain() {
  if (!mission.value?.field_card) return
  fieldCard.value = { tag: `Mission ${mission.value.id}`, card: mission.value.field_card }
  fieldCardManual.value = true
}
const fieldCardVisible = computed(() => fieldCard.value != null && (fieldCardManual.value || (store.pendingFieldCard != null && !store.missionCleared && !store.pendingRankUp)))

// --- 図鑑（ゲーム機能 2・10）: scene 上のレイヤー。開くときに一覧を取り直す ---
async function toggleCodex() {
  store.codexOpen = !store.codexOpen
  if (!store.codexOpen) return
  try {
    const data = await apiFetch<{ commands: CodexCommand[], errors: CodexError[], fragments: Fragment[], total: number }>('/api/codex/')
    store.setCodex(data.commands, data.errors, data.fragments, data.total)
  } catch {
    // 取得失敗時は result で積んだ分だけを見せる
  }
}

// Tab 補完で候補が複数あったとき: bash と同じく候補を一覧で見せる（入力行はそのまま）
function onCompletions(candidates: string[]) {
  store.pushLine('out', candidates.join('  '))
}

// --- 捜査中の事件とこのページの Mission が異なる場合の案内（表示切替専用ページのため、
// `sh case_file.sh` の判定対象は store.activeMissionId であり、このページの mission
// とは限らない） ---
const missionMismatch = computed(() => store.activeMissionId !== missionId.value)

// --- FE-07: セーブ選択（再ログイン時の commit 一覧） ---
function formatWhen(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const saves = computed<SaveEntry[]>(() => store.commits.map((c, idx) => ({
  hash: `#${c.id}`,
  message: c.message || '(無題のセーブ)',
  when: formatWhen(c.created_at),
  mission: c.mission_id != null ? `Mission ${c.mission_id}` : '',
  latest: idx === store.commits.length - 1,
  pushed: c.pushed === true,
})))

function onResume(hash: string) {
  const id = Number(hash.replace('#', ''))
  socket.resume(id)
}
function onStartOver() {
  socket.skipResume()
}
// resume で世界が巻き戻ったら、捜査中の Mission のページへ移る（Mission2 のページを
// 見たまま Mission1 のセーブに戻ると「park が無い」ように見える。2026-09-13 報告）。
watch(() => store.resumeSeq, () => {
  const active = store.activeMissionId
  if (active != null && active !== missionId.value) router.push(`/missions/${active}`)
})

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
  if (next) router.push(`/missions/${next}`)
  else router.push('/missions')
  // 演出を閉じてから保留中の独り言（クリア独り言 → 次 Mission の start）を流す
  store.dismissClear()
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
      <p v-if="elapsed != null" class="clock" :class="{ over: overTarget }">
        ⏱ 経過 {{ fmtSec(elapsed) }} / 目安 {{ store.targetMinutes }}:00
        <span v-if="overTarget">— 焦らなくていい。時間切れは無い</span>
      </p>
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
      <!-- 独り言はブリーフィング（事件ファイル）を閉じてから流す。開いている間は beat を渡さず
           保留する（閉じると先頭から再生される。2026-09-13 ユーザー要望） -->
      <CodexLayer
        :open="store.codexOpen"
        :commands="store.codexCommands"
        :errors="store.codexErrors"
        :fragments="store.fragments"
        :fragments-total="store.fragmentsTotal"
        :fresh="store.codexFresh"
        @close="store.codexOpen = false"
      />
      <MonologueLayer
        :beat="briefingOpen ? null : store.storyCurrent"
        :has-next="store.storyHasNext"
        @advance="store.advanceStory"
        @complete="store.completeStory"
      />
      <div v-if="store.pendingResume" class="resume-overlay">
        <SaveSelectModal
          title="セーブを選んで再開"
          subtitle="選んだ commit の時点まで世界が巻き戻ります（クリア印付きはクリア直後から）"
          :saves="saves"
          @resume="onResume"
          @start-over="onStartOver"
        />
      </div>
      <ClearEffect v-if="store.missionCleared" class="clear-overlay" :verdict="verdict" @next="onNext" />
      <div v-else-if="store.pendingRankUp" class="rankup-overlay" @click="store.dismissRankUp">
        <RankUpEffect
          :from="`Lv.${store.pendingRankUp.from_level} ${store.pendingRankUp.from_rank_name}`"
          :to="`Lv.${store.pendingRankUp.level} ${store.pendingRankUp.rank_name}`"
          :unlocks="store.pendingRankUp.unlocked"
        />
        <p class="rankup-hint">クリックして受領</p>
      </div>
      <div v-else-if="fieldCardVisible && fieldCard" class="fieldcard-overlay">
        <FieldCard :mission-tag="fieldCard.tag" :card="fieldCard.card" @close="closeFieldCard" />
      </div>
    </div>

    <aside class="ga-rail rail">
      <div class="rail-nav">
        <NoirButton variant="ghost" @click="router.push('/missions')">← 捜査ファイル一覧</NoirButton>
        <NoirButton variant="ghost" @click="briefingOpen = true">事件ファイルを見る</NoirButton>
        <NoirButton variant="ghost" @click="toggleCodex">{{ store.codexOpen ? '図鑑を閉じる' : '図鑑（道具 / エラー）' }}</NoirButton>
        <NoirButton v-if="mission.status === 'cleared' && mission.field_card" variant="ghost" @click="showFieldCardAgain">現場実習カード</NoirButton>
      </div>
      <CommandPanel :commands="commands" @select="onSelectCommand" />
      <CommandDetail
        v-if="detail"
        :name="detail.name"
        :syntax="detail.syntax"
        :real="detail.real"
        :in-game="detail.inGame"
        @close="selectedCommand = ''"
      />
      <div v-if="mission.hints.length" class="hint-box">
        <NoirButton
          variant="secondary"
          :class="{ glow: hintGlow }"
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
        :completer="socket.complete"
        @command="socket.exec"
        @clear="store.clearScrollback"
        @interrupt="onInterrupt"
        @completions="onCompletions"
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
.clock {
  margin: 0;
  padding: 2px var(--space-6);
  background: var(--poster-black);
  color: var(--brass-400);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
}
.clock.over {
  color: var(--term-warn);
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
  z-index: 45; /* MonologueLayer（40）より上、SaveSelectModal（50）より下 */
}
.rankup-overlay {
  /* 辞令はクリア演出の後・独り言の前（DESIGN.md § 6）。scene 領域に重ね、クリックで受領 */
  position: absolute;
  inset: 0;
  z-index: 45;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: rgba(10, 8, 6, 0.6);
  cursor: pointer;
}
.rankup-overlay :deep(.decree) {
  max-height: 100%;
  overflow: auto;
}
.fieldcard-overlay {
  position: absolute;
  inset: 0;
  z-index: 45;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(10, 8, 6, 0.6);
}
.rankup-hint {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  color: var(--poster-cream);
  opacity: 0.8;
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
/* flex 子の overflow:hidden は自動最小サイズを 0 にするため、rail の高さに合わせて
   パネルが縮んで中身が切れてしまう。子は縮めず rail 側をスクロールさせる（UX-02）。 */
.ga-rail > * {
  flex-shrink: 0;
}
.rail-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
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
.hint-box :deep(.glow) {
  animation: hint-glow 1.2s ease-in-out infinite;
}
@keyframes hint-glow {
  0%, 100% { box-shadow: var(--bezel-brass); }
  50% { box-shadow: var(--bezel-brass), 0 0 12px 2px var(--brass-400); }
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
