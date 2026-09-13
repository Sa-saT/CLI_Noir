"""WebSocket /ws/terminal のテスト（ハンドシェイク・exec・Mission1 クリア）。"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from starlette.websockets import WebSocketDisconnect

import pytest

from app.api.deps import create_user
from app.models import PlayerState


def _token(client: TestClient) -> str:
    return client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]


def _exec(ws, id_, command, *, expect_story=False, expect_clear=False):
    """exec を送り、result（+ 発火した story/mission_clear event, STORY-01）を消費する。

    どの独り言が発火するかは Mission参照ファイル.md の story_beats 定義に従う
    （呼び出し側が事前に判っている前提で expect_story/expect_clear を渡す）。
    """
    ws.send_json({"type": "exec", "id": id_, "command": command})
    result = ws.receive_json()
    assert result["type"] == "result"
    story_event = None
    clear_event = None
    # クリア時は mission_clear が story より先（フロントが演出中の独り言を保留するため）
    if expect_clear:
        clear_event = ws.receive_json()
        assert clear_event["type"] == "event"
        assert clear_event["name"] == "mission_clear"
    if expect_story:
        story_event = ws.receive_json()
        assert story_event["type"] == "event"
        if story_event["name"] == "rank_up":
            # ランクが上がるクリアでは mission_clear と story の間に辞令が挟まる（test_rank.py）
            story_event = ws.receive_json()
        assert story_event["name"] == "story"
    return result, story_event, clear_event


def test_ws_handshake_and_exec(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["state"]["current_path"] == "/root"
        assert hello["state"]["active_mission_id"] == 1

        ws.send_json({"type": "exec", "id": 1, "command": "ls"})
        res = ws.receive_json()
        assert res["type"] == "result"
        assert res["id"] == 1
        assert res["ok"] is True
        texts = [ln["text"] for ln in res["lines"]]
        assert "case_file.sh" in texts and "desk" in texts


def test_ws_rejects_bad_token(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": "not-a-jwt"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_ws_denylist_result_not_ok(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        ws.send_json({"type": "exec", "id": 9, "command": "rm -rf /"})
        res = ws.receive_json()
        assert res["ok"] is False
        assert res["lines"][0]["style"] == "error"
        assert res["lines"][0]["text"] == "Error: command not allowed"


def test_ws_mission1_clear(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()

        # 各コマンドが独り言（story_beats）を発火するかは Mission参照ファイル.md
        # Mission1 の story_beats 定義どおり（cat=read, echo=wrote, sh 成功=judge_pass,
        # git push 成功=クリア遷移で clear+次 Mission start）。
        transcript = [
            ("cat /root/desk/businesscard.txt", True, False),
            ('echo "NAME: Sam Spade" > /root/desk/businesscard.txt', True, False),
            ("sh case_file.sh", True, False),
            ("git add .", False, False),
            ('git commit -m "solved"', False, False),
            ("git push", True, True),
        ]
        last = None
        clear_event = None
        for i, (cmd, expect_story, expect_clear) in enumerate(transcript):
            last, _story_event, clear_event = _exec(
                ws, i, cmd, expect_story=expect_story, expect_clear=expect_clear
            )

        assert last["ok"] is True
        assert last["lines"][0]["text"] == "Mission Complete! Next mission unlocked."
        # push 後に mission_clear イベントが届く
        assert clear_event["cleared_mission_id"] == 1
        assert clear_event["next_mission_id"] == 2

        # 区画解放: park が ls に現れる
        res, _, _ = _exec(ws, 100, "ls")
        texts = [ln["text"] for ln in res["lines"]]
        assert "park" in texts


def test_ws_state_persists_across_reconnect(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        # "cd /root/desk" は Mission1 の独り言「desk」を発火する
        _exec(ws, 1, "cd /root/desk", expect_story=True)

    # 再接続時に current_path が復元される
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert hello["state"]["current_path"] == "/root/desk"

    rows = session.exec(select(PlayerState)).all()
    assert len(rows) == 1


def test_ws_resume_restores_snapshot(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()

        # "cd desk" は Mission1 の独り言「desk」を発火する（resolved_line 経由）
        commands = [
            ("cd desk", True),
            ("git add .", False),
            ('git commit -m "save"', False),
            ("cd /root", False),
        ]
        for cmd, expect_story in commands:
            _exec(ws, 1, cmd, expect_story=expect_story)

        ws.send_json({"type": "resume", "commit_id": 1})
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["state"]["current_path"] == "/root/desk"
        assert hello["commits"][0]["mission_id"] == 1


def test_ws_resume_rewinds_world_progress(client: TestClient, session: Session) -> None:
    """クリア前のセーブへ resume すると、進捗・区画ロックも当時に戻る（P3-10）。"""
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()

        # クリア前のセーブ（commit #1）を作ってから Mission1 をクリアする
        # （各コマンドが独り言を発火するかは Mission1 の story_beats 定義どおり）
        transcript = [
            ("git add .", False, False),
            ('git commit -m "before"', False, False),
            ("cat /root/desk/businesscard.txt", True, False),
            ('echo "NAME: Sam Spade" > /root/desk/businesscard.txt', True, False),
            ("sh case_file.sh", True, False),
            ("git add .", False, False),
            ('git commit -m "solved"', False, False),
            ("git push", True, True),
        ]
        clear_event = None
        for i, (cmd, expect_story, expect_clear) in enumerate(transcript):
            _, _story_event, clear_event = _exec(
                ws, i, cmd, expect_story=expect_story, expect_clear=expect_clear
            )
        assert clear_event["name"] == "mission_clear"

        ws.send_json({"type": "resume", "commit_id": 1})
        hello = ws.receive_json()
        assert hello["state"]["active_mission_id"] == 1
        # commit 一覧（履歴）は残るが、世界はクリア前に戻る = park は再び不可視
        assert [c["id"] for c in hello["commits"]] == [1, 2]
        res, _, _ = _exec(ws, 100, "ls")
        texts = [ln["text"] for ln in res["lines"]]
        assert "park" not in texts
        # resume で story_fired も commit #1 当時（read 未発火）に巻き戻るため、
        # 同じ cat を打つと「read」の独り言が再び発火する
        res, _, _ = _exec(
            ws, 101, "cat /root/desk/businesscard.txt", expect_story=True
        )
        assert "Sam Spade" not in "\n".join(ln["text"] for ln in res["lines"])


def test_ws_resume_to_pushed_commit_lands_after_clear(
    client: TestClient, session: Session
) -> None:
    """push が通った commit へ resume すると、その Mission をクリアした直後に戻る。

    commit は push の前に作られるため、印（pushed）を見ずに snapshot だけ戻すと
    Mission1 に逆戻りして Mission2 の区画（park）が消える（2026-09-13 ユーザー報告）。
    """
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        transcript = [
            ("cat /root/desk/businesscard.txt", True, False),
            ('echo "NAME: Sam Spade" > /root/desk/businesscard.txt', True, False),
            ("sh case_file.sh", True, False),
            ("git add .", False, False),
            ('git commit -m "solved"', False, False),
            ("git push", True, True),
        ]
        for i, (cmd, expect_story, expect_clear) in enumerate(transcript):
            _exec(ws, i, cmd, expect_story=expect_story, expect_clear=expect_clear)
        # Mission2 で少し進めてから（commit せずに）再開する = 最新セーブは push 済み commit #1
        _exec(ws, 10, "cd /root/park", expect_story=True)

        ws.send_json({"type": "resume", "commit_id": 1})
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["commits"] == [
            {
                "id": 1,
                "message": "solved",
                "created_at": hello["commits"][0]["created_at"],
                "mission_id": 1,
                "pushed": True,
            }
        ]
        # 世界はクリア直後: Mission2 が捜査中で park が見える。cwd は commit 時点（/root）
        assert hello["state"]["active_mission_id"] == 2
        assert hello["state"]["current_path"] == "/root"
        # story_fired も commit 時点に戻るので Mission2 の start 独り言が再び届く
        assert [b["id"] for b in hello["story"]] == ["start"]
        assert hello["story"][0]["mission_id"] == 2
        res, _, _ = _exec(ws, 100, "ls")
        assert "park" in [ln["text"] for ln in res["lines"]]
        # 印の無い（push 前の）commit が最新でも、push は現在の Mission と照合される
        res, _, _ = _exec(ws, 101, "git push")
        assert res["ok"] is False

    # DB にも印が残る（再ログイン後の hello でも pushed が見える）
    row = session.exec(select(PlayerState)).one()
    assert row.data["git_state"]["commits"][0]["pushed"] is True
