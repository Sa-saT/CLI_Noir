"""ls -l / chmod / mode 検査（読み取り・実行権限）のテスト。"""

import pytest

from app.content.missions import build_world_filesystem
from app.evaluator import evaluate
from app.evaluator import fs
from app.models import default_state


def _with_file(
    content: str = "secret",
    *,
    mode: str = "rw-r--r--",
    owner: str = "detective",
    immutable: bool = False,
    name: str = "note.txt",
) -> dict:
    s = default_state()
    s["filesystem"]["root"]["children"][name] = {
        "type": "file",
        "content": content,
        "mode": mode,
        "owner": owner,
        "mtime": "2026-01-01T00:00:00Z",
        "immutable": immutable,
    }
    return s


# --- ls -l ---
def test_ls_long_file() -> None:
    s = _with_file("hello")
    out, _ = evaluate("ls -l /root/note.txt", s)
    assert len(out) == 1
    line = out[0]
    assert line.startswith("-rw-r--r--")
    assert line.endswith("note.txt")
    assert " 5 " in line  # size = len("hello")


def test_ls_long_directory() -> None:
    s = _with_file()
    out, _ = evaluate("ls -l /root", s)
    assert len(out) == 1
    assert out[0].startswith("-rw-r--r--")
    assert out[0].endswith("note.txt")


def test_ls_long_dir_entry_shows_d_prefix() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["box"] = {"type": "dir", "children": {}}
    out, _ = evaluate("ls -l /root", s)
    assert out[0].startswith("d")
    assert out[0].endswith("box")


def test_ls_without_l_unaffected() -> None:
    s = _with_file()
    assert evaluate("ls /root", s)[0] == ["note.txt"]


# --- chmod ---
def test_chmod_symbolic_add_read_no_prefix_all_classes() -> None:
    s = _with_file(mode="---------")
    _, s2 = evaluate("chmod +r /root/note.txt", s)
    node = s2["filesystem"]["root"]["children"]["note.txt"]
    assert node["mode"] == "r--r--r--"


def test_chmod_symbolic_add_exec() -> None:
    s = _with_file(mode="rw-r--r--")
    _, s2 = evaluate("chmod +x /root/note.txt", s)
    assert s2["filesystem"]["root"]["children"]["note.txt"]["mode"] == "rwxr-xr-x"


def test_chmod_symbolic_remove() -> None:
    s = _with_file(mode="rwxrwxrwx")
    _, s2 = evaluate("chmod -w /root/note.txt", s)
    assert s2["filesystem"]["root"]["children"]["note.txt"]["mode"] == "r-xr-xr-x"


def test_chmod_numeric_644() -> None:
    s = _with_file(mode="rwxrwxrwx")
    _, s2 = evaluate("chmod 644 /root/note.txt", s)
    assert s2["filesystem"]["root"]["children"]["note.txt"]["mode"] == "rw-r--r--"


def test_chmod_numeric_755() -> None:
    s = _with_file(mode="rw-r--r--")
    _, s2 = evaluate("chmod 755 /root/note.txt", s)
    assert s2["filesystem"]["root"]["children"]["note.txt"]["mode"] == "rwxr-xr-x"


def test_chmod_invalid_spec() -> None:
    s = _with_file()
    out, new = evaluate("chmod zzz /root/note.txt", s)
    assert out == ["Error: invalid input"]
    new_env = {k: v for k, v in new["env_vars"].items() if k != "?"}
    old_env = {k: v for k, v in s["env_vars"].items() if k != "?"}
    assert {**new, "env_vars": new_env} == {**s, "env_vars": old_env}


def test_chmod_missing_path() -> None:
    s = _with_file()
    out, _ = evaluate("chmod +r /root/nope.txt", s)
    assert out == ["Error: path not found"]


def test_chmod_requires_path_argument() -> None:
    s = _with_file()
    out, _ = evaluate("chmod +r", s)
    assert out == ["Error: invalid input"]


