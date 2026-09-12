"""UX-01a: 実 bash に不自然な差分を残さないための修正5点のテスト。

対象:
  1. `>file` / `>>file`（空白無し）のリダイレクト
  2. `&&` / `||` / `;` を黙って無視しない（invalid input）
  3. チルダ展開（`~` / `~/...`。`~user` は非対応）
  4. `cd -`（OLDPWD へ移動・移動先を1行表示）
  5. `history`（command_log を bash 書式で表示。Mission15 は informant_history 優先）

default_state()（Mission 別 state）・default_world_state()（統合ワールド state）の
両方の state 形状で主要ケースが通ることを確認する（P3-04c で env_for() が両形状を
吸収する設計のため、取りこぼしが無いか両方で見る）。
"""

import pytest

from app.evaluator import evaluate
from app.models.tables import default_state, default_world_state
from app.ws.terminal import build_initial_state


def _without_exit_status(s: dict) -> dict:
    """env_vars["?"]（$? 記録）を除いた env_vars を返す（不変性比較の補助）。"""
    env = s["env_vars"]
    if any(isinstance(v, dict) for v in env.values()):
        user = s.get("current_user", "detective")
        bucket = {k: v for k, v in env.get(user, {}).items() if k != "?"}
        return {**env, user: bucket}
    return {k: v for k, v in env.items() if k != "?"}


@pytest.fixture
def state() -> dict:
    """default_state() + /root/desk/businesscard.txt（test_evaluator.py と同じ配置）。"""
    s = default_state()
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


@pytest.fixture
def world_state() -> dict:
    """default_world_state()。Mission1 区画（/root/desk）は最初から解放済み。"""
    return default_world_state()


# --- 1. `>file` / `>>file`（空白無し） ---


def test_glued_redirect_write_and_append(state: dict) -> None:
    _, s2 = evaluate("echo hi >x.txt", state)
    node = s2["filesystem"]["root"]["children"]["x.txt"]
    assert node["content"] == "hi"
    out, _ = evaluate("cat x.txt", s2)
    assert out == ["hi"]

    _, s3 = evaluate("echo bye >>x.txt", s2)
    node3 = s3["filesystem"]["root"]["children"]["x.txt"]
    assert node3["content"] == "hi\nbye"


def test_glued_redirect_write_and_append_world(world_state: dict) -> None:
    _, s2 = evaluate("cd /root/desk", world_state)
    _, s3 = evaluate("echo hi >x.txt", s2)
    node = s3["filesystem"]["root"]["children"]["desk"]["children"]["x.txt"]
    assert node["content"] == "hi"

    _, s4 = evaluate("echo bye >>x.txt", s3)
    node2 = s4["filesystem"]["root"]["children"]["desk"]["children"]["x.txt"]
    assert node2["content"] == "hi\nbye"


def test_glued_stderr_redirect_not_broken() -> None:
    # 既存の Mission18 挙動（`2>/dev/null` 空白無し）が壊れていないことの確認。
    s = build_initial_state(18)
    out, _ = evaluate('grep -r "witness" /root/archive 2>/dev/null', s)
    joined = "\n".join(out)
    assert "witness report" in joined
    assert "permission denied" not in joined


# --- 2. `&&` / `||` / `;` を黙って無視しない ---


def test_double_ampersand_rejected_and_cd_not_applied(state: dict) -> None:
    out, new = evaluate("cd desk && pwd", state)
    assert out == ["Error: invalid input"]
    # 最重要: cd だけ黙って実行してしまわないこと（current_path 不変）。
    assert new["current_path"] == state["current_path"]
    assert new["env_vars"]["?"] == "1"


def test_double_ampersand_rejected_world(world_state: dict) -> None:
    out, new = evaluate("cd /root/desk && pwd", world_state)
    assert out == ["Error: invalid input"]
    assert new["current_path"] == world_state["current_path"]


def test_semicolon_glued_rejected(state: dict) -> None:
    out, new = evaluate("pwd; ls", state)
    assert out == ["Error: invalid input"]
    assert new["env_vars"]["?"] == "1"


def test_or_operator_rejected(state: dict) -> None:
    out, new = evaluate("ls || pwd", state)
    assert out == ["Error: invalid input"]
    assert new["env_vars"]["?"] == "1"


def test_quoted_operator_is_plain_text(state: dict) -> None:
    # 引用符の中の `;` `&&` は演算子ではなく文字列（`sed 's/x/y/;'` 等を壊さない）。
    out, new = evaluate('echo "a; b && c"', state)
    assert out == ["a; b && c"]
    assert new["env_vars"]["?"] == "0"


# --- 3. チルダ展開 ---


def test_tilde_expansion(state: dict) -> None:
    out, s2 = evaluate("cd ~", state)
    assert out == []
    assert s2["current_path"] == "/root"

    out, _ = evaluate("echo ~", state)
    assert out == ["/root"]

    # シングルクォートは展開しない。
    out, _ = evaluate("echo '~'", state)
    assert out == ["~"]

    # `~user` 形式は非対応（展開しない）。
    out, _ = evaluate("echo ~foo", state)
    assert out == ["~foo"]

    out, _ = evaluate("cat ~/desk/businesscard.txt", state)
    assert out == ["NAME: ???", "ROLE: detective"]


def test_tilde_expansion_world(world_state: dict) -> None:
    out, s2 = evaluate("cd ~", world_state)
    assert out == []
    assert s2["current_path"] == "/root"

    out, _ = evaluate("echo ~", world_state)
    assert out == ["/root"]

    out, _ = evaluate("cat ~/desk/businesscard.txt", world_state)
    assert out[0].startswith("NAME:")


def test_ssh_cd_tilde_returns_to_login_dir() -> None:
    s = build_initial_state(3)
    _, s = evaluate("ssh amusement_park", s)
    _, s = evaluate("cd booth", s)
    assert s["current_path"] == "/gate/booth"

    out, s = evaluate("cd ~", s)
    assert out == []
    assert s["current_path"] == "/gate"


# --- 4. `cd -` ---


def test_cd_dash_round_trip(state: dict) -> None:
    _, s2 = evaluate("cd desk", state)
    out, s3 = evaluate("cd -", s2)
    assert out == ["/root"]
    assert s3["current_path"] == "/root"

    out, s4 = evaluate("cd -", s3)
    assert out == ["/root/desk"]
    assert s4["current_path"] == "/root/desk"


def test_cd_dash_round_trip_world(world_state: dict) -> None:
    _, s2 = evaluate("cd /root/desk", world_state)
    out, s3 = evaluate("cd -", s2)
    assert out == ["/root"]
    assert s3["current_path"] == "/root"


def test_cd_dash_without_oldpwd_errors(state: dict) -> None:
    out, new = evaluate("cd -", state)
    assert out == ["Error: directory not found"]
    assert _without_exit_status(new) == _without_exit_status(state)


# --- 5. history ---


def test_history_shows_command_log_bash_format(state: dict) -> None:
    _, s2 = evaluate("cd desk", state)
    _, s3 = evaluate("pwd", s2)
    out, _ = evaluate("history", s3)
    assert out == ["    1  cd desk", "    2  pwd"]


def test_history_shows_command_log_bash_format_world(world_state: dict) -> None:
    _, s2 = evaluate("cd /root/desk", world_state)
    _, s3 = evaluate("pwd", s2)
    out, _ = evaluate("history", s3)
    assert out == ["    1  cd /root/desk", "    2  pwd"]


def test_history_empty_when_no_prior_commands(state: dict) -> None:
    out, _ = evaluate("history", state)
    assert out == []
