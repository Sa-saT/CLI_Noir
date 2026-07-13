"""Mission API（一覧 / 詳細）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.models import MissionState, default_state


def _auth_header(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


def _complete(session: Session, user_id: int, mission_id: int) -> None:
    state = default_state()
    state["mission_flags"]["completed"] = True
    session.add(MissionState(user_id=user_id, mission_id=mission_id, data=state))
    session.commit()


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/api/missions/").status_code == 401


def test_list_initial_unlock(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    res = client.get("/api/missions/", headers=_auth_header(client))
    assert res.status_code == 200
    missions = res.json()
    assert len(missions) == 22
    by_id = {m["id"]: m for m in missions}
    assert by_id[1]["status"] == "open"
    assert by_id[2]["status"] == "locked"
    assert by_id[1]["title"] == "Edit Business Card"


def test_unlock_progresses_after_completion(client: TestClient, session: Session) -> None:
    user = create_user(session, "detective01", "secret")
    _complete(session, user.id, 1)
    by_id = {m["id"]: m for m in client.get("/api/missions/", headers=_auth_header(client)).json()}
    assert by_id[1]["status"] == "cleared"
    assert by_id[2]["status"] == "open"
    assert by_id[3]["status"] == "locked"


def test_detail_and_not_found(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    headers = _auth_header(client)

    detail = client.get("/api/missions/1/", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Edit Business Card"
    assert "git" in body["allowed_commands"]
    assert body["status"] == "open"

    missing = client.get("/api/missions/999/", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Error: mission not found"
