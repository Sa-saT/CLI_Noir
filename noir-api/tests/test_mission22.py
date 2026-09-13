"""Mission22「最終事件」: 全技術を関所として直列に突破するフィナーレ。

Phase F: 統合ワールド state で検証する（evidence.tar / ledger.txt は
/root/clues に移設済み。clues/vault/logs は Mission22 の被ゲート区画、vault は
Mission5 と加算マージ。ghost.example は Mission12 で /etc/hosts に追記済み）。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def _clear_all_checkpoints(s: dict) -> dict:
    # 1: find
    _, s = _run(s, 'find /root/clues -name "*.key"')
    # 2: ssh + remote 証拠閲覧
    _, s = _run(s, "ssh ghost.example")
    _, s = _run(s, "cat /den/evidence/orders.txt")
    _, s = _run(s, "exit")
    # 3: chmod
    _, s = _run(s, "chmod +r /root/vault/locked.txt")
    _, s = _run(s, "cat /root/vault/locked.txt")
    # 4: パイプ集計
    _, s = _run(s, "grep TEL /root/logs/calls.log | sort | uniq -c | sort")
    # 5: tar
    _, s = _run(s, "tar -xf /root/clues/evidence.tar")
    _, s = _run(s, "cat final_note.txt")
    # 6: md5sum
    _, s = _run(s, "md5sum final_note.txt")
    # 7: 自作 sh
    _, s = _run(s, 'echo "BURNER=555-0199" > /root/verdict.sh')
    _, s = _run(s, 'echo \'if grep -q "$BURNER" /root/logs/calls.log; then\' >> /root/verdict.sh')
    _, s = _run(s, "echo '  echo \"FOUND\"' >> /root/verdict.sh")
    _, s = _run(s, "echo 'fi' >> /root/verdict.sh")
    _, s = _run(s, "chmod +x /root/verdict.sh")
    _, s = _run(s, "sh /root/verdict.sh")
    # 8: 報告
    _, s = _run(s, 'echo "Selene Vance" > report.txt')
    return s


def test_mission22_golden_transcript() -> None:
    s = state_at_mission(22)
    s = _clear_all_checkpoints(s)

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "case closed"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 22 in s["mission_progress"]["completed"]
    # Mission22 は最終 Mission。全クリア後は次のアクティブ Mission が無い。
    assert progress.active_mission_id(s["mission_progress"]) is None


def test_mission22_pipe_confirms_burner_frequency() -> None:
    s = state_at_mission(22)
    out, _ = _run(s, "grep TEL /root/logs/calls.log | sort | uniq -c | sort")
    assert out[-1] == "      6 TEL: 555-0199"


def test_mission22_missing_checkpoint_reports_number() -> None:
    s = state_at_mission(22)
    # 1,2,3,4 は通すが、tar（5番目）を飛ばす。
    _, s = _run(s, 'find /root/clues -name "*.key"')
    _, s = _run(s, "ssh ghost.example")
    _, s = _run(s, "cat /den/evidence/orders.txt")
    _, s = _run(s, "exit")
    _, s = _run(s, "chmod +r /root/vault/locked.txt")
    _, s = _run(s, "grep TEL /root/logs/calls.log | sort | uniq -c | sort")

    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: checkpoint 5 incomplete"]
    assert progress.flags(s)["case_checked"] is False


def test_mission22_missing_first_checkpoint() -> None:
    s = state_at_mission(22)
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: checkpoint 1 incomplete"]
