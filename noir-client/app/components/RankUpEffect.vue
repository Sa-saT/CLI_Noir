<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  fromRank?: string
  toRank?: string
  unlocks?: string[]
}>(), {
  title: '昇格',
  fromRank: 'Lv.2 捜査補',
  toRank: 'Lv.3 探偵',
  unlocks: () => ['grep', 'find', 'head / tail'],
})
</script>

<template>
  <div class="decree">
    <div class="decree-eyebrow">辞 令</div>
    <div class="decree-title">{{ title }}</div>
    <p class="decree-body">貴殿の捜査手腕を認め、下記の通り任ずる。</p>
    <div class="rank-line"><b>{{ fromRank }}</b> → <b>{{ toRank }}</b></div>
    <p v-if="unlocks.length" class="decree-body">新たに以下のコマンドが解放された。</p>
    <div v-if="unlocks.length" class="unlocks">
      <span v-for="cmd in unlocks" :key="cmd" class="chip">{{ cmd }}</span>
    </div>
  </div>
</template>

<style scoped>
.decree {
  width: 460px;
  max-width: 100%;
  margin: 0 auto;
  background: linear-gradient(180deg, var(--sepia-100), var(--sepia-300));
  color: var(--sepia-900);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-panel);
  padding: var(--space-6);
  border: 1px solid var(--sepia-500);
  text-align: center;
}
.decree-eyebrow {
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--sepia-700);
}
.decree-title {
  font-family: var(--font-display);
  font-weight: var(--weight-bold);
  font-size: var(--text-2xl);
  margin: var(--space-2) 0;
}
.decree-body {
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}
.rank-line {
  margin: var(--space-4) 0;
  font-family: var(--font-mono);
  font-size: var(--text-base);
}
.rank-line b {
  color: var(--indigo-700);
}
.unlocks {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
  margin-top: var(--space-4);
}
.chip {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3);
  border-radius: 999px;
  background: var(--gray-900);
  color: var(--green-400);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.5);
}
</style>
