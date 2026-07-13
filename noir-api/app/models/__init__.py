"""SQLModel テーブル定義（User / MissionState）。

MissionState は user_id + mission_id 単位で 1 レコード。
current_path / filesystem / remote_mode / ssh_host / env_vars / git_state /
mission_flags を JSON カラム（`data`）に永続化する（設計指示書 § 4）。

Alembic の autogenerate はここで re-export したテーブルを SQLModel.metadata
経由で検出する。
"""

from app.models.tables import MissionState, User, default_state

__all__ = ["MissionState", "User", "default_state"]
