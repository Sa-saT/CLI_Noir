"""Mission4「盗聴テープを解析せよ」: パイプ集計で最頻出番号を特定するフロー。

Phase F: 統合ワールド state（tape.log は /root/wiretap_room/tape.log に移設済み）で検証する。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_mission4_tape_line_count() -> None:
    s = state_at_mission(4)
    # TEL 20 行 + ノイズ 10 行 = 30 行。
    assert _run(s, "wc -l /root/wiretap_room/tape.log")[0] == [
        "30 /root/wiretap_room/tape.log"
    ]


def test_mission4_pipeline_finds_top_number() -> None:
    s = state_at_mission(4)
    out, _ = _run(s, "grep TEL /root/wiretap_room/tape.log | sort | uniq -c | sort")
    # 昇順ソートの最終行が最頻出（正解）。
    assert out[-1] == "      9 TEL: 555-0142"


def test_mission4_golden_transcript() -> None:
    s = state_at_mission(4)

    _, s = _run(s, "wc -l /root/wiretap_room/tape.log")
    _, s = _run(s, "grep TEL /root/wiretap_room/tape.log | sort | uniq -c | sort")
    _, s = _run(s, 'echo "TEL: 555-0142" > /root/answer.txt')

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "top caller"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 4 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 5


def test_mission4_wrong_number_blocks_clear() -> None:
    s = state_at_mission(4)
    _, s = _run(s, "grep TEL /root/wiretap_room/tape.log | sort | uniq -c | sort")
    # 頻度2位を誤答として記述。
    _, s = _run(s, 'echo "TEL: 555-0199" > /root/answer.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False


def test_mission4_requires_uniq_c() -> None:
    s = state_at_mission(4)
    # uniq -c を使わず正解番号だけ記述しても不合格（集計の証跡が必要）。
    _, s = _run(s, 'echo "TEL: 555-0142" > /root/answer.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
