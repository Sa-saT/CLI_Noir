import { defineStore } from 'pinia'
import type { LineSource, TerminalLine } from '~/components/TerminalView.vue'
import type { PromptState } from '~/components/PromptLabel.vue'
import type { CommitMeta, Style } from '~/types/ws'

/*
 * Pinia store — state / scrollback の単一ソース（DESIGN.md § 10-1）。
 * `useTerminalSocket` composable が WS フレームを受けてここへ書き込み、
 * `TerminalView.vue` はここから props/computed で読むだけ（フロントは FS の意味を知らない）。
 */

const SCROLLBACK_LIMIT = 2000

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
    missionId: null as number | null,
    connected: false,
    connecting: false,
    currentPath: '/root',
    remoteMode: false,
    sshHost: null as string | null,
    commits: [] as CommitMeta[],
    lines: [] as TerminalLine[],
    missionCleared: false,
    nextMissionId: null as number | null,
    pendingResume: false,
    _nextLineId: 1,
  }),
  getters: {
    /**
     * 「今どのホストにいるか」の単一ソース。プロンプト表示（promptState.host）と
     * 場面画像解決（missions/[id].vue の scene_images 最長一致キー）の両方がここを参照する。
     * 別々に再実装すると、一方だけ変更した際に表示とシーンがズレるため統合済み。
     */
    displayHost(state): string {
      return state.remoteMode ? (state.sshHost ?? 'remote') : 'office'
    },
    /** DESIGN.md § 4「プロンプト表記は状態を反映する」。su は未対応（Mission1〜3 の範囲外）。 */
    promptState(state): PromptState {
      return {
        user: 'detective',
        host: this.displayHost,
        path: state.currentPath,
        hostType: state.remoteMode ? 'remote' : 'local',
      }
    },
  },
  actions: {
    resetForMission(missionId: number) {
      this.missionId = missionId
      this.connected = false
      this.connecting = false
      this.currentPath = '/root'
      this.remoteMode = false
      this.sshHost = null
      this.commits = []
      this.lines = []
      this.missionCleared = false
      this.nextMissionId = null
      this.pendingResume = false
      this._nextLineId = 1
    },
    pushLine(source: LineSource, text: string, prompt?: PromptState) {
      this.lines.push({ id: this._nextLineId++, source, text, prompt })
      if (this.lines.length > SCROLLBACK_LIMIT) {
        this.lines.splice(0, this.lines.length - SCROLLBACK_LIMIT)
      }
    },
    pushEchoedInput(text: string, prompt: PromptState) {
      this.pushLine('input', text, prompt)
    },
    applyState(state: { current_path: string, remote_mode: boolean, ssh_host: string | null }) {
      this.currentPath = state.current_path
      this.remoteMode = state.remote_mode
      this.sshHost = state.ssh_host
    },
  },
})
