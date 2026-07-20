"""Mission13「深夜0時の犯行予告」: crontab -l / date と cron 書式解読のフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_crontab_l_lists_jobs() -> None:
    s = build_initial_state(13)
    out, _ = _run(s, "crontab -l")
    assert "0 0 * * 5 /tmp/.dark/broadcast.sh" in out
    assert len(out) == 3


def test_crontab_without_l_flag_invalid() -> None:
    s = build_initial_state(13)
    out, _ = _run(s, "crontab")
    assert out == ["Error: invalid input"]


def test_date_output() -> None:
    s = build_initial_state(13)
    out, _ = _run(s, "date")
    assert out == ["Thu Jan  1 00:00:00 UTC 2026"]


def test_mission13_golden_transcript() -> None:
    s = build_initial_state(13)

    _, s = _run(s, "crontab -l")
    _, s = _run(s, "cat hint.txt")
    _, s = _run(s, 'echo "FRIDAY 00:00" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "bomb defused"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission13_wrong_job_blocks_clear() -> None:
    s = build_initial_state(13)
    _, s = _run(s, "crontab -l")
    _, s = _run(s, 'echo "SATURDAY 06:00" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission13_requires_crontab_l() -> None:
    s = build_initial_state(13)
    _, s = _run(s, 'echo "FRIDAY 00:00" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
