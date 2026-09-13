"""スマート捜査ボーナス（機能 3）とタイムアタック演出（機能 7）。"""

from app.evaluator import evaluate, progress, score
from app.models import default_world_state


def _run(s, line):
    return evaluate(line, s)


def _clear_mission1(s):
    for cmd in [
        "cat /root/desk/businesscard.txt",
        'echo "NAME: Sam Spade" > /root/desk/businesscard.txt',
        "sh case_file.sh",
        "git add .",
        'git commit -m "x"',
        "git push",
    ]:
        _, s = _run(s, cmd)
    return s


def test_par_comes_from_hint_three_minus_judge_and_git() -> None:
    # Mission1 のヒント 3: cat → echo → sh → git add → git commit → git push（6 手）→ 捜査は 2 手 → 下限 3
    assert score.par_for(1) == 3
    assert score.par_for(4) >= 3


def test_smart_clear_scores_bonus_and_records_timer() -> None:
    s = default_world_state()
    score.mark_started(s, 1)
    s = _clear_mission1(s)
    rec = score.score_of(s, 1)
    assert rec["commands"] == 2 and rec["par"] == 3
    assert rec["bonuses"] == ["SMART"] and rec["score"] == 150
    assert rec["elapsed_seconds"] is not None and rec["elapsed_seconds"] >= 0
    # 次 Mission の開始時刻が刻まれる
    assert score.started_at(s, progress.active_mission_id(s["mission_progress"]))


def test_wandering_loses_the_smart_bonus_but_never_fails() -> None:
    s = default_world_state()
    for _ in range(6):
        _, s = _run(s, "ls")
    s = _clear_mission1(s)
    rec = score.score_of(s, 1)
    assert rec["commands"] == 8 and "SMART" not in rec["bonuses"]
    assert rec["score"] == 100
    assert 1 in s["mission_progress"]["completed"]


def test_pipe_bonus() -> None:
    s = default_world_state()
    _, s = _run(s, "cat /root/desk/businesscard.txt | grep NAME")
    s = _clear_mission1(s)
    assert "PIPE" in score.score_of(s, 1)["bonuses"]
