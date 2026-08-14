"""`app/evaluator/progress.py` のテスト（Part5 P3-02/P3-05）。

P3-14 でssh到達性ゲート等の進捗連動テストを本ファイルへ追加する。
"""

from app.content.missions import GHOST_HOSTS_LINE, _build_world_fs
from app.evaluator import fs, progress
from app.models import default_state


def _world_state() -> dict:
    s = default_state()
    s["filesystem"] = _build_world_fs()
    return s


def test_default_mission_progress_shape() -> None:
    state = default_state()
    mp = state["mission_progress"]
    assert mp["completed"] == []
    assert mp["active_mission_id"] == 1
    assert mp["case_checked"] is False


def test_completed_ids_returns_set() -> None:
    assert progress.completed_ids({"completed": [1, 2, 3]}) == {1, 2, 3}
    assert progress.completed_ids({}) == set()


def test_status_for_mission1_always_open() -> None:
    assert progress.status_for(1, {"completed": []}) == "open"


def test_status_for_sequential_unlock() -> None:
    mp = {"completed": [1]}
    assert progress.status_for(1, mp) == "cleared"
    assert progress.status_for(2, mp) == "open"
    assert progress.status_for(3, mp) == "locked"


def test_status_for_locked_when_far_ahead() -> None:
    mp = {"completed": [1, 2]}
    assert progress.status_for(4, mp) == "locked"


def test_active_mission_id_is_smallest_uncompleted() -> None:
    assert progress.active_mission_id({"completed": []}) == 1
    assert progress.active_mission_id({"completed": [1, 2, 3]}) == 4
    assert progress.active_mission_id({"completed": [1, 3]}) == 2


def test_active_mission_id_none_when_all_cleared() -> None:
    all_ids = list(range(1, 23))
    assert progress.active_mission_id({"completed": all_ids}) is None


# --- advance_mission（Part5 P3-05） ---
def test_advance_mission_records_completion_and_recomputes_active() -> None:
    s = _world_state()
    progress.advance_mission(s, 1)
    mp = s["mission_progress"]
    assert mp["completed"] == [1]
    assert mp["active_mission_id"] == 2
    assert mp["case_checked"] is False


def test_advance_mission_unlocks_only_the_newly_active_missions_directory() -> None:
    s = _world_state()
    root = s["filesystem"]["root"]["children"]
    assert root["park"]["mode"] == "---------"
    assert root["wiretap_room"]["mode"] == "---------"

    progress.advance_mission(s, 1)
    assert root["park"]["mode"] == "rwxr-xr-x"
    assert root["park"]["owner"] == "detective"
    # まだ Mission4 は解放されない（Mission2/3 が未クリア）。
    assert root["wiretap_room"]["mode"] == "---------"


def test_advance_mission_to_mission12_appends_ghost_hosts_line() -> None:
    s = _world_state()
    for m in range(1, 11):
        progress.advance_mission(s, m)
    hosts_before = fs.get_node(s, "/etc/hosts")["content"]
    assert GHOST_HOSTS_LINE not in hosts_before

    progress.advance_mission(s, 11)
    hosts_after = fs.get_node(s, "/etc/hosts")["content"]
    assert GHOST_HOSTS_LINE in hosts_after
    assert s["mission_progress"]["active_mission_id"] == 12


def test_advance_mission_releases_processes_and_cron_with_owning_tag() -> None:
    s = _world_state()
    assert s["processes"] == []
    for m in range(1, 6):
        progress.advance_mission(s, m)
    # Mission6 が新たにアクティブになった時点で Mission6 の processes が解放される。
    assert len(s["processes"]) == 4
    assert all(p["owning_mission_id"] == 6 for p in s["processes"])
    assert any(p["name"] == "listener_x" for p in s["processes"])

    for m in range(6, 13):
        progress.advance_mission(s, m)
    # Mission13 解放時に cron_jobs が追加される。
    assert len(s["cron_jobs"]) == 3
    assert all(c["owning_mission_id"] == 13 for c in s["cron_jobs"])


def test_advance_mission_no_op_past_final_mission() -> None:
    s = _world_state()
    for m in range(1, 23):
        progress.advance_mission(s, m)
    assert s["mission_progress"]["active_mission_id"] is None
    # 22 個全て解放済みでも例外を投げない（advance_mission は new_active が
    # None の場合はディレクトリ解放等をスキップする）。
    result = progress.advance_mission(s, 22)
    assert result["mission_progress"]["active_mission_id"] is None
