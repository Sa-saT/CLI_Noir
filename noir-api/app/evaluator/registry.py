"""コマンド registry（デコレータ登録制）。

各コマンドは純粋関数シグネチャ `(state, argv, stdin_lines) -> (stdout_lines, new_state)`
で実装し、`@command("name")` で登録する（設計指示書 § 0.5 / バックエンド_コマンド機能仕様）。
コマンド追加 = 関数を 1 つ書いて登録するだけ。
"""

from collections.abc import Callable

CommandFn = Callable[[dict, list[str], list[str]], tuple[list[str], dict]]

_REGISTRY: dict[str, CommandFn] = {}


def command(*names: str) -> Callable[[CommandFn], CommandFn]:
    def decorator(fn: CommandFn) -> CommandFn:
        for name in names:
            _REGISTRY[name] = fn
        return fn

    return decorator


def get_command(name: str) -> CommandFn | None:
    return _REGISTRY.get(name)
