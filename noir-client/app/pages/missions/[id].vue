<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

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

async function loadMission(id: number) {
  loadError.value = ''
  mission.value = null
  try {
    mission.value = await apiFetch<MissionDetail>(`/api/missions/${id}/`)
  } catch {
    loadError.value = 'Error: mission not found'
  }
}

onMounted(() => loadMission(missionId.value))

// 次 Mission への遷移など、同一コンポーネントのまま id だけ変わるケースに対応
watch(missionId, (id) => {
  socket.disconnect()
  started.value = false
  loadMission(id)
})

onBeforeUnmount(() => socket.disconnect())

function start() {
  if (!mission.value || mission.value.status === 'locked') return
  started.value = true
  socket.connect(missionId.value)
}

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
    />
    <SceneOverlay
      class="briefing-scene"
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
    />

    <div class="ga-scene scene-col">
      <SceneOverlay badge="Scène" />
      <ClearEffect v-if="store.missionCleared" class="clear-overlay" @next="onNext" />
    </div>

    <aside class="ga-rail rail">
      <CommandPanel />
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
