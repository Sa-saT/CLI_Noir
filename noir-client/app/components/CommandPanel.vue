<script setup lang="ts">
export interface CommandEntry {
  name: string
  state: 'unlocked' | 'highlight' | 'locked'
  /** unlock level label shown on locked rows, e.g. "Lv.3" */
  level?: string
}

withDefaults(defineProps<{
  title?: string
  commands?: CommandEntry[]
}>(), {
  title: '使用可能コマンド',
  commands: () => [
    { name: 'ls', state: 'unlocked' },
    { name: 'cd', state: 'unlocked' },
    { name: 'cat', state: 'unlocked' },
    { name: 'git status', state: 'highlight' },
    { name: 'git push', state: 'highlight' },
    { name: 'grep', state: 'locked', level: 'Lv.3' },
    { name: 'awk', state: 'locked', level: 'Lv.5' },
  ],
})

const emit = defineEmits<{ (e: 'select', name: string): void }>()

function icon(state: CommandEntry['state']) {
  if (state === 'highlight') return '★'
  if (state === 'locked') return '🔒'
  return '›'
}
function onSelect(cmd: CommandEntry) {
  if (cmd.state !== 'locked') emit('select', cmd.name)
}
</script>

<template>
  <aside class="panel">
    <div class="panel-head">{{ title }}</div>
    <ul>
      <li
        v-for="cmd in commands"
        :key="cmd.name"
        :class="cmd.state"
        @click="onSelect(cmd)"
      >
        <span class="icon">{{ icon(cmd.state) }}</span>{{ cmd.name }}
        <span v-if="cmd.level" class="badge">{{ cmd.level }}</span>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.panel {
  width: var(--rail-command-w);
  max-width: 100%;
  background: var(--surface-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  overflow: hidden;
}
.panel-head {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-heading);
  letter-spacing: 0.01em;
}
ul {
  list-style: none;
  margin: 0;
  padding: var(--space-2) 0;
}
li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  cursor: default;
}
li.unlocked {
  color: var(--cmd-unlocked);
  cursor: pointer;
}
li.unlocked:hover {
  background: rgba(74, 222, 128, 0.08);
}
li.highlight {
  color: var(--cmd-highlight);
  font-weight: var(--weight-bold);
  cursor: pointer;
}
li.highlight:hover {
  background: rgba(253, 224, 71, 0.08);
}
li.locked {
  color: var(--cmd-locked);
}
.icon {
  width: 1em;
  text-align: center;
  opacity: 0.8;
}
.badge {
  margin-left: auto;
  font-family: var(--font-ui);
  font-size: var(--text-xs);
  color: var(--text-faint);
  letter-spacing: var(--tracking-caps);
}
</style>
