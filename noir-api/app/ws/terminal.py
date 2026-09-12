"""WebSocket ターミナルエンドポイント `/ws/terminal`（設計指示書 § 7、P3-10）。

ハンドシェイク: 接続 → 5秒以内の `auth` フレームで JWT 認証 → `hello`（state + commits）
→ 任意の `resume` → `exec`/`result` ループ。state 更新とクリア判定の書き込みは
evaluator のみ（本ハンドラは evaluate を呼び、結果を DB へ保存して result を返す）。

クエリパラメータは取らない（旧 `?mission_id=<id>` は撤去。FastAPI は未知のクエリを
無視するため、旧フロントの URL でも接続できる）。ユーザーごとに `PlayerState` 1 行
（永続統合ワールド）を読み書きする。Mission クリアは exec 前後で
`progress.active_mission_id(state["mission_progress"])` を比較して検出する
（`git push` が `progress.advance_mission` を呼んで値を進める。§ 疑似Git）。
"""

import asyncio
import copy

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlmodel import Session, select

from app.content.missions import get_mission
from app.evaluator import evaluate, progress, story
from app.models import PlayerState, User, default_state, default_world_state
from app.models.db import get_session
from app.security import ACCESS, decode_token
from app.ws.frames import AuthFrame, ExecFrame, ResumeFrame, state_summary, style_for

router = APIRouter()

AUTH_TIMEOUT_SEC = 5.0
MAX_LINES = 1000


def build_initial_state(mission_id: int) -> dict:
    """Mission 別の初期 state を生成する（default + Mission 固有の初期FS）。

    テスト/移行期用（`tests/test_mission*.py` 等が使う）。WS/API 層は P3-10/P3-11
    で `PlayerState`（統合ワールド）へ切り替え済みでこの関数は使わない。
    Phase F で MissionState ごと廃止する際、テストヘルパーへ移す予定。
    """
    state = default_state()
    state["mission_id"] = mission_id
    mission = get_mission(mission_id)
    if mission is not None and mission.initial_filesystem is not None:
        state["filesystem"] = copy.deepcopy(mission.initial_filesystem)
    if mission is not None and mission.initial_current_path is not None:
        state["current_path"] = mission.initial_current_path
    if mission is not None and mission.initial_processes is not None:
        state["processes"] = copy.deepcopy(mission.initial_processes)
    if mission is not None and mission.initial_cron_jobs is not None:
        state["cron_jobs"] = copy.deepcopy(mission.initial_cron_jobs)
    if mission is not None and mission.initial_env_vars is not None:
        state["env_vars"] = copy.deepcopy(mission.initial_env_vars)
    return state


def _authenticate(token: str, session: Session) -> User | None:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != ACCESS:
        return None
    return session.get(User, int(payload["sub"]))


def _load_or_create(session: Session, user_id: int) -> PlayerState:
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == user_id)
    ).first()
    if row is None:
        row = PlayerState(user_id=user_id, data=default_world_state())
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def _commit_meta(state: dict) -> list[dict]:
    return [
        {
            "id": c["id"],
            "message": c.get("message", ""),
            "created_at": c.get("created_at"),
            "mission_id": c.get("mission_id"),
        }
        for c in state.get("git_state", {}).get("commits", [])
    ]


def _to_lines(raw: list[str]) -> tuple[list[dict], bool]:
    """evaluator の出力行を style 付き lines と ok フラグに変換する。"""
    ok = not any(line.startswith("Error:") for line in raw)
    truncated = len(raw) > MAX_LINES
    shown = raw[:MAX_LINES]
    lines = [{"text": line, "style": style_for(line)} for line in shown]
    if truncated:
        lines.append(
            {"text": f"-- output truncated ({len(raw)} lines) --", "style": "warning"}
        )
    return lines, ok


