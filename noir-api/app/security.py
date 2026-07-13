"""パスワードハッシュと JWT の発行/検証（純粋関数の薄いラッパ）。

FastAPI では SimpleJWT が使えないため、PyJWT で access/refresh を自前実装する
（設計指示書 § 認証: access 30分 / refresh 7日）。パスワードは bcrypt を直接使用。

bcrypt は入力を 72 バイトで切り詰めるため、SHA-256 → base64 で事前ハッシュしてから
渡す（長いパスワードでの静かな衝突を避ける。設計指示書 § 認証の注意に対応）。
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.settings import settings

ACCESS = "access"
REFRESH = "refresh"


# --- パスワード ---
def _prehash(password: str) -> bytes:
    """SHA-256 → base64（44 バイト、bcrypt の 72 バイト上限内）。"""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(password), hashed.encode("utf-8"))


# --- JWT ---
def _create_token(subject: str, token_type: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject, ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict:
    """JWT を検証してペイロードを返す。

    期限切れ・不正トークンは jwt.PyJWTError（ExpiredSignatureError 等）を送出する。
    呼び出し側で捕捉して適切なエラー（token expired / unauthorized）に変換する。
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
