<script setup lang="ts">
withDefaults(defineProps<{
  name?: string
  syntax?: string
  /** real-world meaning of the command */
  real?: string
  /** in-game meaning for the current case */
  game?: string
}>(), {
  name: 'grep',
  syntax: 'grep [オプション] "パターン" ファイル',
  real: 'ファイルの中から指定した文字列を含む行だけを抜き出す。捜査でいう「証言の中からキーワードを拾う」操作。',
  game: '名簿 witnesses.txt から容疑者の名前を含む行を探し出し、アリバイの矛盾を突く。',
})
</script>

<template>
  <div class="detail">
    <p class="name">{{ name }}</p>
    <p class="syntax">{{ syntax }}</p>
    <div class="block">
      <div class="label">実際のPCでは</div>
      <p class="body">{{ real }}</p>
    </div>
    <div class="block">
      <div class="label game">この事件では</div>
      <p class="body">{{ game }}</p>
    </div>
  </div>
</template>

<style scoped>
.detail {
  width: var(--rail-command-w);
  max-width: 100%;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-4);
}
.name {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  color: var(--accent-quiet);
  font-weight: var(--weight-bold);
  margin: 0 0 2px;
}
.syntax {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: var(--space-3);
}
.block {
  margin-top: var(--space-3);
}
.label {
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: 2px;
}
.label.game {
  color: var(--term-warn);
}
.body {
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--text-body);
  margin: 0;
}
</style>
