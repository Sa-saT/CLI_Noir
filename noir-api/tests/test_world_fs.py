"""永続統合ワールドの仮想FS（Part5 / P3-03）。

`app.content.missions._build_world_fs()` が 22 Mission 分の区画を 1 つの世界へ
統合できているか、移設漏れ・意図しない衝突・権限ゲートの初期値を検証する。
"""

import re

import pytest

from app.content.missions import (
    CASE_FILE_NAME,
    GHOST_HOSTS_LINE,
    LOCKED_DIR_MODE,
    LOCKED_DIR_OWNER,
    OPEN_DIR_MODE,
    OPEN_DIR_OWNER,
    _MISSION_AREAS,
    _merge_children,
    _RELOCATIONS,
    build_world_filesystem,
    mission_area_paths,
)
from app.models.tables import default_world_state


def node_at(world: dict, abs_path: str) -> dict | None:
    node: dict | None = {"type": "dir", "children": world}
    for seg in [s for s in abs_path.split("/") if s]:
        if node is None or node.get("type") != "dir":
            return None
        node = node.get("children", {}).get(seg)
    return node


def walk(world: dict, base: str = ""):
    """(絶対パス, ノード) を全件返す。"""
    stack = [(base, world)]
    while stack:
        prefix, children = stack.pop()
        for name, node in children.items():
            path = f"{prefix}/{name}"
            yield path, node
            if node.get("type") == "dir":
                stack.append((path, node.get("children", {})))


@pytest.fixture()
def world() -> dict:
    return build_world_filesystem()


# --- 統合の基本規則 ---------------------------------------------------------


def test_case_file_is_excluded_everywhere(world: dict) -> None:
    # 判定スクリプトはアクティブ Mission から動的生成する（P3-04）ため静的配置しない。
    assert [path for path, _ in walk(world) if path.endswith(f"/{CASE_FILE_NAME}")] == []


def test_no_bare_files_directly_under_root(world: dict) -> None:
    # ディレクトリ権限ゲートは dir 単位でしか効かないため、裸置きファイルがあると
    # その Mission の証拠が最初から丸見えになる。
    root_children = node_at(world, "/root")["children"]
    bare = [name for name, node in root_children.items() if node.get("type") != "dir"]
    assert bare == []


@pytest.mark.parametrize(
    ("mission_id", "filename", "room"),
    [
        (mission_id, filename, room)
        for mission_id, moves in _RELOCATIONS.items()
        for filename, room in moves.items()
    ],
)
def test_relocated_files_moved_out_of_root(
    world: dict, mission_id: int, filename: str, room: str
) -> None:
    assert node_at(world, f"/root/{room}/{filename}") is not None
    assert node_at(world, f"/root/{filename}") is None


def test_every_mission_area_is_reachable_and_populated(world: dict) -> None:
    for mission_id in _MISSION_AREAS:
        for path in mission_area_paths(mission_id):
            node = node_at(world, path)
            assert node is not None, path
            assert node["type"] == "dir", path
            assert node["children"], f"{path} is empty"


@pytest.mark.parametrize(
    "path",
    [
        "/root/desk/businesscard.txt",
        "/root/park/swing/catinfo.txt",
        "/root/wiretap_room/tape.log",
        "/root/bar/back/ledger.txt",
        "/root/evidence_locker/evidence.dat",
        "/root/will_office/original.txt",
        "/root/will_office/submitted.txt",
        "/root/scraps/pieces.txt",
        "/root/crontab_room/hint.txt",
        "/root/mirror_hall/vault/real_deed.txt",
        "/root/informant_trail/journal.log",
        "/root/warehouse/top secret.txt",
        "/root/contracts/copy_4.txt",
        "/root/archive/witness_note.txt",
        "/root/precinct_desk/sample.sh",
        "/root/toolbox_room/hint.txt",
        "/root/clues/deep/access.key",
        "/root/clues/evidence.tar",
        "/root/clues/ledger.txt",
        "/root/logs/calls.log",
        "/etc/passwd",
        "/var/log/entry.log",
        "/tmp/.forgotten",
        "/home/mr_black/registration.txt",
    ],
)
def test_landmark_files_exist(world: dict, path: str) -> None:
    assert node_at(world, path) is not None


