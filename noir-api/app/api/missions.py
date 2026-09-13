"""Mission API（一覧 / 詳細。読み取りのみ）。

status はユーザー進捗から算出する（cleared / open / locked）。
complete API は廃止 — クリアは git push 時にサーバー内部で記録する
（設計指示書 § 6 / § 疑似Git）。
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.content.field_cards import FIELD_CARDS
from app.content.missions import all_missions, get_mission
from app.evaluator import progress
from app.models import PlayerState, User
from app.models.db import get_session

router = APIRouter()


class MissionSummary(BaseModel):
    id: int
    title: str
    title_ja: str
    status: str
    # スマート捜査ボーナス（機能 3）: クリア済みなら評価（score / commands / par / bonuses / elapsed_seconds）
    score: dict | None = None


class MissionDetail(BaseModel):
    id: int
    title: str
    title_ja: str
    description: str
    allowed_commands: list[str]
    status: str
    hints: list[str]
    # 現場実習カード（§ 11 機能 11）。None は未起草
    field_card: dict | None = None


def _completed_ids(session: Session, user_id: int) -> set[int]:
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == user_id)
    ).first()
    if row is None:
        return set()
    return set(row.data["mission_progress"]["completed"])


def _scores(session: Session, user_id: int) -> dict:
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == user_id)
    ).first()
    if row is None:
        return {}
    return row.data["mission_progress"].get("scores", {})


def _status_for(mission_id: int, completed: set[int]) -> str:
    """cleared: 完了 / open: 遊べる / locked: 前の Mission 未完了。

    Mission1 は常に open。以降は直前 Mission の完了で解放される（順次解放）。
    実体は app/evaluator/progress.py::status_from_completed に委譲（P3-02、
    ロジックの二重管理を避ける）。
    """
    return progress.status_from_completed(mission_id, completed)


@router.get("/", response_model=list[MissionSummary])
def list_missions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MissionSummary]:
    completed = _completed_ids(session, current_user.id)
    scores = _scores(session, current_user.id)
    return [
        MissionSummary(
            id=m.id,
            title=m.title,
            title_ja=m.title_ja,
            status=_status_for(m.id, completed),
            score=scores.get(str(m.id)),
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
        hints=mission.hints,
        field_card=FIELD_CARDS.get(mission.id),
    )


class ReplayEntry(BaseModel):
    n: int
    line: str


class ReplayLedger(BaseModel):
    mission_id: int
    status: str
    commands: list[ReplayEntry]
    score: dict | None = None


@router.get("/{mission_id}/replay/", response_model=ReplayLedger)
def mission_replay(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ReplayLedger:
    """リプレイ台帳（§ 11 機能 8）: その Mission で自分が打った（成功した）コマンドを実行順に返す。

    復習 = LPIC 対策。command_log は成功したコマンドだけなので、失敗した試行は載らない
    （エラー図鑑が受け持つ）。未着手の Mission は空。
    """
    if get_mission(mission_id) is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Error: mission not found")
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    ).first()
    if row is None:
        return ReplayLedger(mission_id=mission_id, status="locked", commands=[])
    data = row.data
    completed = set(data["mission_progress"]["completed"])
    entries = [
        e["line"]
        for e in data.get("resolved_command_log", [])
        if e.get("mission_id") == mission_id
    ]
    return ReplayLedger(
        mission_id=mission_id,
        status=_status_for(mission_id, completed),
        commands=[ReplayEntry(n=i + 1, line=line) for i, line in enumerate(entries)],
        score=data["mission_progress"].get("scores", {}).get(str(mission_id)),
    )
