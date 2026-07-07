<script setup lang="ts">
// Mission-complete celebration — emerald glow stage with a Jost stamp, a mono
// subline (e.g. the commit that closed the case) and a next-mission CTA.
withDefaults(defineProps<{
  stamp?: string
  sub?: string
  ctaLabel?: string
}>(), {
  stamp: 'Mission Complete!',
  sub: '$ git push — case closed. snapshot saved.',
  ctaLabel: '次のミッションへ →',
})
defineEmits<{ (e: 'next'): void }>()
</script>

<template>
  <div class="stage">
    <div class="stamp">{{ stamp }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
    <NoirButton variant="primary" size="lg" @click="$emit('next')">{{ ctaLabel }}</NoirButton>
  </div>
</template>

<style scoped>
.stage {
  position: relative;
  height: 100%;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-5);
  text-align: center;
  background: radial-gradient(120% 100% at 50% 40%, rgba(16, 185, 129, 0.18), var(--gray-950) 70%);
}
.stamp {
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-hero);
  font-size: var(--text-display);
  color: #6ee7b7;
  text-shadow: 0 0 24px rgba(16, 185, 129, 0.6);
}
.sub {
  color: #a7f3d0;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}
</style>
