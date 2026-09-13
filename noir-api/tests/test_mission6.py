"""Mission6「盗聴器を止めろ」: ps/kill でプロセステーブルを操作するフロー。

Phase F: 統合ワールド state で検証する。Mission6 はローカル FS 区画を持たず、
initial_processes は Mission6 解放時（advance_mission(state, 5) 内の
release_missions）にプロセステーブルへ積まれる。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission6_ps_lists_all_processes() -> None:
    s = state_at_mission(6)
    out, _ = _run(s, "ps aux")
    joined = "\n".join(out)
    assert "clockd" in joined
    assert "listener_x" in joined
    assert "666" in joined


def _without_exit_status(env_vars: dict) -> dict:
    """統合ワールドの env_vars（ユーザー別 dict）から "?" (直近の終了ステータス)
    を取り除く。kill 失敗時に "?" だけが書き換わることを無視して state 全体の
    不変を確認するため（旧 Mission 別 state のフラットな env_vars と違い、
    "?" は env_vars[current_user] の下にネストされている）。
    """
    return {
        user: {k: v for k, v in vars_.items() if k != "?"}
        for user, vars_ in env_vars.items()
    }


def test_mission6_kill_no_such_process() -> None:
    s = state_at_mission(6)
    out, new = _run(s, "kill 9999")
    assert out == ["Error: no such process"]
    new_env = _without_exit_status(new["env_vars"])
    old_env = _without_exit_status(s["env_vars"])
    assert {**new, "env_vars": new_env} == {**s, "env_vars": old_env}


def test_mission6_kill_protected_warns_and_rolls_back() -> None:
    s = state_at_mission(6)
    out, s2 = _run(s, "kill 100")  # clock is protected
    assert out == ["Warning: you stopped a legitimate process"]
    # 巻き戻し: clock はプロセステーブルに残っている。
    names = [p["name"] for p in s2["processes"]]
    assert "clock" in names


def test_mission6_kill_bug_removes_process() -> None:
    s = state_at_mission(6)
    out, s2 = _run(s, "kill 666")
    assert out == ["[666] terminated"]
    names = [p["name"] for p in s2["processes"]]
    assert "listener_x" not in names


def test_mission6_case_file_fails_while_bug_running() -> None:
    s = state_at_mission(6)
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the bug is still running"]
    assert progress.flags(s)["case_checked"] is False


def test_mission6_golden_transcript() -> None:
    s = state_at_mission(6)

    _, s = _run(s, "ps aux")
    _, s = _run(s, "kill 666")

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True
    assert progress.flags(s)["bug_removed"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "bug removed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 6 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 7