# --- vault の相乗り（Mission5 + Mission22）----------------------------------


def test_vault_is_additively_merged(world: dict) -> None:
    vault = node_at(world, "/root/vault")["children"]
    # Mission5 の持ち物
    assert "locked_evidence.txt" in vault
    assert "inner" in vault
    # Mission22 の持ち物（同じ場所へのコールバック）
    assert "locked.txt" in vault


def test_nested_vault_is_not_confused_with_root_vault(world: dict) -> None:
    # 相乗り許可は絶対パスで持つため、Mission14 の /root/mirror_hall/vault は無関係。
    mirror_vault = node_at(world, "/root/mirror_hall/vault")["children"]
    assert set(mirror_vault) == {"real_deed.txt"}


def test_unexpected_conflict_raises() -> None:
    dest = {"warehouse": {"type": "dir", "children": {}}}
    src = {"warehouse": {"type": "dir", "children": {}}}
    with pytest.raises(ValueError, match="world FS conflict"):
        _merge_children(dest, src, 16, "/root")


# --- ディレクトリ権限ゲートの初期値 -----------------------------------------


def test_mission1_area_is_open_at_start(world: dict) -> None:
    desk = node_at(world, "/root/desk")
    assert desk["mode"] == OPEN_DIR_MODE
    assert desk["owner"] == OPEN_DIR_OWNER


def test_other_mission_areas_are_locked_at_start(world: dict) -> None:
    for mission_id, paths in _MISSION_AREAS.items():
        if mission_id == 1:
            continue
        for path in paths:
            node = node_at(world, path)
            assert node["mode"] == LOCKED_DIR_MODE, path
            assert node["owner"] == LOCKED_DIR_OWNER, path


@pytest.mark.parametrize("path", ["/root", "/etc", "/var", "/tmp", "/bin", "/home"])
def test_infrastructure_dirs_are_always_open(world: dict, path: str) -> None:
    node = node_at(world, path)
    assert node["mode"] == OPEN_DIR_MODE
    assert node["owner"] == OPEN_DIR_OWNER


# --- Mission12 の発見体験を潰さない ------------------------------------------


def test_hosts_hides_ghost_example_until_mission12(world: dict) -> None:
    hosts = node_at(world, "/etc/hosts")
    assert "127.0.0.1 localhost" in hosts["content"]
    assert GHOST_HOSTS_LINE not in hosts["content"]
    assert "ghost.example" not in hosts["content"]


# --- 移設漏れ検出（本文・リンク先が指すパスが実在するか）---------------------


_ROOT_PATH_RE = re.compile(r"/root(?:/[A-Za-z0-9_.\-]+)*")


def test_referenced_root_paths_exist_in_the_world(world: dict) -> None:
    """世界の中の文章・symlink が指す `/root/...` が実在することを確かめる。

    移設（_RELOCATIONS）で置き去りになった参照を機械的に検出するための番犬。
    """
    missing: list[tuple[str, str]] = []
    for path, node in walk(world):
        texts = []
        if node.get("type") == "file":
            texts.append(node.get("content", ""))
        elif node.get("type") == "link":
            texts.append(node.get("target", ""))
        for text in texts:
            for referenced in _ROOT_PATH_RE.findall(text):
                referenced = referenced.rstrip(".")
                if node_at(world, referenced) is None:
                    missing.append((path, referenced))
    assert missing == []


# --- 呼び出し側との結線 ------------------------------------------------------


def test_build_returns_independent_copies() -> None:
    first = build_world_filesystem()
    first["root"]["children"]["desk"]["children"].clear()
    assert build_world_filesystem()["root"]["children"]["desk"]["children"]


def test_default_world_state_uses_the_world_fs() -> None:
    assert default_world_state()["filesystem"] == build_world_filesystem()
