"""Mission5「開かずの資料室」: chmod でヒントを解錠し case_file.sh の判定を通すフロー。

Phase F: 統合ワールド state で検証する。統合ワールドでは case_file.sh は
`/root` にのみ動的合成される（_copy_without_case_files が全 Mission の局所配置を
除去する設計。app/content/missions.py）ため、旧 Mission 別 state で
`/root/vault/inner/case_file.sh` に置かれていた「chmod +x で解錠する」ロック付き
ファイルはワールドに実体を持たない。判定は expected_script_patterns
（chmod +r と chmod +x が command_log に存在すること）で行われる。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission5_initial_ls_shows_locked_permissions() -> None:
    s = state_at_mission(5)
    out, _ = _run(s, "ls -l /root/vault")
    locked = [ln for ln in out if ln.endswith("locked_evidence.txt")][0]
    assert locked.startswith("----------")


def test_mission5_cat_blocked_before_chmod() -> None:
    s = state_at_mission(5)
    out, _ = _run(s, "cat /root/vault/locked_evidence.txt")
    assert out == ["Error: permission denied"]


def test_mission5_locked_case_file_no_longer_exists_in_world() -> None:
    # 旧 Mission 別 state の /root/vault/inner/case_file.sh は統合ワールドでは
    # 実体を持たない（case_file.sh は /root にのみ動的合成される）ため、
    # 「permission denied」ではなく「file not found」になる。
    s = state_at_mission(5)
    out, _ = _run(s, "sh /root/vault/inner/case_file.sh")
    assert out == ["Error: file not found"]


def test_mission5_golden_transcript() -> None:
    s = state_at_mission(5)

    _, s = _run(s, "ls -l /root/vault")
    _, s = _run(s, "chmod +r /root/vault/locked_evidence.txt")
    out, s = _run(s, "cat /root/vault/locked_evidence.txt")
    assert "SEALED EVIDENCE ROOM" in out[0]

    # inner の部屋（今は空だが「解錠」の演出として +x を当てる）を開けてから判定する。
    _, s = _run(s, "chmod +x /root/vault/inner")
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
    # chmod +r のみ行い、+x を行わずに判定すると expected_script_patterns の
    # chmod +x 側が未達成のまま pattern mismatch になる。
    s = state_at_mission(5)
    _, s = _run(s, "chmod +r /root/vault/locked_evidence.txt")
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
