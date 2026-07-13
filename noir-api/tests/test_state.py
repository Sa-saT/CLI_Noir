"""state API（取得のみ）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.models import MissionState, default_state


def _auth_header(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


def test_state_not_found_when_missing(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    res = client.get("/api/missions/1/state/", headers=_auth_header(client))
    assert res.status_code == 404
    assert res.json()["detail"] == "Error: state not found"


def test_state_returns_summary_without_snapshot(client: TestClient, session: Session) -> None:
    user = create_user(session, "detective01", "secret")
    state = default_state()
    state["current_path"] = "/root/desk"
    state["git_state"]["commits"] = [
        {
            "id": 1,
            "message": "探索メモ",
            "snapshot": {"filesystem": {"secret": True}},
            "created_at": "2026-01-01T12:00:00Z",
        }
    ]
    session.add(MissionState(user_id=user.id, mission_id=1, data=state))
    session.commit()

    res = client.get("/api/missions/1/state/", headers=_auth_header(client))
    assert res.status_code == 200
    body = res.json()
    assert body["mission_id"] == 1
    assert body["current_path"] == "/root/desk"
    assert body["remote_mode"] is False
    # commits はメタのみ、snapshot 本体・filesystem は返さない
    commit = body["git_state"]["commits"][0]
    assert commit == {"id": 1, "message": "探索メモ", "created_at": "2026-01-01T12:00:00Z"}
    assert "filesystem" not in body
    assert "snapshot" not in commit


def test_state_requires_auth(client: TestClient) -> None:
    assert client.get("/api/missions/1/state/").status_code == 401
