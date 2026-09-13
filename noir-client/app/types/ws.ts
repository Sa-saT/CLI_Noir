/*
 * WebSocket フレーム型（設計指示書 § 7）。
 * クライアント→サーバー（AuthFrame/ExecFrame/ResumeFrame）は `noir-api/app/ws/frames.py` の
 * Pydantic モデルと 1:1（技術スタック § 2）。
 * サーバー→クライアントは `noir-api/app/ws/terminal.py` が実際に送るのは hello / result /
 * event(name="mission_clear" / "story" / "rank_up") と completions。StreamFrame は
 * バックエンド未実装の先行型（tail -f 監視。実装され次第検証すること）。
 * 探偵ランク（設計指示書 § 8 レベル表 / § 11 ゲーム機能1）は 2026-09-13 に実装:
 * `StateSummary.rank` が現在ランク、クリアでランクが上がると `mission_clear` の後に `rank_up`。
 * `StoryBeat` / `HelloFrame.story` / `event(name="story")`（STORY-01・進行案内「独り言レイヤー」）
 * はバックエンドと並行実装中の契約（2026-09-13 時点で先行導入。実装され次第検証すること）。
 */

export type Style = 'normal' | 'error' | 'warning' | 'emphasis' | 'success'

/** 探偵ランク（設計指示書 § 8 レベル表。解放済みコマンドの最高レベル） */
export interface Rank { level: number, name: string }

export interface StateSummary {
  current_path: string
  remote_mode: boolean
  ssh_host: string | null
  active_mission_id: number | null
  current_user: string
  rank: Rank
  /** やらかし体験室（Mission29）で予備の機械に繋いでいる間 true（本物の世界は退避中） */
  sandbox?: boolean
}

export interface CommitMeta {
  id: number
  message: string
  created_at: string | null
  mission_id: number | null
  /** この commit で `git push` が通った（= その Mission のクリア判定に使われた）。resume するとクリア直後の世界に戻る */
  pushed?: boolean
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
/** Tab 補完の問い合わせ（設計指示書 § 7 補完フレーム / DESIGN.md § 10-4）。 */
export interface CompleteFrame { type: 'complete', id: number, line: string, cursor: number }
export type ClientFrame = AuthFrame | ExecFrame | ResumeFrame | CompleteFrame

// --- サーバー → クライアント ---
export interface HelloFrame {
  type: 'hello'
  state: StateSummary
  commits: CommitMeta[]
  story?: StoryBeat[]
}

export interface ResultLine { text: string, style: Style }

/** 図鑑（ゲーム機能 2・10）。result フレームの `codex` は今回新しく登録されたもの */
export interface CodexNew { kind: 'command' | 'error', key: string, title?: string, text?: string }
export interface CodexCommand { name: string, first_mission: number | null, count: number }
export interface CodexError { key: string, title: string, text: string, first_mission: number | null, count: number, sample?: string }

export interface ResultFrame {
  type: 'result'
  id: number
  ok: boolean
  command: string
  lines: ResultLine[]
  state: StateSummary
  codex?: CodexNew[]
}

/** `complete` への応答。`replace_from` は行内の置換開始位置（候補で置き換える範囲の先頭）。 */
export interface CompletionsFrame {
  type: 'completions'
  id: number
  candidates: string[]
  replace_from: number
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

/** `mission_clear` の直後・`story` の前に届く（ランクが上がったクリアのみ）。 */
export interface RankUpEvent {
  type: 'event'
  name: 'rank_up'
  level: number
  rank_name: string
  from_level: number
  from_rank_name: string
  unlocked: string[]
}

/** `result` の直後に届く（STORY-01）。クリア時は `mission_clear` の**後**（演出中は独り言を保留するため）。 */
export interface StoryEvent {
  type: 'event'
  name: 'story'
  beats: StoryBeat[]
}

export type EventFrame = MissionClearEvent | RankUpEvent | StoryEvent

export type ServerFrame = HelloFrame | ResultFrame | StreamFrame | EventFrame | CompletionsFrame
