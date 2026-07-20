"""Mission6「盗聴器を止めろ」: ps/kill でプロセステーブルを操作するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission6_ps_lists_all_processes() -> None:
    s = build_initial_state(6)
    out, _ = _run(s, "ps aux")
    joined = "\n".join(out)
    assert "clockd" in joined
    assert "listener_x" in joined
    assert "666" in joined


def test_mission6_kill_no_such_process() -> None:
    s = build_initial_state(6)
    out, new = _run(s, "kill 9999")
    assert out == ["Error: no such process"]
    assert new == s


def test_mission6_kill_protected_warns_and_rolls_back() -> None:
    s = build_initial_state(6)
    out, s2 = _run(s, "kill 100")  # clock is protected
    assert out == ["Warning: you stopped a legitimate process"]
    # 巻き戻し: clock はプロセステーブルに残っている。
    names = [p["name"] for p in s2["processes"]]
    assert "clock" in names


def test_mission6_kill_bug_removes_process() -> None:
    s = build_initial_state(6)
    out, s2 = _run(s, "kill 666")
    assert out == ["[666] terminated"]
    names = [p["name"] for p in s2["processes"]]
    assert "listener_x" not in names


def test_mission6_case_file_fails_while_bug_running() -> None:
    s = build_initial_state(6)
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: the bug is still running"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission6_golden_transcript() -> None:
    s = build_initial_state(6)

    _, s = _run(s, "ps aux")
    _, s = _run(s, "kill 666")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True
    assert s["mission_flags"]["bug_removed"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "bug removed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True
