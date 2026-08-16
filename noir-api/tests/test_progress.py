"""app/evaluator/progress.py のテスト（P3-02 / P3-05）。

mission_progress ヘルパーの純粋関数群を検証する。DB は使わない。
"""

import copy

from app.content import missions as missions_content
from app.content.missions import all_missions
from app.evaluator import progress
from app.models.tables import default_state, default_world_state

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


def test_default_world_state_mission_progress_has_released_key() -> None:
    assert default_world_state()["mission_progress"]["released"] == []


# ---------------------------------------------------------------------------
# flags（両 state 形状の吸収。P3-05）
# ---------------------------------------------------------------------------


def test_flags_world_state_returns_mission_progress_flags() -> None:
    state = default_world_state()
    result = progress.flags(state)
    assert result is state["mission_progress"]["flags"]
    assert result == {"case_checked": False}


def test_flags_mission_state_returns_mission_flags() -> None:
    state = default_state()
    result = progress.flags(state)
    assert result is state["mission_flags"]


def test_flags_mission_state_creates_mission_flags_if_missing() -> None:
    state: dict = {}
    result = progress.flags(state)
    assert result == {}
    assert state["mission_flags"] is result


def test_flags_is_a_reference_mutation_reflected_in_state() -> None:
    state = default_world_state()
    progress.flags(state)["case_checked"] = True
    assert state["mission_progress"]["flags"]["case_checked"] is True


def test_flags_works_on_arbitrary_snapshot_dict() -> None:
    """git_ops._push が commit の snapshot dict からも読めることを保証する。"""
    world_snapshot = {"mission_progress": {"flags": {"case_checked": True}}}
    assert progress.flags(world_snapshot) == {"case_checked": True}

    mission_snapshot = {"mission_flags": {"case_checked": True}}
    assert progress.flags(mission_snapshot) == {"case_checked": True}


# ---------------------------------------------------------------------------
# release_missions（冪等。統合ワールド state 専用）
# ---------------------------------------------------------------------------


def _dir_gate(state: dict, abs_path: str) -> tuple[str, str]:
    node = progress._node_at(state["filesystem"], abs_path)
    assert node is not None and node["type"] == "dir"
    return node["mode"], node["owner"]


def test_release_missions_noop_for_mission_state() -> None:
    """mission_progress を持たない state（Mission 別 state）には一切触らない。"""
    state = default_state()
    before = copy.deepcopy(state)
    progress.release_missions(state)
    assert state == before


def test_release_missions_opens_mission1_area_on_fresh_world() -> None:
    state = default_world_state()
    progress.release_missions(state)
    mode, owner = _dir_gate(state, "/root/desk")
    assert mode == missions_content.OPEN_DIR_MODE
    assert owner == missions_content.OPEN_DIR_OWNER
    assert state["mission_progress"]["released"] == [1]


def test_release_missions_locked_mission_area_stays_locked() -> None:
    state = default_world_state()
    progress.release_missions(state)
    # Mission2 は Mission1 未クリアの間は locked のまま（released されない）。
    mode, owner = _dir_gate(state, "/root/park")
    assert mode == missions_content.LOCKED_DIR_MODE
    assert owner == missions_content.LOCKED_DIR_OWNER
    assert 2 not in state["mission_progress"]["released"]


def test_release_missions_opens_area_for_open_status_not_only_cleared() -> None:
    """status が cleared でなく open なだけの Mission も解放対象になる。"""
    state = default_world_state()
    state["mission_progress"]["completed"] = [1]
    progress.release_missions(state)
    mode, _owner = _dir_gate(state, "/root/park")  # Mission2 = open
    assert mode == missions_content.OPEN_DIR_MODE
    assert state["mission_progress"]["released"] == [1, 2]


def test_release_missions_adds_owning_mission_id_to_processes_and_cron() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = [1, 2, 3, 4, 5]
    progress.release_missions(state)  # Mission6 まで open/cleared になる

    m6_procs = [p for p in state["processes"] if p.get("owning_mission_id") == 6]
    assert len(m6_procs) == len(missions_content.get_mission(6).initial_processes)
    assert any(p["name"] == "listener_x" for p in m6_procs)


