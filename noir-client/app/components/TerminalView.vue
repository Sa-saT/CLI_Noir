<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { PromptState } from './PromptLabel.vue'

export type LineSource = 'input' | 'out' | 'error' | 'warn' | 'system'
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
  prompt: () => ({ user: 'detective', host: 'office', path: '/root', remote: false }),
  connected: true,
})

const emit = defineEmits<{ (e: 'command', line: string): void }>()

const input = ref('')
const composing = ref(false)
const scrollback = ref<HTMLElement | null>(null)
const field = ref<HTMLInputElement | null>(null)
const atBottom = ref(true)

function submit() {
  // Never send while IME composition is active (変換確定の Enter を送らない)
  if (composing.value) return
  const line = input.value
  if (!line.trim()) return
  emit('command', line)
  input.value = ''
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
        @keydown.enter.prevent="submit"
        @compositionstart="composing = true"
        @compositionend="composing = false"
      >
    </div>
  </div>
</template>

<style scoped>
.terminal {
  position: relative;
  background: var(--surface-terminal);
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
.input-row {
  display: flex;
  align-items: baseline;
  gap: 0.5ch;
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-2) var(--space-4);
  background: rgba(255, 255, 255, 0.02);
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
  box-shadow: var(--shadow-card);
  cursor: pointer;
}
</style>
