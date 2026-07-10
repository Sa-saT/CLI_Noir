"""WebSocket ターミナルエンドポイント `/ws/terminal`。

プロトコル（設計指示書 § 7）:
  接続 → 初回 `auth` フレームで JWT 認証 → `hello` で state 返却
       → `exec` / `result` フレームでコマンド実行
  判定順序: denylist → allowlist → evaluator → state 更新
  ※ state とクリア判定の書き込みは evaluator のみ。

フレームは Pydantic モデルで型付けする（未実装）。
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: @router.websocket("/ws/terminal")
#   1. accept
#   2. 初回メッセージ(auth フレーム)で JWT を検証（query parameter は不採用）
#   3. mission_id の state を復元し hello フレームを返す
#   4. exec フレームを受けて evaluator に渡し result フレームを返す
