"""Mission16「一斉捜索令状」: glob と引用符で対象を絞り込むフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_star_glob_lists_too_many() -> None:
    s = build_initial_state(16)
    out, _ = _run(s, "ls case_*")
    # case_1..case_42.txt (42) + case_file.sh も "case_*" にマッチする (43件)。
    assert len(out) == 43


def test_digit_glob_narrows_to_nine() -> None:
    s = build_initial_state(16)
    out, _ = _run(s, "ls case_[0-9].txt")
    assert out == [f"case_{i}.txt" for i in range(1, 10)]


def test_unquoted_secret_file_fails() -> None:
    s = build_initial_state(16)
    out, _ = _run(s, "cat top secret.txt")
    assert out == ["Error: file not found"]


def test_quoted_secret_file_succeeds() -> None:
    s = build_initial_state(16)
    out, _ = _run(s, 'cat "top secret.txt"')
    assert out == ["CODE: 4821-VESPER"]


def test_mission16_golden_transcript() -> None:
    s = build_initial_state(16)

    _, s = _run(s, "ls case_*")
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'cat "top secret.txt"')
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "warrant executed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission16_requires_glob() -> None:
    s = build_initial_state(16)
    _, s = _run(s, 'cat "top secret.txt"')
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: narrow the search with a glob pattern"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission16_requires_quoted_read() -> None:
    s = build_initial_state(16)
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: the warrant does not cover an unopened file"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission16_requires_code_report() -> None:
    s = build_initial_state(16)
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'cat "top secret.txt"')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
