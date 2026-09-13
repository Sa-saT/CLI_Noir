"""Mission2（公園の猫）と Mission3（遊園地の爆弾）の判定・フローのテスト。

Mission1 のゴールデントランスクリプト方式を踏襲。Mission2 は統合ワールド
（default_world_state + Mission1 クリア）、Mission3 は build_initial_state で
初期 FS / current_path を含む実プレイ相当の state を組み立てて検証する。
"""

from app.evaluator import evaluate, progress
from app.models import default_world_state
from app.ws.terminal import build_initial_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


# --- Mission2 ---
def _mission2_world() -> dict:
    """Mission1 をクリアした直後の統合ワールド（park が解放済み・cwd は /root）。

    Mission2 の報告書は机（/root/desk/report.txt。Mission1 の区画）に書くため、
    Mission 別 state（build_initial_state(2) には desk が無い）ではなく統合ワールドで検証する。
    """
    s = default_world_state()
    progress.advance_mission(s, 1)
    s["current_path"] = "/root"
    return s


def test_mission2_initial_state() -> None:
    s = _mission2_world()
    # 猫ファイルは swing 配下に絶対パスで存在する。
    out, _ = _run(s, "find /root/park -name catinfo.txt")
    assert "/root/park/swing/catinfo.txt" in out


def test_mission2_golden_transcript() -> None:
    s = _mission2_world()

    _, s = _run(s, "find /root/park -name catinfo.txt")
    # grep で STATUS 抽出を確認する（読み方は絶対パスでよい）。
    out, s = _run(s, "grep STATUS /root/park/swing/catinfo.txt")
    assert out == ["STATUS: stray"]
    # 机に戻って報告書を書く。/ から始まる絶対パスと STATUS を含める。
    _, s = _run(s, "cd desk")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > report.txt')
    out, s = _run(s, "cat /root/desk/report.txt")
    assert out == ["/root/park/swing/catinfo.txt STATUS: stray"]

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True

    _, s = _run(s, "git add .")
    _, s = _run(s, 'git commit -m "cat found"')
    out, s = _run(s, "git push")
    assert out == ["Mission Complete! Next mission unlocked."]
    assert progress.active_mission_id(s["mission_progress"]) == 3


def test_mission2_requires_find() -> None:
    s = _mission2_world()
    _, s = _run(s, "grep STATUS /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: use find to locate clues"]
    assert progress.flags(s)["case_checked"] is False


def test_mission2_requires_report_on_desk() -> None:
    """報告書は机（/root/desk/report.txt）に置く。公園に書いても判定は拾わない。"""
    s = _mission2_world()
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/park/report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: report not found — write /root/desk/report.txt"]
    assert progress.flags(s)["case_checked"] is False


def test_mission2_requires_absolute_path() -> None:
    s = _mission2_world()
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cd /root/park/swing")
    # 相対パスで読むこと自体は自由。だが報告書に絶対パスを書いていない。
    _, s = _run(s, "grep STATUS catinfo.txt")
    _, s = _run(s, 'echo "STATUS: stray" > /root/desk/report.txt')
    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["Error: absolute path required — report the path from /"]
    assert progress.flags(s)["case_checked"] is False


def test_mission2_requires_status_key() -> None:
    s = _mission2_world()
    _, s = _run(s, "find /root/park -name catinfo.txt")
    # 絶対パスで cat したが、報告書に STATUS を写していない。
    _, s = _run(s, "cat /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt" > /root/desk/report.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: required cat status not found"]
    assert progress.flags(s)["case_checked"] is False


def test_mission2_relative_read_with_absolute_report_passes() -> None:
    """P3-08e の主目的: 読み方は自由。cd して相対パスで読んでも、
    報告書に絶対パスと STATUS を書けばクリアできる。"""
    s = _mission2_world()
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cd /root/park/swing")
    out, s = _run(s, "cat catinfo.txt")
    assert "STATUS: stray" in out
    _, s = _run(s, 'echo "/root/park/swing/catinfo.txt STATUS: stray" > /root/desk/report.txt')

    out, s = _run(s, "sh /root/case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert progress.flags(s)["case_checked"] is True


def test_mission2_absolute_read_without_absolute_report_fails() -> None:
    """締め直しの確認: 絶対パスで読んでも、報告書に絶対パスを
    書かなければ絶対パス要件は満たさない。"""
    s = _mission2_world()
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cat /root/park/swing/catinfo.txt")
    _, s = _run(s, 'echo "STATUS: stray" > /root/desk/report.txt')

    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: absolute path required — report the path from /"]
    assert progress.flags(s)["case_checked"] is False


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
