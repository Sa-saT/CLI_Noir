"""Mission7「機械の胸の内」: 疑似 /proc での裏取り + free/uptime のフロー。

Phase F: 統合ワールド state で検証する。統合ワールドでは Mission6 の
プロセス（clock/mailbox/heater/listener_x）が state_at_mission(7) の時点で
既に released 済み（Mission6 クリア扱いだが listener_x を実際に kill する
アクションは再現しないため、状態上は生きたまま残る）で processes に同居する。
そのため /proc・ps の一覧系アサーションは完全一致ではなく部分一致（subset）で
Mission7 固有の PID/静的エントリだけを検証する。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ls_proc_lists_pids_and_static_entries() -> None:
    s = state_at_mission(7)
    out, _ = _run(s, "ls /proc")
    # Mission6 の残存プロセス（advance_mission はクリア済みにするだけで実際に
    # kill はしないため listener_x 等が残る）も同居するため subset で検証する。
    assert {"201", "202", "923", "cpuinfo", "meminfo", "uptime"}.issubset(set(out))


def test_cat_proc_status_and_cmdline() -> None:
    s = state_at_mission(7)
    out, _ = _run(s, "cat /proc/923/status")
    assert any("clock" in ln for ln in out)

    out, _ = _run(s, "cat /proc/923/cmdline")
    assert out == ["/tmp/.fake/exfil --send"]


def test_proc_write_attempts_denied() -> None:
    s = state_at_mission(7)
    assert _run(s, "touch /proc/923/status")[0] == ["Permission denied"]
    assert _run(s, "mkdir /proc/new")[0] == ["Permission denied"]
    out, _ = _run(s, 'echo "haha" > /proc/923/cmdline')
    assert out == ["Permission denied"]


def test_free_matches_meminfo() -> None:
    s = state_at_mission(7)
    free_out, _ = _run(s, "free")
    meminfo_out, _ = _run(s, "cat /proc/meminfo")
    total = int(free_out[1].split()[1])
    used = int(free_out[1].split()[2])
    assert f"MemTotal:       {total} kB" in meminfo_out[0]
    assert f"MemUsed:        {used} kB" in meminfo_out[2]


def test_uptime_output() -> None:
    s = state_at_mission(7)
    out, _ = _run(s, "uptime")
    assert out[0].startswith("up ")


def test_mission7_case_file_fails_without_investigation() -> None:
    s = state_at_mission(7)
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: check /proc before you accuse anyone"]
    assert progress.flags(s)["case_checked"] is False


def test_mission7_case_file_fails_without_report() -> None:
    s = state_at_mission(7)
    _, s = _run(s, "cat /proc/923/cmdline")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: report the impostor's real command"]


def test_mission7_case_file_fails_while_still_running() -> None:
    s = state_at_mission(7)
    _, s = _run(s, "cat /proc/923/cmdline")
    _, s = _run(s, 'echo "/tmp/.fake/exfil --send" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: the impostor is still running"]


def test_mission7_relative_path_passes_case_file() -> None:
    """P3-08c: `cd /proc/923` してから相対パスで `cat status` を読んでも
    resolved_command_log 経由で判定が通ること（実 Linux と同じ意味）。
    """
    s = state_at_mission(7)

    _, s = _run(s, "cd /proc/923")
    _, s = _run(s, "cat status")
    _, s = _run(s, "cd /root")
    _, s = _run(s, 'echo "/tmp/.fake/exfil --send" > report.txt')
    _, s = _run(s, "kill 923")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True


def test_mission7_golden_transcript() -> None:
    s = state_at_mission(7)

    _, s = _run(s, "ps aux")
    _, s = _run(s, "cat /proc/923/status")
    _, s = _run(s, "cat /proc/923/cmdline")
    _, s = _run(s, 'echo "/tmp/.fake/exfil --send" > report.txt')
    _, s = _run(s, "kill 923")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "impostor exposed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 7 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 8
