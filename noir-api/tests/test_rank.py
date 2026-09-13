"""探偵ランク（app/evaluator/rank.py + hello/result の rank + rank_up イベント）のテスト。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.evaluator import rank
from app.models import default_world_state
from tests.helpers import state_at_mission


def test_rank_starts_as_apprentice() -> None:
    # Mission1 は BASE_COMMANDS（ls/cd/cat/pwd/echo/git）だけ → Lv.1 見習い探偵
    assert rank.rank_of(default_world_state()) == {"level": 1, "name": "見習い探偵"}


def test_rank_is_max_level_of_released_commands() -> None:
    assert rank.rank_of(state_at_mission(2))["level"] == 4  # grep/find(3)・awk(4)
    assert rank.rank_of(state_at_mission(3))["level"] == 4  # ssh は表外 → 変わらない
    assert rank.rank_of(state_at_mission(4))["level"] == 5  # head/tail/wc
    assert rank.rank_of(state_at_mission(5))["level"] == 7  # chmod（Mission6 の ps=6 より先に 7）
    assert rank.rank_of(state_at_mission(6))["level"] == 7  # 下がらない
    assert rank.rank_of(state_at_mission(22))["level"] == 11


def test_rank_up_event_only_when_level_rises() -> None:
    event = rank.rank_up_event(state_at_mission(3), state_at_mission(4))
    assert event is not None
    assert event["name"] == "rank_up"
    assert (event["from_level"], event["level"]) == (4, 5)
    assert (event["from_rank_name"], event["rank_name"]) == ("分析官", "情報屋")
    assert set(event["unlocked"]) == {"head", "tail", "wc"}

    # Mission5→6: ps 等が解放されるが Level 6 < 7 なのでランクは変わらない（辞令なし）
    assert rank.rank_up_event(state_at_mission(5), state_at_mission(6)) is None
    # Mission2→3: ssh が解放されるが表外なので変わらない
    assert rank.rank_up_event(state_at_mission(2), state_at_mission(3)) is None


def test_ws_hello_and_result_carry_rank(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        hello = ws.receive_json()
        assert hello["state"]["rank"] == {"level": 1, "name": "見習い探偵"}
        ws.send_json({"type": "exec", "id": 1, "command": "pwd"})
        assert ws.receive_json()["state"]["rank"]["level"] == 1


def test_ws_mission1_clear_sends_rank_up_after_mission_clear(
    client: TestClient, session: Session
) -> None:
    """Mission1 → 2 で grep/find/awk 等が解放され Lv.1 → Lv.4 の辞令が出る。
    順序は result → mission_clear → rank_up → story（フロントの演出順に合わせる）。"""
    create_user(session, "detective01", "secret")
    token = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        for cmd in [
            "cat /root/desk/businesscard.txt",
            'echo "NAME: Sam Spade" > /root/desk/businesscard.txt',
            "sh case_file.sh",
        ]:
            ws.send_json({"type": "exec", "id": 1, "command": cmd})
            ws.receive_json()  # result
            ws.receive_json()  # story
        for cmd in ["git add .", 'git commit -m "solved"']:
            ws.send_json({"type": "exec", "id": 1, "command": cmd})
            ws.receive_json()
        ws.send_json({"type": "exec", "id": 1, "command": "git push"})
        result = ws.receive_json()
        assert result["state"]["rank"] == {"level": 4, "name": "分析官"}
        clear = ws.receive_json()
        assert clear["name"] == "mission_clear"
        rank_up = ws.receive_json()
        assert rank_up["name"] == "rank_up"
        assert (rank_up["from_level"], rank_up["level"]) == (1, 4)
        assert "grep" in rank_up["unlocked"]
        story = ws.receive_json()
        assert story["name"] == "story"
