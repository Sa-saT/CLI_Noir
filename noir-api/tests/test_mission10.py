"""Mission10「改ざんされた遺言状」: diff で改ざん行を見つけ sed で復元するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_diff_shows_classic_format_for_tampered_line() -> None:
    s = build_initial_state(10)
    out, _ = _run(s, "diff /root/original.txt /root/submitted.txt")
    assert out == [
        "2c2",
        "< AMOUNT: $50000",
        "---",
        "> AMOUNT: $5O000",
    ]


def test_diff_identical_files_has_no_output() -> None:
    s = build_initial_state(10)
    out, _ = _run(s, "diff /root/original.txt /root/original.txt")
    assert out == []


def test_sed_replaces_first_occurrence() -> None:
    s = build_initial_state(10)
    out, _ = _run(s, "echo 5O000 5O000 | sed 's/5O000/50000/'")
    assert out == ["50000 5O000"]


def test_sed_global_flag_replaces_all() -> None:
    s = build_initial_state(10)
    out, _ = _run(s, "echo 5O000 5O000 | sed 's/5O000/50000/g'")
    assert out == ["50000 50000"]


def test_sed_invalid_expression() -> None:
    s = build_initial_state(10)
    out, _ = _run(s, "echo x | sed 'not-an-expr'")
    assert out == ["Error: invalid input"]


def test_sed_with_redirect_restores_submitted() -> None:
    s = build_initial_state(10)
    _, s = _run(s, "sed 's/5O000/50000/' /root/submitted.txt > /root/submitted.txt")
    node = s["filesystem"]["root"]["children"]["submitted.txt"]
    original = s["filesystem"]["root"]["children"]["original.txt"]
    assert node["content"] == original["content"]


def test_mission10_golden_transcript() -> None:
    s = build_initial_state(10)

    _, s = _run(s, "diff /root/original.txt /root/submitted.txt")
    _, s = _run(s, "sed 's/5O000/50000/' /root/submitted.txt > /root/submitted.txt")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "will restored"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission10_fails_without_diff() -> None:
    s = build_initial_state(10)
    _, s = _run(s, "sed 's/5O000/50000/' /root/submitted.txt > /root/submitted.txt")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: run diff before you restore the will"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission10_fails_if_not_restored() -> None:
    s = build_initial_state(10)
    _, s = _run(s, "diff /root/original.txt /root/submitted.txt")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: submitted.txt still does not match the original"]
    assert s["mission_flags"]["case_checked"] is False
