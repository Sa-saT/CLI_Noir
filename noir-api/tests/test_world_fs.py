"""`app/content/missions.py::_build_world_fs()` のテスト（Part5 P3-03）。

22 Mission分の初期FSを1つの永続統合ワールドへ合成する処理の検証。旧
`MissionDef.initial_filesystem` / `build_initial_state()`（Mission単位の旧フロー）が
一切変更されないこと、裸置きファイルの移設・vaultの加算マージ・ゲート初期状態・
/etc/hosts の ghost.example 行の非表示を確認する。
"""

import copy

from app.content.missions import (
    GHOST_HOSTS_LINE,
    MISSIONS,
    _build_world_fs,
    all_missions,
)
from app.ws.terminal import build_initial_state


def test_build_world_fs_is_independent_per_call() -> None:
    a = _build_world_fs()
    b = _build_world_fs()
    a["root"]["children"]["desk"]["children"]["hacked"] = {"type": "file", "content": "x"}
    assert "hacked" not in b["root"]["children"]["desk"]["children"]


def test_old_mission_flow_untouched_by_world_build() -> None:
    """世界FS構築後も Mission 単位の旧フローが従来どおり動くこと。"""
    _build_world_fs()
    s4 = build_initial_state(4)
    # 旧フローは裸置きのまま（移設されていない）。
    assert s4["filesystem"]["root"]["children"]["tape.log"]["type"] == "file"
    node = s4["filesystem"]["root"]["children"]["case_file.sh"]
    assert node["type"] == "file"


def test_case_file_sh_excluded_from_every_mission() -> None:
    world = _build_world_fs()

    def walk(node: dict, path: str) -> None:
        if node.get("type") != "dir":
            return
        children = node.get("children", {})
        assert "case_file.sh" not in children, f"case_file.sh leaked at {path}"
        for name, child in children.items():
            walk(child, f"{path}/{name}")

    for top_key, top_node in world.items():
        walk(top_node, f"/{top_key}")


def test_relocated_bare_files_land_in_subdirectories() -> None:
    world = _build_world_fs()
    root = world["root"]["children"]

    assert root["wiretap_room"]["children"]["tape.log"]["type"] == "file"
    assert root["evidence_locker"]["children"]["evidence.dat"]["type"] == "file"
    assert root["will_office"]["children"]["original.txt"]["type"] == "file"
    assert root["will_office"]["children"]["submitted.txt"]["type"] == "file"
    assert root["crontab_room"]["children"]["hint.txt"]["type"] == "file"
    assert root["informant_trail"]["children"]["journal.log"]["type"] == "file"
    assert root["precinct_desk"]["children"]["sample.sh"]["type"] == "file"
    assert root["precinct_desk"]["children"]["evidence.txt"]["type"] == "file"
    assert root["toolbox_room"]["children"]["hint.txt"]["type"] == "file"

    # 元の裸置き名は root 直下に残っていない。
    for leaked in ("tape.log", "evidence.dat", "original.txt", "submitted.txt"):
        assert leaked not in root


def test_vault_is_additively_merged_mission5_and_22() -> None:
    world = _build_world_fs()
    vault_children = world["root"]["children"]["vault"]["children"]
    assert "locked_evidence.txt" in vault_children  # Mission5
    assert "inner" in vault_children  # Mission5
    assert "locked.txt" in vault_children  # Mission22
    assert vault_children["locked.txt"]["content"] == "burner number traced to: 555-0199"


def test_mission20_fhs_dirs_merged_at_world_top_level() -> None:
    world = _build_world_fs()
    assert "etc" in world and "var" in world and "tmp" in world and "bin" in world
    assert "hosts" in world["etc"]["children"]
    assert "mr_black" in world["home"]["children"]


def test_ghost_hosts_line_hidden_until_mission12_unlock() -> None:
    world = _build_world_fs()
    hosts_content = world["etc"]["children"]["hosts"]["content"]
    assert GHOST_HOSTS_LINE not in hosts_content
    assert "127.0.0.1 localhost" in hosts_content


def test_mission1_desk_open_from_start_others_locked() -> None:
    world = _build_world_fs()
    desk = world["root"]["children"]["desk"]
    assert desk["mode"] == "rwxr-xr-x"
    assert desk["owner"] == "detective"

    park = world["root"]["children"]["park"]
    assert park["mode"] == "---------"
    assert park["owner"] == "system"

    mr_black = world["home"]["children"]["mr_black"]
    assert mr_black["mode"] == "---------"
    assert mr_black["owner"] == "system"


def test_public_fhs_dirs_and_home_and_root_always_open() -> None:
    world = _build_world_fs()
    for key in ("etc", "var", "tmp", "bin", "home", "root"):
        assert world[key]["mode"] == "rwxr-xr-x"
        assert world[key]["owner"] == "detective"


def test_every_owned_path_resolves_and_every_mission_dir_covered() -> None:
    """全 owned_paths が world 内に実在し、Mission が持つ root 直下ディレクトリが
    どれか1つの owned_paths に含まれる（無ゲートで放置された区画が無い）ことを確認する。
    """
    world = _build_world_fs()
    owned: set[str] = set()
    for mission in all_missions():
        for path in mission.owned_paths:
            segs = [p for p in path.split("/") if p]
            node = world
            for i, seg in enumerate(segs):
                node = node[seg] if i == 0 else node["children"][seg]
            assert node.get("mode") is not None
            owned.add(path)

    assert "/root/desk" in owned
    assert "/home/mr_black" in owned
    assert "/root/vault" in owned  # Mission5 側のみが所有（Mission22 は追加コンテンツのみ）


def test_default_state_untouched_snapshot() -> None:
    """default_state() 由来の Mission1 filesystem が世界FS構築の影響を受けないこと。"""
    before = copy.deepcopy(MISSIONS[1].initial_filesystem)
    _build_world_fs()
    _build_world_fs()
    assert MISSIONS[1].initial_filesystem == before
