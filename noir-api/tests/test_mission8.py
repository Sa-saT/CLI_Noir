"""Mission8「変装潜入」: su/whoami/id によるユーザー切替と owner ベース権限。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ledger_denied_before_su() -> None:
    s = build_initial_state(8)
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out == ["Error: permission denied"]


def test_whoami_default_is_detective() -> None:
    s = build_initial_state(8)
    assert _run(s, "whoami")[0] == ["detective"]


def test_su_changes_current_user_and_id() -> None:
    s = build_initial_state(8)
    _, s = _run(s, "su barman")
    assert s["current_user"] == "barman"
    assert _run(s, "whoami")[0] == ["barman"]
    out, _ = _run(s, "id")
    assert out == ["uid=1001(barman) gid=1001(barman)"]


def test_su_then_read_ledger_succeeds() -> None:
    s = build_initial_state(8)
    _, s = _run(s, "su barman")
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out[0] == "SUSPECT: Nico Faro"


def test_exit_restores_detective_identity() -> None:
    s = build_initial_state(8)
    _, s = _run(s, "su barman")
    _, s = _run(s, "exit")
    assert s["current_user"] == "detective"
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out == ["Error: permission denied"]


def test_mission8_golden_transcript() -> None:
    s = build_initial_state(8)

    _, s = _run(s, "cat /root/bar/hint.txt")
    _, s = _run(s, "su barman")
    _, s = _run(s, "whoami")
    _, s = _run(s, "cat /root/bar/back/ledger.txt")
    _, s = _run(s, "exit")
    assert s["current_user"] == "detective"

    out, s = _run(s, "sh /root/bar/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "identity confirmed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission8_fails_without_returning_home() -> None:
    s = build_initial_state(8)
    _, s = _run(s, "su barman")
    _, s = _run(s, "whoami")
    _, s = _run(s, "cat /root/bar/back/ledger.txt")
    # exit（元ユーザーへの復帰）をせずに判定を試みる。
    out, s = _run(s, "sh /root/bar/case_file.sh")
    assert out == ["Warning: return to your own identity before reporting"]
    assert s["mission_flags"]["case_checked"] is False
