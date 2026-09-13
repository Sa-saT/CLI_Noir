"""図鑑 API（取得のみ）。GET /api/codex/ — 道具図鑑とエラー図鑑（設計指示書 § 11 機能 2・10）。

登録は WS evaluator 側（app/evaluator/codex.py）だけが行う。未接続（PlayerState 未作成）は
空の図鑑を返す。
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.evaluator import codex
from app.models import PlayerState, User
from app.models.db import get_session

router = APIRouter()


@router.get("/")
def get_codex(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    ).first()
    if row is None:
        return {"commands": [], "errors": []}
    return codex.listing(row.data)
