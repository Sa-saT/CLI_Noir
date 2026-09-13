"""Tab 補完（app/evaluator/complete.py + WS `complete`/`completions` フレーム）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.evaluator import complete, evaluate
from app.models import default_world_state
from tests.helpers import state_at_mission


def test_command_completion_only_released_commands() -> None:
    s = default_world_state()
    candidates, start = complete.complete(s, "c", 1)
    # Mission1 時点: BASE_COMMANDS + 基本操作の cat / cd / clear（Level 5 の cut 等はまだ出ない）
    assert candidates == ["cat", "cd", "clear"]
    assert start == 0
    later, _ = complete.complete(state_at_mission(11), "c", 1)
    assert "cut" in later and "chmod" in later


def test_command_completion_after_pipe() -> None:
    s = state_at_mission(4)
    candidates, start = complete.complete(s, "grep TEL tape.log | so", 22)
    assert candidates == ["sort"]
    assert start == 20


def test_path_completion_spec_example() -> None:
    """設計指示書 § 7 の例: `cat bus` → businesscard.txt（/root/desk で）。"""
    s = default_world_state()
    _, s = evaluate("cd desk", s)
    candidates, start = complete.complete(s, "cat bus", 7)
    assert candidates == ["businesscard.txt"]
    assert start == 4


def test_path_completion_replaces_last_segment_only() -> None:
    s = default_world_state()
    candidates, start = complete.complete(s, "cat /root/de", 12)
    assert candidates == ["desk/"]
    assert start == 10  # "/root/" の直後


def test_path_completion_lists_directory_when_prefix_empty() -> None:
    s = default_world_state()
    candidates, start = complete.complete(s, "ls ", 3)
    # 動的合成の case_file.sh も候補に出る。未解放区画（park 等）は出ない
    assert candidates == ["case_file.sh", "desk/"]
    assert start == 3


def test_path_completion_hides_locked_areas_until_released() -> None:
    s = default_world_state()
    candidates, _ = complete.complete(s, "cd pa", 5)
    assert candidates == []
    candidates, _ = complete.complete(state_at_mission(2), "cd pa", 5)
    assert candidates == ["park/"]


def test_hidden_files_only_with_dot_prefix() -> None:
    s = state_at_mission(20)
    candidates, _ = complete.complete(s, "cat /tmp/", 9)
    assert candidates == []
    candidates, start = complete.complete(s, "cat /tmp/.f", 11)
    assert candidates == [".forgotten"]
    assert start == 9


def test_quoted_name_with_space() -> None:
    s = state_at_mission(16)
    _, s = evaluate("cd /root/warehouse", s)
    line = 'cat "top s'
    candidates, start = complete.complete(s, line, len(line))
    assert candidates == ["top secret.txt"]
    assert start == 5  # 開き引用符の直後


def test_git_subcommand_completion() -> None:
    s = default_world_state()
    candidates, start = complete.complete(s, "git pu", 6)
    assert candidates == ["push"]
    assert start == 4


def test_cursor_in_middle_completes_word_before_cursor() -> None:
    s = default_world_state()
    candidates, start = complete.complete(s, "cat de businesscard.txt", 6)
    assert candidates == ["desk/"]
    assert start == 4


def test_remote_completion_uses_remote_filesystem() -> None:
    s = state_at_mission(3)
    _, s = evaluate("ssh amusement_park", s)
    candidates, _ = complete.complete(s, "cat boo", 7)
    assert candidates == ["booth/"]


def test_ws_complete_frame_roundtrip(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        ws.send_json({"type": "complete", "id": 44, "line": "cat de", "cursor": 6})
        res = ws.receive_json()
        assert res == {
            "type": "completions",
            "id": 44,
            "candidates": ["desk/"],
            "replace_from": 4,
        }
        # 補完は state を変えない（history に残らない）
        ws.send_json({"type": "exec", "id": 1, "command": "history"})
        out = ws.receive_json()
        assert out["lines"] == []
