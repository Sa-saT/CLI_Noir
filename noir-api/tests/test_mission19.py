"""Mission19「捜査手順書を書け」: sh の変数/if/for スクリプト実行フロー。

Phase F: 統合ワールド state で検証する（sample.sh / evidence.txt は
/root/precinct_desk に移設済み。プレイヤーが自作する patrol.sh もこの部屋に置く
—— judge.py の _MISSION19_SCRIPT_PATH を /root/precinct_desk/patrol.sh に追随済み）。
"""

from app.evaluator import evaluate, progress
from tests.helpers import state_at_mission


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_cat_sample_shows_the_pattern() -> None:
    s = state_at_mission(19)
    out, _ = _run(s, "cat /root/precinct_desk/sample.sh")
    assert any("if grep -q" in ln for ln in out)


def _build_patrol_sh(s: dict) -> dict:
    _, s = _run(s, 'echo "TARGET=Sam" > /root/precinct_desk/patrol.sh')
    _, s = _run(
        s,
        'echo \'if grep -q "$TARGET" /root/precinct_desk/evidence.txt; then\''
        " >> /root/precinct_desk/patrol.sh",
    )
    _, s = _run(s, 'echo \'  echo "FOUND"\' >> /root/precinct_desk/patrol.sh')
    _, s = _run(s, "echo 'fi' >> /root/precinct_desk/patrol.sh")
    # sh は読み取りだけで実行できる（実 Linux では chmod +x 不要）が、本ゲームでは
    # Mission5 以来「自作/配置スクリプトは chmod +x してから sh で実行する」を
    # 統一ルールとして採用している（can_exec の実行ビット検査。P2-01）。
    _, s = _run(s, "chmod +x /root/precinct_desk/patrol.sh")
    return s


def test_patrol_sh_runs_and_prints_found() -> None:
    s = state_at_mission(19)
    s = _build_patrol_sh(s)
    out, s = _run(s, "sh /root/precinct_desk/patrol.sh")
    assert out == ["FOUND"]
    assert progress.flags(s)["script_found"] is True


def test_patrol_sh_wrong_target_finds_nothing() -> None:
    s = state_at_mission(19)
    _, s = _run(s, 'echo "TARGET=NoSuchName" > /root/precinct_desk/patrol.sh')
    _, s = _run(
        s,
        'echo \'if grep -q "$TARGET" /root/precinct_desk/evidence.txt; then\''
        " >> /root/precinct_desk/patrol.sh",
    )
    _, s = _run(s, 'echo \'  echo "FOUND"\' >> /root/precinct_desk/patrol.sh')
    _, s = _run(s, "echo 'fi' >> /root/precinct_desk/patrol.sh")
    _, s = _run(s, "chmod +x /root/precinct_desk/patrol.sh")
    out, s = _run(s, "sh /root/precinct_desk/patrol.sh")
    assert out == []
    assert progress.flags(s).get("script_found", False) is False


def test_for_loop_iterates_items() -> None:
    s = state_at_mission(19)
    _, s = _run(s, "cd /root/precinct_desk")
    _, s = _run(s, "echo 'for x in a b c; do' > loop.sh")
    _, s = _run(s, "echo '  echo $x' >> loop.sh")
    _, s = _run(s, "echo 'done' >> loop.sh")
    _, s = _run(s, "chmod +x loop.sh")
    out, _ = _run(s, "sh loop.sh")
    assert out == ["a", "b", "c"]


def test_script_denylist_command_is_blocked() -> None:
    s = state_at_mission(19)
    _, s = _run(s, "echo 'rm -rf /' > /root/precinct_desk/bad.sh")
    _, s = _run(s, "chmod +x /root/precinct_desk/bad.sh")
    out, _ = _run(s, "sh /root/precinct_desk/bad.sh")
    assert out == ["Error: command not allowed"]


def test_mission19_golden_transcript() -> None:
    s = state_at_mission(19)
    s = _build_patrol_sh(s)

    out, s = _run(s, "sh /root/precinct_desk/patrol.sh")
    assert out == ["FOUND"]

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "playbook written"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert 19 in s["mission_progress"]["completed"]
    assert progress.active_mission_id(s["mission_progress"]) == 20


def test_mission19_requires_actual_variable_and_if() -> None:
    # ハードコードした echo FOUND だけでは通らない（変数定義・if が無いため）。
    s = state_at_mission(19)
    _, s = _run(s, 'echo "FOUND" > /root/precinct_desk/patrol.sh')
    _, s = _run(s, "chmod +x /root/precinct_desk/patrol.sh")
    _, s = _run(s, "sh /root/precinct_desk/patrol.sh")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False


def test_mission19_requires_running_the_script() -> None:
    s = state_at_mission(19)
    s = _build_patrol_sh(s)
    # sh /root/precinct_desk/patrol.sh を一度も実行していない。
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert progress.flags(s)["case_checked"] is False