# --- 読み取り権限検査（cat/grep/sort/uniq/wc/head/tail/cut 共通） ---
@pytest.fixture
def locked_state() -> dict:
    return _with_file("classified\ndata", mode="---------")


def test_cat_permission_denied(locked_state: dict) -> None:
    out, _ = evaluate("cat /root/note.txt", locked_state)
    assert out == ["Error: permission denied"]


def test_grep_permission_denied(locked_state: dict) -> None:
    out, _ = evaluate("grep classified /root/note.txt", locked_state)
    assert out == ["Error: permission denied"]


def test_wc_permission_denied(locked_state: dict) -> None:
    out, _ = evaluate("wc -l /root/note.txt", locked_state)
    assert out == ["Error: permission denied"]


def test_sort_permission_denied(locked_state: dict) -> None:
    out, _ = evaluate("sort /root/note.txt", locked_state)
    assert out == ["Error: permission denied"]


def test_chmod_unlocks_read() -> None:
    s = _with_file("classified", mode="---------")
    _, s2 = evaluate("chmod +r /root/note.txt", s)
    out, _ = evaluate("cat /root/note.txt", s2)
    assert out == ["classified"]


# --- 実行権限検査（sh） ---
def test_sh_permission_denied_without_exec_bit() -> None:
    s = _with_file("echo hi", mode="rw-r--r--", immutable=False, name="script.sh")
    out, _ = evaluate("sh /root/script.sh", s)
    assert out == ["Error: permission denied"]


def test_sh_immutable_default_bypasses_exec_check() -> None:
    # Mission1〜4 の case_file.sh は mode に x を持たないが immutable=True のため実行可。
    s = _with_file("# judge", mode="rw-r--r--", immutable=True, name="case_file.sh")
    out, _ = evaluate("sh /root/case_file.sh", s)
    # no checks configured (mission_id 未設定) だが permission denied にはならない。
    assert out != ["Error: permission denied"]


def test_sh_chmod_x_allows_execution() -> None:
    s = _with_file("echo hi", mode="rw-r--r--", immutable=False, name="script.sh")
    _, s2 = evaluate("chmod +x /root/script.sh", s)
    out, _ = evaluate("sh /root/script.sh", s2)
    assert out != ["Error: permission denied"]


# --- ディレクトリ権限ゲート（P3-04a） ---
# mode="---------" / owner="system" は未解放区画（app.content.missions の
# LOCKED_DIR_MODE/LOCKED_DIR_OWNER）を模す。mode 未設定は既存 22 Mission 分の
# ディレクトリノードそのままの状態（デフォルト開放）。


def _with_gated_dir(
    *,
    locked: bool,
    dir_name: str = "box",
    file_name: str = "secret.txt",
    file_content: str = "classified",
) -> dict:
    """/root/<dir_name> にディレクトリ権限ゲートを設定した state を作る（配下に1ファイル）。"""
    s = default_state()
    s["filesystem"]["root"]["children"][dir_name] = {
        "type": "dir",
        "children": {
            file_name: {
                "type": "file",
                "content": file_content,
                "mode": "rw-r--r--",
                "owner": "detective",
                "mtime": "2026-01-01T00:00:00Z",
                "immutable": False,
            },
        },
        "mode": "---------" if locked else "rwxr-xr-x",
        "owner": "system" if locked else "detective",
    }
    return s


def test_can_traverse_default_open_when_mode_unset() -> None:
    # 最重要の回帰保証: mode 未設定ディレクトリは常に通行可能（can_exec のデフォルト
    # 閉鎖とは別物）。既存 22 Mission 分のディレクトリノードは mode を持たない。
    node = {"type": "dir", "children": {}}
    assert fs.can_traverse(node) is True
    assert fs.can_traverse(node, "someone_else") is True


def test_can_traverse_non_dir_node_always_true() -> None:
    file_node = {"type": "file", "mode": "---------", "owner": "system"}
    assert fs.can_traverse(file_node) is True


