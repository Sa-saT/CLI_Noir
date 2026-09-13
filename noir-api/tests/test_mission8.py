"""Mission8「変装潜入」: su/whoami/id によるユーザー切替と owner ベース権限。

Phase F: 統合ワールド state で検証する。case_file.sh は /root にのみ動的合成
される（統合ワールドの設計。旧 Mission 別 state の /root/bar/case_file.sh は
実体を持たない）ため、判定は `sh /root/case_file.sh` で行う。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_ledger_denied_before_su() -> None:
    s = state_at_mission(8)
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out == ["Error: permission denied"]


def test_whoami_default_is_detective() -> None:
    s = state_at_mission(8)
    assert _run(s, "whoami")[0] == ["detective"]


def test_su_changes_current_user_and_id() -> None:
    s = state_at_mission(8)
    _, s = _run(s, "su barman")
    assert s["current_user"] == "barman"
    assert _run(s, "whoami")[0] == ["barman"]
    out, _ = _run(s, "id")
    assert out == ["uid=1001(barman) gid=1001(barman)"]


def test_su_then_read_ledger_succeeds() -> None:
    s = state_at_mission(8)
    _, s = _run(s, "su barman")
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out[0] == "SUSPECT: Nico Faro"


def test_exit_restores_detective_identity() -> None:
    s = state_at_mission(8)
    _, s = _run(s, "su barman")
    _, s = _run(s, "exit")
    assert s["current_user"] == "detective"
    out, _ = _run(s, "cat /root/bar/back/ledger.txt")
    assert out == ["Error: permission denied"]


def test_mission8_relative_path_passes_case_file() -> None:
    """P3-08c: 秘密ファイルのディレクトリへ `cd` してから相対パスで `cat` しても
    resolved_command_log 経由で判定が通ること。
    """
    s = state_at_mission(8)

    _, s = _run(s, "su barman")
    _, s = _run(s, "whoami")
    _, s = _run(s, "cd /root/bar/back")
    _, s = _run(s, "cat ledger.txt")
    _, s = _run(s, "exit")
    assert s["current_user"] == "detective"

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True


def test_mission8_golden_transcript() -> None:
    s = state_at_mission(8)

    _, s = _run(s, "cat /root/bar/hint.txt")
    _, s = _run(s, "su barman")
    _, s = _run(s, "whoami")
    _, s = _run(s, "cat /root/bar/back/ledger.txt")
    _, s = _run(s, "exit")
    assert s["current_user"] == "detective"

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "identity confirmed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 8 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 9


def test_mission8_fails_without_returning_home() -> None:
    s = state_at_mission(8)
    _, s = _run(s, "su barman")
    _, s = _run(s, "whoami")
    _, s = _run(s, "cat /root/bar/back/ledger.txt")
    # exit（元ユーザーへの復帰）をせずに判定を試みる。
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: return to your own identity before reporting"]
    assert progress.flags(s)["case_checked"] is False
