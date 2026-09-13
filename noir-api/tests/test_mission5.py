"""Mission5「開かずの資料室」: chmod でヒントと封印解除スクリプトを解錠するフロー。

統合ワールドでは case_file.sh が /root に動的合成される（P3-04）ため、旧 Mission 別
state で `/root/vault/inner/case_file.sh` をロックしていた実行権限パズルは、奥の部屋の
`unseal.sh`（immutable=False・x ビット無し）に移した（2026-09-13）。判定は
expected_script_patterns（chmod +r / chmod +x / sh unseal.sh が command_log に存在）。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission

_EVIDENCE = "/root/vault/locked_evidence.txt"
_UNSEAL = "/root/vault/inner/unseal.sh"


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission5_initial_ls_shows_locked_permissions() -> None:
    s = state_at_mission(5)
    out, _ = _run(s, "ls -l /root/vault")
    locked = [ln for ln in out if ln.endswith("locked_evidence.txt")][0]
    assert locked.startswith("----------")


def test_mission5_cat_blocked_before_chmod() -> None:
    s = state_at_mission(5)
    out, _ = _run(s, f"cat {_EVIDENCE}")
    assert out == ["Error: permission denied"]


def test_mission5_unseal_blocked_before_chmod_x() -> None:
    # 配置スクリプトは immutable=False なので can_exec の特例が効かず、x ビットが要る。
    s = state_at_mission(5)
    out, _ = _run(s, f"sh {_UNSEAL}")
    assert out == ["Error: permission denied"]


def test_mission5_golden_transcript() -> None:
    s = state_at_mission(5)

    _, s = _run(s, "ls -l /root/vault")
    _, s = _run(s, f"chmod +r {_EVIDENCE}")
    out, s = _run(s, f"cat {_EVIDENCE}")
    assert "SEALED EVIDENCE ROOM" in out[0]
    assert any("inner" in ln for ln in out)

    _, s = _run(s, f"chmod +x {_UNSEAL}")
    out, s = _run(s, f"sh {_UNSEAL}")
    assert out == ["SEAL RELEASED: room B-2", "EVIDENCE TAG: ORCHID-7"]

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "vault cracked"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 5 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 6


def test_mission5_missing_chmod_x_blocks_clear() -> None:
    # chmod +r のみで判定すると chmod +x / sh unseal.sh が未達成のまま pattern mismatch。
    s = state_at_mission(5)
    _, s = _run(s, f"chmod +r {_EVIDENCE}")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False


def test_mission5_chmod_x_without_running_unseal_blocks_clear() -> None:
    # 鍵を付けただけでは封印は解けない（sh unseal.sh の成功が要る）。
    s = state_at_mission(5)
    _, s = _run(s, f"chmod +r {_EVIDENCE}")
    _, s = _run(s, f"chmod +x {_UNSEAL}")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
