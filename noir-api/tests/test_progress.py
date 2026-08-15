"""app/evaluator/progress.py のテスト（P3-02）。

mission_progress ヘルパーの純粋関数群を検証する。DB は使わない。
"""

from app.content.missions import all_missions
from app.evaluator import progress
from app.models.tables import default_world_state

_ALL_IDS = [m.id for m in all_missions()]


def _reference_status_for(mission_id: int, completed: set[int]) -> str:
    """変更前の app/api/missions.py::_status_for のロジックをベタ書きした参照実装。

    パリティテスト用（progress.status_from_completed と結果が一致するはず）。
    """
    if mission_id in completed:
        return "cleared"
    if mission_id == 1 or (mission_id - 1) in completed:
        return "open"
    return "locked"


# ---------------------------------------------------------------------------
# completed_ids
# ---------------------------------------------------------------------------


def test_completed_ids_missing_key() -> None:
    assert progress.completed_ids({}) == set()


def test_completed_ids_empty() -> None:
    assert progress.completed_ids({"completed": []}) == set()


def test_completed_ids_multiple() -> None:
    assert progress.completed_ids({"completed": [1, 2, 5]}) == {1, 2, 5}


# ---------------------------------------------------------------------------
# status_from_completed / status_for
# ---------------------------------------------------------------------------


def test_status_mission1_open_even_if_empty() -> None:
    assert progress.status_from_completed(1, set()) == "open"


def test_status_open_after_previous_cleared() -> None:
    assert progress.status_from_completed(2, {1}) == "open"


def test_status_locked_if_previous_not_cleared() -> None:
    assert progress.status_from_completed(3, {1}) == "locked"


def test_status_cleared_if_in_completed() -> None:
    assert progress.status_from_completed(1, {1}) == "cleared"


def test_status_for_delegates_to_status_from_completed() -> None:
    mission_progress = {"completed": [1, 2]}
    assert progress.status_for(3, mission_progress) == "open"
    assert progress.status_for(4, mission_progress) == "locked"
    assert progress.status_for(1, mission_progress) == "cleared"


def test_status_parity_with_previous_logic_all_missions() -> None:
    """全 22 Mission × 代表的な completed 集合で新旧ロジックが一致すること。"""
    representative_sets: list[set[int]] = [
        set(),
        {1},
        {1, 2, 3},
        set(_ALL_IDS),
    ]
    for completed in representative_sets:
        for mission_id in _ALL_IDS:
            assert progress.status_from_completed(
                mission_id, completed
            ) == _reference_status_for(mission_id, completed)


# ---------------------------------------------------------------------------
# compute_active_mission_id
# ---------------------------------------------------------------------------


def test_compute_active_mission_id_empty_is_first_mission() -> None:
    assert progress.compute_active_mission_id({"completed": []}) == _ALL_IDS[0]


def test_compute_active_mission_id_after_two_cleared() -> None:
    assert progress.compute_active_mission_id({"completed": [1, 2]}) == 3


def test_compute_active_mission_id_gap_returns_smallest_missing() -> None:
    assert progress.compute_active_mission_id({"completed": [1, 3]}) == 2


def test_compute_active_mission_id_all_cleared_is_none() -> None:
    assert progress.compute_active_mission_id({"completed": list(_ALL_IDS)}) is None


# ---------------------------------------------------------------------------
# refresh_active_mission_id
# ---------------------------------------------------------------------------


def test_refresh_active_mission_id_overwrites_stale_cache() -> None:
    mission_progress = {"completed": [1, 2], "active_mission_id": 999}
    result = progress.refresh_active_mission_id(mission_progress)
    assert result == 3
    assert mission_progress["active_mission_id"] == 3


def test_refresh_active_mission_id_all_cleared() -> None:
    mission_progress = {"completed": list(_ALL_IDS), "active_mission_id": 1}
    result = progress.refresh_active_mission_id(mission_progress)
    assert result is None
    assert mission_progress["active_mission_id"] is None


# ---------------------------------------------------------------------------
# active_mission_id
# ---------------------------------------------------------------------------


def test_active_mission_id_returns_cached_value_even_if_stale() -> None:
    # あえて実態とズレたキャッシュ値を入れてもそれを返す（読み取りは再計算しない）。
    mission_progress = {"completed": [1, 2, 3], "active_mission_id": 999}
    assert progress.active_mission_id(mission_progress) == 999


def test_active_mission_id_falls_back_when_key_missing() -> None:
    mission_progress = {"completed": [1, 2]}
    assert progress.active_mission_id(mission_progress) == 3
    # 再計算のみでキャッシュへの書き戻しは行わない。
    assert "active_mission_id" not in mission_progress


# ---------------------------------------------------------------------------
# default_world_state() との統合
# ---------------------------------------------------------------------------


def test_default_world_state_mission_progress_initial_values() -> None:
    mission_progress = default_world_state()["mission_progress"]
    assert progress.completed_ids(mission_progress) == set()
    assert progress.status_for(1, mission_progress) == "open"
    assert progress.status_for(2, mission_progress) == "locked"
    assert progress.compute_active_mission_id(mission_progress) == 1
    assert progress.active_mission_id(mission_progress) == 1
