import { styleToSource, useTerminalStore } from '~/stores/terminal'
import type { EventFrame, HelloFrame, ResultFrame, ServerFrame, StreamFrame } from '~/types/ws'

/*
 * WebSocket 接続 composable（FE-03）。設計指示書 § 7。
 * `/ws/terminal?mission_id=<id>` へ接続 → `auth` → `hello` → `exec`/`result` ループ。
 * 受信フレームは Pinia store（app/stores/terminal.ts）へ書き込むだけ（単方向データフロー。
 * DESIGN.md § 10-1）。切断時は指数バックオフで再接続する（DESIGN.md § 10-7）。
 */

const RECONNECT_MIN_MS = 1000
const RECONNECT_MAX_MS = 30000

export function useTerminalSocket() {
  const store = useTerminalStore()
  const { getToken } = useAuth()
  const config = useRuntimeConfig()

  let ws: WebSocket | null = null
  let execId = 1
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = RECONNECT_MIN_MS
  let manualClose = false
  let missionId: number | null = null
  let everConnected = false
  let awaitingResumeHello = false

  function connect(id: number) {
    manualClose = false
    everConnected = false
    awaitingResumeHello = false
    missionId = id
    reconnectDelay = RECONNECT_MIN_MS
    store.resetForMission(id)
    openSocket()
  }

  function openSocket() {
    if (missionId == null || import.meta.server) return
    store.connecting = true
    const url = `${config.public.wsBase}/ws/terminal?mission_id=${missionId}`
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
    socket.addEventListener('close', () => {
      if (ws !== socket) return // 既に張り替え済みの古い socket
      ws = null
      store.connected = false
      store.connecting = false
      if (manualClose) return
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
    if (awaitingResumeHello) {
      // resume フレームへの応答（§ 7）。再接続ではなくセーブ復元の確認。
      awaitingResumeHello = false
      store.pushLine('system', '-- セーブから再開しました --')
    } else if (everConnected) {
      store.pushLine('system', '-- reconnected --')
    } else {
      everConnected = true
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
  }

  function handleEvent(frame: EventFrame) {
    if (frame.name === 'mission_clear') {
      store.missionCleared = true
      store.nextMissionId = frame.next_mission_id
    } else if (frame.name === 'rank_up') {
      store.pushLine('system', `-- ランクアップ: Level ${frame.level}（新規解放: ${frame.unlocked.join(', ')}） --`)
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

  function disconnect() {
    manualClose = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
  }

  return { connect, disconnect, exec, resume, skipResume }
}
