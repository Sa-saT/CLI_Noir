"""WebSocket /ws/terminal のテスト（ハンドシェイク・exec・Mission1 クリア）。"""

from fastapi.testclient import TestClient
from sqlmodel import Session
from starlette.websockets import WebSocketDisconnect

import pytest

from app.api.deps import create_user


def _token(client: TestClient) -> str:
    return client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]


def test_ws_handshake_and_exec(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["state"]["current_path"] == "/root"

        ws.send_json({"type": "exec", "id": 1, "command": "ls"})
        res = ws.receive_json()
        assert res["type"] == "result"
        assert res["id"] == 1
        assert res["ok"] is True
        texts = [ln["text"] for ln in res["lines"]]
        assert "case_file.sh" in texts and "desk" in texts


def test_ws_rejects_bad_token(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
        ws.send_json({"type": "auth", "token": "not-a-jwt"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_ws_denylist_result_not_ok(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
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
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()

        transcript = [
            "cat /root/desk/businesscard.txt",
            'echo "NAME: Sam Spade" > /root/desk/businesscard.txt',
            "sh case_file.sh",
            "git add .",
            'git commit -m "solved"',
            "git push",
        ]
        last = None
        for i, cmd in enumerate(transcript):
            ws.send_json({"type": "exec", "id": i, "command": cmd})
            last = ws.receive_json()
            assert last["type"] == "result"

        assert last["ok"] is True
        assert last["lines"][0]["text"] == "Mission Complete! Next mission unlocked."
        # push 後に mission_clear イベントが届く
        event = ws.receive_json()
        assert event["type"] == "event"
        assert event["name"] == "mission_clear"
        assert event["next_mission_id"] == 2


def test_ws_state_persists_across_reconnect(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        ws.send_json({"type": "exec", "id": 1, "command": "cd /root/desk"})
        ws.receive_json()

    # 再接続時に current_path が復元される
    with client.websocket_connect("/ws/terminal?mission_id=1") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert hello["state"]["current_path"] == "/root/desk"
