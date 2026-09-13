"""SQLModel テーブル定義（User / PlayerState）。

PlayerState は Part5「永続統合ワールド化」（context/04_task_backlog.md § Part 5）
向けのテーブルで、user_id 単位で 1 レコード（ユーザーごとに 1 つの永続的な仮想
世界を持つ）。旧 MissionState（user_id + mission_id 単位・`default_state()` の
スキーマ）は API/WS 層のカットオーバー（P3-10/P3-11）完了後、Phase F で廃止した
（missionstate テーブルの drop は Alembic リビジョンを参照）。
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.content.missions import build_world_filesystem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=_utcnow)


class PlayerState(SQLModel, table=True):
    """ユーザーごとに 1 レコード持つ永続統合ワールドの state（Part5）。

    `data` は default_world_state() のスキーマに従う仮想世界全体（filesystem /
    git_state / mission_progress 等）を丸ごと保持する。user_id は unique
    （1 ユーザー1 ワールド）。
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_utcnow)


def default_world_state() -> dict:
    """永続統合ワールド（PlayerState）の初期 state（Part5、2026-08-12 設計確定）。

    Mission 単位に分離されていた default_state() と異なり、ユーザーごとに 1 つの
    仮想世界全体を表す。P3-01 時点ではスキーマの枠組みのみを定義し、以下は後続
    Milestone で埋める（今回はこの関数を書くだけで、呼び出し側の切り替えは行わない）:
    - filesystem: P3-03 で 22 Mission 分の区画を持つ `_WORLD_FS` に置き換え済み
      （未解放区画は mode="---------"/owner="system" で不可視。解放は P3-05）
    - processes: 解放済み Mission の分だけ P3-05 で積まれる
    - resolved_command_log: P3-08a で {"line", "resolved_line", "paths", "mission_id"}
      の記録基盤が実装済み（判定側の参照は次段の P3-08b で行う）

    env_vars は「PATH汚染をユーザーアカウントに閉じ込める」ためユーザー別 dict に
    なっている。evaluator 側の追随は P3-04c で完了済み（`app/evaluator/env.py` の
    `env_for(state)` がフラット/ユーザー別の両形状を吸収する）。
    `app/evaluator/git_ops.py` のスナップショットは env_vars を丸ごと deepcopy する
    だけなので、どちらの形状でもそのまま動く。
    """
    return {
        "current_path": "/root",
        # Mission 定義の initial filesystem ではなく、22 Mission 分の区画を最初
        # から実体として持つ統合ワールド構造（P3-03）。未解放区画はディレクトリ
        # 権限で不可視にしてあり、クリア進行に応じて解放される。
        "filesystem": build_world_filesystem(),
        "remote_mode": False,
        "ssh_host": None,
        # 現在のユーザー（su/whoami/id・owner ベースの読み取り権限判定に使う）。
        "current_user": "detective",
        # 仮想プロセステーブル（ps/kill・/proc の対象）。解放済み Mission の分だけ
        # P3-05 で追加される（Mission 単位の initial_processes 一括投入をやめる）。
        "processes": [],
        # 仮想 cron テーブル（crontab -l の対象）。閲覧のみ（rm 禁止と同じ方針）。
        "cron_jobs": [],
        # ユーザー別 dict（旧: フラットな PATH/HOME dict）。su 先アカウントごとに
        # 環境を分けるための形状。Mission21 の PATH 汚染は解放時に detective 自身の
        # バケットへ書かれる（release_missions。2026-09-13 に「本人の環境を汚す」で確定）。
        "env_vars": {
            "detective": {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/root",
            },
        },
        # 実行に成功したコマンド行の生テキスト履歴（リプレイ台帳・実 bash 風履歴）。
        # BUG-01 対応として生テキストのままにし、判定は resolved_command_log 側に
        # 寄せる（P3-08）。
        "command_log": [],
        # {"line", "resolved_line", "paths", "mission_id"} を積む解決済みコマンドログ
        # （P3-08 新設）。command_log と並行して記録し、判定側（case_file.sh 相当）は
        # こちらを見る。
        "resolved_command_log": [],
        # Git commit 履歴はプレイ全体で 1 本（Mission 単位のリセットをやめる。
        # ゲーム機能「リプレイ台帳」の土台）。
        "git_state": {
            "staged": [],
            "commits": [],
            "pushed": False,
        },
        # Mission 横断の進捗管理（旧 mission_flags を置き換え）。
        "mission_progress": {
            # クリア済み mission_id の昇順リスト
            "completed": [],
            # 未クリアの最小 mission_id（キャッシュ。P3-02/P3-05 が更新する）
            "active_mission_id": 1,
            # アクティブ Mission に対する一時フラグ（旧 mission_flags 相当。
            # completed は mission_progress.completed に吸収済みのためここには
            # 持たない）
            "flags": {"case_checked": False},
            # 解放処理（progress.release_missions, P3-05）を実施済みの mission_id
            # リスト。冪等性の保証に使う（同じ Mission を二重解放してプロセス復活や
            # /etc/hosts 二重追記を起こさないため）。
            "released": [],
            # 発火済み独り言（story_beats）の記録（STORY-01）。str(mission_id) →
            # 発火済み beat id のリスト。app/evaluator/story.py が読み書きする。
            "story_fired": {},
        },
    }
