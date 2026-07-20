"""Mission20「この街の地図」: FHS の4区画（/etc /var/log /tmp /home）を巡るフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ls_root_shows_fhs_top_level() -> None:
    s = build_initial_state(20)
    out, _ = _run(s, "ls /")
    assert set(out) == {"bin", "etc", "home", "root", "tmp", "var"}


def test_cat_etc_hosts() -> None:
    s = build_initial_state(20)
    out, _ = _run(s, "cat /etc/hosts")
    assert any("ghost.example" in ln for ln in out)


def test_tail_entry_log_shows_black_trail() -> None:
    s = build_initial_state(20)
    out, _ = _run(s, "tail -n 2 /var/log/entry.log")
    assert any("mr_black" in ln for ln in out)


def test_mission20_golden_transcript() -> None:
    s = build_initial_state(20)

    _, s = _run(s, "cat /etc/hosts")
    _, s = _run(s, "tail /var/log/entry.log")
    _, s = _run(s, "cat /tmp/.forgotten")
    _, s = _run(s, "ls /home/mr_black")
    _, s = _run(s, 'echo "mr_black" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "black identified"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission20_missing_zone_blocks_clear() -> None:
    s = build_initial_state(20)
    # /tmp を探索していない。
    _, s = _run(s, "cat /etc/hosts")
    _, s = _run(s, "tail /var/log/entry.log")
    _, s = _run(s, "ls /home/mr_black")
    _, s = _run(s, 'echo "mr_black" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: the map is incomplete"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission20_missing_report_blocks_clear() -> None:
    s = build_initial_state(20)
    _, s = _run(s, "cat /etc/hosts")
    _, s = _run(s, "tail /var/log/entry.log")
    _, s = _run(s, "cat /tmp/.forgotten")
    _, s = _run(s, "ls /home/mr_black")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
