<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { PromptState } from './PromptLabel.vue'

export type LineSource = 'input' | 'out' | 'error' | 'warn' | 'system' | 'success' | 'emphasis'
export interface TerminalLine {
  id: number
  source: LineSource
  text: string
  /** present on input lines so the echoed prompt keeps its colours */
  prompt?: PromptState
}

const props = withDefaults(defineProps<{
  lines?: TerminalLine[]
  prompt?: PromptState
  connected?: boolean
}>(), {
  lines: () => [],
  prompt: () => ({ user: 'detective', host: 'office', path: '/root', hostType: 'local' }),
  connected: true,
})

const emit = defineEmits<{
  (e: 'command', line: string): void
  /** Ctrl+L / clear コマンド共通のスクロールバッククリア（TerminalView は store を知らない） */
  (e: 'clear'): void
  /** Ctrl+C。破棄した入力途中文字列を渡し、呼び出し側が「プロンプト+文字列+^C」の行を積む */
  (e: 'interrupt', line: string): void
}>()

const input = ref('')
const composing = ref(false)
const scrollback = ref<HTMLElement | null>(null)
const field = ref<HTMLInputElement | null>(null)
const atBottom = ref(true)

// --- UX-01b: コマンド履歴（↑/↓）。ページ内 state のみ・永続化しない ---
const HISTORY_LIMIT = 500
const history = ref<string[]>([])
/** -1 = 履歴外（現在の入力=draft を編集中）。0..history.length-1 = 履歴を遡っている位置 */
const histIdx = ref(-1)
/** 初めて ↑ を押した時点の入力途中文字列（↓ で最新を越えたら復元） */
const draft = ref('')

function submit() {
  // Never send while IME composition is active (変換確定の Enter を送らない)
  if (composing.value) return
  const line = input.value
  if (!line.trim()) return
  pushHistory(line)
  emit('command', line)
  input.value = ''
  histIdx.value = -1
  draft.value = ''
}

function pushHistory(line: string) {
  // bash の HISTCONTROL=ignoredups 相当: 直前と同一の行は積まない
  if (history.value[history.value.length - 1] === line) return
  history.value.push(line)
  if (history.value.length > HISTORY_LIMIT) history.value.shift()
}

function caretPos(): number {
  return field.value?.selectionStart ?? input.value.length
}

function setCaret(pos: number) {
  nextTick(() => field.value?.setSelectionRange(pos, pos))
}

function historyUp() {
  if (history.value.length === 0) return
  if (histIdx.value === -1) {
    draft.value = input.value
    histIdx.value = history.value.length - 1
  } else if (histIdx.value > 0) {
    histIdx.value--
  }
  input.value = history.value[histIdx.value] ?? ''
  setCaret(input.value.length)
}

function historyDown() {
  if (histIdx.value === -1) return
  if (histIdx.value < history.value.length - 1) {
    histIdx.value++
    input.value = history.value[histIdx.value] ?? ''
  } else {
    histIdx.value = -1
    input.value = draft.value
  }
  setCaret(input.value.length)
}

function onCtrlC(event: KeyboardEvent) {
  // 文字列選択中の Ctrl+C はコピー操作（Windows/Linux）。xterm.js と同じく横取りしない
  if (window.getSelection()?.toString()) return
  event.preventDefault()
  const line = input.value
  emit('interrupt', line)
  input.value = ''
  histIdx.value = -1
  draft.value = ''
}

function onCtrlL(event: KeyboardEvent) {
  event.preventDefault()
  emit('clear')
}

function onCtrlA(event: KeyboardEvent) {
  event.preventDefault()
  setCaret(0)
}

function onCtrlE(event: KeyboardEvent) {
  event.preventDefault()
  setCaret(input.value.length)
}

/** unix-line-discard: キャレットより前を削除 */
function onCtrlU(event: KeyboardEvent) {
  event.preventDefault()
  const pos = caretPos()
  input.value = input.value.slice(pos)
  setCaret(0)
}

/** unix-word-rubout: 直前の単語を削除 */
function onCtrlW(event: KeyboardEvent) {
  event.preventDefault()
  const pos = caretPos()
  const before = input.value.slice(0, pos)
  const after = input.value.slice(pos)
  const trimmed = before.replace(/\s+$/, '')
  const lastSpace = trimmed.lastIndexOf(' ')
  const newBefore = lastSpace === -1 ? '' : trimmed.slice(0, lastSpace + 1)
  input.value = newBefore + after
  setCaret(newBefore.length)
}

