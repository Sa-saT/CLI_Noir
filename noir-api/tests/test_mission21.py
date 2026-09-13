"""Mission21「消えた道具箱」: 汚染された PATH の診断・裏取り・復旧のフロー。

Phase F: 統合ワールド state で検証する（hint.txt は /root/toolbox_room に移設済み）。
PATH 汚染は Mission21 解放時に `progress.release_missions` が探偵自身の env バケットへ
書き込む（2026-09-13 確定。「事務所に戻ると道具が使えない」異常事態で開幕）。
`state_at_mission(21)` はその解放を本物の advance_mission で通るので、ここでは
汚染を手で仕込まない。
"""

from app.evaluator import evaluate, progress
from app.evaluator.env import env_for
from tests.helpers import state_at_mission

_HINT_PATH = "/root/toolbox_room/hint.txt"
_BAD_PATH = "/tmp/.stolen"
_GOOD_PATH = "/usr/local/bin:/usr/bin:/bin"


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def _mission21_state() -> dict:
    """Mission21 開始時点の state（解放時の汚染で detective の PATH は既に壊れている）。"""
    s = state_at_mission(21)
    assert env_for(s)["PATH"] == _BAD_PATH
    return s


def test_grep_command_not_found_while_path_poisoned() -> None:
    s = _mission21_state()
    out, _ = _run(s, f"grep x {_HINT_PATH}")
    assert out == ["Error: command not found"]


def test_echo_path_reveals_poisoned_value() -> None:
    s = _mission21_state()
    out, _ = _run(s, "echo $PATH")
    assert out == [_BAD_PATH]


def test_printenv_path_also_works() -> None:
    s = _mission21_state()
    out, _ = _run(s, "printenv PATH")
    assert out == [_BAD_PATH]


def test_absolute_path_bypasses_broken_path() -> None:
    s = _mission21_state()
    out, _ = _run(s, f"/bin/cat {_HINT_PATH}")
    assert any("PATH" in ln for ln in out)


def test_which_and_type_work_despite_broken_path() -> None:
    s = _mission21_state()
    out, _ = _run(s, "which grep")
    assert out == ["/bin/grep"]
    out2, _ = _run(s, "type grep")
    assert out2 == ["grep is /bin/grep"]


def test_export_restores_path_and_unblocks_tools() -> None:
    s = _mission21_state()
    _, s = _run(s, f"export PATH={_GOOD_PATH}")
    assert env_for(s)["PATH"] == _GOOD_PATH
    out, _ = _run(s, f"grep TOOL {_HINT_PATH}")
    assert out != ["Error: command not found"]


def test_mission21_golden_transcript() -> None:
    s = _mission21_state()

    _, s = _run(s, "echo $PATH")
    _, s = _run(s, f"/bin/cat {_HINT_PATH}")
    _, s = _run(s, "which grep")
    _, s = _run(s, f"export PATH={_GOOD_PATH}")
    _, s = _run(s, f"grep TOOL {_HINT_PATH}")
    _, s = _run(s, f'echo "{_BAD_PATH}" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "toolbox recovered"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 21 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 26  # 次はサーバー編（プレイ順序）


def test_mission21_fails_without_restoring_path() -> None:
    s = _mission21_state()
    _, s = _run(s, "echo $PATH")
    _, s = _run(s, f'echo "{_BAD_PATH}" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: command not found"]


def test_mission21_fails_without_reporting_bad_path() -> None:
    s = _mission21_state()
    _, s = _run(s, f"export PATH={_GOOD_PATH}")
    _, s = _run(s, f"grep TOOL {_HINT_PATH}")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
