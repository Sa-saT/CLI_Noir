"""コマンド評価エンジン。

パイプライン（設計指示書 § 0.5 / § 8）:
  入力行 → shlex トークナイズ → パイプ `|` でステージ分割
        → 最終ステージのリダイレクト分解（`>` `>>`）
        → 各ステージ: denylist → allowlist → registry の実装を実行
          （前段 stdout を次段 stdin へ渡す）
        → （リダイレクトあれば最終出力をファイルへ書き込み）→ 出力行 + 新 state

`2>`（stderr）は未対応（Mission18 実装時に追加）。実 OS には触れない。
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


def _split_pipeline(tokens: list[str]) -> list[list[str]]:
    """トークン列を `|` でステージへ分割する（引用符内の | は shlex 済みで安全）。"""
    stages: list[list[str]] = []
    cur: list[str] = []
    for tok in tokens:
        if tok == "|":
            stages.append(cur)
            cur = []
        else:
            cur.append(tok)
    stages.append(cur)
    return stages


def _run_stage(
    argv: list[str], stdin: list[str], state: dict
) -> tuple[list[str], dict]:
    """1 ステージ（denylist→allowlist→registry dispatch）を実行する。"""
    name = argv[0]
    if name in DENYLIST or name not in ALLOWLIST:
        raise CommandError("Error: command not allowed")
    fn = get_command(name)
    if fn is None:
        # allowlist にはあるが未実装。MVP では利用不可として扱う。
        raise CommandError("Error: command not allowed")
    return fn(state, argv, stdin)


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
    if fs.is_proc_path(abs_path):
        raise CommandError("Permission denied")
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

    stages = _split_pipeline(tokens)
    # 空ステージ（`| foo` / `foo |` / `foo || bar`）はパイプ不正。
    if len(stages) > 1 and any(not st for st in stages):
        return ["Error: invalid input"], state

    # リダイレクトは最終ステージにのみ適用する。
    try:
        stages[-1], target, append = _split_redirect(stages[-1])
    except CommandError as exc:
        return [str(exc)], state
    if not stages[-1]:
        # 単段のリダイレクトのみ（`> file`）は no-op。多段での空末尾は不正。
        return ([], state) if len(stages) == 1 else (["Error: invalid input"], state)

    try:
        stdin: list[str] = []
        st_state = working
        out_lines: list[str] = []
        for argv in stages:
            out_lines, st_state = _run_stage(argv, stdin, st_state)
            stdin = out_lines
        if target is not None:
            _write_file(st_state, target, out_lines, append)
            out_lines = []
    except CommandError as exc:
        # エラーは表示のみ・state は変更しない（設計指示書 § 9）。
        return [str(exc)], state

    # 成功したコマンドを履歴に記録（case_file.sh 判定・リプレイ台帳用）。
    st_state.setdefault("command_log", []).append(command_line)
    return out_lines, st_state
