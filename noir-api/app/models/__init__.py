"""SQLModel テーブル定義（User / MissionState / PlayerState）。

MissionState は user_id + mission_id 単位で 1 レコード（旧方式・カットオーバーまで残す）。
PlayerState は user_id 単位で 1 レコード（Part5 永続統合ワールド化。
`context/04_task_backlog.md` Part5 参照）。
current_path / filesystem / remote_mode / ssh_host / env_vars / git_state /
mission_flags 等を JSON カラム（`data`）に永続化する（設計指示書 § 4）。

Alembic の autogenerate はここで re-export したテーブルを SQLModel.metadata
経由で検出する。
"""

from app.models.tables import MissionState, PlayerState, User, default_state

__all__ = ["MissionState", "PlayerState", "User", "default_state"]
