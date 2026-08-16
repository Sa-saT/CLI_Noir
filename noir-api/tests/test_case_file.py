"""統合ワールドの動的 case_file.sh（Part5, P3-04b）。

`/root/case_file.sh` はワールドの filesystem には保存せず、読み取り時に
`mission_progress` のアクティブ Mission から合成する（疑似 /proc と同じ方式）。
Mission 別 state（filesystem に静的な case_file.sh を持つ・mission_progress を
持たない）との共存が壊れていないかも合わせて検証する。
"""

import copy

import pytest

from app.content.missions import CASE_FILE_NAME, MISSIONS, all_missions, get_mission
from app.evaluator import engine, fs
from app.evaluator.commands import cmd_cat, cmd_ls, cmd_sh
from app.evaluator.errors import CommandError
from app.models.tables import default_state, default_world_state


def _mission1_state() -> dict:
    """Mission 別 state（回帰テスト用）。静的な case_file.sh を持つ。"""
    state = default_state()
    state["mission_id"] = 1
    state["filesystem"] = copy.deepcopy(get_mission(1).initial_filesystem)
    return state


# --- 統合ワールド state：動的合成 --------------------------------------------


def test_world_case_file_readable_via_cat() -> None:
    state = default_world_state()
    out, _ = cmd_cat(state, ["cat", "/root/case_file.sh"], [])
    text = "\n".join(out)
    mission1 = get_mission(1)
    assert mission1.title_ja in text
    assert mission1.description in text


def test_world_case_file_not_persisted_in_filesystem() -> None:
    state = default_world_state()
    cmd_cat(state, ["cat", "/root/case_file.sh"], [])
    assert "case_file.sh" not in state["filesystem"]["root"]["children"]


def test_ls_root_lists_case_file() -> None:
    state = default_world_state()
    state["current_path"] = "/root"
    out, _ = cmd_ls(state, ["ls"], [])
    assert "case_file.sh" in out


def test_case_file_tracks_active_mission_change() -> None:
    state = default_world_state()
    out1, _ = cmd_cat(state, ["cat", "/root/case_file.sh"], [])
    assert get_mission(1).title_ja in "\n".join(out1)

    # Mission1 をクリア済みにし、キャッシュを更新（P3-05 の advance_mission 相当を
    # 手で行う。ここでは進捗の書き込み自体はテスト対象ではない）。
    state["mission_progress"]["completed"] = [1]
    state["mission_progress"]["active_mission_id"] = 2

    out2, _ = cmd_cat(state, ["cat", "/root/case_file.sh"], [])
    text2 = "\n".join(out2)
    assert get_mission(2).title_ja in text2
    assert get_mission(1).title_ja not in text2


def test_case_file_absent_when_all_missions_cleared() -> None:
    state = default_world_state()
    state["mission_progress"]["completed"] = [m.id for m in all_missions()]
    state["mission_progress"]["active_mission_id"] = None

    node = fs.get_node(state, "/root/case_file.sh")
    assert node is None

    state["current_path"] = "/root"
    out, _ = cmd_ls(state, ["ls"], [])
    assert "case_file.sh" not in out


def test_sh_case_file_reaches_judge_for_active_mission() -> None:
    state = default_world_state()
    state["current_path"] = "/root"
    # Mission1 の判定パターンに一致するログを直接投入する（engine.evaluate は
    # env_vars のユーザー別スキーマ化 [P3-10 カットオーバー対象] が未対応で
    # PATH 解決が通らないため、ここでは cmd_sh を直接呼び判定到達のみ検証する）。
    state["command_log"] = [
        "cat /root/desk/businesscard.txt",
        "echo NAME: Sam Spade > /root/desk/businesscard.txt",
    ]
    out, new_state = cmd_sh(state, ["sh", "case_file.sh"], [])
    assert out == ["case_file.sh: all checks passed"]
    # 統合ワールド state では mission_flags ではなく mission_progress.flags に
    # 書き込まれる（progress.flags 経由。P3-05）。
    assert new_state["mission_progress"]["flags"]["case_checked"] is True


def test_sh_case_file_pattern_mismatch_for_active_mission() -> None:
    state = default_world_state()
    state["current_path"] = "/root"
    state["command_log"] = ["pwd"]
    out, new_state = cmd_sh(state, ["sh", "case_file.sh"], [])
    assert out == ["Warning: pattern mismatch"]
    assert new_state["mission_progress"]["flags"]["case_checked"] is False


# --- Mission 別 state：回帰（従来どおり静的ファイルが使われる） ------------------


def test_mission_state_uses_static_case_file_not_synthesized() -> None:
    state = _mission1_state()
    node = fs.get_node(state, "/root/case_file.sh")
    assert node is not None
    assert node["content"] == "# 事件ファイル: sh case_file.sh で判定する\n"


def test_mission_state_ls_root_lists_case_file_once() -> None:
    state = _mission1_state()
    state["current_path"] = "/root"
    out, _ = cmd_ls(state, ["ls"], [])
    assert out.count("case_file.sh") == 1


def test_mission_state_sh_case_file_still_works() -> None:
    state = _mission1_state()
    state["current_path"] = "/root"
    state["command_log"] = [
        "cat /root/desk/businesscard.txt",
        "echo NAME: Sam Spade > /root/desk/businesscard.txt",
    ]
    out, new_state = cmd_sh(state, ["sh", "case_file.sh"], [])
    assert out == ["case_file.sh: all checks passed"]
    assert new_state["mission_flags"]["case_checked"] is True


def test_world_case_file_rejects_redirect_write() -> None:
    """合成 case_file.sh への書き込みは黙って消えず Permission denied になる。"""
    state = default_world_state()
    with pytest.raises(CommandError, match="Permission denied"):
        engine._write_file(state, "/root/case_file.sh", ["tampered"], False)
    # filesystem に実体が生えていないこと（合成のまま）。
    assert CASE_FILE_NAME not in state["filesystem"]["root"]["children"]


def test_mission_state_case_file_write_is_unaffected() -> None:
    """Mission 別 state の静的 case_file.sh は従来どおり書き込める（回帰）。"""
    state = default_state()
    state["filesystem"] = copy.deepcopy(MISSIONS[1].initial_filesystem)
    engine._write_file(state, "/root/case_file.sh", ["rewritten"], False)
    assert (
        state["filesystem"]["root"]["children"][CASE_FILE_NAME]["content"] == "rewritten"
    )
