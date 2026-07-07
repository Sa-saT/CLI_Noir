<script setup lang="ts">
// Poster-style mission title band — 60s French film-poster treatment: black
// ground, skewed red cut-out, Jost hero title, Josefin accent tag, brass rank chip.
withDefaults(defineProps<{
  tag?: string
  title?: string
  subtitle?: string
  rank?: string
}>(), {
  tag: 'Mission 1',
  title: 'Edit Business Card',
  subtitle: '',
  rank: '',
})
</script>

<template>
  <header class="header">
    <div class="cutout" aria-hidden="true" />
    <div class="title-wrap">
      <span class="mission-tag">{{ tag }}</span>
      <h1 class="mission-title">{{ title }}</h1>
      <span v-if="subtitle" class="mission-sub">{{ subtitle }}</span>
    </div>
    <span v-if="rank" class="rank">{{ rank }}</span>
  </header>
</template>

<style scoped>
.header {
  position: relative;
  overflow: hidden;
  background: var(--poster-black);
  padding: var(--space-5) var(--space-6);
  border-bottom: 2px solid var(--poster-red);
  box-shadow: var(--shadow-panel);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}
.cutout {
  position: absolute;
  top: -20%;
  left: -4%;
  width: 120px;
  height: 140%;
  background: var(--poster-red);
  transform: skewX(-12deg);
  opacity: 0.9;
}
.title-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.mission-tag {
  font-family: var(--font-accent);
  font-weight: var(--weight-medium);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--poster-mustard);
}
.mission-title {
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  font-size: 2.5rem;
  line-height: 0.95;
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
  color: var(--poster-cream);
  margin: 0;
}
.mission-sub {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--poster-red);
  background: var(--poster-black);
  padding: 1px 8px;
  align-self: flex-start;
}
.rank {
  position: relative;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  color: var(--brass-400);
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-sm);
  box-shadow: var(--glow-brass);
  padding: 3px var(--space-2);
  white-space: nowrap;
  background: rgba(201, 162, 75, 0.06);
}
</style>
