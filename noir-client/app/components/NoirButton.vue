<script setup lang="ts">
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
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
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
}
.btn-primary:hover {
  background: var(--accent-hover);
}
.btn-secondary {
  background: var(--surface-panel);
  color: var(--text-body);
  border-color: var(--border-strong);
}
.btn-secondary:hover {
  border-color: var(--accent-quiet);
  color: var(--text-heading);
}
.btn-ghost {
  background: transparent;
  color: var(--accent-quiet);
}
.btn-ghost:hover {
  background: rgba(99, 102, 241, 0.12);
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
