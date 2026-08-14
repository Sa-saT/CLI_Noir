"""SQLModel テーブル定義（User / MissionState / PlayerState）。

MissionState は user_id + mission_id 単位で 1 レコード（旧方式）。Part5「永続統合
ワールド化」（`context/04_task_backlog.md`）により PlayerState（user_id 単位で
1 レコード = 永続的な統合ワールド）へ移行する。移行中も既存テストを常時緑に保つため
MissionState は残したまま PlayerState を追加し、P3-09/P3-10 で API/WS 層を
カットオーバーする（追加 → カットオーバー方式。MissionState の削除はカットオーバー後）。

ゲーム state 全体（current_path / filesystem / remote_mode / ssh_host / env_vars /
git_state / mission_flags 等）を `data` JSON カラムに永続化する（設計指示書 § 4）。
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


class PlayerState(SQLModel, table=True):
    """ユーザーごとに1つの永続的な統合ワールド state（Part5 P3-01）。

    22 Mission 分の仮想FS・進捗・環境変数を丸ごと1レコードに保持する
    （`app/evaluator/progress.py` の `mission_progress` ヘルパー・
    `app/content/missions.py::_build_world_fs()` が対応する。P3-09/P3-10 で
    `app/ws/terminal.py` / `app/api/*` をこのテーブルへカットオーバーする）。
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    # ゲーム state 全体（default_world_state() のスキーマ）を丸ごと保持する。
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
        # command_log と並行して積む解決済みパスの記録（Part5 P3-08 BUG-01）。
        # 各要素: {"line": <生テキスト>, "paths": [<絶対パス>, ...], "mission_id": <int|None>}。
        # command_log は生テキストのまま維持し（リプレイ台帳・実 bash 風履歴のため）、
        # 判定側（judge.py）はこちらも検索対象に含める。mission_id はリプレイ台帳の
        # Mission別フィルタ用（Part5 P3-09）。
        "resolved_command_log": [],
        "git_state": {
            "staged": [],
            "commits": [],
            "pushed": False,
        },
        "mission_flags": {
            "case_checked": False,
            "completed": False,
        },
        # Mission横断の進捗dict（Part5 P3-02。永続統合ワールドの `mission_flags` 後継）。
        # 旧 MissionState フローは引き続き mission_flags を見るため、このフィールドは
        # 追加のみ（既存挙動に影響なし）。`app/evaluator/progress.py` 参照。
        "mission_progress": {
            "completed": [],
            "active_mission_id": 1,
            "case_checked": False,
        },
    }
