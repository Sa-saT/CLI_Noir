"""疑似 Git（#11）と Mission 判定 case_file.sh（#12）のテスト。

Mission1 のゴールデントランスクリプト（設計指示書 § 10 の判定フロー）を通す。
"""

import pytest

from app.evaluator import evaluate
from app.models import default_state


@pytest.fixture
def mission1_state() -> dict:
    s = default_state()
    s["mission_id"] = 1
    root_children = s["filesystem"]["root"]["children"]
    root_children["desk"] = {
        "type": "dir",
        "children": {
            "businesscard.txt": {
                "type": "file",
                "content": "NAME: ???",
                "mode": "rw-r--r--",
                "owner": "detective",
                "mtime": "2026-01-01T00:00:00Z",
                "immutable": True,
            }
        },
    }
    root_children["case_file.sh"] = {
        "type": "file",
        "content": "# judge",
        "mode": "rw-r--r--",
        "owner": "detective",
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": True,
    }
    return s


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission1_golden_transcript(mission1_state: dict) -> None:
    s = mission1_state

    _, s = _run(s, "cat /root/desk/businesscard.txt")
    _, s = _run(s, 'echo "NAME: Sam Spade" > /root/desk/businesscard.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    out, s = _run(s, "git status")
    assert out == ["Ready to push"] or out == ["Nothing to commit"]

    _, s = _run(s, "git add .")
    assert s["git_state"]["staged"] == ["."]

    out, s = _run(s, 'git commit -m "solved"')
    assert out == ["[saved #1] solved"]
    assert s["git_state"]["staged"] == []
    assert len(s["git_state"]["commits"]) == 1

    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["git_state"]["pushed"] is True
    assert s["mission_flags"]["completed"] is True


def test_case_file_mismatch_does_not_check(mission1_state: dict) -> None:
    s = mission1_state
    # 名刺を編集せず case_file.sh を実行 → 不一致
    _, s = _run(s, "cat /root/desk/businesscard.txt")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False


def test_commit_requires_staged(mission1_state: dict) -> None:
    out, s = _run(mission1_state, 'git commit -m "x"')
    assert out == ["Error: nothing to commit"]


def test_commit_requires_message(mission1_state: dict) -> None:
    _, s = _run(mission1_state, "git add .")
    out, s = _run(s, "git commit")
    assert out == ["Error: commit message required"]


def test_push_before_commit(mission1_state: dict) -> None:
    out, _ = _run(mission1_state, "git push")
    assert out == ["Error: push not allowed before commit"]


def test_push_without_case_checked(mission1_state: dict) -> None:
    # case_file.sh を通さずに commit → push すると条件未達
    s = mission1_state
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "premature"')
    out, s = _run(s, "git push")
    assert out == ["Error: mission requirements not met"]


def test_git_status_progression(mission1_state: dict) -> None:
    s = mission1_state
    assert _run(s, "git status")[0] == ["Nothing to commit"]
    _, s = _run(s, "git add .")
    assert _run(s, "git status")[0] == ["Changes staged"]
