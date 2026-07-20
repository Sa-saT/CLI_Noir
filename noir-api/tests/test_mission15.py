"""Mission15「情報屋の足取り」: history 演出と journal.log の再現フロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_history_shows_informant_trail() -> None:
    s = build_initial_state(15)
    out, _ = _run(s, "history")
    assert out == [
        "1  tail -n 5 /root/journal.log",
        "2  grep PIER /root/journal.log",
    ]


def test_history_default_is_empty_for_other_missions() -> None:
    s = build_initial_state(1)
    out, _ = _run(s, "history")
    assert out == []


def test_tail_and_grep_reveal_destination() -> None:
    s = build_initial_state(15)
    out, _ = _run(s, "grep PIER /root/journal.log")
    assert out == ["10:45 note left: meet at PIER 13"]


def test_mission15_golden_transcript() -> None:
    s = build_initial_state(15)

    _, s = _run(s, "history")
    _, s = _run(s, "tail -n 5 /root/journal.log")
    _, s = _run(s, "grep PIER /root/journal.log")
    _, s = _run(s, 'echo "PIER 13" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "trail traced"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission15_requires_exact_reproduction() -> None:
    s = build_initial_state(15)
    # tail の行数を変えてしまうと再現とみなされない。
    _, s = _run(s, "tail -n 3 /root/journal.log")
    _, s = _run(s, "grep PIER /root/journal.log")
    _, s = _run(s, 'echo "PIER 13" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: retrace the informant's exact steps"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission15_requires_destination_report() -> None:
    s = build_initial_state(15)
    _, s = _run(s, "tail -n 5 /root/journal.log")
    _, s = _run(s, "grep PIER /root/journal.log")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
