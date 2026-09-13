<script setup lang="ts">
import { computed, ref } from 'vue'
import { commandDetailFor } from '~/utils/commandCatalog'
import type { CodexCommand, CodexError, Fragment } from '~/types/ws'

/*
 * CodexLayer — 捜査道具図鑑 / エラー図鑑（設計指示書 § 11 機能 2・10）。
 * scene の上に重ねる半透明の資料板。独り言（MonologueLayer, z 40）の一つ奥（z 30）に置き、
 * 打ちながら読める（別ページに遷移しない。2026-09-13 ユーザー指示）。
 * 登録はサーバー（result フレームの codex）。ここは表示と切替だけ。
 */
const props = defineProps<{
  open: boolean
  commands: CodexCommand[]
  errors: CodexError[]
  /** 回想（隠しファイル収集。機能 5）。見つけた物だけ */
  fragments: Fragment[]
  fragmentsTotal: number
  /** 直近に登録されたキー（NEW 印） */
  fresh: string[]
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const tab = ref<'tools' | 'errors' | 'fragments'>('errors')
const freshSet = computed(() => new Set(props.fresh))
const tools = computed(() => props.commands.map(c => ({ ...c, detail: commandDetailFor(c.name) })))
</script>

<template>
  <div v-if="open" class="codex" role="region" aria-label="図鑑">
    <div class="head">
      <span class="eyebrow">Dossier · 図鑑</span>
      <div class="tabs">
        <button type="button" :class="{ on: tab === 'errors' }" @click="tab = 'errors'">エラー {{ errors.length }}</button>
        <button type="button" :class="{ on: tab === 'tools' }" @click="tab = 'tools'">道具 {{ commands.length }}</button>
        <button type="button" :class="{ on: tab === 'fragments' }" @click="tab = 'fragments'">回想 {{ fragments.length }}/{{ fragmentsTotal }}</button>
      </div>
      <button type="button" class="close" aria-label="閉じる" @mousedown.prevent @click="emit('close')">×</button>
    </div>

    <ul v-if="tab === 'errors'" class="list">
      <li v-if="errors.length === 0" class="empty">まだ資料は無い。エラーは失敗じゃなく、情報が増えた印。</li>
      <li v-for="e in errors" :key="e.key" :class="{ fresh: freshSet.has(e.key) }">
        <div class="row">
          <code class="key">{{ e.key }}</code>
          <span v-if="freshSet.has(e.key)" class="new">NEW</span>
          <span class="count">×{{ e.count }}</span>
        </div>
        <div class="title">{{ e.title }}</div>
        <p class="text">{{ e.text }}</p>
      </li>
    </ul>

    <ul v-else-if="tab === 'fragments'" class="list">
      <li v-if="fragments.length === 0" class="empty">まだ回想は無い。各部屋に隠されたもの（ls -a）を読むと、ここに集まる。</li>
      <li v-for="f in fragments" :key="f.path">
        <div class="row">
          <code class="key">#{{ f.no }}</code>
          <span class="count">{{ f.path }}</span>
        </div>
        <div class="title">{{ f.title }}</div>
        <p class="text fragment">{{ f.text }}</p>
      </li>
    </ul>

    <ul v-else class="list">
      <li v-if="tools.length === 0" class="empty">まだ道具は無い。使えた道具がここに並ぶ。</li>
      <li v-for="c in tools" :key="c.name" :class="{ fresh: freshSet.has(c.name) }">
        <div class="row">
          <code class="key">{{ c.name }}</code>
          <span v-if="freshSet.has(c.name)" class="new">NEW</span>
          <span class="count">×{{ c.count }}</span>
        </div>
        <div class="title">{{ c.detail.syntax }}</div>
        <p class="text"><b>実機:</b> {{ c.detail.real }}</p>
        <p class="text"><b>捜査:</b> {{ c.detail.inGame }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.codex {
  position: absolute;
  top: var(--space-4);
  left: var(--space-4);
  bottom: var(--space-4);
  width: min(52%, 460px);
  z-index: 30; /* 独り言（40）の一つ奥、クリア演出（45）より下 */
  display: flex;
  flex-direction: column;
  background: rgba(20, 16, 12, 0.86);
  border: 1px solid var(--brass-600);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  color: var(--poster-cream);
  font-family: var(--font-ui);
  backdrop-filter: blur(2px);
}
.head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--brass-600);
}
.eyebrow {
  font-family: var(--font-accent);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  color: var(--brass-400);
  white-space: nowrap;
}
.tabs {
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
}
.tabs button,
.close {
  background: transparent;
  border: 1px solid var(--brass-600);
  color: var(--poster-cream);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  padding: 2px var(--space-2);
  cursor: pointer;
}
.tabs button.on {
  background: rgba(201, 162, 75, 0.18);
  color: var(--brass-400);
}
.list {
  list-style: none;
  margin: 0;
  padding: var(--space-2) var(--space-3);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.list li {
  padding-bottom: var(--space-2);
  border-bottom: 1px dashed rgba(242, 232, 213, 0.18);
}
.list li.fresh {
  border-left: 2px solid var(--poster-mustard);
  padding-left: var(--space-2);
}
.empty {
  color: rgba(242, 232, 213, 0.6);
  font-size: var(--text-sm);
}
.row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.key {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--term-error);
}
.list li.fresh .key,
.tabs + .close {
  color: inherit;
}
.new {
  font-family: var(--font-accent);
  font-size: 10px;
  letter-spacing: var(--tracking-hero);
  color: var(--poster-mustard);
}
.count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(242, 232, 213, 0.5);
}
.title {
  margin-top: 2px;
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--poster-cream);
}
.text {
  margin: 2px 0 0;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: rgba(242, 232, 213, 0.85);
}
.text.fragment {
  font-family: var(--font-narration);
  white-space: pre-line;
}
.text b {
  color: var(--brass-400);
  font-weight: var(--weight-semibold);
}
</style>
