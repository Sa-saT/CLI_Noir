"""認証 API（login / refresh / me）。

PyJWT + bcrypt を直接使用（passlib 廃止。設計指示書 § 認証）。
access 30分 / refresh 7日。エラー文言は設計指示書 § 12 に準拠。
"""

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import authenticate_user, get_current_user
from app.models import User
from app.models.db import get_session
from app.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: int
    username: str


@router.post("/login/", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = authenticate_user(session, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Error: unauthorized"
        )
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/refresh/", response_model=TokenResponse)
def refresh(body: RefreshRequest) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Error: token expired"
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Error: unauthorized"
        ) from None

    if payload.get("type") != REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Error: unauthorized"
        )
    return TokenResponse(access_token=create_access_token(payload["sub"]))


@router.get("/me/", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=current_user.id, username=current_user.username)
