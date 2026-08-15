"""SQLModel テーブル定義（User / MissionState / PlayerState）。

MissionState は user_id + mission_id 単位で 1 レコード。
current_path / filesystem / remote_mode / ssh_host / env_vars / git_state /
mission_flags を JSON カラム（`data`）に永続化する（設計指示書 § 4）。

PlayerState は Part5 永続統合ワールド化で追加した user_id 単位（1 ユーザー1
ワールド）のテーブル。MissionState はカットオーバー（P3-10/P3-11）まで並存する。

Alembic の autogenerate はここで re-export したテーブルを SQLModel.metadata
経由で検出する。
"""

from app.models.tables import (
    MissionState,
    PlayerState,
    User,
    default_state,
    default_world_state,
)

__all__ = [
    "MissionState",
    "PlayerState",
    "User",
    "default_state",
    "default_world_state",
]
