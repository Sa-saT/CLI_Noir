"""UX-01a: 実 bash に不自然な差分を残さないための修正5点のテスト。

対象:
  1. `>file` / `>>file`（空白無し）のリダイレクト
  2. `&&` / `||` / `;` を黙って無視しない（invalid input）
  3. チルダ展開（`~` / `~/...`。`~user` は非対応）
  4. `cd -`（OLDPWD へ移動・移動先を1行表示）
  5. `history`（command_log を bash 書式で表示。Mission15 は informant_history 優先）

統合ワールド state（default_world_state()。/root/desk は最初から解放済み）で検証する。
"""

from app.evaluator import evaluate
from app.evaluator.env import env_for
from app.models.tables import default_world_state
from tests.helpers import state_at_mission


def _without_exit_status(s: dict) -> dict:
    """env_vars[user]["?"]（$? 記録）を除いた env_vars を返す（不変性比較の補助）。"""
    env = s["env_vars"]
    user = s.get("current_user", "detective")
    bucket = {k: v for k, v in env.get(user, {}).items() if k != "?"}
    return {**env, user: bucket}


def state() -> dict:
    """default_world_state()。Mission1 区画（/root/desk）は最初から解放済み。"""
    return default_world_state()


# --- 1. `>file` / `>>file`（空白無し） ---


def test_glued_redirect_write_and_append() -> None:
    s = state()
    _, s2 = evaluate("echo hi >x.txt", s)
    node = s2["filesystem"]["root"]["children"]["x.txt"]
    assert node["content"] == "hi"
    out, _ = evaluate("cat x.txt", s2)
    assert out == ["hi"]

    _, s3 = evaluate("echo bye >>x.txt", s2)
    node3 = s3["filesystem"]["root"]["children"]["x.txt"]
    assert node3["content"] == "hi\nbye"


def test_glued_redirect_write_and_append_in_subdir() -> None:
    s = state()
    _, s2 = evaluate("cd /root/desk", s)
    _, s3 = evaluate("echo hi >x.txt", s2)
    node = s3["filesystem"]["root"]["children"]["desk"]["children"]["x.txt"]
    assert node["content"] == "hi"

    _, s4 = evaluate("echo bye >>x.txt", s3)
    node2 = s4["filesystem"]["root"]["children"]["desk"]["children"]["x.txt"]
    assert node2["content"] == "hi\nbye"


def test_glued_stderr_redirect_not_broken() -> None:
    # 既存の Mission18 挙動（`2>/dev/null` 空白無し）が壊れていないことの確認。
    s = state_at_mission(18)
    out, _ = evaluate('grep -r "witness" /root/archive 2>/dev/null', s)
    joined = "\n".join(out)
    assert "witness report" in joined
    assert "permission denied" not in joined


# --- 2. `&&` / `||` / `;` を黙って無視しない ---


def test_double_ampersand_rejected_and_cd_not_applied() -> None:
    s = state()
    out, new = evaluate("cd desk && pwd", s)
    assert out == ["Error: invalid input"]
    # 最重要: cd だけ黙って実行してしまわないこと（current_path 不変）。
    assert new["current_path"] == s["current_path"]
    assert env_for(new)["?"] == "1"


def test_semicolon_glued_rejected() -> None:
    s = state()
    out, new = evaluate("pwd; ls", s)
    assert out == ["Error: invalid input"]
    assert env_for(new)["?"] == "1"


def test_or_operator_rejected() -> None:
    s = state()
    out, new = evaluate("ls || pwd", s)
    assert out == ["Error: invalid input"]
    assert env_for(new)["?"] == "1"


def test_quoted_operator_is_plain_text() -> None:
    s = state()
    # 引用符の中の `;` `&&` は演算子ではなく文字列（`sed 's/x/y/;'` 等を壊さない）。
    out, new = evaluate('echo "a; b && c"', s)
    assert out == ["a; b && c"]
    assert env_for(new)["?"] == "0"


# --- 3. チルダ展開 ---


def test_tilde_expansion() -> None:
    s = state()
    out, s2 = evaluate("cd ~", s)
    assert out == []
    assert s2["current_path"] == "/root"

    out, _ = evaluate("echo ~", s)
    assert out == ["/root"]

    # シングルクォートは展開しない。
    out, _ = evaluate("echo '~'", s)
    assert out == ["~"]

    # `~user` 形式は非対応（展開しない）。
    out, _ = evaluate("echo ~foo", s)
    assert out == ["~foo"]

    out, _ = evaluate("cat ~/desk/businesscard.txt", s)
    assert out == ["NAME: ???", "ROLE: detective"]


def test_ssh_cd_tilde_returns_to_login_dir() -> None:
    s = state_at_mission(3)
    _, s = evaluate("ssh amusement_park", s)
    _, s = evaluate("cd booth", s)
    assert s["current_path"] == "/gate/booth"

    out, s = evaluate("cd ~", s)
    assert out == []
    assert s["current_path"] == "/gate"


# --- 4. `cd -` ---


def test_cd_dash_round_trip() -> None:
    s = state()
    _, s2 = evaluate("cd desk", s)
    out, s3 = evaluate("cd -", s2)
    assert out == ["/root"]
    assert s3["current_path"] == "/root"

    out, s4 = evaluate("cd -", s3)
    assert out == ["/root/desk"]
    assert s4["current_path"] == "/root/desk"


def test_cd_dash_without_oldpwd_errors() -> None:
    s = state()
    out, new = evaluate("cd -", s)
    assert out == ["Error: directory not found"]
    assert _without_exit_status(new) == _without_exit_status(s)


# --- 5. history ---


def test_history_shows_command_log_bash_format() -> None:
    s = state()
    _, s2 = evaluate("cd desk", s)
    _, s3 = evaluate("pwd", s2)
    out, _ = evaluate("history", s3)
    assert out == ["    1  cd desk", "    2  pwd"]


def test_history_shows_command_log_bash_format_absolute_path() -> None:
    s = state()
    _, s2 = evaluate("cd /root/desk", s)
    _, s3 = evaluate("pwd", s2)
    out, _ = evaluate("history", s3)
    assert out == ["    1  cd /root/desk", "    2  pwd"]


def test_history_empty_when_no_prior_commands() -> None:
    s = state()
    out, _ = evaluate("history", s)
    assert out == []
