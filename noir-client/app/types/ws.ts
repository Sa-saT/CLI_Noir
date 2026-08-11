/*
 * WebSocket フレーム型（設計指示書 § 7）。
 * `noir-api/app/ws/frames.py` の Pydantic モデルと 1:1 を保つ（技術スタック § 2）。
 */

export type Style = 'normal' | 'error' | 'warning' | 'emphasis' | 'success'

export interface StateSummary {
  current_path: string
  remote_mode: boolean
  ssh_host: string | null
}

export interface CommitMeta {
  id: number
  message: string
  created_at: string | null
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
  next_mission_id: number | null
}

export interface RankUpEvent {
  type: 'event'
  name: 'rank_up'
  level: number
  unlocked: string[]
}

export type EventFrame = MissionClearEvent | RankUpEvent

export type ServerFrame = HelloFrame | ResultFrame | StreamFrame | EventFrame
