"""resolved_command_log（解決済みコマンドログ）の記録基盤テスト（P3-08a）。

判定側（app/evaluator/judge.py）はまだこのログを参照しない。本テストは記録基盤
そのもの（fs.normalize の解決結果が engine.evaluate() を通じて resolved_command_log
に正しく積まれること）だけを検証する。
"""

from app.evaluator import engine
from app.evaluator import progress
from app.models import default_state, default_world_state


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return engine.evaluate(line, state)


# --- 相対パスが解決されること ---


def test_relative_path_is_resolved() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, "cat businesscard.txt")

    entry = state["resolved_command_log"][-1]
    assert entry["resolved_line"] == "cat /root/desk/businesscard.txt"
    assert "/root/desk/businesscard.txt" in entry["paths"]


# --- 絶対パスはそのまま（置換しても同じ文字列になる） ---


def test_absolute_path_resolved_line_equals_line() -> None:
    state = default_world_state()
    line = "cat /root/desk/businesscard.txt"
    _, state = _run(state, line)

    entry = state["resolved_command_log"][-1]
    assert entry["resolved_line"] == line
    assert entry["line"] == line


# --- リダイレクト先も解決されること ---


def test_redirect_target_is_resolved() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, "echo hello > businesscard.txt")

    entry = state["resolved_command_log"][-1]
    assert "/root/desk/businesscard.txt" in entry["paths"]
    assert entry["resolved_line"] == "echo hello > /root/desk/businesscard.txt"


# --- 失敗コマンドの解決結果が次のコマンドへ漏れないこと ---


def test_failed_command_resolutions_do_not_leak_into_next() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    out, state = _run(state, "cat nonexistent_file.txt")
    assert out[0].startswith("Error:")

    _, state = _run(state, "cat businesscard.txt")

    entry = state["resolved_command_log"][-1]
    assert not any("nonexistent_file.txt" in p for p in entry["paths"])
    assert entry["resolved_line"] == "cat /root/desk/businesscard.txt"


# --- command_log と resolved_command_log が常に 1:1 で揃うこと ---


def test_command_log_and_resolved_log_stay_in_sync() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, "cat nonexistent_file.txt")  # 失敗（command_log には積まれない）
    _, state = _run(state, "cat businesscard.txt")
    _, state = _run(state, "pwd")

    command_log = state["command_log"]
    resolved_log = state["resolved_command_log"]
    assert len(command_log) == len(resolved_log)
    for i, line in enumerate(command_log):
        assert resolved_log[i]["line"] == line


# --- mission_id タグ ---


def test_mission_id_tag_matches_active_mission() -> None:
    state = default_world_state()
    _, state = _run(state, "cd /root/desk")
    _, state = _run(state, "cat businesscard.txt")

    entry = state["resolved_command_log"][-1]
    expected = progress.active_mission_id(state["mission_progress"])
    assert entry["mission_id"] == expected


# --- 回帰: Mission 別 state（default_state()）でも resolved_command_log が存在すること ---


def test_flat_state_has_resolved_command_log_field() -> None:
    state = default_state()
    assert state["resolved_command_log"] == []


def test_flat_state_records_resolutions() -> None:
    """Mission 別 state でも記録が働くこと。

    現行の API/WS はまだこの形状の state を読み書きしており（カットオーバーは
    P3-10/P3-11）、P3-08b で judge がこのログを見るようになる。フィールドが
    存在するだけでなく実際に積まれることを確認しておく。
    """
    state = default_state()
    _, state = _run(state, "mkdir sub")
    _, state = _run(state, "cd sub")
    _, state = _run(state, "touch a.txt")
    _, state = _run(state, "cat a.txt")

    entry = state["resolved_command_log"][-1]
    assert entry["resolved_line"] == "cat /root/sub/a.txt"
    assert "/root/sub/a.txt" in entry["paths"]
    assert len(state["command_log"]) == len(state["resolved_command_log"])
