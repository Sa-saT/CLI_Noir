"""コマンド評価エンジン。

パイプライン（設計指示書 § 0.5 / § 8）:
  入力行 → env_vars による $VAR/$? 展開（シングルクォート内は保持）
        → トークナイズ（引用符情報を保持）→ glob 展開 → `2>` の空白無し表記を分割
        → パイプ `|` でステージ分割
        → 最終ステージのリダイレクト分解（`>` `>>` `2>`）
        → 各ステージ: denylist → allowlist → PATH 解決（絶対パス実行は除外）
          → registry の実装を実行（前段 stdout を次段 stdin へ渡す。
          stderr は state["_stderr"] に集約）
        → （リダイレクトあれば最終出力をファイルへ書き込み。`2>` は指定先へ、
          `2>/dev/null` は破棄、指定無しは stdout の末尾に結合）
        → 実行結果を env_vars["?"]（0=成功/1=失敗）に記録 → 出力行 + 新 state

実 OS には触れない。`evaluate` は state を deepcopy してから渡すため、
呼び出し側の state は不変。
"""

import copy
import fnmatch
import re

from app.evaluator import commands as _commands  # noqa: F401  registry 登録のため import
from app.evaluator import fs
from app.evaluator import git_ops as _git_ops  # noqa: F401  registry 登録のため import
from app.evaluator.allowlist import ALLOWLIST, DENYLIST
from app.evaluator.errors import CommandError
from app.evaluator.registry import get_command

_REDIRECTS = (">", ">>")
_GLOB_CHARS = "*?["

# シェル組み込み相当（実 bash と同じく PATH 解決の対象外。設計指示書 § 4）。
# これが無いと Mission21 で PATH が壊れている間に echo $PATH すら打てなくなる。
_BUILTINS = {
    "cd", "pwd", "echo", "export", "unset", "printenv", "which", "type",
    "history", "clear", "exit", "git",
}
_PATH_BIN_DIRS = ("/bin", "/usr/bin", "/usr/local/bin")

_VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)|\$(\?)")


def _expand_env_vars(command_line: str, env_vars: dict) -> str:
    """コマンド行の `$NAME` / `${NAME}` / `$?` を env_vars で置換する。

    シングルクォート区間は実 bash と同じく展開しない（区間ごとコピー）。
    ダブルクォート区間・裸の単語は展開する。トークナイズより前の生テキストに
    対して行う（設計指示書 § 8。P2-18）。
    """
    out: list[str] = []
    i, n = 0, len(command_line)
    while i < n:
        ch = command_line[i]
        if ch == "'":
            end = command_line.find("'", i + 1)
            if end == -1:
                out.append(command_line[i:])
                break
            out.append(command_line[i : end + 1])
            i = end + 1
            continue
        if ch == "$":
            m = _VAR_REF.match(command_line, i)
            if m:
                name = m.group(1) or m.group(2) or m.group(3)
                default = "0" if name == "?" else ""
                out.append(env_vars.get(name, default))
                i = m.end()
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _resolve_command_name(argv0: str) -> tuple[str, bool]:
    """コマンド名と「絶対パス実行か」を返す。絶対パスは basename で判定・登録引きする。"""
    if argv0.startswith("/"):
        return argv0.rsplit("/", 1)[-1], True
    return argv0, False


def _path_has_bin(state: dict) -> bool:
    path_value = state.get("env_vars", {}).get("PATH", "")
    return any(seg in _PATH_BIN_DIRS for seg in path_value.split(":"))


def _tokenize(command_line: str) -> list[tuple[str, bool]]:
    """shlex.split 相当のトークナイズ + 各トークンが引用符で囲まれていたかを返す。

    glob 展開の判定（引用符付きトークンはリテラル維持=展開しない）に使う。
    バックスラッシュエスケープは未対応（本ゲームのコマンドでは使用しない）。
    未終端の引用符は ValueError（呼び出し側で「Error: invalid input」に変換）。
    """
    tokens: list[tuple[str, bool]] = []
    i, n = 0, len(command_line)
    while i < n:
        while i < n and command_line[i].isspace():
            i += 1
        if i >= n:
            break
        buf: list[str] = []
        quoted = False
        while i < n and not command_line[i].isspace():
            ch = command_line[i]
            if ch in "'\"":
                quoted = True
                quote_char = ch
                i += 1
                start = i
                while i < n and command_line[i] != quote_char:
                    i += 1
                if i >= n:
                    raise ValueError("unterminated quote")
                buf.append(command_line[start:i])
                i += 1
            else:
                buf.append(ch)
                i += 1
        tokens.append(("".join(buf), quoted))
    return tokens


def _glob_matches(pattern: str, state: dict) -> list[str] | None:
    """パターンに一致する名前一覧を返す（マッチ無しは None）。"""
    if "/" in pattern:
        dir_part, _, name_pattern = pattern.rpartition("/")
    else:
        dir_part, name_pattern = "", pattern

    abs_dir = fs.normalize(state["current_path"], dir_part or ".")
    dir_node = fs.get_node(state, abs_dir)
    if not fs.is_dir(dir_node):
        return None

    names = sorted(dir_node.get("children", {}).keys())
    matches = [n for n in names if fnmatch.fnmatch(n, name_pattern)]
    if not matches:
        return None
    if dir_part:
        return [f"{dir_part}/{n}" for n in matches]
    return matches


