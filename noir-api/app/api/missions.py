"""Mission API（一覧 / 詳細。読み取りのみ）。

status はユーザー進捗から算出する（cleared / open / locked）。
complete API は廃止 — クリアは git push 時にサーバー内部で記録する
（設計指示書 § 6 / § 疑似Git）。
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.content.missions import all_missions, get_mission
from app.models import MissionState, User
from app.models.db import get_session

router = APIRouter()


class MissionSummary(BaseModel):
    id: int
    title: str
    title_ja: str
    status: str


class MissionDetail(BaseModel):
    id: int
    title: str
    title_ja: str
    description: str
    allowed_commands: list[str]
    status: str


def _completed_ids(session: Session, user_id: int) -> set[int]:
    rows = session.exec(
        select(MissionState).where(MissionState.user_id == user_id)
    ).all()
    return {
        r.mission_id
        for r in rows
        if r.data.get("mission_flags", {}).get("completed")
    }


def _status_for(mission_id: int, completed: set[int]) -> str:
    """cleared: 完了 / open: 遊べる / locked: 前の Mission 未完了。

    Mission1 は常に open。以降は直前 Mission の完了で解放される（順次解放）。
    """
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


@router.get("/", response_model=list[MissionSummary])
def list_missions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MissionSummary]:
    completed = _completed_ids(session, current_user.id)
    return [
        MissionSummary(
            id=m.id,
            title=m.title,
            title_ja=m.title_ja,
            status=_status_for(m.id, completed),
        )
        for m in all_missions()
    ]


@router.get("/{mission_id}/", response_model=MissionDetail)
def mission_detail(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MissionDetail:
    mission = get_mission(mission_id)
    if mission is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Error: mission not found",
        )
    completed = _completed_ids(session, current_user.id)
    return MissionDetail(
        id=mission.id,
        title=mission.title,
        title_ja=mission.title_ja,
        description=mission.description,
        allowed_commands=mission.allowed_commands,
        status=_status_for(mission.id, completed),
    )
