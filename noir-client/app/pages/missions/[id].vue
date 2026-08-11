<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

/*
 * Mission 詳細 + 開始導線（FE-02）。設計指示書 § 3 ルーティング `/missions/{id}`。
 * ターミナル本体の WS 接続（FE-03/04）は後続タスクでこの続き（「捜査を開始する」の先）
 * に配線する。
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
const { apiFetch } = useApi()

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
watch(missionId, (id) => {
  started.value = false
  loadMission(id)
})

function start() {
  if (!mission.value || mission.value.status === 'locked') return
  started.value = true
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

  <!-- ターミナル本体は WS 接続基盤（FE-03/04）で配線する -->
  <div v-else class="center hint">
    捜査記録を準備中…（ターミナル接続は次のタスクで実装）
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
</style>
