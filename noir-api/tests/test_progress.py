"""`app/evaluator/progress.py` のテスト（Part5 P3-02）。

P3-14 でディレクトリ権限ゲート・ssh到達性ゲート等の進捗連動テストを本ファイルへ追加する。
"""

from app.evaluator import progress
from app.models import default_state


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
