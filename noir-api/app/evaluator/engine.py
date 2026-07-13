"""コマンド評価エンジン。

パイプライン（設計指示書 § 0.5 / § 8）:
  入力行 → shlex トークナイズ → リダイレクト分解（MVP は `>` `>>` のみ）
        → denylist → allowlist → registry から実装を引いて実行
        → （リダイレクトあれば出力をファイルへ書き込み）→ 出力行 + 新 state

MVP はパイプ `|` と `2>` を扱わない（Phase2 で追加）。実 OS には触れない。
`evaluate` は state を deepcopy してから渡すため、呼び出し側の state は不変。
"""

import copy
import shlex

from app.evaluator import commands as _commands  # noqa: F401  registry 登録のため import
from app.evaluator import fs
from app.evaluator import git_ops as _git_ops  # noqa: F401  registry 登録のため import
from app.evaluator.allowlist import ALLOWLIST, DENYLIST
from app.evaluator.errors import CommandError
from app.evaluator.registry import get_command

_REDIRECTS = (">", ">>")


def _split_redirect(tokens: list[str]) -> tuple[list[str], str | None, bool]:
    """トークン列から `> file` / `>> file` を抜き出す。

    戻り値: (リダイレクト除去後の argv, 出力先パス or None, append か)。
    """
    argv: list[str] = []
    target: str | None = None
    append = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _REDIRECTS:
            if i + 1 >= len(tokens):
                raise CommandError("Error: invalid input")
            append = tok == ">>"
            target = tokens[i + 1]
            i += 2
            continue
        argv.append(tok)
        i += 1
    return argv, target, append


def _write_file(state: dict, path: str, lines: list[str], append: bool) -> None:
    abs_path = fs.normalize(state["current_path"], path)
    node = fs.get_node(state, abs_path)
    text = "\n".join(lines)
    if fs.is_file(node):
        if append and node.get("content"):
            node["content"] = node["content"] + "\n" + text
        else:
            node["content"] = text
        node["mtime"] = fs.now_iso()
        return
    if node is not None:  # ディレクトリ等には書き込めない
        raise CommandError("Error: path not found")
    parent, name = fs.get_parent(state, abs_path)
    if parent is None:
        raise CommandError("Error: path not found")
    parent["children"][name] = fs.new_file(content=text)


def evaluate(command_line: str, state: dict) -> tuple[list[str], dict]:
    """1 行を評価し (出力行, 新 state) を返す。state は変更しない（deepcopy を返す）。"""
    working = copy.deepcopy(state)

    try:
        tokens = shlex.split(command_line)
    except ValueError:
        return ["Error: invalid input"], state  # 引用符が閉じていない等
    if not tokens:
        return [], state

    try:
        argv, target, append = _split_redirect(tokens)
    except CommandError as exc:
        return [str(exc)], state
    if not argv:
        return [], state

    name = argv[0]
    if name in DENYLIST or name not in ALLOWLIST:
        return ["Error: command not allowed"], state

    fn = get_command(name)
    if fn is None:
        # allowlist にはあるが未実装。MVP では利用不可として扱う。
        return ["Error: command not allowed"], state

    try:
        out_lines, new_state = fn(working, argv, [])
        if target is not None:
            _write_file(new_state, target, out_lines, append)
            out_lines = []
    except CommandError as exc:
        # エラーは表示のみ・state は変更しない（設計指示書 § 9）。
        return [str(exc)], state

    # 成功したコマンドを履歴に記録（case_file.sh 判定・リプレイ台帳用）。
    new_state.setdefault("command_log", []).append(command_line)
    return out_lines, new_state
