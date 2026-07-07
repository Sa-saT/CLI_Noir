<script setup lang="ts">
// CLI_Noir action button — cyberpunk indigo glow (primary), steampunk brass
// trim (secondary), neon-hover ghost. Three variants × two sizes.
withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'md' | 'lg'
  disabled?: boolean
}>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
})
defineEmits<{ (e: 'click', ev: MouseEvent): void }>()
</script>

<template>
  <button
    class="btn"
    :class="[`btn-${variant}`, size === 'lg' && 'btn-lg']"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.btn {
  font-family: var(--font-ui);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease,
    box-shadow 0.15s ease, transform 0.08s ease;
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
}
.btn-lg {
  padding: var(--space-3) var(--space-6);
  font-size: var(--text-base);
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  box-shadow: var(--bezel-brass), var(--glow-indigo);
}
.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: var(--bezel-brass), var(--glow-indigo), 0 0 28px rgba(99, 102, 241, 0.35);
}
.btn-secondary {
  background: var(--surface-panel);
  color: var(--text-body);
  border-color: var(--brass-600);
}
.btn-secondary:hover:not(:disabled) {
  border-color: var(--brass-400);
  color: var(--brass-400);
  box-shadow: var(--glow-brass);
}
.btn-ghost {
  background: transparent;
  color: var(--accent-quiet);
}
.btn-ghost:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.12);
  color: var(--cyan-400);
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.5);
}
.btn:active:not(:disabled) {
  transform: translateY(1px);
}
.btn:disabled {
  opacity: 0.4;
  box-shadow: none;
  filter: grayscale(0.3);
  cursor: not-allowed;
}
</style>
