"""Mission18「雑音の中の声」: 2>/dev/null と $? のフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_grep_r_without_redirect_shows_noise() -> None:
    s = build_initial_state(18)
    out, _ = _run(s, 'grep -r "witness" /root/archive')
    joined = "\n".join(out)
    assert "witness report" in joined
    assert "permission denied" in joined


def test_grep_r_with_dev_null_hides_noise() -> None:
    s = build_initial_state(18)
    out, _ = _run(s, 'grep -r "witness" /root/archive 2>/dev/null')
    joined = "\n".join(out)
    assert "witness report" in joined
    assert "permission denied" not in joined


def test_stderr_redirect_with_space_also_works() -> None:
    s = build_initial_state(18)
    out, _ = _run(s, 'grep -r "witness" /root/archive 2> /dev/null')
    assert "permission denied" not in "\n".join(out)


def test_stderr_redirect_to_file() -> None:
    s = build_initial_state(18)
    _, s = _run(s, 'grep -r "witness" /root/archive 2> /root/errors.txt')
    node = s["filesystem"]["root"]["children"]["errors.txt"]
    assert "permission denied" in node["content"]


def test_echo_dollar_question_after_success() -> None:
    s = build_initial_state(18)
    _, s = _run(s, "cat /root/archive/witness_note.txt")
    out, _ = _run(s, "echo $?")
    assert out == ["0"]


def test_echo_dollar_question_after_failure() -> None:
    s = build_initial_state(18)
    _, s = _run(s, "cat /root/archive/nope.txt")
    out, _ = _run(s, "echo $?")
    assert out == ["1"]


def test_mission18_golden_transcript() -> None:
    s = build_initial_state(18)

    _, s = _run(s, 'grep -r "witness" /root/archive 2>/dev/null')
    _, s = _run(s, "echo $?")
    _, s = _run(s, 'echo "PLATE: NX-4471" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "witness heard"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission18_requires_dev_null() -> None:
    s = build_initial_state(18)
    _, s = _run(s, 'grep -r "witness" /root/archive')
    _, s = _run(s, 'echo "PLATE: NX-4471" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
