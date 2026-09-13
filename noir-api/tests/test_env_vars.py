"""env_vars のユーザー別 dict 対応（P3-04c）。

state["env_vars"] はユーザー別 dict（default_world_state()）。本テストは、
統合ワールド state でも evaluator が通常どおりコマンドを実行できること
（本タスクの主目的）と、su による PATH 汚染がアカウント単位に閉じ込められる
こと（設計の肝）を検証する。
"""

from app.evaluator import evaluate
from app.models import default_world_state


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
