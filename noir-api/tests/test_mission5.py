"""Mission5「開かずの資料室」: chmod でヒントと case_file.sh を解錠するフロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission5_initial_ls_shows_locked_permissions() -> None:
    s = build_initial_state(5)
    out, _ = _run(s, "ls -l /root/vault")
    locked = [ln for ln in out if ln.endswith("locked_evidence.txt")][0]
    assert locked.startswith("----------")


def test_mission5_cat_blocked_before_chmod() -> None:
    s = build_initial_state(5)
    out, _ = _run(s, "cat /root/vault/locked_evidence.txt")
    assert out == ["Error: permission denied"]


def test_mission5_sh_blocked_before_chmod_x() -> None:
    s = build_initial_state(5)
    out, _ = _run(s, "sh /root/vault/inner/case_file.sh")
    assert out == ["Error: permission denied"]


def test_mission5_golden_transcript() -> None:
    s = build_initial_state(5)

    _, s = _run(s, "ls -l /root/vault")
    _, s = _run(s, "chmod +r /root/vault/locked_evidence.txt")
    out, s = _run(s, "cat /root/vault/locked_evidence.txt")
    assert "SEALED EVIDENCE ROOM" in out[0]

    _, s = _run(s, "chmod +x /root/vault/inner/case_file.sh")
    out, s = _run(s, "sh /root/vault/inner/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "vault cracked"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission5_missing_chmod_x_blocks_clear() -> None:
    # chmod +r のみ行い、+x を行わずに sh を試みると permission denied のまま。
    s = build_initial_state(5)
    _, s = _run(s, "chmod +r /root/vault/locked_evidence.txt")
    out, s = _run(s, "sh /root/vault/inner/case_file.sh")
    assert out == ["Error: permission denied"]
    assert s["mission_flags"]["case_checked"] is False
