"""Mission API（一覧 / 詳細。読み取りのみ）。

complete API は廃止 — クリアは git push 時にサーバー内部で記録する
（設計指示書 § 疑似Git / context/03_pending_items.md）。

未実装。
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: GET /            … Mission 一覧
# TODO: GET /{mission_id} … Mission 詳細
