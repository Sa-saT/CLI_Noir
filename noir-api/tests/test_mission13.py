"""Mission13「深夜0時の犯行予告」: crontab -l / date と cron 書式解読のフロー。"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_crontab_l_lists_jobs() -> None:
    s = state_at_mission(13)
    out, _ = _run(s, "crontab -l")
    assert "0 0 * * 5 /tmp/.dark/broadcast.sh" in out
    assert len(out) == 3


def test_crontab_without_l_flag_invalid() -> None:
    s = state_at_mission(13)
    out, _ = _run(s, "crontab")
    assert out == ["Error: invalid input"]


def test_date_output() -> None:
    s = state_at_mission(13)
    out, _ = _run(s, "date")
    assert out == ["Thu Jan  1 00:00:00 UTC 2026"]


def test_mission13_golden_transcript() -> None:
    s = state_at_mission(13)

    _, s = _run(s, "crontab -l")
    _, s = _run(s, "cat /root/crontab_room/hint.txt")
    _, s = _run(s, 'echo "FRIDAY 00:00" > report.txt')

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "bomb defused"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 13 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 14


def test_mission13_wrong_job_blocks_clear() -> None:
    s = state_at_mission(13)
    _, s = _run(s, "crontab -l")
    _, s = _run(s, 'echo "SATURDAY 06:00" > report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False


def test_mission13_requires_crontab_l() -> None:
    s = state_at_mission(13)
    _, s = _run(s, 'echo "FRIDAY 00:00" > report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
