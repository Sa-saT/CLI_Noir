"""統合ワールド state の Mission 解放遷移（P3-05）の通しテスト。

`engine.evaluate()` を使った実際のコマンド列でプレイし、Mission1 クリア後に
Mission2 の区画が開くこと・二重 push で穴が塞がっていること等を検証する。
purely evaluator 層のみを対象にし、DB・API/WS 層は一切使わない。
"""

from app.content.missions import get_mission
from app.evaluator import engine
from app.models.tables import default_state, default_world_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return engine.evaluate(line, state)


def _clear_mission1(state: dict) -> dict:
    """Mission1（名刺編集）を実際にクリアし push まで完了させる。"""
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, 'echo "NAME: Sam Spade" > /root/desk/businesscard.txt')
    _, state = _run(state, "cat /root/desk/businesscard.txt")
    _, state = _run(state, "cd /root")
    out, state = _run(state, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    _, state = _run(state, "git add .")
    _, state = _run(state, 'git commit -m "solved"')
    out, state = _run(state, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    return state


def test_mission1_area_locked_before_push() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, 'echo "NAME: Sam Spade" > /root/desk/businesscard.txt')
    _, state = _run(state, "cd /root")
    out, _ = _run(state, "cd park")
    assert out == ["Error: directory not found"]


def test_mission1_clear_unlocks_mission2_area() -> None:
    state = default_world_state()
    state = _clear_mission1(state)

    out, state = _run(state, "cd park")
    assert out == []
    assert state["current_path"] == "/root/park"


def test_mission1_clear_advances_active_mission_and_case_file_content() -> None:
    state = default_world_state()
    state = _clear_mission1(state)

    assert state["mission_progress"]["active_mission_id"] == 2

    out, _ = _run(state, "cat /root/case_file.sh")
    text = "\n".join(out)
    assert get_mission(2).title_ja in text
    assert get_mission(1).title_ja not in text


def test_double_push_after_mission1_does_not_clear_mission2() -> None:
    """穴塞ぎ（P3-05）: Git 履歴が1本のため、直近 commit の mission_id が
    現在の active_mission_id と一致しない push は拒否されなければならない。
    """
    state = default_world_state()
    state = _clear_mission1(state)

    out, state = _run(state, "git push")
    assert out == ["Error: mission requirements not met"]
    # Mission2 は勝手にクリアされていないこと。
    assert state["mission_progress"]["completed"] == [1]
    assert state["mission_progress"]["active_mission_id"] == 2


def test_case_checked_flag_resets_on_mission_transition() -> None:
    state = default_world_state()
    state = _clear_mission1(state)
    # push 成功後は次 Mission 用にリセットされている（前 Mission の合格を持ち越さない）。
    assert state["mission_progress"]["flags"] == {"case_checked": False}


def test_case_file_pattern_mismatch_for_mission2_after_transition() -> None:
    state = default_world_state()
    state = _clear_mission1(state)
    _, state = _run(state, "cd park")
    out, state = _run(state, "sh /root/case_file.sh")
    # Mission2 は独自 judge（_judge_mission2）を使うため、まだ何もしていない
    # 状態では find 未使用として警告になる（Mission1 の合格を引き継いでいない証明）。
    assert out == ["Warning: use find to locate clues"]
    assert state["mission_progress"]["flags"]["case_checked"] is False


# --- P3-06: SSH 到達性ゲート -------------------------------------------------


def test_ssh_to_locked_mission_host_reports_host_not_found() -> None:
    """Mission3 未解放（Mission2 未クリア）の統合ワールドでは amusement_park の
    存在自体を隠す（未登録ホストと同じ Host not found）。
    """
    state = default_world_state()
    state["mission_progress"]["completed"] = [1]

    out, _ = _run(state, "ssh amusement_park")
    assert out == ["Host not found"]


def test_ssh_to_open_mission_host_connects() -> None:
    """Mission2 クリア済み（Mission3 open）の統合ワールドでは通常どおり接続できる。"""
    state = default_world_state()
    state["mission_progress"]["completed"] = [1, 2]

    out, state = _run(state, "ssh amusement_park")
    assert out == ["Connected to amusement_park"]
    assert state["current_path"] == "/gate"
    assert state["remote_mode"] is True


def test_ssh_to_locked_mission12_host_and_ip_alias_both_hidden() -> None:
    """Mission12 未解放の統合ワールドでは ghost.example / 10.66.6.6 のどちらも
    Host not found になる（IP エイリアスも同じ dict を共有するため自動的に追従）。
    """
    state = default_world_state()

    out, _ = _run(state, "ssh ghost.example")
    assert out == ["Host not found"]

    state2 = default_world_state()
    out2, _ = _run(state2, "ssh 10.66.6.6")
    assert out2 == ["Host not found"]


def test_ssh_gate_does_not_apply_to_mission_scoped_state() -> None:
    """Mission 別 state（mission_progress を持たない）では従来どおりゲートしない
    （現行 API/WS がまだこの形状を使うため回帰防止）。
    """
    state = default_state()

    out, state = _run(state, "ssh amusement_park")
    assert out == ["Connected to amusement_park"]
    assert state["remote_mode"] is True
