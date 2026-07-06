<script setup lang="ts">
withDefaults(defineProps<{
  index?: number | string
  title?: string
  subtitle?: string
  rank?: string
}>(), {
  index: 1,
  title: 'Edit Business Card',
  subtitle: '',
  rank: '',
})
</script>

<template>
  <header class="header">
    <div class="title-wrap">
      <span class="mission-tag">Mission {{ index }}</span>
      <h1 class="mission-title">{{ title }}</h1>
      <span v-if="subtitle" class="mission-sub">{{ subtitle }}</span>
    </div>
    <span v-if="rank" class="rank">{{ rank }}</span>
  </header>
</template>

<style scoped>
.header {
  background: linear-gradient(180deg, var(--indigo-700), var(--indigo-600));
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid rgba(0, 0, 0, 0.35);
  box-shadow: var(--shadow-panel);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
}
.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.mission-tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--indigo-300);
}
.mission-title {
  font-family: var(--font-display);
  font-weight: var(--weight-bold);
  font-size: var(--text-2xl);
  color: #fff;
  margin: 0;
  line-height: var(--leading-tight);
}
.mission-sub {
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.8);
}
.rank {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  color: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-sm);
  padding: 2px var(--space-2);
  white-space: nowrap;
}
</style>
