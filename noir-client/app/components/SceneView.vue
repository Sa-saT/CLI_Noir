<script setup lang="ts">
withDefaults(defineProps<{
  /** background image url; falls back to the noir sepia wash when empty */
  imageUrl?: string
  /** drives the 0.8s fade used on ssh / exit / clear transitions */
  fading?: boolean
}>(), {
  imageUrl: '',
  fading: false,
})
</script>

<template>
  <section class="scene">
    <div
      class="bg"
      :class="{ 'fade-hide': fading }"
      :style="imageUrl ? { backgroundImage: `url('${imageUrl}')` } : undefined"
      :data-fallback="imageUrl ? undefined : ''"
    />
    <div class="content">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.scene {
  position: relative;
  height: 100%;
  min-height: var(--scene-min-h);
  overflow: hidden;
  background: var(--poster-black);
}
.bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transition: opacity 0.8s ease-in-out;
  opacity: 1;
}
.bg[data-fallback] {
  background-image:
    radial-gradient(110% 80% at 70% 25%, rgba(217, 165, 33, 0.2), transparent 55%),
    linear-gradient(155deg, var(--poster-blue) 0%, var(--poster-black) 62%);
}
.bg[data-fallback]::before {
  content: '';
  position: absolute;
  top: -12%;
  left: -6%;
  width: 48%;
  height: 124%;
  background: var(--poster-red);
  transform: skewX(-10deg);
  opacity: 0.88;
  -webkit-mask-image: radial-gradient(circle at 22% 32%, #000 40%, transparent 41%);
  mask-image: radial-gradient(circle at 22% 32%, #000 40%, transparent 41%);
}
.fade-hide {
  opacity: 0;
}
.content {
  position: relative;
  z-index: 1;
  height: 100%;
}
</style>
