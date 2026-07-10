"""SQLModel テーブル定義（User / MissionState）。

MissionState は user_id + mission_id 単位で 1 レコード。
current_path / filesystem / remote_mode / git_state / mission_flags / env_vars を
JSON カラムに永続化する（設計指示書 § 4 / アーキテクチャの要点）。

テーブル定義は未実装（context/03_pending_items.md「仮想FS モデル / JSON保存」）。
"""
