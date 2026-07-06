<script setup lang="ts">
withDefaults(defineProps<{
  /** the text band pinned over the scene */
  caption?: string
  /** optional centred event card (drawer contents, clue, etc.) */
  cardTitle?: string
  cardBody?: string
}>(), {
  caption: '',
  cardTitle: '',
  cardBody: '',
})
</script>

<template>
  <div class="overlay">
    <p v-if="caption" class="overlay-text">{{ caption }}</p>

    <div v-if="cardTitle" class="event-card">
      <h2>{{ cardTitle }}</h2>
      <p v-if="cardBody">{{ cardBody }}</p>
      <slot />
    </div>

    <slot v-else name="loose" />
  </div>
</template>

<style scoped>
.overlay {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}
.overlay-text {
  position: absolute;
  top: var(--space-4);
  left: var(--space-4);
  margin: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  max-width: 60%;
}
.event-card {
  width: 74%;
  max-width: 420px;
  background: var(--surface-card);
  border: 2px solid var(--accent);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  padding: var(--space-4);
  color: var(--text-body);
}
.event-card h2 {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--accent-quiet);
  margin: 0 0 var(--space-2);
}
.event-card p {
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  margin: 0;
}
</style>
