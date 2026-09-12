<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { StoryBeat } from '~/types/ws'

/*
 * 進行案内「独り言レイヤー」（STORY-01）。探偵の内省をサウンドノベル風にタイプライター表示する。
 * 話者ラベルは付けない。scene 領域の下辺に重ねる（配置は親: pages/missions/[id].vue が担当）。
 * ターミナルの操作を一切邪魔しない — フォーカスを奪わない（mousedown.prevent）・Enter を
 * 横取りしない（キーボードイベントには一切触れない。クリック/タップのみで完結させる）。
 */

const props = defineProps<{
  beat: StoryBeat | null
  hasNext: boolean
  log: StoryBeat[]
}>()
const emit = defineEmits<{ (e: 'advance'): void }>()

const TICK_MS = 28
/** 表示し終えた後、次の独り言が待っていれば自動で送るまでの間。クリックで早送りできる。
 *  （ターミナルに集中している人は台詞窓をクリックしないので、待ちきりにしない） */
const AUTO_ADVANCE_MS = 4000

interface Segment { text: string, code: boolean }

/** `` `code` `` で囲まれた部分を等幅・シアン表示にする簡易パーサ。 */
function parseSegments(text: string): Segment[] {
  const segments: Segment[] = []
  const re = /`([^`]+)`/g
  let last = 0
  let m: RegExpExecArray | null
  // eslint-disable-next-line no-cond-assign
  while ((m = re.exec(text))) {
    if (m.index > last) segments.push({ text: text.slice(last, m.index), code: false })
    segments.push({ text: m[1] ?? '', code: true })
    last = re.lastIndex
  }
  if (last < text.length) segments.push({ text: text.slice(last), code: false })
  return segments
}

const segments = ref<Segment[]>([])
const revealedChars = ref(0)
const showLog = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const totalChars = computed(() => segments.value.reduce((n, s) => n + s.text.length, 0))
const typingDone = computed(() => revealedChars.value >= totalChars.value)

const visibleSegments = computed(() => {
  let remaining = revealedChars.value
  const out: Segment[] = []
  for (const seg of segments.value) {
    if (remaining <= 0) break
    if (seg.text.length <= remaining) {
      out.push(seg)
      remaining -= seg.text.length
    } else {
      out.push({ text: seg.text.slice(0, remaining), code: seg.code })
      remaining = 0
    }
  }
  return out
})

let autoTimer: ReturnType<typeof setTimeout> | null = null

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (autoTimer) {
    clearTimeout(autoTimer)
    autoTimer = null
  }
}

function scheduleAutoAdvance() {
  if (autoTimer) clearTimeout(autoTimer)
  autoTimer = null
  if (!props.hasNext || showLog.value) return
  autoTimer = setTimeout(() => {
    autoTimer = null
    if (props.hasNext && typingDone.value) emit('advance')
  }, AUTO_ADVANCE_MS)
}

// 表示完了 or 次の独り言の到着で自動送りを予約し直す
watch([typingDone, () => props.hasNext, showLog], ([done]) => {
  if (done) scheduleAutoAdvance()
})

function startTyping() {
  stopTimer()
  revealedChars.value = 0
  if (totalChars.value === 0) return
  timer = setInterval(() => {
    revealedChars.value++
    if (revealedChars.value >= totalChars.value) stopTimer()
  }, TICK_MS)
}

watch(() => props.beat, (beat) => {
  showLog.value = false
  segments.value = beat ? parseSegments(beat.text) : []
  startTyping()
}, { immediate: true })

onBeforeUnmount(stopTimer)

/** タイプ中なら全文即表示、表示済みで次があれば進める。 */
function onClick() {
  if (!typingDone.value) {
    revealedChars.value = totalChars.value
    stopTimer()
    return
  }
  if (props.hasNext) emit('advance')
}

function toggleLog() {
  showLog.value = !showLog.value
}
</script>

<template>
  <div v-if="beat" class="story-overlay" @mousedown.prevent>
    <button type="button" class="log-toggle" aria-label="これまでの独り言" @click.stop="toggleLog">
      ⋯
    </button>

    <div v-if="showLog" class="log-list">
      <p v-for="b in log" :key="`${b.mission_id}:${b.id}`" class="log-entry">{{ b.text }}</p>
    </div>
    <div v-else class="body" @click="onClick">
      <p class="text">
        <span v-for="(seg, i) in visibleSegments" :key="i" :class="{ code: seg.code }">{{ seg.text }}</span>
      </p>
      <span v-if="typingDone && hasNext" class="next-indicator" aria-hidden="true">▶</span>
    </div>
  </div>
</template>

<style scoped>
.story-overlay {
  position: absolute;
  left: var(--space-4);
  right: var(--space-4);
  bottom: var(--space-4);
  max-width: 640px;
  margin: 0 auto;
  background: rgba(17, 24, 39, 0.88);
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card), var(--bezel-brass);
  padding: var(--space-4) var(--space-5);
  font-family: var(--font-ui);
}
.body {
  cursor: pointer;
  min-height: 1.5em;
}
.text {
  margin: 0;
  padding-right: var(--space-6);
  color: var(--text-body);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
}
.text .code {
  font-family: var(--font-mono);
  color: var(--cyan-400);
}
.next-indicator {
  position: absolute;
  right: var(--space-4);
  bottom: var(--space-3);
  color: var(--brass-400);
  animation: story-next-blink 1s ease-in-out infinite;
}
.log-toggle {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: var(--text-sm);
  line-height: 1;
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
}
.log-toggle:hover {
  color: var(--brass-400);
}
.log-list {
  max-height: 9rem;
  overflow-y: auto;
  padding-right: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.log-entry {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
}
.log-entry:last-child {
  color: var(--text-body);
}

@keyframes story-next-blink {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}
</style>
