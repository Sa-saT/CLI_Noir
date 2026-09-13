<script setup lang="ts">
/*
 * ReplayLedger — リプレイ台帳（設計指示書 § 11 ゲーム機能 8）。
 * その Mission で自分が打った（成功した）コマンドを実行順に読み返す。復習 = LPIC 対策。
 * 台帳の本文はサーバー（GET /api/missions/{id}/replay/）。ここは表示のみ。
 */
export interface ReplayEntry { n: number, line: string }
export interface ReplayScore { commands: number, par: number, bonuses: string[], score: number, elapsed_seconds: number | null }

defineProps<{
  missionTag: string
  commands: ReplayEntry[]
  score: ReplayScore | null
}>()
defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="ledger" role="dialog" aria-label="リプレイ台帳">
    <div class="head">
      <span class="eyebrow">Ledger · リプレイ台帳</span>
      <span class="tag">{{ missionTag }}</span>
      <button type="button" class="close" aria-label="閉じる" @click="$emit('close')">×</button>
    </div>
    <p v-if="score" class="score">
      {{ score.commands }} 手 / 目安 {{ score.par }} 手 · {{ score.score }} pt
      <span v-for="b in score.bonuses" :key="b" class="bonus">{{ b }}</span>
    </p>
    <ol v-if="commands.length" class="lines">
      <li v-for="c in commands" :key="c.n">
        <span class="n">{{ String(c.n).padStart(3, ' ') }}</span>
        <code class="cmd">{{ c.line }}</code>
      </li>
    </ol>
    <p v-else class="empty">この事件で打ったコマンドはまだ無い。</p>
    <p class="foot">成功したコマンドだけが載る。失敗した試行はエラー図鑑に。</p>
  </div>
</template>

<style scoped>
.ledger {
  width: 560px;
  max-width: 100%;
  max-height: 100%;
  overflow: auto;
  background: rgba(20, 16, 12, 0.94);
  color: var(--poster-cream);
  border: 1px solid var(--brass-600);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  padding: var(--space-4) var(--space-5);
  font-family: var(--font-ui);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.eyebrow {
  font-family: var(--font-accent);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--brass-400);
}
.tag {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--poster-mustard);
}
.close {
  background: transparent;
  border: 1px solid var(--brass-600);
  color: var(--poster-cream);
  font-family: var(--font-mono);
  cursor: pointer;
  padding: 0 var(--space-2);
}
.score {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--brass-400);
  letter-spacing: var(--tracking-caps);
}
.bonus {
  margin-left: var(--space-2);
  color: var(--poster-mustard);
}
.lines {
  margin: 0;
  padding: 0;
  list-style: none;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.n {
  color: rgba(242, 232, 213, 0.45);
  white-space: pre;
  margin-right: var(--space-3);
}
.cmd {
  color: var(--green-300);
  white-space: pre-wrap;
  word-break: break-all;
}
.empty,
.foot {
  margin: 0;
  font-size: var(--text-xs);
  color: rgba(242, 232, 213, 0.6);
}
</style>
