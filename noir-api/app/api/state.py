"""state API（取得のみ）。

更新 API は廃止 — state の書き込みは WS evaluator のみ（設計指示書 § WebSocket）。
current_path / filesystem / remote_mode / git_state / mission_flags / env_vars を返す。

未実装。
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: GET /{mission_id} … user_id + mission_id の仮想FS state を返す（読み取り専用）
