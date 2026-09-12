import { styleToSource, useTerminalStore } from '~/stores/terminal'
import type { EventFrame, HelloFrame, ResultFrame, ServerFrame, StreamFrame } from '~/types/ws'

/*
 * WebSocket 接続 composable（Phase E: FE3-01/FE3-02）。設計指示書 § 7。
 * `/ws/terminal`（クエリ無し）へ接続 → `auth` → `hello` → `exec`/`result` ループ。
 * ユーザーごとに 1 つの永続統合ワールドを表す**単一の常時接続**（`docs/DESIGN.md` § 7
 * 「常時ターミナル」）。接続は `app.vue` がログイン状態にひもづけて張る/切るだけで、
 * Mission ページ（`pages/missions/[id].vue`）は connect/disconnect を呼ばない。
 * `useAuth.ts` の accessToken と同じくモジュールスコープで状態を持ち、
 * `useTerminalSocket()` を何度呼んでも同じ接続を共有する（シングルトン）。
 * 受信フレームは Pinia store（app/stores/terminal.ts）へ書き込むだけ（単方向データフロー。
 * DESIGN.md § 10-1）。切断時は指数バックオフで再接続する（DESIGN.md § 10-7）。
 */

const RECONNECT_MIN_MS = 1000
const RECONNECT_MAX_MS = 30000
/** noir-api/app/ws/terminal.py が auth フレーム欠落・不正/失効トークンで送る close code。 */
const WS_CODE_UNAUTHORIZED = 4401

// --- モジュールスコープ（シングルトン接続。useAuth.ts の accessToken と同じ方式） ---
let ws: WebSocket | null = null
let execId = 1
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectDelay = RECONNECT_MIN_MS
let manualClose = false
let everConnected = false
let awaitingResumeHello = false

export function useTerminalSocket() {
  const store = useTerminalStore()
  const { getToken, logout } = useAuth()
  const config = useRuntimeConfig()

  function connect() {
    // 冪等: 接続済み/接続中の socket があるか、再接続待機中なら何もしない。
    if (import.meta.server) return
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    if (reconnectTimer) return
    manualClose = false
    reconnectDelay = RECONNECT_MIN_MS
    openSocket()
  }

  function openSocket() {
    if (import.meta.server) return
    store.connecting = true
    const url = `${config.public.wsBase}/ws/terminal`
    const socket = new WebSocket(url)
    ws = socket

    socket.addEventListener('open', () => {
      const token = getToken()
      socket.send(JSON.stringify({ type: 'auth', token }))
    })
    socket.addEventListener('message', (ev) => {
      try {
        handleFrame(JSON.parse(ev.data as string) as ServerFrame)
      } catch {
        // 不正な JSON は無視（サーバー側は Pydantic で検証済みのはずだが防御的に）
      }
    })
    socket.addEventListener('close', (ev) => {
      if (ws !== socket) return // 既に張り替え済みの古い socket
      ws = null
      store.connected = false
      store.connecting = false
      if (manualClose) return
      if (ev.code === WS_CODE_UNAUTHORIZED) {
        // トークン欠落/不正/失効。再接続しても同じトークンで同じ結果になるだけなので、
        // useApi.ts の 401 ハンドリング（ログアウト + /login 遷移）と同じ扱いにする。
        manualClose = true
        if (reconnectTimer) {
          clearTimeout(reconnectTimer)
          reconnectTimer = null
        }
        store.pushLine('error', 'Error: unauthorized（再ログインが必要です）')
        logout()
        navigateTo('/login')
        return
      }
      store.pushLine('warn', '-- connection lost, reconnecting... --')
      scheduleReconnect()
    })
    socket.addEventListener('error', () => {
      // close イベントが後続で発火するため、ここでは何もしない
    })
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS)
      openSocket()
    }, reconnectDelay)
  }

  function handleFrame(frame: ServerFrame) {
    if (frame.type === 'hello') return handleHello(frame)
    if (frame.type === 'result') return handleResult(frame)
    if (frame.type === 'event') return handleEvent(frame)
    if (frame.type === 'stream') return handleStream(frame)
  }

  function handleHello(frame: HelloFrame) {
    store.applyState(frame.state)
    store.commits = frame.commits ?? []
    store.connected = true
    store.connecting = false
    reconnectDelay = RECONNECT_MIN_MS
    if (frame.story?.length) store.enqueueStory(frame.story)
    if (awaitingResumeHello) {
      // resume フレームへの応答（§ 7）。再接続ではなくセーブ復元の確認。
      awaitingResumeHello = false
      store.pushLine('system', '-- セーブから再開しました --')
    } else if (everConnected) {
      store.pushLine('system', '-- reconnected --')
    } else {
      everConnected = true
      // ログイン直後の初回 hello のみ（接続がプレイ全体で 1 回になったため、
      // セーブ選択はログインごとに 1 回だけ出る）。
      if (store.commits.length > 0) {
        store.pendingResume = true
      }
    }
  }

  function handleResult(frame: ResultFrame) {
    for (const line of frame.lines) {
      store.pushLine(styleToSource(line.style), line.text)
    }
    store.applyState(frame.state)
    // STORY-01: 停滞（stall）判定はフロント側（Mission ページ）が行う。その材料として
    // 直近の成否と連続失敗回数だけ store に置いておく。
    store.lastResultOk = frame.ok
    store.consecutiveErrors = frame.ok ? 0 : store.consecutiveErrors + 1
    // `clear` コマンドはエコーされた入力行ごと消える（実ターミナルと同じ手触り）。
    // frame.lines を積んだ後にクリアする（バックエンドは空出力を返すため実質 no-op だが順序を保証しておく）。
    if (frame.ok && frame.command.trim() === 'clear') {
      store.clearScrollback()
    }
  }

  function handleEvent(frame: EventFrame) {
    if (frame.name === 'mission_clear') {
      store.missionCleared = true
      store.clearedMissionId = frame.cleared_mission_id
      store.nextMissionId = frame.next_mission_id
    } else if (frame.name === 'rank_up') {
      // バックエンド未実装（types/ws.ts 冒頭コメント参照）。実装され次第、テキスト表示ではなく
      // RankUpEffect.vue（未接続）へ繋ぎ直すこと。
      store.pushLine('system', `-- ランクアップ: Level ${frame.level}（新規解放: ${frame.unlocked.join(', ')}） --`)
    } else if (frame.name === 'story') {
      store.enqueueStory(frame.beats)
    }
  }

  function handleStream(frame: StreamFrame) {
    for (const line of frame.lines) {
      store.pushLine(styleToSource(line.style), line.text)
    }
  }

  function exec(command: string) {
    store.pushEchoedInput(command, store.promptState)
    if (!ws || ws.readyState !== WebSocket.OPEN || !store.connected) {
      store.pushLine('system', 'Error: not connected')
      return
    }
    ws.send(JSON.stringify({ type: 'exec', id: execId++, command }))
  }

  function resume(commitId: number) {
    store.pendingResume = false
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    awaitingResumeHello = true
    ws.send(JSON.stringify({ type: 'resume', commit_id: commitId }))
  }

  function skipResume() {
    store.pendingResume = false
  }

  /** ログアウト時のみ呼ぶ。次のログインで初回 hello（セーブ選択判定含む）からやり直す。 */
  function disconnect() {
    manualClose = true
    everConnected = false
    awaitingResumeHello = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
    // 同じブラウザで別ユーザーがログインしても前のユーザーの scrollback・commit 一覧が
    // 残らないよう、store を初期状態へ戻す。
    store.$reset()
  }

  return { connect, disconnect, exec, resume, skipResume }
}
