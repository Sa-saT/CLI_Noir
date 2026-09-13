"""環境変数アクセスの共通ヘルパー。

state["env_vars"] はユーザー別形状（default_world_state()。統合ワールド state）:
  {"detective": {"PATH": "...", "HOME": "..."}}
su で切り替えたユーザーごとにバケットが分かれる（Mission21 の PATH 汚染を su 先
アカウントに閉じ込めるための形状）。

呼び出し側はこのモジュール経由で読み書きすることで、`env_for(state)["PATH"]` の
ように現在のユーザーの環境変数を統一的に扱える。
"""

# su で未知のユーザーへ切り替わった際に新規バケットへ与える既定値
# （default_world_state() の detective と同じ値）。
_DEFAULT_USER_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
}


def env_for(state: dict) -> dict[str, str]:
    """現在のユーザー（current_user）の環境変数 dict を返す。

    そのユーザーのバケットが無ければ既定値で作ってから返す（su で未知の
    ユーザーに入った場合）。返り値は参照なので、呼び出し側が書き換えると
    state に反映される（$? を _set_status がここ経由でユーザーのバケットへ
    書き込む、等）。
    """
    env_vars = state.setdefault("env_vars", {})
    user = state.get("current_user", "detective")
    return env_vars.setdefault(user, dict(_DEFAULT_USER_ENV))