def test_can_traverse_locked_dir_denies_owner_and_other() -> None:
    node = {"type": "dir", "children": {}, "mode": "---------", "owner": "system"}
    assert fs.can_traverse(node, "detective") is False
    assert fs.can_traverse(node, "system") is False


def test_can_traverse_open_dir_allows_owner_and_other() -> None:
    node = {"type": "dir", "children": {}, "mode": "rwxr-xr-x", "owner": "detective"}
    assert fs.can_traverse(node, "detective") is True
    assert fs.can_traverse(node, "other") is True


# 回帰: mode 未設定ディレクトリ（既存 22 Mission 分の区画）は従来どおり見える・入れる。
def test_regression_unset_mode_dir_visible_in_ls() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["box"] = {"type": "dir", "children": {}}
    out, _ = evaluate("ls /root", s)
    assert "box" in out


def test_regression_unset_mode_dir_enterable_by_cd() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["box"] = {"type": "dir", "children": {}}
    _, s2 = evaluate("cd /root/box", s)
    assert s2["current_path"] == "/root/box"


def test_regression_unset_mode_dir_found_by_find() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["box"] = {"type": "dir", "children": {}}
    out, _ = evaluate("find /root -name box", s)
    assert out == ["/root/box"]


def test_regression_unset_mode_dir_matches_glob() -> None:
    s = default_state()
    s["filesystem"]["root"]["children"]["box"] = {"type": "dir", "children": {}}
    out, _ = evaluate("ls /root/b*", s)
    assert out == []  # box は空ディレクトリなので中身は無いが、glob 自体は box に展開される


def test_regression_unset_mode_dir_readable_by_grep_r() -> None:
    s = _with_file("classified data")
    out, _ = evaluate("grep -r classified /root", s)
    assert out == ["/root/note.txt:classified data"]


# ゲートされたディレクトリ: ls の一覧から消える
def test_ls_hides_locked_directory_from_listing() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("ls /root", s)
    assert "box" not in out


def test_ls_shows_released_directory_in_listing() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("ls /root", s)
    assert "box" in out


# cd: Permission denied ではなく directory not found（見えない/触れない演出）
def test_cd_into_locked_directory_reports_not_found() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("cd /root/box", s)
    assert out == ["Error: directory not found"]


def test_cd_into_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    _, s2 = evaluate("cd /root/box", s)
    assert s2["current_path"] == "/root/box"


# find: 結果に出ない
def test_find_does_not_descend_into_locked_directory() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("find /root", s)
    assert "/root/box" not in out
    assert "/root/box/secret.txt" not in out


def test_find_descends_into_released_directory() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("find /root", s)
    assert "/root/box" in out
    assert "/root/box/secret.txt" in out


# glob: マッチしない（親ディレクトリ側からの候補列挙で除外される。ls/find と同じ
# 「子を fs.can_traverse でフィルタする」方式なので、ここでは box を名前ごと
# glob 候補から見えなくする観点で検証する）
def test_glob_does_not_expand_into_locked_directory() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("ls /root/b*", s)
    # box が候補から消えるためマッチ無し。bash の nullglob 無効と同じくリテラルの
    # まま渡り、実在しないパスとして扱われる。
    assert out == ["Error: path not found"]


def test_glob_expands_into_released_directory() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("ls /root/b*", s)
    assert out == ["secret.txt"]


# grep -r: 中を読まない
def test_grep_r_skips_locked_directory_contents() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("grep -r classified /root", s)
    assert out == []


def test_grep_r_reads_released_directory_contents() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("grep -r classified /root", s)
    assert out == ["/root/box/secret.txt:classified"]


# 絶対パス直指定でも見えない・触れない（get_node が None を返すため）
def test_cat_file_inside_locked_directory_reports_file_not_found() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("cat /root/box/secret.txt", s)
    assert out == ["Error: file not found"]


