<script setup lang="ts">
/*
 * FieldCard — 現場実習カード（設計指示書 § 11 ゲーム機能 11）。
 * 「同じことを君の本物の PC でやってみろ」のテキストカード。クリア演出（と辞令）の後に発行し、
 * クリア済み Mission のページからいつでも再表示できる。手順は読み取り系の安全なコマンドだけ
 * （文面の正は noir-api/app/content/field_cards.py）。ターミナルの開き方は共通文。
 */
export interface FieldCardStep { cmd: string, note: string }
export interface FieldCardData { lead: string, steps: FieldCardStep[], caution?: string }

defineProps<{
  missionTag: string
  card: FieldCardData
}>()
defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="card" role="dialog" aria-label="現場実習カード">
    <div class="head">
      <span class="eyebrow">Field Practice · 現場実習カード</span>
      <span class="tag">{{ missionTag }}</span>
    </div>
    <p class="lead">同じことを、君の本物の PC でやってみろ。</p>
    <p class="sub">{{ card.lead }}</p>

    <ol class="steps">
      <li v-for="(s, i) in card.steps" :key="i">
        <code class="cmd">{{ s.cmd }}</code>
        <span class="note">{{ s.note }}</span>
      </li>
    </ol>
    <p v-if="card.caution" class="caution">⚠ {{ card.caution }}</p>

    <details class="howto">
      <summary>黒い画面の開き方</summary>
      <ul>
        <li><b>macOS</b>: Spotlight（⌘ + Space）で「ターミナル」と打って Enter。または アプリケーション → ユーティリティ → ターミナル.app</li>
        <li><b>Windows</b>: スタートで「PowerShell」と打って Enter（ここに載せた道具の多くは WSL か Git Bash で動く。WSL は「ターミナル」アプリから Ubuntu を選ぶ）</li>
        <li>打ち終わったら <code>exit</code> か、ウィンドウを閉じるだけ。ここに載せたのは読むだけの道具——何も壊れない</li>
      </ul>
    </details>

    <NoirButton variant="primary" size="lg" @click="$emit('close')">受領した</NoirButton>
  </div>
</template>

<style scoped>
.card {
  width: 520px;
  max-width: 100%;
  max-height: 100%;
  overflow: auto;
  background: var(--poster-cream);
  color: var(--poster-black);
  box-shadow: 6px 6px 0 var(--poster-red), var(--shadow-panel);
  padding: var(--space-5) var(--space-6);
  font-family: var(--font-ui);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.eyebrow {
  font-family: var(--font-accent);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--poster-red);
}
.tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--poster-blue);
}
.lead {
  margin: 0;
  font-family: var(--font-hero);
  font-weight: var(--weight-bold);
  font-size: var(--text-lg);
  line-height: 1.2;
}
.sub {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--poster-blue);
}
.steps {
  margin: 0;
  padding-left: 1.4em;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.cmd {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--poster-black);
  color: var(--green-300);
  padding: 4px 8px;
  white-space: pre-wrap;
  word-break: break-all;
}
.note {
  display: block;
  font-size: var(--text-sm);
  margin-top: 2px;
}
.caution {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--poster-red);
}
.howto {
  font-size: var(--text-sm);
}
.howto summary {
  cursor: pointer;
  color: var(--poster-blue);
}
.howto ul {
  margin: var(--space-2) 0 0;
  padding-left: 1.2em;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
