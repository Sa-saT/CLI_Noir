<script setup lang="ts">
import { ref, watch } from 'vue'

// The upper story scene — CLI_Noir's first-class "current image" area. Each
// scene shows a full-bleed illustration (object-fit: cover) as the ground; the
// poster caption band, Scène badge and optional event card are overlaid on top.
// No `image` → poster-gradient placeholder. 0.8s cross-fade on scene change
// (local⇄remote / ssh in / exit out); `fading` forces a scripted fade-out.
const props = withDefaults(defineProps<{
  /** scene illustration URL — swaps per location (自室 / ssh 先など) */
  image?: string
  /** force a fade-out for a scripted transition */
  fading?: boolean
  /** cream caption band pinned top-left over the scene */
  caption?: string
  /** scène / chapter badge pinned top-right */
  badge?: string
  /** optional centred event card */
  cardTitle?: string
  cardBody?: string
  /** CSS height (fills its grid cell by default) */
  height?: string
}>(), {
  image: '',
  fading: false,
  caption: '',
  badge: '',
  cardTitle: '',
  cardBody: '',
  height: '100%',
})

// Cross-fade whenever the image URL changes.
const shown = ref(props.image)
const visible = ref(true)
watch(() => props.image, (img) => {
  if (img === shown.value) return
  visible.value = false
  window.setTimeout(() => {
    shown.value = img
    visible.value = true
  }, 800)
})
</script>

<template>
  <div class="scene" :style="{ height }">
    <img
      v-if="shown"
      class="ground"
      :class="{ hide: !visible || fading }"
      :src="shown"
      alt=""
      aria-hidden="true"
    >
    <div v-else class="placeholder" aria-hidden="true" />

    <div v-if="shown" class="scrim" aria-hidden="true" />

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
.scene {
  position: relative;
  overflow: hidden;
  min-height: var(--scene-min-h);
  border-radius: var(--radius-lg);
  border: 1px solid var(--brass-600);
  box-shadow: var(--bezel-brass);
  /* placeholder ground: shows through during fades and when no image */
  background:
    radial-gradient(110% 80% at 72% 30%, rgba(217, 165, 33, 0.22), transparent 55%),
    linear-gradient(155deg, var(--poster-blue) 0%, var(--poster-black) 62%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
}
.ground {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 1;
  transition: opacity 0.8s ease;
  z-index: 0;
}
.ground.hide {
  opacity: 0;
}
.placeholder {
  position: absolute;
  top: -10%;
  left: -8%;
  width: 55%;
  height: 120%;
  background: var(--poster-red);
  transform: skewX(-10deg);
  opacity: 0.9;
  -webkit-mask-image: radial-gradient(circle at 20% 30%, #000 42%, transparent 43%);
  mask-image: radial-gradient(circle at 20% 30%, #000 42%, transparent 43%);
  z-index: 0;
}
.scrim {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(20, 16, 12, 0.35) 0%, transparent 30%, rgba(20, 16, 12, 0.45) 100%);
}
.scene-badge {
  position: absolute;
  top: var(--space-5);
  right: var(--space-5);
  z-index: 3;
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
  z-index: 3;
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
  z-index: 2;
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
