<script setup lang="ts">
// Rank-up decree — an art-deco award certificate. Distinct from the game's
// poster scene and cyberpunk panels: cream paper, a fine double-rule brass
// frame with corner ticks, centred engraved typography, and a brass wax seal.
withDefaults(defineProps<{
  eyebrow?: string
  title?: string
  body?: string
  from?: string
  to?: string
  unlocks?: string[]
}>(), {
  eyebrow: '辞 令 · Décret',
  title: '昇格',
  body: '貴殿の捜査手腕を認め、下記の通り任ずる。',
  from: 'Lv.2 捜査補',
  to: 'Lv.3 探偵',
  unlocks: () => ['grep', 'find', 'head / tail'],
})
</script>

<template>
  <div class="decree">
    <div class="frame f1" aria-hidden="true" />
    <div class="frame f2" aria-hidden="true" />
    <span class="corner tl" aria-hidden="true" />
    <span class="corner tr" aria-hidden="true" />
    <span class="corner bl" aria-hidden="true" />
    <span class="corner br" aria-hidden="true" />

    <div class="inner">
      <div class="eyebrow">{{ eyebrow }}</div>
      <div class="title-rule">
        <span class="rule left" />
        <span class="title">{{ title }}</span>
        <span class="rule right" />
      </div>
      <p class="body">{{ body }}</p>

      <div v-if="from || to" class="rank-line">
        {{ from }} <span class="arrow">→ {{ to }}</span>
      </div>

      <template v-if="unlocks.length">
        <p class="unlock-eyebrow">Nouvelles commandes</p>
        <div class="unlocks">
          <span v-for="cmd in unlocks" :key="cmd" class="chip">{{ cmd }}</span>
        </div>
      </template>

      <div class="seal" aria-hidden="true">⚙</div>
    </div>
  </div>
</template>

<style scoped>
.decree {
  position: relative;
  width: 460px;
  max-width: 100%;
  margin: 0 auto;
  background: linear-gradient(180deg, var(--sepia-100), var(--poster-cream));
  color: var(--poster-black);
  box-shadow: var(--shadow-panel);
  padding: var(--space-8) var(--space-8) var(--space-6);
  border: 1px solid var(--brass-600);
  text-align: center;
}
.frame {
  position: absolute;
  pointer-events: none;
}
.f1 {
  inset: 10px;
  border: 1px solid var(--brass-600);
}
.f2 {
  inset: 14px;
  border: 1px solid rgba(138, 109, 47, 0.4);
}
.corner {
  position: absolute;
  width: 14px;
  height: 14px;
  border-color: var(--brass-600);
  border-style: solid;
  border-width: 0;
}
.corner.tl {
  top: 6px;
  left: 6px;
  border-width: 2px 0 0 2px;
}
.corner.tr {
  top: 6px;
  right: 6px;
  border-width: 2px 2px 0 0;
}
.corner.bl {
  bottom: 6px;
  left: 6px;
  border-width: 0 0 2px 2px;
}
.corner.br {
  bottom: 6px;
  right: 6px;
  border-width: 0 2px 2px 0;
}
.inner {
  position: relative;
}
.eyebrow {
  font-family: var(--font-accent);
  font-size: var(--text-xs);
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--brass-600);
}
.title-rule {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}
.title {
  font-family: var(--font-display);
  font-weight: var(--weight-bold);
  font-size: var(--text-2xl);
  letter-spacing: 0.04em;
  color: var(--poster-black);
}
.rule {
  flex: 1;
  height: 1px;
}
.rule.left {
  background: linear-gradient(90deg, transparent, var(--brass-600));
}
.rule.right {
  background: linear-gradient(270deg, transparent, var(--brass-600));
}
.body {
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--sepia-900);
  margin: 0;
}
.rank-line {
  margin: var(--space-4) 0 var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-base);
  color: var(--poster-black);
}
.arrow {
  color: var(--copper-600);
  font-weight: var(--weight-bold);
}
.unlock-eyebrow {
  font-family: var(--font-accent);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--sepia-700);
  margin: var(--space-4) 0 var(--space-3);
}
.unlocks {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
}
.chip {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  padding: 4px var(--space-3);
  background: transparent;
  color: var(--sepia-900);
  border: 1px solid var(--brass-600);
}
.seal {
  margin: var(--space-5) auto 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 35% 30%, var(--brass-400), var(--brass-600));
  color: var(--sepia-900);
  font-size: 20px;
  box-shadow: var(--glow-brass), inset 0 0 6px rgba(0, 0, 0, 0.4);
}
</style>