def _expand_globs(tok_pairs: list[tuple[str, bool]], state: dict) -> list[str]:
    """引用符なしトークンのうち glob 文字を含むものを実在エントリへ展開する
    （bash の既定＝nullglob 無効と同じく、マッチが無ければリテラルのまま渡す）。
    コマンド名（各ステージの第1トークン）には適用しない。
    """
    result: list[str] = []
    at_command_position = True
    for tok, quoted in tok_pairs:
        if tok == "|" and not quoted:
            result.append(tok)
            at_command_position = True
            continue
        if at_command_position:
            result.append(tok)
            at_command_position = False
            continue
        if not quoted and any(ch in tok for ch in _GLOB_CHARS):
            matches = _glob_matches(tok, state)
            if matches is not None:
                result.extend(matches)
                continue
        result.append(tok)
    return result


def _split_glued_redirects(tokens: list[str]) -> list[str]:
    """`2>/dev/null`（空白無し）を `2>` と `/dev/null` の2トークンへ分割する。

    トークナイズは空白区切りのため、`2>` と対象が空白無しで連結されていると
    1トークンになってしまう。`2>` そのものは素通しする。
    """
    result: list[str] = []
    for tok in tokens:
        if tok.startswith("2>") and tok != "2>":
            result.append("2>")
            result.append(tok[2:])
        else:
            result.append(tok)
    return result


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
    """1 ステージ（denylist→allowlist→PATH解決→registry dispatch）を実行する。"""
    name, is_absolute = _resolve_command_name(argv[0])
    if name in DENYLIST or name not in ALLOWLIST:
        raise CommandError("Error: command not allowed")
    # PATH に /bin 系が無い間は組み込み以外のコマンドが引けない（絶対パス実行は除外。
    # Mission21）。
    if not is_absolute and name not in _BUILTINS and not _path_has_bin(state):
        raise CommandError("Error: command not found")
    fn = get_command(name)
    if fn is None:
        # allowlist にはあるが未実装。MVP では利用不可として扱う。
        raise CommandError("Error: command not allowed")
    call_argv = [name, *argv[1:]] if is_absolute else argv
    return fn(state, call_argv, stdin)


def _split_redirect(
    tokens: list[str],
) -> tuple[list[str], str | None, bool, str | None]:
    """トークン列から `> file` / `>> file` / `2> file` を抜き出す。

    戻り値: (リダイレクト除去後の argv, stdout先パスorNone, append か, stderr先パスorNone)。
    """
    argv: list[str] = []
    target: str | None = None
    append = False
    stderr_target: str | None = None
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
        if tok == "2>":
            if i + 1 >= len(tokens):
                raise CommandError("Error: invalid input")
            stderr_target = tokens[i + 1]
            i += 2
            continue
        argv.append(tok)
        i += 1
    return argv, target, append, stderr_target


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


def _set_status(state: dict, code: str) -> dict:
    """終了ステータスを env_vars["?"] に記録する（echo $? の最小実装。P2-15）。"""
    state.setdefault("env_vars", {})["?"] = code
    return state


def evaluate(command_line: str, state: dict) -> tuple[list[str], dict]:
    """1 行を評価し (出力行, 新 state) を返す。state は変更しない（deepcopy を返す）。"""
    working = copy.deepcopy(state)

    expanded_line = _expand_env_vars(command_line, working.get("env_vars", {}))

    try:
        tok_pairs = _tokenize(expanded_line)
    except ValueError:
        return ["Error: invalid input"], _set_status(working, "1")  # 引用符が閉じていない等
    if not tok_pairs:
        # 空行の実行は bash と同じく $? を変更しない。
        return [], state

    tokens = _expand_globs(tok_pairs, working)
    tokens = _split_glued_redirects(tokens)

    stages = _split_pipeline(tokens)
    # 空ステージ（`| foo` / `foo |` / `foo || bar`）はパイプ不正。
    if len(stages) > 1 and any(not st for st in stages):
        return ["Error: invalid input"], _set_status(working, "1")

    # リダイレクトは最終ステージにのみ適用する。
    try:
        stages[-1], target, append, stderr_target = _split_redirect(stages[-1])
    except CommandError as exc:
        return [str(exc)], _set_status(working, "1")
    if not stages[-1]:
        # 単段のリダイレクトのみ（`> file`）は no-op。多段での空末尾は不正。
        if len(stages) == 1:
            return [], _set_status(working, "0")
        return ["Error: invalid input"], _set_status(working, "1")

    working["_stderr"] = []
    try:
        stdin: list[str] = []
        st_state = working
        out_lines: list[str] = []
        for argv in stages:
            out_lines, st_state = _run_stage(argv, stdin, st_state)
            stdin = out_lines

        stderr_lines = st_state.pop("_stderr", [])
        if stderr_target == "/dev/null":
            pass  # 雑音を捨てる（Mission18）
        elif stderr_target is not None:
            _write_file(st_state, stderr_target, stderr_lines, False)
        else:
            out_lines = out_lines + stderr_lines

        if target is not None:
            _write_file(st_state, target, out_lines, append)
            out_lines = []
    except CommandError as exc:
        # エラーは表示のみ・domain state は変更しない（設計指示書 § 9）。
        # ただし $? は失敗を記録する（working は state の deepcopy のまま）。
        st_state.pop("_stderr", None)
        return [str(exc)], _set_status(st_state, "1")

    # 成功したコマンドを履歴に記録（case_file.sh 判定・リプレイ台帳用）。
    st_state.setdefault("command_log", []).append(command_line)
    return out_lines, _set_status(st_state, "0")