def test_release_missions_mission13_adds_cron_jobs_with_owning_mission_id() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = list(range(1, 13))
    progress.release_missions(state)

    m13_jobs = [j for j in state["cron_jobs"] if j.get("owning_mission_id") == 13]
    assert len(m13_jobs) == len(missions_content.get_mission(13).initial_cron_jobs)


def test_release_missions_mission12_appends_ghost_hosts_line() -> None:
    state = default_world_state()
    hosts_before = progress._node_at(state["filesystem"], missions_content.HOSTS_PATH)
    assert missions_content.GHOST_HOSTS_LINE not in hosts_before["content"]

    state["mission_progress"]["completed"] = list(range(1, 12))  # Mission12 が open になる
    progress.release_missions(state)

    hosts_after = progress._node_at(state["filesystem"], missions_content.HOSTS_PATH)
    assert missions_content.GHOST_HOSTS_LINE in hosts_after["content"].split("\n")


def test_release_missions_is_idempotent_for_hosts_line() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = list(range(1, 12))
    progress.release_missions(state)
    progress.release_missions(state)
    progress.release_missions(state)

    hosts = progress._node_at(state["filesystem"], missions_content.HOSTS_PATH)
    lines = hosts["content"].split("\n")
    assert lines.count(missions_content.GHOST_HOSTS_LINE) == 1


def test_release_missions_does_not_revive_killed_process() -> None:
    """一度 release 済みの Mission に対して kill 済みプロセスが復活しないこと。"""
    state = default_world_state()
    state["mission_progress"]["completed"] = [1, 2, 3, 4, 5]
    progress.release_missions(state)

    # Mission6 の listener_x を kill 済みにする（プレイヤーが討伐済みの状態を模す）。
    state["processes"] = [
        p for p in state["processes"] if p.get("name") != "listener_x"
    ]
    before_count = len(state["processes"])

    # 2回目・3回目の release_missions（例: git push が連打された想定）は
    # 何も追加しない（released 済みのため mission_id=6 の枝を再訪しない）。
    progress.release_missions(state)
    progress.release_missions(state)

    assert len(state["processes"]) == before_count
    assert not any(p.get("name") == "listener_x" for p in state["processes"])


def test_release_missions_raises_if_area_missing_from_world() -> None:
    state = default_world_state()
    # 世界に存在しないパスを Mission1 の区画として差し替え、設計ミス検知を確認する。
    original = missions_content._MISSION_AREAS[1]
    missions_content._MISSION_AREAS[1] = ["/root/does_not_exist"]
    try:
        try:
            progress.release_missions(state)
            raised = False
        except ValueError:
            raised = True
        assert raised
    finally:
        missions_content._MISSION_AREAS[1] = original


# ---------------------------------------------------------------------------
# advance_mission
# ---------------------------------------------------------------------------


def test_advance_mission_records_completed_without_duplicates() -> None:
    state = default_world_state()
    progress.advance_mission(state, 1)
    progress.advance_mission(state, 1)  # 二重に呼ばれても重複しない
    assert state["mission_progress"]["completed"] == [1]


def test_advance_mission_keeps_completed_sorted() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = [2]
    progress.advance_mission(state, 1)
    assert state["mission_progress"]["completed"] == [1, 2]


def test_advance_mission_updates_active_mission_id() -> None:
    state = default_world_state()
    progress.advance_mission(state, 1)
    assert state["mission_progress"]["active_mission_id"] == 2


def test_advance_mission_resets_flags() -> None:
    state = default_world_state()
    state["mission_progress"]["flags"] = {"case_checked": True, "bug_removed": True}
    progress.advance_mission(state, 1)
    assert state["mission_progress"]["flags"] == {"case_checked": False}


def test_advance_mission_releases_next_area() -> None:
    state = default_world_state()
    progress.advance_mission(state, 1)
    mode, _owner = _dir_gate(state, "/root/park")
    assert mode == missions_content.OPEN_DIR_MODE
    assert state["mission_progress"]["released"] == [1, 2]
