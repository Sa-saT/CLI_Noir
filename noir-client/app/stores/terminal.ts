import { defineStore } from 'pinia'
import type { LineSource, TerminalLine } from '~/components/TerminalView.vue'
import type { PromptState } from '~/components/PromptLabel.vue'
import type { CommitMeta, StoryBeat, Style, StateSummary } from '~/types/ws'

/*
 * Pinia store — state / scrollback の単一ソース（DESIGN.md § 10-1）。
 * `useTerminalSocket` composable が WS フレームを受けてここへ書き込み、
 * `TerminalView.vue` はここから props/computed で読むだけ（フロントは FS の意味を知らない）。
 *
 * Phase E（FE3-01/FE3-02）: 接続がユーザーごとに 1 本の永続ワールドになったため、
 * Mission 単位の `missionId` / `resetForMission()` は廃止。`lines`（scrollback）も
 * Mission ページ間の遷移で消さない（実ターミナルは 1 つしかないため）。
 */

const SCROLLBACK_LIMIT = 2000
const STORY_LOG_LIMIT = 200

const STYLE_TO_SOURCE: Record<Style, LineSource> = {
  normal: 'out',
  error: 'error',
  warning: 'warn',
  emphasis: 'emphasis',
  success: 'success',
}

export function styleToSource(style: Style): LineSource {
  return STYLE_TO_SOURCE[style] ?? 'out'
}

export const useTerminalStore = defineStore('terminal', {
  state: () => ({
    connected: false,
    connecting: false,
    currentPath: '/root',
    remoteMode: false,
    sshHost: null as string | null,
    activeMissionId: null as number | null,
    currentUser: 'detective',
    commits: [] as CommitMeta[],
    lines: [] as TerminalLine[],
    missionCleared: false,
    clearedMissionId: null as number | null,
    nextMissionId: null as number | null,
    pendingResume: false,
    _nextLineId: 1,
    // --- STORY-01: 進行案内「独り言レイヤー」 ---
    storyQueue: [] as StoryBeat[],
    storyLog: [] as StoryBeat[],
    storyCurrent: null as StoryBeat | null,
    // --- STORY-01: 停滞（stall）判定用。useTerminalSocket.handleResult が更新する ---
    lastResultOk: true,
    consecutiveErrors: 0,
  }),
  getters: {
    /** 独り言の未表示キューが残っているか（次へ進めるかの表示制御に使う）。 */
    storyHasNext(state): boolean {
      return state.storyQueue.length > 0
    },
    /**
     * 「今どのホストにいるか」の単一ソース。プロンプト表示（promptState.host）と
     * 場面画像解決（missions/[id].vue の scene_images 最長一致キー）の両方がここを参照する。
     * 別々に再実装すると、一方だけ変更した際に表示とシーンがズレるため統合済み。
     */
    displayHost(state): string {
      return state.remoteMode ? (state.sshHost ?? 'remote') : 'office'
    },
    /** DESIGN.md § 4「プロンプト表記は状態を反映する」。su は `currentUser` の反映で表現する。 */
    promptState(state): PromptState {
      return {
        user: state.currentUser,
        host: this.displayHost,
        path: state.currentPath,
        hostType: state.remoteMode ? 'remote' : 'local',
      }
    },
  },
  actions: {
    pushLine(source: LineSource, text: string, prompt?: PromptState) {
      this.lines.push({ id: this._nextLineId++, source, text, prompt })
      if (this.lines.length > SCROLLBACK_LIMIT) {
        this.lines.splice(0, this.lines.length - SCROLLBACK_LIMIT)
      }
    },
    pushEchoedInput(text: string, prompt: PromptState) {
      this.pushLine('input', text, prompt)
    },
    /** Ctrl+L / `clear` コマンド共通。scrollback を空にする（実ターミナルの clear と同じ）。 */
    clearScrollback() {
      this.lines = []
    },
    applyState(state: StateSummary) {
      this.currentPath = state.current_path
      this.remoteMode = state.remote_mode
      this.sshHost = state.ssh_host
      this.activeMissionId = state.active_mission_id
      this.currentUser = state.current_user
    },
    /** 表示済みログへ積む（上限 200。古いものから捨てる）。 */
    _pushStoryLog(beat: StoryBeat) {
      this.storyLog.push(beat)
      if (this.storyLog.length > STORY_LOG_LIMIT) {
        this.storyLog.splice(0, this.storyLog.length - STORY_LOG_LIMIT)
      }
    },
    /** 独り言をキューへ積む。表示中が無ければ即座に先頭を表示へ回す。 */
    enqueueStory(beats: StoryBeat[]) {
      this.storyQueue.push(...beats)
      if (!this.storyCurrent && this.storyQueue.length > 0) {
        this.advanceStory()
      }
    },
    /** 次の独り言へ進める。キューが空なら何もしない。 */
    advanceStory() {
      if (this.storyQueue.length === 0) return
      const next = this.storyQueue.shift()
      if (!next) return
      this.storyCurrent = next
      this._pushStoryLog(next)
    },
    /** 一連の独り言を閉じる（Esc / 最後の beat をクリック / 放置）。次の beat が届けばまた表示される。 */
    completeStory() {
      this.storyCurrent = null
      if (this.storyQueue.length > 0) this.advanceStory()
    },
  },
})
