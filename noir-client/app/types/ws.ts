/*
 * WebSocket フレーム型（設計指示書 § 7）。
 * クライアント→サーバー（AuthFrame/ExecFrame/ResumeFrame）は `noir-api/app/ws/frames.py` の
 * Pydantic モデルと 1:1（技術スタック § 2）。
 * サーバー→クライアントは `noir-api/app/ws/terminal.py` が実際に送るのは hello / result /
 * event(name="mission_clear") のみ（2026-08-12 時点）。StreamFrame と RankUpEvent は
 * バックエンド未実装の先行型（探偵ランク制度＝設計指示書 § 11 ゲーム機能1。実装され次第
 * 検証すること。それまではこのパスは未到達＝テスト不能）。
 * `StoryBeat` / `HelloFrame.story` / `event(name="story")`（STORY-01・進行案内「独り言レイヤー」）
 * はバックエンドと並行実装中の契約（2026-09-13 時点で先行導入。実装され次第検証すること）。
 */

export type Style = 'normal' | 'error' | 'warning' | 'emphasis' | 'success'

export interface StateSummary {
  current_path: string
  remote_mode: boolean
  ssh_host: string | null
  active_mission_id: number | null
  current_user: string
}

export interface CommitMeta {
  id: number
  message: string
  created_at: string | null
  mission_id: number | null
}

/** 進行案内「独り言レイヤー」（STORY-01）。text は `\n` 区切りで最大 2 行。話者ラベルは付けない。 */
export interface StoryBeat {
  id: string
  mission_id: number
  text: string
}

// --- クライアント → サーバー ---
export interface AuthFrame { type: 'auth', token: string }
export interface ExecFrame { type: 'exec', id: number, command: string }
export interface ResumeFrame { type: 'resume', commit_id: number }
export type ClientFrame = AuthFrame | ExecFrame | ResumeFrame

// --- サーバー → クライアント ---
export interface HelloFrame {
  type: 'hello'
  state: StateSummary
  commits: CommitMeta[]
  story?: StoryBeat[]
}

export interface ResultLine { text: string, style: Style }

export interface ResultFrame {
  type: 'result'
  id: number
  ok: boolean
  command: string
  lines: ResultLine[]
  state: StateSummary
}

export interface StreamFrame {
  type: 'stream'
  source: string
  lines: ResultLine[]
}

export interface MissionClearEvent {
  type: 'event'
  name: 'mission_clear'
  cleared_mission_id: number
  next_mission_id: number | null
}

export interface RankUpEvent {
  type: 'event'
  name: 'rank_up'
  level: number
  unlocked: string[]
}

/** `result` の直後・`mission_clear` の前に届く（STORY-01）。 */
export interface StoryEvent {
  type: 'event'
  name: 'story'
  beats: StoryBeat[]
}

export type EventFrame = MissionClearEvent | RankUpEvent | StoryEvent

export type ServerFrame = HelloFrame | ResultFrame | StreamFrame | EventFrame