@router.websocket("/ws/terminal")
async def terminal_ws(
    websocket: WebSocket,
    session: Session = Depends(get_session),
) -> None:
    await websocket.accept()

    # 1. 5秒以内の auth フレーム
    try:
        raw = await asyncio.wait_for(
            websocket.receive_json(), timeout=AUTH_TIMEOUT_SEC
        )
        auth = AuthFrame.model_validate(raw)
    except (TimeoutError, ValidationError, WebSocketDisconnect, ValueError):
        await websocket.close(code=4401)
        return

    user = _authenticate(auth.token, session)
    if user is None:
        await websocket.close(code=4401)
        return

    # 2. state 復元 / 生成 + hello（story: 独り言レイヤーの start beat。STORY-01）
    row = _load_or_create(session, user.id)
    state = row.data
    initial_beats = story.start_beats(state)
    row.data = state
    _persist(session, row)
    await websocket.send_json(
        {
            "type": "hello",
            "state": state_summary(state),
            "commits": _commit_meta(state),
            "story": initial_beats,
        }
    )

    # 3. exec / resume ループ
    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")

            if mtype == "resume":
                state = _handle_resume(msg, state)
                # resume 先の story_fired は snapshot（mission_progress ごと）に含まれて
                # 復元済みなので、start_beats はその時点で未発火の beat だけを返す。
                resume_beats = story.start_beats(state)
                row.data = state
                _persist(session, row)
                await websocket.send_json(
                    {
                        "type": "hello",
                        "state": state_summary(state),
                        "commits": _commit_meta(state),
                        "story": resume_beats,
                    }
                )
                continue

            if mtype == "exec":
                try:
                    frame = ExecFrame.model_validate(msg)
                except ValidationError:
                    continue
                prev_active = progress.active_mission_id(state["mission_progress"])
                prev_log_len = len(state.get("resolved_command_log", []))
                out_raw, state = evaluate(frame.command, state)

                # そのコマンドで resolved_command_log に append されたときだけ
                # entry を渡す（エラー等で記録されなかった場合は None）。
                entry = None
                if len(state.get("resolved_command_log", [])) > prev_log_len:
                    entry = state["resolved_command_log"][-1]
                beats = story.after_beats(state, prev_active, frame.command, out_raw, entry)

                # クリア遷移で mission_clear イベント + clear/次 Mission start の独り言
                next_active = progress.active_mission_id(state["mission_progress"])
                if next_active != prev_active:
                    beats = beats + story.clear_beats(state, prev_active)

                row.data = state
                _persist(session, row)

                lines, ok = _to_lines(out_raw)
                await websocket.send_json(
                    {
                        "type": "result",
                        "id": frame.id,
                        "ok": ok,
                        "command": frame.command,
                        "lines": lines,
                        "state": state_summary(state),
                    }
                )
                if beats:
                    await websocket.send_json(
                        {"type": "event", "name": "story", "beats": beats}
                    )
                if next_active != prev_active:
                    await websocket.send_json(
                        {
                            "type": "event",
                            "name": "mission_clear",
                            "cleared_mission_id": prev_active,
                            "next_mission_id": next_active,
                        }
                    )
    except WebSocketDisconnect:
        return


def _handle_resume(msg: dict, state: dict) -> dict:
    """resume フレーム: 指定 commit の snapshot から state を復元する。

    統合ワールド state（`mission_progress` を持つ）は、スナップショットに存在する
    キーだけを復元する: current_path / filesystem / env_vars / mission_progress /
    processes / cron_jobs / current_user / remote_mode / ssh_host。command_log /
    resolved_command_log / git_state は復元しない（履歴と commit 一覧は残す）。
    Mission 別 state（mission_flags）は従来どおり復元する。
    """
    try:
        frame = ResumeFrame.model_validate(msg)
    except ValidationError:
        return state
    for commit in state.get("git_state", {}).get("commits", []):
        if commit["id"] == frame.commit_id:
            snap = commit.get("snapshot", {})
            restored = copy.deepcopy(state)
            if "mission_progress" in state:
                for key in (
                    "current_path",
                    "filesystem",
                    "env_vars",
                    "mission_progress",
                    "processes",
                    "cron_jobs",
                    "current_user",
                    "remote_mode",
                    "ssh_host",
                ):
                    if key in snap:
                        restored[key] = copy.deepcopy(snap[key])
            else:
                restored["current_path"] = snap.get("current_path", state["current_path"])
                restored["filesystem"] = copy.deepcopy(
                    snap.get("filesystem", state["filesystem"])
                )
                restored["mission_flags"] = copy.deepcopy(
                    snap.get("mission_flags", state["mission_flags"])
                )
                restored["env_vars"] = copy.deepcopy(
                    snap.get("env_vars", state.get("env_vars", {}))
                )
            return restored
    return state


def _persist(session: Session, row: PlayerState) -> None:
    # SQLAlchemy に JSON カラムの差し替えを検知させる（同一参照の in-place 変更対策）。
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(row, "data")
    session.add(row)
    session.commit()
