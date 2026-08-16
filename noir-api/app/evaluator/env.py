"""環境変数アクセスの共通ヘルパー。

state["env_vars"] には 2 通りの形状がある（P3-04c。context/04_task_backlog.md § Part5）:
  - フラット形状（default_state()。Mission 別 state。当面現役）:
    {"PATH": "...", "HOME": "..."}
  - ユーザー別形状（default_world_state()。統合ワールド state）:
    {"detective": {"PATH": "...", "HOME": "..."}}
  Mission21 の PATH 汚染を su 先アカウントに閉じ込めるための変更。

呼び出し側はこのモジュール経由で読み書きすることで、どちらの形状でも同じ
書き方（`env_for(state)["PATH"]` 等）で扱える。
"""

# su で未知のユーザーへ切り替わった際に新規バケットへ与える既定値
# （default_world_state() の detective と同じ値）。
_DEFAULT_USER_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
}


def env_for(state: dict) -> dict[str, str]:
    """現在のユーザーの環境変数 dict を返す（フラット/ユーザー別の両形状に対応）。

    形状判定は env_vars の値に 1 つでも dict があるかどうかで行う（`{}` はフラット
    扱い）。current_user の値では判定しない（$? を _set_status がここ経由でユーザー
    のバケットへ書き込むことで、判定基準を「値に dict があるか」だけに保っている
    ため。current_user で判定すると、フラット形状の state に current_user が乗って
    いるケースと区別できなくなる）。

    フラット形状なら state["env_vars"] そのもの（参照）を返し、既存挙動を変えない。
    ユーザー別形状なら env_vars[current_user] を返す。そのユーザーのバケットが
    無ければ既定値で作ってから返す（su で未知のユーザーに入った場合）。

    返り値は参照なので、呼び出し側が書き換えると state に反映される。
    """
    env_vars = state.setdefault("env_vars", {})
    if any(isinstance(v, dict) for v in env_vars.values()):
        user = state.get("current_user", "detective")
        return env_vars.setdefault(user, dict(_DEFAULT_USER_ENV))
    return env_vars
