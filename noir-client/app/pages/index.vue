<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { TerminalLine } from '~/components/TerminalView.vue'
import type { PromptState } from '~/components/PromptLabel.vue'
import type { CommandEntry } from '~/components/CommandPanel.vue'

/*
 * Mission 1 — composed game screen (design implementation demo).
 * The evaluator below is a LOCAL STAND-IN so the UI is playable without a
 * backend. Per 設計指示書 § 2 / DESIGN.md § 10, real state + clear judgement
 * come from the WebSocket evaluator — this mock is UI-only scaffolding.
 */

const prompt = reactive<PromptState>({
  user: 'detective',
  host: 'office',
  path: '/root/desk',
  remote: false,
})

let nextId = 1
const lines = ref<TerminalLine[]>([
  { id: nextId++, source: 'out', text: 'Welcome, Detective. Mission 1: Edit Business Card' },
  { id: nextId++, source: 'system', text: 'ヒント: ls で周囲を調べ、businesscard.txt を書き換えろ。' },
])

const commands = ref<CommandEntry[]>([
  { name: 'ls', state: 'unlocked' },
  { name: 'cd', state: 'unlocked' },
  { name: 'cat', state: 'unlocked' },
  { name: 'echo', state: 'unlocked' },
  { name: 'git status', state: 'highlight' },
  { name: 'git add', state: 'highlight' },
  { name: 'git commit', state: 'highlight' },
  { name: 'git push', state: 'highlight' },
  { name: 'grep', state: 'locked', level: 'Lv.3' },
  { name: 'awk', state: 'locked', level: 'Lv.5' },
])

const details: Record<string, { syntax: string, real: string, game: string }> = {
  ls: { syntax: 'ls [パス]', real: 'そのディレクトリにあるファイル・フォルダを一覧する。', game: '今いる部屋にある手がかりを見回す。' },
  cd: { syntax: 'cd <パス>', real: '作業ディレクトリを移動する。', game: '別の部屋・引き出しへ移動する。' },
  cat: { syntax: 'cat <ファイル>', real: 'ファイルの中身を表示する。', game: '書類や手紙を読む。' },
  echo: { syntax: 'echo "文字列" > <ファイル>', real: '文字列を出力し、> でファイルへ書き込む。', game: '名刺の記載を書き換える（このミッションの本命）。' },
  'git status': { syntax: 'git status', real: '作業ツリーの変更状態を確認する。', game: '証拠の提出準備がどこまで整ったか確認する。' },
  'git add': { syntax: 'git add <ファイル>', real: '変更をステージに載せる。', game: '提出する証拠を封筒に入れる（提出前の必須手順）。' },
  'git commit': { syntax: 'git commit -m "..."', real: '変更を記録する。', game: 'ゲームのセーブ。何度でも可能。' },
  'git push': { syntax: 'git push', real: 'コミットをリモートへ送る。', game: 'クリア判定。最新セーブの内容で合否が出る。' },
}

const selected = ref<string>('')
const detail = ref<{ name: string, syntax: string, real: string, game: string } | null>(null)

function onSelect(name: string) {
  selected.value = name
  const d = details[name]
  detail.value = d ? { name, ...d } : null
}

const staged = ref(false)
const committed = ref(false)
const edited = ref(false)
const cleared = ref(false)

function push(source: TerminalLine['source'], text: string) {
  lines.value.push({ id: nextId++, source, text })
}

function run(raw: string) {
  const cmd = raw.trim()
  // echo the input with a snapshot of the current prompt (単一ソース: 親が積む)
  lines.value.push({ id: nextId++, source: 'input', text: cmd, prompt: { ...prompt } })

  if (cmd === 'ls') return push('out', 'businesscard.txt  notes/  case_file.sh')
  if (cmd === 'cd notes' || cmd === 'cd notes/') { prompt.path = '/root/desk/notes'; return }
  if (cmd === 'cd ..') { prompt.path = '/root/desk'; return }
  if (cmd === 'cat businesscard.txt') {
    return push('out', edited.value ? 'The Amusement Park — night watchman, pier gate 22:00' : '(空白の名刺)')
  }
  if (/^echo\s+".*"\s*>\s*businesscard\.txt$/.test(cmd)) {
    edited.value = true
    return push('system', 'businesscard.txt を書き換えた。')
  }
  if (cmd === 'git status') {
    if (!edited.value) return push('out', 'On branch main\nnothing to commit, working tree clean')
    if (!staged.value) return push('out', 'Changes not staged for commit:\n  modified: businesscard.txt')
    if (!committed.value) return push('out', 'Changes staged for commit:\n  modified: businesscard.txt')
    return push('out', 'Ready to push — 1 commit ahead')
  }
  if (cmd === 'git add businesscard.txt' || cmd === 'git add .') {
    if (!edited.value) return push('warn', 'Warning: nothing to add — まだ何も変更していない')
    staged.value = true
    return push('system', 'staged: businesscard.txt')
  }
  if (/^git commit(\s|$)/.test(cmd)) {
    if (!staged.value) return push('warn', 'Warning: nothing staged — run `git add` first')
    committed.value = true
    return push('out', '[main] saved: edit businesscard.txt')
  }
  if (cmd === 'git push') {
    if (!committed.value) return push('warn', 'Warning: no commit to push — git add → commit の順で進めろ')
    push('out', 'git push — case closed.')
    cleared.value = true
    return
  }
  if (/^rm(\s|$)/.test(cmd)) return push('error', 'Error: command not allowed')
  return push('error', `Error: command not allowed`)
}
</script>

<template>
  <div class="screen">
    <MissionHeader
      index="1"
      title="Edit Business Card"
      subtitle="依頼人の名刺を書き換えろ"
      rank="Lv.1 見習い"
    />

    <section class="middle">
      <div class="scene-col">
        <SceneView image-url="/images/office.png">
          <SceneOverlay
            caption="机の引き出しを調べ、businesscard.txt を見つけろ…"
            card-title="引き出しの中身"
            card-body="色褪せた名刺が一枚。裏に走り書き —「22時、桟橋。金は持ってきたか」。これが最初の手がかりだ。"
          />
        </SceneView>
        <ClearEffect v-if="cleared" class="clear-overlay" @next="cleared = false" />
      </div>

      <div class="rail">
        <CommandPanel :commands="commands" @select="onSelect" />
        <CommandDetail
          v-if="detail"
          :name="detail.name"
          :syntax="detail.syntax"
          :real="detail.real"
          :game="detail.game"
        />
      </div>
    </section>

    <section class="term">
      <TerminalView :lines="lines" :prompt="prompt" @command="run" />
    </section>
  </div>
</template>

<style scoped>
.screen {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.middle {
  flex: 1;
  display: flex;
  min-height: 0;
  gap: var(--space-3);
  padding: var(--space-3);
}
.scene-col {
  position: relative;
  flex: 1;
  min-width: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.clear-overlay {
  position: absolute;
  inset: 0;
}
.rail {
  width: var(--rail-command-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
}
.term {
  height: var(--terminal-h);
  min-height: 220px;
  padding: 0 var(--space-3) var(--space-3);
}

@media (max-width: 720px) {
  .middle {
    flex-direction: column;
  }
  .rail {
    width: 100%;
  }
}
</style>
