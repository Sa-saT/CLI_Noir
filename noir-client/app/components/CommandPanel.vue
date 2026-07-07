<script setup lang="ts">
export interface CommandEntry {
  name: string
  state: 'unlocked' | 'highlight' | 'locked'
  /** unlock level label shown on locked rows, e.g. "Lv.3" */
  badge?: string
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
    { name: 'grep', state: 'locked', badge: 'Lv.3' },
    { name: 'awk', state: 'locked', badge: 'Lv.5' },
  ],
})

const emit = defineEmits<{ (e: 'select', name: string): void }>()

const stateIcon = { unlocked: '›', highlight: '★', locked: '☢' } as const

function onSelect(cmd: CommandEntry) {
  if (cmd.state !== 'locked') emit('select', cmd.name)
}
</script>

<template>
  <aside class="panel">
    <div class="panel-head"><span aria-hidden="true">⚙</span>{{ title }}</div>
    <ul>
      <li
        v-for="cmd in commands"
        :key="cmd.name"
        :class="cmd.state"
        @click="onSelect(cmd)"
      >
        <span class="icon">{{ stateIcon[cmd.state] }}</span>
        <span class="cmd-name">{{ cmd.name }}</span>
        <span v-if="cmd.badge" class="badge">{{ cmd.badge }}</span>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.panel {
  width: var(--rail-command-w);
  max-width: 100%;
  background: var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--brass-600);
  background: linear-gradient(180deg, rgba(201, 162, 75, 0.1), transparent);
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--brass-400);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
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
.icon {
  width: 1em;
  text-align: center;
  color: var(--brass-400);
  flex-shrink: 0;
}
li.unlocked {
  color: var(--green-400);
  cursor: pointer;
}
li.unlocked:hover {
  background: rgba(74, 222, 128, 0.08);
  text-shadow: 0 0 8px rgba(74, 222, 128, 0.4);
}
li.highlight {
  color: var(--yellow-300);
  font-weight: var(--weight-bold);
  cursor: pointer;
}
li.highlight:hover {
  background: rgba(253, 224, 71, 0.08);
  text-shadow: 0 0 8px rgba(253, 224, 71, 0.4);
}
li.locked {
  color: var(--cmd-locked);
  filter: grayscale(1);
  cursor: not-allowed;
}
li.locked .icon {
  color: var(--cmd-locked);
}
.badge {
  margin-left: auto;
  font-family: var(--font-ui);
  font-size: var(--text-xs);
  color: var(--text-faint);
  letter-spacing: var(--tracking-caps);
}
</style>
