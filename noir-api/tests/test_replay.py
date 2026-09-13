"""再捜査（クリア済み Mission の遊び直し）と隠し Mission の土台（app/evaluator/replay.py）。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.evaluator import evaluate, progress, replay, story
from tests.helpers import state_at_mission


def _run(s, line):
    return evaluate(line, s)


def test_replay_only_for_cleared_missions() -> None:
    s = state_at_mission(3)
    assert replay.can_replay(s, 1) and replay.can_replay(s, 2)
    assert not replay.can_replay(s, 3) and not replay.can_replay(s, 4)


def test_replay_resets_the_area_and_focuses_judge_story_and_logs() -> None:
    s = state_at_mission(3)
    # 初回プレイの痕跡: 名刺に名前が入っている・履歴に cat/echo がある
    _, s = _run(s, 'echo "NAME: Sam Spade" > /root/desk/businesscard.txt')
    _, s = _run(s, "cat /root/desk/businesscard.txt")
    replay.start(s, 1)
    assert s["replay"]["mission_id"] == 1 and s["current_path"] == "/root"
    assert progress.focused_mission_id(s) == 1
    # 区画は初期状態に戻る
    out, _ = _run(s, "cat /root/desk/businesscard.txt")
    assert out == ["NAME: ???", "ROLE: detective"]
    # case_file.sh は再捜査中の事件を名乗る
    out, _ = _run(s, "cat /root/case_file.sh")
    assert any("再捜査中の事件" in ln for ln in out)
    # 独り言は最初から
    assert [b["id"] for b in story.start_beats(s)] == ["start"]
    # 判定は再捜査開始以降のログだけを見る（開始前の cat/echo は数えない）
    out, s = _run(s, "sh case_file.sh")
    assert out == ["Warning: pattern mismatch"]
    _, s = _run(s, "cat /root/desk/businesscard.txt")
    _, s = _run(s, 'echo "NAME: Again" > /root/desk/businesscard.txt')
    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    assert len(s["command_log"]) > 4  # 本物のログは切り詰められていない


def test_replay_push_records_best_score_and_keeps_progress() -> None:
    s = state_at_mission(3)
    replay.start(s, 1)
    for cmd in ["cat /root/desk/businesscard.txt", 'echo "NAME: Again" > /root/desk/businesscard.txt', "sh case_file.sh", "git add .", 'git commit -m "again"']:
        _, s = _run(s, cmd)
    out, s = _run(s, "git push")
    assert out[0].startswith("Case reopened and closed again.")
    assert "replay" not in s
    assert progress.active_mission_id(s["mission_progress"]) == 3  # 本編は動かない
    rec = s["mission_progress"]["scores_replay"]["1"]
    assert rec["replay"] is True and rec["commands"] == 2 and "SMART" in rec["bonuses"]
    # 2 回目: 手数が多い → ベストは更新されない
    replay.start(s, 1)
    for cmd in ["ls", "ls", "ls", "ls", "cat /root/desk/businesscard.txt", 'echo "NAME: B" > /root/desk/businesscard.txt', "sh case_file.sh", "git add .", 'git commit -m "b"', "git push"]:
        _, s = _run(s, cmd)
    assert s["mission_progress"]["scores_replay"]["1"]["score"] == rec["score"]


def test_replay_reapplies_processes_and_services() -> None:
    s = state_at_mission(7)
    _, s = _run(s, "kill 923")  # 先に Mission7 の侵入者を消してしまう（本編）
    replay.start(s, 6)
    assert any(p["pid"] == 666 for p in s["processes"])  # Mission6 の盗聴器が復活
    _, s = _run(s, "cat /proc/666/cmdline")
    _, s = _run(s, "kill 666")
    out, s = _run(s, "sh case_file.sh")
    assert out == ["case_file.sh: all checks passed"]
    replay.stop(s)
    assert progress.focused_mission_id(s) == 7


def test_replay_of_mission29_uses_the_sandbox_and_restores() -> None:
    s = state_at_mission(12)
    replay.start(s, 29)
    assert s.get("sandbox")
    _, s = _run(s, "rm -rf /root/team_desk")
    assert _run(s, "ls /root/team_desk")[0] == ["Error: path not found"]
    replay.stop(s)
    assert "sandbox" not in s
    assert "case_notes.txt" in _run(s, "ls /root/team_desk")[0]
    assert _run(s, "rm -rf /root/desk")[0] == ["Error: command not allowed"]


def test_ws_focus_frame_starts_and_stops_replay(client: TestClient, session: Session) -> None:
    create_user(session, "detective01", "secret")
    token = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        # Mission1 はまだ未クリア → 再捜査できない
        ws.send_json({"type": "focus", "mission_id": 1})
        res = ws.receive_json()
        assert res["type"] == "focus" and res["error"] == "Error: mission is not replayable"
        # Mission1 をクリア
        for cmd, story_after in [
            ("cat /root/desk/businesscard.txt", True),
            ('echo "NAME: Sam Spade" > /root/desk/businesscard.txt', True),
            ("sh case_file.sh", True),
            ("git add .", False),
            ('git commit -m "solved"', False),
        ]:
            ws.send_json({"type": "exec", "id": 1, "command": cmd})
            ws.receive_json()
            if story_after:
                ws.receive_json()
        ws.send_json({"type": "exec", "id": 1, "command": "git push"})
        for _ in range(4):  # result, mission_clear, rank_up, story
            ws.receive_json()
        # 再捜査開始
        ws.send_json({"type": "focus", "mission_id": 1})
        res = ws.receive_json()
        assert res["error"] is None and res["state"]["replay_mission_id"] == 1
        assert [b["id"] for b in res["story"]] == ["start"]
        for cmd in ["cat /root/desk/businesscard.txt", 'echo "NAME: Again" > /root/desk/businesscard.txt', "sh case_file.sh", "git add .", 'git commit -m "again"']:
            ws.send_json({"type": "exec", "id": 2, "command": cmd})
            res = ws.receive_json()
            if cmd.startswith(("cat", "echo", "sh")):
                ws.receive_json()  # story（再捜査でも独り言が反応する）
        ws.send_json({"type": "exec", "id": 3, "command": "git push"})
        result = ws.receive_json()
        assert result["state"]["replay_mission_id"] is None
        clear = ws.receive_json()
        assert clear["name"] == "mission_clear" and clear["replay"] is True and clear["next_mission_id"] is None
        assert clear["score"]["replay"] is True
        story_ev = ws.receive_json()
        assert [b["id"] for b in story_ev["beats"]] == ["clear"]
        # 離脱（null）は冪等
        ws.send_json({"type": "focus", "mission_id": None})
        assert ws.receive_json()["state"]["replay_mission_id"] is None
