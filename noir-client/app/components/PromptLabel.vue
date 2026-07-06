<script setup lang="ts">
export interface PromptState {
  user: string
  host: string
  path: string
  /** remote (ssh) session — host turns yellow */
  remote?: boolean
}

withDefaults(defineProps<PromptState>(), {
  user: 'detective',
  host: 'office',
  path: '/root',
  remote: false,
})
</script>

<template>
  <span class="prompt">
    <span class="user">{{ user }}</span><span class="d">@</span><span
      class="host"
      :class="remote ? 'remote' : 'local'"
    >{{ host }}</span><span class="d">:</span><span class="path">{{ path }}</span>
    <span class="d">$</span>
  </span>
</template>

<style scoped>
.prompt {
  font-family: var(--font-mono);
  white-space: nowrap;
}
.user {
  color: var(--green-300);
}
.d {
  color: var(--text-muted);
}
.host.local {
  color: var(--gray-300);
}
.host.remote {
  color: var(--yellow-300);
}
.path {
  color: var(--indigo-300);
}
</style>
