"""ls -l / chmod / mode 検査（読み取り・実行権限）のテスト。"""

import pytest

from app.evaluator import evaluate
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
