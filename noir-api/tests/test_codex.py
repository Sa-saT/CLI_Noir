"""図鑑（道具 / エラー。ゲーム機能 2・10）: 登録・翻訳文・API・result フレームの codex。"""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import create_user
from app.content.codex import ERROR_ENTRIES, error_entry_for
from app.evaluator import codex, evaluate
from app.models import default_world_state


def test_error_entries_cover_design_doc_section_12() -> None:
    keys = {e["key"] for e in ERROR_ENTRIES}
    for msg in [
        "Error: command not allowed", "Error: invalid input", "Error: path not found",
        "Error: file not found", "Error: directory not found", "Error: directory already exists",
        "Error: invalid pattern", "Error: pattern mismatch", "Warning: pattern mismatch",
        "Host not found", "Permission denied", "Error: remote not connected",
        "Error: nothing to commit", "Error: commit message required",
        "Error: push not allowed before commit", "Error: mission requirements not met",
    ]:
        assert msg in keys, msg
    assert error_entry_for("Error: file not found")["title"] == "その名前のファイルは無い"
    assert error_entry_for("case_file.sh: all checks passed") is None


def test_register_commands_and_errors_once() -> None:
    s = default_world_state()
    out, s = evaluate("ls", s)
    new = codex.register(s, "ls", out, True)
    assert new == [{"kind": "command", "key": "ls"}]
    out, s = evaluate("cat nope.txt", s)
    new = codex.register(s, "cat nope.txt", out, False)
    assert [n["kind"] for n in new] == ["error"]
    assert new[0]["key"] == "Error: file not found"
    # 二度目は新規扱いにならず count だけ増える
    assert codex.register(s, "ls", ["desk"], True) == []
    assert s["codex"]["commands"]["ls"]["count"] == 2
    assert codex.register(s, "cat nope.txt", out, False) == []
    assert s["codex"]["errors"]["Error: file not found"]["count"] == 2


def test_register_counts_every_stage_of_a_pipeline() -> None:
    s = default_world_state()
    new = codex.register(s, "grep TEL x | sort | uniq -c", ["1 x"], True)
    assert [n["key"] for n in new] == ["grep", "sort", "uniq"]


def test_ws_result_carries_new_codex_entries_and_api_lists_them(
    client: TestClient, session: Session
) -> None:
    create_user(session, "detective01", "secret")
    token = client.post(
        "/api/auth/login/", json={"username": "detective01", "password": "secret"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/codex/", headers=headers).json()["commands"] == []
    with client.websocket_connect("/ws/terminal") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        ws.send_json({"type": "exec", "id": 1, "command": "cat nope.txt"})
        res = ws.receive_json()
        assert res["codex"][0]["kind"] == "error"
        assert res["codex"][0]["title"] == "その名前のファイルは無い"
        ws.send_json({"type": "exec", "id": 2, "command": "ls"})
        res = ws.receive_json()
        assert res["codex"] == [{"kind": "command", "key": "ls"}]
    data = client.get("/api/codex/", headers=headers).json()
    assert [c["name"] for c in data["commands"]] == ["ls"]
    assert data["errors"][0]["key"] == "Error: file not found"
    assert data["errors"][0]["text"]
