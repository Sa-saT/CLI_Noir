"""Mission2（公園の猫）と Mission3（遊園地の爆弾）の判定・フローのテスト。

Mission1 のゴールデントランスクリプト方式を踏襲。build_initial_state で
初期 FS / current_path を含む実プレイ相当の state を組み立てて検証する。
"""

from app.evaluator import evaluate
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


# --- Mission2 ---
def test_mission2_initial_state() -> None:
    s = build_initial_state(2)
    assert s["current_path"] == "/root/park"
    # 猫ファイルは swing 配下に絶対パスで存在する。
    out, _ = _run(s, "find /root/park -name catinfo.txt")
    assert "/root/park/swing/catinfo.txt" in out


def test_mission2_golden_transcript() -> None:
    s = build_initial_state(2)

    _, s = _run(s, "find /root/park -name catinfo.txt")
    # grep で STATUS 抽出を確認する（読み方は絶対パスでよい）。
    out, s = _run(s, "grep STATUS /root/park/swing/catinfo.txt")
    assert out == ["STATUS: stray"]
    # 報告書には / から始まる絶対パスと STATUS を書く（P3-08e: 締め直し後の必須要件）。
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "cat found"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission2_requires_find() -> None:
    s = build_initial_state(2)
    _, s = _run(s, "grep STATUS /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: use find to locate clues"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission2_requires_absolute_path() -> None:
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cd /root/park/swing")
    # 相対パスで読むこと自体は自由。だが報告書（echo 行）に絶対パスを書いていない。
    _, s = _run(s, "grep STATUS catinfo.txt")
    _, s = _run(s, 'echo "STATUS: stray" > report.txt')
    out, s = _run(s, "sh /root/park/case_file.sh")
    assert out == ["Error: absolute path required — report the path from /"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission2_requires_status_key() -> None:
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    # 絶対パスで cat したが STATUS を絞り込んでいない。
    _, s = _run(s, "cat /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: required cat status not found"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission2_relative_read_with_absolute_report_passes() -> None:
    """P3-08e の主目的: 読み方は自由。cd して相対パスで読んでも、
    報告書（echo 行）に絶対パスと STATUS を書けばクリアできる。"""
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cd /root/park/swing")
    out, s = _run(s, "cat catinfo.txt")
    assert "STATUS: stray" in out
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > report.txt')

    out, s = _run(s, "sh /root/park/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True


def test_mission2_absolute_read_without_absolute_report_fails() -> None:
    """締め直しの確認: 絶対パスで読んでも、報告書（echo 行）に絶対パスを
    書かなければ絶対パス要件は満たさない。"""
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cat /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "STATUS: stray" > report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: absolute path required — report the path from /"]
    assert s["mission_flags"]["case_checked"] is False


# --- Mission3 ---
def test_mission3_ssh_connect_and_exit() -> None:
    s = build_initial_state(3)
    assert s["current_path"] == "/root"

    out, s = _run(s, "ssh amusement_park")
    assert out == ["Connected to amusement_park"]
    assert s["current_path"] == "/gate"
    assert s["remote_mode"] is True

    out, s = _run(s, "exit")
    assert s["current_path"] == "/root"
    assert s["remote_mode"] is False


def test_mission3_host_not_found() -> None:
    s = build_initial_state(3)
    out, s = _run(s, "ssh nowhere")
    assert out == ["Host not found"]


def test_mission3_golden_transcript() -> None:
    s = build_initial_state(3)

    _, s = _run(s, "ssh amusement_park")
    out, s = _run(s, 'find /gate -name "*.txt"')
    assert "/gate/booth/manual.txt" in out

    # ヒントを読み、Code/Wire/Height を echo で記録する（証跡）。
    _, s = _run(s, "cat /gate/booth/manual.txt")
    _, s = _run(s, "cat /gate/ferris/wiring.txt")
    _, s = _run(s, "cat /gate/sign/notice.txt")
    _, s = _run(s, 'echo "Code: K3Y9" > report.txt')
    _, s = _run(s, 'echo "Wire: blue" >> report.txt')
    _, s = _run(s, 'echo "Height: 180" >> report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert s["mission_flags"]["case_checked"] is True

    # remote のまま commit/push してもクリア判定が成立する。
    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "defused"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert s["mission_flags"]["completed"] is True


def test_mission3_incomplete_keys_block_clear() -> None:
    s = build_initial_state(3)
    _, s = _run(s, "ssh amusement_park")
    # Code のみ記録（Wire/Height 欠落）。
    _, s = _run(s, 'echo "Code: K3Y9" > report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    assert s["mission_flags"]["case_checked"] is False
