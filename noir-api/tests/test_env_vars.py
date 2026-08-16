"""env_vars のユーザー別 dict 対応（P3-04c）。

state["env_vars"] はフラット形状（default_state()）とユーザー別形状
（default_world_state()）の 2 通りがある。本テストは主に、統合ワールド state
でも evaluator が通常どおりコマンドを実行できること（本タスクの主目的）と、
su による PATH 汚染がアカウント単位に閉じ込められること（設計の肝）を検証する。
フラット形状の回帰確認も併せて行う。
"""

from app.evaluator import evaluate
from app.models import default_state, default_world_state


# --- 統合ワールド state（ユーザー別形状）でコマンドが動くこと ---


def test_world_state_ls_runs() -> None:
    """本タスクの主目的: 統合ワールド state で command not found にならないこと。"""
    state = default_world_state()
    out, _ = evaluate("ls /root", state)
    assert out != ["Error: command not found"]
    assert "desk" in out


def test_world_state_cat_runs() -> None:
    state = default_world_state()
    out, _ = evaluate("cat /root/desk/businesscard.txt", state)
    assert out == ["NAME: ???", "ROLE: detective"]


def test_world_state_cd_and_pwd_run() -> None:
    state = default_world_state()
    out, state = evaluate("cd /root/desk", state)
    assert out == []
    out, _ = evaluate("pwd", state)
    assert out == ["/root/desk"]


# --- echo $VAR / printenv がユーザー別バケットを読むこと ---


def test_world_state_echo_path() -> None:
    state = default_world_state()
    out, _ = evaluate("echo $PATH", state)
    assert out == ["/usr/local/bin:/usr/bin:/bin"]


def test_world_state_printenv_path() -> None:
    state = default_world_state()
    out, _ = evaluate("printenv PATH", state)
    assert out == ["/usr/local/bin:/usr/bin:/bin"]


# --- export / unset がユーザー別バケットに反映されること ---


def test_world_state_export_and_unset() -> None:
    state = default_world_state()
    _, state = evaluate("export FOO=bar", state)
    out, state = evaluate("echo $FOO", state)
    assert out == ["bar"]

    _, state = evaluate("unset FOO", state)
    out, _ = evaluate("echo $FOO", state)
    assert out == [""]
    assert "FOO" not in state["env_vars"]["detective"]


# --- su による PATH 汚染のアカウント閉じ込め（設計の肝） ---


def test_world_state_su_isolates_env_vars() -> None:
    state = default_world_state()
    _, state = evaluate("su barman", state)
    _, state = evaluate("export FOO=leaked", state)
    out, state = evaluate("echo $FOO", state)
    assert out == ["leaked"]

    _, state = evaluate("exit", state)  # detective へ復帰
    out, state = evaluate("echo $FOO", state)
    assert out == [""]  # detective 側には漏れていない

    assert state["env_vars"]["barman"]["FOO"] == "leaked"
    assert "FOO" not in state["env_vars"]["detective"]


# --- $? がユーザー別形状のトップレベルを汚さないこと ---


def test_world_state_exit_status_stays_in_user_bucket() -> None:
    state = default_world_state()
    _, state = evaluate("pwd", state)
    assert set(state["env_vars"].keys()) == {"detective"}
    assert state["env_vars"]["detective"]["?"] == "0"

    _, state = evaluate("rm -rf /", state)  # denylist で失敗する
    assert set(state["env_vars"].keys()) == {"detective"}
    assert state["env_vars"]["detective"]["?"] == "1"


# --- 引数無し cd がユーザー別形状でも HOME に移動すること ---


def test_world_state_cd_no_args_goes_home() -> None:
    state = default_world_state()
    _, state = evaluate("cd /root/desk", state)
    out, state = evaluate("cd", state)
    assert out == []
    out, _ = evaluate("pwd", state)
    assert out == ["/root"]


# --- 回帰: フラット形状（default_state()）は従来どおり ---


def test_flat_state_echo_path_unchanged() -> None:
    state = default_state()
    out, _ = evaluate("echo $PATH", state)
    assert out == ["/usr/local/bin:/usr/bin:/bin"]


def test_flat_state_export_and_unset_unchanged() -> None:
    state = default_state()
    _, state = evaluate("export FOO=bar", state)
    out, state = evaluate("echo $FOO", state)
    assert out == ["bar"]

    _, state = evaluate("unset FOO", state)
    out, _ = evaluate("echo $FOO", state)
    assert out == [""]
    assert "FOO" not in state["env_vars"]


def test_flat_state_exit_status_top_level_unchanged() -> None:
    state = default_state()
    _, state = evaluate("pwd", state)
    assert state["env_vars"]["?"] == "0"
    # ユーザー別バケットは作られず、トップレベルに素の PATH/HOME/? のみが残る。
    assert set(state["env_vars"].keys()) <= {"PATH", "HOME", "?"}


def test_flat_state_cd_no_args_goes_home_unchanged() -> None:
    state = default_state()
    state["filesystem"]["root"]["children"]["desk"] = {"type": "dir", "children": {}}
    _, state = evaluate("cd /desk", state)
    out, state = evaluate("cd", state)
    assert out == []
    out, _ = evaluate("pwd", state)
    assert out == ["/root"]
