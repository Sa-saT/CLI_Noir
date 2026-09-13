"""Mission API（一覧 / 詳細）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.content.missions import all_missions
from app.evaluator import progress
from app.models import PlayerState, default_world_state


def _auth_header(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


def _complete(session: Session, user_id: int, mission_id: int) -> None:
    """mission_id までの Mission を順にクリア済みにした PlayerState を 1 行 add する。"""
    state = default_world_state()
    for mid in range(1, mission_id + 1):
        progress.advance_mission(state, mid)
    session.add(PlayerState(user_id=user_id, data=state))
    session.commit()


def test_list_requires_auth(client: TestClient) -> None:
    assert client.get("/api/missions/").status_code == 401


def test_list_initial_unlock(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    res = client.get("/api/missions/", headers=_auth_header(client))
    assert res.status_code == 200
    missions = res.json()
    assert len(missions) == 29
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
    assert len(body["hints"]) == 3
    assert body["hints"][0] == (
        "ゴール: /root/desk/businesscard.txt に自分の名前を書き込み、"
        "sh case_file.sh で確認 → git add → git commit -m → git push で提出する。"
    )

    missing = client.get("/api/missions/999/", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Error: mission not found"


def test_detail_hints_are_authored_for_all_missions(
    client: TestClient, session: Session
) -> None:
    """全 Mission に直接ヒントがある（Mission22 は最終事件のため 1 段階のみ）。"""
    create_user(session, "detective01", "secret")
    headers = _auth_header(client)

    for mission_id in [m for m in range(1, 30) if m != 22]:
        detail = client.get(f"/api/missions/{mission_id}/", headers=headers).json()
        assert len(detail["hints"]) == 3, mission_id

    mission22 = client.get("/api/missions/22/", headers=headers).json()
    assert len(mission22["hints"]) == 1


def test_detail_carries_a_field_card_for_every_mission(
    client: TestClient, session: Session
) -> None:
    """現場実習カード（§ 11 機能 11）: 全 Mission に安全な読み取り系の手順が付く。"""
    create_user(session, "detective01", "secret")
    headers = _auth_header(client)
    for m in all_missions():
        detail = client.get(f"/api/missions/{m.id}/", headers=headers).json()
        card = detail["field_card"]
        assert card and card["lead"] and card["steps"], m.id
        for step in card["steps"]:
            assert "rm " not in step["cmd"] and "dd " not in step["cmd"], (m.id, step)
