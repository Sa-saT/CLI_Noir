"""Mission15「情報屋の足取り」: history 演出と journal.log の再現フロー。"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_history_shows_informant_trail() -> None:
    s = state_at_mission(15)
    out, _ = _run(s, "history")
    assert out == [
        "1  tail -n 5 /root/informant_trail/journal.log",
        "2  grep PIER /root/informant_trail/journal.log",
    ]


def test_history_default_is_empty_for_other_missions() -> None:
    s = state_at_mission(1)
    out, _ = _run(s, "history")
    assert out == []


def test_tail_and_grep_reveal_destination() -> None:
    s = state_at_mission(15)
    out, _ = _run(s, "grep PIER /root/informant_trail/journal.log")
    assert out == ["10:45 note left: meet at PIER 13"]


def test_mission15_golden_transcript() -> None:
    s = state_at_mission(15)

    _, s = _run(s, "history")
    _, s = _run(s, "tail -n 5 /root/informant_trail/journal.log")
    _, s = _run(s, "grep PIER /root/informant_trail/journal.log")
    _, s = _run(s, 'echo "PIER 13" > report.txt')

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "trail traced"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 15 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 16


def test_mission15_requires_exact_reproduction() -> None:
    s = state_at_mission(15)
    # tail の行数を変えてしまうと再現とみなされない。
    _, s = _run(s, "tail -n 3 /root/informant_trail/journal.log")
    _, s = _run(s, "grep PIER /root/informant_trail/journal.log")
    _, s = _run(s, 'echo "PIER 13" > report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: retrace the informant's exact steps"]
    assert progress.flags(s)["case_checked"] is False


def test_mission15_requires_destination_report() -> None:
    s = state_at_mission(15)
    _, s = _run(s, "tail -n 5 /root/informant_trail/journal.log")
    _, s = _run(s, "grep PIER /root/informant_trail/journal.log")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
