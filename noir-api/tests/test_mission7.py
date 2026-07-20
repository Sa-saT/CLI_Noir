"""Mission7「機械の胸の内」: 疑似 /proc での裏取り + free/uptime のフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ls_proc_lists_pids_and_static_entries() -> None:
    s = build_initial_state(7)
    out, _ = _run(s, "ls /proc")
    assert set(out) == {"201", "202", "923", "cpuinfo", "meminfo", "uptime"}


def test_cat_proc_status_and_cmdline() -> None:
    s = build_initial_state(7)
    out, _ = _run(s, "cat /proc/923/status")
    assert any("clock" in ln for ln in out)

    out, _ = _run(s, "cat /proc/923/cmdline")
    assert out == ["/tmp/.fake/exfil --send"]


def test_proc_write_attempts_denied() -> None:
    s = build_initial_state(7)
    assert _run(s, "touch /proc/923/status")[0] == ["Permission denied"]
    assert _run(s, "mkdir /proc/new")[0] == ["Permission denied"]
    out, _ = _run(s, 'echo "haha" > /proc/923/cmdline')
    assert out == ["Permission denied"]


def test_free_matches_meminfo() -> None:
    s = build_initial_state(7)
    free_out, _ = _run(s, "free")
    meminfo_out, _ = _run(s, "cat /proc/meminfo")
    total = int(free_out[1].split()[1])
    used = int(free_out[1].split()[2])
    assert f"MemTotal:       {total} kB" in meminfo_out[0]
    assert f"MemUsed:        {used} kB" in meminfo_out[2]


def test_uptime_output() -> None:
    s = build_initial_state(7)
    out, _ = _run(s, "uptime")
    assert out[0].startswith("up ")


def test_mission7_case_file_fails_without_investigation() -> None:
    s = build_initial_state(7)
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: check /proc before you accuse anyone"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission7_case_file_fails_without_report() -> None:
    s = build_initial_state(7)
    _, s = _run(s, "cat /proc/923/cmdline")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: report the impostor's real command"]


def test_mission7_case_file_fails_while_still_running() -> None:
    s = build_initial_state(7)
    _, s = _run(s, "cat /proc/923/cmdline")
    _, s = _run(s, 'echo "/tmp/.fake/exfil --send" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: the impostor is still running"]


def test_mission7_golden_transcript() -> None:
    s = build_initial_state(7)

    _, s = _run(s, "ps aux")
    _, s = _run(s, "cat /proc/923/status")
    _, s = _run(s, "cat /proc/923/cmdline")
    _, s = _run(s, 'echo "/tmp/.fake/exfil --send" > report.txt')
    _, s = _run(s, "kill 923")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "impostor exposed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True
