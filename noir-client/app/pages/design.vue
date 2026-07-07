<script setup lang="ts">
import { ref } from 'vue'
import type { TerminalLine } from '~/components/TerminalView.vue'

// Static sample data for the gallery previews.
const termLines = ref<TerminalLine[]>([
  { id: 1, source: 'system', text: '-- reconnected --' },
  { id: 2, source: 'out', text: 'Welcome, Detective. Mission 1: Edit Business Card' },
  { id: 3, source: 'input', text: 'ls', prompt: { user: 'detective', host: 'office', path: '/root/desk' } },
  { id: 4, source: 'out', text: 'businesscard.txt  notes/  case_file.sh' },
  { id: 5, source: 'input', text: 'rm businesscard.txt', prompt: { user: 'detective', host: 'office', path: '/root/desk' } },
  { id: 6, source: 'error', text: 'Error: command not allowed' },
  { id: 7, source: 'input', text: 'git push', prompt: { user: 'detective', host: 'office', path: '/root/desk' } },
  { id: 8, source: 'warn', text: 'Warning: nothing staged — run `git add` first' },
])
</script>

<template>
  <main class="gallery">
    <header class="head">
      <p class="eyebrow">CLI_Noir — Design System</p>
      <h1>コンポーネントギャラリー</h1>
      <p class="lead">docs/design-system の各コンポーネントを Nuxt 実装として一覧表示。<NuxtLink to="/">→ Mission1 画面デモ</NuxtLink></p>
    </header>

    <section class="group">
      <h2>Terminal</h2>
      <div class="card term-card">
        <TerminalView :lines="termLines" :prompt="{ user: 'detective', host: 'office', path: '/root/desk' }" />
      </div>
      <div class="card dark">
        <div class="stack">
          <PromptLabel user="detective" host="office" path="/root/desk" :caret="true" />
          <PromptLabel user="detective" host="amusement_park" path="/gate" host-type="remote" />
          <PromptLabel user="barman" host="office" path="/bar" host-type="su" />
        </div>
      </div>
    </section>

    <section class="group">
      <h2>Panels</h2>
      <div class="row">
        <div class="card"><CommandPanel /></div>
        <div class="card"><CommandDetail /></div>
      </div>
    </section>

    <section class="group">
      <h2>Scene</h2>
      <div class="card no-pad">
        <MissionHeader tag="Mission 1" title="Edit Business Card" subtitle="依頼人の名刺を書き換えろ" rank="Lv.1 見習い" />
      </div>
      <div class="card no-pad scene-card">
        <SceneView image-url="/images/office.png">
          <SceneOverlay
            caption="机の引き出しを調べ、businesscard.txt を見つけろ…"
            card-title="引き出しの中身"
            card-body="色褪せた名刺が一枚。裏に走り書き —「22時、桟橋。金は持ってきたか」。"
          />
        </SceneView>
      </div>
    </section>

    <section class="group">
      <h2>Feedback</h2>
      <div class="card no-pad scene-card"><ClearEffect /></div>
      <div class="row">
        <div class="card"><RankUpEffect /></div>
        <div class="card"><SaveSelectModal /></div>
      </div>
    </section>

    <section class="group">
      <h2>Primitives</h2>
      <div class="card">
        <div class="btn-row">
          <NoirButton variant="primary">保存する</NoirButton>
          <NoirButton variant="primary" size="lg">次のミッションへ</NoirButton>
          <NoirButton variant="secondary">閉じる</NoirButton>
          <NoirButton variant="ghost">ヒントを見る</NoirButton>
          <NoirButton variant="primary" :disabled="true">保存する</NoirButton>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.gallery {
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-16);
}
.head {
  margin-bottom: var(--space-10);
}
.eyebrow {
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--text-faint);
  margin: 0;
}
.head h1 {
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  color: var(--text-heading);
  margin: var(--space-2) 0;
}
.lead {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.group {
  margin-bottom: var(--space-10);
}
.group > h2 {
  font-size: var(--text-sm);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--accent-quiet);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: var(--space-2);
  margin-bottom: var(--space-4);
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: flex-start;
}
.card {
  background: var(--surface-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  margin-bottom: var(--space-4);
}
.card.no-pad {
  padding: 0;
  overflow: hidden;
}
.card.dark {
  background: var(--surface-terminal);
}
.term-card {
  height: 320px;
  padding: 0;
  overflow: hidden;
}
.scene-card {
  height: 300px;
}
.scene-card :deep(section),
.scene-card > * {
  height: 100%;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}
</style>
