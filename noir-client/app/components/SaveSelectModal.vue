<script setup lang="ts">
import { ref } from 'vue'

// Save-select modal — on re-login, pick a git commit (save point) to resume
// from. Brass-trimmed cyberpunk panel; each row shows hash, message, timestamp.
export interface SaveEntry {
  hash: string
  message: string
  when: string
  latest?: boolean
}

const props = withDefaults(defineProps<{
  title?: string
  subtitle?: string
  saves?: SaveEntry[]
}>(), {
  title: 'セーブを選んで再開',
  subtitle: 'Mission 3 — 記録された commit から選択してください',
  saves: () => [
    { hash: 'a1f9c2e', message: '桟橋の足跡を照合', when: '2026-07-05 23:41', latest: true },
    { hash: '7bd0410', message: 'ssh amusement_park に接続', when: '2026-07-05 23:12' },
    { hash: '3e5aa88', message: 'case_file.sh を実行', when: '2026-07-05 22:58' },
  ],
})

const emit = defineEmits<{
  (e: 'resume', hash: string): void
  (e: 'start-over'): void
}>()

const selected = ref(props.saves.find(s => s.latest)?.hash ?? props.saves[0]?.hash ?? '')
</script>

<template>
  <div class="modal">
    <div class="modal-head">
      <h2>{{ title }}</h2>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <ul>
      <li
        v-for="s in saves"
        :key="s.hash"
        :class="{ selected: s.hash === selected }"
        @click="selected = s.hash"
      >
        <span class="hash">{{ s.hash }}</span>
        <span class="msg">
          <span class="title">{{ s.message }}</span>
          <span class="when">{{ s.when }}</span>
        </span>
        <span v-if="s.latest" class="latest">最新</span>
      </li>
    </ul>
    <div class="modal-foot">
      <NoirButton variant="ghost" @click="emit('start-over')">最初から</NoirButton>
      <NoirButton variant="primary" @click="emit('resume', selected)">このセーブで再開</NoirButton>
    </div>
  </div>
</template>

<style scoped>
.modal {
  width: 480px;
  max-width: 100%;
  margin: 0 auto;
  background: var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900));
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  overflow: hidden;
  font-family: var(--font-ui);
}
.modal-head {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--brass-600);
  background: linear-gradient(180deg, rgba(201, 162, 75, 0.08), transparent);
}
.modal-head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--brass-400);
}
.modal-head p {
  margin: 4px 0 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}
ul {
  list-style: none;
  margin: 0;
  padding: var(--space-2);
}
li {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  border: 1px solid transparent;
}
li:hover {
  background: rgba(255, 255, 255, 0.03);
}
li.selected {
  background: rgba(99, 102, 241, 0.12);
  border-color: var(--accent);
  box-shadow: var(--glow-indigo);
}
.hash {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--cyan-400);
}
.msg {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.msg .title {
  font-size: var(--text-sm);
  color: var(--text-body);
}
.msg .when {
  font-size: var(--text-xs);
  color: var(--text-faint);
  font-family: var(--font-mono);
}
.latest {
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  color: var(--term-warn);
  border: 1px solid var(--term-warn);
  border-radius: var(--radius-sm);
  padding: 1px var(--space-2);
}
.modal-foot {
  padding: var(--space-3) var(--space-5);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  border-top: 1px solid var(--border-subtle);
}
</style>
