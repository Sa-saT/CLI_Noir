"""state API（取得のみ）。/api/missions/{id}/state/

セーブ選択 UI 用のサマリを返す（設計指示書 § 6）。commits は一覧表示用メタ
（id / message / created_at）のみで、snapshot 本体・filesystem・env_vars は返さない
（フル state は WS の hello フレームで受け取る）。
更新 API は設けない — 書き込みは WS evaluator のみ。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.models import MissionState, User
from app.models.db import get_session

router = APIRouter()


class CommitMeta(BaseModel):
    id: int
    message: str
    created_at: str | None = None


class GitStateSummary(BaseModel):
    staged: list[str]
    commits: list[CommitMeta]
    pushed: bool


class StateResponse(BaseModel):
    mission_id: int
    current_path: str
    remote_mode: bool
    ssh_host: str | None
    git_state: GitStateSummary
    mission_flags: dict[str, Any]


@router.get("/{mission_id}/state/", response_model=StateResponse)
def get_state(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StateResponse:
    row = session.exec(
        select(MissionState).where(
            MissionState.user_id == current_user.id,
            MissionState.mission_id == mission_id,
        )
    ).first()
    # 初回は WS 接続時にサーバーが state を生成するため、未作成は 404。
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Error: state not found"
        )

    data = row.data
    git = data.get("git_state", {})
    commits = [
        CommitMeta(
            id=c["id"], message=c.get("message", ""), created_at=c.get("created_at")
        )
        for c in git.get("commits", [])
    ]
    return StateResponse(
        mission_id=mission_id,
        current_path=data.get("current_path", "/root"),
        remote_mode=data.get("remote_mode", False),
        ssh_host=data.get("ssh_host"),
        git_state=GitStateSummary(
            staged=git.get("staged", []),
            commits=commits,
            pushed=git.get("pushed", False),
        ),
        mission_flags=data.get("mission_flags", {}),
    )
