<script setup lang="ts">
// The upper story scene overlay — French-poster caption band, corner badge and
// an optional centred event card, floated over the scene image (SceneView).
// Poster palette, cream cards with hard drop-shadows.
withDefaults(defineProps<{
  /** cream caption band pinned top-left over the scene */
  caption?: string
  /** scène / chapter badge pinned top-right */
  badge?: string
  /** optional centred event card (drawer contents, clue, etc.) */
  cardTitle?: string
  cardBody?: string
}>(), {
  caption: '',
  badge: '',
  cardTitle: '',
  cardBody: '',
})
</script>

<template>
  <div class="overlay">
    <span v-if="badge" class="scene-badge">{{ badge }}</span>
    <p v-if="caption" class="scene-caption">{{ caption }}</p>

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
  font-family: var(--font-ui);
}
.scene-badge {
  position: absolute;
  top: var(--space-5);
  right: var(--space-5);
  z-index: 2;
  font-family: var(--font-accent);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
  font-size: var(--text-xs);
  color: var(--poster-cream);
  border: 1px solid var(--poster-cream);
  padding: 4px var(--space-3);
}
.scene-caption {
  position: absolute;
  top: var(--space-4);
  left: var(--space-4);
  z-index: 2;
  margin: 0;
  max-width: 60%;
  background: var(--poster-cream);
  color: var(--poster-black);
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-hero);
  font-weight: var(--weight-medium);
  font-size: var(--text-base);
  letter-spacing: 0.02em;
  box-shadow: 4px 4px 0 var(--poster-red);
}
.event-card {
  position: relative;
  z-index: 1;
  width: 74%;
  max-width: 420px;
  background: var(--poster-cream);
  border-radius: 2px;
  box-shadow: 8px 8px 0 rgba(0, 0, 0, 0.4);
  padding: var(--space-5);
  color: var(--poster-black);
}
.event-card h2 {
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
  font-size: var(--text-xl);
  color: var(--poster-red);
  margin: 0 0 var(--space-2);
}
.event-card p {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  margin: 0;
}
</style>
