<script setup lang="ts">
export type HostType = 'local' | 'remote' | 'su'

export interface PromptState {
  user: string
  host: string
  path: string
  /** local (grey) · remote/ssh (yellow glow) · su (grey, other user) */
  hostType?: HostType
}

withDefaults(defineProps<PromptState & { caret?: boolean }>(), {
  user: 'detective',
  host: 'office',
  path: '/root',
  hostType: 'local',
  caret: false,
})
</script>

<template>
  <span class="prompt">
    <span class="user">{{ user }}</span><span class="d">@</span><span
      class="host"
      :class="hostType"
    >{{ host }}</span><span class="d">:</span><span class="path">{{ path }}</span>
    <span class="d">$</span>
    <span v-if="caret" class="caret" aria-hidden="true" />
  </span>
</template>

<style scoped>
.prompt {
  font-family: var(--font-mono);
  letter-spacing: var(--tracking-term);
  white-space: nowrap;
  display: inline-flex;
  align-items: baseline;
  gap: 0.5ch;
}
.user {
  color: var(--green-300);
}
.d {
  color: var(--text-muted);
}
.host.local,
.host.su {
  color: var(--gray-300);
}
.host.remote {
  color: var(--yellow-300);
  text-shadow: 0 0 8px rgba(253, 224, 71, 0.4);
}
.path {
  color: var(--indigo-300);
}
.caret {
  display: inline-block;
  width: 0.6ch;
  height: 1.1em;
  margin-left: 0.3ch;
  background: var(--green-400);
  box-shadow: var(--shadow-glow-term);
  animation: clinoir-blink 1.1s step-end infinite;
  transform: translateY(2px);
}
@keyframes clinoir-blink {
  50% {
    opacity: 0;
  }
}
</style>
