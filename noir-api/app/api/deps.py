"""API 共通の依存（DB セッション・現在ユーザー）とユーザー操作ヘルパー。"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.models import User
from app.models.db import get_session
from app.security import ACCESS, decode_token, hash_password, verify_password

bearer_scheme = HTTPBearer(auto_error=False)


# --- ユーザー操作（テスト・シード・ログインから利用） ---
def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def create_user(session: Session, username: str, password: str) -> User:
    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


# --- 現在ユーザー（access トークン検証） ---
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        _unauthorized("Error: unauthorized")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        _unauthorized("Error: token expired")
    except jwt.PyJWTError:
        _unauthorized("Error: unauthorized")

    if payload.get("type") != ACCESS:
        _unauthorized("Error: unauthorized")

    user = session.get(User, int(payload["sub"]))
    if user is None:
        _unauthorized("Error: unauthorized")
    return user


def _unauthorized(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
