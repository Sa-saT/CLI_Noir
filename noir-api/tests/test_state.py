"""state API（取得のみ）のテスト。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import create_user
from app.models import MissionState, PlayerState, default_state, default_world_state


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


# --- Part5 P3-01: PlayerState（永続統合ワールド）------------------------------


def test_player_state_json_roundtrip(session: Session) -> None:
    user = create_user(session, "detective01", "secret")
    world = default_world_state()
    world["current_path"] = "/root/desk"
    session.add(PlayerState(user_id=user.id, data=world))
    session.commit()

    fetched = session.exec(
        select(PlayerState).where(PlayerState.user_id == user.id)
    ).one()
    assert fetched.data["current_path"] == "/root/desk"
    assert fetched.data["mission_progress"]["active_mission_id"] == 1


def test_player_state_user_id_is_unique(session: Session) -> None:
    user = create_user(session, "detective01", "secret")
    session.add(PlayerState(user_id=user.id, data=default_world_state()))
    session.commit()

    session.add(PlayerState(user_id=user.id, data=default_world_state()))
    with pytest.raises(IntegrityError):
        session.commit()


def test_default_world_state_schema() -> None:
    world = default_world_state()
    expected_keys = {
        "current_path",
        "filesystem",
        "remote_mode",
        "ssh_host",
        "current_user",
        "processes",
        "cron_jobs",
        "env_vars",
        "command_log",
        "resolved_command_log",
        "git_state",
        "mission_progress",
    }
    assert expected_keys <= world.keys()
    assert world["mission_progress"]["active_mission_id"] == 1
    assert world["mission_progress"]["completed"] == []
    assert world["mission_progress"]["flags"] == {"case_checked": False}
    assert world["env_vars"]["detective"]["HOME"] == "/root"
    assert world["resolved_command_log"] == []
    assert world["command_log"] == []
