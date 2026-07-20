"""SQLModel テーブル定義（User / MissionState）。

MissionState は user_id + mission_id 単位で 1 レコード。ゲーム state 全体
（current_path / filesystem / remote_mode / ssh_host / env_vars / git_state /
mission_flags）を `data` JSON カラムに永続化する（設計指示書 § 4）。
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=_utcnow)


class MissionState(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("user_id", "mission_id", name="uq_user_mission"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    mission_id: int = Field(index=True)
    # ゲーム state 全体（default_state() のスキーマ）を丸ごと保持する。
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_utcnow)


def default_state() -> dict:
    """初期 state（設計指示書 § 4 の JSON スキーマ）。

    filesystem は Mission 定義で上書きする（初期配置ファイル）。ここでは
    空の root ディレクトリのみを持つ最小構造を返す。
    """
    return {
        # 判定対象の Mission（case_file.sh がパターンを引くのに使う。非機密）
        "mission_id": None,
        "current_path": "/root",
        "filesystem": {
            "root": {"type": "dir", "children": {}},
        },
        "remote_mode": False,
        "ssh_host": None,
        # 現在のユーザー（su/whoami/id・owner ベースの読み取り権限判定に使う）。
        "current_user": "detective",
        # 仮想プロセステーブル（ps/kill・/proc の対象。設計指示書 § 4 疑似 /proc）。
        # {"pid": int, "name": str, "user": str, "cmdline": str, "state": str,
        #  "protected": bool}。Mission 定義の initial_processes で上書きする。
        "processes": [],
        # 仮想 cron テーブル（crontab -l の対象）。
        # {"id": int, "schedule": str, "command": str, "malicious": bool}。
        # 書き込み系（crontab -r 等）は実装せず閲覧のみ（rm 禁止と同じ方針）。
        "cron_jobs": [],
        "env_vars": {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/root",
        },
        # 実行に成功したコマンド行の履歴（case_file.sh 判定・リプレイ台帳に使う）
        "command_log": [],
        "git_state": {
            "staged": [],
            "commits": [],
            "pushed": False,
        },
        "mission_flags": {
            "case_checked": False,
            "completed": False,
        },
    }
