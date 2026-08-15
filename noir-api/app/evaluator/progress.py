"""`mission_progress` 読み書きヘルパー（Part5, P3-02）。

PlayerState.data["mission_progress"] のスキーマ（app/models/tables.py::default_world_state()
参照）を対象にした純粋関数群。DB・I/O には一切依存しない。

Mission 解放/クリアの書き込みは P3-05 の `advance_mission` に集約し、`active_mission_id`
キャッシュの更新は本モジュールの `refresh_active_mission_id` 経由のみで行う。それ以外の
関数はすべて引数の `mission_progress` を変更しない（副作用なし）。
"""

from app.content.missions import all_missions


def completed_ids(mission_progress: dict) -> set[int]:
    """クリア済み mission_id の集合。

    `mission_progress` に "completed" キーが無い場合も空集合として扱う。
    """
    return set(mission_progress.get("completed", []))


def status_from_completed(mission_id: int, completed: set[int]) -> str:
    """cleared / open / locked を返す。

    Mission1 は常に open。以降は直前 Mission の完了で順次解放される
    （既存 app/api/missions.py::_status_for と同一ロジック）。
    """
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


def status_for(mission_id: int, mission_progress: dict) -> str:
    """status_from_completed(mission_id, completed_ids(mission_progress)) と同義。"""
    return status_from_completed(mission_id, completed_ids(mission_progress))


def compute_active_mission_id(mission_progress: dict) -> int | None:
    """未クリアの最小 mission_id を再計算する（キャッシュを読まない純粋計算）。

    全 Mission クリア済みなら None を返す。
    """
    completed = completed_ids(mission_progress)
    for mission in all_missions():
        if mission.id not in completed:
            return mission.id
    return None


def refresh_active_mission_id(mission_progress: dict) -> int | None:
    """compute_active_mission_id() で再計算し active_mission_id に書き戻す。

    `mission_progress["active_mission_id"]` キャッシュの唯一の書き込み口
    （P3-05 の advance_mission から呼ぶ）。戻り値は書き戻した値と同じ。
    """
    active = compute_active_mission_id(mission_progress)
    mission_progress["active_mission_id"] = active
    return active


def active_mission_id(mission_progress: dict) -> int | None:
    """キャッシュ済み active_mission_id を読む。

    キーが無い場合のみ再計算にフォールバックする（この場合も mission_progress
    への書き戻しは行わない＝読み取りは副作用なし）。
    """
    if "active_mission_id" in mission_progress:
        return mission_progress["active_mission_id"]
    return compute_active_mission_id(mission_progress)
