"""Mission19「捜査手順書を書け」: sh の変数/if/for スクリプト実行フロー。"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def test_cat_sample_shows_the_pattern() -> None:
    s = build_initial_state(19)
    out, _ = _run(s, "cat sample.sh")
    assert any("if grep -q" in ln for ln in out)


def _build_patrol_sh(s: dict) -> dict:
    _, s = _run(s, 'echo "TARGET=Sam" > /root/patrol.sh')
    _, s = _run(s, 'echo \'if grep -q "$TARGET" /root/evidence.txt; then\' >> /root/patrol.sh')
    _, s = _run(s, 'echo \'  echo "FOUND"\' >> /root/patrol.sh')
    _, s = _run(s, "echo 'fi' >> /root/patrol.sh")
    # sh は読み取りだけで実行できる（実 Linux では chmod +x 不要）が、本ゲームでは
    # Mission5 以来「自作/配置スクリプトは chmod +x してから sh で実行する」を
    # 統一ルールとして採用している（can_exec の実行ビット検査。P2-01）。
    _, s = _run(s, "chmod +x /root/patrol.sh")
    return s


def test_patrol_sh_runs_and_prints_found() -> None:
    s = build_initial_state(19)
    s = _build_patrol_sh(s)
    out, s = _run(s, "sh /root/patrol.sh")
    assert out == ["FOUND"]
    assert s["mission_flags"]["script_found"] is True


def test_patrol_sh_wrong_target_finds_nothing() -> None:
    s = build_initial_state(19)
    _, s = _run(s, 'echo "TARGET=NoSuchName" > /root/patrol.sh')
    _, s = _run(s, 'echo \'if grep -q "$TARGET" /root/evidence.txt; then\' >> /root/patrol.sh')
    _, s = _run(s, 'echo \'  echo "FOUND"\' >> /root/patrol.sh')
    _, s = _run(s, "echo 'fi' >> /root/patrol.sh")
    _, s = _run(s, "chmod +x /root/patrol.sh")
    out, s = _run(s, "sh /root/patrol.sh")
    assert out == []
    assert s["mission_flags"].get("script_found", False) is False


def test_for_loop_iterates_items() -> None:
    s = build_initial_state(19)
    _, s = _run(s, "echo 'for x in a b c; do' > /root/loop.sh")
    _, s = _run(s, "echo '  echo $x' >> /root/loop.sh")
    _, s = _run(s, "echo 'done' >> /root/loop.sh")
    _, s = _run(s, "chmod +x /root/loop.sh")
    out, _ = _run(s, "sh /root/loop.sh")
    assert out == ["a", "b", "c"]


def test_script_denylist_command_is_blocked() -> None:
    s = build_initial_state(19)
    _, s = _run(s, "echo 'rm -rf /' > /root/bad.sh")
    _, s = _run(s, "chmod +x /root/bad.sh")
    out, _ = _run(s, "sh /root/bad.sh")
    assert out == ["Error: command not allowed"]


def test_mission19_golden_transcript() -> None:
    s = build_initial_state(19)
    s = _build_patrol_sh(s)

    out, s = _run(s, "sh /root/patrol.sh")
    assert out == ["FOUND"]

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "playbook written"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission19_requires_actual_variable_and_if() -> None:
    # ハードコードした echo FOUND だけでは通らない（変数定義・if が無いため）。
    s = build_initial_state(19)
    _, s = _run(s, 'echo "FOUND" > /root/patrol.sh')
    _, s = _run(s, "chmod +x /root/patrol.sh")
    _, s = _run(s, "sh /root/patrol.sh")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission19_requires_running_the_script() -> None:
    s = build_initial_state(19)
    s = _build_patrol_sh(s)
    # sh /root/patrol.sh を一度も実行していない。
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
