<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  sub?: string
  ctaLabel?: string
}>(), {
  title: 'Mission Complete!',
  sub: '$ git push — case closed. snapshot saved.',
  ctaLabel: '次の Mission へ →',
})
defineEmits<{ (e: 'next'): void }>()
</script>

<template>
  <div class="stage">
    <div class="stamp">{{ title }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
    <button class="cta" @click="$emit('next')">{{ ctaLabel }}</button>
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
  font-family: var(--font-display);
  font-weight: var(--weight-bold);
  font-size: var(--text-display);
  color: #6ee7b7;
  letter-spacing: 0.01em;
  text-shadow: 0 0 24px rgba(16, 185, 129, 0.5);
}
.sub {
  color: #a7f3d0;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}
.cta {
  background: var(--accent);
  color: #fff;
  border: none;
  cursor: pointer;
  font-family: var(--font-ui);
  font-weight: var(--weight-semibold);
  font-size: var(--text-base);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}
.cta:hover {
  background: var(--accent-hover);
}
</style>
