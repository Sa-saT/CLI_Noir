"""認証 API（login / refresh / me）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user


def test_login_success_and_me(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")

    res = client.post("/api/auth/login/", json={"username": "detective01", "password": "secret"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    me = client.get("/api/auth/me/", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {"id": 1, "username": "detective01"}


def test_login_wrong_password(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    res = client.post("/api/auth/login/", json={"username": "detective01", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Error: unauthorized"


def test_me_without_token(client: TestClient) -> None:
    res = client.get("/api/auth/me/")
    assert res.status_code == 401


def test_refresh_issues_new_access(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    login = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()

    res = client.post("/api/auth/refresh/", json={"refresh_token": login["refresh_token"]})
    assert res.status_code == 200
    assert res.json()["access_token"]

    # access トークンを refresh に使うと拒否される
    bad = client.post("/api/auth/refresh/", json={"refresh_token": login["access_token"]})
    assert bad.status_code == 401
