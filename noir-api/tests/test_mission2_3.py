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
    # grep で絶対パス参照 + STATUS 抽出を同時に満たす。
    out, s = _run(s, "grep STATUS /root/park/swing/catinfo.txt")
    assert out == ["STATUS: stray"]

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
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: use find to locate clues"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission2_requires_absolute_path() -> None:
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    _, s = _run(s, "cd /root/park/swing")
    # 相対パスで開くと絶対パス参照が記録されない。
    _, s = _run(s, "grep STATUS catinfo.txt")
    out, s = _run(s, "sh /root/park/case_file.sh")
    assert out == ["Error: absolute path required"]
    assert s["mission_flags"]["case_checked"] is False


def test_mission2_requires_status_key() -> None:
    s = build_initial_state(2)
    _, s = _run(s, "find /root/park -name catinfo.txt")
    # 絶対パスで cat したが STATUS を絞り込んでいない。
    _, s = _run(s, "cat /root/park/swing/catinfo.txt")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Error: required cat status not found"]
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
