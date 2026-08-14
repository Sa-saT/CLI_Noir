"""`mission_progress`（Mission横断の進捗dict）を操作するヘルパー（Part5 P3-02）。

永続統合ワールド化（`context/04_task_backlog.md` Part5）に伴い、旧`mission_flags`
（Mission単位のstateが個別に持っていた`completed`）を、ワールド全体で共有する
進捗dictへ置き換える。

`mission_progress`のスキーマ:
    {
        "completed": [1, 2, 3],       # クリア済み mission_id の一覧
        "active_mission_id": 4,       # 未クリアの最小 mission_id（キャッシュ）
        "case_checked": False,        # active_mission_id に対する case_file.sh 判定結果
    }

`active_mission_id`はキャッシュフィールドであり、本モジュールの`active_mission_id()`
関数（純粋関数。completed から都度算出する）の戻り値を書き込むのは
`app/evaluator/progress.py::advance_mission`（Mission解放/クリアの唯一の書き込み箇所。
Part5 P3-05）のみとする。
"""

from app.content.missions import all_missions


def completed_ids(mission_progress: dict) -> set[int]:
    """クリア済み mission_id の集合を返す。"""
    return set(mission_progress.get("completed", []))


def status_for(mission_id: int, mission_progress: dict) -> str:
    """cleared: 完了 / open: 遊べる / locked: 前の Mission 未完了。

    Mission1 は常に open。以降は直前 Mission の完了で解放される（順次解放）。
    `app/api/missions.py::_status_for` と同じロジック（P3-11 でこちらへ差し替える）。
    """
    completed = completed_ids(mission_progress)
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


def active_mission_id(mission_progress: dict) -> int | None:
    """未クリアの最小 mission_id を算出する（全 Mission 完了済みなら None）。

    `mission_progress["active_mission_id"]`（キャッシュ）の値ではなく、
    `completed`から都度算出する純粋関数。キャッシュへの反映は`advance_mission`
    （Part5 P3-05）が行う。
    """
    completed = completed_ids(mission_progress)
    for mission in all_missions():
        if mission.id not in completed:
            return mission.id
    return None
