"""Mission の「プレイ順序」が id ではなく `_DEFS` の並び順で決まることの検証。

Mission23〜28 を id を採番し直さず `_DEFS` の途中へ挿入できるようにするための
設計（app/content/missions.py 冒頭コメント参照）。ここでは `_DEFS` を一時的に
並べ替え（monkeypatch。テスト終了後は自動で元に戻る）、id の大小に依存する
実装が紛れ込んでいないかを機械的に確認する。
"""

from app.content import missions as missions_content
from app.content.missions import (
    all_missions,
    first_mission_id,
    mission_index,
    next_mission_id,
    previous_mission_id,
)
from app.evaluator import complete, progress
from tests.helpers import state_at_mission


def test_all_missions_returns_defs_order() -> None:
    """`all_missions()` は `_DEFS` の並び順そのものを返す（id でソートし直さない）。"""
    assert all_missions() == list(missions_content._DEFS)


def test_mission_index_matches_defs_position() -> None:
    for i, mission in enumerate(all_missions()):
        assert mission_index(mission.id) == i


def test_previous_mission_id_of_first_mission_is_none() -> None:
    assert previous_mission_id(first_mission_id()) is None


def test_next_mission_id_of_last_mission_is_none() -> None:
    last_id = all_missions()[-1].id
    assert next_mission_id(last_id) is None


def test_next_and_previous_are_inverse_along_play_order() -> None:
    for mission in all_missions():
        nxt = next_mission_id(mission.id)
        if nxt is not None:
            assert previous_mission_id(nxt) == mission.id


def _defs_with_22_moved_before_13(original: list) -> list:
    """22 を 13 の直前へ移した `_DEFS` の複製（他の Mission の並びは変えない）。

    元の並びは id 順（1..22）なので、この並べ替えにより
    「id の大小」と「プレイ順序」が初めて食い違う状態を作れる。
    """
    by_id = {m.id: m for m in original}
    without_22 = [m for m in original if m.id != 22]
    index_13 = next(i for i, m in enumerate(without_22) if m.id == 13)
    without_22.insert(index_13, by_id[22])
    return without_22


def test_order_assumptions_follow_play_order_not_id(monkeypatch) -> None:
    """`_DEFS` を並べ替えても各所が id 演算ではなくプレイ順序に追随すること。

    並べ替え後のプレイ順序: ..., 11, 12, 22, 13, 14, ..., 21（22 だけが 13 の
    直前へ移動。他は元のまま）。
    """
    original = list(missions_content._DEFS)
    reordered = _defs_with_22_moved_before_13(original)
    monkeypatch.setattr(missions_content, "_DEFS", reordered)

    # mission_index / previous_mission_id / next_mission_id が新しい並びに追随する。
    assert missions_content.previous_mission_id(13) == 22
    assert missions_content.next_mission_id(22) == 13
    assert missions_content.previous_mission_id(22) == 12  # 12 の次に 22 が来た
    assert missions_content.next_mission_id(12) == 22

    # status_from_completed: 「直前 Mission」は id-1(=12) ではなく、プレイ順序で
    # 直前の 22 で判定される。
    assert progress.status_from_completed(13, {22}) == "open"
    assert progress.status_from_completed(13, {12}) == "locked"

    # compute_active_mission_id: プレイ順序で最初の未完了 Mission を返す。
    completed_up_to_12 = {m.id for m in reordered[:12]}  # {1, ..., 12}
    assert (
        progress.compute_active_mission_id({"completed": list(completed_up_to_12)})
        == 22
    )
    completed_up_to_22 = completed_up_to_12 | {22}
    assert (
        progress.compute_active_mission_id({"completed": list(completed_up_to_22)})
        == 13
    )

    # mission_commands: active=13 なら、プレイ順序で手前に割り込んだ 22 の
    # extra_commands（md5sum は Mission13 までの本来の並びには出てこない）も
    # 解放済み扱いになる。id 比較（22 > 13 だから除外）のままだと落ちるはず。
    state = {"mission_progress": {"active_mission_id": 13}}
    unlocked = complete.mission_commands(state)
    assert "md5sum" in unlocked

    # state_at_mission: 13 の手前（プレイ順序）に 22 が割り込むので、advance
    # 対象に 22 が含まれ、13 より後ろの Mission（14 など）は含まれない。
    state13 = state_at_mission(13)
    completed13 = set(state13["mission_progress"]["completed"])
    assert completed13 == completed_up_to_12 | {22}
    assert 14 not in completed13
