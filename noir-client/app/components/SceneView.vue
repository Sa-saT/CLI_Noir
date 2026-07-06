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
  background: var(--gray-700);
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
    radial-gradient(120% 90% at 30% 20%, rgba(201, 177, 143, 0.18), transparent 60%),
    linear-gradient(160deg, var(--sepia-700), var(--sepia-900) 70%, #000);
}
.bg[data-fallback]::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.12;
  background-image: repeating-linear-gradient(35deg, #000 0 1px, transparent 1px 5px);
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
