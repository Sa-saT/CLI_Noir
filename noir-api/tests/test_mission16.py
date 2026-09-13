"""Mission16「一斉捜索令状」: glob と引用符で対象を絞り込むフロー。

Phase F: 統合ワールド state で検証する（Mission16 の区画は /root/warehouse。
統合ワールドでは cwd が /root から始まるため、各テストの先頭で
`cd /root/warehouse` してから旧テストの相対パス操作を再現する）。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def _mission16_state() -> dict:
    s = state_at_mission(16)
    _, s = _run(s, "cd /root/warehouse")
    return s


def test_star_glob_lists_too_many() -> None:
    s = _mission16_state()
    out, _ = _run(s, "ls case_*")
    # case_1..case_42.txt (42) + case_file.sh は /root 直下（動的合成）にあり
    # warehouse には無いため、ここでは 42 件になる。
    assert len(out) == 42


def test_digit_glob_narrows_to_nine() -> None:
    s = _mission16_state()
    out, _ = _run(s, "ls case_[0-9].txt")
    assert out == [f"case_{i}.txt" for i in range(1, 10)]


def test_unquoted_secret_file_fails() -> None:
    s = _mission16_state()
    out, _ = _run(s, "cat top secret.txt")
    assert out == ["Error: file not found"]


def test_quoted_secret_file_succeeds() -> None:
    s = _mission16_state()
    out, _ = _run(s, 'cat "top secret.txt"')
    assert out == ["CODE: 4821-VESPER"]


def test_mission16_golden_transcript() -> None:
    s = _mission16_state()

    _, s = _run(s, "ls case_*")
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'cat "top secret.txt"')
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "warrant executed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 16 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 17


def test_mission16_requires_glob() -> None:
    s = _mission16_state()
    _, s = _run(s, 'cat "top secret.txt"')
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: narrow the search with a glob pattern"]
    assert progress.flags(s)["case_checked"] is False


def test_mission16_requires_quoted_read() -> None:
    s = _mission16_state()
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'echo "CODE: 4821-VESPER" > report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: the warrant does not cover an unopened file"]
    assert progress.flags(s)["case_checked"] is False


def test_mission16_requires_code_report() -> None:
    s = _mission16_state()
    _, s = _run(s, "ls case_[0-9].txt")
    _, s = _run(s, 'cat "top secret.txt"')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
