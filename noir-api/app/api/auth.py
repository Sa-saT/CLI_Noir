"""認証 API（login / refresh / me）。

PyJWT + bcrypt を直接使用（passlib 廃止。設計指示書 § 認証）。
access 30分 / refresh 7日。パスワードは bcrypt の 72 バイト上限に留意。

未実装（context/03_pending_items.md「認証 API 実装」）。
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: POST /login   … 認証してアクセス/リフレッシュトークンを発行
# TODO: POST /refresh … リフレッシュトークンからアクセストークンを再発行
# TODO: GET  /me      … Bearer トークンから現在ユーザーを返す
