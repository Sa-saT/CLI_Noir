"""SQLModel テーブル定義（User / PlayerState）。

PlayerState は Part5 永続統合ワールド化で追加した user_id 単位（1 ユーザー1
ワールド）のテーブル。current_path / filesystem / remote_mode / ssh_host /
env_vars / git_state / mission_progress を JSON カラム（`data`）に永続化する
（設計指示書 § 4）。旧 MissionState（mission_id 単位）は Phase F で廃止した。

Alembic の autogenerate はここで re-export したテーブルを SQLModel.metadata
経由で検出する。
"""

from app.models.tables import (
    PlayerState,
    User,
    default_world_state,
)

__all__ = [
    "PlayerState",
    "User",
    "default_world_state",
]
