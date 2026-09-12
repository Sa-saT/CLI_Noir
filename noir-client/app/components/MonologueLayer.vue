<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { StoryBeat } from '~/types/ws'

/*
 * MonologueLayer — サウンドノベル式の独り言レイヤー（STORY-01）。
 * ClaudeDesign `components/monologue-layer/MonologueLayer.jsx` の Vue 移植（正は ClaudeDesign 側）。
 *
 * 枠なし・窓なし。scene の絵の上に素のテキストを置き、縦方向の薄いスクリムで文字を浮かせるだけ
 * （かまいたちの夜スタイル）。声の分離が要: ターミナルは `--font-mono`、独り言は `--font-narration`
 * （表示用セリフ + OS の明朝フォールバック。等幅で描くとシステム出力に見えてしまう）。
 *
 * 入力を塞がない: スクリムは pointer-events:none、クリックできるのは本文だけ。ターミナルの
 * フォーカスは奪わない（mousedown.prevent）。Esc でこの一連の独り言を閉じる。
 *
 * サーバーから beat が逐次届く前提なので、React 版の `lines[]` 一括ではなく「現在の beat +
 * 次があるか」を props で受ける。次が待っていれば表示完了後 AUTO_ADVANCE_MS で自動送り
 * （ターミナルに集中している人は本文をクリックしないため。クリックで早送りは React 版どおり）。
 */

const props = defineProps<{
  beat: StoryBeat | null
  hasNext: boolean
  /** 1 文字あたりの表示間隔 ms（ClaudeDesign 既定 34） */
  speed?: number
  /** スクリムの濃さ 0〜1（ClaudeDesign 既定 0.55） */
  dim?: number
}>()
const emit = defineEmits<{
  (e: 'advance'): void
  /** 一連の独り言を閉じた（Esc / 最後の beat をクリック / 放置） */
  (e: 'complete'): void
}>()

const SPEED_DEFAULT = 34
const DIM_DEFAULT = 0.55
const PUNCT_HOLD_MS = 180
const AUTO_ADVANCE_MS = 4000
const AUTO_COMPLETE_MS = 8000

const chars = ref(0)
const dismissed = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null
let autoTimer: ReturnType<typeof setTimeout> | null = null

const text = computed(() => props.beat?.text ?? '')
const done = computed(() => chars.value >= text.value.length)
const shown = computed(() => text.value.slice(0, chars.value))
const speed = computed(() => props.speed ?? SPEED_DEFAULT)
const dim = computed(() => props.dim ?? DIM_DEFAULT)
const scrim = computed(() => {
  const d = dim.value
  return `linear-gradient(180deg, rgba(10,8,6,${d * 0.5}) 0%, rgba(10,8,6,${d}) 45%, rgba(10,8,6,${d * 1.15}) 100%)`
})

function clearTimers() {
  if (timer) clearTimeout(timer)
  if (autoTimer) clearTimeout(autoTimer)
  timer = null
  autoTimer = null
}

/** 句読点で長めに、空白は速く — ティッカーではなく小説の呼吸で。 */
function tick() {
  timer = null
  if (done.value) return
  const ch = text.value[chars.value] ?? ''
  const pause = /[。、，,.!?！？…]/.test(ch) ? speed.value + PUNCT_HOLD_MS : /[\s　]/.test(ch) ? speed.value * 0.4 : speed.value
  timer = setTimeout(() => {
    chars.value++
    tick()
  }, pause)
}

function scheduleAuto() {
  if (autoTimer) clearTimeout(autoTimer)
  autoTimer = null
  if (!done.value || dismissed.value) return
  autoTimer = setTimeout(() => {
    autoTimer = null
    if (props.hasNext) emit('advance')
    else complete()
  }, props.hasNext ? AUTO_ADVANCE_MS : AUTO_COMPLETE_MS)
}

function complete() {
  dismissed.value = true
  clearTimers()
  emit('complete')
}

/** 1 回目のクリックで全文表示、2 回目で次へ（最後なら閉じる）。 */
function advance() {
  if (!done.value) {
    if (timer) clearTimeout(timer)
    timer = null
    chars.value = text.value.length
    return
  }
  if (props.hasNext) emit('advance')
  else complete()
}

watch(() => props.beat, () => {
  clearTimers()
  dismissed.value = false
  chars.value = 0
  tick()
}, { immediate: true })

watch([done, () => props.hasNext], () => scheduleAuto())

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.beat && !dismissed.value) complete()
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  clearTimers()
})
</script>

<template>
  <div
    v-if="beat && !dismissed"
    class="monologue"
    :style="{ background: scrim }"
    aria-live="polite"
  >
    <div class="plate" role="button" tabindex="-1" @mousedown.prevent @click="advance">
      <p class="text">{{ shown }}<span class="caret" :class="{ hidden: done }" aria-hidden="true" /></p>
      <div class="next" :class="{ ready: done }" aria-hidden="true">▼</div>
    </div>
  </div>
</template>

<style scoped>
.monologue {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 7vw, 88px);
  pointer-events: none; /* 下のターミナルは生きたまま */
  transition: opacity 0.35s ease;
}
.plate {
  pointer-events: auto;
  cursor: pointer;
  max-width: 720px;
  text-align: left;
}
.text {
  margin: 0;
  font-family: var(--font-narration);
  font-size: clamp(18px, 2.1vw, 28px);
  line-height: var(--leading-narration);
  color: var(--poster-cream);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 2px 24px rgba(0, 0, 0, 0.85);
  text-wrap: pretty;
  white-space: pre-line;
}
.caret {
  display: inline-block;
  width: 0.08em;
  height: 1.05em;
  margin-left: 0.12em;
  vertical-align: -0.16em;
  background: var(--poster-cream);
  animation: cli-noir-monologue-caret 1s steps(1) infinite;
}
.caret.hidden {
  opacity: 0;
  animation: none;
}
.next {
  margin-top: var(--space-4);
  text-align: right;
  font-size: var(--text-sm);
  color: var(--poster-cream);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.95);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.next.ready {
  opacity: 0.72;
  animation: cli-noir-monologue-caret 1.1s steps(1) infinite;
}
</style>
