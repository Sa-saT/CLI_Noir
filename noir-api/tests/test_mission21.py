"""Mission21「消えた道具箱」: 汚染された PATH の診断・裏取り・復旧のフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_grep_command_not_found_while_path_poisoned() -> None:
    s = build_initial_state(21)
    out, _ = _run(s, "grep x /root/hint.txt")
    assert out == ["Error: command not found"]


def test_echo_path_reveals_poisoned_value() -> None:
    s = build_initial_state(21)
    out, _ = _run(s, "echo $PATH")
    assert out == ["/tmp/.stolen"]


def test_printenv_path_also_works() -> None:
    s = build_initial_state(21)
    out, _ = _run(s, "printenv PATH")
    assert out == ["/tmp/.stolen"]


def test_absolute_path_bypasses_broken_path() -> None:
    s = build_initial_state(21)
    out, _ = _run(s, "/bin/cat /root/hint.txt")
    assert any("PATH" in ln for ln in out)


def test_which_and_type_work_despite_broken_path() -> None:
    s = build_initial_state(21)
    out, _ = _run(s, "which grep")
    assert out == ["/bin/grep"]
    out2, _ = _run(s, "type grep")
    assert out2 == ["grep is /bin/grep"]


def test_export_restores_path_and_unblocks_tools() -> None:
    s = build_initial_state(21)
    _, s = _run(s, "export PATH=/usr/local/bin:/usr/bin:/bin")
    assert s["env_vars"]["PATH"] == "/usr/local/bin:/usr/bin:/bin"
    out, _ = _run(s, "grep TOOL /root/hint.txt")
    assert out != ["Error: command not found"]


def test_mission21_golden_transcript() -> None:
    s = build_initial_state(21)

    _, s = _run(s, "echo $PATH")
    _, s = _run(s, "/bin/cat /root/hint.txt")
    _, s = _run(s, "which grep")
    _, s = _run(s, "export PATH=/usr/local/bin:/usr/bin:/bin")
    _, s = _run(s, "grep TOOL /root/hint.txt")
    _, s = _run(s, 'echo "/tmp/.stolen" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "toolbox recovered"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission21_fails_without_restoring_path() -> None:
    s = build_initial_state(21)
    _, s = _run(s, "echo $PATH")
    _, s = _run(s, 'echo "/tmp/.stolen" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: command not found"]


def test_mission21_fails_without_reporting_bad_path() -> None:
    s = build_initial_state(21)
    _, s = _run(s, "export PATH=/usr/local/bin:/usr/bin:/bin")
    _, s = _run(s, "grep TOOL /root/hint.txt")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
