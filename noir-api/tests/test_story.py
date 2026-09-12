"""進行案内「独り言レイヤー」（STORY-01）のテスト。

`app/evaluator/story.py` の純粋関数を `default_world_state()` + `engine.evaluate()`
直呼びで検証する。WS 経由の統合テストは末尾に 2 件だけ置く。
"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.evaluator import engine, story
from app.models.tables import default_world_state
from app.ws.terminal import build_initial_state


def _clear_mission1(state: dict) -> dict:
    """Mission1（名刺編集）を実際にクリアし push まで完了させる。"""
    _, state = engine.evaluate("cd /root/desk", state)
    _, state = engine.evaluate(
        'echo "NAME: Sam Spade" > /root/desk/businesscard.txt', state
    )
    _, state = engine.evaluate("cat /root/desk/businesscard.txt", state)
    _, state = engine.evaluate("cd /root", state)
    _, state = engine.evaluate("sh case_file.sh", state)
    _, state = engine.evaluate("git add .", state)
    _, state = engine.evaluate('git commit -m "solved"', state)
    _, state = engine.evaluate("git push", state)
    return state


def test_start_beats_fires_mission1_start_once() -> None:
    state = default_world_state()
    beats = story.start_beats(state)
    assert [b["id"] for b in beats] == ["start"]
    assert beats[0]["mission_id"] == 1

    # 二度目は既発火なので空
    assert story.start_beats(state) == []


def test_after_beats_cd_desk_fires_via_resolved_line() -> None:
    state = default_world_state()
    out, state = engine.evaluate("cd /root/desk", state)
    entry = state["resolved_command_log"][-1]
    beats = story.after_beats(state, 1, "cd /root/desk", out, entry)
    assert [b["id"] for b in beats] == ["desk"]

    # 発火済みなので、続けて引数無し ls を打っても desk は当たらない
    out2, state = engine.evaluate("ls", state)
    entry2 = state["resolved_command_log"][-1]
    beats2 = story.after_beats(state, 1, "ls", out2, entry2)
    assert beats2 == []


def test_after_beats_ls_fires_desk_via_paths_fallback() -> None:
    """cd を経由せず desk に居る状態で引数無し ls を打つと、paths 経由で desk が当たる。"""
    state = default_world_state()
    state["current_path"] = "/root/desk"
    out, state = engine.evaluate("ls", state)
    entry = state["resolved_command_log"][-1]
    beats = story.after_beats(state, 1, "ls", out, entry)
    assert [b["id"] for b in beats] == ["desk"]


def test_after_beats_no_editor_on_error_with_no_entry() -> None:
    state = default_world_state()
    prev_len = len(state["resolved_command_log"])
    out, state = engine.evaluate("vi businesscard.txt", state)
    # エラーは resolved_command_log に記録されない
    assert len(state["resolved_command_log"]) == prev_len
    beats = story.after_beats(state, 1, "vi businesscard.txt", out, None)
    assert [b["id"] for b in beats] == ["no_editor"]


def test_after_beats_judge_fail_then_judge_pass() -> None:
    state = default_world_state()

    out, state = engine.evaluate("sh case_file.sh", state)
    beats = story.after_beats(
        state, 1, "sh case_file.sh", out, state["resolved_command_log"][-1]
    )
    assert [b["id"] for b in beats] == ["judge_fail"]

    _, state = engine.evaluate("cd /root/desk", state)
    _, state = engine.evaluate(
        'echo "NAME: Sam Spade" > /root/desk/businesscard.txt', state
    )
    _, state = engine.evaluate("cat /root/desk/businesscard.txt", state)
    _, state = engine.evaluate("cd /root", state)

    out2, state = engine.evaluate("sh case_file.sh", state)
    beats2 = story.after_beats(
        state, 1, "sh case_file.sh", out2, state["resolved_command_log"][-1]
    )
    assert [b["id"] for b in beats2] == ["judge_pass"]


def test_after_beats_push_fail_before_case_checked() -> None:
    state = default_world_state()
    _, state = engine.evaluate("git add .", state)
    _, state = engine.evaluate('git commit -m "x"', state)
    out, state = engine.evaluate("git push", state)
    assert out == ["Error: mission requirements not met"]
    beats = story.after_beats(state, 1, "git push", out, None)
    assert [b["id"] for b in beats] == ["push_fail"]


def test_clear_beats_mission1_clear_then_mission2_start() -> None:
    state = default_world_state()
    state = _clear_mission1(state)
    assert state["mission_progress"]["active_mission_id"] == 2

    beats = story.clear_beats(state, 1)
    assert [b["id"] for b in beats] == ["clear", "start"]
    assert beats[0]["mission_id"] == 1
    assert beats[1]["mission_id"] == 2


def test_after_beats_survey_only_fires_when_remote() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = [1, 2]
    state["mission_progress"]["active_mission_id"] = 3

    # local のまま ls しても survey は当たらない
    out, state = engine.evaluate("ls", state)
    entry = state["resolved_command_log"][-1]
    beats = story.after_beats(state, 3, "ls", out, entry)
    assert beats == []

    _, state = engine.evaluate("ssh amusement_park", state)
    assert state["remote_mode"] is True

    out2, state = engine.evaluate("ls", state)
    entry2 = state["resolved_command_log"][-1]
    beats2 = story.after_beats(state, 3, "ls", out2, entry2)
    assert [b["id"] for b in beats2] == ["survey"]


def test_mission_separate_state_all_functions_return_empty() -> None:
    state = build_initial_state(1)
    assert story.start_beats(state) == []
    assert story.after_beats(state, 1, "cd desk", [], None) == []
    assert story.clear_beats(state, 1) == []


# --- WS 統合テスト（最小限） ---


def _token(client: TestClient) -> str:
    return client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]


def test_ws_hello_includes_mission1_start_beat(
    client: TestClient, session: Session
) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert [b["id"] for b in hello["story"]] == ["start"]
        assert hello["story"][0]["mission_id"] == 1


def test_ws_exec_sends_story_event_after_result(
    client: TestClient, session: Session
) -> None:
    create_user(session, "detective01", "secret")
    token = _token(client)
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()

        ws.send_json({"type": "exec", "id": 1, "command": "cd desk"})
        res = ws.receive_json()
        assert res["type"] == "result"

        story_evt = ws.receive_json()
        assert story_evt["type"] == "event"
        assert story_evt["name"] == "story"
        assert [b["id"] for b in story_evt["beats"]] == ["desk"]