# --- ロック済みディレクトリを引数で直接名指ししたケース ---
# fs._walk はループ後に解決済みノード自身の can_traverse も検査する（親経由の子フィルタ
# だけでは「/root/box を直接指定」する経路が塞がらないため）。これにより get_parent 経由の
# touch/mkdir/ln/リダイレクトもまとめてゲートされる。


def test_ls_direct_target_locked_directory_not_found() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("ls /root/box", s)
    assert out == ["Error: path not found"]


def test_ls_long_direct_target_locked_directory_not_found() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("ls -l /root/box", s)
    assert out == ["Error: path not found"]


def test_ls_direct_target_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("ls /root/box", s)
    assert out == ["secret.txt"]


def test_find_direct_target_locked_directory_not_found() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("find /root/box", s)
    assert out == ["Error: path not found"]


def test_find_direct_target_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("find /root/box", s)
    assert out == ["/root/box", "/root/box/secret.txt"]


def test_grep_r_direct_target_locked_directory_reads_nothing() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("grep -r classified /root/box", s)
    assert out == []


def test_grep_r_direct_target_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, _ = evaluate("grep -r classified /root/box", s)
    assert out == ["/root/box/secret.txt:classified"]


def test_touch_inside_locked_directory_fails() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("touch /root/box/new.txt", s)
    assert out == ["Error: path not found"]


def test_touch_inside_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, s2 = evaluate("touch /root/box/new.txt", s)
    assert out == []
    assert "new.txt" in s2["filesystem"]["root"]["children"]["box"]["children"]


def test_mkdir_inside_locked_directory_fails() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("mkdir /root/box/new_dir", s)
    assert out == ["Error: path not found"]


def test_mkdir_inside_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, s2 = evaluate("mkdir /root/box/new_dir", s)
    assert out == []
    assert "new_dir" in s2["filesystem"]["root"]["children"]["box"]["children"]


def test_ln_inside_locked_directory_fails() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("ln -s /root/box/secret.txt /root/box/link.txt", s)
    assert out == ["Error: path not found"]


def test_ln_inside_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, s2 = evaluate("ln -s /root/box/secret.txt /root/box/link.txt", s)
    assert out == []
    assert "link.txt" in s2["filesystem"]["root"]["children"]["box"]["children"]


def test_redirect_into_locked_directory_fails() -> None:
    s = _with_gated_dir(locked=True)
    out, _ = evaluate("echo x > /root/box/new.txt", s)
    assert out == ["Error: path not found"]


def test_redirect_into_released_directory_succeeds() -> None:
    s = _with_gated_dir(locked=False)
    out, s2 = evaluate("echo x > /root/box/new.txt", s)
    assert out == []
    assert "new.txt" in s2["filesystem"]["root"]["children"]["box"]["children"]


# --- 統合ワールド（Part5 P3-03）レベルの確認 ---
def test_world_mission1_area_enterable() -> None:
    s = default_state()
    s["filesystem"] = build_world_filesystem()
    _, s2 = evaluate("cd /root/desk", s)
    assert s2["current_path"] == "/root/desk"


def test_world_unreleased_mission_area_not_enterable() -> None:
    s = default_state()
    s["filesystem"] = build_world_filesystem()
    out, _ = evaluate("cd /root/park", s)  # Mission2 の区画。初期状態では未解放。
    assert out == ["Error: directory not found"]
    out2, _ = evaluate("ls /root", s)
    assert "park" not in out2


def test_world_unreleased_mission_area_direct_target_not_readable_or_writable() -> None:
    # /root/park を cd ではなく直接名指ししても中身は見えず、書き込みもできない。
    s = default_state()
    s["filesystem"] = build_world_filesystem()
    assert evaluate("ls /root/park", s)[0] == ["Error: path not found"]
    assert evaluate("find /root/park", s)[0] == ["Error: path not found"]
    assert evaluate("touch /root/park/x.txt", s)[0] == ["Error: path not found"]
