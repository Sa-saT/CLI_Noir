"""WebSocket ターミナルエンドポイント `/ws/terminal`（設計指示書 § 7、P3-10）。

ハンドシェイク: 接続 → 5秒以内の `auth` フレームで JWT 認証 → `hello`（state + commits）
→ 任意の `resume` → `exec`/`result`（+ `complete`/`completions`）ループ。state 更新とクリア判定の書き込みは
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

from app.evaluator import (
    codex,
    complete,
    evaluate,
    progress,
    rank,
    replay,
    rewards,
    score,
    story,
)
from app.models import PlayerState, User, default_world_state
from app.models.db import get_session
from app.security import ACCESS, decode_token
from app.ws.frames import (
    AuthFrame,
    CompleteFrame,
    ExecFrame,
    FocusFrame,
    ResumeFrame,
    state_summary,
    style_for,
)

router = APIRouter()

AUTH_TIMEOUT_SEC = 5.0
MAX_LINES = 1000


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
            "pushed": c.get("pushed", False),
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
    # 後から増えた世界の中身（隠しファイル等）を古いセーブに継ぎ足す
    progress.ensure_world_content(state)
    # タイムアタック演出（機能 7）: 捜査中 Mission の開始時刻が無ければ今を記録する
    active = progress.active_mission_id(state["mission_progress"])
    if active is not None and score.started_at(state, active) is None:
        score.mark_started(state, active)
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

            if mtype == "complete":
                # Tab 補完（純粋関数。state は変更しないため保存しない）
                try:
                    cframe = CompleteFrame.model_validate(msg)
                except ValidationError:
                    continue
                candidates, replace_from = complete.complete(state, cframe.line, cframe.cursor)
                await websocket.send_json(
                    {
                        "type": "completions",
                        "id": cframe.id,
                        "candidates": candidates,
                        "replace_from": replace_from,
                    }
                )
                continue

            if mtype == "focus":
                # 再捜査（app/evaluator/replay.py）: クリア済み Mission のページで「再捜査を始める」
                # → その Mission に注目、null → やめる。応答は focus フレーム（state + 独り言）。
                try:
                    fframe = FocusFrame.model_validate(msg)
                except ValidationError:
                    continue
                error = None
                focus_beats: list[dict] = []
                if fframe.mission_id is None:
                    replay.stop(state)
                elif replay.can_replay(state, fframe.mission_id):
                    replay.start(state, fframe.mission_id)
                    focus_beats = story.start_beats(state)
                else:
                    error = "Error: mission is not replayable"
                row.data = state
                _persist(session, row)
                await websocket.send_json(
                    {
                        "type": "focus",
                        "state": state_summary(state),
                        "story": focus_beats,
                        "error": error,
                    }
                )
                continue

            if mtype == "exec":
                try:
                    frame = ExecFrame.model_validate(msg)
                except ValidationError:
                    continue
                prev_active = progress.active_mission_id(state["mission_progress"])
                prev_focus = progress.focused_mission_id(state)
                prev_replay = replay.active(state)
                prev_log_len = len(state.get("resolved_command_log", []))
                prev_state = state
                out_raw, state = evaluate(frame.command, state)

                # そのコマンドで resolved_command_log に append されたときだけ
                # entry を渡す（エラー等で記録されなかった場合は None）。
                entry = None
                if len(state.get("resolved_command_log", [])) > prev_log_len:
                    entry = state["resolved_command_log"][-1]
                beats = story.after_beats(
                    replay.view(state) if prev_replay else state,
                    prev_focus, frame.command, out_raw, entry,
                )

                # クリア遷移で mission_clear イベント + clear/次 Mission start の独り言
                next_active = progress.active_mission_id(state["mission_progress"])
                if next_active != prev_active:
                    beats = beats + story.clear_beats(state, prev_active)
                # 再捜査完了（push で replay が閉じた）: クリア独り言だけ（次 Mission の start は無し）
                replay_cleared = prev_replay is not None and replay.active(state) is None and (
                    frame.command.strip().startswith("git push")
                    and any(ln.startswith("Case reopened") for ln in out_raw)
                )
                if replay_cleared:
                    beats = beats + [
                        b for b in story.clear_beats(state, prev_focus) if b["mission_id"] == prev_focus
                    ]

                lines, ok = _to_lines(out_raw)
                # 図鑑（ゲーム機能 2・10）: 成功した道具と遭遇したエラーを登録する
                codex_new = codex.register(state, frame.command, out_raw, ok)
                # 回想の収集（機能 5）とご褒美コマンドの解放（機能 12）
                collection_events = rewards.register(state, frame.command, entry)

                row.data = state
                _persist(session, row)

                await websocket.send_json(
                    {
                        "type": "result",
                        "id": frame.id,
                        "ok": ok,
                        "command": frame.command,
                        "lines": lines,
                        "state": state_summary(state),
                        "codex": codex_new,
                        "collection": collection_events,
                    }
                )
                # mission_clear を story より先に送る: フロントはクリア演出を出している間
                # 独り言を保留し、演出を閉じてからクリア独り言 → 次 Mission の start 独り言
                # を流す（逆順だと演出の下でタイプライターが走って読めない。2026-09-13）。
                # ランクアップ（辞令）はクリア演出の後・独り言の前に見せるので、その間に送る。
                if next_active != prev_active:
                    await websocket.send_json(
                        {
                            "type": "event",
                            "name": "mission_clear",
                            "cleared_mission_id": prev_active,
                            "next_mission_id": next_active,
                            # 機能 3・7: 手数 / 目安 / ボーナス / 所要秒
                            "score": score.score_of(state, prev_active),
                        }
                    )
                    rank_up = rank.rank_up_event(prev_state, state)
                    if rank_up is not None:
                        await websocket.send_json(rank_up)
                if replay_cleared:
                    await websocket.send_json(
                        {
                            "type": "event",
                            "name": "mission_clear",
                            "cleared_mission_id": prev_focus,
                            "next_mission_id": None,
                            "replay": True,
                            "score": state["mission_progress"].get("scores_replay", {}).get(str(prev_focus)),
                        }
                    )
                if beats:
                    await websocket.send_json(
                        {"type": "event", "name": "story", "beats": beats}
                    )
    except WebSocketDisconnect:
        return


def _handle_resume(msg: dict, state: dict) -> dict:
    """resume フレーム: 指定 commit の snapshot から state を復元する。

    スナップショットに存在するキーだけを復元する: current_path / filesystem /
    env_vars / mission_progress / processes / cron_jobs / current_user /
    remote_mode / ssh_host。command_log / resolved_command_log / git_state は
    復元しない（履歴と commit 一覧は残す）。

    push が通った commit（`pushed=True`。git_ops._push が印を付ける）へ resume した
    場合は、スナップショット復元後に `progress.advance_mission` を再適用し、その commit
    でクリアした直後（次 Mission が解放された状態）に戻す。commit は push の前に
    作られるので、印を見ずに snapshot だけ戻すと「クリア済みのはずの Mission に
    逆戻りし、次 Mission の区画が消える」（2026-09-13 ユーザー報告）。
    """
    try:
        frame = ResumeFrame.model_validate(msg)
    except ValidationError:
        return state
    for commit in state.get("git_state", {}).get("commits", []):
        if commit["id"] == frame.commit_id:
            snap = commit.get("snapshot", {})
            restored = copy.deepcopy(state)
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
                "sandbox",
            ):
                if key in snap:
                    restored[key] = copy.deepcopy(snap[key])
            if restored.get("sandbox") is None:
                restored.pop("sandbox", None)
            if commit.get("pushed") and commit.get("mission_id") is not None:
                progress.advance_mission(restored, commit["mission_id"])
            return restored
    return state


def _persist(session: Session, row: PlayerState) -> None:
    # SQLAlchemy に JSON カラムの差し替えを検知させる（同一参照の in-place 変更対策）。
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(row, "data")
    session.add(row)
    session.commit()