const CTRL_HANDLERS: Record<string, (event: KeyboardEvent) => void> = {
  c: onCtrlC,
  l: onCtrlL,
  a: onCtrlA,
  e: onCtrlE,
  u: onCtrlU,
  w: onCtrlW,
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    // 変換確定の Enter で送信しないよう、判定は submit() 内の composing チェックに委ねる
    event.preventDefault()
    submit()
    return
  }
  // IME 変換中は他のショートカット・履歴移動を横取りしない
  if (composing.value || event.isComposing) return

  if (event.ctrlKey) {
    const handler = CTRL_HANDLERS[event.key.toLowerCase()]
    handler?.(event)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    historyUp()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    historyDown()
  }
}

function onScroll() {
  const el = scrollback.value
  if (!el) return
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 24
}

function scrollToBottom() {
  const el = scrollback.value
  if (el) el.scrollTop = el.scrollHeight
  atBottom.value = true
}

function focusInput() {
  // Don't steal focus while the user is selecting text to copy
  if (window.getSelection()?.toString()) return
  field.value?.focus()
}

// Follow new output only when already pinned to the bottom
watch(() => props.lines.length, () => {
  if (atBottom.value) nextTick(scrollToBottom)
})
</script>

<template>
  <div class="terminal" @click="focusInput">
    <div ref="scrollback" class="scrollback" @scroll="onScroll">
      <div v-for="ln in lines" :key="ln.id" class="ln" :class="ln.source">
        <template v-if="ln.source === 'input'">
          <PromptLabel v-if="ln.prompt" v-bind="ln.prompt" />
          <span class="cmd"> {{ ln.text }}</span>
        </template>
        <template v-else>{{ ln.text }}</template>
      </div>
    </div>

    <button v-if="!atBottom" class="pill" @click.stop="scrollToBottom">↓ 新しい出力</button>

    <div class="input-row">
      <PromptLabel v-bind="prompt" />
      <input
        ref="field"
        v-model="input"
        class="field"
        type="text"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        :placeholder="connected ? '' : '-- not connected --'"
        @keydown="onKeydown"
        @compositionstart="composing = true"
        @compositionend="composing = false"
      >
    </div>
  </div>
</template>

<style scoped>
.terminal {
  position: relative;
  background: var(--hairline-scan), var(--surface-terminal);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel), inset 0 0 60px rgba(74, 222, 128, 0.04);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-term);
  letter-spacing: var(--tracking-term);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 260px;
}
.scrollback {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) var(--space-4);
  color: var(--term-fg);
  user-select: text;
  scroll-behavior: smooth;
}
.scrollback::-webkit-scrollbar {
  width: 10px;
}
.scrollback::-webkit-scrollbar-thumb {
  background: var(--gray-700);
  border-radius: 5px;
}
.ln {
  white-space: pre-wrap;
  word-break: break-word;
}
.ln.input .cmd {
  color: var(--green-300);
}
.ln.out {
  color: var(--green-400);
}
.ln.error {
  color: var(--term-error);
}
.ln.warn {
  color: var(--term-warn);
}
.ln.system {
  color: var(--gray-500);
  font-style: italic;
}
.ln.success {
  color: var(--term-success);
}
.ln.emphasis {
  color: var(--term-warn);
  font-weight: var(--weight-bold);
}
.input-row {
  display: flex;
  align-items: baseline;
  gap: 0.5ch;
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-2) var(--space-4);
  background: rgba(255, 255, 255, 0.02);
}
.input-row:focus-within {
  background: rgba(74, 222, 128, 0.04);
  box-shadow: inset 0 1px 0 rgba(74, 222, 128, 0.25);
}
.field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--green-300);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  letter-spacing: var(--tracking-term);
  caret-color: var(--green-400);
}
.pill {
  position: absolute;
  right: var(--space-4);
  bottom: 56px;
  background: var(--accent);
  color: #fff;
  font-family: var(--font-ui);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  padding: var(--space-1) var(--space-3);
  border: none;
  border-radius: 999px;
  box-shadow: var(--shadow-card), var(--glow-indigo);
  cursor: pointer;
}
</style>
