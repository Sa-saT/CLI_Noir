"""Mission10「改ざんされた遺言状」: diff で改ざん行を見つけ sed で復元するフロー。

Phase F: 統合ワールド state で検証する（original.txt / submitted.txt は
/root/will_office に移設済み）。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_diff_shows_classic_format_for_tampered_line() -> None:
    s = state_at_mission(10)
    out, _ = _run(s, "diff /root/will_office/original.txt /root/will_office/submitted.txt")
    assert out == [
        "2c2",
        "< AMOUNT: $50000",
        "---",
        "> AMOUNT: $5O000",
    ]


def test_diff_identical_files_has_no_output() -> None:
    s = state_at_mission(10)
    out, _ = _run(s, "diff /root/will_office/original.txt /root/will_office/original.txt")
    assert out == []


def test_sed_replaces_first_occurrence() -> None:
    s = state_at_mission(10)
    out, _ = _run(s, "echo 5O000 5O000 | sed 's/5O000/50000/'")
    assert out == ["50000 5O000"]


def test_sed_global_flag_replaces_all() -> None:
    s = state_at_mission(10)
    out, _ = _run(s, "echo 5O000 5O000 | sed 's/5O000/50000/g'")
    assert out == ["50000 50000"]


def test_sed_invalid_expression() -> None:
    s = state_at_mission(10)
    out, _ = _run(s, "echo x | sed 'not-an-expr'")
    assert out == ["Error: invalid input"]


def test_sed_with_redirect_restores_submitted() -> None:
    s = state_at_mission(10)
    _, s = _run(
        s,
        "sed 's/5O000/50000/' /root/will_office/submitted.txt > /root/will_office/submitted.txt",
    )
    will_office = s["filesystem"]["root"]["children"]["will_office"]["children"]
    node = will_office["submitted.txt"]
    original = will_office["original.txt"]
    assert node["content"] == original["content"]


def test_mission10_golden_transcript() -> None:
    s = state_at_mission(10)

    _, s = _run(s, "diff /root/will_office/original.txt /root/will_office/submitted.txt")
    _, s = _run(
        s,
        "sed 's/5O000/50000/' /root/will_office/submitted.txt > /root/will_office/submitted.txt",
    )

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "will restored"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 10 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 11


def test_mission10_fails_without_diff() -> None:
    s = state_at_mission(10)
    _, s = _run(
        s,
        "sed 's/5O000/50000/' /root/will_office/submitted.txt > /root/will_office/submitted.txt",
    )
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: run diff before you restore the will"]
    assert progress.flags(s)["case_checked"] is False


def test_mission10_fails_if_not_restored() -> None:
    s = state_at_mission(10)
    _, s = _run(s, "diff /root/will_office/original.txt /root/will_office/submitted.txt")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: submitted.txt still does not match the original"]
    assert progress.flags(s)["case_checked"] is False
