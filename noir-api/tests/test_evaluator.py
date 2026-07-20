"""evaluator コア（denylist/allowlist・MVP コマンド・リダイレクト・ssh）のテスト。"""

import pytest

from app.evaluator import evaluate
from app.models import default_state


def _without_exit_status(s: dict) -> dict:
    """env_vars["?"]（P2-15 の $? 記録）を除いた state を返す（不変性比較用）。"""
    s2 = dict(s)
    s2["env_vars"] = {k: v for k, v in s["env_vars"].items() if k != "?"}
    return s2


@pytest.fixture
def state() -> dict:
    s = default_state()
    # /root/desk/businesscard.txt を用意
    s["filesystem"]["root"]["children"]["desk"] = {
        "type": "dir",
        "children": {
            "businesscard.txt": {
                "type": "file",
                "content": "NAME: ???\nROLE: detective",
                "mode": "rw-r--r--",
                "owner": "detective",
                "mtime": "2026-01-01T00:00:00Z",
                "immutable": True,
            }
        },
    }
    return s


def test_denylist_rejected(state: dict) -> None:
    out, new = evaluate("rm -rf /", state)
    assert out == ["Error: command not allowed"]
    assert _without_exit_status(new) == _without_exit_status(state)
    assert new["env_vars"]["?"] == "1"


def test_unknown_command_rejected(state: dict) -> None:
    out, _ = evaluate("frobnicate x", state)
    assert out == ["Error: command not allowed"]


def test_ls_and_cd_and_pwd(state: dict) -> None:
    out, _ = evaluate("ls", state)
    assert out == ["desk"]

    out, s2 = evaluate("cd desk", state)
    assert s2["current_path"] == "/root/desk"

    out, _ = evaluate("pwd", s2)
    assert out == ["/root/desk"]

    out, _ = evaluate("ls /root/desk", state)
    assert out == ["businesscard.txt"]


def test_cd_into_missing_dir(state: dict) -> None:
    out, new = evaluate("cd nope", state)
    assert out == ["Error: directory not found"]
    assert _without_exit_status(new) == _without_exit_status(state)  # state 不変


def test_cat_file_and_missing(state: dict) -> None:
    out, _ = evaluate("cat /root/desk/businesscard.txt", state)
    assert out == ["NAME: ???", "ROLE: detective"]

    out, _ = evaluate("cat /root/desk/nope.txt", state)
    assert out == ["Error: file not found"]


def test_mkdir_touch_and_duplicate(state: dict) -> None:
    _, s2 = evaluate("mkdir /root/box", state)
    assert s2["filesystem"]["root"]["children"]["box"]["type"] == "dir"

    out, _ = evaluate("mkdir /root/box", s2)
    assert out == ["Error: directory already exists"]

    _, s3 = evaluate("touch /root/box/note.txt", s2)
    assert "note.txt" in s3["filesystem"]["root"]["children"]["box"]["children"]


def test_echo_redirect_write_and_append(state: dict) -> None:
    _, s2 = evaluate('echo "NAME: Sam" > /root/desk/businesscard.txt', state)
    node = s2["filesystem"]["root"]["children"]["desk"]["children"]["businesscard.txt"]
    assert node["content"] == "NAME: Sam"

    _, s3 = evaluate('echo "ROLE: PI" >> /root/desk/businesscard.txt', s2)
    node3 = s3["filesystem"]["root"]["children"]["desk"]["children"]["businesscard.txt"]
    assert node3["content"] == "NAME: Sam\nROLE: PI"

    # リダイレクト時は標準出力に何も出さない
    out, _ = evaluate("echo hi > /root/desk/x.txt", state)
    assert out == []


def test_echo_plain(state: dict) -> None:
    out, _ = evaluate("echo hello world", state)
    assert out == ["hello world"]


def test_grep_on_file(state: dict) -> None:
    out, _ = evaluate("grep NAME /root/desk/businesscard.txt", state)
    assert out == ["NAME: ???"]

    out, _ = evaluate("grep ZZZ /root/desk/businesscard.txt", state)
    assert out == []  # 有効な正規表現・マッチなし

    out, _ = evaluate("grep '(' /root/desk/businesscard.txt", state)
    assert out == ["Error: invalid pattern"]  # 不正な正規表現


def test_egrep_warning(state: dict) -> None:
    out, _ = evaluate("egrep ROLE /root/desk/businesscard.txt", state)
    assert out[0] == "egrep: warning: egrep is obsolescent; using grep -E"
    assert "ROLE: detective" in out


def test_find_name(state: dict) -> None:
    out, _ = evaluate("find /root -name businesscard.txt", state)
    assert out == ["/root/desk/businesscard.txt"]


def test_ssh_and_exit_swaps_filesystem(state: dict) -> None:
    out, s2 = evaluate("ssh amusement_park", state)
    assert out == ["Connected to amusement_park"]
    assert s2["remote_mode"] is True
    assert s2["ssh_host"] == "amusement_park"
    assert s2["current_path"] == "/gate"
    # remote では local の desk は見えない
    ls_out, _ = evaluate("ls /", s2)
    assert ls_out == ["gate"]

    _, s3 = evaluate("exit", s2)
    assert s3["remote_mode"] is False
    assert s3["ssh_host"] is None
    assert s3["current_path"] == "/root"
    assert "desk" in s3["filesystem"]["root"]["children"]


def test_ssh_unknown_host(state: dict) -> None:
    out, new = evaluate("ssh nope", state)
    assert out == ["Host not found"]
    assert _without_exit_status(new) == _without_exit_status(state)


# --- パイプ ---
def test_pipe_echo_into_grep(state: dict) -> None:
    out, _ = evaluate("echo hello world | grep hello", state)
    assert out == ["hello world"]

    out, _ = evaluate("echo hello world | grep zzz", state)
    assert out == []


def test_pipe_cat_into_grep(state: dict) -> None:
    out, _ = evaluate("cat /root/desk/businesscard.txt | grep ROLE", state)
    assert out == ["ROLE: detective"]


def test_pipe_chain_three_stages(state: dict) -> None:
    # grep で2行 → 2段目 grep で絞り込み
    out, _ = evaluate("cat /root/desk/businesscard.txt | grep ':' | grep NAME", state)
    assert out == ["NAME: ???"]


def test_pipe_then_redirect(state: dict) -> None:
    _, s2 = evaluate(
        "cat /root/desk/businesscard.txt | grep NAME > /root/desk/out.txt", state
    )
    node = s2["filesystem"]["root"]["children"]["desk"]["children"]["out.txt"]
    assert node["content"] == "NAME: ???"


def test_pipe_stage_error_propagates(state: dict) -> None:
    out, new = evaluate("cat /root/desk/nope.txt | grep x", state)
    assert out == ["Error: file not found"]
    assert _without_exit_status(new) == _without_exit_status(state)


def test_pipe_denylist_in_stage(state: dict) -> None:
    out, new = evaluate("echo x | rm -rf /", state)
    assert out == ["Error: command not allowed"]
    assert _without_exit_status(new) == _without_exit_status(state)


def test_pipe_empty_stage_invalid(state: dict) -> None:
    assert evaluate("| grep x", state)[0] == ["Error: invalid input"]
    assert evaluate("echo x |", state)[0] == ["Error: invalid input"]
    assert evaluate("echo x | | grep y", state)[0] == ["Error: invalid input"]
