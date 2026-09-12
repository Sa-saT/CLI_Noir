"""state API（取得のみ）。GET /api/state/

セーブ選択 UI 用のサマリを返す（設計指示書 § 6）。commits は一覧表示用メタ
（id / message / created_at / mission_id）のみで、snapshot 本体・filesystem・
env_vars は返さない（フル state は WS の hello フレームで受け取る）。
ユーザーごとの永続統合ワールド（PlayerState）を対象とするため mission_id は
パスに含まない（旧 `/api/missions/{id}/state/` は廃止。P3-11）。
更新 API は設けない — 書き込みは WS evaluator のみ。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.models import PlayerState, User
from app.models.db import get_session

router = APIRouter()


class CommitMeta(BaseModel):
    id: int
    message: str
    created_at: str | None = None
    mission_id: int | None = None


class GitStateSummary(BaseModel):
    staged: list[str]
    commits: list[CommitMeta]
    pushed: bool


class StateResponse(BaseModel):
    active_mission_id: int | None
    current_path: str
    current_user: str
    remote_mode: bool
    ssh_host: str | None
    git_state: GitStateSummary
    mission_progress: dict[str, Any]


@router.get("/", response_model=StateResponse)
def get_state(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StateResponse:
    row = session.exec(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    ).first()
    # 初回は WS 接続時にサーバーが state を生成するため、未作成は 404。
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Error: state not found"
        )

    data = row.data
    git = data.get("git_state", {})
    mission_progress = data.get("mission_progress", {})
    commits = [
        CommitMeta(
            id=c["id"],
            message=c.get("message", ""),
            created_at=c.get("created_at"),
            mission_id=c.get("mission_id"),
        )
        for c in git.get("commits", [])
    ]
    return StateResponse(
        active_mission_id=mission_progress.get("active_mission_id"),
        current_path=data.get("current_path", "/root"),
        current_user=data.get("current_user", "detective"),
        remote_mode=data.get("remote_mode", False),
        ssh_host=data.get("ssh_host"),
        git_state=GitStateSummary(
            staged=git.get("staged", []),
            commits=commits,
            pushed=git.get("pushed", False),
        ),
        mission_progress=mission_progress,
    )
